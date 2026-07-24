from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.main import app
from app.api.routes_chat import get_chat_service
from app.services.chat_service import ChatService, ChatServiceError


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
        async def chat(self, request):  # type: ignore[no-untyped-def]
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

