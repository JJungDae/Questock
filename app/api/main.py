from __future__ import annotations

from fastapi import FastAPI

from app.api.routes_health import health_router

app = FastAPI(title="Questock", version="m1-08")
app.include_router(health_router)

__all__ = ["app"]
