from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from app.api.schemas import ChatRequest
from app.core.models import FinancialDocument, QueryPlan
from app.core.status import ProviderStatus
from app.providers.base import create_provider_result
from app.services.chat_service import ChatService
from app.services.observability import InMemoryObservationSink
from app.services.source_gateway import (
    SourceGatewayResult,
    SourceGatewayTimeoutDescriptor,
)

BASIS_AT = datetime(2026, 7, 25, 3, tzinfo=UTC)
QUESTION = "삼성전자 위험 요인 알려줘"
SECURITY_ID = "KRX:005930"
SENTINEL = "sentinel-secret C:\\private\\provider.txt"


def _news_document() -> FinancialDocument:
    published_at = BASIS_AT - timedelta(days=1)
    source_url = "https://news.example.test/b8-risk"
    return FinancialDocument(
        document_id="document:news:b8-risk",
        source_type="news",
        provider="recorded_news",
        primary_security_ids=[SECURITY_ID],
        mentioned_security_ids=[],
        title="삼성전자 공급망 위험 요인",
        published_at=published_at,
        source_url=source_url,
        text="삼성전자는 공급망 변동을 주요 위험 요인으로 설명했다.",
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


class MatrixGateway:
    timeout_descriptor = SourceGatewayTimeoutDescriptor(
        data_mode="recorded",
        live_connectivity_checked=False,
    )

    def __init__(
        self,
        statuses: dict[str, ProviderStatus],
        *,
        documents: tuple[FinancialDocument, ...] = (),
    ) -> None:
        self._statuses = statuses
        self._documents = documents
        self.calls = 0

    async def fetch(
        self,
        plan: QueryPlan,
        *,
        query: str,
        timeout_seconds: float,
    ) -> SourceGatewayResult:
        self.calls += 1
        provider_results = {}
        for source in plan.required_sources:
            status = self._statuses[source]
            if status == ProviderStatus.OK:
                provider_results[source] = create_provider_result(
                    status=status,
                    data={
                        "document_ids": [
                            item.document_id
                            for item in self._documents
                            if item.source_type == source
                        ]
                    },
                    fetched_at=BASIS_AT,
                )
            else:
                provider_results[source] = create_provider_result(
                    status=status,
                    fetched_at=BASIS_AT,
                    message=SENTINEL,
                )
        return SourceGatewayResult(
            documents=self._documents,
            provider_results_by_source=provider_results,
            documents_by_id={
                item.document_id: item for item in self._documents
            },
            data_mode="recorded",
            live_connectivity_checked=False,
        )


def _chat(gateway: MatrixGateway):
    sink = InMemoryObservationSink()
    service = ChatService(
        source_gateway=gateway,
        utc_now=lambda: BASIS_AT,
        observation_sink=sink,
        request_id_factory=lambda: "request-b8-phase-slice",
    )
    response = asyncio.run(
        service.chat(
            ChatRequest(
                message=QUESTION,
                session_id="b8-quality-phase-slice",
            )
        )
    )
    return response, sink


@pytest.mark.parametrize(
    "status",
    [
        ProviderStatus.TIMEOUT,
        ProviderStatus.RATE_LIMITED,
        ProviderStatus.PROVIDER_UNAVAILABLE,
        ProviderStatus.PARSE_ERROR,
    ],
)
def test_all_required_provider_failures_are_provider_failed(
    status: ProviderStatus,
) -> None:
    gateway = MatrixGateway(
        {
            "news": status,
            "disclosure": status,
            "research_report": status,
        }
    )

    response, sink = _chat(gateway)

    assert response.status == "provider_failed"
    assert response.evidence == []
    assert response.diagnostics_public.generation.mode == "fixed_template"
    assert {
        item.source_type: item.provider_status
        for item in response.diagnostics_public.sources
    } == {
        "news": status,
        "disclosure": status,
        "research_report": status,
    }
    assert SENTINEL not in response.model_dump_json()
    assert len(sink.observations) == 1
    assert sink.observations[0].evidence_decision == "provider_failed"
    assert sink.observations[0].fallback_used is True
    assert sink.observations[0].retrieval_strategy == (
        "lexical-bm25-m2-03-v1"
    )


def test_all_required_provider_no_data_is_no_evidence() -> None:
    gateway = MatrixGateway(
        {
            "news": ProviderStatus.NO_DATA,
            "disclosure": ProviderStatus.NO_DATA,
            "research_report": ProviderStatus.NO_DATA,
        }
    )

    response, sink = _chat(gateway)

    assert response.status == "no_evidence"
    assert response.evidence == []
    assert response.diagnostics_public.decision.no_data_sources == [
        "news",
        "disclosure",
        "research_report",
    ]
    assert response.diagnostics_public.decision.failed_sources == []
    assert len(sink.observations) == 1
    assert sink.observations[0].evidence_decision == "no_evidence"
    assert sink.observations[0].fallback_used is True


def test_successful_source_is_preserved_when_other_sources_are_unavailable() -> None:
    document = _news_document()
    gateway = MatrixGateway(
        {
            "news": ProviderStatus.OK,
            "disclosure": ProviderStatus.TIMEOUT,
            "research_report": ProviderStatus.NO_DATA,
        },
        documents=(document,),
    )

    response, sink = _chat(gateway)

    assert response.status == "partial"
    assert [item.document_id for item in response.evidence] == [
        document.document_id
    ]
    assert response.diagnostics_public.decision.satisfied_sources == ["news"]
    assert response.diagnostics_public.decision.no_data_sources == [
        "research_report"
    ]
    assert response.diagnostics_public.decision.failed_sources == [
        "disclosure"
    ]
    assert response.diagnostics_public.generation.mode == "fixed_template"
    assert len(sink.observations) == 1
    assert sink.observations[0].evidence_decision == "partial"
    assert sink.observations[0].provider_statuses == (
        ("news", "ok"),
        ("disclosure", "timeout"),
        ("research_report", "no_data"),
    )
    assert sink.observations[0].evidence_count == 1
    assert sink.observations[0].fallback_used is True
