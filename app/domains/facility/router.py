from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.openapi import NO_BODY_ERRORS, WITH_BODY_ERRORS, error_response
from app.core.security import verify_internal_api_key
from app.db.session import get_db
from app.domains.facility import service
from app.domains.facility.schema import (
    AmusementRideCreate,
    AmusementRideResponse,
    AmusementRideUpdate,
    FacilityResponse,
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


@router.get(
    "",
    response_model=list[FacilityResponse],
    summary="시설 전체 목록 조회",
    responses=NO_BODY_ERRORS,
)
def list_facilities(db: Session = Depends(get_db)) -> list[FacilityResponse]:
    """공식 데이터 기반 시설 정보를 반환한다. **주의:** 현재 코드베이스에는 `facility` 테이블을
    채우는 크롤링/등록 로직이 없다 — 이 API는 조회만 제공하며, 데이터가 비어 있을 수 있다.
    """
    facilities = service.list_facilities(db)
    return [FacilityResponse.model_validate(f) for f in facilities]


@router.get(
    "/operating-hours",
    response_model=list[OperatingHoursSectionResponse],
    summary="운영시간 안내 섹션 목록 조회",
    responses=NO_BODY_ERRORS,
)
def list_operating_hours(db: Session = Depends(get_db)) -> list[OperatingHoursSectionResponse]:
    """서울시설공단 공식 페이지의 운영시간 안내를 크롤링해 저장한 데이터를 `display_order`
    오름차순으로 반환한다(수집은 `crawl_operating_hours` 스케줄 job이 담당, 매 수집 시 전체
    삭제 후 재삽입하는 방식이라 id가 크롤링마다 바뀔 수 있다).
    """
    sections = service.list_operating_hours_sections(db)
    return [OperatingHoursSectionResponse.model_validate(s) for s in sections]


@router.post(
    "/amusement-rides",
    response_model=AmusementRideResponse,
    status_code=status.HTTP_201_CREATED,
    summary="놀이기구 생성 (관리자)",
    responses={
        **WITH_BODY_ERRORS,
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
    responses=NO_BODY_ERRORS,
)
def list_amusement_rides(db: Session = Depends(get_db)) -> list[AmusementRideResponse]:
    """정렬 조건 없이 전체 놀이기구를 반환한다(운영 중지된 것도 포함)."""
    rides = service.list_amusement_rides(db)
    return [AmusementRideResponse.model_validate(r) for r in rides]


@router.patch(
    "/amusement-rides/{ride_id}",
    response_model=AmusementRideResponse,
    summary="놀이기구 부분 수정",
    responses={**WITH_BODY_ERRORS, 404: _RIDE_NOT_FOUND_RESPONSE},
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
    responses={**WITH_BODY_ERRORS, 404: _RIDE_NOT_FOUND_RESPONSE},
)
def delete_amusement_ride(ride_id: int, db: Session = Depends(get_db)) -> None:
    """대상이 없으면 404."""
    ride = service.get_amusement_ride(db, ride_id)
    if ride is None:
        detail = "amusement ride not found"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    service.delete_amusement_ride(db, ride)
