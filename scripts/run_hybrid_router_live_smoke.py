from __future__ import annotations

import asyncio
import json
from datetime import date
from pathlib import Path

from app.config import LLMConfig
from app.core.resolver import SecurityResolver
from app.llm.litellm_client import LiteLLMClient
from app.services.hybrid_intent_router import HybridIntentRouter
from app.services.planning_observation import build_observed_query_plan
from scripts.run_service_acceptance import load_local_llm_environment

BASIS_DATE = date(2026, 7, 27)
CASES = (
    ("recent_risk", "삼성전자 최근 악재 알려줘"),
    ("price_situation", "삼성전자 주가 상황 어때?"),
)


async def _run() -> int:
    load_local_llm_environment(Path(".env"))
    client = LiteLLMClient(LLMConfig.from_env(require_credential=True))
    router = HybridIntentRouter(client, enabled=True)
    resolver = SecurityResolver()
    results: list[dict[str, object]] = []
    passed = True

    for case_id, query in CASES:
        deterministic = build_observed_query_plan(
            query,
            basis_date=BASIS_DATE,
            resolver=resolver,
        )
        result = await router.classify(
            query,
            deterministic,
            basis_date=BASIS_DATE,
            timeout_seconds=5,
        )
        case_passed = (
            result.mode == "hybrid_llm"
            and result.classifier_status == "accepted"
            and result.classifier_call_count == 1
        )
        passed = passed and case_passed
        results.append(
            {
                "case": case_id,
                "result": "PASS" if case_passed else "FAIL",
                "deterministic_intent": deterministic.plan.intent,
                "final_intent": result.observed.plan.intent,
                "routing_mode": result.mode,
                "classifier_status": result.classifier_status,
                "provider_calls": result.classifier_call_count,
            }
        )

    print(
        json.dumps(
            {
                "result": "PASS" if passed else "FAIL",
                "provider_call_limit": len(CASES),
                "provider_calls_this_run": sum(
                    int(item["provider_calls"])
                    for item in results
                ),
                "cases": results,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
    return 0 if passed else 1


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
