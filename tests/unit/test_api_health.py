from fastapi.testclient import TestClient

from app.api import routes_health
from app.api.main import app


def test_api_import_is_side_effect_free():
    assert app.title == "Questock"


def test_get_health_ok_response_contract():
    response = TestClient(app).get("/health")
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["mode"] == "fixture_readiness"
    assert body["live_connectivity_checked"] is False
    assert body["phase_slice"]["financial_document_count"] == 4


def test_get_health_degraded_and_error_map_to_503(monkeypatch):
    async def degraded():
        return {"status": "degraded", "mode": "fixture_readiness", "live_connectivity_checked": False}

    async def error():
        return {"status": "error", "mode": "fixture_readiness", "live_connectivity_checked": False}

    monkeypatch.setattr(routes_health, "build_health_payload", degraded)
    degraded_response = TestClient(app).get("/health")
    monkeypatch.setattr(routes_health, "build_health_payload", error)
    error_response = TestClient(app).get("/health")

    assert degraded_response.status_code == 503
    assert degraded_response.json()["status"] == "degraded"
    assert error_response.status_code == 503
    assert error_response.json()["status"] == "error"


def test_unexpected_builder_failure_is_sanitized_503(monkeypatch):
    async def raising():
        raise RuntimeError("raw secret")

    monkeypatch.setattr(routes_health, "build_health_payload", raising)

    response = TestClient(app).get("/health")
    body = response.json()

    assert response.status_code == 503
    assert body["status"] == "error"
    assert "raw secret" not in response.text
