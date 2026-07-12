from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import verify_internal_api_key
from app.db.session import get_db
from app.domains.ai import service
from app.domains.ai.schema import AiChatRequest, AiChatResponse

router = APIRouter(
    prefix="/api/v1/ai",
    tags=["ai"],
    dependencies=[Depends(verify_internal_api_key)],
)


@router.post("/chat", response_model=AiChatResponse)
def chat(data: AiChatRequest, db: Session = Depends(get_db)) -> AiChatResponse:
    content = service.generate_chat_response(db, data)
    return AiChatResponse(content=content)
