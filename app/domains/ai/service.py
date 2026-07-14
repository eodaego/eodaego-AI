from string import Template

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.domains.ai.schema import AiChatRequest
from app.domains.ai.suh_aider_client import call_chat
from app.domains.prompt.service import get_active_prompt_template


def generate_chat_response(db: Session, data: AiChatRequest) -> str:
    prompt = get_active_prompt_template(db, purpose="chat")
    if prompt is None:
        detail = "활성화된 프롬프트가 없습니다"
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)

    system_content = Template(prompt.template_text).safe_substitute(data.variables)
    messages = [{"role": "system", "content": system_content}]
    if data.user_message:
        messages.append({"role": "user", "content": data.user_message})

    try:
        return call_chat(model=prompt.model, messages=messages)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
