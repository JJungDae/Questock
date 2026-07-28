from __future__ import annotations

import copy
import hashlib
import math
import re
import time
import unicodedata
from dataclasses import dataclass
from typing import Callable

from app.api.schemas import ChatResponse
from app.services.observability import RequestObservation

RESPONSE_CACHE_TTL_SECONDS = 90.0
MAX_RESPONSE_CACHE_ENTRIES = 256
MAX_RESPONSE_CACHE_ENTRIES_PER_SESSION = 4

_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_CONTROL_CHARACTER = re.compile(r"[\x00-\x1f\x7f]")
_WHITESPACE = re.compile(r"\s+")
_UNAVAILABLE = "response cache is unavailable"


class ResponseCacheError(RuntimeError):
    """Raised when the bounded response cache cannot operate safely."""


@dataclass(frozen=True)
class CachedResponse:
    response: ChatResponse
    observation: RequestObservation


@dataclass(frozen=True)
class _CacheKey:
    session_id: str
    snapshot_id: str
    question_digest: str
    revision: int
    model_fingerprint: str
    checkpoint_id: str


@dataclass
class _CacheEntry:
    response: ChatResponse
    observation: RequestObservation
    created_at: float
    last_access: float


class ResponseCache:
    def __init__(
        self,
        *,
        enabled: bool = False,
        ttl_seconds: float = RESPONSE_CACHE_TTL_SECONDS,
        max_entries: int = MAX_RESPONSE_CACHE_ENTRIES,
        max_entries_per_session: int = (
            MAX_RESPONSE_CACHE_ENTRIES_PER_SESSION
        ),
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if (
            type(enabled) is not bool
            or type(ttl_seconds) not in {int, float}
            or not math.isfinite(ttl_seconds)
            or ttl_seconds <= 0
            or type(max_entries) is not int
            or not 1 <= max_entries <= MAX_RESPONSE_CACHE_ENTRIES
            or type(max_entries_per_session) is not int
            or not 1
            <= max_entries_per_session
            <= MAX_RESPONSE_CACHE_ENTRIES_PER_SESSION
            or max_entries_per_session > max_entries
            or not callable(monotonic)
        ):
            raise ResponseCacheError(_UNAVAILABLE)
        self._enabled = enabled
        self._ttl_seconds = float(ttl_seconds)
        self._max_entries = max_entries
        self._max_entries_per_session = max_entries_per_session
        self._monotonic = monotonic
        self._entries: dict[_CacheKey, _CacheEntry] = {}
        self._last_now: float | None = None

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def size(self) -> int:
        if not self._enabled:
            return 0
        self._purge_expired(self._now())
        return len(self._entries)

    def get(
        self,
        *,
        session_id: str,
        snapshot_id: str,
        question: str,
        revision: int,
        model_fingerprint: str,
        checkpoint_id: str = "legacy",
    ) -> CachedResponse | None:
        if not self._enabled:
            return None
        key = _cache_key(
            session_id=session_id,
            snapshot_id=snapshot_id,
            question=question,
            revision=revision,
            model_fingerprint=model_fingerprint,
            checkpoint_id=checkpoint_id,
        )
        now = self._now()
        self._purge_expired(now)
        entry = self._entries.get(key)
        if entry is None:
            return None
        entry.last_access = now
        return CachedResponse(
            response=entry.response.model_copy(deep=True),
            observation=copy.deepcopy(entry.observation),
        )

    def put(
        self,
        *,
        session_id: str,
        snapshot_id: str,
        question: str,
        resulting_revision: int,
        model_fingerprint: str,
        response: ChatResponse,
        observation: RequestObservation,
        checkpoint_id: str = "legacy",
    ) -> None:
        if not self._enabled:
            return
        if not isinstance(response, ChatResponse) or not isinstance(
            observation,
            RequestObservation,
        ):
            raise ResponseCacheError(_UNAVAILABLE)
        key = _cache_key(
            session_id=session_id,
            snapshot_id=snapshot_id,
            question=question,
            revision=resulting_revision,
            model_fingerprint=model_fingerprint,
            checkpoint_id=checkpoint_id,
        )
        now = self._now()
        self._purge_expired(now)
        self._entries.pop(key, None)
        session_keys = [
            item
            for item in self._entries
            if item.session_id == key.session_id
        ]
        if len(session_keys) >= self._max_entries_per_session:
            self._evict_oldest(session_keys)
        if len(self._entries) >= self._max_entries:
            self._evict_oldest(list(self._entries))
        self._entries[key] = _CacheEntry(
            response=response.model_copy(deep=True),
            observation=copy.deepcopy(observation),
            created_at=now,
            last_access=now,
        )

    def _evict_oldest(self, keys: list[_CacheKey]) -> None:
        if not keys:
            raise ResponseCacheError(_UNAVAILABLE)
        key = min(
            keys,
            key=lambda item: (
                self._entries[item].last_access,
                item.session_id,
                item.snapshot_id,
                item.question_digest,
                item.revision,
                item.model_fingerprint,
                item.checkpoint_id,
            ),
        )
        del self._entries[key]

    def _purge_expired(self, now: float) -> None:
        expired = [
            key
            for key, entry in self._entries.items()
            if now - entry.created_at >= self._ttl_seconds
        ]
        for key in expired:
            del self._entries[key]

    def _now(self) -> float:
        try:
            value = self._monotonic()
        except Exception:
            raise ResponseCacheError(_UNAVAILABLE) from None
        if (
            type(value) not in {int, float}
            or not math.isfinite(value)
            or (self._last_now is not None and value < self._last_now)
        ):
            raise ResponseCacheError(_UNAVAILABLE)
        output = float(value)
        self._last_now = output
        return output


def _cache_key(
    *,
    session_id: object,
    snapshot_id: object,
    question: object,
    revision: object,
    model_fingerprint: object,
    checkpoint_id: object = "legacy",
) -> _CacheKey:
    if (
        not isinstance(session_id, str)
        or not session_id
        or session_id != session_id.strip()
        or len(session_id) > 128
        or _CONTROL_CHARACTER.search(session_id)
        or not isinstance(snapshot_id, str)
        or not _SAFE_TOKEN.fullmatch(snapshot_id)
        or not isinstance(model_fingerprint, str)
        or not _SAFE_TOKEN.fullmatch(model_fingerprint)
        or not isinstance(checkpoint_id, str)
        or not _SAFE_TOKEN.fullmatch(checkpoint_id)
        or type(revision) is not int
        or revision < 0
        or not isinstance(question, str)
    ):
        raise ResponseCacheError(_UNAVAILABLE)
    normalized_question = _WHITESPACE.sub(
        " ",
        unicodedata.normalize("NFKC", question),
    ).strip().casefold()
    if not normalized_question or len(normalized_question) > 2000:
        raise ResponseCacheError(_UNAVAILABLE)
    return _CacheKey(
        session_id=session_id,
        snapshot_id=snapshot_id,
        question_digest=hashlib.sha256(
            normalized_question.encode("utf-8")
        ).hexdigest(),
        revision=revision,
        model_fingerprint=model_fingerprint,
        checkpoint_id=checkpoint_id,
    )


__all__ = [
    "CachedResponse",
    "MAX_RESPONSE_CACHE_ENTRIES",
    "MAX_RESPONSE_CACHE_ENTRIES_PER_SESSION",
    "RESPONSE_CACHE_TTL_SECONDS",
    "ResponseCache",
    "ResponseCacheError",
]
