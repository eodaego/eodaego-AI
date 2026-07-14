from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.openapi import COMMON_ERRORS, error_response
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

_NOT_FOUND_RESPONSE = error_response(
    "NOT_FOUND", "prompt template not found", "path의 prompt_id에 해당하는 템플릿이 없음"
)


@router.post(
    "",
    response_model=PromptTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="프롬프트 템플릿 생성",
    responses=COMMON_ERRORS,
)
def create_prompt(
    data: PromptTemplateCreate, db: Session = Depends(get_db)
) -> PromptTemplateResponse:
    """새 프롬프트 템플릿을 생성한다. `is_active=true`(기본값)로 생성하면 같은 트랜잭션 내에서
    같은 `purpose`로 활성화돼 있던 다른 템플릿들만 자동으로 비활성화한다(purpose별 활성
    템플릿 최대 1개 유지 — purpose가 다르면 동시에 활성화될 수 있다).

    `name`이 이미 존재하면 500이 발생한다(`IntegrityError`를 별도로 잡지 않음 — 생성 전
    `GET /api/v1/prompts`로 중복 여부를 먼저 확인하는 것을 권장한다).
    """
    prompt = service.create_prompt_template(db, data)
    return PromptTemplateResponse.model_validate(prompt)


@router.get(
    "",
    response_model=list[PromptTemplateResponse],
    summary="프롬프트 템플릿 전체 목록 조회",
    responses=COMMON_ERRORS,
)
def list_prompts(db: Session = Depends(get_db)) -> list[PromptTemplateResponse]:
    """정렬 조건 없이 `prompt_template` 테이블의 모든 행을 반환한다."""
    prompts = service.list_prompt_templates(db)
    return [PromptTemplateResponse.model_validate(p) for p in prompts]


@router.patch(
    "/{prompt_id}",
    response_model=PromptTemplateResponse,
    summary="프롬프트 템플릿 부분 수정",
    responses={**COMMON_ERRORS, 404: _NOT_FOUND_RESPONSE},
)
def update_prompt(
    prompt_id: int, data: PromptTemplateUpdate, db: Session = Depends(get_db)
) -> PromptTemplateResponse:
    """요청 바디에 포함된 필드만 반영한다(생략된 필드는 기존 값 유지). 대상이 없으면 404.

    수정 결과 `is_active=true`가 되면(명시적으로 true를 보냈거나 이미 활성 상태인 템플릿을
    수정한 경우) 같은 `purpose`의 다른 템플릿들을 자동으로 비활성화해 purpose별 활성 템플릿을
    항상 최대 1개로 유지한다. 이 요청으로 `purpose` 자체가 바뀌면, 배타적 활성화는 바뀐
    이후의 purpose 그룹을 기준으로 적용된다.
    """
    prompt = service.get_prompt_template(db, prompt_id)
    if prompt is None:
        detail = "prompt template not found"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    updated = service.update_prompt_template(db, prompt, data)
    return PromptTemplateResponse.model_validate(updated)


@router.delete(
    "/{prompt_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="프롬프트 템플릿 삭제",
    responses={**COMMON_ERRORS, 404: _NOT_FOUND_RESPONSE},
)
def delete_prompt(prompt_id: int, db: Session = Depends(get_db)) -> None:
    """대상이 없으면 404. 활성 템플릿(is_active=true)을 삭제해도 다른 템플릿이 자동으로
    활성화되지 않으므로, 삭제 후 해당 purpose의 활성 템플릿이 0개가 되면 그 purpose를 쓰는
    API(POST /api/v1/ai/chat 또는 POST /api/v1/recommendation/routes)가 503을 반환한다.
    """
    prompt = service.get_prompt_template(db, prompt_id)
    if prompt is None:
        detail = "prompt template not found"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    service.delete_prompt_template(db, prompt)
