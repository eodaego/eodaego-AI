from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, func, true
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ScheduleConfig(Base):
    __tablename__ = "schedule_config"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[str] = mapped_column(String(100), unique=True)
    trigger_type: Mapped[str] = mapped_column(String(20))
    trigger_config: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CongestionSnapshot(Base):
    __tablename__ = "congestion_snapshot"

    id: Mapped[int] = mapped_column(primary_key=True)
    place_ref_key: Mapped[str] = mapped_column(String(100))
    congestion_level: Mapped[str] = mapped_column(String(20))
    congestion_message: Mapped[str] = mapped_column(String(200))
    population_min: Mapped[int] = mapped_column(Integer)
    population_max: Mapped[int] = mapped_column(Integer)
    forecast: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
