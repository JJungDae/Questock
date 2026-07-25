from __future__ import annotations

import asyncio
import io
import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.answer.composer import AnswerComposer
from app.api.schemas import ChatRequest
from app.core.models import FinancialDocument, QueryPlan
from app.core.status import ProviderStatus
from app.evidence.budget import LLMCallBudget
from app.llm.base import LLMRequest, LLMResult, LLMStatus, create_llm_result
from app.providers.base import create_provider_result
from app.services import chat_service as chat_service_module
from app.services.chat_service import ChatService, ChatServiceError
from app.services.observability import (
    InMemoryObservationSink,
    JsonLogObservationSink,
    ObservationSink,
)
from app.services.source_gateway import (
    SourceGatewayResult,
    SourceGatewayTimeoutDescriptor,
)

BASIS_AT = datetime(2026, 7, 25, 3, tzinfo=UTC)
SECURITY_ID = "KRX:005930"
QUESTION = "삼성전자 반도체 투자 최근 뉴스"
SNIPPET = "삼성전자 반도체 투자 확대 소식이 발표됐다."


def news_document(
    *,
    document_id: str = "document:news:unit",
    security_id: str = SECURITY_ID,
    published_at: datetime = BASIS_AT - timedelta(days=1),
    snippet: str = SNIPPET,
    source_url: str | None = None,
    locator_source_url: str | None = None,
) -> FinancialDocument:
    canonical_source_url = source_url or (
        f"https://news.example.test/{document_id.replace(':', '-')}"
    )
    return FinancialDocument(
        document_id=document_id,
        source_type="news",
        provider="recorded_news",
        primary_security_ids=[security_id],
        mentioned_security_ids=[],
        title="삼성전자 반도체 투자 최근 뉴스",
        published_at=published_at,
        source_url=canonical_source_url,
        text=snippet,
        locator={
            "provider": "recorded_news",
            "source_url": locator_source_url or canonical_source_url,
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
        after_fetch: Callable[[], None] | None = None,
    ) -> None:
        self.documents = documents
        self.status = status
        self.data_mode = data_mode
        self.timeout_descriptor = SourceGatewayTimeoutDescriptor(
            data_mode=data_mode,  # type: ignore[arg-type]
            live_connectivity_checked=data_mode == "live",
        )
        self.delay = delay
        self.after_fetch = after_fetch
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
        if self.after_fetch is not None:
            self.after_fetch()
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
            live_connectivity_checked=self.data_mode == "live",
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
    monotonic: Callable[[], float] | None = None,
    call_budget_factory: Callable[[], LLMCallBudget] | None = None,
    observation_sink: ObservationSink | None = None,
    request_id_factory: Callable[[], str] | None = None,
) -> ChatService:
    kwargs: dict[str, Any] = {
        "source_gateway": gateway,
        "composer": AnswerComposer(llm),
        "deadline_seconds": deadline_seconds,
        "utc_now": lambda: BASIS_AT,
        "observation_sink": (
            observation_sink
            if observation_sink is not None
            else InMemoryObservationSink()
        ),
    }
    if monotonic is not None:
        kwargs["monotonic"] = monotonic
    if call_budget_factory is not None:
        kwargs["call_budget_factory"] = call_budget_factory
    if request_id_factory is not None:
        kwargs["request_id_factory"] = request_id_factory
    return ChatService(
        **kwargs,
    )


def _request(message: str = QUESTION) -> ChatRequest:
    return ChatRequest(message=message, session_id="chat-service-unit")


class MutableClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class RaisingObservationSink:
    def __init__(self) -> None:
        self.calls = 0

    def emit(self, observation: object) -> None:
        self.calls += 1
        raise RuntimeError(
            "sentinel-secret C:\\private\\observation-error.txt"
        )


def test_default_runtime_observation_sink_is_json_logger() -> None:
    service = ChatService()

    assert isinstance(
        service._observation_sink,  # noqa: SLF001
        JsonLogObservationSink,
    )
    assert (
        service._observation_sink.logger_name  # noqa: SLF001
        == "questock.observability"
    )


def test_complete_response_emits_actual_internal_observation_once() -> None:
    sink = InMemoryObservationSink()
    clock = MutableClock()
    gateway = FakeGateway(
        (news_document(),),
        after_fetch=lambda: clock.advance(0.0125),
    )
    request = _request()
    original_request = request.model_dump(mode="python")

    response = asyncio.run(
        _service(
            gateway,
            ExtractiveLLM(),
            monotonic=clock,
            observation_sink=sink,
            request_id_factory=lambda: "request-complete",
        ).chat(request)
    )

    assert response.status == "complete"
    assert request.model_dump(mode="python") == original_request
    assert len(sink.observations) == 1
    observation = sink.observations[0]
    assert observation.request_id == "request-complete"
    assert observation.intent == "recent_issue"
    assert observation.security_id == SECURITY_ID
    assert observation.provider_statuses == (("news", "ok"),)
    assert observation.evidence_count == 1
    assert (
        observation.retrieval_strategy
        == "lexical-bm25-m2-03-v1"
    )
    assert observation.evidence_decision == "complete"
    assert observation.total_latency_ms == 12.5
    assert observation.llm_call_count == 1
    assert observation.fallback_used is False


def test_fixed_template_and_blocked_fallback_observations_are_distinct() -> None:
    fixed_sink = InMemoryObservationSink()
    blocked_sink = InMemoryObservationSink()

    fixed = asyncio.run(
        _service(
            FakeGateway((news_document(),)),
            ExtractiveLLM(status=LLMStatus.TIMEOUT),
            observation_sink=fixed_sink,
            request_id_factory=lambda: "request-fixed",
        ).chat(_request())
    )
    blocked = asyncio.run(
        _service(
            FakeGateway(()),
            ExtractiveLLM(),
            observation_sink=blocked_sink,
            request_id_factory=lambda: "request-blocked",
        ).chat(
            ChatRequest(
                message="삼성전자 지금 사야 돼?",
                session_id="chat-service-blocked",
            )
        )
    )

    assert fixed.diagnostics_public.generation.mode == "fixed_template"
    assert fixed_sink.observations[0].fallback_used is True
    assert fixed_sink.observations[0].llm_call_count == 1
    assert blocked.status == "blocked"
    assert blocked.diagnostics_public.generation.mode == "blocked"
    assert blocked_sink.observations[0].fallback_used is False
    assert blocked_sink.observations[0].evidence_decision == "blocked"
    assert blocked_sink.observations[0].provider_statuses == ()
    assert blocked_sink.observations[0].llm_call_count == 0


def test_observation_sink_failure_does_not_replace_valid_response() -> None:
    sink = RaisingObservationSink()

    response = asyncio.run(
        _service(
            FakeGateway((news_document(),)),
            ExtractiveLLM(),
            observation_sink=sink,
            request_id_factory=lambda: "request-sink-failure",
        ).chat(_request())
    )

    assert response.status == "complete"
    assert sink.calls == 1


def test_request_without_chat_response_emits_no_terminal_observation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sink = InMemoryObservationSink()

    def fail_response(**kwargs: object) -> object:
        raise RuntimeError(
            "sentinel-secret C:\\private\\response-error.txt"
        )

    monkeypatch.setattr(
        chat_service_module,
        "_build_response",
        fail_response,
    )

    with pytest.raises(
        ChatServiceError,
        match="chat service unavailable",
    ):
        asyncio.run(
            _service(
                FakeGateway((news_document(),)),
                ExtractiveLLM(),
                observation_sink=sink,
                request_id_factory=lambda: "request-no-response",
            ).chat(_request())
        )

    assert sink.observations == ()


def test_json_observation_excludes_request_and_source_content() -> None:
    output = io.StringIO()
    logger = logging.Logger("questock.observability.chat-unit")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(output)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    sentinel = "sentinel-secret"
    session_id = "session-private-path"

    response = asyncio.run(
        _service(
            FakeGateway((news_document(),)),
            ExtractiveLLM(),
            observation_sink=JsonLogObservationSink(logger),
            request_id_factory=lambda: "request-safe-log",
        ).chat(
            ChatRequest(
                message=f"{QUESTION} {sentinel}",
                session_id=session_id,
            )
        )
    )

    rendered = output.getvalue()
    assert response.status == "complete"
    assert sentinel not in rendered
    assert session_id not in rendered
    assert SNIPPET not in rendered
    assert "https://news.example.test" not in rendered
    assert "C:\\private" not in rendered


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
                data_mode="recorded",
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
    budgets: list[LLMCallBudget] = []

    response = asyncio.run(
        _service(
            gateway,
            llm,
            deadline_seconds=0.01,
            call_budget_factory=lambda: _track_budget(budgets),
        ).chat(_request())
    )

    assert response.status == "provider_failed"
    assert response.diagnostics_public.sources[0].provider_status == "timeout"
    assert response.diagnostics_public.data_mode == "recorded"
    assert response.diagnostics_public.live_connectivity_checked is False
    assert response.diagnostics_public.decision.failed_sources == ["news"]
    assert response.warnings == ["request_deadline_exceeded"]
    assert gateway.cancel_count == 1
    assert llm.calls == 0
    assert budgets[0].snapshot().calls_used == 0
    serialized = response.diagnostics_public.model_dump_json()
    assert "TimeoutError" not in serialized
    assert "timeout_descriptor" not in serialized
    assert "total_deadline_exceeded" not in serialized


def test_live_gateway_deadline_preserves_live_timeout_state() -> None:
    gateway = FakeGateway(
        (news_document(),),
        data_mode="live",
        delay=1,
    )
    llm = ExtractiveLLM()
    budgets: list[LLMCallBudget] = []

    response = asyncio.run(
        _service(
            gateway,
            llm,
            deadline_seconds=0.01,
            call_budget_factory=lambda: _track_budget(budgets),
        ).chat(_request())
    )

    assert response.status == "provider_failed"
    assert response.diagnostics_public.sources[0].provider_status == "timeout"
    assert response.diagnostics_public.data_mode == "live"
    assert response.diagnostics_public.live_connectivity_checked is True
    assert response.diagnostics_public.decision.failed_sources == ["news"]
    assert response.warnings == ["request_deadline_exceeded"]
    assert gateway.cancel_count == 1
    assert llm.calls == 0
    assert budgets[0].snapshot().calls_used == 0


def test_llm_deadline_cancels_once_and_uses_fixed_template() -> None:
    gateway = FakeGateway((news_document(),))
    llm = ExtractiveLLM(delay=1)
    clock = MutableClock()

    response = asyncio.run(
        _service(
            gateway,
            llm,
            deadline_seconds=0.02,
            monotonic=clock,
        ).chat(_request())
    )

    assert response.status == "complete"
    assert response.answer_sections.summary == [SNIPPET]
    assert response.diagnostics_public.generation.mode == "fixed_template"
    assert response.diagnostics_public.generation.llm_status == "timeout"
    assert llm.calls == 1
    assert llm.cancel_count == 1


def test_unsafe_conflict_timeout_fallback_is_public_no_evidence() -> None:
    unsafe = "긍정 기사가 더 많으므로 상승이 우세하다."
    gateway = FakeGateway((news_document(snippet=unsafe),))
    llm = ExtractiveLLM(status=LLMStatus.TIMEOUT)

    response = asyncio.run(
        _service(gateway, llm).chat(_request())
    )

    assert response.status == "no_evidence"
    assert response.answer_sections.summary == [
        "답변에 사용할 수 있는 근거를 확인하지 못했습니다."
    ]
    assert response.evidence == []
    assert response.diagnostics_public.generation.mode == "fixed_template"
    assert response.diagnostics_public.generation.llm_status == "timeout"
    assert unsafe not in response.model_dump_json()
    assert llm.calls == 1


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


def test_request_scoped_call_budget_is_fresh_for_each_chat() -> None:
    budgets: list[LLMCallBudget] = []

    def budget_factory() -> LLMCallBudget:
        budget = LLMCallBudget(max_calls=1)
        budgets.append(budget)
        return budget

    llm = ExtractiveLLM()
    service = _service(
        FakeGateway((news_document(),)),
        llm,
        call_budget_factory=budget_factory,
    )

    first = asyncio.run(service.chat(_request()))
    second = asyncio.run(service.chat(_request()))

    assert first.status == second.status == "complete"
    assert llm.calls == 2
    assert len(budgets) == 2
    assert budgets[0] is not budgets[1]
    assert [item.snapshot().calls_used for item in budgets] == [1, 1]


def test_blocked_and_no_evidence_paths_do_not_reserve_call_budget() -> None:
    budgets: list[LLMCallBudget] = []

    def budget_factory() -> LLMCallBudget:
        budget = LLMCallBudget(max_calls=1)
        budgets.append(budget)
        return budget

    blocked = asyncio.run(
        _service(
            FakeGateway(()),
            ExtractiveLLM(),
            call_budget_factory=budget_factory,
        ).chat(_request("삼성전자 지금 매수해야 하나"))
    )
    no_evidence = asyncio.run(
        _service(
            FakeGateway((), status=ProviderStatus.NO_DATA),
            ExtractiveLLM(),
            call_budget_factory=budget_factory,
        ).chat(_request())
    )

    assert blocked.status == "blocked"
    assert no_evidence.status == "no_evidence"
    assert len(budgets) == 2
    assert [item.snapshot().calls_used for item in budgets] == [0, 0]


def test_exhausted_injected_budget_falls_back_without_llm_call() -> None:
    exhausted = LLMCallBudget(max_calls=1)
    exhausted.reserve_call()
    llm = ExtractiveLLM()

    response = asyncio.run(
        _service(
            FakeGateway((news_document(),)),
            llm,
            call_budget_factory=lambda: exhausted,
        ).chat(_request())
    )

    assert response.status == "complete"
    assert response.diagnostics_public.generation.mode == "fixed_template"
    assert response.diagnostics_public.generation.llm_status is None
    assert llm.calls == 0
    assert exhausted.snapshot().calls_used == 1


def test_public_evidence_contains_only_citation_referenced_items() -> None:
    second_snippet = "삼성전자 생산 설비 증설 계획이 별도로 확인됐다."
    documents = (
        news_document(),
        news_document(
            document_id="document:news:second",
            snippet=second_snippet,
        ),
    )

    response = asyncio.run(
        _service(FakeGateway(documents), ExtractiveLLM()).chat(_request())
    )

    assert response.status == "complete"
    assert response.diagnostics_public.context_budget.selected_count == 2
    assert response.diagnostics_public.citation.citation_count == 1
    assert len(response.evidence) == 1
    assert response.evidence[0].snippet == SNIPPET


def test_chat_fixed_fallback_excludes_citation_rejected_evidence() -> None:
    sentinel = "credential-sentinel"
    document = news_document(
        locator_source_url=(
            "https://news.example.test/different-article"
            f"?reference={sentinel}"
        )
    )
    llm = ExtractiveLLM()

    response = asyncio.run(
        _service(FakeGateway((document,)), llm).chat(_request())
    )

    assert response.status == "no_evidence"
    assert (
        response.diagnostics_public.decision.evidence_decision_status
        == "complete"
    )
    assert response.answer_sections.summary == [
        "답변에 사용할 수 있는 근거를 확인하지 못했습니다."
    ]
    assert response.evidence == []
    assert response.diagnostics_public.context_budget.selected_count == 1
    assert response.diagnostics_public.citation.citation_count == 0
    assert response.diagnostics_public.citation.rejection_count >= 1
    assert llm.calls == 1
    assert sentinel not in response.model_dump_json()


def test_gateway_completion_after_deadline_skips_llm_and_keeps_safe_evidence() -> None:
    clock = MutableClock()
    budgets: list[LLMCallBudget] = []
    llm = ExtractiveLLM()
    gateway = FakeGateway(
        (news_document(),),
        after_fetch=lambda: clock.advance(21),
    )

    response = asyncio.run(
        _service(
            gateway,
            llm,
            monotonic=clock,
            call_budget_factory=lambda: _track_budget(budgets),
        ).chat(_request())
    )

    assert response.status == "complete"
    assert response.diagnostics_public.generation.mode == "fixed_template"
    assert response.diagnostics_public.generation.llm_status is None
    assert response.answer_sections.summary == [SNIPPET]
    assert response.warnings == ["request_deadline_exceeded"]
    assert llm.calls == 0
    assert budgets[0].snapshot().calls_used == 0


@pytest.mark.parametrize(
    ("provider_status", "expected_status"),
    [
        (ProviderStatus.PROVIDER_UNAVAILABLE, "provider_failed"),
        (ProviderStatus.NO_DATA, "no_evidence"),
    ],
)
def test_gateway_non_evidence_result_after_deadline_keeps_decision_fallback(
    provider_status: ProviderStatus,
    expected_status: str,
) -> None:
    clock = MutableClock()
    budgets: list[LLMCallBudget] = []
    llm = ExtractiveLLM()
    gateway = FakeGateway(
        (),
        status=provider_status,
        after_fetch=lambda: clock.advance(21),
    )

    response = asyncio.run(
        _service(
            gateway,
            llm,
            monotonic=clock,
            call_budget_factory=lambda: _track_budget(budgets),
        ).chat(_request())
    )

    assert response.status == expected_status
    assert response.evidence == []
    assert (
        response.diagnostics_public.sources[0].provider_status
        == provider_status
    )
    assert response.diagnostics_public.generation.llm_status is None
    assert response.warnings == ["request_deadline_exceeded"]
    assert llm.calls == 0
    assert budgets[0].snapshot().calls_used == 0


def test_pipeline_completion_after_deadline_skips_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = MutableClock()
    original = chat_service_module._run_evidence_pipeline

    def advancing_pipeline(*args: Any, **kwargs: Any) -> Any:
        result = original(*args, **kwargs)
        clock.advance(21)
        return result

    monkeypatch.setattr(
        chat_service_module,
        "_run_evidence_pipeline",
        advancing_pipeline,
    )
    llm = ExtractiveLLM()
    budgets: list[LLMCallBudget] = []

    response = asyncio.run(
        _service(
            FakeGateway((news_document(),)),
            llm,
            monotonic=clock,
            call_budget_factory=lambda: _track_budget(budgets),
        ).chat(_request())
    )

    assert response.status == "complete"
    assert response.diagnostics_public.generation.mode == "fixed_template"
    assert response.warnings == ["request_deadline_exceeded"]
    assert llm.calls == 0
    assert budgets[0].snapshot().calls_used == 0


def test_final_response_audit_replaces_late_llm_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = MutableClock()
    original = chat_service_module._build_response
    calls = 0

    def advancing_build_response(*args: Any, **kwargs: Any) -> Any:
        nonlocal calls
        response = original(*args, **kwargs)
        calls += 1
        if calls == 1:
            clock.advance(21)
        return response

    monkeypatch.setattr(
        chat_service_module,
        "_build_response",
        advancing_build_response,
    )
    llm = ExtractiveLLM()
    budgets: list[LLMCallBudget] = []

    response = asyncio.run(
        _service(
            FakeGateway((news_document(),)),
            llm,
            monotonic=clock,
            call_budget_factory=lambda: _track_budget(budgets),
        ).chat(_request())
    )

    assert response.status == "complete"
    assert response.diagnostics_public.generation.mode == "fixed_template"
    assert response.diagnostics_public.generation.llm_status == "timeout"
    assert response.answer_sections.summary == [SNIPPET]
    assert response.warnings == [
        "request_deadline_exceeded",
        "llm_generation_degraded",
    ]
    assert llm.calls == 1
    assert budgets[0].snapshot().calls_used == 1


def test_same_session_inherits_context_and_new_session_does_not() -> None:
    service = _service(FakeGateway(()), ExtractiveLLM())

    first = asyncio.run(
        service.chat(
            ChatRequest(
                message="삼성전자 최근 뉴스",
                session_id="session-a",
            )
        )
    )
    inherited = asyncio.run(
        service.chat(
            ChatRequest(
                message="그중 공시만",
                session_id="session-a",
            )
        )
    )
    reset = asyncio.run(
        service.chat(
            ChatRequest(
                message="그중 공시만",
                session_id="session-b",
            )
        )
    )

    assert first.security is not None
    assert first.security.ticker == "005930"
    assert inherited.security is not None
    assert inherited.security.ticker == "005930"
    assert inherited.diagnostics_public.query_plan.intent == "disclosure_summary"
    assert reset.security is None
    assert reset.diagnostics_public.security.resolution_status == "not_found"


def test_explicit_new_security_wins_and_prohibited_turn_does_not_replace_it() -> None:
    service = _service(FakeGateway(()), ExtractiveLLM())
    asyncio.run(
        service.chat(
            ChatRequest(
                message="삼성전자 최근 뉴스",
                session_id="session-a",
            )
        )
    )
    explicit = asyncio.run(
        service.chat(
            ChatRequest(
                message="SK하이닉스 최근 공시",
                session_id="session-a",
            )
        )
    )
    asyncio.run(
        service.chat(
            ChatRequest(
                message="현대자동차 지금 사도 돼?",
                session_id="session-a",
            )
        )
    )
    inherited = asyncio.run(
        service.chat(
            ChatRequest(
                message="이어서 알려줘",
                session_id="session-a",
            )
        )
    )

    assert explicit.security is not None
    assert explicit.security.ticker == "000660"
    assert inherited.security is not None
    assert inherited.security.ticker == "000660"
    assert inherited.diagnostics_public.query_plan.intent == "disclosure_summary"


def test_recent_cue_clears_old_session_date_range() -> None:
    service = _service(FakeGateway(()), ExtractiveLLM())
    asyncio.run(
        service.chat(
            ChatRequest(
                message="삼성전자 2026-07-01~2026-07-02 공시",
                session_id="session-a",
            )
        )
    )
    recent = asyncio.run(
        service.chat(
            ChatRequest(
                message="삼성전자 최근 뉴스",
                session_id="session-a",
            )
        )
    )
    follow_up = asyncio.run(
        service.chat(
            ChatRequest(
                message="그중 공시만",
                session_id="session-a",
            )
        )
    )

    assert recent.diagnostics_public.query_plan.date_start is None
    assert recent.diagnostics_public.query_plan.date_end is None
    assert follow_up.diagnostics_public.query_plan.date_start is None
    assert follow_up.diagnostics_public.query_plan.date_end is None


def test_provider_failure_still_preserves_accepted_planning_context() -> None:
    service = _service(
        FakeGateway((), status=ProviderStatus.TIMEOUT),
        ExtractiveLLM(),
    )

    failed = asyncio.run(
        service.chat(
            ChatRequest(
                message="삼성전자 최근 뉴스",
                session_id="session-a",
            )
        )
    )
    inherited = asyncio.run(
        service.chat(
            ChatRequest(
                message="이어서 알려줘",
                session_id="session-a",
            )
        )
    )

    assert failed.status == "provider_failed"
    assert inherited.security is not None
    assert inherited.security.ticker == "005930"
    assert inherited.diagnostics_public.query_plan.intent == "recent_issue"


def test_concurrent_same_session_waits_for_context_update() -> None:
    async def run() -> None:
        started = asyncio.Event()
        release = asyncio.Event()

        class BlockingGateway(FakeGateway):
            async def fetch(
                self,
                plan: QueryPlan,
                *,
                query: str,
                timeout_seconds: float,
            ) -> SourceGatewayResult:
                if self.calls == 0:
                    started.set()
                    await release.wait()
                return await super().fetch(
                    plan,
                    query=query,
                    timeout_seconds=timeout_seconds,
                )

        gateway = BlockingGateway(())
        service = _service(gateway, ExtractiveLLM())
        first_task = asyncio.create_task(
            service.chat(
                ChatRequest(
                    message="삼성전자 최근 뉴스",
                    session_id="session-a",
                )
            )
        )
        await started.wait()
        second_task = asyncio.create_task(
            service.chat(
                ChatRequest(
                    message="이어서 알려줘",
                    session_id="session-a",
                )
            )
        )
        await asyncio.sleep(0)
        assert gateway.calls == 0
        release.set()
        _, inherited = await asyncio.gather(first_task, second_task)

        assert gateway.calls == 2
        assert inherited.security is not None
        assert inherited.security.ticker == "005930"
        assert inherited.diagnostics_public.query_plan.intent == "recent_issue"

    asyncio.run(run())


def _track_budget(output: list[LLMCallBudget]) -> LLMCallBudget:
    budget = LLMCallBudget(max_calls=1)
    output.append(budget)
    return budget
