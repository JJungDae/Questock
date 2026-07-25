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


def _document(
    *,
    document_id: str = "document:news:unit",
    source_type: str = "news",
) -> FinancialDocument:
    return FinancialDocument(
        document_id=document_id,
        source_type=source_type,
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
    validated.provider_results_by_source["news"].data["document_ids"].append(
        "document:news:mutated"
    )
    assert result.provider_results_by_source["news"].data == {
        "document_ids": [document.document_id]
    }


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


def test_gateway_rejects_document_from_unrequested_source() -> None:
    document = _document(source_type="disclosure")
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

    with pytest.raises(
        SourceGatewayValidationError,
        match="source documents are invalid",
    ):
        validate_source_gateway_result(result, required_sources=["news"])


@pytest.mark.parametrize(
    "status",
    [
        ProviderStatus.NO_DATA,
        ProviderStatus.TIMEOUT,
        ProviderStatus.RATE_LIMITED,
        ProviderStatus.PROVIDER_UNAVAILABLE,
        ProviderStatus.PARSE_ERROR,
    ],
)
def test_gateway_rejects_document_when_provider_is_not_ok(
    status: ProviderStatus,
) -> None:
    document = _document()
    kwargs = (
        {"error_code": "attempt_timeout"}
        if status == ProviderStatus.TIMEOUT
        else (
            {}
            if status == ProviderStatus.NO_DATA
            else {"error_code": status.value}
        )
    )
    result = SourceGatewayResult(
        documents=(document,),
        provider_results_by_source={
            "news": create_provider_result(
                status=status,
                fetched_at=BASIS_AT,
                **kwargs,
            )
        },
        documents_by_id={document.document_id: document},
        data_mode="recorded",
        live_connectivity_checked=False,
    )

    with pytest.raises(
        SourceGatewayValidationError,
        match="source documents are invalid",
    ):
        validate_source_gateway_result(result, required_sources=["news"])


@pytest.mark.parametrize(
    ("data_mode", "live_checked", "documents", "status"),
    [
        ("unconfigured", True, (), ProviderStatus.PROVIDER_UNAVAILABLE),
        ("unconfigured", False, (_document(),), ProviderStatus.OK),
        ("unconfigured", False, (), ProviderStatus.NO_DATA),
        ("recorded", True, (), ProviderStatus.NO_DATA),
        ("live", False, (), ProviderStatus.NO_DATA),
        ("mixed", False, (), ProviderStatus.NO_DATA),
        ("mixed", True, (), ProviderStatus.NO_DATA),
    ],
)
def test_gateway_rejects_inconsistent_data_mode_contract(
    data_mode: str,
    live_checked: bool,
    documents: tuple[FinancialDocument, ...],
    status: ProviderStatus,
) -> None:
    kwargs = (
        {"data": {"document_ids": [item.document_id for item in documents]}}
        if status == ProviderStatus.OK
        else {}
    )
    result = SourceGatewayResult(
        documents=documents,
        provider_results_by_source={
            "news": create_provider_result(
                status=status,
                fetched_at=BASIS_AT,
                **kwargs,
            )
        },
        documents_by_id={item.document_id: item for item in documents},
        data_mode=data_mode,  # type: ignore[arg-type]
        live_connectivity_checked=live_checked,
    )

    with pytest.raises(
        SourceGatewayValidationError,
        match="source data mode is invalid",
    ):
        validate_source_gateway_result(result, required_sources=["news"])


@pytest.mark.parametrize(
    ("data_mode", "live_checked"),
    [
        ("recorded", False),
        ("live", True),
    ],
)
def test_gateway_accepts_consistent_recorded_and_live_modes(
    data_mode: str,
    live_checked: bool,
) -> None:
    result = SourceGatewayResult(
        documents=(),
        provider_results_by_source={
            "news": create_provider_result(
                status=ProviderStatus.NO_DATA,
                fetched_at=BASIS_AT,
            )
        },
        documents_by_id={},
        data_mode=data_mode,  # type: ignore[arg-type]
        live_connectivity_checked=live_checked,
    )

    validated = validate_source_gateway_result(
        result,
        required_sources=["news"],
    )

    assert validated.data_mode == data_mode
    assert validated.live_connectivity_checked is live_checked


def test_provider_status_mixture_remains_valid_recorded_mode() -> None:
    result = SourceGatewayResult(
        documents=(),
        provider_results_by_source={
            "news": create_provider_result(
                status=ProviderStatus.NO_DATA,
                fetched_at=BASIS_AT,
            ),
            "disclosure": create_provider_result(
                status=ProviderStatus.PROVIDER_UNAVAILABLE,
                error_code="provider_unavailable",
                fetched_at=BASIS_AT,
            ),
        },
        documents_by_id={},
        data_mode="recorded",
        live_connectivity_checked=False,
    )

    validated = validate_source_gateway_result(
        result,
        required_sources=["news", "disclosure"],
    )

    assert validated.data_mode == "recorded"
    assert [
        item.status
        for item in validated.provider_results_by_source.values()
    ] == [
        ProviderStatus.NO_DATA,
        ProviderStatus.PROVIDER_UNAVAILABLE,
    ]


def test_gateway_validation_error_does_not_echo_document_id() -> None:
    sentinel = "credential-sentinel"
    document = _document(document_id=f"document:news:{sentinel}")
    result = SourceGatewayResult(
        documents=(document, document.model_copy(deep=True)),
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

    with pytest.raises(SourceGatewayValidationError) as exc_info:
        validate_source_gateway_result(result, required_sources=["news"])

    assert sentinel not in str(exc_info.value)
