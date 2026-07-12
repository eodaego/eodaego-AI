from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.openapi import NO_BODY_ERRORS, WITH_BODY_ERRORS, error_response
from app.core.security import verify_internal_api_key
from app.db.session import get_db
from app.domains.crawling import service
from app.domains.crawling.schema import (
    CongestionSnapshotResponse,
    ScheduleConfigCreate,
    ScheduleConfigResponse,
    ScheduleConfigUpdate,
)

router = APIRouter(
    prefix="/api/v1/crawling/schedules",
    tags=["crawling"],
    dependencies=[Depends(verify_internal_api_key)],
)

_SCHEDULE_NOT_FOUND_RESPONSE = error_response(
    "NOT_FOUND", "schedule config not found", "path의 schedule_id에 해당하는 설정이 없음"
)

_SCHEDULE_CREATE_DESC = """크롤링 작업의 실행 주기를 DB에 등록한다.

**주의:** 이 API로 생성/수정한 스케줄은 즉시 반영되지 않는다. AI 서버가 재시작될 때
(`bootstrap_scheduler`, 앱 기동 시 1회 실행)만 `is_active=true`인 설정이 실제 APScheduler에
등록된다. `job_id`가 등록된 작업 식별자 4종(`crawl_congestion`/`crawl_catalog`/
`crawl_operating_hours`/`crawl_weather`) 중 하나가 아니면 저장은 성공하지만 다음 재시작 시
**로그 없이 조용히** 등록이 스킵된다. `trigger_config` 형식이 `trigger_type`과 맞지 않으면
저장은 성공하지만 다음 재시작 시 트리거 생성에 실패해 **경고 로그를 남기고** 등록이 스킵된다.

`job_id`는 DB 유니크 제약이 있으며, 중복 생성 시 500이 발생한다(409로 매핑되지 않음)."""


@router.post(
    "",
    response_model=ScheduleConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="크롤링 스케줄 설정 생성",
    description=_SCHEDULE_CREATE_DESC,
    responses=WITH_BODY_ERRORS,
)
def create_schedule(
    data: ScheduleConfigCreate, db: Session = Depends(get_db)
) -> ScheduleConfigResponse:
    schedule = service.create_schedule_config(db, data)
    return ScheduleConfigResponse.model_validate(schedule)


@router.get(
    "",
    response_model=list[ScheduleConfigResponse],
    summary="크롤링 스케줄 설정 전체 목록 조회",
    responses=NO_BODY_ERRORS,
)
def list_schedules(db: Session = Depends(get_db)) -> list[ScheduleConfigResponse]:
    """등록된 모든 스케줄 설정을 반환한다(`is_active=false`인 것도 포함). 실제로 현재
    스케줄러에 등록돼 있는지 여부는 이 API로 알 수 없다(DB 상 설정값만 반환).
    """
    schedules = service.list_schedule_configs(db)
    return [ScheduleConfigResponse.model_validate(s) for s in schedules]


@router.patch(
    "/{schedule_id}",
    response_model=ScheduleConfigResponse,
    summary="크롤링 스케줄 설정 부분 수정",
    responses={**WITH_BODY_ERRORS, 404: _SCHEDULE_NOT_FOUND_RESPONSE},
)
def update_schedule(
    schedule_id: int, data: ScheduleConfigUpdate, db: Session = Depends(get_db)
) -> ScheduleConfigResponse:
    """대상이 없으면 404. `job_id`는 수정할 수 없다(스키마에서 제외됨). 수정 사항도 생성과
    동일하게 AI 서버 재시작 후에만 스케줄러에 반영된다.
    """
    schedule = service.get_schedule_config(db, schedule_id)
    if schedule is None:
        detail = "schedule config not found"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    updated = service.update_schedule_config(db, schedule, data)
    return ScheduleConfigResponse.model_validate(updated)


@router.delete(
    "/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="크롤링 스케줄 설정 삭제",
    responses={**WITH_BODY_ERRORS, 404: _SCHEDULE_NOT_FOUND_RESPONSE},
)
def delete_schedule(schedule_id: int, db: Session = Depends(get_db)) -> None:
    """대상이 없으면 404. 삭제해도 이미 실행 중인 스케줄러의 job은 AI 서버가 재시작되기
    전까지 계속 동작한다.
    """
    schedule = service.get_schedule_config(db, schedule_id)
    if schedule is None:
        detail = "schedule config not found"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    service.delete_schedule_config(db, schedule)


congestion_router = APIRouter(
    prefix="/api/v1/congestion",
    tags=["congestion"],
    dependencies=[Depends(verify_internal_api_key)],
)


@congestion_router.get(
    "",
    response_model=list[CongestionSnapshotResponse],
    summary="어린이대공원 혼잡도 스냅샷 목록 조회",
    responses=WITH_BODY_ERRORS,
)
def list_congestion(
    limit: int = Query(
        default=20, ge=1, le=100, description="반환할 최대 건수 (1~100, 기본값 20)"
    ),
    db: Session = Depends(get_db),
) -> list[CongestionSnapshotResponse]:
    """서울시 실시간 도시데이터 API에서 수집한 혼잡도 스냅샷을 최신순(`collected_at` 내림차순)으로
    반환한다. 수집은 `crawl_congestion` 스케줄 job이 담당하며, 이 API는 조회 전용이다
    (호출 시점에 직접 수집을 트리거하지 않는다).
    """
    snapshots = service.list_congestion_snapshots(db, limit=limit)
    return [CongestionSnapshotResponse.model_validate(s) for s in snapshots]
