import asyncio
import json
from collections.abc import Sequence
from dataclasses import replace

import pytest

from app.config import ProviderConfig
from app.core.models import DateRange, FinancialDocument, ProviderResult, SecurityIdentifier
from app.core.resolver import SecurityResolver, security_id_for
from app.core.status import ProviderStatus
from app.health import (
    PhaseSliceDependencies,
    PublicPayloadSafetyError,
    assert_public_payload_safe,
    build_health_payload,
    build_phase_slice,
)
from app.ingest.glossary import (
    GlossaryCorpusValidationError,
    build_glossary_index,
    build_glossary_locator,
    evaluate_actual_glossary_coverage,
    load_glossary_entries,
    lookup_glossary_entry,
)
from app.phase_slice import (
    EXPECTED_DOCUMENT_COUNT,
    EXPECTED_DOCUMENT_COUNTS,
    EXPECTED_SOURCE_COUNT,
    REFERENCE_DATE_RANGE,
    REFERENCE_QUERY,
    REFERENCE_SECURITY_ID,
)
from app.providers.base import create_provider_result, fetch_with_policy

SENTINEL = "SENTINEL_SECRET_DO_NOT_LEAK"


def run(coro):
    return asyncio.run(coro)


def config():
    return ProviderConfig(timeout_seconds=1, retry_count=1, total_deadline_seconds=5, cache_ttl_seconds=300)


def samsung_security():
    return SecurityResolver().resolve(REFERENCE_QUERY).security


def financial_document(
    document_id: str,
    source_type: str,
    provider: str,
    *,
    primary_security_ids: list[str] | None = None,
    title: str = "Synthetic title",
):
    return FinancialDocument(
        document_id=document_id,
        source_type=source_type,
        provider=provider,
        primary_security_ids=primary_security_ids or [REFERENCE_SECURITY_ID],
        mentioned_security_ids=[],
        title=title,
        published_at=None,
        source_url=None,
        text="hidden text",
        locator={"kind": "synthetic"},
        metadata={},
        ingestion_version="m1-08-test",
    )


class SpyProvider:
    def __init__(self, key: str, result: ProviderResult[Sequence[FinancialDocument]]):
        self.key = key
        self.result = result

    async def fetch(self, security, query=None, date_range=None, attempt_timeout_seconds=8):
        return self.result


class ResolverSpy:
    def __init__(self, resolver=None):
        self.resolver = resolver or SecurityResolver()

    def resolve(self, query):
        return self.resolver.resolve(query)


def ok_glossary_source():
    return {
        "status": "ok",
        "mode": "approved_local_corpus",
        "actual_coverage": True,
        "meets_minimum": True,
        "lookup_status": "found",
        "entry_id": "glossary:per",
        "locator_section": "definition",
    }


def test_default_health_payload_matches_reference_contract(monkeypatch):
    for key in [
        "OPENDART_API_KEY",
        "NAVER_CLIENT_ID",
        "NAVER_CLIENT_SECRET",
        "QUESTOCK_PROVIDER_TIMEOUT_SECONDS",
        "QUESTOCK_PROVIDER_RETRY_COUNT",
        "QUESTOCK_PROVIDER_TOTAL_DEADLINE_SECONDS",
        "QUESTOCK_PROVIDER_CACHE_TTL_SECONDS",
    ]:
        monkeypatch.delenv(key, raising=False)

    payload = run(build_health_payload())
    phase = payload["phase_slice"]

    assert payload["status"] == "ok"
    assert payload["version"] == "m1-08"
    assert payload["mode"] == "fixture_readiness"
    assert payload["live_connectivity_checked"] is False
    assert payload["environment"]["status"] == "ok"
    assert payload["environment"]["timeout_seconds"] == 8
    assert payload["environment"]["opendart_api_key_configured"] is False
    assert payload["sources"]["news"]["document_count"] == EXPECTED_DOCUMENT_COUNTS["news"]
    assert payload["sources"]["disclosure"]["document_count"] == EXPECTED_DOCUMENT_COUNTS["disclosure"]
    assert payload["sources"]["research_report"]["document_count"] == EXPECTED_DOCUMENT_COUNTS["research_report"]
    assert payload["sources"]["glossary"]["actual_coverage"] is True
    assert payload["sources"]["glossary"]["lookup_status"] == "found"
    assert phase["security_id"] == REFERENCE_SECURITY_ID
    assert phase["financial_document_source_count"] == EXPECTED_SOURCE_COUNT
    assert phase["financial_document_count"] == EXPECTED_DOCUMENT_COUNT
    assert [sample["source_type"] for sample in phase["sample_documents"]] == ["news", "disclosure", "research_report"]
    assert json.loads(json.dumps(payload, ensure_ascii=False))["status"] == "ok"


def test_default_query_ticker_security_id_and_alias_resolve_to_reference():
    resolver = SecurityResolver()
    alias = "Samsung Electronics"
    for query in [REFERENCE_QUERY, "005930", REFERENCE_SECURITY_ID, alias]:
        result = resolver.resolve(query)
        assert result.status == "resolved"
        assert security_id_for(result.security) == REFERENCE_SECURITY_ID


def test_non_resolved_queries_skip_sources_and_loaders():
    calls = {"news": 0, "disclosure": 0, "report": 0, "glossary": 0}

    async def fetcher(**kwargs):
        calls[kwargs["provider"].key] += 1
        return create_provider_result(status=ProviderStatus.NO_DATA)

    def report_loader(_security):
        calls["report"] += 1
        return []

    def glossary_builder():
        calls["glossary"] += 1
        return ok_glossary_source()

    deps = PhaseSliceDependencies(fetcher=fetcher, report_loader=report_loader, glossary_readiness_builder=glossary_builder)

    ambiguous = run(build_phase_slice("삼성", config=config(), dependencies=deps))
    not_found = run(build_phase_slice("없는종목", config=config(), dependencies=deps))
    unsupported = run(build_phase_slice("AAPL", config=config(), dependencies=deps))

    assert ambiguous["phase_slice"]["status"] == "ambiguous"
    assert not_found["phase_slice"]["status"] == "not_found"
    assert unsupported["phase_slice"]["status"] == "unsupported"
    assert calls == {"news": 0, "disclosure": 0, "report": 0, "glossary": 0}


def test_other_supported_securities_are_outside_reference_fixture_scope():
    for query in ["SK하이닉스", "현대자동차"]:
        payload = run(build_phase_slice(query, config=config()))
        assert payload["status"] == "error"
        assert payload["phase_slice"]["status"] == "unsupported_for_fixture_slice"
        assert payload["phase_slice"]["required_reference_security_id"] == REFERENCE_SECURITY_ID


def test_provider_policy_mapping_uses_none_query_fixed_dates_and_config_values():
    calls = []

    async def fetcher(**kwargs):
        calls.append(kwargs)
        docs = [
            financial_document(
                f"{kwargs['provider'].key}:001",
                "news" if kwargs["provider"].key == "news" else "disclosure",
                kwargs["provider"].key,
            )
        ]
        return create_provider_result(status=ProviderStatus.OK, data=docs)

    deps = PhaseSliceDependencies(
        news_provider_factory=lambda: SpyProvider("news", create_provider_result(status=ProviderStatus.NO_DATA)),
        disclosure_provider_factory=lambda: SpyProvider("disclosure", create_provider_result(status=ProviderStatus.NO_DATA)),
        fetcher=fetcher,
        report_loader=lambda _security: [
            financial_document("report:002", "research_report", "manual_manifest"),
            financial_document("report:001", "research_report", "manual_manifest"),
        ],
        glossary_readiness_builder=ok_glossary_source,
    )
    cfg = ProviderConfig(timeout_seconds=1.25, retry_count=2, total_deadline_seconds=3.5)

    payload = run(build_phase_slice(REFERENCE_QUERY, config=cfg, dependencies=deps))

    assert payload["status"] == "ok"
    assert [call["provider"].key for call in calls] == ["news", "disclosure"]
    assert [call["query"] for call in calls] == [None, None]
    assert all(call["date_range"] == REFERENCE_DATE_RANGE for call in calls)
    assert all(call["config"] is cfg for call in calls)
    assert all(call["cache"] is None for call in calls)
    assert payload["phase_slice"]["sample_documents"][2]["document_id"] == "report:001"


def test_wrong_company_documents_are_excluded_and_degrade_count():
    async def fetcher(**kwargs):
        source_type = "news" if kwargs["provider"].key == "news" else "disclosure"
        return create_provider_result(
            status=ProviderStatus.OK,
            data=[financial_document(f"{source_type}:wrong", source_type, kwargs["provider"].key, primary_security_ids=["KRX:000660"])],
        )

    deps = PhaseSliceDependencies(
        news_provider_factory=lambda: SpyProvider("news", create_provider_result(status=ProviderStatus.NO_DATA)),
        disclosure_provider_factory=lambda: SpyProvider("disclosure", create_provider_result(status=ProviderStatus.NO_DATA)),
        fetcher=fetcher,
        report_loader=lambda _security: [],
        glossary_readiness_builder=ok_glossary_source,
    )

    payload = run(build_phase_slice(REFERENCE_QUERY, config=config(), dependencies=deps))

    assert payload["status"] == "degraded"
    assert payload["sources"]["news"]["document_count"] == 0
    assert payload["sources"]["news"]["status"] == "unexpected_document_count"


def test_glossary_actual_coverage_lookup_and_locator_are_public_identity_only():
    coverage = evaluate_actual_glossary_coverage("data/glossary.json")
    bundle = load_glossary_entries("data/glossary.json")
    index = build_glossary_index(bundle, mode="corpus")
    lookup = lookup_glossary_entry(index, "PER")
    locator = build_glossary_locator(bundle, lookup.entry, "definition")
    payload = run(build_health_payload())
    serialized = json.dumps(payload, ensure_ascii=False)

    assert coverage.actual_coverage_evaluated is True
    assert coverage.meets_minimum is True
    assert lookup.status == "found"
    assert locator.entry_id == "glossary:per"
    assert locator.section == "definition"
    assert payload["sources"]["glossary"]["entry_id"] == "glossary:per"
    assert payload["sources"]["glossary"]["locator_section"] == "definition"
    assert lookup.entry.definition not in serialized


def test_payload_is_deterministic_and_hides_timestamps_cache_and_document_body(monkeypatch):
    for key in ["OPENDART_API_KEY", "NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET"]:
        monkeypatch.delenv(key, raising=False)

    first = run(build_health_payload())
    second = run(build_health_payload())
    serialized = json.dumps(first, ensure_ascii=False, sort_keys=True, default=str)

    assert first == second
    assert "fetched_at" not in serialized
    assert "from_cache" not in serialized
    assert '"text"' not in serialized
    assert '"locator"' not in serialized
    assert '"metadata"' not in serialized
    assert '"source_url"' not in serialized


@pytest.mark.parametrize(
    ("news_status", "expected_source"),
    [
        (ProviderStatus.NO_DATA, "no_data"),
        (ProviderStatus.TIMEOUT, "timeout"),
    ],
)
def test_provider_failures_are_degraded_without_raw_message(news_status, expected_source):
    async def fetcher(**kwargs):
        if kwargs["provider"].key == "news":
            return create_provider_result(status=news_status, message=f"raw {SENTINEL}")
        return create_provider_result(
            status=ProviderStatus.OK,
            data=[financial_document("disclosure:ok", "disclosure", kwargs["provider"].key)],
        )

    deps = PhaseSliceDependencies(
        news_provider_factory=lambda: SpyProvider("news", create_provider_result(status=ProviderStatus.NO_DATA)),
        disclosure_provider_factory=lambda: SpyProvider("disclosure", create_provider_result(status=ProviderStatus.NO_DATA)),
        fetcher=fetcher,
        report_loader=lambda _security: [
            financial_document("report:001", "research_report", "manual_manifest"),
            financial_document("report:002", "research_report", "manual_manifest"),
        ],
        glossary_readiness_builder=ok_glossary_source,
    )

    payload = run(build_phase_slice(REFERENCE_QUERY, config=config(), dependencies=deps))
    serialized = json.dumps(payload, ensure_ascii=False)

    assert payload["status"] == "degraded"
    assert payload["sources"]["news"]["status"] == expected_source
    assert SENTINEL not in serialized
    assert "Traceback" not in serialized


@pytest.mark.parametrize(
    ("source_key", "status"),
    [
        ("disclosure", ProviderStatus.PARSE_ERROR),
        ("disclosure", ProviderStatus.PROVIDER_UNAVAILABLE),
    ],
)
def test_disclosure_failure_statuses_are_preserved(source_key, status):
    async def fetcher(**kwargs):
        source_type = "news" if kwargs["provider"].key == "news" else "disclosure"
        if kwargs["provider"].key == source_key:
            return create_provider_result(status=status, message="raw hidden")
        return create_provider_result(
            status=ProviderStatus.OK,
            data=[financial_document(f"{source_type}:ok", source_type, kwargs["provider"].key)],
        )

    deps = PhaseSliceDependencies(
        news_provider_factory=lambda: SpyProvider("news", create_provider_result(status=ProviderStatus.NO_DATA)),
        disclosure_provider_factory=lambda: SpyProvider("disclosure", create_provider_result(status=ProviderStatus.NO_DATA)),
        fetcher=fetcher,
        report_loader=lambda _security: [
            financial_document("report:001", "research_report", "manual_manifest"),
            financial_document("report:002", "research_report", "manual_manifest"),
        ],
        glossary_readiness_builder=ok_glossary_source,
    )

    payload = run(build_phase_slice(REFERENCE_QUERY, config=config(), dependencies=deps))

    assert payload["status"] == "degraded"
    assert payload["sources"][source_key]["status"] == status.value


def test_unexpected_provider_report_glossary_and_resolver_failures_are_sanitized(monkeypatch):
    async def raising_fetcher(**_kwargs):
        raise RuntimeError(f"boom {SENTINEL}")

    provider_failure = run(
        build_phase_slice(
            REFERENCE_QUERY,
            config=config(),
            dependencies=PhaseSliceDependencies(fetcher=raising_fetcher, glossary_readiness_builder=ok_glossary_source),
        )
    )
    report_failure = run(
        build_phase_slice(
            REFERENCE_QUERY,
            config=config(),
            dependencies=PhaseSliceDependencies(
                report_loader=lambda _security: (_ for _ in ()).throw(ValueError(f"bad {SENTINEL}")),
                glossary_readiness_builder=ok_glossary_source,
            ),
        )
    )
    glossary_failure = run(
        build_phase_slice(
            REFERENCE_QUERY,
            config=config(),
            dependencies=PhaseSliceDependencies(
                glossary_readiness_builder=lambda: (_ for _ in ()).throw(
                    GlossaryCorpusValidationError(f"bad {SENTINEL}")
                )
            ),
        )
    )
    resolver_failure = run(
        build_phase_slice(
            REFERENCE_QUERY,
            config=config(),
            dependencies=PhaseSliceDependencies(resolver_factory=lambda: (_ for _ in ()).throw(RuntimeError("resolver"))),
        )
    )
    monkeypatch.setenv("QUESTOCK_PROVIDER_TIMEOUT_SECONDS", "not-a-number-secret")
    config_failure = run(build_health_payload())

    for payload in [provider_failure, report_failure, glossary_failure, resolver_failure, config_failure]:
        serialized = json.dumps(payload, ensure_ascii=False)
        assert payload["status"] in {"degraded", "error"}
        assert SENTINEL not in serialized
        assert "RuntimeError" not in serialized
        assert "Traceback" not in serialized


def test_public_payload_safety_rejects_forbidden_values_without_echoing():
    with pytest.raises(PublicPayloadSafetyError) as exc_info:
        assert_public_payload_safe({"safe": ["C:/Users/name/secret"]})
    assert "C:/Users" not in str(exc_info.value)

    for unsafe in [
        "//server/share",
        "/secret",
        "/mnt/data/secret",
        "/srv/app/config",
        "/usr/local/private",
        "/app/file",
        "/media/user/file",
        "/custom/root/file",
        "prefix /srv/app/config",
        "file://secret",
        SENTINEL,
    ]:
        with pytest.raises(PublicPayloadSafetyError):
            assert_public_payload_safe({"value": unsafe})

    for unsafe_key_payload in [
        {"/mnt/data/secret": "value"},
        {"safe": {"/custom/root/file": "value"}},
    ]:
        with pytest.raises(PublicPayloadSafetyError):
            assert_public_payload_safe(unsafe_key_payload)

    assert_public_payload_safe({"value": "/health"})
    assert_public_payload_safe({"value": "GET /health"})
    assert_public_payload_safe({"value": "http://127.0.0.1:8000/health"})
    assert_public_payload_safe({"value": "https://example.com/path"})

    with pytest.raises(PublicPayloadSafetyError):
        assert_public_payload_safe({"document_id": "x", "source_type": "news", "provider": "p", "title": "t", "text": "bad"})


def test_caller_mutation_does_not_change_already_built_payload():
    mutable_docs = [financial_document("news:001", "news", "news")]

    async def fetcher(**kwargs):
        source_type = "news" if kwargs["provider"].key == "news" else "disclosure"
        if source_type == "news":
            return create_provider_result(status=ProviderStatus.OK, data=mutable_docs)
        return create_provider_result(status=ProviderStatus.OK, data=[financial_document("disclosure:001", "disclosure", "disclosure")])

    deps = PhaseSliceDependencies(
        news_provider_factory=lambda: SpyProvider("news", create_provider_result(status=ProviderStatus.NO_DATA)),
        disclosure_provider_factory=lambda: SpyProvider("disclosure", create_provider_result(status=ProviderStatus.NO_DATA)),
        fetcher=fetcher,
        report_loader=lambda _security: [
            financial_document("report:001", "research_report", "manual_manifest"),
            financial_document("report:002", "research_report", "manual_manifest"),
        ],
        glossary_readiness_builder=ok_glossary_source,
    )

    payload = run(build_phase_slice(REFERENCE_QUERY, config=config(), dependencies=deps))
    mutable_docs[0] = financial_document("news:999", "news", "news")

    assert payload["phase_slice"]["sample_documents"][0]["document_id"] == "news:001"
    assert payload["phase_slice"]["financial_document_count"] == 4


def test_build_phase_slice_can_use_existing_policy_wrapper_directly():
    provider = SpyProvider("news", create_provider_result(status=ProviderStatus.OK, data=[financial_document("news:ok", "news", "news")]))

    result = run(fetch_with_policy(provider, samsung_security(), config(), date_range=DateRange()))

    assert result.status == ProviderStatus.OK
