from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from app.api.schemas import ChatRequest
from app.services.chat_service import ChatService
from app.services.observability import RequestObservation
from app.services.response_cache import ResponseCache

NOW = datetime(2026, 7, 27, tzinfo=UTC)


class Clock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


def _response():
    return asyncio.run(
        ChatService(utc_now=lambda: NOW).chat(
            ChatRequest(
                message="삼성전자 최근 뉴스",
                session_id="cache-fixture",
            )
        )
    )


def _observation() -> RequestObservation:
    return RequestObservation(
        request_id="cache-observation",
        intent="recent_issue",
        security_id="KRX:005930",
        provider_statuses=(("news", "provider_unavailable"),),
        evidence_count=0,
        retrieval_strategy="lexical-bm25-m2-03-v1",
        evidence_decision="provider_failed",
        total_latency_ms=1,
        llm_call_count=0,
        fallback_used=True,
    )


def _put(
    cache: ResponseCache,
    *,
    session_id: str = "session-a",
    question: str = "삼성전자 최근 뉴스",
    revision: int = 1,
    checkpoint_id: str = "legacy",
) -> None:
    cache.put(
        session_id=session_id,
        snapshot_id="svc-20260724-1402",
        question=question,
        resulting_revision=revision,
        model_fingerprint="a" * 64,
        response=_response(),
        observation=_observation(),
        checkpoint_id=checkpoint_id,
    )


def _get(
    cache: ResponseCache,
    *,
    session_id: str = "session-a",
    question: str = "삼성전자 최근 뉴스",
    revision: int = 1,
    checkpoint_id: str = "legacy",
):
    return cache.get(
        session_id=session_id,
        snapshot_id="svc-20260724-1402",
        question=question,
        revision=revision,
        model_fingerprint="a" * 64,
        checkpoint_id=checkpoint_id,
    )


def test_disabled_cache_is_noop() -> None:
    cache = ResponseCache()

    _put(cache)

    assert _get(cache) is None
    assert cache.size == 0


def test_resulting_revision_lookup_and_deep_copy() -> None:
    cache = ResponseCache(enabled=True)

    _put(cache, revision=1)

    assert _get(cache, revision=0) is None
    first = _get(cache, revision=1)
    assert first is not None
    first.response.warnings.append("caller-mutation")
    second = _get(cache, revision=1)
    assert second is not None
    assert "caller-mutation" not in second.response.warnings
    assert second.observation.request_id == "cache-observation"


def test_question_normalization_hits_but_session_isolation_is_exact() -> None:
    cache = ResponseCache(enabled=True)
    _put(cache, question="삼성전자   최근 뉴스")

    assert _get(cache, question="삼성전자 최근 뉴스") is not None
    assert _get(cache, session_id="session-b") is None


def test_checkpoint_identity_prevents_earlier_context_cache_hit() -> None:
    cache = ResponseCache(enabled=True)
    _put(cache, checkpoint_id="20260727T1400KST")

    assert (
        _get(cache, checkpoint_id="20260727T1400KST")
        is not None
    )
    assert (
        _get(cache, checkpoint_id="20260727T1000KST")
        is None
    )


def test_ttl_boundary_never_returns_stale_value() -> None:
    clock = Clock()
    cache = ResponseCache(
        enabled=True,
        ttl_seconds=90,
        monotonic=clock,
    )
    _put(cache)

    clock.advance(89.999)
    assert _get(cache) is not None
    clock.advance(0.001)
    assert _get(cache) is None


def test_per_session_and_global_lru_bounds() -> None:
    clock = Clock()
    cache = ResponseCache(
        enabled=True,
        max_entries=5,
        max_entries_per_session=4,
        monotonic=clock,
    )
    for revision in range(1, 6):
        _put(
            cache,
            question=f"삼성전자 질문 {revision}",
            revision=revision,
        )
        clock.advance(1)

    assert cache.size == 4
    assert _get(
        cache,
        question="삼성전자 질문 1",
        revision=1,
    ) is None

    _put(cache, session_id="session-b", question="질문 b", revision=1)
    clock.advance(1)
    _put(cache, session_id="session-c", question="질문 c", revision=1)
    assert cache.size == 5
