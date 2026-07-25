from __future__ import annotations

import asyncio
import json
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

import pytest
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import RunnableSequence

from app.answer.composer import AnswerComposer
from app.core.models import Evidence, FinancialDocument, QueryPlan, SecurityIdentifier
from app.evidence.budget import LLMCallBudget
from app.llm.base import (
    LLMMessage,
    LLMRequest,
    LLMResult,
    LLMStatus,
    create_llm_result,
)

BASIS_AT = datetime(2026, 7, 25, tzinfo=UTC)
SECURITY_ID = "KRX:005930"
SNIPPET = "삼성전자의 반도체 투자가 확대됐다."


class FakeLLMClient:
    def __init__(
        self,
        content: str | None,
        *,
        status: LLMStatus = LLMStatus.OK,
    ) -> None:
        self.content = content
        self.status = status
        self.calls: list[tuple[LLMRequest, float]] = []

    async def complete(
        self,
        request: LLMRequest,
        *,
        timeout_seconds: float,
    ) -> LLMResult:
        self.calls.append((request, timeout_seconds))
        return create_llm_result(
            status=self.status,
            content=self.content if self.status == LLMStatus.OK else None,
            model="gemini/gemini-2.5-flash",
            provider="gemini",
            usage={"total_tokens": 9} if self.status == LLMStatus.OK else {},
            finish_reason="stop" if self.status == LLMStatus.OK else None,
            latency_ms=2,
        )


def _security() -> SecurityIdentifier:
    return SecurityIdentifier(
        market="KRX",
        ticker="005930",
        security_name="삼성전자",
        security_type="common_stock",
        corp_code="00126380",
        corp_name="삼성전자",
    )


def _plan() -> QueryPlan:
    return QueryPlan(
        security=_security(),
        intent="recent_issue",
        required_sources=["news"],
        required_evidence=["recent_news"],
        requires_clarification=False,
    )


def _document(
    *,
    source_type: str = "news",
    permission: object = True,
) -> FinancialDocument:
    source_url = "https://news.example.test/article"
    return FinancialDocument(
        document_id=f"document:{source_type}:unit",
        source_type=source_type,
        provider="recorded",
        primary_security_ids=[SECURITY_ID],
        mentioned_security_ids=[],
        title="삼성전자 투자",
        published_at=BASIS_AT,
        source_url=source_url,
        text=SNIPPET,
        locator=(
            {
                "provider": "recorded_news",
                "source_url": source_url,
                "published_at": BASIS_AT.isoformat(),
                "raw_index": 0,
                "query": "삼성전자 투자",
            }
            if source_type == "news"
            else {
                "manifest_id": "samsung-report-001",
                "document_id": "document:research_report:unit",
                "page": 1,
                "page_basis": "pdf_1_based",
                "section": "투자",
                "publisher": "Approved Research",
                "source_url": source_url,
                "source_asset_id": None,
                "access_note": "approved fixture",
            }
        ),
        metadata={"external_llm_processing_allowed": permission},
        ingestion_version="unit-v1",
    )


def _evidence(
    *,
    source_type: str = "news",
    evidence_id: str | None = None,
    subject_security_ids: list[str] | None = None,
    source_url: str | None | object = ...,
    locator: dict[str, Any] | None = None,
    snippet: str = SNIPPET,
) -> Evidence:
    document = _document(source_type=source_type)
    actual_url = document.source_url if source_url is ... else source_url
    return Evidence(
        evidence_id=evidence_id or f"evidence:{source_type}:unit",
        document_id=document.document_id,
        source_type=source_type,
        title=document.title,
        source_url=actual_url,
        published_at=BASIS_AT,
        subject_security_ids=subject_security_ids or [SECURITY_ID],
        mentioned_security_ids=[],
        scope="company_specific",
        snippet=snippet,
        locator=deepcopy(locator if locator is not None else document.locator),
        retrieval_score=0.8,
    )


def _draft(
    *,
    text: str = SNIPPET,
    evidence_id: str = "evidence:news:unit",
    extra: dict[str, Any] | None = None,
) -> str:
    claim: dict[str, Any] = {
        "claim_id": "claim-1",
        "section": "summary",
        "text": text,
        "evidence_ids": [evidence_id],
    }
    claim.update(extra or {})
    return json.dumps({"claims": [claim]}, ensure_ascii=False)


def test_real_chain_accepts_only_citation_bound_structured_draft() -> None:
    client = FakeLLMClient(_draft())
    document = _document()
    evidence = _evidence()
    composer = AnswerComposer(client)

    result = asyncio.run(
        composer.compose(
            question="삼성전자 최근 이슈",
            plan=_plan(),
            selected_evidence=[evidence],
            documents_by_id={document.document_id: document},
            timeout_seconds=3.5,
        )
    )

    assert isinstance(composer.chain, RunnableSequence)
    assert result.generation_mode == "llm"
    assert result.answer_sections.summary == [SNIPPET]
    assert len(result.citations.citations) == 1
    assert result.citations.rejections == ()
    assert len(client.calls) == 1
    request, timeout = client.calls[0]
    assert timeout == 3.5
    rendered = "\n".join(message.content for message in request.messages)
    assert "삼성전자 최근 이슈" in rendered
    assert evidence.evidence_id in rendered
    assert SNIPPET in rendered
    for forbidden in ("https://", "source_url", "locator", "permission"):
        assert forbidden not in rendered


def test_production_graph_contains_actual_pydantic_parser_stage() -> None:
    composer = AnswerComposer(FakeLLMClient(_draft()))
    graph_repr = repr(composer.chain)

    assert isinstance(composer.chain, RunnableSequence)
    assert isinstance(composer._parser, PydanticOutputParser)
    assert graph_repr.index("ChatPromptTemplate") < graph_repr.index("_audit_prompt")
    assert graph_repr.index("_audit_prompt") < graph_repr.index("_call_client")
    assert "PydanticOutputParser" in graph_repr


def test_one_eligible_request_reserves_exactly_one_call() -> None:
    budget = LLMCallBudget(max_calls=1)
    client = FakeLLMClient(_draft())
    document = _document()

    result = asyncio.run(
        AnswerComposer(client).compose(
            question="?쇱꽦?꾩옄 理쒓렐 ?댁뒋",
            plan=_plan(),
            selected_evidence=[_evidence()],
            documents_by_id={document.document_id: document},
            timeout_seconds=2,
            call_budget=budget,
        )
    )

    assert result.generation_mode == "llm"
    assert budget.snapshot().calls_used == 1
    assert budget.snapshot().calls_remaining == 0
    assert len(client.calls) == 1


@pytest.mark.parametrize(
    "content",
    [
        '{"claims":',
        json.dumps({"claims": []}),
        _draft(extra={"unknown": "rejected"}),
        _draft(text="근거에 없는 문장"),
        _draft(evidence_id="evidence:unknown"),
    ],
)
def test_invalid_draft_falls_back_without_retry(content: str) -> None:
    client = FakeLLMClient(content)
    document = _document()
    evidence = _evidence()
    budget = LLMCallBudget(max_calls=1)

    result = asyncio.run(
        AnswerComposer(client).compose(
            question="삼성전자 최근 이슈",
            plan=_plan(),
            selected_evidence=[evidence],
            documents_by_id={document.document_id: document},
            timeout_seconds=2,
            call_budget=budget,
        )
    )

    assert result.generation_mode == "fixed_template"
    assert result.answer_sections.summary == [SNIPPET]
    assert result.llm_result is not None
    assert result.llm_result.status == LLMStatus.INVALID_RESPONSE
    assert len(client.calls) == 1
    assert budget.snapshot().calls_used == 1


def test_llm_failure_preserves_fixed_extractive_answer() -> None:
    client = FakeLLMClient(None, status=LLMStatus.TIMEOUT)
    document = _document()
    evidence = _evidence()

    result = asyncio.run(
        AnswerComposer(client).compose(
            question="삼성전자 최근 이슈",
            plan=_plan(),
            selected_evidence=[evidence],
            documents_by_id={document.document_id: document},
            timeout_seconds=2,
        )
    )

    assert result.generation_mode == "fixed_template"
    assert result.answer_sections.summary == [SNIPPET]
    assert result.llm_result is not None
    assert result.llm_result.status == LLMStatus.TIMEOUT
    assert len(client.calls) == 1


@pytest.mark.parametrize("permission", [False, None, "true", 1])
def test_research_report_requires_exact_external_permission(
    permission: object,
) -> None:
    client = FakeLLMClient(
        _draft(evidence_id="evidence:research_report:unit")
    )
    document = _document(source_type="research_report", permission=permission)
    evidence = _evidence(source_type="research_report")
    plan = _plan().model_copy(
        update={
            "intent": "research_report_summary",
            "required_sources": ["research_report"],
            "required_evidence": ["research_report"],
        },
        deep=True,
    )

    result = asyncio.run(
        AnswerComposer(client).compose(
            question="삼성전자 리포트 요약",
            plan=plan,
            selected_evidence=[evidence],
            documents_by_id={document.document_id: document},
            timeout_seconds=2,
        )
    )

    assert result.generation_mode == "fixed_template"
    assert client.calls == []
    assert result.transmitted_evidence == ()


def test_research_report_with_exact_permission_is_transmitted() -> None:
    client = FakeLLMClient(
        _draft(evidence_id="evidence:research_report:unit")
    )
    document = _document(source_type="research_report", permission=True)
    evidence = _evidence(source_type="research_report")
    plan = _plan().model_copy(
        update={
            "intent": "research_report_summary",
            "required_sources": ["research_report"],
            "required_evidence": ["research_report"],
        },
        deep=True,
    )

    result = asyncio.run(
        AnswerComposer(client).compose(
            question="삼성전자 리포트 요약",
            plan=plan,
            selected_evidence=[evidence],
            documents_by_id={document.document_id: document},
            timeout_seconds=2,
        )
    )

    assert result.generation_mode == "llm"
    assert len(client.calls) == 1


def test_prompt_safety_failure_is_closed_and_does_not_call_model() -> None:
    client = FakeLLMClient(_draft())
    document = _document()
    evidence = _evidence()
    budget = LLMCallBudget(max_calls=1)

    result = asyncio.run(
        AnswerComposer(client).compose(
            question="api_key=" + "-".join(("secret", "sentinel")),
            plan=_plan(),
            selected_evidence=[evidence],
            documents_by_id={document.document_id: document},
            timeout_seconds=2,
            call_budget=budget,
        )
    )

    assert result.generation_mode == "fixed_template"
    assert client.calls == []
    assert budget.snapshot().calls_used == 0
    assert "sentinel" not in json.dumps(
        result.answer_sections.model_dump(),
        ensure_ascii=False,
    )


def test_exhausted_budget_fails_closed_without_client_call() -> None:
    budget = LLMCallBudget(max_calls=1)
    budget.reserve_call()
    client = FakeLLMClient(_draft())
    document = _document()

    result = asyncio.run(
        AnswerComposer(client).compose(
            question="?쇱꽦?꾩옄 理쒓렐 ?댁뒋",
            plan=_plan(),
            selected_evidence=[_evidence()],
            documents_by_id={document.document_id: document},
            timeout_seconds=2,
            call_budget=budget,
        )
    )

    assert result.generation_mode == "fixed_template"
    assert result.llm_result is None
    assert len(client.calls) == 0
    assert budget.snapshot().calls_used == 1


def test_no_eligible_evidence_does_not_reserve_call() -> None:
    budget = LLMCallBudget(max_calls=1)
    client = FakeLLMClient(
        _draft(evidence_id="evidence:research_report:unit")
    )
    document = _document(source_type="research_report", permission=False)

    result = asyncio.run(
        AnswerComposer(client).compose(
            question="?쇱꽦?꾩옄 由ы룷???붿빟",
            plan=_plan().model_copy(
                update={
                    "intent": "research_report_summary",
                    "required_sources": ["research_report"],
                    "required_evidence": ["research_report"],
                },
                deep=True,
            ),
            selected_evidence=[_evidence(source_type="research_report")],
            documents_by_id={document.document_id: document},
            timeout_seconds=2,
            call_budget=budget,
        )
    )

    assert result.generation_mode == "fixed_template"
    assert client.calls == []
    assert budget.snapshot().calls_used == 0


def test_blocked_fixed_result_ignores_unexpected_evidence() -> None:
    blocked = _plan().model_copy(
        update={
            "security": None,
            "intent": "prohibited_advice",
            "required_sources": [],
            "required_evidence": [],
            "requires_clarification": True,
        },
        deep=True,
    )

    result = AnswerComposer(FakeLLMClient(_draft())).compose_fixed(
        plan=blocked,
        selected_evidence=[_evidence()],
        fallback_reason="blocked",
    )

    assert result.generation_mode == "blocked"
    assert result.claims == ()
    assert result.citations.citations == ()
    assert result.answer_sections.facts == []
    assert SNIPPET not in result.answer_sections.summary


def test_fixed_result_keeps_only_citation_safe_evidence_in_order() -> None:
    valid = _evidence(evidence_id="evidence:news:valid")
    wrong_company = _evidence(
        evidence_id="evidence:news:wrong-company",
        subject_security_ids=["KRX:000660"],
    )
    unsafe_url = _evidence(
        evidence_id="evidence:news:unsafe-url",
        source_url="https://news.example.test/article?api-key="
        + "-".join(("secret", "sentinel")),
    )

    result = AnswerComposer(FakeLLMClient(_draft())).compose_fixed(
        plan=_plan(),
        selected_evidence=[valid, wrong_company, unsafe_url],
    )

    assert [claim.evidence_ids for claim in result.claims] == [
        ("evidence:news:valid",)
    ]
    assert [item.evidence_id for item in result.public_evidence] == [
        "evidence:news:valid"
    ]
    assert result.answer_sections.summary == [SNIPPET]
    assert result.answer_sections.facts == []
    assert result.citation_rejection_count == 2


@pytest.mark.parametrize(
    "unsafe_locator",
    [
        {
            "provider": "recorded_news",
            "source_url": "https://news.example.test/article",
            "published_at": BASIS_AT.isoformat(),
            "raw_index": 0,
            "query": "?쇱꽦?꾩옄 ?ъ옄",
            "api_key": "-".join(("secret", "sentinel")),
        },
        {
            "provider": "recorded_news",
            "source_url": "https://news.example.test/article",
            "published_at": BASIS_AT.isoformat(),
            "raw_index": 0,
            "query": "?쇱꽦?꾩옄 ?ъ옄",
            "private_path": "C:\\private\\report.txt",
        },
    ],
)
def test_fixed_result_fails_closed_for_unsafe_locator(
    unsafe_locator: dict[str, Any],
) -> None:
    unsafe = _evidence().model_copy(update={"locator": unsafe_locator}, deep=True)

    result = AnswerComposer(FakeLLMClient(_draft())).compose_fixed(
        plan=_plan(),
        selected_evidence=[unsafe],
    )

    assert result.claims == ()
    assert result.citations.citations == ()
    assert result.public_evidence == ()
    serialized = result.answer_sections.model_dump_json()
    assert "sentinel" not in serialized
    assert "C:\\private" not in serialized


def test_equal_input_is_deterministic_and_caller_values_are_not_mutated() -> None:
    client = FakeLLMClient(_draft())
    document = _document()
    evidence = _evidence()
    snapshot = evidence.model_dump(mode="python")
    composer = AnswerComposer(client)

    async def run_twice() -> tuple[Any, Any]:
        first = await composer.compose(
            question="삼성전자 최근 이슈",
            plan=_plan(),
            selected_evidence=[evidence],
            documents_by_id={document.document_id: document},
            timeout_seconds=2,
        )
        second = await composer.compose(
            question="삼성전자 최근 이슈",
            plan=_plan(),
            selected_evidence=[evidence],
            documents_by_id={document.document_id: document},
            timeout_seconds=2,
        )
        return first, second

    first, second = asyncio.run(run_twice())

    assert first.answer_sections.model_dump_json() == second.answer_sections.model_dump_json()
    assert first.citations == second.citations
    assert evidence.model_dump(mode="python") == snapshot
    assert first.answer_sections is not second.answer_sections
