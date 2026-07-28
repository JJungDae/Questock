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
        "답변에 사용할 수 있는 근거를 확인하지 못했습니다."
    )
    assert response.answer_sections.facts == []
    assert all(
        "가능한 배경 요인" not in item
        for item in response.answer_sections.uncertainty
    )
