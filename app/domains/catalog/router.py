from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.job_lock import JobAlreadyRunningError
from app.core.openapi import COMMON_ERRORS, error_response
from app.core.security import verify_internal_api_key
from app.db.session import get_db
from app.domains.catalog import service
from app.domains.catalog.schema import AnimalResponse, CatalogCrawlResult, PlantResponse

router = APIRouter(
    prefix="/api/v1/catalog",
    tags=["catalog"],
    dependencies=[Depends(verify_internal_api_key)],
)


@router.get(
    "/animals",
    response_model=list[AnimalResponse],
    summary="동물 도감 전체 목록 조회",
    responses=COMMON_ERRORS,
)
def list_animals(db: Session = Depends(get_db)) -> list[AnimalResponse]:
    """서울시설공단 어린이대공원 동물 도감 게시판을 크롤링해 저장한 데이터를 반환한다
    (수집은 `crawl_catalog` 스케줄 job이 담당, 이 API는 조회 전용). 정렬 조건 없음.
    """
    animals = service.list_animals(db)
    return [AnimalResponse.model_validate(a) for a in animals]


@router.get(
    "/plants",
    response_model=list[PlantResponse],
    summary="식물 도감 전체 목록 조회",
    responses=COMMON_ERRORS,
)
def list_plants(db: Session = Depends(get_db)) -> list[PlantResponse]:
    """서울시설공단 어린이대공원 식물 도감 게시판을 크롤링해 저장한 데이터를 반환한다
    (수집은 `crawl_catalog` 스케줄 job이 담당, 이 API는 조회 전용). 정렬 조건 없음.
    """
    plants = service.list_plants(db)
    return [PlantResponse.model_validate(p) for p in plants]


_CATALOG_CRAWL_ALREADY_RUNNING_RESPONSE = error_response(
    "CONFLICT",
    "catalog crawl already running",
    "crawl_catalog job이 이미 실행 중(스케줄된 실행 포함)",
)


@router.post(
    "/crawl",
    response_model=CatalogCrawlResult,
    summary="동식물 도감 데이터 즉시 수집",
    responses={**COMMON_ERRORS, 409: _CATALOG_CRAWL_ALREADY_RUNNING_RESPONSE},
)
def trigger_catalog_crawl() -> CatalogCrawlResult:
    """스케줄과 무관하게 동물/식물 도감·위치동기화 3단계를 순서대로 즉시 실행하고 완료될
    때까지 대기한 뒤 단계별 결과를 반환한다. 이미 같은 수집(스케줄된 실행 포함)이 진행 중이면
    409를 반환한다. 3단계는 서로 독립적으로 실패할 수 있으며(예: 동물은 성공, 식물은 실패),
    각 단계의 실패는 HTTP 상태가 아니라 응답 바디의 `success: false`로 표현된다.
    """
    try:
        return service.crawl_catalog_job()
    except JobAlreadyRunningError:
        detail = "catalog crawl already running"
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from None
