from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PreferenceCategoryMapping(Base):
    __tablename__ = "preference_category_mapping"
    __table_args__ = (
        UniqueConstraint("preference_tag", "category", name="uq_preference_category_mapping"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    preference_tag: Mapped[str] = mapped_column(String(20))
    category: Mapped[str] = mapped_column(String(50))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RecommendationHistory(Base):
    __tablename__ = "recommendation_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    request: Mapped[dict[str, Any]] = mapped_column(JSON)
    is_success: Mapped[bool] = mapped_column(Boolean)
    response: Mapped[dict[str, Any] | None] = mapped_column(JSON(none_as_null=True))
    failure_status_code: Mapped[int | None] = mapped_column(Integer)
    failure_reason: Mapped[str | None] = mapped_column(Text)
    prompt_template_id: Mapped[int | None] = mapped_column(Integer)
    model: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
