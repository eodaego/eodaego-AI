from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.prompt.model import PromptTemplate, PromptTemplateProvider
from app.domains.prompt.schema import (
    PromptPurpose,
    PromptTemplateCreate,
    PromptTemplateProviderCreate,
    PromptTemplateProviderUpdate,
    PromptTemplateUpdate,
)


def _deactivate_other_prompt_templates(db: Session, exclude_id: int, purpose: str) -> None:
    stmt = select(PromptTemplate).where(
        PromptTemplate.is_active.is_(True),
        PromptTemplate.purpose == purpose,
        PromptTemplate.id != exclude_id,
    )
    for other in db.scalars(stmt).all():
        other.is_active = False


def create_prompt_template(db: Session, data: PromptTemplateCreate) -> PromptTemplate:
    prompt = PromptTemplate(**data.model_dump())
    db.add(prompt)
    db.flush()
    if prompt.is_active:
        _deactivate_other_prompt_templates(db, exclude_id=prompt.id, purpose=prompt.purpose)
    db.commit()
    db.refresh(prompt)
    return prompt


def list_prompt_templates(db: Session) -> list[PromptTemplate]:
    return list(db.scalars(select(PromptTemplate)).all())


def get_prompt_template(db: Session, prompt_id: int) -> PromptTemplate | None:
    return db.get(PromptTemplate, prompt_id)


def get_active_prompt_template(db: Session, purpose: PromptPurpose) -> PromptTemplate | None:
    stmt = select(PromptTemplate).where(
        PromptTemplate.is_active.is_(True), PromptTemplate.purpose == purpose
    )
    return db.scalars(stmt).first()


def update_prompt_template(
    db: Session, prompt: PromptTemplate, data: PromptTemplateUpdate
) -> PromptTemplate:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(prompt, field, value)
    if prompt.is_active:
        _deactivate_other_prompt_templates(db, exclude_id=prompt.id, purpose=prompt.purpose)
    db.commit()
    db.refresh(prompt)
    return prompt


def delete_prompt_template(db: Session, prompt: PromptTemplate) -> None:
    db.delete(prompt)
    db.commit()


def create_prompt_template_provider(
    db: Session, prompt: PromptTemplate, data: PromptTemplateProviderCreate
) -> PromptTemplateProvider:
    provider = PromptTemplateProvider(prompt_template_id=prompt.id, **data.model_dump())
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider


def list_prompt_template_providers(db: Session, prompt_id: int) -> list[PromptTemplateProvider]:
    stmt = (
        select(PromptTemplateProvider)
        .where(PromptTemplateProvider.prompt_template_id == prompt_id)
        .order_by(PromptTemplateProvider.priority, PromptTemplateProvider.id)
    )
    return list(db.scalars(stmt).all())


def get_prompt_template_provider(db: Session, provider_id: int) -> PromptTemplateProvider | None:
    return db.get(PromptTemplateProvider, provider_id)


def update_prompt_template_provider(
    db: Session, provider: PromptTemplateProvider, data: PromptTemplateProviderUpdate
) -> PromptTemplateProvider:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(provider, field, value)
    db.commit()
    db.refresh(provider)
    return provider


def delete_prompt_template_provider(db: Session, provider: PromptTemplateProvider) -> None:
    db.delete(provider)
    db.commit()
