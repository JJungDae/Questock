from __future__ import annotations

from app.core.models import QueryPlan
from app.core.status import ProviderStatus
from app.providers.base import create_provider_result
from app.services.m5_news_snapshot import load_m5_news_documents
from app.services.source_gateway import (
    SourceGateway,
    SourceGatewayResult,
    validate_source_gateway_result,
)


class M5RecordedSourceGateway:
    def __init__(
        self,
        base: SourceGateway,
    ) -> None:
        self._base = base
        self.timeout_descriptor = base.timeout_descriptor
        self._news_documents = load_m5_news_documents()

    async def fetch(
        self,
        plan: QueryPlan,
        *,
        query: str,
        timeout_seconds: float,
    ) -> SourceGatewayResult:
        base_result = await self._base.fetch(
            plan,
            query=query,
            timeout_seconds=timeout_seconds,
        )
        if (
            "news" not in plan.required_sources
            or plan.security is None
        ):
            return base_result
        security_id = (
            f"{plan.security.market}:{plan.security.ticker}"
        )
        additional = tuple(
            item.model_copy(deep=True)
            for item in self._news_documents
            if security_id in item.primary_security_ids
        )
        if not additional:
            return base_result
        documents = [
            item.model_copy(deep=True)
            for item in base_result.documents
        ]
        documents_by_id = {
            key: item.model_copy(deep=True)
            for key, item in base_result.documents_by_id.items()
        }
        for item in additional:
            if item.document_id in documents_by_id:
                continue
            documents.append(item)
            documents_by_id[item.document_id] = item.model_copy(
                deep=True
            )
        provider_results = {
            key: item.model_copy(deep=True)
            for key, item in (
                base_result.provider_results_by_source.items()
            )
        }
        news_documents = [
            item
            for item in documents
            if item.source_type == "news"
        ]
        news_base = provider_results.get("news")
        fetched_at = (
            news_base.fetched_at
            if news_base is not None
            else additional[-1].published_at
        )
        if fetched_at is None:
            fetched_at = additional[-1].published_at
        assert fetched_at is not None
        provider_results["news"] = create_provider_result(
            status=ProviderStatus.OK,
            data={
                "document_ids": [
                    item.document_id for item in news_documents
                ]
            },
            fetched_at=fetched_at,
        )
        combined = SourceGatewayResult(
            documents=tuple(documents),
            provider_results_by_source=provider_results,
            documents_by_id=documents_by_id,
            data_mode=base_result.data_mode,
            live_connectivity_checked=(
                base_result.live_connectivity_checked
            ),
        )
        return validate_source_gateway_result(
            combined,
            required_sources=plan.required_sources,
        )


__all__ = ["M5RecordedSourceGateway"]
