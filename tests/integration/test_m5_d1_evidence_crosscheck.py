from __future__ import annotations

import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from app.api.schemas import ChatRequest
from app.runtime import RuntimeConfig, build_runtime
from app.services.service_snapshot import SERVICE_SNAPSHOT_ID
from app.ui.projections import project_evidence_comparison

SEOUL_TZ = ZoneInfo("Asia/Seoul")


def test_recorded_runtime_attaches_cited_temporal_comparison() -> None:
    state = build_runtime(
        config=RuntimeConfig(
            source_mode="recorded",
            snapshot_id=SERVICE_SNAPSHOT_ID,
            llm_mode="disabled",
        )
    )
    cutoff = datetime(2026, 7, 27, 21, tzinfo=SEOUL_TZ)

    response = asyncio.run(
        state.chat_service.chat(
            ChatRequest(
                message="삼성전자 HBM5 2나노 이슈가 뭐야?",
                session_id="m5-d1-integration",
                as_of=cutoff,
            )
        )
    )

    comparison = response.evidence_comparison
    assert comparison is not None
    assert all(
        source.published_at <= cutoff
        for source in comparison.article_sources
    )
    assert comparison.common_facts == []
    assert comparison.missing_evidence
    assert all(
        item.source.source_url.startswith(("http://", "https://"))
        for item in comparison.different_interpretations
    )
    assert all(
        item.source_locator
        for item in comparison.different_interpretations
    )
    assert all(
        item.source is None
        or item.source.source_url.startswith(("http://", "https://"))
        for item in comparison.disclosure_links
    )

    view = project_evidence_comparison(comparison)
    assert view is not None
    assert "원출처 관계 미확인" in view.lineage_text
    assert view.article_count_text == "전체 27건 중 20건 표시"
    assert view.articles
    assert view.perspectives
    assert view.disclosures


def test_explicit_repetition_question_is_answered_by_comparison_result() -> None:
    state = build_runtime(
        config=RuntimeConfig(
            source_mode="recorded",
            snapshot_id=SERVICE_SNAPSHOT_ID,
            llm_mode="disabled",
        )
    )
    response = asyncio.run(
        state.chat_service.chat(
            ChatRequest(
                message=(
                    "삼성전자 HBM5 최근 뉴스가 같은 사건을 "
                    "반복한 건지 알려줘."
                ),
                session_id="m5-d1-explicit-repetition",
                as_of=datetime(
                    2026,
                    7,
                    27,
                    21,
                    tzinfo=SEOUL_TZ,
                ),
            )
        )
    )

    assert response.evidence_comparison is not None
    assert "같은 주제의 사건 묶음" in (
        response.answer_sections.summary[0]
    )
    assert "독립 보도인지 재인용인지" in (
        response.answer_sections.summary[0]
    )
    assert all(
        "HBM5" in f"{item.title} {item.snippet}"
        or "2나노" in f"{item.title} {item.snippet}"
        for item in response.evidence
    )


def test_generic_repetition_answer_uses_selected_event_article_links() -> None:
    state = build_runtime(
        config=RuntimeConfig(
            source_mode="recorded",
            snapshot_id=SERVICE_SNAPSHOT_ID,
            llm_mode="disabled",
        )
    )
    response = asyncio.run(
        state.chat_service.chat(
            ChatRequest(
                message=(
                    "현대차 최근 뉴스가 여러 보도사에서 "
                    "반복됐는지 알려줘."
                ),
                session_id="m5-d1-hyundai-repetition",
                as_of=datetime(
                    2026,
                    7,
                    27,
                    21,
                    tzinfo=SEOUL_TZ,
                ),
            )
        )
    )

    comparison = response.evidence_comparison
    assert comparison is not None
    assert response.evidence
    assert {
        item.source_url for item in response.evidence
    }.issubset(
        {
            source.source_url
            for source in comparison.article_sources
        }
    )
    assert all(
        item.subject_security_ids == ["KRX:005380"]
        for item in response.evidence
    )


def test_generic_disclosure_question_does_not_attach_unrelated_event() -> None:
    state = build_runtime(
        config=RuntimeConfig(
            source_mode="recorded",
            snapshot_id=SERVICE_SNAPSHOT_ID,
            llm_mode="disabled",
        )
    )
    response = asyncio.run(
        state.chat_service.chat(
            ChatRequest(
                message="삼성전자 최근 공시의 핵심만 요약해줘.",
                session_id="m5-d1-disclosure-no-event",
                as_of=datetime(
                    2026,
                    7,
                    27,
                    14,
                    tzinfo=SEOUL_TZ,
                ),
            )
        )
    )

    assert response.evidence_comparison is None


def test_generic_recent_issue_does_not_attach_a_different_event() -> None:
    state = build_runtime(
        config=RuntimeConfig(
            source_mode="recorded",
            snapshot_id=SERVICE_SNAPSHOT_ID,
            llm_mode="disabled",
        )
    )
    response = asyncio.run(
        state.chat_service.chat(
            ChatRequest(
                message="현대차 최근 이슈를 알려줘.",
                session_id="m5-d1-generic-no-event",
                as_of=datetime(
                    2026,
                    7,
                    27,
                    21,
                    tzinfo=SEOUL_TZ,
                ),
            )
        )
    )

    assert response.evidence_comparison is None


def test_explicit_evidence_crosscheck_attaches_matching_event() -> None:
    state = build_runtime(
        config=RuntimeConfig(
            source_mode="recorded",
            snapshot_id=SERVICE_SNAPSHOT_ID,
            llm_mode="disabled",
        )
    )
    response = asyncio.run(
        state.chat_service.chat(
            ChatRequest(
                message="현대차 실적 관련 최근 뉴스 근거를 대조해줘.",
                session_id="m5-d1-explicit-crosscheck",
                as_of=datetime(
                    2026,
                    7,
                    27,
                    21,
                    tzinfo=SEOUL_TZ,
                ),
            )
        )
    )

    assert response.evidence_comparison is not None
    assert "같은 주제의 사건 묶음" in (
        response.answer_sections.summary[0]
    )
