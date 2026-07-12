from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.openapi import NO_BODY_ERRORS, WITH_BODY_ERRORS, error_response
from app.core.security import verify_internal_api_key
from app.db.session import get_db
from app.domains.weather import service
from app.domains.weather.schema import WeatherSnapshotResponse

router = APIRouter(
    prefix="/api/v1/weather",
    tags=["weather"],
    dependencies=[Depends(verify_internal_api_key)],
)


@router.get(
    "/current",
    response_model=WeatherSnapshotResponse,
    summary="최신 날씨 스냅샷 조회",
    responses={
        **NO_BODY_ERRORS,
        404: error_response(
            "NOT_FOUND",
            "weather snapshot not found",
            "아직 한 번도 수집되지 않음 (crawl_weather job 미실행)",
        ),
    },
)
def get_current_weather(db: Session = Depends(get_db)) -> WeatherSnapshotResponse:
    """가장 최근에 수집된(`collected_at` 최댓값) 날씨 스냅샷 1건을 반환한다."""
    snapshot = service.get_latest_weather_snapshot(db)
    if snapshot is None:
        detail = "weather snapshot not found"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    return WeatherSnapshotResponse.model_validate(snapshot)


@router.get(
    "",
    response_model=list[WeatherSnapshotResponse],
    summary="날씨 스냅샷 목록 조회",
    responses=WITH_BODY_ERRORS,
)
def list_weather(
    limit: int = Query(
        default=20, ge=1, le=100, description="반환할 최대 건수 (1~100, 기본값 20)"
    ),
    db: Session = Depends(get_db),
) -> list[WeatherSnapshotResponse]:
    """수집된 날씨 스냅샷을 최신순(`collected_at` 내림차순)으로 최대 `limit`건 반환한다."""
    snapshots = service.list_weather_snapshots(db, limit=limit)
    return [WeatherSnapshotResponse.model_validate(s) for s in snapshots]
