import logging
from typing import Any

import requests

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_CONNECT_TIMEOUT_SECONDS = 5
_READ_TIMEOUT_SECONDS = 120
_CHAT_PATH = "/api/flask/ollama/chat"
_MODELS_PATH = "/api/flask/ollama/models"


def call_chat(
    model: str,
    system: str,
    prompt: str,
    response_format: dict[str, Any] | None = None,
    images: list[str] | None = None,
) -> str:
    settings = get_settings()
    url = f"{settings.suh_aider_base_url.rstrip('/')}{_CHAT_PATH}"
    headers = {"Content-Type": "application/json", "X-API-Key": settings.suh_aider_api_key}
    body: dict[str, Any] = {
        "model": model,
        "system": system,
        "prompt": prompt,
        "temperature": 0,
        "auto_unload": True,
    }
    if response_format is not None:
        body["format"] = response_format
    if images is not None:
        body["images"] = images
    logger.info(
        "SUH-AIder %s 요청: model=%s, format=%s, images=%d개\n[system]\n%s\n[prompt]\n%s",
        _CHAT_PATH,
        model,
        "있음" if response_format is not None else "없음",
        len(images) if images is not None else 0,
        system,
        prompt,
    )
    try:
        response = requests.post(
            url,
            headers=headers,
            json=body,
            timeout=(_CONNECT_TIMEOUT_SECONDS, _READ_TIMEOUT_SECONDS),
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        logger.info(
            "SUH-AIder %s 응답: success=%s, model=%s, metrics=%s\n[content]\n%s",
            _CHAT_PATH,
            payload.get("success"),
            payload.get("model"),
            payload.get("metrics"),
            payload.get("content"),
        )
        if payload.get("success") is False:
            logger.warning("SUH-AIder %s 응답 실패 (payload=%s)", _CHAT_PATH, payload)
            raise RuntimeError(f"SUH-AIder {_CHAT_PATH} 응답 실패 (success=false)")
        return str(payload["content"])
    except requests.RequestException as exc:
        status_code = getattr(exc.response, "status_code", "unknown")
        body_text = getattr(exc.response, "text", "")
        logger.warning(
            "SUH-AIder %s 호출 실패 (status=%s, body=%s)", _CHAT_PATH, status_code, body_text
        )
        raise RuntimeError(f"SUH-AIder {_CHAT_PATH} 호출 실패 (status={status_code})") from exc
    except (KeyError, TypeError, AttributeError) as exc:
        logger.warning("SUH-AIder %s 응답 형식이 올바르지 않습니다", _CHAT_PATH, exc_info=True)
        raise RuntimeError(f"SUH-AIder {_CHAT_PATH} 응답 형식이 올바르지 않습니다") from exc


def list_models() -> dict[str, Any]:
    settings = get_settings()
    url = f"{settings.suh_aider_base_url.rstrip('/')}{_MODELS_PATH}"
    headers = {"X-API-Key": settings.suh_aider_api_key}
    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=(_CONNECT_TIMEOUT_SECONDS, _READ_TIMEOUT_SECONDS),
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        if payload.get("success") is False:
            logger.warning("SUH-AIder %s 응답 실패 (payload=%s)", _MODELS_PATH, str(payload)[:200])
            raise RuntimeError(f"SUH-AIder {_MODELS_PATH} 응답 실패 (success=false)")
        return payload
    except requests.RequestException as exc:
        status_code = getattr(exc.response, "status_code", "unknown")
        body_summary = getattr(exc.response, "text", "")[:200]
        logger.warning(
            "SUH-AIder %s 호출 실패 (status=%s, body=%s)", _MODELS_PATH, status_code, body_summary
        )
        raise RuntimeError(f"SUH-AIder {_MODELS_PATH} 호출 실패 (status={status_code})") from exc
    except (KeyError, TypeError, AttributeError) as exc:
        logger.warning("SUH-AIder %s 응답 형식이 올바르지 않습니다", _MODELS_PATH, exc_info=True)
        raise RuntimeError(f"SUH-AIder {_MODELS_PATH} 응답 형식이 올바르지 않습니다") from exc
