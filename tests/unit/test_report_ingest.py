import copy
import hashlib
import json
import traceback
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.ingest.reports import (
    MANUAL_REPORT_PROVIDER,
    REPORT_INGESTION_VERSION,
    REPORT_SOURCE_TYPE,
    NormalizedReportDocumentBundle,
    NormalizedReportDocument,
    ReportBundleValidationError,
    ReportDocumentValidationError,
    ReportIngestValidationError,
    ReportManifestValidationError,
    ReportManifest,
    build_manual_research_documents,
    calculate_report_coverage,
    load_normalized_report_documents,
    load_report_manifest,
    normalize_manual_research_report,
    validate_normalized_report_document,
    validate_report_manifest,
    verify_manifest_source_hash,
)

MANIFEST_PATH = Path("tests/fixtures/reports/report_manifest_synthetic.json")
DOCUMENTS_PATH = Path("tests/fixtures/reports/normalized_report_synthetic.json")
SAMSUNG = "KRX:005930"
SK_HYNIX = "KRX:000660"
HYUNDAI = "KRX:005380"


def manifest_data(**updates):
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    data.update(updates)
    return data


def wrapper_data(**updates):
    data = json.loads(DOCUMENTS_PATH.read_text(encoding="utf-8"))
    data.update(updates)
    return data


def document_data(index=0, **updates):
    data = json.loads(json.dumps(wrapper_data()["documents"][index]))
    data.update(updates)
    return data


def manifest(**updates):
    return validate_report_manifest(manifest_data(**updates))


def documents(*raw_documents):
    if not raw_documents:
        return load_normalized_report_documents(DOCUMENTS_PATH)
    return NormalizedReportDocumentBundle(
        manifest_id=raw_documents[0]["manifest_id"],
        fixture_type="synthetic_unit",
        documents=tuple(validate_normalized_report_document(raw) for raw in raw_documents),
    )


def build_synthetic(selected_manifest=None, selected_documents=None, *, as_of_date=date(2026, 7, 22)):
    return build_manual_research_documents(
        selected_manifest or manifest(),
        selected_documents or load_normalized_report_documents(DOCUMENTS_PATH),
        mode="synthetic_unit",
        as_of_date=as_of_date,
    )


def corpus_manifest(source_bytes=b"approved report bytes", **updates):
    digest = hashlib.sha256(source_bytes).hexdigest()
    base = manifest_data()
    base.update(
        {
            "usage_review_status": "approved",
            "corpus_ingest_allowed": True,
            "external_llm_processing_allowed": True,
            "file_hash": digest,
            "hash_verification_status": "verified",
            "source_url": "https://research.example.com/reports/approved?id=1",
            "source_asset_id": None,
        }
    )
    base.update(updates)
    return validate_report_manifest(base)


def corpus_documents(*updates):
    first = document_data(manual_verification_status="verified_against_source")
    second = document_data(1, manual_verification_status="verified_against_source")
    for target, patch in zip((first, second), updates):
        target.update(patch)
    return tuple(validate_normalized_report_document(raw) for raw in (first, second))


def assert_invalid(raw_manifest=None, raw_document=None, exc=ReportIngestValidationError):
    with pytest.raises(exc):
        if raw_manifest is not None:
            validate_report_manifest(raw_manifest)
        else:
            validate_normalized_report_document(raw_document)


def test_loaders_and_synthetic_build_create_financial_documents():
    loaded_manifest = load_report_manifest(MANIFEST_PATH)
    loaded_documents = load_normalized_report_documents(DOCUMENTS_PATH)

    result = build_manual_research_documents(
        loaded_manifest,
        loaded_documents,
        mode="synthetic_unit",
        as_of_date=date(2026, 7, 22),
    )

    assert len(result) == 2
    first = result[0]
    assert first.document_id == "report:synthetic-report-001:section-1"
    assert first.source_type == REPORT_SOURCE_TYPE
    assert first.provider == MANUAL_REPORT_PROVIDER
    assert first.ingestion_version == REPORT_INGESTION_VERSION
    assert first.primary_security_ids == [SAMSUNG]
    assert first.mentioned_security_ids == []
    assert first.title == "Synthetic Research Report"
    assert first.published_at == datetime(2026, 1, 14, 15, 0, tzinfo=UTC)
    assert first.source_url is None
    assert first.locator == {
        "manifest_id": "synthetic-report-001",
        "document_id": "report:synthetic-report-001:section-1",
        "page": 1,
        "page_basis": "pdf_1_based",
        "section": "Synthetic Research Report",
        "publisher": "Synthetic Research Lab",
        "source_url": None,
        "source_asset_id": "synthetic-report-asset-001",
        "access_note": "Synthetic fixture asset only; no real report source.",
    }
    assert first.metadata["content_level"] == "research_report_section"
    assert first.metadata["published_at_precision"] == "date"
    assert first.metadata["timezone_basis"] == "Asia/Seoul"
    assert first.metadata["external_llm_processing_allowed"] is False
    assert first.metadata["build_mode"] == "synthetic_unit"
    assert first.metadata["is_stale_candidate"] is True
    assert result[1].mentioned_security_ids == [SK_HYNIX]


def test_identical_fixture_rerun_is_deterministic():
    first = [doc.model_dump() for doc in build_synthetic()]
    second = [doc.model_dump() for doc in build_synthetic()]

    assert first == second


def test_normalize_manual_research_report_helper_accepts_single_document_from_multi_section_manifest():
    multi_doc_manifest = manifest()
    one_doc = validate_normalized_report_document(document_data())

    doc = normalize_manual_research_report(
        multi_doc_manifest,
        one_doc,
        mode="synthetic_unit",
        as_of_date=date(2026, 7, 22),
    )

    assert doc.document_id == one_doc.document_id


@pytest.mark.parametrize(
    "field",
    [
        "manifest_id",
        "security_id",
        "title",
        "publisher",
        "published_at",
        "source_url",
        "source_asset_id",
        "access_note",
        "usage_note",
        "usage_review_status",
        "corpus_ingest_allowed",
        "external_llm_processing_allowed",
        "file_hash",
        "hash_scope",
        "hash_verification_status",
        "documents",
        "ingestion_version",
    ],
)
def test_manifest_required_fields(field):
    raw = manifest_data()
    raw.pop(field)

    assert_invalid(raw_manifest=raw, exc=ReportManifestValidationError)


def test_manifest_rejects_unexpected_fields_and_report_level_truth_stays_out_of_documents():
    assert_invalid(raw_manifest=manifest_data(extra="nope"), exc=ReportManifestValidationError)
    assert_invalid(raw_document=document_data(publisher="duplicated"), exc=ReportDocumentValidationError)
    assert_invalid(raw_document=document_data(published_at="2026-01-15"), exc=ReportDocumentValidationError)


@pytest.mark.parametrize(
    "updates",
    [
        {"manifest_id": "bad/id"},
        {"manifest_id": "bad id"},
        {"security_id": "KRX:123456"},
        {"title": "   "},
        {"publisher": 123},
        {"ingestion_version": "future-version"},
        {"documents": []},
        {"documents": ["report:synthetic-report-001:section-1", "report:synthetic-report-001:section-1"]},
        {"documents": ["report:other:section-1"]},
        {"documents": ["report:synthetic-report-001:bad/section"]},
    ],
)
def test_manifest_basic_validation_errors(updates):
    assert_invalid(raw_manifest=manifest_data(**updates), exc=ReportManifestValidationError)


@pytest.mark.parametrize(
    "updates",
    [
        {"usage_review_status": "pending", "corpus_ingest_allowed": True},
        {"usage_review_status": "rejected", "external_llm_processing_allowed": True},
        {"usage_review_status": "synthetic", "corpus_ingest_allowed": False, "external_llm_processing_allowed": True},
        {
            "usage_review_status": "approved",
            "corpus_ingest_allowed": False,
            "external_llm_processing_allowed": True,
        },
        {"usage_review_status": "approved", "corpus_ingest_allowed": "true"},
        {"external_llm_processing_allowed": 1},
        {"usage_review_status": "unknown"},
    ],
)
def test_permission_gate_validation(updates):
    assert_invalid(raw_manifest=manifest_data(**updates), exc=ReportManifestValidationError)


def test_approved_manifest_can_disable_external_llm_and_still_be_valid():
    approved = corpus_manifest(external_llm_processing_allowed=False)

    assert approved.usage_review_status == "approved"
    assert approved.external_llm_processing_allowed is False


@pytest.mark.parametrize(
    "source_url",
    [
        "file:///tmp/report.pdf",
        "C:/Users/USER/report.pdf",
        "/workspace/report.pdf",
        "\\\\server\\share\\report.pdf",
        "ftp://example.com/report.pdf",
        "https://user:pass@example.com/report.pdf",
        "https://example.com:bad/report.pdf",
        "https://example.com/report.pdf#section",
        "https://example.com/report.pdf?api_key=secret",
        "https://example.com/report.pdf?access_token=secret",
        "https://example.com/report.pdf?auth-token=secret",
        "https://example.com/report.pdf?bearer.token=secret",
        "https://example.com/report.pdf?client%5Fsecret=secret",
        "https://example.com/report.pdf?api-key=secret",
        "https://example.com/report.pdf?x-api-key=secret",
        "https://example.com/report.pdf?authorization=secret",
        "https://example.com/report.pdf?credential=secret",
        "https://example.com/report.pdf?signature=secret",
        "https://example.com/report.pdf?X-Amz-Signature=secret",
    ],
)
def test_source_url_safety_validation(source_url):
    assert_invalid(raw_manifest=manifest_data(source_url=source_url, source_asset_id=None), exc=ReportManifestValidationError)


def test_source_url_is_canonicalized_without_dropping_path_or_query():
    result = manifest(source_url="HTTPS://Example.COM:443/a/b?x=1", source_asset_id=None)

    assert result.source_url == "https://example.com/a/b?x=1"


@pytest.mark.parametrize(
    "source_asset_id",
    [
        "C:/report.pdf",
        "/workspace/report.pdf",
        "folder/report",
        "folder\\report",
        "asset id",
        "file://asset",
        ".",
        "..",
        "---",
        "",
    ],
)
def test_source_asset_id_must_be_opaque(source_asset_id):
    assert_invalid(
        raw_manifest=manifest_data(source_url=None, source_asset_id=source_asset_id),
        exc=ReportManifestValidationError,
    )


def test_source_url_or_source_asset_id_is_required_and_access_note_alone_is_not_enough():
    assert_invalid(
        raw_manifest=manifest_data(source_url=None, source_asset_id=None, access_note="can ask analyst"),
        exc=ReportManifestValidationError,
    )


@pytest.mark.parametrize(
    "updates",
    [
        {"published_at": "2026-01-15T10:30:00"},
        {"published_at": "2026-01-15 10:30:00+09:00"},
        {"published_at": "2026-01-15T10:30+09:00"},
        {"published_at": "not-a-date"},
        {"published_at": "2026-02-31"},
        {"basis_date": "2026-02-31"},
        {"basis_date": "20260131"},
    ],
)
def test_publication_and_basis_date_validation(updates):
    assert_invalid(raw_manifest=manifest_data(**updates), exc=ReportManifestValidationError)


def test_rfc3339_publication_datetime_is_timezone_aware_utc():
    result = manifest(published_at="2026-01-15T09:30:00+09:00")

    assert result.published_at == datetime(2026, 1, 15, 0, 30, tzinfo=UTC)
    assert result.published_at_precision == "datetime"
    assert result.published_at_timezone_basis == "+09:00"


def test_future_publication_is_rejected_at_build_time():
    future = manifest(published_at="2026-08-01")

    with pytest.raises(ReportIngestValidationError):
        build_synthetic(selected_manifest=future, as_of_date=date(2026, 7, 22))


def test_stale_boundary_is_deterministic():
    day_180 = build_synthetic(selected_manifest=manifest(published_at="2026-01-23"), as_of_date=date(2026, 7, 22))[0]
    day_181 = build_synthetic(selected_manifest=manifest(published_at="2026-01-22"), as_of_date=date(2026, 7, 22))[0]

    assert day_180.metadata["age_days"] == 180
    assert day_180.metadata["is_stale_candidate"] is False
    assert day_181.metadata["age_days"] == 181
    assert day_181.metadata["is_stale_candidate"] is True


@pytest.mark.parametrize(
    "updates",
    [
        {"segment_id": "bad/id"},
        {"segment_id": "bad id"},
        {"document_id": "report:synthetic-report-001:wrong"},
        {"security_id": "KRX:123456"},
        {"mentioned_security_ids": [SAMSUNG]},
        {"mentioned_security_ids": [SK_HYNIX, SK_HYNIX]},
        {"mentioned_security_ids": ["KRX:123456"]},
        {"subject_scope": "multi_company"},
        {"subject_scope": "company_specific", "mentioned_security_ids": [SK_HYNIX]},
        {"subject_scope": "company_centered_with_mentions", "mentioned_security_ids": []},
        {"page": 0},
        {"page": True},
        {"page": None},
        {"page": 2, "page_basis": "source_section_only"},
        {"page_basis": "zero_based"},
        {"section": "  "},
        {"text": "  "},
        {"text_kind": "generated"},
        {"manual_verification_status": "auto"},
        {"contains_numeric_claims": "false"},
        {"numeric_claims_verified": 1},
        {"contains_numeric_claims": False, "numeric_claims_verified": True},
    ],
)
def test_document_validation_errors(updates):
    assert_invalid(raw_document=document_data(**updates), exc=ReportDocumentValidationError)


def test_no_auto_mentioned_security_extraction_from_text():
    raw = document_data(text="Synthetic text names KRX:000660 but explicit mentions stay empty.")

    doc = validate_normalized_report_document(raw)

    assert doc.mentioned_security_ids == ()


def test_bundle_requires_exact_manifest_document_set_and_matching_security():
    with pytest.raises(ReportBundleValidationError):
        build_synthetic(selected_documents=documents(document_data()))
    with pytest.raises(ReportBundleValidationError):
        build_synthetic(selected_documents=documents(document_data(security_id=HYUNDAI), document_data(1)))
    with pytest.raises(ReportBundleValidationError):
        build_synthetic(
            selected_documents=documents(
                document_data(),
                document_data(document_id="report:synthetic-report-001:section-1"),
            )
        )


def test_bundle_wrapper_manifest_id_must_match_target_manifest():
    bad_bundle = NormalizedReportDocumentBundle(
        manifest_id="other-manifest",
        fixture_type="synthetic_unit",
        documents=load_normalized_report_documents(DOCUMENTS_PATH).documents,
    )

    with pytest.raises(ReportBundleValidationError):
        build_synthetic(selected_documents=bad_bundle)


def test_bundle_output_order_follows_manifest_order_not_document_input_order():
    loaded_manifest = manifest()
    reversed_bundle = documents(document_data(1), document_data())

    result = build_synthetic(selected_manifest=loaded_manifest, selected_documents=reversed_bundle)

    assert [doc.document_id for doc in result] == list(loaded_manifest.documents)


@pytest.mark.parametrize(
    "updates",
    [
        {"file_hash": "A" * 64},
        {"file_hash": "0" * 63},
        {"file_hash": "g" * 64},
        {"hash_scope": "file_path"},
        {"hash_verification_status": "trusted"},
    ],
)
def test_hash_manifest_validation(updates):
    assert_invalid(raw_manifest=manifest_data(**updates), exc=ReportManifestValidationError)


def test_verify_manifest_source_hash_true_false_and_requires_bytes():
    source_bytes = b"approved source"
    approved = corpus_manifest(source_bytes=source_bytes)

    assert verify_manifest_source_hash(approved, source_bytes) is True
    assert verify_manifest_source_hash(approved, b"different") is False
    with pytest.raises(ReportManifestValidationError):
        verify_manifest_source_hash(approved, None)
    with pytest.raises(ReportManifestValidationError):
        verify_manifest_source_hash(approved, bytearray(source_bytes))


@pytest.mark.parametrize(
    "mode",
    ["", "live", None],
)
def test_build_mode_is_explicit_and_limited(mode):
    with pytest.raises(ReportIngestValidationError):
        build_manual_research_documents(manifest(), load_normalized_report_documents(DOCUMENTS_PATH), mode=mode, as_of_date=date(2026, 7, 22))


def test_synthetic_build_rejects_non_synthetic_statuses():
    with pytest.raises(ReportBundleValidationError):
        build_manual_research_documents(
            corpus_manifest(external_llm_processing_allowed=False),
            corpus_documents(),
            mode="synthetic_unit",
            as_of_date=date(2026, 7, 22),
            source_bytes=b"approved report bytes",
        )


def test_synthetic_build_requires_synthetic_wrapper():
    with pytest.raises(ReportBundleValidationError):
        build_manual_research_documents(
            manifest(),
            list(load_normalized_report_documents(DOCUMENTS_PATH).documents),
            mode="synthetic_unit",
            as_of_date=date(2026, 7, 22),
        )


def test_corpus_build_requires_approved_permissions_hash_source_bytes_and_verified_documents():
    source_bytes = b"approved report bytes"
    approved = corpus_manifest(source_bytes=source_bytes)
    result = build_manual_research_documents(
        approved,
        corpus_documents(),
        mode="corpus",
        as_of_date=date(2026, 7, 22),
        source_bytes=source_bytes,
    )

    assert len(result) == 2
    assert result[0].metadata["build_mode"] == "corpus"
    assert result[0].metadata["hash_verification_status"] == "verified"

    with pytest.raises(ReportBundleValidationError):
        build_manual_research_documents(approved, corpus_documents(), mode="corpus", as_of_date=date(2026, 7, 22), source_bytes=b"bad")
    with pytest.raises(ReportBundleValidationError):
        build_manual_research_documents(approved, documents(), mode="corpus", as_of_date=date(2026, 7, 22), source_bytes=source_bytes)
    with pytest.raises(ReportBundleValidationError):
        build_manual_research_documents(manifest(), load_normalized_report_documents(DOCUMENTS_PATH), mode="corpus", as_of_date=date(2026, 7, 22))


@pytest.mark.parametrize("fixture_type", ["synthetic_unit", "corpus", "anything"])
def test_corpus_build_rejects_all_bundle_inputs(fixture_type):
    source_bytes = b"approved report bytes"
    approved = corpus_manifest(source_bytes=source_bytes)
    bundle = NormalizedReportDocumentBundle(
        manifest_id=approved.manifest_id,
        fixture_type=fixture_type,
        documents=corpus_documents(),
    )

    with pytest.raises(ReportBundleValidationError):
        build_manual_research_documents(
            approved,
            bundle,
            mode="corpus",
            as_of_date=date(2026, 7, 22),
            source_bytes=source_bytes,
        )


def test_corpus_build_accepts_plain_list_and_tuple_when_other_gates_pass():
    source_bytes = b"approved report bytes"
    approved = corpus_manifest(source_bytes=source_bytes)

    list_result = build_manual_research_documents(
        approved,
        list(corpus_documents()),
        mode="corpus",
        as_of_date=date(2026, 7, 22),
        source_bytes=source_bytes,
    )
    tuple_result = build_manual_research_documents(
        approved,
        corpus_documents(),
        mode="corpus",
        as_of_date=date(2026, 7, 22),
        source_bytes=source_bytes,
    )

    assert len(list_result) == 2
    assert len(tuple_result) == 2


@pytest.mark.parametrize(
    "bad_documents",
    [
        "not documents",
        b"bytes",
        bytearray(b"bytes"),
        {"document": "..."},
        [],
        (),
        (doc for doc in []),
        [object()],
    ],
)
def test_corpus_build_rejects_bad_plain_sequence_types(bad_documents):
    source_bytes = b"approved report bytes"
    approved = corpus_manifest(source_bytes=source_bytes)

    with pytest.raises(ReportBundleValidationError):
        build_manual_research_documents(
            approved,
            bad_documents,
            mode="corpus",
            as_of_date=date(2026, 7, 22),
            source_bytes=source_bytes,
        )


def test_corpus_build_rejects_mixed_plain_sequence():
    source_bytes = b"approved report bytes"
    approved = corpus_manifest(source_bytes=source_bytes)
    valid_document = corpus_documents()[0]

    with pytest.raises(ReportBundleValidationError):
        build_manual_research_documents(
            approved,
            [valid_document, object()],
            mode="corpus",
            as_of_date=date(2026, 7, 22),
            source_bytes=source_bytes,
        )


def test_corpus_source_asset_only_must_be_resolvable():
    source_bytes = b"asset only report"
    approved = corpus_manifest(
        source_bytes=source_bytes,
        source_url=None,
        source_asset_id="approved-asset-001",
    )

    with pytest.raises(ReportBundleValidationError):
        build_manual_research_documents(
            approved,
            corpus_documents(),
            mode="corpus",
            as_of_date=date(2026, 7, 22),
            source_bytes=source_bytes,
            available_asset_ids=set(),
        )

    result = build_manual_research_documents(
        approved,
        corpus_documents(),
        mode="corpus",
        as_of_date=date(2026, 7, 22),
        source_bytes=source_bytes,
        available_asset_ids={"approved-asset-001"},
    )

    assert result[0].locator["source_asset_id"] == "approved-asset-001"


def test_financial_document_payload_has_no_local_path_or_secret_and_keeps_numeric_metadata():
    result = build_synthetic()[1]
    combined = json.dumps(
        {"locator": result.locator, "metadata": result.metadata, "text": result.text},
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )

    assert "C:/Users" not in combined
    assert "/workspace" not in combined
    assert "SECRET_SENTINEL" not in combined
    assert result.metadata["contains_numeric_claims"] is True
    assert result.metadata["numeric_claims_verified"] is False
    assert result.metadata["text_kind"] == "manual_summary"
    assert result.metadata["manual_verification_status"] == "synthetic"


def test_calculate_report_coverage_counts_distinct_real_eligible_manifests_only():
    source_bytes = b"approved report bytes"
    approved = corpus_manifest(source_bytes=source_bytes)
    duplicate = approved
    documents_by_manifest = {
        approved.manifest_id: corpus_documents(),
    }

    coverage = calculate_report_coverage(
        [approved, duplicate],
        documents_by_manifest,
        as_of_date=date(2026, 7, 22),
        source_bytes_by_manifest={approved.manifest_id: source_bytes},
    )
    synthetic_coverage = calculate_report_coverage(
        [manifest()],
        {manifest().manifest_id: load_normalized_report_documents(DOCUMENTS_PATH)},
        as_of_date=date(2026, 7, 22),
    )
    bundle_coverage = calculate_report_coverage(
        [approved],
        {
            approved.manifest_id: NormalizedReportDocumentBundle(
                manifest_id=approved.manifest_id,
                fixture_type="corpus",
                documents=corpus_documents(),
            )
        },
        as_of_date=date(2026, 7, 22),
        source_bytes_by_manifest={approved.manifest_id: source_bytes},
    )

    assert coverage[SAMSUNG] == 1
    assert synthetic_coverage[SAMSUNG] == 0
    assert bundle_coverage[SAMSUNG] == 0
    assert coverage[SK_HYNIX] == 0
    assert coverage[HYUNDAI] == 0


def test_load_normalized_report_documents_rejects_bad_wrapper(tmp_path):
    bad_file = tmp_path / "bad.json"
    data = wrapper_data(fixture_type="corpus")
    bad_file.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ReportDocumentValidationError):
        load_normalized_report_documents(bad_file)


@pytest.mark.parametrize("fixture_version", [True, "1", 2, 0])
def test_load_normalized_report_documents_rejects_bad_fixture_version(tmp_path, fixture_version):
    bad_file = tmp_path / "bad_version.json"
    data = wrapper_data(fixture_version=fixture_version)
    bad_file.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ReportDocumentValidationError):
        load_normalized_report_documents(bad_file)


def test_json_loaders_reject_non_object_json(tmp_path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("[]", encoding="utf-8")

    with pytest.raises(ReportIngestValidationError):
        load_report_manifest(bad_file)


def test_loaders_normalize_io_and_unicode_errors_without_paths(tmp_path):
    missing_file = tmp_path / "missing.json"
    invalid_unicode = tmp_path / "invalid_unicode.json"
    malformed_json = tmp_path / "malformed.json"
    invalid_unicode.write_bytes(b"\xff")
    malformed_json.write_text('{"secret": "SECRET_SENTINEL"', encoding="utf-8")

    for path in (missing_file, invalid_unicode, malformed_json):
        with pytest.raises(ReportIngestValidationError) as exc:
            load_report_manifest(path)
        message = str(exc.value)
        formatted = "".join(traceback.format_exception(exc.type, exc.value, exc.tb))
        assert str(tmp_path) not in message
        assert str(tmp_path) not in formatted
        assert path.name not in message
        assert path.name not in formatted
        assert "SECRET_SENTINEL" not in message
        assert "SECRET_SENTINEL" not in formatted
        assert exc.value.__cause__ is None


def test_error_messages_do_not_include_raw_secret_or_local_path():
    raw = manifest_data(source_url="https://example.com/report.pdf?api_key=SECRET_SENTINEL")

    with pytest.raises(ReportManifestValidationError) as exc:
        validate_report_manifest(raw)

    message = str(exc.value)
    assert "SECRET_SENTINEL" not in message
    assert "api_key=SECRET_SENTINEL" not in message


@pytest.mark.parametrize(
    "bad_manifest",
    [
        lambda m: replace(m, source_url="https://example.com/report.pdf?api_key=secret", source_asset_id=None),
        lambda m: replace(m, source_url=None, source_asset_id="."),
        lambda m: replace(m, usage_review_status="pending", corpus_ingest_allowed=True),
        lambda m: replace(m, published_at=datetime(2026, 1, 15, 0, 0)),
        lambda m: replace(m, published_local_date=date(2026, 1, 16)),
        lambda m: replace(m, documents=("report:synthetic-report-001:bad/section",)),
        lambda m: replace(m, file_hash="A" * 64),
        lambda m: replace(m, security_id="KRX:123456"),
    ],
)
def test_direct_created_invalid_manifest_fails_public_build_boundaries(bad_manifest):
    bad = bad_manifest(manifest())

    with pytest.raises(ReportIngestValidationError):
        build_manual_research_documents(bad, load_normalized_report_documents(DOCUMENTS_PATH), mode="synthetic_unit", as_of_date=date(2026, 7, 22))
    with pytest.raises(ReportIngestValidationError):
        normalize_manual_research_report(bad, load_normalized_report_documents(DOCUMENTS_PATH).documents[0], mode="synthetic_unit", as_of_date=date(2026, 7, 22))


@pytest.mark.parametrize(
    "bad_document",
    [
        lambda d: replace(d, subject_scope="multi_company"),
        lambda d: replace(d, page=-1),
        lambda d: replace(d, page=1, page_basis="source_section_only"),
        lambda d: replace(d, page=None, page_basis="pdf_1_based"),
        lambda d: replace(d, mentioned_security_ids=(SK_HYNIX, SK_HYNIX)),
        lambda d: replace(d, mentioned_security_ids=("KRX:123456",)),
        lambda d: replace(d, mentioned_security_ids=(SAMSUNG,)),
        lambda d: replace(d, contains_numeric_claims=False, numeric_claims_verified=True),
        lambda d: replace(d, contains_numeric_claims="false"),
        lambda d: replace(d, document_id="report:synthetic-report-001:bad"),
        lambda d: replace(d, text="  "),
    ],
)
def test_direct_created_invalid_document_fails_public_boundaries(bad_document):
    bad = bad_document(load_normalized_report_documents(DOCUMENTS_PATH).documents[0])

    with pytest.raises(ReportIngestValidationError):
        normalize_manual_research_report(manifest(), bad, mode="synthetic_unit", as_of_date=date(2026, 7, 22))


def test_direct_created_invalid_bundle_fails_synthetic_build():
    valid_documents = load_normalized_report_documents(DOCUMENTS_PATH).documents
    bad_fixture = NormalizedReportDocumentBundle("synthetic-report-001", "bad", valid_documents)
    bad_manifest = NormalizedReportDocumentBundle("other-manifest", "synthetic_unit", valid_documents)
    duplicate = NormalizedReportDocumentBundle("synthetic-report-001", "synthetic_unit", (valid_documents[0], valid_documents[0]))
    invalid_child = NormalizedReportDocumentBundle(
        "synthetic-report-001",
        "synthetic_unit",
        (replace(valid_documents[0], text="  "), valid_documents[1]),
    )

    for bundle in (bad_fixture, bad_manifest, duplicate, invalid_child):
        with pytest.raises(ReportBundleValidationError):
            build_manual_research_documents(manifest(), bundle, mode="synthetic_unit", as_of_date=date(2026, 7, 22))


def test_single_synthetic_helper_contract_rejects_mismatches_and_non_synthetic_gates():
    valid_doc = load_normalized_report_documents(DOCUMENTS_PATH).documents[0]

    normalize_manual_research_report(manifest(), valid_doc, mode="synthetic_unit", as_of_date=date(2026, 7, 22))
    with pytest.raises(ReportBundleValidationError):
        normalize_manual_research_report(
            manifest(),
            replace(valid_doc, document_id="report:synthetic-report-001:not-listed", segment_id="not-listed"),
            mode="synthetic_unit",
            as_of_date=date(2026, 7, 22),
        )
    with pytest.raises(ReportBundleValidationError):
        normalize_manual_research_report(
            manifest(),
            replace(valid_doc, manifest_id="other-manifest", document_id="report:other-manifest:section-1"),
            mode="synthetic_unit",
            as_of_date=date(2026, 7, 22),
        )
    with pytest.raises(ReportBundleValidationError):
        normalize_manual_research_report(
            manifest(),
            replace(valid_doc, security_id=HYUNDAI),
            mode="synthetic_unit",
            as_of_date=date(2026, 7, 22),
        )
    with pytest.raises(ReportBundleValidationError):
        normalize_manual_research_report(
            corpus_manifest(external_llm_processing_allowed=False),
            replace(valid_doc, manual_verification_status="verified_against_source"),
            mode="synthetic_unit",
            as_of_date=date(2026, 7, 22),
        )


def assert_manifest_fails_public_boundaries(bad_manifest):
    valid_doc = load_normalized_report_documents(DOCUMENTS_PATH).documents[0]
    valid_bundle = load_normalized_report_documents(DOCUMENTS_PATH)

    with pytest.raises(ReportIngestValidationError):
        build_manual_research_documents(bad_manifest, valid_bundle, mode="synthetic_unit", as_of_date=date(2026, 7, 22))
    with pytest.raises(ReportIngestValidationError):
        normalize_manual_research_report(bad_manifest, valid_doc, mode="synthetic_unit", as_of_date=date(2026, 7, 22))
    with pytest.raises(ReportIngestValidationError):
        verify_manifest_source_hash(bad_manifest, b"source")


@pytest.mark.parametrize(
    "patch",
    [
        {"manifest_id": 123},
        {"security_id": 123},
        {"published_at_precision": 1},
        {"published_at_timezone_basis": 9},
        {"usage_review_status": 1},
        {"file_hash": 123},
        {"hash_scope": 123},
        {"hash_verification_status": 123},
        {"documents": ["report:synthetic-report-001:section-1"]},
        {"documents": ("report:synthetic-report-001:section-1", 123)},
        {"documents": (["bad"],)},
        {"documents": ({"bad": "value"},)},
        {"documents": ({1, 2},)},
        {"source_url": 123},
        {"source_asset_id": 123},
    ],
)
def test_direct_manifest_malformed_types_are_typed_public_boundary_errors(patch):
    assert_manifest_fails_public_boundaries(replace(manifest(), **patch))


def assert_document_fails_public_boundaries(bad_document):
    with pytest.raises(ReportIngestValidationError):
        normalize_manual_research_report(manifest(), bad_document, mode="synthetic_unit", as_of_date=date(2026, 7, 22))
    with pytest.raises(ReportIngestValidationError):
        build_manual_research_documents(
            manifest(),
            NormalizedReportDocumentBundle("synthetic-report-001", "synthetic_unit", (bad_document,)),
            mode="synthetic_unit",
            as_of_date=date(2026, 7, 22),
        )


@pytest.mark.parametrize(
    "patch",
    [
        {"manifest_id": 123},
        {"segment_id": 123},
        {"document_id": 123},
        {"security_id": 123},
        {"subject_scope": 123},
        {"page_basis": 123},
        {"text_kind": 123},
        {"manual_verification_status": 123},
        {"mentioned_security_ids": []},
        {"mentioned_security_ids": "KRX:000660"},
        {"summary_kind": 123},
    ],
)
def test_direct_document_malformed_types_are_typed_public_boundary_errors(patch):
    assert_document_fails_public_boundaries(replace(load_normalized_report_documents(DOCUMENTS_PATH).documents[0], **patch))


@pytest.mark.parametrize(
    "bad_bundle",
    [
        lambda docs: NormalizedReportDocumentBundle(123, "synthetic_unit", docs),
        lambda docs: NormalizedReportDocumentBundle("synthetic-report-001", 123, docs),
        lambda docs: NormalizedReportDocumentBundle("synthetic-report-001", "synthetic_unit", []),
        lambda docs: NormalizedReportDocumentBundle("synthetic-report-001", "synthetic_unit", list(docs)),
        lambda docs: NormalizedReportDocumentBundle("synthetic-report-001", "synthetic_unit", (object(),)),
    ],
)
def test_direct_bundle_malformed_types_are_bundle_errors(bad_bundle):
    docs = load_normalized_report_documents(DOCUMENTS_PATH).documents

    with pytest.raises(ReportBundleValidationError):
        build_manual_research_documents(manifest(), bad_bundle(docs), mode="synthetic_unit", as_of_date=date(2026, 7, 22))


@pytest.mark.parametrize(
    "bad_manifest",
    [
        lambda m: replace(m, published_at_timezone_basis="+09:00"),
        lambda m: replace(m, published_at_timezone_basis="UTC"),
        lambda m: replace(m, published_at=m.published_at + timedelta(seconds=1)),
    ],
)
def test_date_precision_metadata_must_be_internally_consistent(bad_manifest):
    assert_manifest_fails_public_boundaries(bad_manifest(manifest()))


@pytest.mark.parametrize(
    "bad_manifest",
    [
        lambda m: replace(m, published_at_timezone_basis="Asia/Seoul"),
        lambda m: replace(m, published_at_timezone_basis="+99:99"),
        lambda m: replace(m, published_at_timezone_basis="+24:00"),
        lambda m: replace(m, published_at_timezone_basis="-25:00"),
        lambda m: replace(m, published_local_date=m.published_local_date + timedelta(days=1)),
        lambda m: replace(m, published_at_precision=1),
        lambda m: replace(m, published_at_timezone_basis=9),
        lambda m: replace(m, published_at_timezone_basis=None),
    ],
)
def test_datetime_precision_metadata_must_be_internally_consistent(bad_manifest):
    base = manifest(published_at="2026-01-15T09:30:00+09:00")

    assert_manifest_fails_public_boundaries(bad_manifest(base))


@pytest.mark.parametrize(
    "published_at",
    [
        "2026-01-15",
        "2026-01-15T00:30:00Z",
        "2026-01-15T09:30:00+09:00",
        "2026-01-14T19:00:00-05:30",
    ],
)
def test_valid_publication_metadata_combinations_still_build(published_at):
    selected_manifest = manifest(published_at=published_at)
    selected_document = load_normalized_report_documents(DOCUMENTS_PATH).documents[0]

    doc = normalize_manual_research_report(
        selected_manifest,
        selected_document,
        mode="synthetic_unit",
        as_of_date=date(2026, 7, 22),
    )

    assert doc.document_id == selected_document.document_id


def test_calculate_report_coverage_skips_malformed_direct_manifest_and_keeps_valid_entry():
    source_bytes = b"approved report bytes"
    approved = corpus_manifest(source_bytes=source_bytes)
    invalid_id = replace(approved, manifest_id=123)
    invalid_unhashable_list = replace(approved, documents=(["bad"],))
    invalid_unhashable_dict = replace(approved, documents=({"bad": "value"},))
    invalid_unhashable_set = replace(approved, documents=({1, 2},))

    coverage = calculate_report_coverage(
        [invalid_id, invalid_unhashable_list, invalid_unhashable_dict, invalid_unhashable_set, approved],
        {approved.manifest_id: corpus_documents()},
        as_of_date=date(2026, 7, 22),
        source_bytes_by_manifest={approved.manifest_id: source_bytes},
    )

    assert coverage[SAMSUNG] == 1
