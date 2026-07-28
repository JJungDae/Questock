from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import warnings
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    _REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
    if str(_REPOSITORY_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPOSITORY_ROOT))

if __name__ == "__main__":
    warnings.filterwarnings(
        "ignore",
        message=(
            "Core Pydantic V1 functionality isn't compatible with "
            "Python 3.14 or greater."
        ),
        category=UserWarning,
        module=r"langchain_core\.output_parsers\.json",
    )

from app.answer.composer import AnswerComposer
from app.api.schemas import ChatRequest, ChatResponse
from app.core.models import FinancialDocument, QueryPlan
from app.core.status import ProviderStatus
from app.llm.base import LLMRequest, LLMResult, LLMStatus, create_llm_result
from app.providers.base import create_provider_result
from app.services.chat_service import ChatService
from app.services.source_gateway import (
    SourceGatewayResult,
    SourceGatewayTimeoutDescriptor,
)
from app.ui.projections import (
    project_baseline_answer,
    project_baseline_sources,
    project_process_stages,
)

DEFAULT_FIXTURE = Path("tests/fixtures/evaluation/m3_golden_cases.json")
BASIS_AT = datetime(2026, 7, 25, 3, tzinfo=UTC)
BUCKETS = frozenset(
    {
        "resolution_ambiguous",
        "intent_source",
        "retrieval_filter",
        "citation_sufficiency",
        "numeric_freshness",
        "safety_session_provider",
    }
)
CAPABILITIES = frozenset(
    {
        "CORE08",
        "A01",
        "A02",
        "A03",
        "A04",
        "A05-M",
        "A06-M",
        "A07-M",
        "A08-M",
        "A10",
        "A17-M",
        "SAFE01",
        "UI01",
    }
)
SCENARIOS = frozenset(
    {
        "ok",
        "wrong_company",
        "low_relevance",
        "no_data",
        "timeout",
        "rate_limited",
        "numeric_mismatch",
        "correction_unresolved",
        "report_bounded",
        "fake_locator",
        "unsafe_probability",
        "conflict_sources",
        "multi_source_fallback",
        "session_followup",
        "session_reset",
        "glossary_canonical",
        "glossary_alias",
        "glossary_unknown",
    }
)
EXPECTED_KEYS = frozenset(
    {
        "resolution_status",
        "intent",
        "required_sources",
        "status",
        "security_id",
        "evidence_source_types",
        "forbidden_security_ids",
        "forbidden_evidence_source_types",
        "provider_statuses",
        "retrieval_status",
        "generation_mode",
        "warnings",
        "fallback_required",
    }
)
CASE_KEYS = frozenset(
    {
        "case_id",
        "origin",
        "bucket",
        "taxonomy",
        "capabilities",
        "turns",
        "scenario_id",
        "coverage",
        "expected",
        "critical",
    }
)
SECURITY_IDS = frozenset({"KRX:005930", "KRX:000660", "KRX:005380"})
SOURCE_TYPES = frozenset({"news", "disclosure", "research_report", "glossary"})
PROVIDER_STATUSES = frozenset(item.value for item in ProviderStatus)
_LOCAL_PATH = re.compile(
    r"(?<![A-Za-z0-9_])[A-Za-z]:[\\/]|"
    r"(?:\\\\|//)[^\\/\s]+[\\/][^\\/\s]+|"
    r"(?:^|[\s\"'()=\[\]{},;])/(?![/\s])",
)
_PRIVATE_OUTPUT = re.compile(
    r"chain[- ]of[- ]thought|hidden reasoning|system prompt|"
    r"(?:api[-_]?key|client[-_]?secret|access[-_]?token)"
    r"\s*[:=]\s*\S+",
    re.IGNORECASE,
)
_HTTP_URL = re.compile(r"https?://[^\s\"']+", re.IGNORECASE)
_REPORT_SENTENCES = (
    "회사는 설비 투자 계획을 발표했다.",
    "신규 설비 가동은 4분기로 예정됐다.",
    "수요 회복은 성장 조건이다.",
    "원가 상승은 위험 조건이다.",
    "실제 수요는 추가 확인이 필요하다.",
)
_CONFLICT_SUMMARY = "긍정 요인과 위험 요인이 함께 확인됐다."
_CONFLICT_POSITIVE = "삼성전자 수요 증가는 긍정 요인이다."
_CONFLICT_RISK = "삼성전자 원가 상승은 위험 요인이다."
_CONFLICT_UNCERTAINTY = "삼성전자 실제 영향은 추가 확인이 필요하다."
_MULTI_SOURCE_SNIPPETS = {
    "news": "삼성전자 뉴스는 설비 투자 계획을 설명했다.",
    "disclosure": "삼성전자 공시는 투자 결정을 설명했다.",
    "research_report": "삼성전자 리포트는 수요 조건을 설명했다.",
}


class M3GateFixtureError(ValueError):
    """Raised when the executable golden fixture is malformed."""


@dataclass(frozen=True)
class GoldenCase:
    case_id: str
    origin: str
    bucket: str
    taxonomy: tuple[str, ...]
    capabilities: tuple[str, ...]
    turns: tuple[str, ...]
    scenario_id: str
    coverage: tuple[str, str] | None
    expected: Mapping[str, Any]
    critical: bool


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    passed: bool
    critical: bool
    failures: tuple[str, ...]
    taxonomy: tuple[str, ...]
    capabilities: tuple[str, ...]
    exposure_count: int


@dataclass(frozen=True)
class AggregateResult:
    passed: int
    failed: int
    total: int
    percentage: float
    failed_case_ids: tuple[str, ...]


@dataclass(frozen=True)
class GateReport:
    passed: int
    failed: int
    total: int
    percentage: float
    critical_passed: int
    critical_failed: int
    critical_total: int
    critical_percentage: float
    failed_case_ids: tuple[str, ...]
    critical_failed_case_ids: tuple[str, ...]
    exposure_count: int
    taxonomy: Mapping[str, AggregateResult]
    capabilities: Mapping[str, AggregateResult]
    case_results: tuple[CaseResult, ...]
    gate_passed: bool
    m3_12_status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "failed": self.failed,
            "total": self.total,
            "percentage": self.percentage,
            "critical": {
                "passed": self.critical_passed,
                "failed": self.critical_failed,
                "total": self.critical_total,
                "percentage": self.critical_percentage,
                "failed_case_ids": list(self.critical_failed_case_ids),
            },
            "failed_case_ids": list(self.failed_case_ids),
            "exposure_count": self.exposure_count,
            "taxonomy": {
                key: asdict(value)
                for key, value in sorted(self.taxonomy.items())
            },
            "capabilities": {
                key: asdict(value)
                for key, value in sorted(self.capabilities.items())
            },
            "case_results": [
                {
                    **asdict(result),
                    "failures": list(result.failures),
                    "taxonomy": list(result.taxonomy),
                    "capabilities": list(result.capabilities),
                }
                for result in self.case_results
            ],
            "gate_passed": self.gate_passed,
            "m3_12_status": self.m3_12_status,
        }


def load_golden_cases(
    path: str | Path = DEFAULT_FIXTURE,
) -> tuple[GoldenCase, ...]:
    try:
        raw_text = Path(path).read_text(encoding="utf-8")
        payload = json.loads(raw_text)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise M3GateFixtureError("M3 gate fixture is invalid") from None
    if (
        not isinstance(payload, dict)
        or set(payload) != {
            "schema_version",
            "m3_12_status",
            "migration_map",
            "cases",
        }
        or payload["schema_version"] != 1
        or payload["m3_12_status"] != "ACTIVATED_IN_M5"
        or not isinstance(payload["cases"], list)
    ):
        raise M3GateFixtureError("M3 gate fixture is invalid")

    cases = tuple(_parse_case(item) for item in payload["cases"])
    _validate_inventory(cases, payload["migration_map"])
    return cases


def run_gate(path: str | Path = DEFAULT_FIXTURE) -> GateReport:
    cases = load_golden_cases(path)
    try:
        results = tuple(asyncio.run(_run_case(case)) for case in cases)
    except Exception:
        raise M3GateFixtureError("M3 gate execution failed") from None
    return _build_report(results)


async def _run_case(case: GoldenCase) -> CaseResult:
    gateway = _ScenarioGateway(case.scenario_id)
    client = _DeterministicLLM(case.scenario_id)
    service = ChatService(
        source_gateway=gateway,
        composer=AnswerComposer(client),
        utc_now=lambda: BASIS_AT,
    )
    responses: list[ChatResponse] = []
    for index, turn in enumerate(case.turns):
        session_suffix = (
            f"-reset-{index}"
            if case.scenario_id == "session_reset" and index > 0
            else ""
        )
        responses.append(
            await service.chat(
                ChatRequest(
                    message=turn,
                    session_id=(
                        f"gate-{case.case_id.casefold()}{session_suffix}"
                    ),
                )
            )
        )
    response = responses[-1]
    failures = _evaluate_case(case, tuple(responses))
    exposure_count = _exposure_count(response)
    if exposure_count:
        failures.append("public_output_exposure")
    return CaseResult(
        case_id=case.case_id,
        passed=not failures,
        critical=case.critical,
        failures=tuple(failures),
        taxonomy=case.taxonomy,
        capabilities=case.capabilities,
        exposure_count=exposure_count,
    )


class _ScenarioGateway:
    timeout_descriptor = SourceGatewayTimeoutDescriptor(
        data_mode="recorded",
        live_connectivity_checked=False,
    )

    def __init__(self, scenario_id: str) -> None:
        self._scenario_id = scenario_id

    async def fetch(
        self,
        plan: QueryPlan,
        *,
        query: str,
        timeout_seconds: float,
    ) -> SourceGatewayResult:
        del timeout_seconds
        statuses = {
            source: self._status_for(source)
            for source in plan.required_sources
        }
        documents = tuple(
            _document(
                plan,
                source_type=source,
                query=query,
                scenario_id=self._scenario_id,
            )
            for source, status in statuses.items()
            if status == ProviderStatus.OK
        )
        documents_by_id = {
            document.document_id: document.model_copy(deep=True)
            for document in documents
        }
        results = {}
        for source, status in statuses.items():
            source_documents = [
                item.document_id
                for item in documents
                if item.source_type == source
            ]
            if status == ProviderStatus.OK:
                results[source] = create_provider_result(
                    status=status,
                    data={"document_ids": source_documents},
                    fetched_at=BASIS_AT,
                )
            elif status == ProviderStatus.NO_DATA:
                results[source] = create_provider_result(
                    status=status,
                    fetched_at=BASIS_AT,
                )
            else:
                results[source] = create_provider_result(
                    status=status,
                    error_code=(
                        "attempt_timeout"
                        if status == ProviderStatus.TIMEOUT
                        else status.value
                    ),
                    fetched_at=BASIS_AT,
                )
        return SourceGatewayResult(
            documents=documents,
            provider_results_by_source=results,
            documents_by_id=documents_by_id,
            data_mode="recorded",
            live_connectivity_checked=False,
        )

    def _status_for(self, source_type: str) -> ProviderStatus:
        if self._scenario_id == "no_data":
            return ProviderStatus.NO_DATA
        if self._scenario_id == "timeout":
            return ProviderStatus.TIMEOUT
        if self._scenario_id == "rate_limited":
            return ProviderStatus.RATE_LIMITED
        if (
            self._scenario_id == "report_bounded"
            and source_type != "research_report"
        ):
            return ProviderStatus.NO_DATA
        return ProviderStatus.OK


class _DeterministicLLM:
    def __init__(self, scenario_id: str) -> None:
        self._scenario_id = scenario_id

    async def complete(
        self,
        request: LLMRequest,
        *,
        timeout_seconds: float,
    ) -> LLMResult:
        del timeout_seconds
        evidence = _request_evidence(request)
        content = _llm_content(self._scenario_id, evidence)
        return create_llm_result(
            status=LLMStatus.OK,
            content=content,
            model="gemini/gemini-3.5-flash",
            provider="gemini",
            usage={"total_tokens": 1},
            finish_reason="stop",
            latency_ms=1,
        )


def _document(
    plan: QueryPlan,
    *,
    source_type: str,
    query: str,
    scenario_id: str,
) -> FinancialDocument:
    target = (
        f"{plan.security.market}:{plan.security.ticker}"
        if plan.security is not None
        else "KRX:005930"
    )
    attributed = _other_security(target) if scenario_id == "wrong_company" else target
    ticker = attributed.split(":", 1)[1]
    published_at = BASIS_AT - timedelta(days=1)
    text = _document_text(query, source_type, scenario_id)
    metadata: dict[str, Any] = {}

    if source_type == "news":
        document_id = f"document:news:{ticker}:{scenario_id}"
        source_url = f"https://news.example.test/{ticker}/{scenario_id}"
        locator: dict[str, Any] = {
            "provider": "recorded_news",
            "source_url": (
                None if scenario_id == "fake_locator" else source_url
            ),
            "published_at": published_at.isoformat(),
            "raw_index": 0,
            "query": query,
        }
        provider = "recorded_news"
    elif source_type == "disclosure":
        receipt_no = f"20260725{int(ticker):06d}"[-14:]
        document_id = f"disclosure:{receipt_no}"
        source_url = (
            "https://dart.fss.or.kr/dsaf001/main.do"
            f"?rcpNo={receipt_no}"
        )
        locator = {
            "provider": "recorded_disclosure",
            "receipt_no": receipt_no,
            "viewer_url": source_url,
        }
        metadata = {
            "is_correction": False,
            "has_subsequent_correction": (
                scenario_id == "correction_unresolved"
            ),
            "is_withdrawn": False,
            "correction_of": None,
        }
        provider = "recorded_disclosure"
    else:
        document_id = f"report:{ticker}:{scenario_id}:section-1"
        source_url = None
        locator = {
            "manifest_id": f"report-{ticker}-{scenario_id}",
            "document_id": document_id,
            "page_basis": "source_section_only",
            "page": None,
            "section": "검증 구간",
            "source_url": None,
            "source_asset_id": f"report-{ticker}-{scenario_id}",
        }
        metadata = {"external_llm_processing_allowed": True}
        provider = "manual_research_report"

    return FinancialDocument(
        document_id=document_id,
        source_type=source_type,
        provider=provider,
        primary_security_ids=[attributed],
        mentioned_security_ids=[],
        title=query if scenario_id != "low_relevance" else "일반 산업 자료",
        published_at=published_at,
        source_url=source_url,
        text=text,
        locator=locator,
        metadata=metadata,
        ingestion_version="m3-gate-v1",
    )


def _document_text(query: str, source_type: str, scenario_id: str) -> str:
    if scenario_id == "low_relevance":
        return "원자재 운송과 해외 산업 통계에 관한 일반 자료다."
    if scenario_id == "numeric_mismatch":
        return "삼성전자 HBM 출하량은 10만 개다."
    if scenario_id == "conflict_sources":
        return {
            "news": f"{_CONFLICT_SUMMARY} {_CONFLICT_POSITIVE}",
            "disclosure": _CONFLICT_RISK,
            "research_report": _CONFLICT_UNCERTAINTY,
        }[source_type]
    if scenario_id == "multi_source_fallback":
        return _MULTI_SOURCE_SNIPPETS[source_type]
    if scenario_id == "report_bounded" and source_type == "research_report":
        return " ".join(_REPORT_SENTENCES)
    source_labels = {
        "news": "뉴스",
        "disclosure": "공시",
        "research_report": "리포트",
    }
    return f"{query} {source_labels[source_type]}에서 확인된 사실이다."


def _other_security(value: str) -> str:
    return "KRX:000660" if value != "KRX:000660" else "KRX:005930"


def _request_evidence(
    request: LLMRequest,
) -> tuple[tuple[str, str, str], ...]:
    rendered = "\n".join(message.content for message in request.messages)
    items = []
    for block in rendered.split("\n\n"):
        evidence_id = None
        source_type = None
        snippet = None
        for line in block.splitlines():
            if line.startswith("Evidence ID: "):
                evidence_id = line.removeprefix("Evidence ID: ")
            elif line.startswith("Source type: "):
                source_type = line.removeprefix("Source type: ")
            elif line.startswith("Snippet: "):
                snippet = line.removeprefix("Snippet: ")
        if evidence_id and source_type and snippet:
            items.append((evidence_id, source_type, snippet))
    if not items:
        raise ValueError
    return tuple(items)


def _llm_content(
    scenario_id: str,
    evidence: tuple[tuple[str, str, str], ...],
) -> str:
    first_id, _source_type, first_snippet = evidence[0]
    evidence_by_source = {
        source_type: (evidence_id, snippet)
        for evidence_id, source_type, snippet in evidence
    }
    if scenario_id == "conflict_sources":
        claims = [
            {
                "claim_id": "summary",
                "section": "summary",
                "text": _CONFLICT_SUMMARY,
                "evidence_ids": [evidence_by_source["news"][0]],
            },
            {
                "claim_id": "positive",
                "section": "positive_factors",
                "text": _CONFLICT_POSITIVE,
                "evidence_ids": [evidence_by_source["news"][0]],
            },
            {
                "claim_id": "risk",
                "section": "risk_factors",
                "text": _CONFLICT_RISK,
                "evidence_ids": [evidence_by_source["disclosure"][0]],
            },
            {
                "claim_id": "uncertainty",
                "section": "uncertainty",
                "text": _CONFLICT_UNCERTAINTY,
                "evidence_ids": [evidence_by_source["research_report"][0]],
            },
        ]
    elif scenario_id == "multi_source_fallback":
        claims = [
            {
                "claim_id": "unsupported-causal",
                "section": "inference",
                "text": "따라서 실적은 반드시 개선될 것이다.",
                "evidence_ids": [
                    evidence_by_source[source_type][0]
                    for source_type in (
                        "news",
                        "disclosure",
                        "research_report",
                    )
                ],
            }
        ]
    elif scenario_id == "numeric_mismatch":
        claims = [
            {
                "claim_id": "summary",
                "section": "summary",
                "text": "삼성전자 HBM 출하량은 100만 개다.",
                "evidence_ids": [first_id],
            }
        ]
    elif scenario_id == "unsafe_probability":
        claims = [
            {
                "claim_id": "summary",
                "section": "summary",
                "text": "향후 주가가 상승할 확률은 80%입니다.",
                "evidence_ids": [first_id],
            }
        ]
    elif scenario_id == "report_bounded":
        report = next(item for item in evidence if item[1] == "research_report")
        sections = (
            "summary",
            "facts",
            "positive_factors",
            "risk_factors",
            "uncertainty",
        )
        claims = [
            {
                "claim_id": f"report-{index}",
                "section": section,
                "text": text,
                "evidence_ids": [report[0]],
            }
            for index, (section, text) in enumerate(
                zip(sections, _REPORT_SENTENCES, strict=True),
                start=1,
            )
        ]
    else:
        claims = [
            {
                "claim_id": "summary",
                "section": "summary",
                "text": first_snippet,
                "evidence_ids": [first_id],
            }
        ]
    return json.dumps({"claims": claims}, ensure_ascii=False)


def _evaluate_case(
    case: GoldenCase,
    responses: tuple[ChatResponse, ...],
) -> list[str]:
    response = responses[-1]
    expected = case.expected
    process = response.diagnostics_public
    actual_security_id = process.security.security_id
    actual_provider_statuses = {
        item.source_type: item.provider_status
        for item in process.sources
    }
    actual_evidence_sources = list(
        dict.fromkeys(item.source_type for item in response.evidence)
    )
    checks = {
        "resolution_status": (
            process.security.resolution_status
            == expected["resolution_status"]
        ),
        "intent": process.query_plan.intent == expected["intent"],
        "required_sources": (
            process.query_plan.required_sources
            == expected["required_sources"]
        ),
        "status": response.status == expected["status"],
        "security_id": actual_security_id == expected["security_id"],
        "evidence_source_types": (
            actual_evidence_sources == expected["evidence_source_types"]
        ),
        "provider_statuses": (
            actual_provider_statuses == expected["provider_statuses"]
        ),
        "retrieval_status": (
            process.evidence_pipeline.retrieval_status
            == expected["retrieval_status"]
        ),
        "generation_mode": (
            process.generation.mode == expected["generation_mode"]
        ),
        "warnings": all(
            warning in response.warnings for warning in expected["warnings"]
        ),
        "fallback_required": (
            (process.generation.mode != "llm")
            == expected["fallback_required"]
        ),
    }
    failures = [key for key, passed in checks.items() if not passed]

    visible_security_ids = {
        actual_security_id,
        *(
            security_id
            for item in response.evidence
            for security_id in (
                *item.subject_security_ids,
                *item.mentioned_security_ids,
            )
        ),
    }
    if any(
        security_id in visible_security_ids
        for security_id in expected["forbidden_security_ids"]
    ):
        failures.append("forbidden_security")
    if any(
        item.source_type in expected["forbidden_evidence_source_types"]
        for item in response.evidence
    ):
        failures.append("forbidden_evidence_source")
    if response.status == "complete" and not response.evidence:
        failures.append("unsupported_complete")
    if "A17-M" in case.capabilities and process.generation.mode == "llm":
        sections = response.answer_sections
        if not all(
            (
                sections.facts,
                sections.positive_factors,
                sections.risk_factors,
                sections.uncertainty,
            )
        ):
            failures.append("a17_report_structure")
    if case.origin == "B0-18" and (
        process.query_plan.intent != "price_move"
        or process.query_plan.required_sources
        != ["news", "disclosure", "research_report"]
    ):
        failures.append("m5_price_move_inactive")
    failures.extend(
        _evaluate_capability_behavior(case, responses)
    )
    return failures


def _evaluate_capability_behavior(
    case: GoldenCase,
    responses: tuple[ChatResponse, ...],
) -> list[str]:
    response = responses[-1]
    sections = response.answer_sections
    failures: list[str] = []
    source_types = [
        item.source_type for item in response.evidence
    ]

    if "A05-M" in case.capabilities and (
        case.scenario_id != "conflict_sources"
        or sections.positive_factors != [_CONFLICT_POSITIVE]
        or sections.risk_factors != [_CONFLICT_RISK]
        or sections.uncertainty != [_CONFLICT_UNCERTAINTY]
        or source_types
        != ["news", "disclosure", "research_report"]
    ):
        failures.append("a05_conflict_parallelism")

    if "A06-M" in case.capabilities:
        rendered = {
            *sections.summary,
            *sections.facts,
        }
        if (
            case.scenario_id != "multi_source_fallback"
            or len(source_types) != 3
            or set(source_types)
            != {"news", "disclosure", "research_report"}
            or rendered != set(_MULTI_SOURCE_SNIPPETS.values())
            or sections.interpretation
            or sections.inference
        ):
            failures.append("a06_source_specific_fallback")

    if "A07-M" in case.capabilities:
        rendered = response.answer_sections.model_dump_json()
        if (
            case.scenario_id == "numeric_mismatch"
            and ("100만" in rendered or "10만 개" not in rendered)
        ) or (
            case.scenario_id == "unsafe_probability"
            and "80%" in rendered
        ):
            failures.append("a07_numeric_validation")

    if "A08-M" in case.capabilities:
        first = responses[0].diagnostics_public.security
        final = response.diagnostics_public.security
        if case.scenario_id == "session_followup":
            if (
                len(responses) < 2
                or first.security_id is None
                or final.security_id != first.security_id
            ):
                failures.append("a08_context_inheritance")
        elif case.scenario_id == "session_reset":
            if (
                len(responses) < 2
                or first.security_id is None
                or final.security_id is not None
                or final.resolution_status != "not_found"
            ):
                failures.append("a08_session_reset")

    if "A10" in case.capabilities:
        if case.scenario_id in {"glossary_canonical", "glossary_alias"}:
            if (
                response.status != "complete"
                or source_types != ["glossary"]
            ):
                failures.append("a10_glossary_resolution")
        elif case.scenario_id == "glossary_unknown" and (
            response.status != "no_evidence"
            or response.evidence
        ):
            failures.append("a10_glossary_unknown")
    return failures


def _exposure_count(response: ChatResponse) -> int:
    views = (
        project_baseline_answer(response),
        project_baseline_sources(response),
        project_process_stages(response.diagnostics_public),
    )
    serialized = (
        response.model_dump_json()
        + "\n"
        + repr(views)
    )
    without_urls = _HTTP_URL.sub("https-url", serialized)
    return (
        int(_LOCAL_PATH.search(without_urls) is not None)
        + int(_PRIVATE_OUTPUT.search(serialized) is not None)
    )


def _parse_case(value: object) -> GoldenCase:
    if not isinstance(value, dict) or set(value) != CASE_KEYS:
        raise M3GateFixtureError("M3 gate fixture is invalid")
    case_id = value["case_id"]
    origin = value["origin"]
    bucket = value["bucket"]
    taxonomy = _string_tuple(value["taxonomy"])
    capabilities = _string_tuple(value["capabilities"])
    turns = _string_tuple(value["turns"])
    scenario_id = value["scenario_id"]
    expected = value["expected"]
    critical = value["critical"]
    if (
        not isinstance(case_id, str)
        or re.fullmatch(r"(?:B0|B7)-\d{2}", case_id) is None
        or not isinstance(origin, str)
        or (
            origin != "additional"
            and re.fullmatch(r"B0-\d{2}", origin) is None
        )
        or bucket not in BUCKETS
        or not taxonomy
        or any(item not in CAPABILITIES for item in capabilities)
        or scenario_id not in SCENARIOS
        or type(critical) is not bool
        or not isinstance(expected, dict)
        or set(expected) != EXPECTED_KEYS
    ):
        raise M3GateFixtureError("M3 gate fixture is invalid")
    _validate_expected(expected)
    coverage = value["coverage"]
    parsed_coverage = None
    if coverage is not None:
        if (
            not isinstance(coverage, dict)
            or set(coverage) != {"security_id", "source_type"}
            or coverage["security_id"] not in SECURITY_IDS
            or coverage["source_type"] not in SOURCE_TYPES - {"glossary"}
        ):
            raise M3GateFixtureError("M3 gate fixture is invalid")
        parsed_coverage = (
            coverage["security_id"],
            coverage["source_type"],
        )
    return GoldenCase(
        case_id=case_id,
        origin=origin,
        bucket=bucket,
        taxonomy=taxonomy,
        capabilities=capabilities,
        turns=turns,
        scenario_id=scenario_id,
        coverage=parsed_coverage,
        expected=expected,
        critical=critical,
    )


def _validate_expected(value: Mapping[str, Any]) -> None:
    string_keys = (
        "resolution_status",
        "intent",
        "status",
        "retrieval_status",
        "generation_mode",
    )
    list_keys = (
        "required_sources",
        "evidence_source_types",
        "forbidden_security_ids",
        "forbidden_evidence_source_types",
        "warnings",
    )
    if (
        any(
            not isinstance(value[key], str) or not value[key]
            for key in string_keys
        )
        or any(
            not isinstance(value[key], list)
            or any(
                not isinstance(item, str) or not item
                for item in value[key]
            )
            or len(value[key]) != len(set(value[key]))
            for key in list_keys
        )
        or value["security_id"] not in SECURITY_IDS | {None}
        or type(value["fallback_required"]) is not bool
        or not isinstance(value["provider_statuses"], dict)
        or any(
            source not in SOURCE_TYPES or status not in PROVIDER_STATUSES
            for source, status in value["provider_statuses"].items()
        )
    ):
        raise M3GateFixtureError("M3 gate fixture is invalid")


def _validate_inventory(
    cases: tuple[GoldenCase, ...],
    migration_map: object,
) -> None:
    expected_b0_ids = tuple(f"B0-{index:02d}" for index in range(1, 25))
    case_ids = [case.case_id for case in cases]
    if len(case_ids) != len(set(case_ids)) or len(cases) < 24:
        raise M3GateFixtureError("M3 gate fixture is invalid")
    if (
        not isinstance(migration_map, dict)
        or tuple(migration_map) != expected_b0_ids
        or tuple(migration_map.values()) != expected_b0_ids
    ):
        raise M3GateFixtureError("M3 gate fixture is invalid")
    origins = [case.origin for case in cases if case.origin != "additional"]
    if sorted(origins) != sorted(expected_b0_ids):
        raise M3GateFixtureError("M3 gate fixture is invalid")
    bucket_counts = Counter(case.bucket for case in cases)
    if any(bucket_counts[bucket] < 4 for bucket in BUCKETS):
        raise M3GateFixtureError("M3 gate fixture is invalid")
    capability_coverage = {
        capability
        for case in cases
        for capability in case.capabilities
    }
    if capability_coverage != CAPABILITIES:
        raise M3GateFixtureError("M3 gate fixture is invalid")
    _validate_capability_evidence(cases)
    expected_matrix = {
        (security_id, source_type)
        for security_id in SECURITY_IDS
        for source_type in ("news", "disclosure", "research_report")
    }
    actual_matrix = {
        case.coverage for case in cases if case.coverage is not None
    }
    if not expected_matrix.issubset(actual_matrix):
        raise M3GateFixtureError("M3 gate fixture is invalid")


def _validate_capability_evidence(cases: tuple[GoldenCase, ...]) -> None:
    required_scenarios = {
        "A05-M": {"conflict_sources"},
        "A06-M": {"multi_source_fallback"},
        "A07-M": {"numeric_mismatch", "unsafe_probability"},
        "A08-M": {"session_followup", "session_reset"},
        "A10": {
            "glossary_canonical",
            "glossary_alias",
            "glossary_unknown",
        },
    }
    by_capability = {
        capability: tuple(
            case for case in cases if capability in case.capabilities
        )
        for capability in required_scenarios
    }
    if any(
        {case.scenario_id for case in by_capability[capability]}
        != scenarios
        for capability, scenarios in required_scenarios.items()
    ):
        raise M3GateFixtureError("M3 gate fixture is invalid")

    three_sources = {"news", "disclosure", "research_report"}
    a05 = by_capability["A05-M"][0]
    a06 = by_capability["A06-M"][0]
    if (
        a05.expected["intent"] != "risk_factors"
        or set(a05.expected["evidence_source_types"]) != three_sources
        or len(a05.expected["evidence_source_types"]) != 3
        or a05.expected["generation_mode"] != "llm"
        or a06.expected["intent"] != "multi_source_summary"
        or set(a06.expected["evidence_source_types"]) != three_sources
        or len(a06.expected["evidence_source_types"]) != 3
        or a06.expected["generation_mode"] != "fixed_template"
        or a06.expected["fallback_required"] is not True
    ):
        raise M3GateFixtureError("M3 gate fixture is invalid")

    if any(
        case.expected["generation_mode"] != "fixed_template"
        or case.expected["fallback_required"] is not True
        for case in by_capability["A07-M"]
    ):
        raise M3GateFixtureError("M3 gate fixture is invalid")

    session_cases = {
        case.scenario_id: case for case in by_capability["A08-M"]
    }
    if (
        any(len(case.turns) < 2 for case in session_cases.values())
        or session_cases["session_followup"].expected["security_id"] is None
        or session_cases["session_reset"].expected["security_id"] is not None
        or session_cases["session_reset"].expected["resolution_status"]
        != "not_found"
    ):
        raise M3GateFixtureError("M3 gate fixture is invalid")

    glossary_cases = {
        case.scenario_id: case for case in by_capability["A10"]
    }
    if any(
        case.expected["intent"] != "financial_term"
        or case.expected["required_sources"] != ["glossary"]
        for case in glossary_cases.values()
    ) or any(
        glossary_cases[scenario].expected["evidence_source_types"]
        != ["glossary"]
        for scenario in {"glossary_canonical", "glossary_alias"}
    ) or (
        glossary_cases["glossary_unknown"].expected[
            "evidence_source_types"
        ]
        != []
    ):
        raise M3GateFixtureError("M3 gate fixture is invalid")


def _string_tuple(value: object) -> tuple[str, ...]:
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item.strip() for item in value)
        or len(value) != len(set(value))
    ):
        raise M3GateFixtureError("M3 gate fixture is invalid")
    return tuple(item.strip() for item in value)


def _build_report(results: tuple[CaseResult, ...]) -> GateReport:
    passed = sum(result.passed for result in results)
    failed_ids = tuple(
        result.case_id for result in results if not result.passed
    )
    critical = tuple(result for result in results if result.critical)
    critical_passed = sum(result.passed for result in critical)
    critical_failed_ids = tuple(
        result.case_id for result in critical if not result.passed
    )
    percentage = _percentage(passed, len(results))
    critical_percentage = _percentage(critical_passed, len(critical))
    exposure_count = sum(result.exposure_count for result in results)
    return GateReport(
        passed=passed,
        failed=len(results) - passed,
        total=len(results),
        percentage=percentage,
        critical_passed=critical_passed,
        critical_failed=len(critical) - critical_passed,
        critical_total=len(critical),
        critical_percentage=critical_percentage,
        failed_case_ids=failed_ids,
        critical_failed_case_ids=critical_failed_ids,
        exposure_count=exposure_count,
        taxonomy=_aggregate(results, "taxonomy"),
        capabilities=_aggregate(results, "capabilities"),
        case_results=results,
        gate_passed=(
            percentage >= 80.0
            and critical_percentage == 100.0
            and exposure_count == 0
        ),
        m3_12_status="ACTIVATED_IN_M5",
    )


def _aggregate(
    results: Sequence[CaseResult],
    field: str,
) -> dict[str, AggregateResult]:
    grouped: dict[str, list[CaseResult]] = defaultdict(list)
    for result in results:
        for label in getattr(result, field):
            grouped[label].append(result)
    output = {}
    for label, items in grouped.items():
        passed = sum(item.passed for item in items)
        failed_ids = tuple(
            item.case_id for item in items if not item.passed
        )
        output[label] = AggregateResult(
            passed=passed,
            failed=len(items) - passed,
            total=len(items),
            percentage=_percentage(passed, len(items)),
            failed_case_ids=failed_ids,
        )
    return output


def _percentage(passed: int, total: int) -> float:
    return round((passed / total) * 100, 2) if total else 0.0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Questock M3 gate")
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE))
    args = parser.parse_args(argv)
    try:
        report = run_gate(args.fixture)
    except M3GateFixtureError:
        print(
            json.dumps(
                {"error": "M3 gate could not be evaluated"},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 2
    print(
        json.dumps(
            report.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if report.gate_passed else 1


if __name__ == "__main__":
    sys.exit(main())
