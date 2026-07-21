from __future__ import annotations

import hashlib
import html
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from app.core.models import DateRange, FinancialDocument, ProviderResult, SecurityIdentifier
from app.core.status import ProviderStatus
from app.providers.base import create_provider_result, normalize_query, security_id_for

RECORDED_NEWS_PROVIDER_KEY = "recorded_news"
NEWS_INGESTION_VERSION = "news-provider-m1-04-v1"
DEFAULT_SECURITIES_PATH = Path(__file__).resolve().parents[2] / "data" / "securities.json"
SEOUL_TZ = timezone(timedelta(hours=9))
_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


class NewsParseError(ValueError):
    """Raised when a recorded news response cannot be normalized."""


class InvalidNewsQuery(ValueError):
    """Raised when a query cannot be sent to a provider."""


@dataclass(frozen=True)
class NewsSecurityRecord:
    security_id: str
    market: str
    ticker: str
    security_name: str
    security_type: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class NewsMentionLexicon:
    records_by_id: dict[str, NewsSecurityRecord]
    terms_by_id: dict[str, tuple[str, ...]]

    def validate_security(self, security: SecurityIdentifier) -> bool:
        security_id = security_id_for(security)
        record = self.records_by_id.get(security_id)
        return (
            record is not None
            and record.market == security.market
            and record.ticker == security.ticker
            and record.security_name == security.security_name
            and record.security_type == security.security_type
            and record.security_type == "common_stock"
        )

    def canonical_name(self, security_id: str) -> str:
        return self.records_by_id[security_id].security_name

    def mentioned_security_ids(self, text: str) -> set[str]:
        normalized_text = _normalize_for_match(text)
        if not normalized_text:
            return set()
        mentioned: set[str] = set()
        for security_id, terms in self.terms_by_id.items():
            if any(term in normalized_text for term in terms):
                mentioned.add(security_id)
        return mentioned


@dataclass(frozen=True)
class ParsedNewsItem:
    title: str
    description: str
    published_at: datetime
    source_url: str | None
    raw_index: int


def load_news_mention_lexicon(securities_path: str | Path = DEFAULT_SECURITIES_PATH) -> NewsMentionLexicon:
    data = json.loads(Path(securities_path).read_text(encoding="utf-8"))
    records_by_id: dict[str, NewsSecurityRecord] = {}
    terms_by_id: dict[str, tuple[str, ...]] = {}
    for item in data.get("securities", []):
        security_id = item["security_id"]
        record = NewsSecurityRecord(
            security_id=security_id,
            market=item["market"],
            ticker=item["ticker"],
            security_name=item["security_name"],
            security_type=item["security_type"],
            aliases=tuple(item.get("aliases", [])),
        )
        records_by_id[security_id] = record
        terms = [_normalize_for_match(record.security_name)]
        terms.extend(_normalize_for_match(alias) for alias in record.aliases)
        terms_by_id[security_id] = tuple(term for term in dict.fromkeys(terms) if term)
    return NewsMentionLexicon(records_by_id=records_by_id, terms_by_id=terms_by_id)


def build_news_query(security: SecurityIdentifier, query: str | None, lexicon: NewsMentionLexicon) -> str:
    security_id = security_id_for(security)
    canonical_name = lexicon.canonical_name(security_id)
    if query is None:
        return canonical_name
    cleaned_query = _clean_text(query)
    if not cleaned_query:
        raise InvalidNewsQuery("news query must not be blank")
    normalized_query = _normalize_for_match(cleaned_query)
    if any(term in normalized_query for term in lexicon.terms_by_id[security_id]):
        return cleaned_query
    return f"{canonical_name} {cleaned_query}"


def normalize_naver_api_hub_news_response(
    raw_response: Any,
    *,
    security: SecurityIdentifier,
    query: str,
    date_range: DateRange | None,
    provider_key: str,
    ingestion_version: str,
    lexicon: NewsMentionLexicon,
) -> list[FinancialDocument]:
    items = _extract_items(raw_response)
    if not items:
        return []

    valid_items: list[ParsedNewsItem] = []
    for raw_index, raw_item in enumerate(items):
        parsed = _parse_item(raw_item, raw_index)
        if parsed is not None:
            valid_items.append(parsed)
    if not valid_items:
        raise NewsParseError("all news items are malformed")

    security_id = security_id_for(security)
    documents: list[FinancialDocument] = []
    seen_keys: set[str] = set()
    for item in valid_items:
        if not _is_in_date_range(item.published_at, date_range):
            continue
        attribution = _attribute_item(item, security_id, lexicon)
        if attribution is None:
            continue
        primary_ids, mentioned_ids = attribution
        dedupe_key = _dedupe_key(item)
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)
        documents.append(
            FinancialDocument(
                document_id=_document_id(item),
                source_type="news",
                provider=provider_key,
                primary_security_ids=primary_ids,
                mentioned_security_ids=mentioned_ids,
                title=item.title,
                published_at=item.published_at,
                source_url=item.source_url,
                text=_document_text(item.title, item.description),
                locator={
                    "provider": provider_key,
                    "source_url": item.source_url,
                    "published_at": item.published_at.isoformat(),
                    "raw_index": item.raw_index,
                    "query": query,
                },
                metadata={"query": query},
                ingestion_version=ingestion_version,
            )
        )
    return documents


class RecordedNewsProvider:
    key = RECORDED_NEWS_PROVIDER_KEY

    def __init__(
        self,
        recorded_response: dict[str, Any] | None = None,
        fixture_status: ProviderStatus = ProviderStatus.OK,
        fixture_path: str | Path | None = None,
        securities_path: str | Path = DEFAULT_SECURITIES_PATH,
        provider_key: str = RECORDED_NEWS_PROVIDER_KEY,
        ingestion_version: str = NEWS_INGESTION_VERSION,
    ) -> None:
        self.key = provider_key
        self._recorded_response = recorded_response
        if fixture_path is not None:
            self._recorded_response = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
        self._fixture_status = fixture_status
        self._ingestion_version = ingestion_version
        self._lexicon = load_news_mention_lexicon(securities_path)

    async def fetch(
        self,
        security: SecurityIdentifier,
        query: str | None = None,
        date_range: DateRange | None = None,
        attempt_timeout_seconds: float = 8,
    ) -> ProviderResult[list[FinancialDocument]]:
        if not self._lexicon.validate_security(security):
            return create_provider_result(status=ProviderStatus.INVALID_QUERY, message="invalid security")
        try:
            provider_query = build_news_query(security, query, self._lexicon)
        except InvalidNewsQuery:
            return create_provider_result(status=ProviderStatus.INVALID_QUERY, message="invalid query")

        if self._fixture_status != ProviderStatus.OK:
            return create_provider_result(status=self._fixture_status, message=self._fixture_status.value)

        try:
            documents = normalize_naver_api_hub_news_response(
                self._recorded_response if self._recorded_response is not None else {"body": {"items": []}},
                security=security,
                query=provider_query,
                date_range=date_range,
                provider_key=self.key,
                ingestion_version=self._ingestion_version,
                lexicon=self._lexicon,
            )
        except NewsParseError:
            return create_provider_result(status=ProviderStatus.PARSE_ERROR, message="parse error")

        if not documents:
            return create_provider_result(status=ProviderStatus.NO_DATA, message="no news data")
        return create_provider_result(status=ProviderStatus.OK, data=documents)


def _extract_items(raw_response: Any) -> list[Any]:
    if not isinstance(raw_response, dict):
        raise NewsParseError("news response must be an object")
    body = raw_response.get("body")
    if not isinstance(body, dict):
        raise NewsParseError("news response body must be an object")
    items = body.get("items")
    if not isinstance(items, list):
        raise NewsParseError("news response body.items must be a list")
    return items


def _parse_item(raw_item: Any, raw_index: int) -> ParsedNewsItem | None:
    if not isinstance(raw_item, dict):
        return None
    raw_title = raw_item.get("title")
    if not isinstance(raw_title, str):
        return None
    title = _clean_text(raw_title)
    if not title:
        return None
    pub_date = raw_item.get("pubDate")
    if not isinstance(pub_date, str):
        return None
    published_at = _parse_pub_date(pub_date)
    if published_at is None:
        return None
    raw_description = raw_item.get("description")
    description = _clean_text(raw_description) if isinstance(raw_description, str) else ""
    source_url = _select_source_url(raw_item.get("originallink"), raw_item.get("link"))
    return ParsedNewsItem(
        title=title,
        description=description,
        published_at=published_at,
        source_url=source_url,
        raw_index=raw_index,
    )


def _parse_pub_date(value: str) -> datetime | None:
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(UTC)


def _select_source_url(originallink: Any, link: Any) -> str | None:
    original = _canonical_url(originallink)
    if original is not None:
        return original
    return _canonical_url(link)


def _canonical_url(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parts = urlsplit(value.strip())
    except ValueError:
        return None
    scheme = parts.scheme.lower()
    if scheme not in {"http", "https"} or not parts.netloc:
        return None
    if parts.username is not None or parts.password is not None:
        return None
    hostname = parts.hostname
    if hostname is None:
        return None
    try:
        port = parts.port
    except ValueError:
        return None
    normalized_host = hostname.lower()
    default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    netloc = normalized_host if port is None or default_port else f"{normalized_host}:{port}"
    return urlunsplit((scheme, netloc, parts.path, parts.query, ""))


def _document_id(item: ParsedNewsItem) -> str:
    identity = item.source_url
    if identity is None:
        identity = f"{normalize_query(item.title)}|{item.published_at.isoformat()}"
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    return f"news:{digest}"


def _dedupe_key(item: ParsedNewsItem) -> str:
    if item.source_url:
        return f"url:{item.source_url}"
    return f"title-date:{normalize_query(item.title)}|{item.published_at.isoformat()}"


def _attribute_item(
    item: ParsedNewsItem,
    query_security_id: str,
    lexicon: NewsMentionLexicon,
) -> tuple[list[str], list[str]] | None:
    title_ids = lexicon.mentioned_security_ids(item.title)
    description_ids = lexicon.mentioned_security_ids(item.description)
    if title_ids and query_security_id not in title_ids and query_security_id in description_ids:
        return None
    if query_security_id not in title_ids and query_security_id not in description_ids:
        return None

    if query_security_id in title_ids:
        primary_id_set = title_ids
        mentioned_id_set = description_ids - primary_id_set
    else:
        primary_id_set = {query_security_id}
        mentioned_id_set = description_ids - primary_id_set
    primary_ids = sorted(primary_id_set)
    mentioned_ids = sorted(mentioned_id_set)
    if not primary_ids and not mentioned_ids:
        return None
    return primary_ids, mentioned_ids


def _is_in_date_range(published_at: datetime, date_range: DateRange | None) -> bool:
    if date_range is None:
        return True
    seoul_date = published_at.astimezone(SEOUL_TZ).date()
    if date_range.start is not None and seoul_date < date_range.start:
        return False
    if date_range.end is not None and seoul_date > date_range.end:
        return False
    return True


def _document_text(title: str, description: str) -> str:
    if description:
        return f"{title}\n{description}"
    return title


def _clean_text(value: str) -> str:
    unescaped = html.unescape(value)
    without_tags = _TAG_RE.sub(" ", unescaped)
    return _WHITESPACE_RE.sub(" ", without_tags).strip()


def _normalize_for_match(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", _clean_text(value))
    return _WHITESPACE_RE.sub(" ", normalized).strip().casefold()


__all__ = [
    "NEWS_INGESTION_VERSION",
    "RECORDED_NEWS_PROVIDER_KEY",
    "InvalidNewsQuery",
    "NewsMentionLexicon",
    "NewsParseError",
    "RecordedNewsProvider",
    "build_news_query",
    "load_news_mention_lexicon",
    "normalize_naver_api_hub_news_response",
]
