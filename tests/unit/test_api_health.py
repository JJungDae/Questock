import pytest
from fastapi.testclient import TestClient

from app.api import routes_health
from app.api.main import app
from app.runtime import RuntimeConfigurationError, get_runtime_state


@pytest.fixture(autouse=True)
def _clear_runtime_cache():
    get_runtime_state.cache_clear()
    yield
    get_runtime_state.cache_clear()


def test_api_import_is_side_effect_free():
    assert app.title == "Questock"


def test_invalid_mode_fails_startup_with_sanitized_error(monkeypatch):
    sentinel = "recorded-private-sentinel"
    monkeypatch.setenv("QUESTOCK_SOURCE_MODE", sentinel)
    get_runtime_state.cache_clear()

    with pytest.raises(RuntimeConfigurationError) as exc_info:
        with TestClient(app):
            pass

    assert sentinel not in str(exc_info.value)


def test_get_health_defaults_to_unconfigured_runtime_contract(monkeypatch):
    monkeypatch.delenv("QUESTOCK_SOURCE_MODE", raising=False)
    get_runtime_state.cache_clear()
    response = TestClient(app).get("/health")
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["mode"] == "unconfigured"
    assert body["live_connectivity_checked"] is False
    assert body["phase_slice"]["scope"] == "recorded_mvp"


def test_explicit_unconfigured_mode_is_healthy_without_fixture_claims(monkeypatch):
    monkeypatch.setenv("QUESTOCK_SOURCE_MODE", " unconfigured ")
    get_runtime_state.cache_clear()

    response = TestClient(app).get("/health")
    body = response.json()

    assert response.status_code == 200
    assert body == {
        "status": "ok",
        "version": "b9-recorded-v1",
        "mode": "unconfigured",
        "data_mode": "unconfigured",
        "live_connectivity_checked": False,
        "sources": {},
        "phase_slice": {
            "status": "unconfigured",
            "scope": "recorded_mvp",
        },
    }


def test_explicit_recorded_mode_reports_fixed_basis(monkeypatch):
    monkeypatch.setenv("QUESTOCK_SOURCE_MODE", "recorded")
    get_runtime_state.cache_clear()

    response = TestClient(app).get("/health")
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["mode"] == "recorded"
    assert body["basis_at"] == "2026-07-26T00:00:00Z"
    assert body["sources"] == {
        "news": 1,
        "disclosure": 1,
        "research_report": 1,
    }


def test_unexpected_builder_failure_is_sanitized_503(monkeypatch):
    def raising():
        raise RuntimeError("raw secret")

    monkeypatch.setattr(routes_health, "get_runtime_health_payload", raising)

    response = TestClient(app).get("/health")
    body = response.json()

    assert response.status_code == 503
    assert body["status"] == "error"
    assert "raw secret" not in response.text
