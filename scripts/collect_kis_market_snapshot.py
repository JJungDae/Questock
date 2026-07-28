from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time as time_module
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from datetime import UTC, date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.services.market_snapshot_schema import (
    CHECKPOINT_DATES,
    CHECKPOINT_TIMES,
    KST,
    MARKET_CODE,
    PREVIOUS_TRADING_DATE,
    SECURITIES,
    TRADING_DATES,
    MarketSnapshotValidationError,
    MinuteBar,
    build_snapshot_payload,
    build_snapshot_record,
    parse_kis_minute_rows,
    select_latest_bar,
    validate_snapshot_payload,
)

TOKEN_ENDPOINT = (
    "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
)
MINUTE_ENDPOINT = (
    "https://openapi.koreainvestment.com:9443"
    "/uapi/domestic-stock/v1/quotations/"
    "inquire-time-dailychartprice"
)
TR_ID = "FHKST03010230"
DEFAULT_OUTPUT_PATH = Path("data/market_snapshots_m5.json")
DEFAULT_RAW_DIR = Path("var/service_completion/raw/market/m5")
DEFAULT_TIMEOUT_SECONDS = 15.0
DEFAULT_REQUEST_INTERVAL_SECONDS = 0.25


class KisCollectionError(RuntimeError):
    """Raised when the bounded KIS market collection cannot complete."""


class KisHistoricalMinuteTransport:
    def __init__(
        self,
        *,
        app_key: str,
        app_secret: str,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        request_interval_seconds: float = (
            DEFAULT_REQUEST_INTERVAL_SECONDS
        ),
        token_cache_path: Path | None = None,
    ) -> None:
        if (
            not isinstance(app_key, str)
            or not app_key
            or not isinstance(app_secret, str)
            or not app_secret
            or timeout_seconds <= 0
            or request_interval_seconds < 0
        ):
            raise KisCollectionError(
                "KIS collection configuration is invalid"
            )
        self._app_key = app_key
        self._app_secret = app_secret
        self._timeout_seconds = float(timeout_seconds)
        self._request_interval_seconds = float(
            request_interval_seconds
        )
        self._token_cache_path = token_cache_path
        self._access_token: str | None = None

    def authenticate(self) -> None:
        cached = self._load_cached_token()
        if cached is not None:
            self._access_token = cached
            return
        payload = json.dumps(
            {
                "grant_type": "client_credentials",
                "appkey": self._app_key,
                "appsecret": self._app_secret,
            },
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode("utf-8")
        request = urllib.request.Request(
            TOKEN_ENDPOINT,
            data=payload,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": "Questock-M5-Market-Collector/1.0",
            },
            method="POST",
        )
        response = _open_json(
            request,
            timeout_seconds=self._timeout_seconds,
        )
        token = response.get("access_token")
        if not isinstance(token, str) or not token:
            raise KisCollectionError(
                "KIS authentication response is invalid"
            )
        self._access_token = token
        self._save_cached_token(token, response)

    def fetch(
        self,
        *,
        ticker: str,
        requested_date: date,
        requested_time: time,
        market_code: str,
    ) -> dict[str, Any]:
        if self._access_token is None:
            raise KisCollectionError(
                "KIS collection transport is not authenticated"
            )
        query = urllib.parse.urlencode(
            {
                "FID_COND_MRKT_DIV_CODE": market_code,
                "FID_INPUT_ISCD": ticker,
                "FID_INPUT_HOUR_1": requested_time.strftime("%H%M%S"),
                "FID_INPUT_DATE_1": requested_date.strftime("%Y%m%d"),
                "FID_PW_DATA_INCU_YN": "N",
                "FID_FAKE_TICK_INCU_YN": "",
            }
        )
        request = urllib.request.Request(
            f"{MINUTE_ENDPOINT}?{query}",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self._access_token}",
                "appkey": self._app_key,
                "appsecret": self._app_secret,
                "tr_id": TR_ID,
                "custtype": "P",
                "User-Agent": "Questock-M5-Market-Collector/1.0",
            },
            method="GET",
        )
        if self._request_interval_seconds:
            time_module.sleep(self._request_interval_seconds)
        response: dict[str, Any] | None = None
        for attempt in range(3):
            try:
                response = _open_json(
                    request,
                    timeout_seconds=self._timeout_seconds,
                )
                break
            except KisCollectionError:
                if attempt >= 2:
                    raise
                time_module.sleep(0.5 * (attempt + 1))
        if response is None:
            raise KisCollectionError(
                "KIS historical minute response is unavailable"
            )
        if response.get("rt_cd") != "0":
            message_code = response.get("msg_cd")
            safe_code = (
                message_code
                if isinstance(message_code, str)
                and message_code.isalnum()
                and len(message_code) <= 32
                else "unknown"
            )
            raise KisCollectionError(
                "KIS historical minute request failed "
                f"with code {safe_code}"
            )
        if not isinstance(response.get("output2"), list):
            raise KisCollectionError(
                "KIS historical minute response is invalid"
            )
        return response

    def _load_cached_token(self) -> str | None:
        path = self._token_cache_path
        if path is None or not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        token = payload.get("access_token")
        expires_at = payload.get("expires_at")
        app_key_hash = payload.get("app_key_sha256")
        if (
            not isinstance(token, str)
            or not token
            or not isinstance(expires_at, (int, float))
            or expires_at <= time_module.time() + 60
            or app_key_hash
            != hashlib.sha256(
                self._app_key.encode("utf-8")
            ).hexdigest()
        ):
            return None
        return token

    def _save_cached_token(
        self,
        token: str,
        response: Mapping[str, Any],
    ) -> None:
        path = self._token_cache_path
        if path is None:
            return
        raw_expires_in = response.get("expires_in")
        try:
            expires_in = int(str(raw_expires_in))
        except (TypeError, ValueError):
            expires_in = 60 * 60 * 23
        if expires_in <= 60:
            expires_in = 60 * 60 * 23
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "access_token": token,
                    "expires_at": time_module.time() + expires_in,
                    "app_key_sha256": hashlib.sha256(
                        self._app_key.encode("utf-8")
                    ).hexdigest(),
                },
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ),
            encoding="utf-8",
        )


def collect_market_snapshot(
    *,
    transport: KisHistoricalMinuteTransport,
    raw_dir: Path,
    collected_at: datetime | None = None,
) -> dict[str, object]:
    if not isinstance(raw_dir, Path):
        raise KisCollectionError("KIS raw output path is invalid")
    raw_dir.mkdir(parents=True, exist_ok=True)
    transport.authenticate()
    records: list[dict[str, object]] = []
    previous_closes: dict[tuple[str, date], Decimal] = {}
    last_friday_bar: dict[str, MinuteBar] = {}

    for security_id, ticker, security_name in SECURITIES:
        for trading_day in sorted(TRADING_DATES):
            previous_day = PREVIOUS_TRADING_DATE[trading_day]
            previous_response = transport.fetch(
                ticker=ticker,
                requested_date=previous_day,
                requested_time=time(15, 30),
                market_code="J",
            )
            _write_raw_response(
                raw_dir,
                ticker=ticker,
                requested_date=previous_day,
                requested_time=time(15, 30),
                market_code="J",
                payload=previous_response,
            )
            previous_rows = parse_kis_minute_rows(
                previous_response["output2"]
            )
            previous_bar = select_latest_bar(
                previous_rows,
                as_of=datetime.combine(
                    previous_day,
                    time(15, 30),
                    tzinfo=KST,
                ),
            )
            if (
                previous_bar is None
                or previous_bar.observed_at.date() != previous_day
            ):
                raise KisCollectionError(
                    "KIS previous close observation is unavailable"
                )
            previous_closes[(ticker, trading_day)] = previous_bar.price

        for checkpoint_day in CHECKPOINT_DATES:
            if checkpoint_day not in TRADING_DATES:
                friday_bar = last_friday_bar.get(ticker)
                if friday_bar is None:
                    raise KisCollectionError(
                        "KIS closed-market fallback is unavailable"
                    )
                for checkpoint_time in CHECKPOINT_TIMES:
                    requested_as_of = datetime.combine(
                        checkpoint_day,
                        checkpoint_time,
                        tzinfo=KST,
                    )
                    records.append(
                        build_snapshot_record(
                            security_id=security_id,
                            ticker=ticker,
                            security_name=security_name,
                            requested_as_of=requested_as_of,
                            observed=friday_bar,
                            previous_close=previous_closes[
                                (ticker, date(2026, 7, 24))
                            ],
                        )
                    )
                continue

            for checkpoint_time in CHECKPOINT_TIMES:
                requested_as_of = datetime.combine(
                    checkpoint_day,
                    checkpoint_time,
                    tzinfo=KST,
                )
                response = transport.fetch(
                    ticker=ticker,
                    requested_date=checkpoint_day,
                    requested_time=checkpoint_time,
                    market_code=MARKET_CODE,
                )
                _write_raw_response(
                    raw_dir,
                    ticker=ticker,
                    requested_date=checkpoint_day,
                    requested_time=checkpoint_time,
                    market_code=MARKET_CODE,
                    payload=response,
                )
                rows = parse_kis_minute_rows(response["output2"])
                observed = select_latest_bar(
                    rows,
                    as_of=requested_as_of,
                )
                if (
                    observed is None
                    or observed.observed_at.date() != checkpoint_day
                ):
                    raise KisCollectionError(
                        "KIS checkpoint observation is unavailable"
                    )
                records.append(
                    build_snapshot_record(
                        security_id=security_id,
                        ticker=ticker,
                        security_name=security_name,
                        requested_as_of=requested_as_of,
                        observed=observed,
                        previous_close=previous_closes[
                            (ticker, checkpoint_day)
                        ],
                    )
                )
                if (
                    checkpoint_day == date(2026, 7, 24)
                    and checkpoint_time == time(21, 0)
                ):
                    last_friday_bar[ticker] = observed

    payload = build_snapshot_payload(
        records,
        collected_at=collected_at or datetime.now(UTC),
    )
    validate_snapshot_payload(payload)
    return payload


def _write_raw_response(
    raw_dir: Path,
    *,
    ticker: str,
    requested_date: date,
    requested_time: time,
    market_code: str,
    payload: Mapping[str, Any],
) -> None:
    filename = (
        f"{ticker}-{requested_date:%Y%m%d}-"
        f"{requested_time:%H%M%S}-{market_code}.json"
    )
    (raw_dir / filename).write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _open_json(
    request: urllib.request.Request,
    *,
    timeout_seconds: float,
) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout_seconds,
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise KisCollectionError(
            f"KIS request failed with HTTP {exc.code}"
        ) from None
    except (urllib.error.URLError, TimeoutError):
        raise KisCollectionError("KIS request transport failed") from None
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise KisCollectionError("KIS response is invalid") from None
    if not isinstance(payload, dict):
        raise KisCollectionError("KIS response is invalid")
    return payload


def _load_dotenv(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        raise KisCollectionError(
            "KIS credential file is unavailable"
        ) from None
    output: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip():
            output[key.strip()] = value.strip()
    return output


def _credential(
    name: str,
    *,
    dotenv: Mapping[str, str],
) -> str:
    value = os.getenv(name) or dotenv.get(name)
    if not isinstance(value, str) or not value.strip():
        raise KisCollectionError(
            "KIS credentials are not configured"
        )
    return value.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=DEFAULT_RAW_DIR,
    )
    arguments = parser.parse_args(argv)
    try:
        dotenv = _load_dotenv(arguments.env_file)
        transport = KisHistoricalMinuteTransport(
            app_key=_credential("KIS_APP_KEY", dotenv=dotenv),
            app_secret=_credential("KIS_APP_SECRET", dotenv=dotenv),
            token_cache_path=arguments.raw_dir / ".kis_token_cache.json",
        )
        payload = collect_market_snapshot(
            transport=transport,
            raw_dir=arguments.raw_dir,
        )
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    except (KisCollectionError, MarketSnapshotValidationError) as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "reason": "market_snapshot_collection_failed",
                    "detail": str(exc),
                },
                separators=(",", ":"),
            )
        )
        return 1
    except OSError:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "reason": "market_snapshot_collection_failed",
                    "detail": "market snapshot file operation failed",
                },
                separators=(",", ":"),
            )
        )
        return 1
    snapshots = payload["snapshots"]
    assert isinstance(snapshots, list)
    print(
        json.dumps(
            {
                "status": "PASS",
                "record_count": len(snapshots),
                "security_count": len(
                    {
                        item["security_id"]
                        for item in snapshots
                        if isinstance(item, dict)
                    }
                ),
                "checkpoint_count": len(
                    {
                        item["checkpoint_id"]
                        for item in snapshots
                        if isinstance(item, dict)
                    }
                ),
                "checksum": payload["records_sha256"],
            },
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
