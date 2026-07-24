from __future__ import annotations

import asyncio
import math
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Callable

from app.answer.composer import AnswerComposer, CompositionResult
from app.api.schemas import (
    ChatRequest,
    ChatResponse,
    PublicCitationSummary,
    PublicContextBudgetSummary,
    PublicDecisionSummary,
    PublicEvidencePipelineSummary,
    PublicGenerationSummary,
    PublicProcessSummary,
    PublicQueryPlanSummary,
    PublicSecuritySummary,
    PublicSourceSummary,
)
from app.core.models import (
    Evidence,
    FinancialDocument,
    QueryPlan,
    RetrievalRequest,
    RetrievalResult,
)
from app.core.status import ProviderStatus, RetrievalStatus
from app.evidence.budget import ContextBudgetResult, select_evidence_context
from app.evidence.freshness import FreshnessResult, SEOUL_TZ, evaluate_freshness
from app.evidence.normalizer import normalize_financial_documents
from app.evidence.policy import EvidenceDecision, EvidencePolicy
from app.llm.base import LLMRequest, LLMResult, LLMStatus, create_llm_result
from app.planning.query_planner import QueryPlanner
from app.providers.base import create_provider_result
from app.retrieval import filter_evidence, retrieve_evidence
from app.services.source_gateway import (
    ExplicitUnconfiguredSourceGateway,
    SourceGateway,
    SourceGatewayResult,
    validate_source_gateway_result,
)

_DEFAULT_DEADLINE_SECONDS = 20.0
_DEGRADATION_WARNING = "llm_generation_degraded"
_FALLBACK_SECURITY_ID = "KRX:005930"


class ChatServiceError(RuntimeError):
    """Raised for sanitized M3-01 orchestration failures."""


class _DisabledLLMClient:
    async def complete(
        self,
        request: LLMRequest,
        *,
        timeout_seconds: float,
    ) -> LLMResult:
        return create_llm_result(
            status=LLMStatus.PROVIDER_UNAVAILABLE,
            model="gemini/gemini-2.5-flash",
            provider="gemini",
            latency_ms=0,
        )


class ChatService:
    def __init__(
        self,
        *,
        source_gateway: SourceGateway | None = None,
        composer: AnswerComposer | None = None,
        deadline_seconds: float = _DEFAULT_DEADLINE_SECONDS,
        utc_now: Callable[[], datetime] | None = None,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if (
            type(deadline_seconds) not in {int, float}
            or not math.isfinite(deadline_seconds)
            or deadline_seconds <= 0
            or deadline_seconds > _DEFAULT_DEADLINE_SECONDS
        ):
            raise ValueError("chat deadline is invalid")
        self._source_gateway = source_gateway or ExplicitUnconfiguredSourceGateway()
        self._composer = composer or AnswerComposer(_DisabledLLMClient())
        self._deadline_seconds = float(deadline_seconds)
        self._utc_now = utc_now or (lambda: datetime.now(UTC))
        self._monotonic = monotonic

    async def chat(self, request: ChatRequest) -> ChatResponse:
        if not isinstance(request, ChatRequest):
            raise ChatServiceError("chat request is invalid")
        basis_at = _aware_utc(self._utc_now())
        started_at = self._monotonic()
        try:
            plan = QueryPlanner(
                basis_date=basis_at.astimezone(SEOUL_TZ).date()
            ).plan(request.message)
            gateway = await self._source_data(
                plan,
                query=request.message,
                started_at=started_at,
            )
            pipeline = _run_evidence_pipeline(
                query=request.message,
                plan=plan,
                gateway=gateway,
                basis_at=basis_at,
            )
            composition = await self._compose(
                request=request,
                plan=plan,
                pipeline=pipeline,
                started_at=started_at,
            )
            return _build_response(
                plan=plan,
                gateway=gateway,
                pipeline=pipeline,
                composition=composition,
                basis_at=basis_at,
            )
        except ChatServiceError:
            raise
        except Exception:
            raise ChatServiceError("chat service unavailable") from None

    async def _source_data(
        self,
        plan: QueryPlan,
        *,
        query: str,
        started_at: float,
    ) -> SourceGatewayResult:
        if plan.requires_clarification or not plan.required_sources:
            return SourceGatewayResult(
                documents=(),
                provider_results_by_source={},
                documents_by_id={},
                data_mode="unconfigured",
                live_connectivity_checked=False,
            )
        remaining = self._remaining(started_at)
        try:
            value = await asyncio.wait_for(
                self._source_gateway.fetch(
                    plan.model_copy(deep=True),
                    query=query,
                    timeout_seconds=remaining,
                ),
                timeout=remaining,
            )
        except TimeoutError:
            results = {
                source: create_provider_result(
                    status=ProviderStatus.TIMEOUT,
                    error_code="total_deadline_exceeded",
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
        return validate_source_gateway_result(
            value,
            required_sources=plan.required_sources,
        )

    async def _compose(
        self,
        *,
        request: ChatRequest,
        plan: QueryPlan,
        pipeline: "_PipelineResult",
        started_at: float,
    ) -> CompositionResult:
        if (
            pipeline.decision.status not in {"complete", "partial"}
            or not pipeline.budget.evidence
        ):
            return self._composer.compose_fixed(
                plan=plan,
                selected_evidence=pipeline.budget.evidence,
                fallback_reason=(
                    "blocked"
                    if pipeline.decision.status == "blocked"
                    else "provider_failed"
                    if pipeline.decision.status == "provider_failed"
                    else "no_evidence"
                ),
            )
        remaining = self._remaining(started_at)
        try:
            return await asyncio.wait_for(
                self._composer.compose(
                    question=request.message,
                    plan=plan,
                    selected_evidence=pipeline.budget.evidence,
                    documents_by_id=pipeline.documents_by_id,
                    timeout_seconds=remaining,
                ),
                timeout=remaining,
            )
        except TimeoutError:
            timeout_result = create_llm_result(
                status=LLMStatus.TIMEOUT,
                model="gemini/gemini-2.5-flash",
                provider="gemini",
                latency_ms=self._deadline_seconds * 1000,
            )
            return self._composer.compose_fixed(
                plan=plan,
                selected_evidence=pipeline.budget.evidence,
                llm_result=timeout_result,
            )

    def _remaining(self, started_at: float) -> float:
        remaining = self._deadline_seconds - (self._monotonic() - started_at)
        if remaining <= 0:
            raise ChatServiceError("chat request deadline exceeded")
        return remaining


class _PipelineResult:
    def __init__(
        self,
        *,
        documents_by_id: Mapping[str, FinancialDocument],
        normalized: tuple[Evidence, ...],
        hard_filtered: tuple[Evidence, ...],
        freshness: FreshnessResult,
        retrieval: RetrievalResult,
        decision: EvidenceDecision,
        budget: ContextBudgetResult,
    ) -> None:
        self.documents_by_id = {
            key: value.model_copy(deep=True)
            for key, value in documents_by_id.items()
        }
        self.normalized = tuple(item.model_copy(deep=True) for item in normalized)
        self.hard_filtered = tuple(
            item.model_copy(deep=True) for item in hard_filtered
        )
        self.freshness = freshness
        self.retrieval = retrieval.model_copy(deep=True)
        self.decision = decision
        self.budget = budget


def _run_evidence_pipeline(
    *,
    query: str,
    plan: QueryPlan,
    gateway: SourceGatewayResult,
    basis_at: datetime,
) -> _PipelineResult:
    if plan.requires_clarification:
        request = RetrievalRequest(
            query=query,
            security_id=_FALLBACK_SECURITY_ID,
            source_types=[],
        )
        freshness = evaluate_freshness(
            [],
            request,
            documents_by_id={},
            basis_at=basis_at,
        )
        retrieval = RetrievalResult(
            evidence=[],
            status=RetrievalStatus.EMPTY,
            strategy="lexical-bm25-m2-03-v1",
            low_relevance=False,
            diagnostics={},
        )
        decision = EvidencePolicy().evaluate(plan, {}, freshness, retrieval)
        return _PipelineResult(
            documents_by_id={},
            normalized=(),
            hard_filtered=(),
            freshness=freshness,
            retrieval=retrieval,
            decision=decision,
            budget=select_evidence_context([]),
        )

    documents = tuple(item.model_copy(deep=True) for item in gateway.documents)
    documents_by_id = {
        key: item.model_copy(deep=True)
        for key, item in gateway.documents_by_id.items()
    }
    normalized = tuple(normalize_financial_documents(documents))
    request = RetrievalRequest(
        query=query,
        security_id=_request_security_id(plan, documents),
        source_types=list(plan.required_sources),
        date_range=plan.date_range.model_copy(deep=True) if plan.date_range else None,
    )
    hard_filtered = tuple(
        filter_evidence(
            normalized,
            request,
            documents_by_id=documents_by_id,
        )
    )
    freshness = evaluate_freshness(
        hard_filtered,
        request,
        documents_by_id=documents_by_id,
        basis_at=basis_at,
    )
    retrieval = retrieve_evidence(
        freshness.evidence,
        request,
        documents_by_id=documents_by_id,
    )
    decision = EvidencePolicy().evaluate(
        plan,
        gateway.provider_results_by_source,
        freshness,
        retrieval,
    )
    budget = select_evidence_context(decision.evidence)
    return _PipelineResult(
        documents_by_id=documents_by_id,
        normalized=normalized,
        hard_filtered=hard_filtered,
        freshness=freshness,
        retrieval=retrieval,
        decision=decision,
        budget=budget,
    )


def _request_security_id(
    plan: QueryPlan,
    documents: tuple[FinancialDocument, ...],
) -> str:
    if plan.security is not None:
        return f"{plan.security.market}:{plan.security.ticker}"
    for document in documents:
        ids = document.primary_security_ids + document.mentioned_security_ids
        if ids:
            return ids[0]
    return _FALLBACK_SECURITY_ID


def _build_response(
    *,
    plan: QueryPlan,
    gateway: SourceGatewayResult,
    pipeline: _PipelineResult,
    composition: CompositionResult,
    basis_at: datetime,
) -> ChatResponse:
    warnings = [item.code for item in pipeline.decision.warnings]
    if (
        composition.llm_result is not None
        and composition.llm_result.status != LLMStatus.OK
    ):
        warnings.append(_DEGRADATION_WARNING)
    summary = _build_process_summary(
        plan=plan,
        gateway=gateway,
        pipeline=pipeline,
        composition=composition,
    )
    return ChatResponse(
        status=pipeline.decision.status,
        security=plan.security.model_copy(deep=True) if plan.security else None,
        basis_date=basis_at.astimezone(SEOUL_TZ).date(),
        answer_sections=composition.answer_sections.model_copy(deep=True),
        evidence=[
            item.model_copy(deep=True) for item in pipeline.budget.evidence
        ],
        warnings=warnings,
        missing_sources=list(pipeline.decision.missing_sources),
        diagnostics_public=summary,
    )


def _build_process_summary(
    *,
    plan: QueryPlan,
    gateway: SourceGatewayResult,
    pipeline: _PipelineResult,
    composition: CompositionResult,
) -> PublicProcessSummary:
    source_counts = {
        source: sum(
            1 for item in gateway.documents if item.source_type == source
        )
        for source in plan.required_sources
    }
    sources = []
    for source in plan.required_sources:
        result = gateway.provider_results_by_source[source]
        sources.append(
            PublicSourceSummary(
                source_type=source,
                provider_status=result.status,
                document_count=source_counts[source],
                from_cache=result.from_cache,
            )
        )
    diagnostics = pipeline.budget.diagnostics
    llm_result = composition.llm_result
    return PublicProcessSummary(
        data_mode=gateway.data_mode,
        live_connectivity_checked=gateway.live_connectivity_checked,
        security=PublicSecuritySummary(
            resolution_status="resolved" if plan.security else "not_found",
            security_id=(
                f"{plan.security.market}:{plan.security.ticker}"
                if plan.security
                else None
            ),
        ),
        query_plan=PublicQueryPlanSummary(
            intent=plan.intent,
            required_sources=list(plan.required_sources),
            date_start=plan.date_range.start if plan.date_range else None,
            date_end=plan.date_range.end if plan.date_range else None,
        ),
        sources=sources,
        evidence_pipeline=PublicEvidencePipelineSummary(
            normalized_count=len(pipeline.normalized),
            hard_filtered_count=len(pipeline.hard_filtered),
            freshness_retained_count=len(pipeline.freshness.evidence),
            freshness_warning_codes=[
                item.code for item in pipeline.freshness.warnings
            ],
            retrieval_status=pipeline.retrieval.status,
            retrieval_selected_count=len(pipeline.retrieval.evidence),
        ),
        decision=PublicDecisionSummary(
            evidence_decision_status=pipeline.decision.status,
            satisfied_sources=list(pipeline.decision.satisfied_sources),
            missing_sources=list(pipeline.decision.missing_sources),
            no_data_sources=list(pipeline.decision.no_data_sources),
            failed_sources=list(pipeline.decision.failed_sources),
        ),
        context_budget=PublicContextBudgetSummary(
            input_count=diagnostics.input_count,
            unique_count=diagnostics.unique_count,
            selected_count=diagnostics.selected_count,
            duplicate_drop_count=diagnostics.duplicate_drop_count,
            source_cap_drop_count=diagnostics.source_cap_drop_count,
            count_cap_drop_count=diagnostics.count_cap_drop_count,
            context_drop_count=diagnostics.context_drop_count,
            estimated_context_tokens=diagnostics.estimated_context_tokens,
            estimated_context_chars=diagnostics.estimated_evidence_chars,
        ),
        citation=PublicCitationSummary(
            claim_count=len(composition.claims),
            citation_count=len(composition.citations.citations),
            rejection_count=(
                len(composition.citations.rejections)
                + composition.citation_rejection_count
            ),
        ),
        generation=PublicGenerationSummary(
            mode=composition.generation_mode,
            llm_status=llm_result.status if llm_result else None,
            model=llm_result.model if llm_result else None,
            live_verified=False,
        ),
    )


def _aware_utc(value: object) -> datetime:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ChatServiceError("basis time is invalid")
    return value.astimezone(UTC)


__all__ = ["ChatService", "ChatServiceError"]
