from __future__ import annotations

import asyncio
import math
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Callable
from uuid import uuid4

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
    SessionContext,
)
from app.core.resolver import SecurityResolver
from app.core.status import RetrievalStatus
from app.evidence.budget import (
    ContextBudgetResult,
    LLMCallBudget,
    select_evidence_context,
)
from app.evidence.freshness import FreshnessResult, SEOUL_TZ, evaluate_freshness
from app.evidence.freshness import FreshnessWindow
from app.evidence.normalizer import normalize_financial_documents
from app.evidence.policy import EvidenceDecision, EvidencePolicy
from app.llm.base import LLMRequest, LLMResult, LLMStatus, create_llm_result
from app.retrieval import filter_evidence, retrieve_evidence
from app.services.planning_observation import (
    PublicResolutionStatus,
    build_observed_query_plan,
)
from app.services.glossary_service import (
    GlossaryPipelineResult,
    GlossaryService,
    select_glossary_context,
)
from app.services.observability import (
    JsonLogObservationSink,
    ObservationSink,
    RequestObservation,
    fallback_used_for_generation_mode,
)
from app.services.source_gateway import (
    ExplicitUnconfiguredSourceGateway,
    SourceGateway,
    SourceGatewayResult,
    create_source_gateway_timeout_result,
    validate_source_gateway_result,
)
from app.services.session_store import InMemorySessionStore, SessionStoreError

_DEFAULT_DEADLINE_SECONDS = 20.0
_DEGRADATION_WARNING = "llm_generation_degraded"
_DEADLINE_WARNING = "request_deadline_exceeded"
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
        resolver: SecurityResolver | None = None,
        glossary_service: GlossaryService | None = None,
        session_store: InMemorySessionStore | None = None,
        call_budget_factory: Callable[[], LLMCallBudget] | None = None,
        observation_sink: ObservationSink | None = None,
        request_id_factory: Callable[[], str] | None = None,
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
        self._source_gateway = (
            source_gateway or ExplicitUnconfiguredSourceGateway()
        )
        self._composer = composer or AnswerComposer(_DisabledLLMClient())
        self._resolver = resolver or SecurityResolver()
        self._glossary_service = glossary_service
        self._session_store = session_store or InMemorySessionStore()
        self._call_budget_factory = (
            call_budget_factory
            if call_budget_factory is not None
            else lambda: LLMCallBudget(max_calls=1)
        )
        if observation_sink is not None and not isinstance(
            observation_sink,
            ObservationSink,
        ):
            raise ValueError("observation sink is invalid")
        if request_id_factory is not None and not callable(
            request_id_factory
        ):
            raise ValueError("request ID factory is invalid")
        self._observation_sink = (
            observation_sink
            if observation_sink is not None
            else JsonLogObservationSink()
        )
        self._request_id_factory = (
            request_id_factory
            if request_id_factory is not None
            else lambda: uuid4().hex
        )
        self._deadline_seconds = float(deadline_seconds)
        self._utc_now = utc_now or (lambda: datetime.now(UTC))
        self._monotonic = monotonic

    async def chat(self, request: ChatRequest) -> ChatResponse:
        if not isinstance(request, ChatRequest):
            raise ChatServiceError("chat request is invalid")
        try:
            async with self._session_store.serialized(request.session_id):
                return await self._chat_serialized(request)
        except ChatServiceError:
            raise
        except SessionStoreError:
            raise ChatServiceError("chat service unavailable") from None
        except Exception:
            raise ChatServiceError("chat service unavailable") from None

    async def _chat_serialized(self, request: ChatRequest) -> ChatResponse:
        if not isinstance(request, ChatRequest):
            raise ChatServiceError("chat request is invalid")
        basis_at = _aware_utc(self._utc_now())
        started_at = self._monotonic()
        try:
            observed = build_observed_query_plan(
                request.message,
                basis_date=basis_at.astimezone(SEOUL_TZ).date(),
                resolver=self._resolver,
                session=self._session_store.get(request.session_id),
            )
            plan = observed.plan
            call_budget = self._new_call_budget()
            if (
                plan.intent == "financial_term"
                and not plan.requires_clarification
            ):
                glossary = self._glossary_data(
                    request.message,
                    basis_at=basis_at,
                )
                gateway = _glossary_gateway(glossary)
                pipeline = _run_glossary_pipeline(
                    plan=plan,
                    result=glossary,
                    basis_at=basis_at,
                )
            else:
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
            deadline_exhausted = self._deadline_reached(started_at)
            deadline_exhausted = (
                deadline_exhausted or self._deadline_reached(started_at)
            )
            composition = await self._compose(
                request=request,
                plan=plan,
                pipeline=pipeline,
                started_at=started_at,
                call_budget=call_budget,
                deadline_exhausted=deadline_exhausted,
            )
            deadline_exhausted = (
                deadline_exhausted or self._deadline_reached(started_at)
            )
            composition = self._deadline_safe_composition(
                plan=plan,
                pipeline=pipeline,
                composition=composition,
                deadline_exhausted=deadline_exhausted,
            )
            response = _build_response(
                plan=plan,
                gateway=gateway,
                pipeline=pipeline,
                composition=composition,
                basis_at=basis_at,
                resolution_status=observed.resolution_status,
                resolved_security_id=observed.security_id,
                deadline_exhausted=deadline_exhausted,
            )
            if self._deadline_reached(started_at):
                deadline_exhausted = True
                composition = self._deadline_safe_composition(
                    plan=plan,
                    pipeline=pipeline,
                    composition=composition,
                    deadline_exhausted=True,
                )
                response = _build_response(
                    plan=plan,
                    gateway=gateway,
                    pipeline=pipeline,
                    composition=composition,
                    basis_at=basis_at,
                    resolution_status=observed.resolution_status,
                    resolved_security_id=observed.security_id,
                    deadline_exhausted=deadline_exhausted,
                )
            self._save_session_context(request.session_id, plan)
            self._emit_terminal_observation(
                plan=plan,
                gateway=gateway,
                pipeline=pipeline,
                composition=composition,
                call_budget=call_budget,
                started_at=started_at,
            )
            return response
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
            return create_source_gateway_timeout_result(
                getattr(
                    self._source_gateway,
                    "timeout_descriptor",
                    None,
                ),
                required_sources=plan.required_sources,
            )
        return validate_source_gateway_result(
            value,
            required_sources=plan.required_sources,
        )

    def _glossary_data(
        self,
        query: str,
        *,
        basis_at: datetime,
    ) -> GlossaryPipelineResult:
        if self._glossary_service is None:
            self._glossary_service = GlossaryService()
        value = self._glossary_service.lookup(
            query,
            fetched_at=basis_at,
        )
        if not isinstance(value, GlossaryPipelineResult):
            raise ChatServiceError("glossary service unavailable")
        return value

    async def _compose(
        self,
        *,
        request: ChatRequest,
        plan: QueryPlan,
        pipeline: "_PipelineResult",
        started_at: float,
        call_budget: LLMCallBudget,
        deadline_exhausted: bool,
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
        if deadline_exhausted or self._deadline_reached(started_at):
            return self._composer.compose_fixed(
                plan=plan,
                selected_evidence=pipeline.budget.evidence,
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
                    call_budget=call_budget,
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

    def _new_call_budget(self) -> LLMCallBudget:
        try:
            budget = self._call_budget_factory()
            snapshot = budget.snapshot()
        except Exception:
            raise ChatServiceError("LLM call budget is invalid") from None
        if not isinstance(budget, LLMCallBudget) or snapshot.max_calls != 1:
            raise ChatServiceError("LLM call budget is invalid")
        return budget

    def _save_session_context(self, session_id: str, plan: QueryPlan) -> None:
        if (
            plan.requires_clarification
            or plan.intent in {"prohibited_advice", "out_of_scope"}
        ):
            return
        current = self._session_store.get(session_id) or SessionContext()
        security_id = current.current_security_id
        if plan.security is not None:
            security_id = f"{plan.security.market}:{plan.security.ticker}"
        date_range = current.current_date_range
        if plan.intent != "financial_term":
            date_range = (
                plan.date_range.model_copy(deep=True)
                if plan.date_range is not None
                else None
            )
        self._session_store.put(
            session_id,
            SessionContext(
                current_security_id=security_id,
                current_date_range=date_range,
                previous_intent=plan.intent,
                previous_source_types=list(plan.required_sources),
            ),
        )

    def _emit_terminal_observation(
        self,
        *,
        plan: QueryPlan,
        gateway: SourceGatewayResult,
        pipeline: "_PipelineResult",
        composition: CompositionResult,
        call_budget: LLMCallBudget,
        started_at: float,
    ) -> None:
        try:
            request_id = self._request_id_factory()
            security_id = (
                f"{plan.security.market}:{plan.security.ticker}"
                if plan.security is not None
                else None
            )
            elapsed_ms = (
                self._monotonic() - started_at
            ) * 1000
            observation = RequestObservation(
                request_id=request_id,
                intent=plan.intent,
                security_id=security_id,
                provider_statuses=tuple(
                    (
                        source,
                        str(
                            gateway.provider_results_by_source[
                                source
                            ].status
                        ),
                    )
                    for source in plan.required_sources
                ),
                evidence_count=len(pipeline.budget.evidence),
                retrieval_strategy=pipeline.retrieval.strategy,
                evidence_decision=str(pipeline.decision.status),
                total_latency_ms=round(elapsed_ms, 3),
                llm_call_count=call_budget.snapshot().calls_used,
                fallback_used=fallback_used_for_generation_mode(
                    composition.generation_mode
                ),
            )
            self._observation_sink.emit(observation)
        except Exception:
            return

    def _deadline_safe_composition(
        self,
        *,
        plan: QueryPlan,
        pipeline: "_PipelineResult",
        composition: CompositionResult,
        deadline_exhausted: bool,
    ) -> CompositionResult:
        if not deadline_exhausted or composition.generation_mode != "llm":
            return composition
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

    def _deadline_reached(self, started_at: float) -> bool:
        return self._monotonic() - started_at >= self._deadline_seconds

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


def _glossary_gateway(
    result: GlossaryPipelineResult,
) -> SourceGatewayResult:
    return SourceGatewayResult(
        documents=(),
        provider_results_by_source={
            "glossary": result.provider_result.model_copy(deep=True)
        },
        documents_by_id={},
        data_mode=result.data_mode,
        live_connectivity_checked=result.live_connectivity_checked,
    )


def _run_glossary_pipeline(
    *,
    plan: QueryPlan,
    result: GlossaryPipelineResult,
    basis_at: datetime,
) -> _PipelineResult:
    if (
        result.selected_count != len(result.evidence)
        or result.retrieval_status
        not in {RetrievalStatus.OK, RetrievalStatus.EMPTY}
        or (
            result.retrieval_status == RetrievalStatus.OK
            and not result.evidence
        )
        or (
            result.retrieval_status == RetrievalStatus.EMPTY
            and result.evidence
        )
    ):
        raise ChatServiceError("glossary service unavailable")
    freshness_evidence = tuple(
        item.model_copy(deep=True, update={"retrieval_score": None})
        for item in result.evidence
    )
    freshness = FreshnessResult(
        basis_at=basis_at,
        basis_date=basis_at.astimezone(SEOUL_TZ).date(),
        windows=(
            FreshnessWindow(
                source_type="glossary",
                start=None,
                end=None,
                applied_by="none",
            ),
        ),
        evidence=freshness_evidence,
        warnings=(),
        latest_effective_disclosure_at=None,
    )
    retrieval = RetrievalResult(
        evidence=[
            item.model_copy(deep=True) for item in result.evidence
        ],
        status=result.retrieval_status,
        strategy=result.strategy,
        low_relevance=False,
        diagnostics={},
    )
    decision = EvidencePolicy().evaluate(
        plan,
        {"glossary": result.provider_result},
        freshness,
        retrieval,
    )
    budget = select_glossary_context(decision.evidence)
    return _PipelineResult(
        documents_by_id={},
        normalized=result.evidence,
        hard_filtered=result.evidence,
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
    resolution_status: PublicResolutionStatus,
    resolved_security_id: str | None,
    deadline_exhausted: bool,
) -> ChatResponse:
    warnings = [item.code for item in pipeline.decision.warnings]
    if deadline_exhausted:
        warnings.append(_DEADLINE_WARNING)
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
        resolution_status=resolution_status,
        resolved_security_id=resolved_security_id,
    )
    response_status = pipeline.decision.status
    if response_status == "complete" and not composition.public_evidence:
        response_status = "no_evidence"
    return ChatResponse(
        status=response_status,
        security=plan.security.model_copy(deep=True) if plan.security else None,
        basis_date=basis_at.astimezone(SEOUL_TZ).date(),
        answer_sections=composition.answer_sections.model_copy(deep=True),
        evidence=[
            item.model_copy(deep=True) for item in composition.public_evidence
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
    resolution_status: PublicResolutionStatus,
    resolved_security_id: str | None,
) -> PublicProcessSummary:
    source_counts = {}
    for source in plan.required_sources:
        if source == "glossary" and plan.intent == "financial_term":
            source_counts[source] = len(pipeline.normalized)
        else:
            source_counts[source] = sum(
                1 for item in gateway.documents if item.source_type == source
            )
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
            resolution_status=resolution_status,
            security_id=resolved_security_id,
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
