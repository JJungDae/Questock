from __future__ import annotations

import io
import json
import logging

import pytest

from app.services.observability import (
    InMemoryObservationSink,
    JsonLogObservationSink,
    ObservationValidationError,
    RequestObservation,
    fallback_used_for_generation_mode,
)


def _observation(**updates: object) -> RequestObservation:
    values = {
        "request_id": "request-001",
        "intent": "recent_issue",
        "security_id": "KRX:005930",
        "provider_statuses": (
            ("news", "ok"),
            ("disclosure", "timeout"),
        ),
        "evidence_count": 2,
        "retrieval_strategy": "lexical-bm25-m2-03-v1",
        "evidence_decision": "partial",
        "total_latency_ms": 12.5,
        "llm_call_count": 1,
        "fallback_used": False,
    }
    values.update(updates)
    return RequestObservation(**values)  # type: ignore[arg-type]


def test_json_sink_emits_exact_stable_allowlisted_payload() -> None:
    output = io.StringIO()
    logger = logging.Logger("questock.observability.unit")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(output)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    sink = JsonLogObservationSink(logger)

    sink.emit(_observation())

    rendered = output.getvalue().strip()
    payload = json.loads(rendered)
    assert list(payload) == sorted(payload)
    assert payload == {
        "evidence_count": 2,
        "evidence_decision": "partial",
        "fallback_used": False,
        "intent": "recent_issue",
        "llm_call_count": 1,
        "provider_statuses": {
            "disclosure": "timeout",
            "news": "ok",
        },
        "request_id": "request-001",
        "retrieval_strategy": "lexical-bm25-m2-03-v1",
        "security_id": "KRX:005930",
        "total_latency_ms": 12.5,
    }
    assert "\n" not in rendered


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("llm", False),
        ("fixed_template", True),
        ("blocked", False),
        ("not_called", False),
    ],
)
def test_fallback_used_contract(mode: str, expected: bool) -> None:
    assert fallback_used_for_generation_mode(mode) is expected


def test_fallback_used_rejects_unknown_generation_mode() -> None:
    with pytest.raises(
        ObservationValidationError,
        match="generation mode is invalid",
    ):
        fallback_used_for_generation_mode("other")


def test_in_memory_sink_preserves_immutable_observations() -> None:
    sink = InMemoryObservationSink()
    observation = _observation()

    sink.emit(observation)

    assert sink.observations == (observation,)
    assert sink.observations is not sink.observations


@pytest.mark.parametrize(
    "updates",
    [
        {"request_id": "bad request"},
        {"provider_statuses": (("news", "unknown"),)},
        {"provider_statuses": (("news", "ok"), ("news", "no_data"))},
        {"evidence_count": True},
        {"retrieval_strategy": "C:\\private\\strategy"},
        {"evidence_decision": "unknown"},
        {"total_latency_ms": float("nan")},
        {"llm_call_count": 2},
        {"fallback_used": 1},
    ],
)
def test_observation_rejects_malformed_or_content_bearing_fields(
    updates: dict[str, object],
) -> None:
    with pytest.raises(ObservationValidationError):
        _observation(**updates)
