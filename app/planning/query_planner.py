from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

from app.core.models import DateRange, QueryPlan, SecurityIdentifier, SessionContext
from app.core.resolver import SecurityResolver, security_id_for
from app.core.status import ResolutionStatus

Intent = Literal[
    "recent_issue",
    "disclosure_summary",
    "research_report_summary",
    "risk_factors",
    "financial_term",
    "multi_source_summary",
    "prohibited_advice",
    "out_of_scope",
]

NEWS_SOURCE = "news"
DISCLOSURE_SOURCE = "disclosure"
RESEARCH_REPORT_SOURCE = "research_report"
GLOSSARY_SOURCE = "glossary"

RECENT_ISSUE = "recent_issue"
DISCLOSURE_SUMMARY = "disclosure_summary"
RESEARCH_REPORT_SUMMARY = "research_report_summary"
RISK_FACTORS = "risk_factors"
FINANCIAL_TERM = "financial_term"
MULTI_SOURCE_SUMMARY = "multi_source_summary"
PROHIBITED_ADVICE = "prohibited_advice"
OUT_OF_SCOPE = "out_of_scope"

SECURITY_REQUIRED_INTENTS = frozenset(
    {
        RECENT_ISSUE,
        DISCLOSURE_SUMMARY,
        RESEARCH_REPORT_SUMMARY,
        RISK_FACTORS,
        MULTI_SOURCE_SUMMARY,
    }
)

SOURCE_EVIDENCE_MATRIX: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    FINANCIAL_TERM: ((GLOSSARY_SOURCE,), ("definition",)),
    DISCLOSURE_SUMMARY: ((DISCLOSURE_SOURCE,), ("disclosure",)),
    RESEARCH_REPORT_SUMMARY: ((RESEARCH_REPORT_SOURCE,), ("research_report",)),
    RECENT_ISSUE: ((NEWS_SOURCE,), ("recent_news",)),
    RISK_FACTORS: (
        (NEWS_SOURCE, DISCLOSURE_SOURCE, RESEARCH_REPORT_SOURCE),
        ("risk", "recent_news", "disclosure", "research_report"),
    ),
    MULTI_SOURCE_SUMMARY: (
        (NEWS_SOURCE, DISCLOSURE_SOURCE, RESEARCH_REPORT_SOURCE),
        ("recent_news", "disclosure", "research_report"),
    ),
}

PARTICLES = (
    "\uc5d0\uc11c",
    "\uc740",
    "\ub294",
    "\uc774",
    "\uac00",
    "\uc744",
    "\ub97c",
    "\uc640",
    "\uacfc",
    "\uc5d0",
    "\uc758",
)

PROHIBITED_PATTERNS = (
    "\uc0ac\ub3c4 \ub3fc",
    "\uc0ac\uc57c",
    "\ud314\uc544",
    "\ud314\uae4c",
    "\ub9e4\uc218",
    "\ub9e4\ub3c4",
    "\ubcf4\uc720",
    "\ubaa9\ud45c\uac00",
    "\uc190\uc808",
    "\uc775\uc808",
    "\ub0b4\uc77c",
    "\uc624\ub97c\uae4c",
    "\ub5a8\uc5b4\uc9c8\uae4c",
    "\uc0c1\uc2b9 \ud655\ub960",
    "\ud558\ub77d \ud655\ub960",
    "\ud655\uc815 \uc218\uc775",
)
PRICE_MOVE_PATTERNS = (
    "\uc65c \uc62c\ub790",
    "\uc65c \ub0b4\ub838",
    "\uc65c \ub5a8\uc5b4",
    "\uc65c \uc0c1\uc2b9",
    "\uc65c \ud558\ub77d",
    "\uc65c \uc6c0\uc9c1",
    "\uc8fc\uac00 \uc774\uc720",
    "\uc0c1\uc2b9 \uc774\uc720",
    "\ud558\ub77d \uc774\uc720",
    "\uc624\ub978 \uc774\uc720",
    "\ub0b4\ub9b0 \uc774\uc720",
    "\uc8fc\uac00 \ubc30\uacbd",
    "\uc0c1\uc2b9 \ubc30\uacbd",
    "\ud558\ub77d \ubc30\uacbd",
)
FINANCIAL_TERM_CUES = (
    "\ubb50\uc57c",
    "\ubb34\uc5c7",
    "\ub73b",
    "\uc815\uc758",
    "\uc124\uba85",
    "\uc6a9\uc5b4",
)
FINANCIAL_TERM_MARKERS = (
    "per",
    "pbr",
    "roe",
    "eps",
    "\uc2dc\uac00\ucd1d\uc561",
    "\ub9e4\ucd9c",
    "\uc601\uc5c5\uc774\uc775",
    "\uc2dc\ucd1d",
    "\uc720\uc0c1\uc99d\uc790",
    "\uc804\ud658\uc0ac\ucc44",
    "\uacf5\uc2dc",
    "\ucee8\uc13c\uc11c\uc2a4",
    "\uc5f0\uacb0\uc7ac\ubb34\uc81c\ud45c",
    "\ubcc4\ub3c4\uc7ac\ubb34\uc81c\ud45c",
)
RISK_PATTERNS = (
    "\uc704\ud5d8 \uc694\uc778",
    "\uc704\ud5d8",
    "\ub9ac\uc2a4\ud06c",
    "\uc6b0\ub824",
    "\uc545\uc7ac",
)
MULTI_SOURCE_PATTERNS = (
    "\uc885\ud569",
    "\uc5ec\ub7ec \uc790\ub8cc",
    "\uc804\uccb4 \uc790\ub8cc",
    "\ub274\uc2a4\uc640 \uacf5\uc2dc",
    "\ub274\uc2a4\uc640 \ub9ac\ud3ec\ud2b8",
    "\uacf5\uc2dc\uc640 \ub9ac\ud3ec\ud2b8",
    "\ud55c\ubc88\uc5d0 \uc694\uc57d",
)
DISCLOSURE_PATTERNS = (
    "\uc815\uc815\uacf5\uc2dc",
    "\uc0ac\uc5c5\ubcf4\uace0\uc11c",
    "\ubc18\uae30\ubcf4\uace0\uc11c",
    "\ubd84\uae30\ubcf4\uace0\uc11c",
    "\uacf5\uc2dc",
)
RESEARCH_REPORT_PATTERNS = (
    "\ub9ac\uc11c\uce58",
    "\uc99d\uad8c\uc0ac \ub9ac\ud3ec\ud2b8",
    "\uc560\ub110\ub9ac\uc2a4\ud2b8 \ub9ac\ud3ec\ud2b8",
    "\ub9ac\ud3ec\ud2b8",
    "\ud22c\uc790\uc758\uacac \ubcf4\uace0\uc11c",
)
RECENT_ISSUE_PATTERNS = (
    "\ucd5c\uadfc \uc774\uc288",
    "\ucd5c\uadfc \ub274\uc2a4",
    "\ub274\uc2a4 \uc774\uc288",
    "\uc8fc\uc694 \uc774\uc288",
    "\uc774\uc288",
    "\ub274\uc2a4",
)
COMPARISON_PATTERNS = (
    "\ube44\uad50",
    "\uc21c\uc704",
    "\ub7ad\ud0b9",
    "\ub300\ube44",
    "\ub354 \ub098\uc544",
    " vs ",
    " versus ",
)

DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
RANGE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})\s*~\s*(\d{4}-\d{2}-\d{2})")
TOKEN_RE = re.compile(r"\S+")
UPPER_FOREIGN_RE = re.compile(r"^[A-Z]{1,5}([.\-][A-Z])?$")
HANGUL_RE = re.compile(r"[\uac00-\ud7a3]")
SECURITY_ENGLISH_HINTS = frozenset({"samsung", "electronics", "sk", "hynix", "hyundai", "motor"})
IGNORED_ASCII_SECURITY_WORDS = frozenset({"news", "risk", "report", "price", "issue", "per", "pbr", "roe", "eps"})
TRAILING_PUNCTUATION = ".,;:!?()[]{}\"'`"


@dataclass(frozen=True)
class _Candidate:
    text: str
    start: int
    end: int


@dataclass(frozen=True)
class _SecurityExtraction:
    security: SecurityIdentifier | None
    requires_clarification: bool
    multi_security: bool = False


@dataclass(frozen=True)
class _PeriodParse:
    date_range: DateRange | None
    suppress_session_fallback: bool


class QueryPlanner:
    def __init__(
        self,
        resolver: SecurityResolver | None = None,
        *,
        basis_date: date | None = None,
    ) -> None:
        if basis_date is None:
            basis_date = date.today()
        elif not isinstance(basis_date, date):
            raise TypeError("basis_date must be a date or None")
        self._resolver = resolver if resolver is not None else SecurityResolver()
        self._basis_date = basis_date

    def plan(
        self,
        query: str,
        *,
        session: SessionContext | None = None,
    ) -> QueryPlan:
        if not isinstance(query, str):
            raise TypeError("query must be a string")
        if session is not None and not isinstance(session, SessionContext):
            raise TypeError("session must be a SessionContext or None")

        normalized = _normalize_text(query)
        if not normalized:
            return _clarification_plan(OUT_OF_SCOPE)
        if _contains_any(normalized, PROHIBITED_PATTERNS):
            return _clarification_plan(PROHIBITED_ADVICE)
        if _contains_any(normalized, PRICE_MOVE_PATTERNS):
            return _clarification_plan(OUT_OF_SCOPE)

        intent = _classify_intent(normalized)
        if intent == OUT_OF_SCOPE:
            return _clarification_plan(OUT_OF_SCOPE)

        period = _parse_period(normalized, self._basis_date)
        extraction = self._extract_security(normalized)
        if extraction.multi_security:
            return _clarification_plan(OUT_OF_SCOPE, date_range=period.date_range)
        if extraction.requires_clarification:
            return _clarification_plan(intent, date_range=period.date_range)

        security = extraction.security
        if security is None and intent in SECURITY_REQUIRED_INTENTS and session is not None and session.current_security_id:
            security = self._resolve_session_security(session.current_security_id)
            if security is None:
                return _clarification_plan(intent, date_range=period.date_range)

        if intent in SECURITY_REQUIRED_INTENTS and security is None:
            return _clarification_plan(intent, date_range=period.date_range)

        date_range = period.date_range
        if (
            date_range is None
            and not period.suppress_session_fallback
            and _allows_session_date(intent)
            and session is not None
            and session.current_date_range is not None
        ):
            date_range = session.current_date_range.model_copy(deep=True)

        sources, evidence = SOURCE_EVIDENCE_MATRIX[intent]
        return QueryPlan(
            security=security,
            intent=intent,
            date_range=date_range,
            required_sources=list(sources),
            required_evidence=list(evidence),
            requires_clarification=False,
        )

    def _resolve_session_security(self, security_id: str) -> SecurityIdentifier | None:
        result = self._resolver.resolve(security_id)
        if result.status != ResolutionStatus.RESOLVED or result.security is None:
            return None
        return result.security

    def _extract_security(self, normalized_query: str) -> _SecurityExtraction:
        candidates = _candidate_spans(normalized_query)
        accepted: list[tuple[_Candidate, SecurityIdentifier]] = []
        issues: list[_Candidate] = []

        for candidate in candidates:
            if _is_contained_by_resolved(candidate, accepted):
                continue
            result = self._resolver.resolve(candidate.text)
            if result.status == ResolutionStatus.RESOLVED and result.security is not None:
                accepted.append((candidate, result.security))
            elif result.status in {ResolutionStatus.AMBIGUOUS, ResolutionStatus.UNSUPPORTED}:
                issues.append(candidate)

        accepted_by_id: dict[str, SecurityIdentifier] = {}
        for _candidate, security in accepted:
            accepted_by_id.setdefault(security_id_for(security), security)

        if len(accepted_by_id) > 1 or (_contains_any(normalized_query, COMPARISON_PATTERNS) and len(accepted_by_id) > 1):
            return _SecurityExtraction(None, True, multi_security=True)
        if accepted_by_id and issues:
            return _SecurityExtraction(None, True)
        if issues:
            return _SecurityExtraction(None, True)
        if accepted_by_id:
            return _SecurityExtraction(next(iter(accepted_by_id.values())), False)
        return _SecurityExtraction(None, False)


def _classify_intent(normalized_query: str) -> Intent:
    if _contains_any(normalized_query, FINANCIAL_TERM_CUES) and _contains_any(normalized_query, FINANCIAL_TERM_MARKERS):
        return FINANCIAL_TERM
    if _contains_any(normalized_query, RISK_PATTERNS):
        return RISK_FACTORS
    if _contains_any(normalized_query, MULTI_SOURCE_PATTERNS):
        return MULTI_SOURCE_SUMMARY
    if _contains_any(normalized_query, DISCLOSURE_PATTERNS):
        return DISCLOSURE_SUMMARY
    if _contains_any(normalized_query, RESEARCH_REPORT_PATTERNS):
        return RESEARCH_REPORT_SUMMARY
    if _contains_any(normalized_query, RECENT_ISSUE_PATTERNS):
        return RECENT_ISSUE
    return OUT_OF_SCOPE


def _parse_period(normalized_query: str, basis_date: date) -> _PeriodParse:
    if "\uc624\ub298" in normalized_query:
        return _PeriodParse(DateRange(start=basis_date, end=basis_date), True)
    if "\ucd5c\uadfc" in normalized_query:
        return _PeriodParse(None, True)

    ranges = list(RANGE_RE.finditer(normalized_query))
    if ranges:
        if len(ranges) != 1:
            return _PeriodParse(None, True)
        try:
            start = date.fromisoformat(ranges[0].group(1))
            end = date.fromisoformat(ranges[0].group(2))
            return _PeriodParse(DateRange(start=start, end=end), True)
        except ValueError:
            return _PeriodParse(None, True)

    dates = DATE_RE.findall(normalized_query)
    unique_dates = tuple(dict.fromkeys(dates))
    if len(unique_dates) > 1:
        return _PeriodParse(None, True)
    if len(unique_dates) == 1:
        try:
            parsed = date.fromisoformat(unique_dates[0])
            return _PeriodParse(DateRange(start=parsed, end=parsed), True)
        except ValueError:
            return _PeriodParse(None, True)
    return _PeriodParse(None, False)


def _candidate_spans(normalized_query: str) -> list[_Candidate]:
    tokens = list(TOKEN_RE.finditer(normalized_query))
    candidates: dict[tuple[int, int, str], _Candidate] = {}
    max_width = min(4, len(tokens))
    for width in range(max_width, 0, -1):
        for start_index in range(0, len(tokens) - width + 1):
            start = tokens[start_index].start()
            end = tokens[start_index + width - 1].end()
            raw = normalized_query[start:end]
            candidate_text = _clean_candidate(raw)
            if not _should_resolve_candidate(candidate_text, width):
                continue
            clean_start = start + len(raw) - len(raw.lstrip())
            key = (clean_start, clean_start + len(candidate_text), candidate_text)
            candidates[key] = _Candidate(text=candidate_text, start=key[0], end=key[1])
    return sorted(candidates.values(), key=lambda item: (item.end - item.start, len(item.text)), reverse=True)


def _clean_candidate(value: str) -> str:
    cleaned = value.strip().strip(TRAILING_PUNCTUATION)
    for particle in PARTICLES:
        if cleaned.endswith(particle) and len(cleaned) > len(particle):
            cleaned = cleaned[: -len(particle)].strip().strip(TRAILING_PUNCTUATION)
            break
    return cleaned


def _should_resolve_candidate(value: str, token_width: int) -> bool:
    if not value:
        return False
    if any(char.isdigit() for char in value) or ":" in value:
        return True
    if HANGUL_RE.search(value):
        return True
    words = value.split()
    if len(words) > 1:
        return any(word.lower().strip(TRAILING_PUNCTUATION) in SECURITY_ENGLISH_HINTS for word in words)
    if UPPER_FOREIGN_RE.fullmatch(value):
        return True
    if re.fullmatch(r"[a-z]{1,5}([.\-][a-z])?", value) and value not in IGNORED_ASCII_SECURITY_WORDS:
        return True
    if token_width > 1:
        return any(word.lower() in SECURITY_ENGLISH_HINTS for word in words)
    return False


def _is_contained_by_resolved(candidate: _Candidate, accepted: list[tuple[_Candidate, SecurityIdentifier]]) -> bool:
    return any(candidate.start >= accepted_candidate.start and candidate.end <= accepted_candidate.end for accepted_candidate, _ in accepted)


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return " ".join(normalized.split()).casefold()


def _contains_any(normalized_query: str, patterns: tuple[str, ...]) -> bool:
    return any(_normalize_text(pattern) in normalized_query for pattern in patterns)


def _allows_session_date(intent: str) -> bool:
    return intent in SECURITY_REQUIRED_INTENTS


def _clarification_plan(intent: str, date_range: DateRange | None = None) -> QueryPlan:
    return QueryPlan(
        security=None,
        intent=intent,
        date_range=date_range,
        required_sources=[],
        required_evidence=[],
        requires_clarification=True,
    )


__all__ = [
    "DISCLOSURE_SUMMARY",
    "FINANCIAL_TERM",
    "MULTI_SOURCE_SUMMARY",
    "OUT_OF_SCOPE",
    "PROHIBITED_ADVICE",
    "QueryPlanner",
    "RECENT_ISSUE",
    "RESEARCH_REPORT_SUMMARY",
    "RISK_FACTORS",
]
