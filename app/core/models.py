from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.status import EvidenceDecisionStatus, ProviderStatus, RetrievalStatus

T = TypeVar("T")

EvidenceScope = Literal["company_specific", "industry_common", "multi_company"]

_WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[\\/]")


def _has_duplicates(values: list[str]) -> bool:
    return len(values) != len(set(values))


def _looks_like_local_absolute_path(value: str) -> bool:
    normalized = value.replace("\\", "/")
    return (
        value.startswith("file://")
        or value.startswith("\\\\")
        or bool(_WINDOWS_ABSOLUTE_PATH.match(value))
        or normalized.startswith("/")
    )


def _assert_no_local_absolute_paths(value: Any, path: str) -> None:
    if isinstance(value, str):
        if _looks_like_local_absolute_path(value):
            raise ValueError(f"{path} must not expose a local absolute path")
        return
    if isinstance(value, dict):
        for key, nested in value.items():
            _assert_no_local_absolute_paths(nested, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, nested in enumerate(value):
            _assert_no_local_absolute_paths(nested, f"{path}[{index}]")


class QuestockModel(BaseModel):
    model_config = ConfigDict(use_enum_values=True)


class DateRange(QuestockModel):
    start: date | None = None
    end: date | None = None

    @model_validator(mode="after")
    def validate_order(self) -> "DateRange":
        if self.start and self.end and self.start > self.end:
            raise ValueError("start must be on or before end")
        return self


class SecurityIdentifier(QuestockModel):
    market: str
    ticker: str
    security_name: str
    security_type: str
    corp_code: str | None = None
    corp_name: str


class QueryPlan(QuestockModel):
    security: SecurityIdentifier | None = None
    intent: str
    date_range: DateRange | None = None
    required_sources: list[str] = Field(default_factory=list)
    required_evidence: list[str] = Field(default_factory=list)
    requires_clarification: bool = False


class MarketSnapshot(QuestockModel):
    security_id: str
    trading_date: date
    observed_at: datetime
    price: float
    previous_close: float
    change: float
    change_percent: float
    volume: int | None = None
    market_session: str
    currency: str
    source: str


class FinancialDocument(QuestockModel):
    document_id: str
    source_type: str
    provider: str
    primary_security_ids: list[str] = Field(default_factory=list)
    mentioned_security_ids: list[str] = Field(default_factory=list)
    title: str
    published_at: datetime | None = None
    source_url: str | None = None
    text: str
    locator: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)
    ingestion_version: str

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if _looks_like_local_absolute_path(value):
            raise ValueError("source_url must not expose a local absolute path")
        if not value.startswith(("http://", "https://")):
            raise ValueError("source_url must be an HTTP(S) URL or None")
        return value

    @field_validator("locator")
    @classmethod
    def validate_locator(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not value:
            raise ValueError("locator must not be empty")
        _assert_no_local_absolute_paths(value, "locator")
        return value

    @model_validator(mode="after")
    def validate_security_sets(self) -> "FinancialDocument":
        if not self.primary_security_ids and not self.mentioned_security_ids:
            raise ValueError("primary_security_ids and mentioned_security_ids cannot both be empty")
        if _has_duplicates(self.primary_security_ids):
            raise ValueError("primary_security_ids must not contain duplicates")
        if _has_duplicates(self.mentioned_security_ids):
            raise ValueError("mentioned_security_ids must not contain duplicates")
        overlap = set(self.primary_security_ids) & set(self.mentioned_security_ids)
        if overlap:
            raise ValueError("primary_security_ids and mentioned_security_ids must not overlap")
        return self

    @property
    def security_ids(self) -> set[str]:
        return set(self.primary_security_ids) | set(self.mentioned_security_ids)


class Evidence(QuestockModel):
    evidence_id: str
    document_id: str
    source_type: str
    title: str
    source_url: str | None = None
    published_at: datetime | None = None
    subject_security_ids: list[str] = Field(default_factory=list)
    mentioned_security_ids: list[str] = Field(default_factory=list)
    scope: EvidenceScope
    snippet: str
    locator: dict[str, Any]
    retrieval_score: float | None = None

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if _looks_like_local_absolute_path(value):
            raise ValueError("source_url must not expose a local absolute path")
        if not value.startswith(("http://", "https://")):
            raise ValueError("source_url must be an HTTP(S) URL or None")
        return value

    @field_validator("locator")
    @classmethod
    def validate_locator(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not value:
            raise ValueError("locator must not be empty")
        _assert_no_local_absolute_paths(value, "locator")
        return value

    @model_validator(mode="after")
    def validate_scope(self) -> "Evidence":
        if _has_duplicates(self.subject_security_ids):
            raise ValueError("subject_security_ids must not contain duplicates")
        if _has_duplicates(self.mentioned_security_ids):
            raise ValueError("mentioned_security_ids must not contain duplicates")
        overlap = set(self.subject_security_ids) & set(self.mentioned_security_ids)
        if overlap:
            raise ValueError("subject_security_ids and mentioned_security_ids must not overlap")
        if self.scope == "company_specific" and len(self.subject_security_ids) != 1:
            raise ValueError("company_specific evidence must have exactly one subject")
        if self.scope == "industry_common" and self.subject_security_ids:
            raise ValueError("industry_common evidence must not have subjects")
        if self.scope == "multi_company" and len(self.subject_security_ids) < 2:
            raise ValueError("multi_company evidence must have at least two subjects")
        return self


class ProviderResult(QuestockModel, Generic[T]):
    status: ProviderStatus
    data: T | None = None
    error_code: str | None = None
    message: str | None = None
    fetched_at: datetime
    from_cache: bool = False


class RetrievalRequest(QuestockModel):
    query: str
    security_id: str
    source_types: list[str]
    date_range: DateRange | None = None
    document_types: list[str] | None = None
    top_k: int = Field(default=6, gt=0)


class RetrievalResult(QuestockModel):
    evidence: list[Evidence] = Field(default_factory=list)
    status: RetrievalStatus = RetrievalStatus.OK
    strategy: str
    low_relevance: bool = False
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class SessionContext(QuestockModel):
    current_security_id: str | None = None
    current_date_range: DateRange | None = None
    previous_intent: str | None = None
    previous_source_types: list[str] = Field(default_factory=list)


class FinancialAnswer(QuestockModel):
    answer: str
    status: EvidenceDecisionStatus
    security: SecurityIdentifier | None = None
    basis_date: datetime | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    missing_sources: list[str] = Field(default_factory=list)


def ensure_evidence_matches_document(evidence: Evidence, document: FinancialDocument) -> None:
    if evidence.document_id != document.document_id:
        raise ValueError("evidence.document_id must match document.document_id")
    evidence_security_ids = set(evidence.subject_security_ids) | set(evidence.mentioned_security_ids)
    invalid_ids = evidence_security_ids - document.security_ids
    if invalid_ids:
        raise ValueError("evidence security IDs must be present in the linked document")
