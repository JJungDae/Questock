from __future__ import annotations

import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from app.api.schemas import ChatRequest
from app.runtime import RuntimeConfig, build_runtime
from app.services.service_snapshot import SERVICE_SNAPSHOT_ID
from app.ui.projections import project_evidence_comparison

SEOUL_TZ = ZoneInfo("Asia/Seoul")


def test_recorded_runtime_attaches_cited_temporal_comparison() -> None:
    state = build_runtime(
        config=RuntimeConfig(
            source_mode="recorded",
            snapshot_id=SERVICE_SNAPSHOT_ID,
            llm_mode="disabled",
        )
    )
    cutoff = datetime(2026, 7, 27, 21, tzinfo=SEOUL_TZ)

    response = asyncio.run(
        state.chat_service.chat(
            ChatRequest(
                message="삼성전자 HBM5 2나노 이슈가 뭐야?",
                session_id="m5-d1-integration",
                as_of=cutoff,
            )
        )
    )

    comparison = response.evidence_comparison
    assert comparison is not None
    assert all(
        source.published_at <= cutoff
        for source in comparison.article_sources
    )
    assert comparison.common_facts == []
    assert comparison.missing_evidence
    assert all(
        item.source.source_url.startswith(("http://", "https://"))
        for item in comparison.different_interpretations
    )
    assert all(
        item.source_locator
        for item in comparison.different_interpretations
    )
    assert all(
        item.source is None
        or item.source.source_url.startswith(("http://", "https://"))
        for item in comparison.disclosure_links
    )

    view = project_evidence_comparison(comparison)
    assert view is not None
    assert "원출처 관계 미확인" in view.lineage_text
    assert view.article_count_text == "전체 27건 중 20건 표시"
    assert view.articles
    assert view.perspectives
    assert view.disclosures
