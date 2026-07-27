from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.api.routes_chat import get_chat_service
from app.runtime import get_runtime_state
from app.services.chat_service import ChatService, ChatServiceError


@pytest.fixture(autouse=True)
def _clear_runtime_cache(monkeypatch):
    monkeypatch.setenv("QUESTOCK_SOURCE_MODE", "unconfigured")
    get_runtime_state.cache_clear()
    yield
    get_runtime_state.cache_clear()


def test_default_chat_endpoint_returns_explicit_unconfigured_response() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/chat",
            json={
                "message": "삼성전자 최근 뉴스",
                "session_id": "api-unit",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "provider_failed"
    assert payload["diagnostics_public"]["data_mode"] == "unconfigured"
    assert "session_id" not in payload


def test_request_validation_is_sanitized_and_rejects_unknown_fields() -> None:
    sentinel = "-".join(("API", "SECRET", "SENTINEL"))
    with TestClient(app) as client:
        response = client.post(
            "/api/chat",
            json={
                "message": " ",
                "session_id": sentinel,
                "credential": sentinel,
            },
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "request validation failed"}
    assert sentinel not in response.text


def test_missing_required_field_is_sanitized() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/chat",
            json={"message": "삼성전자 최근 뉴스"},
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "request validation failed"}


def test_service_error_maps_to_stable_503() -> None:
    class FailingService(ChatService):
        async def chat(  # type: ignore[no-untyped-def]
            self,
            request,
            *,
            client_key=None,
        ):
            raise ChatServiceError("sentinel raw failure")

    app.dependency_overrides[get_chat_service] = lambda: FailingService()
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/chat",
                json={
                    "message": "삼성전자 최근 뉴스",
                    "session_id": "api-unit",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"detail": "chat service unavailable"}
    assert "sentinel" not in response.text


def test_client_key_header_is_internal_and_passed_outside_public_body() -> None:
    key = "a" * 64

    class CapturingService(ChatService):
        def __init__(self) -> None:
            super().__init__()
            self.client_keys: list[str | None] = []

        async def chat(  # type: ignore[override]
            self,
            request,
            *,
            client_key=None,
        ):
            self.client_keys.append(client_key)
            return await super().chat(request)

    service = CapturingService()
    app.dependency_overrides[get_chat_service] = lambda: service
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/chat",
                headers={"X-Questock-Client-Key": key},
                json={
                    "message": "삼성전자 최근 뉴스",
                    "session_id": "api-client-key",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert service.client_keys == [key]
    assert key not in response.text
    assert "client_key" not in response.text
