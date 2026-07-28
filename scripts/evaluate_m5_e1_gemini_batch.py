from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

if __package__:
    from scripts.evaluate_m5_e1_deepeval import (
        HELD_OUT_PASS_RATE,
        METRIC_NAMES,
        _calibrate_threshold,
    )
else:
    from evaluate_m5_e1_deepeval import (  # type: ignore[no-redef]
        HELD_OUT_PASS_RATE,
        METRIC_NAMES,
        _calibrate_threshold,
    )

BATCH_MODEL = "gemini-3.1-pro-preview"
BATCH_SCHEMA = "m5-e1-gemini-pro-batch-v1"
BATCH_RESULT_SCHEMA = "m5-e1-gemini-pro-batch-result-v1"
RUBRIC_VERSION = "m5-e1-batch-rubric-v1"
MAX_OUTPUT_TOKENS = 768

_TERMINAL_STATES = {
    "JOB_STATE_SUCCEEDED",
    "JOB_STATE_FAILED",
    "JOB_STATE_CANCELLED",
    "JOB_STATE_EXPIRED",
    "JOB_STATE_PARTIALLY_SUCCEEDED",
}

_METRIC_RUBRICS = {
    "answer_relevancy": """
사용자 질문에 직접 답하는 정도를 평가한다.
- 질문의 핵심 요구를 먼저 다루면 높게 평가한다.
- 질문과 무관한 정보, 같은 정보 반복, 핵심을 피한 답변은 감점한다.
- 근거가 부족할 때 한계를 밝히거나 필요한 정보를 요청한 답변은
  짧다는 이유만으로 감점하지 않는다.
""".strip(),
    "faithfulness": """
답변의 사실 주장들이 제공된 근거 문맥으로 뒷받침되는지 평가한다.
- 외부 지식이나 이후 시점 정보는 사용하지 않는다.
- 근거에 없는 수치, 인과, 기업, 시점, 확정 표현이 있으면 감점한다.
- 근거와 추론을 구분하고 불확실성을 밝힌 경우 그 구분을 반영한다.
""".strip(),
    "contextual_relevancy": """
제공된 근거 문맥 자체가 사용자 질문에 필요한 정보를 담고 있는지 평가한다.
- 답변의 문장 품질이 아니라 질문과 근거 문맥의 관련성을 평가한다.
- 직접 근거를 우선하고, 배경 설명만 있거나 다른 기업 이야기면 감점한다.
- 빈 문맥은 관련 정보가 없는 것으로 평가한다.
""".strip(),
    "beginner_usefulness": """
주식 초보자가 답변을 이해하고 다음 확인점을 알 수 있는지 평가한다.
- 마지막 사용자 질문에 먼저 직접 답했는지 확인한다.
- 필요한 용어만 쉬운 말로 설명했는지 확인한다.
- 질문 난이도에 비례한 상세도인지 평가하고 길이 자체에는 가점하지 않는다.
- 근거의 한계와 불확실성을 필요한 경우 분명히 구분했는지 확인한다.
- 근거 없는 사실, 반복, 무관한 장황함은 감점한다.
""".strip(),
}


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("evaluation payload must be an object")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _prompt(
    metric_name: str,
    *,
    user_input: str,
    actual_output: str,
    retrieval_context: list[str],
) -> str:
    context = (
        "\n".join(f"- {item}" for item in retrieval_context)
        or "(제공된 근거 문맥 없음)"
    )
    return f"""당신은 한국 주식 질의응답 서비스의 품질 평가자입니다.
아래 자료만 사용해 지정된 지표 하나를 평가하세요.
세계 지식이나 현재 날짜의 외부 정보는 추가하지 마세요.

[평가 지표]
{metric_name}

[평가 기준]
{_METRIC_RUBRICS[metric_name]}

[사용자 질문]
{user_input}

[서비스 답변]
{actual_output}

[서비스가 실제 사용한 근거 문맥]
{context}

0점은 기준을 전혀 충족하지 못함, 10점은 완전히 충족함입니다.
정수 점수와 입력에 근거한 짧은 한국어 사유만 JSON으로 반환하세요."""


def _request_specs(
    pilot_fixture: dict[str, Any],
    frozen: dict[str, Any],
) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for split, cases in (
        ("pilot", pilot_fixture["cases"]),
        ("held_out", frozen["records"]),
    ):
        for case in cases:
            user_input = case["input"] if split == "pilot" else case["judge_input"]
            for metric_name in METRIC_NAMES:
                prompt = _prompt(
                    metric_name,
                    user_input=user_input,
                    actual_output=case["actual_output"],
                    retrieval_context=case["retrieval_context"],
                )
                specs.append(
                    {
                        "split": split,
                        "case_id": case["case_id"],
                        "metric": metric_name,
                        "prompt": prompt,
                        "prompt_sha256": hashlib.sha256(
                            prompt.encode("utf-8")
                        ).hexdigest(),
                    }
                )
    return specs


def _inline_requests(
    specs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    response_schema = {
        "type": "object",
        "properties": {
            "score": {
                "type": "integer",
                "minimum": 0,
                "maximum": 10,
            },
            "reason": {
                "type": "string",
                "minLength": 1,
                "maxLength": 800,
            },
        },
        "required": ["score", "reason"],
        "additionalProperties": False,
    }
    return [
        {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": spec["prompt"]}],
                }
            ],
            "metadata": {
                "split": spec["split"],
                "case_id": spec["case_id"],
                "metric": spec["metric"],
            },
            "config": {
                "response_mime_type": "application/json",
                "response_json_schema": response_schema,
                "temperature": 0,
                "max_output_tokens": MAX_OUTPUT_TOKENS,
                "thinking_config": {"thinking_level": "low"},
            },
        }
        for spec in specs
    ]


def _client() -> Any:
    load_dotenv(Path(".env"))
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    from google import genai

    return genai.Client(api_key=api_key)


def submit_batch(
    pilot_path: Path,
    frozen_path: Path,
    state_path: Path,
) -> dict[str, Any]:
    if state_path.exists():
        raise FileExistsError(
            "state file already exists; batch creation is not idempotent"
        )
    pilot = _read_json(pilot_path)
    frozen = _read_json(frozen_path)
    specs = _request_specs(pilot, frozen)
    client = _client()
    batch = client.batches.create(
        model=BATCH_MODEL,
        src={"inlined_requests": _inline_requests(specs)},
        config={
            "display_name": (
                f"questock-m5-e1-pro-batch-{datetime.now().astimezone():%Y%m%d-%H%M%S}"
            )
        },
    )
    payload = {
        "schema_version": BATCH_SCHEMA,
        "created_at": datetime.now().astimezone().isoformat(),
        "batch_name": batch.name,
        "batch_state": (None if batch.state is None else batch.state.value),
        "judge_model": BATCH_MODEL,
        "rubric_version": RUBRIC_VERSION,
        "temperature_requested": 0,
        "thinking_level": "low",
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "pilot_fixture_sha256": _sha256(pilot),
        "frozen_response_sha256": _sha256(frozen),
        "request_count": len(specs),
        "request_manifest": [
            {
                "split": spec["split"],
                "case_id": spec["case_id"],
                "metric": spec["metric"],
                "prompt_sha256": spec["prompt_sha256"],
            }
            for spec in specs
        ],
    }
    _write_json(state_path, payload)
    return payload


def batch_status(state_path: Path) -> dict[str, Any]:
    state = _read_json(state_path)
    client = _client()
    batch = client.batches.get(name=state["batch_name"])
    payload = {
        "batch_name": batch.name,
        "batch_state": (None if batch.state is None else batch.state.value),
        "done": batch.done,
        "error": (
            None
            if batch.error is None
            else {
                "code": batch.error.code,
                "message": batch.error.message,
            }
        ),
        "update_time": (
            None if batch.update_time is None else batch.update_time.isoformat()
        ),
    }
    state["last_status"] = payload
    _write_json(state_path, state)
    return payload


def _empty_results(
    manifest: list[dict[str, Any]],
) -> dict[str, dict[str, dict[str, Any]]]:
    results: dict[str, dict[str, dict[str, Any]]] = {}
    for item in manifest:
        results.setdefault(item["split"], {}).setdefault(
            item["case_id"],
            {},
        )[item["metric"]] = {
            "score": None,
            "reason": None,
            "error": "missing_batch_response",
        }
    return results


def _parse_responses(
    manifest: list[dict[str, Any]],
    responses: list[Any],
) -> dict[str, dict[str, dict[str, Any]]]:
    results = _empty_results(manifest)
    for item, response_item in zip(
        manifest,
        responses,
        strict=False,
    ):
        target = results[item["split"]][item["case_id"]][item["metric"]]
        if response_item.error is not None:
            target["error"] = f"provider_error:{response_item.error.code}"
            continue
        try:
            parsed = json.loads(response_item.response.text)
            raw_score = int(parsed["score"])
            reason = str(parsed["reason"]).strip()
            if not 0 <= raw_score <= 10 or not reason:
                raise ValueError("invalid score or reason")
        except (AttributeError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            target["error"] = "invalid_structured_response"
            continue
        target.update(
            {
                "score": raw_score / 10,
                "raw_score": raw_score,
                "reason": reason,
                "error": None,
            }
        )
    return results


def _calibrations(
    pilot_fixture: dict[str, Any],
    pilot_results: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    labels = {item["case_id"]: item["human_labels"] for item in pilot_fixture["cases"]}
    output = {}
    for metric_name in METRIC_NAMES:
        scored = []
        errors = []
        for case_id, metrics in pilot_results.items():
            metric = metrics[metric_name]
            if metric["score"] is None:
                errors.append(case_id)
            else:
                scored.append(
                    (
                        metric["score"],
                        labels[case_id][metric_name],
                    )
                )
        if errors or len(scored) != len(labels):
            output[metric_name] = {
                "threshold": None,
                "agreement_count": 0,
                "false_pass_count": None,
                "false_fail_count": None,
                "status": "REPORT_ONLY",
                "error_case_ids": errors,
            }
        else:
            output[metric_name] = _calibrate_threshold(scored)
    return output


def _aggregates(
    held_out_results: dict[str, dict[str, Any]],
    calibrations: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    output = {}
    total = len(held_out_results)
    for metric_name in METRIC_NAMES:
        scores = [
            metrics[metric_name]["score"]
            for metrics in held_out_results.values()
            if metrics[metric_name]["score"] is not None
        ]
        errors = [
            case_id
            for case_id, metrics in held_out_results.items()
            if metrics[metric_name]["score"] is None
        ]
        threshold = calibrations[metric_name]["threshold"]
        pass_count = (
            sum(score >= threshold for score in scores) if threshold is not None else 0
        )
        pass_rate = pass_count / total if total else 0.0
        status = calibrations[metric_name]["status"]
        if status == "REQUIRED":
            status = (
                "PASS"
                if not errors
                and pass_rate >= HELD_OUT_PASS_RATE
                and scores
                and statistics.fmean(scores) >= threshold
                else "FAIL"
            )
        output[metric_name] = {
            "calibration_status": calibrations[metric_name]["status"],
            "threshold": threshold,
            "mean": (statistics.fmean(scores) if scores else None),
            "median": statistics.median(scores) if scores else None,
            "minimum": min(scores) if scores else None,
            "pass_count": pass_count,
            "pass_rate": pass_rate,
            "error_case_ids": errors,
            "status": status,
        }
    return output


def collect_batch(
    state_path: Path,
    pilot_path: Path,
    hard_gate_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    state = _read_json(state_path)
    pilot = _read_json(pilot_path)
    hard_gate = _read_json(hard_gate_path)
    client = _client()
    batch = client.batches.get(name=state["batch_name"])
    batch_state = None if batch.state is None else batch.state.value
    if batch_state not in _TERMINAL_STATES:
        raise RuntimeError(f"batch is not complete: {batch_state}")
    if batch_state not in {
        "JOB_STATE_SUCCEEDED",
        "JOB_STATE_PARTIALLY_SUCCEEDED",
    }:
        raise RuntimeError(f"batch ended without results: {batch_state}")
    responses = (
        []
        if batch.dest is None or batch.dest.inlined_responses is None
        else batch.dest.inlined_responses
    )
    results = _parse_responses(
        state["request_manifest"],
        responses,
    )
    calibrations = _calibrations(pilot, results["pilot"])
    aggregates = _aggregates(
        results["held_out"],
        calibrations,
    )
    required = [
        item for item in aggregates.values() if item["calibration_status"] == "REQUIRED"
    ]
    generic_status = (
        "REPORT_ONLY"
        if not required
        else "PASS"
        if all(item["status"] == "PASS" for item in required)
        else "FAIL"
    )
    overall = (
        "PASS"
        if hard_gate["overall_status"] == "PASS" and generic_status == "PASS"
        else "FAIL"
    )
    payload = {
        "schema_version": BATCH_RESULT_SCHEMA,
        "created_at": datetime.now().astimezone().isoformat(),
        "batch_name": state["batch_name"],
        "batch_state": batch_state,
        "judge_model": state["judge_model"],
        "rubric_version": state["rubric_version"],
        "request_count": state["request_count"],
        "response_count": len(responses),
        "pilot_case_count": len(results["pilot"]),
        "held_out_case_count": len(results["held_out"]),
        "hard_gate_status": hard_gate["overall_status"],
        "calibrations": calibrations,
        "aggregates": aggregates,
        "generic_metrics_status": generic_status,
        "overall_status": overall,
        "results": results,
        "limitations": [
            "Gemini Batch G-Eval형 rubric 결과이며 기존 DeepEval built-in partial 점수와 혼합하지 않는다.",
            "LLM judge는 결정론적 금융 hard gate를 대체하지 않는다.",
            "judge와 generator가 모두 Gemini 계열이므로 계열 편향 가능성이 있다.",
            "raw judge reason은 Git ignored 로컬 artifact에만 보관한다.",
        ],
        "raw_artifact_committed": False,
    }
    _write_json(output_path, payload)
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the M5-E1 Gemini Pro Batch cross-evaluation."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    submit = subparsers.add_parser("submit")
    submit.add_argument("--pilot", type=Path, required=True)
    submit.add_argument("--frozen", type=Path, required=True)
    submit.add_argument("--state", type=Path, required=True)

    status = subparsers.add_parser("status")
    status.add_argument("--state", type=Path, required=True)

    collect = subparsers.add_parser("collect")
    collect.add_argument("--state", type=Path, required=True)
    collect.add_argument("--pilot", type=Path, required=True)
    collect.add_argument("--hard-gate", type=Path, required=True)
    collect.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "submit":
        payload = submit_batch(args.pilot, args.frozen, args.state)
        print(
            json.dumps(
                {
                    "batch_name": payload["batch_name"],
                    "batch_state": payload["batch_state"],
                    "request_count": payload["request_count"],
                },
                sort_keys=True,
            )
        )
        return 0
    if args.command == "status":
        print(json.dumps(batch_status(args.state), sort_keys=True))
        return 0
    payload = collect_batch(
        args.state,
        args.pilot,
        args.hard_gate,
        args.output,
    )
    print(
        json.dumps(
            {
                "overall_status": payload["overall_status"],
                "generic_metrics_status": payload["generic_metrics_status"],
                "aggregates": payload["aggregates"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if payload["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
