from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.openapi import WITH_BODY_ERRORS, error_response
from app.core.security import verify_internal_api_key
from app.db.session import get_db
from app.domains.ai import service
from app.domains.ai.schema import AiChatRequest, AiChatResponse

router = APIRouter(
    prefix="/api/v1/ai",
    tags=["ai"],
    dependencies=[Depends(verify_internal_api_key)],
)


@router.post(
    "/chat",
    response_model=AiChatResponse,
    summary="AI 챗 응답 생성 (관리자 제어형)",
    response_description="SUH-AIder가 생성한 응답 텍스트",
    responses={
        **WITH_BODY_ERRORS,
        503: error_response(
            "SERVICE_UNAVAILABLE",
            "활성화된 프롬프트가 없습니다",
            "is_active=true인 프롬프트 템플릿이 하나도 없음 — "
            "POST 또는 PATCH /api/v1/prompts로 먼저 활성 템플릿을 만들어야 함",
        ),
        502: error_response(
            "BAD_GATEWAY",
            "SUH-AIder /api/chat 호출 실패 (status=500)",
            "SUH-AIder 호출이 실패했거나(연결 오류·타임아웃·4xx/5xx) "
            "응답 바디에 message.content 필드가 없는 등 형식이 예상과 다름",
        ),
    },
)
def chat(data: AiChatRequest, db: Session = Depends(get_db)) -> AiChatResponse:
    """현재 활성화된(`is_active=true`) 프롬프트 템플릿 1개로 system 메시지를 구성하고,
    SUH-AIder(`POST {SUH_AIDER_BASE_URL}/api/chat`)를 호출해 응답을 생성한다.

    **처리 순서**
    1. `prompt_template` 테이블에서 `is_active=true`인 행을 1개 조회한다. 없으면 503.
    2. 활성 프롬프트의 `template_text`에서 `$변수명` 자리표시자를 `variables`로 치환한다
       (`string.Template.safe_substitute` — 없는 변수는 무시되고 `$변수명` 그대로 남음).
    3. 치환된 텍스트를 `system` 메시지로, `user_message`가 있으면 `user` 메시지를 추가한다.
    4. SUH-AIder에 `{"model": <활성 프롬프트의 model>, "messages": [...], "stream": false}`로
       POST 요청한다(연결 타임아웃 5초, 읽기 타임아웃 60초).
    5. 호출 실패 또는 응답 형식 오류 시 502.

    프롬프트 템플릿 자체는 `/api/v1/prompts` API로 관리한다.
    """
    content = service.generate_chat_response(db, data)
    return AiChatResponse(content=content)
