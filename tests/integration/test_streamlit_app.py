from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from streamlit.testing.v1 import AppTest

from app.api.schemas import ChatRequest
from app.core.models import Evidence
from app.services.chat_service import ChatService
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


def _app(transport: FakeTransport) -> None:
    from app.ui.app import run

    run(transport)


def test_app_initial_render_has_expected_shell() -> None:
    app = AppTest.from_file("streamlit_app.py").run()

    assert not app.exception
    assert app.title[0].value == "Questock"
    assert app.selectbox[0].label == "지원 종목"
    assert app.text_area[0].label == "질문"
    reset = next(item for item in app.button if item.key == "reset_session")
    submit = next(
        item
        for item in app.button
        if item.key.startswith("FormSubmitter:chat_form-")
    )
    assert reset.label == "새 세션"
    assert submit.label == "질문 보내기"


def test_app_submit_uses_injected_transport_and_renders_process() -> None:
    transport = FakeTransport(_response())
    app = AppTest.from_function(_app, args=(transport,)).run()

    app.text_area[0].input("삼성전자 최근 뉴스")
    submit = next(
        item
        for item in app.button
        if item.key.startswith("FormSubmitter:chat_form-")
    )
    submit.click()
    app.run()

    assert not app.exception
    assert len(transport.requests) == 1
    assert transport.requests[0].message == "삼성전자 최근 뉴스"
    assert transport.requests[0].session_id.startswith("anonymous-")
    assert transport.timeouts == [21.0]
    assert any(item.label == "분석 과정 보기" for item in app.expander)
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


def test_app_renders_glossary_cards_source_detail_and_fixed_fallback() -> None:
    response = _glossary_response()
    transport = FakeTransport(response)
    app = AppTest.from_function(_app, args=(transport,)).run()

    app.text_area[0].input("PER이 뭐야?")
    submit = next(
        item
        for item in app.button
        if item.key.startswith("FormSubmitter:chat_form-")
    )
    submit.click()
    app.run()

    assert not app.exception
    labels = "\n".join(item.value for item in app.markdown)
    for label in (
        "한 줄 결론",
        "왜 중요한가",
        "더 확인할 것",
    ):
        assert label in labels
    for hidden in (
        "확인된 사실",
        "긍정 요인",
        "확인된 위험",
        "AI 정리·추론",
    ):
        assert hidden not in labels
    captions = "\n".join(item.value for item in app.caption)
    assert "금융 용어" in captions
    visible_text = "\n".join(item.value for item in app.text)
    assert "항목 ID: glossary:per" in visible_text
    assert "버전: 1" in visible_text
    assert "구간: definition" in visible_text
    warnings = "\n".join(item.value for item in app.warning)
    assert "AI 정리 대신 근거 기반 고정 응답 사용" in warnings
    assert response.status == "complete"
    assert response.diagnostics_public.generation.mode == "fixed_template"
    assert response.diagnostics_public.sources[0].document_count == 4


def test_app_provider_failure_uses_stable_red_fallback_and_mode() -> None:
    response = _response()
    transport = FakeTransport(response)
    app = AppTest.from_function(_app, args=(transport,)).run()

    app.text_area[0].input("삼성전자 최근 뉴스")
    submit = next(
        item
        for item in app.button
        if item.key.startswith("FormSubmitter:chat_form-")
    )
    submit.click()
    app.run()

    assert not app.exception
    assert response.status == "provider_failed"
    assert app.error
    assert any(
        "자료 제공 상태를 확인하지 못해 답변을 보류합니다."
        in item.value
        for item in app.error
    )
    captions = "\n".join(item.value for item in app.caption)
    assert "상태: 자료 제공 실패" in captions
    assert "자료 모드: 자료 미연결" in captions
    visible_text = "\n".join(item.value for item in app.text)
    assert "자료 제공 경로가 구성되지 않았거나 이용 불가" in visible_text
    assert "provider_unavailable" not in visible_text


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

    app.text_area[0].input("PER이 뭐야?")
    submit = next(
        item
        for item in app.button
        if item.key.startswith("FormSubmitter:chat_form-")
    )
    submit.click()
    app.run()

    assert not app.exception
    assert any(
        "<script>alert('display-only')</script>" == item.value
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

    app.text_area[0].input("PER이 뭐야?")
    submit = next(
        item
        for item in app.button
        if item.key.startswith("FormSubmitter:chat_form-")
    )
    submit.click()
    app.run()

    assert not app.exception
    visible_text = "\n".join(item.value for item in app.text)
    assert "/tmp" not in visible_text
    assert "[공식](https://unapproved.example)" in visible_text
    assert "![이미지](https://unapproved.example)" in visible_text
    links = app.get("link_button")
    assert len(links) == 1
    assert links[0].proto.label == "원문 보기"
    assert links[0].proto.url == "https://approved.example/source"
    assert all(
        "unapproved.example" not in item.value
        for item in app.markdown
    )


def test_app_keeps_session_across_turns_and_reset_creates_isolated_id() -> None:
    transport = FakeTransport(_response())
    app = AppTest.from_function(_app, args=(transport,)).run()

    app.text_area[0].input("삼성전자 최근 뉴스")
    submit = next(
        item
        for item in app.button
        if item.key.startswith("FormSubmitter:chat_form-")
    )
    submit.click()
    app.run()
    first_session_id = transport.requests[-1].session_id

    app.text_area[0].input("그럼 위험 요인은?")
    submit = next(
        item
        for item in app.button
        if item.key.startswith("FormSubmitter:chat_form-")
    )
    submit.click()
    app.run()

    assert transport.requests[-1].session_id == first_session_id
    reset = next(item for item in app.button if item.key == "reset_session")
    reset.click()
    app.run()
    assert not app.subheader

    app.text_area[0].input("그럼 위험 요인은?")
    submit = next(
        item
        for item in app.button
        if item.key.startswith("FormSubmitter:chat_form-")
    )
    submit.click()
    app.run()

    assert transport.requests[-1].session_id != first_session_id
    assert transport.requests[-1].session_id.startswith("anonymous-")


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

    app.text_area[0].input("삼성전자 여러 자료 요약")
    submit = next(
        item
        for item in app.button
        if item.key.startswith("FormSubmitter:chat_form-")
    )
    submit.click()
    app.run()

    assert not app.exception
    labels = "\n".join(item.value for item in app.markdown)
    for label in ("긍정 요인", "확인된 위험", "더 확인할 것"):
        assert label in labels
    captions = "\n".join(item.value for item in app.caption)
    for label in ("뉴스", "공시", "리서치 리포트"):
        assert label in captions
    links = app.get("link_button")
    assert len(links) == 2
    assert any(item.label == "분석 과정 보기" for item in app.expander)


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
