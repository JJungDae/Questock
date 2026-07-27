from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime

import pytest

from app.answer.composer import AnswerComposer
from app.api.schemas import ChatRequest
from app.core.status import ProviderStatus, RetrievalStatus
from app.ingest.glossary import (
    GlossaryCorpusValidationError,
    evaluate_actual_glossary_coverage,
)
from app.llm.base import (
    LLMRequest,
    LLMResult,
    LLMStatus,
    create_llm_result,
)
from app.services import glossary_service as glossary_module
from app.services.chat_service import ChatService
from app.services.glossary_service import (
    GlossaryService,
    select_glossary_context,
)

BASIS_AT = datetime(2026, 7, 25, 3, tzinfo=UTC)


class GlossaryLLM:
    def __init__(self, *, invalid_section: bool = False) -> None:
        self.invalid_section = invalid_section
        self.calls = 0
        self.last_prompt = ""

    async def complete(
        self,
        request: LLMRequest,
        *,
        timeout_seconds: float,
    ) -> LLMResult:
        self.calls += 1
        self.last_prompt = "\n".join(
            item.content for item in request.messages
        )
        evidence = _prompt_evidence(self.last_prompt)
        section_order = {
            "definition": 0,
            "formula": 1,
            "example": 1,
            "why_it_matters": 2,
            "caution": 3,
        }
        answer_section = {
            "definition": "summary",
            "formula": "facts",
            "example": "facts",
            "why_it_matters": "interpretation",
            "caution": "uncertainty",
        }
        claims = []
        for index, item in enumerate(
            sorted(evidence, key=lambda value: section_order[value["section"]])
        ):
            claims.append(
                {
                    "claim_id": f"claim-{index + 1}",
                    "section": (
                        "facts"
                        if self.invalid_section
                        and item["section"] == "definition"
                        else answer_section[item["section"]]
                    ),
                    "text": item["snippet"],
                    "evidence_ids": [item["evidence_id"]],
                }
            )
        return create_llm_result(
            status=LLMStatus.OK,
            content=json.dumps({"claims": claims}, ensure_ascii=False),
            model="gemini/gemini-3.5-flash",
            provider="gemini",
            latency_ms=1,
        )


def test_approved_coverage_canonical_alias_and_security_free_evidence() -> None:
    coverage = evaluate_actual_glossary_coverage("data/glossary.json")
    service = GlossaryService()

    canonical = service.lookup("당기순이익이 뭐야?", fetched_at=BASIS_AT)
    alias = service.lookup("순이익이 뭐야?", fetched_at=BASIS_AT)

    assert coverage.actual_coverage_evaluated is True
    assert coverage.approved_actual_entries == 15
    assert coverage.meets_minimum is True
    assert canonical.lookup_state == alias.lookup_state == "found"
    assert canonical.provider_result.status == ProviderStatus.OK
    assert canonical.retrieval_status == RetrievalStatus.OK
    assert canonical.evidence == alias.evidence
    assert canonical.selected_count == 3
    assert all(item.source_type == "glossary" for item in canonical.evidence)
    assert all(item.scope == "industry_common" for item in canonical.evidence)
    assert all(not item.subject_security_ids for item in canonical.evidence)
    assert all(not item.mentioned_security_ids for item in canonical.evidence)
    assert "KRX:005930" not in repr(canonical)


def test_stable_ids_locator_and_formula_presence() -> None:
    service = GlossaryService()

    first = service.lookup("PER이 뭐야?", fetched_at=BASIS_AT)
    second = service.lookup("PER 뜻", fetched_at=BASIS_AT)
    without_formula = service.lookup("매출이 뭐야?", fetched_at=BASIS_AT)

    assert first.evidence == second.evidence
    assert [item.locator["section"] for item in first.evidence] == [
        "definition",
        "why_it_matters",
        "caution",
        "formula",
    ]
    assert [item.locator["section"] for item in without_formula.evidence] == [
        "definition",
        "why_it_matters",
        "caution",
    ]
    assert len({item.document_id for item in first.evidence}) == 4
    assert len({item.evidence_id for item in first.evidence}) == 4
    for item in first.evidence:
        assert item.source_url is None
        assert set(item.locator) == {
            "corpus_id",
            "entry_id",
            "version",
            "section",
            "source_type",
            "provider",
            "ingestion_version",
        }
        assert item.locator["provider"] == "manual_glossary"
        assert item.locator["ingestion_version"] == (
            "glossary-ingest-m1-07-v1"
        )
        assert "data/glossary.json" not in item.model_dump_json()


def test_unknown_term_and_corpus_failure_are_sanitized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unknown = GlossaryService().lookup(
        "알 수 없는 용어 설명",
        fetched_at=BASIS_AT,
    )
    assert unknown.lookup_state == "not_found"
    assert unknown.provider_result.status == ProviderStatus.NO_DATA
    assert unknown.evidence == ()

    def fail_load(path: object) -> object:
        raise GlossaryCorpusValidationError(
            "C:\\private\\credential-sentinel.json"
        )

    monkeypatch.setattr(
        glossary_module,
        "load_glossary_entries",
        fail_load,
    )
    unavailable = GlossaryService().lookup("PER", fetched_at=BASIS_AT)

    assert unavailable.lookup_state == "unavailable"
    assert unavailable.provider_result.status == ProviderStatus.PARSE_ERROR
    serialized = repr(unavailable)
    assert "credential-sentinel" not in serialized
    assert "private" not in serialized


def test_service_loads_validates_and_indexes_once_per_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"load": 0, "validate": 0, "index": 0}
    real_load = glossary_module.load_glossary_entries
    real_validate = glossary_module.validate_glossary_corpus
    real_index = glossary_module.build_glossary_index

    def load(path: object) -> object:
        calls["load"] += 1
        return real_load(path)  # type: ignore[arg-type]

    def validate(bundle: object, *, mode: str) -> object:
        calls["validate"] += 1
        return real_validate(bundle, mode=mode)  # type: ignore[arg-type]

    def index(bundle: object, *, mode: str) -> object:
        calls["index"] += 1
        return real_index(bundle, mode=mode)  # type: ignore[arg-type]

    monkeypatch.setattr(glossary_module, "load_glossary_entries", load)
    monkeypatch.setattr(
        glossary_module,
        "validate_glossary_corpus",
        validate,
    )
    monkeypatch.setattr(glossary_module, "build_glossary_index", index)

    service = GlossaryService()
    service.lookup("PER이 뭐야?", fetched_at=BASIS_AT)
    service.lookup("PBR이 뭐야?", fetched_at=BASIS_AT)

    assert calls == {"load": 1, "validate": 1, "index": 1}


def test_glossary_context_reuses_existing_per_source_cap() -> None:
    result = GlossaryService().lookup("PER이 뭐야?", fetched_at=BASIS_AT)

    selected = select_glossary_context(result.evidence)

    assert selected.evidence == result.evidence[:3]
    assert selected.diagnostics.input_count == 4
    assert selected.diagnostics.unique_count == 4
    assert selected.diagnostics.selected_count == 3
    assert selected.diagnostics.source_cap_drop_count == 1
    assert selected.diagnostics.context_drop_count == 0
    assert selected.diagnostics.max_evidence_per_source == 3


@pytest.mark.parametrize(
    ("query", "entry_id"),
    [
        ("PER이 뭐야?", "glossary:per"),
        ("PER 뜻", "glossary:per"),
        ("당기순이익이 뭐야?", "glossary:net_income"),
        ("영업이익률 설명", "glossary:operating_margin"),
        ("주가 이익 비율은 무엇인가?", "glossary:per"),
    ],
)
def test_glossary_lookup_accepts_complete_canonical_and_alias_terms(
    query: str,
    entry_id: str,
) -> None:
    first = GlossaryService().lookup(query, fetched_at=BASIS_AT)
    second = GlossaryService().lookup(query, fetched_at=BASIS_AT)

    assert first == second
    assert first.lookup_state == "found"
    assert first.provider_result.status == ProviderStatus.OK
    assert {
        item.locator["entry_id"] for item in first.evidence
    } == {entry_id}


@pytest.mark.parametrize(
    "query",
    [
        "super가 뭐야?",
        "hyper PERformance가 뭐야?",
        "매출원가가 뭐야?",
        "공시가격이 뭐야?",
        "PER과 PBR이 뭐야?",
        "영업이익과 당기순이익이 뭐야?",
    ],
)
def test_glossary_lookup_rejects_partial_or_multiple_distinct_terms(
    query: str,
) -> None:
    first = GlossaryService().lookup(query, fetched_at=BASIS_AT)
    second = GlossaryService().lookup(query, fetched_at=BASIS_AT)

    assert first == second
    assert first.lookup_state == "not_found"
    assert first.provider_result.status == ProviderStatus.NO_DATA
    assert first.evidence == ()


def test_ambiguous_glossary_lookup_has_no_fallback_security_or_llm_call() -> None:
    llm = GlossaryLLM()
    service = ChatService(
        glossary_service=GlossaryService(),
        composer=AnswerComposer(llm),
        utc_now=lambda: BASIS_AT,
    )

    first = asyncio.run(
        service.chat(
            ChatRequest(
                message="PER과 PBR이 뭐야?",
                session_id="ambiguous-first",
            )
        )
    )
    second = asyncio.run(
        service.chat(
            ChatRequest(
                message="PER과 PBR이 뭐야?",
                session_id="ambiguous-second",
            )
        )
    )

    assert first.model_dump_json() == second.model_dump_json()
    assert first.status == "no_evidence"
    assert first.security is None
    assert first.evidence == []
    assert llm.calls == 0
    assert first.answer_sections.summary == [
        "답변에 사용할 수 있는 근거를 확인하지 못했습니다."
    ]


def test_chat_service_glossary_path_has_actual_counts_and_citations() -> None:
    llm = GlossaryLLM()
    response = asyncio.run(
        ChatService(
            glossary_service=GlossaryService(),
            composer=AnswerComposer(llm),
            utc_now=lambda: BASIS_AT,
        ).chat(
            ChatRequest(
                message="PER이 뭐야?",
                session_id="glossary-unit",
            )
        )
    )

    assert response.status == "complete"
    assert response.security is None
    assert response.missing_sources == []
    assert len(response.evidence) == 3
    assert len(response.answer_sections.summary) == 1
    assert response.answer_sections.facts == []
    assert len(response.answer_sections.interpretation) == 1
    assert len(response.answer_sections.uncertainty) == 1
    assert llm.calls == 1
    assert "permission_note" not in llm.last_prompt
    assert response.diagnostics_public.data_mode == "recorded"
    assert response.diagnostics_public.live_connectivity_checked is False
    assert response.diagnostics_public.security.model_dump() == {
        "resolution_status": "not_found",
        "security_id": None,
    }
    assert response.diagnostics_public.sources[0].model_dump() == {
        "source_type": "glossary",
        "provider_status": "ok",
        "document_count": 4,
        "from_cache": False,
    }
    assert response.diagnostics_public.evidence_pipeline.model_dump() == {
        "normalized_count": 4,
        "hard_filtered_count": 4,
        "freshness_retained_count": 4,
        "freshness_warning_codes": [],
        "retrieval_status": "ok",
        "retrieval_selected_count": 4,
    }
    assert (
        response.diagnostics_public.decision.evidence_decision_status
        == "complete"
    )
    assert response.diagnostics_public.context_budget.selected_count == 3
    assert (
        response.diagnostics_public.context_budget.source_cap_drop_count
        == 1
    )
    assert response.diagnostics_public.citation.citation_count == 3
    assert all(
        item.locator["section"]
        in {"definition", "why_it_matters", "caution"}
        for item in response.evidence
    )
    assert "KRX:005930" not in response.model_dump_json()


def test_invalid_glossary_draft_fails_closed_to_one_fixed_answer() -> None:
    llm = GlossaryLLM(invalid_section=True)
    service = ChatService(
        glossary_service=GlossaryService(),
        composer=AnswerComposer(llm),
        utc_now=lambda: BASIS_AT,
    )

    first = asyncio.run(
        service.chat(
            ChatRequest(message="순이익이 뭐야?", session_id="first")
        )
    )
    second = asyncio.run(
        service.chat(
            ChatRequest(message="순이익이 뭐야?", session_id="second")
        )
    )

    assert first.model_dump_json() == second.model_dump_json()
    assert first.status == "complete"
    assert first.diagnostics_public.generation.mode == "fixed_template"
    assert first.diagnostics_public.generation.llm_status == "invalid_response"
    assert len(first.answer_sections.summary) == 1
    assert len(first.answer_sections.interpretation) == 1
    assert len(first.answer_sections.uncertainty) == 1
    assert llm.calls == 2


def _prompt_evidence(prompt: str) -> list[dict[str, str]]:
    blocks = prompt.split("\n\n")
    output = []
    for block in blocks:
        values = {}
        for line in block.splitlines():
            if ": " in line:
                key, value = line.split(": ", 1)
                values[key] = value
        if "Evidence ID" in values:
            output.append(
                {
                    "evidence_id": values["Evidence ID"],
                    "section": values["Glossary section"],
                    "snippet": values["Snippet"],
                }
            )
    return output
