from typing import Any

from pydantic import BaseModel, ConfigDict

from app.core.kst import KstDatetime


class WeatherSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    place_ref_key: str
    temperature: float
    humidity: int
    precipitation_type: str
    wind_speed: float
    sky_condition: str | None
    hourly_forecast: list[dict[str, Any]]
    observed_at: KstDatetime
    collected_at: KstDatetime
