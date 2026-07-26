from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from app.api.main import app
from app.api.schemas import ChatRequest, ChatResponse
from app.runtime import get_runtime_state


@pytest.fixture(autouse=True)
def _recorded_runtime(monkeypatch):
    monkeypatch.setenv("QUESTOCK_SOURCE_MODE", "recorded")
    get_runtime_state.cache_clear()
    yield
    get_runtime_state.cache_clear()


def _post(
    client: TestClient,
    message: str,
    *,
    session_id: str,
) -> dict[str, Any]:
    response = client.post(
        "/api/chat",
        json={"message": message, "session_id": session_id},
    )
    assert response.status_code == 200
    return response.json()


def test_recorded_api_health_and_two_turn_anonymous_session() -> None:
    with TestClient(app) as client:
        health = client.get("/health")
        first = _post(
            client,
            "삼성전자 최근 이슈 요약",
            session_id="anonymous-b9-two-turn",
        )
        follow_up = _post(
            client,
            "그럼 위험 요인은?",
            session_id="anonymous-b9-two-turn",
        )

    assert health.status_code == 200
    assert health.json()["basis_at"] == "2026-07-26T00:00:00Z"
    assert first["status"] == "complete"
    assert first["basis_date"] == "2026-07-26"
    assert first["diagnostics_public"]["data_mode"] == "recorded"
    assert first["diagnostics_public"]["live_connectivity_checked"] is False
    assert first["diagnostics_public"]["query_plan"]["intent"] == "recent_issue"
    assert first["evidence"][0]["source_type"] == "news"
    assert "session_id" not in first
    assert follow_up["status"] == "partial"
    assert follow_up["security"]["ticker"] == "005930"
    assert (
        follow_up["diagnostics_public"]["query_plan"]["intent"]
        == "risk_factors"
    )
    assert follow_up["evidence"][0]["source_type"] == "research_report"
    assert "session_id" not in follow_up


def test_recorded_glossary_and_verified_disclosure_body_facts() -> None:
    with TestClient(app) as client:
        glossary = _post(
            client,
            "PER이 뭐야?",
            session_id="anonymous-b9-glossary",
        )
        disclosure = _post(
            client,
            "삼성전자 최근 공시 핵심",
            session_id="anonymous-b9-disclosure",
        )

    assert glossary["status"] == "complete"
    assert glossary["diagnostics_public"]["data_mode"] == "recorded"
    assert glossary["evidence"][0]["source_type"] == "glossary"
    assert disclosure["status"] == "partial"
    assert disclosure["evidence"][0]["document_id"] == (
        "disclosure:20260515002181"
    )
    assert disclosure["evidence"][0]["locator"] == {
        "provider": "recorded_demo",
        "content_origin": "verified_public_recorded",
        "receipt_no": "20260515002181",
        "viewer_url": (
            "https://dart.fss.or.kr/dsaf001/main.do"
            "?rcpNo=20260515002181"
        ),
        "content_level": "verified_body_facts",
        "section": "verified body facts",
        "facts": [
            {
                "fact": "연결 매출",
                "value": "133,873,444",
                "unit": "백만원",
                "physical_pdf_page": 53,
                "dart_printed_page": 50,
                "section": "연결 매출",
            },
            {
                "fact": "연결 영업이익",
                "value": "57,232,797",
                "unit": "백만원",
                "physical_pdf_page": 53,
                "dart_printed_page": 50,
                "section": "연결 영업이익",
            },
            {
                "fact": "DS 부문 매출",
                "value": "817,156",
                "unit": "억원",
                "physical_pdf_page": 52,
                "dart_printed_page": 49,
                "section": "DS 부문 매출",
            },
            {
                "fact": "DS 부문 영업이익",
                "value": "536,633",
                "unit": "억원",
                "physical_pdf_page": 52,
                "dart_printed_page": 49,
                "section": "DS 부문 영업이익",
            },
            {
                "fact": "시설투자 합계",
                "value": "112,332",
                "unit": "억원",
                "physical_pdf_page": 16,
                "dart_printed_page": 13,
                "section": "시설투자 합계",
            },
            {
                "fact": "HBM4 관련 사실",
                "value": "1c D램·4나노 베이스 다이 적용 HBM4 양산 출하",
                "unit": None,
                "physical_pdf_page": 31,
                "dart_printed_page": 28,
                "section": "HBM4 관련 사실",
            },
        ],
    }
    answer_text = json.dumps(
        disclosure["answer_sections"],
        ensure_ascii=False,
    )
    assert "연결 매출 133,873,444백만원" in answer_text
    assert "연결 영업이익 57,232,797백만원" in answer_text
    assert "DS 부문 매출 817,156억원" in answer_text
    assert "DS 부문 영업이익 536,633억원" in answer_text
    assert "시설투자 합계 112,332억원" in answer_text
    assert "1c D램·4나노 베이스 다이 적용 HBM4 양산 출하" in answer_text
    assert "insufficient_disclosure_coverage" in disclosure["warnings"]


def test_wrong_company_no_data_and_blocked_advice_do_not_leak_receipt() -> None:
    with TestClient(app) as client:
        wrong_company = _post(
            client,
            "SK하이닉스 최근 공시 요약",
            session_id="anonymous-b9-wrong-company",
        )
        blocked = _post(
            client,
            "삼성전자 지금 매수해야 해?",
            session_id="anonymous-b9-blocked",
        )

    assert wrong_company["status"] == "no_evidence"
    assert wrong_company["evidence"] == []
    assert wrong_company["diagnostics_public"]["sources"] == [
        {
            "source_type": "disclosure",
            "provider_status": "no_data",
            "document_count": 0,
            "from_cache": False,
        }
    ]
    assert "20260515002181" not in str(wrong_company)
    assert blocked["status"] == "blocked"
    assert blocked["evidence"] == []
    assert blocked["diagnostics_public"]["data_mode"] == "recorded"
    assert (
        blocked["diagnostics_public"]["live_connectivity_checked"] is False
    )
    assert (
        blocked["diagnostics_public"]["generation"]["mode"]
        == "blocked"
    )


class _RecordedTransport:
    def __init__(self, response: ChatResponse) -> None:
        self.response = response
        self.requests: list[ChatRequest] = []

    def send(
        self,
        request: ChatRequest,
        timeout_seconds: float,
    ) -> ChatResponse:
        self.requests.append(request)
        return self.response.model_copy(deep=True)


def _streamlit_app(transport: "_RecordedTransport") -> None:
    from app.ui.app import run

    run(transport)


def test_streamlit_renders_recorded_answer_and_process_visibility() -> None:
    with TestClient(app) as client:
        payload = _post(
            client,
            "삼성전자 최근 이슈 요약",
            session_id="anonymous-b9-streamlit-source",
        )
    transport = _RecordedTransport(ChatResponse.model_validate(payload))
    rendered = AppTest.from_function(
        _streamlit_app,
        args=(transport,),
    ).run()

    rendered.text_area[0].input("삼성전자 최근 이슈 요약")
    submit = next(
        item
        for item in rendered.button
        if item.key.startswith("FormSubmitter:chat_form-")
    )
    submit.click()
    rendered.run()

    assert not rendered.exception
    assert len(transport.requests) == 1
    captions = "\n".join(item.value for item in rendered.caption)
    visible_text = "\n".join(item.value for item in rendered.text)
    assert "자료 모드: 기록 자료" in captions
    assert "고정 데모 자료 · 실시간 연결 아님" in captions
    assert "기준일: 2026-07-26" in captions
    assert "확인 안 함" in captions
    assert "자료 성격: Questock 작성 요약" in visible_text
    assert "선택 근거:" in visible_text
    assert "AI 상태:" in visible_text
