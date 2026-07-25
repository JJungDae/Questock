from __future__ import annotations

import json
import logging
import math
import re
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from app.core.status import EvidenceDecisionStatus, ProviderStatus

_LOGGER_NAME = "questock.observability"
_SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9._:/-]{1,128}$")
_PROVIDER_STATUSES = frozenset(status.value for status in ProviderStatus)
_DECISION_STATUSES = frozenset(
    status.value for status in EvidenceDecisionStatus
)
_GENERATION_MODES = frozenset(
    {"llm", "fixed_template", "blocked", "not_called"}
)


class ObservationValidationError(ValueError):
    """Raised when an internal observation violates the safe log contract."""


@dataclass(frozen=True)
class RequestObservation:
    request_id: str
    intent: str
    security_id: str | None
    provider_statuses: tuple[tuple[str, str], ...]
    evidence_count: int
    retrieval_strategy: str
    evidence_decision: str
    total_latency_ms: float
    llm_call_count: int
    fallback_used: bool

    def __post_init__(self) -> None:
        _validate_token(self.request_id, "request ID")
        _validate_token(self.intent, "intent")
        if self.security_id is not None:
            _validate_token(self.security_id, "security ID")
        if not isinstance(self.provider_statuses, tuple):
            raise ObservationValidationError(
                "provider statuses are invalid"
            )
        seen_sources: set[str] = set()
        for item in self.provider_statuses:
            if (
                not isinstance(item, tuple)
                or len(item) != 2
                or not isinstance(item[0], str)
                or not isinstance(item[1], str)
            ):
                raise ObservationValidationError(
                    "provider statuses are invalid"
                )
            source, status = item
            _validate_token(source, "provider source")
            if source in seen_sources or status not in _PROVIDER_STATUSES:
                raise ObservationValidationError(
                    "provider statuses are invalid"
                )
            seen_sources.add(source)
        if type(self.evidence_count) is not int or self.evidence_count < 0:
            raise ObservationValidationError("evidence count is invalid")
        _validate_token(self.retrieval_strategy, "retrieval strategy")
        if self.evidence_decision not in _DECISION_STATUSES:
            raise ObservationValidationError(
                "evidence decision is invalid"
            )
        if (
            type(self.total_latency_ms) not in {int, float}
            or not math.isfinite(self.total_latency_ms)
            or self.total_latency_ms < 0
        ):
            raise ObservationValidationError("latency is invalid")
        if (
            type(self.llm_call_count) is not int
            or self.llm_call_count < 0
            or self.llm_call_count > 1
        ):
            raise ObservationValidationError("LLM call count is invalid")
        if type(self.fallback_used) is not bool:
            raise ObservationValidationError("fallback state is invalid")

    def to_payload(self) -> dict[str, object]:
        return {
            "evidence_count": self.evidence_count,
            "evidence_decision": self.evidence_decision,
            "fallback_used": self.fallback_used,
            "intent": self.intent,
            "llm_call_count": self.llm_call_count,
            "provider_statuses": dict(self.provider_statuses),
            "request_id": self.request_id,
            "retrieval_strategy": self.retrieval_strategy,
            "security_id": self.security_id,
            "total_latency_ms": self.total_latency_ms,
        }


@runtime_checkable
class ObservationSink(Protocol):
    def emit(self, observation: RequestObservation) -> None: ...


class JsonLogObservationSink:
    def __init__(self, logger: logging.Logger | None = None) -> None:
        if logger is not None and not isinstance(logger, logging.Logger):
            raise ObservationValidationError(
                "observation logger is invalid"
            )
        self._logger = logger or _project_logger()

    @property
    def logger_name(self) -> str:
        return self._logger.name

    def emit(self, observation: RequestObservation) -> None:
        if not isinstance(observation, RequestObservation):
            raise ObservationValidationError("observation is invalid")
        payload = json.dumps(
            observation.to_payload(),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        self._logger.info("%s", payload)


class InMemoryObservationSink:
    def __init__(self) -> None:
        self._observations: list[RequestObservation] = []

    @property
    def observations(self) -> tuple[RequestObservation, ...]:
        return tuple(self._observations)

    def emit(self, observation: RequestObservation) -> None:
        if not isinstance(observation, RequestObservation):
            raise ObservationValidationError("observation is invalid")
        self._observations.append(observation)


def fallback_used_for_generation_mode(generation_mode: object) -> bool:
    if (
        not isinstance(generation_mode, str)
        or generation_mode not in _GENERATION_MODES
    ):
        raise ObservationValidationError("generation mode is invalid")
    return generation_mode == "fixed_template"


def _validate_token(value: object, label: str) -> None:
    if not isinstance(value, str) or not _SAFE_TOKEN_RE.fullmatch(value):
        raise ObservationValidationError(f"{label} is invalid")


def _project_logger() -> logging.Logger:
    logger = logging.getLogger(_LOGGER_NAME)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


__all__ = [
    "InMemoryObservationSink",
    "JsonLogObservationSink",
    "ObservationSink",
    "ObservationValidationError",
    "RequestObservation",
    "fallback_used_for_generation_mode",
]
