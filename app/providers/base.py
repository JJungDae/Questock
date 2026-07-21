from __future__ import annotations

import asyncio
import unicodedata
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Protocol, TypeVar

from app.config import ProviderConfig
from app.core.models import DateRange, ProviderResult, SecurityIdentifier
from app.core.status import ProviderStatus

T = TypeVar("T")

_FAILURE_ERROR_CODES: dict[ProviderStatus, str] = {
    ProviderStatus.INVALID_QUERY: "invalid_query",
    ProviderStatus.UNAUTHORIZED: "unauthorized",
    ProviderStatus.RATE_LIMITED: "rate_limited",
    ProviderStatus.TIMEOUT: "attempt_timeout",
    ProviderStatus.PROVIDER_UNAVAILABLE: "provider_unavailable",
    ProviderStatus.PARSE_ERROR: "parse_error",
}
_RETRYABLE_STATUSES = {ProviderStatus.TIMEOUT, ProviderStatus.PROVIDER_UNAVAILABLE}


class ProviderResultContractError(ValueError):
    """Raised when provider output violates the shared ProviderResult contract."""


class Provider(Protocol[T]):
    key: str

    async def fetch(
        self,
        security: SecurityIdentifier,
        query: str | None = None,
        date_range: DateRange | None = None,
        attempt_timeout_seconds: float = 8,
    ) -> ProviderResult[T]:
        """Fetch normalized provider data for an already resolved security."""


@dataclass(frozen=True)
class CacheKey:
    provider_key: str
    security_id: str
    normalized_query: str
    date_start: date | None
    date_end: date | None


def security_id_for(security: SecurityIdentifier) -> str:
    return f"{security.market}:{security.ticker}"


def normalize_query(query: str | None) -> str:
    if query is None:
        return ""
    normalized = unicodedata.normalize("NFKC", query)
    return " ".join(normalized.split()).casefold()


def make_cache_key(
    provider_key: str,
    security: SecurityIdentifier,
    query: str | None = None,
    date_range: DateRange | None = None,
) -> CacheKey:
    return CacheKey(
        provider_key=provider_key,
        security_id=security_id_for(security),
        normalized_query=normalize_query(query),
        date_start=date_range.start if date_range else None,
        date_end=date_range.end if date_range else None,
    )


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ProviderResultContractError("fetched_at must be timezone-aware UTC")
    return value.astimezone(UTC)


def _sanitize_message(message: str | None, default: str) -> str:
    if not message:
        return default
    sanitized = " ".join(message.split())
    if len(sanitized) > 160:
        sanitized = sanitized[:157] + "..."
    return sanitized


def create_provider_result(
    *,
    status: ProviderStatus,
    data: T | None = None,
    error_code: str | None = None,
    message: str | None = None,
    fetched_at: datetime | None = None,
    from_cache: bool = False,
) -> ProviderResult[T]:
    fetched_at = _ensure_utc(fetched_at) if fetched_at is not None else _utc_now()

    if status == ProviderStatus.OK:
        if data is None:
            raise ProviderResultContractError("ok provider result requires data")
        if error_code is not None:
            raise ProviderResultContractError("ok provider result must not include error_code")
        return ProviderResult(
            status=status,
            data=data,
            error_code=None,
            message=message,
            fetched_at=fetched_at,
            from_cache=from_cache,
        )

    if status == ProviderStatus.NO_DATA:
        if data is not None:
            raise ProviderResultContractError("no_data provider result must not include data")
        if error_code is not None:
            raise ProviderResultContractError("no_data provider result must not include error_code")
        return ProviderResult(
            status=status,
            data=None,
            error_code=None,
            message=message,
            fetched_at=fetched_at,
            from_cache=from_cache,
        )

    if data is not None:
        raise ProviderResultContractError("failed provider result must not include data")
    if status not in _FAILURE_ERROR_CODES:
        raise ProviderResultContractError(f"unsupported provider status: {status}")

    if status == ProviderStatus.TIMEOUT:
        stable_error_code = error_code or "attempt_timeout"
        if stable_error_code not in {"attempt_timeout", "total_deadline_exceeded"}:
            raise ProviderResultContractError("timeout provider result has invalid error_code")
    else:
        stable_error_code = _FAILURE_ERROR_CODES[status]
        if error_code is not None and error_code != stable_error_code:
            raise ProviderResultContractError(f"{status.value} provider result has invalid error_code")

    return ProviderResult(
        status=status,
        data=None,
        error_code=stable_error_code,
        message=_sanitize_message(message, stable_error_code),
        fetched_at=fetched_at,
        from_cache=from_cache,
    )


class InMemoryTTLCache:
    def __init__(self, ttl_seconds: float = 300, clock: Callable[[], float] | None = None) -> None:
        if ttl_seconds < 0:
            raise ValueError("ttl_seconds must be greater than or equal to 0")
        self.ttl_seconds = ttl_seconds
        self._clock = clock
        self._items: dict[CacheKey, tuple[float, ProviderResult[Any]]] = {}

    def _now(self) -> float:
        if self._clock is None:
            return asyncio.get_running_loop().time()
        return self._clock()

    def get(self, key: CacheKey) -> ProviderResult[Any] | None:
        if self.ttl_seconds == 0:
            return None
        item = self._items.get(key)
        if item is None:
            return None
        stored_at, result = item
        if self._now() - stored_at >= self.ttl_seconds:
            self._items.pop(key, None)
            return None
        return result.model_copy(update={"from_cache": True})

    def set(self, key: CacheKey, result: ProviderResult[Any]) -> None:
        if self.ttl_seconds == 0:
            return
        if result.status != ProviderStatus.OK:
            return
        self._items[key] = (self._now(), result.model_copy(update={"from_cache": False}))


def _total_deadline_result() -> ProviderResult[Any]:
    return create_provider_result(
        status=ProviderStatus.TIMEOUT,
        error_code="total_deadline_exceeded",
        message="provider total deadline exceeded",
    )


async def _call_once(
    provider: Provider[Any],
    security: SecurityIdentifier,
    query: str | None,
    date_range: DateRange | None,
    attempt_timeout_seconds: float,
    timeout_error_code: str = "attempt_timeout",
) -> ProviderResult[Any]:
    try:
        result = await asyncio.wait_for(
            provider.fetch(
                security=security,
                query=query,
                date_range=date_range,
                attempt_timeout_seconds=attempt_timeout_seconds,
            ),
            timeout=attempt_timeout_seconds,
        )
    except TimeoutError:
        message = "provider total deadline exceeded"
        if timeout_error_code == "attempt_timeout":
            message = "provider attempt timed out"
        return create_provider_result(
            status=ProviderStatus.TIMEOUT,
            error_code=timeout_error_code,
            message=message,
        )
    return create_provider_result(
        status=result.status,
        data=result.data,
        error_code=result.error_code,
        message=result.message,
        fetched_at=result.fetched_at,
        from_cache=False,
    )


async def fetch_with_policy(
    provider: Provider[Any],
    security: SecurityIdentifier,
    config: ProviderConfig,
    query: str | None = None,
    date_range: DateRange | None = None,
    cache: InMemoryTTLCache | None = None,
    clock: Callable[[], float] | None = None,
) -> ProviderResult[Any]:
    cache_key = make_cache_key(provider.key, security, query, date_range)
    if cache is not None:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    loop = asyncio.get_running_loop()
    monotonic = clock or loop.time
    deadline_at = monotonic() + config.total_deadline_seconds
    attempts_allowed = config.retry_count + 1
    last_result: ProviderResult[Any] | None = None

    for attempt_index in range(attempts_allowed):
        remaining = deadline_at - monotonic()
        if remaining <= 0:
            return _total_deadline_result()
        attempt_timeout = min(config.timeout_seconds, remaining)
        timeout_error_code = "attempt_timeout" if attempt_timeout == config.timeout_seconds else "total_deadline_exceeded"
        result = await _call_once(provider, security, query, date_range, attempt_timeout, timeout_error_code)
        last_result = result

        if result.status == ProviderStatus.OK and cache is not None:
            cache.set(cache_key, result)
        if result.status not in _RETRYABLE_STATUSES:
            return result
        if attempt_index == attempts_allowed - 1:
            return result

    return last_result or _total_deadline_result()


async def fetch_required_providers(
    providers: Mapping[str, Provider[Any]],
    security: SecurityIdentifier,
    config: ProviderConfig,
    query: str | None = None,
    date_range: DateRange | None = None,
    cache: InMemoryTTLCache | None = None,
    clock: Callable[[], float] | None = None,
) -> dict[str, ProviderResult[Any]]:
    async def run_provider(provider_key: str, provider: Provider[Any]) -> tuple[str, ProviderResult[Any]]:
        try:
            result = await fetch_with_policy(
                provider=provider,
                security=security,
                config=config,
                query=query,
                date_range=date_range,
                cache=cache,
                clock=clock,
            )
        except Exception:
            result = create_provider_result(
                status=ProviderStatus.PROVIDER_UNAVAILABLE,
                error_code="provider_unavailable",
                message="provider unavailable",
            )
        return provider_key, result

    tasks = [asyncio.create_task(run_provider(provider_key, provider)) for provider_key, provider in providers.items()]
    try:
        pairs = await asyncio.wait_for(asyncio.gather(*tasks), timeout=config.total_deadline_seconds)
    except TimeoutError:
        for task in tasks:
            if not task.done():
                task.cancel()
        pairs = []
        for provider_key, task in zip(providers.keys(), tasks, strict=True):
            if task.done() and not task.cancelled():
                try:
                    pairs.append(task.result())
                except Exception:
                    pairs.append((provider_key, _total_deadline_result()))
            else:
                pairs.append((provider_key, _total_deadline_result()))
        await asyncio.gather(*tasks, return_exceptions=True)
    return dict(pairs)


__all__ = [
    "CacheKey",
    "InMemoryTTLCache",
    "Provider",
    "ProviderResultContractError",
    "create_provider_result",
    "fetch_required_providers",
    "fetch_with_policy",
    "make_cache_key",
    "normalize_query",
    "security_id_for",
]
