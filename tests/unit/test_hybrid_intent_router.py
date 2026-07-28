from __future__ import annotations

import asyncio
import json
from datetime import date

import pytest

from app.core.resolver import SecurityResolver
from app.llm.base import (
    LLMRequest,
    LLMResult,
    LLMStatus,
    create_llm_result,
)
from app.services.hybrid_intent_router import HybridIntentRouter
from app.services.hybrid_intent_router import HybridRoutingResult
from app.services.planning_observation import build_observed_query_plan

BASIS_DATE = date(2026, 7, 27)


class FakeClassifier:
    def __init__(
        self,
        *,
        content: str = '{"intent":"multi_source_summary"}',
        status: LLMStatus = LLMStatus.OK,
        delay: float = 0,
    ) -> None:
        self.content = content
        self.status = status
        self.delay = delay
        self.calls = 0
        self.requests: list[LLMRequest] = []

    async def complete(
        self,
        request: LLMRequest,
        *,
        timeout_seconds: float,
    ) -> LLMResult:
        self.calls += 1
        self.requests.append(request.model_copy(deep=True))
        if self.delay:
            await asyncio.sleep(self.delay)
        return create_llm_result(
            status=self.status,
            content=(
                self.content
                if self.status == LLMStatus.OK
                else None
            ),
            model="gemini/gemini-3.5-flash",
            provider="gemini",
            latency_ms=1,
        )


def _observed(query: str):
    return build_observed_query_plan(
        query,
        basis_date=BASIS_DATE,
        resolver=SecurityResolver(),
    )


def test_ambiguous_price_situation_accepts_supported_llm_intent() -> None:
    query = "삼성전자 주가 상황 어때?"
    deterministic = _observed(query)
    client = FakeClassifier()
    router = HybridIntentRouter(client, enabled=True)

    result = asyncio.run(
        router.classify(
            query,
            deterministic,
            basis_date=BASIS_DATE,
            timeout_seconds=5,
        )
    )

    assert deterministic.plan.intent == "multi_source_summary"
    assert result.observed.plan.intent == "multi_source_summary"
    assert result.observed.security_id == deterministic.security_id
    assert result.observed.plan.security == deterministic.plan.security
    assert result.mode == "hybrid_llm"
    assert result.classifier_status == "accepted"
    assert result.classifier_call_count == 1
    assert client.calls == 1
    payload = json.loads(client.requests[0].messages[1].content)
    assert payload == {
        "deterministic_intent": "multi_source_summary",
        "user_text": query,
    }


def test_conflicting_recent_risk_cues_can_select_recent_issue() -> None:
    query = "삼성전자 최근 악재 알려줘"
    deterministic = _observed(query)
    client = FakeClassifier(
        content='{"intent":"recent_issue"}',
    )
    router = HybridIntentRouter(client, enabled=True)

    result = asyncio.run(
        router.classify(
            query,
            deterministic,
            basis_date=BASIS_DATE,
            timeout_seconds=5,
        )
    )

    assert deterministic.plan.intent == "risk_factors"
    assert result.observed.plan.intent == "recent_issue"
    assert result.observed.plan.required_sources == ["news"]


@pytest.mark.parametrize(
    "query",
    [
        "삼성전자 주가 얼마야?",
        "삼성전자 최근 뉴스 알려줘",
        "왜 주가변동성이 위험요인이야?",
        "공시가 뭐야?",
        "삼성전자 지금 사야 돼?",
        "날씨 알려줘",
    ],
)
def test_unambiguous_or_safety_queries_use_zero_classifier_calls(
    query: str,
) -> None:
    observed = _observed(query)
    client = FakeClassifier()
    router = HybridIntentRouter(client, enabled=True)

    assert router.should_classify(query, observed) is False
    result = asyncio.run(
        router.classify(
            query,
            observed,
            basis_date=BASIS_DATE,
            timeout_seconds=5,
        )
    )

    assert result.observed == observed
    assert result.mode == "deterministic"
    assert result.classifier_call_count == 0
    assert client.calls == 0


@pytest.mark.parametrize(
    "content",
    [
        "not-json",
        '```json\n{"intent":"risk_factors"}\n```',
        '{"intent":"unsupported"}',
        '{"intent":"risk_factors","reason":"extra"}',
        '["risk_factors"]',
    ],
)
def test_malformed_classifier_output_falls_back_to_rule_plan(
    content: str,
) -> None:
    query = "삼성전자 주가 상황 어때?"
    deterministic = _observed(query)
    client = FakeClassifier(content=content)
    router = HybridIntentRouter(client, enabled=True)

    result = asyncio.run(
        router.classify(
            query,
            deterministic,
            basis_date=BASIS_DATE,
            timeout_seconds=5,
        )
    )

    assert result.observed == deterministic
    assert result.mode == "hybrid_fallback"
    assert result.classifier_status == "invalid_response"
    assert result.classifier_call_count == 1


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (LLMStatus.TIMEOUT, "timeout"),
        (LLMStatus.RATE_LIMITED, "rate_limited"),
        (LLMStatus.AUTHENTICATION_ERROR, "authentication_error"),
        (LLMStatus.PROVIDER_UNAVAILABLE, "provider_unavailable"),
        (LLMStatus.INVALID_RESPONSE, "invalid_response"),
        (LLMStatus.CONTENT_BLOCKED, "content_blocked"),
    ],
)
def test_classifier_failure_statuses_preserve_rule_plan(
    status: LLMStatus,
    expected: str,
) -> None:
    query = "삼성전자 주가 상황 어때?"
    deterministic = _observed(query)
    client = FakeClassifier(status=status)
    router = HybridIntentRouter(client, enabled=True)

    result = asyncio.run(
        router.classify(
            query,
            deterministic,
            basis_date=BASIS_DATE,
            timeout_seconds=5,
        )
    )

    assert result.observed == deterministic
    assert result.mode == "hybrid_fallback"
    assert result.classifier_status == expected
    assert result.classifier_call_count == 1


def test_classifier_wall_timeout_preserves_rule_plan() -> None:
    query = "삼성전자 주가 상황 어때?"
    deterministic = _observed(query)
    client = FakeClassifier(delay=0.05)
    router = HybridIntentRouter(
        client,
        enabled=True,
        timeout_seconds=0.01,
    )

    result = asyncio.run(
        router.classify(
            query,
            deterministic,
            basis_date=BASIS_DATE,
            timeout_seconds=5,
        )
    )

    assert result.observed == deterministic
    assert result.mode == "hybrid_fallback"
    assert result.classifier_status == "timeout"
    assert result.classifier_call_count == 1


def test_price_move_reclassification_keeps_basis_date_contract() -> None:
    query = "삼성전자 주가 어때, 왜 올랐어?"
    deterministic = _observed(query)
    client = FakeClassifier(
        content='{"intent":"price_move"}',
    )
    router = HybridIntentRouter(client, enabled=True)

    result = asyncio.run(
        router.classify(
            query,
            deterministic,
            basis_date=BASIS_DATE,
            timeout_seconds=5,
        )
    )

    assert result.observed.plan.intent == "price_move"
    assert result.observed.plan.date_range is not None
    assert result.observed.plan.date_range.start == BASIS_DATE
    assert result.observed.plan.date_range.end == BASIS_DATE


@pytest.mark.parametrize(
    ("status", "call_count"),
    [
        ("accepted", 1),
        ("not_called", 0),
        ("timeout", 0),
    ],
)
def test_hybrid_fallback_result_rejects_inconsistent_state(
    status: str,
    call_count: int,
) -> None:
    with pytest.raises(ValueError):
        HybridRoutingResult(
            observed=_observed("삼성전자 주가 상황 어때?"),
            mode="hybrid_fallback",
            classifier_status=status,  # type: ignore[arg-type]
            classifier_call_count=call_count,
        )
