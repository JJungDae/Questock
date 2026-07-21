from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, ValidationError, field_validator, model_validator

from app.core.models import QuestockModel, SecurityIdentifier
from app.core.status import ResolutionStatus

MatchedBy = Literal["name", "ticker", "security_id", "alias", "unsupported_rule", "none"]
VerificationStatus = Literal["verified", "candidate", "blocked"]

DEFAULT_FIXTURE_PATH = Path(__file__).resolve().parents[2] / "data" / "securities.json"
_WHITESPACE_RE = re.compile(r"\s+")
_FOREIGN_TICKER_RE = re.compile(r"^[a-z]{1,5}([.-][a-z])?$")


class FixtureValidationError(ValueError):
    """Raised when the supported security fixture has unsafe duplicates."""


class ResolutionResult(QuestockModel):
    status: ResolutionStatus
    security: SecurityIdentifier | None = None
    candidates: list[SecurityIdentifier] = Field(default_factory=list)
    normalized_query: str
    message: str | None = None
    matched_by: MatchedBy

    @model_validator(mode="after")
    def validate_status_contract(self) -> "ResolutionResult":
        status = str(self.status)
        if status == ResolutionStatus.RESOLVED.value:
            if self.security is None:
                raise ValueError("resolved result requires security")
            if self.candidates:
                raise ValueError("resolved result candidates must be empty")
            if self.matched_by not in {"name", "ticker", "security_id", "alias"}:
                raise ValueError("resolved result has invalid matched_by")
            return self

        if status == ResolutionStatus.AMBIGUOUS.value:
            if self.security is not None:
                raise ValueError("ambiguous result must not include security")
            if not self.candidates:
                raise ValueError("ambiguous result requires at least one candidate")
            if not self.message:
                raise ValueError("ambiguous result requires clarification message")
            if self.matched_by != "none":
                raise ValueError("ambiguous result matched_by must be none")
            return self

        if status == ResolutionStatus.NOT_FOUND.value:
            if self.security is not None:
                raise ValueError("not_found result must not include security")
            if self.candidates:
                raise ValueError("not_found result candidates must be empty")
            if self.matched_by != "none":
                raise ValueError("not_found result matched_by must be none")
            return self

        if status == ResolutionStatus.UNSUPPORTED.value:
            if self.security is not None:
                raise ValueError("unsupported result must not include security")
            if self.candidates:
                raise ValueError("unsupported result candidates must be empty")
            if self.matched_by != "unsupported_rule":
                raise ValueError("unsupported result matched_by must be unsupported_rule")
            return self

        raise ValueError(f"unknown resolution status: {self.status}")


class _SecurityRecord(QuestockModel):
    security_id: str
    market: str
    ticker: str
    security_name: str
    security_type: str
    corp_code: str | None = None
    corp_name: str
    verification_status: VerificationStatus
    verified_at: str | None = None
    aliases: list[str] = Field(default_factory=list)

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, value: str) -> str:
        if not re.fullmatch(r"\d{6}", value):
            raise FixtureValidationError("ticker must be a 6-digit string")
        return value

    @model_validator(mode="after")
    def validate_security_id(self) -> "_SecurityRecord":
        expected = f"{self.market.upper()}:{self.ticker}"
        if self.security_id != expected:
            raise FixtureValidationError("security_id must match market:ticker")
        normalized_aliases = [_normalize_lookup(alias) for alias in self.aliases]
        if any(not alias for alias in normalized_aliases):
            raise FixtureValidationError("aliases must not contain empty values")
        if len(normalized_aliases) != len(set(normalized_aliases)):
            raise FixtureValidationError("aliases must not contain duplicates")
        return self


class _AmbiguousTerm(QuestockModel):
    term: str
    candidate_security_ids: list[str]
    message: str

    @model_validator(mode="after")
    def validate_term(self) -> "_AmbiguousTerm":
        if not _normalize_lookup(self.term):
            raise FixtureValidationError("ambiguous term must not be empty")
        if not self.candidate_security_ids:
            raise FixtureValidationError("ambiguous term requires at least one candidate")
        if not self.message:
            raise FixtureValidationError("ambiguous term requires message")
        return self


class _UnsupportedTerm(QuestockModel):
    term: str
    reason: str

    @model_validator(mode="after")
    def validate_term(self) -> "_UnsupportedTerm":
        if not _normalize_lookup(self.term):
            raise FixtureValidationError("unsupported term must not be empty")
        if not self.reason:
            raise FixtureValidationError("unsupported term requires reason")
        return self


def security_id_for(security: SecurityIdentifier) -> str:
    return f"{security.market}:{security.ticker}"


def _normalize_lookup(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    normalized = _WHITESPACE_RE.sub(" ", normalized).strip()
    return normalized.casefold()


class SecurityResolver:
    def __init__(
        self,
        fixture_path: str | Path | None = None,
        fixture_data: dict[str, Any] | None = None,
    ) -> None:
        if fixture_data is None:
            path = Path(fixture_path) if fixture_path is not None else DEFAULT_FIXTURE_PATH
            fixture_data = json.loads(path.read_text(encoding="utf-8"))
        self._load_fixture(fixture_data)

    def resolve(self, query: str) -> ResolutionResult:
        normalized_query = _normalize_lookup(query)
        if not normalized_query:
            return ResolutionResult(
                status=ResolutionStatus.NOT_FOUND,
                normalized_query=normalized_query,
                message="입력한 종목을 찾을 수 없습니다.",
                matched_by="none",
            )

        if normalized_query in self._security_id_index:
            return self._resolved(self._security_id_index[normalized_query], normalized_query, "security_id")

        if normalized_query in self._ticker_index:
            return self._resolved(self._ticker_index[normalized_query], normalized_query, "ticker")

        if normalized_query in self._name_index:
            return self._resolved(self._name_index[normalized_query], normalized_query, "name")

        if normalized_query in self._alias_index:
            return self._resolved(self._alias_index[normalized_query], normalized_query, "alias")

        if normalized_query in self._ambiguous_terms:
            term = self._ambiguous_terms[normalized_query]
            return ResolutionResult(
                status=ResolutionStatus.AMBIGUOUS,
                candidates=[self._to_security(self._records_by_id[security_id]) for security_id in term.candidate_security_ids],
                normalized_query=normalized_query,
                message=term.message,
                matched_by="none",
            )

        if normalized_query in self._unsupported_terms or _FOREIGN_TICKER_RE.fullmatch(normalized_query):
            return ResolutionResult(
                status=ResolutionStatus.UNSUPPORTED,
                normalized_query=normalized_query,
                message="지원 범위 밖의 종목 입력입니다.",
                matched_by="unsupported_rule",
            )

        return ResolutionResult(
            status=ResolutionStatus.NOT_FOUND,
            normalized_query=normalized_query,
            message="입력한 종목을 찾을 수 없습니다.",
            matched_by="none",
        )

    @property
    def supported_security_ids(self) -> set[str]:
        return set(self._records_by_id)

    def _load_fixture(self, fixture_data: dict[str, Any]) -> None:
        try:
            records = [_SecurityRecord.model_validate(item) for item in fixture_data.get("securities", [])]
        except ValidationError as exc:
            raise FixtureValidationError(str(exc)) from exc
        if not records:
            raise FixtureValidationError("fixture must include at least one security")

        self._records_by_id: dict[str, _SecurityRecord] = {}
        self._security_id_index: dict[str, _SecurityRecord] = {}
        self._ticker_index: dict[str, _SecurityRecord] = {}
        self._name_index: dict[str, _SecurityRecord] = {}
        self._alias_index: dict[str, _SecurityRecord] = {}
        global_lookup_owner: dict[str, str] = {}

        for record in records:
            if record.security_id in self._records_by_id:
                raise FixtureValidationError(f"duplicate security_id: {record.security_id}")
            self._records_by_id[record.security_id] = record
            self._register_lookup(
                self._security_id_index,
                global_lookup_owner,
                record.security_id,
                record,
                "security_id",
            )
            self._register_lookup(self._ticker_index, global_lookup_owner, record.ticker, record, "ticker")
            self._register_lookup(self._name_index, global_lookup_owner, record.security_name, record, "name")
            for alias in record.aliases:
                self._register_lookup(self._alias_index, global_lookup_owner, alias, record, "alias")

        self._ambiguous_terms = self._load_ambiguous_terms(fixture_data.get("ambiguous_terms", []))
        self._unsupported_terms = self._load_unsupported_terms(
            fixture_data.get("unsupported", []),
            global_lookup_owner,
            self._ambiguous_terms,
        )

    def _register_lookup(
        self,
        index: dict[str, _SecurityRecord],
        global_lookup_owner: dict[str, str],
        value: str,
        record: _SecurityRecord,
        label: str,
    ) -> None:
        normalized = _normalize_lookup(value)
        if not normalized:
            raise FixtureValidationError(f"{label} must not be empty")
        existing_record = index.get(normalized)
        if existing_record is not None and existing_record.security_id != record.security_id:
            raise FixtureValidationError(f"{label} collision: {value}")
        existing_owner = global_lookup_owner.get(normalized)
        if existing_owner is not None and existing_owner != record.security_id:
            raise FixtureValidationError(f"canonical lookup collision: {value}")
        index[normalized] = record
        global_lookup_owner.setdefault(normalized, record.security_id)

    def _load_ambiguous_terms(self, raw_terms: list[dict[str, Any]]) -> dict[str, _AmbiguousTerm]:
        terms: dict[str, _AmbiguousTerm] = {}
        for item in raw_terms:
            try:
                term = _AmbiguousTerm.model_validate(item)
            except ValidationError as exc:
                raise FixtureValidationError(str(exc)) from exc
            normalized = _normalize_lookup(term.term)
            if normalized in terms:
                raise FixtureValidationError(f"duplicate ambiguous term: {term.term}")
            unknown_ids = set(term.candidate_security_ids) - set(self._records_by_id)
            if unknown_ids:
                raise FixtureValidationError("ambiguous candidates must be in supported universe")
            terms[normalized] = term
        return terms

    def _load_unsupported_terms(
        self,
        raw_terms: list[dict[str, Any]],
        global_lookup_owner: dict[str, str],
        ambiguous_terms: dict[str, _AmbiguousTerm],
    ) -> set[str]:
        terms: set[str] = set()
        for item in raw_terms:
            try:
                term = _UnsupportedTerm.model_validate(item)
            except ValidationError as exc:
                raise FixtureValidationError(str(exc)) from exc
            normalized = _normalize_lookup(term.term)
            if normalized in terms:
                raise FixtureValidationError(f"duplicate unsupported term: {term.term}")
            if normalized in global_lookup_owner:
                raise FixtureValidationError(f"unsupported term collides with supported lookup: {term.term}")
            if normalized in ambiguous_terms:
                raise FixtureValidationError(f"unsupported term collides with ambiguous term: {term.term}")
            terms.add(normalized)
        return terms

    def _resolved(self, record: _SecurityRecord, normalized_query: str, matched_by: MatchedBy) -> ResolutionResult:
        return ResolutionResult(
            status=ResolutionStatus.RESOLVED,
            security=self._to_security(record),
            candidates=[],
            normalized_query=normalized_query,
            matched_by=matched_by,
        )

    def _to_security(self, record: _SecurityRecord) -> SecurityIdentifier:
        corp_code = record.corp_code if record.verification_status == "verified" else None
        return SecurityIdentifier(
            market=record.market,
            ticker=record.ticker,
            security_name=record.security_name,
            security_type=record.security_type,
            corp_code=corp_code,
            corp_name=record.corp_name,
        )


__all__ = [
    "DEFAULT_FIXTURE_PATH",
    "FixtureValidationError",
    "MatchedBy",
    "ResolutionResult",
    "SecurityResolver",
    "security_id_for",
]
