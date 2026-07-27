from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException

from app.api.schemas import ChatRequest, ChatResponse
from app.runtime import get_chat_service as get_runtime_chat_service
from app.services.chat_service import ChatService, ChatServiceError
from app.services.request_protection import CLIENT_KEY_HEADER

chat_router = APIRouter()


def get_chat_service() -> ChatService:
    return get_runtime_chat_service()


@chat_router.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    service: ChatService = Depends(get_chat_service),
    client_key: Annotated[
        str | None,
        Header(alias=CLIENT_KEY_HEADER),
    ] = None,
) -> ChatResponse:
    try:
        return await service.chat(request, client_key=client_key)
    except ChatServiceError:
        raise HTTPException(
            status_code=503,
            detail="chat service unavailable",
        ) from None


__all__ = ["chat_router", "get_chat_service"]
