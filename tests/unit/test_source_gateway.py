from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from app.core.models import FinancialDocument, QueryPlan
from app.core.status import ProviderStatus
from app.providers.base import create_provider_result
from app.services.source_gateway import (
    ExplicitUnconfiguredSourceGateway,
    SourceGateway,
    SourceGatewayResult,
    SourceGatewayValidationError,
    validate_source_gateway_result,
)

BASIS_AT = datetime(2026, 7, 25, tzinfo=UTC)


def _plan() -> QueryPlan:
    return QueryPlan(
        intent="multi_source_summary",
        required_sources=["news", "disclosure", "research_report"],
        required_evidence=["recent_news", "disclosure", "research_report"],
    )


def _document() -> FinancialDocument:
    return FinancialDocument(
        document_id="document:news:unit",
        source_type="news",
        provider="recorded_news",
        primary_security_ids=["KRX:005930"],
        mentioned_security_ids=[],
        title="Samsung investment update",
        published_at=BASIS_AT,
        source_url="https://news.example.test/unit",
        text="Samsung investment expanded.",
        locator={
            "provider": "recorded_news",
            "source_url": "https://news.example.test/unit",
            "published_at": BASIS_AT.isoformat(),
            "raw_index": 0,
            "query": "Samsung investment",
        },
        metadata={},
        ingestion_version="unit-v1",
    )


def test_explicit_unconfigured_gateway_preserves_every_required_key() -> None:
    gateway = ExplicitUnconfiguredSourceGateway()

    result = asyncio.run(
        gateway.fetch(_plan(), query="query", timeout_seconds=2)
    )

    assert isinstance(gateway, SourceGateway)
    assert result.documents == ()
    assert result.documents_by_id == {}
    assert list(result.provider_results_by_source) == [
        "news",
        "disclosure",
        "research_report",
    ]
    assert all(
        item.status == ProviderStatus.PROVIDER_UNAVAILABLE
        and item.error_code == "provider_unavailable"
        and item.message == "provider unavailable"
        for item in result.provider_results_by_source.values()
    )
    assert result.data_mode == "unconfigured"
    assert result.live_connectivity_checked is False


def test_gateway_validation_returns_deep_copies() -> None:
    document = _document()
    result = SourceGatewayResult(
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

    validated = validate_source_gateway_result(
        result,
        required_sources=["news"],
    )

    assert validated.documents[0] is not document
    assert validated.documents_by_id[document.document_id] is not document
    validated.documents_by_id[document.document_id].locator["raw_index"] = 9
    assert document.locator["raw_index"] == 0


@pytest.mark.parametrize(
    "result",
    [
        SourceGatewayResult(
            documents=(),
            provider_results_by_source={},
            documents_by_id={},
            data_mode="recorded",
            live_connectivity_checked=False,
        ),
        SourceGatewayResult(
            documents=(_document(),),
            provider_results_by_source={
                "news": create_provider_result(
                    status=ProviderStatus.NO_DATA,
                    fetched_at=BASIS_AT,
                )
            },
            documents_by_id={},
            data_mode="recorded",
            live_connectivity_checked=False,
        ),
    ],
)
def test_gateway_contract_rejects_missing_keys_or_mapping(
    result: SourceGatewayResult,
) -> None:
    with pytest.raises(SourceGatewayValidationError):
        validate_source_gateway_result(result, required_sources=["news"])

