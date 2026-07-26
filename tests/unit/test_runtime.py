from __future__ import annotations

import asyncio
from datetime import date

import pytest

from app.api.schemas import ChatRequest
from app import runtime
from app.runtime import (
    RuntimeConfig,
    RuntimeConfigurationError,
    build_runtime,
    get_runtime_state,
    load_runtime_config,
)
from app.services.demo_source_gateway import load_demo_corpus
from app.services.source_gateway import ExplicitUnconfiguredSourceGateway


@pytest.fixture(autouse=True)
def _clear_runtime_cache():
    get_runtime_state.cache_clear()
    yield
    get_runtime_state.cache_clear()


def test_missing_mode_selects_explicit_unconfigured_runtime() -> None:
    config = load_runtime_config({})
    state = build_runtime(config=config)

    assert config == RuntimeConfig(source_mode="unconfigured")
    assert state.corpus is None
    assert isinstance(
        state.chat_service._source_gateway,  # noqa: SLF001
        ExplicitUnconfiguredSourceGateway,
    )


def test_invalid_mode_failure_is_sanitized() -> None:
    sentinel = "live-sentinel-private"

    with pytest.raises(RuntimeConfigurationError) as exc_info:
        load_runtime_config({"QUESTOCK_SOURCE_MODE": sentinel})

    assert sentinel not in str(exc_info.value)


def test_recorded_runtime_uses_manifest_basis_for_chat() -> None:
    state = build_runtime(config=RuntimeConfig(source_mode="recorded"))

    response = asyncio.run(
        state.chat_service.chat(
            ChatRequest(
                message="삼성전자 최근 이슈 요약",
                session_id="runtime-recorded",
            )
        )
    )

    assert state.corpus is not None
    assert response.status == "complete"
    assert response.basis_date == date(2026, 7, 26)
    assert response.diagnostics_public.data_mode == "recorded"
    assert response.diagnostics_public.live_connectivity_checked is False
    assert response.diagnostics_public.sources[0].provider_status == "ok"
    assert response.evidence


def test_recorded_runtime_preserves_mode_for_blocked_response() -> None:
    state = build_runtime(config=RuntimeConfig(source_mode="recorded"))

    response = asyncio.run(
        state.chat_service.chat(
            ChatRequest(
                message="삼성전자 지금 매수해야 해?",
                session_id="runtime-recorded-blocked",
            )
        )
    )

    assert response.status == "blocked"
    assert response.evidence == []
    assert response.diagnostics_public.data_mode == "recorded"
    assert response.diagnostics_public.live_connectivity_checked is False


def test_runtime_singleton_loads_corpus_once_and_preserves_session(
    monkeypatch,
) -> None:
    calls = 0

    def counted_loader():
        nonlocal calls
        calls += 1
        return load_demo_corpus()

    monkeypatch.setenv("QUESTOCK_SOURCE_MODE", "recorded")
    monkeypatch.setattr(runtime, "load_demo_corpus", counted_loader)

    first = get_runtime_state()
    second = get_runtime_state()
    first_response = asyncio.run(
        first.chat_service.chat(
            ChatRequest(
                message="삼성전자 최근 이슈 요약",
                session_id="anonymous-runtime-session",
            )
        )
    )
    follow_up = asyncio.run(
        second.chat_service.chat(
            ChatRequest(
                message="그럼 위험 요인은?",
                session_id="anonymous-runtime-session",
            )
        )
    )

    assert first is second
    assert first.chat_service is second.chat_service
    assert calls == 1
    assert first_response.security is not None
    assert follow_up.security is not None
    assert follow_up.security.ticker == "005930"
    assert follow_up.diagnostics_public.query_plan.intent == "risk_factors"


def test_runtime_wraps_loader_failure_without_raw_details() -> None:
    sentinel = "C:\\private\\demo-corpus.json"

    def raising_loader():
        raise OSError(sentinel)

    with pytest.raises(RuntimeConfigurationError) as exc_info:
        build_runtime(
            config=RuntimeConfig(source_mode="recorded"),
            corpus_loader=raising_loader,
        )

    assert sentinel not in str(exc_info.value)
    assert "private" not in str(exc_info.value)
