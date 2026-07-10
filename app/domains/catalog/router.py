from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import verify_internal_api_key
from app.db.session import get_db
from app.domains.catalog import service
from app.domains.catalog.schema import AnimalResponse, PlantResponse

router = APIRouter(
    prefix="/api/v1/catalog",
    tags=["catalog"],
    dependencies=[Depends(verify_internal_api_key)],
)


@router.get("/animals", response_model=list[AnimalResponse])
def list_animals(db: Session = Depends(get_db)) -> list[AnimalResponse]:
    animals = service.list_animals(db)
    return [AnimalResponse.model_validate(a) for a in animals]


@router.get("/plants", response_model=list[PlantResponse])
def list_plants(db: Session = Depends(get_db)) -> list[PlantResponse]:
    plants = service.list_plants(db)
    return [PlantResponse.model_validate(p) for p in plants]
