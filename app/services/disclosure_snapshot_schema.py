from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

from app.core.models import FinancialDocument
from app.providers.disclosure import build_dart_viewer_url, parse_report_markers

DISCLOSURE_SNAPSHOT_SCHEMA_VERSION = "service-disclosure-curated-v1"
DISCLOSURE_SNAPSHOT_ID = "svc-20260724-1402"
DISCLOSURE_SNAPSHOT_INGESTION_VERSION = "disclosure-snapshot-fsc-v1"
DISCLOSURE_PROVIDER_KEY = "recorded_disclosure"
DISCLOSURE_CONTENT_LEVEL = "verified_body_facts"
SEOUL_TZ = timezone(timedelta(hours=9))
_RECEIPT_RE = re.compile(r"^\d{14}$")
_FACT_ID_RE = re.compile(r"^[a-z0-9-]+-disc-\d{3}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_CATEGORIES = frozenset(
    {
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
    }
)
_ALLOWED_CATEGORIES = _REQUIRED_CATEGORIES | {
    "contract_or_business_plan",
    "major_product_or_technology",
}
_ALLOWED_VERIFICATION_STATUSES = {
    "verified_against_source",
    "verified_against_source_with_conflict_note",
}


class DisclosureSnapshotValidationError(ValueError):
    """Raised when FSC disclosure source data violates the fixed contract."""


@dataclass(frozen=True)
class DisclosureInputSpec:
    security_id: str
    ticker: str
    security_name: str
    matrix_company_name: str
    corp_code: str
    corp_code_verification_status: str
    receipt_no: str
    report_name: str
    pdf_page_count: int

    @property
    def viewer_url(self) -> str:
        return build_dart_viewer_url(self.receipt_no)


@dataclass(frozen=True)
class DisclosureCorrectionVerification:
    receipt_no: str
    status: Literal[
        "verified_official_api",
        "verified_official_viewer",
        "pending",
    ]
    remark: str | None
    report_name: str | None


DISCLOSURE_INPUT_SPECS: tuple[DisclosureInputSpec, ...] = (
    DisclosureInputSpec(
        security_id="KRX:005930",
        ticker="005930",
        security_name="삼성전자",
        matrix_company_name="삼성전자주식회사",
        corp_code="00126380",
        corp_code_verification_status="candidate",
        receipt_no="20260515002181",
        report_name="분기보고서 (제58기)",
        pdf_page_count=323,
    ),
    DisclosureInputSpec(
        security_id="KRX:000660",
        ticker="000660",
        security_name="SK하이닉스",
        matrix_company_name="에스케이하이닉스 주식회사",
        corp_code="00164779",
        corp_code_verification_status="candidate",
        receipt_no="20260515002287",
        report_name="분기보고서 (제79기)",
        pdf_page_count=236,
    ),
    DisclosureInputSpec(
        security_id="KRX:005380",
        ticker="005380",
        security_name="현대자동차",
        matrix_company_name="현대자동차 주식회사",
        corp_code="00164742",
        corp_code_verification_status="candidate",
        receipt_no="20260515002418",
        report_name="분기보고서 (제59기 1분기)",
        pdf_page_count=286,
    ),
)


def load_disclosure_fact_matrix(path: str | Path) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError):
        raise DisclosureSnapshotValidationError(
            "disclosure source input could not be loaded"
        ) from None
    if not isinstance(payload, dict):
        raise DisclosureSnapshotValidationError(
            "disclosure source input is invalid"
        )
    return payload


def build_disclosure_snapshot_payload(
    matrix: Mapping[str, Any],
    *,
    spec: DisclosureInputSpec,
    source_pdf_sha256: str,
    source_matrix_sha256: str,
    observed_pdf_page_count: int,
    correction: DisclosureCorrectionVerification,
) -> dict[str, Any]:
    _validate_build_input(
        matrix,
        spec=spec,
        source_pdf_sha256=source_pdf_sha256,
        source_matrix_sha256=source_matrix_sha256,
        observed_pdf_page_count=observed_pdf_page_count,
        correction=correction,
    )
    identity = _validate_identity(matrix, spec=spec)
    facts = _validate_facts(
        matrix.get("facts"),
        spec=spec,
        observed_pdf_page_count=observed_pdf_page_count,
    )
    categories = frozenset(item["category"] for item in facts)
    missing_categories = sorted(_REQUIRED_CATEGORIES - categories)
    if len(facts) < 10 or missing_categories:
        raise DisclosureSnapshotValidationError(
            "disclosure fact coverage is incomplete"
        )
    correction_payload = _correction_payload(correction, spec=spec)
    document = _build_document(
        facts=facts,
        identity=identity,
        spec=spec,
        correction=correction_payload,
    )
    return {
        "schema_version": DISCLOSURE_SNAPSHOT_SCHEMA_VERSION,
        "snapshot_id": DISCLOSURE_SNAPSHOT_ID,
        "security_id": spec.security_id,
        "source_integrity": {
            "pdf_sha256": source_pdf_sha256,
            "matrix_sha256": source_matrix_sha256,
            "pdf_page_count": observed_pdf_page_count,
        },
        "coverage": {
            "fact_count": len(facts),
            "required_categories": sorted(_REQUIRED_CATEGORIES),
            "observed_categories": sorted(categories),
            "missing_categories": missing_categories,
            "ready": True,
        },
        "identity": {
            "security_id": spec.security_id,
            "ticker": spec.ticker,
            "ticker_source": "project_security_mapping",
            "corp_code": spec.corp_code,
            "corp_code_source": "project_security_mapping",
            "corp_code_verification_status": (
                spec.corp_code_verification_status
            ),
            "company_name": identity["company_name"],
            "report_name": identity["report_name"],
            "report_period": identity["report_period"],
            "submitted_at": identity["submitted_at"],
            "receipt_no": spec.receipt_no,
            "viewer_url": spec.viewer_url,
            "pdf_identity_status": "verified_from_pdf",
        },
        "correction": correction_payload,
        "document": document.model_dump(mode="json"),
    }


def validate_disclosure_snapshot_payload(
    payload: Mapping[str, Any],
    *,
    spec: DisclosureInputSpec,
) -> FinancialDocument:
    if (
        not isinstance(payload, Mapping)
        or set(payload)
        != {
            "schema_version",
            "snapshot_id",
            "security_id",
            "source_integrity",
            "coverage",
            "identity",
            "correction",
            "document",
        }
        or payload.get("schema_version")
        != DISCLOSURE_SNAPSHOT_SCHEMA_VERSION
        or payload.get("snapshot_id") != DISCLOSURE_SNAPSHOT_ID
        or payload.get("security_id") != spec.security_id
    ):
        raise DisclosureSnapshotValidationError(
            "disclosure snapshot payload is invalid"
        )
    source_integrity = payload.get("source_integrity")
    coverage = payload.get("coverage")
    identity = payload.get("identity")
    correction = payload.get("correction")
    if (
        not isinstance(source_integrity, Mapping)
        or source_integrity.get("pdf_page_count") != spec.pdf_page_count
        or not _valid_sha256(source_integrity.get("pdf_sha256"))
        or not _valid_sha256(source_integrity.get("matrix_sha256"))
        or not isinstance(coverage, Mapping)
        or not isinstance(identity, Mapping)
        or not isinstance(correction, Mapping)
        or not _valid_output_identity(identity, spec=spec)
        or not _valid_output_correction(correction)
    ):
        raise DisclosureSnapshotValidationError(
            "disclosure snapshot payload is invalid"
        )
    try:
        document = FinancialDocument.model_validate(payload.get("document"))
    except (TypeError, ValueError):
        raise DisclosureSnapshotValidationError(
            "disclosure snapshot document is invalid"
        ) from None
    observed_categories = _validate_output_document(
        document,
        spec=spec,
        correction=correction,
    )
    facts = document.locator["facts"]
    if (
        set(coverage)
        != {
            "fact_count",
            "required_categories",
            "observed_categories",
            "missing_categories",
            "ready",
        }
        or coverage.get("fact_count") != len(facts)
        or coverage.get("required_categories") != sorted(_REQUIRED_CATEGORIES)
        or coverage.get("observed_categories") != sorted(observed_categories)
        or coverage.get("missing_categories") != []
        or coverage.get("ready") is not True
        or len(facts) < 10
        or _REQUIRED_CATEGORIES - observed_categories
    ):
        raise DisclosureSnapshotValidationError(
            "disclosure snapshot coverage is invalid"
        )
    return document.model_copy(deep=True)


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    try:
        with Path(path).open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
    except (OSError, TypeError):
        raise DisclosureSnapshotValidationError(
            "disclosure source input could not be read"
        ) from None
    return digest.hexdigest()


def write_disclosure_snapshot_json(
    path: str | Path,
    payload: Mapping[str, Any],
) -> None:
    if not isinstance(payload, Mapping):
        raise DisclosureSnapshotValidationError(
            "disclosure snapshot output is invalid"
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
        raise DisclosureSnapshotValidationError(
            "disclosure snapshot output could not be written"
        ) from None


def _validate_build_input(
    matrix: Mapping[str, Any],
    *,
    spec: DisclosureInputSpec,
    source_pdf_sha256: str,
    source_matrix_sha256: str,
    observed_pdf_page_count: int,
    correction: DisclosureCorrectionVerification,
) -> None:
    if (
        not isinstance(matrix, Mapping)
        or not isinstance(spec, DisclosureInputSpec)
        or not _valid_sha256(source_pdf_sha256)
        or not _valid_sha256(source_matrix_sha256)
        or isinstance(observed_pdf_page_count, bool)
        or observed_pdf_page_count != spec.pdf_page_count
        or not isinstance(correction, DisclosureCorrectionVerification)
        or correction.receipt_no != spec.receipt_no
    ):
        raise DisclosureSnapshotValidationError(
            "disclosure snapshot build input is invalid"
        )


def _validate_identity(
    matrix: Mapping[str, Any],
    *,
    spec: DisclosureInputSpec,
) -> dict[str, str]:
    identity = matrix.get("identity")
    contract = matrix.get("document_contract")
    if (
        not isinstance(identity, Mapping)
        or not isinstance(contract, Mapping)
        or contract.get("one_receipt_one_document") is not True
        or contract.get("content_level") != DISCLOSURE_CONTENT_LEVEL
    ):
        raise DisclosureSnapshotValidationError(
            "disclosure document contract is invalid"
        )
    expected = {
        "company_name": spec.matrix_company_name,
        "ticker": "not_found",
        "corp_code": "not_found",
        "report_name": spec.report_name,
        "report_period": "2026-01-01~2026-03-31",
        "submitted_at": "2026-05-15",
        "receipt_no": spec.receipt_no,
        "official_url": spec.viewer_url,
        "identity_status": "verified_from_pdf",
    }
    if any(identity.get(key) != value for key, value in expected.items()):
        raise DisclosureSnapshotValidationError(
            "disclosure source identity is invalid"
        )
    return {key: value for key, value in expected.items() if isinstance(value, str)}


def _validate_facts(
    value: object,
    *,
    spec: DisclosureInputSpec,
    observed_pdf_page_count: int,
) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list) or not value:
        raise DisclosureSnapshotValidationError(
            "disclosure facts are invalid"
        )
    facts: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for raw_fact in value:
        if not isinstance(raw_fact, Mapping):
            raise DisclosureSnapshotValidationError(
                "disclosure facts are invalid"
            )
        fact_id = _nonblank(raw_fact.get("fact_id"))
        category = _nonblank(raw_fact.get("category"))
        claim = _nonblank(raw_fact.get("claim"))
        period = _nonblank(raw_fact.get("period"))
        basis = _nonblank(raw_fact.get("basis"))
        confidence = raw_fact.get("confidence")
        verification_status = raw_fact.get("verification_status")
        physical_page = _positive_integer(raw_fact.get("physical_pdf_page"))
        printed_page = _positive_integer(raw_fact.get("printed_page"))
        value_text = _optional_text(raw_fact.get("value"))
        unit = _optional_text(raw_fact.get("unit"))
        section_path = _string_sequence(raw_fact.get("section_path"))
        notes = _string_sequence(raw_fact.get("notes"), allow_empty=True)
        if (
            _FACT_ID_RE.fullmatch(fact_id) is None
            or fact_id in seen_ids
            or category not in _ALLOWED_CATEGORIES
            or confidence not in {"high", "medium"}
            or verification_status not in _ALLOWED_VERIFICATION_STATUSES
            or physical_page > observed_pdf_page_count
            or printed_page > observed_pdf_page_count
            or (
                verification_status
                == "verified_against_source_with_conflict_note"
                and not notes
            )
        ):
            raise DisclosureSnapshotValidationError(
                "disclosure facts are invalid"
            )
        seen_ids.add(fact_id)
        facts.append(
            {
                "fact_id": fact_id,
                "category": category,
                "claim": claim,
                "value": value_text,
                "unit": unit,
                "period": period,
                "physical_pdf_page": physical_page,
                "dart_printed_page": printed_page,
                "section_path": list(section_path),
                "basis": basis,
                "confidence": confidence,
                "verification_status": verification_status,
                "notes": list(notes),
            }
        )
    facts.sort(key=lambda item: item["fact_id"])
    return tuple(facts)


def _correction_payload(
    correction: DisclosureCorrectionVerification,
    *,
    spec: DisclosureInputSpec,
) -> dict[str, Any]:
    if correction.status == "pending":
        return {
            "verification_status": "pending",
            "remark": None,
            "is_correction": None,
            "has_subsequent_correction": None,
            "is_withdrawn": None,
        }
    if (
        correction.status
        not in {"verified_official_api", "verified_official_viewer"}
        or not isinstance(correction.remark, str)
        or not isinstance(correction.report_name, str)
        or "분기보고서" not in correction.report_name
    ):
        raise DisclosureSnapshotValidationError(
            "disclosure correction verification is invalid"
        )
    markers = parse_report_markers(
        correction.report_name,
        spec.receipt_no,
        correction.remark,
        {},
    )
    return {
        "verification_status": correction.status,
        "remark": correction.remark,
        "is_correction": markers.is_correction,
        "has_subsequent_correction": markers.has_subsequent_correction,
        "is_withdrawn": markers.is_withdrawn,
    }


def _build_document(
    *,
    facts: Sequence[Mapping[str, Any]],
    identity: Mapping[str, str],
    spec: DisclosureInputSpec,
    correction: Mapping[str, Any],
) -> FinancialDocument:
    published_at = datetime(2026, 5, 15, tzinfo=SEOUL_TZ).astimezone(UTC)
    public_facts = [dict(item) for item in facts]
    return FinancialDocument(
        document_id=f"disclosure:{spec.receipt_no}",
        source_type="disclosure",
        provider=DISCLOSURE_PROVIDER_KEY,
        primary_security_ids=[spec.security_id],
        mentioned_security_ids=[],
        title=f"{spec.security_name} 공시 핵심: {identity['report_name']}",
        published_at=published_at,
        source_url=spec.viewer_url,
        text="\n".join(item["claim"] for item in public_facts),
        locator={
            "provider": DISCLOSURE_PROVIDER_KEY,
            "receipt_no": spec.receipt_no,
            "viewer_url": spec.viewer_url,
            "content_level": DISCLOSURE_CONTENT_LEVEL,
            "section": "verified body facts",
            "facts": public_facts,
        },
        metadata={
            "document_type": "disclosure_listing",
            "report_type": "분기보고서",
            "content_level": DISCLOSURE_CONTENT_LEVEL,
            "content_origin": "verified_public_recorded",
            "verification_status": "local_source_verified",
            "reference_title": identity["report_name"],
            "reference_publisher": "금융감독원 전자공시시스템 DART",
            "reference_url": spec.viewer_url,
            "reference_published_at": identity["submitted_at"],
            "reference_section": "verified body facts",
            "summary_author": "Questock",
            "usage_note": (
                "Verified public facts only; the full filing body is excluded."
            ),
            "ticker_source": "project_security_mapping",
            "corp_code": spec.corp_code,
            "corp_code_source": "project_security_mapping",
            "corp_code_verification_status": (
                spec.corp_code_verification_status
            ),
            "correction_verification_status": correction[
                "verification_status"
            ],
            "remark": correction["remark"],
            "is_correction": correction["is_correction"],
            "has_subsequent_correction": correction[
                "has_subsequent_correction"
            ],
            "is_withdrawn": correction["is_withdrawn"],
        },
        ingestion_version=DISCLOSURE_SNAPSHOT_INGESTION_VERSION,
    )


def _validate_output_document(
    document: FinancialDocument,
    *,
    spec: DisclosureInputSpec,
    correction: Mapping[str, Any],
) -> frozenset[str]:
    facts = document.locator.get("facts")
    if (
        document.document_id != f"disclosure:{spec.receipt_no}"
        or document.source_type != "disclosure"
        or document.provider != DISCLOSURE_PROVIDER_KEY
        or document.primary_security_ids != [spec.security_id]
        or document.mentioned_security_ids
        or document.source_url != spec.viewer_url
        or document.locator.get("receipt_no") != spec.receipt_no
        or document.locator.get("viewer_url") != spec.viewer_url
        or document.locator.get("content_level") != DISCLOSURE_CONTENT_LEVEL
        or document.metadata.get("content_level") != DISCLOSURE_CONTENT_LEVEL
        or document.title != f"{spec.security_name} 공시 핵심: {spec.report_name}"
        or document.published_at
        != datetime(2026, 5, 15, tzinfo=SEOUL_TZ).astimezone(UTC)
        or document.metadata.get("correction_verification_status")
        != correction.get("verification_status")
        or document.metadata.get("remark") != correction.get("remark")
        or document.metadata.get("is_correction")
        != correction.get("is_correction")
        or document.metadata.get("has_subsequent_correction")
        != correction.get("has_subsequent_correction")
        or document.metadata.get("is_withdrawn")
        != correction.get("is_withdrawn")
        or document.metadata.get("corp_code") != spec.corp_code
        or document.metadata.get("corp_code_verification_status")
        != spec.corp_code_verification_status
        or document.ingestion_version
        != DISCLOSURE_SNAPSHOT_INGESTION_VERSION
        or not isinstance(facts, list)
        or len(facts) < 10
    ):
        raise DisclosureSnapshotValidationError(
            "disclosure snapshot document is invalid"
        )
    categories = _validate_public_facts(facts, spec=spec)
    if document.text != "\n".join(item["claim"] for item in facts):
        raise DisclosureSnapshotValidationError(
            "disclosure snapshot document is invalid"
        )
    return categories


def _validate_public_facts(
    value: list[Any],
    *,
    spec: DisclosureInputSpec,
) -> frozenset[str]:
    seen_ids: set[str] = set()
    categories: set[str] = set()
    for fact in value:
        if (
            not isinstance(fact, dict)
            or set(fact)
            != {
                "fact_id",
                "category",
                "claim",
                "value",
                "unit",
                "period",
                "physical_pdf_page",
                "dart_printed_page",
                "section_path",
                "basis",
                "confidence",
                "verification_status",
                "notes",
            }
        ):
            raise DisclosureSnapshotValidationError(
                "disclosure snapshot facts are invalid"
            )
        fact_id = _nonblank(fact.get("fact_id"))
        category = _nonblank(fact.get("category"))
        _nonblank(fact.get("claim"))
        _optional_text(fact.get("value"))
        _optional_text(fact.get("unit"))
        _nonblank(fact.get("period"))
        physical_page = _positive_integer(fact.get("physical_pdf_page"))
        printed_page = _positive_integer(fact.get("dart_printed_page"))
        _string_sequence(fact.get("section_path"))
        _nonblank(fact.get("basis"))
        notes = _string_sequence(fact.get("notes"), allow_empty=True)
        if (
            _FACT_ID_RE.fullmatch(fact_id) is None
            or fact_id in seen_ids
            or category not in _ALLOWED_CATEGORIES
            or fact.get("confidence") not in {"high", "medium"}
            or fact.get("verification_status")
            not in _ALLOWED_VERIFICATION_STATUSES
            or physical_page > spec.pdf_page_count
            or printed_page > spec.pdf_page_count
            or (
                fact.get("verification_status")
                == "verified_against_source_with_conflict_note"
                and not notes
            )
        ):
            raise DisclosureSnapshotValidationError(
                "disclosure snapshot facts are invalid"
            )
        seen_ids.add(fact_id)
        categories.add(category)
    return frozenset(categories)


def _valid_output_identity(
    value: Mapping[str, Any],
    *,
    spec: DisclosureInputSpec,
) -> bool:
    return dict(value) == {
        "security_id": spec.security_id,
        "ticker": spec.ticker,
        "ticker_source": "project_security_mapping",
        "corp_code": spec.corp_code,
        "corp_code_source": "project_security_mapping",
        "corp_code_verification_status": spec.corp_code_verification_status,
        "company_name": spec.matrix_company_name,
        "report_name": spec.report_name,
        "report_period": "2026-01-01~2026-03-31",
        "submitted_at": "2026-05-15",
        "receipt_no": spec.receipt_no,
        "viewer_url": spec.viewer_url,
        "pdf_identity_status": "verified_from_pdf",
    }


def _valid_output_correction(value: Mapping[str, Any]) -> bool:
    if set(value) != {
        "verification_status",
        "remark",
        "is_correction",
        "has_subsequent_correction",
        "is_withdrawn",
    }:
        return False
    status = value.get("verification_status")
    if status == "pending":
        return all(
            value.get(key) is None
            for key in (
                "remark",
                "is_correction",
                "has_subsequent_correction",
                "is_withdrawn",
            )
        )
    remark = value.get("remark")
    return (
        status in {"verified_official_api", "verified_official_viewer"}
        and isinstance(remark, str)
        and value.get("is_correction") is False
        and isinstance(value.get("has_subsequent_correction"), bool)
        and value.get("has_subsequent_correction") == ("정" in remark)
        and isinstance(value.get("is_withdrawn"), bool)
        and value.get("is_withdrawn") == ("철" in remark)
    )


def _nonblank(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DisclosureSnapshotValidationError(
            "disclosure fact field is invalid"
        )
    return value.strip()


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    return _nonblank(value)


def _positive_integer(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise DisclosureSnapshotValidationError(
            "disclosure fact locator is invalid"
        )
    return value


def _string_sequence(
    value: object,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    if (
        not isinstance(value, list)
        or (not value and not allow_empty)
        or any(not isinstance(item, str) or not item.strip() for item in value)
    ):
        raise DisclosureSnapshotValidationError(
            "disclosure fact field is invalid"
        )
    return tuple(item.strip() for item in value)


def _valid_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


__all__ = [
    "DISCLOSURE_INPUT_SPECS",
    "DISCLOSURE_SNAPSHOT_INGESTION_VERSION",
    "DISCLOSURE_SNAPSHOT_SCHEMA_VERSION",
    "DisclosureCorrectionVerification",
    "DisclosureInputSpec",
    "DisclosureSnapshotValidationError",
    "build_disclosure_snapshot_payload",
    "file_sha256",
    "load_disclosure_fact_matrix",
    "validate_disclosure_snapshot_payload",
    "write_disclosure_snapshot_json",
]
