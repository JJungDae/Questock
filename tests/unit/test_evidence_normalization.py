from __future__ import annotations

import builtins
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.core.models import Evidence, FinancialDocument, RetrievalRequest, ensure_evidence_matches_document
from app.core.status import RetrievalStatus
from app.evidence import EvidenceNormalizationError, normalize_financial_document, normalize_financial_documents
from app.evidence import normalizer
from app.retrieval import filter_evidence, retrieve_evidence

SAMSUNG = "KRX:005930"
SK_HYNIX = "KRX:000660"
HYUNDAI = "KRX:005380"
UTC = timezone.utc
PUBLISHED_AT = datetime(2026, 7, 23, 1, 2, 3, tzinfo=UTC)


def document(
    document_id: str = "doc:unit",
    *,
    source_type: str = "news",
    primary_security_ids: list[str] | None = None,
    mentioned_security_ids: list[str] | None = None,
    title: str = "Exact document title",
    source_url: str | None = "https://example.test/document",
    text: str = "Revenue growth is 12 percent.",
    locator: dict[str, object] | None = None,
    metadata: dict[str, object] | None = None,
) -> FinancialDocument:
    return FinancialDocument(
        document_id=document_id,
        source_type=source_type,
        provider="unit-provider",
        primary_security_ids=[SAMSUNG] if primary_security_ids is None else primary_security_ids,
        mentioned_security_ids=[] if mentioned_security_ids is None else mentioned_security_ids,
        title=title,
        published_at=PUBLISHED_AT,
        source_url=source_url,
        text=text,
        locator={"kind": "unit", "nested": {"items": ["original"]}} if locator is None else locator,
        metadata={} if metadata is None else metadata,
        ingestion_version="unit-v1",
    )


def bypass_document(**updates: object) -> FinancialDocument:
    values = document().model_dump(mode="python")
    values.update(updates)
    return FinancialDocument.model_construct(**values)


def request(*, security_id: str = SAMSUNG, document_types: list[str] | None = None) -> RetrievalRequest:
    return RetrievalRequest(
        query="growth",
        security_id=security_id,
        source_types=["news", "disclosure", "research_report", "report"],
        document_types=document_types,
        top_k=6,
    )


def assert_sanitized(exc_info: pytest.ExceptionInfo[EvidenceNormalizationError], *raw_values: str) -> None:
    message = str(exc_info.value)
    for raw_value in raw_values:
        assert raw_value not in message
    assert "ValidationError" not in message
    assert "C:\\" not in message
    assert "/root" not in message


def test_package_exports_exact_public_api() -> None:
    from app import evidence

    assert evidence.__all__ == [
        "EvidenceNormalizationError",
        "normalize_financial_document",
        "normalize_financial_documents",
    ]
    assert evidence.EvidenceNormalizationError is EvidenceNormalizationError
    assert evidence.normalize_financial_document is normalize_financial_document
    assert evidence.normalize_financial_documents is normalize_financial_documents


@pytest.mark.parametrize("bad_document", [None, "not-a-document", object()])
def test_single_public_boundary_rejects_wrong_type(bad_document: object) -> None:
    with pytest.raises(EvidenceNormalizationError) as exc_info:
        normalize_financial_document(bad_document)  # type: ignore[arg-type]

    assert_sanitized(exc_info, "not-a-document")


@pytest.mark.parametrize(
    "bad_documents",
    [
        "documents",
        b"documents",
        bytearray(b"documents"),
        {"document": document()},
        (item for item in []),
        1,
    ],
)
def test_batch_public_boundary_rejects_non_sequences(bad_documents: object) -> None:
    with pytest.raises(EvidenceNormalizationError) as exc_info:
        normalize_financial_documents(bad_documents)  # type: ignore[arg-type]

    assert_sanitized(exc_info)


def test_batch_public_boundary_rejects_invalid_item() -> None:
    with pytest.raises(EvidenceNormalizationError) as exc_info:
        normalize_financial_documents([document(), "not-a-document"])  # type: ignore[list-item]

    assert_sanitized(exc_info, "not-a-document")


def test_empty_batch_returns_a_fresh_empty_list() -> None:
    first = normalize_financial_documents([])
    second = normalize_financial_documents([])

    assert first == []
    assert second == []
    assert first is not second


def test_batch_failure_returns_no_partial_result() -> None:
    invalid = bypass_document(source_url="not-an-http-url")

    with pytest.raises(EvidenceNormalizationError) as exc_info:
        normalize_financial_documents([document("doc:first"), invalid, document("doc:last")])

    assert_sanitized(exc_info, "not-an-http-url")


def test_bypass_created_document_is_canonically_revalidated() -> None:
    invalid = bypass_document(primary_security_ids="not-a-list")

    with pytest.raises(EvidenceNormalizationError) as exc_info:
        normalize_financial_document(invalid)

    assert_sanitized(exc_info, "not-a-list")


def test_expected_pydantic_validation_error_is_sanitized() -> None:
    invalid = bypass_document(source_url="not-an-http-url")

    with pytest.raises(EvidenceNormalizationError) as exc_info:
        normalize_financial_document(invalid)

    assert_sanitized(exc_info, "not-an-http-url")


def test_unexpected_internal_error_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(_: FinancialDocument) -> Evidence:
        raise RuntimeError("injected internal failure")

    monkeypatch.setattr(normalizer, "_build_evidence", fail)

    with pytest.raises(RuntimeError, match="injected internal failure"):
        normalize_financial_document(document())


def test_exact_field_mapping_and_source_type_passthrough() -> None:
    source_document = document(
        document_id="doc:exact",
        source_type="report",
        title="  Exact title is preserved  ",
        source_url=None,
    )

    evidence = normalize_financial_document(source_document)

    assert evidence.evidence_id == "evidence:doc:exact"
    assert evidence.document_id == source_document.document_id
    assert evidence.source_type == "report"
    assert evidence.title == "  Exact title is preserved  "
    assert evidence.source_url is None
    assert evidence.published_at == source_document.published_at
    assert evidence.retrieval_score is None
    assert set(Evidence.model_fields) == {
        "evidence_id",
        "document_id",
        "source_type",
        "title",
        "source_url",
        "published_at",
        "subject_security_ids",
        "mentioned_security_ids",
        "scope",
        "snippet",
        "locator",
        "retrieval_score",
    }


def test_snippet_whitespace_truncation_and_content_contract() -> None:
    long_text = "  revenue\n  12 percent\t" + ("x" * 600)
    source_document = document(text=long_text, title="Title must not be prepended")

    evidence = normalize_financial_document(source_document)

    expected = "revenue 12 percent " + ("x" * 600)
    assert evidence.snippet == expected[:500]
    assert len(evidence.snippet) == 500
    assert not evidence.snippet.endswith("...")
    assert "Title must not be prepended" not in evidence.snippet
    assert "12 percent" in evidence.snippet


@pytest.mark.parametrize("text", ["", " \n\t "])
def test_blank_document_text_is_rejected(text: str) -> None:
    with pytest.raises(EvidenceNormalizationError) as exc_info:
        normalize_financial_document(document(text=text))

    assert_sanitized(exc_info)


def test_repeated_normalization_is_deterministic() -> None:
    source_document = document(text="same\ntext")

    first = normalize_financial_document(source_document)
    second = normalize_financial_document(source_document)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_company_specific_attribution_preserves_mentions() -> None:
    source_document = document(mentioned_security_ids=[SK_HYNIX])

    evidence = normalize_financial_document(source_document)

    assert evidence.scope == "company_specific"
    assert evidence.subject_security_ids == [SAMSUNG]
    assert evidence.mentioned_security_ids == [SK_HYNIX]
    ensure_evidence_matches_document(evidence, source_document)


def test_multi_company_attribution_preserves_primary_order() -> None:
    source_document = document(
        primary_security_ids=[SK_HYNIX, SAMSUNG],
        mentioned_security_ids=[HYUNDAI],
    )

    evidence = normalize_financial_document(source_document)

    assert evidence.scope == "multi_company"
    assert evidence.subject_security_ids == [SK_HYNIX, SAMSUNG]
    assert evidence.mentioned_security_ids == [HYUNDAI]
    ensure_evidence_matches_document(evidence, source_document)


def test_mentioned_only_document_maps_to_industry_common() -> None:
    source_document = document(primary_security_ids=[], mentioned_security_ids=[SAMSUNG, SK_HYNIX])

    evidence = normalize_financial_document(source_document)

    assert evidence.scope == "industry_common"
    assert evidence.subject_security_ids == []
    assert evidence.mentioned_security_ids == [SAMSUNG, SK_HYNIX]
    ensure_evidence_matches_document(evidence, source_document)


@pytest.mark.parametrize(
    "updates",
    [
        {"primary_security_ids": [], "mentioned_security_ids": []},
        {"primary_security_ids": [SAMSUNG, SAMSUNG]},
        {"primary_security_ids": [SAMSUNG], "mentioned_security_ids": [SAMSUNG]},
    ],
)
def test_invalid_security_structure_is_rejected_by_revalidation(updates: dict[str, object]) -> None:
    with pytest.raises(EvidenceNormalizationError) as exc_info:
        normalize_financial_document(bypass_document(**updates))

    assert_sanitized(exc_info)


def test_report_company_centered_metadata_does_not_change_structural_attribution() -> None:
    source_document = document(
        source_type="research_report",
        mentioned_security_ids=[SK_HYNIX],
        metadata={"subject_scope": "company_centered_with_mentions"},
    )

    evidence = normalize_financial_document(source_document)

    assert evidence.scope == "company_specific"
    assert evidence.subject_security_ids == [SAMSUNG]
    assert evidence.mentioned_security_ids == [SK_HYNIX]


@pytest.mark.parametrize(
    "locator",
    [
        {
            "provider": "recorded_news",
            "source_url": "https://news.example.test/article",
            "published_at": "2026-07-23T01:02:03+00:00",
            "raw_index": 0,
            "query": "Samsung",
        },
        {
            "provider": "recorded_disclosure",
            "receipt_no": "20260723000001",
            "viewer_url": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260723000001",
            "corp_code": "00126380",
            "stock_code": "005930",
            "corp_name": "Samsung Electronics",
            "report_name": "Annual report",
            "received_date": "20260723",
        },
        {
            "manifest_id": "report-samsung-001",
            "document_id": "report:samsung:001:page-3",
            "page": 3,
            "page_basis": "pdf_1_based",
            "section": "Investment thesis",
            "publisher": "Unit Research",
            "source_url": "https://research.example.test/report",
            "source_asset_id": None,
            "access_note": "public URL",
        },
        {
            "manifest_id": "report-samsung-001",
            "document_id": "report:samsung:001:section-summary",
            "page": None,
            "page_basis": "source_section_only",
            "section": "Summary",
            "publisher": "Unit Research",
            "source_url": None,
            "source_asset_id": "asset-report-001",
            "access_note": "approved local record",
        },
    ],
)
def test_producer_shaped_locators_round_trip_without_identity(locator: dict[str, object]) -> None:
    source_document = document(locator=locator)

    evidence = normalize_financial_document(source_document)

    assert evidence.locator == source_document.locator
    assert evidence.locator is not source_document.locator


def test_generic_locator_is_supported_and_deep_copied() -> None:
    source_document = document(locator={"anchor": "section-1", "nested": {"items": ["original"]}})

    evidence = normalize_financial_document(source_document)
    evidence.locator["nested"]["items"].append("changed")  # type: ignore[index]

    assert source_document.locator == {"anchor": "section-1", "nested": {"items": ["original"]}}
    assert normalize_financial_document(source_document).locator == source_document.locator


@pytest.mark.parametrize(
    "locator",
    [
        {},
        {"path": "/root/private"},
        {"C:\\secret\\path": "safe"},
        {"nested": ("safe", "\\\\server\\share\\private")},
        {"file": "file:///private/source"},
    ],
)
def test_missing_or_unsafe_locator_is_rejected(locator: dict[str, object]) -> None:
    source_document = bypass_document(locator=locator)

    with pytest.raises(EvidenceNormalizationError) as exc_info:
        normalize_financial_document(source_document)

    assert_sanitized(exc_info)


def test_locator_output_is_json_serializable() -> None:
    evidence = normalize_financial_document(document(locator={"anchor": "section", "pages": (1, 2)}))

    assert json.loads(json.dumps(evidence.locator)) == {"anchor": "section", "pages": [1, 2]}


@pytest.mark.parametrize("path", ["C:\\private\\source", "\\\\server\\share\\source", "file:///private/source", "/root/private"])
def test_unsafe_output_scalars_are_rejected(path: str) -> None:
    source_document = bypass_document(title=path)

    with pytest.raises(EvidenceNormalizationError) as exc_info:
        normalize_financial_document(source_document)

    assert_sanitized(exc_info, path)


@pytest.mark.parametrize(
    ("source_document", "raw_path"),
    [
        (document(title=r"report saved at C:\Users\review\private.txt"), r"C:\Users\review\private.txt"),
        (document(text="loaded from /root/private/report.txt"), "/root/private/report.txt"),
        (document(locator={"source": r"source \\server\share\private.pdf"}), r"\\server\share\private.pdf"),
        (
            document(locator={"internal file file:///home/user/report.pdf": "safe"}),
            "file:///home/user/report.pdf",
        ),
        (document(document_id="doc stored at D:/private/report"), "D:/private/report"),
    ],
)
def test_embedded_local_absolute_paths_are_rejected(source_document: FinancialDocument, raw_path: str) -> None:
    with pytest.raises(EvidenceNormalizationError) as exc_info:
        normalize_financial_document(source_document)

    assert_sanitized(exc_info, raw_path)


@pytest.mark.parametrize(
    "source_document",
    [
        document(source_url="https://example.test/report"),
        document(source_url="http://example.test/article"),
        document(title="profit / loss widened"),
        document(title="API key exposure was discussed in the report"),
        document(title="authorization policy changed"),
    ],
)
def test_safe_near_neighbor_text_and_urls_remain_valid(source_document: FinancialDocument) -> None:
    evidence = normalize_financial_document(source_document)

    assert evidence.document_id == source_document.document_id
    assert evidence.title == source_document.title
    assert evidence.source_url == source_document.source_url


def test_returned_security_lists_are_isolated_from_caller_mutation() -> None:
    source_document = document(primary_security_ids=[SAMSUNG], mentioned_security_ids=[SK_HYNIX])

    evidence = normalize_financial_document(source_document)
    evidence.subject_security_ids.append(HYUNDAI)
    evidence.mentioned_security_ids.append(HYUNDAI)
    later = normalize_financial_document(source_document)

    assert source_document.primary_security_ids == [SAMSUNG]
    assert source_document.mentioned_security_ids == [SK_HYNIX]
    assert later.subject_security_ids == [SAMSUNG]
    assert later.mentioned_security_ids == [SK_HYNIX]


def test_non_string_locator_key_is_rejected_without_leaking_input() -> None:
    source_document = bypass_document(locator={1: "safe"})

    with pytest.raises(EvidenceNormalizationError) as exc_info:
        normalize_financial_document(source_document)

    assert_sanitized(exc_info, "safe")


def test_http_url_is_allowed_and_ordinary_credential_vocabulary_is_preserved() -> None:
    source_document = document(
        source_url="https://example.test/article?topic=api-key",
        title="Authorization event is discussed",
        text="The API key authorization policy is part of the source text.",
    )

    evidence = normalize_financial_document(source_document)

    assert evidence.source_url == "https://example.test/article?topic=api-key"
    assert evidence.title == "Authorization event is discussed"
    assert evidence.snippet == "The API key authorization policy is part of the source text."


@pytest.mark.parametrize(
    "source_url",
    [
        "https://user:password@example.test/article",
        "https://example.test/article?access_token=sentinel-secret",
        "https://example.test/article?api%2Dkey=sentinel-secret",
        "https://example.test/article?X-Amz-Signature=sentinel-secret",
    ],
)
def test_unsafe_source_url_is_rejected_without_leaking_values(source_url: str) -> None:
    with pytest.raises(EvidenceNormalizationError) as exc_info:
        normalize_financial_document(document(source_url=source_url))

    assert_sanitized(exc_info, source_url, "sentinel-secret", "password")


def test_duplicate_documents_preserve_order_and_return_fresh_evidence() -> None:
    source_document = document("doc:duplicate")

    normalized = normalize_financial_documents([source_document, source_document])

    assert [item.evidence_id for item in normalized] == ["evidence:doc:duplicate", "evidence:doc:duplicate"]
    assert normalized[0] is not normalized[1]
    assert normalized[0].locator is not normalized[1].locator


def test_permission_and_provenance_metadata_do_not_change_mapping() -> None:
    source_document = document(metadata={"fixture_type": "synthetic_unit", "external_llm_processing_allowed": False})
    changed_metadata = source_document.model_copy(
        update={"metadata": {"fixture_type": "recorded", "external_llm_processing_allowed": True}}
    )

    assert normalize_financial_document(source_document).model_dump(mode="json") == normalize_financial_document(
        changed_metadata
    ).model_dump(mode="json")


def test_normalizer_performs_no_file_io(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_open(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("file I/O is out of scope")

    monkeypatch.setattr(builtins, "open", fail_open)

    assert normalize_financial_document(document()).document_id == "doc:unit"


def test_normalized_evidence_passes_m2_hard_filter_for_all_scopes() -> None:
    company_document = document("doc:company")
    multi_document = document("doc:multi", primary_security_ids=[SAMSUNG, SK_HYNIX])
    industry_document = document("doc:industry", primary_security_ids=[], mentioned_security_ids=[SAMSUNG])
    normalized = normalize_financial_documents([company_document, multi_document, industry_document])
    documents_by_id = {item.document_id: item for item in [company_document, multi_document, industry_document]}

    result = filter_evidence(normalized, request(), documents_by_id=documents_by_id)

    assert result == normalized


def test_document_type_proof_remains_in_linked_document() -> None:
    source_document = document(metadata={"content_level": "listing_metadata"})
    evidence = normalize_financial_document(source_document)

    without_document = filter_evidence([evidence], request(document_types=["listing_metadata"]))
    with_document = filter_evidence(
        [evidence],
        request(document_types=["listing_metadata"]),
        documents_by_id={source_document.document_id: source_document},
    )

    assert without_document == []
    assert with_document == [evidence]


def test_m2_retriever_scores_a_copy_of_normalized_evidence() -> None:
    source_document = document(title="Growth growth outlook", text="Growth growth supports the outlook.")
    evidence = normalize_financial_document(source_document)

    result = retrieve_evidence(
        [evidence],
        request(),
        documents_by_id={source_document.document_id: source_document},
    )

    assert result.status == RetrievalStatus.OK
    assert result.evidence[0].document_id == source_document.document_id
    assert result.evidence[0] is not evidence
    assert result.evidence[0].retrieval_score is not None
    assert evidence.retrieval_score is None
    assert evidence.published_at == source_document.published_at


def test_normalizer_has_no_out_of_scope_module_imports() -> None:
    source = Path("app/evidence/normalizer.py").read_text(encoding="utf-8")

    for forbidden in (
        "app.providers",
        "app.ingest",
        "app.retrieval",
        "app.planning",
        "app.api",
        "app.llm",
        "embedding",
        "vector",
        "reranker",
        "dedupe",
    ):
        assert forbidden not in source
