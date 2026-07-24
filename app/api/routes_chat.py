from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas import ChatRequest, ChatResponse
from app.services.chat_service import ChatService, ChatServiceError

chat_router = APIRouter()
_DEFAULT_CHAT_SERVICE = ChatService()


def get_chat_service() -> ChatService:
    return _DEFAULT_CHAT_SERVICE


@chat_router.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    try:
        return await service.chat(request)
    except ChatServiceError:
        raise HTTPException(
            status_code=503,
            detail="chat service unavailable",
        ) from None


__all__ = ["chat_router", "get_chat_service"]
