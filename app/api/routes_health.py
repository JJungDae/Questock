from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.health import build_error_payload, build_health_payload

health_router = APIRouter()


def _http_status(payload: dict[str, Any]) -> int:
    return 200 if payload.get("status") == "ok" else 503


@health_router.get("/health")
async def health() -> JSONResponse:
    try:
        payload = await build_health_payload()
    except Exception:
        payload = build_error_payload({"status": "error"})
    return JSONResponse(content=payload, status_code=_http_status(payload))


__all__ = ["health_router"]
