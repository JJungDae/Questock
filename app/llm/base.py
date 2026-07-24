from __future__ import annotations

import copy
import math
import re
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SAFE_NAME = re.compile(r"^[A-Za-z0-9._:/-]+$")
_ALLOWED_ROLES = frozenset({"system", "user"})


class LLMStatus(StrEnum):
    OK = "ok"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    AUTHENTICATION_ERROR = "authentication_error"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    INVALID_RESPONSE = "invalid_response"
    CONTENT_BLOCKED = "content_blocked"


class LLMValidationError(ValueError):
    """Raised when a project-owned LLM boundary value is invalid."""


class LLMMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    role: str
    content: str = Field(min_length=1, max_length=16_000)

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        if value not in _ALLOWED_ROLES:
            raise ValueError("unsupported LLM message role")
        return value

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("LLM message content must not be blank")
        return value


class LLMRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    messages: tuple[LLMMessage, ...] = Field(min_length=1, max_length=8)
    response_schema: dict[str, Any]

    @field_validator("response_schema")
    @classmethod
    def validate_response_schema(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not value:
            raise ValueError("response schema must not be empty")
        return copy.deepcopy(value)


class LLMResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    content: str | None = None
    model: str
    provider: str
    usage: dict[str, int | float] = Field(default_factory=dict)
    finish_reason: str | None = None
    latency_ms: float
    status: LLMStatus

    @field_validator("model", "provider")
    @classmethod
    def validate_safe_name(cls, value: str) -> str:
        if not value or not _SAFE_NAME.fullmatch(value):
            raise ValueError("LLM identifier is invalid")
        return value

    @field_validator("latency_ms")
    @classmethod
    def validate_latency(cls, value: float) -> float:
        if not math.isfinite(value) or value < 0:
            raise ValueError("LLM latency is invalid")
        return value

    @field_validator("usage")
    @classmethod
    def validate_usage(
        cls,
        value: dict[str, int | float],
    ) -> dict[str, int | float]:
        output: dict[str, int | float] = {}
        for key, amount in value.items():
            if (
                not isinstance(key, str)
                or not key
                or not _SAFE_NAME.fullmatch(key)
                or type(amount) not in {int, float}
                or not math.isfinite(amount)
                or amount < 0
            ):
                raise ValueError("LLM usage is invalid")
            output[key] = amount
        return copy.deepcopy(output)

    @field_validator("finish_reason")
    @classmethod
    def validate_finish_reason(cls, value: str | None) -> str | None:
        if value is not None and (not value or not _SAFE_NAME.fullmatch(value)):
            raise ValueError("LLM finish reason is invalid")
        return value

    @model_validator(mode="after")
    def validate_status_contract(self) -> "LLMResult":
        if self.status == LLMStatus.OK:
            if self.content is None or not self.content.strip():
                raise ValueError("successful LLM result requires content")
        elif self.content is not None:
            raise ValueError("failed LLM result must not expose content")
        return self


def create_llm_result(
    *,
    status: LLMStatus,
    model: str,
    provider: str,
    latency_ms: float,
    content: str | None = None,
    usage: dict[str, int | float] | None = None,
    finish_reason: str | None = None,
) -> LLMResult:
    try:
        return LLMResult(
            status=status,
            content=content,
            model=model,
            provider=provider,
            usage=copy.deepcopy(usage or {}),
            finish_reason=finish_reason,
            latency_ms=latency_ms,
        )
    except (TypeError, ValueError) as exc:
        raise LLMValidationError("LLM result is invalid") from exc


@runtime_checkable
class LLMClient(Protocol):
    async def complete(
        self,
        request: LLMRequest,
        *,
        timeout_seconds: float,
    ) -> LLMResult: ...


__all__ = [
    "LLMClient",
    "LLMMessage",
    "LLMRequest",
    "LLMResult",
    "LLMStatus",
    "LLMValidationError",
    "create_llm_result",
]
