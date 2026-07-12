from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.openapi import COMMON_ERRORS
from app.core.security import verify_internal_api_key
from app.db.session import get_db
from app.domains.catalog import service
from app.domains.catalog.schema import AnimalResponse, PlantResponse

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
