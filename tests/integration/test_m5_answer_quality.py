from __future__ import annotations

import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from app.api.schemas import ChatRequest
from app.runtime import RuntimeConfig, build_runtime

KST = ZoneInfo("Asia/Seoul")


def _service():
    return build_runtime(
        config=RuntimeConfig(
            source_mode="recorded",
            snapshot_id="svc-20260724-1402",
            llm_mode="disabled",
        )
    ).chat_service


def _chat(
    service,
    message: str,
    *,
    session_id: str,
    as_of: datetime,
):
    return asyncio.run(
        service.chat(
            ChatRequest(
                message=message,
                session_id=session_id,
                as_of=as_of,
            )
        )
    )


def test_price_move_defaults_to_same_day_and_uses_news_before_reports() -> None:
    response = _chat(
        _service(),
        "삼성전자 주가 왜 떨어졌어?",
        session_id="quality-samsung-news-first",
        as_of=datetime(2026, 7, 24, 14, 0, tzinfo=KST),
    )

    assert response.diagnostics_public.query_plan.intent == "price_move"
    assert response.diagnostics_public.query_plan.date_start.isoformat() == (
        "2026-07-24"
    )
    assert response.diagnostics_public.query_plan.date_end.isoformat() == (
        "2026-07-24"
    )
    assert response.evidence
    assert {item.source_type for item in response.evidence} == {"news"}
    assert response.missing_sources == []
    assert "disclosure_window_expanded" not in response.warnings
    assert "insufficient_disclosure_coverage" not in response.warnings
    assert "7.22% 하락" in response.answer_sections.summary[0]
    assert all(
        "가격 250,500원" not in item
        for item in response.answer_sections.facts
    )


def test_risk_follow_up_is_not_misrouted_to_direct_price() -> None:
    service = _service()
    as_of = datetime(2026, 7, 24, 14, 0, tzinfo=KST)
    _chat(
        service,
        "오늘 하이닉스 주식 올랐어?",
        session_id="quality-risk-follow-up",
        as_of=as_of,
    )

    response = _chat(
        service,
        "왜 주가변동성이 위험요인이야?",
        session_id="quality-risk-follow-up",
        as_of=as_of,
    )

    assert response.diagnostics_public.query_plan.intent == "risk_factors"
    assert response.market_snapshot is None
    public_text = " ".join(
        (
            *response.answer_sections.summary,
            *response.answer_sections.facts,
        )
    )
    assert "1,775,000원" not in public_text


def test_after_market_price_move_uses_all_same_day_news_and_natural_fallback() -> None:
    response = _chat(
        _service(),
        "삼성전자 주가 왜 올랐어?",
        session_id="quality-samsung-after-market",
        as_of=datetime(2026, 7, 27, 19, 0, tzinfo=KST),
    )

    assert len(response.evidence) == 3
    assert any("HBM5" in item.title for item in response.evidence)
    assert all(
        item.published_at is not None
        and item.published_at <= response.basis_at
        for item in response.evidence
    )
    public_text = " ".join(
        value
        for section in (
            response.answer_sections.summary,
            response.answer_sections.facts,
            response.answer_sections.uncertainty,
        )
        for value in section
    )
    assert "기사 제목에서 확인되는 내용" not in public_text
    assert "직접 원인" not in public_text


def test_no_evidence_price_move_keeps_no_evidence_status_without_price_card() -> None:
    response = _chat(
        _service(),
        "현대차 주가 왜 올랐어?",
        session_id="quality-hyundai-no-evidence",
        as_of=datetime(2026, 7, 27, 21, 0, tzinfo=KST),
    )

    assert response.status == "no_evidence"
    assert response.evidence == []
    assert response.answer_sections.summary[1] == (
        "현대자동차의 해당 시점 당일 가격 움직임을 설명할 회사 직접 "
        "근거를 확인하지 못했습니다. 확인되지 않은 원인을 추정하지 "
        "않겠습니다."
    )
    assert response.answer_sections.facts == []
    assert all(
        "가능한 배경 요인" not in item
        for item in response.answer_sections.uncertainty
    )


def test_disclosure_fixed_answer_leads_with_readable_core_financials() -> None:
    response = _chat(
        _service(),
        "삼성전자 최근 공시의 핵심만 요약해줘.",
        session_id="quality-disclosure-core",
        as_of=datetime(2026, 7, 27, 14, 0, tzinfo=KST),
    )

    public_text = " ".join(
        (
            *response.answer_sections.summary,
            *response.answer_sections.facts,
        )
    )
    assert response.answer_sections.summary[0].startswith(
        "분기보고서 (제58기) 기준으로,"
    )
    assert "약 133.9조원" in response.answer_sections.summary[0]
    assert "약 57.2조원" in public_text
    assert "환율변동위험" not in response.answer_sections.summary[0]
    assert len(response.evidence) <= 3


def test_per_fixed_answer_connects_alias_to_beginner_definition() -> None:
    response = _chat(
        _service(),
        "PER이 뭐야?",
        session_id="quality-term-per",
        as_of=datetime(2026, 7, 27, 14, 0, tzinfo=KST),
    )

    assert response.answer_sections.summary[0].startswith(
        "PER(주가수익비율)은"
    )
    assert "EPS" in " ".join(response.answer_sections.facts)


def test_easy_report_fixed_answer_omits_low_priority_dense_figures() -> None:
    response = _chat(
        _service(),
        "현대차 증권사 리포트의 관점을 쉽게 설명해줘.",
        session_id="quality-report-easy",
        as_of=datetime(2026, 7, 27, 19, 0, tzinfo=KST),
    )

    public_text = " ".join(
        value
        for section in response.answer_sections.model_dump().values()
        for value in section
    )
    assert "3분기 로봇 관련 일정" in response.answer_sections.summary[0]
    assert "RMAC" not in public_text
    assert "목표 시가총액" not in public_text
    assert len(response.evidence) <= 3


def test_risk_answer_does_not_append_positive_limited_risk_report() -> None:
    response = _chat(
        _service(),
        "삼성전자 최근 뉴스에서 조심할 점을 알려줘.",
        session_id="quality-risk-report-filter",
        as_of=datetime(2026, 7, 27, 14, 0, tzinfo=KST),
    )

    public_text = " ".join(
        value
        for section in response.answer_sections.model_dump().values()
        for value in section
    )
    assert "가격 훼손 우려가 제한적" not in public_text
    assert "평균판매가격(ASP) 상승세 둔화" not in public_text
    assert response.evidence
    assert all(item.source_type == "news" for item in response.evidence)


def test_short_company_switch_preserves_news_context() -> None:
    service = _service()
    as_of = datetime(2026, 7, 25, 21, 0, tzinfo=KST)
    _chat(
        service,
        "삼성전자 최근 뉴스에서 호재가 뭐야?",
        session_id="quality-short-company-switch",
        as_of=as_of,
    )

    response = _chat(
        service,
        "SK하이닉스는?",
        session_id="quality-short-company-switch",
        as_of=as_of,
    )

    assert response.diagnostics_public.query_plan.intent == "recent_issue"
    assert response.security is not None
    assert response.security.ticker == "000660"
    assert response.evidence
    assert {item.source_type for item in response.evidence} == {"news"}


def test_core_follow_up_is_shorter_than_initial_disclosure_answer() -> None:
    service = _service()
    as_of = datetime(2026, 7, 27, 14, 0, tzinfo=KST)
    first = _chat(
        service,
        "삼성전자 최근 공시를 요약해줘.",
        session_id="quality-disclosure-resummary",
        as_of=as_of,
    )
    second = _chat(
        service,
        "그 공시의 핵심 사실만 다시 요약해줘.",
        session_id="quality-disclosure-resummary",
        as_of=as_of,
    )

    first_claims = sum(
        len(values)
        for values in first.answer_sections.model_dump().values()
    )
    second_claims = sum(
        len(values)
        for values in second.answer_sections.model_dump().values()
    )
    assert second_claims < first_claims
    assert (
        second.answer_sections.model_dump_json()
        != first.answer_sections.model_dump_json()
    )
    assert second.answer_sections.summary[0].startswith(
        "다시 핵심만 말하면,"
    )
    assert second.answer_sections.facts[0].startswith(
        "같은 기간 연결 영업이익"
    )


def test_explicit_news_and_disclosure_fixed_fallback_respects_sources() -> None:
    response = _chat(
        _service(),
        "SK하이닉스 뉴스와 공시를 한 번에 요약해줘.",
        session_id="quality-explicit-source-types",
        as_of=datetime(2026, 7, 27, 21, 0, tzinfo=KST),
    )

    assert response.evidence
    assert {item.source_type for item in response.evidence} == {
        "news",
        "disclosure",
    }
    public_text = " ".join(
        value
        for values in response.answer_sections.model_dump().values()
        for value in values
    )
    assert "약 52.6조원" in public_text
    assert "약 37.6조원" in public_text


def test_beginner_per_answer_explains_eps() -> None:
    response = _chat(
        _service(),
        "PER 뜻을 주식 초보도 이해하게 설명해줘.",
        session_id="quality-beginner-per",
        as_of=datetime(2026, 7, 27, 21, 0, tzinfo=KST),
    )

    assert any(
        "회사의 이익을 주식 수로 나눈 주식 1주당 이익" in value
        for value in response.answer_sections.facts
    )


def test_operating_margin_answer_explains_high_value_intuitively() -> None:
    response = _chat(
        _service(),
        "영업이익률이 높으면 무슨 뜻이야?",
        session_id="quality-operating-margin",
        as_of=datetime(2026, 7, 27, 21, 0, tzinfo=KST),
    )

    assert any(
        "본업의 이익으로 남는 몫이 크다" in value
        for value in response.answer_sections.interpretation
    )
