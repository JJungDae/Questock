from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from streamlit.testing.v1 import AppTest

from app.api.schemas import ChatRequest
from app.core.models import Evidence
from app.runtime import RuntimeConfig, build_runtime
from app.services.chat_service import ChatService
from app.services.market_snapshot_store import RecordedMarketSnapshotStore
from app.services.service_snapshot import SERVICE_SNAPSHOT_ID

NOW = datetime(2026, 7, 25, 3, tzinfo=UTC)


class FakeTransport:
    def __init__(self, response: Any) -> None:
        self.response = response
        self.requests: list[ChatRequest] = []
        self.timeouts: list[float] = []

    def send(
        self,
        request: ChatRequest,
        timeout_seconds: float,
    ) -> Any:
        self.requests.append(request)
        self.timeouts.append(timeout_seconds)
        return self.response.model_copy(deep=True)


def _response():
    return asyncio.run(
        ChatService(utc_now=lambda: NOW).chat(
            ChatRequest(
                message="삼성전자 최근 뉴스",
                session_id="streamlit-response",
            )
        )
    )


def _glossary_response():
    return asyncio.run(
        ChatService(utc_now=lambda: NOW).chat(
            ChatRequest(
                message="PER이 뭐야?",
                session_id="streamlit-glossary",
            )
        )
    )


def _comparison_response():
    state = build_runtime(
        config=RuntimeConfig(
            source_mode="recorded",
            snapshot_id=SERVICE_SNAPSHOT_ID,
            llm_mode="disabled",
        )
    )
    return asyncio.run(
        state.chat_service.chat(
            ChatRequest(
                message="현대차 실적 관련 최근 뉴스 근거를 대조해줘.",
                session_id="streamlit-comparison",
                as_of=datetime(
                    2026,
                    7,
                    27,
                    21,
                    tzinfo=ZoneInfo("Asia/Seoul"),
                ),
            )
        )
    )


def _app(transport: "FakeTransport") -> None:
    from app.ui.app import run

    run(transport)


def _submit(app: AppTest, question: str) -> None:
    app.chat_input[0].set_value(question).run()


def test_app_initial_render_has_expected_shell() -> None:
    app = AppTest.from_file("streamlit_app.py").run()

    assert not app.exception
    assert app.title[0].value == "Questock"
    assert len(app.selectbox) == 2
    assert app.selectbox[0].label == "기준 날짜"
    assert app.selectbox[1].label == "기준 시점"
    assert list(app.selectbox[0].options) == [
        "2026-07-24",
        "2026-07-25",
        "2026-07-26",
        "2026-07-27",
    ]
    assert len(app.selectbox[1].options) == 5
    assert len(app.chat_input) == 1
    assert (
        app.chat_input[0].proto.placeholder
        == "종목에 대해 궁금한 점을 물어보세요"
    )
    captions = "\n".join(item.value for item in app.caption)
    assert "Snapshot ID: svc-20260724-1402" in captions
    assert "선택 기준 시점: 2026-07-27 14:00 KST" in captions
    assert (
        "뉴스 수집 범위: 2026-07-24 00:00~2026-07-27 23:59 KST"
        in captions
    )
    assert "자료 모드: recorded" in captions
    assert "Gemini 3.5 Flash 또는 근거 기반 고정 응답" in captions
    assert "외부 LLM 전송 안 함" in captions
    assert "범위 부족 시 경고" in captions
    assert (
        "요청 한도 도달 시: 한도 안내와 함께 근거 기반 고정 응답"
        in captions
    )
    assert any(
        "개인 금융정보를 입력하지 마세요" in item.value
        for item in app.warning
    )
    reset = next(item for item in app.button if item.key == "reset_session")
    assert reset.label == "새 세션"
    assert all(
        not item.key.startswith("FormSubmitter:")
        for item in app.button
    )


def _price_response():
    return asyncio.run(
        ChatService(
            market_snapshot_store=RecordedMarketSnapshotStore(),
        ).chat(
            ChatRequest(
                message="삼성전자 현재 주가 얼마야?",
                session_id="streamlit-price",
                as_of=datetime(
                    2026,
                    7,
                    24,
                    21,
                    0,
                    tzinfo=ZoneInfo("Asia/Seoul"),
                ),
            )
        )
    )
def test_app_submit_uses_injected_transport_and_renders_process() -> None:
    transport = FakeTransport(_response())
    app = AppTest.from_function(_app, args=(transport,)).run()

    _submit(app, "삼성전자 최근 뉴스")

    assert not app.exception
    assert len(transport.requests) == 1
    assert transport.requests[0].message == "삼성전자 최근 뉴스"
    assert transport.requests[0].session_id.startswith("anonymous-")
    assert transport.requests[0].as_of == datetime(
        2026,
        7,
        27,
        14,
        0,
        tzinfo=ZoneInfo("Asia/Seoul"),
    )
    assert transport.timeouts == [35.0]
    assert app.chat_input[0].value in {None, ""}
    assert not app.get("spinner")
    assert any(item.label == "답변이 만들어진 과정" for item in app.expander)
    visible_text = "\n".join(item.value for item in app.text)
    for stage in (
        "상태:",
        "정규화:",
        "선택 근거:",
        "AI 상태:",
    ):
        assert stage in visible_text
    for forbidden in (
        "prompt",
        "reasoning",
        "api_key",
        "permission",
        "exception",
    ):
        assert forbidden not in visible_text.casefold()


def test_app_repeated_submissions_leave_no_loading_spinner() -> None:
    transport = FakeTransport(_response())
    app = AppTest.from_function(_app, args=(transport,)).run()

    _submit(app, "삼성전자 최근 뉴스")
    assert not app.get("spinner")

    _submit(app, "삼성전자 위험 요인")
    assert not app.get("spinner")
    assert len(transport.requests) == 2


def test_app_renders_comparison_conclusion_and_detailed_panel() -> None:
    response = _comparison_response()
    transport = FakeTransport(response)
    app = AppTest.from_function(_app, args=(transport,)).run()
    app.selectbox[0].select("2026-07-27").run()
    app.selectbox[1].select("전체 장 종료 후 (21:00)").run()

    _submit(app, "현대차 실적 관련 최근 뉴스 근거를 대조해줘.")

    assert not app.exception
    labels = [item.label for item in app.expander]
    assert "근거 대조 보기" in labels
    rendered = "\n".join(
        [
            *(item.value for item in app.markdown),
            *(item.value for item in app.text),
        ]
    )
    for expected in (
        "공통으로 확인된 사실",
        "뉴스가 다르게 본 점",
        "뉴스와 연결되는 리포트 배경",
        "DART가 확인해 주는 범위",
        "자료를 함께 보면",
    ):
        assert expected in rendered
    assert "참고한 자료" not in rendered
    for perspective in response.evidence_comparison.report_perspectives:
        assert perspective.source.source_url is None
        assert perspective.source.publisher in rendered


def test_app_renders_glossary_cards_source_detail_and_fixed_fallback() -> None:
    response = _glossary_response()
    transport = FakeTransport(response)
    app = AppTest.from_function(_app, args=(transport,)).run()

    _submit(app, "PER이 뭐야?")

    assert not app.exception
    labels = "\n".join(item.value for item in app.markdown)
    for label in (
        "핵심 요약",
        "왜 중요한가",
        "앞으로 확인할 점",
    ):
        assert label in labels
    for hidden in (
        "긍정적으로 볼 점",
        "주의해서 볼 점",
        "근거를 바탕으로 보면",
    ):
        assert hidden not in labels
    visible_output = "\n".join(
        [*(item.value for item in app.text), *(item.value for item in app.markdown)]
    )
    assert "금융 용어 ·" in visible_output
    visible_text = "\n".join(item.value for item in app.text)
    assert "항목 ID:" not in visible_text
    assert "버전:" not in visible_text
    assert "구간:" not in visible_text
    notices = "\n".join(item.value for item in app.info)
    assert (
        "AI 정리를 일시적으로 사용할 수 없어 검증된 근거를 직접 구성한 "
        "답변입니다."
        in notices
    )
    assert response.status == "complete"
    assert response.diagnostics_public.generation.mode == "fixed_template"
    assert response.diagnostics_public.sources[0].document_count == 4


def test_app_provider_failure_uses_stable_red_fallback_and_mode() -> None:
    response = _response()
    transport = FakeTransport(response)
    app = AppTest.from_function(_app, args=(transport,)).run()

    _submit(app, "삼성전자 최근 뉴스")

    assert not app.exception
    assert response.status == "provider_failed"
    assert app.error
    assert any(
        "자료 제공 상태를 확인하지 못해 답변을 보류합니다."
        in item.value
        for item in app.error
    )
    captions = "\n".join(item.value for item in app.caption)
    assert "자료 제공 실패" in captions
    assert "상태: 자료 제공 실패" not in captions
    assert "자료 모드: 자료 미연결" in captions
    visible_text = "\n".join(item.value for item in app.text)
    assert "자료 제공 경로가 구성되지 않았거나 이용 불가" in visible_text
    assert "provider_unavailable" not in visible_text


def test_app_renders_selected_time_market_status_and_observation_time() -> None:
    transport = FakeTransport(_price_response())
    app = AppTest.from_function(_app, args=(transport,)).run()

    _submit(app, "삼성전자 현재 주가 얼마야?")

    assert not app.exception
    captions = "\n".join(item.value for item in app.caption)
    assert "기준 시점 2026-07-24 21:00 KST" in captions
    assert "시장 상태 장 종료·휴장" in captions
    assert "가격 관측 2026-07-24 19:59 KST" in captions
    rendered = "\n".join(
        item.value for item in app.markdown
    )
    assert "252,500원" in rendered


def test_app_renders_malicious_html_as_text_not_markdown() -> None:
    response = _glossary_response()
    malicious = response.evidence[0].model_copy(
        update={
            "snippet": "<script>alert('display-only')</script>",
        }
    )
    response = response.model_copy(update={"evidence": [malicious]})
    transport = FakeTransport(response)
    app = AppTest.from_function(_app, args=(transport,)).run()

    _submit(app, "PER이 뭐야?")

    assert not app.exception
    assert all(
        "<script>" not in item.value
        for item in app.text
    )
    assert all(
        "<script>" not in item.value
        for item in app.markdown
    )


def test_app_dynamic_metadata_is_plain_text_and_only_source_url_is_link() -> None:
    response = _glossary_response()
    injected = response.evidence[0].model_copy(
        update={
            "title": "/tmp",
            "source_url": "https://approved.example/source",
            "locator": {
                **response.evidence[0].locator,
                "entry_id": "![이미지](https://unapproved.example)",
                "section": "[공식](https://unapproved.example)",
            },
        }
    )
    response = response.model_copy(update={"evidence": [injected]})
    transport = FakeTransport(response)
    app = AppTest.from_function(_app, args=(transport,)).run()

    _submit(app, "PER이 뭐야?")

    assert not app.exception
    visible_text = "\n".join(item.value for item in app.text)
    assert "/tmp" not in visible_text
    assert "[공식](https://unapproved.example)" not in visible_text
    assert "![이미지](https://unapproved.example)" not in visible_text
    rendered_markdown = "\n".join(item.value for item in app.markdown)
    assert "https://approved.example/source" in rendered_markdown
    assert "안전하게 표시할 수 없는 내용입니다." in rendered_markdown
    assert all(
        "unapproved.example" not in item.value
        for item in app.markdown
    )


def test_app_keeps_session_across_turns_and_reset_creates_isolated_id() -> None:
    transport = FakeTransport(_response())
    app = AppTest.from_function(_app, args=(transport,)).run()

    _submit(app, "삼성전자 최근 뉴스")
    first_session_id = transport.requests[-1].session_id

    _submit(app, "그럼 위험 요인은?")

    assert transport.requests[-1].session_id == first_session_id
    reset = next(item for item in app.button if item.key == "reset_session")
    reset.click()
    app.run()
    assert not app.subheader

    _submit(app, "그럼 위험 요인은?")

    assert transport.requests[-1].session_id != first_session_id
    assert transport.requests[-1].session_id.startswith("anonymous-")


def test_app_rerun_without_submit_never_calls_transport() -> None:
    transport = FakeTransport(_response())
    app = AppTest.from_function(_app, args=(transport,)).run()

    app.run()

    assert not app.exception
    assert transport.requests == []


def test_changing_checkpoint_clears_visible_conversation_and_session() -> None:
    transport = FakeTransport(_response())
    app = AppTest.from_function(_app, args=(transport,)).run()
    _submit(app, "삼성전자 최근 뉴스")
    first_session_id = transport.requests[-1].session_id

    app.selectbox[1].select("장중 (10:00)").run()

    assert not app.exception
    assert not app.chat_message
    _submit(app, "삼성전자 현재 주가 얼마야?")
    assert transport.requests[-1].session_id != first_session_id
    assert transport.requests[-1].as_of == datetime(
        2026,
        7,
        27,
        10,
        0,
        tzinfo=ZoneInfo("Asia/Seoul"),
    )


def test_changing_checkpoint_date_clears_visible_conversation_and_session() -> None:
    transport = FakeTransport(_response())
    app = AppTest.from_function(_app, args=(transport,)).run()
    _submit(app, "삼성전자 최근 뉴스")
    first_session_id = transport.requests[-1].session_id

    app.selectbox[0].select(date(2026, 7, 25)).run()

    assert not app.exception
    assert not app.chat_message
    _submit(app, "삼성전자 현재 주가 얼마야?")
    assert transport.requests[-1].session_id != first_session_id
    assert transport.requests[-1].as_of == datetime(
        2026,
        7,
        25,
        14,
        0,
        tzinfo=ZoneInfo("Asia/Seoul"),
    )


def test_app_renders_conflict_cards_and_three_safe_sources() -> None:
    response = _glossary_response()
    response = response.model_copy(
        deep=True,
        update={
            "answer_sections": response.answer_sections.model_copy(
                update={
                    "summary": ["수요와 비용 변수가 함께 확인됐다."],
                    "facts": [],
                    "interpretation": [],
                    "inference": [],
                    "positive_factors": ["수요 증가는 긍정 요인이다."],
                    "risk_factors": ["원가 상승은 위험 요인이다."],
                    "uncertainty": ["실제 영향은 추가 확인이 필요하다."],
                }
            ),
            "evidence": _three_source_evidence(),
        },
    )
    transport = FakeTransport(response)
    app = AppTest.from_function(_app, args=(transport,)).run()

    _submit(app, "삼성전자 여러 자료 요약")

    assert not app.exception
    labels = "\n".join(item.value for item in app.markdown)
    for label in (
        "긍정적으로 볼 점",
        "주의해서 볼 점",
        "앞으로 확인할 점",
    ):
        assert label in labels
    rendered_sources = "\n".join(
        [*(item.value for item in app.markdown), *(item.value for item in app.text)]
    )
    for label in ("뉴스", "공시", "리서치 리포트"):
        assert label in rendered_sources
    assert sum("](" in item.value for item in app.markdown) == 2
    assert any(item.label == "답변이 만들어진 과정" for item in app.expander)


def _three_source_evidence() -> list[Evidence]:
    news_url = "https://news.example.test/multi"
    receipt_no = "20260725000001"
    disclosure_url = (
        "https://dart.fss.or.kr/dsaf001/main.do"
        f"?rcpNo={receipt_no}"
    )
    return [
        Evidence(
            evidence_id="evidence:news:multi",
            document_id="document:news:multi",
            source_type="news",
            title="뉴스 근거",
            source_url=news_url,
            published_at=NOW,
            subject_security_ids=["KRX:005930"],
            mentioned_security_ids=[],
            scope="company_specific",
            snippet="수요 증가는 긍정 요인이다.",
            locator={"provider": "recorded_news", "source_url": news_url},
            retrieval_score=0.9,
        ),
        Evidence(
            evidence_id="evidence:disclosure:multi",
            document_id="document:disclosure:multi",
            source_type="disclosure",
            title="공시 근거",
            source_url=disclosure_url,
            published_at=NOW,
            subject_security_ids=["KRX:005930"],
            mentioned_security_ids=[],
            scope="company_specific",
            snippet="회사는 투자 계획을 공시했다.",
            locator={
                "provider": "recorded_disclosure",
                "receipt_no": receipt_no,
                "viewer_url": disclosure_url,
            },
            retrieval_score=0.8,
        ),
        Evidence(
            evidence_id="evidence:report:multi",
            document_id="document:report:multi",
            source_type="research_report",
            title="리포트 근거",
            source_url=None,
            published_at=NOW,
            subject_security_ids=["KRX:005930"],
            mentioned_security_ids=[],
            scope="company_specific",
            snippet="원가 상승은 위험 요인이다.",
            locator={
                "manifest_id": "report-multi-001",
                "document_id": "document:report:multi",
                "page_basis": "source_section_only",
                "page": None,
                "section": "위험 요인",
                "source_url": None,
                "source_asset_id": "report-multi-001",
            },
            retrieval_score=0.7,
        ),
    ]
