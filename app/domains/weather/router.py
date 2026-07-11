from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import verify_internal_api_key
from app.db.session import get_db
from app.domains.weather import service
from app.domains.weather.schema import WeatherSnapshotResponse

router = APIRouter(
    prefix="/api/v1/weather",
    tags=["weather"],
    dependencies=[Depends(verify_internal_api_key)],
)


@router.get("/current", response_model=WeatherSnapshotResponse)
def get_current_weather(db: Session = Depends(get_db)) -> WeatherSnapshotResponse:
    snapshot = service.get_latest_weather_snapshot(db)
    if snapshot is None:
        detail = "weather snapshot not found"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    return WeatherSnapshotResponse.model_validate(snapshot)


@router.get("", response_model=list[WeatherSnapshotResponse])
def list_weather(
    limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db)
) -> list[WeatherSnapshotResponse]:
    snapshots = service.list_weather_snapshots(db, limit=limit)
    return [WeatherSnapshotResponse.model_validate(s) for s in snapshots]
