from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.models import MarketSnapshot
from app.services.market_snapshot_schema import (
    MarketSnapshotValidationError,
    checkpoint_id,
    validate_snapshot_payload,
)

DEFAULT_MARKET_SNAPSHOT_PATH = Path("data/market_snapshots_m5.json")


class MarketSnapshotStoreError(RuntimeError):
    """Raised when the recorded checkpoint store cannot be used safely."""


class RecordedMarketSnapshotStore:
    def __init__(
        self,
        path: Path = DEFAULT_MARKET_SNAPSHOT_PATH,
        *,
        payload: dict[str, Any] | None = None,
    ) -> None:
        if payload is not None and path != DEFAULT_MARKET_SNAPSHOT_PATH:
            raise MarketSnapshotStoreError(
                "market snapshot store input is invalid"
            )
        try:
            raw = (
                payload
                if payload is not None
                else json.loads(path.read_text(encoding="utf-8"))
            )
            validated = validate_snapshot_payload(raw)
        except (
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            MarketSnapshotValidationError,
        ):
            raise MarketSnapshotStoreError(
                "market snapshot store is unavailable"
            ) from None
        raw_snapshots = validated["snapshots"]
        if not isinstance(raw_snapshots, list):
            raise MarketSnapshotStoreError(
                "market snapshot store is unavailable"
            )
        self._snapshots = {
            (str(item["security_id"]), str(item["checkpoint_id"])): (
                _to_market_snapshot(item)
            )
            for item in raw_snapshots
        }

    def get(
        self,
        *,
        security_id: str,
        as_of: datetime,
    ) -> MarketSnapshot | None:
        try:
            key = (security_id, checkpoint_id(as_of))
        except MarketSnapshotValidationError:
            raise MarketSnapshotStoreError(
                "market snapshot request is invalid"
            ) from None
        snapshot = self._snapshots.get(key)
        return (
            None
            if snapshot is None
            else snapshot.model_copy(deep=True)
        )


def _to_market_snapshot(value: dict[str, object]) -> MarketSnapshot:
    try:
        return MarketSnapshot(
            security_id=value["security_id"],
            trading_date=value["trading_date"],
            observed_at=value["observed_at"],
            price=value["price"],
            previous_close=value["previous_close"],
            change=value["change"],
            change_percent=value["change_percent"],
            volume=value["volume"],
            market_session=value["market_session"],
            currency=value["currency"],
            source=value["source"],
            checkpoint_id=value["checkpoint_id"],
            requested_as_of=value["requested_as_of"],
            market_code=value["market_code"],
            market_status=value["market_status"],
        )
    except (TypeError, ValueError):
        raise MarketSnapshotStoreError(
            "market snapshot record is invalid"
        ) from None


__all__ = [
    "DEFAULT_MARKET_SNAPSHOT_PATH",
    "MarketSnapshotStoreError",
    "RecordedMarketSnapshotStore",
]
