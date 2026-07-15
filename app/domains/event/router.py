from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.job_lock import JobAlreadyRunningError
from app.core.openapi import COMMON_ERRORS, error_response
from app.core.schema import CrawlResult
from app.core.security import verify_internal_api_key
from app.db.session import get_db
from app.domains.event import service
from app.domains.event.schema import CulturalEventResponse

router = APIRouter(
    prefix="/api/v1/events",
    tags=["event"],
    dependencies=[Depends(verify_internal_api_key)],
)


@router.get(
    "",
    response_model=list[CulturalEventResponse],
    summary="어린이대공원 행사·공연 목록 조회",
    responses=COMMON_ERRORS,
)
def list_events(db: Session = Depends(get_db)) -> list[CulturalEventResponse]:
    """가장 최근 crawl_event 실행 시점 기준으로 유효했던 행사 목록을 시작일
    (`start_date`) 오름차순으로 반환한다. 수집은 `crawl_event` 스케줄 job이 담당하며,
    이 API는 조회 전용이다(호출 시점에 직접 수집을 트리거하지 않는다).
    """
    events = service.list_cultural_events(db)
    return [CulturalEventResponse.model_validate(e) for e in events]


_EVENT_CRAWL_ALREADY_RUNNING_RESPONSE = error_response(
    "CONFLICT",
    "event crawl already running",
    "crawl_event job이 이미 실행 중(스케줄된 실행 포함)",
)


@router.post(
    "/crawl",
    response_model=CrawlResult,
    summary="행사·공연 데이터 즉시 수집",
    responses={**COMMON_ERRORS, 409: _EVENT_CRAWL_ALREADY_RUNNING_RESPONSE},
)
def trigger_event_crawl() -> CrawlResult:
    """스케줄과 무관하게 행사 데이터 수집을 즉시 실행하고 완료될 때까지 대기한 뒤
    결과를 반환한다. 이번 수집 결과로 기존 데이터를 전체 교체한다(삭제 후 재삽입).
    이미 같은 수집(스케줄된 실행 포함)이 진행 중이면 409를 반환한다.
    """
    try:
        return service.crawl_event_job()
    except JobAlreadyRunningError:
        detail = "event crawl already running"
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from None
