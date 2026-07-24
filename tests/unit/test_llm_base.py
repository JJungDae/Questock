from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from app.llm.base import (
    LLMClient,
    LLMMessage,
    LLMRequest,
    LLMResult,
    LLMStatus,
    LLMValidationError,
    create_llm_result,
)


def test_llm_status_values_are_exact_and_separate() -> None:
    assert [item.value for item in LLMStatus] == [
        "ok",
        "timeout",
        "rate_limited",
        "authentication_error",
        "provider_unavailable",
        "invalid_response",
        "content_blocked",
    ]


@pytest.mark.parametrize("status", list(LLMStatus))
def test_every_llm_result_json_round_trip(status: LLMStatus) -> None:
    result = create_llm_result(
        status=status,
        content='{"claims":[]}' if status == LLMStatus.OK else None,
        model="gemini/gemini-2.5-flash",
        provider="gemini",
        usage={"total_tokens": 3} if status == LLMStatus.OK else {},
        finish_reason="stop" if status == LLMStatus.OK else None,
        latency_ms=1.25,
    )

    restored = LLMResult.model_validate_json(result.model_dump_json())

    assert restored == result
    assert restored is not result


def test_result_factory_deep_copies_usage() -> None:
    usage = {"prompt_tokens": 7}
    result = create_llm_result(
        status=LLMStatus.OK,
        content="{}",
        model="gemini/gemini-2.5-flash",
        provider="gemini",
        usage=usage,
        latency_ms=0,
    )

    usage["prompt_tokens"] = 99

    assert result.usage == {"prompt_tokens": 7}


@pytest.mark.parametrize("value", [True, -1, math.nan, math.inf])
def test_invalid_usage_is_rejected(value: object) -> None:
    with pytest.raises(LLMValidationError):
        create_llm_result(
            status=LLMStatus.OK,
            content="{}",
            model="gemini/gemini-2.5-flash",
            provider="gemini",
            usage={"total_tokens": value},  # type: ignore[dict-item]
            latency_ms=0,
        )


def test_status_invariants_reject_missing_or_failed_content() -> None:
    with pytest.raises(LLMValidationError):
        create_llm_result(
            status=LLMStatus.OK,
            model="gemini/gemini-2.5-flash",
            provider="gemini",
            latency_ms=0,
        )
    with pytest.raises(LLMValidationError):
        create_llm_result(
            status=LLMStatus.TIMEOUT,
            content="raw response",
            model="gemini/gemini-2.5-flash",
            provider="gemini",
            latency_ms=0,
        )


def test_request_rejects_unknown_fields_and_blank_messages() -> None:
    with pytest.raises(ValidationError):
        LLMMessage(role="user", content=" ")
    with pytest.raises(ValidationError):
        LLMRequest(
            messages=(LLMMessage(role="user", content="question"),),
            response_schema={"type": "object"},
            raw_prompt="forbidden",
        )


def test_request_json_round_trip_is_isolated() -> None:
    request = LLMRequest(
        messages=(LLMMessage(role="user", content="question"),),
        response_schema={"type": "object", "properties": {}},
    )

    restored = LLMRequest.model_validate_json(request.model_dump_json())

    assert restored == request
    assert restored is not request
    assert restored.response_schema is not request.response_schema


def test_runtime_protocol_accepts_structural_client() -> None:
    class FakeClient:
        async def complete(
            self,
            request: LLMRequest,
            *,
            timeout_seconds: float,
        ) -> LLMResult:
            raise AssertionError

    assert isinstance(FakeClient(), LLMClient)
