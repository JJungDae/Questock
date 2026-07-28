from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Literal
from urllib.parse import parse_qsl, urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

M5_D1_REPORT_INVENTORY_SCHEMA_VERSION = "m5-d1-report-inventory-v2"
M5_D1_REPORT_INVENTORY_PATH = Path("data/m5_d1_report_inventory.json")
M5_D1_REPORT_LOCAL_EXTRACT_SCHEMA_VERSION = (
    "m5-d1-report-local-extract-v1"
)
KST = timezone(timedelta(hours=9))
SUPPORTED_REPORT_SECURITIES = {
    "KRX:005930": ("005930", "삼성전자"),
    "KRX:000660": ("000660", "SK하이닉스"),
    "KRX:005380": ("005380", "현대차"),
}
SUPPORTED_REPORT_PUBLISHERS = {
    "삼성증권": frozenset({"samsungpop.com", "www.samsungpop.com"}),
    "미래에셋증권": frozenset({"securities.miraeasset.com"}),
    "키움증권": frozenset({"bbn.kiwoom.com"}),
}
REPORT_SELECTION_CUTOFF = date(2026, 7, 27)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REPORT_ID_RE = re.compile(r"^report:[0-9a-f]{64}$")
_WINDOWS_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")
_SECRET_QUERY_KEYS = frozenset(
    {
        "access_token",
        "apikey",
        "api_key",
        "authorization",
        "client_secret",
        "credential",
        "key",
        "secret",
        "signature",
        "token",
    }
)
_FORBIDDEN_PUBLIC_KEYS = frozenset(
    {
        "description",
        "evidence_excerpt",
        "local_path",
        "page_text",
        "pages",
        "pdf_bytes",
        "raw",
        "raw_text",
        "source_file",
        "source_pdf",
        "text",
    }
)


class M5D1ReportInventoryError(ValueError):
    """Raised when the M5-D1 report inventory is invalid."""


class _InventoryModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ReportPageChecksum(_InventoryModel):
    page: int = Field(ge=1)
    text_sha256: str
    extracted_character_count: int = Field(ge=1)

    @field_validator("text_sha256")
    @classmethod
    def validate_text_sha256(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("report page checksum is invalid")
        return value


class ReportPermissions(_InventoryModel):
    local_preprocessing_allowed: Literal[True] = True
    corpus_ingest_allowed: Literal[False] = False
    external_llm_processing_allowed: Literal[False] = False
    runtime_source_pdf_allowed: Literal[False] = False
    runtime_raw_text_allowed: Literal[False] = False
    runtime_evidence_excerpt_allowed: Literal[False] = False


class ReportInventoryItem(_InventoryModel):
    report_id: str
    security_id: str
    ticker: str
    security_name: str
    publisher: Literal["삼성증권", "미래에셋증권", "키움증권"]
    analyst: str
    title: str
    published_date: date
    available_from: datetime
    published_at_precision: Literal["date"] = "date"
    source_url: str
    pdf_sha256: str
    pdf_page_count: int = Field(ge=1)
    extracted_nonempty_page_count: int = Field(ge=0)
    extracted_character_count: int = Field(ge=0)
    page_text_checksums: tuple[ReportPageChecksum, ...]
    extraction_status: Literal[
        "text_extracted",
        "partial_text_extracted",
        "image_only_visual_review_required",
    ]
    report_scope: Literal[
        "company_specific",
        "market_strategy_with_company_focus",
    ]
    selection_status: Literal[
        "selected_for_m5_d1",
        "excluded_after_m5_d1_cutoff",
    ]
    preprocessing_status: Literal[
        "metadata_and_local_text_ready",
        "metadata_and_visual_review_ready",
        "excluded_after_cutoff_local_text_preserved",
    ]
    identity_verification_status: Literal[
        "filename_source_map_pdf_text_and_visual_review",
        "filename_source_map_and_visual_review",
        "filename_source_map_pdf_text_visual_review_pending",
    ]
    permissions: ReportPermissions

    @field_validator("report_id")
    @classmethod
    def validate_report_id(cls, value: str) -> str:
        if not _REPORT_ID_RE.fullmatch(value):
            raise ValueError("report id is invalid")
        return value

    @field_validator("security_id")
    @classmethod
    def validate_security_id(cls, value: str) -> str:
        if value not in SUPPORTED_REPORT_SECURITIES:
            raise ValueError("report security is invalid")
        return value

    @field_validator(
        "ticker",
        "security_name",
        "analyst",
        "title",
    )
    @classmethod
    def validate_nonblank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("report metadata text is invalid")
        return value

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        return _public_source_url(value)

    @field_validator("pdf_sha256")
    @classmethod
    def validate_pdf_sha256(cls, value: str) -> str:
        return _required_sha256(value)

    @field_validator("available_from")
    @classmethod
    def validate_available_from(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("report timestamp is invalid")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_identity(self) -> ReportInventoryItem:
        if (
            (self.ticker, self.security_name)
            != SUPPORTED_REPORT_SECURITIES[self.security_id]
            or urlsplit(self.source_url).hostname.casefold()
            not in SUPPORTED_REPORT_PUBLISHERS[self.publisher]
        ):
            raise ValueError("report security identity is invalid")
        return self


def build_report_inventory_payload(
    raw_reports: Sequence[Mapping[str, Any]],
    *,
    prepared_at: datetime,
    visual_review_confirmed: bool,
) -> dict[str, Any]:
    if (
        isinstance(raw_reports, (str, bytes, bytearray))
        or not isinstance(raw_reports, Sequence)
        or not raw_reports
    ):
        raise M5D1ReportInventoryError(
            "report inventory input is invalid"
        )
    prepared_at_utc = _aware_utc(prepared_at)
    items: list[ReportInventoryItem] = []
    seen_source_hashes: set[str] = set()
    for raw in raw_reports:
        if not isinstance(raw, Mapping):
            raise M5D1ReportInventoryError(
                "report inventory input is invalid"
            )
        security_id = _required_str(raw, "security_id")
        expected = SUPPORTED_REPORT_SECURITIES.get(security_id)
        ticker = _required_str(raw, "ticker")
        security_name = _required_str(raw, "security_name")
        if (
            expected is None
            or (ticker, security_name) != expected
        ):
            raise M5D1ReportInventoryError(
                "report security identity is invalid"
            )
        analyst = _required_str(raw, "analyst")
        title = _required_str(raw, "title")
        publisher = _required_publisher(raw.get("publisher"))
        published_date = _required_date(raw.get("published_date"))
        source_url = _public_source_url(
            raw.get("source_url"),
            publisher=publisher,
        )
        pdf_sha256 = _required_sha256(raw.get("pdf_sha256"))
        if pdf_sha256 in seen_source_hashes:
            raise M5D1ReportInventoryError(
                "report source duplicate is invalid"
            )
        seen_source_hashes.add(pdf_sha256)
        page_texts = raw.get("page_texts")
        if (
            isinstance(page_texts, (str, bytes, bytearray))
            or not isinstance(page_texts, Sequence)
            or not page_texts
            or any(not isinstance(text, str) for text in page_texts)
        ):
            raise M5D1ReportInventoryError(
                "report page extraction is invalid"
            )
        normalized_pages = tuple(
            _normalize_page_text(text) for text in page_texts
        )
        nonempty_pages = tuple(
            (index, text)
            for index, text in enumerate(normalized_pages, start=1)
            if text
        )
        if not nonempty_pages and not visual_review_confirmed:
            raise M5D1ReportInventoryError(
                "report page extraction is invalid"
            )
        first_page = normalized_pages[0].casefold()
        if (
            first_page
            and ticker not in first_page
            and security_name.casefold() not in first_page
        ):
            raise M5D1ReportInventoryError(
                "report first-page identity is invalid"
            )
        extraction_status: Literal[
            "text_extracted",
            "partial_text_extracted",
            "image_only_visual_review_required",
        ] = (
            "image_only_visual_review_required"
            if not nonempty_pages
            else (
                "text_extracted"
                if len(nonempty_pages) == len(normalized_pages)
                else "partial_text_extracted"
            )
        )
        selection_status: Literal[
            "selected_for_m5_d1",
            "excluded_after_m5_d1_cutoff",
        ] = (
            "selected_for_m5_d1"
            if published_date <= REPORT_SELECTION_CUTOFF
            else "excluded_after_m5_d1_cutoff"
        )
        available_from = datetime.combine(
            published_date,
            time(23, 59, 59),
            tzinfo=KST,
        ).astimezone(UTC)
        report_id = "report:" + hashlib.sha256(
            (
                f"{security_id}|{publisher}|"
                f"{published_date.isoformat()}|{title}|{pdf_sha256}"
            ).encode("utf-8")
        ).hexdigest()
        try:
            item = ReportInventoryItem(
                report_id=report_id,
                security_id=security_id,
                ticker=ticker,
                security_name=security_name,
                publisher=publisher,
                analyst=analyst,
                title=title,
                published_date=published_date,
                available_from=available_from,
                source_url=source_url,
                pdf_sha256=pdf_sha256,
                pdf_page_count=len(normalized_pages),
                extracted_nonempty_page_count=len(nonempty_pages),
                extracted_character_count=sum(
                    len(text) for _, text in nonempty_pages
                ),
                extraction_status=extraction_status,
                page_text_checksums=tuple(
                    ReportPageChecksum(
                        page=index,
                        text_sha256=hashlib.sha256(
                            text.encode("utf-8")
                        ).hexdigest(),
                        extracted_character_count=len(text),
                    )
                    for index, text in nonempty_pages
                ),
                report_scope=(
                    "market_strategy_with_company_focus"
                    if any(
                        marker in title.casefold()
                        for marker in ("etp", "msci")
                    )
                    else "company_specific"
                ),
                selection_status=selection_status,
                preprocessing_status=(
                    (
                        "metadata_and_visual_review_ready"
                        if not nonempty_pages
                        else "metadata_and_local_text_ready"
                    )
                    if selection_status == "selected_for_m5_d1"
                    else (
                        "excluded_after_cutoff_local_text_preserved"
                    )
                ),
                identity_verification_status=(
                    (
                        "filename_source_map_and_visual_review"
                        if not nonempty_pages
                        else (
                            "filename_source_map_pdf_text_and_visual_review"
                        )
                    )
                    if visual_review_confirmed
                    else (
                        "filename_source_map_pdf_text_"
                        "visual_review_pending"
                    )
                ),
                permissions=ReportPermissions(),
            )
        except ValidationError:
            raise M5D1ReportInventoryError(
                "normalized report inventory item is invalid"
            ) from None
        if not _REPORT_ID_RE.fullmatch(item.report_id):
            raise M5D1ReportInventoryError(
                "report inventory id is invalid"
            )
        items.append(item)
    items.sort(
        key=lambda item: (
            item.security_id,
            item.published_date,
            item.report_id,
        )
    )
    serialized = [item.model_dump(mode="json") for item in items]
    selected = [
        item
        for item in items
        if item.selection_status == "selected_for_m5_d1"
    ]
    source_sha256 = hashlib.sha256(
        json.dumps(
            serialized,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    payload = {
        "schema_version": M5_D1_REPORT_INVENTORY_SCHEMA_VERSION,
        "prepared_at": prepared_at_utc.isoformat().replace("+00:00", "Z"),
        "selection_rule": "supplied_verified_reports_through_2026_07_27",
        "permissions": ReportPermissions().model_dump(mode="json"),
        "coverage": {
            "discovered_count": len(items),
            "selected_count": len(selected),
            "excluded_count": len(items) - len(selected),
            "selected_by_security": dict(
                sorted(Counter(item.security_id for item in selected).items())
            ),
            "selected_by_publisher": dict(
                sorted(Counter(item.publisher for item in selected).items())
            ),
            "extraction_status_counts": dict(
                sorted(Counter(item.extraction_status for item in items).items())
            ),
            "visual_review_confirmed": visual_review_confirmed,
            "runtime_ready_count": 0,
        },
        "source_sha256": source_sha256,
        "reports": serialized,
    }
    validate_report_inventory_payload(payload)
    return payload


def validate_report_inventory_payload(
    payload: Mapping[str, Any],
) -> None:
    if (
        not isinstance(payload, Mapping)
        or payload.get("schema_version")
        != M5_D1_REPORT_INVENTORY_SCHEMA_VERSION
        or not isinstance(payload.get("reports"), list)
        or not isinstance(payload.get("coverage"), Mapping)
        or not isinstance(payload.get("permissions"), Mapping)
    ):
        raise M5D1ReportInventoryError(
            "report inventory payload is invalid"
        )
    try:
        items = tuple(
            ReportInventoryItem.model_validate(item)
            for item in payload["reports"]
        )
        _aware_utc(
            datetime.fromisoformat(
                str(payload.get("prepared_at")).replace("Z", "+00:00")
            )
        )
    except (TypeError, ValueError, ValidationError):
        raise M5D1ReportInventoryError(
            "report inventory payload is invalid"
        ) from None
    visual_review_confirmed = payload["coverage"].get(
        "visual_review_confirmed"
    )
    if type(visual_review_confirmed) is not bool:
        raise M5D1ReportInventoryError(
            "report inventory payload is invalid"
        )
    selected = [
        item
        for item in items
        if item.selection_status == "selected_for_m5_d1"
    ]
    expected_coverage = {
        "discovered_count": len(items),
        "selected_count": len(selected),
        "excluded_count": len(items) - len(selected),
        "selected_by_security": dict(
            sorted(Counter(item.security_id for item in selected).items())
        ),
        "selected_by_publisher": dict(
            sorted(Counter(item.publisher for item in selected).items())
        ),
        "extraction_status_counts": dict(
            sorted(Counter(item.extraction_status for item in items).items())
        ),
        "visual_review_confirmed": visual_review_confirmed,
        "runtime_ready_count": 0,
    }
    for item in items:
        expected_available_from = datetime.combine(
            item.published_date,
            time(23, 59, 59),
            tzinfo=KST,
        ).astimezone(UTC)
        expected_selection = (
            "selected_for_m5_d1"
            if item.published_date <= REPORT_SELECTION_CUTOFF
            else "excluded_after_m5_d1_cutoff"
        )
        expected_scope = (
            "market_strategy_with_company_focus"
            if any(
                marker in item.title.casefold()
                for marker in ("etp", "msci")
            )
            else "company_specific"
        )
        expected_preprocessing_status = (
            (
                "metadata_and_visual_review_ready"
                if item.extracted_nonempty_page_count == 0
                else "metadata_and_local_text_ready"
            )
            if expected_selection == "selected_for_m5_d1"
            else "excluded_after_cutoff_local_text_preserved"
        )
        checksums = item.page_text_checksums
        expected_extraction_status = (
            "image_only_visual_review_required"
            if item.extracted_nonempty_page_count == 0
            else (
                "text_extracted"
                if item.extracted_nonempty_page_count
                == item.pdf_page_count
                else "partial_text_extracted"
            )
        )
        if (
            item.available_from != expected_available_from
            or item.selection_status != expected_selection
            or item.report_scope != expected_scope
            or item.preprocessing_status
            != expected_preprocessing_status
            or item.extraction_status != expected_extraction_status
            or len(checksums) != item.extracted_nonempty_page_count
            or len({checksum.page for checksum in checksums})
            != len(checksums)
            or any(
                checksum.page > item.pdf_page_count
                or not _SHA256_RE.fullmatch(checksum.text_sha256)
                for checksum in checksums
            )
            or sum(
                checksum.extracted_character_count
                for checksum in checksums
            )
            != item.extracted_character_count
            or item.identity_verification_status
            != (
                (
                    "filename_source_map_and_visual_review"
                    if item.extracted_nonempty_page_count == 0
                    else (
                        "filename_source_map_pdf_text_and_visual_review"
                    )
                )
                if visual_review_confirmed
                else (
                    "filename_source_map_pdf_text_"
                    "visual_review_pending"
                )
            )
        ):
            raise M5D1ReportInventoryError(
                "report inventory payload is invalid"
            )
    if (
        len({item.report_id for item in items}) != len(items)
        or len({item.pdf_sha256 for item in items}) != len(items)
    ):
        raise M5D1ReportInventoryError(
            "report inventory payload is invalid"
        )
    if (
        payload.get("selection_rule")
        != "supplied_verified_reports_through_2026_07_27"
        or payload.get("permissions")
        != ReportPermissions().model_dump(mode="json")
        or payload.get("source_sha256")
        != hashlib.sha256(
            json.dumps(
                [
                    item.model_dump(mode="json")
                    for item in items
                ],
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        or payload.get("coverage") != expected_coverage
    ):
        raise M5D1ReportInventoryError(
            "report inventory payload is invalid"
        )
    _validate_public_payload(payload)


def write_report_inventory(
    payload: Mapping[str, Any],
    path: Path = M5_D1_REPORT_INVENTORY_PATH,
) -> None:
    validate_report_inventory_payload(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            dict(payload),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _validate_public_payload(value: object) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key).casefold() in _FORBIDDEN_PUBLIC_KEYS:
                raise M5D1ReportInventoryError(
                    "report inventory contains forbidden source content"
                )
            _validate_public_payload(nested)
        return
    if isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    ):
        for nested in value:
            _validate_public_payload(nested)
        return
    if isinstance(value, str) and _WINDOWS_PATH_RE.match(value):
        raise M5D1ReportInventoryError(
            "report inventory contains a local path"
        )


def _public_source_url(
    value: object,
    *,
    publisher: str | None = None,
) -> str:
    if not isinstance(value, str):
        raise M5D1ReportInventoryError(
            "report source URL is invalid"
        )
    try:
        parsed = urlsplit(value.strip())
    except ValueError:
        raise M5D1ReportInventoryError(
            "report source URL is invalid"
        ) from None
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.hostname.casefold()
        not in frozenset().union(*SUPPORTED_REPORT_PUBLISHERS.values())
        or (
            publisher is not None
            and parsed.hostname.casefold()
            not in SUPPORTED_REPORT_PUBLISHERS.get(
                publisher,
                frozenset(),
            )
        )
        or any(
            key.casefold() in _SECRET_QUERY_KEYS
            for key, _nested in parse_qsl(
                parsed.query,
                keep_blank_values=True,
            )
        )
    ):
        raise M5D1ReportInventoryError(
            "report source URL is invalid"
        )
    return value.strip()


def _required_publisher(value: object) -> str:
    if (
        not isinstance(value, str)
        or value.strip() not in SUPPORTED_REPORT_PUBLISHERS
    ):
        raise M5D1ReportInventoryError(
            "report publisher is invalid"
        )
    return value.strip()


def _required_str(raw: Mapping[str, Any], field: str) -> str:
    value = raw.get(field)
    if not isinstance(value, str) or not value.strip():
        raise M5D1ReportInventoryError(
            "report inventory field is invalid"
        )
    return value.strip()


def _required_date(value: object) -> date:
    if not isinstance(value, str):
        raise M5D1ReportInventoryError(
            "report publication date is invalid"
        )
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise M5D1ReportInventoryError(
            "report publication date is invalid"
        ) from None
    return parsed


def _required_sha256(value: object) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise M5D1ReportInventoryError(
            "report source hash is invalid"
        )
    return value


def _normalize_page_text(value: str) -> str:
    return "\n".join(
        line.rstrip()
        for line in value.replace("\x00", " ").splitlines()
    ).strip()


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise M5D1ReportInventoryError(
            "report inventory timestamp is invalid"
        )
    return value.astimezone(UTC)


__all__ = [
    "M5_D1_REPORT_INVENTORY_PATH",
    "M5_D1_REPORT_INVENTORY_SCHEMA_VERSION",
    "M5_D1_REPORT_LOCAL_EXTRACT_SCHEMA_VERSION",
    "M5D1ReportInventoryError",
    "ReportInventoryItem",
    "ReportPageChecksum",
    "ReportPermissions",
    "SUPPORTED_REPORT_SECURITIES",
    "SUPPORTED_REPORT_PUBLISHERS",
    "build_report_inventory_payload",
    "validate_report_inventory_payload",
    "write_report_inventory",
]
