from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.api.schemas import ChatRequest
from app.runtime import RuntimeConfig, build_runtime
from scripts.evaluate_m5_e1_deepeval import (
    HELD_OUT_SCHEMA,
    METRIC_NAMES,
    PILOT_SCHEMA,
    _calibrate_threshold,
)
from scripts.evaluate_m5_e1_gemini_batch import (
    _calibrations,
    _inline_requests,
    _request_specs,
)

ROOT = Path(__file__).resolve().parents[2]
PILOT_PATH = ROOT / "tests/fixtures/evaluation/m5_e1_pilot_cases.json"
HELD_OUT_PATH = ROOT / "tests/fixtures/evaluation/m5_e1_held_out_cases.json"


def _payload(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_m5_e1_pilot_fixture_contract() -> None:
    payload = _payload(PILOT_PATH)

    assert payload["schema_version"] == PILOT_SCHEMA
    assert payload["metrics"] == list(METRIC_NAMES)
    cases = payload["cases"]
    assert isinstance(cases, list)
    assert len(cases) == 6
    assert len({case["case_id"] for case in cases}) == 6
    assert {case["quality_class"] for case in cases} == {
        "known_good",
        "borderline",
        "known_bad",
    }
    assert all(set(case["human_labels"]) == set(METRIC_NAMES) for case in cases)
    assert all(
        case["input"].strip()
        and case["actual_output"].strip()
        and case["retrieval_context"]
        for case in cases
    )


def test_m5_e1_held_out_fixture_contract() -> None:
    payload = _payload(HELD_OUT_PATH)

    assert payload["schema_version"] == HELD_OUT_SCHEMA
    cases = payload["cases"]
    assert isinstance(cases, list)
    assert len(cases) == 24
    assert len({case["case_id"] for case in cases}) == 24
    assert {
        category: sum(case["category"] == category for case in cases)
        for category in {
            "price",
            "price_move",
            "issue",
            "disclosure_report",
            "financial_term",
            "evidence_crosscheck",
            "multi_turn",
        }
    } == {
        "price": 4,
        "price_move": 4,
        "issue": 4,
        "disclosure_report": 3,
        "financial_term": 2,
        "evidence_crosscheck": 3,
        "multi_turn": 4,
    }
    assert all(
        case["question"].strip() and case["as_of"] and case["expected_intent"]
        for case in cases
    )
    assert sum(bool(case.get("setup_turns")) for case in cases) == 4


def test_threshold_calibration_prefers_no_false_pass() -> None:
    result = _calibrate_threshold(
        [
            (1.0, True),
            (0.9, True),
            (0.8, True),
            (0.6, False),
            (0.4, False),
            (0.2, False),
        ]
    )

    assert result["status"] == "REQUIRED"
    assert result["agreement_count"] == 6
    assert result["false_pass_count"] == 0
    assert result["threshold"] > 0.6


def test_held_out_expected_routes_match_recorded_runtime() -> None:
    payload = _payload(HELD_OUT_PATH)
    runtime = build_runtime(
        config=RuntimeConfig(
            source_mode="recorded",
            snapshot_id="svc-20260724-1402",
        )
    )

    for case in payload["cases"]:
        session_id = f"fixture-{case['case_id']}"
        for setup in case.get("setup_turns", []):
            asyncio.run(
                runtime.chat_service.chat(
                    ChatRequest(
                        message=setup["question"],
                        session_id=session_id,
                        as_of=setup["as_of"],
                    )
                )
            )
        response = asyncio.run(
            runtime.chat_service.chat(
                ChatRequest(
                    message=case["question"],
                    session_id=session_id,
                    as_of=case["as_of"],
                )
            )
        )
        security_id = (
            None
            if response.security is None
            else f"{response.security.market}:{response.security.ticker}"
        )

        assert (
            response.diagnostics_public.query_plan.intent == case["expected_intent"]
        ), case["case_id"]
        assert security_id == case["expected_security_id"], case["case_id"]


def test_m5_e1_batch_request_contract() -> None:
    pilot = _payload(PILOT_PATH)
    frozen = {
        "records": [
            {
                "case_id": case["case_id"],
                "judge_input": case["question"],
                "actual_output": "고정 답변",
                "retrieval_context": ["공개 근거 요약"],
            }
            for case in _payload(HELD_OUT_PATH)["cases"]
        ]
    }

    specs = _request_specs(pilot, frozen)
    requests = _inline_requests(specs)

    assert len(specs) == (6 + 24) * len(METRIC_NAMES)
    assert len(requests) == len(specs)
    assert {(spec["split"], spec["case_id"], spec["metric"]) for spec in specs} == {
        (
            split,
            case["case_id"],
            metric_name,
        )
        for split, cases in (
            ("pilot", pilot["cases"]),
            ("held_out", frozen["records"]),
        )
        for case in cases
        for metric_name in METRIC_NAMES
    }
    assert all(
        request["config"]["temperature"] == 0
        and request["config"]["response_mime_type"] == "application/json"
        and request["config"]["max_output_tokens"] == 2048
        for request in requests
    )


def test_batch_reuses_locked_pilot_thresholds() -> None:
    pilot = _payload(PILOT_PATH)
    pilot_results = {
        case["case_id"]: {
            metric_name: {
                "score": (
                    0.8
                    if metric_name == "beginner_usefulness"
                    else 1.0
                )
            }
            for metric_name in METRIC_NAMES
        }
        for case in pilot["cases"]
    }

    calibrations = _calibrations(pilot, pilot_results)

    assert calibrations["answer_relevancy"]["threshold"] == 0.3
    assert calibrations["faithfulness"]["threshold"] == 0.5
    assert calibrations["contextual_relevancy"]["threshold"] == 0.0
    assert calibrations["beginner_usefulness"]["threshold"] == 0.9
    assert calibrations["beginner_usefulness"]["status"] == "REQUIRED"
