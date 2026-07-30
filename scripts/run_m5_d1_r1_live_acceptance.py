from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import litellm

from app.api.schemas import ChatRequest
from app.runtime import RuntimeConfig, build_runtime
from app.services.service_snapshot import SERVICE_SNAPSHOT_ID
from scripts.run_service_acceptance import load_local_llm_environment

SEOUL_TZ = ZoneInfo("Asia/Seoul")
AS_OF = datetime(2026, 7, 27, 21, 0, tzinfo=SEOUL_TZ)
QUESTION = "현대차 실적 관련 최근 뉴스 근거를 대조해줘."
MAX_PROVIDER_CALLS = 5


async def _run() -> int:
    load_local_llm_environment(Path(".env"))
    provider_calls = 0
    original_completion = litellm.acompletion

    async def counted_completion(**kwargs: Any) -> Any:
        nonlocal provider_calls
        if provider_calls >= MAX_PROVIDER_CALLS:
            raise RuntimeError("live comparison call limit exceeded")
        provider_calls += 1
        return await original_completion(**kwargs)

    logging.getLogger("questock.observability").disabled = True
    litellm.acompletion = counted_completion
    try:
        state = build_runtime(
            config=RuntimeConfig(
                source_mode="recorded",
                snapshot_id=SERVICE_SNAPSHOT_ID,
                llm_mode="gemini",
                request_protection_enabled=False,
                response_cache_enabled=False,
                hybrid_router_enabled=False,
            )
        )
    finally:
        litellm.acompletion = original_completion

    results: list[dict[str, object]] = []
    passed = True
    for index in range(MAX_PROVIDER_CALLS):
        response = await state.chat_service.chat(
            ChatRequest(
                message=QUESTION,
                session_id=f"m5-d1-r1-live-{index + 1}",
                as_of=AS_OF,
            )
        )
        comparison = response.evidence_comparison
        generation = response.diagnostics_public.generation
        article_urls = (
            {
                item.source_url
                for item in comparison.article_sources
                if item.source_url is not None
            }
            if comparison is not None
            else set()
        )
        body_items = (
            *response.answer_sections.summary,
            *response.answer_sections.facts,
            *response.answer_sections.interpretation,
            *response.answer_sections.inference,
            *response.answer_sections.uncertainty,
        )
        body = "\n".join(body_items)
        future_evidence_count = sum(
            item.published_at is None
            or item.published_at > AS_OF
            for item in response.evidence
        )
        report_url_count = (
            sum(
                item.source.source_url is not None
                for item in comparison.report_perspectives
            )
            if comparison is not None
            else 0
        )
        case_passed = (
            generation.mode == "llm"
            and generation.llm_status == "ok"
            and generation.live_verified
            and comparison is not None
            and bool(comparison.common_facts)
            and bool(comparison.different_interpretations)
            and comparison.support_summary is not None
            and comparison.common_facts[0].text in body
            and len(response.answer_sections.interpretation) == 1
            and "전자신문" in response.answer_sections.interpretation[0]
            and "매일신문" in response.answer_sections.interpretation[0]
            and "반면" in response.answer_sections.interpretation[0]
            and comparison.support_summary in body
            and future_evidence_count == 0
            and report_url_count == 0
            and all(
                item.source_url in article_urls
                for item in response.evidence
            )
        )
        passed = passed and case_passed
        results.append(
            {
                "run": index + 1,
                "result": "PASS" if case_passed else "FAIL",
                "generation_mode": generation.mode,
                "llm_status": generation.llm_status,
                "live_verified": generation.live_verified,
                "comparison_attached": comparison is not None,
                "future_evidence_count": future_evidence_count,
                "report_url_count": report_url_count,
            }
        )

    print(
        json.dumps(
            {
                "result": "PASS" if passed else "FAIL",
                "provider_call_limit": MAX_PROVIDER_CALLS,
                "provider_calls_this_run": provider_calls,
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
