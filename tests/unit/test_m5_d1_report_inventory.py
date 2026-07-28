from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.services.m5_d1_report_inventory import (
    M5D1ReportInventoryError,
    build_report_inventory_payload,
    validate_report_inventory_payload,
)
from scripts.prepare_m5_d1_reports import (
    M5D1ReportPreparationError,
    prepare_report_inventory,
)


def test_report_inventory_selects_all_reports_through_cutoff_and_excludes_source_text() -> None:
    payload = build_report_inventory_payload(
        [
            _raw_report(
                published_date="2026-07-13",
                title=(
                    "ETP Weekly Insight-SK하이닉스 ADR 단일종목 "
                    "레버리지 ETF"
                ),
                pdf_sha256="1" * 64,
            ),
            _raw_report(
                published_date="2026-06-25",
                title="SK하이닉스 ADR, 7월 나스닥 입성",
                pdf_sha256="2" * 64,
            ),
        ],
        prepared_at=datetime(2026, 7, 28, tzinfo=UTC),
        visual_review_confirmed=True,
    )

    validate_report_inventory_payload(payload)

    assert payload["coverage"] == {
        "discovered_count": 2,
        "selected_count": 2,
        "excluded_count": 0,
        "selected_by_security": {"KRX:000660": 2},
        "selected_by_publisher": {"삼성증권": 2},
        "extraction_status_counts": {"text_extracted": 2},
        "visual_review_confirmed": True,
        "runtime_ready_count": 0,
    }
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "source body must stay local" not in serialized
    assert '"page_text":' not in serialized
    assert "C:\\" not in serialized
    assert all(
        report["permissions"]["corpus_ingest_allowed"] is False
        for report in payload["reports"]
    )
    assert all(
        report["permissions"]["external_llm_processing_allowed"] is False
        for report in payload["reports"]
    )


def test_report_inventory_rejects_unapproved_source_host() -> None:
    raw = _raw_report(
        published_date="2026-07-13",
        title="SK하이닉스 리포트",
        pdf_sha256="1" * 64,
    )
    raw["source_url"] = "https://example.test/report.pdf"

    with pytest.raises(M5D1ReportInventoryError):
        build_report_inventory_payload(
            [raw],
            prepared_at=datetime(2026, 7, 28, tzinfo=UTC),
            visual_review_confirmed=True,
        )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda payload: payload["reports"][0].__setitem__(
            "pdf_sha256",
            "bad",
        ),
        lambda payload: payload["reports"][0].__setitem__(
            "source_url",
            "https://example.test/report.pdf",
        ),
        lambda payload: payload["reports"][0].__setitem__(
            "ticker",
            "005930",
        ),
        lambda payload: payload["reports"][0].__setitem__(
            "report_scope",
            "company_specific",
        ),
        lambda payload: payload["reports"][0].__setitem__(
            "publisher",
            "미래에셋증권",
        ),
    ],
)
def test_saved_report_inventory_revalidates_derived_contract(
    mutation,
) -> None:
    payload = build_report_inventory_payload(
        [
            _raw_report(
                published_date="2026-07-13",
                title="ETP Weekly Insight-SK하이닉스 ADR",
                pdf_sha256="1" * 64,
            )
        ],
        prepared_at=datetime(2026, 7, 28, tzinfo=UTC),
        visual_review_confirmed=True,
    )
    changed = deepcopy(payload)
    mutation(changed)

    with pytest.raises(M5D1ReportInventoryError):
        validate_report_inventory_payload(changed)


def test_report_preparation_writes_public_and_local_layers(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "source"
    ticker_dir = source_root / "000660"
    ticker_dir.mkdir(parents=True)
    july_stem = (
        "20260713_삼성증권_(한수진) ETP Weekly Insight-"
        "SK하이닉스 ADR 단일종목 레버리지 ETF"
    )
    june_stem = (
        "20260625_삼성증권_(이종욱)SK하이닉스(000660_BUY)-"
        "SK하이닉스 ADR, 7월 나스닥 입성"
    )
    (ticker_dir / f"{july_stem}.pdf").write_bytes(b"july-pdf")
    (ticker_dir / f"{june_stem}.pdf").write_bytes(b"june-pdf")
    (ticker_dir / "sources.txt").write_text(
        "\n".join(
            (
                f"{july_stem} : https://www.samsungpop.com/july.pdf",
                f"{june_stem} : https://www.samsungpop.com/june.pdf",
            )
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "inventory.json"
    local_extract_root = tmp_path / "extracts"

    payload = prepare_report_inventory(
        source_root=source_root,
        local_extract_root=local_extract_root,
        output_path=output_path,
        visual_review_confirmed=True,
        page_extractor=lambda _path: (
            "SK하이닉스 000660 source body must stay local",
            "second source page",
        ),
        prepared_at=datetime(2026, 7, 28, tzinfo=UTC),
    )

    assert payload["coverage"]["selected_count"] == 2
    assert output_path.exists()
    assert len(tuple(local_extract_root.glob("*.json"))) == 2
    assert "source body must stay local" not in output_path.read_text(
        encoding="utf-8"
    )
    assert any(
        "source body must stay local" in path.read_text(encoding="utf-8")
        for path in local_extract_root.glob("*.json")
    )


def test_report_preparation_rejects_source_map_mismatch(
    tmp_path: Path,
) -> None:
    ticker_dir = tmp_path / "000660"
    ticker_dir.mkdir()
    filename = (
        "20260713_삼성증권_(한수진)SK하이닉스(000660_BUY)-리포트.pdf"
    )
    (ticker_dir / filename).write_bytes(b"pdf")
    (ticker_dir / "sources.txt").write_text(
        "wrong : https://www.samsungpop.com/report.pdf\n",
        encoding="utf-8",
    )

    with pytest.raises(M5D1ReportPreparationError):
        prepare_report_inventory(
            source_root=tmp_path,
            local_extract_root=tmp_path / "extracts",
            output_path=tmp_path / "inventory.json",
            visual_review_confirmed=True,
            page_extractor=lambda _path: ("SK하이닉스 000660",),
            prepared_at=datetime(2026, 7, 28, tzinfo=UTC),
        )


def test_report_inventory_accepts_image_only_pdf_after_visual_review() -> None:
    raw = _raw_report(
        published_date="2026-07-13",
        title="SK하이닉스 급락 코멘트",
        pdf_sha256="3" * 64,
    )
    raw["publisher"] = "미래에셋증권"
    raw["source_url"] = (
        "https://securities.miraeasset.com/report.pdf"
    )
    raw["page_texts"] = ("", "")

    payload = build_report_inventory_payload(
        [raw],
        prepared_at=datetime(2026, 7, 28, tzinfo=UTC),
        visual_review_confirmed=True,
    )

    report = payload["reports"][0]
    assert report["extraction_status"] == (
        "image_only_visual_review_required"
    )
    assert report["extracted_nonempty_page_count"] == 0
    assert report["page_text_checksums"] == []


def test_report_preparation_accepts_multiple_publishers_and_short_date(
    tmp_path: Path,
) -> None:
    ticker_dir = tmp_path / "005930"
    ticker_dir.mkdir()
    stems = (
        (
            "260708_키움증권_(박유악)"
            "삼성전자(005930_BUY)-하반기 전망"
        ),
        (
            "20260707_미래에셋증권_(김영건)"
            "삼성전자(005930_매수)-주가 반응 점검"
        ),
    )
    for stem in stems:
        (ticker_dir / f"{stem}.pdf").write_bytes(stem.encode("utf-8"))
    (ticker_dir / "sources.txt").write_text(
        "\n".join(
            (
                f"{stems[0]} : https://bbn.kiwoom.com/rfCR12174",
                (
                    f"{stems[1]} : "
                    "https://securities.miraeasset.com/report.pdf"
                ),
            )
        ),
        encoding="utf-8",
    )

    payload = prepare_report_inventory(
        source_root=tmp_path,
        local_extract_root=tmp_path / "extracts",
        output_path=tmp_path / "inventory.json",
        visual_review_confirmed=True,
        page_extractor=lambda _path: ("삼성전자 005930",),
        prepared_at=datetime(2026, 7, 28, tzinfo=UTC),
    )

    assert payload["coverage"]["selected_by_publisher"] == {
        "미래에셋증권": 1,
        "키움증권": 1,
    }
    assert {
        report["published_date"] for report in payload["reports"]
    } == {"2026-07-07", "2026-07-08"}


def _raw_report(
    *,
    published_date: str,
    title: str,
    pdf_sha256: str,
) -> dict[str, object]:
    return {
        "security_id": "KRX:000660",
        "ticker": "000660",
        "security_name": "SK하이닉스",
        "publisher": "삼성증권",
        "analyst": "테스트",
        "title": title,
        "published_date": published_date,
        "source_url": "https://www.samsungpop.com/report.pdf",
        "pdf_sha256": pdf_sha256,
        "page_texts": (
            "SK하이닉스 000660 source body must stay local",
            "second source page",
        ),
    }
