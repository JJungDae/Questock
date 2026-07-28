from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.api.schemas import (
    PublicComparisonLineageSummary,
    PublicComparisonPerspective,
    PublicComparisonSource,
    PublicDisclosureLink,
    PublicEvidenceComparison,
)

_DEFAULT_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "m5_d1_evidence_comparisons.json"
)
_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9.+-]*|[가-힣]{2,}|\d+(?:\.\d+)?")
_STOP_TOKENS = frozenset(
    {
        "삼성전자",
        "하이닉스",
        "sk하이닉스",
        "현대차",
        "현대자동차",
        "최근",
        "오늘",
        "이슈",
        "뉴스",
        "호재",
        "악재",
        "주가",
        "상승",
        "하락",
        "이유",
        "원인",
        "상황",
        "알려줘",
        "해줘",
        "관련",
        "대한",
    }
)
_EVENT_QUERY_MARKERS = (
    "최근",
    "이슈",
    "뉴스",
    "호재",
    "악재",
    "오늘",
    "왜",
    "원인",
    "상황",
    "오른",
    "올랐",
    "떨어",
    "하락",
    "상승",
)
_GENERIC_LINK_TOPICS = frozenset(
    {
        "ai",
        "규모",
        "기술",
        "달러",
        "매출",
        "메모리",
        "반도체",
        "분기",
        "파운드리",
        "사업",
        "생산",
        "수급",
        "실적",
        "영업이익",
        "위험",
        "전망",
        "제품",
        "투자",
    }
)


class M5D1EvidenceComparisonError(ValueError):
    """Raised when the public M5-D1 sidecar is invalid."""


class _StoredModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StoredComparisonSource(_StoredModel):
    source_id: str = Field(min_length=1, max_length=128)
    source_type: Literal["news", "disclosure", "research_report"]
    title: str = Field(min_length=1, max_length=500)
    publisher: str = Field(min_length=1, max_length=120)
    published_at: datetime
    source_url: str = Field(min_length=1, max_length=2000)


class StoredEventCluster(_StoredModel):
    event_id: str = Field(min_length=1, max_length=128)
    security_id: Literal["KRX:005930", "KRX:000660", "KRX:005380"]
    event_label: str = Field(min_length=1, max_length=500)
    event_terms: list[str] = Field(min_length=1, max_length=30)
    first_published_at: datetime
    last_published_at: datetime
    article_sources: list[StoredComparisonSource] = Field(
        min_length=2,
        max_length=100,
    )
    security_match_basis: Literal["title_alias_only"]
    cluster_basis: Literal["deterministic_title_similarity"]
    review_status: Literal["labeled", "conservative_automatic"]


class StoredReportPerspective(_StoredModel):
    source: StoredComparisonSource
    security_id: Literal["KRX:005930", "KRX:000660", "KRX:005380"]
    topics: list[str] = Field(min_length=1, max_length=20)
    text: str = Field(min_length=1, max_length=1000)
    actual_or_estimate: Literal["actual", "estimate", "interpretation"]
    source_locator: str = Field(min_length=1, max_length=200)
    verified_against_source: Literal[True]


class StoredDisclosureBackground(_StoredModel):
    source: StoredComparisonSource
    security_id: Literal["KRX:005930", "KRX:000660", "KRX:005380"]
    topics: list[str] = Field(min_length=1, max_length=20)
    text: str = Field(min_length=1, max_length=1000)
    source_locator: str = Field(min_length=1, max_length=300)
    link_basis: Literal[
        "verified_body_fact",
        "official_list_metadata",
    ]
    verified_against_source: Literal[True]


class StoredComparisonPayload(_StoredModel):
    schema_version: Literal["m5-d1-evidence-comparison-v2"]
    built_at: datetime
    source_inventory_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    report_inventory_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    event_clusters: list[StoredEventCluster]
    report_perspectives: list[StoredReportPerspective]
    disclosure_backgrounds: list[StoredDisclosureBackground]


class M5D1EvidenceComparisonStore:
    def __init__(self, path: Path | None = None) -> None:
        source_path = path or _DEFAULT_PATH
        try:
            raw = json.loads(source_path.read_text(encoding="utf-8"))
            self._payload = StoredComparisonPayload.model_validate(raw)
        except (OSError, ValueError, TypeError, ValidationError):
            raise M5D1EvidenceComparisonError(
                "M5-D1 comparison data is invalid"
            ) from None
        self._validate_payload()

    def select(
        self,
        *,
        query: str,
        security_id: str | None,
        as_of: datetime,
    ) -> PublicEvidenceComparison | None:
        if (
            security_id not in {"KRX:005930", "KRX:000660", "KRX:005380"}
            or not isinstance(query, str)
            or not query.strip()
            or not isinstance(as_of, datetime)
            or as_of.tzinfo is None
        ):
            return None
        cutoff = as_of.astimezone(UTC)
        query_terms = _terms(query)
        recognized_event_terms = query_terms.intersection(
            term
            for cluster in self._payload.event_clusters
            for term in cluster.event_terms
        )
        if not recognized_event_terms and not any(
            marker in query.casefold()
            for marker in _EVENT_QUERY_MARKERS
        ):
            return None
        candidates: list[tuple[float, StoredEventCluster]] = []
        for cluster in self._payload.event_clusters:
            if cluster.security_id != security_id:
                continue
            eligible = [
                item
                for item in cluster.article_sources
                if item.published_at.astimezone(UTC) <= cutoff
            ]
            if len(eligible) < 2:
                continue
            overlap = len(query_terms.intersection(cluster.event_terms))
            if recognized_event_terms and overlap == 0:
                continue
            score = float(overlap * 10)
            eligible_latest = max(
                item.published_at.astimezone(UTC)
                for item in eligible
            )
            score += eligible_latest.timestamp() / 10**10
            candidates.append((score, cluster))
        if not candidates:
            return None
        _, selected = max(candidates, key=lambda item: item[0])
        articles = [
            item
            for item in selected.article_sources
            if item.published_at.astimezone(UTC) <= cutoff
        ]
        event_terms = set(selected.event_terms)
        perspectives = self._select_perspectives(
            security_id=security_id,
            event_terms=event_terms,
            query_terms=query_terms,
            cutoff=cutoff,
        )
        disclosure_links = self._select_disclosures(
            security_id=security_id,
            event_terms=event_terms,
            query_terms=query_terms,
            cutoff=cutoff,
        )
        status = (
            "background_linked"
            if perspectives or any(
                item.role != "no_link" for item in disclosure_links
            )
            else "coverage_only"
        )
        displayed_articles = articles[:20]
        return PublicEvidenceComparison(
            comparison_status=status,
            event_id=selected.event_id,
            event_label=selected.event_label,
            article_sources=[
                PublicComparisonSource.model_validate(
                    item.model_dump(mode="python")
                )
                for item in displayed_articles
            ],
            article_total_count=len(articles),
            article_displayed_count=len(displayed_articles),
            source_lineage_summary=PublicComparisonLineageSummary(
                confirmed_independent_count=0,
                confirmed_republication_count=0,
                unknown_count=len(articles),
            ),
            common_facts=[],
            different_interpretations=perspectives,
            unconfirmed_claims=[],
            missing_evidence=[
                (
                    "현재 수집본은 기사 제목 중심이므로 공통 사실이나 "
                    "기사별 해석 차이는 단정하지 않았습니다."
                ),
                (
                    "기사 원출처 관계를 확인하지 못해 매체 수를 독립 "
                    "근거 수로 계산하지 않았습니다."
                ),
            ],
            disclosure_links=disclosure_links,
        )

    def _select_perspectives(
        self,
        *,
        security_id: str,
        event_terms: set[str],
        query_terms: set[str],
        cutoff: datetime,
    ) -> list[PublicComparisonPerspective]:
        ranked: list[tuple[int, StoredReportPerspective]] = []
        focus = event_terms | query_terms
        specific_focus = focus - _GENERIC_LINK_TOPICS
        for item in self._payload.report_perspectives:
            if (
                item.security_id != security_id
                or item.source.published_at.astimezone(UTC) > cutoff
            ):
                continue
            specific_overlap = len(
                specific_focus.intersection(item.topics)
            )
            if specific_overlap:
                score = (
                    specific_overlap * 100
                    + len(focus.intersection(item.topics))
                )
                ranked.append((score, item))
        ranked.sort(
            key=lambda pair: (
                pair[0],
                pair[1].source.published_at,
                pair[1].source.publisher,
            ),
            reverse=True,
        )
        return [
            PublicComparisonPerspective(
                text=item.text,
                source=PublicComparisonSource.model_validate(
                    item.source.model_dump(mode="python")
                ),
                source_locator=item.source_locator,
                actual_or_estimate=item.actual_or_estimate,
            )
            for _, item in ranked[:3]
        ]

    def _select_disclosures(
        self,
        *,
        security_id: str,
        event_terms: set[str],
        query_terms: set[str],
        cutoff: datetime,
    ) -> list[PublicDisclosureLink]:
        focus = event_terms | query_terms
        specific_focus = focus - _GENERIC_LINK_TOPICS
        ranked: list[
            tuple[int, datetime, StoredDisclosureBackground]
        ] = []
        for item in self._payload.disclosure_backgrounds:
            if (
                item.security_id != security_id
                or item.source.published_at.astimezone(UTC) > cutoff
            ):
                continue
            specific_overlap = len(
                specific_focus.intersection(item.topics)
            )
            if specific_overlap:
                score = (
                    specific_overlap * 100
                    + len(focus.intersection(item.topics)) * 10
                    + (
                        1
                        if item.link_basis
                        == "official_list_metadata"
                        else 0
                    )
                )
                ranked.append(
                    (
                        score,
                        item.source.published_at.astimezone(UTC),
                        item,
                    )
                )
        ranked.sort(
            key=lambda candidate: (
                candidate[0],
                candidate[1],
            ),
            reverse=True,
        )
        if not ranked:
            return [
                PublicDisclosureLink(
                    role="no_link",
                    text="이 사건과 직접 연결해 확인한 DART 공시는 없습니다.",
                )
            ]
        return [
                PublicDisclosureLink(
                    role="official_background",
                    text=item.text,
                    source=PublicComparisonSource.model_validate(
                        item.source.model_dump(mode="python")
                    ),
                    source_locator=item.source_locator,
                )
            for _, _, item in ranked[:2]
        ]

    def _validate_payload(self) -> None:
        source_ids: set[str] = set()
        for cluster in self._payload.event_clusters:
            if (
                cluster.first_published_at > cluster.last_published_at
                or cluster.security_match_basis != "title_alias_only"
                or len(
                    {
                        item.publisher
                        for item in cluster.article_sources
                    }
                )
                < 2
            ):
                raise M5D1EvidenceComparisonError(
                    "M5-D1 comparison data is invalid"
                )
            for source in cluster.article_sources:
                if source.source_type != "news":
                    raise M5D1EvidenceComparisonError(
                        "M5-D1 comparison data is invalid"
                    )
                source_ids.add(source.source_id)
        for item in self._payload.report_perspectives:
            if (
                item.source.source_type != "research_report"
                or item.source.source_id in source_ids
            ):
                raise M5D1EvidenceComparisonError(
                    "M5-D1 comparison data is invalid"
                )
            source_ids.add(item.source.source_id)
        for item in self._payload.disclosure_backgrounds:
            if item.source.source_type != "disclosure":
                raise M5D1EvidenceComparisonError(
                    "M5-D1 comparison data is invalid"
                )


def _terms(value: str) -> set[str]:
    return {
        token.casefold()
        for token in _TOKEN.findall(value)
        if token.casefold() not in _STOP_TOKENS and len(token) >= 2
    }


__all__ = [
    "M5D1EvidenceComparisonError",
    "M5D1EvidenceComparisonStore",
    "StoredComparisonPayload",
]
