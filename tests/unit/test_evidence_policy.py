import ast
from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, timedelta, timezone
import inspect
from types import MappingProxyType

import pytest

from app.core.models import (
    DateRange,
    Evidence,
    FinancialDocument,
    ProviderResult,
    QueryPlan,
    RetrievalRequest,
    RetrievalResult,
    SecurityIdentifier,
)
from app.core.status import EvidenceDecisionStatus, ProviderStatus, RetrievalStatus
from app.evidence.freshness import (
    FreshnessResult,
    FreshnessWarning,
    FreshnessWindow,
    evaluate_freshness,
)
from app.evidence.normalizer import normalize_financial_documents
from app.evidence.policy import EvidencePolicy, EvidencePolicyValidationError
from app.planning.query_planner import QueryPlanner
from app.providers.base import create_provider_result
from app.retrieval import filter_evidence, retrieve_evidence

UTC = timezone.utc
BASIS_AT = datetime(2026, 7, 23, 3, 0, tzinfo=UTC)
BASIS_DATE = date(2026, 7, 23)
SAMSUNG = "KRX:005930"
SK_HYNIX = "KRX:000660"
HYUNDAI = "KRX:005380"

MATRIX = {
    "financial_term": (["glossary"], ["definition"], False),
    "disclosure_summary": (["disclosure"], ["disclosure"], True),
    "research_report_summary": (["research_report"], ["research_report"], True),
    "recent_issue": (["news"], ["recent_news"], True),
    "risk_factors": (
        ["news", "disclosure", "research_report"],
        ["risk", "recent_news", "disclosure", "research_report"],
        True,
    ),
    "multi_source_summary": (
        ["news", "disclosure", "research_report"],
        ["recent_news", "disclosure", "research_report"],
        True,
    ),
}


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
        security_name=names.get(security_id, "Unsupported"),
        security_type="common_stock",
        corp_code=None,
        corp_name=names.get(security_id, "Unsupported"),
    )


def query_plan(
    intent: str = "recent_issue",
    *,
    target: str | None = SAMSUNG,
    date_range: DateRange | None = None,
) -> QueryPlan:
    sources, requirements, security_required = MATRIX[intent]
    return QueryPlan(
        security=security(target) if target is not None else None,
        intent=intent,
        date_range=date_range,
        required_sources=list(sources),
        required_evidence=list(requirements),
        requires_clarification=False,
    )


def clarification(intent: str = "out_of_scope") -> QueryPlan:
    return QueryPlan(
        security=None,
        intent=intent,
        date_range=None,
        required_sources=[],
        required_evidence=[],
        requires_clarification=True,
    )


def evidence(
    source_type: str = "news",
    *,
    target: str = SAMSUNG,
    scope: str = "company_specific",
    subjects: list[str] | None = None,
    mentions: list[str] | None = None,
    evidence_id: str | None = None,
    score: float | None = 0.75,
) -> Evidence:
    default_subjects: list[str]
    default_mentions: list[str]
    if scope == "company_specific":
        default_subjects = [target]
        default_mentions = []
    elif scope == "multi_company":
        default_subjects = [target, SK_HYNIX if target != SK_HYNIX else SAMSUNG]
        default_mentions = []
    else:
        default_subjects = []
        default_mentions = [target]
    item_id = evidence_id or f"evidence:{source_type}:{scope}:{target}"
    return Evidence(
        evidence_id=item_id,
        document_id=f"document:{item_id}",
        source_type=source_type,
        title=f"{source_type} supporting title",
        source_url="https://example.test/source",
        published_at=BASIS_AT - timedelta(days=1),
        subject_security_ids=list(subjects) if subjects is not None else default_subjects,
        mentioned_security_ids=list(mentions) if mentions is not None else default_mentions,
        scope=scope,
        snippet=f"{source_type} supporting evidence",
        locator={"kind": "unit", "id": item_id, "nested": {"values": ["original"]}},
        retrieval_score=score,
    )


def window_for(source: str, plan: QueryPlan, *, mode: str | None = None) -> FreshnessWindow:
    date_range = plan.date_range
    if date_range is not None and (date_range.start is not None or date_range.end is not None):
        return FreshnessWindow(source, date_range.start, date_range.end, "user")
    if source == "glossary":
        return FreshnessWindow(source, None, None, "none")
    days = 30 if source == "news" else 180
    applied_by = mode or "default"
    if applied_by == "fallback":
        days = 365
    return FreshnessWindow(source, BASIS_DATE - timedelta(days=days), BASIS_DATE, applied_by)


def freshness_result(
    plan: QueryPlan,
    items: list[Evidence] | tuple[Evidence, ...] = (),
    *,
    warnings: tuple[FreshnessWarning, ...] = (),
    windows: tuple[FreshnessWindow, ...] | None = None,
) -> FreshnessResult:
    if windows is None:
        windows = tuple(window_for(source, plan) for source in plan.required_sources)
    return FreshnessResult(
        basis_at=BASIS_AT,
        basis_date=BASIS_DATE,
        windows=windows,
        evidence=tuple(item.model_copy(deep=True, update={"retrieval_score": None}) for item in items),
        warnings=warnings,
        latest_effective_disclosure_at=None,
    )


def retrieval_result(
    items: list[Evidence] | tuple[Evidence, ...] = (),
    *,
    status: RetrievalStatus | str | None = None,
    low_relevance: bool | None = None,
) -> RetrievalResult:
    if status is None:
        status = RetrievalStatus.OK if items else RetrievalStatus.EMPTY
    if low_relevance is None:
        low_relevance = status == RetrievalStatus.LOW_RELEVANCE
    return RetrievalResult(
        evidence=[item.model_copy(deep=True) for item in items],
        status=status,
        strategy="lexical-bm25-m2-03-v1",
        low_relevance=low_relevance,
        diagnostics={},
    )


def provider(
    status: ProviderStatus,
    *,
    error_code: str | None = None,
) -> ProviderResult[object]:
    return create_provider_result(
        status=status,
        data={"items": []} if status == ProviderStatus.OK else None,
        error_code=error_code,
        fetched_at=BASIS_AT,
    )


def evaluate(
    plan: QueryPlan,
    items: list[Evidence] | tuple[Evidence, ...] = (),
    *,
    providers: dict[str, ProviderResult[object]] | None = None,
    freshness: FreshnessResult | None = None,
    retrieval: RetrievalResult | None = None,
):
    return EvidencePolicy().evaluate(
        plan,
        providers or {},
        freshness or freshness_result(plan, items),
        retrieval or retrieval_result(items),
    )


def assert_sanitized(exc_info: pytest.ExceptionInfo[EvidencePolicyValidationError]) -> None:
    message = str(exc_info.value)
    assert message in {
        "plan must be a QueryPlan",
        "provider results must be a source mapping",
        "provider results are invalid",
        "freshness result is invalid",
        "retrieval result is invalid",
        "policy inputs are inconsistent",
    }
    assert "sentinel-secret" not in message
    assert "C:\\" not in message
    assert "/root" not in message


def test_complete_requires_threshold_evidence_for_every_required_source():
    plan = query_plan("risk_factors")
    items = [
        evidence("news", evidence_id="evidence:news"),
        evidence("disclosure", evidence_id="evidence:disclosure"),
        evidence("research_report", evidence_id="evidence:report"),
    ]
    result = evaluate(plan, items)
    assert result.status == EvidenceDecisionStatus.COMPLETE
    assert result.satisfied_sources == ("news", "disclosure", "research_report")
    assert result.missing_sources == ()
    assert result.no_data_sources == ()
    assert result.failed_sources == ()


def test_missing_one_required_source_is_partial_in_matrix_order():
    plan = query_plan("risk_factors")
    items = [
        evidence("news", evidence_id="evidence:news"),
        evidence("research_report", evidence_id="evidence:report"),
    ]
    result = evaluate(plan, items)
    assert result.status == EvidenceDecisionStatus.PARTIAL
    assert result.satisfied_sources == ("news", "research_report")
    assert result.missing_sources == ("disclosure",)


def test_all_required_sources_missing_is_no_evidence():
    result = evaluate(query_plan(), [])
    assert result.status == EvidenceDecisionStatus.NO_EVIDENCE
    assert result.evidence == ()
    assert result.missing_sources == ("news",)


@pytest.mark.parametrize(
    "status",
    [
        ProviderStatus.TIMEOUT,
        ProviderStatus.RATE_LIMITED,
        ProviderStatus.PROVIDER_UNAVAILABLE,
        ProviderStatus.PARSE_ERROR,
        ProviderStatus.UNAUTHORIZED,
        ProviderStatus.INVALID_QUERY,
    ],
)
def test_each_provider_failure_without_evidence_is_provider_failed(status):
    result = evaluate(query_plan(), providers={"news": provider(status)})
    assert result.status == EvidenceDecisionStatus.PROVIDER_FAILED
    assert result.failed_sources == ("news",)
    assert result.no_data_sources == ()
    assert result.evidence == ()


def test_timeout_stable_error_code_variants_are_accepted():
    for code in ("attempt_timeout", "total_deadline_exceeded"):
        result = evaluate(
            query_plan(),
            providers={"news": provider(ProviderStatus.TIMEOUT, error_code=code)},
        )
        assert result.status == EvidenceDecisionStatus.PROVIDER_FAILED


def test_provider_no_data_is_not_failure():
    result = evaluate(query_plan(), providers={"news": provider(ProviderStatus.NO_DATA)})
    assert result.status == EvidenceDecisionStatus.NO_EVIDENCE
    assert result.no_data_sources == ("news",)
    assert result.failed_sources == ()


def test_provider_ok_without_retrieval_evidence_is_no_evidence():
    result = evaluate(query_plan(), providers={"news": provider(ProviderStatus.OK)})
    assert result.status == EvidenceDecisionStatus.NO_EVIDENCE
    assert result.missing_sources == ("news",)


@pytest.mark.parametrize("status", [ProviderStatus.NO_DATA, ProviderStatus.PROVIDER_UNAVAILABLE])
def test_provider_problem_with_usable_evidence_is_partial(status):
    item = evidence()
    result = evaluate(query_plan(), [item], providers={"news": provider(status)})
    assert result.status == EvidenceDecisionStatus.PARTIAL
    if status == ProviderStatus.NO_DATA:
        assert result.no_data_sources == ("news",)
    else:
        assert result.failed_sources == ("news",)


def test_local_corpus_sources_can_complete_without_provider_mapping():
    glossary_plan = query_plan("financial_term", target=None)
    report_plan = query_plan("research_report_summary")
    assert evaluate(glossary_plan, [evidence("glossary")]).status == EvidenceDecisionStatus.COMPLETE
    assert (
        evaluate(report_plan, [evidence("research_report")]).status
        == EvidenceDecisionStatus.COMPLETE
    )


def test_extra_provider_result_does_not_affect_decision_or_order():
    item = evidence()
    first = evaluate(
        query_plan(),
        [item],
        providers={
            "glossary": provider(ProviderStatus.PROVIDER_UNAVAILABLE),
            "news": provider(ProviderStatus.OK),
        },
    )
    second = evaluate(
        query_plan(),
        [item],
        providers={
            "news": provider(ProviderStatus.OK),
            "glossary": provider(ProviderStatus.PROVIDER_UNAVAILABLE),
        },
    )
    assert first == second
    assert first.status == EvidenceDecisionStatus.COMPLETE


def test_low_relevance_maps_to_no_evidence_without_provider_failure():
    result = evaluate(
        query_plan(),
        freshness=freshness_result(query_plan(), [evidence()]),
        retrieval=retrieval_result([], status=RetrievalStatus.LOW_RELEVANCE),
    )
    assert result.status == EvidenceDecisionStatus.NO_EVIDENCE


def test_low_relevance_with_provider_failure_maps_to_provider_failed():
    result = evaluate(
        query_plan(),
        providers={"news": provider(ProviderStatus.TIMEOUT)},
        freshness=freshness_result(query_plan(), [evidence()]),
        retrieval=retrieval_result([], status=RetrievalStatus.LOW_RELEVANCE),
    )
    assert result.status == EvidenceDecisionStatus.PROVIDER_FAILED


@pytest.mark.parametrize(
    ("intent", "source", "warning_code"),
    [
        ("recent_issue", "news", "stale_news"),
        ("research_report_summary", "research_report", "stale_research_report"),
        ("disclosure_summary", "disclosure", "insufficient_disclosure_coverage"),
        ("disclosure_summary", "disclosure", "unresolved_disclosure_correction"),
    ],
)
def test_limiting_freshness_warning_prevents_complete(intent, source, warning_code):
    plan = query_plan(intent)
    item = evidence(source)
    result = evaluate(
        plan,
        [item],
        freshness=freshness_result(
            plan,
            [item],
            warnings=(FreshnessWarning(warning_code, source),),
        ),
    )
    assert result.status == EvidenceDecisionStatus.PARTIAL
    assert result.warnings == (FreshnessWarning(warning_code, source),)


def test_disclosure_window_extended_is_informational_only():
    plan = query_plan("disclosure_summary")
    item = evidence("disclosure")
    windows = (window_for("disclosure", plan, mode="fallback"),)
    result = evaluate(
        plan,
        [item],
        freshness=freshness_result(
            plan,
            [item],
            windows=windows,
            warnings=(FreshnessWarning("disclosure_window_extended", "disclosure"),),
        ),
    )
    assert result.status == EvidenceDecisionStatus.COMPLETE


@pytest.mark.parametrize("warning_code", ["missing_published_at", "future_published_at"])
def test_date_quality_warning_is_preserved_without_forcing_partial(warning_code):
    plan = query_plan()
    item = evidence()
    result = evaluate(
        plan,
        [item],
        freshness=freshness_result(
            plan,
            [item],
            warnings=(FreshnessWarning(warning_code, "news"),),
        ),
    )
    assert result.status == EvidenceDecisionStatus.COMPLETE
    assert result.warnings == (FreshnessWarning(warning_code, "news"),)


def test_warning_for_source_outside_windows_is_rejected():
    plan = query_plan()
    bad = freshness_result(
        plan,
        [evidence()],
        warnings=(FreshnessWarning("unresolved_disclosure_correction", "disclosure"),),
    )
    with pytest.raises(EvidencePolicyValidationError) as exc_info:
        evaluate(plan, [evidence()], freshness=bad)
    assert_sanitized(exc_info)


@pytest.mark.parametrize(
    "warnings",
    [
        (
            FreshnessWarning("stale_news", "news"),
            FreshnessWarning("stale_news", "news"),
        ),
        (
            FreshnessWarning("stale_news", "news"),
            FreshnessWarning("missing_published_at", "news"),
        ),
        (FreshnessWarning("stale_news", "disclosure"),),
    ],
)
def test_duplicate_out_of_order_or_incompatible_warning_is_rejected(warnings):
    plan = query_plan()
    bad = freshness_result(plan, [evidence()], warnings=warnings)
    with pytest.raises(EvidencePolicyValidationError) as exc_info:
        evaluate(plan, [evidence()], freshness=bad)
    assert_sanitized(exc_info)


@pytest.mark.parametrize(
    "query",
    [
        "\uc21c\uc774\uc775\uc774 \ubb50\uc57c?",
        "\uc0bc\uc131\uc804\uc790 \uacf5\uc2dc \uc694\uc57d",
        "\uc0bc\uc131\uc804\uc790 \ub9ac\ud3ec\ud2b8 \uc694\uc57d",
        "\uc0bc\uc131\uc804\uc790 \ucd5c\uadfc \ub274\uc2a4",
        "\uc0bc\uc131\uc804\uc790 \uc704\ud5d8 \uc694\uc778",
        "\uc0bc\uc131\uc804\uc790 \ub274\uc2a4\uc640 \uacf5\uc2dc\ub97c \uc885\ud569\ud574\uc918",
    ],
)
def test_actual_query_planner_outputs_match_policy_matrix(query):
    plan = QueryPlanner(basis_date=BASIS_DATE).plan(query)
    result = evaluate(plan)
    assert result.status == EvidenceDecisionStatus.NO_EVIDENCE


def test_public_recent_news_pipeline_composes_to_complete_without_mutating_inputs():
    query = "\uc0bc\uc131\uc804\uc790 \ucd5c\uadfc \ub274\uc2a4 samsung earnings"
    plan = QueryPlanner(basis_date=BASIS_DATE).plan(query)
    assert plan.security is not None
    planned_security_id = f"{plan.security.market}:{plan.security.ticker}"
    request = RetrievalRequest(
        query=query,
        security_id=planned_security_id,
        source_types=list(plan.required_sources),
        date_range=plan.date_range,
        top_k=6,
    )

    def news_document(
        document_id: str,
        target: str,
        published_at: datetime,
    ) -> FinancialDocument:
        return FinancialDocument(
            document_id=document_id,
            source_type="news",
            provider="recorded_news",
            primary_security_ids=[target],
            mentioned_security_ids=[],
            title="Samsung earnings semiconductor outlook",
            published_at=published_at,
            source_url=f"https://example.test/{document_id.replace(':', '-')}",
            text="Samsung earnings semiconductor outlook remains relevant.",
            locator={"kind": "unit", "document_id": document_id},
            metadata={"document_type": "article"},
            ingestion_version="news-provider-m1-04-v1",
        )

    documents = [
        news_document("document:news:current", SAMSUNG, BASIS_AT - timedelta(days=1)),
        news_document("document:news:wrong-company", SK_HYNIX, BASIS_AT - timedelta(days=1)),
        news_document("document:news:stale", SAMSUNG, BASIS_AT - timedelta(days=31)),
    ]
    documents_by_id = {item.document_id: item for item in documents}
    provider_results = {"news": provider(ProviderStatus.OK)}
    plan_before = plan.model_dump(mode="python")
    request_before = request.model_dump(mode="python")
    documents_before = [item.model_dump(mode="python") for item in documents]
    providers_before = {
        key: value.model_dump(mode="python")
        for key, value in provider_results.items()
    }

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
    freshness_before = [
        item.model_dump(mode="python")
        for item in fresh.evidence
    ]
    retrieved = retrieve_evidence(
        fresh.evidence,
        request,
        documents_by_id=documents_by_id,
    )
    retrieval_before = retrieved.model_dump(mode="python")
    decision = EvidencePolicy().evaluate(plan, provider_results, fresh, retrieved)

    assert plan.intent == "recent_issue"
    assert plan.required_sources == ["news"]
    assert [item.document_id for item in filtered] == [
        "document:news:current",
        "document:news:stale",
    ]
    assert "document:news:wrong-company" not in {
        item.document_id
        for item in filtered
    }
    assert [item.document_id for item in fresh.evidence] == ["document:news:current"]
    assert "document:news:stale" not in {
        item.document_id
        for item in fresh.evidence
    }
    assert retrieved.status == RetrievalStatus.OK
    assert [item.document_id for item in retrieved.evidence] == ["document:news:current"]
    assert all(
        item.retrieval_score is not None and item.retrieval_score >= 0.5
        for item in retrieved.evidence
    )
    assert all(item.subject_security_ids == [SAMSUNG] for item in retrieved.evidence)
    assert decision.status == EvidenceDecisionStatus.COMPLETE
    assert decision.satisfied_sources == ("news",)
    assert decision.missing_sources == ()
    assert [item.document_id for item in decision.evidence] == ["document:news:current"]
    assert decision.evidence[0].subject_security_ids == [SAMSUNG]

    assert plan.model_dump(mode="python") == plan_before
    assert request.model_dump(mode="python") == request_before
    assert [item.model_dump(mode="python") for item in documents] == documents_before
    assert [item.model_dump(mode="python") for item in normalized] == normalized_before
    assert [item.model_dump(mode="python") for item in filtered] == filtered_before
    assert [item.model_dump(mode="python") for item in fresh.evidence] == freshness_before
    assert retrieved.model_dump(mode="python") == retrieval_before
    assert {
        key: value.model_dump(mode="python")
        for key, value in provider_results.items()
    } == providers_before


@pytest.mark.parametrize("field", ["required_sources", "required_evidence", "requires_clarification"])
def test_one_field_drift_from_actual_planner_output_is_rejected(field):
    plan = QueryPlanner(basis_date=BASIS_DATE).plan("\uc0bc\uc131\uc804\uc790 \ucd5c\uadfc \ub274\uc2a4")
    updates = {
        "required_sources": ["disclosure"],
        "required_evidence": ["disclosure"],
        "requires_clarification": True,
    }
    drifted = plan.model_copy(deep=True, update={field: updates[field]})
    with pytest.raises(EvidencePolicyValidationError) as exc_info:
        evaluate(drifted)
    assert_sanitized(exc_info)


def test_security_required_plan_without_security_is_rejected():
    bad = query_plan().model_copy(update={"security": None})
    with pytest.raises(EvidencePolicyValidationError) as exc_info:
        evaluate(bad)
    assert_sanitized(exc_info)


def test_unsupported_security_id_is_rejected():
    bad = query_plan().model_copy(update={"security": security("KRX:999999")})
    with pytest.raises(EvidencePolicyValidationError) as exc_info:
        evaluate(bad)
    assert_sanitized(exc_info)


def test_non_clarification_prohibited_or_out_of_scope_is_rejected():
    for intent in ("prohibited_advice", "out_of_scope"):
        bad = QueryPlan(
            security=None,
            intent=intent,
            required_sources=[],
            required_evidence=[],
            requires_clarification=False,
        )
        with pytest.raises(EvidencePolicyValidationError) as exc_info:
            evaluate(bad)
        assert_sanitized(exc_info)


def test_exact_prohibited_plan_is_blocked_and_discards_valid_downstream_values():
    plan = clarification("prohibited_advice")
    item = evidence()
    downstream_freshness = FreshnessResult(
        basis_at=BASIS_AT,
        basis_date=BASIS_DATE,
        windows=(window_for("news", query_plan()),),
        evidence=(item.model_copy(update={"retrieval_score": None}),),
        warnings=(FreshnessWarning("stale_news", "news"),),
        latest_effective_disclosure_at=None,
    )
    result = evaluate(
        plan,
        providers={"news": provider(ProviderStatus.TIMEOUT)},
        freshness=downstream_freshness,
        retrieval=retrieval_result([item]),
    )
    assert result.status == EvidenceDecisionStatus.BLOCKED
    assert result.evidence == ()
    assert result.warnings == ()
    assert result.satisfied_sources == ()
    assert result.missing_sources == ()
    assert result.no_data_sources == ()
    assert result.failed_sources == ()


@pytest.mark.parametrize(
    "plan",
    [
        clarification("out_of_scope"),
        clarification("recent_issue"),
        clarification("financial_term"),
    ],
)
def test_non_prohibited_clarification_is_no_evidence_with_empty_collections(plan):
    result = evaluate(plan)
    assert result.status == EvidenceDecisionStatus.NO_EVIDENCE
    assert result.evidence == ()
    assert result.warnings == ()
    assert result.satisfied_sources == ()
    assert result.missing_sources == ()


def test_actual_financial_term_conflicting_security_clarification_is_accepted():
    plan = QueryPlanner(basis_date=BASIS_DATE).plan(
        "\uc0bc\uc131 PER\uc774 \ubb50\uc57c?"
    )
    assert plan.intent == "financial_term"
    assert plan.requires_clarification is True
    assert evaluate(plan).status == EvidenceDecisionStatus.NO_EVIDENCE


def test_wrong_company_company_specific_retrieval_is_rejected():
    plan = query_plan()
    wrong = evidence(target=SK_HYNIX)
    with pytest.raises(EvidencePolicyValidationError) as exc_info:
        evaluate(plan, [wrong])
    assert_sanitized(exc_info)


def test_multi_company_requires_target_in_subjects():
    plan = query_plan()
    wrong = evidence(
        scope="multi_company",
        subjects=[SK_HYNIX, HYUNDAI],
        evidence_id="evidence:multi:wrong",
    )
    valid = evidence(
        scope="multi_company",
        subjects=[SAMSUNG, SK_HYNIX],
        evidence_id="evidence:multi:valid",
    )
    with pytest.raises(EvidencePolicyValidationError):
        evaluate(plan, [wrong])
    assert evaluate(plan, [valid]).status == EvidenceDecisionStatus.COMPLETE


def test_industry_common_requires_target_in_mentions():
    plan = query_plan()
    wrong = evidence(
        scope="industry_common",
        subjects=[],
        mentions=[SK_HYNIX],
        evidence_id="evidence:industry:wrong",
    )
    valid = evidence(
        scope="industry_common",
        subjects=[],
        mentions=[SAMSUNG],
        evidence_id="evidence:industry:valid",
    )
    with pytest.raises(EvidencePolicyValidationError):
        evaluate(plan, [wrong])
    assert evaluate(plan, [valid]).status == EvidenceDecisionStatus.COMPLETE


def test_unselected_wrong_company_freshness_candidate_is_not_refiltered():
    plan = query_plan()
    selected = evidence(evidence_id="evidence:selected")
    unselected = evidence(target=SK_HYNIX, evidence_id="evidence:unselected")
    result = evaluate(
        plan,
        [selected],
        freshness=freshness_result(plan, [selected, unselected]),
    )
    assert result.status == EvidenceDecisionStatus.COMPLETE
    assert [item.evidence_id for item in result.evidence] == ["evidence:selected"]


def test_financial_term_does_not_add_company_target_filter():
    plan = query_plan("financial_term", target=None)
    glossary = evidence("glossary", target=SK_HYNIX)
    assert evaluate(plan, [glossary]).status == EvidenceDecisionStatus.COMPLETE


def test_scored_retrieval_matches_unscored_freshness_occurrence():
    plan = query_plan()
    item = evidence(score=0.5)
    result = evaluate(plan, [item])
    assert result.status == EvidenceDecisionStatus.COMPLETE
    assert result.evidence[0].retrieval_score == 0.5


def test_retrieval_evidence_absent_from_freshness_is_rejected():
    plan = query_plan()
    first = evidence(evidence_id="evidence:first")
    other = evidence(evidence_id="evidence:other")
    with pytest.raises(EvidencePolicyValidationError) as exc_info:
        evaluate(plan, [other], freshness=freshness_result(plan, [first]))
    assert_sanitized(exc_info)


def test_retrieval_occurrence_count_cannot_exceed_freshness():
    plan = query_plan()
    item = evidence()
    with pytest.raises(EvidencePolicyValidationError) as exc_info:
        evaluate(
            plan,
            [item, item],
            freshness=freshness_result(plan, [item]),
        )
    assert_sanitized(exc_info)


@pytest.mark.parametrize("score", [None, 0.499999, float("nan"), float("inf"), -float("inf")])
def test_retrieval_ok_rejects_missing_below_threshold_or_nonfinite_score(score):
    plan = query_plan()
    item = evidence(score=score)
    with pytest.raises(EvidencePolicyValidationError) as exc_info:
        evaluate(plan, [item])
    assert_sanitized(exc_info)


def test_retrieval_empty_or_low_relevance_cannot_carry_evidence():
    plan = query_plan()
    item = evidence()
    for status, low_relevance in (
        (RetrievalStatus.EMPTY, False),
        (RetrievalStatus.LOW_RELEVANCE, True),
    ):
        bad = RetrievalResult.model_construct(
            evidence=[item],
            status=status.value,
            strategy="lexical-bm25-m2-03-v1",
            low_relevance=low_relevance,
            diagnostics={},
        )
        with pytest.raises(EvidencePolicyValidationError) as exc_info:
            evaluate(plan, [item], retrieval=bad)
        assert_sanitized(exc_info)


def test_retrieval_low_relevance_flag_must_match_status():
    plan = query_plan()
    bad = RetrievalResult.model_construct(
        evidence=[],
        status=RetrievalStatus.LOW_RELEVANCE.value,
        strategy="lexical-bm25-m2-03-v1",
        low_relevance=False,
        diagnostics={},
    )
    with pytest.raises(EvidencePolicyValidationError) as exc_info:
        evaluate(plan, retrieval=bad)
    assert_sanitized(exc_info)


def test_freshness_window_source_order_must_match_plan():
    plan = query_plan("risk_factors")
    windows = tuple(reversed(tuple(window_for(source, plan) for source in plan.required_sources)))
    with pytest.raises(EvidencePolicyValidationError) as exc_info:
        evaluate(plan, freshness=freshness_result(plan, windows=windows))
    assert_sanitized(exc_info)


def test_explicit_plan_date_requires_equal_user_windows():
    requested = DateRange(start=date(2026, 7, 1), end=date(2026, 7, 2))
    plan = query_plan(date_range=requested)
    valid = freshness_result(plan)
    assert evaluate(plan, freshness=valid).status == EvidenceDecisionStatus.NO_EVIDENCE

    non_user = replace(valid.windows[0], applied_by="default")
    unequal = replace(valid.windows[0], end=date(2026, 7, 3))
    for bad_window in (non_user, unequal):
        with pytest.raises(EvidencePolicyValidationError) as exc_info:
            evaluate(plan, freshness=replace(valid, windows=(bad_window,)))
        assert_sanitized(exc_info)


def test_no_meaningful_date_range_rejects_user_window():
    plan = query_plan(date_range=DateRange())
    bad_window = FreshnessWindow("news", date(2026, 7, 1), date(2026, 7, 2), "user")
    with pytest.raises(EvidencePolicyValidationError) as exc_info:
        evaluate(plan, freshness=freshness_result(plan, windows=(bad_window,)))
    assert_sanitized(exc_info)


def test_returned_evidence_is_deep_copy_and_inputs_are_unchanged():
    plan = query_plan()
    item = evidence()
    fresh = freshness_result(plan, [item])
    retrieved = retrieval_result([item])
    original_item = item.model_dump()
    original_fresh = fresh.evidence[0].model_dump()
    original_retrieved = retrieved.evidence[0].model_dump()

    result = evaluate(plan, [item], freshness=fresh, retrieval=retrieved)
    result.evidence[0].subject_security_ids.append(SK_HYNIX)
    result.evidence[0].locator["nested"]["values"].append("changed")

    assert item.model_dump() == original_item
    assert fresh.evidence[0].model_dump() == original_fresh
    assert retrieved.evidence[0].model_dump() == original_retrieved


def test_frozen_result_and_duplicate_occurrences_are_preserved():
    plan = query_plan()
    item = evidence()
    result = evaluate(plan, [item, item])
    assert len(result.evidence) == 2
    assert result.evidence[0] == result.evidence[1]
    with pytest.raises(FrozenInstanceError):
        result.status = EvidenceDecisionStatus.PARTIAL  # type: ignore[misc]


def test_repeated_evaluation_is_deterministic_and_mapping_proxy_is_accepted():
    plan = query_plan()
    item = evidence()
    providers = MappingProxyType({"news": provider(ProviderStatus.OK)})
    fresh = freshness_result(plan, [item])
    retrieved = retrieval_result([item])
    first = EvidencePolicy().evaluate(plan, providers, fresh, retrieved)
    second = EvidencePolicy().evaluate(plan, providers, fresh, retrieved)
    assert first == second


@pytest.mark.parametrize("bad_plan", [None, "bad", object()])
def test_wrong_plan_type_is_sanitized(bad_plan):
    with pytest.raises(EvidencePolicyValidationError) as exc_info:
        EvidencePolicy().evaluate(  # type: ignore[arg-type]
            bad_plan,
            {},
            freshness_result(query_plan()),
            retrieval_result(),
        )
    assert_sanitized(exc_info)


def test_model_constructed_malformed_plan_is_sanitized():
    bad = QueryPlan.model_construct(
        security=security(),
        intent="recent_issue",
        date_range=None,
        required_sources=["news", 3],
        required_evidence=["recent_news"],
        requires_clarification=False,
    )
    with pytest.raises(EvidencePolicyValidationError) as exc_info:
        evaluate(bad)
    assert_sanitized(exc_info)


@pytest.mark.parametrize("bad_mapping", [None, [], "bad", 3])
def test_wrong_provider_mapping_type_is_sanitized(bad_mapping):
    plan = query_plan()
    with pytest.raises(EvidencePolicyValidationError) as exc_info:
        EvidencePolicy().evaluate(
            plan,
            bad_mapping,  # type: ignore[arg-type]
            freshness_result(plan),
            retrieval_result(),
        )
    assert_sanitized(exc_info)


@pytest.mark.parametrize("bad_key", ["", " ", "market", 3])
def test_bad_provider_mapping_key_is_sanitized(bad_key):
    plan = query_plan()
    with pytest.raises(EvidencePolicyValidationError) as exc_info:
        EvidencePolicy().evaluate(
            plan,
            {bad_key: provider(ProviderStatus.OK)},  # type: ignore[dict-item]
            freshness_result(plan),
            retrieval_result(),
        )
    assert_sanitized(exc_info)


def test_wrong_provider_result_item_type_is_sanitized():
    plan = query_plan()
    with pytest.raises(EvidencePolicyValidationError) as exc_info:
        EvidencePolicy().evaluate(
            plan,
            {"news": object()},  # type: ignore[dict-item]
            freshness_result(plan),
            retrieval_result(),
        )
    assert_sanitized(exc_info)


def test_malformed_provider_result_and_raw_message_are_sanitized():
    bad = ProviderResult.model_construct(
        status=ProviderStatus.PROVIDER_UNAVAILABLE.value,
        data=None,
        error_code="provider_unavailable",
        message="sentinel-secret C:\\private /root/file",
        fetched_at=BASIS_AT,
        from_cache=False,
    )
    with pytest.raises(EvidencePolicyValidationError) as exc_info:
        evaluate(query_plan(), providers={"news": bad})
    assert_sanitized(exc_info)


def test_naive_provider_timestamp_is_rejected():
    bad = ProviderResult.model_construct(
        status=ProviderStatus.NO_DATA.value,
        data=None,
        error_code=None,
        message=None,
        fetched_at=datetime(2026, 7, 23, 3, 0),
        from_cache=False,
    )
    with pytest.raises(EvidencePolicyValidationError) as exc_info:
        evaluate(query_plan(), providers={"news": bad})
    assert_sanitized(exc_info)


@pytest.mark.parametrize(
    "update",
    [
        {"windows": []},
        {"evidence": []},
        {"warnings": []},
        {"basis_at": datetime(2026, 7, 23, 3, 0)},
        {"basis_date": date(2026, 7, 22)},
    ],
)
def test_malformed_direct_freshness_result_is_sanitized(update):
    plan = query_plan()
    bad = replace(freshness_result(plan), **update)
    with pytest.raises(EvidencePolicyValidationError) as exc_info:
        evaluate(plan, freshness=bad)
    assert_sanitized(exc_info)


@pytest.mark.parametrize(
    "update",
    [
        {"windows": (object(),)},
        {"warnings": (object(),)},
        {"evidence": (object(),)},
    ],
)
def test_malformed_direct_freshness_items_are_sanitized(update):
    plan = query_plan()
    bad = replace(freshness_result(plan), **update)
    with pytest.raises(EvidencePolicyValidationError) as exc_info:
        evaluate(plan, freshness=bad)
    assert_sanitized(exc_info)


def test_wrong_retrieval_type_and_model_constructed_fields_are_sanitized():
    plan = query_plan()
    with pytest.raises(EvidencePolicyValidationError) as exc_info:
        EvidencePolicy().evaluate(
            plan,
            {},
            freshness_result(plan),
            object(),  # type: ignore[arg-type]
        )
    assert_sanitized(exc_info)

    malformed = RetrievalResult.model_construct(
        evidence=(),
        status=RetrievalStatus.EMPTY.value,
        strategy="lexical-bm25-m2-03-v1",
        low_relevance=False,
        diagnostics={},
    )
    with pytest.raises(EvidencePolicyValidationError) as exc_info:
        evaluate(plan, retrieval=malformed)
    assert_sanitized(exc_info)


def test_policy_module_does_not_import_planner_provider_or_later_step_modules():
    source = inspect.getsource(__import__("app.evidence.policy", fromlist=["*"]))
    tree = ast.parse(source)
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    forbidden = {
        "app.planning",
        "app.providers",
        "app.api",
        "app.llm",
        "app.evidence.citation",
        "app.evidence.dedupe",
        "app.evidence.context_budget",
    }
    assert not any(
        module == blocked or module.startswith(f"{blocked}.")
        for module in imported_modules
        for blocked in forbidden
    )
