from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

AnswerSectionName = Literal[
    "summary",
    "facts",
    "interpretation",
    "inference",
    "positive_factors",
    "risk_factors",
    "uncertainty",
]

_SECTION_NAMES = frozenset(
    {
        "summary",
        "facts",
        "interpretation",
        "inference",
        "positive_factors",
        "risk_factors",
        "uncertainty",
    }
)


class DraftClaim(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_id: str = Field(
        min_length=1,
        max_length=80,
        description="Unique claim ID such as claim-1.",
    )
    section: AnswerSectionName = Field(
        description=(
            "The first and only summary claim uses summary; later claims "
            "follow the required section order."
        )
    )
    text: str = Field(
        min_length=1,
        max_length=1200,
        description=(
            "One complete eligible evidence snippet copied character-for-"
            "character, without paraphrasing, combining, or added text."
        ),
    )
    evidence_ids: tuple[str, ...] = Field(
        min_length=1,
        max_length=6,
        description=(
            "Exactly the Evidence ID belonging to the copied snippet."
        ),
    )

    @field_validator("claim_id", "text")
    @classmethod
    def validate_nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("draft text must not be blank")
        return value.strip()

    @field_validator("evidence_ids")
    @classmethod
    def validate_evidence_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if (
            any(not item.strip() for item in value)
            or len(value) != len(set(value))
        ):
            raise ValueError("draft evidence IDs are invalid")
        return value


class StructuredAnswerDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    claims: tuple[DraftClaim, ...] = Field(
        min_length=1,
        max_length=14,
        description=(
            "One to three citation-bound extractive claims; omit rather "
            "than inventing an unsupported claim."
        ),
    )

    @model_validator(mode="after")
    def validate_claim_ids(self) -> "StructuredAnswerDraft":
        claim_ids = [item.claim_id for item in self.claims]
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("draft claim IDs must be unique")
        return self


class AnswerSections(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: list[str] = Field(default_factory=list)
    facts: list[str] = Field(default_factory=list)
    interpretation: list[str] = Field(default_factory=list)
    inference: list[str] = Field(default_factory=list)
    positive_factors: list[str] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list)

    @field_validator("*")
    @classmethod
    def validate_section(cls, value: list[str]) -> list[str]:
        if any(not isinstance(item, str) or not item.strip() for item in value):
            raise ValueError("answer section values must be nonblank strings")
        return [item.strip() for item in value]

    @classmethod
    def from_claims(cls, claims: tuple[DraftClaim, ...]) -> "AnswerSections":
        values: dict[str, list[str]] = {name: [] for name in _SECTION_NAMES}
        for claim in claims:
            values[claim.section].append(claim.text)
        return cls(**values)


__all__ = [
    "AnswerSectionName",
    "AnswerSections",
    "DraftClaim",
    "StructuredAnswerDraft",
]
