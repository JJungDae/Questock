from __future__ import annotations

import math
import os
from typing import Any

from pydantic import PrivateAttr, ValidationError, model_validator

from app.core.models import QuestockModel

APPROVED_LLM_MODEL = "gemini/gemini-3.5-flash"
_APPROVED_THINKING_LEVEL = "minimal"
_APPROVED_MAX_OUTPUT_TOKENS = 4096
_APPROVED_LLM_TIMEOUT_SECONDS = 15


class ConfigValidationError(ValueError):
    """Raised when environment config is invalid without echoing raw values."""


def _read_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ConfigValidationError(f"{name} must be a finite number") from exc
    if not math.isfinite(parsed):
        raise ConfigValidationError(f"{name} must be a finite number")
    return parsed


def _read_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ConfigValidationError(f"{name} must be an integer") from exc
    return parsed


class ProviderConfig(QuestockModel):
    timeout_seconds: float = 8
    retry_count: int = 1
    total_deadline_seconds: float = 20
    cache_ttl_seconds: float = 300
    opendart_api_key_configured: bool = False
    naver_client_id_configured: bool = False
    naver_client_secret_configured: bool = False

    _opendart_api_key: str | None = PrivateAttr(default=None)
    _naver_client_id: str | None = PrivateAttr(default=None)
    _naver_client_secret: str | None = PrivateAttr(default=None)

    @classmethod
    def from_env(cls) -> "ProviderConfig":
        timeout_seconds = _read_float("QUESTOCK_PROVIDER_TIMEOUT_SECONDS", 8)
        retry_count = _read_int("QUESTOCK_PROVIDER_RETRY_COUNT", 1)
        total_deadline_seconds = _read_float("QUESTOCK_PROVIDER_TOTAL_DEADLINE_SECONDS", 20)
        cache_ttl_seconds = _read_float("QUESTOCK_PROVIDER_CACHE_TTL_SECONDS", 300)
        opendart_api_key = os.getenv("OPENDART_API_KEY") or None
        naver_client_id = os.getenv("NAVER_CLIENT_ID") or None
        naver_client_secret = os.getenv("NAVER_CLIENT_SECRET") or None

        try:
            config = cls(
                timeout_seconds=timeout_seconds,
                retry_count=retry_count,
                total_deadline_seconds=total_deadline_seconds,
                cache_ttl_seconds=cache_ttl_seconds,
                opendart_api_key_configured=bool(opendart_api_key),
                naver_client_id_configured=bool(naver_client_id),
                naver_client_secret_configured=bool(naver_client_secret),
            )
        except ValidationError as exc:
            raise ConfigValidationError("provider numeric config is outside allowed range") from exc
        config._opendart_api_key = opendart_api_key
        config._naver_client_id = naver_client_id
        config._naver_client_secret = naver_client_secret
        return config

    @model_validator(mode="after")
    def validate_ranges(self) -> "ProviderConfig":
        if not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0:
            raise ConfigValidationError("QUESTOCK_PROVIDER_TIMEOUT_SECONDS must be greater than 0")
        if self.retry_count < 0:
            raise ConfigValidationError("QUESTOCK_PROVIDER_RETRY_COUNT must be greater than or equal to 0")
        if not math.isfinite(self.total_deadline_seconds) or self.total_deadline_seconds <= 0:
            raise ConfigValidationError("QUESTOCK_PROVIDER_TOTAL_DEADLINE_SECONDS must be greater than 0")
        if not math.isfinite(self.cache_ttl_seconds) or self.cache_ttl_seconds < 0:
            raise ConfigValidationError("QUESTOCK_PROVIDER_CACHE_TTL_SECONDS must be greater than or equal to 0")
        return self

    def safe_summary(self) -> dict[str, Any]:
        return {
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
            "total_deadline_seconds": self.total_deadline_seconds,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "opendart_api_key_configured": self.opendart_api_key_configured,
            "naver_client_id_configured": self.naver_client_id_configured,
            "naver_client_secret_configured": self.naver_client_secret_configured,
        }


class LLMConfig(QuestockModel):
    model: str = APPROVED_LLM_MODEL
    thinking_level: str = _APPROVED_THINKING_LEVEL
    max_output_tokens: int = _APPROVED_MAX_OUTPUT_TOKENS
    timeout_seconds: float = _APPROVED_LLM_TIMEOUT_SECONDS
    gemini_api_key_configured: bool = False

    _gemini_api_key: str | None = PrivateAttr(default=None)

    @classmethod
    def from_env(cls, *, require_credential: bool = False) -> "LLMConfig":
        if "LLM_THINKING_BUDGET" in os.environ:
            raise ConfigValidationError(
                "LLM_THINKING_BUDGET is not supported"
            )
        model = os.getenv("LLM_MODEL") or APPROVED_LLM_MODEL
        thinking_level = (
            os.getenv("LLM_THINKING_LEVEL") or _APPROVED_THINKING_LEVEL
        )
        max_output_tokens = _read_int(
            "LLM_MAX_OUTPUT_TOKENS",
            _APPROVED_MAX_OUTPUT_TOKENS,
        )
        timeout_seconds = _read_float(
            "LLM_TIMEOUT_SECONDS",
            _APPROVED_LLM_TIMEOUT_SECONDS,
        )
        api_key = os.getenv("GEMINI_API_KEY") or None
        try:
            config = cls(
                model=model,
                thinking_level=thinking_level,
                max_output_tokens=max_output_tokens,
                timeout_seconds=timeout_seconds,
                gemini_api_key_configured=bool(api_key),
            )
        except (ConfigValidationError, ValidationError) as exc:
            raise ConfigValidationError("LLM config is invalid") from exc
        config._gemini_api_key = api_key
        if require_credential and api_key is None:
            raise ConfigValidationError("GEMINI_API_KEY is not configured")
        return config

    @model_validator(mode="after")
    def validate_llm_config(self) -> "LLMConfig":
        if self.model != APPROVED_LLM_MODEL:
            raise ConfigValidationError("LLM_MODEL is not an approved model")
        if self.thinking_level != _APPROVED_THINKING_LEVEL:
            raise ConfigValidationError(
                "LLM_THINKING_LEVEL is not approved"
            )
        if (
            type(self.max_output_tokens) is not int
            or self.max_output_tokens != _APPROVED_MAX_OUTPUT_TOKENS
        ):
            raise ConfigValidationError(
                "LLM_MAX_OUTPUT_TOKENS is not approved"
            )
        if (
            type(self.timeout_seconds) not in {int, float}
            or not math.isfinite(self.timeout_seconds)
            or self.timeout_seconds != _APPROVED_LLM_TIMEOUT_SECONDS
        ):
            raise ConfigValidationError(
                "LLM_TIMEOUT_SECONDS is not approved"
            )
        if type(self.gemini_api_key_configured) is not bool:
            raise ConfigValidationError("LLM credential state is invalid")
        return self

    def require_api_key(self) -> str:
        if self._gemini_api_key is None:
            raise ConfigValidationError("GEMINI_API_KEY is not configured")
        return self._gemini_api_key

    def safe_summary(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "thinking_level": self.thinking_level,
            "max_output_tokens": self.max_output_tokens,
            "timeout_seconds": self.timeout_seconds,
            "gemini_api_key_configured": self.gemini_api_key_configured,
        }


__all__ = [
    "APPROVED_LLM_MODEL",
    "ConfigValidationError",
    "LLMConfig",
    "ProviderConfig",
]
