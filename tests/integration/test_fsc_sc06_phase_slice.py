from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from app.api.main import app
from app.api.schemas import ChatRequest, ChatResponse
from app.answer import composer as composer_module
from app.evidence.freshness import SEOUL_TZ
from app.runtime import get_runtime_state
from app.services import chat_service as chat_service_module
from app.services.planning_observation import build_observed_query_plan
from app.services.service_acceptance import (
    ServiceAcceptanceResultError,
    load_service_acceptance_fixture,
    validate_service_acceptance_response,
)

_ACCEPTANCE_FIXTURE_PATH = Path(
    "tests/fixtures/service_acceptance/fsc_v1.json"
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
        del timeout_seconds
        self.requests.append(request)
        return self.response.model_copy(deep=True)


def _streamlit_app(transport) -> None:
    from app.ui.app import run

    run(transport)


def _acceptance_pipeline(case):
    state = get_runtime_state()
    assert state.corpus is not None
    basis_at = state.corpus.basis_at
    observed = build_observed_query_plan(
        case.question,
        basis_date=basis_at.astimezone(SEOUL_TZ).date(),
        resolver=state.chat_service._resolver,  # noqa: SLF001
        session=None,
    )
    gateway = asyncio.run(
        state.chat_service._source_gateway.fetch(  # noqa: SLF001
            observed.plan,
            query=case.question,
            timeout_seconds=1,
        )
    )
    pipeline = chat_service_module._run_evidence_pipeline(
        query=case.question,
        plan=observed.plan,
        gateway=gateway,
        basis_at=basis_at,
    )
    return state, observed.plan, pipeline


@pytest.fixture(autouse=True)
def _recorded_fixed_runtime(monkeypatch):
    monkeypatch.setenv("QUESTOCK_SOURCE_MODE", "recorded")
    monkeypatch.setenv("QUESTOCK_SNAPSHOT_ID", "svc-20260724-1402")
    monkeypatch.setenv("QUESTOCK_LLM_MODE", "disabled")
    get_runtime_state.cache_clear()
    yield
    get_runtime_state.cache_clear()


@pytest.mark.parametrize(
    ("question", "security_id"),
    [
        ("삼성전자 최근 이슈 요약", "KRX:005930"),
        ("SK하이닉스 최근 이슈 요약", "KRX:000660"),
        ("현대차 최근 이슈 요약", "KRX:005380"),
    ],
)
def test_three_company_recorded_api_and_ui_flow(
    question: str,
    security_id: str,
) -> None:
    with TestClient(app) as client:
        api_response = client.post(
            "/api/chat",
            json={
                "message": question,
                "session_id": f"fsc-sc06-{security_id[-6:]}",
            },
        )

    assert api_response.status_code == 200
    payload: dict[str, Any] = api_response.json()
    assert payload["status"] == "complete"
    assert payload["basis_date"] == "2026-07-24"
    assert (
        f"{payload['security']['market']}:{payload['security']['ticker']}"
        == security_id
    )
    assert payload["diagnostics_public"]["data_mode"] == "recorded"
    assert payload["diagnostics_public"]["live_connectivity_checked"] is False
    assert payload["diagnostics_public"]["generation"]["mode"] == (
        "fixed_template"
    )
    assert payload["evidence"]
    assert {
        item["source_type"] for item in payload["evidence"]
    } == {"news"}

    transport = _RecordedTransport(ChatResponse.model_validate(payload))
    rendered = AppTest.from_function(
        _streamlit_app,
        args=(transport,),
    ).run()
    rendered.run()
    assert transport.requests == []

    rendered.chat_input[0].set_value(question).run()

    assert not rendered.exception
    assert len(transport.requests) == 1
    assert not rendered.selectbox
    captions = "\n".join(item.value for item in rendered.caption)
    assert "Snapshot ID: svc-20260724-1402" in captions
    assert "기준 시점: 2026-07-24 14:02 KST" in captions
    assert "현재 답변 생성: 근거 기반 고정 응답" in captions


def test_exact_fifteen_cases_pass_fixed_acceptance_without_external_calls() -> None:
    fixture = load_service_acceptance_fixture(
        _ACCEPTANCE_FIXTURE_PATH
    )
    observed_eligibility: list[bool] = []

    for case in fixture.cases:
        state, plan, pipeline = _acceptance_pipeline(case)
        eligible = state.chat_service._composer.llm_eligible(  # noqa: SLF001
            plan=plan,
            selected_evidence=pipeline.budget.evidence,
            documents_by_id=pipeline.documents_by_id,
        )
        observed_eligibility.append(eligible)
        assert eligible is case.llm_eligible

        response = asyncio.run(
            state.chat_service.chat(
                ChatRequest(
                    message=case.question,
                    session_id=case.session_id,
                )
            )
        )
        validated = validate_service_acceptance_response(
            case,
            response,
        )
        assert validated.status in case.allowed_statuses
        assert (
            tuple(
                validated.diagnostics_public.decision.satisfied_sources
            )
            == case.required_evidence_sources
        )

        if case.expected_intent == "recent_issue":
            assert validated.status == "complete"
            assert {
                item.source_type for item in validated.evidence
            } == {"news"}
        if case.expected_intent in {
            "risk_factors",
            "multi_source_summary",
        }:
            assert validated.status == "partial"
            assert {
                item.source_type for item in validated.evidence
            } == {
                "news",
                "disclosure",
                "research_report",
            }

    assert sum(observed_eligibility) == 12
    final = fixture.cases[-1]
    _, final_plan, final_pipeline = _acceptance_pipeline(final)
    assert final_plan.date_range is not None
    assert final_plan.date_range.start.isoformat() == "2025-01-01"
    assert final_plan.date_range.end.isoformat() == "2025-01-31"
    assert final_pipeline.retrieval.status == "empty"
    assert final_pipeline.decision.status == "no_evidence"


def test_required_evidence_sources_use_policy_not_public_projection() -> None:
    case = load_service_acceptance_fixture(
        _ACCEPTANCE_FIXTURE_PATH
    ).cases[2]
    state = get_runtime_state()
    response = asyncio.run(
        state.chat_service.chat(
            ChatRequest(
                message=case.question,
                session_id="fsc-policy-sources",
            )
        )
    )
    payload = response.model_dump(mode="python")
    payload["evidence"] = payload["evidence"][:1]
    citation_bound_subset = ChatResponse.model_validate(payload)

    validated = validate_service_acceptance_response(
        case,
        citation_bound_subset,
    )

    assert len(validated.evidence) == 1
    assert (
        tuple(validated.diagnostics_public.decision.satisfied_sources)
        == case.required_evidence_sources
    )

    invalid_payload = response.model_dump(mode="python")
    invalid_payload["diagnostics_public"]["decision"][
        "satisfied_sources"
    ] = ["news", "disclosure"]
    invalid = ChatResponse.model_validate(invalid_payload)
    with pytest.raises(ServiceAcceptanceResultError):
        validate_service_acceptance_response(case, invalid)


def test_mixed_snapshot_projection_excludes_reports_from_llm_input() -> None:
    fixture = load_service_acceptance_fixture(
        _ACCEPTANCE_FIXTURE_PATH
    )
    mixed_cases = [
        case
        for case in fixture.cases
        if case.expected_intent
        in {"risk_factors", "multi_source_summary"}
    ]

    for case in mixed_cases:
        _, plan, pipeline = _acceptance_pipeline(case)
        eligible = composer_module._external_processing_eligible(
            pipeline.budget.evidence,
            pipeline.documents_by_id,
        )
        projected = composer_module._project_m3_evidence(
            plan,
            eligible,
        )

        assert projected
        assert {
            item.source_type for item in projected
        } == {"news", "disclosure"}
        assert all(
            item.source_type != "research_report"
            for item in projected
        )
