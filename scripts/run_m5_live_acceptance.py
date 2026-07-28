from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.api.schemas import ChatRequest
from app.runtime import RuntimeConfig, build_runtime
from app.services.service_snapshot import SERVICE_SNAPSHOT_ID
from scripts.run_service_acceptance import load_local_llm_environment

SEOUL_TZ = ZoneInfo("Asia/Seoul")
AS_OF = datetime(2026, 7, 27, 14, 0, tzinfo=SEOUL_TZ)
CASES = (
    ("recent_issue", "삼성전자 최근 이슈 요약해줘"),
    ("price_move", "삼성전자 오늘 왜 올랐어?"),
)


async def _run() -> int:
    load_local_llm_environment(Path(".env"))
    state = build_runtime(
        config=RuntimeConfig(
            source_mode="recorded",
            snapshot_id=SERVICE_SNAPSHOT_ID,
            llm_mode="gemini",
        )
    )
    results = []
    passed = True
    for expected_intent, question in CASES:
        response = await state.chat_service.chat(
            ChatRequest(
                message=question,
                session_id=f"m5-live-{expected_intent}",
                as_of=AS_OF,
            )
        )
        process = response.diagnostics_public
        generation = process.generation
        future_evidence_count = sum(
            item.published_at is None
            or item.published_at > AS_OF
            for item in response.evidence
        )
        case_passed = (
            process.query_plan.intent == expected_intent
            and generation.mode == "llm"
            and generation.llm_status == "ok"
            and generation.live_verified
            and future_evidence_count == 0
            and (
                expected_intent != "price_move"
                or response.market_snapshot is not None
            )
        )
        passed = passed and case_passed
        results.append(
            {
                "case": expected_intent,
                "result": "PASS" if case_passed else "FAIL",
                "public_status": response.status,
                "generation_mode": generation.mode,
                "llm_status": generation.llm_status,
                "live_verified": generation.live_verified,
                "model": generation.model,
                "evidence_count": len(response.evidence),
                "future_evidence_count": future_evidence_count,
                "market_snapshot_attached": (
                    response.market_snapshot is not None
                ),
            }
        )
    print(
        json.dumps(
            {
                "result": "PASS" if passed else "FAIL",
                "provider_call_limit": len(CASES),
                "provider_calls_this_run": len(CASES),
                "as_of": AS_OF.isoformat(),
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
