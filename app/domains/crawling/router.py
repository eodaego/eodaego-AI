from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

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


@router.post("", response_model=ScheduleConfigResponse, status_code=status.HTTP_201_CREATED)
def create_schedule(
    data: ScheduleConfigCreate, db: Session = Depends(get_db)
) -> ScheduleConfigResponse:
    schedule = service.create_schedule_config(db, data)
    return ScheduleConfigResponse.model_validate(schedule)


@router.get("", response_model=list[ScheduleConfigResponse])
def list_schedules(db: Session = Depends(get_db)) -> list[ScheduleConfigResponse]:
    schedules = service.list_schedule_configs(db)
    return [ScheduleConfigResponse.model_validate(s) for s in schedules]


@router.patch("/{schedule_id}", response_model=ScheduleConfigResponse)
def update_schedule(
    schedule_id: int, data: ScheduleConfigUpdate, db: Session = Depends(get_db)
) -> ScheduleConfigResponse:
    schedule = service.get_schedule_config(db, schedule_id)
    if schedule is None:
        detail = "schedule config not found"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    updated = service.update_schedule_config(db, schedule, data)
    return ScheduleConfigResponse.model_validate(updated)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(schedule_id: int, db: Session = Depends(get_db)) -> None:
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


@congestion_router.get("", response_model=list[CongestionSnapshotResponse])
def list_congestion(
    limit: int = 20, db: Session = Depends(get_db)
) -> list[CongestionSnapshotResponse]:
    snapshots = service.list_congestion_snapshots(db, limit=limit)
    return [CongestionSnapshotResponse.model_validate(s) for s in snapshots]
