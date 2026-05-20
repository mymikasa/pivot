from typing import Annotated

from fastapi import APIRouter, Depends

from src.api.deps import get_current_parse_user
from src.infrastructure.security import AuthenticatedUser
from src.rag.generation import chat_with_tools
from src.rag.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    _user: Annotated[AuthenticatedUser, Depends(get_current_parse_user)],
) -> ChatResponse:
    return chat_with_tools(
        message=body.message,
        kb_id=body.kb_id,
        history=[{"role": m.role, "content": m.content} for m in body.history],
        top_k=body.top_k,
    )
