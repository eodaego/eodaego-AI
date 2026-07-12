from pydantic import BaseModel, ConfigDict, Field

from app.core.kst import KstDatetime

_NAME_DESC = (
    "템플릿 식별용 이름. DB에 유니크 제약이 걸려 있으며, 중복 생성 시 별도 처리 없이 "
    "500 INTERNAL_SERVER_ERROR가 발생한다(사전에 GET /api/v1/prompts로 중복 여부 확인 권장)."
)
_MODEL_DESC = (
    "SUH-AIder에 전달할 모델 식별자 문자열. 이 서버는 값을 검증하지 않으므로, "
    "실제 사용 가능한 값은 SUH-AIder 설정을 따른다."
)
_TEMPLATE_TEXT_DESC = (
    "AI 챗의 system 메시지로 사용될 템플릿 원문. `$변수명`(또는 `${변수명}`) 형태의 "
    "자리표시자를 포함할 수 있으며, POST /api/v1/ai/chat 호출 시 요청의 `variables`로 치환된다 "
    "(치환되지 않은 자리표시자는 문자열 그대로 남는다)."
)
_IS_ACTIVE_CREATE_DESC = (
    "true로 설정(기본값)하면 기존에 활성화돼 있던 다른 모든 프롬프트 템플릿이 자동으로 "
    "is_active=false로 전환된다 — 활성 템플릿은 항상 최대 1개로 유지된다(배타적 활성화). "
    "활성 템플릿이 POST /api/v1/ai/chat에서 사용된다."
)


class PromptTemplateCreate(BaseModel):
    name: str = Field(description=_NAME_DESC, examples=["기본 코스 추천 프롬프트"])
    model: str = Field(description=_MODEL_DESC)
    template_text: str = Field(
        description=_TEMPLATE_TEXT_DESC,
        examples=["오늘 $place_name의 날씨는 $weather 입니다. 이에 어울리는 코스를 추천해주세요."],
    )
    is_active: bool = Field(default=True, description=_IS_ACTIVE_CREATE_DESC)


class PromptTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, description=f"{_NAME_DESC} 생략 시 기존 값 유지.")
    model: str | None = Field(default=None, description=f"{_MODEL_DESC} 생략 시 기존 값 유지.")
    template_text: str | None = Field(
        default=None, description=f"{_TEMPLATE_TEXT_DESC} 생략 시 기존 값 유지."
    )
    is_active: bool | None = Field(
        default=None,
        description=(
            f"{_IS_ACTIVE_CREATE_DESC} 생략 시 기존 값 유지. false로 바꿔 활성 템플릿이 0개가 되면 "
            "POST /api/v1/ai/chat이 503을 반환하게 되므로 주의한다."
        ),
    )


class PromptTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="프롬프트 템플릿 PK")
    name: str = Field(description=_NAME_DESC)
    model: str = Field(description=_MODEL_DESC)
    template_text: str = Field(description=_TEMPLATE_TEXT_DESC)
    is_active: bool = Field(
        description="현재 활성화 여부. 전체 템플릿 중 최대 1개만 true일 수 있다."
    )
    updated_at: KstDatetime = Field(
        description="마지막 수정 시각 (KST, `yyyy-MM-ddTHH:mm:ss` 형식, 오프셋·마이크로초 없음)"
    )
