from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Literal

MARKET_SNAPSHOT_SCHEMA_VERSION = "m5-market-snapshot-v1"
MARKET_SNAPSHOT_TYPE = "questock_recorded_market_checkpoints"
MARKET_SNAPSHOT_SOURCE = "kis_open_api_historical_minute"
MARKET_CODE = "UN"
KST = timezone(timedelta(hours=9))

CHECKPOINT_DATES = (
    date(2026, 7, 24),
    date(2026, 7, 25),
    date(2026, 7, 26),
    date(2026, 7, 27),
)
CHECKPOINT_TIMES = (
    time(8, 30),
    time(10, 0),
    time(14, 0),
    time(19, 0),
    time(21, 0),
)
TRADING_DATES = frozenset({date(2026, 7, 24), date(2026, 7, 27)})
SECURITIES = (
    ("KRX:005930", "005930", "삼성전자"),
    ("KRX:000660", "000660", "SK하이닉스"),
    ("KRX:005380", "005380", "현대자동차"),
)
PREVIOUS_TRADING_DATE = {
    date(2026, 7, 24): date(2026, 7, 23),
    date(2026, 7, 27): date(2026, 7, 24),
}

MarketStatus = Literal["open", "closed", "no_trade_yet", "no_data"]
MarketSession = Literal[
    "pre_market",
    "regular",
    "after_market",
    "after_close",
    "closed",
]


class MarketSnapshotValidationError(ValueError):
    """Raised when an M5 recorded market snapshot is malformed."""


@dataclass(frozen=True)
class MinuteBar:
    observed_at: datetime
    price: Decimal
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    minute_volume: int


def checkpoint_id(value: datetime) -> str:
    canonical = _aware_kst(value)
    return canonical.strftime("%Y%m%dT%H%MKST")


def checkpoint_matrix() -> tuple[datetime, ...]:
    return tuple(
        datetime.combine(day, checkpoint_time, tzinfo=KST)
        for day in CHECKPOINT_DATES
        for checkpoint_time in CHECKPOINT_TIMES
    )


def parse_kis_minute_rows(
    rows: object,
) -> tuple[MinuteBar, ...]:
    if not isinstance(rows, Sequence) or isinstance(
        rows,
        (str, bytes, bytearray),
    ):
        raise MarketSnapshotValidationError(
            "KIS minute rows must be a sequence"
        )
    output: list[MinuteBar] = []
    seen: set[datetime] = set()
    for raw in rows:
        if not isinstance(raw, Mapping):
            raise MarketSnapshotValidationError(
                "KIS minute row must be an object"
            )
        try:
            observed_at = datetime.strptime(
                f"{raw['stck_bsop_date']}{raw['stck_cntg_hour']}",
                "%Y%m%d%H%M%S",
            ).replace(tzinfo=KST)
            item = MinuteBar(
                observed_at=observed_at,
                price=_positive_decimal(raw["stck_prpr"]),
                open_price=_positive_decimal(raw["stck_oprc"]),
                high_price=_positive_decimal(raw["stck_hgpr"]),
                low_price=_positive_decimal(raw["stck_lwpr"]),
                minute_volume=_non_negative_int(raw["cntg_vol"]),
            )
        except (KeyError, TypeError, ValueError):
            raise MarketSnapshotValidationError(
                "KIS minute row is invalid"
            ) from None
        if item.observed_at in seen:
            raise MarketSnapshotValidationError(
                "KIS minute rows contain duplicates"
            )
        if not (
            item.low_price
            <= min(item.open_price, item.price)
            <= max(item.open_price, item.price)
            <= item.high_price
        ):
            raise MarketSnapshotValidationError(
                "KIS minute price range is invalid"
            )
        seen.add(item.observed_at)
        output.append(item)
    return tuple(sorted(output, key=lambda item: item.observed_at))


def select_latest_bar(
    rows: Sequence[MinuteBar],
    *,
    as_of: datetime,
) -> MinuteBar | None:
    canonical_as_of = _aware_kst(as_of)
    eligible = [
        item
        for item in rows
        if isinstance(item, MinuteBar)
        and item.observed_at <= canonical_as_of
    ]
    return max(eligible, key=lambda item: item.observed_at, default=None)


def build_snapshot_record(
    *,
    security_id: str,
    ticker: str,
    security_name: str,
    requested_as_of: datetime,
    observed: MinuteBar,
    previous_close: Decimal,
    market_code: str = MARKET_CODE,
) -> dict[str, object]:
    canonical_as_of = _aware_kst(requested_as_of)
    if (
        (security_id, ticker, security_name) not in SECURITIES
        or not isinstance(observed, MinuteBar)
        or observed.observed_at > canonical_as_of
        or market_code not in {"J", "NX", "UN"}
    ):
        raise MarketSnapshotValidationError(
            "market snapshot record input is invalid"
        )
    prior = _positive_decimal(previous_close)
    change = observed.price - prior
    percent = (change / prior * Decimal("100")).quantize(
        Decimal("0.000001")
    )
    market_status: MarketStatus
    if canonical_as_of.date() not in TRADING_DATES:
        market_status = "closed"
    elif canonical_as_of.time() >= time(20, 0):
        market_status = "closed"
    else:
        market_status = "open"
    return {
        "security_id": security_id,
        "market": "KRX",
        "ticker": ticker,
        "security_name": security_name,
        "security_type": "common_stock",
        "checkpoint_id": checkpoint_id(canonical_as_of),
        "requested_as_of": canonical_as_of.isoformat(),
        "trading_date": observed.observed_at.date().isoformat(),
        "observed_at": observed.observed_at.isoformat(),
        "price": _number(observed.price),
        "previous_close": _number(prior),
        "change": _number(change),
        "change_percent": _number(percent),
        "volume": None,
        "market_code": market_code,
        "market_session": _market_session(canonical_as_of),
        "market_status": market_status,
        "currency": "KRW",
        "source": MARKET_SNAPSHOT_SOURCE,
    }


def build_snapshot_payload(
    records: Sequence[Mapping[str, object]],
    *,
    collected_at: datetime,
) -> dict[str, object]:
    canonical_records = [
        _validate_snapshot_record(dict(record))
        for record in records
    ]
    expected_count = (
        len(SECURITIES) * len(CHECKPOINT_DATES) * len(CHECKPOINT_TIMES)
    )
    if len(canonical_records) != expected_count:
        raise MarketSnapshotValidationError(
            "market snapshot matrix is incomplete"
        )
    identities = {
        (item["security_id"], item["checkpoint_id"])
        for item in canonical_records
    }
    if len(identities) != expected_count:
        raise MarketSnapshotValidationError(
            "market snapshot matrix contains duplicates"
        )
    canonical_records.sort(
        key=lambda item: (
            str(item["security_id"]),
            str(item["checkpoint_id"]),
        )
    )
    collected = _aware_utc(collected_at)
    payload: dict[str, object] = {
        "snapshot_type": MARKET_SNAPSHOT_TYPE,
        "schema_version": MARKET_SNAPSHOT_SCHEMA_VERSION,
        "collected_at": collected.isoformat().replace("+00:00", "Z"),
        "source": {
            "provider": "Korea Investment & Securities Open API",
            "interface": "inquire-time-dailychartprice",
            "tr_id": "FHKST03010230",
            "market_code": MARKET_CODE,
            "raw_responses_committed": False,
        },
        "snapshots": canonical_records,
    }
    payload["records_sha256"] = hashlib.sha256(
        json.dumps(
            canonical_records,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return payload


def validate_snapshot_payload(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise MarketSnapshotValidationError(
            "market snapshot payload must be an object"
        )
    payload = dict(value)
    if (
        payload.get("snapshot_type") != MARKET_SNAPSHOT_TYPE
        or payload.get("schema_version")
        != MARKET_SNAPSHOT_SCHEMA_VERSION
        or not isinstance(payload.get("snapshots"), list)
    ):
        raise MarketSnapshotValidationError(
            "market snapshot payload header is invalid"
        )
    collected_at = payload.get("collected_at")
    if not isinstance(collected_at, str):
        raise MarketSnapshotValidationError(
            "market snapshot collected_at is invalid"
        )
    try:
        _aware_utc(datetime.fromisoformat(collected_at.replace("Z", "+00:00")))
    except ValueError:
        raise MarketSnapshotValidationError(
            "market snapshot collected_at is invalid"
        ) from None
    canonical = build_snapshot_payload(
        payload["snapshots"],
        collected_at=datetime.fromisoformat(
            collected_at.replace("Z", "+00:00")
        ),
    )
    if payload.get("source") != canonical["source"]:
        raise MarketSnapshotValidationError(
            "market snapshot source metadata is invalid"
        )
    if payload.get("records_sha256") != canonical["records_sha256"]:
        raise MarketSnapshotValidationError(
            "market snapshot checksum is invalid"
        )
    return canonical


def _validate_snapshot_record(
    value: dict[str, object],
) -> dict[str, object]:
    required = {
        "security_id",
        "market",
        "ticker",
        "security_name",
        "security_type",
        "checkpoint_id",
        "requested_as_of",
        "trading_date",
        "observed_at",
        "price",
        "previous_close",
        "change",
        "change_percent",
        "volume",
        "market_code",
        "market_session",
        "market_status",
        "currency",
        "source",
    }
    if set(value) != required:
        raise MarketSnapshotValidationError(
            "market snapshot record fields are invalid"
        )
    identity = (
        value["security_id"],
        value["ticker"],
        value["security_name"],
    )
    if (
        identity not in SECURITIES
        or value["market"] != "KRX"
        or value["security_type"] != "common_stock"
        or value["market_code"] not in {"J", "NX", "UN"}
        or value["market_status"]
        not in {"open", "closed", "no_trade_yet", "no_data"}
        or value["market_session"]
        not in {
            "pre_market",
            "regular",
            "after_market",
            "after_close",
            "closed",
        }
        or value["currency"] != "KRW"
        or value["source"] != MARKET_SNAPSHOT_SOURCE
        or value["volume"] is not None
    ):
        raise MarketSnapshotValidationError(
            "market snapshot record metadata is invalid"
        )
    requested = _parse_timestamp(value["requested_as_of"])
    observed = _parse_timestamp(value["observed_at"])
    if (
        value["checkpoint_id"] != checkpoint_id(requested)
        or requested not in checkpoint_matrix()
        or observed > requested
        or value["trading_date"] != observed.date().isoformat()
    ):
        raise MarketSnapshotValidationError(
            "market snapshot record time is invalid"
        )
    price = _positive_decimal(value["price"])
    previous_close = _positive_decimal(value["previous_close"])
    change = _decimal(value["change"])
    percent = _decimal(value["change_percent"])
    if change != price - previous_close:
        raise MarketSnapshotValidationError(
            "market snapshot change is invalid"
        )
    expected_percent = (change / previous_close * Decimal("100")).quantize(
        Decimal("0.000001")
    )
    if percent != expected_percent:
        raise MarketSnapshotValidationError(
            "market snapshot percent is invalid"
        )
    return value


def _market_session(value: datetime) -> MarketSession:
    if value.date() not in TRADING_DATES:
        return "closed"
    current = value.time()
    if current <= time(8, 50):
        return "pre_market"
    if current <= time(15, 20):
        return "regular"
    if current <= time(20, 0):
        return "after_market"
    return "after_close"


def _parse_timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise MarketSnapshotValidationError(
            "market snapshot timestamp is invalid"
        )
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise MarketSnapshotValidationError(
            "market snapshot timestamp is invalid"
        ) from None
    return _aware_kst(parsed)


def _aware_kst(value: datetime) -> datetime:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise MarketSnapshotValidationError(
            "timestamp must be timezone-aware"
        )
    return value.astimezone(KST)


def _aware_utc(value: datetime) -> datetime:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise MarketSnapshotValidationError(
            "timestamp must be timezone-aware"
        )
    return value.astimezone(UTC)


def _decimal(value: object) -> Decimal:
    if isinstance(value, bool) or not isinstance(
        value,
        (str, int, float, Decimal),
    ):
        raise MarketSnapshotValidationError(
            "market snapshot number is invalid"
        )
    try:
        parsed = Decimal(str(value))
    except InvalidOperation:
        raise MarketSnapshotValidationError(
            "market snapshot number is invalid"
        ) from None
    if not parsed.is_finite():
        raise MarketSnapshotValidationError(
            "market snapshot number is invalid"
        )
    return parsed


def _positive_decimal(value: object) -> Decimal:
    parsed = _decimal(value)
    if parsed <= 0:
        raise MarketSnapshotValidationError(
            "market snapshot positive number is invalid"
        )
    return parsed


def _non_negative_int(value: object) -> int:
    if isinstance(value, bool):
        raise MarketSnapshotValidationError(
            "market snapshot volume is invalid"
        )
    try:
        parsed = int(str(value))
    except (TypeError, ValueError):
        raise MarketSnapshotValidationError(
            "market snapshot volume is invalid"
        ) from None
    if parsed < 0:
        raise MarketSnapshotValidationError(
            "market snapshot volume is invalid"
        )
    return parsed


def _number(value: Decimal) -> int | float:
    integral = value.to_integral_value()
    if value == integral:
        return int(integral)
    return float(value)


__all__ = [
    "CHECKPOINT_DATES",
    "CHECKPOINT_TIMES",
    "KST",
    "MARKET_CODE",
    "MARKET_SNAPSHOT_SCHEMA_VERSION",
    "MARKET_SNAPSHOT_SOURCE",
    "MARKET_SNAPSHOT_TYPE",
    "PREVIOUS_TRADING_DATE",
    "SECURITIES",
    "TRADING_DATES",
    "MarketSnapshotValidationError",
    "MinuteBar",
    "build_snapshot_payload",
    "build_snapshot_record",
    "checkpoint_id",
    "checkpoint_matrix",
    "parse_kis_minute_rows",
    "select_latest_bar",
    "validate_snapshot_payload",
]
