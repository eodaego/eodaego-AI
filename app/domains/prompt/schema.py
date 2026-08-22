from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.kst import KstDatetime
from app.core.llm_types import LlmProvider

PromptPurpose = Literal["chat", "recommendation", "photo_recognition"]

_NAME_DESC = (
    "템플릿 식별용 이름. DB에 유니크 제약이 걸려 있으며, 중복 생성 시 별도 처리 없이 "
    "500 INTERNAL_SERVER_ERROR가 발생한다(사전에 GET /api/v1/prompts로 중복 여부 확인 권장)."
)
_PURPOSE_DESC = (
    "이 템플릿이 사용되는 용도. 'chat'은 POST /api/v1/ai/chat, 'recommendation'은 "
    "POST /api/v1/recommendation/routes, 'photo_recognition'은 "
    "POST /api/v1/recognition/identify에서 사용된다. 활성 템플릿(is_active=true)은 "
    "용도(purpose)별로 각각 최대 1개까지 존재할 수 있다(용도가 다르면 동시에 활성화 가능)."
)
_TEMPLATE_TEXT_DESC = (
    "AI 챗의 system 메시지로 사용될 템플릿 원문. `$변수명`(또는 `${변수명}`) 형태의 "
    "자리표시자를 포함할 수 있으며, 각 용도(purpose)의 API 호출 시 해당 API가 구성한 "
    "변수로 치환된다(치환되지 않은 자리표시자는 문자열 그대로 남는다)."
)
_IS_ACTIVE_CREATE_DESC = (
    "true로 설정(기본값)하면 같은 purpose로 기존에 활성화돼 있던 다른 모든 프롬프트 템플릿이 "
    "자동으로 is_active=false로 전환된다 — 용도(purpose)별로 활성 템플릿은 항상 최대 1개로 "
    "유지된다(배타적 활성화). 활성 템플릿이 각 용도의 API에서 사용된다."
)
_PROVIDER_DESC = (
    "LLM provider 식별자. 'SUH_AIDER'(로컬 개인 LLM 서버) 또는 'GEMINI'(Google Gemini API)."
)
_PROVIDER_MODEL_DESC = "해당 provider에 전달할 모델 식별자 문자열. 이 서버는 값을 검증하지 않는다."
_PRIORITY_DESC = (
    "낮을수록 먼저 시도된다(1=주 provider, 2=1차 fallback, ...). 같은 템플릿 내에서 값이 "
    "같으면 id 오름차순으로 정렬된다(별도 유니크 제약 없음)."
)
_IS_ENABLED_DESC = "false면 이 provider 행은 호출 순서에서 건너뛴다(삭제 없이 임시 비활성화)."


class PromptTemplateCreate(BaseModel):
    name: str = Field(description=_NAME_DESC, examples=["기본 코스 추천 프롬프트"])
    purpose: PromptPurpose = Field(description=_PURPOSE_DESC, examples=["recommendation"])
    template_text: str = Field(
        description=_TEMPLATE_TEXT_DESC,
        examples=["오늘 $place_name의 날씨는 $weather 입니다. 이에 어울리는 코스를 추천해주세요."],
    )
    is_active: bool = Field(default=True, description=_IS_ACTIVE_CREATE_DESC)


class PromptTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, description=f"{_NAME_DESC} 생략 시 기존 값 유지.")
    purpose: PromptPurpose | None = Field(
        default=None, description=f"{_PURPOSE_DESC} 생략 시 기존 값 유지."
    )
    template_text: str | None = Field(
        default=None, description=f"{_TEMPLATE_TEXT_DESC} 생략 시 기존 값 유지."
    )
    is_active: bool | None = Field(
        default=None,
        description=(
            f"{_IS_ACTIVE_CREATE_DESC} 생략 시 기존 값 유지. false로 바꿔 해당 purpose의 활성 "
            "템플릿이 0개가 되면 그 용도의 API가 503을 반환하게 되므로 주의한다."
        ),
    )


class PromptTemplateProviderCreate(BaseModel):
    provider: LlmProvider = Field(description=_PROVIDER_DESC, examples=["SUH_AIDER"])
    model: str = Field(description=_PROVIDER_MODEL_DESC, examples=["gemma4:e4b"])
    priority: int = Field(description=_PRIORITY_DESC, examples=[1])
    is_enabled: bool = Field(default=True, description=_IS_ENABLED_DESC)


class PromptTemplateProviderUpdate(BaseModel):
    provider: LlmProvider | None = Field(
        default=None, description=f"{_PROVIDER_DESC} 생략 시 기존 값 유지."
    )
    model: str | None = Field(
        default=None, description=f"{_PROVIDER_MODEL_DESC} 생략 시 기존 값 유지."
    )
    priority: int | None = Field(
        default=None, description=f"{_PRIORITY_DESC} 생략 시 기존 값 유지."
    )
    is_enabled: bool | None = Field(
        default=None, description=f"{_IS_ENABLED_DESC} 생략 시 기존 값 유지."
    )


class PromptTemplateProviderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="provider 행 PK")
    provider: LlmProvider = Field(description=_PROVIDER_DESC)
    model: str = Field(description=_PROVIDER_MODEL_DESC)
    priority: int = Field(description=_PRIORITY_DESC)
    is_enabled: bool = Field(description=_IS_ENABLED_DESC)


class PromptTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="프롬프트 템플릿 PK")
    name: str = Field(description=_NAME_DESC)
    purpose: PromptPurpose = Field(description=_PURPOSE_DESC)
    template_text: str = Field(description=_TEMPLATE_TEXT_DESC)
    is_active: bool = Field(
        description="현재 활성화 여부. 같은 purpose 내에서 최대 1개만 true일 수 있다."
    )
    providers: list[PromptTemplateProviderResponse] = Field(
        description="이 템플릿에 등록된 LLM provider 목록(priority 오름차순)."
    )
    updated_at: KstDatetime = Field(
        description="마지막 수정 시각 (KST, `yyyy-MM-ddTHH:mm:ss` 형식, 오프셋·마이크로초 없음)"
    )
