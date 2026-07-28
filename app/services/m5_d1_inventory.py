from __future__ import annotations

import hashlib
import html
import json
import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.services.m5_news_snapshot import SECURITY_TERMS

M5_D1_INVENTORY_SCHEMA_VERSION = "m5-d1-source-inventory-v1"
M5_D1_INVENTORY_PATH = Path(
    "var/service_completion/m5_d1/inventory/m5_d1_source_inventory.json"
)
KST = timezone(timedelta(hours=9))
NEWS_WINDOW_START = datetime(2026, 7, 24, 0, 0, tzinfo=KST)
NEWS_WINDOW_END = datetime(2026, 7, 27, 21, 0, tzinfo=KST)
DISCLOSURE_WINDOW_START = date(2026, 1, 1)
DISCLOSURE_WINDOW_END = date(2026, 7, 27)
CHECKPOINT_TIMES = (
    time(8, 30),
    time(10, 0),
    time(14, 0),
    time(19, 0),
    time(21, 0),
)
SECURITY_DART_IDENTITIES: dict[str, tuple[str, str, str]] = {
    "KRX:005930": ("005930", "00126380", "삼성전자"),
    "KRX:000660": ("000660", "00164779", "SK하이닉스"),
    "KRX:005380": ("005380", "00164742", "현대자동차"),
}

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_RECEIPT_RE = re.compile(r"^\d{14}$")
_DATE_RE = re.compile(r"^\d{8}$")
_LINEAGE_PREFIX_RE = re.compile(
    r"^(?:\[(?:기재정정|첨부정정|첨부추가|변경등록|발행조건확정|"
    r"정정명령부과|정정제출요구|정정|철회|연장결정)\]\s*)+"
)
_CORRECTION_PREFIX_RE = re.compile(
    r"^(?:\[(?:기재정정|첨부정정|첨부추가|변경등록|발행조건확정|"
    r"정정명령부과|정정제출요구|정정)\]\s*)+"
)
_TRACKING_QUERY_KEYS = frozenset(
    {
        "fbclid",
        "gclid",
        "mc_cid",
        "mc_eid",
        "ref",
        "source",
    }
)
_SK_HYNIX_EXTRA_TITLE_ALIASES = ("삼전닉스",)
_SK_HYNIX_DESCRIPTION_MAX_ALIAS_OFFSET = 100
_SK_HYNIX_DESCRIPTION_TITLE_TERMS = (
    "ADR",
    "AI",
    "CXMT",
    "ETF",
    "FOMC",
    "HBM",
    "낸드",
    "레버리지",
    "메모리",
    "반도체",
    "실적",
    "주가",
    "증시",
    "코스피",
    "키옥시아",
    "투자",
)


class M5D1InventoryError(ValueError):
    """Raised when the M5-D1 source inventory is invalid."""


class _InventoryModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class NewsInventoryItem(_InventoryModel):
    news_id: str
    security_id: str
    title: str
    publisher: str
    publisher_host: str
    published_at: datetime
    canonical_url: str
    provider_item_id: str | None = None
    content_level: Literal["source_title_only"] = "source_title_only"
    security_match_basis: Literal[
        "title_alias",
        "provider_description_alias",
    ]
    collected_at: datetime
    query_provenance: tuple[str, ...] = Field(min_length=1)

    @field_validator("security_id")
    @classmethod
    def validate_security_id(cls, value: str) -> str:
        if value not in SECURITY_TERMS:
            raise ValueError("unsupported news security")
        return value

    @field_validator("published_at", "collected_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("news timestamp must be timezone-aware")
        return value.astimezone(UTC)

    @field_validator("canonical_url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise ValueError("news URL is invalid")
        return value


class DisclosureInventoryItem(_InventoryModel):
    disclosure_id: str
    security_id: str
    receipt_no: str
    corp_code: str
    stock_code: str
    company_name: str
    report_name: str
    submitter_name: str
    submitted_date: date
    available_from: datetime
    published_at_precision: Literal["date"] = "date"
    viewer_url: str
    report_category: Literal[
        "periodic",
        "material_event",
        "securities",
        "ownership",
        "other",
    ]
    correction_status: Literal[
        "original",
        "correction",
        "superseded",
        "withdrawal",
        "unknown",
    ]
    lineage_key: str
    lineage_status: Literal["candidate_only"] = "candidate_only"
    remark: str

    @field_validator("security_id")
    @classmethod
    def validate_security_id(cls, value: str) -> str:
        if value not in SECURITY_DART_IDENTITIES:
            raise ValueError("unsupported disclosure security")
        return value

    @field_validator("receipt_no")
    @classmethod
    def validate_receipt_no(cls, value: str) -> str:
        if not _RECEIPT_RE.fullmatch(value):
            raise ValueError("disclosure receipt number is invalid")
        return value

    @field_validator("available_from")
    @classmethod
    def validate_available_from(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("disclosure timestamp must be timezone-aware")
        return value.astimezone(UTC)


def validate_corp_code_registry(
    raw_entries: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, str]]:
    if isinstance(raw_entries, (str, bytes, bytearray)):
        raise M5D1InventoryError("OpenDART corporation registry is invalid")
    by_stock: dict[str, Mapping[str, Any]] = {}
    for item in raw_entries:
        if not isinstance(item, Mapping):
            continue
        stock_code = _clean_text(item.get("stock_code"))
        if stock_code:
            by_stock[stock_code] = item
    output: dict[str, dict[str, str]] = {}
    for security_id, (stock_code, corp_code, expected_name) in (
        SECURITY_DART_IDENTITIES.items()
    ):
        item = by_stock.get(stock_code)
        if (
            item is None
            or _clean_text(item.get("corp_code")) != corp_code
            or expected_name not in _clean_text(item.get("corp_name"))
        ):
            raise M5D1InventoryError(
                "OpenDART corporation mapping is invalid"
            )
        output[security_id] = {
            "stock_code": stock_code,
            "corp_code": corp_code,
            "corp_name": _clean_text(item.get("corp_name")),
            "verification_status": "verified_official_api",
        }
    return output


def normalize_news_inventory(
    raw_items_by_security: Mapping[
        str,
        Sequence[Mapping[str, Any]],
    ],
    *,
    collected_at: datetime,
) -> tuple[tuple[NewsInventoryItem, ...], dict[str, int]]:
    if set(raw_items_by_security) != set(SECURITY_TERMS):
        raise M5D1InventoryError("news inventory securities are invalid")
    collected = _aware_utc(collected_at)
    rejection_counts: Counter[str] = Counter()
    by_url: dict[tuple[str, str], dict[str, Any]] = {}
    for security_id, raw_items in raw_items_by_security.items():
        if isinstance(raw_items, (str, bytes, bytearray)):
            raise M5D1InventoryError("news inventory input is invalid")
        _security_name, aliases = SECURITY_TERMS[security_id]
        for raw in raw_items:
            if not isinstance(raw, Mapping):
                rejection_counts["invalid_item"] += 1
                continue
            title = _clean_text(raw.get("title"))
            published_at = _news_timestamp(raw.get("pubDate"))
            canonical_url = _canonical_news_url(
                raw.get("originallink"),
                raw.get("link"),
            )
            if not title or published_at is None or canonical_url is None:
                rejection_counts["invalid_metadata"] += 1
                continue
            if not (
                NEWS_WINDOW_START.astimezone(UTC)
                <= published_at
                <= NEWS_WINDOW_END.astimezone(UTC)
            ):
                rejection_counts["outside_window"] += 1
                continue
            security_match_basis = _security_match_basis(
                security_id=security_id,
                title=title,
                description=raw.get("description"),
                aliases=aliases,
            )
            if security_match_basis is None:
                rejection_counts["security_not_established"] += 1
                continue
            provenance = _query_provenance(raw)
            key = (security_id, canonical_url)
            existing = by_url.get(key)
            if existing is not None:
                existing["query_provenance"].update(provenance)
                if security_match_basis == "title_alias":
                    existing["security_match_basis"] = "title_alias"
                rejection_counts["exact_url_duplicate"] += 1
                continue
            publisher_host = _publisher_host(canonical_url)
            provider_item_id = _provider_item_id(raw.get("link"))
            digest = hashlib.sha256(
                f"{security_id}|{canonical_url}".encode("utf-8")
            ).hexdigest()
            by_url[key] = {
                "news_id": f"news:{digest}",
                "security_id": security_id,
                "title": title,
                "publisher": publisher_host,
                "publisher_host": publisher_host,
                "published_at": published_at,
                "canonical_url": canonical_url,
                "provider_item_id": provider_item_id,
                "content_level": "source_title_only",
                "security_match_basis": security_match_basis,
                "collected_at": collected,
                "query_provenance": set(provenance),
            }
    items: list[NewsInventoryItem] = []
    for raw in by_url.values():
        raw["query_provenance"] = tuple(sorted(raw["query_provenance"]))
        try:
            items.append(NewsInventoryItem.model_validate(raw))
        except ValidationError:
            raise M5D1InventoryError("normalized news item is invalid") from None
    items.sort(
        key=lambda item: (
            item.security_id,
            item.published_at,
            item.news_id,
        )
    )
    rejection_counts["retained"] = len(items)
    return tuple(items), dict(sorted(rejection_counts.items()))


def normalize_disclosure_inventory(
    raw_items_by_security: Mapping[
        str,
        Sequence[Mapping[str, Any]],
    ],
) -> tuple[DisclosureInventoryItem, ...]:
    if set(raw_items_by_security) != set(SECURITY_DART_IDENTITIES):
        raise M5D1InventoryError(
            "disclosure inventory securities are invalid"
        )
    output: list[DisclosureInventoryItem] = []
    seen_receipts: set[str] = set()
    for security_id, raw_items in raw_items_by_security.items():
        if isinstance(raw_items, (str, bytes, bytearray)):
            raise M5D1InventoryError(
                "disclosure inventory input is invalid"
            )
        expected_stock, expected_corp, expected_name = (
            SECURITY_DART_IDENTITIES[security_id]
        )
        for raw in raw_items:
            if not isinstance(raw, Mapping):
                raise M5D1InventoryError(
                    "disclosure inventory item is invalid"
                )
            receipt_no = _clean_text(raw.get("rcept_no"))
            corp_code = _clean_text(raw.get("corp_code"))
            stock_code = _clean_text(raw.get("stock_code"))
            company_name = _clean_text(raw.get("corp_name"))
            report_name = _clean_text(raw.get("report_nm"))
            submitter_name = _clean_text(raw.get("flr_nm"))
            submitted_date = _dart_date(raw.get("rcept_dt"))
            remark = _clean_text(raw.get("rm"), allow_empty=True)
            if (
                not _RECEIPT_RE.fullmatch(receipt_no)
                or receipt_no in seen_receipts
                or corp_code != expected_corp
                or stock_code != expected_stock
                or expected_name not in company_name
                or not report_name
                or not submitter_name
                or submitted_date is None
                or not (
                    DISCLOSURE_WINDOW_START
                    <= submitted_date
                    <= DISCLOSURE_WINDOW_END
                )
            ):
                raise M5D1InventoryError(
                    "disclosure inventory item is invalid"
                )
            seen_receipts.add(receipt_no)
            available_from = datetime.combine(
                submitted_date,
                time(23, 59, 59),
                tzinfo=KST,
            )
            try:
                output.append(
                    DisclosureInventoryItem(
                        disclosure_id=f"disclosure:{receipt_no}",
                        security_id=security_id,
                        receipt_no=receipt_no,
                        corp_code=corp_code,
                        stock_code=stock_code,
                        company_name=company_name,
                        report_name=report_name,
                        submitter_name=submitter_name,
                        submitted_date=submitted_date,
                        available_from=available_from,
                        viewer_url=(
                            "https://dart.fss.or.kr/dsaf001/main.do"
                            f"?rcpNo={receipt_no}"
                        ),
                        report_category=_report_category(report_name),
                        correction_status=_correction_status(
                            report_name,
                            remark,
                        ),
                        lineage_key=_lineage_key(
                            security_id,
                            report_name,
                        ),
                        remark=remark,
                    )
                )
            except ValidationError:
                raise M5D1InventoryError(
                    "normalized disclosure item is invalid"
                ) from None
    output.sort(
        key=lambda item: (
            item.security_id,
            item.submitted_date,
            item.receipt_no,
        )
    )
    return tuple(output)


def build_source_inventory_payload(
    *,
    news_items: Sequence[NewsInventoryItem],
    disclosure_items: Sequence[DisclosureInventoryItem],
    corp_registry: Mapping[str, Mapping[str, str]],
    news_rejections: Mapping[str, int],
    collected_at: datetime,
    provider_calls: Mapping[str, int],
) -> dict[str, Any]:
    _validate_sequence(news_items, NewsInventoryItem, "news")
    _validate_sequence(
        disclosure_items,
        DisclosureInventoryItem,
        "disclosure",
    )
    if set(corp_registry) != set(SECURITY_DART_IDENTITIES):
        raise M5D1InventoryError("corporation registry coverage is invalid")
    if (
        set(provider_calls) != {"naver", "opendart"}
        or any(
            type(value) is not int or value < 0
            for value in provider_calls.values()
        )
    ):
        raise M5D1InventoryError("provider call inventory is invalid")
    serialized_news = [
        item.model_dump(mode="json") for item in news_items
    ]
    serialized_disclosures = [
        item.model_dump(mode="json") for item in disclosure_items
    ]
    checksum_news = [
        {
            key: value
            for key, value in item.items()
            if key != "collected_at"
        }
        for item in serialized_news
    ]
    source_checksum = hashlib.sha256(
        json.dumps(
            {
                "news": checksum_news,
                "disclosures": serialized_disclosures,
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": M5_D1_INVENTORY_SCHEMA_VERSION,
        "collected_at": _aware_utc(collected_at)
        .isoformat()
        .replace("+00:00", "Z"),
        "windows": {
            "news_start": NEWS_WINDOW_START.isoformat(),
            "news_end": NEWS_WINDOW_END.isoformat(),
            "disclosure_start": DISCLOSURE_WINDOW_START.isoformat(),
            "disclosure_end": DISCLOSURE_WINDOW_END.isoformat(),
        },
        "provider_calls": dict(sorted(provider_calls.items())),
        "corp_registry": {
            key: dict(sorted(value.items()))
            for key, value in sorted(corp_registry.items())
        },
        "news_rejections": dict(sorted(news_rejections.items())),
        "coverage": {
            "news": _news_coverage(news_items),
            "disclosures": _disclosure_coverage(disclosure_items),
        },
        "source_sha256": source_checksum,
        "news_items": serialized_news,
        "disclosure_items": serialized_disclosures,
    }


def validate_source_inventory_payload(
    payload: Mapping[str, Any],
) -> None:
    if (
        not isinstance(payload, Mapping)
        or payload.get("schema_version")
        != M5_D1_INVENTORY_SCHEMA_VERSION
        or not isinstance(payload.get("news_items"), list)
        or not isinstance(payload.get("disclosure_items"), list)
        or not isinstance(payload.get("corp_registry"), Mapping)
        or not isinstance(payload.get("news_rejections"), Mapping)
        or not isinstance(payload.get("provider_calls"), Mapping)
    ):
        raise M5D1InventoryError("source inventory payload is invalid")
    try:
        news_items = tuple(
            NewsInventoryItem.model_validate(item)
            for item in payload["news_items"]
        )
        disclosure_items = tuple(
            DisclosureInventoryItem.model_validate(item)
            for item in payload["disclosure_items"]
        )
        collected_at = datetime.fromisoformat(
            str(payload.get("collected_at")).replace("Z", "+00:00")
        )
    except (TypeError, ValueError, ValidationError):
        raise M5D1InventoryError("source inventory payload is invalid") from None
    canonical = build_source_inventory_payload(
        news_items=news_items,
        disclosure_items=disclosure_items,
        corp_registry=payload["corp_registry"],
        news_rejections=payload["news_rejections"],
        collected_at=collected_at,
        provider_calls=payload["provider_calls"],
    )
    if dict(payload) != canonical:
        raise M5D1InventoryError("source inventory payload is invalid")


def write_source_inventory(
    payload: Mapping[str, Any],
    path: Path = M5_D1_INVENTORY_PATH,
) -> None:
    validate_source_inventory_payload(payload)
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


def _news_coverage(
    items: Sequence[NewsInventoryItem],
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for security_id in SECURITY_TERMS:
        scoped = [item for item in items if item.security_id == security_id]
        by_day = Counter(
            item.published_at.astimezone(KST).date().isoformat()
            for item in scoped
        )
        hosts = Counter(item.publisher_host for item in scoped)
        by_title: dict[str, set[str]] = defaultdict(set)
        for item in scoped:
            by_title[_normalized_title(item.title)].add(item.publisher_host)
        same_title_multi_publisher = sum(
            len(hosts_for_title) > 1
            for hosts_for_title in by_title.values()
        )
        checkpoint_counts: dict[str, int] = {}
        for day in (
            date(2026, 7, 24),
            date(2026, 7, 25),
            date(2026, 7, 26),
            date(2026, 7, 27),
        ):
            for checkpoint_time in CHECKPOINT_TIMES:
                checkpoint = datetime.combine(
                    day,
                    checkpoint_time,
                    tzinfo=KST,
                )
                key = checkpoint.strftime("%Y%m%dT%H%MKST")
                checkpoint_counts[key] = sum(
                    NEWS_WINDOW_START
                    <= item.published_at.astimezone(KST)
                    <= checkpoint
                    for item in scoped
                )
        output[security_id] = {
            "total": len(scoped),
            "by_day": dict(sorted(by_day.items())),
            "publisher_hosts": dict(sorted(hosts.items())),
            "publisher_host_count": len(hosts),
            "same_title_multi_publisher_groups": (
                same_title_multi_publisher
            ),
            "by_security_match_basis": dict(
                sorted(
                    Counter(
                        item.security_match_basis for item in scoped
                    ).items()
                )
            ),
            "checkpoint_cumulative_counts": checkpoint_counts,
        }
    return output


def _disclosure_coverage(
    items: Sequence[DisclosureInventoryItem],
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for security_id in SECURITY_DART_IDENTITIES:
        scoped = [
            item for item in items if item.security_id == security_id
        ]
        output[security_id] = {
            "total": len(scoped),
            "by_category": dict(
                sorted(Counter(item.report_category for item in scoped).items())
            ),
            "by_correction_status": dict(
                sorted(
                    Counter(
                        item.correction_status for item in scoped
                    ).items()
                )
            ),
            "lineage_candidate_count": len(
                {item.lineage_key for item in scoped}
            ),
        }
    return output


def _validate_sequence(
    values: Sequence[Any],
    expected_type: type[Any],
    label: str,
) -> None:
    if (
        isinstance(values, (str, bytes, bytearray))
        or any(not isinstance(item, expected_type) for item in values)
    ):
        raise M5D1InventoryError(f"{label} inventory is invalid")


def _clean_text(value: object, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        return "" if allow_empty else ""
    normalized = _WHITESPACE_RE.sub(
        " ",
        html.unescape(_TAG_RE.sub("", value)),
    ).strip()
    return normalized


def _news_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    from email.utils import parsedate_to_datetime

    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(UTC)


def _canonical_news_url(*values: object) -> str | None:
    for value in values:
        if not isinstance(value, str):
            continue
        try:
            parsed = urlsplit(value.strip())
        except ValueError:
            continue
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
        ):
            continue
        query = [
            (key, nested)
            for key, nested in parse_qsl(
                parsed.query,
                keep_blank_values=True,
            )
            if not key.casefold().startswith("utm_")
            and key.casefold() not in _TRACKING_QUERY_KEYS
        ]
        return urlunsplit(
            (
                parsed.scheme.casefold(),
                parsed.netloc.casefold(),
                parsed.path or "/",
                urlencode(query, doseq=True),
                "",
            )
        )
    return None


def _publisher_host(value: str) -> str:
    host = urlsplit(value).hostname
    if not host:
        raise M5D1InventoryError("news publisher host is invalid")
    normalized = host.casefold()
    return normalized[4:] if normalized.startswith("www.") else normalized


def _provider_item_id(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return hashlib.sha256(value.strip().encode("utf-8")).hexdigest()


def _query_provenance(raw: Mapping[str, Any]) -> tuple[str, ...]:
    value = raw.get("_questock_query_provenance")
    if isinstance(value, str) and value.strip():
        return (value.strip(),)
    if isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    ):
        output = tuple(
            sorted(
                {
                    item.strip()
                    for item in value
                    if isinstance(item, str) and item.strip()
                }
            )
        )
        if output:
            return output
    return ("legacy_unknown_query",)


def _security_match_basis(
    *,
    security_id: str,
    title: str,
    description: object,
    aliases: Sequence[str],
) -> Literal[
    "title_alias",
    "provider_description_alias",
] | None:
    title_aliases = tuple(aliases)
    if security_id == "KRX:000660":
        title_aliases = (
            *title_aliases,
            *_SK_HYNIX_EXTRA_TITLE_ALIASES,
        )
    normalized_title = title.casefold()
    if any(
        alias.casefold() in normalized_title
        for alias in title_aliases
    ):
        return "title_alias"
    if security_id != "KRX:000660":
        return None
    normalized_description = _clean_text(
        description,
        allow_empty=True,
    ).casefold()
    positions = tuple(
        position
        for alias in aliases
        if (
            position := normalized_description.find(alias.casefold())
        )
        >= 0
    )
    if (
        not positions
        or min(positions) > _SK_HYNIX_DESCRIPTION_MAX_ALIAS_OFFSET
        or not any(
            term.casefold() in normalized_title
            for term in _SK_HYNIX_DESCRIPTION_TITLE_TERMS
        )
    ):
        return None
    return "provider_description_alias"


def _dart_date(value: object) -> date | None:
    if not isinstance(value, str) or not _DATE_RE.fullmatch(value):
        return None
    try:
        return datetime.strptime(value, "%Y%m%d").date()
    except ValueError:
        return None


def _report_category(
    report_name: str,
) -> Literal[
    "periodic",
    "material_event",
    "securities",
    "ownership",
    "other",
]:
    normalized = report_name.replace(" ", "")
    if any(
        term in normalized
        for term in ("사업보고서", "반기보고서", "분기보고서")
    ):
        return "periodic"
    if any(
        term in normalized
        for term in (
            "주요사항보고서",
            "수시공시",
            "공정공시",
            "영업실적",
            "매출액또는손익구조",
            "단일판매",
            "공급계약",
            "시설투자",
            "유형자산",
            "타법인주식",
            "배당",
        )
    ):
        return "material_event"
    if any(
        term in normalized
        for term in (
            "증권신고서",
            "투자설명서",
            "주식매수선택권",
            "유상증자",
            "무상증자",
            "전환사채",
            "신주인수권",
        )
    ):
        return "securities"
    if any(
        term in normalized
        for term in (
            "임원ㆍ주요주주",
            "대량보유",
            "최대주주",
            "소유상황",
        )
    ):
        return "ownership"
    return "other"


def _correction_status(
    report_name: str,
    remark: str,
) -> Literal[
    "original",
    "correction",
    "superseded",
    "withdrawal",
    "unknown",
]:
    compact_name = report_name.replace(" ", "")
    compact_remark = remark.replace(" ", "")
    if "철회" in compact_name or "철" in compact_remark:
        return "withdrawal"
    if _CORRECTION_PREFIX_RE.match(report_name):
        return "correction"
    if "정" in compact_remark:
        return "superseded"
    if report_name:
        return "original"
    return "unknown"


def _lineage_key(security_id: str, report_name: str) -> str:
    normalized = _LINEAGE_PREFIX_RE.sub("", report_name).casefold()
    normalized = _WHITESPACE_RE.sub("", normalized)
    digest = hashlib.sha256(
        f"{security_id}|{normalized}".encode("utf-8")
    ).hexdigest()
    return f"lineage:{digest}"


def _normalized_title(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", value.casefold()).strip()


def _aware_utc(value: datetime) -> datetime:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise M5D1InventoryError("inventory timestamp is invalid")
    return value.astimezone(UTC)


__all__ = [
    "DISCLOSURE_WINDOW_END",
    "DISCLOSURE_WINDOW_START",
    "M5_D1_INVENTORY_PATH",
    "M5_D1_INVENTORY_SCHEMA_VERSION",
    "NEWS_WINDOW_END",
    "NEWS_WINDOW_START",
    "SECURITY_DART_IDENTITIES",
    "DisclosureInventoryItem",
    "M5D1InventoryError",
    "NewsInventoryItem",
    "build_source_inventory_payload",
    "normalize_disclosure_inventory",
    "normalize_news_inventory",
    "validate_corp_code_registry",
    "validate_source_inventory_payload",
    "write_source_inventory",
]
