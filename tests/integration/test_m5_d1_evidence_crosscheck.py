from __future__ import annotations

import asyncio
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from app.answer.models import AnswerSections
from app.api.schemas import ChatRequest
from app.llm.base import (
    LLMRequest,
    LLMResult,
    LLMStatus,
    create_llm_result,
)
from app.runtime import RuntimeConfig, build_runtime
from app.services.service_snapshot import SERVICE_SNAPSHOT_ID
from app.ui.projections import (
    project_baseline_answer,
    project_evidence_comparison,
)

SEOUL_TZ = ZoneInfo("Asia/Seoul")


class _ComparisonLLM:
    def __init__(
        self,
        *,
        status: LLMStatus = LLMStatus.OK,
    ) -> None:
        self.status = status
        self.requests: list[LLMRequest] = []

    async def complete(
        self,
        request: LLMRequest,
        *,
        timeout_seconds: float,
    ) -> LLMResult:
        del timeout_seconds
        self.requests.append(request.model_copy(deep=True))
        rendered = "\n".join(
            item.content for item in request.messages
        )
        snippet = next(
            line.split("Snippet: ", 1)[1].strip()
            for line in rendered.splitlines()
            if line.startswith("Snippet: ")
        )
        content = json.dumps(
            {
                "claims": [
                    {
                        "claim_id": "comparison-summary",
                        "section": "summary",
                        "text": snippet,
                        "evidence_ids": ["E1"],
                    },
                    {
                        "claim_id": "comparison-interpretation",
                        "section": "interpretation",
                        "text": (
                            "전자신문은 영업이익 감소와 당일 주가 반응을 "
                            "중심으로 설명했습니다. 반면 매일신문은 판매 "
                            "감소와 관세·원재료 부담을 실적 부진의 배경으로 "
                            "강조했습니다. 즉 전자는 시장 반응을, 후자는 "
                            "실적 부진의 원인을 더 강조했습니다."
                        ),
                        "evidence_ids": ["E3", "E4"],
                    }
                ]
            },
            ensure_ascii=False,
        )
        return create_llm_result(
            status=self.status,
            content=content if self.status == LLMStatus.OK else None,
            model="gemini/gemini-3.5-flash",
            provider="gemini",
            latency_ms=1,
        )


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
    assert not comparison.answer_integrated
    general_view = project_baseline_answer(
        response.model_copy(
            update={
                "answer_sections": AnswerSections(
                    summary=["일반 답변"],
                    interpretation=["일반적인 중요성 설명"],
                )
            },
            deep=True,
        )
    )
    assert ("interpretation", "왜 중요한가") in {
        (item.key, item.title)
        for item in general_view.cards
    }
    assert all(
        source.published_at <= cutoff
        for source in comparison.article_sources
    )
    assert comparison.common_facts == []
    assert comparison.missing_evidence
    assert all(
        item.source.source_url is None
        for item in comparison.report_perspectives
    )
    assert all(
        item.source_locator
        for item in comparison.report_perspectives
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
    assert view.report_perspectives
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
    assert response.evidence_comparison.answer_integrated
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
    assert comparison.answer_integrated
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
    assert response.evidence_comparison.answer_integrated
    comparison = response.evidence_comparison
    assert comparison.common_facts
    assert comparison.different_interpretations
    assert "2분기 실적 부진" in response.answer_sections.summary[0]
    assert len(response.answer_sections.interpretation) == 1
    assert "반면" in response.answer_sections.interpretation[0]
    comparison_view = project_baseline_answer(response)
    assert ("interpretation", "뉴스가 다르게 본 점") in {
        (item.key, item.title)
        for item in comparison_view.cards
    }
    assert ("inference", "자료를 함께 보면") in {
        (item.key, item.title)
        for item in comparison_view.cards
    }
    assert any(
        "DART" in item
        for item in response.answer_sections.inference
    )
    assert response.answer_sections.inference == [
        comparison.support_summary
    ]
    assert any(
        "공식 발표 이후" in item.text
        and "구체적인 실적 수치" in item.text
        for item in comparison.disclosure_links
    )


def test_explicit_unmatched_comparison_keeps_general_answer_after_notice() -> None:
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
                message="삼성전자 실적 관련 최근 뉴스 근거를 대조해줘.",
                session_id="m5-d1-unmatched-comparison",
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
    assert "동일 사건 대조 자료" in response.answer_sections.summary[0]
    assert (
        len(response.answer_sections.summary) > 1
        or response.answer_sections.facts
        or response.answer_sections.positive_factors
        or response.answer_sections.risk_factors
    )


def test_matching_comparison_uses_low_randomness_gemini_once(
    monkeypatch,
) -> None:
    client = _ComparisonLLM()
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(
        "app.runtime.LiteLLMClient",
        lambda config: client,
    )
    state = build_runtime(
        config=RuntimeConfig(
            source_mode="recorded",
            snapshot_id=SERVICE_SNAPSHOT_ID,
            llm_mode="gemini",
        )
    )

    response = asyncio.run(
        state.chat_service.chat(
            ChatRequest(
                message="현대차 실적 관련 최근 뉴스 근거를 대조해줘.",
                session_id="m5-d1-gemini-comparison",
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

    assert len(client.requests) == 1
    request = client.requests[0]
    assert request.temperature == 0.1
    rendered = "\n".join(
        item.content for item in request.messages
    )
    assert "뉴스 공통 사실:" in rendered
    assert "기사별 강조점 차이:" in rendered
    assert "생산 차질·환율·인센티브" not in rendered
    assert "DART에서는 7월 23일" not in rendered
    assert response.diagnostics_public.generation.mode == "llm"
    assert response.diagnostics_public.generation.llm_status == "ok"
    assert response.evidence_comparison is not None
    assert response.evidence_comparison.answer_integrated
    assert response.evidence_comparison.common_facts
    assert response.evidence_comparison.different_interpretations
    assert response.evidence_comparison.support_summary in (
        response.answer_sections.inference
    )
    assert len(response.answer_sections.interpretation) == 1
    assert "반면" in response.answer_sections.interpretation[0]
    assert "즉" in response.answer_sections.interpretation[0]


def test_matching_comparison_keeps_cited_fallback_when_gemini_times_out(
    monkeypatch,
) -> None:
    client = _ComparisonLLM(status=LLMStatus.TIMEOUT)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(
        "app.runtime.LiteLLMClient",
        lambda config: client,
    )
    state = build_runtime(
        config=RuntimeConfig(
            source_mode="recorded",
            snapshot_id=SERVICE_SNAPSHOT_ID,
            llm_mode="gemini",
        )
    )

    response = asyncio.run(
        state.chat_service.chat(
            ChatRequest(
                message="현대차 실적 관련 최근 뉴스 근거를 대조해줘.",
                session_id="m5-d1-gemini-timeout",
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

    assert len(client.requests) == 1
    assert response.diagnostics_public.generation.mode == "fixed_template"
    assert response.diagnostics_public.generation.llm_status == "timeout"
    assert "llm_generation_degraded" in response.warnings
    comparison = response.evidence_comparison
    assert comparison is not None
    assert comparison.answer_integrated
    assert comparison.common_facts[0].text in (
        response.answer_sections.summary
    )
    assert len(response.answer_sections.interpretation) == 1
    comparison_text = response.answer_sections.interpretation[0]
    assert "전자신문" in comparison_text
    assert "매일신문" in comparison_text
    assert "반면" in comparison_text
    assert "즉" in comparison_text
    assert response.answer_sections.inference == [
        comparison.support_summary
    ]


def test_public_report_evidence_omits_report_urls() -> None:
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
                message="현대차 리포트 핵심을 요약해줘.",
                session_id="m5-d1-report-link-policy",
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

    reports = [
        item
        for item in response.evidence
        if item.source_type == "research_report"
    ]
    assert reports
    assert all(item.source_url is None for item in reports)
    assert all(
        all("url" not in key.casefold() for key in item.locator)
        for item in reports
    )
