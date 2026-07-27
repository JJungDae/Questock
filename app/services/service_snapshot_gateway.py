from __future__ import annotations

import math

from app.core.models import QueryPlan
from app.core.status import ProviderStatus
from app.providers.base import create_provider_result
from app.services.service_snapshot import (
    ServiceSnapshot,
    ServiceSnapshotValidationError,
    copy_service_snapshot,
)
from app.services.source_gateway import (
    SourceGatewayResult,
    SourceGatewayTimeoutDescriptor,
    validate_source_gateway_result,
)


class RecordedServiceSnapshotGateway:
    timeout_descriptor = SourceGatewayTimeoutDescriptor(
        data_mode="recorded",
        live_connectivity_checked=False,
    )

    def __init__(self, snapshot: ServiceSnapshot) -> None:
        self._snapshot = copy_service_snapshot(snapshot)

    async def fetch(
        self,
        plan: QueryPlan,
        *,
        query: str,
        timeout_seconds: float,
    ) -> SourceGatewayResult:
        if (
            not isinstance(plan, QueryPlan)
            or not isinstance(query, str)
            or not query.strip()
            or isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0
        ):
            raise ServiceSnapshotValidationError(
                "recorded snapshot request is invalid"
            )
        security_id = (
            None
            if plan.security is None
            else f"{plan.security.market}:{plan.security.ticker}"
        )
        selected = tuple(
            document.model_copy(deep=True)
            for document in self._snapshot.documents
            if security_id is not None
            and security_id in document.security_ids
            and document.source_type in plan.required_sources
        )
        provider_results = {}
        for source in plan.required_sources:
            source_documents = tuple(
                item for item in selected if item.source_type == source
            )
            if source_documents:
                provider_results[source] = create_provider_result(
                    status=ProviderStatus.OK,
                    data={
                        "document_ids": [
                            item.document_id for item in source_documents
                        ]
                    },
                    fetched_at=self._snapshot.basis_at,
                )
            else:
                provider_results[source] = create_provider_result(
                    status=ProviderStatus.NO_DATA,
                    fetched_at=self._snapshot.basis_at,
                )
        result = SourceGatewayResult(
            documents=selected,
            provider_results_by_source=provider_results,
            documents_by_id={
                item.document_id: item.model_copy(deep=True)
                for item in selected
            },
            data_mode="recorded",
            live_connectivity_checked=False,
        )
        return validate_source_gateway_result(
            result,
            required_sources=plan.required_sources,
        )


__all__ = ["RecordedServiceSnapshotGateway"]
