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
            "생략(null)하거나 빈 문자열이면 system 메시지만 SUH-AIder에 전달된다 "
            "(truthy 값일 때만 user 메시지가 추가됨)."
        ),
        examples=["오늘 날씨에 어울리는 코스를 추천해줘"],
    )


class AiChatResponse(BaseModel):
    content: str = Field(description="SUH-AIder가 생성한 응답 텍스트 원문")


class SuhAiderModelDetails(BaseModel):
    parent_model: str = Field(
        description="이 모델이 파생된 원본 모델 경로/이름. 파생 관계가 없으면 빈 문자열."
    )
    format: str = Field(description="모델 파일 포맷 (예: 'gguf')")
    family: str = Field(description="모델 계열 (예: 'qwen35', 'gemma3')")
    families: list[str] | None = Field(
        default=None, description="모델이 속한 계열 목록. 없으면 null."
    )
    parameter_size: str = Field(description="파라미터 크기 문자열 (예: '4.0B', '752.16M')")
    quantization_level: str = Field(description="양자화 수준 (예: 'Q4_K_M', 'F16')")
    context_length: int | None = Field(
        default=None,
        description=(
            "컨텍스트 윈도우 길이(토큰 수). "
            "SUH-AIder 응답에 이 필드가 없는 모델도 있어 선택 필드로 둔다."
        ),
    )
    embedding_length: int | None = Field(
        default=None,
        description=(
            "임베딩 벡터 차원 수. SUH-AIder 응답에 이 필드가 없는 모델도 있어 선택 필드로 둔다."
        ),
    )


class SuhAiderModel(BaseModel):
    name: str = Field(description="모델 식별자 (예: 'functiongemma:latest')")
    model: str = Field(description="SUH-AIder API 호출 시 사용하는 모델명. 보통 name과 동일.")
    modified_at: str = Field(
        description=(
            "모델이 SUH-AIder에 등록/수정된 시각(ISO 8601 문자열). 모델마다 초 이하 자릿수가 "
            "달라 datetime으로 파싱하지 않고 원문 문자열 그대로 전달한다."
        )
    )
    size: int = Field(description="모델 파일 크기(바이트)")
    digest: str = Field(description="모델 파일의 SHA-256 다이제스트")
    details: SuhAiderModelDetails = Field(description="모델 상세 정보")
    capabilities: list[str] = Field(
        description=(
            "모델이 지원하는 기능 목록 "
            "(예: ['completion', 'tools', 'vision', 'thinking', 'embedding'])"
        )
    )


class AiModelListResponse(BaseModel):
    models: list[SuhAiderModel] = Field(
        description=(
            "SUH-AIder(Ollama 호환)에 현재 등록된 모델 목록. GET /api/tags 응답을 그대로 반영한다."
        )
    )
