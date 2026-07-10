from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func, true
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Facility(Base):
    __tablename__ = "facility"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[int] = mapped_column(unique=True)
    category: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(100))
    intro: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    facility_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AmusementRide(Base):
    __tablename__ = "amusement_ride"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class OperatingHoursSection(Base):
    __tablename__ = "operating_hours_section"

    id: Mapped[int] = mapped_column(primary_key=True)
    section_title: Mapped[str] = mapped_column(String(100))
    content_html: Mapped[str] = mapped_column(Text)
    display_order: Mapped[int] = mapped_column(Integer)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
