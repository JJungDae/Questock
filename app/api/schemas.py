from __future__ import annotations

from datetime import date, datetime, time
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.answer.models import AnswerSections
from app.core.models import Evidence, SecurityIdentifier

SEOUL_TZ = ZoneInfo("Asia/Seoul")

ProviderStatusValue = Literal[
    "ok",
    "no_data",
    "invalid_query",
    "unauthorized",
    "rate_limited",
    "timeout",
    "provider_unavailable",
    "parse_error",
]
ResolutionStatusValue = Literal[
    "resolved",
    "ambiguous",
    "not_found",
    "unsupported",
]
RetrievalStatusValue = Literal["ok", "empty", "low_relevance"]
EvidenceDecisionStatusValue = Literal[
    "complete",
    "partial",
    "provider_failed",
    "no_evidence",
    "blocked",
]
IntentValue = Literal[
    "recent_issue",
    "disclosure_summary",
    "research_report_summary",
    "risk_factors",
    "financial_term",
    "multi_source_summary",
    "price",
    "price_move",
    "prohibited_advice",
    "out_of_scope",
]
SourceTypeValue = Literal[
    "news",
    "disclosure",
    "research_report",
    "glossary",
]
FreshnessWarningValue = Literal[
    "missing_published_at",
    "future_published_at",
    "stale_news",
    "stale_research_report",
    "disclosure_window_extended",
    "insufficient_disclosure_coverage",
    "unresolved_disclosure_correction",
]
SecurityIDValue = Literal[
    "KRX:005930",
    "KRX:000660",
    "KRX:005380",
]


class PublicModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ChatRequest(PublicModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str = Field(min_length=1, max_length=128)
    as_of: datetime | None = None

    @field_validator("message", "session_id")
    @classmethod
    def trim_nonblank(cls, value: str) -> str:
        output = value.strip()
        if not output:
            raise ValueError("value must not be blank")
        return output

    @field_validator("as_of")
    @classmethod
    def validate_as_of(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        local = value.astimezone(SEOUL_TZ)
        if (
            local.date()
            not in {
                date(2026, 7, 24),
                date(2026, 7, 25),
                date(2026, 7, 26),
                date(2026, 7, 27),
            }
            or local.time().replace(tzinfo=None)
            not in {
                time(8, 30),
                time(10, 0),
                time(14, 0),
                time(19, 0),
                time(21, 0),
            }
        ):
            raise ValueError("as_of is not a supported checkpoint")
        return value


class PublicSecuritySummary(PublicModel):
    resolution_status: ResolutionStatusValue
    security_id: SecurityIDValue | None


class PublicQueryPlanSummary(PublicModel):
    intent: IntentValue
    required_sources: list[SourceTypeValue]
    date_start: date | None
    date_end: date | None


class PublicSourceSummary(PublicModel):
    source_type: SourceTypeValue
    provider_status: ProviderStatusValue
    document_count: int = Field(ge=0)
    from_cache: bool


class PublicEvidencePipelineSummary(PublicModel):
    normalized_count: int = Field(ge=0)
    hard_filtered_count: int = Field(ge=0)
    freshness_retained_count: int = Field(ge=0)
    freshness_warning_codes: list[FreshnessWarningValue]
    retrieval_status: RetrievalStatusValue
    retrieval_selected_count: int = Field(ge=0)


class PublicDecisionSummary(PublicModel):
    evidence_decision_status: EvidenceDecisionStatusValue
    satisfied_sources: list[SourceTypeValue]
    missing_sources: list[SourceTypeValue]
    no_data_sources: list[SourceTypeValue]
    failed_sources: list[SourceTypeValue]


class PublicContextBudgetSummary(PublicModel):
    input_count: int = Field(ge=0)
    unique_count: int = Field(ge=0)
    selected_count: int = Field(ge=0)
    duplicate_drop_count: int = Field(ge=0)
    source_cap_drop_count: int = Field(ge=0)
    count_cap_drop_count: int = Field(ge=0)
    context_drop_count: int = Field(ge=0)
    estimated_context_tokens: int = Field(ge=0)
    estimated_context_chars: int = Field(ge=0)


class PublicCitationSummary(PublicModel):
    claim_count: int = Field(ge=0)
    citation_count: int = Field(ge=0)
    rejection_count: int = Field(ge=0)


class PublicGenerationSummary(PublicModel):
    mode: Literal["llm", "fixed_template", "blocked", "not_called"]
    llm_status: Literal[
        "ok",
        "timeout",
        "rate_limited",
        "authentication_error",
        "provider_unavailable",
        "invalid_response",
        "content_blocked",
    ] | None
    model: Literal["gemini/gemini-3.5-flash"] | None
    live_verified: bool


class PublicMarketSnapshot(PublicModel):
    checkpoint_id: str
    requested_as_of: datetime
    observed_at: datetime
    price: float
    previous_close: float
    change: float
    change_percent: float
    volume: int | None
    market_code: Literal["J", "NX", "UN"]
    market_session: Literal[
        "pre_market",
        "regular",
        "after_market",
        "after_close",
        "closed",
    ]
    market_status: Literal[
        "open",
        "closed",
        "no_trade_yet",
        "no_data",
    ]
    currency: Literal["KRW"]


class PublicComparisonSource(PublicModel):
    source_id: str = Field(min_length=1, max_length=128)
    source_type: Literal["news", "disclosure", "research_report"]
    title: str = Field(min_length=1, max_length=500)
    publisher: str = Field(min_length=1, max_length=120)
    published_at: datetime
    source_url: str = Field(min_length=1, max_length=2000)


class PublicComparisonLineageSummary(PublicModel):
    confirmed_independent_count: int = Field(ge=0)
    confirmed_republication_count: int = Field(ge=0)
    unknown_count: int = Field(ge=0)


class PublicComparisonClaim(PublicModel):
    text: str = Field(min_length=1, max_length=1000)
    source_ids: list[str] = Field(min_length=1, max_length=20)
    corroboration_status: Literal[
        "independently_corroborated",
        "same_lineage_repeated",
        "lineage_unknown",
    ]


class PublicComparisonPerspective(PublicModel):
    text: str = Field(min_length=1, max_length=1000)
    source: PublicComparisonSource
    source_locator: str = Field(min_length=1, max_length=300)
    actual_or_estimate: Literal["actual", "estimate", "interpretation"]


class PublicDisclosureLink(PublicModel):
    role: Literal[
        "official_confirmation",
        "official_background",
        "official_conflict",
        "no_link",
    ]
    text: str = Field(min_length=1, max_length=1000)
    source: PublicComparisonSource | None = None
    source_locator: str | None = Field(default=None, max_length=300)


class PublicEvidenceComparison(PublicModel):
    comparison_status: Literal[
        "coverage_only",
        "background_linked",
        "not_applicable",
    ]
    event_id: str = Field(min_length=1, max_length=128)
    event_label: str = Field(min_length=1, max_length=500)
    article_sources: list[PublicComparisonSource] = Field(max_length=20)
    article_total_count: int = Field(ge=2)
    article_displayed_count: int = Field(ge=2, le=20)
    source_lineage_summary: PublicComparisonLineageSummary
    common_facts: list[PublicComparisonClaim] = Field(max_length=20)
    different_interpretations: list[PublicComparisonPerspective] = Field(
        max_length=20
    )
    unconfirmed_claims: list[str] = Field(max_length=20)
    missing_evidence: list[str] = Field(max_length=20)
    disclosure_links: list[PublicDisclosureLink] = Field(max_length=20)


class PublicProcessSummary(PublicModel):
    trace_version: Literal["m3-01-v1"] = "m3-01-v1"
    data_mode: Literal["recorded", "live", "mixed", "unconfigured"]
    live_connectivity_checked: bool
    security: PublicSecuritySummary
    query_plan: PublicQueryPlanSummary
    sources: list[PublicSourceSummary]
    evidence_pipeline: PublicEvidencePipelineSummary
    decision: PublicDecisionSummary
    context_budget: PublicContextBudgetSummary
    citation: PublicCitationSummary
    generation: PublicGenerationSummary


class ChatResponse(PublicModel):
    status: EvidenceDecisionStatusValue
    security: SecurityIdentifier | None
    basis_date: date
    basis_at: datetime | None = None
    market_snapshot: PublicMarketSnapshot | None = None
    evidence_comparison: PublicEvidenceComparison | None = None
    answer_sections: AnswerSections
    evidence: list[Evidence]
    warnings: list[str]
    missing_sources: list[str]
    diagnostics_public: PublicProcessSummary


__all__ = [
    "ChatRequest",
    "ChatResponse",
    "PublicCitationSummary",
    "PublicContextBudgetSummary",
    "PublicDecisionSummary",
    "PublicDisclosureLink",
    "PublicEvidenceComparison",
    "PublicEvidencePipelineSummary",
    "PublicGenerationSummary",
    "PublicMarketSnapshot",
    "PublicComparisonClaim",
    "PublicComparisonLineageSummary",
    "PublicComparisonPerspective",
    "PublicComparisonSource",
    "PublicProcessSummary",
    "PublicQueryPlanSummary",
    "PublicSecuritySummary",
    "PublicSourceSummary",
]
