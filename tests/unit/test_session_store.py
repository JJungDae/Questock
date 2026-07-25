from __future__ import annotations

import asyncio
from datetime import date

import pytest

from app.core.models import DateRange, SessionContext
from app.services.session_store import InMemorySessionStore, SessionStoreError


class Clock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


def context(security_id: str = "KRX:005930") -> SessionContext:
    return SessionContext(
        current_security_id=security_id,
        current_date_range=DateRange(
            start=date(2026, 7, 1),
            end=date(2026, 7, 2),
        ),
        previous_intent="recent_issue",
        previous_source_types=["news"],
    )


def test_get_put_are_deep_copied_and_caller_safe() -> None:
    store = InMemorySessionStore()
    original = context()

    store.put("session-a", original)
    first = store.get("session-a")
    assert first == original
    assert first is not original

    assert first is not None
    first.previous_source_types.append("disclosure")
    second = store.get("session-a")
    assert second == original
    assert original.previous_source_types == ["news"]


def test_ttl_boundary_expires_without_stale_return() -> None:
    clock = Clock()
    store = InMemorySessionStore(ttl_seconds=10, monotonic=clock)
    store.put("session-a", context())

    clock.advance(9.999)
    assert store.get("session-a") is not None
    clock.advance(10)
    assert store.get("session-a") is None
    assert store.size == 0


def test_capacity_eviction_uses_last_access_then_session_id() -> None:
    clock = Clock()
    store = InMemorySessionStore(max_sessions=2, monotonic=clock)
    store.put("session-b", context("KRX:000660"))
    store.put("session-a", context())

    store.put("session-c", context("KRX:005380"))

    assert store.get("session-a") is None
    assert store.get("session-b") is not None
    assert store.get("session-c") is not None


def test_same_session_is_serialized_and_different_session_can_enter() -> None:
    async def run() -> None:
        store = InMemorySessionStore()
        first_entered = asyncio.Event()
        release_first = asyncio.Event()
        second_entered = asyncio.Event()
        other_entered = asyncio.Event()

        async def first() -> None:
            async with store.serialized("same"):
                first_entered.set()
                await release_first.wait()

        async def second() -> None:
            await first_entered.wait()
            async with store.serialized("same"):
                second_entered.set()

        async def other() -> None:
            await first_entered.wait()
            async with store.serialized("other"):
                other_entered.set()

        tasks = [
            asyncio.create_task(first()),
            asyncio.create_task(second()),
            asyncio.create_task(other()),
        ]
        await first_entered.wait()
        await asyncio.wait_for(other_entered.wait(), timeout=0.2)
        assert not second_entered.is_set()
        release_first.set()
        await asyncio.gather(*tasks)
        assert second_entered.is_set()

    asyncio.run(run())


def test_capacity_with_only_active_sessions_fails_safely() -> None:
    async def run() -> None:
        store = InMemorySessionStore(max_sessions=1)
        async with store.serialized("active"):
            with pytest.raises(SessionStoreError, match="session store is unavailable"):
                async with store.serialized("new"):
                    raise AssertionError("unreachable")

    asyncio.run(run())


@pytest.mark.parametrize(
    "session_id",
    ["", " leading", "trailing ", "bad\nvalue", "x" * 129],
)
def test_invalid_session_id_is_sanitized(session_id: str) -> None:
    store = InMemorySessionStore()
    with pytest.raises(SessionStoreError, match="session store is unavailable"):
        store.get(session_id)


def test_malformed_context_and_clock_fail_with_typed_error() -> None:
    store = InMemorySessionStore()
    malformed = SessionContext.model_construct(
        previous_intent="not-an-intent",
        previous_source_types=["news"],
    )
    with pytest.raises(SessionStoreError, match="session store is unavailable"):
        store.put("session-a", malformed)

    clock = Clock()
    timed = InMemorySessionStore(monotonic=clock)
    assert timed.size == 0
    clock.value = -1
    with pytest.raises(SessionStoreError, match="session store is unavailable"):
        _ = timed.size
