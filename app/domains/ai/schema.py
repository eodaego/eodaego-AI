from typing import Any

from pydantic import BaseModel, Field


class AiChatRequest(BaseModel):
    variables: dict[str, Any] = Field(
        default={},
        description=(
            "활성 프롬프트 템플릿의 `$변수명` 자리표시자에 치환할 값 목록. "
            "`string.Template.safe_substitute`로 치환되므로, 여기 없는 변수명은 무시되고 "
            "`$변수명` 문자열이 그대로 남는다(에러가 발생하지 않음)."
        ),
        examples=[{"place_name": "어린이대공원", "weather": "맑음"}],
    )
    user_message: str | None = Field(
        default=None,
        description=(
            "활성 프롬프트의 system 메시지에 이어 전달할 사용자 메시지. "
            "생략(null)하면 system 메시지만 SUH-AIder에 전달된다."
        ),
        examples=["오늘 날씨에 어울리는 코스를 추천해줘"],
    )


class AiChatResponse(BaseModel):
    content: str = Field(description="SUH-AIder가 생성한 응답 텍스트 원문")
