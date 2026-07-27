from __future__ import annotations

import asyncio
import copy
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
MAX_RECENT_EXCHANGES = 4
MAX_EXCHANGE_USER_CHARS = 2000
MAX_EXCHANGE_ASSISTANT_CHARS = 2000
MAX_SESSION_CONVERSATION_CHARS = 16_000
MAX_LLM_CONTEXT_EXCHANGES = 2
MAX_LLM_CONTEXT_CHARS = 4000

_CONTROL_CHARACTER = re.compile(r"[\x00-\x1f\x7f]")
_TEXT_CONTROL_CHARACTER = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_WINDOWS_PATH = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z]:[\\/]")
_UNC_PATH = re.compile(r"(?:\\\\|//)[^\\/\s]+[\\/][^\\/\s]+")
_POSIX_PRIVATE_PATH = re.compile(
    r"(?:^|[\s\"'()=\[\]{},;])/"
    r"(?:root|opt|workspace|home|Users|etc|var|tmp|mnt|srv|usr|app|media|custom)"
    r"(?:/|$)"
)
_CREDENTIAL_VALUE = re.compile(
    r"(?i)(?:api[-_]?key|client[-_]?secret|access[-_]?token|"
    r"authorization|credential)\s*[:=]\s*\S+"
)
_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9._:/-]{1,256}$")
_SECURITY_IDS = frozenset(
    {"KRX:005930", "KRX:000660", "KRX:005380"}
)
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
_EXCHANGE_INTENTS = _INTENTS | frozenset(
    {"prohibited_advice", "out_of_scope"}
)
_SOURCES = frozenset({"news", "disclosure", "research_report", "glossary"})
_RESPONSE_STATUSES = frozenset(
    {"complete", "partial", "provider_failed", "no_evidence", "blocked"}
)
_INVALID_STORE = "session store is unavailable"


class SessionStoreError(RuntimeError):
    """Raised when bounded anonymous session state cannot be used safely."""


@dataclass
class _SessionEntry:
    context: SessionContext
    recent_exchanges: tuple["SessionExchange", ...]
    revision: int
    last_access: float
    lock: asyncio.Lock
    users: int = 0


@dataclass(frozen=True)
class SessionExchange:
    user_question: str
    assistant_public_text: str
    status: str
    security_id: str | None
    intent: str
    selected_evidence_ids: tuple[str, ...]
    snapshot_id: str
    revision: int


@dataclass(frozen=True)
class SessionState:
    context: SessionContext
    recent_exchanges: tuple[SessionExchange, ...]
    revision: int


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
                entry.recent_exchanges = ()
                entry.revision = 0
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

    def state(self, session_id: str) -> SessionState | None:
        key = _session_id(session_id)
        now = self._now()
        self._purge_expired(now)
        entry = self._entries.get(key)
        if entry is None:
            return None
        entry.last_access = now
        return SessionState(
            context=_canonical_context(entry.context),
            recent_exchanges=tuple(
                copy.deepcopy(item) for item in entry.recent_exchanges
            ),
            revision=entry.revision,
        )

    def revision(self, session_id: str) -> int:
        state = self.state(session_id)
        return 0 if state is None else state.revision

    def append_exchange(
        self,
        session_id: str,
        *,
        user_question: str,
        assistant_public_text: str,
        status: str,
        security_id: str | None,
        intent: str,
        selected_evidence_ids: tuple[str, ...],
        snapshot_id: str,
    ) -> int:
        key = _session_id(session_id)
        now = self._now()
        self._purge_expired(now)
        entry = self._entries.get(key)
        if entry is None:
            entry = self._new_entry(key, now)
        revision = entry.revision + 1
        exchange = _canonical_exchange(
            SessionExchange(
                user_question=user_question,
                assistant_public_text=assistant_public_text,
                status=status,
                security_id=security_id,
                intent=intent,
                selected_evidence_ids=selected_evidence_ids,
                snapshot_id=snapshot_id,
                revision=revision,
            )
        )
        recent = (*entry.recent_exchanges, exchange)[
            -MAX_RECENT_EXCHANGES:
        ]
        if (
            sum(
                len(item.user_question)
                + len(item.assistant_public_text)
                for item in recent
            )
            > MAX_SESSION_CONVERSATION_CHARS
        ):
            raise SessionStoreError(_INVALID_STORE)
        entry.recent_exchanges = recent
        entry.revision = revision
        entry.last_access = now
        return revision

    def conversation_context(
        self,
        session_id: str,
        *,
        max_exchanges: int = MAX_LLM_CONTEXT_EXCHANGES,
        max_chars: int = MAX_LLM_CONTEXT_CHARS,
    ) -> str:
        if (
            type(max_exchanges) is not int
            or not 1 <= max_exchanges <= MAX_LLM_CONTEXT_EXCHANGES
            or type(max_chars) is not int
            or not 1 <= max_chars <= MAX_LLM_CONTEXT_CHARS
        ):
            raise SessionStoreError(_INVALID_STORE)
        state = self.state(session_id)
        if state is None:
            return ""
        selected: list[str] = []
        remaining = max_chars
        for exchange in reversed(state.recent_exchanges):
            block = (
                f"User: {exchange.user_question}\n"
                f"Assistant: {exchange.assistant_public_text}"
            )
            if len(block) > remaining:
                if not selected and remaining > 0:
                    selected.append(block[:remaining])
                    remaining = 0
                break
            selected.append(block)
            remaining -= len(block)
            if len(selected) >= max_exchanges:
                break
        selected.reverse()
        return "\n\n".join(selected)

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
            recent_exchanges=(),
            revision=0,
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


def _canonical_exchange(value: object) -> SessionExchange:
    if not isinstance(value, SessionExchange):
        raise SessionStoreError(_INVALID_STORE)
    if (
        not _memory_text(
            value.user_question,
            max_chars=MAX_EXCHANGE_USER_CHARS,
        )
        or not _memory_text(
            value.assistant_public_text,
            max_chars=MAX_EXCHANGE_ASSISTANT_CHARS,
        )
        or value.status not in _RESPONSE_STATUSES
        or (
            value.security_id is not None
            and value.security_id not in _SECURITY_IDS
        )
        or value.intent not in _EXCHANGE_INTENTS
        or not isinstance(value.selected_evidence_ids, tuple)
        or len(value.selected_evidence_ids) > 6
        or any(
            not isinstance(item, str)
            or not _SAFE_IDENTIFIER.fullmatch(item)
            for item in value.selected_evidence_ids
        )
        or len(value.selected_evidence_ids)
        != len(set(value.selected_evidence_ids))
        or not isinstance(value.snapshot_id, str)
        or not _SAFE_IDENTIFIER.fullmatch(value.snapshot_id)
        or type(value.revision) is not int
        or value.revision < 1
    ):
        raise SessionStoreError(_INVALID_STORE)
    return copy.deepcopy(value)


def _memory_text(value: object, *, max_chars: int) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
        and len(value) <= max_chars
        and not _TEXT_CONTROL_CHARACTER.search(value)
        and not _WINDOWS_PATH.search(value)
        and not _UNC_PATH.search(value)
        and not _POSIX_PRIVATE_PATH.search(value)
        and not _CREDENTIAL_VALUE.search(value)
    )


__all__ = [
    "InMemorySessionStore",
    "MAX_EXCHANGE_ASSISTANT_CHARS",
    "MAX_EXCHANGE_USER_CHARS",
    "MAX_LLM_CONTEXT_CHARS",
    "MAX_LLM_CONTEXT_EXCHANGES",
    "MAX_RECENT_EXCHANGES",
    "MAX_SESSIONS",
    "MAX_SESSION_CONVERSATION_CHARS",
    "SESSION_TTL_SECONDS",
    "SessionExchange",
    "SessionState",
    "SessionStoreError",
]
