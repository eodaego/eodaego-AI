from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint, func
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
