import logging
from typing import Any

import requests

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_CONNECT_TIMEOUT_SECONDS = 5
_READ_TIMEOUT_SECONDS = 60


def call_chat(model: str, messages: list[dict[str, str]]) -> str:
    settings = get_settings()
    url = f"{settings.suh_aider_base_url.rstrip('/')}/api/chat"
    headers = {"Content-Type": "application/json", "X-API-Key": settings.suh_aider_api_key}
    body: dict[str, Any] = {"model": model, "messages": messages, "stream": False}
    try:
        response = requests.post(
            url,
            headers=headers,
            json=body,
            timeout=(_CONNECT_TIMEOUT_SECONDS, _READ_TIMEOUT_SECONDS),
        )
        response.raise_for_status()
        payload = response.json()
        return str(payload["message"]["content"])
    except requests.RequestException as exc:
        status_code = getattr(exc.response, "status_code", "unknown")
        body_summary = getattr(exc.response, "text", "")[:200]
        logger.warning(
            "SUH-AIder /api/chat 호출 실패 (status=%s, body=%s)", status_code, body_summary
        )
        raise RuntimeError(f"SUH-AIder /api/chat 호출 실패 (status={status_code})") from exc
    except (KeyError, TypeError) as exc:
        logger.warning("SUH-AIder /api/chat 응답 형식이 올바르지 않습니다", exc_info=True)
        raise RuntimeError("SUH-AIder /api/chat 응답 형식이 올바르지 않습니다") from exc


def list_models() -> dict[str, Any]:
    settings = get_settings()
    url = f"{settings.suh_aider_base_url.rstrip('/')}/api/tags"
    headers = {"X-API-Key": settings.suh_aider_api_key}
    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=(_CONNECT_TIMEOUT_SECONDS, _READ_TIMEOUT_SECONDS),
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        return payload
    except requests.RequestException as exc:
        status_code = getattr(exc.response, "status_code", "unknown")
        body_summary = getattr(exc.response, "text", "")[:200]
        logger.warning(
            "SUH-AIder /api/tags 호출 실패 (status=%s, body=%s)", status_code, body_summary
        )
        raise RuntimeError(f"SUH-AIder /api/tags 호출 실패 (status={status_code})") from exc
