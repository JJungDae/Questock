from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.disclosure_snapshot_schema import (
    DISCLOSURE_INPUT_SPECS,
    DISCLOSURE_SNAPSHOT_SCHEMA_VERSION,
    DisclosureCorrectionVerification,
    DisclosureSnapshotValidationError,
    build_disclosure_snapshot_payload,
    validate_disclosure_snapshot_payload,
)
from scripts.curate_disclosure_snapshot import (
    CORRECTION_PENDING_EXIT,
    DisclosureSnapshotCurationError,
    build_curation_result,
    run_curation,
    verify_dart_viewer_correction_state,
    verify_opendart_correction_state,
)

REQUIRED_CATEGORIES = (
    "consolidated_revenue",
    "consolidated_operating_profit",
    "net_income_or_equivalent",
    "major_segment_revenue",
    "major_segment_profit",
    "production_or_sales",
    "capex",
    "research_and_development",
    "financial_position_or_cashflow_or_debt",
    "risk_or_uncertainty",
)


def _matrix(spec, *, conflicting_segment: bool = False) -> dict[str, object]:
    facts = []
    categories = (*REQUIRED_CATEGORIES, "major_product_or_technology", "capex")
    for index, category in enumerate(categories, start=1):
        conflict = conflicting_segment and category == "major_segment_revenue"
        facts.append(
            {
                "fact_id": f"{spec.ticker}-disc-{index:03d}",
                "category": category,
                "claim": f"{spec.security_name} 공개 fact {index}",
                "value": str(index * 100),
                "unit": "백만원",
                "period": "2026년 1분기",
                "physical_pdf_page": min(index + 3, spec.pdf_page_count),
                "printed_page": index,
                "section_path": ["III. 재무에 관한 사항", f"section {index}"],
                "confidence": "medium" if conflict else "high",
                "verification_status": (
                    "verified_against_source_with_conflict_note"
                    if conflict
                    else "verified_against_source"
                ),
                "basis": (
                    "차량부문 외부고객 매출"
                    if conflict
                    else "연결 공시 기준"
                ),
                "notes": (
                    ["다른 표의 순매출액과 정의가 달라 직접 비교에 주의한다."]
                    if conflict
                    else []
                ),
                "verification_excerpt": "must never enter canonical output",
            }
        )
    return {
        "schema_version": "input-v1",
        "identity": {
            "company_name": spec.matrix_company_name,
            "ticker": "not_found",
            "corp_code": "not_found",
            "report_name": spec.report_name,
            "report_period": "2026-01-01~2026-03-31",
            "submitted_at": "2026-05-15",
            "receipt_no": spec.receipt_no,
            "official_url": spec.viewer_url,
            "identity_status": "verified_from_pdf",
        },
        "document_contract": {
            "one_receipt_one_document": True,
            "content_level": "verified_body_facts",
        },
        "coverage": {
            "verified_fact_count": 999,
            "required_categories": [],
        },
        "facts": facts,
        "uncertain_items": [
            {"field": "ticker", "status": "not_found"},
            {"item": "corp_code", "status": "not_found"},
        ],
    }


def _correction(spec, remark: str = "유") -> DisclosureCorrectionVerification:
    return DisclosureCorrectionVerification(
        receipt_no=spec.receipt_no,
        status="verified_official_api",
        remark=remark,
        report_name="분기보고서 (2026.03)",
    )


def _payload(spec, *, matrix=None, correction=None):
    return build_disclosure_snapshot_payload(
        matrix or _matrix(spec),
        spec=spec,
        source_pdf_sha256="a" * 64,
        source_matrix_sha256="b" * 64,
        observed_pdf_page_count=spec.pdf_page_count,
        correction=correction or _correction(spec),
    )


def test_three_company_snapshots_recompute_coverage_and_keep_one_receipt() -> None:
    documents = []
    for spec in DISCLOSURE_INPUT_SPECS:
        payload = _payload(
            spec,
            matrix=_matrix(
                spec,
                conflicting_segment=spec.security_id == "KRX:005380",
            ),
        )
        document = validate_disclosure_snapshot_payload(payload, spec=spec)
        documents.append(document)

        assert payload["schema_version"] == DISCLOSURE_SNAPSHOT_SCHEMA_VERSION
        assert payload["coverage"]["fact_count"] == 12
        assert payload["coverage"]["missing_categories"] == []
        assert payload["coverage"]["ready"] is True
        assert payload["identity"]["ticker_source"] == "project_security_mapping"
        assert payload["identity"]["corp_code_verification_status"] == "candidate"
        assert document.document_id == f"disclosure:{spec.receipt_no}"
        assert document.locator["receipt_no"] == spec.receipt_no
        assert document.locator["viewer_url"] == spec.viewer_url
        assert len(document.locator["facts"]) == 12

    assert len(documents) == 3
    assert len({item.document_id for item in documents}) == 3


def test_output_excludes_excerpt_local_path_and_source_file() -> None:
    spec = DISCLOSURE_INPUT_SPECS[0]
    serialized = json.dumps(_payload(spec), ensure_ascii=False)

    assert "verification_excerpt" not in serialized
    assert "must never enter canonical output" not in serialized
    assert "source_file" not in serialized
    assert "Downloads" not in serialized
    assert "C:\\" not in serialized


def test_hyundai_conflict_basis_and_note_are_preserved_without_mixing() -> None:
    spec = DISCLOSURE_INPUT_SPECS[2]
    payload = _payload(spec, matrix=_matrix(spec, conflicting_segment=True))
    facts = payload["document"]["locator"]["facts"]
    segment = next(
        item for item in facts if item["category"] == "major_segment_revenue"
    )

    assert segment["value"] == "400"
    assert segment["basis"] == "차량부문 외부고객 매출"
    assert segment["verification_status"] == (
        "verified_against_source_with_conflict_note"
    )
    assert segment["notes"] == [
        "다른 표의 순매출액과 정의가 달라 직접 비교에 주의한다."
    ]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda payload: payload["coverage"].__setitem__("fact_count", 999),
        lambda payload: payload["coverage"].__setitem__(
            "observed_categories", []
        ),
        lambda payload: payload["document"]["locator"]["facts"][0].__setitem__(
            "category", "risk_or_uncertainty"
        ),
        lambda payload: payload["document"].__setitem__("text", "changed"),
        lambda payload: payload["correction"].__setitem__(
            "has_subsequent_correction", True
        ),
    ],
)
def test_saved_payload_is_recomputed_instead_of_trusting_manifest_fields(
    mutation,
) -> None:
    spec = DISCLOSURE_INPUT_SPECS[0]
    payload = _payload(spec)
    mutation(payload)

    with pytest.raises(DisclosureSnapshotValidationError):
        validate_disclosure_snapshot_payload(payload, spec=spec)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda matrix, spec: matrix["identity"].__setitem__(
            "receipt_no", "20260515000000"
        ),
        lambda matrix, spec: matrix["identity"].__setitem__(
            "company_name", "다른 회사"
        ),
        lambda matrix, spec: matrix["facts"][0].__setitem__(
            "physical_pdf_page", spec.pdf_page_count + 1
        ),
        lambda matrix, spec: matrix.__setitem__(
            "facts",
            [
                item
                for item in matrix["facts"]
                if item["category"] != "risk_or_uncertainty"
            ],
        ),
    ],
)
def test_identity_page_bounds_and_required_categories_fail_typed(
    mutation,
) -> None:
    spec = DISCLOSURE_INPUT_SPECS[0]
    matrix = _matrix(spec)
    mutation(matrix, spec)

    with pytest.raises(DisclosureSnapshotValidationError):
        _payload(spec, matrix=matrix)


@pytest.mark.parametrize(
    ("remark", "subsequent", "withdrawn"),
    [
        ("유", False, False),
        ("정", True, False),
        ("유정", True, False),
        ("유철", False, True),
    ],
)
def test_rm_contract_is_reused_without_forcing_current_item_correction(
    remark: str,
    subsequent: bool,
    withdrawn: bool,
) -> None:
    spec = DISCLOSURE_INPUT_SPECS[0]
    payload = _payload(spec, correction=_correction(spec, remark))

    assert payload["correction"]["is_correction"] is False
    assert payload["correction"]["has_subsequent_correction"] is subsequent
    assert payload["correction"]["is_withdrawn"] is withdrawn


def test_pending_correction_is_explicit_and_blocks_ready_result() -> None:
    spec = DISCLOSURE_INPUT_SPECS[0]
    payload = _payload(
        spec,
        correction=DisclosureCorrectionVerification(
            receipt_no=spec.receipt_no,
            status="pending",
            remark=None,
            report_name=None,
        ),
    )
    assert payload["correction"]["verification_status"] == "pending"
    result, exit_code = build_curation_result(
        [
            {"ready": False},
            {"ready": True},
            {"ready": True},
        ]
    )

    assert exit_code == CORRECTION_PENDING_EXIT
    assert result["status"] == "BLOCKED"
    assert result["reason"] == "correction_verification_pending"


def test_opendart_verifier_requires_exact_receipt_corp_and_stock() -> None:
    spec = DISCLOSURE_INPUT_SPECS[0]

    class FakeTransport:
        def search(self, **kwargs):
            return {
                "status": "000",
                "list": [
                    {
                        "rcept_no": spec.receipt_no,
                        "corp_code": spec.corp_code,
                        "stock_code": spec.ticker,
                        "report_nm": "분기보고서 (2026.03)",
                        "rm": "유",
                    }
                ],
            }

    result = verify_opendart_correction_state(
        spec=spec,
        api_key="configured",
        transport=FakeTransport(),
    )

    assert result == _correction(spec)


def test_opendart_verifier_failure_is_sanitized() -> None:
    spec = DISCLOSURE_INPUT_SPECS[0]
    sentinel = "private-secret-value"

    class FakeTransport:
        def search(self, **kwargs):
            raise DisclosureSnapshotCurationError(sentinel)

    with pytest.raises(DisclosureSnapshotCurationError) as exc_info:
        verify_opendart_correction_state(
            spec=spec,
            api_key=sentinel,
            transport=FakeTransport(),
        )

    assert sentinel not in str(exc_info.value)


def test_official_viewer_fallback_reads_exact_receipt_corp_and_rm_badges() -> None:
    spec = DISCLOSURE_INPUT_SPECS[0]

    class FakeViewerTransport:
        def fetch(self, **kwargs):
            return f"""
            <script>
            node1['text'] = "분 기 보 고 서";
            node1['rcpNo'] = "{spec.receipt_no}";
            </script>
            <div class="nameWrap">
              <span class="tagCom_kospi" title="유가증권시장">유</span>
              <span onclick="openCorpInfoNew('{spec.corp_code}', 'winCorpInfo',
                '/dsae001/selectPopup.ax');">{spec.security_name}</span>
            </div>
            """

    result = verify_dart_viewer_correction_state(
        spec=spec,
        transport=FakeViewerTransport(),
    )

    assert result.status == "verified_official_viewer"
    assert result.remark == "유"
    assert result.report_name == "분기보고서"


def test_run_curation_writes_three_deterministic_ignored_outputs(
    tmp_path: Path,
) -> None:
    input_dirs = {}
    for spec in DISCLOSURE_INPUT_SPECS:
        source_dir = tmp_path / spec.ticker
        source_dir.mkdir()
        (source_dir / f"disclosure_fact_matrix_{spec.ticker}.json").write_text(
            json.dumps(
                _matrix(
                    spec,
                    conflicting_segment=spec.security_id == "KRX:005380",
                ),
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (source_dir / f"{spec.ticker}.pdf").write_bytes(b"%PDF-1.7\nfixture")
        input_dirs[spec.security_id] = source_dir

    class FakeTransport:
        def search(self, *, corp_code, **kwargs):
            spec = next(
                item
                for item in DISCLOSURE_INPUT_SPECS
                if item.corp_code == corp_code
            )
            return {
                "status": "000",
                "list": [
                    {
                        "rcept_no": spec.receipt_no,
                        "corp_code": spec.corp_code,
                        "stock_code": spec.ticker,
                        "report_nm": "분기보고서 (2026.03)",
                        "rm": "유",
                    }
                ],
            }

    page_counts = {
        f"disclosure_{spec.ticker}.pdf": spec.pdf_page_count
        for spec in DISCLOSURE_INPUT_SPECS
    }
    first_output = tmp_path / "first"
    second_output = tmp_path / "second"
    first = run_curation(
        input_dirs=input_dirs,
        output_dir=first_output,
        working_dir=tmp_path / "work-first",
        api_key="configured",
        page_counter=lambda path: page_counts[path.name],
        transport=FakeTransport(),
    )
    second = run_curation(
        input_dirs=input_dirs,
        output_dir=second_output,
        working_dir=tmp_path / "work-second",
        api_key="configured",
        page_counter=lambda path: page_counts[path.name],
        transport=FakeTransport(),
    )

    assert first == second
    assert all(item["document_count"] == 1 for item in first)
    assert all(item["fact_count"] == 12 for item in first)
    assert all(item["ready"] is True for item in first)
    for spec in DISCLOSURE_INPUT_SPECS:
        name = f"disclosure_snapshot_curated_{spec.ticker}.json"
        assert (first_output / name).read_bytes() == (
            second_output / name
        ).read_bytes()
