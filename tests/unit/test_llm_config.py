from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.config import ConfigValidationError, LLMConfig

LLM_ENV = (
    "GEMINI_API_KEY",
    "LLM_MODEL",
    "LLM_THINKING_LEVEL",
    "LLM_THINKING_BUDGET",
    "LLM_MAX_OUTPUT_TOKENS",
    "LLM_TIMEOUT_SECONDS",
    "LLM_API_KEY",
)


def _clear(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in LLM_ENV:
        monkeypatch.delenv(name, raising=False)


def test_fake_config_loads_without_credential(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear(monkeypatch)

    config = LLMConfig.from_env()

    assert config.safe_summary() == {
        "model": "gemini/gemini-3.5-flash",
        "thinking_level": "minimal",
        "max_output_tokens": 4096,
        "timeout_seconds": 15,
        "gemini_api_key_configured": False,
    }
    with pytest.raises(ConfigValidationError, match="not configured"):
        config.require_api_key()


def test_exact_thinking_level_is_supported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear(monkeypatch)
    monkeypatch.setenv("LLM_THINKING_LEVEL", "minimal")

    assert LLMConfig.from_env().thinking_level == "minimal"


@pytest.mark.parametrize("value", ["", "0", "1024", "not-a-number"])
def test_legacy_thinking_budget_env_is_rejected_without_echo(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    _clear(monkeypatch)
    monkeypatch.setenv("LLM_THINKING_BUDGET", value)

    with pytest.raises(ConfigValidationError) as exc_info:
        LLMConfig.from_env()

    assert str(exc_info.value) == "LLM_THINKING_BUDGET is not supported"
    if value:
        assert value not in str(exc_info.value)


@pytest.mark.parametrize(
    "model",
    [
        "gemini/gemini-2.5-flash",
        "gemini/gemini-2.5-flash-preview",
        "gemini/gemini-2.5-flash-latest",
        "gemini/gemini-2.0-flash",
        "gemini/gemini-3.5-flash-preview",
    ],
)
def test_nonapproved_model_is_rejected_without_echo(
    monkeypatch: pytest.MonkeyPatch,
    model: str,
) -> None:
    _clear(monkeypatch)
    monkeypatch.setenv("LLM_MODEL", model)

    with pytest.raises(ConfigValidationError) as exc_info:
        LLMConfig.from_env()

    assert model not in str(exc_info.value)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("LLM_THINKING_LEVEL", "low"),
        ("LLM_MAX_OUTPUT_TOKENS", "0"),
        ("LLM_MAX_OUTPUT_TOKENS", "256"),
        ("LLM_MAX_OUTPUT_TOKENS", "1024"),
        ("LLM_MAX_OUTPUT_TOKENS", "9000"),
        ("LLM_TIMEOUT_SECONDS", "0"),
        ("LLM_TIMEOUT_SECONDS", "8"),
        ("LLM_TIMEOUT_SECONDS", "10"),
        ("LLM_TIMEOUT_SECONDS", "nan"),
        ("LLM_TIMEOUT_SECONDS", "inf"),
        ("LLM_TIMEOUT_SECONDS", "21"),
    ],
)
def test_invalid_llm_contract_value_is_sanitized(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    value: str,
) -> None:
    _clear(monkeypatch)
    monkeypatch.setenv(name, value)

    with pytest.raises(ConfigValidationError) as exc_info:
        LLMConfig.from_env()

    assert value not in str(exc_info.value)


def test_only_gemini_api_key_is_a_credential_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear(monkeypatch)
    monkeypatch.setenv("LLM_API_KEY", "-".join(("ignored", "test", "key")))

    config = LLMConfig.from_env()

    assert config.gemini_api_key_configured is False


def test_secret_is_absent_from_public_config_surfaces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear(monkeypatch)
    sentinel = "-".join(("M3", "SECRET", "SENTINEL"))
    monkeypatch.setenv("GEMINI_API_KEY", sentinel)

    config = LLMConfig.from_env(require_credential=True)
    surfaces = (
        repr(config),
        str(config),
        config.model_dump_json(),
        json.dumps(config.safe_summary(), sort_keys=True),
    )

    assert config.require_api_key() == sentinel
    assert config.gemini_api_key_configured is True
    assert all(sentinel not in surface for surface in surfaces)


def test_env_example_keeps_llm_values_empty() -> None:
    values = {}
    for line in Path(".env.example").read_text(encoding="utf-8").splitlines():
        if "=" in line:
            name, value = line.split("=", 1)
            values[name] = value

    assert values["GEMINI_API_KEY"] == ""
    assert values["LLM_MODEL"] == ""
    assert values["LLM_THINKING_LEVEL"] == ""
    assert "LLM_THINKING_BUDGET" not in values
    assert values["LLM_MAX_OUTPUT_TOKENS"] == ""
    assert values["LLM_TIMEOUT_SECONDS"] == ""
    assert values["QUESTOCK_LLM_MODE"] == ""
    assert values["QUESTOCK_REQUEST_PROTECTION_ENABLED"] == ""
    assert values["QUESTOCK_RESPONSE_CACHE_ENABLED"] == ""
