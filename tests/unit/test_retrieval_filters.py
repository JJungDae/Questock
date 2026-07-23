from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from app.core.models import DateRange, Evidence, FinancialDocument, RetrievalRequest
from app.retrieval import HardFilterValidationError, filter_evidence, filter_financial_documents

SAMSUNG = "KRX:005930"
SK_HYNIX = "KRX:000660"
HYUNDAI = "KRX:005380"
UTC = timezone.utc


def request(
    *,
    security_id: str = SAMSUNG,
    source_types: list[str] | None = None,
    date_range: DateRange | None = None,
    document_types: list[str] | None = None,
    top_k: int = 1,
) -> RetrievalRequest:
    return RetrievalRequest(
        query="query",
        security_id=security_id,
        source_types=source_types if source_types is not None else ["news", "disclosure", "research_report"],
        date_range=date_range,
        document_types=document_types,
        top_k=top_k,
    )


def document(
    document_id: str = "doc:1",
    *,
    source_type: str = "news",
    primary_security_ids: list[str] | None = None,
    mentioned_security_ids: list[str] | None = None,
    published_at: datetime | None = datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
    metadata: dict[str, object] | None = None,
    text: str = "document text",
) -> FinancialDocument:
    return FinancialDocument(
        document_id=document_id,
        source_type=source_type,
        provider="test",
        primary_security_ids=primary_security_ids if primary_security_ids is not None else [SAMSUNG],
        mentioned_security_ids=mentioned_security_ids or [],
        title=f"title {document_id}",
        published_at=published_at,
        source_url="https://example.com/doc",
        text=text,
        locator={"kind": "test", "id": document_id},
        metadata=metadata or {},
        ingestion_version="test-v1",
    )


def evidence(
    evidence_id: str = "ev:1",
    *,
    document_id: str = "doc:1",
    source_type: str = "news",
    subject_security_ids: list[str] | None = None,
    mentioned_security_ids: list[str] | None = None,
    scope: str = "company_specific",
    published_at: datetime | None = datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
    retrieval_score: float | None = 0.1,
) -> Evidence:
    return Evidence(
        evidence_id=evidence_id,
        document_id=document_id,
        source_type=source_type,
        title=f"title {evidence_id}",
        source_url="https://example.com/evidence",
        published_at=published_at,
        subject_security_ids=subject_security_ids if subject_security_ids is not None else [SAMSUNG],
        mentioned_security_ids=mentioned_security_ids or [],
        scope=scope,  # type: ignore[arg-type]
        snippet="evidence snippet",
        locator={"kind": "test", "id": evidence_id},
        retrieval_score=retrieval_score,
    )


def assert_sanitized(exc_info) -> None:
    message = str(exc_info.value)
    assert "C:" not in message
    assert "/root" not in message
    assert "document text" not in message
    assert "evidence snippet" not in message
    assert "locator" not in message
    assert "metadata" not in message
    assert "secret" not in message.lower()


@pytest.mark.parametrize(
    "bad_request",
    [None, "query", object()],
)
def test_non_retrieval_request_raises_sanitized_error(bad_request):
    with pytest.raises(HardFilterValidationError) as exc_info:
        filter_financial_documents([], bad_request)  # type: ignore[arg-type]

    assert_sanitized(exc_info)


@pytest.mark.parametrize(
    "bad_documents",
    ["C:\\secret\\doc", b"secret", bytearray(b"secret"), {"doc": "secret"}, (item for item in []), 123],
)
def test_document_sequence_public_boundary_rejects_invalid_inputs(bad_documents):
    with pytest.raises(HardFilterValidationError) as exc_info:
        filter_financial_documents(bad_documents, request())  # type: ignore[arg-type]

    assert_sanitized(exc_info)


def test_wrong_document_item_type_raises_sanitized_error():
    with pytest.raises(HardFilterValidationError) as exc_info:
        filter_financial_documents([document(), "C:\\secret\\doc"], request())  # type: ignore[list-item]

    assert_sanitized(exc_info)


@pytest.mark.parametrize(
    "bad_evidence",
    ["C:\\secret\\ev", b"secret", bytearray(b"secret"), {"ev": "secret"}, (item for item in []), 123],
)
def test_evidence_sequence_public_boundary_rejects_invalid_inputs(bad_evidence):
    with pytest.raises(HardFilterValidationError) as exc_info:
        filter_evidence(bad_evidence, request())  # type: ignore[arg-type]

    assert_sanitized(exc_info)


def test_wrong_evidence_item_type_raises_sanitized_error():
    with pytest.raises(HardFilterValidationError) as exc_info:
        filter_evidence([evidence(), "C:\\secret\\ev"], request())  # type: ignore[list-item]

    assert_sanitized(exc_info)


@pytest.mark.parametrize(
    "documents_by_id",
    [
        "bad",
        {123: document()},
        {"doc:1": "bad"},
        {"wrong": document("doc:1")},
    ],
)
def test_documents_by_id_public_boundary_rejects_invalid_mappings(documents_by_id):
    with pytest.raises(HardFilterValidationError) as exc_info:
        filter_evidence([evidence()], request(), documents_by_id=documents_by_id)  # type: ignore[arg-type]

    assert_sanitized(exc_info)


def test_document_filter_source_security_and_order_are_deterministic():
    first = document("doc:1", source_type="disclosure", primary_security_ids=[SAMSUNG])
    second = document("doc:2", source_type="news", primary_security_ids=[SK_HYNIX], mentioned_security_ids=[SAMSUNG])
    wrong_source = document("doc:3", source_type="research_report", primary_security_ids=[SAMSUNG])
    wrong_company = document("doc:4", source_type="news", primary_security_ids=[SK_HYNIX])
    docs = [first, second, wrong_source, wrong_company]

    result = filter_financial_documents(docs, request(source_types=["disclosure", "news"]))

    assert result == [first, second]
    assert result is not docs
    result.append(wrong_company)
    assert docs == [first, second, wrong_source, wrong_company]


@pytest.mark.parametrize(
    ("source_types", "expected_ids"),
    [
        ([], []),
        (["unsupported"], []),
    ],
)
def test_document_filter_empty_or_unsupported_source_types_match_nothing(source_types, expected_ids):
    docs = [document("doc:1", source_type="news")]

    result = filter_financial_documents(docs, request(source_types=source_types))

    assert [item.document_id for item in result] == expected_ids


@pytest.mark.parametrize(
    ("published_at", "date_range", "passes"),
    [
        (datetime(2026, 7, 20, 15, 0, tzinfo=UTC), DateRange(start=date(2026, 7, 21), end=date(2026, 7, 21)), True),
        (datetime(2026, 7, 21, 14, 59, tzinfo=UTC), DateRange(start=date(2026, 7, 21), end=date(2026, 7, 21)), True),
        (datetime(2026, 7, 21, 15, 0, tzinfo=UTC), DateRange(start=date(2026, 7, 21), end=date(2026, 7, 21)), False),
        (datetime(2026, 7, 21, 0, 0, tzinfo=UTC), DateRange(start=date(2026, 7, 22), end=None), False),
        (datetime(2026, 7, 21, 0, 0, tzinfo=UTC), DateRange(start=None, end=date(2026, 7, 21)), True),
        (None, DateRange(start=date(2026, 7, 21), end=date(2026, 7, 21)), False),
        (datetime(2026, 7, 21, 0, 0), DateRange(start=date(2026, 7, 21), end=date(2026, 7, 21)), False),
        (None, None, True),
        (datetime(2026, 7, 21, 0, 0), None, True),
    ],
)
def test_document_filter_date_range_uses_aware_asia_seoul_dates(published_at, date_range, passes):
    doc = document(published_at=published_at)

    result = filter_financial_documents([doc], request(date_range=date_range))

    assert result == ([doc] if passes else [])


@pytest.mark.parametrize(
    ("metadata", "document_types", "passes"),
    [
        ({"document_type": "annual"}, None, True),
        ({"document_type": "annual"}, [], False),
        ({"document_type": "annual"}, ["annual"], True),
        ({"report_type": "initiation"}, ["initiation"], True),
        ({"content_level": "listing_metadata"}, ["listing_metadata"], True),
        ({}, ["annual"], False),
        ({"document_type": ""}, ["annual"], False),
        ({"document_type": "   "}, ["   "], False),
        ({"document_type": 1}, ["annual"], False),
        ({"title": "annual"}, ["annual"], False),
    ],
)
def test_document_filter_document_type_proof_uses_exact_metadata_fields(metadata, document_types, passes):
    doc = document(metadata=metadata)

    result = filter_financial_documents([doc], request(document_types=document_types))

    assert result == ([doc] if passes else [])


def test_document_filter_preserves_model_identity_and_does_not_mutate_request_or_document():
    req = request(document_types=["annual"], top_k=1)
    doc = document(metadata={"document_type": "annual"})
    original_metadata = dict(doc.metadata)

    result = filter_financial_documents([doc], req)

    assert result == [doc]
    assert result[0] is doc
    assert req.document_types == ["annual"]
    assert req.top_k == 1
    assert doc.metadata == original_metadata


def test_company_specific_evidence_scope_and_linked_primary_contract():
    target_primary = document("doc:1", primary_security_ids=[SAMSUNG])
    target_mentioned_only = document("doc:2", primary_security_ids=[SK_HYNIX], mentioned_security_ids=[SAMSUNG])
    target_ev = evidence("ev:1", document_id="doc:1", subject_security_ids=[SAMSUNG])
    mentioned_only_ev = evidence("ev:2", document_id="doc:2", subject_security_ids=[SAMSUNG])
    other_ev = evidence("ev:3", document_id="doc:1", subject_security_ids=[SK_HYNIX])

    result = filter_evidence(
        [target_ev, mentioned_only_ev, other_ev],
        request(source_types=["news"]),
        documents_by_id={"doc:1": target_primary, "doc:2": target_mentioned_only},
    )

    assert result == [target_ev]


def test_multi_company_evidence_subjects_must_be_document_primary_when_linked():
    both_primary = document("doc:1", primary_security_ids=[SAMSUNG, SK_HYNIX])
    sk_mentioned = document("doc:2", primary_security_ids=[SAMSUNG], mentioned_security_ids=[SK_HYNIX])
    target_ev = evidence("ev:1", document_id="doc:1", subject_security_ids=[SAMSUNG, SK_HYNIX], scope="multi_company")
    missing_target_ev = evidence("ev:2", document_id="doc:1", subject_security_ids=[SK_HYNIX, HYUNDAI], scope="multi_company")
    mentioned_subject_ev = evidence("ev:3", document_id="doc:2", subject_security_ids=[SAMSUNG, SK_HYNIX], scope="multi_company")

    result = filter_evidence(
        [target_ev, missing_target_ev, mentioned_subject_ev],
        request(source_types=["news"]),
        documents_by_id={"doc:1": both_primary, "doc:2": sk_mentioned},
    )

    assert result == [target_ev]


def test_industry_common_evidence_target_connection_rules():
    linked_target = document("doc:1", primary_security_ids=[SAMSUNG])
    linked_wrong = document("doc:2", primary_security_ids=[SK_HYNIX])
    mentioned_target = evidence(
        "ev:1",
        document_id="doc:missing",
        subject_security_ids=[],
        mentioned_security_ids=[SAMSUNG],
        scope="industry_common",
    )
    linked_target_ev = evidence(
        "ev:2",
        document_id="doc:1",
        subject_security_ids=[],
        mentioned_security_ids=[],
        scope="industry_common",
    )
    wrong_ev = evidence(
        "ev:3",
        document_id="doc:2",
        subject_security_ids=[],
        mentioned_security_ids=[SK_HYNIX],
        scope="industry_common",
    )

    without_mapping = filter_evidence([mentioned_target, linked_target_ev, wrong_ev], request(source_types=["news"]))
    with_mapping = filter_evidence(
        [mentioned_target, linked_target_ev, wrong_ev],
        request(source_types=["news"]),
        documents_by_id={"doc:1": linked_target, "doc:2": linked_wrong},
    )

    assert without_mapping == [mentioned_target]
    assert with_mapping == [linked_target_ev]


def test_industry_common_evidence_passes_when_target_only_mentioned_by_linked_document():
    linked_mentioned_only = document("doc:1", primary_security_ids=[SK_HYNIX], mentioned_security_ids=[SAMSUNG])
    linked_ev = evidence(
        "ev:1",
        document_id="doc:1",
        subject_security_ids=[],
        mentioned_security_ids=[],
        scope="industry_common",
    )

    result = filter_evidence(
        [linked_ev],
        request(source_types=["news"]),
        documents_by_id={"doc:1": linked_mentioned_only},
    )

    assert result == [linked_ev]


def test_linked_evidence_integrity_excludes_missing_source_mismatch_and_security_mismatch():
    linked_doc = document("doc:1", source_type="news", primary_security_ids=[SAMSUNG])
    missing = evidence("ev:1", document_id="missing", subject_security_ids=[SAMSUNG])
    source_mismatch = evidence("ev:2", document_id="doc:1", source_type="disclosure", subject_security_ids=[SAMSUNG])
    security_mismatch = evidence("ev:3", document_id="doc:1", subject_security_ids=[SK_HYNIX])
    valid = evidence("ev:4", document_id="doc:1", subject_security_ids=[SAMSUNG])

    result = filter_evidence(
        [missing, source_mismatch, security_mismatch, valid],
        request(source_types=["news", "disclosure"]),
        documents_by_id={"doc:1": linked_doc},
    )

    assert result == [valid]


def test_evidence_date_precedence_uses_evidence_timestamp_before_linked_document_timestamp():
    inside = datetime(2026, 7, 21, 0, 0, tzinfo=UTC)
    outside = datetime(2026, 7, 25, 0, 0, tzinfo=UTC)
    linked_inside = document("doc:1", published_at=inside)
    linked_outside = document("doc:2", published_at=outside)
    evidence_inside_document_outside = evidence("ev:1", document_id="doc:2", published_at=inside)
    evidence_outside_document_inside = evidence("ev:2", document_id="doc:1", published_at=outside)
    evidence_missing_document_inside = evidence("ev:3", document_id="doc:1", published_at=None)
    evidence_naive_document_inside = evidence("ev:4", document_id="doc:1", published_at=datetime(2026, 7, 21, 0, 0))
    evidence_missing_document_missing = evidence("ev:5", document_id="doc:3", published_at=None)
    linked_missing_date = document("doc:3", published_at=None)

    result = filter_evidence(
        [
            evidence_inside_document_outside,
            evidence_outside_document_inside,
            evidence_missing_document_inside,
            evidence_naive_document_inside,
            evidence_missing_document_missing,
        ],
        request(date_range=DateRange(start=date(2026, 7, 21), end=date(2026, 7, 21)), source_types=["news"]),
        documents_by_id={"doc:1": linked_inside, "doc:2": linked_outside, "doc:3": linked_missing_date},
    )

    assert result == [evidence_inside_document_outside, evidence_missing_document_inside, evidence_naive_document_inside]


def test_evidence_without_date_range_allows_missing_or_naive_timestamps():
    linked_doc = document("doc:1", published_at=None)
    missing = evidence("ev:1", document_id="doc:1", published_at=None)
    naive = evidence("ev:2", document_id="doc:1", published_at=datetime(2026, 7, 21, 0, 0))

    result = filter_evidence([missing, naive], request(source_types=["news"]), documents_by_id={"doc:1": linked_doc})

    assert result == [missing, naive]


def test_evidence_document_type_requires_valid_linked_document_proof():
    linked = document("doc:1", metadata={"content_level": "listing_metadata"})
    missing_metadata = document("doc:2", metadata={})
    non_string_metadata = document("doc:3", metadata={"content_level": 1})
    good = evidence("ev:1", document_id="doc:1")
    missing_link = evidence("ev:2", document_id="missing")
    no_metadata = evidence("ev:3", document_id="doc:2")
    wrong_metadata = evidence("ev:4", document_id="doc:3")

    with_mapping = filter_evidence(
        [good, missing_link, no_metadata, wrong_metadata],
        request(source_types=["news"], document_types=["listing_metadata"]),
        documents_by_id={"doc:1": linked, "doc:2": missing_metadata, "doc:3": non_string_metadata},
    )
    without_mapping = filter_evidence([good], request(source_types=["news"], document_types=["listing_metadata"]))

    assert with_mapping == [good]
    assert without_mapping == []


def test_evidence_document_type_none_works_without_linked_mapping_and_does_not_use_score_or_top_k():
    low_score = evidence("ev:1", retrieval_score=0.0)
    high_score = evidence("ev:2", retrieval_score=1.0)

    result = filter_evidence([low_score, high_score], request(source_types=["news"], top_k=1))

    assert result == [low_score, high_score]
    assert result[0] is low_score
    assert result[1] is high_score


def test_evidence_filter_preserves_outer_list_order_identity_and_does_not_mutate_inputs():
    req = request(source_types=["news"])
    linked = document("doc:1", metadata={"content_level": "listing_metadata"})
    first = evidence("ev:1", document_id="doc:1")
    second = evidence("ev:2", document_id="doc:1")
    evidence_items = [first, second]
    original_metadata = dict(linked.metadata)
    original_subjects = list(first.subject_security_ids)

    result = filter_evidence(evidence_items, req, documents_by_id={"doc:1": linked})

    assert result == [first, second]
    assert result is not evidence_items
    assert result[0] is first
    result.pop()
    assert req.source_types == ["news"]
    assert linked.metadata == original_metadata
    assert first.subject_security_ids == original_subjects


def test_filter_module_does_not_import_out_of_scope_boundaries():
    source = Path("app/retrieval/filters.py").read_text(encoding="utf-8")

    assert "app.providers" not in source
    assert "app.ingest" not in source
    assert "app.api" not in source
    assert "app.planning" not in source
    assert "top_k" not in source
    assert "retrieval_score" not in source
