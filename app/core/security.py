from fastapi import Header, HTTPException, status

from app.core.config import get_settings


def verify_internal_api_key(
    x_internal_api_key: str = Header(
        ...,
        description=(
            "BE(eodaego-server)가 내부망 인증에 사용하는 고정 API 키. "
            "AI 서버의 `.env.{APP_ENV}`에 설정된 INTERNAL_API_KEY와 값이 정확히 일치해야 한다. "
            "헤더 자체가 없으면 422(필수 파라미터 누락)가, 값이 일치하지 않으면 401이 반환된다."
        ),
    ),
) -> None:
    settings = get_settings()
    if x_internal_api_key != settings.internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid internal api key"
        )
