from __future__ import annotations

import re
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from types import TracebackType
from typing import Any
from urllib.parse import urlsplit

from app.config import ConfigValidationError, ProviderConfig
from app.core.models import DateRange, FinancialDocument, ProviderResult, SecurityIdentifier
from app.core.resolver import SecurityResolver
from app.core.status import ProviderStatus, ResolutionStatus
from app.ingest.glossary import (
    GlossaryIngestValidationError,
    build_glossary_index,
    build_glossary_locator,
    evaluate_actual_glossary_coverage,
    load_glossary_entries,
    lookup_glossary_entry,
)
from app.ingest.reports import (
    ReportIngestValidationError,
    build_manual_research_documents,
    load_normalized_report_documents,
    load_report_manifest,
)
from app.providers.base import Provider, fetch_with_policy, security_id_for
from app.providers.disclosure import RecordedDisclosureProvider
from app.providers.news import RecordedNewsProvider

HEALTH_VERSION = "m1-08"
HEALTH_MODE = "fixture_readiness"
PHASE_SLICE_SCOPE = "representative_single_security"
REFERENCE_QUERY = "\uc0bc\uc131\uc804\uc790"
REFERENCE_SECURITY_ID = "KRX:005930"
REFERENCE_SECURITY_NAME = "\uc0bc\uc131\uc804\uc790"
REFERENCE_TICKER = "005930"
REFERENCE_DATE_RANGE = DateRange(start=date(2026, 7, 21), end=date(2026, 7, 21))
REFERENCE_REPORT_AS_OF_DATE = date(2026, 7, 22)
EXPECTED_DOCUMENT_COUNTS = {"news": 1, "disclosure": 1, "research_report": 2}
EXPECTED_SOURCE_COUNT = 3
EXPECTED_DOCUMENT_COUNT = 4

NEWS_FIXTURE_PATH = Path("tests/fixtures/news/naver_api_hub_synthetic.json")
DISCLOSURE_FIXTURE_PATH = Path("tests/fixtures/disclosures/opendart_list_synthetic.json")
REPORT_MANIFEST_PATH = Path("tests/fixtures/reports/report_manifest_synthetic.json")
REPORT_DOCUMENTS_PATH = Path("tests/fixtures/reports/normalized_report_synthetic.json")
GLOSSARY_PATH = Path("data/glossary.json")

SOURCE_ORDER = ("news", "disclosure", "research_report")
SAMPLE_KEYS = ("document_id", "source_type", "provider", "title")
FORBIDDEN_SAMPLE_KEYS = {"text", "locator", "metadata", "source_url"}
SECRET_SENTINELS = (
    "SENTINEL_SECRET_DO_NOT_LEAK",
    "SECRET_SENTINEL",
    "opendart-secret",
    "naver-secret",
    "naver-id",
)
WINDOWS_ABSOLUTE_PATH_RE = re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/]")
UNC_PATH_RE = re.compile(r"(?<!:)//[A-Za-z0-9_.-]+/|\\\\[A-Za-z0-9_.-]+[\\/]")
POSIX_ABSOLUTE_PATH_RE = re.compile(r"(^|[\s\"'(=])/(?!health(?:$|[\s`\"')\],.;:]))(?=[A-Za-z0-9._~-])[^\s\"'<>]*")
ALLOWED_ROUTE_TOKENS = {"/health", "GET /health"}

PhaseFetcher = Callable[..., Awaitable[ProviderResult[Any]]]
ReportLoader = Callable[[SecurityIdentifier], Sequence[FinancialDocument]]
GlossaryReadinessBuilder = Callable[[], dict[str, object]]


class PhaseSliceError(ValueError):
    """Raised when the M1-08 readiness payload cannot be built safely."""


class PublicPayloadSafetyError(PhaseSliceError):
    """Raised when a public payload would expose unsafe runtime data."""


@dataclass(frozen=True)
class PhaseSliceDependencies:
    resolver_factory: Callable[[], Any] | None = None
    news_provider_factory: Callable[[], Provider[Any]] | None = None
    disclosure_provider_factory: Callable[[], Provider[Any]] | None = None
    fetcher: PhaseFetcher | None = None
    report_loader: ReportLoader | None = None
    glossary_readiness_builder: GlossaryReadinessBuilder | None = None


def _default_resolver_factory() -> SecurityResolver:
    return SecurityResolver()


def _default_news_provider_factory() -> RecordedNewsProvider:
    return RecordedNewsProvider(fixture_path=NEWS_FIXTURE_PATH)


def _default_disclosure_provider_factory() -> RecordedDisclosureProvider:
    return RecordedDisclosureProvider(fixture_path=DISCLOSURE_FIXTURE_PATH)


def _source_template(status: str, mode: str, expected_count: int) -> dict[str, object]:
    result: dict[str, object] = {
        "status": status,
        "mode": mode,
        "document_count": 0,
        "expected_document_count": expected_count,
    }
    if mode == "recorded_fixture":
        result["live_connectivity_checked"] = False
    return result


def _provider_status_value(status: Any) -> str:
    return status.value if hasattr(status, "value") else str(status)


def _empty_sources() -> dict[str, dict[str, object]]:
    return {}


def _base_payload(status: str, sources: dict[str, object], phase_slice: dict[str, object]) -> dict[str, object]:
    payload: dict[str, object] = {
        "status": status,
        "version": HEALTH_VERSION,
        "mode": HEALTH_MODE,
        "live_connectivity_checked": False,
        "sources": sources,
        "phase_slice": phase_slice,
    }
    assert_public_payload_safe(payload)
    return payload


def build_error_payload(environment: dict[str, object] | None = None) -> dict[str, object]:
    payload: dict[str, object] = {
        "status": "error",
        "version": HEALTH_VERSION,
        "mode": HEALTH_MODE,
        "live_connectivity_checked": False,
        "environment": environment or {"status": "error"},
        "sources": {},
        "phase_slice": {
            "status": "error",
            "scope": PHASE_SLICE_SCOPE,
        },
    }
    assert_public_payload_safe(payload)
    return payload


def _security_failure_payload(query: str, result: Any) -> dict[str, object]:
    status = _provider_status_value(getattr(result, "status", "error"))
    phase_slice: dict[str, object] = {
        "status": status,
        "scope": PHASE_SLICE_SCOPE,
        "query": query,
        "source_calls_skipped": True,
    }
    candidates = getattr(result, "candidates", None)
    if candidates:
        phase_slice["candidate_security_ids"] = [security_id_for(candidate) for candidate in candidates]
    return _base_payload("error", _empty_sources(), phase_slice)


def _unsupported_fixture_scope_payload(query: str, security: SecurityIdentifier) -> dict[str, object]:
    return _base_payload(
        "error",
        _empty_sources(),
        {
            "status": "unsupported_for_fixture_slice",
            "scope": PHASE_SLICE_SCOPE,
            "query": query,
            "resolved_security_id": security_id_for(security),
            "required_reference_security_id": REFERENCE_SECURITY_ID,
            "source_calls_skipped": True,
        },
    )


def _selected_documents(
    documents: Any,
    *,
    selected_security_id: str,
    source_type: str,
) -> list[FinancialDocument]:
    if not isinstance(documents, list):
        return []
    selected = [
        document
        for document in documents
        if isinstance(document, FinancialDocument)
        and document.source_type == source_type
        and selected_security_id in document.primary_security_ids
    ]
    return sorted(selected, key=lambda document: document.document_id)


def _sample_for(document: FinancialDocument) -> dict[str, object]:
    return {key: getattr(document, key) for key in SAMPLE_KEYS}


def _source_from_provider_result(
    result: ProviderResult[Any] | None,
    *,
    source_type: str,
    expected_count: int,
    selected_security_id: str,
) -> tuple[dict[str, object], list[FinancialDocument]]:
    if result is None:
        source = _source_template("provider_unavailable", "recorded_fixture", expected_count)
        return source, []

    status = _provider_status_value(result.status)
    documents = _selected_documents(
        result.data if result.status == ProviderStatus.OK else [],
        selected_security_id=selected_security_id,
        source_type=source_type,
    )
    source_status = status
    if result.status == ProviderStatus.OK and len(documents) != expected_count:
        source_status = "unexpected_document_count"
    source = _source_template(source_status, "recorded_fixture", expected_count)
    source["document_count"] = len(documents)
    return source, documents


def _source_from_local_documents(
    documents: Sequence[FinancialDocument],
    *,
    source_type: str,
    mode: str,
    expected_count: int,
    selected_security_id: str,
) -> tuple[dict[str, object], list[FinancialDocument]]:
    selected = sorted(
        [
            document
            for document in documents
            if isinstance(document, FinancialDocument)
            and document.source_type == source_type
            and selected_security_id in document.primary_security_ids
        ],
        key=lambda document: document.document_id,
    )
    status = "ok" if len(selected) == expected_count else "unexpected_document_count"
    source = _source_template(status, mode, expected_count)
    source["document_count"] = len(selected)
    return source, selected


async def _fetch_provider_source(
    provider: Provider[Any],
    *,
    source_type: str,
    security: SecurityIdentifier,
    config: ProviderConfig,
    fetcher: PhaseFetcher,
) -> tuple[dict[str, object], list[FinancialDocument]]:
    try:
        result = await fetcher(
            provider=provider,
            security=security,
            config=config,
            query=None,
            date_range=REFERENCE_DATE_RANGE,
            cache=None,
        )
    except Exception:
        result = None
    return _source_from_provider_result(
        result,
        source_type=source_type,
        expected_count=EXPECTED_DOCUMENT_COUNTS[source_type],
        selected_security_id=security_id_for(security),
    )


def _default_report_loader(security: SecurityIdentifier) -> list[FinancialDocument]:
    manifest = load_report_manifest(REPORT_MANIFEST_PATH)
    if manifest.security_id != security_id_for(security):
        raise ReportIngestValidationError("report manifest security mismatch")
    bundle = load_normalized_report_documents(REPORT_DOCUMENTS_PATH)
    documents = build_manual_research_documents(
        manifest,
        bundle,
        mode="synthetic_unit",
        as_of_date=REFERENCE_REPORT_AS_OF_DATE,
    )
    if any(security_id_for(security) not in document.primary_security_ids for document in documents):
        raise ReportIngestValidationError("report document security mismatch")
    return documents


def _default_glossary_readiness_builder() -> dict[str, object]:
    coverage = evaluate_actual_glossary_coverage(GLOSSARY_PATH)
    bundle = load_glossary_entries(GLOSSARY_PATH)
    index = build_glossary_index(bundle, mode="corpus")
    lookup = lookup_glossary_entry(index, "PER")
    locator_section: str | None = None
    entry_id: str | None = None
    if lookup.status == "found" and lookup.entry is not None:
        locator = build_glossary_locator(bundle, lookup.entry, "definition")
        locator_section = locator.section
        entry_id = locator.entry_id
    status = (
        "ok"
        if coverage.actual_coverage_evaluated and coverage.meets_minimum and lookup.status == "found" and locator_section == "definition"
        else "not_ready"
    )
    return {
        "status": status,
        "mode": "approved_local_corpus",
        "actual_coverage": coverage.actual_coverage_evaluated,
        "meets_minimum": coverage.meets_minimum,
        "lookup_status": lookup.status,
        "entry_id": entry_id,
        "locator_section": locator_section,
    }


def _resolve_dependencies(dependencies: PhaseSliceDependencies | None) -> PhaseSliceDependencies:
    return dependencies or PhaseSliceDependencies()


async def build_phase_slice(
    query: str,
    *,
    config: ProviderConfig,
    dependencies: PhaseSliceDependencies | None = None,
) -> dict[str, object]:
    deps = _resolve_dependencies(dependencies)
    resolver_factory = deps.resolver_factory or _default_resolver_factory
    news_provider_factory = deps.news_provider_factory or _default_news_provider_factory
    disclosure_provider_factory = deps.disclosure_provider_factory or _default_disclosure_provider_factory
    fetcher = deps.fetcher or fetch_with_policy
    report_loader = deps.report_loader or _default_report_loader
    glossary_builder = deps.glossary_readiness_builder or _default_glossary_readiness_builder

    try:
        resolver = resolver_factory()
        resolution = resolver.resolve(query)
    except Exception:
        return _base_payload(
            "error",
            _empty_sources(),
            {"status": "resolver_error", "scope": PHASE_SLICE_SCOPE, "query": query, "source_calls_skipped": True},
        )

    if resolution.status != ResolutionStatus.RESOLVED:
        return _security_failure_payload(query, resolution)
    if resolution.security is None:
        return _base_payload(
            "error",
            _empty_sources(),
            {"status": "resolver_error", "scope": PHASE_SLICE_SCOPE, "query": query, "source_calls_skipped": True},
        )

    security = resolution.security
    selected_security_id = security_id_for(security)
    if selected_security_id != REFERENCE_SECURITY_ID:
        return _unsupported_fixture_scope_payload(query, security)

    sources: dict[str, object] = {}
    documents_by_source: dict[str, list[FinancialDocument]] = {}

    news_source, news_documents = await _fetch_provider_source(
        news_provider_factory(),
        source_type="news",
        security=security,
        config=config,
        fetcher=fetcher,
    )
    sources["news"] = news_source
    documents_by_source["news"] = news_documents

    disclosure_source, disclosure_documents = await _fetch_provider_source(
        disclosure_provider_factory(),
        source_type="disclosure",
        security=security,
        config=config,
        fetcher=fetcher,
    )
    sources["disclosure"] = disclosure_source
    documents_by_source["disclosure"] = disclosure_documents

    try:
        report_source, report_documents = _source_from_local_documents(
            list(report_loader(security)),
            source_type="research_report",
            mode="synthetic_manual_ingest",
            expected_count=EXPECTED_DOCUMENT_COUNTS["research_report"],
            selected_security_id=selected_security_id,
        )
    except ReportIngestValidationError:
        report_source = _source_template(
            "validation_error",
            "synthetic_manual_ingest",
            EXPECTED_DOCUMENT_COUNTS["research_report"],
        )
        report_documents = []
    except Exception:
        report_source = _source_template(
            "validation_error",
            "synthetic_manual_ingest",
            EXPECTED_DOCUMENT_COUNTS["research_report"],
        )
        report_documents = []
    sources["research_report"] = report_source
    documents_by_source["research_report"] = report_documents

    try:
        glossary_source = glossary_builder()
    except GlossaryIngestValidationError:
        glossary_source = {
            "status": "not_ready",
            "mode": "approved_local_corpus",
            "actual_coverage": False,
            "meets_minimum": False,
            "lookup_status": "not_found",
            "entry_id": None,
            "locator_section": None,
        }
    except Exception:
        glossary_source = {
            "status": "not_ready",
            "mode": "approved_local_corpus",
            "actual_coverage": False,
            "meets_minimum": False,
            "lookup_status": "not_found",
            "entry_id": None,
            "locator_section": None,
        }
    sources["glossary"] = glossary_source

    sample_documents = [
        _sample_for(documents_by_source[source_type][0])
        for source_type in SOURCE_ORDER
        if documents_by_source[source_type]
    ]
    document_count = sum(len(documents_by_source[source_type]) for source_type in SOURCE_ORDER)
    financial_document_source_count = sum(1 for source_type in SOURCE_ORDER if documents_by_source[source_type])
    phase_status = (
        "ok"
        if financial_document_source_count == EXPECTED_SOURCE_COUNT
        and document_count == EXPECTED_DOCUMENT_COUNT
        and len(sample_documents) == EXPECTED_SOURCE_COUNT
        else "degraded"
    )
    phase_slice = {
        "status": phase_status,
        "scope": PHASE_SLICE_SCOPE,
        "query": query,
        "security_id": selected_security_id,
        "security_name": security.security_name,
        "ticker": security.ticker,
        "date_start": REFERENCE_DATE_RANGE.start.isoformat() if REFERENCE_DATE_RANGE.start else None,
        "date_end": REFERENCE_DATE_RANGE.end.isoformat() if REFERENCE_DATE_RANGE.end else None,
        "financial_document_source_count": financial_document_source_count,
        "financial_document_count": document_count,
        "sample_documents": sample_documents,
    }

    top_level_status = _aggregate_status(sources, phase_slice)
    return _base_payload(top_level_status, sources, phase_slice)


async def build_health_payload(*, dependencies: PhaseSliceDependencies | None = None) -> dict[str, object]:
    try:
        config = ProviderConfig.from_env()
    except ConfigValidationError:
        return build_error_payload({"status": "error"})

    environment = {"status": "ok", **config.safe_summary()}
    try:
        payload = await build_phase_slice(REFERENCE_QUERY, config=config, dependencies=dependencies)
    except Exception:
        return build_error_payload(environment)

    result: dict[str, object] = {
        "status": payload["status"],
        "version": HEALTH_VERSION,
        "mode": HEALTH_MODE,
        "live_connectivity_checked": False,
        "environment": environment,
        "sources": payload["sources"],
        "phase_slice": payload["phase_slice"],
    }
    assert_public_payload_safe(result)
    return result


def _aggregate_status(sources: dict[str, object], phase_slice: dict[str, object]) -> str:
    if phase_slice.get("status") not in {"ok", "degraded"}:
        return "error"
    for source in sources.values():
        if not isinstance(source, dict):
            return "degraded"
        if source.get("status") != "ok":
            return "degraded"
    if phase_slice.get("status") != "ok":
        return "degraded"
    return "ok"


def assert_public_payload_safe(payload: Any) -> None:
    try:
        _assert_public_payload_safe(payload)
    except PublicPayloadSafetyError:
        raise
    except Exception:
        raise PublicPayloadSafetyError("public payload failed safety check") from None


def _assert_public_payload_safe(value: Any) -> None:
    if isinstance(value, (BaseException, TracebackType)):
        raise PublicPayloadSafetyError("public payload failed safety check")
    if isinstance(value, str):
        if _looks_unsafe_public_string(value):
            raise PublicPayloadSafetyError("public payload failed safety check")
        return
    if isinstance(value, dict):
        keys = set(value)
        if FORBIDDEN_SAMPLE_KEYS & keys or "message" in keys:
            raise PublicPayloadSafetyError("public payload failed safety check")
        if keys & set(SAMPLE_KEYS) and keys != set(SAMPLE_KEYS):
            raise PublicPayloadSafetyError("public payload failed safety check")
        for key, nested in value.items():
            if not isinstance(key, str):
                raise PublicPayloadSafetyError("public payload failed safety check")
            _assert_public_payload_safe(key)
            _assert_public_payload_safe(nested)
        return
    if isinstance(value, (list, tuple)):
        for nested in value:
            _assert_public_payload_safe(nested)
        return
    if isinstance(value, (str, int, float, bool)) or value is None:
        return
    if isinstance(value, (date,)):
        raise PublicPayloadSafetyError("public payload failed safety check")
    raise PublicPayloadSafetyError("public payload failed safety check")


def _looks_unsafe_public_string(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return False
    if any(sentinel in value for sentinel in SECRET_SENTINELS):
        return True
    if _is_http_url(stripped):
        return False
    if stripped in ALLOWED_ROUTE_TOKENS:
        return False
    lowered = stripped.lower()
    normalized = stripped.replace("\\", "/")
    return (
        "file://" in lowered
        or bool(UNC_PATH_RE.search(stripped))
        or bool(WINDOWS_ABSOLUTE_PATH_RE.search(stripped))
        or bool(POSIX_ABSOLUTE_PATH_RE.search(normalized))
    )


def _is_http_url(value: str) -> bool:
    try:
        parts = urlsplit(value)
    except ValueError:
        return False
    return parts.scheme.lower() in {"http", "https"} and bool(parts.netloc)


__all__ = [
    "DISCLOSURE_FIXTURE_PATH",
    "EXPECTED_DOCUMENT_COUNT",
    "EXPECTED_DOCUMENT_COUNTS",
    "EXPECTED_SOURCE_COUNT",
    "GLOSSARY_PATH",
    "HEALTH_MODE",
    "HEALTH_VERSION",
    "NEWS_FIXTURE_PATH",
    "PHASE_SLICE_SCOPE",
    "PhaseSliceDependencies",
    "PhaseSliceError",
    "PublicPayloadSafetyError",
    "REFERENCE_DATE_RANGE",
    "REFERENCE_QUERY",
    "REFERENCE_REPORT_AS_OF_DATE",
    "REFERENCE_SECURITY_ID",
    "REFERENCE_SECURITY_NAME",
    "REFERENCE_TICKER",
    "REPORT_DOCUMENTS_PATH",
    "REPORT_MANIFEST_PATH",
    "assert_public_payload_safe",
    "build_error_payload",
    "build_health_payload",
    "build_phase_slice",
]
