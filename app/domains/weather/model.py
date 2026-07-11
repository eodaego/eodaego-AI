from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WeatherSnapshot(Base):
    __tablename__ = "weather_snapshot"

    id: Mapped[int] = mapped_column(primary_key=True)
    place_ref_key: Mapped[str] = mapped_column(String(100))
    temperature: Mapped[float] = mapped_column(Float)
    humidity: Mapped[int] = mapped_column(Integer)
    precipitation_type: Mapped[str] = mapped_column(String(20))
    wind_speed: Mapped[float] = mapped_column(Float)
    sky_condition: Mapped[str | None] = mapped_column(String(20), nullable=True)
    hourly_forecast: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
