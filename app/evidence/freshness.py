from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
import copy
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import re
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import ValidationError

from app.core.models import DateRange, Evidence, FinancialDocument, RetrievalRequest, ensure_evidence_matches_document

SEOUL_TZ = ZoneInfo("Asia/Seoul")

_SUPPORTED_SOURCES = frozenset({"news", "disclosure", "research_report"})
_DEFAULT_MAX_AGE_DAYS = {
    "news": 30,
    "disclosure": 180,
    "research_report": 180,
}
_DISCLOSURE_FALLBACK_MAX_AGE_DAYS = 365
_MIN_DISCLOSURE_COUNT = 5
_DISCLOSURE_ID = re.compile(r"^disclosure:(\d{14})$")
_RECEIPT = re.compile(r"^\d{14}$")
_WARNING_ORDER = (
    "missing_published_at",
    "future_published_at",
    "stale_news",
    "stale_research_report",
    "disclosure_window_extended",
    "insufficient_disclosure_coverage",
    "unresolved_disclosure_correction",
)

WarningCode = Literal[
    "missing_published_at",
    "future_published_at",
    "stale_news",
    "stale_research_report",
    "disclosure_window_extended",
    "insufficient_disclosure_coverage",
    "unresolved_disclosure_correction",
]
WindowSource = Literal["default", "fallback", "user", "none"]


class FreshnessValidationError(ValueError):
    """Raised for malformed public freshness-policy inputs."""


@dataclass(frozen=True)
class FreshnessWindow:
    source_type: str
    start: date | None
    end: date | None
    applied_by: WindowSource


@dataclass(frozen=True)
class FreshnessWarning:
    code: WarningCode
    source_type: str


@dataclass(frozen=True)
class FreshnessResult:
    basis_at: datetime
    basis_date: date
    windows: tuple[FreshnessWindow, ...]
    evidence: tuple[Evidence, ...]
    warnings: tuple[FreshnessWarning, ...]
    latest_effective_disclosure_at: datetime | None


@dataclass(frozen=True)
class _Candidate:
    evidence: Evidence
    document: FinancialDocument
    effective_at: datetime | None
    age_days: int | None
    date_eligible: bool


@dataclass(frozen=True)
class _DisclosureMetadata:
    is_correction: bool
    has_subsequent_correction: bool
    is_withdrawn: bool
    correction_of: str | None


def evaluate_freshness(
    evidence: Sequence[Evidence],
    request: RetrievalRequest,
    *,
    documents_by_id: Mapping[str, FinancialDocument],
    basis_at: datetime,
) -> FreshnessResult:
    """Evaluate deterministic source freshness after the caller's hard-filter stage."""
    raw_evidence = _validate_evidence_sequence(evidence)
    validated_request = _validate_request(request)
    canonical_basis_at = _validate_basis_at(basis_at)
    basis_date = canonical_basis_at.astimezone(SEOUL_TZ).date()
    raw_documents = _validate_document_mapping(documents_by_id)
    source_order = _unique_sources(validated_request.source_types)
    requested_sources = set(source_order)

    canonical_documents: dict[str, FinancialDocument] = {}
    candidates: list[_Candidate] = []
    warning_keys: set[tuple[str, str]] = set()

    for item in raw_evidence:
        validated_evidence = _canonical_evidence(item)
        linked_document = _linked_document(
            validated_evidence,
            raw_documents,
            canonical_documents,
        )
        _validate_link(validated_evidence, linked_document)
        if validated_evidence.source_type not in requested_sources:
            raise FreshnessValidationError("evidence source is not requested")

        effective_at = _effective_timestamp(validated_evidence, linked_document)
        date_eligible = True
        age_days: int | None = None
        if validated_evidence.source_type in _SUPPORTED_SOURCES:
            if effective_at is None:
                warning_keys.add(("missing_published_at", validated_evidence.source_type))
                date_eligible = False
            elif effective_at > canonical_basis_at:
                warning_keys.add(("future_published_at", validated_evidence.source_type))
                date_eligible = False
            else:
                age_days = (basis_date - effective_at.astimezone(SEOUL_TZ).date()).days

        candidates.append(
            _Candidate(
                evidence=validated_evidence,
                document=linked_document,
                effective_at=effective_at,
                age_days=age_days,
                date_eligible=date_eligible,
            )
        )

    disclosure_metadata = _validate_disclosure_metadata(
        candidates,
        raw_documents,
        canonical_documents,
    )
    active_edges = _build_active_correction_graph(candidates, disclosure_metadata)
    replaced_ids = set(active_edges.values())
    visible_candidates = [
        candidate
        for candidate in candidates
        if candidate.date_eligible
        and not _is_withdrawn(candidate, disclosure_metadata)
        and candidate.evidence.document_id not in replaced_ids
    ]

    meaningful_user_range = _meaningful_user_range(validated_request.date_range)
    windows, max_ages = _build_windows(
        source_order,
        validated_request.date_range,
        meaningful_user_range,
        basis_date,
        visible_candidates,
        warning_keys,
    )
    _add_stale_warnings(candidates, meaningful_user_range, warning_keys)
    retained = _apply_windows(
        visible_candidates,
        meaningful_user_range=meaningful_user_range,
        max_ages=max_ages,
    )
    _add_disclosure_coverage_warning(
        retained,
        source_order,
        meaningful_user_range,
        warning_keys,
    )

    unresolved = _has_unresolved_disclosure(
        retained,
        disclosure_metadata,
        active_edges,
        replaced_ids,
    )
    if unresolved and "disclosure" in requested_sources:
        warning_keys.add(("unresolved_disclosure_correction", "disclosure"))

    warnings = _ordered_warnings(source_order, warning_keys)
    output_evidence = tuple(copy.deepcopy(candidate.evidence) for candidate in retained)
    latest_disclosure_at = None if unresolved else _latest_disclosure_timestamp(retained)

    return FreshnessResult(
        basis_at=canonical_basis_at,
        basis_date=basis_date,
        windows=windows,
        evidence=output_evidence,
        warnings=warnings,
        latest_effective_disclosure_at=latest_disclosure_at,
    )


def _validate_evidence_sequence(value: object) -> list[Evidence]:
    if isinstance(value, (str, bytes, bytearray, Mapping)) or not isinstance(value, Sequence):
        raise FreshnessValidationError("evidence must be a sequence")
    items: list[Evidence] = []
    for item in value:
        if not isinstance(item, Evidence):
            raise FreshnessValidationError("evidence items are invalid")
        items.append(item)
    return items


def _validate_request(value: object) -> RetrievalRequest:
    if not isinstance(value, RetrievalRequest):
        raise FreshnessValidationError("request must be a RetrievalRequest")
    try:
        values = _model_values(value, RetrievalRequest)
        date_range = values.get("date_range")
        if date_range is not None:
            if not isinstance(date_range, DateRange):
                raise FreshnessValidationError("request must be a RetrievalRequest")
            values["date_range"] = _canonical_date_range(date_range)
        validated = RetrievalRequest.model_validate(values, strict=True)
    except (AttributeError, ValidationError):
        raise FreshnessValidationError("request must be a RetrievalRequest") from None
    if any(not isinstance(source, str) or not source.strip() for source in validated.source_types):
        raise FreshnessValidationError("request must be a RetrievalRequest")
    return validated


def _canonical_date_range(value: DateRange) -> DateRange:
    try:
        return DateRange.model_validate(_model_values(value, DateRange), strict=True)
    except (AttributeError, ValidationError):
        raise FreshnessValidationError("request must be a RetrievalRequest") from None


def _validate_basis_at(value: object) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise FreshnessValidationError("basis_at must be an aware UTC datetime")
    return value.astimezone(timezone.utc)


def _validate_document_mapping(value: object) -> Mapping[str, FinancialDocument]:
    if not isinstance(value, Mapping):
        raise FreshnessValidationError("documents_by_id must be a mapping")
    for key, document in value.items():
        if not isinstance(key, str) or not isinstance(document, FinancialDocument):
            raise FreshnessValidationError("documents_by_id is invalid")
        try:
            document_id = document.document_id
        except AttributeError:
            raise FreshnessValidationError("documents_by_id is invalid") from None
        if key != document_id:
            raise FreshnessValidationError("documents_by_id is invalid")
    return value


def _canonical_evidence(value: Evidence) -> Evidence:
    try:
        return Evidence.model_validate(_model_values(value, Evidence), strict=True)
    except (AttributeError, ValidationError):
        raise FreshnessValidationError("evidence items are invalid") from None


def _canonical_document(value: FinancialDocument) -> FinancialDocument:
    try:
        return FinancialDocument.model_validate(_model_values(value, FinancialDocument), strict=True)
    except (AttributeError, ValidationError):
        raise FreshnessValidationError("linked evidence is invalid") from None


def _model_values(value: object, model_type: type) -> dict[str, object]:
    return {field_name: getattr(value, field_name) for field_name in model_type.model_fields}


def _linked_document(
    evidence: Evidence,
    raw_documents: Mapping[str, FinancialDocument],
    canonical_documents: dict[str, FinancialDocument],
) -> FinancialDocument:
    raw_document = raw_documents.get(evidence.document_id)
    if raw_document is None:
        raise FreshnessValidationError("linked document is missing")
    return _cached_canonical_document(evidence.document_id, raw_document, canonical_documents)


def _cached_canonical_document(
    document_id: str,
    raw_document: FinancialDocument,
    cache: dict[str, FinancialDocument],
) -> FinancialDocument:
    if document_id not in cache:
        cache[document_id] = _canonical_document(raw_document)
    return cache[document_id]


def _validate_link(evidence: Evidence, document: FinancialDocument) -> None:
    if evidence.source_type != document.source_type:
        raise FreshnessValidationError("linked evidence is invalid")
    try:
        ensure_evidence_matches_document(evidence, document)
    except ValueError:
        raise FreshnessValidationError("linked evidence is invalid") from None


def _unique_sources(source_types: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(source_types))


def _effective_timestamp(evidence: Evidence, document: FinancialDocument) -> datetime | None:
    for value in (evidence.published_at, document.published_at):
        if _is_aware_datetime(value):
            try:
                return value.astimezone(timezone.utc)
            except (OverflowError, TypeError, ValueError):
                raise FreshnessValidationError("freshness timestamp is invalid") from None
    return None


def _is_aware_datetime(value: datetime | None) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _validate_disclosure_metadata(
    candidates: Sequence[_Candidate],
    raw_documents: Mapping[str, FinancialDocument],
    canonical_documents: dict[str, FinancialDocument],
) -> dict[str, _DisclosureMetadata]:
    metadata_by_id: dict[str, _DisclosureMetadata] = {}
    documents_by_input_id = {candidate.document.document_id: candidate.document for candidate in candidates}

    for candidate in candidates:
        if candidate.evidence.source_type != "disclosure":
            continue
        document = candidate.document
        if _DISCLOSURE_ID.fullmatch(document.document_id) is None:
            raise FreshnessValidationError("disclosure metadata is invalid")
        if document.document_id in metadata_by_id:
            continue

        metadata = document.metadata
        bool_values: dict[str, bool] = {}
        for key in ("is_correction", "has_subsequent_correction", "is_withdrawn"):
            raw_value = metadata.get(key, False)
            if type(raw_value) is not bool:
                raise FreshnessValidationError("disclosure metadata is invalid")
            bool_values[key] = raw_value

        correction_of_value = metadata.get("correction_of")
        if correction_of_value is not None:
            if not isinstance(correction_of_value, str) or _RECEIPT.fullmatch(correction_of_value) is None:
                raise FreshnessValidationError("disclosure metadata is invalid")
            if not bool_values["is_correction"]:
                raise FreshnessValidationError("disclosure metadata is invalid")
            target_id = f"disclosure:{correction_of_value}"
            if target_id == document.document_id:
                raise FreshnessValidationError("disclosure correction relation is invalid")
            target_document = documents_by_input_id.get(target_id)
            if target_document is None:
                raw_target = raw_documents.get(target_id)
                if raw_target is not None:
                    target_document = _cached_canonical_document(target_id, raw_target, canonical_documents)
            if target_document is not None:
                _validate_correction_target(document, target_document)

        metadata_by_id[document.document_id] = _DisclosureMetadata(
            is_correction=bool_values["is_correction"],
            has_subsequent_correction=bool_values["has_subsequent_correction"],
            is_withdrawn=bool_values["is_withdrawn"],
            correction_of=correction_of_value,
        )

    return metadata_by_id


def _validate_correction_target(
    correction: FinancialDocument,
    target: FinancialDocument,
) -> None:
    if (
        target.source_type != "disclosure"
        or _DISCLOSURE_ID.fullmatch(target.document_id) is None
        or set(correction.primary_security_ids) != set(target.primary_security_ids)
    ):
        raise FreshnessValidationError("disclosure correction relation is invalid")


def _build_active_correction_graph(
    candidates: Sequence[_Candidate],
    metadata_by_id: Mapping[str, _DisclosureMetadata],
) -> dict[str, str]:
    active_ids = {
        candidate.evidence.document_id
        for candidate in candidates
        if candidate.evidence.source_type == "disclosure"
        and candidate.date_eligible
        and not metadata_by_id[candidate.evidence.document_id].is_withdrawn
    }
    edges: dict[str, str] = {}
    for document_id in active_ids:
        metadata = metadata_by_id[document_id]
        if metadata.is_correction and metadata.correction_of is not None:
            edges[document_id] = f"disclosure:{metadata.correction_of}"
    _validate_acyclic_graph(edges, active_ids)
    return edges


def _validate_acyclic_graph(edges: Mapping[str, str], active_ids: set[str]) -> None:
    for start in edges:
        seen: set[str] = set()
        current = start
        while current in edges and current in active_ids:
            if current in seen:
                raise FreshnessValidationError("disclosure correction relation is invalid")
            seen.add(current)
            current = edges[current]


def _is_withdrawn(
    candidate: _Candidate,
    metadata_by_id: Mapping[str, _DisclosureMetadata],
) -> bool:
    if candidate.evidence.source_type != "disclosure":
        return False
    return metadata_by_id[candidate.evidence.document_id].is_withdrawn


def _meaningful_user_range(value: DateRange | None) -> bool:
    return value is not None and (value.start is not None or value.end is not None)


def _build_windows(
    source_order: Sequence[str],
    user_range: DateRange | None,
    meaningful_user_range: bool,
    basis_date: date,
    candidates: Sequence[_Candidate],
    warning_keys: set[tuple[str, str]],
) -> tuple[tuple[FreshnessWindow, ...], dict[str, int]]:
    windows: list[FreshnessWindow] = []
    max_ages = dict(_DEFAULT_MAX_AGE_DAYS)

    if meaningful_user_range:
        assert user_range is not None
        for source in source_order:
            windows.append(
                FreshnessWindow(
                    source_type=source,
                    start=user_range.start,
                    end=user_range.end,
                    applied_by="user",
                )
            )
        return tuple(windows), max_ages

    if "disclosure" in source_order:
        recent_disclosure_ids = {
            candidate.evidence.document_id
            for candidate in candidates
            if candidate.evidence.source_type == "disclosure"
            and candidate.age_days is not None
            and 0 <= candidate.age_days <= _DEFAULT_MAX_AGE_DAYS["disclosure"]
        }
        if len(recent_disclosure_ids) < _MIN_DISCLOSURE_COUNT:
            max_ages["disclosure"] = _DISCLOSURE_FALLBACK_MAX_AGE_DAYS
            warning_keys.add(("disclosure_window_extended", "disclosure"))

    for source in source_order:
        if source in _SUPPORTED_SOURCES:
            maximum_age = max_ages[source]
            windows.append(
                FreshnessWindow(
                    source_type=source,
                    start=basis_date - timedelta(days=maximum_age),
                    end=basis_date,
                    applied_by="fallback" if source == "disclosure" and maximum_age == 365 else "default",
                )
            )
        else:
            windows.append(
                FreshnessWindow(
                    source_type=source,
                    start=None,
                    end=None,
                    applied_by="none",
                )
            )
    return tuple(windows), max_ages


def _add_stale_warnings(
    candidates: Sequence[_Candidate],
    meaningful_user_range: bool,
    warning_keys: set[tuple[str, str]],
) -> None:
    if meaningful_user_range:
        return
    valid_ages: dict[str, list[int]] = defaultdict(list)
    for candidate in candidates:
        if (
            candidate.evidence.source_type in {"news", "research_report"}
            and candidate.date_eligible
            and candidate.age_days is not None
        ):
            valid_ages[candidate.evidence.source_type].append(candidate.age_days)

    if valid_ages["news"] and min(valid_ages["news"]) > 14:
        warning_keys.add(("stale_news", "news"))
    if valid_ages["research_report"] and min(valid_ages["research_report"]) > 180:
        warning_keys.add(("stale_research_report", "research_report"))


def _apply_windows(
    candidates: Sequence[_Candidate],
    *,
    meaningful_user_range: bool,
    max_ages: Mapping[str, int],
) -> list[_Candidate]:
    retained: list[_Candidate] = []
    for candidate in candidates:
        source = candidate.evidence.source_type
        if meaningful_user_range or source not in _SUPPORTED_SOURCES:
            retained.append(candidate)
            continue
        maximum_age = max_ages[source]
        if candidate.age_days is not None and 0 <= candidate.age_days <= maximum_age:
            retained.append(candidate)
    return retained


def _add_disclosure_coverage_warning(
    retained: Sequence[_Candidate],
    source_order: Sequence[str],
    meaningful_user_range: bool,
    warning_keys: set[tuple[str, str]],
) -> None:
    if meaningful_user_range or "disclosure" not in source_order:
        return
    retained_ids = {
        candidate.evidence.document_id
        for candidate in retained
        if candidate.evidence.source_type == "disclosure"
    }
    if len(retained_ids) < _MIN_DISCLOSURE_COUNT:
        warning_keys.add(("insufficient_disclosure_coverage", "disclosure"))


def _has_unresolved_disclosure(
    retained: Sequence[_Candidate],
    metadata_by_id: Mapping[str, _DisclosureMetadata],
    active_edges: Mapping[str, str],
    replaced_ids: set[str],
) -> bool:
    retained_ids = {
        candidate.evidence.document_id
        for candidate in retained
        if candidate.evidence.source_type == "disclosure"
    }
    for document_id in retained_ids:
        metadata = metadata_by_id[document_id]
        if metadata.has_subsequent_correction and document_id not in active_edges.values():
            return True
        if metadata.is_correction and metadata.correction_of is None:
            return True

    terminal_by_root: dict[str, set[str]] = defaultdict(set)
    for correction_id in active_edges:
        if correction_id in replaced_ids or correction_id not in retained_ids:
            continue
        terminal_by_root[_correction_root(correction_id, active_edges)].add(correction_id)
    return any(len(terminal_ids) > 1 for terminal_ids in terminal_by_root.values())


def _correction_root(correction_id: str, edges: Mapping[str, str]) -> str:
    current = correction_id
    while current in edges:
        current = edges[current]
    return current


def _latest_disclosure_timestamp(candidates: Sequence[_Candidate]) -> datetime | None:
    timestamps = [
        candidate.effective_at
        for candidate in candidates
        if candidate.evidence.source_type == "disclosure" and candidate.effective_at is not None
    ]
    return max(timestamps) if timestamps else None


def _ordered_warnings(
    source_order: Sequence[str],
    warning_keys: set[tuple[str, str]],
) -> tuple[FreshnessWarning, ...]:
    warning_order = {code: index for index, code in enumerate(_WARNING_ORDER)}
    ordered: list[FreshnessWarning] = []
    for source in source_order:
        codes = sorted(
            (code for code, warning_source in warning_keys if warning_source == source),
            key=warning_order.__getitem__,
        )
        ordered.extend(
            FreshnessWarning(code=code, source_type=source)  # type: ignore[arg-type]
            for code in codes
        )
    return tuple(ordered)


__all__ = [
    "FreshnessResult",
    "FreshnessValidationError",
    "FreshnessWarning",
    "FreshnessWindow",
    "evaluate_freshness",
]
