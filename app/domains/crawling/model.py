from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, String, func, true
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
    congestion_level: Mapped[float] = mapped_column(Float)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class OperatingHoursSnapshot(Base):
    __tablename__ = "operating_hours_snapshot"

    id: Mapped[int] = mapped_column(primary_key=True)
    place_ref_key: Mapped[str] = mapped_column(String(100))
    raw_hours_text: Mapped[str] = mapped_column(String(500))
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
