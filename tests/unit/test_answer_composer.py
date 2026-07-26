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


def test_llm_failure_rejects_unsafe_conflict_fallback_without_retry() -> None:
    unsafe = "긍정 기사가 더 많으므로 상승이 우세하다."
    client = FakeLLMClient(None, status=LLMStatus.TIMEOUT)
    document = _document()
    evidence = _evidence(snippet=unsafe)

    result = asyncio.run(
        AnswerComposer(client).compose(
            question="삼성전자 긍정 요인과 위험 요인",
            plan=_plan(),
            selected_evidence=[evidence],
            documents_by_id={document.document_id: document},
            timeout_seconds=2,
        )
    )

    assert result.generation_mode == "fixed_template"
    assert result.answer_sections.summary == [
        "답변에 사용할 수 있는 근거를 확인하지 못했습니다."
    ]
    assert result.claims == ()
    assert result.citations.citations == ()
    assert result.public_evidence == ()
    assert unsafe not in result.answer_sections.model_dump_json()
    assert len(client.calls) == 1


def test_fixed_fallback_keeps_neutral_fact_after_conflict_rejection() -> None:
    unsafe = _evidence(
        evidence_id="evidence:news:unsafe",
        snippet="긍정 감성 점수는 80점이다.",
    )
    neutral = _evidence(
        evidence_id="evidence:news:neutral",
        snippet="뉴스는 공급 일정과 원가 변수를 각각 설명했다.",
    )

    result = AnswerComposer(FakeLLMClient(_draft())).compose_fixed(
        plan=_plan(),
        selected_evidence=[unsafe, neutral],
    )

    assert result.generation_mode == "fixed_template"
    assert result.answer_sections.summary == [neutral.snippet]
    assert [item.evidence_id for item in result.public_evidence] == [
        neutral.evidence_id
    ]
    assert unsafe.snippet not in result.answer_sections.model_dump_json()


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


def test_beginner_sections_are_kept_in_explicit_order() -> None:
    snippets = (
        "핵심 결론이다.",
        "확인된 사실이다.",
        "자료의 의미다.",
        "AI 추론이다.",
        "긍정 조건이다.",
        "위험 조건이다.",
        "추가 확인이 필요하다.",
    )
    evidence = _evidence(snippet=" ".join(snippets))
    sections = (
        "summary",
        "facts",
        "interpretation",
        "inference",
        "positive_factors",
        "risk_factors",
        "uncertainty",
    )
    content = json.dumps(
        {
            "claims": [
                {
                    "claim_id": f"claim-{index}",
                    "section": section,
                    "text": text,
                    "evidence_ids": [evidence.evidence_id],
                }
                for index, (section, text) in enumerate(
                    zip(sections, snippets, strict=True),
                    start=1,
                )
            ]
        },
        ensure_ascii=False,
    )

    result = asyncio.run(
        AnswerComposer(FakeLLMClient(content)).compose(
            question="삼성전자 최근 이슈",
            plan=_plan(),
            selected_evidence=[evidence],
            documents_by_id={_document().document_id: _document()},
            timeout_seconds=2,
        )
    )

    assert result.generation_mode == "llm"
    assert list(result.answer_sections.model_dump()) == list(sections)
    assert result.answer_sections.inference == ["AI 추론이다."]


@pytest.mark.parametrize(
    "claims",
    [
        [
            {
                "claim_id": "facts-first",
                "section": "facts",
                "text": SNIPPET,
                "evidence_ids": ["evidence:news:unit"],
            }
        ],
        [
            {
                "claim_id": "summary-1",
                "section": "summary",
                "text": SNIPPET,
                "evidence_ids": ["evidence:news:unit"],
            },
            {
                "claim_id": "summary-2",
                "section": "summary",
                "text": SNIPPET,
                "evidence_ids": ["evidence:news:unit"],
            },
        ],
        [
            {
                "claim_id": "summary",
                "section": "summary",
                "text": SNIPPET,
                "evidence_ids": ["evidence:news:unit"],
            },
            {
                "claim_id": "facts-late",
                "section": "facts",
                "text": SNIPPET,
                "evidence_ids": ["evidence:news:unit"],
            },
        ][::-1],
    ],
)
def test_malformed_beginner_structure_fails_closed_without_retry(
    claims: list[dict[str, Any]],
) -> None:
    client = FakeLLMClient(
        json.dumps({"claims": claims}, ensure_ascii=False)
    )

    result = asyncio.run(
        AnswerComposer(client).compose(
            question="삼성전자 최근 이슈",
            plan=_plan(),
            selected_evidence=[_evidence()],
            documents_by_id={_document().document_id: _document()},
            timeout_seconds=2,
        )
    )

    assert result.generation_mode == "fixed_template"
    assert len(client.calls) == 1
    assert result.citation_rejection_count == 1


@pytest.mark.parametrize(
    "duplicate_sections",
    [
        ("summary", "facts"),
        ("positive_factors", "risk_factors"),
    ],
)
def test_duplicate_claim_text_across_sections_fails_without_retry(
    duplicate_sections: tuple[str, str],
) -> None:
    summary_text = "요약 문장이다."
    duplicate_text = "같은 주장이다."
    evidence = _evidence(snippet=f"{summary_text} {duplicate_text}")
    claims = []
    if duplicate_sections[0] != "summary":
        claims.append(
            {
                "claim_id": "summary",
                "section": "summary",
                "text": summary_text,
                "evidence_ids": [evidence.evidence_id],
            }
        )
    claims.extend(
        {
            "claim_id": f"duplicate-{index}",
            "section": section,
            "text": duplicate_text,
            "evidence_ids": [evidence.evidence_id],
        }
        for index, section in enumerate(duplicate_sections, start=1)
    )
    client = FakeLLMClient(
        json.dumps({"claims": claims}, ensure_ascii=False)
    )

    result = asyncio.run(
        AnswerComposer(client).compose(
            question="삼성전자 최근 이슈",
            plan=_plan(),
            selected_evidence=[evidence],
            documents_by_id={_document().document_id: _document()},
            timeout_seconds=2,
        )
    )

    assert result.generation_mode == "fixed_template"
    assert result.citation_rejection_count == 1
    assert len(client.calls) == 1


def test_duplicate_text_and_evidence_occurrence_fails_without_retry() -> None:
    summary_text = "요약 문장이다."
    duplicate_text = "중복 사실이다."
    evidence = _evidence(snippet=f"{summary_text} {duplicate_text}")
    claims = [
        {
            "claim_id": "summary",
            "section": "summary",
            "text": summary_text,
            "evidence_ids": [evidence.evidence_id],
        },
        *[
            {
                "claim_id": f"fact-{index}",
                "section": "facts",
                "text": duplicate_text,
                "evidence_ids": [evidence.evidence_id],
            }
            for index in range(2)
        ],
    ]
    client = FakeLLMClient(
        json.dumps({"claims": claims}, ensure_ascii=False)
    )

    result = asyncio.run(
        AnswerComposer(client).compose(
            question="삼성전자 최근 이슈",
            plan=_plan(),
            selected_evidence=[evidence],
            documents_by_id={_document().document_id: _document()},
            timeout_seconds=2,
        )
    )

    assert result.generation_mode == "fixed_template"
    assert result.citation_rejection_count == 1
    assert len(client.calls) == 1


def test_distinct_claims_using_same_evidence_are_accepted() -> None:
    summary_text = "첫 번째 주장이다."
    fact_text = "두 번째 주장이다."
    evidence = _evidence(snippet=f"{summary_text} {fact_text}")
    client = FakeLLMClient(
        json.dumps(
            {
                "claims": [
                    {
                        "claim_id": "summary",
                        "section": "summary",
                        "text": summary_text,
                        "evidence_ids": [evidence.evidence_id],
                    },
                    {
                        "claim_id": "fact",
                        "section": "facts",
                        "text": fact_text,
                        "evidence_ids": [evidence.evidence_id],
                    },
                ]
            },
            ensure_ascii=False,
        )
    )

    result = asyncio.run(
        AnswerComposer(client).compose(
            question="삼성전자 최근 이슈",
            plan=_plan(),
            selected_evidence=[evidence],
            documents_by_id={_document().document_id: _document()},
            timeout_seconds=2,
        )
    )

    assert result.generation_mode == "llm"
    assert result.answer_sections.summary == [summary_text]
    assert result.answer_sections.facts == [fact_text]
    assert len(client.calls) == 1


def test_report_plan_event_condition_and_risk_mapping_is_accepted() -> None:
    snippets = (
        "회사는 설비 투자를 확대할 계획이다.",
        "신규 설비 가동은 4분기로 예정됐다.",
        "수요 회복은 성장 조건이다.",
        "원가 상승은 위험 조건이다.",
        "실제 수요는 추가 확인이 필요하다.",
    )
    evidence = _evidence(
        source_type="research_report",
        snippet=" ".join(snippets),
    )
    claims = [
        ("summary", snippets[0]),
        ("facts", snippets[1]),
        ("positive_factors", snippets[2]),
        ("risk_factors", snippets[3]),
        ("uncertainty", snippets[4]),
    ]
    content = json.dumps(
        {
            "claims": [
                {
                    "claim_id": f"report-{index}",
                    "section": section,
                    "text": text,
                    "evidence_ids": [evidence.evidence_id],
                }
                for index, (section, text) in enumerate(claims, start=1)
            ]
        },
        ensure_ascii=False,
    )
    plan = _plan().model_copy(
        update={
            "intent": "research_report_summary",
            "required_sources": ["research_report"],
            "required_evidence": ["research_report"],
        },
        deep=True,
    )
    document = _document(source_type="research_report", permission=True)

    result = asyncio.run(
        AnswerComposer(FakeLLMClient(content)).compose(
            question="삼성전자 리포트 요약",
            plan=plan,
            selected_evidence=[evidence],
            documents_by_id={document.document_id: document},
            timeout_seconds=2,
        )
    )

    assert result.generation_mode == "llm"
    assert result.answer_sections.facts == [snippets[1]]
    assert result.answer_sections.positive_factors == [snippets[2]]
    assert result.answer_sections.risk_factors == [snippets[3]]
    assert result.answer_sections.uncertainty == [snippets[4]]


@pytest.mark.parametrize(
    ("intent", "snippet"),
    [
        ("recent_issue", "지금 매수하세요."),
        ("research_report_summary", "실적 개선이 보장된다."),
    ],
)
def test_direct_advice_or_report_future_certainty_fails_closed(
    intent: str,
    snippet: str,
) -> None:
    source_type = (
        "research_report"
        if intent == "research_report_summary"
        else "news"
    )
    evidence = _evidence(source_type=source_type, snippet=snippet)
    document = _document(source_type=source_type, permission=True)
    plan = _plan().model_copy(
        update={
            "intent": intent,
            "required_sources": [source_type],
            "required_evidence": [source_type],
        },
        deep=True,
    )
    client = FakeLLMClient(
        _draft(
            text=snippet,
            evidence_id=evidence.evidence_id,
        )
    )

    result = asyncio.run(
        AnswerComposer(client).compose(
            question="자료 요약",
            plan=plan,
            selected_evidence=[evidence],
            documents_by_id={document.document_id: document},
            timeout_seconds=2,
        )
    )

    assert result.generation_mode == "fixed_template"
    assert len(client.calls) == 1
    assert result.citation_rejection_count >= 1
    assert snippet not in result.answer_sections.model_dump_json()


def test_unsupported_numeric_claim_is_removed_without_second_llm_call() -> None:
    summary = "회사는 신규 설비 계획을 발표했다."
    unsupported = "투자 규모는 20조원이다."
    evidence = _evidence(
        snippet=f"{summary} 투자 규모는 2조원이다.",
    )
    content = json.dumps(
        {
            "claims": [
                {
                    "claim_id": "summary",
                    "section": "summary",
                    "text": summary,
                    "evidence_ids": [evidence.evidence_id],
                },
                {
                    "claim_id": "fact",
                    "section": "facts",
                    "text": unsupported,
                    "evidence_ids": [evidence.evidence_id],
                },
            ]
        },
        ensure_ascii=False,
    )
    client = FakeLLMClient(content)

    result = asyncio.run(
        AnswerComposer(client).compose(
            question="삼성전자 최근 투자 계획",
            plan=_plan(),
            selected_evidence=[evidence],
            documents_by_id={_document().document_id: _document()},
            timeout_seconds=2,
        )
    )

    assert result.generation_mode == "llm"
    assert result.answer_sections.summary == [summary]
    assert result.answer_sections.facts == []
    assert unsupported not in result.answer_sections.model_dump_json()
    assert result.citation_rejection_count == 1
    assert len(client.calls) == 1


def test_removed_numeric_summary_uses_supported_fixed_fallback() -> None:
    unsupported = "투자 규모는 20조원이다."
    evidence = _evidence(snippet="실제 투자 규모는 2조원이다.")
    content = json.dumps(
        {
            "claims": [
                {
                    "claim_id": "summary",
                    "section": "summary",
                    "text": unsupported,
                    "evidence_ids": [evidence.evidence_id],
                },
                {
                    "claim_id": "fact",
                    "section": "facts",
                    "text": "회사는 투자 계획을 발표했다.",
                    "evidence_ids": [evidence.evidence_id],
                },
            ]
        },
        ensure_ascii=False,
    )
    client = FakeLLMClient(content)

    result = asyncio.run(
        AnswerComposer(client).compose(
            question="삼성전자 최근 투자 계획",
            plan=_plan(),
            selected_evidence=[evidence],
            documents_by_id={_document().document_id: _document()},
            timeout_seconds=2,
        )
    )

    assert result.generation_mode == "fixed_template"
    assert result.answer_sections.summary == [evidence.snippet]
    assert unsupported not in result.answer_sections.model_dump_json()
    assert result.citation_rejection_count >= 2
    assert len(client.calls) == 1


def test_wrong_company_numeric_evidence_is_rejected() -> None:
    evidence = _evidence(
        snippet="매출은 10억원이다.",
        subject_security_ids=["KRX:000660"],
    )
    client = FakeLLMClient(
        _draft(
            text="매출은 10억원이다.",
            evidence_id=evidence.evidence_id,
        )
    )

    result = asyncio.run(
        AnswerComposer(client).compose(
            question="삼성전자 매출",
            plan=_plan(),
            selected_evidence=[evidence],
            documents_by_id={_document().document_id: _document()},
            timeout_seconds=2,
        )
    )

    assert result.generation_mode == "fixed_template"
    assert result.public_evidence == ()
    assert result.citation_rejection_count >= 1
    assert len(client.calls) == 1


def test_industry_mention_is_not_promoted_to_subject() -> None:
    evidence = Evidence(
        evidence_id="evidence:news:mentioned-only",
        document_id="document:news:unit",
        source_type="news",
        title="산업 기사",
        source_url="https://news.example.test/article",
        published_at=BASIS_AT,
        subject_security_ids=[],
        mentioned_security_ids=[SECURITY_ID],
        scope="industry_common",
        snippet="업계 투자 규모는 10조원이다.",
        locator={
            "provider": "recorded_news",
            "source_url": "https://news.example.test/article",
            "published_at": BASIS_AT.isoformat(),
            "raw_index": 0,
            "query": "삼성전자 투자",
        },
        retrieval_score=0.8,
    )
    before = evidence.model_dump(mode="python")
    client = FakeLLMClient(
        _draft(
            text=evidence.snippet,
            evidence_id=evidence.evidence_id,
        )
    )

    result = asyncio.run(
        AnswerComposer(client).compose(
            question="삼성전자 업계 투자",
            plan=_plan(),
            selected_evidence=[evidence],
            documents_by_id={_document().document_id: _document()},
            timeout_seconds=2,
        )
    )

    assert result.generation_mode == "llm"
    assert result.public_evidence[0].subject_security_ids == []
    assert result.public_evidence[0].mentioned_security_ids == [SECURITY_ID]
    assert evidence.model_dump(mode="python") == before


def test_m3_projection_is_source_diverse_deterministic_and_limited_to_three() -> None:
    report = _evidence(
        source_type="research_report",
        evidence_id="evidence:report:1",
        snippet="리포트는 설비 계획을 설명했다.",
    )
    news = _evidence(
        evidence_id="evidence:news:1",
        snippet="뉴스는 공급 일정을 설명했다.",
    )
    disclosure = _evidence(
        source_type="disclosure",
        evidence_id="evidence:disclosure:1",
        snippet="공시는 투자 결정을 설명했다.",
    )
    extra_news = _evidence(
        evidence_id="evidence:news:2",
        snippet="추가 뉴스는 수요를 설명했다.",
    )
    plan = _plan().model_copy(
        update={
            "intent": "multi_source_summary",
            "required_sources": [
                "research_report",
                "news",
                "disclosure",
            ],
            "required_evidence": ["multi_source"],
        },
        deep=True,
    )
    client = FakeLLMClient(
        _draft(
            text=report.snippet,
            evidence_id=report.evidence_id,
        )
    )
    documents = {
        document.document_id: document
        for document in (
            _document(source_type="research_report", permission=True),
            _document(source_type="news"),
            _document(source_type="disclosure"),
        )
    }
    before = [
        item.model_dump(mode="python")
        for item in (news, disclosure, report, extra_news)
    ]

    result = asyncio.run(
        AnswerComposer(client).compose(
            question="삼성전자 여러 자료 요약",
            plan=plan,
            selected_evidence=[news, disclosure, report, extra_news],
            documents_by_id=documents,
            timeout_seconds=2,
        )
    )

    assert result.generation_mode == "llm"
    assert [item.evidence_id for item in result.transmitted_evidence] == [
        report.evidence_id,
        news.evidence_id,
        disclosure.evidence_id,
    ]
    assert len(result.transmitted_evidence) == 3
    assert result.public_evidence == (report,)
    rendered = "\n".join(
        message.content for message in client.calls[0][0].messages
    )
    assert extra_news.evidence_id not in rendered
    assert before == [
        item.model_dump(mode="python")
        for item in (news, disclosure, report, extra_news)
    ]


def test_permission_denied_report_is_excluded_before_projection_and_refilled() -> None:
    denied_report = _evidence(
        source_type="research_report",
        evidence_id="evidence:report:denied",
        snippet="비전송 리포트다.",
    )
    news = _evidence(
        evidence_id="evidence:news:1",
        snippet="뉴스는 공급 일정을 설명했다.",
    )
    disclosure = _evidence(
        source_type="disclosure",
        evidence_id="evidence:disclosure:1",
        snippet="공시는 투자 결정을 설명했다.",
    )
    extra_news = _evidence(
        evidence_id="evidence:news:2",
        snippet="추가 뉴스는 수요를 설명했다.",
    )
    plan = _plan().model_copy(
        update={
            "intent": "multi_source_summary",
            "required_sources": [
                "research_report",
                "news",
                "disclosure",
            ],
            "required_evidence": ["multi_source"],
        },
        deep=True,
    )
    client = FakeLLMClient(
        _draft(
            text=news.snippet,
            evidence_id=news.evidence_id,
        )
    )
    documents = {
        document.document_id: document
        for document in (
            _document(source_type="research_report", permission=False),
            _document(source_type="news"),
            _document(source_type="disclosure"),
        )
    }

    result = asyncio.run(
        AnswerComposer(client).compose(
            question="삼성전자 여러 자료 요약",
            plan=plan,
            selected_evidence=[
                denied_report,
                news,
                disclosure,
                extra_news,
            ],
            documents_by_id=documents,
            timeout_seconds=2,
        )
    )

    assert result.generation_mode == "llm"
    assert [item.evidence_id for item in result.transmitted_evidence] == [
        news.evidence_id,
        disclosure.evidence_id,
        extra_news.evidence_id,
    ]
    rendered = "\n".join(
        message.content for message in client.calls[0][0].messages
    )
    assert denied_report.evidence_id not in rendered
    assert denied_report.snippet not in rendered


def test_two_sided_composition_requires_uncertainty_without_retry() -> None:
    snippets = {
        "summary": "수요와 원가 변수가 함께 확인됐다.",
        "positive_factors": "수요 증가는 긍정 요인이다.",
        "risk_factors": "원가 상승은 위험 요인이다.",
    }
    evidence = _evidence(snippet=" ".join(snippets.values()))
    content = json.dumps(
        {
            "claims": [
                {
                    "claim_id": section,
                    "section": section,
                    "text": text,
                    "evidence_ids": [evidence.evidence_id],
                }
                for section, text in snippets.items()
            ]
        },
        ensure_ascii=False,
    )
    client = FakeLLMClient(content)

    result = asyncio.run(
        AnswerComposer(client).compose(
            question="삼성전자 긍정 요인과 위험 요인",
            plan=_plan().model_copy(
                update={"intent": "risk_factors"},
                deep=True,
            ),
            selected_evidence=[evidence],
            documents_by_id={_document().document_id: _document()},
            timeout_seconds=2,
        )
    )

    assert result.generation_mode == "fixed_template"
    assert result.citation_rejection_count >= 3
    assert len(client.calls) == 1


def test_two_sided_composition_keeps_parallel_supported_views() -> None:
    snippets = {
        "summary": "수요와 원가 변수가 함께 확인됐다.",
        "positive_factors": "수요 증가는 긍정 요인이다.",
        "risk_factors": "원가 상승은 위험 요인이다.",
        "uncertainty": "실제 영향은 추가 확인이 필요하다.",
    }
    evidence = _evidence(snippet=" ".join(snippets.values()))
    content = json.dumps(
        {
            "claims": [
                {
                    "claim_id": section,
                    "section": section,
                    "text": text,
                    "evidence_ids": [evidence.evidence_id],
                }
                for section, text in snippets.items()
            ]
        },
        ensure_ascii=False,
    )

    result = asyncio.run(
        AnswerComposer(FakeLLMClient(content)).compose(
            question="삼성전자 긍정 요인과 위험 요인",
            plan=_plan().model_copy(
                update={"intent": "risk_factors"},
                deep=True,
            ),
            selected_evidence=[evidence],
            documents_by_id={_document().document_id: _document()},
            timeout_seconds=2,
        )
    )

    assert result.generation_mode == "llm"
    assert result.answer_sections.positive_factors == [
        snippets["positive_factors"]
    ]
    assert result.answer_sections.risk_factors == [snippets["risk_factors"]]
    assert result.answer_sections.uncertainty == [snippets["uncertainty"]]
