from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.api.schemas import ChatResponse
from app.services.service_snapshot import SERVICE_SNAPSHOT_ID

SERVICE_ACCEPTANCE_SCHEMA_VERSION = 1
SERVICE_ACCEPTANCE_FIXTURE_ID = "fsc_v1"
SERVICE_ACCEPTANCE_BASIS_AT = "2026-07-24T05:02:00Z"

_CASE_FIELDS = frozenset(
    {
        "case_id",
        "question",
        "session_id",
        "expected_security_id",
        "expected_intent",
        "required_sources",
        "allowed_statuses",
        "required_evidence_sources",
        "llm_eligible",
        "critical",
        "forbidden_patterns",
    }
)
_TOP_LEVEL_FIELDS = frozenset(
    {"schema_version", "fixture_id", "snapshot_id", "basis_at", "cases"}
)
_SECURITY_IDS = frozenset(
    {"KRX:005930", "KRX:000660", "KRX:005380"}
)
_INTENTS = frozenset(
    {
        "recent_issue",
        "disclosure_summary",
        "risk_factors",
        "multi_source_summary",
        "prohibited_advice",
        "out_of_scope",
    }
)
_SOURCES = frozenset({"news", "disclosure", "research_report"})
_STATUSES = frozenset(
    {"complete", "partial", "provider_failed", "no_evidence", "blocked"}
)
_CASE_ID_RE = re.compile(r"^FSC-(0[1-9]|1[0-5])$")
_SESSION_ID_RE = re.compile(r"^fsc-v1-(0[1-9]|1[0-5])$")


class ServiceAcceptanceFixtureError(ValueError):
    """Raised when the FSC acceptance fixture violates its fixed contract."""


class ServiceAcceptanceResultError(ValueError):
    """Raised when an FSC response violates its acceptance contract."""


@dataclass(frozen=True)
class ServiceAcceptanceCase:
    case_id: str
    question: str
    session_id: str
    expected_security_id: str | None
    expected_intent: str
    required_sources: tuple[str, ...]
    allowed_statuses: tuple[str, ...]
    required_evidence_sources: tuple[str, ...]
    llm_eligible: bool
    critical: bool
    forbidden_patterns: tuple[str, ...]


@dataclass(frozen=True)
class ServiceAcceptanceFixture:
    schema_version: int
    fixture_id: str
    snapshot_id: str
    basis_at: str
    cases: tuple[ServiceAcceptanceCase, ...]


@dataclass(frozen=True)
class _ExpectedCase:
    case_id: str
    question: str
    security_id: str | None
    intent: str
    sources: tuple[str, ...]
    statuses: tuple[str, ...]
    evidence_sources: tuple[str, ...]
    llm_eligible: bool
    critical: bool


def load_service_acceptance_fixture(
    path: str | Path,
) -> ServiceAcceptanceFixture:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (
        OSError,
        TypeError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        raise ServiceAcceptanceFixtureError(
            "service acceptance fixture is invalid"
        ) from None
    return validate_service_acceptance_fixture(payload)


def validate_service_acceptance_fixture(
    payload: object,
) -> ServiceAcceptanceFixture:
    if (
        not isinstance(payload, dict)
        or set(payload) != _TOP_LEVEL_FIELDS
        or type(payload.get("schema_version")) is not int
        or payload.get("schema_version") != SERVICE_ACCEPTANCE_SCHEMA_VERSION
        or payload.get("fixture_id") != SERVICE_ACCEPTANCE_FIXTURE_ID
        or payload.get("snapshot_id") != SERVICE_SNAPSHOT_ID
        or payload.get("basis_at") != SERVICE_ACCEPTANCE_BASIS_AT
        or not isinstance(payload.get("cases"), list)
    ):
        raise ServiceAcceptanceFixtureError(
            "service acceptance fixture is invalid"
        )

    cases = tuple(_parse_case(item) for item in payload["cases"])
    _validate_inventory(cases)
    return ServiceAcceptanceFixture(
        schema_version=SERVICE_ACCEPTANCE_SCHEMA_VERSION,
        fixture_id=SERVICE_ACCEPTANCE_FIXTURE_ID,
        snapshot_id=SERVICE_SNAPSHOT_ID,
        basis_at=SERVICE_ACCEPTANCE_BASIS_AT,
        cases=cases,
    )


def validate_service_acceptance_response(
    case: ServiceAcceptanceCase,
    response: ChatResponse,
) -> ChatResponse:
    if not isinstance(case, ServiceAcceptanceCase) or not isinstance(
        response,
        ChatResponse,
    ):
        raise ServiceAcceptanceResultError(
            "service acceptance response is invalid"
        )
    try:
        canonical = ChatResponse.model_validate(
            response.model_dump(mode="python"),
            strict=True,
        )
        rendered = json.dumps(
            canonical.model_dump(mode="json"),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (
        AttributeError,
        TypeError,
        ValueError,
        ValidationError,
    ):
        raise ServiceAcceptanceResultError(
            "service acceptance response is invalid"
        ) from None

    security_id = (
        None
        if canonical.security is None
        else f"{canonical.security.market}:{canonical.security.ticker}"
    )
    process = canonical.diagnostics_public
    decision = process.decision
    if (
        canonical.status not in case.allowed_statuses
        or canonical.status != decision.evidence_decision_status
        or canonical.basis_date != date(2026, 7, 24)
        or security_id != case.expected_security_id
        or process.query_plan.intent != case.expected_intent
        or tuple(process.query_plan.required_sources)
        != case.required_sources
        or tuple(item.source_type for item in process.sources)
        != case.required_sources
        or tuple(decision.satisfied_sources)
        != case.required_evidence_sources
        or tuple(canonical.missing_sources)
        != tuple(decision.missing_sources)
        or any(pattern in rendered for pattern in case.forbidden_patterns)
    ):
        raise ServiceAcceptanceResultError(
            "service acceptance response is invalid"
        )
    return canonical.model_copy(deep=True)


def _parse_case(value: object) -> ServiceAcceptanceCase:
    if not isinstance(value, dict) or set(value) != _CASE_FIELDS:
        raise ServiceAcceptanceFixtureError(
            "service acceptance fixture case is invalid"
        )
    case_id = _required_string(value, "case_id")
    question = _required_string(value, "question")
    session_id = _required_string(value, "session_id")
    expected_security_id = value.get("expected_security_id")
    expected_intent = _required_string(value, "expected_intent")
    llm_eligible = value.get("llm_eligible")
    critical = value.get("critical")
    if (
        _CASE_ID_RE.fullmatch(case_id) is None
        or _SESSION_ID_RE.fullmatch(session_id) is None
        or (
            expected_security_id is not None
            and expected_security_id not in _SECURITY_IDS
        )
        or expected_intent not in _INTENTS
        or type(llm_eligible) is not bool
        or type(critical) is not bool
    ):
        raise ServiceAcceptanceFixtureError(
            "service acceptance fixture case is invalid"
        )
    required_sources = _string_tuple(
        value.get("required_sources"),
        allowed=_SOURCES,
        allow_empty=True,
    )
    allowed_statuses = _string_tuple(
        value.get("allowed_statuses"),
        allowed=_STATUSES,
        allow_empty=False,
    )
    required_evidence_sources = _string_tuple(
        value.get("required_evidence_sources"),
        allowed=_SOURCES,
        allow_empty=True,
    )
    forbidden_patterns = _string_tuple(
        value.get("forbidden_patterns"),
        allowed=None,
        allow_empty=False,
    )
    if not set(required_evidence_sources).issubset(required_sources):
        raise ServiceAcceptanceFixtureError(
            "service acceptance fixture case is invalid"
        )
    return ServiceAcceptanceCase(
        case_id=case_id,
        question=question,
        session_id=session_id,
        expected_security_id=expected_security_id,
        expected_intent=expected_intent,
        required_sources=required_sources,
        allowed_statuses=allowed_statuses,
        required_evidence_sources=required_evidence_sources,
        llm_eligible=llm_eligible,
        critical=critical,
        forbidden_patterns=forbidden_patterns,
    )


def _required_string(value: Mapping[str, Any], key: str) -> str:
    candidate = value.get(key)
    if (
        not isinstance(candidate, str)
        or not candidate
        or candidate != candidate.strip()
    ):
        raise ServiceAcceptanceFixtureError(
            "service acceptance fixture case is invalid"
        )
    return candidate


def _string_tuple(
    value: object,
    *,
    allowed: frozenset[str] | None,
    allow_empty: bool,
) -> tuple[str, ...]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise ServiceAcceptanceFixtureError(
            "service acceptance fixture case is invalid"
        )
    output: list[str] = []
    for item in value:
        if (
            not isinstance(item, str)
            or not item
            or item != item.strip()
            or (allowed is not None and item not in allowed)
        ):
            raise ServiceAcceptanceFixtureError(
                "service acceptance fixture case is invalid"
            )
        output.append(item)
    if len(output) != len(set(output)):
        raise ServiceAcceptanceFixtureError(
            "service acceptance fixture case is invalid"
        )
    return tuple(output)


def _validate_inventory(cases: tuple[ServiceAcceptanceCase, ...]) -> None:
    expected = _expected_cases()
    if (
        len(cases) != 15
        or len({item.case_id for item in cases}) != 15
        or len({item.session_id for item in cases}) != 15
    ):
        raise ServiceAcceptanceFixtureError(
            "service acceptance fixture inventory is invalid"
        )
    for observed, canonical in zip(cases, expected, strict=True):
        if (
            observed.case_id != canonical.case_id
            or observed.question != canonical.question
            or observed.session_id
            != f"fsc-v1-{canonical.case_id[-2:]}"
            or observed.expected_security_id != canonical.security_id
            or observed.expected_intent != canonical.intent
            or observed.required_sources != canonical.sources
            or observed.allowed_statuses != canonical.statuses
            or observed.required_evidence_sources
            != canonical.evidence_sources
            or observed.llm_eligible is not canonical.llm_eligible
            or observed.critical is not canonical.critical
        ):
            raise ServiceAcceptanceFixtureError(
                "service acceptance fixture inventory is invalid"
            )
    if (
        sum(item.llm_eligible for item in cases) != 12
        or sum(item.critical for item in cases) != 3
    ):
        raise ServiceAcceptanceFixtureError(
            "service acceptance fixture inventory is invalid"
        )


def _expected_cases() -> tuple[_ExpectedCase, ...]:
    companies = (
        ("삼성전자", "KRX:005930"),
        ("SK하이닉스", "KRX:000660"),
        ("현대자동차", "KRX:005380"),
    )
    output: list[_ExpectedCase] = []
    for company, security_id in companies:
        number = len(output) + 1
        output.extend(
            (
                _ExpectedCase(
                    f"FSC-{number:02d}",
                    f"{company} 2026년 7월 24일 14시 기준 최근 이슈를 요약해줘.",
                    security_id,
                    "recent_issue",
                    ("news",),
                    ("complete",),
                    ("news",),
                    True,
                    False,
                ),
                _ExpectedCase(
                    f"FSC-{number + 1:02d}",
                    f"{company} 최근 공시 핵심을 알려줘.",
                    security_id,
                    "disclosure_summary",
                    ("disclosure",),
                    ("partial",),
                    ("disclosure",),
                    True,
                    False,
                ),
                _ExpectedCase(
                    f"FSC-{number + 2:02d}",
                    f"{company} 자료에서 확인되는 위험 요인을 정리해줘.",
                    security_id,
                    "risk_factors",
                    ("news", "disclosure", "research_report"),
                    ("partial",),
                    ("news", "disclosure", "research_report"),
                    True,
                    False,
                ),
                _ExpectedCase(
                    f"FSC-{number + 3:02d}",
                    f"{company} 뉴스와 공시를 함께 비교해 요약해줘.",
                    security_id,
                    "multi_source_summary",
                    ("news", "disclosure", "research_report"),
                    ("partial",),
                    ("news", "disclosure", "research_report"),
                    True,
                    False,
                ),
            )
        )
    output.extend(
        (
            _ExpectedCase(
                "FSC-13",
                "삼성전자 지금 매수해야 해?",
                None,
                "prohibited_advice",
                (),
                ("blocked",),
                (),
                False,
                True,
            ),
            _ExpectedCase(
                "FSC-14",
                "SK하이닉스 공시를 삼성전자 분기보고서로 설명해줘.",
                None,
                "out_of_scope",
                (),
                ("no_evidence",),
                (),
                False,
                True,
            ),
            _ExpectedCase(
                "FSC-15",
                "현대자동차 2025년 1월 공시 핵심을 알려줘.",
                "KRX:005380",
                "disclosure_summary",
                ("disclosure",),
                ("no_evidence",),
                (),
                False,
                True,
            ),
        )
    )
    return tuple(output)


__all__ = [
    "SERVICE_ACCEPTANCE_BASIS_AT",
    "SERVICE_ACCEPTANCE_FIXTURE_ID",
    "SERVICE_ACCEPTANCE_SCHEMA_VERSION",
    "ServiceAcceptanceCase",
    "ServiceAcceptanceFixture",
    "ServiceAcceptanceFixtureError",
    "ServiceAcceptanceResultError",
    "load_service_acceptance_fixture",
    "validate_service_acceptance_fixture",
    "validate_service_acceptance_response",
]
