from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from math import isfinite
from typing import Any

from pydantic import ValidationError

from app.core.models import (
    DateRange,
    Evidence,
    ProviderResult,
    QueryPlan,
    RetrievalResult,
    SecurityIdentifier,
)
from app.core.status import EvidenceDecisionStatus, ProviderStatus, RetrievalStatus
from app.evidence.freshness import (
    SEOUL_TZ,
    FreshnessResult,
    FreshnessWarning,
    FreshnessWindow,
)
from app.retrieval.retriever import LOW_RELEVANCE_THRESHOLD

_SUPPORTED_SOURCES = frozenset({"news", "disclosure", "research_report", "glossary"})
_SUPPORTED_SECURITY_IDS = frozenset({"KRX:005930", "KRX:000660", "KRX:005380"})
_SECURITY_REQUIRED_INTENTS = frozenset(
    {
        "recent_issue",
        "disclosure_summary",
        "research_report_summary",
        "risk_factors",
        "multi_source_summary",
    }
)
_PLAN_MATRIX: dict[str, tuple[tuple[str, ...], tuple[str, ...], bool]] = {
    "financial_term": (("glossary",), ("definition",), False),
    "disclosure_summary": (("disclosure",), ("disclosure",), True),
    "research_report_summary": (("research_report",), ("research_report",), True),
    "recent_issue": (("news",), ("recent_news",), True),
    "risk_factors": (
        ("news", "disclosure", "research_report"),
        ("risk", "recent_news", "disclosure", "research_report"),
        True,
    ),
    "multi_source_summary": (
        ("news", "disclosure", "research_report"),
        ("recent_news", "disclosure", "research_report"),
        True,
    ),
}
_CLARIFICATION_INTENTS = frozenset({*_PLAN_MATRIX, "prohibited_advice", "out_of_scope"})
_SUPPORTED_EVIDENCE_REQUIREMENTS = frozenset(
    {"definition", "disclosure", "research_report", "recent_news", "risk"}
)
_FAILURE_ERROR_CODES: dict[ProviderStatus, frozenset[str]] = {
    ProviderStatus.INVALID_QUERY: frozenset({"invalid_query"}),
    ProviderStatus.UNAUTHORIZED: frozenset({"unauthorized"}),
    ProviderStatus.RATE_LIMITED: frozenset({"rate_limited"}),
    ProviderStatus.TIMEOUT: frozenset({"attempt_timeout", "total_deadline_exceeded"}),
    ProviderStatus.PROVIDER_UNAVAILABLE: frozenset({"provider_unavailable"}),
    ProviderStatus.PARSE_ERROR: frozenset({"parse_error"}),
}
_FAILURE_MESSAGES = {
    "invalid_query": "provider rejected the query",
    "unauthorized": "provider authorization failed",
    "rate_limited": "provider rate limit reached",
    "attempt_timeout": "provider attempt timed out",
    "total_deadline_exceeded": "provider total deadline exceeded",
    "provider_unavailable": "provider unavailable",
    "parse_error": "provider response could not be parsed",
}
_WARNING_ORDER = (
    "missing_published_at",
    "future_published_at",
    "stale_news",
    "stale_research_report",
    "disclosure_window_extended",
    "insufficient_disclosure_coverage",
    "unresolved_disclosure_correction",
)
_WARNING_SOURCES: dict[str, frozenset[str]] = {
    "missing_published_at": frozenset({"news", "disclosure", "research_report"}),
    "future_published_at": frozenset({"news", "disclosure", "research_report"}),
    "stale_news": frozenset({"news"}),
    "stale_research_report": frozenset({"research_report"}),
    "disclosure_window_extended": frozenset({"disclosure"}),
    "insufficient_disclosure_coverage": frozenset({"disclosure"}),
    "unresolved_disclosure_correction": frozenset({"disclosure"}),
}
_LIMITING_WARNINGS = frozenset(
    {
        "stale_news",
        "stale_research_report",
        "insufficient_disclosure_coverage",
        "unresolved_disclosure_correction",
    }
)
_WINDOW_MODES = frozenset({"default", "fallback", "user", "none"})


class EvidencePolicyValidationError(ValueError):
    """Raised for malformed or inconsistent public policy inputs."""


@dataclass(frozen=True)
class EvidenceDecision:
    status: EvidenceDecisionStatus
    evidence: tuple[Evidence, ...]
    warnings: tuple[FreshnessWarning, ...]
    satisfied_sources: tuple[str, ...]
    missing_sources: tuple[str, ...]
    no_data_sources: tuple[str, ...]
    failed_sources: tuple[str, ...]


class EvidencePolicy:
    def evaluate(
        self,
        plan: QueryPlan,
        provider_results_by_source: Mapping[str, ProviderResult[Any]],
        freshness: FreshnessResult,
        retrieval: RetrievalResult,
    ) -> EvidenceDecision:
        canonical_plan = _canonical_plan(plan)
        canonical_providers = _canonical_provider_mapping(provider_results_by_source)
        clarification = canonical_plan.requires_clarification
        canonical_freshness = _canonical_freshness(
            freshness,
            canonical_plan,
            enforce_plan_contract=not clarification,
        )
        canonical_retrieval = _canonical_retrieval(retrieval)

        if clarification:
            status = (
                EvidenceDecisionStatus.BLOCKED
                if canonical_plan.intent == "prohibited_advice"
                else EvidenceDecisionStatus.NO_EVIDENCE
            )
            return _create_decision(
                canonical_plan,
                status=status,
                evidence=(),
                warnings=(),
                satisfied_sources=(),
                missing_sources=(),
                no_data_sources=(),
                failed_sources=(),
                limiting_warning=False,
            )

        _validate_retrieval_occurrences(canonical_freshness.evidence, canonical_retrieval.evidence)
        _validate_target_security(canonical_plan, canonical_retrieval.evidence)

        required_sources = tuple(canonical_plan.required_sources)
        returned_sources = {item.source_type for item in canonical_retrieval.evidence}
        satisfied_sources = tuple(source for source in required_sources if source in returned_sources)
        missing_sources = tuple(source for source in required_sources if source not in returned_sources)
        no_data_sources = tuple(
            source
            for source in required_sources
            if source in canonical_providers
            and _provider_status(canonical_providers[source]) == ProviderStatus.NO_DATA
        )
        failed_sources = tuple(
            source
            for source in required_sources
            if source in canonical_providers
            and _provider_status(canonical_providers[source]) in _FAILURE_ERROR_CODES
        )
        limiting_warning = any(
            warning.code in _LIMITING_WARNINGS and warning.source_type in required_sources
            for warning in canonical_freshness.warnings
        )

        retrieval_status = _retrieval_status(canonical_retrieval)
        if retrieval_status in {RetrievalStatus.EMPTY, RetrievalStatus.LOW_RELEVANCE}:
            status = (
                EvidenceDecisionStatus.PROVIDER_FAILED
                if failed_sources
                else EvidenceDecisionStatus.NO_EVIDENCE
            )
        elif missing_sources or no_data_sources or failed_sources or limiting_warning:
            status = EvidenceDecisionStatus.PARTIAL
        else:
            status = EvidenceDecisionStatus.COMPLETE

        return _create_decision(
            canonical_plan,
            status=status,
            evidence=tuple(canonical_retrieval.evidence),
            warnings=canonical_freshness.warnings,
            satisfied_sources=satisfied_sources,
            missing_sources=missing_sources,
            no_data_sources=no_data_sources,
            failed_sources=failed_sources,
            limiting_warning=limiting_warning,
        )


def _canonical_plan(value: object) -> QueryPlan:
    if not isinstance(value, QueryPlan):
        raise EvidencePolicyValidationError("plan must be a QueryPlan")
    try:
        values = _model_values(value, QueryPlan)
    except (AttributeError, TypeError):
        raise EvidencePolicyValidationError("plan must be a QueryPlan") from None

    security = values.get("security")
    if security is not None:
        security = _canonical_security(security)
    date_range = values.get("date_range")
    if date_range is not None:
        date_range = _canonical_date_range(date_range)
    values["security"] = security
    values["date_range"] = date_range

    try:
        canonical = QueryPlan.model_validate(values, strict=True)
    except (AttributeError, TypeError, ValueError, ValidationError):
        raise EvidencePolicyValidationError("plan must be a QueryPlan") from None

    if (
        not isinstance(canonical.intent, str)
        or not canonical.intent.strip()
        or type(canonical.requires_clarification) is not bool
    ):
        raise EvidencePolicyValidationError("plan must be a QueryPlan")
    _validate_string_list(canonical.required_sources, _SUPPORTED_SOURCES, "plan must be a QueryPlan")
    _validate_string_list(
        canonical.required_evidence,
        _SUPPORTED_EVIDENCE_REQUIREMENTS,
        "plan must be a QueryPlan",
    )
    _validate_plan_matrix(canonical)
    return canonical.model_copy(deep=True)


def _canonical_security(value: object) -> SecurityIdentifier:
    if not isinstance(value, SecurityIdentifier):
        raise EvidencePolicyValidationError("plan must be a QueryPlan")
    try:
        canonical = SecurityIdentifier.model_validate(
            _model_values(value, SecurityIdentifier),
            strict=True,
        )
    except (AttributeError, TypeError, ValueError, ValidationError):
        raise EvidencePolicyValidationError("plan must be a QueryPlan") from None

    required_strings = (
        canonical.market,
        canonical.ticker,
        canonical.security_name,
        canonical.security_type,
        canonical.corp_name,
    )
    if any(not isinstance(item, str) or not item.strip() for item in required_strings):
        raise EvidencePolicyValidationError("plan must be a QueryPlan")
    if canonical.corp_code is not None and (
        not isinstance(canonical.corp_code, str) or not canonical.corp_code.strip()
    ):
        raise EvidencePolicyValidationError("plan must be a QueryPlan")

    security_id = f"{canonical.market}:{canonical.ticker}"
    if security_id not in _SUPPORTED_SECURITY_IDS or canonical.security_type != "common_stock":
        raise EvidencePolicyValidationError("policy inputs are inconsistent")
    return canonical.model_copy(deep=True)


def _canonical_date_range(value: object) -> DateRange:
    if not isinstance(value, DateRange):
        raise EvidencePolicyValidationError("plan must be a QueryPlan")
    try:
        canonical = DateRange.model_validate(_model_values(value, DateRange), strict=True)
    except (AttributeError, TypeError, ValueError, ValidationError):
        raise EvidencePolicyValidationError("plan must be a QueryPlan") from None
    for boundary in (canonical.start, canonical.end):
        if boundary is not None and type(boundary) is not date:
            raise EvidencePolicyValidationError("plan must be a QueryPlan")
    return canonical.model_copy(deep=True)


def _validate_string_list(values: object, allowed: frozenset[str], error_message: str) -> None:
    if not isinstance(values, list):
        raise EvidencePolicyValidationError(error_message)
    if any(not isinstance(item, str) or not item.strip() or item not in allowed for item in values):
        raise EvidencePolicyValidationError(error_message)
    if len(values) != len(set(values)):
        raise EvidencePolicyValidationError(error_message)


def _validate_plan_matrix(plan: QueryPlan) -> None:
    if plan.requires_clarification:
        if (
            plan.intent not in _CLARIFICATION_INTENTS
            or plan.required_sources
            or plan.required_evidence
            or plan.security is not None
        ):
            raise EvidencePolicyValidationError("policy inputs are inconsistent")
        return

    contract = _PLAN_MATRIX.get(plan.intent)
    if contract is None:
        raise EvidencePolicyValidationError("policy inputs are inconsistent")
    expected_sources, expected_evidence, security_required = contract
    if (
        tuple(plan.required_sources) != expected_sources
        or tuple(plan.required_evidence) != expected_evidence
        or (security_required and plan.security is None)
    ):
        raise EvidencePolicyValidationError("policy inputs are inconsistent")


def _canonical_provider_mapping(value: object) -> dict[str, ProviderResult[Any]]:
    if not isinstance(value, Mapping):
        raise EvidencePolicyValidationError("provider results must be a source mapping")
    canonical: dict[str, ProviderResult[Any]] = {}
    for source, result in value.items():
        if not isinstance(source, str) or not source.strip() or source not in _SUPPORTED_SOURCES:
            raise EvidencePolicyValidationError("provider results are invalid")
        canonical[source] = _canonical_provider_result(result)
    return canonical


def _canonical_provider_result(value: object) -> ProviderResult[Any]:
    if not isinstance(value, ProviderResult):
        raise EvidencePolicyValidationError("provider results are invalid")
    try:
        values = _model_values(value, ProviderResult)
        status = ProviderStatus(values["status"])
        values["status"] = status
        canonical = ProviderResult.model_validate(values, strict=True)
    except (AttributeError, KeyError, TypeError, ValueError, ValidationError):
        raise EvidencePolicyValidationError("provider results are invalid") from None

    if type(canonical.from_cache) is not bool or not _is_aware_utc(canonical.fetched_at):
        raise EvidencePolicyValidationError("provider results are invalid")
    if status == ProviderStatus.OK:
        if canonical.data is None or canonical.error_code is not None:
            raise EvidencePolicyValidationError("provider results are invalid")
    elif status == ProviderStatus.NO_DATA:
        if canonical.data is not None or canonical.error_code is not None:
            raise EvidencePolicyValidationError("provider results are invalid")
    else:
        allowed_codes = _FAILURE_ERROR_CODES.get(status)
        if (
            allowed_codes is None
            or canonical.data is not None
            or canonical.error_code not in allowed_codes
            or canonical.message != _FAILURE_MESSAGES[canonical.error_code]
        ):
            raise EvidencePolicyValidationError("provider results are invalid")
    return canonical.model_copy(deep=True)


def _canonical_freshness(
    value: object,
    plan: QueryPlan,
    *,
    enforce_plan_contract: bool,
) -> FreshnessResult:
    if not isinstance(value, FreshnessResult):
        raise EvidencePolicyValidationError("freshness result is invalid")
    try:
        basis_at = value.basis_at
        basis_date = value.basis_date
        windows = value.windows
        evidence = value.evidence
        warnings = value.warnings
        latest_disclosure = value.latest_effective_disclosure_at
    except (AttributeError, TypeError):
        raise EvidencePolicyValidationError("freshness result is invalid") from None

    if (
        not _is_aware_utc(basis_at)
        or type(basis_date) is not date
        or basis_at.astimezone(SEOUL_TZ).date() != basis_date
        or not isinstance(windows, tuple)
        or not isinstance(evidence, tuple)
        or not isinstance(warnings, tuple)
    ):
        raise EvidencePolicyValidationError("freshness result is invalid")

    canonical_windows = _canonical_windows(windows)
    window_sources = tuple(window.source_type for window in canonical_windows)
    canonical_evidence = tuple(_canonical_evidence(item, "freshness result is invalid") for item in evidence)
    if any(item.source_type not in window_sources for item in canonical_evidence):
        raise EvidencePolicyValidationError("freshness result is invalid")
    canonical_warnings = _canonical_warnings(warnings, canonical_windows)

    if latest_disclosure is not None:
        if not _is_aware_utc(latest_disclosure) or "disclosure" not in window_sources:
            raise EvidencePolicyValidationError("freshness result is invalid")
        latest_disclosure = latest_disclosure.astimezone(timezone.utc)

    canonical = FreshnessResult(
        basis_at=basis_at.astimezone(timezone.utc),
        basis_date=basis_date,
        windows=canonical_windows,
        evidence=canonical_evidence,
        warnings=canonical_warnings,
        latest_effective_disclosure_at=latest_disclosure,
    )
    if enforce_plan_contract:
        _validate_freshness_plan_contract(canonical, plan)
    return canonical


def _canonical_windows(values: tuple[object, ...]) -> tuple[FreshnessWindow, ...]:
    canonical: list[FreshnessWindow] = []
    seen_sources: set[str] = set()
    for value in values:
        if not isinstance(value, FreshnessWindow):
            raise EvidencePolicyValidationError("freshness result is invalid")
        try:
            source = value.source_type
            start = value.start
            end = value.end
            applied_by = value.applied_by
        except (AttributeError, TypeError):
            raise EvidencePolicyValidationError("freshness result is invalid") from None
        if (
            not isinstance(source, str)
            or not source.strip()
            or source not in _SUPPORTED_SOURCES
            or source in seen_sources
            or not isinstance(applied_by, str)
            or applied_by not in _WINDOW_MODES
        ):
            raise EvidencePolicyValidationError("freshness result is invalid")
        if any(boundary is not None and type(boundary) is not date for boundary in (start, end)):
            raise EvidencePolicyValidationError("freshness result is invalid")
        if start is not None and end is not None and start > end:
            raise EvidencePolicyValidationError("freshness result is invalid")
        if applied_by == "none" and (source != "glossary" or start is not None or end is not None):
            raise EvidencePolicyValidationError("freshness result is invalid")
        if applied_by in {"default", "fallback"} and (start is None or end is None):
            raise EvidencePolicyValidationError("freshness result is invalid")
        if applied_by == "default" and source == "glossary":
            raise EvidencePolicyValidationError("freshness result is invalid")
        if applied_by == "fallback" and source != "disclosure":
            raise EvidencePolicyValidationError("freshness result is invalid")
        if applied_by == "user" and start is None and end is None:
            raise EvidencePolicyValidationError("freshness result is invalid")
        seen_sources.add(source)
        canonical.append(FreshnessWindow(source, start, end, applied_by))
    return tuple(canonical)


def _canonical_warnings(
    values: tuple[object, ...],
    windows: tuple[FreshnessWindow, ...],
) -> tuple[FreshnessWarning, ...]:
    source_order = {window.source_type: index for index, window in enumerate(windows)}
    warning_order = {code: index for index, code in enumerate(_WARNING_ORDER)}
    canonical: list[FreshnessWarning] = []
    seen: set[tuple[str, str]] = set()
    previous_rank: tuple[int, int] | None = None
    for value in values:
        if not isinstance(value, FreshnessWarning):
            raise EvidencePolicyValidationError("freshness result is invalid")
        try:
            code = value.code
            source = value.source_type
        except (AttributeError, TypeError):
            raise EvidencePolicyValidationError("freshness result is invalid") from None
        if (
            not isinstance(code, str)
            or not isinstance(source, str)
            or code not in _WARNING_SOURCES
            or source not in source_order
            or source not in _WARNING_SOURCES[code]
            or (code, source) in seen
        ):
            raise EvidencePolicyValidationError("freshness result is invalid")
        rank = (source_order[source], warning_order[code])
        if previous_rank is not None and rank <= previous_rank:
            raise EvidencePolicyValidationError("freshness result is invalid")
        previous_rank = rank
        seen.add((code, source))
        canonical.append(FreshnessWarning(code, source))  # type: ignore[arg-type]
    return tuple(canonical)


def _validate_freshness_plan_contract(freshness: FreshnessResult, plan: QueryPlan) -> None:
    windows = freshness.windows
    if tuple(window.source_type for window in windows) != tuple(plan.required_sources):
        raise EvidencePolicyValidationError("policy inputs are inconsistent")
    date_range = plan.date_range
    meaningful_range = date_range is not None and (date_range.start is not None or date_range.end is not None)

    if meaningful_range:
        assert date_range is not None
        if any(
            window.applied_by != "user"
            or window.start != date_range.start
            or window.end != date_range.end
            for window in windows
        ):
            raise EvidencePolicyValidationError("policy inputs are inconsistent")
        return

    for window in windows:
        if window.applied_by == "user":
            raise EvidencePolicyValidationError("policy inputs are inconsistent")
        if window.source_type == "glossary" and window.applied_by != "none":
            raise EvidencePolicyValidationError("policy inputs are inconsistent")
        if window.source_type in {"news", "research_report"} and window.applied_by != "default":
            raise EvidencePolicyValidationError("policy inputs are inconsistent")
        if window.source_type == "disclosure" and window.applied_by not in {"default", "fallback"}:
            raise EvidencePolicyValidationError("policy inputs are inconsistent")


def _canonical_retrieval(value: object) -> RetrievalResult:
    if not isinstance(value, RetrievalResult):
        raise EvidencePolicyValidationError("retrieval result is invalid")
    try:
        values = _model_values(value, RetrievalResult)
        raw_evidence = values["evidence"]
        if not isinstance(raw_evidence, list):
            raise TypeError
        evidence = [_canonical_evidence(item, "retrieval result is invalid") for item in raw_evidence]
        status = RetrievalStatus(values["status"])
        values["evidence"] = evidence
        values["status"] = status
        canonical = RetrievalResult.model_validate(values, strict=True)
    except (AttributeError, KeyError, TypeError, ValueError, ValidationError):
        raise EvidencePolicyValidationError("retrieval result is invalid") from None

    if not isinstance(canonical.strategy, str) or not canonical.strategy.strip() or type(canonical.low_relevance) is not bool:
        raise EvidencePolicyValidationError("retrieval result is invalid")

    if status == RetrievalStatus.OK:
        if not canonical.evidence or canonical.low_relevance:
            raise EvidencePolicyValidationError("retrieval result is invalid")
        for item in canonical.evidence:
            score = item.retrieval_score
            if (
                isinstance(score, bool)
                or not isinstance(score, (int, float))
                or not isfinite(score)
                or score < LOW_RELEVANCE_THRESHOLD
            ):
                raise EvidencePolicyValidationError("retrieval result is invalid")
    elif status == RetrievalStatus.EMPTY:
        if canonical.evidence or canonical.low_relevance:
            raise EvidencePolicyValidationError("retrieval result is invalid")
    elif canonical.evidence or not canonical.low_relevance:
        raise EvidencePolicyValidationError("retrieval result is invalid")
    return canonical.model_copy(deep=True)


def _canonical_evidence(value: object, error_message: str) -> Evidence:
    if not isinstance(value, Evidence):
        raise EvidencePolicyValidationError(error_message)
    try:
        canonical = Evidence.model_validate(_model_values(value, Evidence), strict=True)
    except (AttributeError, TypeError, ValueError, ValidationError):
        raise EvidencePolicyValidationError(error_message) from None
    required_strings = (
        canonical.evidence_id,
        canonical.document_id,
        canonical.source_type,
        canonical.title,
        canonical.snippet,
    )
    security_ids = (*canonical.subject_security_ids, *canonical.mentioned_security_ids)
    if (
        any(not isinstance(item, str) or not item.strip() for item in required_strings)
        or canonical.source_type not in _SUPPORTED_SOURCES
        or any(not isinstance(item, str) or not item.strip() for item in security_ids)
    ):
        raise EvidencePolicyValidationError(error_message)
    return canonical.model_copy(deep=True)


def _validate_retrieval_occurrences(
    freshness_evidence: tuple[Evidence, ...],
    retrieval_evidence: list[Evidence],
) -> None:
    available = [item.model_copy(deep=True, update={"retrieval_score": None}) for item in freshness_evidence]
    used = [False] * len(available)
    for selected in retrieval_evidence:
        comparable = selected.model_copy(deep=True, update={"retrieval_score": None})
        for index, candidate in enumerate(available):
            if not used[index] and comparable == candidate:
                used[index] = True
                break
        else:
            raise EvidencePolicyValidationError("policy inputs are inconsistent")


def _validate_target_security(plan: QueryPlan, evidence: list[Evidence]) -> None:
    if plan.intent not in _SECURITY_REQUIRED_INTENTS:
        return
    if plan.security is None:
        raise EvidencePolicyValidationError("policy inputs are inconsistent")
    target = f"{plan.security.market}:{plan.security.ticker}"
    for item in evidence:
        if item.scope == "company_specific":
            allowed = item.subject_security_ids == [target]
        elif item.scope == "multi_company":
            allowed = target in item.subject_security_ids
        else:
            allowed = target in item.mentioned_security_ids
        if not allowed:
            raise EvidencePolicyValidationError("policy inputs are inconsistent")


def _create_decision(
    plan: QueryPlan,
    *,
    status: EvidenceDecisionStatus,
    evidence: tuple[Evidence, ...],
    warnings: tuple[FreshnessWarning, ...],
    satisfied_sources: tuple[str, ...],
    missing_sources: tuple[str, ...],
    no_data_sources: tuple[str, ...],
    failed_sources: tuple[str, ...],
    limiting_warning: bool,
) -> EvidenceDecision:
    output_evidence = tuple(copy.deepcopy(item) for item in evidence)
    output_warnings = tuple(FreshnessWarning(item.code, item.source_type) for item in warnings)
    decision = EvidenceDecision(
        status=status,
        evidence=output_evidence,
        warnings=output_warnings,
        satisfied_sources=tuple(satisfied_sources),
        missing_sources=tuple(missing_sources),
        no_data_sources=tuple(no_data_sources),
        failed_sources=tuple(failed_sources),
    )
    _validate_decision_invariants(plan, decision, limiting_warning)
    return decision


def _validate_decision_invariants(
    plan: QueryPlan,
    decision: EvidenceDecision,
    limiting_warning: bool,
) -> None:
    if decision.status == EvidenceDecisionStatus.BLOCKED:
        if (
            plan.intent != "prohibited_advice"
            or not plan.requires_clarification
            or any(
                (
                    decision.evidence,
                    decision.warnings,
                    decision.satisfied_sources,
                    decision.missing_sources,
                    decision.no_data_sources,
                    decision.failed_sources,
                )
            )
        ):
            raise EvidencePolicyValidationError("policy inputs are inconsistent")
        return

    if plan.requires_clarification:
        if decision.status != EvidenceDecisionStatus.NO_EVIDENCE or any(
            (
                decision.evidence,
                decision.warnings,
                decision.satisfied_sources,
                decision.missing_sources,
                decision.no_data_sources,
                decision.failed_sources,
            )
        ):
            raise EvidencePolicyValidationError("policy inputs are inconsistent")
        return

    required = tuple(plan.required_sources)
    if (
        len(decision.satisfied_sources) != len(set(decision.satisfied_sources))
        or len(decision.missing_sources) != len(set(decision.missing_sources))
        or set(decision.satisfied_sources) & set(decision.missing_sources)
        or set(decision.satisfied_sources) | set(decision.missing_sources) != set(required)
        or not _is_ordered_subsequence(decision.satisfied_sources, required)
        or not _is_ordered_subsequence(decision.missing_sources, required)
        or not set(decision.no_data_sources).issubset(required)
        or not set(decision.failed_sources).issubset(required)
        or set(decision.no_data_sources) & set(decision.failed_sources)
        or not _is_ordered_subsequence(decision.no_data_sources, required)
        or not _is_ordered_subsequence(decision.failed_sources, required)
    ):
        raise EvidencePolicyValidationError("policy inputs are inconsistent")

    if decision.status == EvidenceDecisionStatus.COMPLETE:
        if (
            not decision.evidence
            or not required
            or decision.missing_sources
            or decision.no_data_sources
            or decision.failed_sources
            or limiting_warning
        ):
            raise EvidencePolicyValidationError("policy inputs are inconsistent")
    elif decision.status == EvidenceDecisionStatus.PARTIAL:
        if not decision.evidence or not (
            decision.missing_sources
            or decision.no_data_sources
            or decision.failed_sources
            or limiting_warning
        ):
            raise EvidencePolicyValidationError("policy inputs are inconsistent")
    elif decision.status == EvidenceDecisionStatus.PROVIDER_FAILED:
        if decision.evidence or not decision.failed_sources:
            raise EvidencePolicyValidationError("policy inputs are inconsistent")
    elif decision.status == EvidenceDecisionStatus.NO_EVIDENCE:
        if decision.evidence or decision.failed_sources:
            raise EvidencePolicyValidationError("policy inputs are inconsistent")
    else:
        raise EvidencePolicyValidationError("policy inputs are inconsistent")


def _provider_status(result: ProviderResult[Any]) -> ProviderStatus:
    try:
        return ProviderStatus(result.status)
    except (TypeError, ValueError):
        raise EvidencePolicyValidationError("provider results are invalid") from None


def _retrieval_status(result: RetrievalResult) -> RetrievalStatus:
    try:
        return RetrievalStatus(result.status)
    except (TypeError, ValueError):
        raise EvidencePolicyValidationError("retrieval result is invalid") from None


def _is_aware_utc(value: object) -> bool:
    if not isinstance(value, datetime) or value.tzinfo is None:
        return False
    try:
        return value.utcoffset() == timedelta(0)
    except (OverflowError, TypeError, ValueError):
        return False


def _is_ordered_subsequence(values: tuple[str, ...], expected: tuple[str, ...]) -> bool:
    positions = {value: index for index, value in enumerate(expected)}
    return all(
        value in positions and (index == 0 or positions[values[index - 1]] < positions[value])
        for index, value in enumerate(values)
    )


def _model_values(value: object, model_type: type) -> dict[str, object]:
    return {field_name: getattr(value, field_name) for field_name in model_type.model_fields}


__all__ = ["EvidenceDecision", "EvidencePolicy", "EvidencePolicyValidationError"]
