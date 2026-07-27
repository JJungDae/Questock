from __future__ import annotations

import asyncio
import math
import re
import time
from collections import deque
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

CLIENT_WINDOW_SECONDS = 300.0
CLIENT_WINDOW_LIMIT = 10
CLIENT_DAY_LIMIT = 50
GLOBAL_CONCURRENCY_LIMIT = 2
GLOBAL_DAY_LIMIT = 100
MAX_CLIENT_BUCKETS = 1024
CLIENT_BUCKET_TTL_SECONDS = 86_400.0
CLIENT_KEY_HEADER = "X-Questock-Client-Key"

_SEOUL_TZ = ZoneInfo("Asia/Seoul")
_CLIENT_KEY = re.compile(r"^[0-9a-f]{64}$")
_UNAVAILABLE = "request protection is unavailable"
_LIMITED = "LLM request limit reached"


class RequestProtectionError(RuntimeError):
    """Raised when request protection cannot operate safely."""


class RequestProtectionLimitError(RequestProtectionError):
    """Raised when an admitted LLM attempt would exceed a fixed limit."""


@dataclass
class _ClientBucket:
    window_attempts: deque[float]
    day: date
    day_attempts: int
    last_access: float
    active: int = 0


@dataclass(frozen=True)
class ProtectionSnapshot:
    bucket_count: int
    global_day_attempts: int
    active_attempts: int


class RequestProtector:
    def __init__(
        self,
        *,
        enabled: bool = False,
        max_client_buckets: int = MAX_CLIENT_BUCKETS,
        client_bucket_ttl_seconds: float = CLIENT_BUCKET_TTL_SECONDS,
        monotonic: Callable[[], float] = time.monotonic,
        utc_now: Callable[[], datetime] | None = None,
    ) -> None:
        if (
            type(enabled) is not bool
            or type(max_client_buckets) is not int
            or not 1 <= max_client_buckets <= MAX_CLIENT_BUCKETS
            or type(client_bucket_ttl_seconds) not in {int, float}
            or not math.isfinite(client_bucket_ttl_seconds)
            or client_bucket_ttl_seconds <= 0
            or not callable(monotonic)
            or (utc_now is not None and not callable(utc_now))
        ):
            raise RequestProtectionError(_UNAVAILABLE)
        self._enabled = enabled
        self._max_client_buckets = max_client_buckets
        self._client_bucket_ttl_seconds = float(
            client_bucket_ttl_seconds
        )
        self._monotonic = monotonic
        self._utc_now = utc_now or (lambda: datetime.now(UTC))
        self._buckets: dict[str, _ClientBucket] = {}
        self._global_day: date | None = None
        self._global_day_attempts = 0
        self._active_attempts = 0
        self._last_now: float | None = None
        self._state_lock = asyncio.Lock()
        self._slots = asyncio.Semaphore(GLOBAL_CONCURRENCY_LIMIT)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def snapshot(self) -> ProtectionSnapshot:
        return ProtectionSnapshot(
            bucket_count=len(self._buckets),
            global_day_attempts=self._global_day_attempts,
            active_attempts=self._active_attempts,
        )

    @asynccontextmanager
    async def admit(
        self,
        client_key: str | None,
        *,
        timeout_seconds: float,
    ) -> AsyncIterator[None]:
        if not self._enabled:
            yield
            return
        key = _canonical_client_key(client_key)
        timeout = _positive_timeout(timeout_seconds)
        acquired = False
        admitted = False
        try:
            try:
                await asyncio.wait_for(
                    self._slots.acquire(),
                    timeout=timeout,
                )
                acquired = True
            except TimeoutError:
                raise RequestProtectionLimitError(_LIMITED) from None

            async with self._state_lock:
                now = self._now()
                day = self._kst_day()
                self._purge_expired(now)
                self._roll_global_day(day)
                bucket = self._bucket(key, now, day)
                self._roll_client_day(bucket, day)
                cutoff = now - CLIENT_WINDOW_SECONDS
                while (
                    bucket.window_attempts
                    and bucket.window_attempts[0] <= cutoff
                ):
                    bucket.window_attempts.popleft()
                if (
                    len(bucket.window_attempts) >= CLIENT_WINDOW_LIMIT
                    or bucket.day_attempts >= CLIENT_DAY_LIMIT
                    or self._global_day_attempts >= GLOBAL_DAY_LIMIT
                ):
                    raise RequestProtectionLimitError(_LIMITED)
                bucket.window_attempts.append(now)
                bucket.day_attempts += 1
                bucket.active += 1
                bucket.last_access = now
                self._global_day_attempts += 1
                self._active_attempts += 1
                admitted = True
            yield
        finally:
            if admitted:
                async with self._state_lock:
                    bucket = self._buckets.get(key)
                    if bucket is not None:
                        bucket.active = max(0, bucket.active - 1)
                        bucket.last_access = self._now()
                    self._active_attempts = max(
                        0,
                        self._active_attempts - 1,
                    )
            if acquired:
                self._slots.release()

    def _bucket(
        self,
        key: str,
        now: float,
        day: date,
    ) -> _ClientBucket:
        bucket = self._buckets.get(key)
        if bucket is not None:
            return bucket
        if len(self._buckets) >= self._max_client_buckets:
            candidates = [
                (item.last_access, client_key)
                for client_key, item in self._buckets.items()
                if item.active == 0
            ]
            if not candidates:
                raise RequestProtectionLimitError(_LIMITED)
            _, evicted_key = min(candidates)
            del self._buckets[evicted_key]
        bucket = _ClientBucket(
            window_attempts=deque(),
            day=day,
            day_attempts=0,
            last_access=now,
        )
        self._buckets[key] = bucket
        return bucket

    def _purge_expired(self, now: float) -> None:
        expired = [
            key
            for key, bucket in self._buckets.items()
            if bucket.active == 0
            and now - bucket.last_access
            >= self._client_bucket_ttl_seconds
        ]
        for key in expired:
            del self._buckets[key]

    def _roll_global_day(self, day: date) -> None:
        if self._global_day != day:
            self._global_day = day
            self._global_day_attempts = 0

    @staticmethod
    def _roll_client_day(bucket: _ClientBucket, day: date) -> None:
        if bucket.day != day:
            bucket.day = day
            bucket.day_attempts = 0

    def _kst_day(self) -> date:
        try:
            value = self._utc_now()
        except Exception:
            raise RequestProtectionError(_UNAVAILABLE) from None
        if (
            not isinstance(value, datetime)
            or value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise RequestProtectionError(_UNAVAILABLE)
        return value.astimezone(_SEOUL_TZ).date()

    def _now(self) -> float:
        try:
            value = self._monotonic()
        except Exception:
            raise RequestProtectionError(_UNAVAILABLE) from None
        if (
            type(value) not in {int, float}
            or not math.isfinite(value)
            or (self._last_now is not None and value < self._last_now)
        ):
            raise RequestProtectionError(_UNAVAILABLE)
        output = float(value)
        self._last_now = output
        return output


def _canonical_client_key(value: object) -> str:
    if not isinstance(value, str) or not _CLIENT_KEY.fullmatch(value):
        raise RequestProtectionLimitError(_LIMITED)
    return value


def _positive_timeout(value: object) -> float:
    if (
        type(value) not in {int, float}
        or not math.isfinite(value)
        or value <= 0
    ):
        raise RequestProtectionError(_UNAVAILABLE)
    return float(value)


__all__ = [
    "CLIENT_BUCKET_TTL_SECONDS",
    "CLIENT_DAY_LIMIT",
    "CLIENT_KEY_HEADER",
    "CLIENT_WINDOW_LIMIT",
    "CLIENT_WINDOW_SECONDS",
    "GLOBAL_CONCURRENCY_LIMIT",
    "GLOBAL_DAY_LIMIT",
    "MAX_CLIENT_BUCKETS",
    "ProtectionSnapshot",
    "RequestProtectionError",
    "RequestProtectionLimitError",
    "RequestProtector",
]
