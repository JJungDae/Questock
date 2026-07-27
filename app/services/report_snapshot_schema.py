from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.core.models import FinancialDocument
from app.ingest.reports import (
    REPORT_INGESTION_VERSION,
    ReportIngestValidationError,
    build_manual_research_documents,
    validate_normalized_report_document,
    validate_report_manifest,
)

REPORT_SNAPSHOT_SCHEMA_VERSION = "service-report-curated-v1"
REPORT_SNAPSHOT_ID = "svc-20260724-1402"
REPORT_SNAPSHOT_AS_OF_DATE = date(2026, 7, 24)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_WINDOWS_ABSOLUTE_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")
_FORBIDDEN_OUTPUT_KEYS = frozenset(
    {
        "evidence_excerpt",
        "verification_excerpt",
        "source_file",
        "viewer_pdf_url",
        "source_pdf",
        "source_pdf_bytes",
        "pdf_bytes",
        "raw",
        "raw_text",
    }
)


class ReportSnapshotValidationError(ValueError):
    """Raised when an FSC report snapshot violates the fixed contract."""


@dataclass(frozen=True)
class ReportRecommendationSpec:
    investment_opinion: str
    target_price: int
    target_price_currency: str
    current_price: int
    current_price_date: str
    upside_pct: float
    attribution: str

    def as_payload(self) -> dict[str, Any]:
        return {
            "investment_opinion": self.investment_opinion,
            "target_price": self.target_price,
            "target_price_currency": self.target_price_currency,
            "current_price": self.current_price,
            "current_price_date": self.current_price_date,
            "upside_pct": self.upside_pct,
            "attribution": self.attribution,
        }


@dataclass(frozen=True)
class ReportSegmentSpec:
    segment_id: str
    segment_type: str
    page: int
    section: str
    confidence: str
    summary_sha256: str
    summary_override: str | None = None


@dataclass(frozen=True)
class ReportInputSpec:
    security_id: str
    ticker: str
    security_name: str
    input_company_name: str
    input_extract_filename: str
    manifest_id: str
    title: str
    publisher: str
    analyst: str
    published_at: str
    source_url: str
    source_asset_id: str
    extract_sha256: str
    pdf_sha256: str
    pdf_page_count: int
    recommendation: ReportRecommendationSpec
    segments: tuple[ReportSegmentSpec, ...]


_SAMSUNG_SEGMENTS = (
    ReportSegmentSpec(
        "samsung-report-001",
        "investment_thesis",
        1,
        "2Q26 잠정실적 당시 기대치 상회",
        "high",
        "5b31b24c198a59b582874c60b6f1817c1ebbe68263e9a8c938df34f3605f914a",
    ),
    ReportSegmentSpec(
        "samsung-report-002",
        "earnings_preliminary",
        1,
        "2Q26 잠정실적 당시 기대치 상회",
        "high",
        "c2756d7a0b1d03eba27ec7ce6b5cf8ccf2bd6470177f14e1624b5dc2b0dc0def",
    ),
    ReportSegmentSpec(
        "samsung-report-003",
        "segment_profit_estimate",
        1,
        "2Q26 잠정실적 당시 기대치 상회",
        "high",
        "8eb347106ba18b1307460d4282590e1e80fa1fe5836ab35ca1d72cea3a1d90f8",
    ),
    ReportSegmentSpec(
        "samsung-report-004",
        "memory_operating_metrics",
        1,
        "2Q26 잠정실적 당시 기대치 상회",
        "high",
        "88e074e2162f6555ad49717c94ac88d4ae7d08d7fc1f3beea94898f6b5226b89",
        (
            "메모리 사업은 DRAM 출하량 +4%, ASP +36%, 영업이익 65.6조원, "
            "NAND 출하량 +3%, ASP +54%, 영업이익 21.4조원으로 추정됐다."
        ),
    ),
    ReportSegmentSpec(
        "samsung-report-005",
        "hbm_outlook",
        1,
        "2Q26 잠정실적 당시 기대치 상회",
        "high",
        "ad0e1ce31359b182319e604770a9fe0b38dd5ffd5176e67dcac054196fe7d804",
    ),
    ReportSegmentSpec(
        "samsung-report-006",
        "earnings_forecast_revision",
        1,
        "2Q26 잠정실적 당시 기대치 상회",
        "high",
        "41c242d35e37b8af4d61894d4e278f36c6723a8fdcc93a256914d80a30bb00d9",
    ),
    ReportSegmentSpec(
        "samsung-report-007",
        "forward_forecast",
        7,
        "예상 포괄손익계산서 (요약)",
        "high",
        "cccebbb7de77aff67c8ebdb8ebce658d8dc45494d168de6b6497ce749152e1f0",
    ),
    ReportSegmentSpec(
        "samsung-report-008",
        "valuation",
        5,
        "표 6. 삼성전자 SOTP 밸류에이션 (5/27 발간 기준)",
        "high",
        "6a50fba214819772422bdd0a12e25e31de9f978ba29a67048c8b5f4c0e33e052",
    ),
    ReportSegmentSpec(
        "samsung-report-009",
        "valuation_multiple",
        5,
        "표 6. 삼성전자 SOTP 밸류에이션 (5/27 발간 기준)",
        "high",
        "003e851d4e684b1ce3897056fabbe296fc13d92eb9df4c539a0f7242a646ff2c",
    ),
    ReportSegmentSpec(
        "samsung-report-010",
        "shareholder_return",
        6,
        "표 7. 삼성전자 주주환원 규모 추정",
        "high",
        "be77387c0e680483f21de9970fb7b58ff20cc2dae8a097ccd107db6747a3fb9c",
    ),
    ReportSegmentSpec(
        "samsung-report-011",
        "dividend_view",
        1,
        "2Q26 잠정실적 당시 기대치 상회",
        "high",
        "807448272b0e946b23f24fac3945049d48d41b9dd99a227c70baa5b5d0f61bf4",
    ),
    ReportSegmentSpec(
        "samsung-report-012",
        "risk_and_catalyst",
        1,
        "2Q26 잠정실적 당시 기대치 상회",
        "medium",
        "2a4e0a822f7d3b41b2d6d56f9faff79e385f22257b69493c41cd9bec7d46eff6",
    ),
)

_SK_HYNIX_SEGMENTS = (
    ReportSegmentSpec(
        "skhynix-report-001",
        "investment_thesis",
        1,
        "목표주가 유지, 대외 업황 변수는 여전히 견조",
        "high",
        "53b409d6bd2e62c297459b2397b46199ddda89a2d5b9ff824b3625dac08bf46e",
    ),
    ReportSegmentSpec(
        "skhynix-report-002",
        "external_demand_indicator",
        1,
        "목표주가 유지, 대외 업황 변수는 여전히 견조",
        "high",
        "064f7d66a8231b6bdf9e01dde974bd19801efda5174b02c175cfb34d2acc2e59",
    ),
    ReportSegmentSpec(
        "skhynix-report-003",
        "cloud_order_outlook",
        1,
        "목표주가 유지, 대외 업황 변수는 여전히 견조",
        "high",
        "9bdee365be68182e0d0957d31b6b4eba6b1e1207bf5ce3c01950723e2885e097",
    ),
    ReportSegmentSpec(
        "skhynix-report-004",
        "near_term_earnings_revision",
        2,
        "표 1. SK하이닉스 실적 추정치 변경",
        "high",
        "41e564a71d2527110bca5320a0b9b517f504225e99c8c58c949b3bf3a2c4070b",
    ),
    ReportSegmentSpec(
        "skhynix-report-005",
        "memory_assumption_revision",
        2,
        "표 1. SK하이닉스 실적 추정치 변경",
        "high",
        "8083c5e88cf1448ec2b77016f6d9600413acd3990445116ab9c68e407c117f9a",
    ),
    ReportSegmentSpec(
        "skhynix-report-006",
        "annual_forecast",
        7,
        "예상 포괄손익계산서 (요약)",
        "high",
        "3a69700b4f78b77d80acc0adce4ac6adb8a96583a7bb9ba44923465d22e805e6",
    ),
    ReportSegmentSpec(
        "skhynix-report-007",
        "forward_forecast",
        7,
        "예상 포괄손익계산서 (요약)",
        "high",
        "ad5cbf7502c895e41b1c5a632b47edd254331cbb89bd8f2247ea37c0ace8e5d1",
    ),
    ReportSegmentSpec(
        "skhynix-report-008",
        "hbm_outlook",
        1,
        "2Q26 이익 추정치 하향 조정. 27년 증익 기조는 유지",
        "medium",
        "26770c27a1aebee6678489e7001c396364e7b5acbf04b0caf2374d5116a41eac",
        (
            "컨벤셔널 메모리 가격의 전반적 상승과 HBM 가격 상승이 "
            "2027년 실적을 지지할 것으로 봤으며, HBM 생산능력 제약 때문에 "
            "공급은 타이트할 것으로 판단했다."
        ),
    ),
    ReportSegmentSpec(
        "skhynix-report-009",
        "valuation",
        2,
        "표 2. SK하이닉스 목표주가 산정",
        "high",
        "3df5192a503424ffa07da84ae75b1b15e40e44075bc727508b08fb990f89c4a6",
    ),
    ReportSegmentSpec(
        "skhynix-report-010",
        "valuation_context",
        2,
        "표 2. SK하이닉스 목표주가 산정",
        "high",
        "ee54c031c54a641dba70623e740a41e42a1419fb6c2b77187192ce06b5e0c5a2",
    ),
    ReportSegmentSpec(
        "skhynix-report-011",
        "product_forecast",
        3,
        "표 4. SK하이닉스 주요 제품별 추정치",
        "high",
        "5922f96e325c67422e99e762b652289659e88bfb7839102b325bc1d337c1c6d9",
    ),
    ReportSegmentSpec(
        "skhynix-report-012",
        "risk_and_catalyst",
        1,
        "2Q26 이익 추정치 하향 조정. 27년 증익 기조는 유지",
        "medium",
        "c4d43e45bfe86314d64f2f21fad4fd3956a41b1ce5c5f6c8806075dc5376f43f",
    ),
)

_HYUNDAI_SEGMENTS = (
    ReportSegmentSpec(
        "hyundai-report-001",
        "investment_thesis",
        1,
        "2분기 실적은 알려진 기말환율 기저와 생산차질 영향",
        "high",
        "4f7ae2c613cb36d3c2b5a4f0a305d6a20dbf814d90c067b2e1f95d1e5ce13742",
    ),
    ReportSegmentSpec(
        "hyundai-report-002",
        "earnings_review",
        2,
        "표 2. 현대차 2026 발표치와 컨센서스 비교",
        "high",
        "cef3aec2b59760094e7a0460ccc7939df77b09f44dc10d3ba88e0e1a53dc7229",
    ),
    ReportSegmentSpec(
        "hyundai-report-003",
        "consensus_comparison",
        2,
        "표 2. 현대차 2026 발표치와 컨센서스 비교",
        "high",
        "f7018cb12398276ca70738dcbe318aeb7d18a358b1da4f66152f88f6ecf65b13",
    ),
    ReportSegmentSpec(
        "hyundai-report-004",
        "earnings_bridge",
        1,
        "2분기 실적은 알려진 기말환율 기저와 생산차질 영향",
        "medium",
        "1ebd538617dd96192c0aceb30f6803e136514a21741de9f986ab6b5fa92aab47",
    ),
    ReportSegmentSpec(
        "hyundai-report-005",
        "segment_forecast",
        2,
        "표 3. 현대차 분기 및 연간 실적 전망",
        "high",
        "c49fa78275a2b291e9a7741b49f7633242877ac8bd06317bb9cf72feb5544ffc",
    ),
    ReportSegmentSpec(
        "hyundai-report-006",
        "annual_forecast",
        10,
        "예상 포괄손익계산서 (요약)",
        "high",
        "302be6063fdd377eb6709edb5fa61b4d131f538be34a84c87ba4b33c4030b97c",
    ),
    ReportSegmentSpec(
        "hyundai-report-007",
        "forward_forecast",
        10,
        "예상 포괄손익계산서 (요약)",
        "high",
        "9b36d5d2c84eafb32cbee6258b1fd88ffb7444b72adf0a97648291c50deab122",
    ),
    ReportSegmentSpec(
        "hyundai-report-008",
        "company_guidance",
        3,
        "그림 2. 현대차 26년 연간 가이던스",
        "high",
        "e1f906887715b836270cf4bb29d1d7ac6d26c92a1f677900b3c298de6cada9c6",
    ),
    ReportSegmentSpec(
        "hyundai-report-009",
        "shareholder_return",
        3,
        "그림 2. 현대차 26년 연간 가이던스",
        "high",
        "3bc842fc423262e133ab25e58036893bd61378347d532206fce0f5e1674d3c6f",
    ),
    ReportSegmentSpec(
        "hyundai-report-010",
        "valuation",
        2,
        "표 1. 현대차 목표주가 산출 테이블",
        "high",
        "fdc0af02e1774102a3ce48a05b2e02f421a4a78ead25df3b1d1b63e38e94d154",
    ),
    ReportSegmentSpec(
        "hyundai-report-011",
        "robotics_valuation",
        4,
        "표 5. 보스턴다이내믹스 기업가치 추정",
        "high",
        "2994720d1e3973d7e5cd5f7e2cd5096dccdacbadfc1fba6c7d2693b2b1040e47",
    ),
    ReportSegmentSpec(
        "hyundai-report-012",
        "robotics_catalyst_and_risk",
        1,
        "3Q 로봇 모멘텀 주목, 실적은 양호할 것으로 예상",
        "medium",
        "1b8d9ba60f94646f3cf8709f4b66ead3d59a364830e34f7eb1f3961345f4523b",
    ),
)

REPORT_INPUT_SPECS: tuple[ReportInputSpec, ...] = (
    ReportInputSpec(
        security_id="KRX:005930",
        ticker="005930",
        security_name="삼성전자",
        input_company_name="삼성전자",
        input_extract_filename="report_extract_samsung_electronics.json",
        manifest_id="miraeasset-005930-20260707-2341060",
        title="과격한 주가 반응에 뇌동하지 말자",
        publisher="미래에셋증권",
        analyst="김영건",
        published_at="2026-07-07",
        source_url=(
            "https://securities.miraeasset.com/bbs/board/message/view.do"
            "?categoryId=1800&messageId=2341060"
        ),
        source_asset_id="miraeasset-attachment-2145729",
        extract_sha256=(
            "dda881ed9d6a01441ddc421512a9d40d4be9f718b5491c5fc9c003d853b514ef"
        ),
        pdf_sha256=(
            "23846dcb0c45932b97297ebb7dc4c3a4a798e09732c0a3e4a3c4c248a366d3d0"
        ),
        pdf_page_count=8,
        recommendation=ReportRecommendationSpec(
            investment_opinion="매수",
            target_price=550000,
            target_price_currency="KRW",
            current_price=318000,
            current_price_date="2026-07-06",
            upside_pct=73.0,
            attribution=(
                "미래에셋증권 김영건 애널리스트의 2026-07-07 발행 당시 의견"
            ),
        ),
        segments=_SAMSUNG_SEGMENTS,
    ),
    ReportInputSpec(
        security_id="KRX:000660",
        ticker="000660",
        security_name="SK하이닉스",
        input_company_name="SK하이닉스",
        input_extract_filename="report_extract_sk_hynix.json",
        manifest_id="miraeasset-000660-20260714-2341215",
        title="시선을 약간만 아래로",
        publisher="미래에셋증권",
        analyst="김영건",
        published_at="2026-07-14",
        source_url=(
            "https://securities.miraeasset.com/bbs/board/message/view.do"
            "?categoryId=1533&messageId=2341215"
        ),
        source_asset_id="miraeasset-attachment-2145830",
        extract_sha256=(
            "33b9f2a2777b120f19823dc74f36091d9b9a528f87024dc52f2dc055acf840a6"
        ),
        pdf_sha256=(
            "418e9cff7d4cd9632ebfb74e818922c575d76fa975ac0fa39108635136e46926"
        ),
        pdf_page_count=9,
        recommendation=ReportRecommendationSpec(
            investment_opinion="매수",
            target_price=4200000,
            target_price_currency="KRW",
            current_price=1845000,
            current_price_date="2026-07-13",
            upside_pct=127.6,
            attribution=(
                "미래에셋증권 김영건 애널리스트의 2026-07-14 발행 당시 의견"
            ),
        ),
        segments=_SK_HYNIX_SEGMENTS,
    ),
    ReportInputSpec(
        security_id="KRX:005380",
        ticker="005380",
        security_name="현대자동차",
        input_company_name="현대차",
        input_extract_filename="report_extract_hyundai_motor.json",
        manifest_id="miraeasset-005380-20260724-2341441",
        title="2Q26 리뷰: 우려 대비 양호, 로봇 모멘텀 주목",
        publisher="미래에셋증권",
        analyst="김진석",
        published_at="2026-07-24",
        source_url=(
            "https://securities.miraeasset.com/bbs/board/message/view.do"
            "?categoryId=1800&messageId=2341441"
        ),
        source_asset_id="miraeasset-attachment-2146110",
        extract_sha256=(
            "76174375e32d0d76de10d387b4350d4b96ec1dfc4ea513e466ed508e0caded8f"
        ),
        pdf_sha256=(
            "65e415b51b057712ebd2c0dac97413060c7f317bcca8297590e9ebf2560d97b7"
        ),
        pdf_page_count=12,
        recommendation=ReportRecommendationSpec(
            investment_opinion="매수",
            target_price=840000,
            target_price_currency="KRW",
            current_price=432000,
            current_price_date="2026-07-23",
            upside_pct=94.4,
            attribution=(
                "미래에셋증권 김진석 애널리스트의 2026-07-24 발행 당시 의견"
            ),
        ),
        segments=_HYUNDAI_SEGMENTS,
    ),
)


def load_report_extract(path: str | Path) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError):
        raise ReportSnapshotValidationError(
            "report source input could not be loaded"
        ) from None
    if not isinstance(payload, dict):
        raise ReportSnapshotValidationError("report source input is invalid")
    return payload


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    try:
        with Path(path).open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
    except (OSError, TypeError):
        raise ReportSnapshotValidationError(
            "report source input could not be read"
        ) from None
    return digest.hexdigest()


def build_report_snapshot_payload(
    extract: Mapping[str, Any],
    *,
    spec: ReportInputSpec,
    source_pdf_bytes: bytes,
    source_extract_sha256: str,
    observed_pdf_page_count: int,
    as_of_date: date = REPORT_SNAPSHOT_AS_OF_DATE,
) -> dict[str, Any]:
    _validate_build_input(
        extract,
        spec=spec,
        source_pdf_bytes=source_pdf_bytes,
        source_extract_sha256=source_extract_sha256,
        observed_pdf_page_count=observed_pdf_page_count,
        as_of_date=as_of_date,
    )
    segments = _validate_extract(extract, spec=spec)
    document_ids = [
        f"report:{spec.manifest_id}:{segment.segment_id}"
        for segment in spec.segments
    ]
    try:
        manifest = validate_report_manifest(
            {
                "manifest_id": spec.manifest_id,
                "security_id": spec.security_id,
                "title": spec.title,
                "publisher": spec.publisher,
                "published_at": spec.published_at,
                "source_url": spec.source_url,
                "source_asset_id": spec.source_asset_id,
                "access_note": (
                    "Official publisher page; source PDF verified in a "
                    "Git-ignored FSC workspace."
                ),
                "usage_note": (
                    "Questock-authored short structured summaries and verified "
                    "facts only; source PDF, excerpts, and raw text are excluded."
                ),
                "usage_review_status": "approved",
                "corpus_ingest_allowed": True,
                "external_llm_processing_allowed": False,
                "file_hash": spec.pdf_sha256,
                "hash_scope": "source_asset_bytes",
                "hash_verification_status": "verified",
                "documents": document_ids,
                "ingestion_version": REPORT_INGESTION_VERSION,
                "analyst": spec.analyst,
                "report_type": "company_research",
                "basis_date": spec.published_at,
                "language": "ko",
            }
        )
        normalized_documents = [
            validate_normalized_report_document(
                {
                    "manifest_id": spec.manifest_id,
                    "segment_id": segment_spec.segment_id,
                    "document_id": document_id,
                    "security_id": spec.security_id,
                    "mentioned_security_ids": [],
                    "subject_scope": "company_specific",
                    "page": segment_spec.page,
                    "page_basis": "pdf_1_based",
                    "section": segment_spec.section,
                    "text": summary,
                    "text_kind": "manual_summary",
                    "manual_verification_status": "verified_against_source",
                    "contains_numeric_claims": True,
                    "numeric_claims_verified": True,
                    "summary_kind": "questock_structured_summary",
                }
            )
            for segment_spec, document_id, summary in zip(
                spec.segments,
                document_ids,
                segments,
                strict=True,
            )
        ]
        documents = build_manual_research_documents(
            manifest,
            normalized_documents,
            mode="corpus",
            as_of_date=as_of_date,
            source_bytes=source_pdf_bytes,
        )
    except ReportIngestValidationError:
        raise ReportSnapshotValidationError(
            "report corpus normalization failed"
        ) from None

    return {
        "schema_version": REPORT_SNAPSHOT_SCHEMA_VERSION,
        "snapshot_id": REPORT_SNAPSHOT_ID,
        "security_id": spec.security_id,
        "source_integrity": {
            "pdf_sha256": spec.pdf_sha256,
            "extract_sha256": spec.extract_sha256,
            "pdf_page_count": observed_pdf_page_count,
            "hash_verification_status": "verified",
            "manual_verification_status": "verified_against_source",
        },
        "permissions": _permission_payload(),
        "report_metadata": _report_metadata(spec),
        "coverage": {
            "document_count": len(documents),
            "minimum_required": 8,
            "verified_section_count": len(documents),
            "verified_pdf_pages": sorted(
                {segment.page for segment in spec.segments}
            ),
            "ready": len(documents) >= 8,
        },
        "documents": [document.model_dump(mode="json") for document in documents],
    }


def validate_report_snapshot_payload(
    payload: Mapping[str, Any],
    *,
    spec: ReportInputSpec,
) -> tuple[FinancialDocument, ...]:
    if (
        not isinstance(payload, Mapping)
        or set(payload)
        != {
            "schema_version",
            "snapshot_id",
            "security_id",
            "source_integrity",
            "permissions",
            "report_metadata",
            "coverage",
            "documents",
        }
        or payload.get("schema_version") != REPORT_SNAPSHOT_SCHEMA_VERSION
        or payload.get("snapshot_id") != REPORT_SNAPSHOT_ID
        or payload.get("security_id") != spec.security_id
        or payload.get("source_integrity") != _source_integrity(spec)
        or payload.get("permissions") != _permission_payload()
        or payload.get("report_metadata") != _report_metadata(spec)
    ):
        raise ReportSnapshotValidationError(
            "report snapshot payload is invalid"
        )
    raw_documents = payload.get("documents")
    if not isinstance(raw_documents, list):
        raise ReportSnapshotValidationError(
            "report snapshot documents are invalid"
        )
    try:
        documents = tuple(
            FinancialDocument.model_validate(document)
            for document in raw_documents
        )
    except (TypeError, ValueError, ValidationError):
        raise ReportSnapshotValidationError(
            "report snapshot documents are invalid"
        ) from None
    _validate_output_documents(documents, spec=spec)
    expected_coverage = {
        "document_count": len(spec.segments),
        "minimum_required": 8,
        "verified_section_count": len(spec.segments),
        "verified_pdf_pages": sorted({segment.page for segment in spec.segments}),
        "ready": len(spec.segments) >= 8,
    }
    if payload.get("coverage") != expected_coverage:
        raise ReportSnapshotValidationError(
            "report snapshot coverage is invalid"
        )
    _assert_safe_output(payload)
    return tuple(document.model_copy(deep=True) for document in documents)


def write_report_snapshot_json(
    path: str | Path,
    payload: Mapping[str, Any],
) -> None:
    if not isinstance(payload, Mapping):
        raise ReportSnapshotValidationError(
            "report snapshot output is invalid"
        )
    try:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(
            dict(payload),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        output_path.write_text(f"{text}\n", encoding="utf-8", newline="\n")
    except (OSError, TypeError, ValueError):
        raise ReportSnapshotValidationError(
            "report snapshot output could not be written"
        ) from None


def _validate_build_input(
    extract: Mapping[str, Any],
    *,
    spec: ReportInputSpec,
    source_pdf_bytes: bytes,
    source_extract_sha256: str,
    observed_pdf_page_count: int,
    as_of_date: date,
) -> None:
    if (
        not isinstance(extract, Mapping)
        or not isinstance(spec, ReportInputSpec)
        or type(source_pdf_bytes) is not bytes
        or not source_pdf_bytes.startswith(b"%PDF-")
        or hashlib.sha256(source_pdf_bytes).hexdigest() != spec.pdf_sha256
        or source_extract_sha256 != spec.extract_sha256
        or not _valid_sha256(source_extract_sha256)
        or type(observed_pdf_page_count) is not int
        or observed_pdf_page_count != spec.pdf_page_count
        or not isinstance(as_of_date, date)
        or spec.published_at > as_of_date.isoformat()
    ):
        raise ReportSnapshotValidationError(
            "report snapshot build input is invalid"
        )


def _validate_extract(
    extract: Mapping[str, Any],
    *,
    spec: ReportInputSpec,
) -> tuple[str, ...]:
    identity = extract.get("identity")
    recommendation = extract.get("recommendation")
    raw_segments = extract.get("segments")
    if (
        extract.get("schema_version") != "fsc-research-report-extract-v1"
        or extract.get("document_type") != "research_report"
        or not isinstance(identity, Mapping)
        or not isinstance(recommendation, Mapping)
        or not isinstance(raw_segments, list)
        or len(raw_segments) != len(spec.segments)
    ):
        raise ReportSnapshotValidationError("report source input is invalid")
    expected_identity = {
        "company_name": spec.input_company_name,
        "ticker": spec.ticker,
        "report_title": spec.title,
        "issuer": spec.publisher,
        "analyst": spec.analyst,
        "published_at": spec.published_at,
        "identity_status": "verified_from_pdf_and_user_supplied_links",
    }
    if any(identity.get(key) != value for key, value in expected_identity.items()):
        raise ReportSnapshotValidationError(
            "report source identity is invalid"
        )
    if dict(recommendation) != spec.recommendation.as_payload():
        raise ReportSnapshotValidationError(
            "report source recommendation is invalid"
        )

    by_id: dict[str, Mapping[str, Any]] = {}
    for segment in raw_segments:
        if not isinstance(segment, Mapping):
            raise ReportSnapshotValidationError(
                "report source segments are invalid"
            )
        segment_id = segment.get("segment_id")
        if not isinstance(segment_id, str) or segment_id in by_id:
            raise ReportSnapshotValidationError(
                "report source segments are invalid"
            )
        by_id[segment_id] = segment
    if set(by_id) != {segment.segment_id for segment in spec.segments}:
        raise ReportSnapshotValidationError(
            "report source segments are invalid"
        )

    summaries: list[str] = []
    for segment_spec in spec.segments:
        segment = by_id[segment_spec.segment_id]
        summary = segment.get("summary")
        evidence_excerpt = segment.get("evidence_excerpt")
        if (
            segment.get("type") != segment_spec.segment_type
            or segment.get("page") != segment_spec.page
            or segment.get("confidence") != segment_spec.confidence
            or not isinstance(summary, str)
            or not summary.strip()
            or not isinstance(evidence_excerpt, str)
            or not evidence_excerpt.strip()
            or segment_spec.page > spec.pdf_page_count
        ):
            raise ReportSnapshotValidationError(
                "report source segments are invalid"
            )
        curated_summary = segment_spec.summary_override or summary.strip()
        if _text_sha256(curated_summary) != segment_spec.summary_sha256:
            raise ReportSnapshotValidationError(
                "report source summary is not approved"
            )
        summaries.append(curated_summary)
    return tuple(summaries)


def _validate_output_documents(
    documents: Sequence[FinancialDocument],
    *,
    spec: ReportInputSpec,
) -> None:
    if len(documents) != len(spec.segments):
        raise ReportSnapshotValidationError(
            "report snapshot documents are invalid"
        )
    for document, segment in zip(documents, spec.segments, strict=True):
        expected_document_id = (
            f"report:{spec.manifest_id}:{segment.segment_id}"
        )
        if (
            document.document_id != expected_document_id
            or document.source_type != "research_report"
            or document.provider != "manual_manifest"
            or document.primary_security_ids != [spec.security_id]
            or document.mentioned_security_ids
            or document.source_url != spec.source_url
            or document.locator.get("manifest_id") != spec.manifest_id
            or document.locator.get("document_id") != expected_document_id
            or document.locator.get("page") != segment.page
            or document.locator.get("page_basis") != "pdf_1_based"
            or document.locator.get("section") != segment.section
            or document.metadata.get("usage_review_status") != "approved"
            or document.metadata.get("corpus_ingest_allowed") is not True
            or document.metadata.get("external_llm_processing_allowed")
            is not False
            or document.metadata.get("hash_verification_status") != "verified"
            or document.metadata.get("manual_verification_status")
            != "verified_against_source"
            or document.metadata.get("text_kind") != "manual_summary"
            or document.metadata.get("summary_kind")
            != "questock_structured_summary"
            or document.metadata.get("build_mode") != "corpus"
            or document.ingestion_version != REPORT_INGESTION_VERSION
            or _text_sha256(document.text) != segment.summary_sha256
        ):
            raise ReportSnapshotValidationError(
                "report snapshot documents are invalid"
            )


def _source_integrity(spec: ReportInputSpec) -> dict[str, Any]:
    return {
        "pdf_sha256": spec.pdf_sha256,
        "extract_sha256": spec.extract_sha256,
        "pdf_page_count": spec.pdf_page_count,
        "hash_verification_status": "verified",
        "manual_verification_status": "verified_against_source",
    }


def _permission_payload() -> dict[str, Any]:
    return {
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


def _report_metadata(spec: ReportInputSpec) -> dict[str, Any]:
    return {
        "manifest_id": spec.manifest_id,
        "security_name": spec.security_name,
        "title": spec.title,
        "publisher": spec.publisher,
        "analyst": spec.analyst,
        "published_at": spec.published_at,
        "source_url": spec.source_url,
        "source_asset_id": spec.source_asset_id,
        "report_type": "company_research",
        "recommendation": spec.recommendation.as_payload(),
        "recommendation_owner": spec.publisher,
        "questock_investment_opinion": False,
    }


def _assert_safe_output(value: object) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key).lower() in _FORBIDDEN_OUTPUT_KEYS:
                raise ReportSnapshotValidationError(
                    "report snapshot contains forbidden source content"
                )
            _assert_safe_output(nested)
        return
    if isinstance(value, list):
        for nested in value:
            _assert_safe_output(nested)
        return
    if isinstance(value, str) and _looks_like_local_absolute_path(value):
        raise ReportSnapshotValidationError(
            "report snapshot contains a local absolute path"
        )


def _looks_like_local_absolute_path(value: str) -> bool:
    normalized = value.replace("\\", "/")
    return (
        value.startswith("file://")
        or value.startswith("\\\\")
        or bool(_WINDOWS_ABSOLUTE_PATH_RE.match(value))
        or normalized.startswith("/")
    )


def _valid_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def _text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


__all__ = [
    "REPORT_INPUT_SPECS",
    "REPORT_SNAPSHOT_AS_OF_DATE",
    "REPORT_SNAPSHOT_ID",
    "REPORT_SNAPSHOT_SCHEMA_VERSION",
    "ReportInputSpec",
    "ReportRecommendationSpec",
    "ReportSegmentSpec",
    "ReportSnapshotValidationError",
    "build_report_snapshot_payload",
    "file_sha256",
    "load_report_extract",
    "validate_report_snapshot_payload",
    "write_report_snapshot_json",
]
