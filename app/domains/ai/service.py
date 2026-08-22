import logging
from string import Template

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.domains.ai.llm_router import call_with_fallback
from app.domains.ai.schema import AiChatRequest, AiModelListResponse
from app.domains.ai.suh_aider_client import list_models
from app.domains.prompt.service import get_active_prompt_template

logger = logging.getLogger(__name__)

_DEFAULT_PROMPT = "위 지침에 따라 응답해줘."


def generate_chat_response(db: Session, data: AiChatRequest) -> str:
    prompt = get_active_prompt_template(db, purpose="chat")
    if prompt is None:
        detail = "활성화된 프롬프트가 없습니다"
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)

    providers = [(p.provider, p.model) for p in prompt.providers if p.is_enabled]
    if not providers:
        detail = "사용 가능한 LLM provider가 없습니다"
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)

    system_content = Template(prompt.template_text).safe_substitute(data.variables)
    user_prompt = data.user_message if data.user_message else _DEFAULT_PROMPT

    try:
        result, _, _ = call_with_fallback(
            providers=providers,
            system=system_content,
            prompt=user_prompt,
            parse=lambda content: content,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return result


def get_available_models() -> AiModelListResponse:
    try:
        payload = list_models()
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    try:
        return AiModelListResponse.model_validate(payload)
    except ValidationError as exc:
        logger.warning(
            "SUH-AIder /api/flask/ollama/models 응답 형식이 올바르지 않습니다", exc_info=True
        )
        detail = "SUH-AIder /api/flask/ollama/models 응답 형식이 올바르지 않습니다"
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail) from exc
