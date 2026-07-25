from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime

import pytest

from app.answer.models import DraftClaim, StructuredAnswerDraft
from app.answer.validators import (
    AnswerValidationError,
    is_unsafe_answer_text,
    validate_answer_draft,
)
from app.core.models import Evidence, QueryPlan, SecurityIdentifier

SECURITY_ID = "KRX:005930"
BASIS_AT = datetime(2026, 7, 25, tzinfo=UTC)


def _plan() -> QueryPlan:
    return QueryPlan(
        security=SecurityIdentifier(
            market="KRX",
            ticker="005930",
            security_name="삼성전자",
            security_type="common_stock",
            corp_code="00126380",
            corp_name="삼성전자",
        ),
        intent="recent_issue",
        required_sources=["news"],
        required_evidence=["recent_news"],
        requires_clarification=False,
    )


def _evidence(
    *,
    evidence_id: str = "evidence:news:1",
    snippet: str,
    source_type: str = "news",
    published_at: datetime | None = BASIS_AT,
    subject_security_ids: list[str] | None = None,
    mentioned_security_ids: list[str] | None = None,
    scope: str = "company_specific",
) -> Evidence:
    return Evidence(
        evidence_id=evidence_id,
        document_id=f"document:{evidence_id}",
        source_type=source_type,
        title="검증 기사",
        source_url="https://news.example.test/article",
        published_at=published_at,
        subject_security_ids=(
            [SECURITY_ID]
            if subject_security_ids is None
            else subject_security_ids
        ),
        mentioned_security_ids=mentioned_security_ids or [],
        scope=scope,
        snippet=snippet,
        locator={"provider": "recorded_news"},
        retrieval_score=0.8,
    )


def _draft(
    *claims: tuple[str, str, str, tuple[str, ...]],
) -> StructuredAnswerDraft:
    return StructuredAnswerDraft(
        claims=tuple(
            DraftClaim(
                claim_id=claim_id,
                section=section,
                text=text,
                evidence_ids=evidence_ids,
            )
            for claim_id, section, text, evidence_ids in claims
        )
    )


@pytest.mark.parametrize(
    "text",
    [
        "지금 삼성전자를 매수하세요.",
        "현재 가격에서는 파세요.",
        "이 종목은 계속 보유해야 합니다.",
        "목표가는 10만원으로 제시합니다.",
        "8만원에서 손절하세요.",
        "다음 주에 익절하는 것을 권장합니다.",
        "수익이 보장됩니다.",
        "주가는 반드시 상승할 것입니다.",
        "향후 상승 확률은 80%입니다.",
        "긍정 기사가 더 많으므로 상승이 우세하다.",
        "긍정 감성 점수는 80점이다.",
        "종합하면 매수 의견이다.",
        "투자 책임은 본인에게 있지만 지금 매수하세요.",
    ],
)
def test_unsafe_action_and_prediction_are_blocked(text: str) -> None:
    assert is_unsafe_answer_text(text, intent="recent_issue") is True


@pytest.mark.parametrize(
    "text",
    [
        "외국인은 최근 3거래일 동안 순매수했다.",
        "회사는 자사주 10만 주를 취득했다고 공시했다.",
        "해당 보고서는 투자 의견을 매수로 유지했다.",
        "회사는 현금성 자산 2조원을 보유하고 있다.",
        "손절 관련 리포트의 위험 요인을 요약했다.",
        "익절 전략을 다룬 리포트가 발간됐다.",
    ],
)
def test_neutral_reported_fact_is_allowed(text: str) -> None:
    assert is_unsafe_answer_text(text, intent="recent_issue") is False


@pytest.mark.parametrize(
    ("claim_text", "snippet", "accepted"),
    [
        ("매출은 10억원이다.", "매출은 10억원이다.", True),
        ("영업이익률은 12.5%다.", "영업이익률은 12.5%다.", True),
        ("거래대금은 1,234억원이다.", "거래대금은 1,234억원이다.", True),
        ("증감률은 -3.2%다.", "증감률은 -3.2%다.", True),
        ("매출은 10억원이다.", "매출은 100억원이다.", False),
        ("상승 폭은 3%다.", "상승 폭은 3%p다.", False),
        ("개선 폭은 3%p다.", "개선 폭은 3%다.", False),
        ("현금은 KRW 2조원이다.", "현금은 KRW 2조원이다.", True),
        ("가격은 80,000원이다.", "가격은 80,000원이다.", True),
        ("기준일은 2026-07-25다.", "기준일은 2026-07-25다.", True),
        ("기간은 2026년 2분기다.", "기간은 2026년 2분기다.", True),
        ("기간은 2026년 7월이다.", "기간은 2026년 8월이다.", False),
        ("기간은 3개월이다.", "기간은 6개월이다.", False),
    ],
)
def test_numeric_date_and_unit_tokens_require_exact_evidence_match(
    claim_text: str,
    snippet: str,
    accepted: bool,
) -> None:
    draft = _draft(
        ("summary", "summary", claim_text, ("evidence:news:1",)),
    )

    result = validate_answer_draft(
        draft,
        _plan(),
        [_evidence(snippet=snippet)],
    )

    assert (result.draft is not None) is accepted
    assert result.rejection_count == (0 if accepted else 1)


def test_invalid_numeric_claim_is_removed_while_valid_claim_remains() -> None:
    draft = _draft(
        (
            "summary",
            "summary",
            "회사는 신규 설비 계획을 발표했다.",
            ("evidence:news:1",),
        ),
        (
            "fact",
            "facts",
            "투자 규모는 20조원이다.",
            ("evidence:news:1",),
        ),
    )

    result = validate_answer_draft(
        draft,
        _plan(),
        [_evidence(snippet="회사는 신규 설비 계획을 발표했다. 투자 규모는 2조원이다.")],
    )

    assert result.rejection_count == 1
    assert result.draft is not None
    assert [claim.claim_id for claim in result.draft.claims] == ["summary"]


def test_every_occurrence_of_referenced_evidence_must_support_numeric_token() -> None:
    draft = _draft(
        (
            "summary",
            "summary",
            "매출은 10억원이다.",
            ("evidence:duplicate",),
        ),
    )
    evidence = [
        _evidence(evidence_id="evidence:duplicate", snippet="매출은 10억원이다."),
        _evidence(evidence_id="evidence:duplicate", snippet="매출은 11억원이다."),
    ]

    result = validate_answer_draft(draft, _plan(), evidence)

    assert result.draft is None
    assert result.rejection_count == 1


def test_safety_failure_rejects_whole_draft() -> None:
    draft = _draft(
        (
            "summary",
            "summary",
            "회사는 신규 설비 계획을 발표했다.",
            ("evidence:news:1",),
        ),
        (
            "advice",
            "facts",
            "지금 매수하세요.",
            ("evidence:news:1",),
        ),
    )

    result = validate_answer_draft(
        draft,
        _plan(),
        [_evidence(snippet="회사는 신규 설비 계획을 발표했다.")],
    )

    assert result.draft is None
    assert result.safety_blocked is True
    assert result.rejection_count == 2


def test_validator_is_deterministic_and_does_not_mutate_callers() -> None:
    draft = _draft(
        (
            "summary",
            "summary",
            "매출은 10억원이다.",
            ("evidence:news:1",),
        ),
    )
    plan = _plan()
    evidence = [_evidence(snippet="매출은 10억원이다.")]
    before = (
        deepcopy(draft.model_dump(mode="python")),
        deepcopy(plan.model_dump(mode="python")),
        deepcopy([item.model_dump(mode="python") for item in evidence]),
    )

    first = validate_answer_draft(draft, plan, evidence)
    second = validate_answer_draft(draft, plan, evidence)

    assert first == second
    assert before == (
        draft.model_dump(mode="python"),
        plan.model_dump(mode="python"),
        [item.model_dump(mode="python") for item in evidence],
    )
    assert first.draft is not draft
    assert first.draft is not None
    assert first.draft.claims[0] is not draft.claims[0]


@pytest.mark.parametrize(
    ("draft", "plan", "evidence"),
    [
        (object(), _plan(), []),
        (_draft(("c", "summary", "문장", ("e",))), object(), []),
        (_draft(("c", "summary", "문장", ("e",))), _plan(), "bad"),
        (_draft(("c", "summary", "문장", ("e",))), _plan(), [object()]),
    ],
)
def test_malformed_inputs_raise_sanitized_typed_error(
    draft: object,
    plan: object,
    evidence: object,
) -> None:
    with pytest.raises(AnswerValidationError) as exc_info:
        validate_answer_draft(draft, plan, evidence)  # type: ignore[arg-type]

    assert str(exc_info.value) == "answer validation input is invalid"


def test_invalid_safety_input_raises_sanitized_typed_error() -> None:
    with pytest.raises(AnswerValidationError) as exc_info:
        is_unsafe_answer_text(object(), intent="recent_issue")  # type: ignore[arg-type]

    assert str(exc_info.value) == "answer validation input is invalid"


def test_two_sided_draft_requires_uncertainty_section() -> None:
    evidence = _evidence(
        snippet="수요 증가는 긍정 요인이다. 원가 상승은 위험 요인이다.",
    )
    draft = _draft(
        (
            "summary",
            "summary",
            "수요와 원가 변수가 함께 확인됐다.",
            (evidence.evidence_id,),
        ),
        (
            "positive",
            "positive_factors",
            "수요 증가는 긍정 요인이다.",
            (evidence.evidence_id,),
        ),
        (
            "risk",
            "risk_factors",
            "원가 상승은 위험 요인이다.",
            (evidence.evidence_id,),
        ),
    )

    result = validate_answer_draft(draft, _plan(), [evidence])

    assert result.draft is None
    assert result.rejection_count == 3


def test_two_sided_draft_with_uncertainty_is_accepted() -> None:
    snippets = (
        "수요와 원가 변수가 함께 확인됐다.",
        "수요 증가는 긍정 요인이다.",
        "원가 상승은 위험 요인이다.",
        "실제 영향은 추가 확인이 필요하다.",
    )
    evidence = _evidence(snippet=" ".join(snippets))
    draft = _draft(
        *(
            (
                f"claim-{index}",
                section,
                text,
                (evidence.evidence_id,),
            )
            for index, (section, text) in enumerate(
                zip(
                    (
                        "summary",
                        "positive_factors",
                        "risk_factors",
                        "uncertainty",
                    ),
                    snippets,
                    strict=True,
                ),
                start=1,
            )
        )
    )

    result = validate_answer_draft(draft, _plan(), [evidence])

    assert result.draft is not None
    assert result.rejection_count == 0


@pytest.mark.parametrize(
    "text",
    [
        "긍정 기사가 더 많으므로 상승이 우세하다.",
        "긍정 감성 점수는 80점이다.",
        "종합하면 매수 의견이다.",
    ],
)
def test_unsupported_conflict_conclusion_rejects_draft(text: str) -> None:
    evidence = _evidence(snippet=text)
    draft = _draft(
        ("summary", "summary", text, (evidence.evidence_id,)),
    )

    result = validate_answer_draft(draft, _plan(), [evidence])

    assert result.draft is None
    assert result.safety_blocked is True
    assert result.rejection_count == 1


@pytest.mark.parametrize(
    ("first_at", "second_at", "second_subjects", "accepted"),
    [
        (
            datetime(2026, 7, 20, tzinfo=UTC),
            datetime(2026, 7, 21, tzinfo=UTC),
            [SECURITY_ID],
            True,
        ),
        (
            datetime(2026, 7, 22, tzinfo=UTC),
            datetime(2026, 7, 21, tzinfo=UTC),
            [SECURITY_ID],
            False,
        ),
        (
            datetime(2026, 7, 20, tzinfo=UTC),
            None,
            [SECURITY_ID],
            False,
        ),
        (
            datetime(2026, 7, 20, tzinfo=UTC),
            datetime(2026, 7, 21, tzinfo=UTC),
            ["KRX:000660"],
            False,
        ),
    ],
)
def test_multi_source_causal_claim_requires_chronology_and_company_continuity(
    first_at: datetime,
    second_at: datetime | None,
    second_subjects: list[str],
    accepted: bool,
) -> None:
    text = "공시 이후 공급 계획이 구체화된 것으로 해석된다."
    evidence = [
        _evidence(
            evidence_id="evidence:disclosure:1",
            source_type="disclosure",
            published_at=first_at,
            snippet=text,
        ),
        _evidence(
            evidence_id="evidence:news:2",
            published_at=second_at,
            snippet=text,
            subject_security_ids=second_subjects,
        ),
    ]
    plan = _plan().model_copy(
        update={
            "intent": "multi_source_summary",
            "required_sources": ["disclosure", "news"],
        },
        deep=True,
    )
    draft = _draft(
        (
            "causal",
            "interpretation",
            text,
            ("evidence:disclosure:1", "evidence:news:2"),
        ),
    )

    result = validate_answer_draft(draft, plan, evidence)

    assert (result.draft is not None) is accepted
    assert result.rejection_count == (0 if accepted else 1)


def test_source_specific_noncausal_claims_do_not_require_cross_source_dates() -> None:
    first = _evidence(
        evidence_id="evidence:disclosure:1",
        source_type="disclosure",
        published_at=None,
        snippet="공시는 투자 계획을 설명했다.",
    )
    second = _evidence(
        evidence_id="evidence:news:2",
        published_at=None,
        snippet="뉴스는 공급망 위험을 설명했다.",
    )
    plan = _plan().model_copy(
        update={
            "intent": "multi_source_summary",
            "required_sources": ["disclosure", "news"],
        },
        deep=True,
    )
    draft = _draft(
        (
            "summary",
            "summary",
            first.snippet,
            (first.evidence_id,),
        ),
        (
            "risk",
            "risk_factors",
            second.snippet,
            (second.evidence_id,),
        ),
    )

    result = validate_answer_draft(draft, plan, [first, second])

    assert result.draft is not None
    assert result.rejection_count == 0
