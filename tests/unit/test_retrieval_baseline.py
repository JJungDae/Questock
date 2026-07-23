from __future__ import annotations

from datetime import date, datetime, timezone
from math import ceil
from pathlib import Path
from statistics import median
from time import perf_counter_ns

import pytest

from app.core.models import DateRange, Evidence, FinancialDocument, RetrievalRequest
from app.core.status import RetrievalStatus
from app.retrieval import HardFilterValidationError, retrieve_evidence
from app.retrieval import retriever

SAMSUNG = "KRX:005930"
SK_HYNIX = "KRX:000660"
HYUNDAI = "KRX:005380"
UTC = timezone.utc
INSIDE_DATE = datetime(2026, 7, 21, 3, 0, tzinfo=UTC)
OUTSIDE_DATE = datetime(2026, 7, 18, 3, 0, tzinfo=UTC)

EXPECTED_TOP6_BY_CASE = {
    "samsung_risk": ("ev:samsung:risk",),
    "sk_disclosure": ("ev:sk:disclosure",),
    "hyundai_report": ("ev:hyundai:report",),
}
EXPECTED_HARD_FILTER_EXCLUDED_IDS = {
    "ev:wrong-company",
    "ev:wrong-source",
    "ev:outside-date",
    "ev:unproven-type",
}
EXPECTED_LOW_RELEVANCE_IDS = {"ev:samsung:low"}


def request(
    query: str,
    *,
    security_id: str = SAMSUNG,
    source_types: list[str] | None = None,
    date_range: DateRange | None = None,
    document_types: list[str] | None = None,
    top_k: int = 6,
) -> RetrievalRequest:
    return RetrievalRequest(
        query=query,
        security_id=security_id,
        source_types=source_types if source_types is not None else ["news", "disclosure", "research_report"],
        date_range=date_range,
        document_types=document_types,
        top_k=top_k,
    )


def evidence(
    evidence_id: str,
    *,
    document_id: str | None = None,
    source_type: str = "news",
    title: str = "title",
    snippet: str = "snippet",
    subject_security_ids: list[str] | None = None,
    mentioned_security_ids: list[str] | None = None,
    scope: str = "company_specific",
    published_at: datetime | None = INSIDE_DATE,
    retrieval_score: float | None = None,
) -> Evidence:
    subjects = subject_security_ids if subject_security_ids is not None else [SAMSUNG]
    return Evidence(
        evidence_id=evidence_id,
        document_id=document_id or f"doc:{evidence_id}",
        source_type=source_type,
        title=title,
        source_url="https://example.test/evidence",
        published_at=published_at,
        subject_security_ids=subjects,
        mentioned_security_ids=mentioned_security_ids or [],
        scope=scope,  # type: ignore[arg-type]
        snippet=snippet,
        locator={"kind": "unit", "id": evidence_id, "nested": {"values": ["original"]}},
        retrieval_score=retrieval_score,
    )


def document(
    document_id: str,
    *,
    source_type: str = "news",
    primary_security_ids: list[str] | None = None,
    mentioned_security_ids: list[str] | None = None,
    published_at: datetime | None = INSIDE_DATE,
    metadata: dict[str, object] | None = None,
    title: str = "linked title",
    text: str = "linked text",
) -> FinancialDocument:
    return FinancialDocument(
        document_id=document_id,
        source_type=source_type,
        provider="unit",
        primary_security_ids=primary_security_ids if primary_security_ids is not None else [SAMSUNG],
        mentioned_security_ids=mentioned_security_ids or [],
        title=title,
        published_at=published_at,
        source_url="https://example.test/document",
        text=text,
        locator={"kind": "unit", "id": document_id},
        metadata=metadata or {},
        ingestion_version="unit-v1",
    )


def benchmark_candidates() -> list[Evidence]:
    return [
        evidence(
            "ev:samsung:risk",
            title="삼성전자 메모리 수요 위험",
            snippet="반도체 가격 하락 위험을 점검했다",
        ),
        evidence(
            "ev:samsung:industry",
            title="반도체 업황 위험",
            snippet="메모리 수요 변동을 다뤘다",
            subject_security_ids=[],
            mentioned_security_ids=[SAMSUNG],
            scope="industry_common",
        ),
        evidence(
            "ev:samsung:multi",
            title="삼성전자 SK하이닉스 공급 위험",
            snippet="메모리 공급 변화",
            subject_security_ids=[SAMSUNG, SK_HYNIX],
            scope="multi_company",
        ),
        evidence(
            "ev:samsung:low",
            title="삼성전자 정기 안내",
            snippet="일반 공지 사항",
        ),
        evidence("ev:samsung:tie-a", title="삼성전자 공급 위험", snippet="동일 점수"),
        evidence("ev:samsung:tie-b", title="삼성전자 공급 위험", snippet="동일 점수"),
        evidence("ev:samsung:duplicate", title="삼성전자 중복 위험", snippet="중복 후보"),
        evidence(
            "ev:sk:disclosure",
            source_type="disclosure",
            title="SK하이닉스 주주총회 공시",
            snippet="공시 안건을 공개했다",
            subject_security_ids=[SK_HYNIX],
        ),
        evidence(
            "ev:hyundai:report",
            source_type="research_report",
            title="현대자동차 전기차 판매 전망",
            snippet="판매 성장 조건을 분석했다",
            subject_security_ids=[HYUNDAI],
        ),
        evidence(
            "ev:wrong-company",
            title="SK하이닉스 메모리 수요 위험",
            snippet="삼성전자 질문에는 사용할 수 없다",
            subject_security_ids=[SK_HYNIX],
        ),
        evidence(
            "ev:wrong-source",
            source_type="disclosure",
            title="삼성전자 메모리 수요 위험",
            snippet="뉴스 요청과 다른 source",
        ),
        evidence(
            "ev:outside-date",
            title="삼성전자 메모리 수요 위험",
            snippet="기간 밖 항목",
            published_at=OUTSIDE_DATE,
        ),
        evidence(
            "ev:unproven-type",
            document_id="doc:unproven",
            title="삼성전자 연차 보고서 위험",
            snippet="문서 유형 증명이 없다",
        ),
    ]


def result_ids(result) -> list[str]:
    return [item.evidence_id for item in result.evidence]


def test_package_exports_retrieve_evidence() -> None:
    from app import retrieval

    assert retrieval.retrieve_evidence is retrieve_evidence
    assert "retrieve_evidence" in retrieval.__all__


@pytest.mark.parametrize(
    ("bad_evidence", "bad_request", "bad_mapping"),
    [
        ("bad", request("query"), None),
        ([evidence("ev:valid")], "bad", None),
        ([evidence("ev:valid")], request("query"), {"wrong": document("doc:right")}),
    ],
)
def test_malformed_public_inputs_raise_hard_filter_validation_error(
    bad_evidence,
    bad_request,
    bad_mapping,
) -> None:
    with pytest.raises(HardFilterValidationError):
        retrieve_evidence(bad_evidence, bad_request, documents_by_id=bad_mapping)  # type: ignore[arg-type]


def test_hard_filter_empty_precedes_query_tokenization(monkeypatch) -> None:
    def fail_tokenizer(_: str) -> list[str]:
        raise AssertionError("tokenizer must not run")

    monkeypatch.setattr(retriever, "filter_evidence", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(retriever, "_tokenize_query", fail_tokenizer)

    result = retrieve_evidence([], request("최근 요약"))

    assert result.status == RetrievalStatus.EMPTY
    assert result.low_relevance is False
    assert result.evidence == []
    assert result.diagnostics["query_token_count"] == 0


def test_internal_scoring_error_propagates_without_status_conversion(monkeypatch) -> None:
    candidate = evidence("ev:internal", title="internalterm", snippet="")

    def fail_scoring(*_args, **_kwargs):
        raise RuntimeError("internal scoring failure")

    monkeypatch.setattr(retriever, "filter_evidence", lambda *_args, **_kwargs: [candidate])
    monkeypatch.setattr(retriever, "_score_candidates", fail_scoring)

    with pytest.raises(RuntimeError, match="internal scoring failure"):
        retrieve_evidence([candidate], request("internalterm"))


def test_excluded_candidates_do_not_affect_scores_or_diagnostics() -> None:
    allowed = evidence(
        "ev:allowed",
        title="삼성전자 반도체 위험",
        snippet="메모리 수요 위험",
    )
    excluded = [
        evidence(
            "ev:wrong-company",
            title="삼성전자 반도체 위험",
            snippet="wrong company",
            subject_security_ids=[SK_HYNIX],
        ),
        evidence(
            "ev:wrong-source",
            source_type="disclosure",
            title="삼성전자 반도체 위험",
            snippet="wrong source",
        ),
        evidence(
            "ev:outside-date",
            title="삼성전자 반도체 위험",
            snippet="outside date",
            published_at=OUTSIDE_DATE,
        ),
    ]
    retrieval_request = request(
        "반도체 위험",
        source_types=["news"],
        date_range=DateRange(start=date(2026, 7, 21), end=date(2026, 7, 21)),
    )

    baseline = retrieve_evidence([allowed], retrieval_request)
    result = retrieve_evidence([allowed, *excluded], retrieval_request)

    assert result_ids(result) == ["ev:allowed"]
    assert result.evidence[0].retrieval_score == baseline.evidence[0].retrieval_score
    assert result.diagnostics["input_count"] == 4
    assert result.diagnostics["filtered_count"] == 1
    assert result.diagnostics["scored_count"] == 1
    assert result.diagnostics["eligible_count"] == 1


def test_linked_document_type_and_scope_contracts_are_preserved() -> None:
    company_ok = evidence("ev:company", document_id="doc:company", title="companytoken", snippet="")
    company_mentioned_only = evidence("ev:company-mentioned", document_id="doc:mentioned", title="badtoken", snippet="")
    multi_ok = evidence(
        "ev:multi",
        document_id="doc:multi",
        title="multitoken",
        snippet="",
        subject_security_ids=[SAMSUNG, SK_HYNIX],
        scope="multi_company",
    )
    industry_mentioned = evidence(
        "ev:industry",
        document_id="doc:industry",
        title="industrytoken",
        snippet="",
        subject_security_ids=[],
        scope="industry_common",
    )
    unproven_type = evidence("ev:unproven-type", document_id="doc:unproven", title="unproventoken", snippet="")
    documents = {
        "doc:company": document("doc:company", metadata={"document_type": "annual"}),
        "doc:mentioned": document(
            "doc:mentioned",
            primary_security_ids=[SK_HYNIX],
            mentioned_security_ids=[SAMSUNG],
            metadata={"document_type": "annual"},
        ),
        "doc:multi": document(
            "doc:multi",
            primary_security_ids=[SAMSUNG, SK_HYNIX],
            metadata={"document_type": "annual"},
        ),
        "doc:industry": document(
            "doc:industry",
            primary_security_ids=[SK_HYNIX],
            mentioned_security_ids=[SAMSUNG],
            metadata={"document_type": "annual"},
        ),
        "doc:unproven": document("doc:unproven", metadata={}),
    }

    result = retrieve_evidence(
        [company_ok, company_mentioned_only, multi_ok, industry_mentioned, unproven_type],
        request("companytoken multitoken industrytoken", document_types=["annual"]),
        documents_by_id=documents,
    )

    assert set(result_ids(result)) == {"ev:company", "ev:multi", "ev:industry"}
    assert result.diagnostics["filtered_count"] == 3
    assert EXPECTED_HARD_FILTER_EXCLUDED_IDS & set(result_ids(result)) == set()


def test_evidence_timestamp_precedes_linked_document_timestamp() -> None:
    candidate = evidence("ev:evidence-date", document_id="doc:late", title="datetoken", snippet="")
    late_document = document("doc:late", published_at=OUTSIDE_DATE)

    result = retrieve_evidence(
        [candidate],
        request(
            "datetoken datetoken",
            date_range=DateRange(start=date(2026, 7, 21), end=date(2026, 7, 21)),
        ),
        documents_by_id={"doc:late": late_document},
    )

    assert result_ids(result) == ["ev:evidence-date"]


def test_start_end_and_same_day_date_boundaries_flow_through_hard_filter() -> None:
    start_boundary = evidence(
        "ev:start-boundary",
        title="startbound",
        snippet="",
        published_at=datetime(2026, 7, 20, 15, 0, tzinfo=UTC),
    )
    end_boundary = evidence(
        "ev:end-boundary",
        title="endbound",
        snippet="",
        published_at=datetime(2026, 7, 21, 14, 59, tzinfo=UTC),
    )
    outside = evidence(
        "ev:outside-boundary",
        title="outsidetoken",
        snippet="",
        published_at=datetime(2026, 7, 21, 15, 0, tzinfo=UTC),
    )
    candidates = [start_boundary, end_boundary, outside]

    start_only = retrieve_evidence(
        candidates,
        request("startbound startbound", date_range=DateRange(start=date(2026, 7, 21), end=None)),
    )
    end_only = retrieve_evidence(
        candidates,
        request("endbound endbound", date_range=DateRange(start=None, end=date(2026, 7, 21))),
    )
    same_day = retrieve_evidence(
        candidates,
        request(
            "startbound endbound",
            date_range=DateRange(start=date(2026, 7, 21), end=date(2026, 7, 21)),
        ),
    )

    assert result_ids(start_only) == ["ev:start-boundary"]
    assert result_ids(end_only) == ["ev:end-boundary"]
    assert result_ids(same_day) == ["ev:start-boundary", "ev:end-boundary"]


def test_linked_document_text_and_title_are_not_scored() -> None:
    candidate = evidence("ev:document-text", document_id="doc:text", title="visible", snippet="visible")
    linked = document("doc:text", title="hiddenword", text="hiddenword hiddenword hiddenword")

    result = retrieve_evidence(
        [candidate],
        request("hiddenword hiddenword hiddenword"),
        documents_by_id={"doc:text": linked},
    )

    assert result.status == RetrievalStatus.LOW_RELEVANCE
    assert result.evidence == []


@pytest.mark.parametrize("query", ["", "   ", "!!!", "최근 자료 요약 알려줘"])
def test_unusable_query_tokens_return_low_relevance_when_candidates_exist(query: str) -> None:
    candidate = evidence("ev:token", title="matchtoken", snippet="")

    result = retrieve_evidence([candidate], request(query))

    assert result.status == RetrievalStatus.LOW_RELEVANCE
    assert result.low_relevance is True
    assert result.evidence == []
    assert result.diagnostics["filtered_count"] == 1
    assert result.diagnostics["scored_count"] == 0


def test_below_threshold_candidate_is_omitted_when_late_candidate_is_relevant() -> None:
    early = evidence("ev:early", title="shared", snippet="")
    late = evidence("ev:late", title="shared specific", snippet="")

    result = retrieve_evidence([early, late], request("shared specific"))

    assert result.status == RetrievalStatus.OK
    assert result_ids(result) == ["ev:late"]
    assert result.evidence[0].retrieval_score >= 0.5
    assert result.diagnostics["eligible_count"] == 1


def test_top_k_cap_and_stable_tie_order() -> None:
    candidates = [evidence(f"ev:rank-{index}", title=f"term{index}", snippet="") for index in range(1, 8)]
    query = " ".join(f"term{index}" for index in range(1, 8))

    capped = retrieve_evidence(candidates, request(query, top_k=10))
    limited = retrieve_evidence(candidates, request(query, top_k=3))

    assert result_ids(capped) == [f"ev:rank-{index}" for index in range(1, 7)]
    assert result_ids(limited) == [f"ev:rank-{index}" for index in range(1, 4)]
    assert capped.diagnostics["effective_top_k"] == 6
    assert limited.diagnostics["effective_top_k"] == 3


def test_equal_scores_keep_input_order() -> None:
    first = evidence("ev:tie-first", title="tie", snippet="")
    second = evidence("ev:tie-second", title="tie", snippet="")

    result = retrieve_evidence([first, second], request("tie tie tie"))

    assert result_ids(result) == ["ev:tie-first", "ev:tie-second"]
    assert result.evidence[0].retrieval_score == result.evidence[1].retrieval_score


def test_repeated_query_terms_use_fixed_bm25_query_term_frequency() -> None:
    candidate = evidence("ev:growth", title="growth", snippet="")

    result = retrieve_evidence([candidate], request("growth growth growth"))

    assert result.evidence[0].retrieval_score == 1.186689


def test_returned_evidence_is_deep_copied_and_input_score_is_ignored() -> None:
    original = evidence("ev:copy", title="copytoken", snippet="", retrieval_score=99.0)

    result = retrieve_evidence([original], request("copytoken copytoken"))
    returned = result.evidence[0]
    returned.subject_security_ids.append(SK_HYNIX)
    returned.locator["nested"]["values"].append("changed")

    assert returned is not original
    assert returned.retrieval_score != 99.0
    assert original.retrieval_score == 99.0
    assert original.subject_security_ids == [SAMSUNG]
    assert original.locator["nested"]["values"] == ["original"]


def test_duplicate_candidates_are_preserved() -> None:
    first = evidence("ev:duplicate", title="duplicate", snippet="")
    second = first.model_copy(deep=True)

    result = retrieve_evidence([first, second], request("duplicate duplicate duplicate"))

    assert result_ids(result) == ["ev:duplicate", "ev:duplicate"]
    assert result.diagnostics["filtered_count"] == 2


def test_permission_metadata_does_not_change_retrieval_eligibility_or_score() -> None:
    first = evidence("ev:permission-a", document_id="doc:permission-a", title="permission", snippet="")
    second = evidence("ev:permission-b", document_id="doc:permission-b", title="permission", snippet="")
    documents = {
        "doc:permission-a": document(
            "doc:permission-a",
            metadata={
                "external_llm_processing_allowed": False,
                "corpus_ingest_allowed": False,
                "usage_review_status": "restricted",
            },
        ),
        "doc:permission-b": document(
            "doc:permission-b",
            metadata={
                "external_llm_processing_allowed": True,
                "corpus_ingest_allowed": True,
                "usage_review_status": "approved",
            },
        ),
    }

    result = retrieve_evidence(
        [first, second],
        request("permission permission permission"),
        documents_by_id=documents,
    )

    assert result_ids(result) == ["ev:permission-a", "ev:permission-b"]
    assert result.evidence[0].retrieval_score == result.evidence[1].retrieval_score


def test_request_is_not_rewritten_and_no_date_default_is_added() -> None:
    candidate = evidence("ev:no-date", title="nodatetoken", snippet="", published_at=None)
    retrieval_request = request("nodatetoken nodatetoken", date_range=None, source_types=["news"])
    before = retrieval_request.model_dump()

    result = retrieve_evidence([candidate], retrieval_request)

    assert result_ids(result) == ["ev:no-date"]
    assert retrieval_request.model_dump() == before
    assert retrieval_request.date_range is None


def test_diagnostics_are_exact_sanitized_and_fresh() -> None:
    candidate = evidence("ev:diagnostics", title="diagnostictoken", snippet="secret snippet")
    retrieval_request = request("diagnostictoken")

    first = retrieve_evidence([candidate], retrieval_request)
    second = retrieve_evidence([candidate], retrieval_request)
    first.diagnostics["input_count"] = 999

    assert set(second.diagnostics) == {
        "input_count",
        "filtered_count",
        "scored_count",
        "eligible_count",
        "returned_count",
        "query_token_count",
        "requested_top_k",
        "effective_top_k",
        "max_top_k",
        "low_relevance_threshold",
    }
    assert second.diagnostics["input_count"] == 1
    assert second.diagnostics["returned_count"] == len(second.evidence)
    diagnostics_text = repr(second.diagnostics)
    for forbidden in (candidate.evidence_id, candidate.document_id, candidate.snippet, retrieval_request.query):
        assert forbidden not in diagnostics_text


def test_benchmark_labels_are_independent_and_relevant_top_six_is_complete() -> None:
    candidates = benchmark_candidates()
    cases = {
        "samsung_risk": request(
            "메모리 수요 위험",
            source_types=["news"],
            date_range=DateRange(start=date(2026, 7, 21), end=date(2026, 7, 21)),
        ),
        "sk_disclosure": request("주주총회 공시", security_id=SK_HYNIX, source_types=["disclosure"]),
        "hyundai_report": request(
            "전기차 판매 전망",
            security_id=HYUNDAI,
            source_types=["research_report"],
        ),
    }

    for case_name, retrieval_request in cases.items():
        returned = set(result_ids(retrieve_evidence(candidates, retrieval_request)))
        assert set(EXPECTED_TOP6_BY_CASE[case_name]) <= returned

    candidate_ids = {item.evidence_id for item in candidates}
    assert len(candidates) >= 12
    assert len(candidate_ids) == len(candidates)
    assert {"news", "disclosure", "research_report"} <= {item.source_type for item in candidates}
    represented_securities = {
        security_id
        for item in candidates
        for security_id in [*item.subject_security_ids, *item.mentioned_security_ids]
    }
    assert {SAMSUNG, SK_HYNIX, HYUNDAI} <= represented_securities


def test_benchmark_wrong_company_and_low_relevance_paths() -> None:
    candidates = benchmark_candidates()
    retrieval_request = request(
        "메모리 수요 위험",
        source_types=["news"],
        date_range=DateRange(start=date(2026, 7, 21), end=date(2026, 7, 21)),
    )

    result = retrieve_evidence(candidates, retrieval_request)
    low_relevance = retrieve_evidence(
        [item for item in candidates if item.evidence_id in EXPECTED_LOW_RELEVANCE_IDS],
        request("전혀다른질문", source_types=["news"]),
    )

    assert EXPECTED_HARD_FILTER_EXCLUDED_IDS.isdisjoint(result_ids(result))
    assert low_relevance.status == RetrievalStatus.LOW_RELEVANCE
    assert low_relevance.evidence == []


def test_retriever_has_no_out_of_scope_imports() -> None:
    source = Path("app/retrieval/retriever.py").read_text(encoding="utf-8")

    for forbidden in (
        "app.providers",
        "app.ingest",
        "app.planning",
        "QueryPlanner",
        "SessionContext",
        "app.api",
        "app.llm",
        "embedding",
        "vector",
        "rerank",
    ):
        assert forbidden not in source


def test_local_synthetic_benchmark_latency_is_deterministic() -> None:
    candidates = benchmark_candidates()
    retrieval_request = request(
        "메모리 수요 위험",
        source_types=["news"],
        date_range=DateRange(start=date(2026, 7, 21), end=date(2026, 7, 21)),
    )
    baseline = retrieve_evidence(candidates, retrieval_request)
    baseline_snapshot = (
        result_ids(baseline),
        [item.retrieval_score for item in baseline.evidence],
        baseline.status,
        baseline.diagnostics,
    )
    elapsed_ns: list[int] = []

    for _ in range(200):
        started_at = perf_counter_ns()
        result = retrieve_evidence(candidates, retrieval_request)
        elapsed_ns.append(perf_counter_ns() - started_at)
        assert (
            result_ids(result),
            [item.retrieval_score for item in result.evidence],
            result.status,
            result.diagnostics,
        ) == baseline_snapshot

    ordered = sorted(elapsed_ns)
    median_ns = int(median(elapsed_ns))
    p95_ns = ordered[ceil(len(ordered) * 0.95) - 1]
    print(f"local synthetic benchmark: median_ns={median_ns}, p95_ns={p95_ns}")
    assert median_ns >= 0
    assert p95_ns >= median_ns
