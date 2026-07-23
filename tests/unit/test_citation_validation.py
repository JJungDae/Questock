from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, timedelta, timezone
import math

import pytest

from app.core.models import (
    Evidence,
    FinancialDocument,
    QueryPlan,
    RetrievalRequest,
    SecurityIdentifier,
)
from app.core.status import EvidenceDecisionStatus, ProviderStatus, RetrievalStatus
from app.evidence import citations as citation_module
from app.evidence.citations import (
    Citation,
    CitationClaim,
    CitationRejection,
    CitationValidationError,
    CitationValidationResult,
    validate_citations,
)
from app.evidence.freshness import evaluate_freshness
from app.evidence.normalizer import normalize_financial_documents
from app.evidence.policy import EvidenceDecision, EvidencePolicy
from app.planning.query_planner import QueryPlanner
from app.providers.base import create_provider_result
from app.retrieval import filter_evidence, retrieve_evidence

UTC = timezone.utc
BASIS_AT = datetime(2026, 7, 23, 3, 0, tzinfo=UTC)
BASIS_DATE = date(2026, 7, 23)
SAMSUNG = "KRX:005930"
SK_HYNIX = "KRX:000660"
HYUNDAI = "KRX:005380"
NEWS_URL = "https://news.example.com/articles/samsung"
DISCLOSURE_RECEIPT = "20260721000005"
DISCLOSURE_URL = (
    "https://dart.fss.or.kr/dsaf001/main.do?rcpNo="
    f"{DISCLOSURE_RECEIPT}"
)
REPORT_URL = "https://research.example.com/reports/samsung.pdf"


def security(security_id: str = SAMSUNG) -> SecurityIdentifier:
    market, ticker = security_id.split(":")
    names = {
        SAMSUNG: "Samsung Electronics",
        SK_HYNIX: "SK hynix",
        HYUNDAI: "Hyundai Motor",
    }
    return SecurityIdentifier(
        market=market,
        ticker=ticker,
        security_name=names[security_id],
        security_type="common_stock",
        corp_code=None,
        corp_name=names[security_id],
    )


def plan(
    intent: str = "recent_issue",
    *,
    target: str | None = SAMSUNG,
    sources: list[str] | None = None,
    clarification: bool = False,
) -> QueryPlan:
    default_sources = {
        "recent_issue": ["news"],
        "disclosure_summary": ["disclosure"],
        "research_report_summary": ["research_report"],
        "financial_term": ["glossary"],
        "risk_factors": ["news", "disclosure", "research_report"],
        "multi_source_summary": ["news", "disclosure", "research_report"],
    }
    return QueryPlan(
        security=security(target) if target is not None else None,
        intent=intent,
        required_sources=list(sources or default_sources.get(intent, [])),
        required_evidence=[],
        requires_clarification=clarification,
    )


def locator_for(
    source_type: str,
    *,
    source_url: str | None,
    document_id: str,
) -> dict[str, object]:
    if source_type == "news":
        return {
            "provider": "recorded_news",
            "source_url": source_url,
            "published_at": BASIS_AT.isoformat(),
            "raw_index": 0,
            "query": "Samsung earnings",
        }
    if source_type == "disclosure":
        return {
            "provider": "opendart_disclosure",
            "receipt_no": DISCLOSURE_RECEIPT,
            "viewer_url": source_url,
            "corp_code": "00126380",
            "stock_code": "005930",
            "corp_name": "Samsung Electronics",
            "report_name": "Quarterly report",
            "received_date": "20260721",
        }
    if source_type == "research_report":
        return {
            "manifest_id": "samsung-report-001",
            "document_id": document_id,
            "page": 2,
            "page_basis": "pdf_1_based",
            "section": "Earnings",
            "publisher": "Approved Research",
            "source_url": source_url,
            "source_asset_id": None if source_url is not None else "approved-asset-001",
            "access_note": "approved fixture",
        }
    if source_type == "glossary":
        return {
            "corpus_id": "glossary-approved-v1",
            "entry_id": "glossary:roe",
            "version": 1,
            "section": "definition",
            "source_type": "glossary",
            "provider": "manual_glossary",
            "ingestion_version": "glossary-m1-07-v1",
            "source_url": source_url,
            "source_asset_id": None,
        }
    raise AssertionError("unsupported unit source")


def evidence(
    source_type: str = "news",
    *,
    evidence_id: str | None = None,
    target: str = SAMSUNG,
    scope: str = "company_specific",
    subjects: list[str] | None = None,
    mentions: list[str] | None = None,
    snippet: str = "Samsung earnings improved in the latest quarter.",
    title: str = "Samsung earnings update",
    source_url: str | None | object = ...,
    locator: dict[object, object] | None = None,
    score: float | None = 0.8,
) -> Evidence:
    urls = {
        "news": NEWS_URL,
        "disclosure": DISCLOSURE_URL,
        "research_report": REPORT_URL,
        "glossary": None,
    }
    actual_url = urls[source_type] if source_url is ... else source_url
    item_id = evidence_id or f"evidence:{source_type}:unit"
    document_id = (
        f"disclosure:{DISCLOSURE_RECEIPT}"
        if source_type == "disclosure"
        else f"document:{source_type}:unit"
    )
    if scope == "company_specific":
        default_subjects = [target]
        default_mentions: list[str] = []
    elif scope == "multi_company":
        default_subjects = [target, SK_HYNIX if target != SK_HYNIX else SAMSUNG]
        default_mentions = []
    else:
        default_subjects = []
        default_mentions = [target]
    return Evidence(
        evidence_id=item_id,
        document_id=document_id,
        source_type=source_type,
        title=title,
        source_url=actual_url,
        published_at=BASIS_AT,
        subject_security_ids=default_subjects if subjects is None else subjects,
        mentioned_security_ids=default_mentions if mentions is None else mentions,
        scope=scope,
        snippet=snippet,
        locator=(
            locator_for(source_type, source_url=actual_url, document_id=document_id)
            if locator is None
            else locator
        ),
        retrieval_score=score,
    )


def claim(
    *evidence_ids: str,
    claim_id: str = "claim-1",
    text: str = "Samsung earnings improved",
) -> CitationClaim:
    return CitationClaim(claim_id, text, tuple(evidence_ids or ("evidence:news:unit",)))


def assert_sanitized(exc_info: pytest.ExceptionInfo[CitationValidationError]) -> None:
    message = str(exc_info.value)
    assert message in {
        "claims must be a sequence",
        "claims are invalid",
        "claims are incompatible with the plan",
        "plan must be a QueryPlan",
        "selected evidence must be a sequence",
        "selected evidence is invalid",
        "selected evidence IDs are inconsistent",
        "citation output is invalid",
    }
    assert "SECRET_SENTINEL" not in message
    assert "C:\\" not in message
    assert "/root" not in message


def test_public_api_is_explicit_and_frozen():
    assert citation_module.__all__ == [
        "Citation",
        "CitationClaim",
        "CitationRejection",
        "CitationValidationError",
        "CitationValidationResult",
        "validate_citations",
    ]
    with pytest.raises(FrozenInstanceError):
        claim().__setattr__("text", "changed")


@pytest.mark.parametrize(
    ("source_type", "query_plan", "source_url"),
    [
        ("news", plan(), NEWS_URL),
        ("news", plan(), None),
        ("disclosure", plan("disclosure_summary"), DISCLOSURE_URL),
        ("research_report", plan("research_report_summary"), REPORT_URL),
        ("research_report", plan("research_report_summary"), None),
        ("glossary", plan("financial_term", target=None), None),
    ],
)
def test_valid_source_citations_are_built_only_from_evidence(
    source_type,
    query_plan,
    source_url,
):
    item = evidence(source_type, source_url=source_url)
    result = validate_citations(
        [claim(item.evidence_id)],
        query_plan,
        [item],
    )
    assert result.rejections == ()
    assert result.citations == (
        Citation(
            claim_id="claim-1",
            evidence_id=item.evidence_id,
            document_id=item.document_id,
            source_type=item.source_type,
            title=item.title,
            source_url=item.source_url,
            snippet=item.snippet,
            locator=item.locator,
        ),
    )
    assert result.citations[0].locator is not item.locator


def test_empty_claims_are_valid_after_plan_and_selected_evidence_validation():
    item = evidence()
    assert validate_citations([], plan(), [item]) == CitationValidationResult((), ())
    assert validate_citations([], plan(), []) == CitationValidationResult((), ())
    assert validate_citations(
        [],
        plan("out_of_scope", target=None, sources=[], clarification=True),
        [],
    ) == CitationValidationResult((), ())


@pytest.mark.parametrize("bad_claims", [None, "claim", b"claim", {"claim": 1}, iter(())])
def test_claims_must_be_a_materialized_sequence(bad_claims):
    with pytest.raises(CitationValidationError) as exc_info:
        validate_citations(bad_claims, plan(), [])
    assert_sanitized(exc_info)


@pytest.mark.parametrize(
    "bad_claim",
    [
        None,
        CitationClaim("", "supported", ("evidence:news:unit",)),
        CitationClaim("claim", "", ("evidence:news:unit",)),
        CitationClaim("claim", " !? ", ("evidence:news:unit",)),
        CitationClaim("claim", "supported", []),
        CitationClaim("claim", "supported", ()),
        CitationClaim("claim", "supported", ("",)),
        CitationClaim("claim", "supported", ("duplicate", "duplicate")),
        CitationClaim("C:\\SECRET_SENTINEL", "supported", ("evidence:news:unit",)),
    ],
)
def test_malformed_claims_are_sanitized(bad_claim):
    with pytest.raises(CitationValidationError) as exc_info:
        validate_citations([bad_claim], plan(), [])
    assert_sanitized(exc_info)


def test_duplicate_claim_ids_are_rejected_before_partial_results():
    claims = [
        claim(claim_id="same"),
        claim(claim_id="same"),
    ]
    with pytest.raises(CitationValidationError) as exc_info:
        validate_citations(claims, plan(), [evidence()])
    assert_sanitized(exc_info)


@pytest.mark.parametrize("bad_plan", [None, "plan", object()])
def test_plan_type_is_strict_and_sanitized(bad_plan):
    with pytest.raises(CitationValidationError) as exc_info:
        validate_citations([], bad_plan, [])
    assert_sanitized(exc_info)


def test_bypass_created_malformed_plan_is_rejected():
    bad = QueryPlan.model_construct(
        security="SECRET_SENTINEL",
        intent="recent_issue",
        required_sources=["news"],
        required_evidence=[],
        requires_clarification=False,
        date_range=None,
    )
    with pytest.raises(CitationValidationError) as exc_info:
        validate_citations([], bad, [])
    assert_sanitized(exc_info)


def test_clarification_plan_with_claims_is_invalid():
    query_plan = plan("out_of_scope", target=None, sources=[], clarification=True)
    with pytest.raises(CitationValidationError) as exc_info:
        validate_citations([claim()], query_plan, [])
    assert_sanitized(exc_info)


def test_selected_source_must_be_requested_and_financial_term_is_glossary_only():
    with pytest.raises(CitationValidationError) as exc_info:
        validate_citations([], plan(), [evidence("disclosure")])
    assert_sanitized(exc_info)

    with pytest.raises(CitationValidationError) as exc_info:
        validate_citations(
            [],
            plan("financial_term", target=None, sources=["news"]),
            [evidence("news")],
        )
    assert_sanitized(exc_info)


@pytest.mark.parametrize(
    "bad_evidence",
    [None, "evidence", b"evidence", {"evidence": 1}, iter(())],
)
def test_selected_evidence_must_be_a_materialized_sequence(bad_evidence):
    with pytest.raises(CitationValidationError) as exc_info:
        validate_citations([], plan(), bad_evidence)
    assert_sanitized(exc_info)


def test_selected_evidence_items_and_scores_are_strict():
    with pytest.raises(CitationValidationError) as exc_info:
        validate_citations([], plan(), [object()])
    assert_sanitized(exc_info)

    for score in (None, 0.499999, float("nan"), float("inf"), -float("inf")):
        with pytest.raises(CitationValidationError) as exc_info:
            validate_citations([], plan(), [evidence(score=score)])
        assert_sanitized(exc_info)


def test_bypass_created_malformed_evidence_is_revalidated():
    values = evidence().model_dump(mode="python")
    values["snippet"] = 123
    bad = Evidence.model_construct(**values)
    with pytest.raises(CitationValidationError) as exc_info:
        validate_citations([], plan(), [bad])
    assert_sanitized(exc_info)


def test_bypass_mutated_cyclic_locator_is_sanitized():
    item = evidence()
    cyclic: dict[str, object] = {}
    cyclic["self"] = cyclic
    item.locator["nested"] = cyclic
    with pytest.raises(CitationValidationError) as exc_info:
        validate_citations([claim(item.evidence_id)], plan(), [item])
    assert_sanitized(exc_info)


@pytest.mark.parametrize(
    "item",
    [
        evidence(target=SK_HYNIX),
        evidence(
            scope="multi_company",
            subjects=[SK_HYNIX, HYUNDAI],
            evidence_id="evidence:multi:wrong",
        ),
        evidence(
            scope="industry_common",
            subjects=[],
            mentions=[SK_HYNIX],
            evidence_id="evidence:industry:wrong",
        ),
    ],
)
def test_wrong_company_references_are_rejected(item):
    result = validate_citations(
        [claim(item.evidence_id)],
        plan(),
        [item],
    )
    assert result.citations == ()
    assert result.rejections == (CitationRejection("claim-1", "wrong_company"),)


def test_industry_common_target_mention_is_accepted():
    item = evidence(
        scope="industry_common",
        subjects=[],
        mentions=[SAMSUNG],
        evidence_id="evidence:industry:valid",
    )
    result = validate_citations([claim(item.evidence_id)], plan(), [item])
    assert [citation.evidence_id for citation in result.citations] == [item.evidence_id]


def test_generic_glossary_is_accepted_with_or_without_supported_security():
    item = evidence(
        "glossary",
        scope="industry_common",
        subjects=[],
        mentions=[],
    )
    for query_plan in (
        plan("financial_term", target=None),
        plan("financial_term", target=SAMSUNG),
    ):
        result = validate_citations([claim(item.evidence_id)], query_plan, [item])
        assert len(result.citations) == 1


@pytest.mark.parametrize(
    ("claim_text", "snippet"),
    [
        ("Samsung earnings improved", "Samsung earnings improved in the quarter."),
        ("SAMSUNG EARNINGS IMPROVED", "samsung earnings improved in the quarter."),
        ("Samsung   earnings\nimproved", "Samsung earnings improved in the quarter."),
        ("\uff33\uff41\uff4d\uff53\uff55\uff4e\uff47 earnings improved", "Samsung earnings improved."),
    ],
)
def test_extract_support_normalizes_nfkc_case_and_whitespace(claim_text, snippet):
    item = evidence(snippet=snippet)
    result = validate_citations(
        [claim(item.evidence_id, text=claim_text)],
        plan(),
        [item],
    )
    assert len(result.citations) == 1
    assert result.rejections == ()


@pytest.mark.parametrize(
    ("claim_text", "title", "snippet"),
    [
        ("Samsung earnings improved", "Samsung earnings improved", "Other facts only."),
        ("Samsung profit rose", "Samsung earnings", "Samsung earnings improved."),
    ],
)
def test_title_only_or_unsupported_paraphrase_is_rejected(claim_text, title, snippet):
    item = evidence(title=title, snippet=snippet)
    result = validate_citations(
        [claim(item.evidence_id, text=claim_text)],
        plan(),
        [item],
    )
    assert result == CitationValidationResult(
        (),
        (CitationRejection("claim-1", "unsupported_claim"),),
    )


def test_multi_evidence_claim_is_all_or_nothing():
    first = evidence(evidence_id="evidence:first")
    second = evidence(
        evidence_id="evidence:second",
        snippet="A different unsupported statement.",
    )
    result = validate_citations(
        [claim(first.evidence_id, second.evidence_id)],
        plan(),
        [first, second],
    )
    assert result.citations == ()
    assert result.rejections == (CitationRejection("claim-1", "unsupported_claim"),)


def test_unknown_evidence_precedes_other_claim_checks():
    result = validate_citations(
        [claim("evidence:missing")],
        plan(),
        [evidence()],
    )
    assert result == CitationValidationResult(
        (),
        (CitationRejection("claim-1", "unknown_evidence"),),
    )


def test_identical_duplicate_occurrences_are_preserved():
    item = evidence()
    result = validate_citations([claim(item.evidence_id)], plan(), [item, item.model_copy(deep=True)])
    assert [citation.evidence_id for citation in result.citations] == [
        item.evidence_id,
        item.evidence_id,
    ]


def test_conflicting_duplicate_payloads_are_rejected():
    item = evidence()
    conflicting = item.model_copy(deep=True, update={"title": "Conflicting title"})
    with pytest.raises(CitationValidationError) as exc_info:
        validate_citations([claim(item.evidence_id)], plan(), [item, conflicting])
    assert_sanitized(exc_info)


@pytest.mark.parametrize(
    "unsafe_value",
    [
        {"bad": float("nan")},
        {"bad": float("inf")},
        {"bad": {1, 2}},
        {"bad": b"secret"},
        {1: "bad-key"},
        {"OPENDART_API_KEY": "SECRET_SENTINEL"},
    ],
)
def test_recursive_locator_failures_return_invalid_locator(unsafe_value):
    item = evidence()
    item.locator["nested"] = unsafe_value
    result = validate_citations([claim(item.evidence_id)], plan(), [item])
    assert result == CitationValidationResult(
        (),
        (CitationRejection("claim-1", "invalid_locator"),),
    )


@pytest.mark.parametrize(
    "unsafe_value",
    [
        "C:\\private\\file",
        "\\\\server\\share\\file",
        "/root/private",
        "file://private/report",
    ],
)
def test_bypass_mutated_nested_paths_fail_canonical_revalidation(unsafe_value):
    item = evidence()
    item.locator["nested"] = {"bad": unsafe_value}
    with pytest.raises(CitationValidationError) as exc_info:
        validate_citations([claim(item.evidence_id)], plan(), [item])
    assert_sanitized(exc_info)


@pytest.mark.parametrize(
    "unsafe_url",
    [
        "https://",
        "https://user:password@example.com/path",
        "https://example.com/path#fragment",
        "https://example.com:99999/path",
        "https://example.com/path?api_key=SECRET_SENTINEL",
        "https://example.com/path?%61pi%2Dkey=SECRET_SENTINEL",
        "https://example.com/path?X-Amz-Signature=SECRET_SENTINEL",
        "https://example.com/path?source=C%3A%5Cprivate%5Cfile",
        "https://example.com/path with space",
    ],
)
def test_unsafe_urls_are_rejected_without_leaking_values(unsafe_url):
    item = evidence(
        source_url=unsafe_url,
        locator={
            "provider": "recorded_news",
            "source_url": unsafe_url,
            "published_at": BASIS_AT.isoformat(),
            "raw_index": 0,
        },
    )
    result = validate_citations([claim(item.evidence_id)], plan(), [item])
    assert result == CitationValidationResult(
        (),
        (CitationRejection("claim-1", "unsafe_source_url"),),
    )
    assert "SECRET_SENTINEL" not in str(result)


def test_safe_url_path_is_not_misclassified_as_a_local_path():
    url = "https://example.com/root/private/report?a=1"
    item = evidence(
        source_url=url,
        locator={
            "provider": "recorded_news",
            "source_url": url,
            "published_at": BASIS_AT.isoformat(),
            "raw_index": 0,
        },
    )
    assert len(validate_citations([claim(item.evidence_id)], plan(), [item]).citations) == 1


@pytest.mark.parametrize(
    "updates",
    [
        {"provider": ""},
        {"published_at": "not-a-timestamp"},
        {"published_at": "2026-07-23T03:00:00"},
        {"raw_index": -1},
        {"raw_index": True},
    ],
)
def test_url_less_news_requires_recorded_coordinates(updates):
    locator = locator_for("news", source_url=None, document_id="document:news:unit")
    locator.update(updates)
    item = evidence(source_url=None, locator=locator)
    result = validate_citations([claim(item.evidence_id)], plan(), [item])
    assert result.rejections == (CitationRejection("claim-1", "invalid_locator"),)


def test_news_query_is_preserved_when_present_but_not_a_runtime_requirement():
    item = evidence(source_url=None)
    item.locator.pop("query")
    result = validate_citations([claim(item.evidence_id)], plan(), [item])
    assert len(result.citations) == 1
    assert "query" not in result.citations[0].locator


def test_news_locator_url_must_equal_evidence_url():
    item = evidence(
        locator=locator_for(
            "news",
            source_url="https://news.example.com/other",
            document_id="document:news:unit",
        )
    )
    result = validate_citations([claim(item.evidence_id)], plan(), [item])
    assert result.rejections == (CitationRejection("claim-1", "unsafe_source_url"),)


@pytest.mark.parametrize(
    "updates",
    [
        {"receipt_no": "123"},
        {"receipt_no": 20260721000005},
        {"provider": ""},
    ],
)
def test_disclosure_identity_fields_are_required(updates):
    locator = locator_for(
        "disclosure",
        source_url=DISCLOSURE_URL,
        document_id=f"disclosure:{DISCLOSURE_RECEIPT}",
    )
    locator.update(updates)
    item = evidence("disclosure", locator=locator)
    result = validate_citations(
        [claim(item.evidence_id)],
        plan("disclosure_summary"),
        [item],
    )
    assert result.rejections == (CitationRejection("claim-1", "invalid_locator"),)


def test_disclosure_viewer_must_be_the_exact_official_receipt_url():
    item = evidence(
        "disclosure",
        source_url="https://example.com/not-dart",
        locator={
            **locator_for(
                "disclosure",
                source_url="https://example.com/not-dart",
                document_id=f"disclosure:{DISCLOSURE_RECEIPT}",
            ),
            "viewer_url": "https://example.com/not-dart",
        },
    )
    result = validate_citations(
        [claim(item.evidence_id)],
        plan("disclosure_summary"),
        [item],
    )
    assert result.rejections == (CitationRejection("claim-1", "unsafe_source_url"),)


def test_disclosure_descriptive_fields_are_not_minimum_runtime_requirements():
    item = evidence(
        "disclosure",
        locator={
            "provider": "opendart_disclosure",
            "receipt_no": DISCLOSURE_RECEIPT,
            "viewer_url": DISCLOSURE_URL,
        },
    )
    result = validate_citations(
        [claim(item.evidence_id)],
        plan("disclosure_summary"),
        [item],
    )
    assert len(result.citations) == 1


@pytest.mark.parametrize(
    ("page_basis", "page"),
    [
        ("pdf_1_based", 1),
        ("printed_page", 2),
        ("source_section_only", None),
    ],
)
def test_report_page_contract_accepts_valid_boundaries(page_basis, page):
    item = evidence("research_report")
    item.locator["page_basis"] = page_basis
    item.locator["page"] = page
    result = validate_citations(
        [claim(item.evidence_id)],
        plan("research_report_summary"),
        [item],
    )
    assert len(result.citations) == 1


@pytest.mark.parametrize(
    ("page_basis", "page"),
    [
        ("pdf_1_based", None),
        ("pdf_1_based", 0),
        ("pdf_1_based", -1),
        ("pdf_1_based", True),
        ("printed_page", False),
        ("source_section_only", 1),
        ("unknown", 1),
    ],
)
def test_report_page_contract_rejects_invalid_boundaries(page_basis, page):
    item = evidence("research_report")
    item.locator["page_basis"] = page_basis
    item.locator["page"] = page
    result = validate_citations(
        [claim(item.evidence_id)],
        plan("research_report_summary"),
        [item],
    )
    assert result.rejections == (CitationRejection("claim-1", "invalid_locator"),)


@pytest.mark.parametrize(
    ("updates", "structural_error"),
    [
        ({"manifest_id": ""}, False),
        ({"document_id": "report:other"}, False),
        ({"section": ""}, False),
        ({"source_url": None, "source_asset_id": None}, False),
        ({"source_url": None, "source_asset_id": "/workspace/private"}, True),
    ],
)
def test_report_minimum_locator_is_enforced(updates, structural_error):
    item = evidence("research_report")
    if updates.get("source_url") is None and "source_url" in updates:
        item = item.model_copy(update={"source_url": None}, deep=True)
    item.locator.update(updates)
    if structural_error:
        with pytest.raises(CitationValidationError) as exc_info:
            validate_citations(
                [claim(item.evidence_id)],
                plan("research_report_summary"),
                [item],
            )
        assert_sanitized(exc_info)
        return
    result = validate_citations(
        [claim(item.evidence_id)],
        plan("research_report_summary"),
        [item],
    )
    assert result.rejections[0].code in {"invalid_locator", "unsafe_source_url"}


def test_report_publisher_and_access_note_are_not_minimum_runtime_requirements():
    item = evidence("research_report")
    item.locator.pop("publisher")
    item.locator.pop("access_note")
    result = validate_citations(
        [claim(item.evidence_id)],
        plan("research_report_summary"),
        [item],
    )
    assert len(result.citations) == 1


@pytest.mark.parametrize(
    "updates",
    [
        {"corpus_id": ""},
        {"entry_id": ""},
        {"version": True},
        {"section": ""},
        {"source_type": "news"},
    ],
)
def test_glossary_minimum_locator_is_enforced(updates):
    item = evidence("glossary")
    item.locator.update(updates)
    result = validate_citations(
        [claim(item.evidence_id)],
        plan("financial_term", target=None),
        [item],
    )
    assert result.rejections == (CitationRejection("claim-1", "invalid_locator"),)


def test_glossary_optional_url_must_match_evidence_url():
    item = evidence(
        "glossary",
        source_url="https://example.com/glossary/roe",
        locator={
            **locator_for(
                "glossary",
                source_url="https://example.com/glossary/other",
                document_id="document:glossary:unit",
            ),
        },
    )
    result = validate_citations(
        [claim(item.evidence_id)],
        plan("financial_term", target=None),
        [item],
    )
    assert result.rejections == (CitationRejection("claim-1", "unsafe_source_url"),)


def test_glossary_provider_and_ingestion_version_are_producer_regression_fields():
    item = evidence("glossary")
    item.locator.pop("provider")
    item.locator.pop("ingestion_version")
    result = validate_citations(
        [claim(item.evidence_id)],
        plan("financial_term", target=None),
        [item],
    )
    assert len(result.citations) == 1


def test_mixed_claims_preserve_order_and_do_not_emit_partial_citations():
    item = evidence()
    claims = [
        claim(item.evidence_id, claim_id="valid"),
        claim("evidence:missing", claim_id="missing"),
        claim(item.evidence_id, claim_id="unsupported", text="Unsupported claim"),
    ]
    result = validate_citations(claims, plan(), [item])
    assert [citation.claim_id for citation in result.citations] == ["valid"]
    assert result.rejections == (
        CitationRejection("missing", "unknown_evidence"),
        CitationRejection("unsupported", "unsupported_claim"),
    )


def test_results_are_deep_copied_deterministic_and_input_is_unchanged():
    item = evidence()
    query_plan = plan()
    citation_claim = claim(item.evidence_id)
    item_before = item.model_dump(mode="python")
    plan_before = query_plan.model_dump(mode="python")
    claim_before = replace(citation_claim)

    first = validate_citations([citation_claim], query_plan, [item])
    second = validate_citations([citation_claim], query_plan, [item])
    assert first == second
    assert first is not second
    assert first.citations is not second.citations
    assert first.citations[0].locator is not second.citations[0].locator

    first.citations[0].locator["provider"] = "changed"
    assert second.citations[0].locator["provider"] == "recorded_news"
    assert item.model_dump(mode="python") == item_before
    assert query_plan.model_dump(mode="python") == plan_before
    assert citation_claim == claim_before


def test_unexpected_internal_runtime_error_propagates(monkeypatch):
    def explode(_result):
        raise RuntimeError("unexpected internal failure")

    monkeypatch.setattr(citation_module, "_audit_result", explode)
    with pytest.raises(RuntimeError, match="unexpected internal failure"):
        validate_citations([claim()], plan(), [evidence()])


@pytest.mark.parametrize(
    ("query", "source_type"),
    [
        ("\uc21c\uc774\uc775\uc774 \ubb50\uc57c?", "glossary"),
        ("\uc0bc\uc131\uc804\uc790 \ucd5c\uadfc \ub274\uc2a4", "news"),
        ("\uc0bc\uc131\uc804\uc790 \uacf5\uc2dc \uc694\uc57d", "disclosure"),
        ("\uc0bc\uc131\uc804\uc790 \ub9ac\ud3ec\ud2b8 \uc694\uc57d", "research_report"),
        ("\uc0bc\uc131\uc804\uc790 \uc704\ud5d8 \uc694\uc778", "news"),
        ("\uc0bc\uc131\uc804\uc790 \ub274\uc2a4\uc640 \uacf5\uc2dc\ub97c \uc885\ud569\ud574\uc918", "news"),
    ],
)
def test_actual_query_planner_outputs_are_citation_capable(query, source_type):
    query_plan = QueryPlanner(basis_date=BASIS_DATE).plan(query)
    item = evidence(source_type)
    result = validate_citations([claim(item.evidence_id)], query_plan, [item])
    assert len(result.citations) == 1


def news_document(
    document_id: str,
    target: str,
    published_at: datetime,
    *,
    text: str = "Samsung earnings improved in the latest quarter.",
) -> FinancialDocument:
    return FinancialDocument(
        document_id=document_id,
        source_type="news",
        provider="recorded_news",
        primary_security_ids=[target],
        mentioned_security_ids=[],
        title="Samsung earnings update",
        published_at=published_at,
        source_url=f"https://news.example.com/{document_id.replace(':', '-')}",
        text=text,
        locator={
            "provider": "recorded_news",
            "source_url": f"https://news.example.com/{document_id.replace(':', '-')}",
            "published_at": published_at.isoformat(),
            "raw_index": 0,
            "query": "Samsung earnings",
        },
        metadata={"document_type": "article"},
        ingestion_version="news-provider-m1-04-v1",
    )


def test_public_m2_capability_composes_into_citation_validation():
    query = "\uc0bc\uc131\uc804\uc790 \ucd5c\uadfc \ub274\uc2a4 samsung earnings"
    query_plan = QueryPlanner(basis_date=BASIS_DATE).plan(query)
    assert query_plan.security is not None
    request = RetrievalRequest(
        query=query,
        security_id=f"{query_plan.security.market}:{query_plan.security.ticker}",
        source_types=list(query_plan.required_sources),
        date_range=query_plan.date_range,
        top_k=6,
    )
    documents = [
        news_document("document:current", SAMSUNG, BASIS_AT - timedelta(days=1)),
        news_document("document:wrong", SK_HYNIX, BASIS_AT - timedelta(days=1)),
        news_document("document:stale", SAMSUNG, BASIS_AT - timedelta(days=31)),
    ]
    documents_by_id = {item.document_id: item for item in documents}
    documents_before = [item.model_dump(mode="python") for item in documents]
    request_before = request.model_dump(mode="python")
    plan_before = query_plan.model_dump(mode="python")

    normalized = normalize_financial_documents(documents)
    normalized_before = [item.model_dump(mode="python") for item in normalized]
    filtered = filter_evidence(normalized, request, documents_by_id=documents_by_id)
    filtered_before = [item.model_dump(mode="python") for item in filtered]
    fresh = evaluate_freshness(
        filtered,
        request,
        documents_by_id=documents_by_id,
        basis_at=BASIS_AT,
    )
    fresh_before = [item.model_dump(mode="python") for item in fresh.evidence]
    retrieved = retrieve_evidence(
        fresh.evidence,
        request,
        documents_by_id=documents_by_id,
    )
    retrieved_before = retrieved.model_dump(mode="python")
    provider_result = create_provider_result(
        status=ProviderStatus.OK,
        data={"items": []},
        fetched_at=BASIS_AT,
    )
    decision = EvidencePolicy().evaluate(
        query_plan,
        {"news": provider_result},
        fresh,
        retrieved,
    )
    decision_before = [
        item.model_dump(mode="python")
        for item in decision.evidence
    ]

    result = validate_citations(
        [
            claim(
                decision.evidence[0].evidence_id,
                text="Samsung earnings improved",
            )
        ],
        query_plan,
        decision.evidence,
    )

    assert query_plan.intent == "recent_issue"
    assert [item.document_id for item in filtered] == ["document:current", "document:stale"]
    assert [item.document_id for item in fresh.evidence] == ["document:current"]
    assert retrieved.status == RetrievalStatus.OK
    assert decision.status == EvidenceDecisionStatus.COMPLETE
    assert [citation.document_id for citation in result.citations] == ["document:current"]
    assert result.citations[0].locator == decision.evidence[0].locator
    assert result.citations[0].source_url == decision.evidence[0].source_url
    assert result.rejections == ()

    assert [item.model_dump(mode="python") for item in documents] == documents_before
    assert request.model_dump(mode="python") == request_before
    assert query_plan.model_dump(mode="python") == plan_before
    assert [item.model_dump(mode="python") for item in normalized] == normalized_before
    assert [item.model_dump(mode="python") for item in filtered] == filtered_before
    assert [item.model_dump(mode="python") for item in fresh.evidence] == fresh_before
    assert retrieved.model_dump(mode="python") == retrieved_before
    assert [item.model_dump(mode="python") for item in decision.evidence] == decision_before


def test_selected_subset_simulates_future_budget_boundary_without_deduping():
    first = evidence(evidence_id="evidence:first")
    second = evidence(
        evidence_id="evidence:second",
        source_url="https://news.example.com/articles/second",
        locator={
            "provider": "recorded_news",
            "source_url": "https://news.example.com/articles/second",
            "published_at": BASIS_AT.isoformat(),
            "raw_index": 1,
        },
    )
    decision = EvidenceDecision(
        status=EvidenceDecisionStatus.COMPLETE,
        evidence=(first, second),
        warnings=(),
        satisfied_sources=("news",),
        missing_sources=(),
        no_data_sources=(),
        failed_sources=(),
    )
    selected_evidence = decision.evidence[:1]
    result = validate_citations(
        [
            claim(first.evidence_id, claim_id="retained"),
            claim(second.evidence_id, claim_id="removed"),
        ],
        plan(),
        selected_evidence,
    )
    assert [citation.claim_id for citation in result.citations] == ["retained"]
    assert result.rejections == (CitationRejection("removed", "unknown_evidence"),)
