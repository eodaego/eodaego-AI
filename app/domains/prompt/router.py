from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import verify_internal_api_key
from app.db.session import get_db
from app.domains.prompt import service
from app.domains.prompt.schema import (
    PromptTemplateCreate,
    PromptTemplateResponse,
    PromptTemplateUpdate,
)

router = APIRouter(
    prefix="/api/v1/prompts",
    tags=["prompts"],
    dependencies=[Depends(verify_internal_api_key)],
)


@router.post("", response_model=PromptTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_prompt(
    data: PromptTemplateCreate, db: Session = Depends(get_db)  # noqa: B008
) -> PromptTemplateResponse:
    prompt = service.create_prompt_template(db, data)
    return PromptTemplateResponse.model_validate(prompt)


@router.get("", response_model=list[PromptTemplateResponse])
def list_prompts(db: Session = Depends(get_db)) -> list[PromptTemplateResponse]:  # noqa: B008
    prompts = service.list_prompt_templates(db)
    return [PromptTemplateResponse.model_validate(p) for p in prompts]


@router.patch("/{prompt_id}", response_model=PromptTemplateResponse)
def update_prompt(
    prompt_id: int, data: PromptTemplateUpdate, db: Session = Depends(get_db)  # noqa: B008
) -> PromptTemplateResponse:
    prompt = service.get_prompt_template(db, prompt_id)
    if prompt is None:
        detail = "prompt template not found"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    updated = service.update_prompt_template(db, prompt, data)
    return PromptTemplateResponse.model_validate(updated)


@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prompt(prompt_id: int, db: Session = Depends(get_db)) -> None:  # noqa: B008
    prompt = service.get_prompt_template(db, prompt_id)
    if prompt is None:
        detail = "prompt template not found"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    service.delete_prompt_template(db, prompt)
