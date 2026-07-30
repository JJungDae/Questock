from __future__ import annotations

import asyncio
import hashlib
import math
import re
import time
from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime
from typing import Callable
from uuid import uuid4

from app.answer.composer import AnswerComposer, CompositionResult
from app.answer.models import AnswerSections
from app.api.schemas import (
    ChatRequest,
    ChatResponse,
    PublicCitationSummary,
    PublicContextBudgetSummary,
    PublicDecisionSummary,
    PublicEvidenceComparison,
    PublicEvidencePipelineSummary,
    PublicGenerationSummary,
    PublicMarketSnapshot,
    PublicProcessSummary,
    PublicQueryPlanSummary,
    PublicSecuritySummary,
    PublicSourceSummary,
)
from app.config import APPROVED_LLM_MODEL
from app.core.models import (
    Evidence,
    FinancialDocument,
    MarketSnapshot,
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
    ObservedQueryPlan,
    PublicResolutionStatus,
    build_observed_query_plan,
)
from app.services.hybrid_intent_router import (
    HybridIntentRouter,
    HybridRoutingResult,
)
from app.services.market_snapshot_schema import checkpoint_id
from app.services.m5_d1_evidence_comparison import (
    M5D1EvidenceComparisonStore,
)
from app.services.market_snapshot_store import (
    MarketSnapshotStoreError,
    RecordedMarketSnapshotStore,
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
from app.services.request_protection import (
    RequestProtectionError,
    RequestProtectionLimitError,
    RequestProtector,
)
from app.services.response_cache import (
    ResponseCache,
    ResponseCacheError,
)
from app.services.source_gateway import (
    ExplicitUnconfiguredSourceGateway,
    SourceGateway,
    SourceGatewayResult,
    create_source_gateway_timeout_result,
    validate_source_gateway_result,
)
from app.services.session_store import InMemorySessionStore, SessionStoreError

_DEFAULT_DEADLINE_SECONDS = 30.0
_DEGRADATION_WARNING = "llm_generation_degraded"
_DEADLINE_WARNING = "request_deadline_exceeded"
_FALLBACK_SECURITY_ID = "KRX:005930"
_SAFE_RUNTIME_TOKEN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_EVIDENCE_COMPARISON_QUERY = re.compile(
    r"(?:같은\s*사건|서로\s*다른\s*사건|반복|재탕|재인용|"
    r"독립\s*(?:기사|보도|근거)|원출처|중복\s*(?:기사|보도)|"
    r"(?:뉴스|기사|보도|근거)(?:의|를|을)?\s*(?:대조|비교))",
    re.IGNORECASE,
)
_COMPARISON_TERM = re.compile(
    r"[A-Za-z][A-Za-z0-9.+-]{2,}|[가-힣0-9]{2,}",
    re.IGNORECASE,
)
_FOCUS_QUERY_TERMS: dict[str, tuple[str, ...]] = {
    "general": ("최근", "이슈", "실적", "매출", "영업이익", "전망", "위험", "기술", "배당"),
    "recent_events": ("최근", "이슈", "뉴스", "보도", "실적", "전망"),
    "positive": ("기대", "성장", "수요", "공급", "계약", "기술", "배당", "주주환원", "모멘텀"),
    "risk": ("위험", "리스크", "우려", "변동성", "둔화", "하락", "불확실성"),
    "performance": ("실적", "매출", "영업이익", "순이익", "현금흐름", "가이던스"),
    "business": ("사업", "부문", "제품", "매출", "생산", "수주"),
    "technology": ("기술", "제품", "연구개발", "특허", "HBM", "로봇", "전기차"),
    "outlook": ("전망", "예상", "가이던스", "촉매", "위험", "불확실성"),
    "shareholder_return": ("배당", "주주환원", "자사주", "현금흐름"),
    "disclosure": ("공시", "분기보고서", "사업보고서", "실적", "위험"),
    "research_view": ("리포트", "전망", "예상", "목표", "촉매", "위험"),
    "balanced": ("실적", "호재", "위험", "전망", "기술", "배당"),
    "term": (),
    "price": (),
    "price_move": (
        "가격",
        "상승",
        "하락",
        "배경",
        "뉴스",
        "공시",
        "전망",
        "위험",
        "HBM",
        "반도체",
        "수주",
        "공급",
        "실적",
        "제품",
        "기술",
        "투자",
        "생산",
        "판매",
        "동맹",
        "지분",
    ),
}


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
            model=APPROVED_LLM_MODEL,
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
        request_protector: RequestProtector | None = None,
        response_cache: ResponseCache | None = None,
        call_budget_factory: Callable[[], LLMCallBudget] | None = None,
        observation_sink: ObservationSink | None = None,
        request_id_factory: Callable[[], str] | None = None,
        deadline_seconds: float = _DEFAULT_DEADLINE_SECONDS,
        utc_now: Callable[[], datetime] | None = None,
        monotonic: Callable[[], float] = time.monotonic,
        snapshot_id: str = "runtime-unconfigured",
        model_fingerprint: str = "disabled",
        live_llm_enabled: bool = False,
        market_snapshot_store: RecordedMarketSnapshotStore | None = None,
        intent_router: HybridIntentRouter | None = None,
        evidence_comparison_store: M5D1EvidenceComparisonStore | None = None,
    ) -> None:
        if (
            type(deadline_seconds) not in {int, float}
            or not math.isfinite(deadline_seconds)
            or deadline_seconds <= 0
            or deadline_seconds > _DEFAULT_DEADLINE_SECONDS
        ):
            raise ValueError("chat deadline is invalid")
        if (
            not isinstance(snapshot_id, str)
            or not _SAFE_RUNTIME_TOKEN.fullmatch(snapshot_id)
            or not isinstance(model_fingerprint, str)
            or not _SAFE_RUNTIME_TOKEN.fullmatch(model_fingerprint)
            or type(live_llm_enabled) is not bool
        ):
            raise ValueError("chat runtime identity is invalid")
        self._source_gateway = (
            source_gateway or ExplicitUnconfiguredSourceGateway()
        )
        self._composer = composer or AnswerComposer(_DisabledLLMClient())
        self._resolver = resolver or SecurityResolver()
        self._glossary_service = glossary_service
        self._session_store = session_store or InMemorySessionStore()
        self._request_protector = request_protector or RequestProtector()
        self._response_cache = response_cache or ResponseCache()
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
        self._snapshot_id = snapshot_id
        self._model_fingerprint = model_fingerprint
        self._live_llm_enabled = live_llm_enabled
        self._market_snapshot_store = market_snapshot_store
        self._intent_router = intent_router or HybridIntentRouter()
        self._evidence_comparison_store = evidence_comparison_store

    async def chat(
        self,
        request: ChatRequest,
        *,
        client_key: str | None = None,
    ) -> ChatResponse:
        if not isinstance(request, ChatRequest):
            raise ChatServiceError("chat request is invalid")
        try:
            basis_at = _request_basis_at(request, self._utc_now)
            checkpoint = (
                checkpoint_id(basis_at)
                if request.as_of is not None
                else "legacy"
            )
            session_id = _time_scoped_session_id(
                request.session_id,
                checkpoint,
            )
            async with self._session_store.serialized(session_id):
                revision = self._session_store.revision(
                    session_id
                )
                cached = self._response_cache.get(
                    session_id=session_id,
                    snapshot_id=self._snapshot_id,
                    question=request.message,
                    revision=revision,
                    model_fingerprint=self._model_fingerprint,
                    checkpoint_id=checkpoint,
                )
                if cached is not None:
                    self._emit_cached_observation(cached.observation)
                    return cached.response.model_copy(deep=True)
                return await self._chat_serialized(
                    request,
                    client_key=client_key,
                    basis_at=basis_at,
                    checkpoint=checkpoint,
                    session_id=session_id,
                )
        except ChatServiceError:
            raise
        except (
            RequestProtectionError,
            ResponseCacheError,
            SessionStoreError,
        ):
            raise ChatServiceError("chat service unavailable") from None
        except Exception:
            raise ChatServiceError("chat service unavailable") from None

    async def _chat_serialized(
        self,
        request: ChatRequest,
        *,
        client_key: str | None,
        basis_at: datetime,
        checkpoint: str,
        session_id: str,
    ) -> ChatResponse:
        if not isinstance(request, ChatRequest):
            raise ChatServiceError("chat request is invalid")
        started_at = self._monotonic()
        try:
            deterministic = build_observed_query_plan(
                request.message,
                basis_date=basis_at.astimezone(SEOUL_TZ).date(),
                resolver=self._resolver,
                session=self._session_store.get(session_id),
            )
            routing = await self._route_intent(
                request.message,
                deterministic,
                basis_at=basis_at,
                started_at=started_at,
                client_key=client_key,
            )
            observed = routing.observed
            plan = observed.plan
            market_snapshot = self._market_snapshot(
                plan,
                basis_at=basis_at,
            )
            if plan.intent == "price" and not plan.requires_clarification:
                response = _build_price_only_response(
                    plan=plan,
                    snapshot=market_snapshot,
                    basis_at=basis_at,
                    resolution_status=observed.resolution_status,
                    resolved_security_id=observed.security_id,
                )
                self._save_session_context(session_id, plan)
                self._record_session_exchange(
                    request=request,
                    response=response,
                    plan=plan,
                    session_id=session_id,
                )
                self._emit_price_observation(
                    plan=plan,
                    snapshot=market_snapshot,
                    routing=routing,
                    started_at=started_at,
                )
                return response
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
            explicit_comparison = (
                _EVIDENCE_COMPARISON_QUERY.search(request.message)
                is not None
            )
            comparison = self._select_evidence_comparison(
                query=request.message,
                plan=plan,
                basis_at=basis_at,
            )
            if explicit_comparison and comparison is not None:
                pipeline = _augment_pipeline_with_comparison(
                    pipeline,
                    comparison,
                    security_id=(
                        f"{plan.security.market}:{plan.security.ticker}"
                        if plan.security is not None
                        else None
                    ),
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
                client_key=client_key,
                conversation_context=(
                    self._session_store.conversation_context(
                        session_id
                    )
                ),
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
                live_llm_enabled=self._live_llm_enabled,
                market_snapshot=market_snapshot,
            )
            response = self._attach_evidence_comparison(
                response=response,
                query=request.message,
                plan=plan,
                comparison=comparison,
                explicit_comparison=explicit_comparison,
            )
            response = _strip_public_report_links(response)
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
                    live_llm_enabled=self._live_llm_enabled,
                    market_snapshot=market_snapshot,
                )
                response = self._attach_evidence_comparison(
                    response=response,
                    query=request.message,
                    plan=plan,
                    comparison=comparison,
                    explicit_comparison=explicit_comparison,
                )
                response = _strip_public_report_links(response)
            self._save_session_context(session_id, plan)
            resulting_revision = self._record_session_exchange(
                request=request,
                response=response,
                plan=plan,
                session_id=session_id,
            )
            observation = self._emit_terminal_observation(
                plan=plan,
                gateway=gateway,
                pipeline=pipeline,
                composition=composition,
                call_budget=call_budget,
                routing=routing,
                started_at=started_at,
            )
            if resulting_revision is not None and observation is not None:
                self._response_cache.put(
                    session_id=session_id,
                    snapshot_id=self._snapshot_id,
                    question=request.message,
                    resulting_revision=resulting_revision,
                    model_fingerprint=self._model_fingerprint,
                    response=response,
                    observation=observation,
                    checkpoint_id=checkpoint,
                )
            return response
        except ChatServiceError:
            raise
        except Exception:
            raise ChatServiceError("chat service unavailable") from None

    def _attach_evidence_comparison(
        self,
        *,
        response: ChatResponse,
        query: str,
        plan: QueryPlan,
        comparison: PublicEvidenceComparison | None,
        explicit_comparison: bool,
    ) -> ChatResponse:
        if not _comparison_request_eligible(plan):
            return response
        if comparison is None:
            if explicit_comparison:
                return response.model_copy(
                    update={
                        "answer_sections": (
                            _comparison_unavailable_sections(
                                response.answer_sections
                            )
                        )
                    },
                    deep=True,
                )
            return response
        if (
            not explicit_comparison
            and not _comparison_query_matches_event(query, comparison)
        ):
            return response
        attached_comparison = (
            comparison.model_copy(
                update={"answer_integrated": True},
                deep=True,
            )
            if explicit_comparison
            else comparison
        )
        updated = response.model_copy(
            update={"evidence_comparison": attached_comparison},
            deep=True,
        )
        if not explicit_comparison:
            return updated
        return updated.model_copy(
            update={
                "answer_sections": _comparison_answer_sections(
                    attached_comparison,
                    generated=updated.answer_sections,
                ),
            },
            deep=True,
        )

    def _select_evidence_comparison(
        self,
        *,
        query: str,
        plan: QueryPlan,
        basis_at: datetime,
    ) -> PublicEvidenceComparison | None:
        store = self._evidence_comparison_store
        if store is None or not _comparison_request_eligible(plan):
            return None
        return store.select(
            query=query,
            security_id=(
                f"{plan.security.market}:{plan.security.ticker}"
                if plan.security is not None
                else None
            ),
            as_of=basis_at,
        )

    async def _route_intent(
        self,
        query: str,
        deterministic: ObservedQueryPlan,
        *,
        basis_at: datetime,
        started_at: float,
        client_key: str | None,
    ) -> HybridRoutingResult:
        if not self._intent_router.should_classify(
            query,
            deterministic,
        ):
            return self._intent_router.deterministic(deterministic)
        try:
            async with self._request_protector.admit(
                client_key,
                timeout_seconds=self._remaining(started_at),
            ):
                return await self._intent_router.classify(
                    query,
                    deterministic,
                    basis_date=basis_at.astimezone(SEOUL_TZ).date(),
                    timeout_seconds=self._remaining(started_at),
                )
        except RequestProtectionLimitError:
            return self._intent_router.fallback(
                deterministic,
                status="rate_limited",
                classifier_called=False,
            )

    def _market_snapshot(
        self,
        plan: QueryPlan,
        *,
        basis_at: datetime,
    ) -> MarketSnapshot | None:
        if (
            plan.intent not in {"price", "price_move"}
            or plan.security is None
            or self._market_snapshot_store is None
        ):
            return None
        try:
            return self._market_snapshot_store.get(
                security_id=(
                    f"{plan.security.market}:{plan.security.ticker}"
                ),
                as_of=basis_at,
            )
        except MarketSnapshotStoreError:
            return None

    async def _source_data(
        self,
        plan: QueryPlan,
        *,
        query: str,
        started_at: float,
    ) -> SourceGatewayResult:
        if plan.requires_clarification or not plan.required_sources:
            return create_source_gateway_timeout_result(
                getattr(
                    self._source_gateway,
                    "timeout_descriptor",
                    None,
                ),
                required_sources=plan.required_sources,
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
        client_key: str | None,
        conversation_context: str,
    ) -> CompositionResult:
        if (
            pipeline.decision.status not in {"complete", "partial"}
            or not pipeline.budget.evidence
        ):
            return self._composer.compose_fixed(
                plan=plan,
                selected_evidence=pipeline.budget.evidence,
                question=request.message,
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
                question=request.message,
            )
        if not self._composer.llm_eligible(
            plan=plan,
            selected_evidence=pipeline.budget.evidence,
            documents_by_id=pipeline.documents_by_id,
        ):
            return self._composer.compose_fixed(
                plan=plan,
                selected_evidence=pipeline.budget.evidence,
                question=request.message,
            )
        try:
            async with self._request_protector.admit(
                client_key,
                timeout_seconds=self._remaining(started_at),
            ):
                remaining = self._remaining(started_at)
                return await asyncio.wait_for(
                    self._composer.compose(
                        question=request.message,
                        plan=plan,
                        selected_evidence=pipeline.budget.evidence,
                        documents_by_id=pipeline.documents_by_id,
                        timeout_seconds=remaining,
                        call_budget=call_budget,
                        conversation_context=conversation_context,
                    ),
                    timeout=remaining,
                )
        except RequestProtectionLimitError:
            limited_result = create_llm_result(
                status=LLMStatus.RATE_LIMITED,
                model=APPROVED_LLM_MODEL,
                provider="gemini",
                latency_ms=0,
            )
            return self._composer.compose_fixed(
                plan=plan,
                selected_evidence=pipeline.budget.evidence,
                question=request.message,
                llm_result=limited_result,
            )
        except TimeoutError:
            timeout_result = create_llm_result(
                status=LLMStatus.TIMEOUT,
                model=APPROVED_LLM_MODEL,
                provider="gemini",
                latency_ms=self._deadline_seconds * 1000,
            )
            return self._composer.compose_fixed(
                plan=plan,
                selected_evidence=pipeline.budget.evidence,
                question=request.message,
                llm_result=timeout_result,
            )

    def _record_session_exchange(
        self,
        *,
        request: ChatRequest,
        response: ChatResponse,
        plan: QueryPlan,
        session_id: str,
    ) -> int | None:
        try:
            security_id = (
                f"{plan.security.market}:{plan.security.ticker}"
                if plan.security is not None
                else None
            )
            return self._session_store.append_exchange(
                session_id,
                user_question=request.message,
                assistant_public_text=_assistant_memory_text(response),
                status=response.status,
                security_id=security_id,
                intent=plan.intent,
                selected_evidence_ids=tuple(
                    item.evidence_id for item in response.evidence
                ),
                snapshot_id=self._snapshot_id,
            )
        except SessionStoreError:
            return None

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
        routing: HybridRoutingResult,
        started_at: float,
    ) -> RequestObservation | None:
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
                llm_call_count=(
                    routing.classifier_call_count
                    + call_budget.snapshot().calls_used
                ),
                fallback_used=fallback_used_for_generation_mode(
                    composition.generation_mode
                ),
                intent_routing=routing.mode,
                intent_classifier_status=routing.classifier_status,
            )
        except Exception:
            return None
        try:
            self._observation_sink.emit(observation)
        except Exception:
            pass
        return observation

    def _emit_cached_observation(
        self,
        observation: RequestObservation,
    ) -> None:
        try:
            cached = replace(
                observation,
                request_id=self._request_id_factory(),
                total_latency_ms=0.0,
                llm_call_count=0,
                intent_routing="cached",
                intent_classifier_status="not_called",
            )
            self._observation_sink.emit(cached)
        except Exception:
            return

    def _emit_price_observation(
        self,
        *,
        plan: QueryPlan,
        snapshot: MarketSnapshot | None,
        routing: HybridRoutingResult,
        started_at: float,
    ) -> RequestObservation | None:
        try:
            security_id = (
                f"{plan.security.market}:{plan.security.ticker}"
                if plan.security is not None
                else None
            )
            elapsed_ms = (
                self._monotonic() - started_at
            ) * 1000
            observation = RequestObservation(
                request_id=self._request_id_factory(),
                intent=plan.intent,
                security_id=security_id,
                provider_statuses=(),
                evidence_count=0,
                retrieval_strategy="market-snapshot-m5-01-v1",
                evidence_decision=(
                    "complete" if snapshot is not None else "no_evidence"
                ),
                total_latency_ms=round(elapsed_ms, 3),
                llm_call_count=routing.classifier_call_count,
                fallback_used=False,
                intent_routing=routing.mode,
                intent_classifier_status=routing.classifier_status,
            )
        except Exception:
            return None
        try:
            self._observation_sink.emit(observation)
        except Exception:
            pass
        return observation

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
            model=APPROVED_LLM_MODEL,
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


def _comparison_request_eligible(plan: QueryPlan) -> bool:
    return (
        plan.security is not None
        and not plan.requires_clarification
        and plan.intent
        not in {
            "financial_term",
            "price",
            "prohibited_advice",
            "out_of_scope",
        }
    )


def _augment_pipeline_with_comparison(
    pipeline: _PipelineResult,
    comparison: PublicEvidenceComparison,
    *,
    security_id: str | None,
) -> _PipelineResult:
    comparison_evidence = _comparison_prompt_evidence(
        comparison,
        security_id=security_id,
    )
    if not comparison_evidence:
        return pipeline
    # An explicit comparison must stay inside the selected event cluster.
    # Mixing the ordinary retrieval tail back in can make the generated
    # comparison discuss unrelated same-day articles.
    budget = select_evidence_context(comparison_evidence)
    return _PipelineResult(
        documents_by_id=pipeline.documents_by_id,
        normalized=pipeline.normalized,
        hard_filtered=pipeline.hard_filtered,
        freshness=pipeline.freshness,
        retrieval=pipeline.retrieval,
        decision=pipeline.decision,
        budget=budget,
    )


def _comparison_prompt_evidence(
    comparison: PublicEvidenceComparison,
    *,
    security_id: str | None,
) -> tuple[Evidence, ...]:
    if security_id is None:
        return ()
    source_by_id = {
        source.source_id: source
        for source in comparison.article_sources
    }
    output: list[Evidence] = []
    for claim_kind, claims in (
        ("common", comparison.common_facts),
        ("difference", comparison.different_interpretations),
    ):
        for claim_index, claim in enumerate(claims, start=1):
            for source_id in claim.source_ids:
                source = source_by_id.get(source_id)
                if source is None or source.source_url is None:
                    continue
                digest = hashlib.sha256(
                    (
                        f"{comparison.event_id}:{claim_kind}:"
                        f"{claim_index}:{source_id}"
                    ).encode("utf-8")
                ).hexdigest()[:24]
                output.append(
                    Evidence(
                        evidence_id=f"comparison:{digest}",
                        document_id=source.source_id,
                        source_type="news",
                        title=source.title,
                        source_url=source.source_url,
                        published_at=source.published_at,
                        subject_security_ids=[security_id],
                        mentioned_security_ids=[],
                        scope="company_specific",
                        snippet=(
                            "뉴스 공통 사실: "
                            if claim_kind == "common"
                            else "기사별 강조점 차이: "
                        )
                        + claim.text,
                        locator={
                            "provider": "m5_d1_comparison",
                            "source_url": source.source_url,
                            "published_at": (
                                source.published_at.isoformat()
                            ),
                            "content_level": (
                                "questock_authored_comparison_claim"
                            ),
                            "claim_kind": claim_kind,
                        },
                        retrieval_score=1.0,
                    )
                )
    if output:
        return tuple(output)
    return tuple(
        Evidence(
            evidence_id=(
                "comparison:"
                + hashlib.sha256(
                    f"{comparison.event_id}:{source.source_id}".encode(
                        "utf-8"
                    )
                ).hexdigest()[:24]
            ),
            document_id=source.source_id,
            source_type="news",
            title=source.title,
            source_url=source.source_url,
            published_at=source.published_at,
            subject_security_ids=[security_id],
            mentioned_security_ids=[],
            scope="company_specific",
            snippet=f"기사 제목에서 확인되는 내용: {source.title}",
            locator={
                "provider": "m5_d1_comparison",
                "source_url": source.source_url,
                "published_at": source.published_at.isoformat(),
                "content_level": "source_title_only",
                "claim_kind": "coverage",
            },
            retrieval_score=1.0,
        )
        for source in comparison.article_sources[:4]
        if source.source_url is not None
    )


def _comparison_answer_sections(
    comparison: PublicEvidenceComparison,
    *,
    generated: AnswerSections,
) -> AnswerSections:
    lineage = comparison.source_lineage_summary
    generated_summary = [
        _clean_comparison_summary(item)
        for item in generated.summary[:1]
    ]
    if comparison.common_facts and generated_summary:
        summary = generated_summary
    elif comparison.common_facts:
        summary = [comparison.common_facts[0].text]
    elif (
        lineage.confirmed_independent_count == 0
        and lineage.confirmed_republication_count == 0
    ):
        summary = [
            f"수집된 기사 {comparison.article_total_count}건은 제목 유사성 "
            f"기준으로 ‘{comparison.event_label}’이라는 같은 주제의 사건 "
            "묶음으로 분류됐습니다. 다만 원출처 관계를 확인하지 못해 "
            "모두 독립 보도인지 재인용인지까지는 단정할 수 없습니다."
        ]
    else:
        summary = [
            f"이 사건 관련 기사 {comparison.article_total_count}건 중 "
            f"독립 보도 {lineage.confirmed_independent_count}건, 재배포 "
            f"{lineage.confirmed_republication_count}건이 확인됐습니다."
        ]
    facts = [
        item.text for item in comparison.common_facts[:1]
        if item.text not in summary
    ]
    interpretation = _comparison_news_interpretation(
        comparison,
        generated=generated,
    )
    inference = []
    if (
        comparison.support_summary
        and (
            comparison.report_perspectives
            or any(
                item.role != "no_link"
                for item in comparison.disclosure_links
            )
        )
    ):
        inference.append(comparison.support_summary)
    uncertainty = list(comparison.missing_evidence[:2])
    return AnswerSections(
        summary=summary,
        facts=facts,
        interpretation=interpretation,
        inference=inference,
        uncertainty=uncertainty,
    )


def _comparison_news_interpretation(
    comparison: PublicEvidenceComparison,
    *,
    generated: AnswerSections,
) -> list[str]:
    generated_items = [
        _clean_comparison_summary(item)
        for item in generated.interpretation[:2]
        if _clean_comparison_summary(item)
    ]
    if generated_items:
        return [_connect_comparison_sentences(generated_items)]
    return [
        _connect_comparison_sentences(
            [
                item.text
                for item in comparison.different_interpretations[:2]
            ]
        )
    ] if comparison.different_interpretations else []


def _connect_comparison_sentences(items: list[str]) -> str:
    canonical = [
        item.strip()
        for item in items
        if isinstance(item, str) and item.strip()
    ]
    if not canonical:
        return ""
    if len(canonical) == 1:
        return _ensure_comparison_synthesis(canonical[0])
    first = canonical[0].rstrip()
    if first.endswith("."):
        first = first[:-1]
    second = canonical[1].strip()
    return _ensure_comparison_synthesis(f"{first}. 반면 {second}")


def _ensure_comparison_synthesis(value: str) -> str:
    canonical = value.strip()
    if "즉" in canonical:
        return canonical
    canonical = canonical.rstrip(".")
    return (
        f"{canonical}. 즉 같은 사건을 다루더라도 기사마다 강조한 "
        "지점이 달랐습니다."
    )


def _clean_comparison_summary(value: str) -> str:
    prefixes = (
        "뉴스 공통 사실:",
        "기사별 강조점 차이:",
        "기사 제목에서 확인되는 내용:",
    )
    output = value.strip()
    for prefix in prefixes:
        if output.startswith(prefix):
            output = output[len(prefix) :].strip()
    return output


def _comparison_unavailable_sections(
    generated: AnswerSections,
) -> AnswerSections:
    notice = (
        "질문과 직접 맞는 동일 사건 대조 자료는 아직 확인되지 "
        "않았습니다. 대신 현재 확보된 관련 자료를 기준으로 보면 "
        "다음과 같이 바라볼 수 있습니다."
    )
    return generated.model_copy(
        update={"summary": [notice, *generated.summary[:1]]},
        deep=True,
    )


def _strip_public_report_links(response: ChatResponse) -> ChatResponse:
    evidence = []
    for item in response.evidence:
        if item.source_type != "research_report":
            evidence.append(item.model_copy(deep=True))
            continue
        locator = {
            key: value
            for key, value in item.locator.items()
            if "url" not in key.casefold()
        }
        evidence.append(
            item.model_copy(
                update={
                    "source_url": None,
                    "locator": locator,
                },
                deep=True,
            )
        )
    return response.model_copy(
        update={"evidence": evidence},
        deep=True,
    )


def _comparison_query_matches_event(
    query: str,
    comparison: PublicEvidenceComparison,
) -> bool:
    generic = {
        "삼성전자",
        "sk하이닉스",
        "하이닉스",
        "현대차",
        "현대자동차",
        "최근",
        "뉴스",
        "기사",
        "보도",
        "사건",
        "이슈",
        "관련",
        "핵심",
        "요약",
        "적용",
        "속도",
        "향상",
        "전망",
        "실적",
        "기술",
    }
    query_terms = {
        item.casefold()
        for item in _COMPARISON_TERM.findall(query)
        if item.casefold() not in generic
        and not item.isdigit()
    }
    event_terms = {
        item.casefold()
        for item in _COMPARISON_TERM.findall(comparison.event_label)
        if item.casefold() not in generic
        and not item.isdigit()
    }
    return bool(query_terms.intersection(event_terms))


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
        query=_retrieval_query(query, plan),
        security_id=_request_security_id(plan, documents),
        source_types=list(plan.required_sources),
        date_range=plan.date_range.model_copy(deep=True) if plan.date_range else None,
        as_of=basis_at,
        top_k=10,
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
    retrieval = _retrieve_for_plan(
        freshness.evidence,
        request,
        plan=plan,
        documents_by_id=documents_by_id,
    )
    decision = EvidencePolicy().evaluate(
        plan,
        gateway.provider_results_by_source,
        freshness,
        retrieval,
    )
    budget = select_evidence_context(
        decision.evidence,
        required_sources=plan.required_sources,
    )
    return _PipelineResult(
        documents_by_id=documents_by_id,
        normalized=normalized,
        hard_filtered=hard_filtered,
        freshness=freshness,
        retrieval=retrieval,
        decision=decision,
        budget=budget,
    )


def _retrieve_for_plan(
    evidence: tuple[Evidence, ...],
    request: RetrievalRequest,
    *,
    plan: QueryPlan,
    documents_by_id: Mapping[str, FinancialDocument],
) -> RetrievalResult:
    if plan.intent == "price_move":
        news_request = request.model_copy(
            deep=True,
            update={
                "source_types": ["news"],
                "top_k": 6,
            },
        )
        news_result = retrieve_evidence(
            evidence,
            news_request,
            documents_by_id=documents_by_id,
        )
        if (
            news_result.status == RetrievalStatus.OK
            and news_result.evidence
        ):
            return news_result
    return retrieve_evidence(
        evidence,
        request,
        documents_by_id=documents_by_id,
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


def _retrieval_query(query: str, plan: QueryPlan) -> str:
    terms = _FOCUS_QUERY_TERMS.get(plan.answer_focus, ())
    if not terms:
        return query
    return " ".join((query, *terms))


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
    live_llm_enabled: bool,
    market_snapshot: MarketSnapshot | None,
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
        live_llm_enabled=live_llm_enabled,
    )
    response_status = pipeline.decision.status
    if response_status == "complete" and not composition.public_evidence:
        response_status = "no_evidence"
    response = ChatResponse(
        status=response_status,
        security=plan.security.model_copy(deep=True) if plan.security else None,
        basis_date=basis_at.astimezone(SEOUL_TZ).date(),
        basis_at=basis_at,
        market_snapshot=_public_market_snapshot(market_snapshot),
        answer_sections=composition.answer_sections.model_copy(deep=True),
        evidence=[
            item.model_copy(deep=True) for item in composition.public_evidence
        ],
        warnings=warnings,
        missing_sources=list(pipeline.decision.missing_sources),
        diagnostics_public=summary,
    )
    if plan.intent == "price_move" and market_snapshot is not None:
        return _attach_price_movement(response, market_snapshot)
    return response


def _build_process_summary(
    *,
    plan: QueryPlan,
    gateway: SourceGatewayResult,
    pipeline: _PipelineResult,
    composition: CompositionResult,
    resolution_status: PublicResolutionStatus,
    resolved_security_id: str | None,
    live_llm_enabled: bool,
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
            live_verified=(
                live_llm_enabled
                and composition.generation_mode == "llm"
                and llm_result is not None
                and llm_result.status == LLMStatus.OK
            ),
        ),
    )


def _assistant_memory_text(response: ChatResponse) -> str:
    sections = response.answer_sections
    ordered = (
        sections.summary,
        sections.facts,
        sections.risk_factors,
        sections.uncertainty,
        sections.interpretation,
        sections.inference,
        sections.positive_factors,
    )
    output: list[str] = []
    remaining = 2000
    for values in ordered:
        for value in values:
            separator = "\n" if output else ""
            available = remaining - len(separator)
            if available <= 0:
                return "".join(output)
            fragment = value[:available]
            if fragment:
                output.append(f"{separator}{fragment}")
                remaining -= len(separator) + len(fragment)
            if len(fragment) < len(value) or remaining == 0:
                return "".join(output)
    text = "".join(output)
    if not text:
        raise ChatServiceError("chat response is invalid")
    return text


def _request_basis_at(
    request: ChatRequest,
    utc_now: Callable[[], datetime],
) -> datetime:
    if request.as_of is not None:
        return _aware_utc(request.as_of)
    return _aware_utc(utc_now())


def _time_scoped_session_id(
    session_id: str,
    checkpoint: str,
) -> str:
    if checkpoint == "legacy":
        return session_id
    digest = hashlib.sha256(
        f"{session_id}\n{checkpoint}".encode("utf-8")
    ).hexdigest()
    return f"m5-{digest}"


def _public_market_snapshot(
    snapshot: MarketSnapshot | None,
) -> PublicMarketSnapshot | None:
    if (
        snapshot is None
        or snapshot.checkpoint_id is None
        or snapshot.requested_as_of is None
        or snapshot.market_code not in {"J", "NX", "UN"}
        or snapshot.market_session
        not in {
            "pre_market",
            "regular",
            "after_market",
            "after_close",
            "closed",
        }
        or snapshot.market_status
        not in {"open", "closed", "no_trade_yet", "no_data"}
    ):
        return None
    return PublicMarketSnapshot(
        checkpoint_id=snapshot.checkpoint_id,
        requested_as_of=snapshot.requested_as_of,
        observed_at=snapshot.observed_at,
        price=snapshot.price,
        previous_close=snapshot.previous_close,
        change=snapshot.change,
        change_percent=snapshot.change_percent,
        volume=snapshot.volume,
        market_code=snapshot.market_code,
        market_session=snapshot.market_session,
        market_status=snapshot.market_status,
        currency="KRW",
    )


def _build_price_only_response(
    *,
    plan: QueryPlan,
    snapshot: MarketSnapshot | None,
    basis_at: datetime,
    resolution_status: PublicResolutionStatus,
    resolved_security_id: str | None,
) -> ChatResponse:
    public_snapshot = _public_market_snapshot(snapshot)
    if snapshot is None or public_snapshot is None:
        status = "provider_failed"
        sections = AnswerSections(
            summary=[
                "선택한 기준 시점의 가격 자료를 확인하지 못했습니다."
            ],
            uncertainty=[
                "기준 날짜와 시점을 다시 선택한 뒤 확인해 주세요."
            ],
        )
        decision_status = "provider_failed"
    else:
        status = "complete"
        sections = AnswerSections(
            summary=[_price_summary_text(snapshot)],
            facts=[_price_fact_text(snapshot)],
            uncertainty=(
                [_closed_market_text(snapshot)]
                if snapshot.market_status == "closed"
                else []
            ),
        )
        decision_status = "complete"
    process = _price_process_summary(
        plan=plan,
        resolution_status=resolution_status,
        resolved_security_id=resolved_security_id,
        decision_status=decision_status,
        has_snapshot=public_snapshot is not None,
    )
    return ChatResponse(
        status=status,
        security=(
            plan.security.model_copy(deep=True)
            if plan.security is not None
            else None
        ),
        basis_date=basis_at.astimezone(SEOUL_TZ).date(),
        basis_at=basis_at,
        market_snapshot=public_snapshot,
        answer_sections=sections,
        evidence=[],
        warnings=[],
        missing_sources=[],
        diagnostics_public=process,
    )


def _price_process_summary(
    *,
    plan: QueryPlan,
    resolution_status: PublicResolutionStatus,
    resolved_security_id: str | None,
    decision_status: str,
    has_snapshot: bool,
) -> PublicProcessSummary:
    return PublicProcessSummary(
        data_mode="recorded",
        live_connectivity_checked=False,
        security=PublicSecuritySummary(
            resolution_status=resolution_status,
            security_id=resolved_security_id,
        ),
        query_plan=PublicQueryPlanSummary(
            intent=plan.intent,
            required_sources=[],
            date_start=plan.date_range.start if plan.date_range else None,
            date_end=plan.date_range.end if plan.date_range else None,
        ),
        sources=[],
        evidence_pipeline=PublicEvidencePipelineSummary(
            normalized_count=0,
            hard_filtered_count=0,
            freshness_retained_count=0,
            freshness_warning_codes=[],
            retrieval_status="empty",
            retrieval_selected_count=0,
        ),
        decision=PublicDecisionSummary(
            evidence_decision_status=decision_status,
            satisfied_sources=[],
            missing_sources=[],
            no_data_sources=[] if has_snapshot else [],
            failed_sources=[],
        ),
        context_budget=PublicContextBudgetSummary(
            input_count=0,
            unique_count=0,
            selected_count=0,
            duplicate_drop_count=0,
            source_cap_drop_count=0,
            count_cap_drop_count=0,
            context_drop_count=0,
            estimated_context_tokens=0,
            estimated_context_chars=0,
        ),
        citation=PublicCitationSummary(
            claim_count=1 if has_snapshot else 0,
            citation_count=0,
            rejection_count=0,
        ),
        generation=PublicGenerationSummary(
            mode="fixed_template",
            llm_status=None,
            model=None,
            live_verified=False,
        ),
    )


def _attach_price_movement(
    response: ChatResponse,
    snapshot: MarketSnapshot,
) -> ChatResponse:
    sections = response.answer_sections.model_copy(deep=True)
    sections.summary = [
        _price_movement_context_text(snapshot),
        *sections.summary,
    ]
    uncertainty = (
        "확인된 자료는 가격 움직임의 가능한 배경 요인입니다. "
        "하나의 원인으로 단정할 수 없습니다."
    )
    if response.evidence and uncertainty not in sections.uncertainty:
        sections.uncertainty.append(uncertainty)
    if snapshot.market_status == "closed":
        closed_notice = _closed_market_text(snapshot)
        if closed_notice not in sections.uncertainty:
            sections.uncertainty.append(closed_notice)
    return response.model_copy(
        deep=True,
        update={
            "answer_sections": sections,
        },
    )


def _price_movement_context_text(snapshot: MarketSnapshot) -> str:
    direction = (
        "상승"
        if snapshot.change > 0
        else "하락"
        if snapshot.change < 0
        else "보합"
    )
    return (
        f"{_kst_label(snapshot.observed_at)}에는 전 거래일 KRX 종가보다 "
        f"{abs(snapshot.change_percent):.2f}% {direction}했습니다."
    )


def _price_summary_text(snapshot: MarketSnapshot) -> str:
    direction = (
        "상승"
        if snapshot.change > 0
        else "하락"
        if snapshot.change < 0
        else "보합"
    )
    return (
        f"{_kst_label(snapshot.observed_at)} 관측 가격은 "
        f"{_won(snapshot.price)}원으로, 전 거래일 KRX 종가 대비 "
        f"{direction}했습니다."
    )


def _price_fact_text(snapshot: MarketSnapshot) -> str:
    sign = "+" if snapshot.change > 0 else ""
    return (
        f"가격 {_won(snapshot.price)}원 · 전일 종가 "
        f"{_won(snapshot.previous_close)}원 · 변동 "
        f"{sign}{_won(snapshot.change)}원 "
        f"({sign}{snapshot.change_percent:.2f}%)"
    )


def _closed_market_text(snapshot: MarketSnapshot) -> str:
    return (
        "선택한 시점에는 시장이 닫혀 있어 "
        f"{_kst_label(snapshot.observed_at)}의 마지막 실제 체결을 "
        "표시했습니다."
    )


def _kst_label(value: datetime) -> str:
    return value.astimezone(SEOUL_TZ).strftime(
        "%Y-%m-%d %H:%M KST"
    )


def _won(value: float) -> str:
    return f"{value:,.0f}"


def _aware_utc(value: object) -> datetime:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ChatServiceError("basis time is invalid")
    return value.astimezone(UTC)


__all__ = ["ChatService", "ChatServiceError"]
