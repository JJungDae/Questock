from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Literal

from app.core.models import DateRange, MarketSnapshot, ProviderResult, SecurityIdentifier
from app.core.resolver import SecurityResolver
from app.core.status import ProviderStatus, ResolutionStatus
from app.providers.base import create_provider_result, normalize_query, security_id_for

RECORDED_MARKET_SNAPSHOT_PROVIDER_KEY = "recorded_market_snapshot"
DEFAULT_MARKET_FIXTURE_PATH = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "market" / "market_snapshot_synthetic.json"
DEFAULT_SECURITIES_PATH = Path(__file__).resolve().parents[2] / "data" / "securities.json"
PRICE_CHANGE_TOLERANCE = Decimal("0.000001")
PERCENT_TOLERANCE = Decimal("0.000001")
KST = timezone(timedelta(hours=9))
MARKET_SESSIONS = frozenset({"pre_market", "regular", "closing", "after_close", "closed"})
_REQUIRED_RECORD_FIELDS = frozenset(
    {
        "security_id",
        "market",
        "ticker",
        "security_name",
        "security_type",
        "trading_date",
        "observed_at",
        "price",
        "previous_close",
        "change",
        "change_percent",
        "volume",
        "market_session",
        "currency",
    }
)

MarketDirection = Literal["up", "down", "flat"]


class MarketSnapshotParseError(ValueError):
    """Raised when a recorded market snapshot fixture is malformed."""


@dataclass(frozen=True)
class ParsedMarketSnapshotRecord:
    security_id: str
    trading_date: date
    observed_at: datetime
    price: Decimal
    previous_close: Decimal
    change: Decimal
    change_percent: Decimal
    volume: int | None
    market_session: str
    currency: str


class RecordedMarketSnapshotProvider:
    key = RECORDED_MARKET_SNAPSHOT_PROVIDER_KEY

    def __init__(
        self,
        *,
        fixture_path: str | Path = DEFAULT_MARKET_FIXTURE_PATH,
        fixture_data: dict[str, Any] | None = None,
        fixture_status: ProviderStatus = ProviderStatus.OK,
        securities_path: str | Path = DEFAULT_SECURITIES_PATH,
        provider_key: str = RECORDED_MARKET_SNAPSHOT_PROVIDER_KEY,
    ) -> None:
        fixture_path_obj = Path(fixture_path)
        if fixture_data is not None and fixture_path_obj != DEFAULT_MARKET_FIXTURE_PATH:
            raise ValueError("fixture_path and fixture_data must not both be supplied")
        self.key = provider_key
        self._fixture_path = fixture_path_obj
        self._fixture_data = copy.deepcopy(fixture_data) if fixture_data is not None else None
        self._fixture_status = fixture_status
        self._securities_path = Path(securities_path)

    async def fetch(
        self,
        security: SecurityIdentifier,
        query: str | None = None,
        date_range: DateRange | None = None,
        attempt_timeout_seconds: float = 8,
    ) -> ProviderResult[MarketSnapshot]:
        canonical = self._canonical_security(security)
        if canonical is None or not _matches_requested_security(security, canonical):
            return create_provider_result(status=ProviderStatus.INVALID_QUERY, message="invalid security")
        if normalize_query(query):
            return create_provider_result(status=ProviderStatus.INVALID_QUERY, message="invalid query")

        if self._fixture_status != ProviderStatus.OK:
            return create_provider_result(status=self._fixture_status, message=self._fixture_status.value)

        try:
            fixture_data = self._load_fixture_data()
        except OSError:
            return create_provider_result(status=ProviderStatus.PROVIDER_UNAVAILABLE, message="fixture unavailable")
        except UnicodeDecodeError:
            return create_provider_result(status=ProviderStatus.PROVIDER_UNAVAILABLE, message="fixture unavailable")
        except json.JSONDecodeError:
            return create_provider_result(status=ProviderStatus.PARSE_ERROR, message="parse error")

        try:
            records = normalize_market_snapshot_fixture(
                fixture_data,
                provider_key=self.key,
                securities_path=self._securities_path,
            )
        except MarketSnapshotParseError:
            return create_provider_result(status=ProviderStatus.PARSE_ERROR, message="parse error")

        selected = select_market_snapshot(records, security_id=security_id_for(security), date_range=date_range)
        if selected is None:
            return create_provider_result(status=ProviderStatus.NO_DATA, message="no market snapshot data")
        return create_provider_result(status=ProviderStatus.OK, data=_to_market_snapshot(selected, provider_key=self.key))

    def _load_fixture_data(self) -> Any:
        if self._fixture_data is not None:
            return copy.deepcopy(self._fixture_data)
        return json.loads(self._fixture_path.read_text(encoding="utf-8"))

    def _canonical_security(self, security: SecurityIdentifier) -> SecurityIdentifier | None:
        try:
            resolution = SecurityResolver(fixture_path=self._securities_path).resolve(security_id_for(security))
        except (OSError, ValueError, json.JSONDecodeError):
            return None
        if resolution.status != ResolutionStatus.RESOLVED or resolution.security is None:
            return None
        return resolution.security


def normalize_market_snapshot_fixture(
    fixture_data: Any,
    *,
    provider_key: str,
    securities_path: str | Path = DEFAULT_SECURITIES_PATH,
) -> tuple[ParsedMarketSnapshotRecord, ...]:
    if not isinstance(fixture_data, dict):
        raise MarketSnapshotParseError("market snapshot fixture must be an object")
    schema_version = fixture_data.get("schema_version")
    if isinstance(schema_version, bool) or not isinstance(schema_version, int) or schema_version != 1:
        raise MarketSnapshotParseError("market snapshot schema_version must be 1")
    raw_snapshots = fixture_data.get("snapshots")
    if not isinstance(raw_snapshots, list):
        raise MarketSnapshotParseError("market snapshot snapshots must be a list")

    resolver = _load_resolver(securities_path)
    records: list[ParsedMarketSnapshotRecord] = []
    seen: set[tuple[str, str, str]] = set()
    for raw_record in raw_snapshots:
        record = _parse_record(raw_record, resolver=resolver)
        duplicate_key = (record.security_id, record.trading_date.isoformat(), record.observed_at.isoformat())
        if duplicate_key in seen:
            raise MarketSnapshotParseError("market snapshot records must not contain duplicates")
        seen.add(duplicate_key)
        records.append(record)

    return tuple(records)


def select_market_snapshot(
    records: tuple[ParsedMarketSnapshotRecord, ...],
    *,
    security_id: str,
    date_range: DateRange | None,
) -> ParsedMarketSnapshotRecord | None:
    candidates = [record for record in records if record.security_id == security_id]
    if date_range is not None:
        if date_range.start is not None:
            candidates = [record for record in candidates if record.trading_date >= date_range.start]
        if date_range.end is not None:
            candidates = [record for record in candidates if record.trading_date <= date_range.end]
    candidates.sort(key=lambda record: (record.trading_date, record.observed_at))
    if not candidates:
        return None
    return candidates[-1]


def market_snapshot_direction(snapshot: MarketSnapshot) -> MarketDirection:
    if snapshot.change > 0:
        return "up"
    if snapshot.change < 0:
        return "down"
    return "flat"


def _load_resolver(securities_path: str | Path) -> SecurityResolver:
    try:
        return SecurityResolver(fixture_path=securities_path)
    except Exception as exc:
        raise MarketSnapshotParseError("market security registry could not be loaded") from exc


def _parse_record(raw_record: Any, *, resolver: SecurityResolver) -> ParsedMarketSnapshotRecord:
    if not isinstance(raw_record, dict):
        raise MarketSnapshotParseError("market snapshot record must be an object")
    if not _REQUIRED_RECORD_FIELDS <= raw_record.keys():
        raise MarketSnapshotParseError("market snapshot record is missing required fields")

    security_id = _required_string(raw_record["security_id"])
    market = _required_string(raw_record["market"])
    ticker = _required_string(raw_record["ticker"])
    security_name = _required_string(raw_record["security_name"])
    security_type = _required_string(raw_record["security_type"])
    if security_id != f"{market}:{ticker}":
        raise MarketSnapshotParseError("market snapshot security_id must match market:ticker")

    canonical = _canonical_security_for_id(resolver, security_id)
    if canonical is None or not _matches_fixture_identity(
        market=market,
        ticker=ticker,
        security_name=security_name,
        security_type=security_type,
        canonical=canonical,
    ):
        raise MarketSnapshotParseError("market snapshot identity does not match canonical security")

    trading_date = _parse_date(raw_record["trading_date"])
    observed_at = _parse_observed_at(raw_record["observed_at"])
    if observed_at.astimezone(KST).date() != trading_date:
        raise MarketSnapshotParseError("market snapshot observed_at must match trading_date in KST")

    price = _parse_decimal(raw_record["price"])
    previous_close = _parse_decimal(raw_record["previous_close"])
    change = _parse_decimal(raw_record["change"])
    change_percent = _parse_decimal(raw_record["change_percent"])
    volume = _parse_volume(raw_record["volume"])
    market_session = _required_string(raw_record["market_session"])
    currency = _required_string(raw_record["currency"])

    if market_session not in MARKET_SESSIONS:
        raise MarketSnapshotParseError("market snapshot has invalid market_session")
    if currency != "KRW":
        raise MarketSnapshotParseError("market snapshot currency must be KRW")
    if price <= 0 or previous_close <= 0:
        raise MarketSnapshotParseError("market snapshot price values must be positive")
    if abs(change - (price - previous_close)) > PRICE_CHANGE_TOLERANCE:
        raise MarketSnapshotParseError("market snapshot change invariant failed")
    expected_percent = (change / previous_close) * Decimal("100")
    if abs(change_percent - expected_percent) > PERCENT_TOLERANCE:
        raise MarketSnapshotParseError("market snapshot change_percent invariant failed")

    return ParsedMarketSnapshotRecord(
        security_id=security_id,
        trading_date=trading_date,
        observed_at=observed_at,
        price=price,
        previous_close=previous_close,
        change=change,
        change_percent=change_percent,
        volume=volume,
        market_session=market_session,
        currency=currency,
    )


def _canonical_security_for_id(resolver: SecurityResolver, security_id: str) -> SecurityIdentifier | None:
    resolution = resolver.resolve(security_id)
    if resolution.status != ResolutionStatus.RESOLVED or resolution.security is None:
        return None
    return resolution.security


def _matches_requested_security(security: SecurityIdentifier, canonical: SecurityIdentifier) -> bool:
    return (
        security.market == canonical.market
        and security.ticker == canonical.ticker
        and security.security_name == canonical.security_name
        and security.security_type == canonical.security_type
        and security.security_type == "common_stock"
    )


def _matches_fixture_identity(
    *,
    market: str,
    ticker: str,
    security_name: str,
    security_type: str,
    canonical: SecurityIdentifier,
) -> bool:
    return (
        market == canonical.market
        and ticker == canonical.ticker
        and security_name == canonical.security_name
        and security_type == canonical.security_type
        and security_type == "common_stock"
    )


def _required_string(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise MarketSnapshotParseError("market snapshot field must be a non-empty string")
    return value


def _parse_date(value: Any) -> date:
    if not isinstance(value, str):
        raise MarketSnapshotParseError("market snapshot date must be a string")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise MarketSnapshotParseError("market snapshot date must be ISO formatted") from None


def _parse_observed_at(value: Any) -> datetime:
    if not isinstance(value, str):
        raise MarketSnapshotParseError("market snapshot observed_at must be a string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise MarketSnapshotParseError("market snapshot observed_at must be ISO formatted") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise MarketSnapshotParseError("market snapshot observed_at must be timezone-aware")
    return parsed.astimezone(UTC)


def _parse_decimal(value: Any) -> Decimal:
    if isinstance(value, bool):
        raise MarketSnapshotParseError("market snapshot numeric fields must not be bool")
    if not isinstance(value, (int, float, str)):
        raise MarketSnapshotParseError("market snapshot numeric field has invalid type")
    try:
        parsed = Decimal(str(value))
    except InvalidOperation:
        raise MarketSnapshotParseError("market snapshot numeric field must be decimal") from None
    if not parsed.is_finite():
        raise MarketSnapshotParseError("market snapshot numeric field must be finite")
    return parsed


def _parse_volume(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise MarketSnapshotParseError("market snapshot volume must be an integer or null")
    if value < 0:
        raise MarketSnapshotParseError("market snapshot volume must be non-negative")
    return value


def _to_market_snapshot(record: ParsedMarketSnapshotRecord, *, provider_key: str) -> MarketSnapshot:
    return MarketSnapshot(
        security_id=record.security_id,
        trading_date=record.trading_date,
        observed_at=record.observed_at,
        price=float(record.price),
        previous_close=float(record.previous_close),
        change=float(record.change),
        change_percent=float(record.change_percent),
        volume=record.volume,
        market_session=record.market_session,
        currency=record.currency,
        source=provider_key,
    )


__all__ = [
    "DEFAULT_MARKET_FIXTURE_PATH",
    "DEFAULT_SECURITIES_PATH",
    "KST",
    "MARKET_SESSIONS",
    "PERCENT_TOLERANCE",
    "PRICE_CHANGE_TOLERANCE",
    "RECORDED_MARKET_SNAPSHOT_PROVIDER_KEY",
    "MarketSnapshotParseError",
    "RecordedMarketSnapshotProvider",
    "market_snapshot_direction",
    "normalize_market_snapshot_fixture",
    "select_market_snapshot",
]
