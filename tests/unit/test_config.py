import json

import pytest

from app.config import ConfigValidationError, ProviderConfig

ENV_KEYS = [
    "OPENDART_API_KEY",
    "NAVER_CLIENT_ID",
    "NAVER_CLIENT_SECRET",
    "QUESTOCK_PROVIDER_TIMEOUT_SECONDS",
    "QUESTOCK_PROVIDER_RETRY_COUNT",
    "QUESTOCK_PROVIDER_TOTAL_DEADLINE_SECONDS",
    "QUESTOCK_PROVIDER_CACHE_TTL_SECONDS",
]


@pytest.fixture(autouse=True)
def clear_provider_env(monkeypatch):
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_provider_config_loads_defaults_without_credentials():
    config = ProviderConfig.from_env()

    assert config.timeout_seconds == 8
    assert config.retry_count == 1
    assert config.total_deadline_seconds == 20
    assert config.cache_ttl_seconds == 300
    assert config.safe_summary()["opendart_api_key_configured"] is False
    assert config.safe_summary()["naver_client_id_configured"] is False
    assert config.safe_summary()["naver_client_secret_configured"] is False


def test_provider_config_loads_numeric_env_and_secret_configured_flags(monkeypatch):
    monkeypatch.setenv("OPENDART_API_KEY", "opendart-secret")
    monkeypatch.setenv("NAVER_CLIENT_ID", "naver-id")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "naver-secret")
    monkeypatch.setenv("QUESTOCK_PROVIDER_TIMEOUT_SECONDS", "1.5")
    monkeypatch.setenv("QUESTOCK_PROVIDER_RETRY_COUNT", "2")
    monkeypatch.setenv("QUESTOCK_PROVIDER_TOTAL_DEADLINE_SECONDS", "4.5")
    monkeypatch.setenv("QUESTOCK_PROVIDER_CACHE_TTL_SECONDS", "0")

    config = ProviderConfig.from_env()

    assert config.timeout_seconds == 1.5
    assert config.retry_count == 2
    assert config.total_deadline_seconds == 4.5
    assert config.cache_ttl_seconds == 0
    assert config.safe_summary()["opendart_api_key_configured"] is True
    assert config.safe_summary()["naver_client_id_configured"] is True
    assert config.safe_summary()["naver_client_secret_configured"] is True


def test_provider_config_does_not_expose_secret_values(monkeypatch):
    secret_values = ["opendart-secret", "naver-id", "naver-secret"]
    monkeypatch.setenv("OPENDART_API_KEY", secret_values[0])
    monkeypatch.setenv("NAVER_CLIENT_ID", secret_values[1])
    monkeypatch.setenv("NAVER_CLIENT_SECRET", secret_values[2])

    config = ProviderConfig.from_env()
    exposed_text = "\n".join(
        [
            repr(config),
            str(config),
            config.model_dump_json(),
            json.dumps(config.safe_summary(), ensure_ascii=False),
        ]
    )

    for secret in secret_values:
        assert secret not in exposed_text
    assert "configured" in exposed_text


@pytest.mark.parametrize(
    ("env_key", "env_value"),
    [
        ("QUESTOCK_PROVIDER_TIMEOUT_SECONDS", "not-a-number-secret"),
        ("QUESTOCK_PROVIDER_TIMEOUT_SECONDS", "-1"),
        ("QUESTOCK_PROVIDER_TIMEOUT_SECONDS", "nan"),
        ("QUESTOCK_PROVIDER_TIMEOUT_SECONDS", "inf"),
        ("QUESTOCK_PROVIDER_RETRY_COUNT", "-1"),
        ("QUESTOCK_PROVIDER_RETRY_COUNT", "1.5"),
        ("QUESTOCK_PROVIDER_TOTAL_DEADLINE_SECONDS", "0"),
        ("QUESTOCK_PROVIDER_CACHE_TTL_SECONDS", "-0.1"),
    ],
)
def test_provider_config_rejects_invalid_numeric_env_without_echoing_raw_value(monkeypatch, env_key, env_value):
    monkeypatch.setenv(env_key, env_value)

    with pytest.raises(ConfigValidationError) as exc_info:
        ProviderConfig.from_env()

    assert env_value not in str(exc_info.value)
