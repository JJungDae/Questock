from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes_chat import chat_router
from app.api.routes_health import health_router
from app.runtime import get_runtime_state


@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    get_runtime_state()
    yield


app = FastAPI(title="Questock", version="m3-01", lifespan=_lifespan)
app.include_router(health_router)
app.include_router(chat_router)


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": "request validation failed"},
    )

__all__ = ["app"]
