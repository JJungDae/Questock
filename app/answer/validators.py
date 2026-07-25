from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC

from app.answer.models import DraftClaim, StructuredAnswerDraft
from app.core.models import Evidence, QueryPlan

_DIRECT_ACTION = re.compile(
    r"(?:사세요|파세요|보유하세요|"
    r"(?:매수|매도|보유).{0,16}(?:하세요|해야|권장|추천)|"
    r"(?:buy|sell|hold).{0,16}(?:now|should|recommend))",
    re.IGNORECASE,
)
_TARGET_PRICE = re.compile(
    r"(?:목표가|목표\s*가격|target\s*price).{0,24}"
    r"(?:\d|제시|설정|도달)",
    re.IGNORECASE,
)
_EXIT_TIMING = re.compile(
    r"(?:손절|익절|stop[- ]?loss|take[- ]?profit).{0,24}"
    r"(?:\d|가격|시점|하세요|해야|권장|추천)",
    re.IGNORECASE,
)
_GUARANTEE = re.compile(
    r"(?:보장(?:된다|됩니다|한다|합니다)|확정\s*수익|"
    r"틀림없이|무조건|guaranteed?\s+return)",
    re.IGNORECASE,
)
_FUTURE_CERTAINTY = re.compile(
    r"(?:확실히|반드시|분명히).{0,24}"
    r"(?:상승|하락|오른|내린|개선|성장|달성)|"
    r"(?:상승|하락|오를|내릴).{0,16}(?:것이\s*확실|확정)",
    re.IGNORECASE,
)
_DIRECTION_PROBABILITY = re.compile(
    r"(?:상승|하락|오를|내릴|급등|급락).{0,24}"
    r"[-+]?\d+(?:\.\d+)?\s*%",
    re.IGNORECASE,
)
_UNSUPPORTED_CONFLICT_CONCLUSION = re.compile(
    r"(?:기사|자료|근거).{0,16}(?:수가\s*더\s*많|개수가\s*더\s*많|과반|다수이므로)|"
    r"(?:긍정|부정|상승|하락).{0,16}(?:우세|승리|더\s*많으므로)|"
    r"(?:감성|sentiment)\s*(?:점수|score)|"
    r"종합하면.{0,24}(?:매수|매도|상승|하락|긍정|부정)",
    re.IGNORECASE,
)
_NUMERIC_TOKEN = re.compile(
    r"(?<![\dA-Za-z_.])(?:"
    r"\d{4}-\d{2}-\d{2}|"
    r"\d{4}년\s*\d{1,2}월(?:\s*\d{1,2}일)?|"
    r"\d{4}년\s*[1-4]분기|"
    r"(?:(?:KRW|USD|EUR|JPY|₩|\$|€|¥)\s*)?"
    r"[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
    r"(?:\s*(?:%p|%|조원|억원|만원|천원|원|배|주|년|개월|일))?"
    r")(?![\dA-Za-z_.])",
    re.IGNORECASE,
)
_INVALID_INPUT = "answer validation input is invalid"


class AnswerValidationError(ValueError):
    """Raised for malformed validator inputs without raw-content disclosure."""


@dataclass(frozen=True)
class AnswerDraftValidation:
    draft: StructuredAnswerDraft | None
    rejection_count: int
    safety_blocked: bool


def validate_answer_draft(
    draft: StructuredAnswerDraft,
    plan: QueryPlan,
    selected_evidence: Sequence[Evidence],
) -> AnswerDraftValidation:
    canonical_draft = _draft(draft)
    canonical_plan = _plan(plan)
    evidence = _evidence(selected_evidence)

    unsafe = [
        claim
        for claim in canonical_draft.claims
        if is_unsafe_answer_text(claim.text, intent=canonical_plan.intent)
    ]
    if unsafe:
        return AnswerDraftValidation(
            draft=None,
            rejection_count=len(canonical_draft.claims),
            safety_blocked=True,
        )
    if any(
        _UNSUPPORTED_CONFLICT_CONCLUSION.search(_normalize_text(claim.text))
        for claim in canonical_draft.claims
    ):
        return AnswerDraftValidation(
            draft=None,
            rejection_count=len(canonical_draft.claims),
            safety_blocked=True,
        )

    evidence_by_id: dict[str, list[Evidence]] = {}
    for item in evidence:
        evidence_by_id.setdefault(item.evidence_id, []).append(item)

    accepted: list[DraftClaim] = []
    rejected = 0
    for claim in canonical_draft.claims:
        occurrences = [
            occurrence
            for evidence_id in claim.evidence_ids
            for occurrence in evidence_by_id.get(evidence_id, ())
        ]
        if not _causal_claim_supported(
            claim,
            canonical_plan,
            occurrences,
        ):
            rejected += 1
            continue
        tokens = _numeric_tokens(claim.text)
        if not tokens:
            accepted.append(claim.model_copy(deep=True))
            continue
        if (
            len({evidence_id for evidence_id in claim.evidence_ids})
            != len(claim.evidence_ids)
            or not occurrences
            or any(
                not tokens.issubset(_numeric_tokens(item.snippet))
                for item in occurrences
            )
        ):
            rejected += 1
            continue
        accepted.append(claim.model_copy(deep=True))

    if not accepted:
        return AnswerDraftValidation(
            draft=None,
            rejection_count=rejected,
            safety_blocked=False,
        )
    sections = {claim.section for claim in accepted}
    if (
        "positive_factors" in sections
        and "risk_factors" in sections
        and "uncertainty" not in sections
        and not _has_cross_section_duplicate(accepted)
    ):
        return AnswerDraftValidation(
            draft=None,
            rejection_count=len(canonical_draft.claims),
            safety_blocked=False,
        )
    return AnswerDraftValidation(
        draft=StructuredAnswerDraft(claims=tuple(accepted)),
        rejection_count=rejected,
        safety_blocked=False,
    )


def is_unsafe_answer_text(value: str, *, intent: str) -> bool:
    if not isinstance(value, str) or not isinstance(intent, str):
        raise AnswerValidationError(_INVALID_INPUT)
    normalized = _normalize_text(value)
    return bool(
        _DIRECT_ACTION.search(normalized)
        or _TARGET_PRICE.search(normalized)
        or _EXIT_TIMING.search(normalized)
        or _GUARANTEE.search(normalized)
        or _FUTURE_CERTAINTY.search(normalized)
        or _DIRECTION_PROBABILITY.search(normalized)
    )


def _numeric_tokens(value: str) -> frozenset[str]:
    normalized = unicodedata.normalize("NFKC", value)
    return frozenset(
        re.sub(r"\s+", "", match.group(0)).casefold()
        for match in _NUMERIC_TOKEN.finditer(normalized)
    )


def _normalize_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split()).casefold()


def _causal_claim_supported(
    claim: DraftClaim,
    plan: QueryPlan,
    occurrences: Sequence[Evidence],
) -> bool:
    if (
        plan.intent != "multi_source_summary"
        or claim.section not in {"interpretation", "inference"}
        or len(claim.evidence_ids) < 2
    ):
        return True
    target = _target_security_id(plan)
    if target is None or any(
        not _supports_target(item, target) for item in occurrences
    ):
        return False
    timestamps = []
    for item in occurrences:
        published_at = item.published_at
        if (
            published_at is None
            or published_at.tzinfo is None
            or published_at.utcoffset() is None
        ):
            return False
        timestamps.append(published_at.astimezone(UTC))
    return timestamps == sorted(timestamps)


def _target_security_id(plan: QueryPlan) -> str | None:
    if plan.security is None:
        return None
    return f"{plan.security.market}:{plan.security.ticker}"


def _supports_target(item: Evidence, target: str) -> bool:
    if item.scope == "company_specific":
        return item.subject_security_ids == [target]
    if item.scope == "multi_company":
        return target in item.subject_security_ids
    return (
        item.scope == "industry_common"
        and not item.subject_security_ids
        and target in item.mentioned_security_ids
    )


def _has_cross_section_duplicate(claims: Sequence[DraftClaim]) -> bool:
    sections_by_text: dict[str, set[str]] = {}
    for claim in claims:
        sections_by_text.setdefault(
            _normalize_text(claim.text),
            set(),
        ).add(claim.section)
    return any(len(sections) > 1 for sections in sections_by_text.values())


def _draft(value: object) -> StructuredAnswerDraft:
    if not isinstance(value, StructuredAnswerDraft):
        raise AnswerValidationError(_INVALID_INPUT)
    try:
        return StructuredAnswerDraft.model_validate(
            value.model_dump(mode="python"),
            strict=True,
        )
    except (AttributeError, TypeError, ValueError):
        raise AnswerValidationError(_INVALID_INPUT) from None


def _plan(value: object) -> QueryPlan:
    if not isinstance(value, QueryPlan):
        raise AnswerValidationError(_INVALID_INPUT)
    try:
        return QueryPlan.model_validate(
            value.model_dump(mode="python"),
            strict=True,
        )
    except (AttributeError, TypeError, ValueError):
        raise AnswerValidationError(_INVALID_INPUT) from None


def _evidence(value: object) -> tuple[Evidence, ...]:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes, bytearray))
    ):
        raise AnswerValidationError(_INVALID_INPUT)
    output: list[Evidence] = []
    for item in value:
        if not isinstance(item, Evidence):
            raise AnswerValidationError(_INVALID_INPUT)
        try:
            output.append(
                Evidence.model_validate(
                    item.model_dump(mode="python"),
                    strict=True,
                )
            )
        except (AttributeError, TypeError, ValueError):
            raise AnswerValidationError(_INVALID_INPUT) from None
    return tuple(output)


__all__ = [
    "AnswerDraftValidation",
    "AnswerValidationError",
    "is_unsafe_answer_text",
    "validate_answer_draft",
]
