from __future__ import annotations

from datetime import date

import pytest

from app.core.models import DateRange, QueryPlan, SessionContext
from app.core.resolver import SecurityResolver, security_id_for
from app.planning.query_planner import (
    DISCLOSURE_SUMMARY,
    FINANCIAL_TERM,
    MULTI_SOURCE_SUMMARY,
    OUT_OF_SCOPE,
    PROHIBITED_ADVICE,
    QueryPlanner,
    RECENT_ISSUE,
    RESEARCH_REPORT_SUMMARY,
    RISK_FACTORS,
)

SAMSUNG_ID = "KRX:005930"
SK_HYNIX_ID = "KRX:000660"
HYUNDAI_ID = "KRX:005380"
SAMSUNG = "\uc0bc\uc131\uc804\uc790"
SK_HYNIX = "SK\ud558\uc774\ub2c9\uc2a4"
HYUNDAI = "\ud604\ub300\uc790\ub3d9\ucc28"
SAMSUNG_ALIAS = "\uc0bc\uc804"
TODAY = "\uc624\ub298"
RECENT_NEWS = "\ucd5c\uadfc \ub274\uc2a4"
RECENT_ISSUE_TEXT = "\ucd5c\uadfc \uc774\uc288"
DISCLOSURE = "\uacf5\uc2dc"
REPORT = "\ub9ac\ud3ec\ud2b8"
RISK = "\uc704\ud5d8 \uc694\uc778"
SUMMARY = "\uc885\ud569"
WHAT_IS = "\ubb50\uc57c"


class SpyResolver:
    def __init__(self):
        self.delegate = SecurityResolver()
        self.calls: list[str] = []

    def resolve(self, query: str):
        self.calls.append(query)
        return self.delegate.resolve(query)


class FailingResolver:
    def resolve(self, query: str):
        raise RuntimeError("sentinel-secret raw resolver failure")


def planner(resolver=None, basis_date: date = date(2026, 7, 23)) -> QueryPlanner:
    return QueryPlanner(resolver=resolver or SecurityResolver(), basis_date=basis_date)


def assert_clarification(plan: QueryPlan, intent: str, date_range: DateRange | None = None) -> None:
    assert plan.security is None
    assert plan.intent == intent
    assert plan.date_range == date_range
    assert plan.required_sources == []
    assert plan.required_evidence == []
    assert plan.requires_clarification is True


def assert_success(
    plan: QueryPlan,
    *,
    security_id: str | None,
    intent: str,
    sources: list[str],
    evidence: list[str],
    date_range: DateRange | None = None,
) -> None:
    assert (security_id_for(plan.security) if plan.security else None) == security_id
    assert plan.intent == intent
    assert plan.date_range == date_range
    assert plan.required_sources == sources
    assert plan.required_evidence == evidence
    assert plan.requires_clarification is False


def test_default_resolver_is_constructed_once_and_none_resolver_is_allowed(monkeypatch):
    created: list[SpyResolver] = []

    def resolver_factory():
        resolver = SpyResolver()
        created.append(resolver)
        return resolver

    monkeypatch.setattr("app.planning.query_planner.SecurityResolver", resolver_factory)
    default_planner = QueryPlanner(basis_date=date(2026, 7, 23))
    explicit_none_planner = QueryPlanner(resolver=None, basis_date=date(2026, 7, 23))

    assert len(created) == 2
    default_planner.plan(f"{SAMSUNG} {DISCLOSURE}")
    default_planner.plan(f"{SK_HYNIX} {DISCLOSURE}")
    explicit_none_planner.plan(f"{SAMSUNG} {DISCLOSURE}")

    assert len(created) == 2
    assert len(created[0].calls) > 0
    assert len(created[1].calls) > 0


def test_type_errors_are_sanitized_and_do_not_call_resolver():
    resolver = SpyResolver()
    query_planner = planner(resolver=resolver)

    with pytest.raises(TypeError, match="query must be a string"):
        query_planner.plan(123)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="session must be a SessionContext or None"):
        query_planner.plan(f"{SAMSUNG} {DISCLOSURE}", session="bad")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="basis_date must be a date or None"):
        QueryPlanner(resolver=resolver, basis_date="2026-07-23")  # type: ignore[arg-type]

    assert resolver.calls == []


@pytest.mark.parametrize(
    ("query", "intent"),
    [
        ("   ", OUT_OF_SCOPE),
        (f"{SAMSUNG} \ub0b4\uc77c \uc624\ub97c\uae4c", PROHIBITED_ADVICE),
        (f"{SAMSUNG} {TODAY} \uc65c \uc62c\ub790\uc5b4", OUT_OF_SCOPE),
        (f"{SAMSUNG} \uc54c\ub824\uc918", OUT_OF_SCOPE),
    ],
)
def test_early_return_paths_do_not_call_resolver(query, intent):
    resolver = SpyResolver()
    result = planner(resolver=resolver).plan(query)

    assert_clarification(result, intent)
    assert resolver.calls == []


@pytest.mark.parametrize(
    ("query", "security_id"),
    [
        (f"{SAMSUNG}\ub294 {RECENT_ISSUE_TEXT}", SAMSUNG_ID),
        (f"005930 {RECENT_NEWS}", SAMSUNG_ID),
        (f"{SAMSUNG_ID} {RECENT_NEWS}", SAMSUNG_ID),
        (f"{SAMSUNG_ALIAS} {RECENT_NEWS}", SAMSUNG_ID),
        (f"Samsung Electronics stock {RECENT_NEWS}", SAMSUNG_ID),
        (f"{SAMSUNG} stock {RECENT_NEWS}", SAMSUNG_ID),
        (f"{SAMSUNG} aapl {RECENT_NEWS}", SAMSUNG_ID),
        (f"SK hynix {RECENT_NEWS}", SK_HYNIX_ID),
        (f"{SK_HYNIX} {RECENT_NEWS}", SK_HYNIX_ID),
        (f"SK  \ud558\uc774\ub2c9\uc2a4 {RECENT_NEWS}", SK_HYNIX_ID),
    ],
)
def test_security_mentions_resolve_inside_full_questions(query, security_id):
    result = planner().plan(query)

    assert_success(
        result,
        security_id=security_id,
        intent=RECENT_ISSUE,
        sources=["news"],
        evidence=["recent_news"],
    )


def test_ordinary_lowercase_english_words_do_not_become_foreign_tickers():
    result = planner().plan(f"{SAMSUNG} news risk")

    assert_clarification(result, OUT_OF_SCOPE)


@pytest.mark.parametrize(
    "query",
    [
        "Samsung Electronics stock news",
        "SK hynix recent news",
        f"{SAMSUNG} brief report",
    ],
)
def test_english_only_intent_routing_is_not_implemented(query):
    result = planner().plan(query)

    assert_clarification(result, OUT_OF_SCOPE)


@pytest.mark.parametrize("query", [f"\uc0bc\uc131 {RECENT_NEWS}", f"SK {RECENT_NEWS}", f"\ud604\ub300 {RECENT_NEWS}"])
def test_ambiguous_security_requires_clarification(query):
    result = planner().plan(query)

    assert_clarification(result, RECENT_ISSUE)


@pytest.mark.parametrize("query", [f"005935 {RECENT_NEWS}", f"{SAMSUNG} AAPL {RECENT_NEWS}"])
def test_unsupported_or_conflicting_security_requires_clarification(query):
    result = planner().plan(query)

    assert_clarification(result, RECENT_ISSUE)


@pytest.mark.parametrize(
    "query",
    [
        f"{SAMSUNG} {SK_HYNIX} {RECENT_NEWS}",
        f"{SAMSUNG}\uacfc {SK_HYNIX} \ube44\uad50",
        f"{SAMSUNG} vs {SK_HYNIX}",
    ],
)
def test_multiple_supported_securities_do_not_first_match(query):
    result = planner().plan(query)

    assert_clarification(result, OUT_OF_SCOPE)


def test_session_security_fallback_and_explicit_security_precedence():
    session = SessionContext(current_security_id=SK_HYNIX_ID)
    query_planner = planner()

    fallback = query_planner.plan(RECENT_NEWS, session=session)
    explicit = query_planner.plan(f"{SAMSUNG} {RECENT_NEWS}", session=session)
    ambiguous = query_planner.plan(f"\uc0bc\uc131 {RECENT_NEWS}", session=session)

    assert_success(fallback, security_id=SK_HYNIX_ID, intent=RECENT_ISSUE, sources=["news"], evidence=["recent_news"])
    assert_success(explicit, security_id=SAMSUNG_ID, intent=RECENT_ISSUE, sources=["news"], evidence=["recent_news"])
    assert_clarification(ambiguous, RECENT_ISSUE)


def test_financial_term_does_not_inherit_session_security_but_preserves_explicit_security():
    session = SessionContext(current_security_id=SK_HYNIX_ID, current_date_range=DateRange(start=date(2026, 7, 1), end=date(2026, 7, 2)))
    query_planner = planner()

    no_security = query_planner.plan(f"PER\uc774 {WHAT_IS}", session=session)
    explicit = query_planner.plan(f"{SAMSUNG} PER\uc774 {WHAT_IS}", session=session)

    assert_success(no_security, security_id=None, intent=FINANCIAL_TERM, sources=["glossary"], evidence=["definition"])
    assert_success(explicit, security_id=SAMSUNG_ID, intent=FINANCIAL_TERM, sources=["glossary"], evidence=["definition"])


def test_net_income_financial_term_routes_to_exact_query_plan():
    result = planner().plan("\uc21c\uc774\uc775\uc774 \ubb50\uc57c?")

    assert result == QueryPlan(
        security=None,
        intent=FINANCIAL_TERM,
        date_range=None,
        required_sources=["glossary"],
        required_evidence=["definition"],
        requires_clarification=False,
    )


@pytest.mark.parametrize("query", ["\uc601\uc5c5\uc774\uc775\ub960\uc774 \ubb50\uc57c?"])
def test_financial_term_markers_route_without_security(query):
    result = planner().plan(query)

    assert_success(result, security_id=None, intent=FINANCIAL_TERM, sources=["glossary"], evidence=["definition"])


def test_invalid_session_security_clarifies_only_security_required_intent():
    session = SessionContext(current_security_id="KRX:999999")
    query_planner = planner()

    news_plan = query_planner.plan(RECENT_NEWS, session=session)
    term_plan = query_planner.plan(f"PER\uc774 {WHAT_IS}", session=session)

    assert_clarification(news_plan, RECENT_ISSUE)
    assert_success(term_plan, security_id=None, intent=FINANCIAL_TERM, sources=["glossary"], evidence=["definition"])


@pytest.mark.parametrize(
    ("query", "intent", "sources", "evidence"),
    [
        (f"{SAMSUNG} {DISCLOSURE}", DISCLOSURE_SUMMARY, ["disclosure"], ["disclosure"]),
        (f"{SAMSUNG} {REPORT} \uc694\uc57d", RESEARCH_REPORT_SUMMARY, ["research_report"], ["research_report"]),
        (f"{SAMSUNG} {RECENT_NEWS}", RECENT_ISSUE, ["news"], ["recent_news"]),
        (f"{SAMSUNG} {RISK}", RISK_FACTORS, ["news", "disclosure", "research_report"], ["risk", "recent_news", "disclosure", "research_report"]),
        (f"{SAMSUNG} \ub274\uc2a4\uc640 {DISCLOSURE} {SUMMARY}", MULTI_SOURCE_SUMMARY, ["news", "disclosure", "research_report"], ["recent_news", "disclosure", "research_report"]),
    ],
)
def test_exact_intent_source_and_evidence_matrix(query, intent, sources, evidence):
    result = planner().plan(query)

    assert_success(result, security_id=SAMSUNG_ID, intent=intent, sources=sources, evidence=evidence)


@pytest.mark.parametrize(
    ("query", "intent", "sources", "evidence"),
    [
        (f"{SAMSUNG} \ubcf4\uc720 \uc9c0\ubd84 {DISCLOSURE} \uc694\uc57d", DISCLOSURE_SUMMARY, ["disclosure"], ["disclosure"]),
        (f"{SAMSUNG} \ub0b4\uc77c \ubc1c\ud45c {DISCLOSURE} \uc694\uc57d", DISCLOSURE_SUMMARY, ["disclosure"], ["disclosure"]),
        (f"{SAMSUNG} \ub9e4\uc218 \uc758\uacac {REPORT} \uc694\uc57d", RESEARCH_REPORT_SUMMARY, ["research_report"], ["research_report"]),
        (f"{SAMSUNG} \ubaa9\ud45c\uac00 {REPORT} \uc694\uc57d", RESEARCH_REPORT_SUMMARY, ["research_report"], ["research_report"]),
        (f"{SAMSUNG} brief {REPORT} \uc694\uc57d", RESEARCH_REPORT_SUMMARY, ["research_report"], ["research_report"]),
        (f"{SAMSUNG} \uc190\uc808 \uad00\ub828 {REPORT} \uc694\uc57d", RESEARCH_REPORT_SUMMARY, ["research_report"], ["research_report"]),
        (f"{SAMSUNG} \uc775\uc808 \uc804\ub7b5 {REPORT} \uc694\uc57d", RESEARCH_REPORT_SUMMARY, ["research_report"], ["research_report"]),
    ],
)
def test_benign_financial_wording_is_not_prohibited(query, intent, sources, evidence):
    result = planner().plan(query)

    assert_success(result, security_id=SAMSUNG_ID, intent=intent, sources=sources, evidence=evidence)


@pytest.mark.parametrize(
    ("query", "intent"),
    [
        (f"{SAMSUNG} \uc0ac\ub3c4 \ub3fc?", PROHIBITED_ADVICE),
        (f"{SAMSUNG} \ub9e4\uc218\ud574\uc57c \ud574?", PROHIBITED_ADVICE),
        (f"{SAMSUNG} \ub9e4\ub3c4\ud574\uc57c \ud574?", PROHIBITED_ADVICE),
        (f"{SAMSUNG} \uacc4\uc18d \ubcf4\uc720\ud574\uc57c \ud574?", PROHIBITED_ADVICE),
        (f"{SAMSUNG} \ubaa9\ud45c\uac00 \uc5bc\ub9c8\uc57c?", PROHIBITED_ADVICE),
        (f"{SAMSUNG} \ub0b4\uc77c \uc624\ub97c\uae4c?", PROHIBITED_ADVICE),
        (f"{SAMSUNG} \uc0c1\uc2b9 \ud655\ub960 \uc54c\ub824\uc918", PROHIBITED_ADVICE),
        (f"{SAMSUNG} \uc190\uc808\ud574\uc57c \ud574?", PROHIBITED_ADVICE),
        (f"{SAMSUNG} \uc190\uc808 \uc2dc\uc810 \uc54c\ub824\uc918", PROHIBITED_ADVICE),
        (f"{SAMSUNG} \uc775\uc808\ud560\uae4c?", PROHIBITED_ADVICE),
        (f"{SAMSUNG} \uc775\uc808 \uc2dc\uc810 \uc54c\ub824\uc918", PROHIBITED_ADVICE),
        (f"{SAMSUNG} {TODAY} \uc65c \uc62c\ub790\uc5b4?", OUT_OF_SCOPE),
    ],
)
def test_prohibited_and_inactive_price_move_plans_are_non_retrievable(query, intent):
    result = planner().plan(query)

    assert_clarification(result, intent)


def test_benign_historical_probability_word_is_not_prohibited_by_itself():
    result = planner().plan(f"{SAMSUNG} {RISK} \ud655\ub960")

    assert_success(
        result,
        security_id=SAMSUNG_ID,
        intent=RISK_FACTORS,
        sources=["news", "disclosure", "research_report"],
        evidence=["risk", "recent_news", "disclosure", "research_report"],
    )


def test_missing_security_for_security_required_intent_clarifies():
    result = planner().plan(RECENT_NEWS)

    assert_clarification(result, RECENT_ISSUE)


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        (f"{SAMSUNG} 2026-07-21 {DISCLOSURE}", DateRange(start=date(2026, 7, 21), end=date(2026, 7, 21))),
        (f"{SAMSUNG} 2026-07-20~2026-07-21 {DISCLOSURE}", DateRange(start=date(2026, 7, 20), end=date(2026, 7, 21))),
        (f"{SAMSUNG} 2026-07-20 ~ 2026-07-21 {DISCLOSURE}", DateRange(start=date(2026, 7, 20), end=date(2026, 7, 21))),
        (f"{SAMSUNG} {TODAY} {DISCLOSURE}", DateRange(start=date(2026, 7, 23), end=date(2026, 7, 23))),
    ],
)
def test_deterministic_period_parsing(query, expected):
    result = planner().plan(query)

    assert_success(result, security_id=SAMSUNG_ID, intent=DISCLOSURE_SUMMARY, sources=["disclosure"], evidence=["disclosure"], date_range=expected)


@pytest.mark.parametrize(
    "query",
    [
        f"{SAMSUNG} {RECENT_NEWS}",
        f"{SAMSUNG} 2026-02-30 {DISCLOSURE}",
        f"{SAMSUNG} 2026-07-210 {DISCLOSURE}",
        f"{SAMSUNG} 2026-07-22~2026-07-21 {DISCLOSURE}",
        f"{SAMSUNG} 2026-07-20~2026-07-21 2026-08-01~2026-08-02 {DISCLOSURE}",
        f"{SAMSUNG} 2026-07-20~2026-07-21 2026-08-01 {DISCLOSURE}",
        f"{SAMSUNG} {TODAY} 2026-07-21 {DISCLOSURE}",
        f"{SAMSUNG} {RECENT_NEWS} 2026-07-21",
        f"{SAMSUNG} {TODAY} 2026-07-20~2026-07-21 {DISCLOSURE}",
        f"{SAMSUNG} \ucd5c\uadfc 2026-07-20~2026-07-21 {DISCLOSURE}",
    ],
)
def test_period_cues_suppress_session_date_fallback(query):
    session = SessionContext(current_date_range=DateRange(start=date(2026, 1, 1), end=date(2026, 1, 2)))
    result = planner().plan(query, session=session)

    if result.intent == RECENT_ISSUE:
        assert_success(result, security_id=SAMSUNG_ID, intent=RECENT_ISSUE, sources=["news"], evidence=["recent_news"], date_range=None)
    else:
        assert_success(result, security_id=SAMSUNG_ID, intent=DISCLOSURE_SUMMARY, sources=["disclosure"], evidence=["disclosure"], date_range=None)


def test_session_date_fallback_is_used_only_without_period_cue_and_not_for_financial_term():
    session = SessionContext(current_date_range=DateRange(start=date(2026, 1, 1), end=date(2026, 1, 2)))
    query_planner = planner()

    disclosure = query_planner.plan(f"{SAMSUNG} {DISCLOSURE}", session=session)
    term = query_planner.plan(f"PER\uc774 {WHAT_IS}", session=session)

    assert_success(
        disclosure,
        security_id=SAMSUNG_ID,
        intent=DISCLOSURE_SUMMARY,
        sources=["disclosure"],
        evidence=["disclosure"],
        date_range=DateRange(start=date(2026, 1, 1), end=date(2026, 1, 2)),
    )
    assert_success(term, security_id=None, intent=FINANCIAL_TERM, sources=["glossary"], evidence=["definition"], date_range=None)


def test_result_lists_are_fresh_and_session_is_not_mutated():
    session_range = DateRange(start=date(2026, 1, 1), end=date(2026, 1, 2))
    session = SessionContext(current_security_id=SAMSUNG_ID, current_date_range=session_range)
    query_planner = planner()

    first = query_planner.plan(DISCLOSURE, session=session)
    first.required_sources.append("mutated")
    second = query_planner.plan(DISCLOSURE, session=session)

    assert second.required_sources == ["disclosure"]
    assert session.current_security_id == SAMSUNG_ID
    assert session.current_date_range == session_range


def test_resolver_failure_is_not_converted_to_query_plan():
    query_planner = planner(resolver=FailingResolver())

    with pytest.raises(RuntimeError):
        query_planner.plan(f"{SAMSUNG} {DISCLOSURE}")
