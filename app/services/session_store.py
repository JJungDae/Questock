from __future__ import annotations

import asyncio
import math
import re
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass

from pydantic import ValidationError

from app.core.models import SessionContext

MAX_SESSIONS = 256
SESSION_TTL_SECONDS = 1800.0

_CONTROL_CHARACTER = re.compile(r"[\x00-\x1f\x7f]")
_INTENTS = frozenset(
    {
        "recent_issue",
        "disclosure_summary",
        "research_report_summary",
        "risk_factors",
        "financial_term",
        "multi_source_summary",
    }
)
_SOURCES = frozenset({"news", "disclosure", "research_report", "glossary"})
_INVALID_STORE = "session store is unavailable"


class SessionStoreError(RuntimeError):
    """Raised when bounded anonymous session state cannot be used safely."""


@dataclass
class _SessionEntry:
    context: SessionContext
    last_access: float
    lock: asyncio.Lock
    users: int = 0


class InMemorySessionStore:
    def __init__(
        self,
        *,
        max_sessions: int = MAX_SESSIONS,
        ttl_seconds: float = SESSION_TTL_SECONDS,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if (
            type(max_sessions) is not int
            or max_sessions < 1
            or max_sessions > MAX_SESSIONS
            or type(ttl_seconds) not in {int, float}
            or not math.isfinite(ttl_seconds)
            or ttl_seconds <= 0
            or not callable(monotonic)
        ):
            raise SessionStoreError(_INVALID_STORE)
        self._max_sessions = max_sessions
        self._ttl_seconds = float(ttl_seconds)
        self._monotonic = monotonic
        self._entries: dict[str, _SessionEntry] = {}
        self._last_now: float | None = None

    @property
    def size(self) -> int:
        self._purge_expired(self._now())
        return len(self._entries)

    @asynccontextmanager
    async def serialized(self, session_id: str) -> AsyncIterator[None]:
        key = _session_id(session_id)
        entry = self._entry_for_request(key)
        entry.users += 1
        acquired = False
        try:
            await entry.lock.acquire()
            acquired = True
            now = self._now()
            if now - entry.last_access >= self._ttl_seconds:
                entry.context = SessionContext()
            entry.last_access = now
            yield
        finally:
            if acquired:
                entry.last_access = self._now()
                entry.lock.release()
            entry.users -= 1

    def get(self, session_id: str) -> SessionContext | None:
        key = _session_id(session_id)
        now = self._now()
        self._purge_expired(now)
        entry = self._entries.get(key)
        if entry is None:
            return None
        entry.last_access = now
        return _canonical_context(entry.context)

    def put(self, session_id: str, context: SessionContext) -> None:
        key = _session_id(session_id)
        canonical = _canonical_context(context)
        now = self._now()
        self._purge_expired(now)
        entry = self._entries.get(key)
        if entry is None:
            entry = self._new_entry(key, now)
        entry.context = canonical
        entry.last_access = now

    def _entry_for_request(self, key: str) -> _SessionEntry:
        now = self._now()
        self._purge_expired(now)
        entry = self._entries.get(key)
        if entry is not None:
            return entry
        return self._new_entry(key, now)

    def _new_entry(self, key: str, now: float) -> _SessionEntry:
        if len(self._entries) >= self._max_sessions:
            candidates = [
                (entry.last_access, session_id)
                for session_id, entry in self._entries.items()
                if entry.users == 0
            ]
            if not candidates:
                raise SessionStoreError(_INVALID_STORE)
            _, evicted_id = min(candidates)
            del self._entries[evicted_id]
        entry = _SessionEntry(
            context=SessionContext(),
            last_access=now,
            lock=asyncio.Lock(),
        )
        self._entries[key] = entry
        return entry

    def _purge_expired(self, now: float) -> None:
        expired = [
            session_id
            for session_id, entry in self._entries.items()
            if entry.users == 0
            and now - entry.last_access >= self._ttl_seconds
        ]
        for session_id in expired:
            del self._entries[session_id]

    def _now(self) -> float:
        try:
            value = self._monotonic()
        except Exception:
            raise SessionStoreError(_INVALID_STORE) from None
        if (
            type(value) not in {int, float}
            or not math.isfinite(value)
            or (self._last_now is not None and value < self._last_now)
        ):
            raise SessionStoreError(_INVALID_STORE)
        output = float(value)
        self._last_now = output
        return output


def _session_id(value: object) -> str:
    if not isinstance(value, str):
        raise SessionStoreError(_INVALID_STORE)
    canonical = value.strip()
    if (
        not canonical
        or canonical != value
        or len(canonical) > 128
        or _CONTROL_CHARACTER.search(canonical)
    ):
        raise SessionStoreError(_INVALID_STORE)
    return canonical


def _canonical_context(value: object) -> SessionContext:
    if not isinstance(value, SessionContext):
        raise SessionStoreError(_INVALID_STORE)
    try:
        canonical = SessionContext.model_validate(
            value.model_dump(mode="python"),
            strict=True,
        )
    except (AttributeError, TypeError, ValueError, ValidationError):
        raise SessionStoreError(_INVALID_STORE) from None
    if (
        canonical.previous_intent is not None
        and canonical.previous_intent not in _INTENTS
    ):
        raise SessionStoreError(_INVALID_STORE)
    if (
        not isinstance(canonical.previous_source_types, list)
        or any(
            not isinstance(source, str) or source not in _SOURCES
            for source in canonical.previous_source_types
        )
        or len(canonical.previous_source_types)
        != len(set(canonical.previous_source_types))
    ):
        raise SessionStoreError(_INVALID_STORE)
    return canonical.model_copy(deep=True)


__all__ = [
    "InMemorySessionStore",
    "MAX_SESSIONS",
    "SESSION_TTL_SECONDS",
    "SessionStoreError",
]
