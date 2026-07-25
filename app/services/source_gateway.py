from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, Protocol, runtime_checkable

from app.core.models import FinancialDocument, ProviderResult, QueryPlan
from app.core.status import ProviderStatus
from app.providers.base import create_provider_result

DataMode = Literal["recorded", "live", "mixed", "unconfigured"]
TimeoutDataMode = Literal["recorded", "live", "unconfigured"]
_DATA_MODES = frozenset({"recorded", "live", "mixed", "unconfigured"})
_TIMEOUT_DATA_MODES = frozenset({"recorded", "live", "unconfigured"})


class SourceGatewayValidationError(ValueError):
    """Raised when a gateway violates the project-owned source contract."""


@dataclass(frozen=True)
class SourceGatewayResult:
    documents: tuple[FinancialDocument, ...]
    provider_results_by_source: Mapping[str, ProviderResult[Any]]
    documents_by_id: Mapping[str, FinancialDocument]
    data_mode: DataMode
    live_connectivity_checked: bool


@dataclass(frozen=True)
class SourceGatewayTimeoutDescriptor:
    data_mode: TimeoutDataMode
    live_connectivity_checked: bool

    def __post_init__(self) -> None:
        if (
            not isinstance(self.data_mode, str)
            or self.data_mode not in _TIMEOUT_DATA_MODES
            or type(self.live_connectivity_checked) is not bool
            or self.live_connectivity_checked != (self.data_mode == "live")
        ):
            raise SourceGatewayValidationError(
                "source gateway timeout descriptor is invalid"
            )


@runtime_checkable
class SourceGateway(Protocol):
    timeout_descriptor: SourceGatewayTimeoutDescriptor

    async def fetch(
        self,
        plan: QueryPlan,
        *,
        query: str,
        timeout_seconds: float,
    ) -> SourceGatewayResult: ...


class ExplicitUnconfiguredSourceGateway:
    timeout_descriptor = SourceGatewayTimeoutDescriptor(
        data_mode="unconfigured",
        live_connectivity_checked=False,
    )

    async def fetch(
        self,
        plan: QueryPlan,
        *,
        query: str,
        timeout_seconds: float,
    ) -> SourceGatewayResult:
        if not isinstance(plan, QueryPlan):
            raise SourceGatewayValidationError("source plan is invalid")
        results = {
            source: create_provider_result(
                status=ProviderStatus.PROVIDER_UNAVAILABLE,
                error_code="provider_unavailable",
            )
            for source in plan.required_sources
        }
        return SourceGatewayResult(
            documents=(),
            provider_results_by_source=results,
            documents_by_id={},
            data_mode="unconfigured",
            live_connectivity_checked=False,
        )


def create_source_gateway_timeout_result(
    descriptor: object,
    *,
    required_sources: Sequence[str],
) -> SourceGatewayResult:
    canonical_descriptor = _validate_timeout_descriptor(descriptor)
    if canonical_descriptor.data_mode == "unconfigured":
        status = ProviderStatus.PROVIDER_UNAVAILABLE
        error_code = "provider_unavailable"
    else:
        status = ProviderStatus.TIMEOUT
        error_code = "total_deadline_exceeded"
    result = SourceGatewayResult(
        documents=(),
        provider_results_by_source={
            source: create_provider_result(
                status=status,
                error_code=error_code,
            )
            for source in required_sources
        },
        documents_by_id={},
        data_mode=canonical_descriptor.data_mode,
        live_connectivity_checked=(
            canonical_descriptor.live_connectivity_checked
        ),
    )
    return validate_source_gateway_result(
        result,
        required_sources=required_sources,
    )


def validate_source_gateway_result(
    value: object,
    *,
    required_sources: Sequence[str],
) -> SourceGatewayResult:
    if not isinstance(value, SourceGatewayResult):
        raise SourceGatewayValidationError("source gateway result is invalid")
    if (
        not isinstance(value.documents, tuple)
        or not isinstance(value.provider_results_by_source, Mapping)
        or not isinstance(value.documents_by_id, Mapping)
        or value.data_mode not in _DATA_MODES
        or type(value.live_connectivity_checked) is not bool
    ):
        raise SourceGatewayValidationError("source gateway result is invalid")
    if tuple(value.provider_results_by_source) != tuple(required_sources):
        raise SourceGatewayValidationError("source gateway keys are invalid")

    provider_results: dict[str, ProviderResult[Any]] = {}
    for source in required_sources:
        result = value.provider_results_by_source.get(source)
        if not isinstance(result, ProviderResult):
            raise SourceGatewayValidationError("source provider result is invalid")
        provider_results[source] = result.model_copy(deep=True)

    documents: list[FinancialDocument] = []
    documents_by_id: dict[str, FinancialDocument] = {}
    for document in value.documents:
        if not isinstance(document, FinancialDocument):
            raise SourceGatewayValidationError("source documents are invalid")
        source_result = provider_results.get(document.source_type)
        if (
            source_result is None
            or source_result.status != ProviderStatus.OK
        ):
            raise SourceGatewayValidationError("source documents are invalid")
        if document.document_id in documents_by_id:
            raise SourceGatewayValidationError("source document IDs are duplicated")
        canonical = document.model_copy(deep=True)
        documents.append(canonical)
        documents_by_id[canonical.document_id] = canonical.model_copy(deep=True)

    if set(value.documents_by_id) != set(documents_by_id):
        raise SourceGatewayValidationError("source document mapping is inconsistent")
    for key, document in value.documents_by_id.items():
        if (
            not isinstance(key, str)
            or not isinstance(document, FinancialDocument)
            or key != document.document_id
            or document.model_dump(mode="python")
            != documents_by_id[key].model_dump(mode="python")
        ):
            raise SourceGatewayValidationError("source document mapping is inconsistent")

    _validate_data_mode(
        data_mode=value.data_mode,
        live_connectivity_checked=value.live_connectivity_checked,
        documents=documents,
        provider_results=provider_results,
    )

    return SourceGatewayResult(
        documents=tuple(item.model_copy(deep=True) for item in documents),
        provider_results_by_source=provider_results,
        documents_by_id={
            key: item.model_copy(deep=True)
            for key, item in documents_by_id.items()
        },
        data_mode=value.data_mode,
        live_connectivity_checked=value.live_connectivity_checked,
    )


def _validate_timeout_descriptor(
    value: object,
) -> SourceGatewayTimeoutDescriptor:
    if not isinstance(value, SourceGatewayTimeoutDescriptor):
        raise SourceGatewayValidationError(
            "source gateway timeout descriptor is invalid"
        )
    return SourceGatewayTimeoutDescriptor(
        data_mode=value.data_mode,
        live_connectivity_checked=value.live_connectivity_checked,
    )


def _validate_data_mode(
    *,
    data_mode: DataMode,
    live_connectivity_checked: bool,
    documents: Sequence[FinancialDocument],
    provider_results: Mapping[str, ProviderResult[Any]],
) -> None:
    if data_mode == "unconfigured":
        if (
            documents
            or live_connectivity_checked
            or any(
                result.status != ProviderStatus.PROVIDER_UNAVAILABLE
                for result in provider_results.values()
            )
        ):
            raise SourceGatewayValidationError("source data mode is invalid")
        return
    if data_mode == "recorded":
        if live_connectivity_checked:
            raise SourceGatewayValidationError("source data mode is invalid")
        return
    if data_mode == "live":
        if not live_connectivity_checked:
            raise SourceGatewayValidationError("source data mode is invalid")
        return
    # The current result contract has no per-document provenance proof.
    raise SourceGatewayValidationError("source data mode is invalid")


__all__ = [
    "DataMode",
    "ExplicitUnconfiguredSourceGateway",
    "SourceGateway",
    "SourceGatewayResult",
    "SourceGatewayTimeoutDescriptor",
    "SourceGatewayValidationError",
    "TimeoutDataMode",
    "create_source_gateway_timeout_result",
    "validate_source_gateway_result",
]
