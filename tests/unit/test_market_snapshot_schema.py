from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.services.market_snapshot_schema import (
    CHECKPOINT_DATES,
    KST,
    SECURITIES,
    MarketSnapshotValidationError,
    MinuteBar,
    build_snapshot_payload,
    build_snapshot_record,
    checkpoint_matrix,
    parse_kis_minute_rows,
    select_latest_bar,
    validate_snapshot_payload,
)


def minute_row(
    *,
    day: str = "20260724",
    observed_time: str = "083000",
    price: str = "101000",
) -> dict[str, str]:
    return {
        "stck_bsop_date": day,
        "stck_cntg_hour": observed_time,
        "stck_prpr": price,
        "stck_oprc": "100000",
        "stck_hgpr": "102000",
        "stck_lwpr": "99000",
        "cntg_vol": "123",
    }


def test_parse_and_select_latest_bar_never_crosses_as_of() -> None:
    rows = parse_kis_minute_rows(
        [
            minute_row(observed_time="082900", price="100000"),
            minute_row(observed_time="083000", price="101000"),
            minute_row(observed_time="083100", price="102000"),
        ]
    )

    selected = select_latest_bar(
        rows,
        as_of=datetime(2026, 7, 24, 8, 30, tzinfo=KST),
    )

    assert selected is not None
    assert selected.observed_at == datetime(
        2026,
        7,
        24,
        8,
        30,
        tzinfo=KST,
    )
    assert selected.price == Decimal("101000")


def test_snapshot_record_keeps_weekend_observation_time() -> None:
    observed = MinuteBar(
        observed_at=datetime(2026, 7, 24, 19, 59, tzinfo=KST),
        price=Decimal("102000"),
        open_price=Decimal("102000"),
        high_price=Decimal("102000"),
        low_price=Decimal("102000"),
        minute_volume=10,
    )

    record = build_snapshot_record(
        security_id="KRX:005930",
        ticker="005930",
        security_name="삼성전자",
        requested_as_of=datetime(2026, 7, 25, 8, 30, tzinfo=KST),
        observed=observed,
        previous_close=Decimal("100000"),
    )

    assert record["market_status"] == "closed"
    assert record["market_session"] == "closed"
    assert record["requested_as_of"] == "2026-07-25T08:30:00+09:00"
    assert record["observed_at"] == "2026-07-24T19:59:00+09:00"
    assert record["change"] == 2000
    assert record["change_percent"] == 2


def test_snapshot_record_rejects_future_observation() -> None:
    observed = MinuteBar(
        observed_at=datetime(2026, 7, 24, 8, 31, tzinfo=KST),
        price=Decimal("100000"),
        open_price=Decimal("100000"),
        high_price=Decimal("100000"),
        low_price=Decimal("100000"),
        minute_volume=1,
    )

    with pytest.raises(MarketSnapshotValidationError):
        build_snapshot_record(
            security_id="KRX:005930",
            ticker="005930",
            security_name="삼성전자",
            requested_as_of=datetime(
                2026,
                7,
                24,
                8,
                30,
                tzinfo=KST,
            ),
            observed=observed,
            previous_close=Decimal("99000"),
        )


def test_full_sixty_case_payload_is_deterministic_and_valid() -> None:
    records = []
    for security_id, ticker, security_name in SECURITIES:
        for requested_as_of in checkpoint_matrix():
            observed_day = (
                date(2026, 7, 24)
                if requested_as_of.date()
                in {date(2026, 7, 25), date(2026, 7, 26)}
                else requested_as_of.date()
            )
            observed = MinuteBar(
                observed_at=datetime.combine(
                    observed_day,
                    (
                        requested_as_of.time()
                        if requested_as_of.hour < 20
                        else datetime.strptime("19:59", "%H:%M").time()
                    ),
                    tzinfo=KST,
                ),
                price=Decimal("101000"),
                open_price=Decimal("101000"),
                high_price=Decimal("101000"),
                low_price=Decimal("101000"),
                minute_volume=1,
            )
            records.append(
                build_snapshot_record(
                    security_id=security_id,
                    ticker=ticker,
                    security_name=security_name,
                    requested_as_of=requested_as_of,
                    observed=observed,
                    previous_close=Decimal("100000"),
                )
            )

    payload = build_snapshot_payload(
        records,
        collected_at=datetime(2026, 7, 28, 1, 0, tzinfo=UTC),
    )
    validated = validate_snapshot_payload(payload)

    assert len(validated["snapshots"]) == 60
    assert len(
        {
            item["checkpoint_id"]
            for item in validated["snapshots"]
        }
    ) == len(CHECKPOINT_DATES) * 5
    assert (
        build_snapshot_payload(
            list(reversed(records)),
            collected_at=datetime(2026, 7, 28, 1, 0, tzinfo=UTC),
        )["records_sha256"]
        == payload["records_sha256"]
    )
