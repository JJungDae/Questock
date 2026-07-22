import asyncio
import copy
import json
from datetime import UTC, date
from pathlib import Path

import pytest

from app.config import ProviderConfig
from app.core.models import DateRange, SecurityIdentifier
from app.core.resolver import SecurityResolver
from app.core.status import ProviderStatus
from app.providers import RecordedMarketSnapshotProvider as ExportedRecordedMarketSnapshotProvider
from app.providers.base import fetch_with_policy
from app.providers.market import (
    PERCENT_TOLERANCE,
    PRICE_CHANGE_TOLERANCE,
    RECORDED_MARKET_SNAPSHOT_PROVIDER_KEY,
    RecordedMarketSnapshotProvider,
    market_snapshot_direction,
)

FIXTURE_PATH = Path("tests/fixtures/market/market_snapshot_synthetic.json")
SAMSUNG = "KRX:005930"
SK_HYNIX = "KRX:000660"
HYUNDAI = "KRX:005380"


def run(coro):
    return asyncio.run(coro)


def fixture_data():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def fixture_with_update(index: int, **updates):
    data = fixture_data()
    data["snapshots"][index].update(updates)
    return data


def supported_security(security_id: str) -> SecurityIdentifier:
    result = SecurityResolver().resolve(security_id)
    assert result.security is not None
    return result.security


def fetch_snapshot(provider, security_id=SAMSUNG, date_range=None, query=None):
    result = run(provider.fetch(supported_security(security_id), date_range=date_range, query=query))
    assert result.status == ProviderStatus.OK
    assert result.data is not None
    return result.data


def assert_failure_is_sanitized(result):
    rendered = json.dumps(result.model_dump(mode="json"), ensure_ascii=False)
    assert "C:\\Users" not in rendered
    assert "/tmp/" not in rendered
    assert "sentinel-secret" not in rendered
    assert "Traceback" not in rendered
    assert "raw" not in rendered


def test_provider_key_and_package_export():
    provider = RecordedMarketSnapshotProvider()

    assert provider.key == RECORDED_MARKET_SNAPSHOT_PROVIDER_KEY
    assert ExportedRecordedMarketSnapshotProvider is RecordedMarketSnapshotProvider


def test_recorded_fixture_covers_three_supported_securities_and_directions():
    provider = RecordedMarketSnapshotProvider()

    samsung = fetch_snapshot(provider, SAMSUNG)
    sk_hynix = fetch_snapshot(provider, SK_HYNIX)
    hyundai = fetch_snapshot(provider, HYUNDAI)

    assert samsung.security_id == SAMSUNG
    assert sk_hynix.security_id == SK_HYNIX
    assert hyundai.security_id == HYUNDAI
    assert market_snapshot_direction(samsung) == "up"
    assert market_snapshot_direction(sk_hynix) == "down"
    assert market_snapshot_direction(hyundai) == "flat"


def test_default_selection_is_latest_and_date_range_filters_are_inclusive():
    provider = RecordedMarketSnapshotProvider()

    latest = fetch_snapshot(provider, SAMSUNG)
    start_only = fetch_snapshot(provider, SAMSUNG, DateRange(start=date(2026, 7, 21)))
    end_only = fetch_snapshot(provider, SAMSUNG, DateRange(end=date(2026, 7, 20)))
    same_day = fetch_snapshot(provider, SAMSUNG, DateRange(start=date(2026, 7, 20), end=date(2026, 7, 20)))
    both_boundaries = fetch_snapshot(provider, SAMSUNG, DateRange(start=date(2026, 7, 20), end=date(2026, 7, 21)))

    assert latest.trading_date == date(2026, 7, 21)
    assert start_only.trading_date == date(2026, 7, 21)
    assert end_only.trading_date == date(2026, 7, 20)
    assert same_day.trading_date == date(2026, 7, 20)
    assert both_boundaries.trading_date == date(2026, 7, 21)


def test_no_matching_date_returns_no_data():
    provider = RecordedMarketSnapshotProvider()

    result = run(provider.fetch(supported_security(SAMSUNG), date_range=DateRange(start=date(2026, 7, 19), end=date(2026, 7, 19))))

    assert result.status == ProviderStatus.NO_DATA
    assert result.data is None
    assert result.error_code is None


@pytest.mark.parametrize("query", [None, "", "   "])
def test_none_empty_and_whitespace_query_are_allowed(query):
    provider = RecordedMarketSnapshotProvider()

    result = run(provider.fetch(supported_security(SAMSUNG), query=query))

    assert result.status == ProviderStatus.OK


@pytest.mark.parametrize("query", ["price", " \uc8fc\uac00 "])
def test_explicit_non_empty_query_is_invalid_query(query):
    provider = RecordedMarketSnapshotProvider()

    result = run(provider.fetch(supported_security(SAMSUNG), query=query))

    assert result.status == ProviderStatus.INVALID_QUERY
    assert result.error_code == "invalid_query"
    assert_failure_is_sanitized(result)


def test_observed_at_is_timezone_aware_utc_and_kst_date_must_match_trading_date():
    provider = RecordedMarketSnapshotProvider()
    snapshot = fetch_snapshot(provider, SAMSUNG)

    assert snapshot.observed_at.tzinfo is UTC
    assert snapshot.observed_at.isoformat() == "2026-07-21T06:30:00+00:00"

    naive = RecordedMarketSnapshotProvider(fixture_data=fixture_with_update(0, observed_at="2026-07-20T15:30:00"))
    mismatch = RecordedMarketSnapshotProvider(fixture_data=fixture_with_update(0, trading_date="2026-07-21"))

    naive_result = run(naive.fetch(supported_security(SAMSUNG), date_range=DateRange(end=date(2026, 7, 20))))
    mismatch_result = run(mismatch.fetch(supported_security(SAMSUNG), date_range=DateRange(end=date(2026, 7, 20))))

    assert naive_result.status == ProviderStatus.PARSE_ERROR
    assert mismatch_result.status == ProviderStatus.PARSE_ERROR


def test_market_session_source_and_tolerance_contracts():
    provider = RecordedMarketSnapshotProvider(fixture_data=fixture_with_update(0, source="untrusted"))

    snapshot = fetch_snapshot(provider, SAMSUNG, DateRange(end=date(2026, 7, 20)))

    assert snapshot.market_session == "closing"
    assert snapshot.source == RECORDED_MARKET_SNAPSHOT_PROVIDER_KEY
    assert PRICE_CHANGE_TOLERANCE == PERCENT_TOLERANCE
    assert str(PRICE_CHANGE_TOLERANCE) == "0.000001"

    invalid_session = RecordedMarketSnapshotProvider(fixture_data=fixture_with_update(0, market_session="live_open"))
    result = run(invalid_session.fetch(supported_security(SAMSUNG), date_range=DateRange(end=date(2026, 7, 20))))

    assert result.status == ProviderStatus.PARSE_ERROR


@pytest.mark.parametrize("schema_version", [True, "1", 2])
def test_fixture_schema_version_must_be_real_integer_one(schema_version):
    data = fixture_data()
    data["schema_version"] = schema_version
    provider = RecordedMarketSnapshotProvider(fixture_data=data)

    result = run(provider.fetch(supported_security(SAMSUNG)))

    assert result.status == ProviderStatus.PARSE_ERROR


def test_fixture_top_level_snapshots_required_fields_and_duplicates_are_validated():
    top_level = RecordedMarketSnapshotProvider(fixture_data=[])
    missing_snapshots = RecordedMarketSnapshotProvider(fixture_data={"schema_version": 1})
    missing_field_data = fixture_data()
    missing_field_data["snapshots"][0].pop("price")
    missing_field = RecordedMarketSnapshotProvider(fixture_data=missing_field_data)
    duplicate_data = fixture_data()
    duplicate_data["snapshots"].append(copy.deepcopy(duplicate_data["snapshots"][0]))
    duplicate = RecordedMarketSnapshotProvider(fixture_data=duplicate_data)

    for provider in [top_level, missing_snapshots, missing_field, duplicate]:
        result = run(provider.fetch(supported_security(SAMSUNG)))
        assert result.status == ProviderStatus.PARSE_ERROR
        assert_failure_is_sanitized(result)


def test_fixture_identity_drift_and_unknown_security_are_parse_errors():
    drift = RecordedMarketSnapshotProvider(fixture_data=fixture_with_update(0, security_name="wrong"))
    unknown_data = fixture_data()
    unknown_data["snapshots"][0].update(security_id="KRX:123456", ticker="123456")
    unknown = RecordedMarketSnapshotProvider(fixture_data=unknown_data)

    for provider in [drift, unknown]:
        result = run(provider.fetch(supported_security(SAMSUNG)))
        assert result.status == ProviderStatus.PARSE_ERROR
        assert_failure_is_sanitized(result)


def test_requested_unsupported_preferred_stock_and_wrong_identity_are_invalid_query():
    samsung = supported_security(SAMSUNG)
    sk_hynix = supported_security(SK_HYNIX)
    unsupported = SecurityIdentifier(
        market="KRX",
        ticker="123456",
        security_name=samsung.security_name,
        security_type="common_stock",
        corp_code=None,
        corp_name=samsung.corp_name,
    )
    preferred = SecurityIdentifier(
        market=samsung.market,
        ticker=samsung.ticker,
        security_name=samsung.security_name,
        security_type="preferred_stock",
        corp_code=None,
        corp_name=samsung.corp_name,
    )
    wrong_identity = SecurityIdentifier(
        market=samsung.market,
        ticker=samsung.ticker,
        security_name=sk_hynix.security_name,
        security_type=samsung.security_type,
        corp_code=None,
        corp_name=samsung.corp_name,
    )
    provider = RecordedMarketSnapshotProvider()

    for selected_security in [unsupported, preferred, wrong_identity]:
        result = run(provider.fetch(selected_security))
        assert result.status == ProviderStatus.INVALID_QUERY
        assert result.error_code == "invalid_query"
        assert_failure_is_sanitized(result)


@pytest.mark.parametrize(
    "updates",
    [
        {"price": True},
        {"price": "NaN"},
        {"price": "Infinity"},
        {"price": "not-a-number"},
        {"price": 0},
        {"previous_close": 0},
        {"change": 999},
        {"change_percent": 1.4},
        {"currency": "USD"},
    ],
)
def test_numeric_price_change_percent_and_currency_invariants(updates):
    provider = RecordedMarketSnapshotProvider(fixture_data=fixture_with_update(0, **updates))

    result = run(provider.fetch(supported_security(SAMSUNG), date_range=DateRange(end=date(2026, 7, 20))))

    assert result.status == ProviderStatus.PARSE_ERROR
    assert_failure_is_sanitized(result)


def test_volume_accepts_null_zero_positive_and_rejects_negative_bool_fractional():
    null_snapshot = fetch_snapshot(RecordedMarketSnapshotProvider(), HYUNDAI)
    zero_snapshot = fetch_snapshot(RecordedMarketSnapshotProvider(fixture_data=fixture_with_update(0, volume=0)), SAMSUNG, DateRange(end=date(2026, 7, 20)))
    positive_snapshot = fetch_snapshot(RecordedMarketSnapshotProvider(), SAMSUNG)

    assert null_snapshot.volume is None
    assert zero_snapshot.volume == 0
    assert positive_snapshot.volume == 1000000

    for value in [-1, True, 1.5]:
        provider = RecordedMarketSnapshotProvider(fixture_data=fixture_with_update(0, volume=value))
        result = run(provider.fetch(supported_security(SAMSUNG), date_range=DateRange(end=date(2026, 7, 20))))
        assert result.status == ProviderStatus.PARSE_ERROR


def test_timeout_missing_fixture_and_malformed_json_statuses_are_normalized(tmp_path):
    timeout = RecordedMarketSnapshotProvider(fixture_status=ProviderStatus.TIMEOUT)
    missing = RecordedMarketSnapshotProvider(fixture_path=tmp_path / "missing.json")
    malformed_path = tmp_path / "malformed.json"
    malformed_path.write_text("{", encoding="utf-8")
    malformed = RecordedMarketSnapshotProvider(fixture_path=malformed_path)

    timeout_result = run(timeout.fetch(supported_security(SAMSUNG)))
    missing_result = run(missing.fetch(supported_security(SAMSUNG)))
    malformed_result = run(malformed.fetch(supported_security(SAMSUNG)))

    assert timeout_result.status == ProviderStatus.TIMEOUT
    assert timeout_result.error_code == "attempt_timeout"
    assert missing_result.status == ProviderStatus.PROVIDER_UNAVAILABLE
    assert missing_result.error_code == "provider_unavailable"
    assert malformed_result.status == ProviderStatus.PARSE_ERROR
    assert malformed_result.error_code == "parse_error"
    for result in [timeout_result, missing_result, malformed_result]:
        assert_failure_is_sanitized(result)


def test_fixture_path_and_fixture_data_conflict_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        RecordedMarketSnapshotProvider(fixture_path=tmp_path / "fixture.json", fixture_data=fixture_data())


def test_fixture_data_is_copied_and_repeated_fetch_is_deterministic():
    data = fixture_data()
    provider = RecordedMarketSnapshotProvider(fixture_data=data)

    first = fetch_snapshot(provider, SAMSUNG)
    data["snapshots"][1]["price"] = 1
    second = fetch_snapshot(provider, SAMSUNG)

    assert first == second
    assert first.price == 71000


def test_provider_result_factory_and_fetch_with_policy_boundary():
    provider = RecordedMarketSnapshotProvider()
    config = ProviderConfig(timeout_seconds=1, retry_count=0, total_deadline_seconds=2, cache_ttl_seconds=0)

    result = run(fetch_with_policy(provider, security=supported_security(SAMSUNG), config=config))

    assert result.status == ProviderStatus.OK
    assert result.data is not None
    assert result.data.security_id == SAMSUNG
    assert result.error_code is None
