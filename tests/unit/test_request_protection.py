from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from app.services.request_protection import (
    CLIENT_DAY_LIMIT,
    CLIENT_WINDOW_LIMIT,
    GLOBAL_CONCURRENCY_LIMIT,
    GLOBAL_DAY_LIMIT,
    RequestProtectionLimitError,
    RequestProtector,
)


class Clock:
    def __init__(self) -> None:
        self.monotonic_value = 0.0
        self.utc_value = datetime(2026, 7, 27, 0, tzinfo=UTC)

    def monotonic(self) -> float:
        return self.monotonic_value

    def utc_now(self) -> datetime:
        return self.utc_value

    def advance(self, seconds: float) -> None:
        self.monotonic_value += seconds
        self.utc_value += timedelta(seconds=seconds)


def _key(index: int) -> str:
    return f"{index:064x}"


async def _attempt(
    protector: RequestProtector,
    key: str | None,
) -> None:
    async with protector.admit(key, timeout_seconds=1):
        return


def _protector(
    clock: Clock,
    **kwargs: object,
) -> RequestProtector:
    return RequestProtector(
        enabled=True,
        monotonic=clock.monotonic,
        utc_now=clock.utc_now,
        **kwargs,
    )


def test_disabled_protection_does_not_require_client_key_or_count() -> None:
    protector = RequestProtector()

    asyncio.run(_attempt(protector, None))

    assert protector.snapshot().bucket_count == 0
    assert protector.snapshot().global_day_attempts == 0


def test_client_window_allows_ten_and_blocks_eleventh_until_boundary() -> None:
    clock = Clock()
    protector = _protector(clock)

    for _ in range(CLIENT_WINDOW_LIMIT):
        asyncio.run(_attempt(protector, _key(1)))

    with pytest.raises(
        RequestProtectionLimitError,
        match="LLM request limit reached",
    ):
        asyncio.run(_attempt(protector, _key(1)))

    clock.advance(300)
    asyncio.run(_attempt(protector, _key(1)))


def test_client_day_limit_and_kst_rollover() -> None:
    clock = Clock()
    protector = _protector(clock)

    for index in range(CLIENT_DAY_LIMIT):
        if index and index % CLIENT_WINDOW_LIMIT == 0:
            clock.advance(301)
        asyncio.run(_attempt(protector, _key(2)))

    clock.advance(301)
    with pytest.raises(RequestProtectionLimitError):
        asyncio.run(_attempt(protector, _key(2)))

    clock.utc_value = datetime(2026, 7, 27, 15, tzinfo=UTC)
    clock.monotonic_value += 1
    asyncio.run(_attempt(protector, _key(2)))


def test_global_day_limit_is_shared_across_clients() -> None:
    clock = Clock()
    protector = _protector(clock)

    for client in range(10):
        for _ in range(10):
            asyncio.run(_attempt(protector, _key(client + 10)))

    assert protector.snapshot().global_day_attempts == GLOBAL_DAY_LIMIT
    with pytest.raises(RequestProtectionLimitError):
        asyncio.run(_attempt(protector, _key(100)))


def test_global_concurrency_is_two_and_pending_attempt_waits() -> None:
    async def run() -> None:
        clock = Clock()
        protector = _protector(clock)
        entered = [asyncio.Event() for _ in range(3)]
        release = asyncio.Event()

        async def worker(index: int) -> None:
            async with protector.admit(
                _key(index + 20),
                timeout_seconds=1,
            ):
                entered[index].set()
                await release.wait()

        tasks = [
            asyncio.create_task(worker(index))
            for index in range(3)
        ]
        await asyncio.wait_for(entered[0].wait(), timeout=0.2)
        await asyncio.wait_for(entered[1].wait(), timeout=0.2)
        await asyncio.sleep(0)
        assert not entered[2].is_set()
        assert (
            protector.snapshot().active_attempts
            == GLOBAL_CONCURRENCY_LIMIT
        )
        release.set()
        await asyncio.gather(*tasks)
        assert entered[2].is_set()
        assert protector.snapshot().active_attempts == 0

    asyncio.run(run())


def test_bucket_map_stays_bounded_and_expired_buckets_are_purged() -> None:
    clock = Clock()
    protector = _protector(
        clock,
        max_client_buckets=2,
        client_bucket_ttl_seconds=10,
    )

    asyncio.run(_attempt(protector, _key(30)))
    clock.advance(1)
    asyncio.run(_attempt(protector, _key(31)))
    clock.advance(1)
    asyncio.run(_attempt(protector, _key(32)))
    assert protector.snapshot().bucket_count == 2

    clock.advance(10)
    asyncio.run(_attempt(protector, _key(33)))
    assert protector.snapshot().bucket_count == 1


@pytest.mark.parametrize(
    "client_key",
    [None, "", "raw-ip-address", "A" * 64, "0" * 63],
)
def test_invalid_client_key_is_rejected_without_echo(
    client_key: str | None,
) -> None:
    clock = Clock()
    protector = _protector(clock)

    with pytest.raises(RequestProtectionLimitError) as exc_info:
        asyncio.run(_attempt(protector, client_key))

    if client_key:
        assert client_key not in str(exc_info.value)
