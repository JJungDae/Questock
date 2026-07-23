from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, timedelta, timezone
import json
import math

import pytest

from app.core.models import (
    Evidence,
    ProviderResult,
    QueryPlan,
    RetrievalResult,
    SecurityIdentifier,
)
from app.core.status import ProviderStatus, RetrievalStatus
from app.evidence import budget as budget_module
from app.evidence.budget import (
    ContextBudgetLimits,
    ContextBudgetResult,
    ContextBudgetValidationError,
    LLMCallBudget,
    LLMCallBudgetExceededError,
    LLMCallBudgetSnapshot,
    select_evidence_context,
)
from app.evidence.citations import (
    CitationClaim,
    CitationRejection,
    validate_citations,
)
from app.evidence.freshness import FreshnessResult, FreshnessWindow
from app.evidence.policy import EvidencePolicy
from app.providers.base import create_provider_result

UTC = timezone.utc
BASIS_AT = datetime(2026, 7, 23, 3, 0, tzinfo=UTC)
BASIS_DATE = date(2026, 7, 23)
SAMSUNG = "KRX:005930"
SK_HYNIX = "KRX:000660"
SOURCES = ("news", "disclosure", "research_report", "glossary")


def evidence(
    index: int = 1,
    *,
    source_type: str = "news",
    evidence_id: str | None = None,
    document_id: str | None = None,
    title: str | None = None,
    snippet: str | None = None,
    score: float | None = 0.8,
    subjects: list[str] | None = None,
    mentions: list[str] | None = None,
    scope: str = "company_specific",
    locator: dict[str, object] | None = None,
) -> Evidence:
    actual_id = evidence_id or f"evidence:{source_type}:{index}"
    source_url = f"https://example.test/{source_type}/{index}"
    if scope == "company_specific":
        actual_subjects = [SAMSUNG] if subjects is None else subjects
        actual_mentions = [] if mentions is None else mentions
    elif scope == "industry_common":
        actual_subjects = [] if subjects is None else subjects
        actual_mentions = [SAMSUNG] if mentions is None else mentions
    else:
        actual_subjects = (
            [SAMSUNG, SK_HYNIX] if subjects is None else subjects
        )
        actual_mentions = [] if mentions is None else mentions
    return Evidence(
        evidence_id=actual_id,
        document_id=document_id or f"document:{source_type}:{index}",
        source_type=source_type,
        title=title or f"{source_type} supporting title {index}",
        source_url=source_url,
        published_at=BASIS_AT - timedelta(hours=index),
        subject_security_ids=actual_subjects,
        mentioned_security_ids=actual_mentions,
        scope=scope,
        snippet=snippet or f"{source_type} supporting evidence {index}",
        locator=locator
        or (
            {
                "provider": "recorded_news",
                "source_url": source_url,
                "nested": {"values": ["original"]},
            }
            if source_type == "news"
            else {
                "kind": "unit",
                "id": f"locator-{index}",
                "nested": {"values": ["original"]},
            }
        ),
        retrieval_score=score,
    )


def limits(
    *,
    count: int = 6,
    per_source: int = 3,
    tokens: int = 3000,
    chars: int = 4500,
) -> ContextBudgetLimits:
    return ContextBudgetLimits(
        max_evidence_count=count,
        max_evidence_per_source=per_source,
        max_context_tokens=tokens,
        max_context_chars=chars,
    )


def projection_json(items: tuple[Evidence, ...] | list[Evidence]) -> str:
    if not items:
        return ""
    payload = [
        {
            "evidence_id": item.evidence_id,
            "source_type": item.source_type,
            "title": item.title,
            "published_at": (
                item.published_at.isoformat()
                if item.published_at is not None
                else None
            ),
            "subject_security_ids": list(item.subject_security_ids),
            "mentioned_security_ids": list(item.mentioned_security_ids),
            "scope": item.scope,
            "snippet": item.snippet,
        }
        for item in items
    ]
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )


def projection_estimate(
    items: tuple[Evidence, ...] | list[Evidence],
) -> tuple[int, int]:
    serialized = projection_json(items)
    if not serialized:
        return 0, 0
    return math.ceil(len(serialized.encode("utf-8")) / 3), len(serialized)


def assert_sanitized(
    exc_info: pytest.ExceptionInfo[ContextBudgetValidationError],
) -> None:
    assert str(exc_info.value) in {
        "evidence context input is invalid",
        "context budget limits are invalid",
        "LLM call budget is invalid",
        "LLM call budget exceeded",
        "evidence occurrences are inconsistent",
        "context budget output is invalid",
    }
    assert "SECRET_SENTINEL" not in str(exc_info.value)
    assert "C:\\" not in str(exc_info.value)
    assert "/root" not in str(exc_info.value)
    assert "https://" not in str(exc_info.value)


def security() -> SecurityIdentifier:
    return SecurityIdentifier(
        market="KRX",
        ticker="005930",
        security_name="Samsung Electronics",
        security_type="common_stock",
        corp_code=None,
        corp_name="Samsung Electronics",
    )


def query_plan() -> QueryPlan:
    return QueryPlan(
        security=security(),
        intent="recent_issue",
        required_sources=["news"],
        required_evidence=["recent_news"],
        requires_clarification=False,
    )


def provider_result() -> ProviderResult[object]:
    return create_provider_result(
        status=ProviderStatus.OK,
        data={"items": []},
        fetched_at=BASIS_AT,
    )


def freshness_result(items: list[Evidence]) -> FreshnessResult:
    return FreshnessResult(
        basis_at=BASIS_AT,
        basis_date=BASIS_DATE,
        windows=(
            FreshnessWindow(
                "news",
                BASIS_DATE - timedelta(days=30),
                BASIS_DATE,
                "default",
            ),
        ),
        evidence=tuple(
            item.model_copy(deep=True, update={"retrieval_score": None})
            for item in items
        ),
        warnings=(),
        latest_effective_disclosure_at=None,
    )


def policy_decision(items: list[Evidence]):
    return EvidencePolicy().evaluate(
        query_plan(),
        {"news": provider_result()},
        freshness_result(items),
        RetrievalResult(
            evidence=[item.model_copy(deep=True) for item in items],
            status=RetrievalStatus.OK,
            strategy="lexical-bm25-m2-03-v1",
            low_relevance=False,
            diagnostics={},
        ),
    )


def test_public_api_and_literal_limits_are_fixed():
    assert budget_module.MAX_EVIDENCE_COUNT == 6
    assert budget_module.MAX_EVIDENCE_PER_SOURCE == 3
    assert budget_module.MAX_CONTEXT_TOKENS == 3000
    assert budget_module.MAX_CONTEXT_CHARS == 4500
    assert budget_module.MAX_LLM_CALLS == 2
    assert budget_module.TOKEN_ESTIMATOR_VERSION == "utf8-bytes-div-3-v1"
    assert budget_module.__all__ == [
        "ContextBudgetDiagnostics",
        "ContextBudgetLimits",
        "ContextBudgetResult",
        "ContextBudgetValidationError",
        "LLMCallBudget",
        "LLMCallBudgetExceededError",
        "LLMCallBudgetSnapshot",
        "MAX_CONTEXT_CHARS",
        "MAX_CONTEXT_TOKENS",
        "MAX_EVIDENCE_COUNT",
        "MAX_EVIDENCE_PER_SOURCE",
        "MAX_LLM_CALLS",
        "TOKEN_ESTIMATOR_VERSION",
        "select_evidence_context",
    ]
    assert not hasattr(ContextBudgetLimits(), "max_llm_calls")


def test_result_limit_and_snapshot_dataclasses_are_frozen():
    result = select_evidence_context([])
    with pytest.raises(FrozenInstanceError):
        result.diagnostics.__setattr__("input_count", 1)
    with pytest.raises(FrozenInstanceError):
        ContextBudgetLimits().__setattr__("max_evidence_count", 1)
    with pytest.raises(FrozenInstanceError):
        LLMCallBudget().snapshot().__setattr__("calls_used", 1)


@pytest.mark.parametrize(
    "bad_input",
    [
        None,
        "evidence",
        b"evidence",
        bytearray(b"evidence"),
        {"evidence": 1},
        {1, 2},
        iter(()),
        range(0),
    ],
)
def test_public_boundary_rejects_non_materialized_list_or_tuple(bad_input):
    with pytest.raises(ContextBudgetValidationError) as exc_info:
        select_evidence_context(bad_input)
    assert_sanitized(exc_info)


def test_public_boundary_rejects_custom_list():
    class CustomList(list):
        pass

    with pytest.raises(ContextBudgetValidationError) as exc_info:
        select_evidence_context(CustomList())
    assert_sanitized(exc_info)


def test_list_and_tuple_are_accepted_and_empty_is_deterministic():
    item = evidence()
    assert select_evidence_context([item]) == select_evidence_context((item,))
    assert select_evidence_context([]) == select_evidence_context(())
    empty = select_evidence_context([], reserved_tokens=7)
    assert empty.evidence == ()
    assert empty.diagnostics.input_count == 0
    assert empty.diagnostics.unique_count == 0
    assert empty.diagnostics.selected_count == 0
    assert empty.diagnostics.estimated_context_tokens == 7
    assert empty.diagnostics.estimated_evidence_chars == 0
    assert empty.diagnostics.budget_exhausted is False


@pytest.mark.parametrize("bad_item", [None, {}, object()])
def test_non_evidence_item_is_rejected(bad_item):
    with pytest.raises(ContextBudgetValidationError) as exc_info:
        select_evidence_context([bad_item])
    assert_sanitized(exc_info)


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("evidence_id", ""),
        ("document_id", " "),
        ("source_type", "market"),
        ("title", "\t"),
        ("snippet", "\n"),
    ],
)
def test_blank_required_values_and_unsupported_source_are_rejected(
    field_name,
    bad_value,
):
    malformed = evidence().model_copy(update={field_name: bad_value})
    with pytest.raises(ContextBudgetValidationError) as exc_info:
        select_evidence_context([malformed])
    assert_sanitized(exc_info)


@pytest.mark.parametrize(
    "bad_score",
    [None, True, float("nan"), float("inf"), float("-inf"), -1.0, 0.499999],
)
def test_invalid_retrieval_scores_are_rejected(bad_score):
    malformed = evidence().model_copy(update={"retrieval_score": bad_score})
    with pytest.raises(ContextBudgetValidationError) as exc_info:
        select_evidence_context([malformed])
    assert_sanitized(exc_info)


def test_direct_model_constructed_malformed_evidence_is_sanitized():
    malformed = Evidence.model_construct(
        **{
            **evidence().model_dump(),
            "evidence_id": "C:\\SECRET_SENTINEL",
            "locator": {"path": "/root/SECRET_SENTINEL"},
            "retrieval_score": "SECRET_SENTINEL",
        }
    )
    with pytest.raises(ContextBudgetValidationError) as exc_info:
        select_evidence_context([malformed])
    assert_sanitized(exc_info)


def test_unserializable_locator_is_a_typed_sanitized_input_error():
    malformed = Evidence.model_construct(
        **{
            **evidence().model_dump(),
            "locator": {"value": object()},
        }
    )
    with pytest.raises(ContextBudgetValidationError) as exc_info:
        select_evidence_context([malformed])
    assert_sanitized(exc_info)


@pytest.mark.parametrize("bad_limits", [None, {}, object()])
def test_limits_must_be_actual_context_budget_limits(bad_limits):
    with pytest.raises(ContextBudgetValidationError) as exc_info:
        select_evidence_context([], limits=bad_limits)
    assert_sanitized(exc_info)


def test_context_budget_limits_subclass_is_rejected():
    class CustomLimits(ContextBudgetLimits):
        pass

    with pytest.raises(ContextBudgetValidationError) as exc_info:
        select_evidence_context([], limits=CustomLimits())
    assert_sanitized(exc_info)


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("max_evidence_count", True),
        ("max_evidence_count", 0),
        ("max_evidence_count", 7),
        ("max_evidence_per_source", False),
        ("max_evidence_per_source", 0),
        ("max_evidence_per_source", 4),
        ("max_context_tokens", True),
        ("max_context_tokens", 0),
        ("max_context_tokens", 3001),
        ("max_context_chars", False),
        ("max_context_chars", 0),
        ("max_context_chars", 4501),
    ],
)
def test_every_context_limit_boundary_is_revalidated(field_name, bad_value):
    malformed = replace(ContextBudgetLimits(), **{field_name: bad_value})
    with pytest.raises(ContextBudgetValidationError) as exc_info:
        select_evidence_context([], limits=malformed)
    assert_sanitized(exc_info)


@pytest.mark.parametrize("bad_reserved", [True, -1, 3001, "1"])
def test_reserved_token_type_and_range_are_validated(bad_reserved):
    with pytest.raises(ContextBudgetValidationError) as exc_info:
        select_evidence_context([], reserved_tokens=bad_reserved)
    assert_sanitized(exc_info)


def test_reserved_token_limit_uses_effective_configured_maximum():
    with pytest.raises(ContextBudgetValidationError) as exc_info:
        select_evidence_context(
            [],
            limits=limits(tokens=5),
            reserved_tokens=6,
        )
    assert_sanitized(exc_info)


def test_identical_occurrence_with_same_id_keeps_first():
    first = evidence()
    duplicate = first.model_copy(deep=True)
    result = select_evidence_context([first, duplicate])
    assert result.evidence == (first,)
    assert result.evidence[0] is not first
    assert result.diagnostics.input_count == 2
    assert result.diagnostics.unique_count == 1
    assert result.diagnostics.duplicate_drop_count == 1


@pytest.mark.parametrize(
    "update",
    [
        {"snippet": "conflicting payload"},
        {"retrieval_score": 0.9},
        {"subject_security_ids": [SK_HYNIX]},
        {"locator": {"kind": "changed"}},
    ],
)
def test_same_id_with_conflicting_full_payload_fails_closed(update):
    first = evidence()
    conflicting = first.model_copy(deep=True, update=update)
    with pytest.raises(ContextBudgetValidationError) as exc_info:
        select_evidence_context([first, conflicting])
    assert str(exc_info.value) == "evidence occurrences are inconsistent"
    assert_sanitized(exc_info)


def test_exact_content_under_different_ids_keeps_first_id_and_score():
    first = evidence(score=0.7)
    duplicate = first.model_copy(
        deep=True,
        update={"evidence_id": "evidence:duplicate", "retrieval_score": 0.95},
    )
    result = select_evidence_context([first, duplicate])
    assert [item.evidence_id for item in result.evidence] == [first.evidence_id]
    assert result.evidence[0].retrieval_score == 0.7
    assert result.diagnostics.duplicate_drop_count == 1


def test_equivalent_locator_key_order_is_an_exact_duplicate():
    first = evidence(
        locator={"alpha": 1, "nested": {"one": 1, "two": 2}},
    )
    duplicate = first.model_copy(
        deep=True,
        update={
            "evidence_id": "evidence:duplicate",
            "locator": {"nested": {"two": 2, "one": 1}, "alpha": 1},
        },
    )
    assert len(select_evidence_context([first, duplicate]).evidence) == 1


def test_same_id_equivalent_locator_key_order_is_consistent():
    first = evidence(
        locator={"alpha": 1, "nested": {"one": 1, "two": 2}},
    )
    duplicate = first.model_copy(
        deep=True,
        update={"locator": {"nested": {"two": 2, "one": 1}, "alpha": 1}},
    )
    result = select_evidence_context([first, duplicate])
    assert result.evidence == (first,)


def test_same_document_with_different_snippets_remains_distinct():
    first = evidence(snippet="first exact passage")
    second = first.model_copy(
        deep=True,
        update={
            "evidence_id": "evidence:second",
            "snippet": "second exact passage",
        },
    )
    result = select_evidence_context([first, second])
    assert [item.evidence_id for item in result.evidence] == [
        first.evidence_id,
        second.evidence_id,
    ]


def test_attribution_and_scope_differences_never_deduplicate():
    first = evidence()
    different_subject = first.model_copy(
        deep=True,
        update={
            "evidence_id": "evidence:sk",
            "subject_security_ids": [SK_HYNIX],
        },
    )
    industry = first.model_copy(
        deep=True,
        update={
            "evidence_id": "evidence:industry",
            "subject_security_ids": [],
            "mentioned_security_ids": [SAMSUNG],
            "scope": "industry_common",
        },
    )
    result = select_evidence_context([first, different_subject, industry])
    assert [item.evidence_id for item in result.evidence] == [
        first.evidence_id,
        different_subject.evidence_id,
        industry.evidence_id,
    ]


def test_similar_title_url_and_event_are_not_semantically_deduplicated():
    first = evidence(title="Same event", snippet="First view")
    second = evidence(
        2,
        title="Same event",
        snippet="Second view",
    ).model_copy(update={"source_url": first.source_url})
    result = select_evidence_context([first, second])
    assert len(result.evidence) == 2


def test_duplicate_result_is_deterministic_across_repeated_calls():
    first = evidence()
    duplicate = first.model_copy(update={"evidence_id": "evidence:duplicate"})
    assert select_evidence_context([first, duplicate]) == select_evidence_context(
        [first, duplicate]
    )


def test_fourth_item_from_one_source_is_dropped():
    items = [evidence(index) for index in range(1, 5)]
    result = select_evidence_context(items)
    assert [item.evidence_id for item in result.evidence] == [
        item.evidence_id for item in items[:3]
    ]
    assert result.diagnostics.source_cap_drop_count == 1
    assert result.diagnostics.count_cap_drop_count == 0


def test_all_sources_are_capped_independently_before_total_count():
    items = [
        evidence(index, source_type=source)
        for source in SOURCES
        for index in range(1, 5)
    ]
    result = select_evidence_context(items)
    assert len(result.evidence) == 6
    assert result.diagnostics.input_count == 16
    assert result.diagnostics.unique_count == 16
    assert result.diagnostics.source_cap_drop_count == 4
    assert result.diagnostics.count_cap_drop_count == 6
    assert result.diagnostics.context_drop_count == 0


def test_mixed_sources_keep_input_order():
    items = [
        evidence(1, source_type="news"),
        evidence(1, source_type="disclosure"),
        evidence(2, source_type="news"),
        evidence(1, source_type="glossary"),
        evidence(3, source_type="news"),
        evidence(4, source_type="news"),
    ]
    result = select_evidence_context(items)
    assert [item.evidence_id for item in result.evidence] == [
        items[0].evidence_id,
        items[1].evidence_id,
        items[2].evidence_id,
        items[3].evidence_id,
        items[4].evidence_id,
    ]


def test_source_cap_precedes_count_cap_and_each_drop_has_one_stage():
    items = [
        evidence(1, source_type="news"),
        evidence(2, source_type="news"),
        evidence(1, source_type="disclosure"),
        evidence(2, source_type="disclosure"),
        evidence(1, source_type="glossary"),
    ]
    result = select_evidence_context(
        items,
        limits=limits(count=3, per_source=1),
    )
    assert [item.evidence_id for item in result.evidence] == [
        items[0].evidence_id,
        items[2].evidence_id,
        items[4].evidence_id,
    ]
    assert result.diagnostics.source_cap_drop_count == 2
    assert result.diagnostics.count_cap_drop_count == 0
    assert (
        result.diagnostics.input_count
        == result.diagnostics.duplicate_drop_count
        + result.diagnostics.source_cap_drop_count
        + result.diagnostics.count_cap_drop_count
        + result.diagnostics.context_drop_count
        + result.diagnostics.selected_count
    )


def test_final_count_cap_removes_lower_priority_tail():
    items = [
        evidence(1, source_type="news"),
        evidence(1, source_type="disclosure"),
        evidence(1, source_type="research_report"),
        evidence(1, source_type="glossary"),
    ]
    result = select_evidence_context(items, limits=limits(count=3))
    assert [item.evidence_id for item in result.evidence] == [
        item.evidence_id for item in items[:3]
    ]
    assert result.diagnostics.count_cap_drop_count == 1


def test_ascii_and_korean_projection_estimates_follow_literal_formula():
    ascii_item = evidence(snippet="ascii supporting passage")
    korean_item = evidence(
        2,
        snippet="삼성전자 실적 개선 근거",
    )
    expected_tokens, expected_chars = projection_estimate(
        [ascii_item, korean_item]
    )
    result = select_evidence_context([ascii_item, korean_item])
    assert result.diagnostics.estimated_context_tokens == expected_tokens
    assert result.diagnostics.estimated_evidence_chars == expected_chars


def test_projection_field_order_and_timestamp_are_literal():
    item = evidence()
    serialized = projection_json([item])
    assert serialized.startswith(
        '[{"evidence_id":"evidence:news:1","source_type":"news",'
        '"title":"news supporting title 1","published_at":'
        '"2026-07-23T02:00:00+00:00","subject_security_ids":'
    )
    assert '"mentioned_security_ids":[],"scope":"company_specific",' in serialized
    assert serialized.endswith('"snippet":"news supporting evidence 1"}]')


def item_at_exact_token_boundary() -> Evidence:
    base = evidence(snippet="x")
    base_bytes = len(projection_json([base]).encode("utf-8")) - 1
    remaining = 9000 - base_bytes
    korean_count, ascii_count = divmod(remaining, 3)
    item = evidence(snippet="가" * korean_count + "x" * ascii_count)
    assert len(projection_json([item]).encode("utf-8")) == 9000
    return item


def item_at_exact_char_boundary() -> Evidence:
    base = evidence(snippet="x")
    overhead = len(projection_json([base])) - 1
    item = evidence(snippet="x" * (4500 - overhead))
    assert len(projection_json([item])) == 4500
    return item


def test_exact_3000_token_boundary_is_included():
    item = item_at_exact_token_boundary()
    result = select_evidence_context([item])
    assert result.evidence == (item,)
    assert result.diagnostics.estimated_context_tokens == 3000
    assert result.diagnostics.estimated_evidence_chars < 4500


def test_one_token_over_3000_removes_the_item():
    item = item_at_exact_token_boundary()
    oversized = item.model_copy(update={"snippet": item.snippet + "x"})
    result = select_evidence_context([oversized])
    assert projection_estimate([oversized])[0] == 3001
    assert result.evidence == ()
    assert result.diagnostics.budget_exhausted is True


def test_exact_4500_character_boundary_is_included():
    item = item_at_exact_char_boundary()
    result = select_evidence_context([item])
    assert result.evidence == (item,)
    assert result.diagnostics.estimated_evidence_chars == 4500
    assert result.diagnostics.estimated_context_tokens <= 3000


def test_one_character_over_4500_removes_the_item():
    item = item_at_exact_char_boundary()
    oversized = item.model_copy(update={"snippet": item.snippet + "x"})
    result = select_evidence_context([oversized])
    assert projection_estimate([oversized])[1] == 4501
    assert result.evidence == ()
    assert result.diagnostics.budget_exhausted is True


def test_whichever_context_cap_is_stricter_controls_selection():
    ascii_item = evidence(snippet="x" * 1000)
    ascii_tokens, ascii_chars = projection_estimate([ascii_item])
    char_limited = select_evidence_context(
        [ascii_item],
        limits=limits(tokens=ascii_tokens, chars=ascii_chars - 1),
    )
    assert char_limited.evidence == ()

    korean_item = evidence(snippet="가" * 1000)
    korean_tokens, korean_chars = projection_estimate([korean_item])
    token_limited = select_evidence_context(
        [korean_item],
        limits=limits(tokens=korean_tokens - 1, chars=korean_chars),
    )
    assert token_limited.evidence == ()


def test_multiple_tail_drops_stop_as_soon_as_both_limits_fit():
    items = [
        evidence(1, source_type="news"),
        evidence(1, source_type="disclosure"),
        evidence(1, source_type="glossary"),
    ]
    one_token_count, one_chars = projection_estimate(items[:1])
    result = select_evidence_context(
        items,
        limits=limits(tokens=one_token_count, chars=one_chars),
    )
    assert result.evidence == (items[0],)
    assert result.diagnostics.context_drop_count == 2
    assert result.diagnostics.budget_exhausted is False


def test_reserved_tokens_reduce_only_token_capacity():
    items = [
        evidence(1, source_type="news"),
        evidence(1, source_type="disclosure"),
    ]
    both_tokens, both_chars = projection_estimate(items)
    first_tokens, _ = projection_estimate(items[:1])
    reservation = both_tokens - first_tokens
    result = select_evidence_context(
        items,
        limits=limits(tokens=both_tokens, chars=both_chars),
        reserved_tokens=reservation,
    )
    assert result.evidence == (items[0],)
    assert (
        result.diagnostics.estimated_context_tokens
        == reservation + first_tokens
    )


def test_one_oversized_item_returns_empty_budget_exhausted_without_truncation():
    item = evidence(snippet="unaltered supporting text")
    before = item.model_dump()
    result = select_evidence_context(
        [item],
        limits=limits(tokens=1),
    )
    assert result.evidence == ()
    assert result.diagnostics.context_drop_count == 1
    assert result.diagnostics.budget_exhausted is True
    assert item.model_dump() == before


def test_partial_context_drop_keeps_full_text_and_is_not_exhausted():
    items = [
        evidence(1, source_type="news", snippet="first full text"),
        evidence(1, source_type="disclosure", snippet="second full text"),
    ]
    first_tokens, first_chars = projection_estimate(items[:1])
    result = select_evidence_context(
        items,
        limits=limits(tokens=first_tokens, chars=first_chars),
    )
    assert result.evidence[0].title == items[0].title
    assert result.evidence[0].snippet == "first full text"
    assert result.diagnostics.context_drop_count == 1
    assert result.diagnostics.budget_exhausted is False


def test_all_diagnostic_equations_and_effective_limits_are_exact():
    first = evidence(1, source_type="news")
    duplicate = first.model_copy(update={"evidence_id": "evidence:duplicate"})
    items = [
        first,
        duplicate,
        evidence(2, source_type="news"),
        evidence(3, source_type="news"),
        evidence(4, source_type="news"),
        evidence(1, source_type="disclosure"),
        evidence(1, source_type="glossary"),
    ]
    result = select_evidence_context(
        items,
        limits=limits(count=3, per_source=2),
    )
    diagnostics = result.diagnostics
    assert diagnostics.input_count == 7
    assert diagnostics.unique_count == 6
    assert diagnostics.duplicate_drop_count == 1
    assert diagnostics.source_cap_drop_count == 2
    assert diagnostics.count_cap_drop_count == 1
    assert diagnostics.context_drop_count == 0
    assert diagnostics.selected_count == 3
    assert diagnostics.input_count == 1 + 2 + 1 + 0 + 3
    assert diagnostics.max_evidence_count == 3
    assert diagnostics.max_evidence_per_source == 2
    assert diagnostics.max_context_tokens == 3000
    assert diagnostics.max_context_chars == 4500
    assert diagnostics.estimator_version == "utf8-bytes-div-3-v1"


def test_diagnostics_are_count_only_and_do_not_expose_evidence_content():
    sentinel = "SECRET_SENTINEL"
    item = evidence(title=sentinel, snippet=sentinel)
    diagnostics = select_evidence_context([item]).diagnostics
    assert sentinel not in repr(diagnostics)
    assert item.evidence_id not in repr(diagnostics)
    assert item.source_url not in repr(diagnostics)
    assert "locator" not in repr(diagnostics)


def test_caller_and_nested_locator_are_deep_copy_isolated():
    item = evidence()
    before = item.model_dump()
    first = select_evidence_context([item])
    second = select_evidence_context([item])
    first.evidence[0].locator["nested"]["values"].append("changed")
    assert item.model_dump() == before
    assert second.evidence[0].locator["nested"]["values"] == ["original"]


def test_equal_calls_return_equal_fresh_values():
    item = evidence()
    first = select_evidence_context([item])
    second = select_evidence_context([item])
    assert first == second
    assert first is not second
    assert first.evidence[0] is not second.evidence[0]
    assert first.diagnostics is not second.diagnostics


def test_final_audit_rejects_monkeypatched_diagnostic_count(monkeypatch):
    original = budget_module._build_result

    def bad_builder(*args, **kwargs):
        result = original(*args, **kwargs)
        return replace(
            result,
            diagnostics=replace(
                result.diagnostics,
                selected_count=result.diagnostics.selected_count + 1,
            ),
        )

    monkeypatch.setattr(budget_module, "_build_result", bad_builder)
    with pytest.raises(ContextBudgetValidationError) as exc_info:
        select_evidence_context([evidence()])
    assert str(exc_info.value) == "context budget output is invalid"


def test_final_audit_rejects_monkeypatched_estimate(monkeypatch):
    original = budget_module._build_result

    def bad_builder(*args, **kwargs):
        result = original(*args, **kwargs)
        return replace(
            result,
            diagnostics=replace(
                result.diagnostics,
                estimated_context_tokens=(
                    result.diagnostics.estimated_context_tokens + 1
                ),
            ),
        )

    monkeypatch.setattr(budget_module, "_build_result", bad_builder)
    with pytest.raises(ContextBudgetValidationError) as exc_info:
        select_evidence_context([evidence()])
    assert str(exc_info.value) == "context budget output is invalid"


def test_final_audit_rejects_monkeypatched_order(monkeypatch):
    original = budget_module._build_result

    def bad_builder(*args, **kwargs):
        result = original(*args, **kwargs)
        return replace(result, evidence=tuple(reversed(result.evidence)))

    monkeypatch.setattr(budget_module, "_build_result", bad_builder)
    with pytest.raises(ContextBudgetValidationError) as exc_info:
        select_evidence_context(
            [
                evidence(1, source_type="news"),
                evidence(1, source_type="disclosure"),
            ]
        )
    assert str(exc_info.value) == "context budget output is invalid"


def test_final_audit_rejects_monkeypatched_malformed_evidence(monkeypatch):
    original = budget_module._build_result

    def bad_builder(*args, **kwargs):
        result = original(*args, **kwargs)
        malformed = result.evidence[0].model_copy(update={"title": ""})
        return replace(result, evidence=(malformed,))

    monkeypatch.setattr(budget_module, "_build_result", bad_builder)
    with pytest.raises(ContextBudgetValidationError) as exc_info:
        select_evidence_context([evidence()])
    assert str(exc_info.value) == "context budget output is invalid"


def test_default_llm_budget_allows_two_calls_then_fails_closed():
    budget = LLMCallBudget()
    assert budget.reserve_call() == 1
    assert budget.reserve_call() == 2
    with pytest.raises(LLMCallBudgetExceededError) as exc_info:
        budget.reserve_call()
    assert str(exc_info.value) == "LLM call budget exceeded"
    assert budget.snapshot() == LLMCallBudgetSnapshot(2, 0, 2)


def test_explicit_one_call_budget_and_fresh_snapshots():
    budget = LLMCallBudget(1)
    before = budget.snapshot()
    assert budget.reserve_call() == 1
    after = budget.snapshot()
    assert before == LLMCallBudgetSnapshot(0, 1, 1)
    assert after == LLMCallBudgetSnapshot(1, 0, 1)
    assert before is not budget.snapshot()
    with pytest.raises(LLMCallBudgetExceededError):
        budget.reserve_call()
    assert budget.snapshot() == after


@pytest.mark.parametrize("bad_max", [True, False, 0, -1, 3, 1.0, "2"])
def test_llm_call_limit_rejects_invalid_values(bad_max):
    with pytest.raises(ContextBudgetValidationError) as exc_info:
        LLMCallBudget(bad_max)
    assert str(exc_info.value) == "LLM call budget is invalid"
    assert_sanitized(exc_info)


def test_independent_llm_call_budgets_share_no_state():
    first = LLMCallBudget()
    second = LLMCallBudget()
    first.reserve_call()
    assert first.snapshot() == LLMCallBudgetSnapshot(1, 1, 2)
    assert second.snapshot() == LLMCallBudgetSnapshot(0, 2, 2)


def test_llm_budget_stores_and_exposes_counts_only():
    sentinel = "SECRET_SENTINEL"
    budget = LLMCallBudget()
    snapshot = budget.snapshot()
    assert set(budget.__dict__) == {"_max_calls", "_calls_used"}
    assert sentinel not in repr(budget.__dict__)
    assert sentinel not in repr(snapshot)


def test_real_policy_output_composes_with_budget_and_citation():
    item = evidence(snippet="Samsung earnings improved in the latest quarter.")
    decision = policy_decision([item])
    decision_before = decision
    budget_result = select_evidence_context(decision.evidence)
    claims = [
        CitationClaim(
            "claim-1",
            "Samsung earnings improved",
            (budget_result.evidence[0].evidence_id,),
        )
    ]
    citations = validate_citations(claims, query_plan(), budget_result.evidence)
    assert citations.rejections == ()
    assert citations.citations[0].evidence_id == item.evidence_id
    assert decision == decision_before
    assert decision.evidence[0].retrieval_score == item.retrieval_score


def test_removed_exact_duplicate_is_unknown_at_citation_boundary():
    first = evidence(snippet="Samsung earnings improved.")
    duplicate = first.model_copy(
        deep=True,
        update={"evidence_id": "evidence:removed"},
    )
    decision = policy_decision([first, duplicate])
    budget_result = select_evidence_context(decision.evidence)
    claims = [
        CitationClaim(
            "claim-removed",
            "Samsung earnings improved",
            (duplicate.evidence_id,),
        )
    ]
    citations = validate_citations(claims, query_plan(), budget_result.evidence)
    assert citations.citations == ()
    assert citations.rejections == (
        CitationRejection("claim-removed", "unknown_evidence"),
    )


def test_removed_source_cap_item_is_unknown_at_citation_boundary():
    items = [
        evidence(index, snippet=f"Samsung evidence passage {index}.")
        for index in range(1, 5)
    ]
    decision = policy_decision(items)
    before = decision
    budget_result = select_evidence_context(decision.evidence)
    removed = items[3]
    claims = [
        CitationClaim(
            "claim-removed",
            "Samsung evidence passage 4",
            (removed.evidence_id,),
        )
    ]
    citations = validate_citations(claims, query_plan(), budget_result.evidence)
    assert citations.rejections == (
        CitationRejection("claim-removed", "unknown_evidence"),
    )
    assert decision == before
    assert [item.evidence_id for item in budget_result.evidence] == [
        item.evidence_id for item in items[:3]
    ]


@pytest.mark.parametrize("drop_kind", ["count", "context"])
def test_removed_count_or_context_item_is_unknown_at_citation_boundary(
    drop_kind,
):
    items = [
        evidence(1, source_type="news", snippet="Samsung first passage."),
        evidence(
            1,
            source_type="disclosure",
            snippet="Samsung second passage.",
        ),
    ]
    if drop_kind == "count":
        selected = select_evidence_context(items, limits=limits(count=1))
    else:
        first_tokens, first_chars = projection_estimate(items[:1])
        selected = select_evidence_context(
            items,
            limits=limits(tokens=first_tokens, chars=first_chars),
        )
    removed = items[1]
    claims = [
        CitationClaim(
            "claim-removed",
            "Samsung second passage",
            (removed.evidence_id,),
        )
    ]
    citations = validate_citations(
        claims,
        QueryPlan(
            security=security(),
            intent="multi_source_summary",
            required_sources=["news", "disclosure", "research_report"],
            required_evidence=[
                "recent_news",
                "disclosure",
                "research_report",
            ],
        ),
        selected.evidence,
    )
    assert citations.rejections == (
        CitationRejection("claim-removed", "unknown_evidence"),
    )
