import asyncio
from datetime import UTC, date, datetime

import pytest

from app.config import ProviderConfig
from app.core.models import DateRange, SecurityIdentifier
from app.core.status import ProviderStatus
from app.providers.base import (
    InMemoryTTLCache,
    ProviderResultContractError,
    create_provider_result,
    fetch_required_providers,
    fetch_with_policy,
    make_cache_key,
)
from app.providers.fake import FakeProvider


class ManualClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def samsung_security():
    return SecurityIdentifier(
        market="KRX",
        ticker="005930",
        security_name="삼성전자",
        security_type="common_stock",
        corp_code=None,
        corp_name="삼성전자",
    )


def run(coro):
    return asyncio.run(coro)


def test_provider_result_factory_enforces_ok_and_no_data_contracts():
    ok = create_provider_result(status=ProviderStatus.OK, data={"count": 1})
    no_data = create_provider_result(status=ProviderStatus.NO_DATA)

    assert ok.data == {"count": 1}
    assert ok.error_code is None
    assert ok.fetched_at.tzinfo == UTC
    assert no_data.data is None
    assert no_data.error_code is None

    with pytest.raises(ProviderResultContractError):
        create_provider_result(status=ProviderStatus.OK, data=None)
    with pytest.raises(ProviderResultContractError):
        create_provider_result(status=ProviderStatus.NO_DATA, data={"unexpected": True})


@pytest.mark.parametrize(
    ("status", "error_code", "safe_message"),
    [
        (ProviderStatus.INVALID_QUERY, "invalid_query", "provider rejected the query"),
        (ProviderStatus.UNAUTHORIZED, "unauthorized", "provider authorization failed"),
        (ProviderStatus.RATE_LIMITED, "rate_limited", "provider rate limit reached"),
        (ProviderStatus.PARSE_ERROR, "parse_error", "provider response could not be parsed"),
        (ProviderStatus.PROVIDER_UNAVAILABLE, "provider_unavailable", "provider unavailable"),
    ],
)
def test_provider_result_factory_enforces_failure_contracts(status, error_code, safe_message):
    result = create_provider_result(status=status, message="caller message is ignored")

    assert result.data is None
    assert result.error_code == error_code
    assert result.message == safe_message
    assert result.fetched_at.tzinfo == UTC

    with pytest.raises(ProviderResultContractError):
        create_provider_result(status=status, data={"unexpected": True})
    with pytest.raises(ProviderResultContractError):
        create_provider_result(status=status, error_code="other")


@pytest.mark.parametrize(
    "status",
    [ProviderStatus.UNAUTHORIZED, ProviderStatus.PROVIDER_UNAVAILABLE, ProviderStatus.PARSE_ERROR],
)
def test_failure_messages_do_not_include_raw_secret_sentinel(status):
    secret = "SENTINEL_SECRET_DO_NOT_LEAK"

    result = create_provider_result(status=status, message=f"raw failure contained {secret}")
    rendered = result.model_dump_json() + repr(result) + str(result)

    assert secret not in rendered


def test_provider_result_factory_enforces_timeout_error_codes_and_utc_fetched_at():
    attempt = create_provider_result(status=ProviderStatus.TIMEOUT)
    total = create_provider_result(status=ProviderStatus.TIMEOUT, error_code="total_deadline_exceeded")

    assert attempt.error_code == "attempt_timeout"
    assert total.error_code == "total_deadline_exceeded"

    with pytest.raises(ProviderResultContractError):
        create_provider_result(status=ProviderStatus.TIMEOUT, error_code="timeout")
    with pytest.raises(ProviderResultContractError):
        create_provider_result(
            status=ProviderStatus.NO_DATA,
            fetched_at=datetime(2026, 7, 21, 9, 0),
        )


@pytest.mark.parametrize(
    ("scenario", "status", "error_code"),
    [
        ("ok", ProviderStatus.OK, None),
        ("no_data", ProviderStatus.NO_DATA, None),
        ("invalid_query", ProviderStatus.INVALID_QUERY, "invalid_query"),
        ("timeout", ProviderStatus.TIMEOUT, "attempt_timeout"),
        ("rate_limited", ProviderStatus.RATE_LIMITED, "rate_limited"),
        ("parse_error", ProviderStatus.PARSE_ERROR, "parse_error"),
        ("provider_unavailable", ProviderStatus.PROVIDER_UNAVAILABLE, "provider_unavailable"),
        ("unauthorized", ProviderStatus.UNAUTHORIZED, "unauthorized"),
    ],
)
def test_fake_provider_scenarios_are_deterministic(scenario, status, error_code):
    provider = FakeProvider(scenario=scenario)

    result = run(provider.fetch(samsung_security(), query="최근 뉴스"))

    assert result.status == status
    assert result.error_code == error_code
    if status == ProviderStatus.OK:
        assert result.data["security_id"] == "KRX:005930"
    else:
        assert result.data is None


def test_fetch_with_policy_retries_timeout_and_provider_unavailable_only():
    retry_provider = FakeProvider(scenario=["provider_unavailable", "ok"])
    rate_limited_provider = FakeProvider(scenario=["rate_limited", "ok"])
    timeout_provider = FakeProvider(scenario=["timeout", "ok"])
    config = ProviderConfig(timeout_seconds=0.05, retry_count=1, total_deadline_seconds=1)

    retry_result = run(fetch_with_policy(retry_provider, samsung_security(), config))
    rate_limited_result = run(fetch_with_policy(rate_limited_provider, samsung_security(), config))
    timeout_result = run(fetch_with_policy(timeout_provider, samsung_security(), config))

    assert retry_result.status == ProviderStatus.OK
    assert retry_provider.attempt_count == 2
    assert rate_limited_result.status == ProviderStatus.RATE_LIMITED
    assert rate_limited_provider.attempt_count == 1
    assert timeout_result.status == ProviderStatus.OK
    assert timeout_provider.attempt_count == 2


def test_fetch_with_policy_normalizes_provider_exception_inside_retry_loop():
    provider = FakeProvider(scenario=["raise", "ok"])
    config = ProviderConfig(timeout_seconds=0.05, retry_count=1, total_deadline_seconds=1)

    result = run(fetch_with_policy(provider, samsung_security(), config))

    assert result.status == ProviderStatus.OK
    assert provider.attempt_count == 2


def test_fetch_with_policy_attempt_timeout_cancels_pending_task():
    provider = FakeProvider(scenario="pending")
    config = ProviderConfig(timeout_seconds=0.01, retry_count=0, total_deadline_seconds=1)

    result = run(fetch_with_policy(provider, samsung_security(), config))

    assert result.status == ProviderStatus.TIMEOUT
    assert result.error_code == "attempt_timeout"
    assert provider.cancel_count == 1


def test_fetch_with_policy_total_deadline_exceeded_cancels_pending_task():
    provider = FakeProvider(scenario="pending")
    config = ProviderConfig(timeout_seconds=1, retry_count=1, total_deadline_seconds=0.01)

    result = run(fetch_with_policy(provider, samsung_security(), config))

    assert result.status == ProviderStatus.TIMEOUT
    assert result.error_code == "total_deadline_exceeded"
    assert provider.cancel_count == 1


def test_fetch_required_providers_keeps_all_keys_and_isolates_failures():
    providers = {
        "news": FakeProvider(key="news", scenario="ok"),
        "disclosure": FakeProvider(key="disclosure", scenario="raise"),
    }
    config = ProviderConfig(timeout_seconds=0.05, retry_count=0, total_deadline_seconds=1)

    results = run(fetch_required_providers(providers, samsung_security(), config))

    assert set(results) == {"news", "disclosure"}
    assert results["news"].status == ProviderStatus.OK
    assert results["disclosure"].status == ProviderStatus.PROVIDER_UNAVAILABLE
    assert results["disclosure"].error_code == "provider_unavailable"


def test_fetch_required_providers_preserves_ok_result_when_another_provider_hits_total_deadline():
    ok_provider = FakeProvider(key="news", scenario="ok")
    pending_provider = FakeProvider(key="disclosure", scenario="pending")
    providers = {"news": ok_provider, "disclosure": pending_provider}
    config = ProviderConfig(timeout_seconds=1, retry_count=0, total_deadline_seconds=0.01)

    results = run(fetch_required_providers(providers, samsung_security(), config))

    assert set(results) == {"news", "disclosure"}
    assert results["news"].status == ProviderStatus.OK
    assert results["disclosure"].status == ProviderStatus.TIMEOUT
    assert results["disclosure"].error_code == "total_deadline_exceeded"
    assert pending_provider.cancel_count == 1


def test_fetch_required_providers_rejects_mapping_key_mismatch():
    providers = {"news": FakeProvider(key="other", scenario="ok")}
    config = ProviderConfig(timeout_seconds=0.05, retry_count=0, total_deadline_seconds=1)

    with pytest.raises(ValueError):
        run(fetch_required_providers(providers, samsung_security(), config))


def test_cache_key_uses_provider_security_normalized_query_and_date_range():
    key = make_cache_key(
        provider_key="news",
        security=samsung_security(),
        query="  Ｓａｍｓｕｎｇ   NEWS  ",
        date_range=DateRange(start=date(2026, 7, 1), end=date(2026, 7, 21)),
    )

    assert key.provider_key == "news"
    assert key.security_id == "KRX:005930"
    assert key.normalized_query == "samsung news"
    assert key.date_start == date(2026, 7, 1)
    assert key.date_end == date(2026, 7, 21)


def test_ttl_cache_only_caches_ok_results_and_preserves_original_fetched_at_on_hit():
    clock = ManualClock()
    cache = InMemoryTTLCache(ttl_seconds=300, clock=clock)
    key = make_cache_key("news", samsung_security(), "query")
    fetched_at = datetime(2026, 7, 21, 9, 0, tzinfo=UTC)
    original = create_provider_result(status=ProviderStatus.OK, data={"item": 1}, fetched_at=fetched_at)
    no_data = create_provider_result(status=ProviderStatus.NO_DATA)

    cache.set(key, original)
    hit = cache.get(key)
    no_data_key = make_cache_key("news", samsung_security(), "empty")
    cache.set(no_data_key, no_data)

    assert hit is not None
    assert hit.from_cache is True
    assert hit.fetched_at == fetched_at
    assert original.from_cache is False
    assert cache.get(no_data_key) is None


def test_ttl_cache_deep_copies_mutable_payload_on_set_and_get():
    clock = ManualClock()
    cache = InMemoryTTLCache(ttl_seconds=300, clock=clock)
    key = make_cache_key("news", samsung_security(), "query")
    original = create_provider_result(status=ProviderStatus.OK, data={"items": [{"value": 1}]})

    cache.set(key, original)
    original.data["items"][0]["value"] = 99
    first_hit = cache.get(key)
    assert first_hit is not None
    first_hit.data["items"][0]["value"] = 42
    second_hit = cache.get(key)

    assert second_hit is not None
    assert second_hit.data["items"][0]["value"] == 1


def test_ttl_cache_expires_without_returning_stale_result_and_ttl_zero_disables_cache():
    clock = ManualClock()
    cache = InMemoryTTLCache(ttl_seconds=10, clock=clock)
    disabled = InMemoryTTLCache(ttl_seconds=0, clock=clock)
    key = make_cache_key("news", samsung_security(), "query")
    original = create_provider_result(status=ProviderStatus.OK, data={"item": 1})

    cache.set(key, original)
    disabled.set(key, original)
    clock.advance(10)

    assert cache.get(key) is None
    assert disabled.get(key) is None


def test_fetch_with_policy_uses_cache_for_ok_results_only():
    clock = ManualClock()
    cache = InMemoryTTLCache(ttl_seconds=300, clock=clock)
    config = ProviderConfig(timeout_seconds=0.05, retry_count=0, total_deadline_seconds=1)
    ok_provider = FakeProvider(key="news", scenario="ok", data={"item": 1})
    no_data_provider = FakeProvider(key="empty", scenario="no_data")

    first = run(fetch_with_policy(ok_provider, samsung_security(), config, query="q", cache=cache, clock=clock))
    second = run(fetch_with_policy(ok_provider, samsung_security(), config, query="q", cache=cache, clock=clock))
    run(fetch_with_policy(no_data_provider, samsung_security(), config, query="q", cache=cache, clock=clock))
    run(fetch_with_policy(no_data_provider, samsung_security(), config, query="q", cache=cache, clock=clock))

    assert first.from_cache is False
    assert second.from_cache is True
    assert second.fetched_at == first.fetched_at
    assert ok_provider.attempt_count == 1
    assert no_data_provider.attempt_count == 2
