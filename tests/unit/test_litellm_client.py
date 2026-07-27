from __future__ import annotations

import asyncio
import os
from typing import Any

import litellm
import pytest

from app.config import LLMConfig
from app.llm.base import LLMMessage, LLMRequest, LLMStatus
from app.llm.litellm_client import LiteLLMClient


def _config(monkeypatch: pytest.MonkeyPatch) -> LLMConfig:
    monkeypatch.delenv("LLM_THINKING_BUDGET", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "-".join(("m3", "fixture", "key")))
    monkeypatch.setenv("LLM_THINKING_LEVEL", "minimal")
    monkeypatch.setenv("LLM_MAX_OUTPUT_TOKENS", "4096")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "15")
    return LLMConfig.from_env(require_credential=True)


def _request() -> LLMRequest:
    return LLMRequest(
        messages=(LLMMessage(role="user", content="Synthetic question"),),
        response_schema={
            "type": "object",
            "properties": {"claims": {"type": "array"}},
            "required": ["claims"],
            "additionalProperties": False,
        },
    )


def _response(*, finish_reason: str = "stop") -> dict[str, Any]:
    return {
        "choices": [
            {
                "message": {"content": '{"claims":[]}'},
                "finish_reason": finish_reason,
            }
        ],
        "usage": {
            "prompt_tokens": 5,
            "completion_tokens": 2,
            "total_tokens": 7,
        },
    }


def test_adapter_maps_exact_options_and_normalizes_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []

    async def completion(**kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs)
        return _response()

    result = asyncio.run(
        LiteLLMClient(
            _config(monkeypatch),
            completion=completion,
            monotonic=iter((1.0, 1.012)).__next__,
        ).complete(_request(), timeout_seconds=4)
    )

    assert result.status == LLMStatus.OK
    assert result.content == '{"claims":[]}'
    assert result.usage == {
        "prompt_tokens": 5,
        "completion_tokens": 2,
        "total_tokens": 7,
    }
    assert result.finish_reason == "stop"
    assert result.latency_ms == 12
    assert len(calls) == 1
    call = calls[0]
    assert call["model"] == "gemini/gemini-3.5-flash"
    assert call["timeout"] == 4
    assert call["max_tokens"] == 4096
    assert call["reasoning_effort"] == "minimal"
    assert "thinking" not in call
    assert "thinking_budget" not in call
    assert "drop_params" not in call
    assert "extra_body" not in call
    assert call["num_retries"] == 0
    assert "response_format" not in call
    assert os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] == "True"
    assert os.environ["LANGSMITH_TRACING"] == "false"
    assert os.environ["LANGCHAIN_TRACING_V2"] == "false"


@pytest.mark.parametrize(
    ("exception", "status"),
    [
        (
            litellm.Timeout("sentinel", "model", "gemini"),
            LLMStatus.TIMEOUT,
        ),
        (
            litellm.RateLimitError("sentinel", "gemini", "model"),
            LLMStatus.RATE_LIMITED,
        ),
        (
            litellm.AuthenticationError("sentinel", "gemini", "model"),
            LLMStatus.AUTHENTICATION_ERROR,
        ),
        (
            litellm.ServiceUnavailableError("sentinel", "gemini", "model"),
            LLMStatus.PROVIDER_UNAVAILABLE,
        ),
        (RuntimeError("sentinel"), LLMStatus.PROVIDER_UNAVAILABLE),
    ],
)
def test_exception_mapping_is_single_call_and_sanitized(
    monkeypatch: pytest.MonkeyPatch,
    exception: Exception,
    status: LLMStatus,
) -> None:
    call_count = 0

    async def completion(**kwargs: Any) -> dict[str, Any]:
        nonlocal call_count
        call_count += 1
        raise exception

    result = asyncio.run(
        LiteLLMClient(
            _config(monkeypatch),
            completion=completion,
            monotonic=iter((1.0, 1.001)).__next__,
        ).complete(_request(), timeout_seconds=2)
    )

    assert result.status == status
    assert result.content is None
    assert "sentinel" not in result.model_dump_json()
    assert call_count == 1


def test_invalid_response_and_content_blocked_are_distinct(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = iter(({"choices": []}, _response(finish_reason="safety")))

    async def completion(**kwargs: Any) -> dict[str, Any]:
        return next(responses)

    client = LiteLLMClient(
        _config(monkeypatch),
        completion=completion,
        monotonic=iter((1.0, 1.0, 2.0, 2.0)).__next__,
    )
    first = asyncio.run(client.complete(_request(), timeout_seconds=2))
    second = asyncio.run(client.complete(_request(), timeout_seconds=2))

    assert first.status == LLMStatus.INVALID_RESPONSE
    assert second.status == LLMStatus.CONTENT_BLOCKED


def test_cancellation_is_reraised_without_second_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    async def completion(**kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            LiteLLMClient(
                _config(monkeypatch),
                completion=completion,
            ).complete(_request(), timeout_seconds=2)
        )

    assert calls == 1
