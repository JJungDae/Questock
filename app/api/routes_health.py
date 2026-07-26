from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.runtime import (
    RuntimeConfigurationError,
    get_runtime_health_payload,
)

health_router = APIRouter()


def _http_status(payload: dict[str, Any]) -> int:
    return 200 if payload.get("status") == "ok" else 503


def _error_health_payload() -> dict[str, Any]:
    return {
        "status": "error",
        "version": "b9-recorded-v1",
        "mode": "unconfigured",
        "data_mode": "unconfigured",
        "live_connectivity_checked": False,
        "sources": {},
        "phase_slice": {
            "status": "error",
            "scope": "recorded_mvp",
        },
    }


@health_router.get("/health")
async def health() -> JSONResponse:
    try:
        payload = get_runtime_health_payload()
    except (RuntimeConfigurationError, Exception):
        payload = _error_health_payload()
    return JSONResponse(content=payload, status_code=_http_status(payload))


__all__ = ["health_router"]
