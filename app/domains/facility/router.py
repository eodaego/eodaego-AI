from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.job_lock import JobAlreadyRunningError
from app.core.openapi import COMMON_ERRORS, error_response
from app.core.schema import CrawlResult
from app.core.security import verify_internal_api_key
from app.db.session import get_db
from app.domains.facility import service
from app.domains.facility.schema import (
    AmusementRideCreate,
    AmusementRideResponse,
    AmusementRideUpdate,
    FacilityCreate,
    FacilityResponse,
    FacilityUpdate,
    OperatingHoursSectionResponse,
)

router = APIRouter(
    prefix="/api/v1/facility",
    tags=["facility"],
    dependencies=[Depends(verify_internal_api_key)],
)

_RIDE_NOT_FOUND_RESPONSE = error_response(
    "NOT_FOUND", "amusement ride not found", "path의 ride_id에 해당하는 놀이기구가 없음"
)


_FACILITY_NOT_FOUND_RESPONSE = error_response(
    "NOT_FOUND", "facility not found", "path의 facility_id에 해당하는 시설이 없음"
)


@router.get(
    "",
    response_model=list[FacilityResponse],
    summary="시설 전체 목록 조회",
    responses=COMMON_ERRORS,
)
def list_facilities(
    category: str | None = Query(default=None, description="지정 시 해당 category만 필터링."),
    db: Session = Depends(get_db),
) -> list[FacilityResponse]:
    """시설 정보를 반환한다. `category` 쿼리 파라미터를 지정하면 해당 분류만 필터링한다.
    공식 데이터로 채워진 기존 시설(`scripts/import_facility_locations.py`로 1회성 임포트됨) 외에,
    관리자가 `POST /api/v1/facility`로 직접 등록한 시설(예: `category="출입문"`)도 포함된다.
    """
    facilities = service.list_facilities(db, category=category)
    return [FacilityResponse.model_validate(f) for f in facilities]


@router.post(
    "",
    response_model=FacilityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="시설 생성 (관리자)",
    responses={
        **COMMON_ERRORS,
        409: error_response(
            "CONFLICT",
            "facility code already exists",
            "code를 지정했고 그 값이 이미 다른 시설에 사용 중임(IntegrityError를 서버가 직접 "
            "감지해 409로 매핑함). code를 생략하면(null) 이 충돌이 발생하지 않는다.",
        ),
    },
)
def create_facility(data: FacilityCreate, db: Session = Depends(get_db)) -> FacilityResponse:
    """관리자가 직접 시설을 등록한다. `external_id`는 공공데이터 크롤링 전용 필드라 이
    경로로 생성하는 행에는 항상 null이 저장된다(요청 스키마에도 포함되지 않는다). `code`가
    이미 다른 시설에서 사용 중이면 409를 반환한다.
    """
    try:
        facility = service.create_facility(db, data)
    except IntegrityError:
        db.rollback()
        detail = "facility code already exists"
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from None
    return FacilityResponse.model_validate(facility)


@router.patch(
    "/{facility_id}",
    response_model=FacilityResponse,
    summary="시설 부분 수정",
    responses={**COMMON_ERRORS, 404: _FACILITY_NOT_FOUND_RESPONSE},
)
def update_facility(
    facility_id: int, data: FacilityUpdate, db: Session = Depends(get_db)
) -> FacilityResponse:
    """대상이 없으면 404. `category`, `name`은 요청에 필드 자체를 포함하면 null을 허용하지
    않는다(DB NOT NULL 제약 반영, 422) — 필드를 아예 생략해야 기존 값이 유지된다.
    """
    facility = service.get_facility(db, facility_id)
    if facility is None:
        detail = "facility not found"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    updated = service.update_facility(db, facility, data)
    return FacilityResponse.model_validate(updated)


@router.delete(
    "/{facility_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="시설 삭제",
    responses={**COMMON_ERRORS, 404: _FACILITY_NOT_FOUND_RESPONSE},
)
def delete_facility(facility_id: int, db: Session = Depends(get_db)) -> None:
    """대상이 없으면 404."""
    facility = service.get_facility(db, facility_id)
    if facility is None:
        detail = "facility not found"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    service.delete_facility(db, facility)


@router.get(
    "/operating-hours",
    response_model=list[OperatingHoursSectionResponse],
    summary="운영시간 안내 섹션 목록 조회",
    responses=COMMON_ERRORS,
)
def list_operating_hours(db: Session = Depends(get_db)) -> list[OperatingHoursSectionResponse]:
    """서울시설공단 공식 페이지의 운영시간 안내를 크롤링해 저장한 데이터를 `display_order`
    오름차순으로 반환한다(수집은 `crawl_operating_hours` 스케줄 job이 담당, 매 수집 시 전체
    삭제 후 재삽입하는 방식이라 id가 크롤링마다 바뀔 수 있다).
    """
    sections = service.list_operating_hours_sections(db)
    return [OperatingHoursSectionResponse.model_validate(s) for s in sections]


_OPERATING_HOURS_CRAWL_ALREADY_RUNNING_RESPONSE = error_response(
    "CONFLICT",
    "operating hours crawl already running",
    "crawl_operating_hours job이 이미 실행 중(스케줄된 실행 포함)",
)


@router.post(
    "/operating-hours/crawl",
    response_model=CrawlResult,
    summary="운영시간 안내 데이터 즉시 수집",
    responses={**COMMON_ERRORS, 409: _OPERATING_HOURS_CRAWL_ALREADY_RUNNING_RESPONSE},
)
def trigger_operating_hours_crawl() -> CrawlResult:
    """스케줄과 무관하게 운영시간 안내 크롤링을 즉시 실행하고 완료될 때까지 대기한 뒤 결과를
    반환한다. 이미 같은 수집(스케줄된 실행 포함)이 진행 중이면 409를 반환한다.
    """
    try:
        return service.crawl_operating_hours_job()
    except JobAlreadyRunningError:
        detail = "operating hours crawl already running"
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from None


@router.post(
    "/import",
    response_model=CrawlResult,
    summary="시설 위치정보 xlsx 즉시 임포트",
    responses=COMMON_ERRORS,
)
def trigger_facility_locations_import(db: Session = Depends(get_db)) -> CrawlResult:
    """공식 xlsx(`data/seoul_childrens_grand_park_facility_locations.xlsx`)를 읽어
    `external_id` 기준으로 upsert한다. 로컬 개발 환경에서 `alembic upgrade head` 이후
    이 엔드포인트를 한 번 호출하면 prod와 동일한 시설 위치정보를 반영할 수 있다. 이미
    존재하는 시설(`external_id` 기준)은 중복 추가되지 않고 값만 갱신된다. 관리자가
    `POST /api/v1/facility`로 직접 등록한 시설(`external_id=null`)에는 영향을 주지 않는다.
    """
    return service.import_facility_locations(db)


@router.post(
    "/amusement-rides",
    response_model=AmusementRideResponse,
    status_code=status.HTTP_201_CREATED,
    summary="놀이기구 생성 (관리자)",
    responses={
        **COMMON_ERRORS,
        409: error_response(
            "CONFLICT",
            "amusement ride name already exists",
            "name이 이미 존재하는 놀이기구와 중복됨 (IntegrityError를 서버가 직접 감지해 "
            "409로 매핑함 — prompt/schedule 도메인의 중복 생성과 달리 500이 아님). "
            "단, PATCH(수정)에서 이름이 중복되는 경우는 이 처리가 없어 500이 발생한다.",
        ),
    },
)
def create_amusement_ride(
    data: AmusementRideCreate, db: Session = Depends(get_db)
) -> AmusementRideResponse:
    try:
        ride = service.create_amusement_ride(db, data)
    except IntegrityError:
        db.rollback()
        detail = "amusement ride name already exists"
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from None
    return AmusementRideResponse.model_validate(ride)


@router.get(
    "/amusement-rides",
    response_model=list[AmusementRideResponse],
    summary="놀이기구 전체 목록 조회",
    responses=COMMON_ERRORS,
)
def list_amusement_rides(db: Session = Depends(get_db)) -> list[AmusementRideResponse]:
    """정렬 조건 없이 전체 놀이기구를 반환한다(운영 중지된 것도 포함)."""
    rides = service.list_amusement_rides(db)
    return [AmusementRideResponse.model_validate(r) for r in rides]


@router.patch(
    "/amusement-rides/{ride_id}",
    response_model=AmusementRideResponse,
    summary="놀이기구 부분 수정",
    responses={**COMMON_ERRORS, 404: _RIDE_NOT_FOUND_RESPONSE},
)
def update_amusement_ride(
    ride_id: int, data: AmusementRideUpdate, db: Session = Depends(get_db)
) -> AmusementRideResponse:
    """대상이 없으면 404. `name`, `is_active`는 요청에 필드 자체를 포함하면 null을 허용하지
    않는다(DB NOT NULL 제약 반영, 422) — 필드를 아예 생략해야 기존 값이 유지된다.
    """
    ride = service.get_amusement_ride(db, ride_id)
    if ride is None:
        detail = "amusement ride not found"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    updated = service.update_amusement_ride(db, ride, data)
    return AmusementRideResponse.model_validate(updated)


@router.delete(
    "/amusement-rides/{ride_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="놀이기구 삭제",
    responses={**COMMON_ERRORS, 404: _RIDE_NOT_FOUND_RESPONSE},
)
def delete_amusement_ride(ride_id: int, db: Session = Depends(get_db)) -> None:
    """대상이 없으면 404."""
    ride = service.get_amusement_ride(db, ride_id)
    if ride is None:
        detail = "amusement ride not found"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    service.delete_amusement_ride(db, ride)
