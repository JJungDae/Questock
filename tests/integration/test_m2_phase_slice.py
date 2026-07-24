from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Mapping, Sequence

from app.core.models import (
    Evidence,
    FinancialAnswer,
    FinancialDocument,
    ProviderResult,
    QueryPlan,
    RetrievalRequest,
    RetrievalResult,
)
from app.core.status import EvidenceDecisionStatus, ProviderStatus, RetrievalStatus
from app.evidence.budget import ContextBudgetResult, select_evidence_context
from app.evidence.citations import (
    CitationClaim,
    CitationRejection,
    CitationValidationResult,
    validate_citations,
)
from app.evidence.freshness import FreshnessResult, evaluate_freshness
from app.evidence.normalizer import normalize_financial_documents
from app.evidence.policy import EvidenceDecision, EvidencePolicy
from app.planning.query_planner import QueryPlanner
from app.providers.base import create_provider_result
from app.retrieval import filter_evidence, retrieve_evidence

BASIS_AT = datetime(2026, 7, 24, 3, 0, tzinfo=UTC)
SAMSUNG = "KRX:005930"
SK_HYNIX = "KRX:000660"
DEFAULT_QUERY = "삼성전자 최근 뉴스"

NO_EVIDENCE_ANSWER = "답변에 사용할 근거를 확인하지 못했습니다."
PROVIDER_FAILED_ANSWER = "자료 제공 오류로 답변을 보류합니다."
BLOCKED_ANSWER = "안전 정책에 따라 이 요청에는 답변할 수 없습니다."

_FIXED_EMPTY_ANSWERS = {
    EvidenceDecisionStatus.NO_EVIDENCE: NO_EVIDENCE_ANSWER,
    EvidenceDecisionStatus.PROVIDER_FAILED: PROVIDER_FAILED_ANSWER,
    EvidenceDecisionStatus.BLOCKED: BLOCKED_ANSWER,
}


@dataclass(frozen=True)
class _PhaseSliceResult:
    plan: QueryPlan
    request: RetrievalRequest
    normalized: tuple[Evidence, ...]
    hard_filtered: tuple[Evidence, ...]
    freshness: FreshnessResult
    retrieval: RetrievalResult
    decision: EvidenceDecision
    budget: ContextBudgetResult
    claims: tuple[CitationClaim, ...]
    citations: CitationValidationResult
    answer: FinancialAnswer


def _news_document(
    document_id: str,
    *,
    security_id: str = SAMSUNG,
    published_at: datetime = BASIS_AT - timedelta(days=1),
    title: str = "삼성전자 반도체 투자 뉴스",
    text: str = "삼성전자 반도체 투자 확대 소식이 발표됐다.",
    raw_index: int = 0,
    query: str = DEFAULT_QUERY,
) -> FinancialDocument:
    slug = document_id.replace(":", "-")
    source_url = f"https://news.example.test/{slug}"
    return FinancialDocument(
        document_id=document_id,
        source_type="news",
        provider="recorded_news",
        primary_security_ids=[security_id],
        mentioned_security_ids=[],
        title=title,
        published_at=published_at,
        source_url=source_url,
        text=text,
        locator={
            "provider": "recorded_news",
            "source_url": source_url,
            "published_at": published_at.isoformat(),
            "raw_index": raw_index,
            "query": query,
        },
        metadata={},
        ingestion_version="news-provider-m1-04-v1",
    )


def _ok_provider_result(
    documents: Sequence[FinancialDocument],
) -> ProviderResult[dict[str, list[str]]]:
    return create_provider_result(
        status=ProviderStatus.OK,
        data={"document_ids": [item.document_id for item in documents]},
        fetched_at=BASIS_AT,
    )


def _model_snapshots(models: Sequence[Any]) -> tuple[dict[str, Any], ...]:
    return tuple(item.model_dump(mode="python") for item in models)


def _run_phase_slice(
    raw_query: str,
    documents: Sequence[FinancialDocument],
    provider_results_by_source: Mapping[str, ProviderResult[Any]],
) -> _PhaseSliceResult:
    document_snapshots = _model_snapshots(documents)
    provider_snapshots = {
        source: result.model_dump(mode="python")
        for source, result in provider_results_by_source.items()
    }

    plan = QueryPlanner(basis_date=BASIS_AT.date()).plan(raw_query)
    assert plan.security is not None
    assert not plan.requires_clarification
    plan_snapshot = plan.model_dump(mode="python")

    request = RetrievalRequest(
        query=raw_query,
        security_id=f"{plan.security.market}:{plan.security.ticker}",
        source_types=list(plan.required_sources),
        date_range=plan.date_range.model_copy(deep=True) if plan.date_range else None,
    )
    request_snapshot = request.model_dump(mode="python")
    documents_by_id = {item.document_id: item for item in documents}

    normalized = normalize_financial_documents(documents)
    normalized_snapshot = _model_snapshots(normalized)
    hard_filtered = filter_evidence(
        normalized,
        request,
        documents_by_id=documents_by_id,
    )
    hard_filtered_snapshot = _model_snapshots(hard_filtered)
    freshness = evaluate_freshness(
        hard_filtered,
        request,
        documents_by_id=documents_by_id,
        basis_at=BASIS_AT,
    )
    freshness_evidence_snapshot = _model_snapshots(freshness.evidence)
    retrieval = retrieve_evidence(
        freshness.evidence,
        request,
        documents_by_id=documents_by_id,
    )
    retrieval_snapshot = retrieval.model_dump(mode="python")
    decision = EvidencePolicy().evaluate(
        plan,
        provider_results_by_source,
        freshness,
        retrieval,
    )
    decision_evidence_snapshot = _model_snapshots(decision.evidence)
    budget = select_evidence_context(decision.evidence)
    budget_evidence_snapshot = _model_snapshots(budget.evidence)

    if decision.status in {
        EvidenceDecisionStatus.COMPLETE,
        EvidenceDecisionStatus.PARTIAL,
    }:
        assert budget.evidence
        cited = budget.evidence[0]
        claims = (
            CitationClaim(
                claim_id="fixed-extractive-claim",
                text=cited.snippet,
                evidence_ids=(cited.evidence_id,),
            ),
        )
        answer_text = cited.snippet
    else:
        assert not budget.evidence
        claims = ()
        answer_text = _FIXED_EMPTY_ANSWERS[decision.status]

    citations = validate_citations(claims, plan, budget.evidence)
    answer = FinancialAnswer(
        answer=answer_text,
        status=decision.status,
        security=plan.security.model_copy(deep=True),
        basis_date=BASIS_AT,
        evidence=[item.model_copy(deep=True) for item in budget.evidence],
        warnings=[warning.code for warning in decision.warnings],
        missing_sources=list(decision.missing_sources),
    )

    assert _model_snapshots(documents) == document_snapshots
    assert {
        source: result.model_dump(mode="python")
        for source, result in provider_results_by_source.items()
    } == provider_snapshots
    assert plan.model_dump(mode="python") == plan_snapshot
    assert request.model_dump(mode="python") == request_snapshot
    assert _model_snapshots(normalized) == normalized_snapshot
    assert _model_snapshots(hard_filtered) == hard_filtered_snapshot
    assert _model_snapshots(freshness.evidence) == freshness_evidence_snapshot
    assert retrieval.model_dump(mode="python") == retrieval_snapshot
    assert _model_snapshots(decision.evidence) == decision_evidence_snapshot
    assert _model_snapshots(budget.evidence) == budget_evidence_snapshot

    return _PhaseSliceResult(
        plan=plan,
        request=request,
        normalized=tuple(normalized),
        hard_filtered=tuple(hard_filtered),
        freshness=freshness,
        retrieval=retrieval,
        decision=decision,
        budget=budget,
        claims=claims,
        citations=citations,
        answer=answer,
    )


def test_recent_news_complete_filters_wrong_company_and_stale_evidence():
    current = _news_document("news:current", raw_index=0)
    wrong_company = _news_document(
        "news:wrong-company",
        security_id=SK_HYNIX,
        title="SK하이닉스 반도체 투자 뉴스",
        text="SK하이닉스 반도체 투자 확대 소식이 발표됐다.",
        raw_index=1,
    )
    stale = _news_document(
        "news:stale",
        published_at=BASIS_AT - timedelta(days=31),
        raw_index=2,
    )
    documents = [current, wrong_company, stale]

    result = _run_phase_slice(
        DEFAULT_QUERY,
        documents,
        {"news": _ok_provider_result(documents)},
    )

    assert result.plan.intent == "recent_issue"
    assert result.request.security_id == SAMSUNG
    assert [item.document_id for item in result.hard_filtered] == [
        current.document_id,
        stale.document_id,
    ]
    assert [item.document_id for item in result.freshness.evidence] == [
        current.document_id
    ]
    assert result.retrieval.status == RetrievalStatus.OK
    assert result.decision.status == EvidenceDecisionStatus.COMPLETE
    assert [item.document_id for item in result.budget.evidence] == [
        current.document_id
    ]
    assert result.citations.rejections == ()
    assert len(result.citations.citations) == 1

    selected = result.budget.evidence[0]
    citation = result.citations.citations[0]
    assert citation.evidence_id == selected.evidence_id
    assert citation.document_id == selected.document_id
    assert citation.source_type == selected.source_type
    assert citation.title == selected.title
    assert citation.source_url == selected.source_url
    assert citation.snippet == selected.snippet
    assert citation.locator == selected.locator
    assert result.answer.status == EvidenceDecisionStatus.COMPLETE
    assert result.answer.answer == selected.snippet
    assert [item.document_id for item in result.answer.evidence] == [
        current.document_id
    ]
    assert wrong_company.document_id not in {
        item.document_id for item in result.answer.evidence
    }
    assert stale.document_id not in {
        item.document_id for item in result.answer.evidence
    }


def test_low_relevance_maps_to_no_evidence_fixed_response():
    unrelated = _news_document(
        "news:unrelated",
        title="공급망 점검 결과",
        text="원자재 수급 상황을 검토했다.",
    )

    result = _run_phase_slice(
        DEFAULT_QUERY,
        [unrelated],
        {"news": _ok_provider_result([unrelated])},
    )

    assert [item.document_id for item in result.hard_filtered] == [
        unrelated.document_id
    ]
    assert [item.document_id for item in result.freshness.evidence] == [
        unrelated.document_id
    ]
    assert result.retrieval.status == RetrievalStatus.LOW_RELEVANCE
    assert result.retrieval.low_relevance is True
    assert result.decision.status == EvidenceDecisionStatus.NO_EVIDENCE
    assert result.budget.evidence == ()
    assert result.claims == ()
    assert result.citations.citations == ()
    assert result.citations.rejections == ()
    assert result.answer.status == EvidenceDecisionStatus.NO_EVIDENCE
    assert result.answer.answer == NO_EVIDENCE_ANSWER
    assert result.answer.evidence == []


def test_provider_failure_is_preserved_and_sanitized():
    sentinel = "SECRET_SENTINEL C:\\private\\provider.log"
    provider_result = create_provider_result(
        status=ProviderStatus.TIMEOUT,
        error_code="attempt_timeout",
        message=sentinel,
        fetched_at=BASIS_AT,
    )

    result = _run_phase_slice(
        DEFAULT_QUERY,
        [],
        {"news": provider_result},
    )

    assert result.retrieval.status == RetrievalStatus.EMPTY
    assert result.decision.status == EvidenceDecisionStatus.PROVIDER_FAILED
    assert result.decision.failed_sources == ("news",)
    assert result.decision.no_data_sources == ()
    assert result.decision.evidence == ()
    assert result.answer.status == EvidenceDecisionStatus.PROVIDER_FAILED
    assert result.answer.answer == PROVIDER_FAILED_ANSWER
    assert result.answer.evidence == []
    assert result.citations == CitationValidationResult((), ())
    serialized = result.answer.model_dump_json()
    assert "SECRET_SENTINEL" not in serialized
    assert "C:\\private" not in serialized
    assert sentinel not in (provider_result.message or "")


def test_budget_caps_news_before_citation_and_removed_id_is_unknown():
    query = "삼성전자 반도체 투자 뉴스"
    documents = [
        _news_document(
            f"news:budget-{index}",
            title=f"삼성전자 반도체 투자 뉴스 {index}",
            text=f"삼성전자 반도체 투자 뉴스 근거 {index}가 발표됐다.",
            raw_index=index,
            query=query,
        )
        for index in range(4)
    ]

    result = _run_phase_slice(
        query,
        documents,
        {"news": _ok_provider_result(documents)},
    )

    assert result.retrieval.status == RetrievalStatus.OK
    assert len(result.decision.evidence) == 4
    assert result.decision.status == EvidenceDecisionStatus.COMPLETE
    assert len(result.budget.evidence) == 3
    assert result.budget.diagnostics.source_cap_drop_count == 1
    assert [item.evidence_id for item in result.budget.evidence] == [
        item.evidence_id for item in result.decision.evidence[:3]
    ]

    retained_ids = {item.evidence_id for item in result.budget.evidence}
    cited_ids = {item.evidence_id for item in result.citations.citations}
    removed = result.decision.evidence[3]
    assert cited_ids
    assert cited_ids <= retained_ids
    assert removed.evidence_id not in cited_ids
    assert all(
        evidence_id in retained_ids
        for claim in result.claims
        for evidence_id in claim.evidence_ids
    )

    removed_result = validate_citations(
        [
            CitationClaim(
                claim_id="removed-claim",
                text=removed.snippet,
                evidence_ids=(removed.evidence_id,),
            )
        ],
        result.plan,
        result.budget.evidence,
    )
    assert removed_result.citations == ()
    assert removed_result.rejections == (
        CitationRejection("removed-claim", "unknown_evidence"),
    )


def test_phase_slice_is_deterministic_and_returns_fresh_nested_evidence():
    current = _news_document("news:deterministic", raw_index=7)
    documents = [current]
    provider_result = _ok_provider_result(documents)
    document_snapshot = _model_snapshots(documents)
    provider_snapshot = provider_result.model_dump(mode="python")

    first = _run_phase_slice(
        DEFAULT_QUERY,
        documents,
        {"news": provider_result},
    )
    second = _run_phase_slice(
        DEFAULT_QUERY,
        documents,
        {"news": provider_result},
    )

    assert first.answer.model_dump_json() == second.answer.model_dump_json()
    assert first.citations == second.citations
    assert first.budget.diagnostics == second.budget.diagnostics
    assert first.request.model_dump(mode="python") == second.request.model_dump(
        mode="python"
    )
    assert first.answer is not second.answer
    assert first.answer.evidence[0] is not first.budget.evidence[0]
    assert first.answer.evidence[0] is not second.answer.evidence[0]

    first.answer.evidence[0].locator["raw_index"] = 999
    assert _model_snapshots(documents) == document_snapshot
    assert provider_result.model_dump(mode="python") == provider_snapshot
    assert first.budget.evidence[0].locator["raw_index"] == 7
    assert second.answer.evidence[0].locator["raw_index"] == 7
