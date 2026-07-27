from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.api.schemas import ChatRequest
from app.core.models import SessionContext
from app.core.resolver import security_id_for
from app.planning.query_planner import QueryPlanner
from app.runtime import RuntimeConfig, build_runtime
from app.services.service_snapshot import SERVICE_SNAPSHOT_ID

FIXTURE_PATH = Path(
    "tests/fixtures/service_acceptance/fsc4_beginner_qa_v1.json"
)


def _fixture() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _everyday_cases(payload: dict[str, object]) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for security in payload["securities"]:
        for focus_group in payload["focus_templates"]:
            for template in focus_group["templates"]:
                output.append(
                    {
                        "question": template.format(
                            company=security["name"]
                        ),
                        "security_id": security["security_id"],
                        "focus": focus_group["focus"],
                        "intent": focus_group["intent"],
                    }
                )
    return output


def test_fsc4_fixture_expands_to_exact_120_case_inventory() -> None:
    payload = _fixture()
    everyday = _everyday_cases(payload)
    follow_ups = payload["follow_ups"]
    boundaries = payload["boundary_cases"]

    assert payload["schema_version"] == 1
    assert payload["fixture_id"] == "fsc4_beginner_qa_v1"
    assert payload["snapshot_id"] == SERVICE_SNAPSHOT_ID
    assert len(everyday) == 90
    assert len(follow_ups) == 15
    assert len(boundaries) == 15
    assert len({item["question"] for item in everyday}) == 90
    assert len(everyday) + len(follow_ups) + len(boundaries) == 120


def test_all_90_everyday_questions_reach_the_expected_grounded_route() -> None:
    planner = QueryPlanner()

    for case in _everyday_cases(_fixture()):
        plan = planner.plan(case["question"])

        assert security_id_for(plan.security) == case["security_id"], case
        allowed_intents = {case["intent"]}
        if case["focus"] in {"outlook", "balanced"}:
            allowed_intents.add("risk_factors")
        assert plan.intent in allowed_intents, case
        assert plan.answer_focus == case["focus"], case
        assert plan.requires_clarification is False
        assert plan.required_sources


def test_all_15_follow_ups_keep_company_context_and_new_focus() -> None:
    planner = QueryPlanner()
    payload = _fixture()
    session = SessionContext(
        current_security_id="KRX:005930",
        previous_intent="multi_source_summary",
        previous_source_types=[
            "news",
            "disclosure",
            "research_report",
        ],
    )

    for case in payload["follow_ups"]:
        plan = planner.plan(case["question"], session=session)

        assert security_id_for(plan.security) == "KRX:005930", case
        assert plan.answer_focus == case["focus"], case
        assert plan.requires_clarification is False


def test_all_15_boundary_questions_keep_safety_and_m5_limits() -> None:
    planner = QueryPlanner()

    for case in _fixture()["boundary_cases"]:
        plan = planner.plan(case["question"])

        assert plan.intent == case["intent"], case


def test_recorded_runtime_has_usable_evidence_for_all_90_everyday_questions() -> None:
    state = build_runtime(
        config=RuntimeConfig(
            source_mode="recorded",
            snapshot_id=SERVICE_SNAPSHOT_ID,
        )
    )

    async def run_cases() -> list[tuple[dict[str, str], object]]:
        results = []
        for index, case in enumerate(_everyday_cases(_fixture()), start=1):
            response = await state.chat_service.chat(
                ChatRequest(
                    message=case["question"],
                    session_id=f"fsc4-everyday-{index:03d}",
                )
            )
            results.append((case, response))
        return results

    for case, response in asyncio.run(run_cases()):
        assert response.status in {"complete", "partial"}, case
        assert response.evidence, case
        assert response.answer_sections.summary, case
        assert all(
            item.source_type
            in {"news", "disclosure", "research_report"}
            for item in response.evidence
        )
