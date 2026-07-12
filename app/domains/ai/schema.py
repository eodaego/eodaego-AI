from typing import Any

from pydantic import BaseModel


class AiChatRequest(BaseModel):
    variables: dict[str, Any] = {}
    user_message: str | None = None


class AiChatResponse(BaseModel):
    content: str
