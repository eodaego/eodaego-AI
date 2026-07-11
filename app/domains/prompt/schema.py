from pydantic import BaseModel, ConfigDict

from app.core.kst import KstDatetime


class PromptTemplateCreate(BaseModel):
    name: str
    template_text: str
    is_active: bool = True


class PromptTemplateUpdate(BaseModel):
    name: str | None = None
    template_text: str | None = None
    is_active: bool | None = None


class PromptTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    template_text: str
    is_active: bool
    updated_at: KstDatetime
