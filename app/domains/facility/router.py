from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

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


@router.get("", response_model=list[FacilityResponse])
def list_facilities(db: Session = Depends(get_db)) -> list[FacilityResponse]:
    facilities = service.list_facilities(db)
    return [FacilityResponse.model_validate(f) for f in facilities]


@router.get("/operating-hours", response_model=list[OperatingHoursSectionResponse])
def list_operating_hours(db: Session = Depends(get_db)) -> list[OperatingHoursSectionResponse]:
    sections = service.list_operating_hours_sections(db)
    return [OperatingHoursSectionResponse.model_validate(s) for s in sections]


@router.post(
    "/amusement-rides",
    response_model=AmusementRideResponse,
    status_code=status.HTTP_201_CREATED,
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


@router.get("/amusement-rides", response_model=list[AmusementRideResponse])
def list_amusement_rides(db: Session = Depends(get_db)) -> list[AmusementRideResponse]:
    rides = service.list_amusement_rides(db)
    return [AmusementRideResponse.model_validate(r) for r in rides]


@router.patch("/amusement-rides/{ride_id}", response_model=AmusementRideResponse)
def update_amusement_ride(
    ride_id: int, data: AmusementRideUpdate, db: Session = Depends(get_db)
) -> AmusementRideResponse:
    ride = service.get_amusement_ride(db, ride_id)
    if ride is None:
        detail = "amusement ride not found"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    updated = service.update_amusement_ride(db, ride, data)
    return AmusementRideResponse.model_validate(updated)


@router.delete("/amusement-rides/{ride_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_amusement_ride(ride_id: int, db: Session = Depends(get_db)) -> None:
    ride = service.get_amusement_ride(db, ride_id)
    if ride is None:
        detail = "amusement ride not found"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    service.delete_amusement_ride(db, ride)
