from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.prompt.model import PromptTemplate
from app.domains.prompt.schema import PromptTemplateCreate, PromptTemplateUpdate


def create_prompt_template(db: Session, data: PromptTemplateCreate) -> PromptTemplate:
    prompt = PromptTemplate(**data.model_dump())
    db.add(prompt)
    db.commit()
    db.refresh(prompt)
    return prompt


def list_prompt_templates(db: Session) -> list[PromptTemplate]:
    return list(db.scalars(select(PromptTemplate)).all())


def get_prompt_template(db: Session, prompt_id: int) -> PromptTemplate | None:
    return db.get(PromptTemplate, prompt_id)


def update_prompt_template(
    db: Session, prompt: PromptTemplate, data: PromptTemplateUpdate
) -> PromptTemplate:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(prompt, field, value)
    db.commit()
    db.refresh(prompt)
    return prompt


def delete_prompt_template(db: Session, prompt: PromptTemplate) -> None:
    db.delete(prompt)
    db.commit()
