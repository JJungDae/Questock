from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from datetime import date, datetime, time, timedelta, timezone
import inspect
from types import MappingProxyType
from zoneinfo import ZoneInfo

import pytest

import app.evidence as evidence_package
from app.core.models import DateRange, Evidence, FinancialDocument, RetrievalRequest
from app.evidence.freshness import (
    FreshnessResult,
    FreshnessValidationError,
    FreshnessWarning,
    FreshnessWindow,
    evaluate_freshness,
)
from app.evidence.normalizer import normalize_financial_documents
from app.retrieval import filter_evidence, retrieve_evidence

UTC = timezone.utc
SEOUL = ZoneInfo("Asia/Seoul")
SAMSUNG = "KRX:005930"
SK_HYNIX = "KRX:000660"
BASIS_AT = datetime(2026, 7, 23, 3, 0, tzinfo=UTC)
BASIS_DATE = date(2026, 7, 23)


def timestamp_at_age(age_days: int, *, local_hour: int = 9) -> datetime:
    local_day = BASIS_DATE - timedelta(days=age_days)
    return datetime.combine(local_day, time(local_hour), tzinfo=SEOUL).astimezone(UTC)


def request(
    *,
    source_types: list[str] | None = None,
    date_range: DateRange | None = None,
    document_types: list[str] | None = None,
    query: str = "memory risk",
    security_id: str = SAMSUNG,
) -> RetrievalRequest:
    return RetrievalRequest(
        query=query,
        security_id=security_id,
        source_types=source_types if source_types is not None else ["news"],
        date_range=date_range,
        document_types=document_types,
        top_k=6,
    )


def document(
    document_id: str = "news:1",
    *,
    source_type: str = "news",
    published_at: datetime | None | object = ...,
    primary_security_ids: list[str] | None = None,
    mentioned_security_ids: list[str] | None = None,
    metadata: dict[str, object] | None = None,
    title: str = "memory risk",
    text: str = "memory risk evidence",
) -> FinancialDocument:
    effective_published_at = timestamp_at_age(1) if published_at is ... else published_at
    return FinancialDocument(
        document_id=document_id,
        source_type=source_type,
        provider="unit",
        primary_security_ids=primary_security_ids if primary_security_ids is not None else [SAMSUNG],
        mentioned_security_ids=mentioned_security_ids or [],
        title=title,
        published_at=effective_published_at,  # type: ignore[arg-type]
        source_url="https://example.test/document",
        text=text,
        locator={"kind": "unit", "id": document_id, "nested": {"values": ["original"]}},
        metadata=metadata or {},
        ingestion_version="unit-v1",
    )


def evidence(
    linked_document: FinancialDocument,
    *,
    evidence_id: str | None = None,
    published_at: datetime | None | object = ...,
    retrieval_score: float | None = 0.25,
) -> Evidence:
    if len(linked_document.primary_security_ids) == 1:
        scope = "company_specific"
        subjects = list(linked_document.primary_security_ids)
    elif len(linked_document.primary_security_ids) >= 2:
        scope = "multi_company"
        subjects = list(linked_document.primary_security_ids)
    else:
        scope = "industry_common"
        subjects = []
    effective_published_at = linked_document.published_at if published_at is ... else published_at
    return Evidence(
        evidence_id=evidence_id or f"evidence:{linked_document.document_id}",
        document_id=linked_document.document_id,
        source_type=linked_document.source_type,
        title=linked_document.title,
        source_url=linked_document.source_url,
        published_at=effective_published_at,  # type: ignore[arg-type]
        subject_security_ids=subjects,
        mentioned_security_ids=list(linked_document.mentioned_security_ids),
        scope=scope,
        snippet=linked_document.text,
        locator={"kind": "unit", "id": linked_document.document_id, "nested": {"values": ["original"]}},
        retrieval_score=retrieval_score,
    )


def disclosure(
    receipt: str,
    *,
    age_days: int = 1,
    metadata: dict[str, object] | None = None,
    security_id: str = SAMSUNG,
    title: str = "periodic filing",
) -> tuple[FinancialDocument, Evidence]:
    linked_document = document(
        f"disclosure:{receipt}",
        source_type="disclosure",
        published_at=timestamp_at_age(age_days),
        primary_security_ids=[security_id],
        metadata=metadata,
        title=title,
        text="filing details",
    )
    return linked_document, evidence(linked_document)


def evaluate(
    items: list[Evidence] | tuple[Evidence, ...],
    documents: list[FinancialDocument] | tuple[FinancialDocument, ...],
    *,
    retrieval_request: RetrievalRequest | None = None,
    basis_at: datetime = BASIS_AT,
) -> FreshnessResult:
    return evaluate_freshness(
        items,
        retrieval_request or request(),
        documents_by_id={item.document_id: item for item in documents},
        basis_at=basis_at,
    )


def warning_codes(result: FreshnessResult) -> list[str]:
    return [warning.code for warning in result.warnings]


def correction_request() -> RetrievalRequest:
    return request(
        source_types=["disclosure"],
        date_range=DateRange(start=BASIS_DATE - timedelta(days=365), end=BASIS_DATE),
    )


def assert_sanitized(exc_info: pytest.ExceptionInfo[FreshnessValidationError]) -> None:
    message = str(exc_info.value)
    assert message in {
        "evidence must be a sequence",
        "evidence items are invalid",
        "request must be a RetrievalRequest",
        "documents_by_id must be a mapping",
        "documents_by_id is invalid",
        "linked document is missing",
        "linked evidence is invalid",
        "evidence source is not requested",
        "basis_at must be an aware UTC datetime",
        "freshness timestamp is invalid",
        "disclosure metadata is invalid",
        "disclosure correction relation is invalid",
    }
    assert "C:" not in message
    assert "/root" not in message
    assert "secret" not in message.lower()


def test_root_package_exports_remain_unchanged_and_submodule_import_works():
    assert evidence_package.__all__ == [
        "EvidenceNormalizationError",
        "normalize_financial_document",
        "normalize_financial_documents",
    ]
    assert not hasattr(evidence_package, "evaluate_freshness")
    assert callable(evaluate_freshness)


@pytest.mark.parametrize(
    "bad_evidence",
    [
        "bad",
        b"bad",
        bytearray(b"bad"),
        {"bad": "value"},
        (item for item in []),
        1,
    ],
)
def test_public_boundary_rejects_non_sequences(bad_evidence):
    with pytest.raises(FreshnessValidationError) as exc_info:
        evaluate_freshness(  # type: ignore[arg-type]
            bad_evidence,
            request(),
            documents_by_id={},
            basis_at=BASIS_AT,
        )
    assert_sanitized(exc_info)


def test_invalid_item_returns_no_partial_result():
    linked_document = document()
    original = evidence(linked_document)
    with pytest.raises(FreshnessValidationError) as exc_info:
        evaluate_freshness(
            [original, object()],  # type: ignore[list-item]
            request(),
            documents_by_id={linked_document.document_id: linked_document},
            basis_at=BASIS_AT,
        )
    assert_sanitized(exc_info)
    assert original.retrieval_score == 0.25


@pytest.mark.parametrize("bad_request", [None, "bad", object()])
def test_public_boundary_rejects_invalid_request_type(bad_request):
    with pytest.raises(FreshnessValidationError) as exc_info:
        evaluate_freshness([], bad_request, documents_by_id={}, basis_at=BASIS_AT)  # type: ignore[arg-type]
    assert_sanitized(exc_info)


@pytest.mark.parametrize(
    "bad_source_types",
    [["news", " "], ["news", 3], "news"],
)
def test_bypass_created_request_is_canonically_revalidated(bad_source_types):
    bad_request = RetrievalRequest.model_construct(
        query="query",
        security_id=SAMSUNG,
        source_types=bad_source_types,
        date_range=None,
        document_types=None,
        top_k=6,
    )
    with pytest.raises(FreshnessValidationError) as exc_info:
        evaluate_freshness([], bad_request, documents_by_id={}, basis_at=BASIS_AT)
    assert_sanitized(exc_info)


@pytest.mark.parametrize("bad_mapping", ["bad", [], 3])
def test_public_boundary_rejects_non_mapping_documents(bad_mapping):
    with pytest.raises(FreshnessValidationError) as exc_info:
        evaluate_freshness([], request(), documents_by_id=bad_mapping, basis_at=BASIS_AT)  # type: ignore[arg-type]
    assert_sanitized(exc_info)


@pytest.mark.parametrize(
    "bad_mapping",
    [
        {3: document()},
        {"news:1": object()},
        {"wrong": document()},
    ],
)
def test_public_boundary_rejects_invalid_mapping_items(bad_mapping):
    with pytest.raises(FreshnessValidationError) as exc_info:
        evaluate_freshness([], request(), documents_by_id=bad_mapping, basis_at=BASIS_AT)  # type: ignore[arg-type]
    assert_sanitized(exc_info)


def test_bypass_created_evidence_and_document_are_revalidated():
    linked_document = document()
    bad_evidence = evidence(linked_document).model_copy()
    object.__setattr__(bad_evidence, "locator", {})
    with pytest.raises(FreshnessValidationError) as exc_info:
        evaluate_freshness(
            [bad_evidence],
            request(),
            documents_by_id={linked_document.document_id: linked_document},
            basis_at=BASIS_AT,
        )
    assert_sanitized(exc_info)

    bad_document = linked_document.model_copy()
    object.__setattr__(bad_document, "primary_security_ids", [])
    with pytest.raises(FreshnessValidationError) as exc_info:
        evaluate_freshness(
            [evidence(linked_document)],
            request(),
            documents_by_id={linked_document.document_id: bad_document},
            basis_at=BASIS_AT,
        )
    assert_sanitized(exc_info)


def test_missing_link_source_mismatch_and_unrequested_source_fail_safely():
    linked_document = document()
    item = evidence(linked_document)
    with pytest.raises(FreshnessValidationError) as exc_info:
        evaluate_freshness([item], request(), documents_by_id={}, basis_at=BASIS_AT)
    assert str(exc_info.value) == "linked document is missing"

    bad_source = item.model_copy(update={"source_type": "disclosure"})
    with pytest.raises(FreshnessValidationError) as exc_info:
        evaluate_freshness(
            [bad_source],
            request(source_types=["disclosure"]),
            documents_by_id={linked_document.document_id: linked_document},
            basis_at=BASIS_AT,
        )
    assert str(exc_info.value) == "linked evidence is invalid"

    with pytest.raises(FreshnessValidationError) as exc_info:
        evaluate_freshness(
            [item],
            request(source_types=["disclosure"]),
            documents_by_id={linked_document.document_id: linked_document},
            basis_at=BASIS_AT,
        )
    assert str(exc_info.value) == "evidence source is not requested"


def test_extra_unrelated_mapping_document_does_not_affect_result():
    linked_document = document()
    extra = document("news:extra", published_at=timestamp_at_age(30))
    item = evidence(linked_document)
    baseline = evaluate([item], [linked_document])
    with_extra = evaluate_freshness(
        [item],
        request(),
        documents_by_id={
            linked_document.document_id: linked_document,
            extra.document_id: extra,
        },
        basis_at=BASIS_AT,
    )
    assert with_extra == baseline


def test_zero_offset_basis_is_accepted_and_normalized():
    zero_offset = timezone(timedelta(0), name="ZERO")
    result = evaluate([], [], basis_at=BASIS_AT.replace(tzinfo=zero_offset))
    assert result.basis_at == BASIS_AT
    assert result.basis_at.tzinfo is UTC
    assert result.basis_date == BASIS_DATE


@pytest.mark.parametrize(
    "bad_basis",
    [
        None,
        "2026-07-23",
        datetime(2026, 7, 23, 3, 0),
        datetime(2026, 7, 23, 3, 0, tzinfo=timezone(timedelta(hours=9))),
    ],
)
def test_invalid_basis_fails_safely(bad_basis):
    with pytest.raises(FreshnessValidationError) as exc_info:
        evaluate_freshness([], request(), documents_by_id={}, basis_at=bad_basis)  # type: ignore[arg-type]
    assert str(exc_info.value) == "basis_at must be an aware UTC datetime"


def test_unexpected_runtime_error_propagates(monkeypatch):
    import app.evidence.freshness as freshness

    linked_document = document()

    def fail(_value):
        raise RuntimeError("sentinel")

    monkeypatch.setattr(freshness, "_canonical_evidence", fail)
    with pytest.raises(RuntimeError, match="sentinel"):
        evaluate([evidence(linked_document)], [linked_document])


def test_duplicate_sources_keep_first_occurrence_window_order():
    result = evaluate_freshness(
        [],
        request(source_types=["research_report", "news", "research_report", "disclosure", "news"]),
        documents_by_id={},
        basis_at=BASIS_AT,
    )
    assert [window.source_type for window in result.windows] == [
        "research_report",
        "news",
        "disclosure",
    ]
    assert len([warning for warning in result.warnings if warning.source_type == "disclosure"]) == 2


def test_empty_date_range_uses_default_windows():
    result = evaluate_freshness(
        [],
        request(source_types=["news"], date_range=DateRange()),
        documents_by_id={},
        basis_at=BASIS_AT,
    )
    assert result.windows == (
        FreshnessWindow(
            source_type="news",
            start=BASIS_DATE - timedelta(days=30),
            end=BASIS_DATE,
            applied_by="default",
        ),
    )


@pytest.mark.parametrize(
    "date_range",
    [
        DateRange(start=BASIS_DATE - timedelta(days=7)),
        DateRange(end=BASIS_DATE),
        DateRange(start=BASIS_DATE, end=BASIS_DATE),
        DateRange(start=BASIS_DATE - timedelta(days=7), end=BASIS_DATE),
    ],
)
def test_meaningful_user_ranges_are_copied_exactly(date_range):
    old_news = document(published_at=timestamp_at_age(40))
    old_disclosure, old_disclosure_evidence = disclosure("20260723000001", age_days=366)
    news_evidence = evidence(old_news)
    retrieval_request = request(
        source_types=["news", "disclosure"],
        date_range=date_range,
    )
    before = retrieval_request.model_dump()
    result = evaluate(
        [news_evidence, old_disclosure_evidence],
        [old_news, old_disclosure],
        retrieval_request=retrieval_request,
    )
    assert result.windows == (
        FreshnessWindow("news", date_range.start, date_range.end, "user"),
        FreshnessWindow("disclosure", date_range.start, date_range.end, "user"),
    )
    assert [item.document_id for item in result.evidence] == [
        old_news.document_id,
        old_disclosure.document_id,
    ]
    assert result.warnings == ()
    assert retrieval_request.model_dump() == before


def test_empty_sources_behavior_is_exact():
    result = evaluate_freshness(
        [],
        request(source_types=[]),
        documents_by_id={},
        basis_at=BASIS_AT,
    )
    assert result.windows == ()
    assert result.evidence == ()
    assert result.warnings == ()

    linked_document = document()
    with pytest.raises(FreshnessValidationError, match="evidence source is not requested"):
        evaluate_freshness(
            [evidence(linked_document)],
            request(source_types=[]),
            documents_by_id={linked_document.document_id: linked_document},
            basis_at=BASIS_AT,
        )


def test_unknown_source_has_no_date_policy_and_passes_through():
    linked_document = document("glossary:1", source_type="glossary", published_at=None)
    item = evidence(linked_document, published_at=None)
    result = evaluate(
        [item],
        [linked_document],
        retrieval_request=request(source_types=["glossary"]),
    )
    assert result.windows == (FreshnessWindow("glossary", None, None, "none"),)
    assert result.evidence[0] == item
    assert result.warnings == ()


def test_basis_date_uses_asia_seoul_around_utc_date_change():
    basis = datetime(2026, 7, 22, 16, 0, tzinfo=UTC)
    result = evaluate([], [], basis_at=basis)
    assert result.basis_at == basis
    assert result.basis_date == date(2026, 7, 23)


@pytest.mark.parametrize(
    ("source_type", "included_age", "excluded_age"),
    [
        ("news", 30, 31),
        ("research_report", 180, 181),
    ],
)
def test_default_window_boundaries(source_type, included_age, excluded_age):
    included = document(f"{source_type}:included", source_type=source_type, published_at=timestamp_at_age(included_age))
    excluded = document(f"{source_type}:excluded", source_type=source_type, published_at=timestamp_at_age(excluded_age))
    result = evaluate(
        [evidence(included), evidence(excluded)],
        [included, excluded],
        retrieval_request=request(source_types=[source_type]),
    )
    assert [item.document_id for item in result.evidence] == [included.document_id]


def test_disclosure_age_180_is_in_default_window_when_count_is_five():
    pairs = [disclosure(f"2026072300000{index}", age_days=180 if index == 1 else index) for index in range(1, 6)]
    result = evaluate(
        [item for _, item in pairs],
        [item for item, _ in pairs],
        retrieval_request=request(source_types=["disclosure"]),
    )
    assert len(result.evidence) == 5
    assert result.windows[0].applied_by == "default"
    assert result.windows[0].start == BASIS_DATE - timedelta(days=180)


def test_basis_date_item_is_included():
    linked_document = document(published_at=timestamp_at_age(0))
    result = evaluate([evidence(linked_document)], [linked_document])
    assert len(result.evidence) == 1


def test_same_seoul_day_later_instant_is_future_and_does_not_fallback():
    older_document = document("news:future", published_at=timestamp_at_age(1))
    future_evidence = evidence(
        older_document,
        published_at=BASIS_AT + timedelta(minutes=1),
    )
    result = evaluate([future_evidence], [older_document])
    assert result.evidence == ()
    assert warning_codes(result) == ["future_published_at"]


def test_future_date_is_omitted():
    linked_document = document(published_at=BASIS_AT + timedelta(days=1))
    result = evaluate([evidence(linked_document)], [linked_document])
    assert result.evidence == ()
    assert warning_codes(result) == ["future_published_at"]


def test_evidence_timestamp_wins_and_document_timestamp_is_fallback():
    recent_document = document("news:evidence-wins", published_at=timestamp_at_age(1))
    old_evidence = evidence(recent_document, published_at=timestamp_at_age(31))
    fallback_document = document("news:fallback", published_at=timestamp_at_age(2))
    naive_evidence = evidence(
        fallback_document,
        published_at=datetime(2026, 7, 1, 9, 0),
    )
    result = evaluate(
        [old_evidence, naive_evidence],
        [recent_document, fallback_document],
    )
    assert [item.document_id for item in result.evidence] == [fallback_document.document_id]


def test_missing_or_naive_timestamps_warn_once():
    first = document("news:missing", published_at=None)
    second = document(
        "news:naive",
        published_at=datetime(2026, 7, 22, 9, 0),
    )
    result = evaluate(
        [evidence(first, published_at=None), evidence(second)],
        [first, second],
    )
    assert result.evidence == ()
    assert warning_codes(result) == ["missing_published_at"]


@pytest.mark.parametrize(
    ("source_type", "age_days", "warning_code"),
    [
        ("news", 14, None),
        ("news", 15, "stale_news"),
        ("research_report", 180, None),
        ("research_report", 181, "stale_research_report"),
    ],
)
def test_stale_thresholds_are_exact(source_type, age_days, warning_code):
    linked_document = document(
        f"{source_type}:stale",
        source_type=source_type,
        published_at=timestamp_at_age(age_days),
    )
    result = evaluate(
        [evidence(linked_document)],
        [linked_document],
        retrieval_request=request(source_types=[source_type]),
    )
    assert warning_code in warning_codes(result) if warning_code else warning_codes(result) == []


def test_old_only_source_warns_before_default_omission():
    linked_document = document(published_at=timestamp_at_age(31))
    result = evaluate([evidence(linked_document)], [linked_document])
    assert result.evidence == ()
    assert warning_codes(result) == ["stale_news"]


def test_missing_and_future_do_not_suppress_old_valid_stale_warning():
    old = document("news:old", published_at=timestamp_at_age(31))
    missing = document("news:missing", published_at=None)
    future = document("news:future", published_at=BASIS_AT + timedelta(days=1))
    result = evaluate(
        [evidence(old), evidence(missing, published_at=None), evidence(future)],
        [old, missing, future],
    )
    assert warning_codes(result) == [
        "missing_published_at",
        "future_published_at",
        "stale_news",
    ]


def test_no_valid_dated_item_has_no_stale_warning():
    missing = document("news:missing", published_at=None)
    result = evaluate([evidence(missing, published_at=None)], [missing])
    assert warning_codes(result) == ["missing_published_at"]


def test_five_unique_recent_disclosures_keep_default_window():
    pairs = [disclosure(f"2026072300010{index}", age_days=index) for index in range(5)]
    result = evaluate(
        [item for _, item in pairs],
        [item for item, _ in pairs],
        retrieval_request=request(source_types=["disclosure"]),
    )
    assert result.windows[0].applied_by == "default"
    assert "disclosure_window_extended" not in warning_codes(result)
    assert "insufficient_disclosure_coverage" not in warning_codes(result)


def test_four_unique_disclosures_trigger_fallback_and_shortage():
    pairs = [disclosure(f"2026072300020{index}", age_days=index) for index in range(4)]
    result = evaluate(
        [item for _, item in pairs],
        [item for item, _ in pairs],
        retrieval_request=request(source_types=["disclosure"]),
    )
    assert result.windows[0] == FreshnessWindow(
        "disclosure",
        BASIS_DATE - timedelta(days=365),
        BASIS_DATE,
        "fallback",
    )
    assert warning_codes(result) == [
        "disclosure_window_extended",
        "insufficient_disclosure_coverage",
    ]


def test_duplicate_disclosure_occurrences_do_not_inflate_count():
    pairs = [disclosure(f"2026072300030{index}", age_days=index) for index in range(4)]
    items = [item for _, item in pairs]
    items.append(items[0].model_copy(update={"evidence_id": "evidence:duplicate"}))
    result = evaluate(
        items,
        [item for item, _ in pairs],
        retrieval_request=request(source_types=["disclosure"]),
    )
    assert result.windows[0].applied_by == "fallback"
    assert "insufficient_disclosure_coverage" in warning_codes(result)
    assert len(result.evidence) == 5


def test_fallback_includes_age_365_omits_366_and_can_reach_five():
    recent = [disclosure(f"2026072300040{index}", age_days=index) for index in range(4)]
    age_365 = disclosure("20260723000410", age_days=365)
    age_366 = disclosure("20260723000411", age_days=366)
    pairs = [*recent, age_365, age_366]
    result = evaluate(
        [item for _, item in pairs],
        [item for item, _ in pairs],
        retrieval_request=request(source_types=["disclosure"]),
    )
    assert result.windows[0].applied_by == "fallback"
    assert age_365[0].document_id in [item.document_id for item in result.evidence]
    assert age_366[0].document_id not in [item.document_id for item in result.evidence]
    assert warning_codes(result) == ["disclosure_window_extended"]


def test_fallback_never_adds_unrelated_evidence_or_calls_provider():
    pairs = [disclosure(f"2026072300050{index}", age_days=index) for index in range(4)]
    news = document("news:unrelated")
    result = evaluate(
        [*(item for _, item in pairs), evidence(news)],
        [*(item for item, _ in pairs), news],
        retrieval_request=request(source_types=["disclosure", "news"]),
    )
    assert len(result.evidence) == 5
    assert [item.document_id for item in result.evidence].count(news.document_id) == 1


def test_user_range_disables_fallback_and_shortage():
    pair = disclosure("20260723000601", age_days=300)
    result = evaluate(
        [pair[1]],
        [pair[0]],
        retrieval_request=correction_request(),
    )
    assert result.windows[0].applied_by == "user"
    assert warning_codes(result) == []


def test_exact_correction_replaces_exact_original_and_sets_latest_date():
    original = disclosure(
        "20260723001001",
        age_days=5,
        metadata={"has_subsequent_correction": True},
    )
    correction = disclosure(
        "20260723001002",
        age_days=2,
        metadata={"is_correction": True, "correction_of": "20260723001001"},
    )
    result = evaluate(
        [original[1], correction[1]],
        [original[0], correction[0]],
        retrieval_request=correction_request(),
    )
    assert [item.document_id for item in result.evidence] == [correction[0].document_id]
    assert result.latest_effective_disclosure_at == timestamp_at_age(2)
    assert "unresolved_disclosure_correction" not in warning_codes(result)


def test_explicit_correction_chain_retains_only_terminal():
    original = disclosure("20260723001101", age_days=7)
    first = disclosure(
        "20260723001102",
        age_days=5,
        metadata={"is_correction": True, "correction_of": "20260723001101"},
    )
    terminal = disclosure(
        "20260723001103",
        age_days=2,
        metadata={"is_correction": True, "correction_of": "20260723001102"},
    )
    result = evaluate(
        [original[1], first[1], terminal[1]],
        [original[0], first[0], terminal[0]],
        retrieval_request=correction_request(),
    )
    assert [item.document_id for item in result.evidence] == [terminal[0].document_id]
    assert warning_codes(result) == []


def test_unrelated_same_title_disclosure_remains():
    original = disclosure("20260723001201", title="same title")
    correction = disclosure(
        "20260723001202",
        metadata={"is_correction": True, "correction_of": "20260723001201"},
        title="same title",
    )
    unrelated = disclosure("20260723001203", title="same title")
    result = evaluate(
        [original[1], correction[1], unrelated[1]],
        [original[0], correction[0], unrelated[0]],
        retrieval_request=correction_request(),
    )
    assert [item.document_id for item in result.evidence] == [
        correction[0].document_id,
        unrelated[0].document_id,
    ]


def test_withdrawn_original_is_omitted():
    withdrawn = disclosure(
        "20260723001301",
        metadata={"is_withdrawn": True},
    )
    result = evaluate(
        [withdrawn[1]],
        [withdrawn[0]],
        retrieval_request=correction_request(),
    )
    assert result.evidence == ()
    assert result.latest_effective_disclosure_at is None


def test_withdrawn_correction_does_not_replace_original():
    original = disclosure("20260723001401", age_days=5)
    withdrawn_correction = disclosure(
        "20260723001402",
        age_days=2,
        metadata={
            "is_correction": True,
            "correction_of": "20260723001401",
            "is_withdrawn": True,
        },
    )
    result = evaluate(
        [original[1], withdrawn_correction[1]],
        [original[0], withdrawn_correction[0]],
        retrieval_request=correction_request(),
    )
    assert [item.document_id for item in result.evidence] == [original[0].document_id]


def test_unresolved_subsequent_correction_warns_and_nulls_latest():
    original = disclosure(
        "20260723001501",
        metadata={"has_subsequent_correction": True},
    )
    result = evaluate(
        [original[1]],
        [original[0]],
        retrieval_request=correction_request(),
    )
    assert "unresolved_disclosure_correction" in warning_codes(result)
    assert result.latest_effective_disclosure_at is None


def test_correction_without_relation_warns_and_nulls_latest():
    correction = disclosure(
        "20260723001601",
        metadata={"is_correction": True},
    )
    result = evaluate(
        [correction[1]],
        [correction[0]],
        retrieval_request=correction_request(),
    )
    assert "unresolved_disclosure_correction" in warning_codes(result)
    assert result.latest_effective_disclosure_at is None


def test_correction_with_absent_original_is_terminal_and_resolved():
    correction = disclosure(
        "20260723001702",
        age_days=2,
        metadata={"is_correction": True, "correction_of": "20260723001701"},
    )
    result = evaluate(
        [correction[1]],
        [correction[0]],
        retrieval_request=correction_request(),
    )
    assert [item.document_id for item in result.evidence] == [correction[0].document_id]
    assert warning_codes(result) == []
    assert result.latest_effective_disclosure_at == timestamp_at_age(2)


def test_available_cross_company_target_fails_closed():
    target = disclosure("20260723001801", security_id=SK_HYNIX)
    correction = disclosure(
        "20260723001802",
        metadata={"is_correction": True, "correction_of": "20260723001801"},
    )
    with pytest.raises(FreshnessValidationError) as exc_info:
        evaluate_freshness(
            [correction[1]],
            correction_request(),
            documents_by_id={
                correction[0].document_id: correction[0],
                target[0].document_id: target[0],
            },
            basis_at=BASIS_AT,
        )
    assert str(exc_info.value) == "disclosure correction relation is invalid"


def test_absent_target_does_not_create_output_or_affect_count():
    correction = disclosure(
        "20260723001902",
        metadata={"is_correction": True, "correction_of": "20260723001901"},
    )
    result = evaluate(
        [correction[1]],
        [correction[0]],
        retrieval_request=request(source_types=["disclosure"]),
    )
    assert len(result.evidence) == 1
    assert result.windows[0].applied_by == "fallback"
    assert "insufficient_disclosure_coverage" in warning_codes(result)


def test_multiple_unordered_terminal_corrections_warn():
    original = disclosure("20260723002001", age_days=5)
    first = disclosure(
        "20260723002002",
        age_days=2,
        metadata={"is_correction": True, "correction_of": "20260723002001"},
    )
    second = disclosure(
        "20260723002003",
        age_days=1,
        metadata={"is_correction": True, "correction_of": "20260723002001"},
    )
    result = evaluate(
        [original[1], first[1], second[1]],
        [original[0], first[0], second[0]],
        retrieval_request=correction_request(),
    )
    assert [item.document_id for item in result.evidence] == [
        first[0].document_id,
        second[0].document_id,
    ]
    assert "unresolved_disclosure_correction" in warning_codes(result)
    assert result.latest_effective_disclosure_at is None


def test_self_link_and_active_cycle_fail_closed():
    self_link = disclosure(
        "20260723002101",
        metadata={"is_correction": True, "correction_of": "20260723002101"},
    )
    with pytest.raises(FreshnessValidationError, match="disclosure correction relation is invalid"):
        evaluate(
            [self_link[1]],
            [self_link[0]],
            retrieval_request=correction_request(),
        )

    first = disclosure(
        "20260723002102",
        metadata={"is_correction": True, "correction_of": "20260723002103"},
    )
    second = disclosure(
        "20260723002103",
        metadata={"is_correction": True, "correction_of": "20260723002102"},
    )
    with pytest.raises(FreshnessValidationError, match="disclosure correction relation is invalid"):
        evaluate(
            [first[1], second[1]],
            [first[0], second[0]],
            retrieval_request=correction_request(),
        )


@pytest.mark.parametrize("bad_bool", [None, 0, 1, "true"])
def test_malformed_disclosure_bool_fails_safely(bad_bool):
    pair = disclosure(
        "20260723002201",
        metadata={"is_correction": bad_bool},
    )
    with pytest.raises(FreshnessValidationError) as exc_info:
        evaluate([pair[1]], [pair[0]], retrieval_request=correction_request())
    assert str(exc_info.value) == "disclosure metadata is invalid"


@pytest.mark.parametrize("bad_receipt", ["", " ", "123", 20260723002301])
def test_malformed_correction_receipt_fails_safely(bad_receipt):
    pair = disclosure(
        "20260723002302",
        metadata={"is_correction": True, "correction_of": bad_receipt},
    )
    with pytest.raises(FreshnessValidationError) as exc_info:
        evaluate([pair[1]], [pair[0]], retrieval_request=correction_request())
    assert str(exc_info.value) == "disclosure metadata is invalid"


def test_duplicate_replaced_and_withdrawn_occurrences_are_all_omitted():
    original = disclosure("20260723002401")
    correction = disclosure(
        "20260723002402",
        metadata={"is_correction": True, "correction_of": "20260723002401"},
    )
    withdrawn = disclosure("20260723002403", metadata={"is_withdrawn": True})
    items = [
        original[1],
        original[1].model_copy(update={"evidence_id": "evidence:original:duplicate"}),
        correction[1],
        withdrawn[1],
        withdrawn[1].model_copy(update={"evidence_id": "evidence:withdrawn:duplicate"}),
    ]
    result = evaluate(
        items,
        [original[0], correction[0], withdrawn[0]],
        retrieval_request=correction_request(),
    )
    assert [item.document_id for item in result.evidence] == [correction[0].document_id]


def test_duplicate_retained_occurrences_keep_input_order():
    pair = disclosure("20260723002501")
    duplicate = pair[1].model_copy(update={"evidence_id": "evidence:second"})
    result = evaluate(
        [duplicate, pair[1]],
        [pair[0]],
        retrieval_request=correction_request(),
    )
    assert [item.evidence_id for item in result.evidence] == ["evidence:second", pair[1].evidence_id]


def test_title_date_and_receipt_order_do_not_infer_correction():
    first = disclosure("20260723002601", age_days=5, title="same corrected title")
    second = disclosure("20260723002602", age_days=1, title="same corrected title")
    result = evaluate(
        [first[1], second[1]],
        [first[0], second[0]],
        retrieval_request=correction_request(),
    )
    assert [item.document_id for item in result.evidence] == [
        first[0].document_id,
        second[0].document_id,
    ]


def test_result_containers_are_frozen_tuples_and_evidence_is_isolated():
    linked_document = document()
    item = evidence(linked_document, retrieval_score=0.75)
    result = evaluate([item], [linked_document])
    assert isinstance(result.evidence, tuple)
    assert isinstance(result.windows, tuple)
    assert isinstance(result.warnings, tuple)
    with pytest.raises(FrozenInstanceError):
        result.basis_date = date(2020, 1, 1)  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.windows[0].start = date(2020, 1, 1)  # type: ignore[misc]

    returned = result.evidence[0]
    assert returned is not item
    assert returned.retrieval_score == 0.75
    returned.subject_security_ids.append(SK_HYNIX)
    returned.locator["nested"]["values"].append("changed")
    assert item.subject_security_ids == [SAMSUNG]
    assert item.locator["nested"]["values"] == ["original"]
    again = evaluate([item], [linked_document])
    assert again.evidence[0].subject_security_ids == [SAMSUNG]
    assert again.evidence[0].locator["nested"]["values"] == ["original"]


def test_repeated_calls_are_deterministic_and_inputs_are_unchanged():
    linked_document = document()
    item = evidence(linked_document)
    input_dump = item.model_dump()
    document_dump = linked_document.model_dump()
    retrieval_request = request(source_types=["news", "news"])
    request_dump = retrieval_request.model_dump()
    mapping = {linked_document.document_id: linked_document}
    mapping_view = MappingProxyType(mapping)
    first = evaluate_freshness([item], retrieval_request, documents_by_id=mapping_view, basis_at=BASIS_AT)
    second = evaluate_freshness([item], retrieval_request, documents_by_id=mapping_view, basis_at=BASIS_AT)
    assert first == second
    assert item.model_dump() == input_dump
    assert linked_document.model_dump() == document_dump
    assert retrieval_request.model_dump() == request_dump
    assert mapping == {linked_document.document_id: linked_document}


def test_warnings_are_deterministic_unique_and_expose_no_raw_values():
    old = document("news:old", published_at=timestamp_at_age(31), title="secret title")
    missing = document("news:missing", published_at=None)
    future = document("news:future", published_at=BASIS_AT + timedelta(days=1))
    result = evaluate(
        [evidence(old), evidence(missing, published_at=None), evidence(future)],
        [old, missing, future],
    )
    assert result.warnings == (
        FreshnessWarning("missing_published_at", "news"),
        FreshnessWarning("future_published_at", "news"),
        FreshnessWarning("stale_news", "news"),
    )
    serialized = repr(result.warnings)
    assert "secret title" not in serialized
    assert "news:old" not in serialized
    assert "https://" not in serialized


def test_hard_filter_then_freshness_then_retrieval_composition():
    good = document(
        "news:good",
        published_at=timestamp_at_age(1),
        metadata={"document_type": "article"},
    )
    wrong_company = document(
        "news:wrong-company",
        primary_security_ids=[SK_HYNIX],
        published_at=timestamp_at_age(1),
        metadata={"document_type": "article"},
    )
    wrong_source = document(
        "disclosure:20260723003001",
        source_type="disclosure",
        published_at=timestamp_at_age(1),
        metadata={"document_type": "article"},
    )
    wrong_date = document(
        "news:wrong-date",
        published_at=timestamp_at_age(5),
        metadata={"document_type": "article"},
    )
    wrong_type = document(
        "news:wrong-type",
        published_at=timestamp_at_age(1),
        metadata={"document_type": "memo"},
    )
    documents = [good, wrong_company, wrong_source, wrong_date, wrong_type]
    normalized = normalize_financial_documents(documents)
    retrieval_request = request(
        source_types=["news"],
        date_range=DateRange(start=BASIS_DATE - timedelta(days=1), end=BASIS_DATE),
        document_types=["article"],
    )
    mapping = {item.document_id: item for item in documents}
    filtered = filter_evidence(normalized, retrieval_request, documents_by_id=mapping)
    freshness = evaluate_freshness(
        filtered,
        retrieval_request,
        documents_by_id=mapping,
        basis_at=BASIS_AT,
    )
    retrieved = retrieve_evidence(
        freshness.evidence,
        retrieval_request,
        documents_by_id=mapping,
    )
    assert [item.document_id for item in filtered] == [good.document_id]
    assert [item.document_id for item in freshness.evidence] == [good.document_id]
    assert [item.document_id for item in retrieved.evidence] == [good.document_id]
    assert freshness.evidence[0].retrieval_score is None
    assert retrieved.evidence[0].retrieval_score is not None
    assert retrieved.evidence[0] is not freshness.evidence[0]
    assert normalized[0].retrieval_score is None


def test_stale_items_are_removed_before_retrieval_top_k():
    current = document(
        "news:current",
        published_at=timestamp_at_age(1),
        text="memory risk current",
    )
    stale = document(
        "news:stale",
        published_at=timestamp_at_age(31),
        text="memory risk memory risk memory risk",
    )
    documents = [current, stale]
    normalized = normalize_financial_documents(documents)
    retrieval_request = request(source_types=["news"])
    mapping = {item.document_id: item for item in documents}
    filtered = filter_evidence(normalized, retrieval_request, documents_by_id=mapping)
    freshness = evaluate_freshness(
        filtered,
        retrieval_request,
        documents_by_id=mapping,
        basis_at=BASIS_AT,
    )
    retrieved = retrieve_evidence(
        freshness.evidence,
        retrieval_request,
        documents_by_id=mapping,
    )
    assert [item.document_id for item in freshness.evidence] == [current.document_id]
    assert stale.document_id not in [item.document_id for item in retrieved.evidence]


def test_module_scope_has_no_forbidden_runtime_imports():
    source = inspect.getsource(__import__("app.evidence.freshness", fromlist=["*"]))
    tree = ast.parse(source)
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_modules.update(
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    )
    forbidden = {
        "app.providers",
        "app.ingest",
        "app.retrieval",
        "app.planning",
        "app.api",
        "app.llm",
        "cache",
        "repository",
        "vector",
        "reranker",
        "dedupe",
    }
    assert not any(
        module == forbidden_module or module.startswith(f"{forbidden_module}.")
        for module in imported_modules
        for forbidden_module in forbidden
    )
