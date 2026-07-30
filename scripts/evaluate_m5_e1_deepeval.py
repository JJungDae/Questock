from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import re
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.api.schemas import ChatRequest, ChatResponse  # noqa: E402
from app.runtime import RuntimeConfig, build_runtime  # noqa: E402
from scripts.evaluate_m5_d1_event_grouping import (  # noqa: E402
    evaluate_event_pairs,
)

PILOT_SCHEMA = "m5-e1-pilot-v1"
HELD_OUT_SCHEMA = "m5-e1-held-out-v1"
FROZEN_SCHEMA = "m5-e1-frozen-responses-v1"
PILOT_RESULT_SCHEMA = "m5-e1-pilot-result-v1"
HELD_OUT_RESULT_SCHEMA = "m5-e1-held-out-result-v1"
HARD_GATE_SCHEMA = "m5-e1-hard-gate-result-v1"
SUMMARY_SCHEMA = "m5-e1-sanitized-summary-v1"
METRIC_NAMES = (
    "answer_relevancy",
    "faithfulness",
    "contextual_relevancy",
    "beginner_usefulness",
)
JUDGE_MODEL = "gemini-3.1-pro-preview"
DEEPEVAL_VERSION = "4.1.4"
MAX_JUDGE_OUTPUT_TOKENS = 4096
HELD_OUT_PASS_RATE = 0.80
HUMAN_AGREEMENT_MINIMUM = 5
_ADVICE_PATTERN = re.compile(
    r"(?:매수|매도|손절|익절)(?:하세요|해야|해라|추천)"
)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("evaluation payload must be an object")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _sha256(value: object) -> str:
    serialized = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _load_project_env() -> None:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
    if not os.getenv("GEMINI_API_KEY"):
        raise RuntimeError("GEMINI_API_KEY is missing")
    if not os.getenv("LLM_API_KEY"):
        os.environ["LLM_API_KEY"] = os.environ["GEMINI_API_KEY"]


def _configure_deepeval() -> None:
    os.environ["DEEPEVAL_DISABLE_DOTENV"] = "1"
    os.environ["DEEPEVAL_DISABLE_LEGACY_KEYFILE"] = "1"
    os.environ["DEEPEVAL_TELEMETRY_OPT_OUT"] = "1"
    os.environ["DEEPEVAL_FILE_SYSTEM"] = "READ_ONLY"
    os.environ["DEEPEVAL_RETRY_MAX_ATTEMPTS"] = "1"
    os.environ["DEEPEVAL_PER_ATTEMPT_TIMEOUT_SECONDS_OVERRIDE"] = "120"
    os.environ["DEEPEVAL_PER_TASK_TIMEOUT_SECONDS_OVERRIDE"] = "300"
    os.environ["DEEPEVAL_NO_INSPECT_PROMPT"] = "1"
    os.environ.pop("CONFIDENT_API_KEY", None)


def _answer_text(response: ChatResponse) -> str:
    sections = response.answer_sections
    ordered = (
        ("요약", sections.summary),
        ("확인된 사실", sections.facts),
        ("해석", sections.interpretation),
        ("추론", sections.inference),
        ("긍정 요인", sections.positive_factors),
        ("위험 요인", sections.risk_factors),
        ("불확실성", sections.uncertainty),
    )
    blocks: list[str] = []
    for label, values in ordered:
        if values:
            blocks.append(
                f"[{label}]\n" + "\n".join(value.strip() for value in values)
            )
    if not blocks:
        raise ValueError("response has no public answer text")
    return "\n\n".join(blocks)


def _retrieval_context(response: ChatResponse) -> list[str]:
    contexts: list[str] = []
    snapshot = response.market_snapshot
    if snapshot is not None:
        contexts.append(
            "시장 스냅샷: "
            f"기준 {snapshot.requested_as_of.isoformat()}, "
            f"관측 {snapshot.observed_at.isoformat()}, "
            f"가격 {snapshot.price:.0f}원, "
            f"전일 종가 {snapshot.previous_close:.0f}원, "
            f"변동 {snapshot.change:.0f}원, "
            f"변동률 {snapshot.change_percent:.6f}%."
        )
    for evidence in response.evidence[:10]:
        published = (
            evidence.published_at.isoformat()
            if evidence.published_at is not None
            else "미상"
        )
        contexts.append(
            f"{evidence.source_type} | {evidence.title} | "
            f"published_at={published} | {evidence.snippet[:1200]}"
        )
    comparison = response.evidence_comparison
    if comparison is not None:
        contexts.append(
            "근거 대조: "
            f"{comparison.event_label}; 기사 {comparison.article_total_count}건; "
            "독립 원출처 확인 수 "
            f"{comparison.source_lineage_summary.confirmed_independent_count}건."
        )
        for source in comparison.article_sources[:8]:
            contexts.append(
                f"뉴스 제목 | {source.title} | "
                f"published_at={source.published_at.isoformat()}"
            )
        for item in comparison.common_facts:
            contexts.append(f"뉴스 공통 사실 | {item.text}")
        for item in comparison.different_interpretations:
            contexts.append(f"기사별 강조점 차이 | {item.text}")
        for item in comparison.report_perspectives:
            contexts.append(
                f"검증 리포트 관점 | {item.source.title} | {item.text}"
            )
        for item in comparison.disclosure_links:
            contexts.append(f"DART 연결 | {item.role} | {item.text}")
    if not contexts:
        contexts.append(
            "사용 가능한 근거가 없어 제한 또는 재질문 안내만 허용됩니다."
        )
    return contexts


def _judge_input(
    *,
    question: str,
    setup_history: list[dict[str, str]],
) -> str:
    if not setup_history:
        return question
    lines = ["다음 대화의 마지막 사용자 질문을 평가하세요."]
    for turn in setup_history:
        lines.append(f"사용자: {turn['question']}")
        lines.append(f"Questock: {turn['answer']}")
    lines.append(f"마지막 사용자 질문: {question}")
    return "\n".join(lines)


async def _generate_one_case(
    service: object,
    case: dict[str, Any],
) -> dict[str, Any]:
    session_id = f"m5-e1-{case['case_id']}"
    history: list[dict[str, str]] = []
    setup_records: list[dict[str, Any]] = []
    for index, setup in enumerate(case.get("setup_turns", []), start=1):
        request = ChatRequest(
            message=setup["question"],
            session_id=session_id,
            as_of=setup["as_of"],
        )
        started = time.perf_counter()
        response = await service.chat(request)  # type: ignore[attr-defined]
        answer = _answer_text(response)
        setup_records.append(
            {
                "turn": index,
                "question": setup["question"],
                "as_of": setup["as_of"],
                "answer_sha256": _sha256(answer),
                "status": response.status,
                "intent": response.diagnostics_public.query_plan.intent,
                "elapsed_seconds": round(
                    time.perf_counter() - started,
                    3,
                ),
            }
        )
        history.append(
            {
                "question": setup["question"],
                "answer": answer,
            }
        )
    request = ChatRequest(
        message=case["question"],
        session_id=session_id,
        as_of=case["as_of"],
    )
    started = time.perf_counter()
    response = await service.chat(request)  # type: ignore[attr-defined]
    elapsed = time.perf_counter() - started
    dumped = response.model_dump(mode="json")
    actual_output = _answer_text(response)
    context = _retrieval_context(response)
    judge_input = _judge_input(
        question=case["question"],
        setup_history=history,
    )
    return {
        "case_id": case["case_id"],
        "category": case["category"],
        "question": case["question"],
        "judge_input": judge_input,
        "as_of": case["as_of"],
        "setup_records": setup_records,
        "actual_output": actual_output,
        "retrieval_context": context,
        "response": dumped,
        "response_sha256": _sha256(dumped),
        "judge_payload_sha256": _sha256(
            {
                "input": judge_input,
                "actual_output": actual_output,
                "retrieval_context": context,
            }
        ),
        "elapsed_seconds": round(elapsed, 3),
    }


async def generate_frozen_responses(
    fixture_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    fixture = _read_json(fixture_path)
    if fixture.get("schema_version") != HELD_OUT_SCHEMA:
        raise ValueError("held-out fixture schema is invalid")
    _load_project_env()
    runtime = build_runtime(
        config=RuntimeConfig(
            source_mode="recorded",
            snapshot_id="svc-20260724-1402",
            llm_mode="gemini",
            request_protection_enabled=False,
            response_cache_enabled=False,
            hybrid_router_enabled=True,
        )
    )
    records = []
    started = time.perf_counter()
    for index, case in enumerate(fixture["cases"], start=1):
        record = await _generate_one_case(runtime.chat_service, case)
        records.append(record)
        generation = record["response"]["diagnostics_public"]["generation"]
        print(
            f"generated {index}/{len(fixture['cases'])} "
            f"{case['case_id']} status={record['response']['status']} "
            f"mode={generation['mode']}",
            flush=True,
        )
    payload = {
        "schema_version": FROZEN_SCHEMA,
        "created_at": datetime.now().astimezone().isoformat(),
        "fixture_sha256": _sha256(fixture),
        "generator_model": os.getenv("LLM_MODEL"),
        "generator_response_count": len(records),
        "setup_response_count": sum(
            len(record["setup_records"]) for record in records
        ),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "records": records,
    }
    _write_json(output_path, payload)
    return payload


def _security_id(response: dict[str, Any]) -> str | None:
    security = response.get("security")
    if not isinstance(security, dict):
        return None
    return f"{security.get('market')}:{security.get('ticker')}"


def _comparison_sources(comparison: dict[str, Any]) -> list[dict[str, Any]]:
    output = list(comparison.get("article_sources", []))
    for perspective in comparison.get("report_perspectives", []):
        source = perspective.get("source")
        if isinstance(source, dict):
            output.append(source)
    for disclosure in comparison.get("disclosure_links", []):
        source = disclosure.get("source")
        if isinstance(source, dict):
            output.append(source)
    return output


def _case_hard_gate(
    case: dict[str, Any],
    record: dict[str, Any],
) -> dict[str, Any]:
    response = record["response"]
    basis_at = datetime.fromisoformat(response["basis_at"])
    evidence = response.get("evidence", [])
    comparison = response.get("evidence_comparison")
    future_evidence = [
        item["evidence_id"]
        for item in evidence
        if item.get("published_at") is not None
        and datetime.fromisoformat(item["published_at"]) > basis_at
    ]
    future_comparison = []
    if isinstance(comparison, dict):
        future_comparison = [
            item["source_id"]
            for item in _comparison_sources(comparison)
            if datetime.fromisoformat(item["published_at"]) > basis_at
        ]
    expected_security = case.get("expected_security_id")
    wrong_company = []
    if expected_security is not None:
        for item in evidence:
            subjects = item.get("subject_security_ids", [])
            if subjects and expected_security not in subjects:
                wrong_company.append(item["evidence_id"])
    market = response.get("market_snapshot")
    expected_market = case.get("expected_market")
    market_match = expected_market is None and market is None
    if expected_market is not None and isinstance(market, dict):
        market_match = (
            math.isclose(
                float(market["price"]),
                float(expected_market["price"]),
                abs_tol=0.000001,
            )
            and market["observed_at"] == expected_market["observed_at"]
            and math.isclose(
                float(market["change_percent"]),
                float(expected_market["change_percent"]),
                abs_tol=0.000001,
            )
        )
    urls = [
        item["source_url"]
        for item in evidence
        if item.get("source_url") is not None
    ]
    if isinstance(comparison, dict):
        urls.extend(
            item["source_url"]
            for item in _comparison_sources(comparison)
            if item.get("source_url") is not None
        )
    structural_links_valid = all(
        isinstance(url, str)
        and url.startswith(("http://", "https://"))
        and "\\" not in url
        for url in urls
    )
    comparison_conservative = True
    if isinstance(comparison, dict):
        lineage = comparison["source_lineage_summary"]
        comparison_conservative = (
            lineage["confirmed_independent_count"] == 0
            and lineage["confirmed_republication_count"] == 0
            and all(
                item.get("corroboration_status") == "lineage_unknown"
                for item in comparison["common_facts"]
            )
        )
    expected_comparison = case.get("expected_comparison", False)
    citation_summary = response["diagnostics_public"]["citation"]
    public_claims_citation_covered = (
        citation_summary["claim_count"] == 0
        or (
            citation_summary["citation_count"]
            >= citation_summary["claim_count"]
            and bool(evidence)
        )
        or market is not None
    )
    checks = {
        "intent_match": (
            response["diagnostics_public"]["query_plan"]["intent"]
            == case["expected_intent"]
        ),
        "security_match": _security_id(response) == expected_security,
        "future_information_leakage_zero": not (
            future_evidence or future_comparison
        ),
        "wrong_company_evidence_zero": not wrong_company,
        "price_time_percent_match": market_match,
        "direct_investment_advice_zero": not _ADVICE_PATTERN.search(
            record["actual_output"]
        ),
        "public_claims_citation_covered": (
            public_claims_citation_covered
        ),
        "citation_links_structurally_valid": structural_links_valid,
        "comparison_lineage_conservative": comparison_conservative,
        "expected_comparison_present": (
            isinstance(comparison, dict) if expected_comparison else True
        ),
    }
    return {
        "case_id": case["case_id"],
        "passed": all(checks.values()),
        "checks": checks,
        "diagnostics": {
            "future_evidence_ids": future_evidence,
            "future_comparison_source_ids": future_comparison,
            "wrong_company_evidence_ids": wrong_company,
        },
    }


def run_hard_gates(
    fixture_path: Path,
    frozen_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    fixture = _read_json(fixture_path)
    frozen = _read_json(frozen_path)
    if fixture.get("schema_version") != HELD_OUT_SCHEMA:
        raise ValueError("held-out fixture schema is invalid")
    if frozen.get("schema_version") != FROZEN_SCHEMA:
        raise ValueError("frozen response schema is invalid")
    records = {
        item["case_id"]: item for item in frozen["records"]
    }
    case_results = [
        _case_hard_gate(case, records[case["case_id"]])
        for case in fixture["cases"]
    ]
    pairs = _read_json(ROOT / "tests/fixtures/m5_d1_event_pairs.json")
    grouping = evaluate_event_pairs(pairs)
    grouping_passed = (
        grouping["precision"] >= 0.90
        and grouping["false_positive"] == 0
    )
    payload = {
        "schema_version": HARD_GATE_SCHEMA,
        "fixture_sha256": _sha256(fixture),
        "frozen_response_sha256": _sha256(frozen),
        "case_count": len(case_results),
        "passed_case_count": sum(
            item["passed"] for item in case_results
        ),
        "failed_case_ids": [
            item["case_id"]
            for item in case_results
            if not item["passed"]
        ],
        "m5_d1_grouping": grouping,
        "m5_d1_grouping_passed": grouping_passed,
        "overall_status": (
            "PASS"
            if all(item["passed"] for item in case_results)
            and grouping_passed
            else "FAIL"
        ),
        "cases": case_results,
    }
    _write_json(output_path, payload)
    return payload


def _metric_factories(model: object) -> dict[str, object]:
    from deepeval.metrics import (
        AnswerRelevancyMetric,
        ContextualRelevancyMetric,
        FaithfulnessMetric,
        GEval,
    )
    from deepeval.test_case import SingleTurnParams

    common = {
        "threshold": None,
        "model": model,
        "include_reason": True,
        "async_mode": False,
        "verbose_mode": False,
    }
    return {
        "answer_relevancy": AnswerRelevancyMetric(**common),
        "faithfulness": FaithfulnessMetric(**common),
        "contextual_relevancy": ContextualRelevancyMetric(**common),
        "beginner_usefulness": GEval(
            name="Beginner Usefulness",
            evaluation_params=[
                SingleTurnParams.INPUT,
                SingleTurnParams.ACTUAL_OUTPUT,
                SingleTurnParams.RETRIEVAL_CONTEXT,
            ],
            evaluation_steps=[
                "마지막 사용자 질문에 먼저 직접 답했는지 확인한다.",
                "주식 초보자에게 필요한 용어만 쉬운 말로 설명했는지 확인한다.",
                "질문 난이도에 비례한 상세도인지 평가하고 길이 자체에는 가점을 주지 않는다.",
                "근거의 한계와 불확실성을 필요한 경우 분명히 구분했는지 확인한다.",
                "근거 없는 사실 추가, 같은 정보 반복, 질문과 무관한 장황함을 감점한다.",
                "근거가 없을 때 적절히 제한하거나 재질문을 요청한 답변은 짧다는 이유로 감점하지 않는다.",
            ],
            threshold=None,
            model=model,
            async_mode=False,
            verbose_mode=False,
        ),
    }


def _judge_model() -> object:
    _configure_deepeval()
    _load_project_env()
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]
    from deepeval.models import GeminiModel

    class CountingGeminiModel(GeminiModel):
        def __init__(self, **kwargs: Any) -> None:
            self.logical_request_count = 0
            super().__init__(**kwargs)

        def generate(
            self,
            prompt: str,
            schema: object | None = None,
        ) -> object:
            self.logical_request_count += 1
            return super().generate(prompt, schema=schema)  # type: ignore[arg-type]

        async def a_generate(
            self,
            prompt: str,
            schema: object | None = None,
        ) -> object:
            self.logical_request_count += 1
            return await super().a_generate(  # type: ignore[arg-type]
                prompt,
                schema=schema,
            )

    return CountingGeminiModel(
        model=JUDGE_MODEL,
        temperature=0,
        generation_kwargs={
            "max_output_tokens": MAX_JUDGE_OUTPUT_TOKENS,
        },
    )


def _evaluate_cases(
    cases: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from deepeval.test_case import LLMTestCase

    model = _judge_model()
    output = []
    started = time.perf_counter()
    for case_index, case in enumerate(cases, start=1):
        test_case = LLMTestCase(
            input=case["input"],
            actual_output=case["actual_output"],
            retrieval_context=case["retrieval_context"],
        )
        metric_results: dict[str, Any] = {}
        for metric_name, metric in _metric_factories(model).items():
            metric_started = time.perf_counter()
            try:
                metric.measure(test_case)  # type: ignore[attr-defined]
                metric_results[metric_name] = {
                    "score": float(metric.score),  # type: ignore[attr-defined]
                    "reason": metric.reason,  # type: ignore[attr-defined]
                    "error": None,
                    "evaluation_cost": metric.evaluation_cost,  # type: ignore[attr-defined]
                    "input_tokens": metric.input_tokens,  # type: ignore[attr-defined]
                    "output_tokens": metric.output_tokens,  # type: ignore[attr-defined]
                    "elapsed_seconds": round(
                        time.perf_counter() - metric_started,
                        3,
                    ),
                }
            except Exception as exc:
                metric_results[metric_name] = {
                    "score": None,
                    "reason": None,
                    "error": type(exc).__name__,
                    "evaluation_cost": None,
                    "input_tokens": None,
                    "output_tokens": None,
                    "elapsed_seconds": round(
                        time.perf_counter() - metric_started,
                        3,
                    ),
                }
            print(
                f"judged {case_index}/{len(cases)} "
                f"{case['case_id']} {metric_name} "
                f"score={metric_results[metric_name]['score']} "
                f"error={metric_results[metric_name]['error']}",
                flush=True,
            )
        output.append(
            {
                "case_id": case["case_id"],
                "metrics": metric_results,
            }
        )
    usage = {
        "logical_provider_requests": model.logical_request_count,  # type: ignore[attr-defined]
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "input_tokens": sum(
            result["input_tokens"] or 0
            for item in output
            for result in item["metrics"].values()
        ),
        "output_tokens": sum(
            result["output_tokens"] or 0
            for item in output
            for result in item["metrics"].values()
        ),
        "reported_cost": sum(
            result["evaluation_cost"] or 0
            for item in output
            for result in item["metrics"].values()
        ),
    }
    return output, usage


def _calibrate_threshold(
    scored: list[tuple[float, bool]],
) -> dict[str, Any]:
    values = sorted({score for score, _ in scored})
    candidates = {0.0, 1.000001, *values}
    for left, right in zip(values, values[1:], strict=False):
        candidates.add((left + right) / 2)
    ranked = []
    for threshold in sorted(candidates):
        agreement = sum(
            (score >= threshold) is label for score, label in scored
        )
        false_pass = sum(
            score >= threshold and not label for score, label in scored
        )
        false_fail = sum(
            score < threshold and label for score, label in scored
        )
        ranked.append(
            (
                agreement,
                -false_pass,
                -false_fail,
                threshold,
                false_pass,
                false_fail,
            )
        )
    best = max(ranked)
    return {
        "threshold": round(best[3], 6),
        "agreement_count": best[0],
        "false_pass_count": best[4],
        "false_fail_count": best[5],
        "status": (
            "REQUIRED"
            if best[0] >= HUMAN_AGREEMENT_MINIMUM
            and best[4] == 0
            else "REPORT_ONLY"
        ),
    }


def evaluate_pilot(
    fixture_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    fixture = _read_json(fixture_path)
    if fixture.get("schema_version") != PILOT_SCHEMA:
        raise ValueError("pilot fixture schema is invalid")
    results, usage = _evaluate_cases(fixture["cases"])
    labels = {
        case["case_id"]: case["human_labels"]
        for case in fixture["cases"]
    }
    calibrations = {}
    for metric_name in METRIC_NAMES:
        metric_scores = []
        errors = []
        for result in results:
            metric = result["metrics"][metric_name]
            if metric["score"] is None:
                errors.append(result["case_id"])
                continue
            metric_scores.append(
                (
                    metric["score"],
                    labels[result["case_id"]][metric_name],
                )
            )
        if errors or len(metric_scores) != len(fixture["cases"]):
            calibrations[metric_name] = {
                "threshold": None,
                "agreement_count": 0,
                "false_pass_count": None,
                "false_fail_count": None,
                "status": "REPORT_ONLY",
                "error_case_ids": errors,
            }
        else:
            calibrations[metric_name] = _calibrate_threshold(
                metric_scores
            )
    payload = {
        "schema_version": PILOT_RESULT_SCHEMA,
        "deepeval_version": DEEPEVAL_VERSION,
        "judge_model": JUDGE_MODEL,
        "temperature": 0,
        "max_output_tokens": MAX_JUDGE_OUTPUT_TOKENS,
        "fixture_sha256": _sha256(fixture),
        "case_count": len(results),
        "usage": usage,
        "calibrations": calibrations,
        "results": results,
    }
    _write_json(output_path, payload)
    return payload


def evaluate_held_out(
    frozen_path: Path,
    pilot_result_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    frozen = _read_json(frozen_path)
    pilot = _read_json(pilot_result_path)
    if frozen.get("schema_version") != FROZEN_SCHEMA:
        raise ValueError("frozen response schema is invalid")
    if pilot.get("schema_version") != PILOT_RESULT_SCHEMA:
        raise ValueError("pilot result schema is invalid")
    cases = [
        {
            "case_id": item["case_id"],
            "input": item["judge_input"],
            "actual_output": item["actual_output"],
            "retrieval_context": item["retrieval_context"],
        }
        for item in frozen["records"]
    ]
    results, usage = _evaluate_cases(cases)
    aggregates = {}
    for metric_name in METRIC_NAMES:
        calibration = pilot["calibrations"][metric_name]
        scores = [
            item["metrics"][metric_name]["score"]
            for item in results
            if item["metrics"][metric_name]["score"] is not None
        ]
        errors = [
            item["case_id"]
            for item in results
            if item["metrics"][metric_name]["score"] is None
        ]
        threshold = calibration["threshold"]
        pass_count = (
            sum(score >= threshold for score in scores)
            if threshold is not None
            else 0
        )
        pass_rate = (
            pass_count / len(results) if results else 0.0
        )
        mean = statistics.fmean(scores) if scores else None
        metric_status = calibration["status"]
        if metric_status == "REQUIRED":
            metric_status = (
                "PASS"
                if not errors
                and pass_rate >= HELD_OUT_PASS_RATE
                and mean is not None
                and mean >= threshold
                else "FAIL"
            )
        aggregates[metric_name] = {
            "calibration_status": calibration["status"],
            "threshold": threshold,
            "mean": mean,
            "median": statistics.median(scores) if scores else None,
            "minimum": min(scores) if scores else None,
            "pass_count": pass_count,
            "pass_rate": pass_rate,
            "error_case_ids": errors,
            "status": metric_status,
        }
    required = [
        value
        for value in aggregates.values()
        if value["calibration_status"] == "REQUIRED"
    ]
    generic_status = (
        "REPORT_ONLY"
        if not required
        else "PASS"
        if all(item["status"] == "PASS" for item in required)
        else "FAIL"
    )
    payload = {
        "schema_version": HELD_OUT_RESULT_SCHEMA,
        "deepeval_version": DEEPEVAL_VERSION,
        "judge_model": JUDGE_MODEL,
        "temperature": 0,
        "max_output_tokens": MAX_JUDGE_OUTPUT_TOKENS,
        "frozen_response_sha256": _sha256(frozen),
        "pilot_result_sha256": _sha256(pilot),
        "case_count": len(results),
        "held_out_pass_rate_requirement": HELD_OUT_PASS_RATE,
        "usage": usage,
        "aggregates": aggregates,
        "generic_metrics_status": generic_status,
        "results": results,
    }
    _write_json(output_path, payload)
    return payload


def build_sanitized_summary(
    hard_gate_path: Path,
    pilot_path: Path,
    held_out_path: Path,
    output_path: Path,
    *,
    incomplete_reason: str | None = None,
) -> dict[str, Any]:
    hard = _read_json(hard_gate_path)
    pilot = _read_json(pilot_path)
    held_out = _read_json(held_out_path)
    if hard.get("schema_version") != HARD_GATE_SCHEMA:
        raise ValueError("hard gate result schema is invalid")
    if pilot.get("schema_version") != PILOT_RESULT_SCHEMA:
        raise ValueError("pilot result schema is invalid")
    if held_out.get("schema_version") != HELD_OUT_RESULT_SCHEMA:
        raise ValueError("held-out result schema is invalid")
    aggregates = json.loads(json.dumps(held_out["aggregates"]))
    required_errors = False
    for aggregate in aggregates.values():
        scored_count = held_out["case_count"] - len(
            aggregate["error_case_ids"]
        )
        aggregate["scored_case_count"] = scored_count
        aggregate["scored_pass_rate"] = (
            aggregate["pass_count"] / scored_count
            if scored_count
            else None
        )
        if (
            aggregate["calibration_status"] == "REQUIRED"
            and aggregate["error_case_ids"]
        ):
            aggregate["status"] = "PARTIAL"
            required_errors = True
    generic_status = (
        "PARTIAL"
        if required_errors
        else held_out["generic_metrics_status"]
    )
    overall = (
        "PASS"
        if hard["overall_status"] == "PASS"
        and generic_status == "PASS"
        else "PARTIAL"
        if hard["overall_status"] == "PASS"
        and generic_status == "PARTIAL"
        else "FAIL"
    )
    payload = {
        "schema_version": SUMMARY_SCHEMA,
        "created_at": datetime.now().astimezone().isoformat(),
        "deepeval_version": held_out["deepeval_version"],
        "judge_model": held_out["judge_model"],
        "generator_model": "gemini/gemini-3.5-flash",
        "pilot_case_count": pilot["case_count"],
        "held_out_case_count": held_out["case_count"],
        "hard_gate_status": hard["overall_status"],
        "hard_gate_passed_case_count": hard["passed_case_count"],
        "hard_gate_failed_case_ids": hard["failed_case_ids"],
        "m5_d1_grouping_precision": hard["m5_d1_grouping"]["precision"],
        "m5_d1_grouping_false_positive": hard["m5_d1_grouping"][
            "false_positive"
        ],
        "generic_metrics_status": generic_status,
        "raw_generic_metrics_status": held_out[
            "generic_metrics_status"
        ],
        "calibrations": pilot["calibrations"],
        "aggregates": aggregates,
        "judge_usage": {
            "pilot": pilot["usage"],
            "held_out": held_out["usage"],
        },
        "failed_metric_cases": {
            metric_name: [
                item["case_id"]
                for item in held_out["results"]
                if item["metrics"][metric_name]["score"] is None
                or (
                    held_out["aggregates"][metric_name]["threshold"]
                    is not None
                    and item["metrics"][metric_name]["score"]
                    < held_out["aggregates"][metric_name]["threshold"]
                )
            ]
            for metric_name in METRIC_NAMES
        },
        "overall_status": overall,
        "incomplete_reason": incomplete_reason,
        "limitations": [
            "LLM-as-a-judge 결과이며 결정론적 금융 hard gate를 대체하지 않는다.",
            "judge와 generator가 모두 Gemini 계열이므로 계열 편향 가능성이 있다.",
            "citation URL은 구조만 검사했으며 외부 페이지 HTTP 가용성은 검사하지 않았다.",
            "raw 답변과 judge reason은 Git ignored 로컬 artifact에만 보관한다.",
        ],
        "raw_artifact_committed": False,
        "pro_comparison_ready": overall == "PASS",
    }
    _write_json(output_path, payload)
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the bounded M5-E1 DeepEval evaluation.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate")
    generate.add_argument("--fixture", type=Path, required=True)
    generate.add_argument("--output", type=Path, required=True)

    hard_gate = subparsers.add_parser("hard-gate")
    hard_gate.add_argument("--fixture", type=Path, required=True)
    hard_gate.add_argument("--frozen", type=Path, required=True)
    hard_gate.add_argument("--output", type=Path, required=True)

    pilot = subparsers.add_parser("pilot")
    pilot.add_argument("--fixture", type=Path, required=True)
    pilot.add_argument("--output", type=Path, required=True)

    held_out = subparsers.add_parser("held-out")
    held_out.add_argument("--frozen", type=Path, required=True)
    held_out.add_argument("--pilot-result", type=Path, required=True)
    held_out.add_argument("--output", type=Path, required=True)

    summary = subparsers.add_parser("summary")
    summary.add_argument("--hard-gate", type=Path, required=True)
    summary.add_argument("--pilot-result", type=Path, required=True)
    summary.add_argument("--held-out-result", type=Path, required=True)
    summary.add_argument("--output", type=Path, required=True)
    summary.add_argument("--incomplete-reason")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "generate":
        payload = asyncio.run(
            generate_frozen_responses(args.fixture, args.output)
        )
        print(
            json.dumps(
                {
                    "schema_version": payload["schema_version"],
                    "generator_response_count": payload[
                        "generator_response_count"
                    ],
                    "setup_response_count": payload[
                        "setup_response_count"
                    ],
                    "elapsed_seconds": payload["elapsed_seconds"],
                },
                sort_keys=True,
            )
        )
        return 0
    if args.command == "hard-gate":
        payload = run_hard_gates(
            args.fixture,
            args.frozen,
            args.output,
        )
        print(
            json.dumps(
                {
                    "overall_status": payload["overall_status"],
                    "passed_case_count": payload["passed_case_count"],
                    "failed_case_ids": payload["failed_case_ids"],
                },
                sort_keys=True,
            )
        )
        return 0 if payload["overall_status"] == "PASS" else 1
    if args.command == "pilot":
        payload = evaluate_pilot(args.fixture, args.output)
        print(
            json.dumps(
                {
                    "calibrations": payload["calibrations"],
                    "usage": payload["usage"],
                },
                sort_keys=True,
            )
        )
        return 0
    if args.command == "held-out":
        payload = evaluate_held_out(
            args.frozen,
            args.pilot_result,
            args.output,
        )
        print(
            json.dumps(
                {
                    "aggregates": payload["aggregates"],
                    "generic_metrics_status": payload[
                        "generic_metrics_status"
                    ],
                    "usage": payload["usage"],
                },
                sort_keys=True,
            )
        )
        return 0
    payload = build_sanitized_summary(
        args.hard_gate,
        args.pilot_result,
        args.held_out_result,
        args.output,
        incomplete_reason=args.incomplete_reason,
    )
    print(
        json.dumps(
            {
                "overall_status": payload["overall_status"],
                "pro_comparison_ready": payload[
                    "pro_comparison_ready"
                ],
            },
            sort_keys=True,
        )
    )
    return 0 if payload["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
