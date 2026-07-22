from __future__ import annotations

import html
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.core.models import DateRange, FinancialDocument, ProviderResult, SecurityIdentifier
from app.core.status import ProviderStatus
from app.providers.base import create_provider_result, security_id_for

RECORDED_DISCLOSURE_PROVIDER_KEY = "recorded_disclosure"
DISCLOSURE_INGESTION_VERSION = "disclosure-provider-m1-05-v1"
DEFAULT_SECURITIES_PATH = Path(__file__).resolve().parents[2] / "data" / "securities.json"
SEOUL_TZ = timezone(timedelta(hours=9))
DART_VIEWER_BASE_URL = "https://dart.fss.or.kr/dsaf001/main.do"
_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_CORP_CODE_RE = re.compile(r"^\d{8}$")
_STOCK_CODE_RE = re.compile(r"^\d{6}$")
_RECEIPT_NO_RE = re.compile(r"^\d{14}$")
_MARKER_RE = re.compile(r"\[([^\]]+)\]")

_CORRECTION_MARKERS = {
    "\uae30\uc7ac\uc815\uc815",
    "\ucca8\ubd80\uc815\uc815",
}
_UPDATE_VARIANT_MARKERS = {
    "\ucca8\ubd80\ucd94\uac00",
    "\ubcc0\uacbd\ub4f1\ub85d",
    "\uc5f0\uc7a5\uacb0\uc815",
    "\ubc1c\ud589\uc870\uac74\uc815\uc815",
}
_CORRECTION_ORDER_MARKER = "\uc815\uc815\uba85\ub839\ubd80\uacfc"
_CORRECTION_REQUEST_MARKER = "\uc815\uc815\uc81c\ucd9c\uc694\uad6c"
_SUBSEQUENT_CORRECTION_REMARK = "\uc815"
_WITHDRAWN_REMARK = "\ucca0"


class DisclosureParseError(ValueError):
    """Raised when a recorded disclosure response cannot be normalized."""


class DisclosureRegistryError(ValueError):
    """Raised when the disclosure security registry is invalid."""


@dataclass(frozen=True)
class DisclosureSecurityRecord:
    security_id: str
    market: str
    ticker: str
    security_name: str
    security_type: str
    corp_code: str
    corp_name: str
    verification_status: str


@dataclass(frozen=True)
class DisclosureSecurityRegistry:
    records_by_id: dict[str, DisclosureSecurityRecord]

    def validate_security(self, security: SecurityIdentifier) -> bool:
        record = self.records_by_id.get(security_id_for(security))
        return (
            record is not None
            and record.market == security.market
            and record.ticker == security.ticker
            and record.security_name == security.security_name
            and record.security_type == security.security_type
            and record.security_type == "common_stock"
            and record.corp_name == security.corp_name
            and (security.corp_code is None or security.corp_code == record.corp_code)
        )

    def record_for(self, security: SecurityIdentifier) -> DisclosureSecurityRecord:
        return self.records_by_id[security_id_for(security)]


@dataclass(frozen=True)
class ParsedDisclosureItem:
    corp_cls: str
    corp_name: str
    corp_code: str
    stock_code: str
    report_name: str
    receipt_no: str
    submitter: str
    received_date: date
    remark: str
    raw_index: int


@dataclass(frozen=True)
class DisclosureMarkers:
    report_marker: str | None
    is_correction: bool
    correction_type: str | None
    correction_of: str | None
    is_update_variant: bool
    update_variant_type: str | None
    has_correction_order: bool
    has_correction_request: bool
    has_subsequent_correction: bool
    is_withdrawn: bool


def load_disclosure_security_registry(
    securities_path: str | Path = DEFAULT_SECURITIES_PATH,
) -> DisclosureSecurityRegistry:
    data = json.loads(Path(securities_path).read_text(encoding="utf-8"))
    records_by_id: dict[str, DisclosureSecurityRecord] = {}
    for item in data.get("securities", []):
        corp_code = item.get("corp_code")
        ticker = item.get("ticker")
        if not isinstance(corp_code, str) or not _CORP_CODE_RE.fullmatch(corp_code):
            raise DisclosureRegistryError("registry corp_code must be exactly 8 digits")
        if not isinstance(ticker, str) or not _STOCK_CODE_RE.fullmatch(ticker):
            raise DisclosureRegistryError("registry ticker must be exactly 6 digits")
        record = DisclosureSecurityRecord(
            security_id=item["security_id"],
            market=item["market"],
            ticker=ticker,
            security_name=item["security_name"],
            security_type=item["security_type"],
            corp_code=corp_code,
            corp_name=item["corp_name"],
            verification_status=item["verification_status"],
        )
        records_by_id[record.security_id] = record
    return DisclosureSecurityRegistry(records_by_id=records_by_id)


def map_opendart_status(status: Any) -> ProviderStatus:
    if not isinstance(status, str):
        return ProviderStatus.PARSE_ERROR
    if status == "000":
        return ProviderStatus.OK
    if status == "013":
        return ProviderStatus.NO_DATA
    if status in {"010", "011", "012", "101", "901"}:
        return ProviderStatus.UNAUTHORIZED
    if status == "020":
        return ProviderStatus.RATE_LIMITED
    if status in {"021", "100"}:
        return ProviderStatus.INVALID_QUERY
    if status in {"014", "800", "900"}:
        return ProviderStatus.PROVIDER_UNAVAILABLE
    return ProviderStatus.PROVIDER_UNAVAILABLE


def normalize_opendart_disclosure_response(
    response: Any,
    *,
    security: SecurityIdentifier,
    query: str | None,
    date_range: DateRange | None,
    provider_key: str,
    ingestion_version: str,
    registry: DisclosureSecurityRegistry,
    correction_links: dict[str, str],
) -> list[FinancialDocument]:
    items = _extract_items(response)
    if not items:
        return []

    valid_items: list[ParsedDisclosureItem] = []
    for raw_index, raw_item in enumerate(items):
        parsed = _parse_item(raw_item, raw_index)
        if parsed is not None:
            valid_items.append(parsed)
    if not valid_items:
        raise DisclosureParseError("all disclosure items are malformed")

    target_record = registry.record_for(security)
    normalized_query = _normalize_query_text(query)
    documents: list[tuple[date, str, int, FinancialDocument]] = []
    seen_receipts: set[str] = set()
    for item in valid_items:
        if item.receipt_no in seen_receipts:
            continue
        if not _matches_target(item, target_record):
            continue
        if not _is_in_date_range(item.received_date, date_range):
            continue
        if normalized_query and not _matches_query(item, normalized_query):
            continue

        seen_receipts.add(item.receipt_no)
        document = _build_document(
            item=item,
            target_record=target_record,
            provider_key=provider_key,
            ingestion_version=ingestion_version,
            query=query,
            correction_links=correction_links,
        )
        documents.append((item.received_date, item.receipt_no, item.raw_index, document))

    documents.sort(key=lambda entry: (entry[0], entry[1]), reverse=True)
    return [entry[3] for entry in documents]


class RecordedDisclosureProvider:
    key = RECORDED_DISCLOSURE_PROVIDER_KEY

    def __init__(
        self,
        recorded_fixture: dict[str, Any] | None = None,
        fixture_path: str | Path | None = None,
        securities_path: str | Path = DEFAULT_SECURITIES_PATH,
        provider_key: str = RECORDED_DISCLOSURE_PROVIDER_KEY,
        ingestion_version: str = DISCLOSURE_INGESTION_VERSION,
    ) -> None:
        self.key = provider_key
        self._fixture = recorded_fixture
        if fixture_path is not None:
            self._fixture = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
        if self._fixture is None:
            self._fixture = _response_fixture({"status": "000", "message": "OK", "list": []})
        self._ingestion_version = ingestion_version
        self._registry = load_disclosure_security_registry(securities_path)

    async def fetch(
        self,
        security: SecurityIdentifier,
        query: str | None = None,
        date_range: DateRange | None = None,
        attempt_timeout_seconds: float = 8,
    ) -> ProviderResult[list[FinancialDocument]]:
        if not self._registry.validate_security(security):
            return create_provider_result(status=ProviderStatus.INVALID_QUERY, message="invalid security")
        if query is not None and not _normalize_query_text(query):
            return create_provider_result(status=ProviderStatus.INVALID_QUERY, message="invalid query")

        case = self._fixture.get("case")
        if case == "timeout":
            return create_provider_result(status=ProviderStatus.TIMEOUT, message="timeout")
        if case == "network_error":
            return create_provider_result(status=ProviderStatus.PROVIDER_UNAVAILABLE, message="network error")
        if case not in {None, "response"}:
            return create_provider_result(status=ProviderStatus.PROVIDER_UNAVAILABLE, message="unknown fixture")

        response = self._fixture.get("response")
        if not isinstance(response, dict):
            return create_provider_result(status=ProviderStatus.PARSE_ERROR, message="parse error")
        mapped_status = map_opendart_status(response.get("status"))
        if mapped_status != ProviderStatus.OK:
            return create_provider_result(status=mapped_status, message=mapped_status.value)

        try:
            documents = normalize_opendart_disclosure_response(
                response,
                security=security,
                query=query,
                date_range=date_range,
                provider_key=self.key,
                ingestion_version=self._ingestion_version,
                registry=self._registry,
                correction_links=_correction_links_from_fixture(self._fixture),
            )
        except DisclosureParseError:
            return create_provider_result(status=ProviderStatus.PARSE_ERROR, message="parse error")

        if not documents:
            return create_provider_result(status=ProviderStatus.NO_DATA, message="no disclosure data")
        return create_provider_result(status=ProviderStatus.OK, data=documents)


def _response_fixture(response: dict[str, Any]) -> dict[str, Any]:
    return {
        "fixture_version": 1,
        "fixture_type": "synthetic_unit",
        "case": "response",
        "response": response,
        "extensions": {"correction_links": {}},
    }


def _correction_links_from_fixture(fixture: dict[str, Any]) -> dict[str, str]:
    extensions = fixture.get("extensions")
    if not isinstance(extensions, dict):
        return {}
    raw_links = extensions.get("correction_links")
    if not isinstance(raw_links, dict):
        return {}
    return {
        key: value
        for key, value in raw_links.items()
        if isinstance(key, str) and _RECEIPT_NO_RE.fullmatch(key) and isinstance(value, str) and _RECEIPT_NO_RE.fullmatch(value)
    }


def _extract_items(response: Any) -> list[Any]:
    if not isinstance(response, dict):
        raise DisclosureParseError("disclosure response must be an object")
    if response.get("status") != "000":
        raise DisclosureParseError("disclosure response must be successful")
    items = response.get("list")
    if not isinstance(items, list):
        raise DisclosureParseError("disclosure response list must be a list")
    return items


def _parse_item(raw_item: Any, raw_index: int) -> ParsedDisclosureItem | None:
    if not isinstance(raw_item, dict):
        return None
    required = {
        "corp_code": _required_clean(raw_item.get("corp_code")),
        "corp_name": _required_clean(raw_item.get("corp_name")),
        "stock_code": _required_clean(raw_item.get("stock_code")),
        "report_nm": _required_clean(raw_item.get("report_nm")),
        "rcept_no": _required_clean(raw_item.get("rcept_no")),
        "rcept_dt": _required_clean(raw_item.get("rcept_dt")),
    }
    if any(value is None for value in required.values()):
        return None
    corp_code = required["corp_code"]
    stock_code = required["stock_code"]
    receipt_no = required["rcept_no"]
    received_date_text = required["rcept_dt"]
    report_name = required["report_nm"]
    if not (
        _CORP_CODE_RE.fullmatch(corp_code)
        and _STOCK_CODE_RE.fullmatch(stock_code)
        and _RECEIPT_NO_RE.fullmatch(receipt_no)
    ):
        return None
    received_date = _parse_received_date(received_date_text)
    if received_date is None:
        return None
    return ParsedDisclosureItem(
        corp_cls=_optional_clean(raw_item.get("corp_cls")),
        corp_name=required["corp_name"],
        corp_code=corp_code,
        stock_code=stock_code,
        report_name=report_name,
        receipt_no=receipt_no,
        submitter=_optional_clean(raw_item.get("flr_nm")),
        received_date=received_date,
        remark=_optional_clean(raw_item.get("rm")),
        raw_index=raw_index,
    )


def _required_clean(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = _clean_text(value)
    return cleaned or None


def _optional_clean(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return _clean_text(value)


def _parse_received_date(value: str) -> date | None:
    try:
        return datetime.strptime(value, "%Y%m%d").date()
    except ValueError:
        return None


def _matches_target(item: ParsedDisclosureItem, target_record: DisclosureSecurityRecord) -> bool:
    return item.corp_code == target_record.corp_code and item.stock_code == target_record.ticker


def _is_in_date_range(received_date: date, date_range: DateRange | None) -> bool:
    if date_range is None:
        return True
    if date_range.start is not None and received_date < date_range.start:
        return False
    if date_range.end is not None and received_date > date_range.end:
        return False
    return True


def _matches_query(item: ParsedDisclosureItem, normalized_query: str) -> bool:
    search_fields = (item.report_name, item.submitter, item.remark)
    return any(normalized_query in _normalize_query_text(value) for value in search_fields)


def _build_document(
    *,
    item: ParsedDisclosureItem,
    target_record: DisclosureSecurityRecord,
    provider_key: str,
    ingestion_version: str,
    query: str | None,
    correction_links: dict[str, str],
) -> FinancialDocument:
    markers = parse_report_markers(item.report_name, item.receipt_no, item.remark, correction_links)
    viewer_url = build_dart_viewer_url(item.receipt_no)
    received_date_text = item.received_date.strftime("%Y%m%d")
    published_at = datetime(
        item.received_date.year,
        item.received_date.month,
        item.received_date.day,
        tzinfo=SEOUL_TZ,
    ).astimezone(UTC)
    locator = {
        "provider": provider_key,
        "receipt_no": item.receipt_no,
        "viewer_url": viewer_url,
        "corp_code": item.corp_code,
        "stock_code": item.stock_code,
        "corp_name": item.corp_name,
        "report_name": item.report_name,
        "received_date": received_date_text,
    }
    metadata = {
        "content_level": "listing_metadata",
        "corp_cls": item.corp_cls,
        "submitter": item.submitter,
        "remark": item.remark,
        "report_marker": markers.report_marker,
        "is_correction": markers.is_correction,
        "correction_type": markers.correction_type,
        "correction_of": markers.correction_of,
        "is_update_variant": markers.is_update_variant,
        "update_variant_type": markers.update_variant_type,
        "has_correction_order": markers.has_correction_order,
        "has_correction_request": markers.has_correction_request,
        "has_subsequent_correction": markers.has_subsequent_correction,
        "is_withdrawn": markers.is_withdrawn,
        "corp_code_verification_status": target_record.verification_status,
        "published_at_precision": "date",
        "timezone_basis": "Asia/Seoul",
        "received_date": received_date_text,
        "query_filter": _normalize_query_text(query) if query is not None else None,
    }
    return FinancialDocument(
        document_id=f"disclosure:{item.receipt_no}",
        source_type="disclosure",
        provider=provider_key,
        primary_security_ids=[target_record.security_id],
        mentioned_security_ids=[],
        title=item.report_name,
        published_at=published_at,
        source_url=viewer_url,
        text=_document_text(item, markers),
        locator=locator,
        metadata=metadata,
        ingestion_version=ingestion_version,
    )


def build_dart_viewer_url(receipt_no: str) -> str:
    return f"{DART_VIEWER_BASE_URL}?rcpNo={receipt_no}"


def parse_report_markers(
    report_name: str,
    receipt_no: str,
    remark: str,
    correction_links: dict[str, str],
) -> DisclosureMarkers:
    marker = next(iter(_MARKER_RE.findall(report_name)), None)
    is_explicit_correction = receipt_no in correction_links
    is_correction_marker = marker in _CORRECTION_MARKERS
    is_update_variant = marker in _UPDATE_VARIANT_MARKERS
    has_correction_order = marker == _CORRECTION_ORDER_MARKER
    has_correction_request = marker == _CORRECTION_REQUEST_MARKER
    correction_type: str | None = None
    if is_correction_marker:
        correction_type = "report_marker"
    elif is_explicit_correction:
        correction_type = "explicit_link"
    return DisclosureMarkers(
        report_marker=marker,
        is_correction=is_correction_marker or is_explicit_correction,
        correction_type=correction_type,
        correction_of=correction_links.get(receipt_no),
        is_update_variant=is_update_variant,
        update_variant_type=marker if is_update_variant else None,
        has_correction_order=has_correction_order,
        has_correction_request=has_correction_request,
        has_subsequent_correction=_SUBSEQUENT_CORRECTION_REMARK in remark,
        is_withdrawn=_WITHDRAWN_REMARK in remark,
    )


def _document_text(item: ParsedDisclosureItem, markers: DisclosureMarkers) -> str:
    parts = [
        f"Report: {item.report_name}",
        f"Company: {item.corp_name}",
        f"Submitter: {item.submitter}",
        f"Received date: {item.received_date.strftime('%Y%m%d')}",
    ]
    if markers.is_correction:
        parts.append("Correction: yes")
    if markers.is_update_variant:
        parts.append("Update variant: yes")
    if markers.has_correction_order:
        parts.append("Correction order: yes")
    if markers.has_correction_request:
        parts.append("Correction request: yes")
    if markers.has_subsequent_correction:
        parts.append("Subsequent correction exists: yes")
    if markers.is_withdrawn:
        parts.append("Withdrawn: yes")
    return "\n".join(parts)


def _clean_text(value: str) -> str:
    unescaped = html.unescape(value)
    without_tags = _TAG_RE.sub(" ", unescaped)
    normalized = unicodedata.normalize("NFKC", without_tags)
    return _WHITESPACE_RE.sub(" ", normalized).strip()


def _normalize_query_text(value: str | None) -> str:
    if value is None:
        return ""
    return _WHITESPACE_RE.sub(" ", _clean_text(value)).strip().casefold()


__all__ = [
    "DISCLOSURE_INGESTION_VERSION",
    "RECORDED_DISCLOSURE_PROVIDER_KEY",
    "DisclosureParseError",
    "DisclosureRegistryError",
    "DisclosureSecurityRegistry",
    "RecordedDisclosureProvider",
    "build_dart_viewer_url",
    "load_disclosure_security_registry",
    "map_opendart_status",
    "normalize_opendart_disclosure_response",
    "parse_report_markers",
]
