from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.llm_types import LlmProvider
from app.db.base import Base


class PromptTemplate(Base):
    __tablename__ = "prompt_template"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    purpose: Mapped[str] = mapped_column(String(20))
    template_text: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    providers: Mapped[list["PromptTemplateProvider"]] = relationship(
        back_populates="prompt_template",
        order_by="PromptTemplateProvider.priority, PromptTemplateProvider.id",
        cascade="all, delete-orphan",
    )


class PromptTemplateProvider(Base):
    __tablename__ = "prompt_template_provider"

    id: Mapped[int] = mapped_column(primary_key=True)
    prompt_template_id: Mapped[int] = mapped_column(
        ForeignKey("prompt_template.id", ondelete="CASCADE")
    )
    provider: Mapped[LlmProvider] = mapped_column(String(20))
    model: Mapped[str] = mapped_column(String(100))
    priority: Mapped[int] = mapped_column(Integer)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())

    prompt_template: Mapped["PromptTemplate"] = relationship(back_populates="providers")
