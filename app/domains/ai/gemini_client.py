import logging
from typing import Any

import requests

from app.core.config import get_settings
from app.core.llm_types import ImageInput

logger = logging.getLogger(__name__)

_CONNECT_TIMEOUT_SECONDS = 5
_READ_TIMEOUT_SECONDS = 120
_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


def call_chat(
    model: str,
    system: str,
    prompt: str,
    response_format: dict[str, Any] | None = None,
    images: list[ImageInput] | None = None,
) -> str:
    settings = get_settings()
    url = f"{_BASE_URL}/models/{model}:generateContent"
    headers = {"Content-Type": "application/json", "x-goog-api-key": settings.gemini_api_key}

    parts: list[dict[str, Any]] = [{"text": prompt}]
    if images is not None:
        for image in images:
            parts.append({"inlineData": {"mimeType": image.mime_type, "data": image.base64_data}})

    generation_config: dict[str, Any] = {"temperature": 0}
    if response_format is not None:
        generation_config["responseMimeType"] = "application/json"
        # responseSchema(OpenAPI 3.0 서브셋)는 Pydantic model_json_schema()가 생성하는
        # $ref/$defs/anyOf를 지원하지 않아 400을 반환한다. responseJsonSchema는 표준 JSON
        # Schema를 그대로 받아들이므로 이걸 사용한다(gemini-2.5 계열부터 지원).
        generation_config["responseJsonSchema"] = response_format

    body: dict[str, Any] = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": generation_config,
    }

    logger.info(
        "Gemini generateContent 요청: model=%s, format=%s, images=%d개\n[system]\n%s\n[prompt]\n%s",
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
        content = payload["candidates"][0]["content"]["parts"][0]["text"]
        logger.info(
            "Gemini generateContent 응답: finishReason=%s, usage=%s\n[content]\n%s",
            payload["candidates"][0].get("finishReason"),
            payload.get("usageMetadata"),
            content,
        )
        return str(content)
    except requests.RequestException as exc:
        status_code = getattr(exc.response, "status_code", "unknown")
        body_text = getattr(exc.response, "text", "")
        logger.warning(
            "Gemini generateContent 호출 실패 (status=%s, body=%s)", status_code, body_text
        )
        raise RuntimeError(f"Gemini generateContent 호출 실패 (status={status_code})") from exc
    except (KeyError, IndexError, TypeError) as exc:
        logger.warning("Gemini generateContent 응답 형식이 올바르지 않습니다", exc_info=True)
        raise RuntimeError("Gemini generateContent 응답 형식이 올바르지 않습니다") from exc
