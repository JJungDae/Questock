from __future__ import annotations

import hashlib
import html
import json
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from pydantic import ValidationError

from app.core.models import FinancialDocument

M5_NEWS_SCHEMA_VERSION = "m5-news-title-corpus-v1"
M5_NEWS_INGESTION_VERSION = "m5-news-title-ingest-v1"
M5_NEWS_PATH = Path("data/m5_news_documents.json")
KST = timezone(timedelta(hours=9))
COLLECTION_START = datetime(2026, 7, 24, 14, 0, tzinfo=KST)
COLLECTION_END = datetime(2026, 7, 27, 23, 59, 59, tzinfo=KST)
DAILY_CAP = 15
PERIOD_CAP = 60

SECURITY_TERMS: dict[str, tuple[str, tuple[str, ...]]] = {
    "KRX:005930": ("삼성전자", ("삼성전자", "삼전")),
    "KRX:000660": (
        "SK하이닉스",
        ("SK하이닉스", "SK 하이닉스", "하이닉스"),
    ),
    "KRX:005380": (
        "현대자동차",
        ("현대자동차", "현대차"),
    ),
}
_EVENT_TERMS = (
    "실적",
    "매출",
    "영업이익",
    "공급",
    "계약",
    "수주",
    "투자",
    "HBM",
    "반도체",
    "파업",
    "생산",
    "판매",
    "전기차",
    "로봇",
    "배당",
    "공시",
    "리콜",
    "관세",
    "환율",
    "AI",
    "메모리",
    "스마트폰",
    "아이폰",
    "지분",
    "인수",
    "최대주주",
    "신제품",
    "출시",
    "양산",
    "개발",
    "파트너십",
    "동맹",
    "수익성",
    "영업이익률",
    "사전 판매",
)
_BROAD_MARKET_TERMS = (
    "코스피",
    "코스닥",
    "증시",
    "시황",
    "마감",
    "상한가",
)
_REJECT_TERMS = (
    "레버리지",
    "ETF",
    "삼성전자우",
    "대학생",
    "일하고 싶은 기업",
    "구직자",
    "교육 지원",
    "직무훈련",
    "아카데미",
    "정상회의",
    "장학",
    "특징주",
    "자사주 매입",
    "촉구",
    "오늘 뭐했니",
    "오늘과 내일",
)
_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


class M5NewsSnapshotError(ValueError):
    """Raised when the M5 title-only news corpus is invalid."""


def curate_m5_news_items(
    raw_items_by_security: Mapping[str, Sequence[Mapping[str, Any]]],
) -> tuple[FinancialDocument, ...]:
    if set(raw_items_by_security) != set(SECURITY_TERMS):
        raise M5NewsSnapshotError("M5 news input securities are invalid")
    selected: list[FinancialDocument] = []
    for security_id in SECURITY_TERMS:
        candidates = _candidates(
            security_id,
            raw_items_by_security[security_id],
        )
        by_day: dict[object, list[FinancialDocument]] = defaultdict(list)
        for document in candidates:
            assert document.published_at is not None
            local_day = document.published_at.astimezone(KST).date()
            if len(by_day[local_day]) < DAILY_CAP:
                by_day[local_day].append(document)
        flattened = [
            item
            for day in sorted(by_day)
            for item in by_day[day]
        ][:PERIOD_CAP]
        selected.extend(flattened)
    selected.sort(
        key=lambda item: (
            item.primary_security_ids[0],
            item.published_at or datetime.min.replace(tzinfo=UTC),
            item.document_id,
        )
    )
    return tuple(item.model_copy(deep=True) for item in selected)


def build_m5_news_payload(
    documents: Sequence[FinancialDocument],
    *,
    collected_at: datetime,
) -> dict[str, object]:
    canonical = [
        _canonical_document(item)
        for item in documents
    ]
    ids = [item.document_id for item in canonical]
    if len(ids) != len(set(ids)):
        raise M5NewsSnapshotError(
            "M5 news document IDs are duplicated"
        )
    serialized = [
        item.model_dump(mode="json")
        for item in canonical
    ]
    serialized.sort(
        key=lambda item: (
            item["primary_security_ids"][0],
            item["published_at"],
            item["document_id"],
        )
    )
    checksum = hashlib.sha256(
        json.dumps(
            serialized,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    counts = {
        security_id: sum(
            security_id in item.primary_security_ids
            for item in canonical
        )
        for security_id in SECURITY_TERMS
    }
    return {
        "schema_version": M5_NEWS_SCHEMA_VERSION,
        "collection_start": COLLECTION_START.isoformat(),
        "collection_end": COLLECTION_END.isoformat(),
        "collected_at": _aware_utc(collected_at).isoformat().replace(
            "+00:00",
            "Z",
        ),
        "selection_policy": {
            "content_level": "source_title_only",
            "daily_cap": DAILY_CAP,
            "period_cap": PERIOD_CAP,
            "irrelevant_quota_fill": False,
        },
        "counts_by_security": counts,
        "documents_sha256": checksum,
        "documents": serialized,
    }


def load_m5_news_documents(
    path: Path = M5_NEWS_PATH,
) -> tuple[FinancialDocument, ...]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise M5NewsSnapshotError(
            "M5 news corpus is unavailable"
        ) from None
    if not isinstance(payload, dict):
        raise M5NewsSnapshotError("M5 news corpus is invalid")
    raw_documents = payload.get("documents")
    if not isinstance(raw_documents, list):
        raise M5NewsSnapshotError("M5 news corpus is invalid")
    documents: list[FinancialDocument] = []
    for raw in raw_documents:
        try:
            documents.append(
                FinancialDocument.model_validate(raw)
            )
        except (TypeError, ValueError, ValidationError):
            raise M5NewsSnapshotError(
                "M5 news corpus is invalid"
            ) from None
    canonical = build_m5_news_payload(
        documents,
        collected_at=_parse_timestamp(payload.get("collected_at")),
    )
    for key in (
        "schema_version",
        "collection_start",
        "collection_end",
        "selection_policy",
        "counts_by_security",
        "documents_sha256",
        "documents",
    ):
        if payload.get(key) != canonical.get(key):
            raise M5NewsSnapshotError(
                "M5 news corpus is invalid"
            )
    return tuple(
        item.model_copy(deep=True) for item in documents
    )


def _candidates(
    security_id: str,
    raw_items: Sequence[Mapping[str, Any]],
) -> list[FinancialDocument]:
    security_name, aliases = SECURITY_TERMS[security_id]
    output: list[tuple[int, FinancialDocument]] = []
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    for raw in raw_items:
        if not isinstance(raw, Mapping):
            continue
        title = _clean_text(raw.get("title"))
        published_at = _published_at(raw.get("pubDate"))
        source_url = _source_url(
            raw.get("originallink"),
            raw.get("link"),
        )
        if (
            not title
            or published_at is None
            or source_url is None
            or not (
                COLLECTION_START.astimezone(UTC)
                < published_at
                <= COLLECTION_END.astimezone(UTC)
            )
        ):
            continue
        normalized = title.casefold()
        alias_positions = [
            normalized.find(alias.casefold())
            for alias in aliases
            if alias.casefold() in normalized
        ]
        if (
            not alias_positions
            or min(alias_positions) > 14
            or any(
                term.casefold() in normalized
                for term in _REJECT_TERMS
            )
            or any(
                term.casefold() in normalized
                for term in _BROAD_MARKET_TERMS
            )
            or not any(
                term.casefold() in normalized
                for term in _EVENT_TERMS
            )
        ):
            continue
        score = 4
        score += 2 * sum(
            term.casefold() in normalized for term in _EVENT_TERMS
        )
        if score < 4:
            continue
        title_key = _WHITESPACE_RE.sub(" ", normalized).strip()
        if source_url in seen_urls or title_key in seen_titles:
            continue
        seen_urls.add(source_url)
        seen_titles.add(title_key)
        digest = hashlib.sha256(
            source_url.encode("utf-8")
        ).hexdigest()
        try:
            document = FinancialDocument(
                document_id=f"m5-news:{digest}",
                source_type="news",
                provider="naver_api_hub_news",
                primary_security_ids=[security_id],
                mentioned_security_ids=[],
                title=title,
                published_at=published_at,
                source_url=source_url,
                text=f"기사 제목에서 확인되는 내용: {title}",
                locator={
                    "provider": "naver_api_hub_news",
                    "source_url": source_url,
                    "published_at": published_at.isoformat(),
                    "content_level": "source_title_only",
                },
                metadata={
                    "document_type": "article",
                    "content_origin": "source_title_only",
                    "external_llm_processing_allowed": True,
                    "security_name": security_name,
                },
                ingestion_version=M5_NEWS_INGESTION_VERSION,
            )
        except (TypeError, ValueError, ValidationError):
            continue
        output.append((score, document))
    output.sort(
        key=lambda item: (
            -(item[1].published_at or datetime.min.replace(
                tzinfo=UTC
            )).timestamp(),
            -item[0],
            item[1].document_id,
        )
    )
    return [item for _, item in output]


def _canonical_document(
    value: object,
) -> FinancialDocument:
    if not isinstance(value, FinancialDocument):
        raise M5NewsSnapshotError(
            "M5 news document is invalid"
        )
    try:
        item = FinancialDocument.model_validate(
            value.model_dump(mode="python"),
            strict=True,
        )
    except (TypeError, ValueError, ValidationError):
        raise M5NewsSnapshotError(
            "M5 news document is invalid"
        ) from None
    if (
        item.source_type != "news"
        or item.provider != "naver_api_hub_news"
        or len(item.primary_security_ids) != 1
        or item.primary_security_ids[0] not in SECURITY_TERMS
        or item.mentioned_security_ids
        or item.published_at is None
        or not (
            COLLECTION_START.astimezone(UTC)
            < item.published_at.astimezone(UTC)
            <= COLLECTION_END.astimezone(UTC)
        )
        or item.locator.get("content_level") != "source_title_only"
        or item.metadata.get("content_origin")
        != "source_title_only"
        or item.metadata.get("external_llm_processing_allowed")
        is not True
        or item.ingestion_version != M5_NEWS_INGESTION_VERSION
    ):
        raise M5NewsSnapshotError(
            "M5 news document is invalid"
        )
    return item.model_copy(deep=True)


def _clean_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return _WHITESPACE_RE.sub(
        " ",
        html.unescape(_TAG_RE.sub("", value)),
    ).strip()


def _published_at(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(UTC)


def _source_url(*values: object) -> str | None:
    for value in values:
        if not isinstance(value, str):
            continue
        try:
            parsed = urlsplit(value.strip())
        except ValueError:
            continue
        if (
            parsed.scheme in {"http", "https"}
            and parsed.hostname
            and parsed.username is None
            and parsed.password is None
        ):
            return parsed.geturl()
    return None


def _parse_timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise M5NewsSnapshotError(
            "M5 news collected_at is invalid"
        )
    try:
        return _aware_utc(
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        )
    except ValueError:
        raise M5NewsSnapshotError(
            "M5 news collected_at is invalid"
        ) from None


def _aware_utc(value: datetime) -> datetime:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise M5NewsSnapshotError(
            "M5 news timestamp is invalid"
        )
    return value.astimezone(UTC)


__all__ = [
    "COLLECTION_END",
    "COLLECTION_START",
    "DAILY_CAP",
    "M5_NEWS_PATH",
    "M5_NEWS_SCHEMA_VERSION",
    "PERIOD_CAP",
    "SECURITY_TERMS",
    "M5NewsSnapshotError",
    "build_m5_news_payload",
    "curate_m5_news_items",
    "load_m5_news_documents",
]
