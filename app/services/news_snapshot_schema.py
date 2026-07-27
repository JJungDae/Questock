from __future__ import annotations

import json
import math
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import ValidationError

from app.core.models import FinancialDocument, SecurityIdentifier
from app.providers.news import (
    InvalidNewsQuery,
    NewsParseError,
    build_news_query,
    load_news_mention_lexicon,
    normalize_naver_api_hub_news_response,
)

NEWS_QUERY_SCHEMA_VERSION = "service-news-queries-v2"
NEWS_CANDIDATE_SCHEMA_VERSION = "service-news-candidates-v2"
NEWS_CURATED_SCHEMA_VERSION = "service-news-curated-v1"
SERVICE_SNAPSHOT_ID = "svc-20260724-1402"
NAVER_NEWS_ENDPOINT = "https://naverapihub.apigw.ntruss.com/search/v1/news"
NAVER_NEWS_PROVIDER_KEY = "naver_api_hub_news"
NEWS_SNAPSHOT_INGESTION_VERSION = "news-snapshot-fsc-v1"
SUPPORTED_SECURITY_IDS = frozenset(
    {"KRX:005930", "KRX:000660", "KRX:005380"}
)
SEOUL_TZ = timezone(timedelta(hours=9))
COLLECTION_START = datetime(2026, 7, 24, 0, 0, tzinfo=SEOUL_TZ)
COLLECTION_CUTOFF = datetime(2026, 7, 24, 14, 0, tzinfo=SEOUL_TZ)
_SECURITIES_PATH = Path(__file__).resolve().parents[2] / "data" / "securities.json"
_MATCH_WHITESPACE_RE = re.compile(r"\s+")


class NewsSnapshotValidationError(ValueError):
    """Raised when FSC news collection data violates the fixed contract."""


class NewsCurationError(ValueError):
    """Raised when FSC news candidates cannot produce a valid curated set."""


@dataclass(frozen=True)
class NewsSearchQuery:
    query: str
    sort: Literal["date", "sim"]


@dataclass(frozen=True)
class NewsQuerySpec:
    security: SecurityIdentifier
    security_id: str
    query: str
    sort: Literal["date", "sim"]
    quality_queries: tuple[NewsSearchQuery, ...]


@dataclass(frozen=True)
class NewsSnapshotConfig:
    schema_version: str
    snapshot_id: str
    endpoint: str
    display: int
    max_calls_per_security: int
    max_quality_queries_per_security: int
    max_calls_per_quality_query: int
    timeout_seconds: float
    securities: tuple[NewsQuerySpec, ...]


@dataclass(frozen=True)
class NewsCoverage:
    total: int
    pre_market: int
    intraday: int
    ready: bool


@dataclass(frozen=True)
class NewsCollectionWindow:
    raw_item_count: int
    valid_published_at_count: int
    invalid_published_at_count: int
    cutoff_window_item_count: int
    oldest_published_at: datetime | None
    newest_published_at: datetime | None


@dataclass(frozen=True)
class NewsCurationRule:
    event_id: str
    terms: tuple[str, ...]
    time_band: Literal["pre_market", "intraday"]
    summary: str


@dataclass(frozen=True)
class CuratedNewsSelection:
    event_id: str
    document: FinancialDocument
    time_band: Literal["pre_market", "intraday"]
    summary: str


_CURATION_RULES: dict[str, tuple[NewsCurationRule, ...]] = {
    "KRX:005930": (
        NewsCurationRule(
            event_id="ai_supply_outlook",
            terms=("ai 공급 부족",),
            time_band="pre_market",
            summary=(
                "AI 반도체 공급 여건과 삼성전자 실적 발표를 앞둔 "
                "시장 전망을 다룬 보도입니다."
            ),
        ),
        NewsCurationRule(
            event_id="earnings_expectation",
            terms=("실적 발표가 예정", "장기 공급 계약"),
            time_band="pre_market",
            summary=(
                "빅테크 변동성 속 삼성전자 실적 기대와 반도체 업황을 "
                "점검한 보도입니다."
            ),
        ),
        NewsCurationRule(
            event_id="foreign_investor_flow",
            terms=("돌아온 외국인", "반도체부터 샀다"),
            time_band="intraday",
            summary=(
                "외국인 자금이 삼성전자를 포함한 반도체주로 돌아온 "
                "수급 흐름을 다룬 보도입니다."
            ),
        ),
        NewsCurationRule(
            event_id="ai_capex_reaction",
            terms=("구글 ai 투자",),
            time_band="intraday",
            summary=(
                "구글의 AI 투자 전망 변화가 삼성전자 주가와 반도체 "
                "투자심리에 미친 영향을 다룬 보도입니다."
            ),
        ),
        NewsCurationRule(
            event_id="smartphone_supply_cycle",
            terms=("아이폰 성장 사이클",),
            time_band="intraday",
            summary=(
                "아이폰 성장 전망이 삼성전자 부품 수요에 미칠 "
                "가능성을 다룬 보도입니다."
            ),
        ),
    ),
    "KRX:000660": (
        NewsCurationRule(
            event_id="ai_supply_outlook",
            terms=("ai 공급 부족",),
            time_band="pre_market",
            summary=(
                "AI 반도체 수급과 예정된 실적 발표를 앞둔 시장 전망을 "
                "다룬 보도입니다."
            ),
        ),
        NewsCurationRule(
            event_id="foreign_investor_flow",
            terms=("반도체 피크아웃", "돌아온 외인"),
            time_band="intraday",
            summary=(
                "반도체 업황 우려 완화와 SK하이닉스에 대한 외국인 "
                "매수 흐름을 다룬 보도입니다."
            ),
        ),
        NewsCurationRule(
            event_id="ai_capex_reaction",
            terms=("구글 ai 투자",),
            time_band="intraday",
            summary=(
                "구글의 AI 투자 전망 변화가 SK하이닉스 주가와 "
                "반도체 투자심리에 미친 영향을 다룬 보도입니다."
            ),
        ),
        NewsCurationRule(
            event_id="investor_positioning",
            terms=("개인과 외국인", "엇갈린 베팅"),
            time_band="intraday",
            summary=(
                "SK하이닉스를 둘러싼 개인과 외국인의 상반된 수급 "
                "방향을 다룬 보도입니다."
            ),
        ),
        NewsCurationRule(
            event_id="smartphone_supply_cycle",
            terms=("아이폰 성장 사이클",),
            time_band="intraday",
            summary=(
                "스마트폰 성장 전망이 SK하이닉스 수요에 미칠 가능성을 "
                "다룬 보도입니다."
            ),
        ),
    ),
    "KRX:005380": (
        NewsCurationRule(
            event_id="earnings_outlook",
            terms=("2분기 부진", "2분기 실적"),
            time_band="pre_market",
            summary=(
                "현대차의 2분기 실적 평가와 하반기 개선 조건을 다룬 "
                "보도입니다."
            ),
        ),
        NewsCurationRule(
            event_id="labor_dispute",
            terms=("파업 장기화", "생산 손실"),
            time_band="intraday",
            summary=(
                "노사 교섭 중단과 파업 장기화가 현대차 생산에 미치는 "
                "영향을 다룬 보도입니다."
            ),
        ),
        NewsCurationRule(
            event_id="earnings_market_reaction",
            terms=("실적 부진에 하락세",),
            time_band="intraday",
            summary=(
                "현대차의 2분기 실적 부진이 장중 주가에 미친 영향을 "
                "다룬 보도입니다."
            ),
        ),
        NewsCurationRule(
            event_id="investor_day_catalyst",
            terms=("cid 행사", "실적은 노이즈"),
            time_band="pre_market",
            summary=(
                "현대차 2분기 실적을 일시 요인으로 평가하고 후속 "
                "Investor Day를 촉매로 본 증권사 전망을 다룬 보도입니다."
            ),
        ),
        NewsCurationRule(
            event_id="robot_cluster",
            terms=("수소·로봇 특화", "로봇 부품"),
            time_band="intraday",
            summary=(
                "현대차그룹이 참여하는 수소·로봇 산업단지 추진 내용을 "
                "다룬 보도입니다."
            ),
        ),
    ),
}


def load_news_snapshot_config(
    path: str | Path,
    *,
    securities_path: str | Path = _SECURITIES_PATH,
) -> NewsSnapshotConfig:
    payload = _load_json_object(path)
    securities_payload = _load_json_object(securities_path)
    if set(payload) != {
        "schema_version",
        "snapshot_id",
        "endpoint",
        "display",
        "max_calls_per_security",
        "max_quality_queries_per_security",
        "max_calls_per_quality_query",
        "timeout_seconds",
        "securities",
    }:
        raise NewsSnapshotValidationError("news collection config is invalid")
    if (
        payload.get("schema_version") != NEWS_QUERY_SCHEMA_VERSION
        or payload.get("snapshot_id") != SERVICE_SNAPSHOT_ID
        or payload.get("endpoint") != NAVER_NEWS_ENDPOINT
    ):
        raise NewsSnapshotValidationError("news collection config is invalid")

    display = _bounded_integer(payload.get("display"), minimum=1, maximum=100)
    max_calls = _bounded_integer(
        payload.get("max_calls_per_security"),
        minimum=1,
        maximum=10,
    )
    max_quality_queries = _bounded_integer(
        payload.get("max_quality_queries_per_security"),
        minimum=1,
        maximum=3,
    )
    max_calls_per_quality_query = _bounded_integer(
        payload.get("max_calls_per_quality_query"),
        minimum=1,
        maximum=2,
    )
    timeout = _positive_number(payload.get("timeout_seconds"))
    raw_specs = payload.get("securities")
    raw_records = securities_payload.get("securities")
    if not isinstance(raw_specs, list) or not isinstance(raw_records, list):
        raise NewsSnapshotValidationError("news collection config is invalid")

    records = _security_records(raw_records)
    lexicon = load_news_mention_lexicon(securities_path)
    specs: list[NewsQuerySpec] = []
    seen_ids: set[str] = set()
    for raw_spec in raw_specs:
        if not isinstance(raw_spec, dict) or set(raw_spec) != {
            "security_id",
            "query",
            "sort",
            "quality_queries",
        }:
            raise NewsSnapshotValidationError("news collection config is invalid")
        security_id = _nonblank(raw_spec.get("security_id"))
        query = _nonblank(raw_spec.get("query"))
        sort = raw_spec.get("sort")
        if sort not in {"date", "sim"}:
            raise NewsSnapshotValidationError("news collection config is invalid")
        if security_id in seen_ids or security_id not in SUPPORTED_SECURITY_IDS:
            raise NewsSnapshotValidationError("news collection config is invalid")
        record = records.get(security_id)
        if record is None:
            raise NewsSnapshotValidationError("news collection config is invalid")
        try:
            validated_query = build_news_query(record, query, lexicon)
        except (InvalidNewsQuery, KeyError):
            raise NewsSnapshotValidationError(
                "news collection config is invalid"
            ) from None
        if validated_query != query:
            raise NewsSnapshotValidationError("news collection config is invalid")
        raw_quality_queries = raw_spec.get("quality_queries")
        if (
            not isinstance(raw_quality_queries, list)
            or len(raw_quality_queries) != max_quality_queries
        ):
            raise NewsSnapshotValidationError("news collection config is invalid")
        quality_queries: list[NewsSearchQuery] = []
        seen_queries = {query}
        for raw_quality_query in raw_quality_queries:
            if (
                not isinstance(raw_quality_query, dict)
                or set(raw_quality_query) != {"query", "sort"}
            ):
                raise NewsSnapshotValidationError(
                    "news collection config is invalid"
                )
            quality_query = _nonblank(raw_quality_query.get("query"))
            quality_sort = raw_quality_query.get("sort")
            if quality_sort not in {"date", "sim"}:
                raise NewsSnapshotValidationError(
                    "news collection config is invalid"
                )
            try:
                validated_quality_query = build_news_query(
                    record,
                    quality_query,
                    lexicon,
                )
            except (InvalidNewsQuery, KeyError):
                raise NewsSnapshotValidationError(
                    "news collection config is invalid"
                ) from None
            if (
                validated_quality_query != quality_query
                or quality_query in seen_queries
            ):
                raise NewsSnapshotValidationError(
                    "news collection config is invalid"
                )
            seen_queries.add(quality_query)
            quality_queries.append(
                NewsSearchQuery(
                    query=quality_query,
                    sort=quality_sort,
                )
            )
        seen_ids.add(security_id)
        specs.append(
            NewsQuerySpec(
                security=record,
                security_id=security_id,
                query=query,
                sort=sort,
                quality_queries=tuple(quality_queries),
            )
        )
    if seen_ids != SUPPORTED_SECURITY_IDS:
        raise NewsSnapshotValidationError("news collection config is invalid")
    return NewsSnapshotConfig(
        schema_version=NEWS_QUERY_SCHEMA_VERSION,
        snapshot_id=SERVICE_SNAPSHOT_ID,
        endpoint=NAVER_NEWS_ENDPOINT,
        display=display,
        max_calls_per_security=max_calls,
        max_quality_queries_per_security=max_quality_queries,
        max_calls_per_quality_query=max_calls_per_quality_query,
        timeout_seconds=timeout,
        securities=tuple(specs),
    )


def normalize_collected_news_pages(
    pages: Sequence[Mapping[str, Any]],
    *,
    spec: NewsQuerySpec,
) -> tuple[FinancialDocument, ...]:
    if (
        isinstance(pages, (str, bytes, bytearray))
        or not isinstance(pages, Sequence)
        or not pages
        or not isinstance(spec, NewsQuerySpec)
    ):
        raise NewsSnapshotValidationError("news collection pages are invalid")
    combined_items: list[Any] = []
    for page in pages:
        if not isinstance(page, Mapping):
            raise NewsSnapshotValidationError("news collection pages are invalid")
        items = page.get("items")
        if not isinstance(items, list):
            raise NewsSnapshotValidationError("news collection pages are invalid")
        combined_items.extend(items)

    try:
        documents = normalize_naver_api_hub_news_response(
            {"body": {"items": combined_items}},
            security=spec.security,
            query=spec.query,
            date_range=None,
            provider_key=NAVER_NEWS_PROVIDER_KEY,
            ingestion_version=NEWS_SNAPSHOT_INGESTION_VERSION,
            lexicon=load_news_mention_lexicon(),
        )
    except (NewsParseError, KeyError, TypeError, ValueError):
        raise NewsSnapshotValidationError(
            "news collection response is invalid"
        ) from None

    start_utc = COLLECTION_START.astimezone(UTC)
    cutoff_utc = COLLECTION_CUTOFF.astimezone(UTC)
    selected = [
        document
        for document in documents
        if isinstance(document.published_at, datetime)
        and document.published_at.tzinfo is not None
        and document.published_at.utcoffset() is not None
        and start_utc <= document.published_at.astimezone(UTC) <= cutoff_utc
        and document.source_url is not None
    ]
    selected.sort(
        key=lambda item: (
            item.published_at.astimezone(UTC) if item.published_at else start_utc,
            item.document_id,
        ),
        reverse=True,
    )
    return tuple(item.model_copy(deep=True) for item in selected)


def calculate_news_coverage(
    documents: Sequence[FinancialDocument],
    *,
    security_id: str,
) -> NewsCoverage:
    if (
        isinstance(documents, (str, bytes, bytearray))
        or not isinstance(documents, Sequence)
        or security_id not in SUPPORTED_SECURITY_IDS
    ):
        raise NewsSnapshotValidationError("news coverage input is invalid")
    pre_market = 0
    intraday = 0
    for document in documents:
        if (
            not isinstance(document, FinancialDocument)
            or security_id not in document.primary_security_ids
            or document.source_type != "news"
            or document.provider != NAVER_NEWS_PROVIDER_KEY
            or not isinstance(document.published_at, datetime)
            or document.published_at.tzinfo is None
            or document.published_at.utcoffset() is None
        ):
            raise NewsSnapshotValidationError("news coverage input is invalid")
        local_time = document.published_at.astimezone(SEOUL_TZ)
        if not COLLECTION_START <= local_time <= COLLECTION_CUTOFF:
            raise NewsSnapshotValidationError("news coverage input is invalid")
        if local_time.hour < 9:
            pre_market += 1
        else:
            intraday += 1
    total = len(documents)
    return NewsCoverage(
        total=total,
        pre_market=pre_market,
        intraday=intraday,
        ready=total >= 5 and pre_market >= 1 and intraday >= 2,
    )


def summarize_collected_news_window(
    pages: Sequence[Mapping[str, Any]],
) -> NewsCollectionWindow:
    if (
        isinstance(pages, (str, bytes, bytearray))
        or not isinstance(pages, Sequence)
        or not pages
    ):
        raise NewsSnapshotValidationError("news collection pages are invalid")

    raw_item_count = 0
    invalid_published_at_count = 0
    published_at_values: list[datetime] = []
    for page in pages:
        if not isinstance(page, Mapping):
            raise NewsSnapshotValidationError("news collection pages are invalid")
        items = page.get("items")
        if not isinstance(items, list):
            raise NewsSnapshotValidationError("news collection pages are invalid")
        raw_item_count += len(items)
        for item in items:
            if not isinstance(item, Mapping):
                invalid_published_at_count += 1
                continue
            raw_published_at = item.get("pubDate")
            if not isinstance(raw_published_at, str):
                invalid_published_at_count += 1
                continue
            try:
                published_at = parsedate_to_datetime(raw_published_at)
            except (TypeError, ValueError, OverflowError):
                invalid_published_at_count += 1
                continue
            if (
                not isinstance(published_at, datetime)
                or published_at.tzinfo is None
                or published_at.utcoffset() is None
            ):
                invalid_published_at_count += 1
                continue
            published_at_values.append(published_at.astimezone(UTC))

    start_utc = COLLECTION_START.astimezone(UTC)
    cutoff_utc = COLLECTION_CUTOFF.astimezone(UTC)
    cutoff_window_item_count = sum(
        start_utc <= published_at <= cutoff_utc
        for published_at in published_at_values
    )
    return NewsCollectionWindow(
        raw_item_count=raw_item_count,
        valid_published_at_count=len(published_at_values),
        invalid_published_at_count=invalid_published_at_count,
        cutoff_window_item_count=cutoff_window_item_count,
        oldest_published_at=min(published_at_values, default=None),
        newest_published_at=max(published_at_values, default=None),
    )


def build_news_candidate_payload(
    *,
    spec: NewsQuerySpec,
    pages: Sequence[Mapping[str, Any]],
    collected_at: datetime,
) -> dict[str, Any]:
    return build_merged_news_candidate_payload(
        spec=spec,
        query_runs=((NewsSearchQuery(spec.query, spec.sort), pages),),
        collected_at=collected_at,
    )


def build_merged_news_candidate_payload(
    *,
    spec: NewsQuerySpec,
    query_runs: Sequence[
        tuple[NewsSearchQuery, Sequence[Mapping[str, Any]]]
    ],
    collected_at: datetime,
) -> dict[str, Any]:
    if (
        not isinstance(spec, NewsQuerySpec)
        or isinstance(query_runs, (str, bytes, bytearray))
        or not isinstance(query_runs, Sequence)
        or not query_runs
        or not isinstance(collected_at, datetime)
        or collected_at.tzinfo is None
        or collected_at.utcoffset() is None
    ):
        raise NewsSnapshotValidationError("news collection time is invalid")

    all_pages: list[Mapping[str, Any]] = []
    query_run_payloads: list[dict[str, Any]] = []
    merged_documents: dict[str, FinancialDocument] = {}
    seen_urls: set[str] = set()
    seen_queries: set[str] = set()
    for search_query, pages in query_runs:
        if (
            not isinstance(search_query, NewsSearchQuery)
            or search_query.query in seen_queries
        ):
            raise NewsSnapshotValidationError("news collection runs are invalid")
        run_spec = NewsQuerySpec(
            security=spec.security,
            security_id=spec.security_id,
            query=search_query.query,
            sort=search_query.sort,
            quality_queries=(),
        )
        documents = normalize_collected_news_pages(pages, spec=run_spec)
        window = summarize_collected_news_window(pages)
        all_pages.extend(pages)
        seen_queries.add(search_query.query)
        query_run_payloads.append(
            {
                "query": search_query.query,
                "sort": search_query.sort,
                "api_call_count": len(pages),
                "raw_item_count": window.raw_item_count,
                "cutoff_window_item_count": window.cutoff_window_item_count,
                "normalized_candidate_count": len(documents),
            }
        )
        for document in documents:
            if (
                document.document_id in merged_documents
                or document.source_url in seen_urls
            ):
                continue
            merged_documents[document.document_id] = document.model_copy(deep=True)
            if document.source_url is not None:
                seen_urls.add(document.source_url)

    collection_window = summarize_collected_news_window(all_pages)
    documents = tuple(
        sorted(
            merged_documents.values(),
            key=lambda item: (
                item.published_at.astimezone(UTC)
                if item.published_at is not None
                else COLLECTION_START.astimezone(UTC),
                item.document_id,
            ),
            reverse=True,
        )
    )
    coverage = calculate_news_coverage(
        documents,
        security_id=spec.security_id,
    )
    return {
        "schema_version": NEWS_CANDIDATE_SCHEMA_VERSION,
        "snapshot_id": SERVICE_SNAPSHOT_ID,
        "security_id": spec.security_id,
        "query": spec.query,
        "sort": spec.sort,
        "query_runs": query_run_payloads,
        "collection_start": _utc_timestamp(COLLECTION_START),
        "collection_cutoff": _utc_timestamp(COLLECTION_CUTOFF),
        "collected_at": _utc_timestamp(collected_at),
        "api_call_count": len(all_pages),
        "retrieval_window": {
            "raw_item_count": collection_window.raw_item_count,
            "valid_published_at_count": (
                collection_window.valid_published_at_count
            ),
            "invalid_published_at_count": (
                collection_window.invalid_published_at_count
            ),
            "cutoff_window_item_count": (
                collection_window.cutoff_window_item_count
            ),
            "oldest_published_at": (
                _utc_timestamp(collection_window.oldest_published_at)
                if collection_window.oldest_published_at is not None
                else None
            ),
            "newest_published_at": (
                _utc_timestamp(collection_window.newest_published_at)
                if collection_window.newest_published_at is not None
                else None
            ),
        },
        "coverage": {
            "total": coverage.total,
            "pre_market": coverage.pre_market,
            "intraday": coverage.intraday,
            "ready": coverage.ready,
        },
        "documents": [
            document.model_dump(mode="json")
            for document in documents
        ],
    }


def load_news_candidate_documents(
    path: str | Path,
    *,
    spec: NewsQuerySpec,
) -> tuple[FinancialDocument, ...]:
    if not isinstance(spec, NewsQuerySpec):
        raise NewsCurationError("news curation input is invalid")
    payload = _load_json_object(path)
    if set(payload) != {
        "schema_version",
        "snapshot_id",
        "security_id",
        "query",
        "sort",
        "query_runs",
        "collection_start",
        "collection_cutoff",
        "collected_at",
        "api_call_count",
        "retrieval_window",
        "coverage",
        "documents",
    }:
        raise NewsCurationError("news candidate payload is invalid")
    if (
        payload.get("schema_version") != NEWS_CANDIDATE_SCHEMA_VERSION
        or payload.get("snapshot_id") != SERVICE_SNAPSHOT_ID
        or payload.get("security_id") != spec.security_id
        or payload.get("query") != spec.query
        or payload.get("sort") != spec.sort
        or not _valid_query_run_payloads(payload.get("query_runs"), spec=spec)
    ):
        raise NewsCurationError("news candidate payload is invalid")
    raw_documents = payload.get("documents")
    if not isinstance(raw_documents, list):
        raise NewsCurationError("news candidate payload is invalid")
    try:
        documents = tuple(
            FinancialDocument.model_validate(raw_document)
            for raw_document in raw_documents
        )
    except (ValidationError, TypeError, ValueError):
        raise NewsCurationError("news candidate payload is invalid") from None

    _validate_candidate_documents(documents, security_id=spec.security_id)
    coverage = calculate_news_coverage(
        documents,
        security_id=spec.security_id,
    )
    raw_coverage = payload.get("coverage")
    if (
        not isinstance(raw_coverage, dict)
        or raw_coverage.get("total") != coverage.total
        or raw_coverage.get("pre_market") != coverage.pre_market
        or raw_coverage.get("intraday") != coverage.intraday
        or raw_coverage.get("ready") is not coverage.ready
    ):
        raise NewsCurationError("news candidate payload is invalid")
    return tuple(document.model_copy(deep=True) for document in documents)


def _valid_query_run_payloads(
    value: object,
    *,
    spec: NewsQuerySpec,
) -> bool:
    if not isinstance(value, list) or not value:
        return False
    allowed = {
        (spec.query, spec.sort),
        *((item.query, item.sort) for item in spec.quality_queries),
    }
    seen: set[tuple[str, str]] = set()
    for index, item in enumerate(value):
        if (
            not isinstance(item, dict)
            or set(item)
            != {
                "query",
                "sort",
                "api_call_count",
                "raw_item_count",
                "cutoff_window_item_count",
                "normalized_candidate_count",
            }
        ):
            return False
        query_key = (item.get("query"), item.get("sort"))
        if query_key not in allowed or query_key in seen:
            return False
        if index == 0 and query_key != (spec.query, spec.sort):
            return False
        if any(
            isinstance(item.get(key), bool)
            or not isinstance(item.get(key), int)
            or item[key] < 0
            for key in (
                "api_call_count",
                "raw_item_count",
                "cutoff_window_item_count",
                "normalized_candidate_count",
            )
        ):
            return False
        seen.add(query_key)
    return True


def curate_news_documents(
    documents: Sequence[FinancialDocument],
    *,
    security_id: str,
) -> tuple[CuratedNewsSelection, ...]:
    if (
        isinstance(documents, (str, bytes, bytearray))
        or not isinstance(documents, Sequence)
        or security_id not in _CURATION_RULES
    ):
        raise NewsCurationError("news curation input is invalid")
    copied_documents = tuple(
        document.model_copy(deep=True)
        if isinstance(document, FinancialDocument)
        else document
        for document in documents
    )
    _validate_candidate_documents(copied_documents, security_id=security_id)

    selected: list[CuratedNewsSelection] = []
    used_document_ids: set[str] = set()
    used_urls: set[str] = set()
    used_titles: set[str] = set()
    used_published_at: set[datetime] = set()
    used_hosts: set[str] = set()
    for rule in _CURATION_RULES[security_id]:
        matches = [
            document
            for document in copied_documents
            if _candidate_matches_rule(document, rule)
            and document.document_id not in used_document_ids
            and document.source_url not in used_urls
            and _normalized_match_text(document.title) not in used_titles
            and document.published_at not in used_published_at
        ]
        if not matches:
            raise NewsCurationError("news curation requirements are not met")
        matches.sort(
            key=lambda document: _curation_sort_key(
                document,
                rule=rule,
                used_hosts=used_hosts,
            )
        )
        document = matches[0]
        source_url = document.source_url
        if source_url is None:
            raise NewsCurationError("news curation requirements are not met")
        selected.append(
            CuratedNewsSelection(
                event_id=rule.event_id,
                document=document,
                time_band=rule.time_band,
                summary=rule.summary,
            )
        )
        used_document_ids.add(document.document_id)
        used_urls.add(source_url)
        used_titles.add(_normalized_match_text(document.title))
        if document.published_at is None:
            raise NewsCurationError("news curation requirements are not met")
        used_published_at.add(document.published_at)
        used_hosts.add(_source_host(source_url))

    selected_documents = tuple(item.document for item in selected)
    coverage = calculate_news_coverage(
        selected_documents,
        security_id=security_id,
    )
    if len(selected) != 5 or not coverage.ready:
        raise NewsCurationError("news curation requirements are not met")
    if len({item.event_id for item in selected}) != len(selected):
        raise NewsCurationError("news curation requirements are not met")
    return tuple(selected)


def build_curated_news_payload(
    documents: Sequence[FinancialDocument],
    *,
    security_id: str,
) -> dict[str, Any]:
    selections = curate_news_documents(
        documents,
        security_id=security_id,
    )
    coverage = calculate_news_coverage(
        tuple(item.document for item in selections),
        security_id=security_id,
    )
    return {
        "schema_version": NEWS_CURATED_SCHEMA_VERSION,
        "snapshot_id": SERVICE_SNAPSHOT_ID,
        "security_id": security_id,
        "selection_policy": "deterministic-event-diverse-v1",
        "summary_author": "Questock",
        "summary_kind": "project_owned_short_summary",
        "coverage": {
            "total": coverage.total,
            "pre_market": coverage.pre_market,
            "intraday": coverage.intraday,
            "ready": coverage.ready,
        },
        "documents": [
            {
                "document_id": item.document.document_id,
                "time_band": item.time_band,
                "source_locator": {
                    "provider": item.document.provider,
                    "source_url": item.document.source_url,
                    "published_at": _utc_timestamp(
                        item.document.published_at
                    ),
                },
                "summary": item.summary,
            }
            for item in selections
        ],
    }


def write_utf8_json(path: str | Path, payload: Mapping[str, Any]) -> None:
    if not isinstance(payload, Mapping):
        raise NewsSnapshotValidationError("news output payload is invalid")
    output_path = Path(path)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(
            dict(payload),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        output_path.write_text(f"{text}\n", encoding="utf-8", newline="\n")
    except (OSError, TypeError, ValueError):
        raise NewsSnapshotValidationError(
            "news output could not be written"
        ) from None


def _load_json_object(path: str | Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError):
        raise NewsSnapshotValidationError(
            "news collection input could not be loaded"
        ) from None
    if not isinstance(value, dict):
        raise NewsSnapshotValidationError("news collection input is invalid")
    return value


def _security_records(
    raw_records: list[Any],
) -> dict[str, SecurityIdentifier]:
    records: dict[str, SecurityIdentifier] = {}
    for raw in raw_records:
        if not isinstance(raw, dict):
            raise NewsSnapshotValidationError("security registry is invalid")
        security_id = raw.get("security_id")
        if security_id not in SUPPORTED_SECURITY_IDS:
            continue
        required = (
            raw.get("market"),
            raw.get("ticker"),
            raw.get("security_name"),
            raw.get("security_type"),
            raw.get("corp_name"),
        )
        if any(not isinstance(value, str) or not value.strip() for value in required):
            raise NewsSnapshotValidationError("security registry is invalid")
        corp_code = raw.get("corp_code")
        if corp_code is not None and (
            not isinstance(corp_code, str) or not corp_code.strip()
        ):
            raise NewsSnapshotValidationError("security registry is invalid")
        records[security_id] = SecurityIdentifier(
            market=raw["market"],
            ticker=raw["ticker"],
            security_name=raw["security_name"],
            security_type=raw["security_type"],
            corp_code=corp_code,
            corp_name=raw["corp_name"],
        )
    return records


def _validate_candidate_documents(
    documents: Sequence[object],
    *,
    security_id: str,
) -> None:
    if not documents:
        raise NewsCurationError("news candidate documents are invalid")
    document_ids: set[str] = set()
    source_urls: set[str] = set()
    for document in documents:
        if not isinstance(document, FinancialDocument):
            raise NewsCurationError("news candidate documents are invalid")
        if (
            document.document_id in document_ids
            or document.source_url is None
            or document.source_url in source_urls
        ):
            raise NewsCurationError("news candidate documents are invalid")
        _source_host(document.source_url)
        document_ids.add(document.document_id)
        source_urls.add(document.source_url)
    try:
        calculate_news_coverage(
            documents,
            security_id=security_id,
        )
    except NewsSnapshotValidationError:
        raise NewsCurationError("news candidate documents are invalid") from None


def _candidate_matches_rule(
    document: FinancialDocument,
    rule: NewsCurationRule,
) -> bool:
    if _news_time_band(document) != rule.time_band:
        return False
    normalized_title = _normalized_match_text(document.title)
    normalized_text = _normalized_match_text(document.text)
    return any(
        _normalized_match_text(term) in normalized_title
        or _normalized_match_text(term) in normalized_text
        for term in rule.terms
    )


def _curation_sort_key(
    document: FinancialDocument,
    *,
    rule: NewsCurationRule,
    used_hosts: set[str],
) -> tuple[int, float, int, str]:
    source_url = document.source_url
    published_at = document.published_at
    if source_url is None or published_at is None:
        raise NewsCurationError("news candidate documents are invalid")
    normalized_title = _normalized_match_text(document.title)
    title_match = any(
        _normalized_match_text(term) in normalized_title
        for term in rule.terms
    )
    return (
        int(not title_match),
        -published_at.astimezone(UTC).timestamp(),
        int(_source_host(source_url) in used_hosts),
        document.document_id,
    )


def _news_time_band(
    document: FinancialDocument,
) -> Literal["pre_market", "intraday"]:
    published_at = document.published_at
    if (
        published_at is None
        or published_at.tzinfo is None
        or published_at.utcoffset() is None
    ):
        raise NewsCurationError("news candidate documents are invalid")
    return (
        "pre_market"
        if published_at.astimezone(SEOUL_TZ).hour < 9
        else "intraday"
    )


def _source_host(source_url: str) -> str:
    try:
        parsed = urlsplit(source_url)
        host = parsed.hostname
        _ = parsed.port
    except (TypeError, ValueError):
        raise NewsCurationError("news source locator is invalid") from None
    if (
        parsed.scheme not in {"http", "https"}
        or host is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise NewsCurationError("news source locator is invalid")
    return host.lower()


def _normalized_match_text(value: str) -> str:
    if not isinstance(value, str):
        raise NewsCurationError("news candidate text is invalid")
    return _MATCH_WHITESPACE_RE.sub(
        "",
        unicodedata.normalize("NFKC", value).casefold(),
    )


def _nonblank(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise NewsSnapshotValidationError("news collection config is invalid")
    return value.strip()


def _bounded_integer(value: object, *, minimum: int, maximum: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or value > maximum
    ):
        raise NewsSnapshotValidationError("news collection config is invalid")
    return value


def _positive_number(value: object) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
        or value > 60
    ):
        raise NewsSnapshotValidationError("news collection config is invalid")
    return float(value)


def _utc_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "COLLECTION_CUTOFF",
    "COLLECTION_START",
    "NAVER_NEWS_ENDPOINT",
    "NEWS_CANDIDATE_SCHEMA_VERSION",
    "NEWS_CURATED_SCHEMA_VERSION",
    "NEWS_QUERY_SCHEMA_VERSION",
    "NEWS_SNAPSHOT_INGESTION_VERSION",
    "SERVICE_SNAPSHOT_ID",
    "CuratedNewsSelection",
    "NewsCollectionWindow",
    "NewsCurationError",
    "NewsCurationRule",
    "NewsCoverage",
    "NewsQuerySpec",
    "NewsSearchQuery",
    "NewsSnapshotConfig",
    "NewsSnapshotValidationError",
    "build_curated_news_payload",
    "build_merged_news_candidate_payload",
    "build_news_candidate_payload",
    "calculate_news_coverage",
    "curate_news_documents",
    "load_news_candidate_documents",
    "load_news_snapshot_config",
    "normalize_collected_news_pages",
    "summarize_collected_news_window",
    "write_utf8_json",
]
