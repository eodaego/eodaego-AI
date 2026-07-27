from typing import Any

from pydantic import BaseModel, Field


class AiChatRequest(BaseModel):
    variables: dict[str, Any] = Field(
        default={},
        description=(
            "활성 프롬프트 템플릿의 `$변수명` 자리표시자에 치환할 값 매핑. "
            "`string.Template.safe_substitute`로 치환되므로, 여기 없는 변수명은 무시되고 "
            "`$변수명` 문자열이 그대로 남는다(에러가 발생하지 않음)."
        ),
        examples=[{"place_name": "어린이대공원", "weather": "맑음"}],
    )
    user_message: str | None = Field(
        default=None,
        description=(
            "활성 프롬프트의 system 메시지에 이어 전달할 사용자 메시지. "
            '생략(null)하거나 빈 문자열이면 기본 문구("위 지침에 따라 응답해줘.")가 대신 '
            "SUH-AIder의 prompt로 전달된다."
        ),
        examples=["오늘 날씨에 어울리는 코스를 추천해줘"],
    )


class AiChatResponse(BaseModel):
    content: str = Field(description="SUH-AIder가 생성한 응답 텍스트 원문")


class SuhAiderModel(BaseModel):
    name: str = Field(description="모델 식별자 (예: 'gemma3:4b')")
    family: str = Field(description="모델 계열 (예: 'gemma3', 'qwen3')")
    parameter_size: str = Field(description="파라미터 크기 문자열 (예: '4.3B', '751.63M')")
    size: int = Field(description="모델 파일 크기(바이트)")


class AiModelListResponse(BaseModel):
    models: list[SuhAiderModel] = Field(
        description=(
            "SUH-AIder(Ollama 호환)에 현재 등록된 모델 목록. "
            "GET /api/flask/ollama/models 응답의 models 배열을 그대로 반영한다."
        )
    )
