from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.api.schemas import ChatRequest
from app.runtime import (
    RuntimeConfig,
    RuntimeConfigurationError,
    build_runtime,
    get_runtime_state,
    load_runtime_config,
)
from app.services.service_snapshot import SERVICE_SNAPSHOT_ID
from app.services.service_snapshot_gateway import (
    RecordedServiceSnapshotGateway,
)


@pytest.fixture(autouse=True)
def _clear_runtime_cache():
    get_runtime_state.cache_clear()
    yield
    get_runtime_state.cache_clear()


def test_snapshot_runtime_config_is_explicit_and_sanitized() -> None:
    config = load_runtime_config(
        {
            "QUESTOCK_SOURCE_MODE": "recorded",
            "QUESTOCK_SNAPSHOT_ID": SERVICE_SNAPSHOT_ID,
        }
    )

    assert config == RuntimeConfig(
        source_mode="recorded",
        snapshot_id=SERVICE_SNAPSHOT_ID,
    )
    sentinel = "C:\\private\\snapshot"
    with pytest.raises(RuntimeConfigurationError) as exc_info:
        load_runtime_config(
            {
                "QUESTOCK_SOURCE_MODE": "recorded",
                "QUESTOCK_SNAPSHOT_ID": sentinel,
            }
        )
    assert sentinel not in str(exc_info.value)


def test_snapshot_runtime_loads_once_and_uses_fixed_basis(monkeypatch) -> None:
    calls = 0

    from app.services.service_snapshot import load_service_snapshot

    def counted_loader():
        nonlocal calls
        calls += 1
        return load_service_snapshot()

    monkeypatch.setenv("QUESTOCK_SOURCE_MODE", "recorded")
    monkeypatch.setenv("QUESTOCK_SNAPSHOT_ID", SERVICE_SNAPSHOT_ID)
    monkeypatch.setattr("app.runtime.load_service_snapshot", counted_loader)

    first = get_runtime_state()
    second = get_runtime_state()

    assert first is second
    assert calls == 1
    assert first.corpus is not None
    assert first.corpus.basis_at.isoformat() == "2026-07-24T05:02:00+00:00"
    assert isinstance(
        first.chat_service._source_gateway,  # noqa: SLF001
        RecordedServiceSnapshotGateway,
    )


def test_snapshot_health_reports_exact_source_counts(monkeypatch) -> None:
    monkeypatch.setenv("QUESTOCK_SOURCE_MODE", "recorded")
    monkeypatch.setenv("QUESTOCK_SNAPSHOT_ID", SERVICE_SNAPSHOT_ID)

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": "service-snapshot-v1",
        "mode": "recorded",
        "data_mode": "recorded",
        "live_connectivity_checked": False,
        "basis_at": "2026-07-24T05:02:00Z",
        "sources": {
            "news": 15,
            "disclosure": 3,
            "research_report": 36,
        },
        "snapshot_id": SERVICE_SNAPSHOT_ID,
        "phase_slice": {
            "status": "recorded",
            "scope": "service_snapshot",
            "document_count": 54,
            "report_count": 3,
        },
    }


@pytest.mark.parametrize(
    ("message", "source_type"),
    [
        ("삼성전자 최근 이슈 요약", "news"),
        ("SK하이닉스 최근 이슈 요약", "news"),
        ("현대차 최근 이슈 요약", "news"),
        ("삼성전자 최근 공시 핵심", "disclosure"),
        ("SK하이닉스 최근 공시 핵심", "disclosure"),
        ("현대차 최근 공시 핵심", "disclosure"),
        ("삼성전자 리포트 요약", "research_report"),
        ("SK하이닉스 리포트 요약", "research_report"),
        ("현대차 리포트 요약", "research_report"),
    ],
)
def test_snapshot_chat_uses_only_requested_company_and_source(
    message: str,
    source_type: str,
) -> None:
    state = build_runtime(
        config=RuntimeConfig(
            source_mode="recorded",
            snapshot_id=SERVICE_SNAPSHOT_ID,
        )
    )
    response = asyncio.run(
        state.chat_service.chat(
            ChatRequest(message=message, session_id=f"snapshot-{source_type}")
        )
    )

    assert response.status in {"complete", "partial"}
    assert response.basis_date.isoformat() == "2026-07-24"
    assert response.security is not None
    security_id = f"{response.security.market}:{response.security.ticker}"
    assert response.evidence
    assert all(item.source_type == source_type for item in response.evidence)
    assert all(
        security_id in item.subject_security_ids
        or security_id in item.mentioned_security_ids
        for item in response.evidence
    )
    assert response.diagnostics_public.data_mode == "recorded"
    assert response.diagnostics_public.live_connectivity_checked is False
    if source_type == "disclosure":
        assert response.status == "partial"
        assert "insufficient_disclosure_coverage" in response.warnings
    if source_type == "research_report":
        assert response.diagnostics_public.generation.mode == "fixed_template"
