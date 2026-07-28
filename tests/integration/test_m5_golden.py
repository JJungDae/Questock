from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from app.api.schemas import ChatRequest
from app.runtime import RuntimeConfig, build_runtime

GOLDEN_PATH = Path(
    "tests/fixtures/evaluation/m5_time_grounding_cases.json"
)


def _cases() -> list[dict[str, object]]:
    payload = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "m5-time-grounding-golden-v1"
    return payload["cases"]


@pytest.mark.parametrize(
    "case",
    _cases(),
    ids=lambda case: case["case_id"],
)
def test_m5_time_grounding_golden(case: dict[str, object]) -> None:
    service = build_runtime(
        config=RuntimeConfig(
            source_mode="recorded",
            snapshot_id="svc-20260724-1402",
        )
    ).chat_service
    request = ChatRequest(
        message=case["question"],
        session_id=f"golden-{case['case_id']}",
        as_of=case["as_of"],
    )

    response = asyncio.run(service.chat(request))

    assert response.diagnostics_public.query_plan.intent == case[
        "expected_intent"
    ]
    assert response.security is not None
    assert (
        f"{response.security.market}:{response.security.ticker}"
        == case["expected_security_id"]
    )
    assert response.basis_at == request.as_of
    assert all(
        item.published_at is not None
        and item.published_at <= response.basis_at
        for item in response.evidence
    )
    if case["expected_price"] is None:
        assert response.market_snapshot is None
        return
    assert response.market_snapshot is not None
    assert response.market_snapshot.price == case["expected_price"]
    assert (
        response.market_snapshot.observed_at.isoformat()
        == case["expected_observed_at"]
    )
    assert (
        response.market_snapshot.market_status
        == case["expected_market_status"]
    )
    assert response.market_snapshot.observed_at <= response.basis_at
