from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.health import build_error_payload, build_health_payload

health_router = APIRouter()
_SOURCE_MODE_ENV = "QUESTOCK_SOURCE_MODE"
_UNCONFIGURED_MODE = "unconfigured"


def _http_status(payload: dict[str, Any]) -> int:
    return 200 if payload.get("status") == "ok" else 503


def _unconfigured_health_payload() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": "b9-foundation",
        "mode": _UNCONFIGURED_MODE,
        "data_mode": _UNCONFIGURED_MODE,
        "live_connectivity_checked": False,
        "sources": {},
        "phase_slice": {
            "status": _UNCONFIGURED_MODE,
            "scope": "recorded_mvp",
        },
    }


@health_router.get("/health")
async def health() -> JSONResponse:
    source_mode = (os.getenv(_SOURCE_MODE_ENV) or "").strip().casefold()
    if source_mode == _UNCONFIGURED_MODE:
        payload = _unconfigured_health_payload()
    else:
        try:
            payload = await build_health_payload()
        except Exception:
            payload = build_error_payload({"status": "error"})
    return JSONResponse(content=payload, status_code=_http_status(payload))


__all__ = ["health_router"]
