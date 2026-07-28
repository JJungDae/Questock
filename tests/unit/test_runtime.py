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


def test_llm_and_protection_switch_defaults_and_exact_values() -> None:
    defaults = load_runtime_config({})
    enabled = load_runtime_config(
        {
            "QUESTOCK_SOURCE_MODE": "recorded",
            "QUESTOCK_LLM_MODE": "gemini",
            "QUESTOCK_REQUEST_PROTECTION_ENABLED": "true",
            "QUESTOCK_RESPONSE_CACHE_ENABLED": "true",
        }
    )

    assert defaults.llm_mode == "disabled"
    assert defaults.request_protection_enabled is False
    assert defaults.response_cache_enabled is False
    assert defaults.hybrid_router_enabled is False
    assert enabled.llm_mode == "gemini"
    assert enabled.request_protection_enabled is True
    assert enabled.response_cache_enabled is True
    assert enabled.hybrid_router_enabled is False


def test_hybrid_router_switch_requires_gemini_mode() -> None:
    enabled = load_runtime_config(
        {
            "QUESTOCK_SOURCE_MODE": "recorded",
            "QUESTOCK_LLM_MODE": "gemini",
            "QUESTOCK_HYBRID_ROUTER_ENABLED": "true",
        }
    )

    assert enabled.hybrid_router_enabled is True

    with pytest.raises(RuntimeConfigurationError):
        build_runtime(
            config=RuntimeConfig(
                source_mode="recorded",
                hybrid_router_enabled=True,
            )
        )


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("QUESTOCK_LLM_MODE", "automatic"),
        ("QUESTOCK_REQUEST_PROTECTION_ENABLED", "1"),
        ("QUESTOCK_RESPONSE_CACHE_ENABLED", "yes"),
        ("QUESTOCK_HYBRID_ROUTER_ENABLED", "enabled"),
    ],
)
def test_invalid_runtime_switch_is_sanitized(
    name: str,
    value: str,
) -> None:
    with pytest.raises(RuntimeConfigurationError) as exc_info:
        load_runtime_config({name: value})

    assert value not in str(exc_info.value)


def test_gemini_runtime_wires_llm_protection_and_cache_without_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeLiteLLMClient:
        def __init__(self, config):
            self.config = config

        async def complete(self, request, *, timeout_seconds):  # pragma: no cover
            raise AssertionError("unit runtime wiring must not call Gemini")

    monkeypatch.delenv("LLM_THINKING_BUDGET", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "unit-configured-key")
    monkeypatch.setattr(runtime, "LiteLLMClient", FakeLiteLLMClient)

    state = build_runtime(
        config=RuntimeConfig(
            source_mode="recorded",
            llm_mode="gemini",
            request_protection_enabled=True,
            response_cache_enabled=True,
            hybrid_router_enabled=True,
        )
    )

    assert state.chat_service._live_llm_enabled is True  # noqa: SLF001
    assert state.chat_service._request_protector.enabled is True  # noqa: SLF001
    assert state.chat_service._response_cache.enabled is True  # noqa: SLF001
    assert state.chat_service._intent_router.enabled is True  # noqa: SLF001
    assert state.chat_service._model_fingerprint != "disabled"  # noqa: SLF001


def test_gemini_runtime_missing_credential_is_sanitized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LLM_THINKING_BUDGET", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(RuntimeConfigurationError) as exc_info:
        build_runtime(
            config=RuntimeConfig(
                source_mode="recorded",
                llm_mode="gemini",
            )
        )

    assert "GEMINI_API_KEY" not in str(exc_info.value)


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
