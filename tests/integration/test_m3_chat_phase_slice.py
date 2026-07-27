from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta

from app.answer.composer import AnswerComposer
from app.api.schemas import ChatRequest
from app.core.models import FinancialDocument, QueryPlan
from app.core.status import ProviderStatus
from app.llm.base import LLMRequest, LLMResult, LLMStatus, create_llm_result
from app.providers.base import create_provider_result
from app.services.chat_service import ChatService
from app.services.source_gateway import SourceGatewayResult

BASIS_AT = datetime(2026, 7, 25, 3, tzinfo=UTC)
QUERY = "삼성전자 반도체 투자 최근 뉴스"
SNIPPET = "삼성전자 반도체 투자 확대 소식이 발표됐다."


def _document() -> FinancialDocument:
    source_url = "https://news.example.test/m3-phase"
    published_at = BASIS_AT - timedelta(days=1)
    return FinancialDocument(
        document_id="document:news:m3-phase",
        source_type="news",
        provider="recorded_news",
        primary_security_ids=["KRX:005930"],
        mentioned_security_ids=[],
        title=QUERY,
        published_at=published_at,
        source_url=source_url,
        text=SNIPPET,
        locator={
            "provider": "recorded_news",
            "source_url": source_url,
            "published_at": published_at.isoformat(),
            "raw_index": 0,
            "query": QUERY,
        },
        metadata={},
        ingestion_version="news-provider-m1-04-v1",
    )


class _Gateway:
    async def fetch(
        self,
        plan: QueryPlan,
        *,
        query: str,
        timeout_seconds: float,
    ) -> SourceGatewayResult:
        document = _document()
        return SourceGatewayResult(
            documents=(document,),
            provider_results_by_source={
                "news": create_provider_result(
                    status=ProviderStatus.OK,
                    data={"document_ids": [document.document_id]},
                    fetched_at=BASIS_AT,
                )
            },
            documents_by_id={document.document_id: document},
            data_mode="recorded",
            live_connectivity_checked=False,
        )


class _LLM:
    def __init__(self) -> None:
        self.calls = 0

    async def complete(
        self,
        request: LLMRequest,
        *,
        timeout_seconds: float,
    ) -> LLMResult:
        self.calls += 1
        rendered = "\n".join(item.content for item in request.messages)
        evidence_id = next(
            line.removeprefix("Evidence ID: ").strip()
            for line in rendered.splitlines()
            if line.startswith("Evidence ID: ")
        )
        return create_llm_result(
            status=LLMStatus.OK,
            content=json.dumps(
                {
                    "claims": [
                        {
                            "claim_id": "claim-1",
                            "section": "summary",
                            "text": SNIPPET,
                            "evidence_ids": [evidence_id],
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            model="gemini/gemini-3.5-flash",
            provider="gemini",
            latency_ms=1,
        )


def test_m3_chat_vertical_slice_composes_existing_m2_contracts() -> None:
    llm = _LLM()
    service = ChatService(
        source_gateway=_Gateway(),
        composer=AnswerComposer(llm),
        utc_now=lambda: BASIS_AT,
    )

    response = asyncio.run(
        service.chat(
            ChatRequest(message=QUERY, session_id="integration-m3")
        )
    )

    assert response.status == "complete"
    assert response.answer_sections.summary == [SNIPPET]
    assert len(response.evidence) == 1
    assert llm.calls == 1
    process = response.diagnostics_public
    assert process.data_mode == "recorded"
    assert process.live_connectivity_checked is False
    assert process.evidence_pipeline.model_dump() == {
        "normalized_count": 1,
        "hard_filtered_count": 1,
        "freshness_retained_count": 1,
        "freshness_warning_codes": [],
        "retrieval_status": "ok",
        "retrieval_selected_count": 1,
    }
    assert process.decision.evidence_decision_status == "complete"
    assert process.context_budget.selected_count == 1
    assert process.citation.model_dump() == {
        "claim_count": 1,
        "citation_count": 1,
        "rejection_count": 0,
    }
    assert process.generation.model_dump() == {
        "mode": "llm",
        "llm_status": "ok",
        "model": "gemini/gemini-3.5-flash",
        "live_verified": False,
    }
