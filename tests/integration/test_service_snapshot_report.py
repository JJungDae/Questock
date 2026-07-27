from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from app.core.models import FinancialDocument
from app.services.report_snapshot_schema import (
    REPORT_INPUT_SPECS,
    REPORT_SNAPSHOT_SCHEMA_VERSION,
    ReportInputSpec,
    ReportSnapshotValidationError,
    build_report_snapshot_payload,
    load_report_extract,
    validate_report_snapshot_payload,
)
from scripts.curate_report_snapshot import (
    ReportSnapshotCurationError,
    run_curation,
)


def _sha256(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _fixture(
    original_spec: ReportInputSpec,
) -> tuple[ReportInputSpec, dict[str, object], bytes, bytes]:
    pdf_bytes = f"%PDF-1.7\nfixture-{original_spec.ticker}".encode()
    segments = []
    segment_specs = []
    for segment in original_spec.segments:
        if segment.segment_id == "samsung-report-004":
            input_summary = (
                "메모리 사업은 DRAM 출하량 +4%, NAND 출하량 -3%로 "
                "추정됐다."
            )
            output_summary = segment.summary_override
        elif segment.segment_id == "skhynix-report-008":
            input_summary = (
                "컨벤셔널 메모리 가격과 HBM1 가격이 2027년 실적을 "
                "지지한다고 봤다."
            )
            output_summary = segment.summary_override
        else:
            input_summary = (
                f"{original_spec.publisher}의 {segment.segment_id} 검증 요약이며 "
                "2026년 수치를 포함한다."
            )
            output_summary = input_summary
        assert output_summary is not None
        segment_specs.append(
            replace(segment, summary_sha256=_sha256(output_summary))
        )
        segments.append(
            {
                "segment_id": segment.segment_id,
                "type": segment.segment_type,
                "summary": input_summary,
                "page": segment.page,
                "evidence_excerpt": "source excerpt must not enter output",
                "confidence": segment.confidence,
                "notes": ["source-side note must not enter output"],
            }
        )
    extract: dict[str, object] = {
        "schema_version": "fsc-research-report-extract-v1",
        "document_type": "research_report",
        "identity": {
            "company_name": original_spec.input_company_name,
            "ticker": original_spec.ticker,
            "report_title": original_spec.title,
            "issuer": original_spec.publisher,
            "analyst": original_spec.analyst,
            "published_at": original_spec.published_at,
            "source_file": f"{original_spec.ticker}.pdf",
            "web_page_url": original_spec.source_url,
            "viewer_pdf_url": "https://example.invalid/source.pdf",
            "identity_status": "verified_from_pdf_and_user_supplied_links",
        },
        "recommendation": original_spec.recommendation.as_payload(),
        "segments": segments,
        "coverage": {"segment_count": len(segments)},
    }
    extract_bytes = json.dumps(
        extract,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ).encode("utf-8")
    spec = replace(
        original_spec,
        extract_sha256=_sha256(extract_bytes),
        pdf_sha256=_sha256(pdf_bytes),
        segments=tuple(segment_specs),
    )
    return spec, extract, extract_bytes, pdf_bytes


def _payload(
    original_spec: ReportInputSpec,
) -> tuple[ReportInputSpec, dict[str, object], bytes]:
    spec, extract, _, pdf_bytes = _fixture(original_spec)
    payload = build_report_snapshot_payload(
        extract,
        spec=spec,
        source_pdf_bytes=pdf_bytes,
        source_extract_sha256=spec.extract_sha256,
        observed_pdf_page_count=spec.pdf_page_count,
    )
    return spec, payload, pdf_bytes


def test_three_company_report_corpus_uses_verified_m1_06_documents() -> None:
    observed_security_ids = []
    for original_spec in REPORT_INPUT_SPECS:
        spec, payload, _ = _payload(original_spec)
        documents = validate_report_snapshot_payload(payload, spec=spec)
        observed_security_ids.append(payload["security_id"])

        assert payload["schema_version"] == REPORT_SNAPSHOT_SCHEMA_VERSION
        assert payload["source_integrity"]["hash_verification_status"] == (
            "verified"
        )
        assert payload["source_integrity"]["manual_verification_status"] == (
            "verified_against_source"
        )
        assert payload["permissions"] == {
            "usage_review_status": "approved",
            "corpus_ingest_allowed": True,
            "external_llm_processing_allowed": False,
            "human_owner_confirmed_at": "2026-07-27",
            "allowed_content": (
                "metadata_verified_structured_facts_and_questock_short_summaries"
            ),
            "source_pdf_runtime": "excluded",
            "source_excerpt_runtime": "excluded",
            "external_llm_source_processing": "prohibited",
        }
        assert payload["coverage"]["document_count"] == 12
        assert payload["coverage"]["verified_section_count"] == 12
        assert payload["coverage"]["ready"] is True
        assert len(documents) == 12
        assert all(item.source_type == "research_report" for item in documents)
        assert all(item.provider == "manual_manifest" for item in documents)
        assert all(
            item.metadata["external_llm_processing_allowed"] is False
            for item in documents
        )
        assert all(item.locator["page"] >= 1 for item in documents)
        assert all(item.locator["section"] for item in documents)

    assert observed_security_ids == [
        "KRX:005930",
        "KRX:000660",
        "KRX:005380",
    ]


def test_output_excludes_pdf_raw_text_excerpt_and_local_source_path() -> None:
    spec, payload, _ = _payload(REPORT_INPUT_SPECS[0])
    validate_report_snapshot_payload(payload, spec=spec)
    serialized = json.dumps(payload, ensure_ascii=False)

    assert "evidence_excerpt" not in serialized
    assert "source excerpt must not enter output" not in serialized
    assert "source-side note must not enter output" not in serialized
    assert "source_file" not in serialized
    assert "viewer_pdf_url" not in serialized
    assert "raw_text" not in serialized
    assert "%PDF-" not in serialized
    assert "Downloads" not in serialized
    assert "C:\\" not in serialized


def test_verified_summary_corrections_follow_official_pdf() -> None:
    samsung_spec, samsung_payload, _ = _payload(REPORT_INPUT_SPECS[0])
    samsung_documents = validate_report_snapshot_payload(
        samsung_payload,
        spec=samsung_spec,
    )
    samsung_summary = next(
        item.text
        for item in samsung_documents
        if item.document_id.endswith(":samsung-report-004")
    )
    assert "NAND 출하량 +3%" in samsung_summary
    assert "NAND 출하량 -3%" not in samsung_summary

    hynix_spec, hynix_payload, _ = _payload(REPORT_INPUT_SPECS[1])
    hynix_documents = validate_report_snapshot_payload(
        hynix_payload,
        spec=hynix_spec,
    )
    hynix_summary = next(
        item.text
        for item in hynix_documents
        if item.document_id.endswith(":skhynix-report-008")
    )
    assert "HBM 가격" in hynix_summary
    assert "HBM1" not in hynix_summary


def test_hyundai_publication_date_uses_pdf_date_not_source_filename() -> None:
    spec, payload, _ = _payload(REPORT_INPUT_SPECS[2])
    documents = validate_report_snapshot_payload(payload, spec=spec)

    assert payload["report_metadata"]["published_at"] == "2026-07-24"
    assert all(
        item.published_at is not None
        and item.published_at.isoformat() == "2026-07-23T15:00:00+00:00"
        for item in documents
    )


def test_recommendation_remains_publisher_attributed_not_questock_opinion() -> None:
    spec, payload, _ = _payload(REPORT_INPUT_SPECS[0])
    validate_report_snapshot_payload(payload, spec=spec)
    metadata = payload["report_metadata"]

    assert metadata["recommendation_owner"] == "미래에셋증권"
    assert metadata["questock_investment_opinion"] is False
    assert metadata["recommendation"]["investment_opinion"] == "매수"
    assert metadata["recommendation"]["target_price"] == 550000
    assert metadata["recommendation"]["attribution"].startswith("미래에셋증권")


@pytest.mark.parametrize(
    "mutation",
    [
        lambda payload: payload["coverage"].__setitem__("document_count", 11),
        lambda payload: payload["permissions"].__setitem__(
            "external_llm_processing_allowed", True
        ),
        lambda payload: payload["source_integrity"].__setitem__(
            "pdf_sha256", "0" * 64
        ),
        lambda payload: payload["documents"][0].__setitem__("text", "changed"),
        lambda payload: payload["documents"][0]["locator"].__setitem__(
            "page", 999
        ),
        lambda payload: payload["report_metadata"].__setitem__(
            "source_url", "C:\\private\\report.pdf"
        ),
    ],
)
def test_saved_payload_is_recomputed_instead_of_trusting_fields(
    mutation,
) -> None:
    spec, payload, _ = _payload(REPORT_INPUT_SPECS[0])
    mutation(payload)

    with pytest.raises(ReportSnapshotValidationError):
        validate_report_snapshot_payload(payload, spec=spec)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda extract: extract["identity"].__setitem__("ticker", "999999"),
        lambda extract: extract["identity"].__setitem__(
            "report_title", "different"
        ),
        lambda extract: extract["identity"].__setitem__(
            "published_at", "2026-07-25"
        ),
        lambda extract: extract["segments"][0].__setitem__("page", 999),
        lambda extract: extract["segments"][0].__setitem__(
            "summary", "unapproved"
        ),
        lambda extract: extract["segments"].append(
            deepcopy(extract["segments"][0])
        ),
    ],
)
def test_identity_locator_summary_and_exact_set_fail_typed(mutation) -> None:
    spec, extract, _, pdf_bytes = _fixture(REPORT_INPUT_SPECS[0])
    mutation(extract)

    with pytest.raises(ReportSnapshotValidationError):
        build_report_snapshot_payload(
            extract,
            spec=spec,
            source_pdf_bytes=pdf_bytes,
            source_extract_sha256=spec.extract_sha256,
            observed_pdf_page_count=spec.pdf_page_count,
        )


def test_pdf_hash_page_count_extract_hash_and_cutoff_are_gates() -> None:
    spec, extract, _, pdf_bytes = _fixture(REPORT_INPUT_SPECS[0])
    calls = [
        {
            "source_pdf_bytes": b"%PDF-1.7\nwrong",
            "source_extract_sha256": spec.extract_sha256,
            "observed_pdf_page_count": spec.pdf_page_count,
            "as_of_date": date(2026, 7, 24),
        },
        {
            "source_pdf_bytes": pdf_bytes,
            "source_extract_sha256": "0" * 64,
            "observed_pdf_page_count": spec.pdf_page_count,
            "as_of_date": date(2026, 7, 24),
        },
        {
            "source_pdf_bytes": pdf_bytes,
            "source_extract_sha256": spec.extract_sha256,
            "observed_pdf_page_count": spec.pdf_page_count + 1,
            "as_of_date": date(2026, 7, 24),
        },
        {
            "source_pdf_bytes": pdf_bytes,
            "source_extract_sha256": spec.extract_sha256,
            "observed_pdf_page_count": spec.pdf_page_count,
            "as_of_date": date(2026, 7, 6),
        },
    ]
    for kwargs in calls:
        with pytest.raises(ReportSnapshotValidationError):
            build_report_snapshot_payload(extract, spec=spec, **kwargs)


def test_financial_document_json_round_trip_preserves_corpus_contract() -> None:
    spec, payload, _ = _payload(REPORT_INPUT_SPECS[1])
    documents = validate_report_snapshot_payload(payload, spec=spec)

    round_tripped = tuple(
        FinancialDocument.model_validate(item.model_dump(mode="json"))
        for item in documents
    )

    assert round_tripped == documents
    assert len({item.document_id for item in round_tripped}) == 12


def test_run_curation_writes_three_byte_identical_ignored_outputs(
    tmp_path: Path,
) -> None:
    input_dirs = {}
    specs = []
    source_pdf_dir = tmp_path / "source"
    source_pdf_dir.mkdir()
    page_counts = {}
    for original_spec in REPORT_INPUT_SPECS:
        spec, extract, extract_bytes, pdf_bytes = _fixture(original_spec)
        input_dir = tmp_path / f"input-{spec.ticker}"
        input_dir.mkdir()
        (input_dir / spec.input_extract_filename).write_bytes(extract_bytes)
        (source_pdf_dir / f"{spec.ticker}.pdf").write_bytes(pdf_bytes)
        input_dirs[spec.security_id] = input_dir
        page_counts[spec.ticker] = spec.pdf_page_count
        specs.append(spec)
        assert load_report_extract(
            input_dir / spec.input_extract_filename
        ) == extract

    first_output = tmp_path / "first"
    second_output = tmp_path / "second"

    def page_counter(path: Path) -> int:
        return page_counts[path.stem]

    first = run_curation(
        input_dirs=input_dirs,
        source_pdf_dir=source_pdf_dir,
        output_dir=first_output,
        page_counter=page_counter,
        specs=tuple(specs),
    )
    second = run_curation(
        input_dirs=input_dirs,
        source_pdf_dir=source_pdf_dir,
        output_dir=second_output,
        page_counter=page_counter,
        specs=tuple(specs),
    )

    assert first == second
    assert all(item["document_count"] == 12 for item in first)
    assert all(item["ready"] is True for item in first)
    assert all(
        item["external_llm_processing_allowed"] is False for item in first
    )
    for spec in specs:
        name = f"report_snapshot_curated_{spec.ticker}.json"
        assert (first_output / name).read_bytes() == (
            second_output / name
        ).read_bytes()


def test_loader_and_curator_errors_are_sanitized(tmp_path: Path) -> None:
    sentinel = "C:\\private\\sentinel-report.json"
    invalid = tmp_path / "invalid.json"
    invalid.write_text(f'{{"secret": "{sentinel}"', encoding="utf-8")

    with pytest.raises(ReportSnapshotValidationError) as exc_info:
        load_report_extract(invalid)
    assert sentinel not in str(exc_info.value)
    assert str(invalid) not in str(exc_info.value)

    with pytest.raises(ReportSnapshotCurationError) as curation_error:
        run_curation(
            input_dirs={},
            source_pdf_dir=tmp_path,
            output_dir=tmp_path / "out",
        )
    assert sentinel not in str(curation_error.value)
    assert str(tmp_path) not in str(curation_error.value)
