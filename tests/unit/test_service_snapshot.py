from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from app.core.models import QueryPlan, SecurityIdentifier
from app.services.service_snapshot import (
    SERVICE_SNAPSHOT_BASIS_AT,
    SERVICE_SNAPSHOT_CHECKSUM_FILE,
    SERVICE_SNAPSHOT_COVERAGE_FILE,
    SERVICE_SNAPSHOT_DOCUMENTS_FILE,
    SERVICE_SNAPSHOT_ID,
    SERVICE_SNAPSHOT_PERMISSION_FILE,
    SERVICE_SNAPSHOT_ROOT,
    SERVICE_SNAPSHOT_VALIDATION_FILE,
    ServiceSnapshotValidationError,
    build_service_snapshot,
    build_snapshot_checksum,
    copy_service_snapshot,
    load_service_snapshot,
    serialize_service_snapshot_json,
)
from app.services.service_snapshot_gateway import (
    RecordedServiceSnapshotGateway,
)

_SNAPSHOT_DIR = SERVICE_SNAPSHOT_ROOT / SERVICE_SNAPSHOT_ID


def _payloads() -> tuple[dict[str, object], dict[str, object]]:
    manifest = json.loads(
        (_SNAPSHOT_DIR / "manifest.json").read_text(encoding="utf-8")
    )
    documents = json.loads(
        (_SNAPSHOT_DIR / "documents.json").read_text(encoding="utf-8")
    )
    return manifest, documents


def _rehash(
    manifest: dict[str, object],
    documents: dict[str, object],
) -> bytes:
    raw = serialize_service_snapshot_json(documents)
    manifest["documents_sha256"] = hashlib.sha256(raw).hexdigest()
    return raw


def test_canonical_service_snapshot_has_exact_approved_coverage() -> None:
    snapshot = load_service_snapshot()

    assert snapshot.snapshot_id == SERVICE_SNAPSHOT_ID
    assert snapshot.basis_at == SERVICE_SNAPSHOT_BASIS_AT
    assert len(snapshot.documents) == 54
    assert len({item.document_id for item in snapshot.documents}) == 54
    assert snapshot.coverage == {
        "news": {
            "document_count": 15,
            "per_security": {
                "KRX:005930": {
                    "document_count": 5,
                    "pre_market": 2,
                    "intraday": 3,
                },
                "KRX:000660": {
                    "document_count": 5,
                    "pre_market": 1,
                    "intraday": 4,
                },
                "KRX:005380": {
                    "document_count": 5,
                    "pre_market": 2,
                    "intraday": 3,
                },
            },
        },
        "disclosure": {
            "document_count": 3,
            "per_security": {
                "KRX:005930": {"document_count": 1, "fact_count": 18},
                "KRX:000660": {"document_count": 1, "fact_count": 21},
                "KRX:005380": {"document_count": 1, "fact_count": 20},
            },
        },
        "research_report": {
            "report_count": 3,
            "section_document_count": 36,
            "per_security": {
                "KRX:005930": {
                    "report_count": 1,
                    "section_document_count": 12,
                },
                "KRX:000660": {
                    "report_count": 1,
                    "section_document_count": 12,
                },
                "KRX:005380": {
                    "report_count": 1,
                    "section_document_count": 12,
                },
            },
        },
    }


def test_canonical_checksum_matches_exact_documents_bytes() -> None:
    manifest, _ = _payloads()
    raw = (_SNAPSHOT_DIR / SERVICE_SNAPSHOT_DOCUMENTS_FILE).read_bytes()
    canonical_files = {
        name: (_SNAPSHOT_DIR / name).read_bytes()
        for name in (
            "manifest.json",
            SERVICE_SNAPSHOT_DOCUMENTS_FILE,
            SERVICE_SNAPSHOT_COVERAGE_FILE,
            SERVICE_SNAPSHOT_PERMISSION_FILE,
        )
    }

    assert hashlib.sha256(raw).hexdigest() == manifest["documents_sha256"]
    assert (
        (_SNAPSHOT_DIR / SERVICE_SNAPSHOT_CHECKSUM_FILE).read_bytes()
        == build_snapshot_checksum(canonical_files)
    )
    assert len(manifest["source_artifacts"]) == 9
    assert all(
        len(item["sha256"]) == 64 for item in manifest["source_artifacts"]
    )


def test_canonical_files_are_compact_utf8_lf_and_validation_passes() -> None:
    canonical_names = (
        "manifest.json",
        SERVICE_SNAPSHOT_DOCUMENTS_FILE,
        SERVICE_SNAPSHOT_COVERAGE_FILE,
        SERVICE_SNAPSHOT_PERMISSION_FILE,
        SERVICE_SNAPSHOT_VALIDATION_FILE,
    )
    for name in canonical_names:
        raw = (_SNAPSHOT_DIR / name).read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf")
        assert raw.endswith(b"\n")
        assert b"\r\n" not in raw
        assert b"\n " not in raw
        assert json.loads(raw.decode("utf-8"))
    report = json.loads(
        (_SNAPSHOT_DIR / SERVICE_SNAPSHOT_VALIDATION_FILE).read_text(
            encoding="utf-8"
        )
    )
    assert report["status"] == "PASS"
    assert report["document_count"] == 54
    assert all(report["checks"].values())


def test_canonical_snapshot_excludes_raw_source_content_and_local_paths() -> None:
    snapshot = load_service_snapshot()
    serialized = (_SNAPSHOT_DIR / "documents.json").read_text(
        encoding="utf-8"
    )

    for forbidden in (
        "evidence_excerpt",
        "verification_excerpt",
        "raw_text",
        "source_file",
        "source_pdf",
        "pdf_bytes",
        "viewer_pdf_url",
        "C:\\",
        "Downloads",
    ):
        assert forbidden not in serialized
    news = [item for item in snapshot.documents if item.source_type == "news"]
    assert len(news) == 15
    assert all(
        item.metadata["summary_kind"] == "project_owned_short_summary"
        and item.locator["section"] == "Questock short summary"
        for item in news
    )
    reports = [
        item
        for item in snapshot.documents
        if item.source_type == "research_report"
    ]
    assert all(
        item.metadata["usage_review_status"] == "approved"
        and item.metadata["corpus_ingest_allowed"] is True
        and item.metadata["external_llm_processing_allowed"] is False
        for item in reports
    )


def test_disclosure_receipts_facts_and_report_locators_are_complete() -> None:
    snapshot = load_service_snapshot()
    disclosures = [
        item
        for item in snapshot.documents
        if item.source_type == "disclosure"
    ]
    assert {
        item.locator["receipt_no"] for item in disclosures
    } == {
        "20260515002181",
        "20260515002287",
        "20260515002418",
    }
    assert all(
        len(item.locator["facts"]) >= 10
        and all(
            fact["physical_pdf_page"] >= 1
            and fact["dart_printed_page"] >= 1
            and fact["section_path"]
            for fact in item.locator["facts"]
        )
        for item in disclosures
    )
    reports = [
        item
        for item in snapshot.documents
        if item.source_type == "research_report"
    ]
    assert all(
        item.locator["page"] >= 1 and item.locator["section"]
        for item in reports
    )


def test_checksum_mismatch_fails_typed() -> None:
    manifest, documents = _payloads()
    manifest["documents_sha256"] = "0" * 64

    with pytest.raises(ServiceSnapshotValidationError):
        build_service_snapshot(manifest, documents)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda documents: documents["documents"][0].__setitem__(
            "published_at", "2026-07-24T05:03:00Z"
        ),
        lambda documents: documents["documents"][0].__setitem__(
            "source_url", "C:\\private\\news.json"
        ),
        lambda documents: documents["documents"][0]["metadata"].__setitem__(
            "raw", "source body"
        ),
        lambda documents: documents["documents"][5]["locator"].__setitem__(
            "receipt_no", "20260515000000"
        ),
        lambda documents: documents["documents"][6]["locator"].__setitem__(
            "page", 999
        ),
        lambda documents: documents["documents"][6]["metadata"].__setitem__(
            "external_llm_processing_allowed", True
        ),
    ],
)
def test_cutoff_url_raw_receipt_page_and_permission_mutations_fail(
    mutation,
) -> None:
    manifest, documents = _payloads()
    mutation(documents)
    raw = _rehash(manifest, documents)

    with pytest.raises(ServiceSnapshotValidationError):
        build_service_snapshot(manifest, documents, documents_bytes=raw)


def test_duplicate_document_id_fails_even_with_recomputed_checksum() -> None:
    manifest, documents = _payloads()
    duplicate = documents["documents"][0]["document_id"]
    documents["documents"][1]["document_id"] = duplicate
    manifest["document_ids"][1] = duplicate
    raw = _rehash(manifest, documents)

    with pytest.raises(ServiceSnapshotValidationError):
        build_service_snapshot(manifest, documents, documents_bytes=raw)


def test_unknown_snapshot_id_and_loader_error_are_sanitized(tmp_path: Path) -> None:
    sentinel = "C:\\private\\snapshot"

    with pytest.raises(ServiceSnapshotValidationError) as exc_info:
        load_service_snapshot(sentinel, root=tmp_path)

    assert sentinel not in str(exc_info.value)
    assert str(tmp_path) not in str(exc_info.value)


def test_snapshot_gateway_filters_company_and_returns_deep_copies() -> None:
    snapshot = load_service_snapshot()
    gateway = RecordedServiceSnapshotGateway(snapshot)
    security = SecurityIdentifier(
        market="KRX",
        ticker="005930",
        security_name="삼성전자",
        security_type="common_stock",
        corp_code=None,
        corp_name="삼성전자",
    )
    plan = QueryPlan(
        security=security,
        intent="multi_source_summary",
        date_range=None,
        required_sources=["news", "disclosure", "research_report"],
        required_evidence=[],
        requires_clarification=False,
    )

    first = asyncio.run(
        gateway.fetch(plan, query="삼성전자 요약", timeout_seconds=1)
    )
    first.documents[0].metadata["mutated"] = True
    second = asyncio.run(
        gateway.fetch(plan, query="삼성전자 요약", timeout_seconds=1)
    )

    assert len(second.documents) == 18
    assert {item.source_type for item in second.documents} == {
        "news",
        "disclosure",
        "research_report",
    }
    assert all(
        item.primary_security_ids == ["KRX:005930"]
        for item in second.documents
    )
    assert all("mutated" not in item.metadata for item in second.documents)
    assert all(
        result.status == "ok"
        for result in second.provider_results_by_source.values()
    )


def test_snapshot_dates_are_not_after_fixed_basis() -> None:
    snapshot = load_service_snapshot()

    assert snapshot.basis_at.date() == date(2026, 7, 24)
    assert all(
        item.published_at is not None
        and item.published_at <= snapshot.basis_at
        for item in snapshot.documents
    )


def test_snapshot_copy_preserves_source_artifact_hashes_and_rejects_bad_type() -> None:
    snapshot = load_service_snapshot()
    copied = copy_service_snapshot(snapshot)

    assert copied.source_artifacts == snapshot.source_artifacts
    assert all(item["sha256"] != "0" * 64 for item in copied.source_artifacts)
    with pytest.raises(ServiceSnapshotValidationError):
        copy_service_snapshot(replace(snapshot, source_artifacts=()))
