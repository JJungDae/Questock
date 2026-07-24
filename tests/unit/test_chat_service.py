from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from app.answer.composer import AnswerComposer
from app.api.schemas import ChatRequest
from app.core.models import FinancialDocument, QueryPlan
from app.core.status import ProviderStatus
from app.llm.base import LLMRequest, LLMResult, LLMStatus, create_llm_result
from app.providers.base import create_provider_result
from app.services.chat_service import ChatService
from app.services.source_gateway import SourceGatewayResult

BASIS_AT = datetime(2026, 7, 25, 3, tzinfo=UTC)
SECURITY_ID = "KRX:005930"
QUESTION = "삼성전자 반도체 투자 최근 뉴스"
SNIPPET = "삼성전자 반도체 투자 확대 소식이 발표됐다."


def news_document(
    *,
    document_id: str = "document:news:unit",
    security_id: str = SECURITY_ID,
    published_at: datetime = BASIS_AT - timedelta(days=1),
) -> FinancialDocument:
    source_url = f"https://news.example.test/{document_id.replace(':', '-')}"
    return FinancialDocument(
        document_id=document_id,
        source_type="news",
        provider="recorded_news",
        primary_security_ids=[security_id],
        mentioned_security_ids=[],
        title="삼성전자 반도체 투자 최근 뉴스",
        published_at=published_at,
        source_url=source_url,
        text=SNIPPET,
        locator={
            "provider": "recorded_news",
            "source_url": source_url,
            "published_at": published_at.isoformat(),
            "raw_index": 0,
            "query": QUESTION,
        },
        metadata={},
        ingestion_version="news-provider-m1-04-v1",
    )


class FakeGateway:
    def __init__(
        self,
        documents: tuple[FinancialDocument, ...],
        *,
        status: ProviderStatus = ProviderStatus.OK,
        data_mode: str = "recorded",
        delay: float = 0,
    ) -> None:
        self.documents = documents
        self.status = status
        self.data_mode = data_mode
        self.delay = delay
        self.calls = 0
        self.cancel_count = 0

    async def fetch(
        self,
        plan: QueryPlan,
        *,
        query: str,
        timeout_seconds: float,
    ) -> SourceGatewayResult:
        self.calls += 1
        try:
            if self.delay:
                await asyncio.sleep(self.delay)
        except asyncio.CancelledError:
            self.cancel_count += 1
            raise
        if self.status == ProviderStatus.OK:
            provider_result = create_provider_result(
                status=self.status,
                data={"document_ids": [item.document_id for item in self.documents]},
                fetched_at=BASIS_AT,
            )
        else:
            provider_result = create_provider_result(
                status=self.status,
                fetched_at=BASIS_AT,
            )
        return SourceGatewayResult(
            documents=self.documents,
            provider_results_by_source={
                source: provider_result.model_copy(deep=True)
                for source in plan.required_sources
            },
            documents_by_id={
                item.document_id: item for item in self.documents
            },
            data_mode=self.data_mode,  # type: ignore[arg-type]
            live_connectivity_checked=False,
        )


class ExtractiveLLM:
    def __init__(
        self,
        *,
        status: LLMStatus = LLMStatus.OK,
        delay: float = 0,
    ) -> None:
        self.status = status
        self.delay = delay
        self.calls = 0
        self.cancel_count = 0

    async def complete(
        self,
        request: LLMRequest,
        *,
        timeout_seconds: float,
    ) -> LLMResult:
        self.calls += 1
        try:
            if self.delay:
                await asyncio.sleep(self.delay)
        except asyncio.CancelledError:
            self.cancel_count += 1
            raise
        rendered = "\n".join(item.content for item in request.messages)
        evidence_id = next(
            line.split("Evidence ID: ", 1)[1].strip()
            for line in rendered.splitlines()
            if line.startswith("Evidence ID: ")
        )
        content = json.dumps(
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
        )
        return create_llm_result(
            status=self.status,
            content=content if self.status == LLMStatus.OK else None,
            model="gemini/gemini-2.5-flash",
            provider="gemini",
            latency_ms=1,
        )


def _service(
    gateway: FakeGateway,
    llm: ExtractiveLLM,
    *,
    deadline_seconds: float = 20,
) -> ChatService:
    return ChatService(
        source_gateway=gateway,
        composer=AnswerComposer(llm),
        deadline_seconds=deadline_seconds,
        utc_now=lambda: BASIS_AT,
    )


def _request(message: str = QUESTION) -> ChatRequest:
    return ChatRequest(message=message, session_id="chat-service-unit")


def test_recorded_complete_path_preserves_m2_order_and_generates_once() -> None:
    document = news_document()
    gateway = FakeGateway((document,))
    llm = ExtractiveLLM()

    response = asyncio.run(_service(gateway, llm).chat(_request()))

    assert response.status == "complete"
    assert response.answer_sections.summary == [SNIPPET]
    assert len(response.evidence) == 1
    assert llm.calls == 1
    summary = response.diagnostics_public
    assert summary.data_mode == "recorded"
    assert summary.evidence_pipeline.normalized_count == 1
    assert summary.evidence_pipeline.hard_filtered_count == 1
    assert summary.evidence_pipeline.freshness_retained_count == 1
    assert summary.evidence_pipeline.retrieval_status == "ok"
    assert summary.decision.evidence_decision_status == "complete"
    assert summary.context_budget.selected_count == 1
    assert summary.citation.claim_count == 1
    assert summary.citation.citation_count == 1
    assert summary.generation.mode == "llm"
    assert summary.generation.llm_status == "ok"
    assert summary.generation.live_verified is False


def test_default_unconfigured_runtime_is_explicit_provider_failure() -> None:
    response = asyncio.run(
        ChatService(utc_now=lambda: BASIS_AT).chat(_request())
    )

    assert response.status == "provider_failed"
    assert response.evidence == []
    assert response.diagnostics_public.data_mode == "unconfigured"
    assert response.diagnostics_public.sources[0].provider_status == "provider_unavailable"
    assert response.diagnostics_public.generation.llm_status is None
    assert response.diagnostics_public.generation.model is None
    assert response.answer_sections.summary == [
        "자료 제공 상태를 확인하지 못해 답변을 보류합니다."
    ]


def test_no_data_is_not_misreported_as_provider_failure() -> None:
    gateway = FakeGateway((), status=ProviderStatus.NO_DATA)
    llm = ExtractiveLLM()

    response = asyncio.run(_service(gateway, llm).chat(_request()))

    assert response.status == "no_evidence"
    assert response.diagnostics_public.decision.no_data_sources == ["news"]
    assert response.diagnostics_public.decision.failed_sources == []
    assert llm.calls == 0


def test_blocked_advice_calls_neither_gateway_nor_llm() -> None:
    gateway = FakeGateway(())
    llm = ExtractiveLLM()

    response = asyncio.run(
        _service(gateway, llm).chat(
            _request("삼성전자 지금 매수해야 하나")
        )
    )

    assert response.status == "blocked"
    assert response.diagnostics_public.generation.mode == "blocked"
    assert gateway.calls == 0
    assert llm.calls == 0


def test_llm_failure_does_not_change_complete_decision() -> None:
    gateway = FakeGateway((news_document(),))
    llm = ExtractiveLLM(status=LLMStatus.RATE_LIMITED)

    response = asyncio.run(_service(gateway, llm).chat(_request()))

    assert response.status == "complete"
    assert response.diagnostics_public.decision.evidence_decision_status == "complete"
    assert response.diagnostics_public.generation.mode == "fixed_template"
    assert response.diagnostics_public.generation.llm_status == "rate_limited"
    assert response.warnings == ["llm_generation_degraded"]
    assert llm.calls == 1


def test_completed_source_result_is_preserved_when_other_sources_fail() -> None:
    document = news_document()

    class PartialGateway:
        async def fetch(
            self,
            plan: QueryPlan,
            *,
            query: str,
            timeout_seconds: float,
        ) -> SourceGatewayResult:
            return SourceGatewayResult(
                documents=(document,),
                provider_results_by_source={
                    "news": create_provider_result(
                        status=ProviderStatus.OK,
                        data={"document_ids": [document.document_id]},
                        fetched_at=BASIS_AT,
                    ),
                    "disclosure": create_provider_result(
                        status=ProviderStatus.TIMEOUT,
                        fetched_at=BASIS_AT,
                    ),
                    "research_report": create_provider_result(
                        status=ProviderStatus.NO_DATA,
                        fetched_at=BASIS_AT,
                    ),
                },
                documents_by_id={document.document_id: document},
                data_mode="mixed",
                live_connectivity_checked=False,
            )

    llm = ExtractiveLLM()
    response = asyncio.run(
        ChatService(
            source_gateway=PartialGateway(),
            composer=AnswerComposer(llm),
            utc_now=lambda: BASIS_AT,
        ).chat(
            _request("삼성전자 반도체 투자 위험 요인")
        )
    )

    assert response.status == "partial"
    assert response.diagnostics_public.decision.satisfied_sources == ["news"]
    assert response.diagnostics_public.decision.failed_sources == ["disclosure"]
    assert response.diagnostics_public.decision.no_data_sources == [
        "research_report"
    ]
    assert [
        item.provider_status for item in response.diagnostics_public.sources
    ] == ["ok", "timeout", "no_data"]
    assert len(response.evidence) == 1
    assert llm.calls == 1


def test_gateway_deadline_cancels_pending_and_preserves_source_key() -> None:
    gateway = FakeGateway((news_document(),), delay=1)
    llm = ExtractiveLLM()

    response = asyncio.run(
        _service(
            gateway,
            llm,
            deadline_seconds=0.01,
        ).chat(_request())
    )

    assert response.status == "provider_failed"
    assert response.diagnostics_public.sources[0].provider_status == "timeout"
    assert response.diagnostics_public.decision.failed_sources == ["news"]
    assert gateway.cancel_count == 1
    assert llm.calls == 0


def test_llm_deadline_cancels_once_and_uses_fixed_template() -> None:
    gateway = FakeGateway((news_document(),))
    llm = ExtractiveLLM(delay=1)

    response = asyncio.run(
        _service(
            gateway,
            llm,
            deadline_seconds=0.02,
        ).chat(_request())
    )

    assert response.status == "complete"
    assert response.answer_sections.summary == [SNIPPET]
    assert response.diagnostics_public.generation.mode == "fixed_template"
    assert response.diagnostics_public.generation.llm_status == "timeout"
    assert llm.calls == 1
    assert llm.cancel_count == 1


def test_wrong_company_and_stale_documents_are_visible_only_as_counts() -> None:
    documents = (
        news_document(),
        news_document(
            document_id="document:news:wrong",
            security_id="KRX:000660",
        ),
        news_document(
            document_id="document:news:stale",
            published_at=BASIS_AT - timedelta(days=31),
        ),
    )
    response = asyncio.run(
        _service(FakeGateway(documents), ExtractiveLLM()).chat(_request())
    )

    pipeline = response.diagnostics_public.evidence_pipeline
    assert pipeline.normalized_count == 3
    assert pipeline.hard_filtered_count == 2
    assert pipeline.freshness_retained_count == 1
    assert len(response.evidence) == 1
    serialized = response.diagnostics_public.model_dump_json()
    assert "document:news:wrong" not in serialized
    assert "document:news:stale" not in serialized


def test_equal_fixture_input_returns_equal_isolated_json() -> None:
    document = news_document()
    first = asyncio.run(
        _service(FakeGateway((document,)), ExtractiveLLM()).chat(_request())
    )
    second = asyncio.run(
        _service(FakeGateway((document,)), ExtractiveLLM()).chat(_request())
    )

    assert first.model_dump_json() == second.model_dump_json()
    assert first.evidence[0] is not second.evidence[0]
    first.evidence[0].locator["raw_index"] = 99
    assert second.evidence[0].locator["raw_index"] == 0
    assert document.locator["raw_index"] == 0
