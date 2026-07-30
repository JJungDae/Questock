from __future__ import annotations

import asyncio
import math
import os
import time
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"

import litellm

from app.config import LLMConfig
from app.llm.base import (
    LLMRequest,
    LLMResult,
    LLMStatus,
    create_llm_result,
)

_PROVIDER = "gemini"
_CONTENT_BLOCKED_REASONS = frozenset({"content_filter", "safety", "blocked"})

CompletionCallable = Callable[..., Awaitable[Any]]


class LiteLLMClient:
    def __init__(
        self,
        config: LLMConfig,
        *,
        completion: CompletionCallable | None = None,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if not isinstance(config, LLMConfig):
            raise TypeError("config must be an LLMConfig")
        self._config = config.model_copy(deep=True)
        self._api_key = config.require_api_key()
        self._completion = completion or litellm.acompletion
        self._monotonic = monotonic

    async def complete(
        self,
        request: LLMRequest,
        *,
        timeout_seconds: float,
    ) -> LLMResult:
        if not isinstance(request, LLMRequest):
            raise TypeError("request must be an LLMRequest")
        if (
            type(timeout_seconds) not in {int, float}
            or not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be a finite positive number")

        started_at = self._monotonic()
        try:
            completion_kwargs = {
                "model": self._config.model,
                "messages": [
                    {"role": item.role, "content": item.content}
                    for item in request.messages
                ],
                "timeout": min(
                    float(timeout_seconds),
                    self._config.timeout_seconds,
                ),
                "max_tokens": self._config.max_output_tokens,
                "reasoning_effort": self._config.thinking_level,
                "num_retries": 0,
                "api_key": self._api_key,
            }
            if request.temperature is not None:
                completion_kwargs["temperature"] = request.temperature
            response = await self._completion(
                **completion_kwargs,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            return self._failure_result(
                _exception_status(exc),
                started_at=started_at,
            )

        latency_ms = _latency_ms(self._monotonic() - started_at)
        try:
            content, finish_reason = _content_and_finish_reason(response)
            if finish_reason in _CONTENT_BLOCKED_REASONS:
                return create_llm_result(
                    status=LLMStatus.CONTENT_BLOCKED,
                    model=self._config.model,
                    provider=_PROVIDER,
                    latency_ms=latency_ms,
                )
            return create_llm_result(
                status=LLMStatus.OK,
                content=content,
                model=self._config.model,
                provider=_PROVIDER,
                usage=_usage(response),
                finish_reason=finish_reason,
                latency_ms=latency_ms,
            )
        except (AttributeError, IndexError, KeyError, TypeError, ValueError):
            return create_llm_result(
                status=LLMStatus.INVALID_RESPONSE,
                model=self._config.model,
                provider=_PROVIDER,
                latency_ms=latency_ms,
            )

    def _failure_result(
        self,
        status: LLMStatus,
        *,
        started_at: float,
    ) -> LLMResult:
        return create_llm_result(
            status=status,
            model=self._config.model,
            provider=_PROVIDER,
            latency_ms=_latency_ms(self._monotonic() - started_at),
        )


def _exception_status(exc: Exception) -> LLMStatus:
    if isinstance(exc, litellm.AuthenticationError):
        return LLMStatus.AUTHENTICATION_ERROR
    if isinstance(exc, litellm.RateLimitError):
        return LLMStatus.RATE_LIMITED
    if isinstance(exc, litellm.Timeout):
        return LLMStatus.TIMEOUT
    blocked_type = getattr(litellm, "ContentPolicyViolationError", None)
    if isinstance(blocked_type, type) and isinstance(exc, blocked_type):
        return LLMStatus.CONTENT_BLOCKED
    if isinstance(exc, litellm.ServiceUnavailableError):
        return LLMStatus.PROVIDER_UNAVAILABLE
    return LLMStatus.PROVIDER_UNAVAILABLE


def _content_and_finish_reason(response: Any) -> tuple[str, str | None]:
    choices = _read(response, "choices")
    if not isinstance(choices, (list, tuple)) or not choices:
        raise ValueError
    choice = choices[0]
    message = _read(choice, "message")
    content = _read(message, "content")
    finish_reason = _read(choice, "finish_reason")
    if not isinstance(content, str) or not content.strip():
        raise ValueError
    if finish_reason is not None:
        if not isinstance(finish_reason, str) or not finish_reason:
            raise ValueError
        finish_reason = finish_reason.casefold()
    return content, finish_reason


def _usage(response: Any) -> dict[str, int | float]:
    raw_usage = _read(response, "usage")
    if raw_usage is None:
        return {}
    output: dict[str, int | float] = {}
    for source_key, target_key in (
        ("prompt_tokens", "prompt_tokens"),
        ("completion_tokens", "completion_tokens"),
        ("total_tokens", "total_tokens"),
    ):
        value = _read(raw_usage, source_key)
        if value is None:
            continue
        if type(value) not in {int, float} or not math.isfinite(value) or value < 0:
            raise ValueError
        output[target_key] = value
    return output


def _read(value: Any, key: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(key)
    return getattr(value, key)


def _latency_ms(elapsed_seconds: float) -> float:
    if not math.isfinite(elapsed_seconds):
        return 0.0
    return round(max(0.0, elapsed_seconds) * 1000, 3)


__all__ = ["LiteLLMClient"]
