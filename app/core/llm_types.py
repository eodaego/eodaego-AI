from typing import Literal, NamedTuple

LlmProvider = Literal["SUH_AIDER", "GEMINI"]


class ImageInput(NamedTuple):
    """LLM에 전달할 이미지 1장. base64 인코딩된 바이트와 원본 MIME 타입을 함께 갖는다
    (SUH-AIder는 MIME 타입을 요구하지 않아 무시하지만, Gemini의 inline_data는 필요로 한다)."""

    base64_data: str
    mime_type: str
