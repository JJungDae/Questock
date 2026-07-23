from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import ValidationError
from pydantic_core import PydanticSerializationError

from app.core.models import Evidence
from app.retrieval.retriever import LOW_RELEVANCE_THRESHOLD

MAX_EVIDENCE_COUNT = 6
MAX_EVIDENCE_PER_SOURCE = 3
MAX_CONTEXT_TOKENS = 3000
MAX_CONTEXT_CHARS = 4500
MAX_LLM_CALLS = 2
TOKEN_ESTIMATOR_VERSION = "utf8-bytes-div-3-v1"

_SUPPORTED_SOURCES = frozenset(
    {"news", "disclosure", "research_report", "glossary"}
)
_INVALID_INPUT = "evidence context input is invalid"
_INVALID_LIMITS = "context budget limits are invalid"
_INVALID_CALL_BUDGET = "LLM call budget is invalid"
_INCONSISTENT_EVIDENCE = "evidence occurrences are inconsistent"
_INVALID_OUTPUT = "context budget output is invalid"


class ContextBudgetValidationError(ValueError):
    """Raised for malformed public budget inputs or invalid internal output."""


class LLMCallBudgetExceededError(ContextBudgetValidationError):
    """Raised when a request attempts more than its allowed LLM calls."""


@dataclass(frozen=True)
class ContextBudgetLimits:
    max_evidence_count: int = MAX_EVIDENCE_COUNT
    max_evidence_per_source: int = MAX_EVIDENCE_PER_SOURCE
    max_context_tokens: int = MAX_CONTEXT_TOKENS
    max_context_chars: int = MAX_CONTEXT_CHARS


@dataclass(frozen=True)
class ContextBudgetDiagnostics:
    input_count: int
    unique_count: int
    duplicate_drop_count: int
    source_cap_drop_count: int
    count_cap_drop_count: int
    context_drop_count: int
    selected_count: int
    estimated_context_tokens: int
    estimated_evidence_chars: int
    reserved_tokens: int
    max_evidence_count: int
    max_evidence_per_source: int
    max_context_tokens: int
    max_context_chars: int
    estimator_version: str
    budget_exhausted: bool


@dataclass(frozen=True)
class ContextBudgetResult:
    evidence: tuple[Evidence, ...]
    diagnostics: ContextBudgetDiagnostics


@dataclass(frozen=True)
class LLMCallBudgetSnapshot:
    calls_used: int
    calls_remaining: int
    max_calls: int


@dataclass(frozen=True)
class _CanonicalEvidence:
    evidence: Evidence
    full_payload: str
    content_fingerprint: str


@dataclass(frozen=True)
class _SelectionState:
    input_count: int
    unique_count: int
    after_source_cap_count: int
    after_count_cap_count: int


class LLMCallBudget:
    def __init__(self, max_calls: int = MAX_LLM_CALLS) -> None:
        if (
            type(max_calls) is not int
            or max_calls < 1
            or max_calls > MAX_LLM_CALLS
        ):
            raise ContextBudgetValidationError(_INVALID_CALL_BUDGET)
        self._max_calls = max_calls
        self._calls_used = 0

    def reserve_call(self) -> int:
        if self._calls_used >= self._max_calls:
            raise LLMCallBudgetExceededError("LLM call budget exceeded")
        self._calls_used += 1
        return self._calls_used

    def snapshot(self) -> LLMCallBudgetSnapshot:
        return LLMCallBudgetSnapshot(
            calls_used=self._calls_used,
            calls_remaining=self._max_calls - self._calls_used,
            max_calls=self._max_calls,
        )


def select_evidence_context(
    evidence: list[Evidence] | tuple[Evidence, ...],
    *,
    limits: ContextBudgetLimits = ContextBudgetLimits(),
    reserved_tokens: int = 0,
) -> ContextBudgetResult:
    canonical_limits = _validate_limits(limits)
    canonical_reserved_tokens = _validate_reserved_tokens(
        reserved_tokens,
        canonical_limits,
    )
    canonical_items = _canonical_evidence_sequence(evidence)
    _validate_repeated_ids(canonical_items)

    unique_items = _deduplicate(canonical_items)
    source_capped = _apply_source_cap(
        unique_items,
        canonical_limits.max_evidence_per_source,
    )
    count_capped = source_capped[: canonical_limits.max_evidence_count]
    selected = _apply_context_caps(
        count_capped,
        canonical_limits,
        canonical_reserved_tokens,
    )
    state = _SelectionState(
        input_count=len(canonical_items),
        unique_count=len(unique_items),
        after_source_cap_count=len(source_capped),
        after_count_cap_count=len(count_capped),
    )
    result = _build_result(
        selected,
        state,
        canonical_limits,
        canonical_reserved_tokens,
    )
    _audit_result(
        result,
        canonical_items,
        state,
        canonical_limits,
        canonical_reserved_tokens,
    )
    output = _copy_result(result)
    _audit_result(
        output,
        canonical_items,
        state,
        canonical_limits,
        canonical_reserved_tokens,
    )
    return output


def _validate_limits(value: object) -> ContextBudgetLimits:
    if type(value) is not ContextBudgetLimits:
        raise ContextBudgetValidationError(_INVALID_LIMITS)
    fields = (
        value.max_evidence_count,
        value.max_evidence_per_source,
        value.max_context_tokens,
        value.max_context_chars,
    )
    if (
        any(type(item) is not int for item in fields)
        or not 1 <= value.max_evidence_count <= MAX_EVIDENCE_COUNT
        or not 1 <= value.max_evidence_per_source <= MAX_EVIDENCE_PER_SOURCE
        or not 1 <= value.max_context_tokens <= MAX_CONTEXT_TOKENS
        or not 1 <= value.max_context_chars <= MAX_CONTEXT_CHARS
    ):
        raise ContextBudgetValidationError(_INVALID_LIMITS)
    return ContextBudgetLimits(*fields)


def _validate_reserved_tokens(
    value: object,
    limits: ContextBudgetLimits,
) -> int:
    if (
        type(value) is not int
        or value < 0
        or value > limits.max_context_tokens
    ):
        raise ContextBudgetValidationError(_INVALID_LIMITS)
    return value


def _canonical_evidence_sequence(value: object) -> tuple[_CanonicalEvidence, ...]:
    if type(value) not in {list, tuple}:
        raise ContextBudgetValidationError(_INVALID_INPUT)

    items: list[_CanonicalEvidence] = []
    for raw_item in value:
        if not isinstance(raw_item, Evidence):
            raise ContextBudgetValidationError(_INVALID_INPUT)
        try:
            canonical = Evidence.model_validate(
                _model_values(raw_item),
                strict=True,
            )
            _validate_evidence_fields(canonical)
            full_payload, content_fingerprint = _canonical_payloads(canonical)
        except (
            AttributeError,
            KeyError,
            OverflowError,
            PydanticSerializationError,
            RecursionError,
            TypeError,
            ValueError,
            ValidationError,
        ):
            raise ContextBudgetValidationError(_INVALID_INPUT) from None
        items.append(
            _CanonicalEvidence(
                evidence=canonical.model_copy(deep=True),
                full_payload=full_payload,
                content_fingerprint=content_fingerprint,
            )
        )
    return tuple(items)


def _model_values(value: Evidence) -> dict[str, Any]:
    return {
        field_name: getattr(value, field_name)
        for field_name in Evidence.model_fields
    }


def _validate_evidence_fields(value: Evidence) -> None:
    required_strings = (
        value.evidence_id,
        value.document_id,
        value.source_type,
        value.title,
        value.snippet,
    )
    score = value.retrieval_score
    if (
        any(not isinstance(item, str) or not item.strip() for item in required_strings)
        or value.source_type not in _SUPPORTED_SOURCES
        or type(score) not in {int, float}
        or not math.isfinite(score)
        or score < LOW_RELEVANCE_THRESHOLD
    ):
        raise ValueError


def _canonical_payloads(value: Evidence) -> tuple[str, str]:
    payload = value.model_dump(mode="json", warnings="error")
    full_payload = _canonical_json(payload, sort_keys=True)
    content_payload = dict(payload)
    content_payload.pop("evidence_id")
    content_payload.pop("retrieval_score")
    content_fingerprint = _canonical_json(content_payload, sort_keys=True)
    return full_payload, content_fingerprint


def _canonical_json(value: object, *, sort_keys: bool) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=sort_keys,
        separators=(",", ":"),
        allow_nan=False,
    )


def _validate_repeated_ids(items: tuple[_CanonicalEvidence, ...]) -> None:
    payload_by_id: dict[str, str] = {}
    for item in items:
        evidence_id = item.evidence.evidence_id
        previous = payload_by_id.get(evidence_id)
        if previous is not None and previous != item.full_payload:
            raise ContextBudgetValidationError(_INCONSISTENT_EVIDENCE)
        payload_by_id.setdefault(evidence_id, item.full_payload)


def _deduplicate(
    items: tuple[_CanonicalEvidence, ...],
) -> tuple[_CanonicalEvidence, ...]:
    seen: set[str] = set()
    selected: list[_CanonicalEvidence] = []
    for item in items:
        if item.content_fingerprint in seen:
            continue
        seen.add(item.content_fingerprint)
        selected.append(item)
    return tuple(selected)


def _apply_source_cap(
    items: tuple[_CanonicalEvidence, ...],
    max_per_source: int,
) -> tuple[_CanonicalEvidence, ...]:
    counts: Counter[str] = Counter()
    selected: list[_CanonicalEvidence] = []
    for item in items:
        source_type = item.evidence.source_type
        if counts[source_type] >= max_per_source:
            continue
        counts[source_type] += 1
        selected.append(item)
    return tuple(selected)


def _apply_context_caps(
    items: tuple[_CanonicalEvidence, ...],
    limits: ContextBudgetLimits,
    reserved_tokens: int,
) -> tuple[_CanonicalEvidence, ...]:
    selected = list(items)
    while selected:
        evidence = tuple(item.evidence for item in selected)
        estimated_tokens, estimated_chars = _estimate_projection(evidence)
        if (
            reserved_tokens + estimated_tokens <= limits.max_context_tokens
            and estimated_chars <= limits.max_context_chars
        ):
            break
        selected.pop()
    return tuple(selected)


def _projection(evidence: tuple[Evidence, ...]) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "evidence_id": item.evidence_id,
            "source_type": item.source_type,
            "title": item.title,
            "published_at": _timestamp(item.published_at),
            "subject_security_ids": list(item.subject_security_ids),
            "mentioned_security_ids": list(item.mentioned_security_ids),
            "scope": item.scope,
            "snippet": item.snippet,
        }
        for item in evidence
    )


def _timestamp(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _serialize_projection(evidence: tuple[Evidence, ...]) -> str:
    if not evidence:
        return ""
    return _canonical_json(_projection(evidence), sort_keys=False)


def _estimate_projection(evidence: tuple[Evidence, ...]) -> tuple[int, int]:
    serialized = _serialize_projection(evidence)
    if not serialized:
        return 0, 0
    byte_count = len(serialized.encode("utf-8"))
    return (byte_count + 2) // 3, len(serialized)


def _build_result(
    selected: tuple[_CanonicalEvidence, ...],
    state: _SelectionState,
    limits: ContextBudgetLimits,
    reserved_tokens: int,
) -> ContextBudgetResult:
    evidence = tuple(item.evidence.model_copy(deep=True) for item in selected)
    estimated_evidence_tokens, estimated_evidence_chars = _estimate_projection(evidence)
    selected_count = len(evidence)
    diagnostics = ContextBudgetDiagnostics(
        input_count=state.input_count,
        unique_count=state.unique_count,
        duplicate_drop_count=state.input_count - state.unique_count,
        source_cap_drop_count=state.unique_count - state.after_source_cap_count,
        count_cap_drop_count=(
            state.after_source_cap_count - state.after_count_cap_count
        ),
        context_drop_count=state.after_count_cap_count - selected_count,
        selected_count=selected_count,
        estimated_context_tokens=reserved_tokens + estimated_evidence_tokens,
        estimated_evidence_chars=estimated_evidence_chars,
        reserved_tokens=reserved_tokens,
        max_evidence_count=limits.max_evidence_count,
        max_evidence_per_source=limits.max_evidence_per_source,
        max_context_tokens=limits.max_context_tokens,
        max_context_chars=limits.max_context_chars,
        estimator_version=TOKEN_ESTIMATOR_VERSION,
        budget_exhausted=bool(state.after_count_cap_count and not evidence),
    )
    return ContextBudgetResult(evidence=evidence, diagnostics=diagnostics)


def _copy_result(value: ContextBudgetResult) -> ContextBudgetResult:
    return ContextBudgetResult(
        evidence=tuple(item.model_copy(deep=True) for item in value.evidence),
        diagnostics=ContextBudgetDiagnostics(**value.diagnostics.__dict__),
    )


def _audit_result(
    result: object,
    canonical_input: tuple[_CanonicalEvidence, ...],
    state: _SelectionState,
    limits: ContextBudgetLimits,
    reserved_tokens: int,
) -> None:
    try:
        if type(result) is not ContextBudgetResult or type(result.evidence) is not tuple:
            raise ValueError
        diagnostics = result.diagnostics
        if type(diagnostics) is not ContextBudgetDiagnostics:
            raise ValueError

        output = _canonical_evidence_sequence(result.evidence)
        full_payloads = tuple(item.full_payload for item in output)
        input_payloads = tuple(item.full_payload for item in canonical_input)
        if not _ordered_subsequence(full_payloads, input_payloads):
            raise ValueError
        content_fingerprints = tuple(item.content_fingerprint for item in output)
        if len(content_fingerprints) != len(set(content_fingerprints)):
            raise ValueError

        source_counts = Counter(item.evidence.source_type for item in output)
        if (
            len(output) > limits.max_evidence_count
            or any(
                count > limits.max_evidence_per_source
                for count in source_counts.values()
            )
        ):
            raise ValueError

        evidence = tuple(item.evidence for item in output)
        estimated_evidence_tokens, estimated_evidence_chars = _estimate_projection(
            evidence
        )
        expected_counts = (
            state.input_count,
            state.unique_count,
            state.input_count - state.unique_count,
            state.unique_count - state.after_source_cap_count,
            state.after_source_cap_count - state.after_count_cap_count,
            state.after_count_cap_count - len(output),
            len(output),
        )
        actual_counts = (
            diagnostics.input_count,
            diagnostics.unique_count,
            diagnostics.duplicate_drop_count,
            diagnostics.source_cap_drop_count,
            diagnostics.count_cap_drop_count,
            diagnostics.context_drop_count,
            diagnostics.selected_count,
        )
        diagnostic_numbers = (
            *actual_counts,
            diagnostics.estimated_context_tokens,
            diagnostics.estimated_evidence_chars,
            diagnostics.reserved_tokens,
            diagnostics.max_evidence_count,
            diagnostics.max_evidence_per_source,
            diagnostics.max_context_tokens,
            diagnostics.max_context_chars,
        )
        if (
            any(type(value) is not int or value < 0 for value in actual_counts)
            or any(type(value) is not int or value < 0 for value in diagnostic_numbers)
            or actual_counts != expected_counts
            or diagnostics.input_count
            != (
                diagnostics.duplicate_drop_count
                + diagnostics.source_cap_drop_count
                + diagnostics.count_cap_drop_count
                + diagnostics.context_drop_count
                + diagnostics.selected_count
            )
            or diagnostics.estimated_context_tokens
            != reserved_tokens + estimated_evidence_tokens
            or diagnostics.estimated_evidence_chars != estimated_evidence_chars
            or diagnostics.reserved_tokens != reserved_tokens
            or diagnostics.max_evidence_count != limits.max_evidence_count
            or diagnostics.max_evidence_per_source
            != limits.max_evidence_per_source
            or diagnostics.max_context_tokens != limits.max_context_tokens
            or diagnostics.max_context_chars != limits.max_context_chars
            or diagnostics.estimator_version != TOKEN_ESTIMATOR_VERSION
            or type(diagnostics.budget_exhausted) is not bool
            or diagnostics.budget_exhausted
            != bool(state.after_count_cap_count and not output)
            or diagnostics.estimated_context_tokens > limits.max_context_tokens
            or diagnostics.estimated_evidence_chars > limits.max_context_chars
        ):
            raise ValueError
    except (
        AttributeError,
        KeyError,
        OverflowError,
        PydanticSerializationError,
        RecursionError,
        TypeError,
        ValueError,
        ValidationError,
    ):
        raise ContextBudgetValidationError(_INVALID_OUTPUT) from None


def _ordered_subsequence(
    values: tuple[str, ...],
    expected: tuple[str, ...],
) -> bool:
    position = 0
    for value in values:
        while position < len(expected) and expected[position] != value:
            position += 1
        if position == len(expected):
            return False
        position += 1
    return True


__all__ = [
    "ContextBudgetDiagnostics",
    "ContextBudgetLimits",
    "ContextBudgetResult",
    "ContextBudgetValidationError",
    "LLMCallBudget",
    "LLMCallBudgetExceededError",
    "LLMCallBudgetSnapshot",
    "MAX_CONTEXT_CHARS",
    "MAX_CONTEXT_TOKENS",
    "MAX_EVIDENCE_COUNT",
    "MAX_EVIDENCE_PER_SOURCE",
    "MAX_LLM_CALLS",
    "TOKEN_ESTIMATOR_VERSION",
    "select_evidence_context",
]
