import logging
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from app.core.llm_types import ImageInput, LlmProvider
from app.domains.ai import gemini_client, suh_aider_client

logger = logging.getLogger(__name__)

_PROVIDER_CLIENTS: dict[LlmProvider, Callable[..., str]] = {
    "SUH_AIDER": suh_aider_client.call_chat,
    "GEMINI": gemini_client.call_chat,
}


def call_with_fallback[T](
    providers: list[tuple[LlmProvider, str]],
    system: str,
    prompt: str,
    parse: Callable[[str], T],
    response_format: dict[str, Any] | None = None,
    images: list[ImageInput] | None = None,
) -> tuple[T, LlmProvider, str]:
    """providers를 (provider, model) 순서대로 1회씩 시도한다. call_chat 실패(RuntimeError)
    또는 parse 실패(ValidationError)는 모두 다음 provider로 넘어가는 트리거다. providers가
    비어 있거나 전부 실패하면 각 provider별 실패 사유를 모아 RuntimeError로 최종 실패한다.
    성공하면 (파싱된 결과, 실제로 성공한 provider, 그 model) 3-튜플을 반환한다."""
    if not providers:
        raise RuntimeError("호출 가능한 LLM provider가 없습니다")

    errors: list[str] = []
    for index, (provider, model) in enumerate(providers):
        client = _PROVIDER_CLIENTS.get(provider)
        if client is None:
            errors.append(f"{provider}: 등록되지 않은 provider")
            continue
        try:
            content = client(
                model=model,
                system=system,
                prompt=prompt,
                response_format=response_format,
                images=images,
            )
            return parse(content), provider, model
        except (RuntimeError, ValidationError) as exc:
            errors.append(f"{provider}: {exc}")
            if index + 1 < len(providers):
                next_provider = providers[index + 1][0]
                logger.warning(
                    "%s 실패 → fallback provider(%s) 시도: %s", provider, next_provider, exc
                )
            continue

    raise RuntimeError(f"모든 LLM provider 호출 실패: {'; '.join(errors)}")
