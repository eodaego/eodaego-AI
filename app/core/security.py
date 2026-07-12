from fastapi import Header, HTTPException, status

from app.core.config import get_settings


def verify_internal_api_key(
    x_internal_api_key: str = Header(
        ...,
        description=(
            "BE(eodaego-server)가 내부망 인증에 사용하는 고정 API 키. "
            "AI 서버의 `.env.{APP_ENV}`에 설정된 INTERNAL_API_KEY와 값이 정확히 일치해야 하며, "
            "일치하지 않거나 헤더 자체가 없으면 401을 반환한다."
        ),
    ),
) -> None:
    settings = get_settings()
    if x_internal_api_key != settings.internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid internal api key"
        )
