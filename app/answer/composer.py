from __future__ import annotations

import os
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import (
    RunnableLambda,
    RunnablePassthrough,
    RunnableSequence,
)

from app.answer.models import (
    AnswerSectionName,
    AnswerSections,
    DraftClaim,
    StructuredAnswerDraft,
)
from app.answer.validators import (
    is_unsafe_answer_text,
    validate_answer_draft,
)
from app.core.models import Evidence, FinancialDocument, QueryPlan
from app.evidence.citations import (
    Citation,
    CitationClaim,
    CitationValidationError,
    CitationValidationResult,
    validate_citations,
)
from app.evidence.budget import (
    LLMCallBudget,
    LLMCallBudgetExceededError,
)
from app.llm.base import (
    LLMClient,
    LLMMessage,
    LLMRequest,
    LLMResult,
    LLMStatus,
    create_llm_result,
)

os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"

GenerationMode = Literal["llm", "fixed_template", "blocked", "not_called"]

_WINDOWS_PATH = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z]:[\\/]")
_UNC_PATH = re.compile(r"(?:\\\\|//)[^\\/\s]+[\\/][^\\/\s]+")
_POSIX_PATH = re.compile(r"(?:^|[\s\"'()=\[\]{},;])/(?![/\s])")
_CREDENTIAL_VALUE = re.compile(
    r"(?i)(?:api[-_]?key|client[-_]?secret|access[-_]?token|authorization|credential)"
    r"\s*[:=]\s*\S+"
)
_URL = re.compile(r"(?i)\b(?:https?|file)://")
_SAFE_FALLBACKS = {
    "blocked": "요청 범위상 제공할 수 없는 답변입니다.",
    "provider_failed": "자료 제공 상태를 확인하지 못해 답변을 보류합니다.",
    "no_evidence": "답변에 사용할 수 있는 근거를 확인하지 못했습니다.",
}
_SECTION_ORDER = {
    "summary": 0,
    "facts": 1,
    "interpretation": 2,
    "inference": 3,
    "positive_factors": 4,
    "risk_factors": 5,
    "uncertainty": 6,
}
_GLOSSARY_SECTION_MAP: dict[str, AnswerSectionName] = {
    "definition": "summary",
    "why_it_matters": "interpretation",
    "caution": "uncertainty",
    "formula": "facts",
    "example": "facts",
}


class AnswerCompositionError(ValueError):
    """Raised for malformed composer inputs without exposing raw content."""


@dataclass(frozen=True)
class _ParsedOutput:
    draft: StructuredAnswerDraft
    result: LLMResult


@dataclass(frozen=True)
class CompositionResult:
    answer_sections: AnswerSections
    claims: tuple[CitationClaim, ...]
    citations: CitationValidationResult
    generation_mode: GenerationMode
    llm_result: LLMResult | None
    transmitted_evidence: tuple[Evidence, ...]
    public_evidence: tuple[Evidence, ...]
    citation_rejection_count: int = 0


class _GenerationFailure(Exception):
    def __init__(self, result: LLMResult, *, rejection_count: int = 0) -> None:
        super().__init__("structured generation failed")
        self.result = result
        self.rejection_count = rejection_count


class AnswerComposer:
    def __init__(self, client: LLMClient) -> None:
        if not isinstance(client, LLMClient):
            raise TypeError("client must implement LLMClient")
        self._client = client
        self._parser = PydanticOutputParser(pydantic_object=StructuredAnswerDraft)
        self._prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Return only the requested JSON. Every claim must be an exact "
                    "extract from every referenced evidence snippet. The first "
                    "claim must be the only summary claim. Keep claims in this "
                    "section order: summary, facts, interpretation, inference, "
                    "positive_factors, risk_factors, uncertainty. Omit unsupported "
                    "sections. Never provide direct investment action or guaranteed "
                    "future performance. For research_report_summary, place stated "
                    "plans and scheduled events in facts, growth conditions in "
                    "positive_factors or interpretation, risk conditions in "
                    "risk_factors, and missing confirmation in uncertainty. For "
                    "financial_term, map definition to summary, formula and "
                    "example to facts, why_it_matters to interpretation, and "
                    "caution to uncertainty.\n"
                    "{format_instructions}",
                ),
                (
                    "human",
                    "Intent:\n{intent}\n\nQuestion:\n{question}\n\n"
                    "Eligible evidence:\n{evidence}",
                ),
            ]
        ).partial(format_instructions=self._parser.get_format_instructions())
        parse_stage = RunnablePassthrough.assign(
            draft=RunnableLambda(_boundary_content) | self._parser
        ).with_fallbacks(
            [RunnableLambda(self._raise_parse_failure)],
            exception_key="parser_exception",
        )
        self.chain: RunnableSequence = (
            self._prompt
            | RunnableLambda(self._audit_prompt)
            | RunnableLambda(self._call_client)
            | parse_stage
            | RunnableLambda(self._combine_output)
        )

    async def compose(
        self,
        *,
        question: str,
        plan: QueryPlan,
        selected_evidence: Sequence[Evidence],
        documents_by_id: Mapping[str, FinancialDocument],
        timeout_seconds: float,
        call_budget: LLMCallBudget | None = None,
    ) -> CompositionResult:
        canonical_question = _validate_question(question)
        canonical_plan = _copy_plan(plan)
        canonical_evidence = _copy_evidence(selected_evidence)
        canonical_documents = _copy_documents(documents_by_id)
        eligible = _external_processing_eligible(
            canonical_evidence,
            canonical_documents,
        )
        projected = _project_m3_evidence(canonical_plan, eligible)
        canonical_budget = _call_budget(call_budget)
        if not projected:
            return _fixed_result(canonical_plan, canonical_evidence)

        payload = {
            "intent": canonical_plan.intent,
            "question": canonical_question,
            "evidence": _prompt_evidence(projected),
            "timeout_seconds": timeout_seconds,
        }
        try:
            parsed = await self.chain.ainvoke(
                payload,
                config={
                    "callbacks": [],
                    "configurable": {
                        "timeout_seconds": timeout_seconds,
                        "call_budget": canonical_budget,
                    },
                },
            )
            if not isinstance(parsed, _ParsedOutput):
                raise AnswerCompositionError("structured generation output is invalid")
            validation = validate_answer_draft(
                parsed.draft,
                canonical_plan,
                projected,
            )
            if validation.draft is None:
                raise _GenerationFailure(
                    _invalid_response_from(parsed.result),
                    rejection_count=max(1, validation.rejection_count),
                )
            try:
                _validate_draft_structure(
                    validation.draft,
                    canonical_plan,
                    projected,
                    parsed.result,
                )
                claims = _citation_claims(
                    validation.draft,
                    projected,
                    parsed.result,
                )
                citations = validate_citations(claims, canonical_plan, projected)
                if citations.rejections:
                    raise _GenerationFailure(
                        _invalid_response_from(parsed.result),
                        rejection_count=len(citations.rejections),
                    )
            except _GenerationFailure as exc:
                raise _GenerationFailure(
                    exc.result,
                    rejection_count=(
                        validation.rejection_count + exc.rejection_count
                    ),
                ) from None
            return CompositionResult(
                answer_sections=AnswerSections.from_claims(
                    validation.draft.claims
                ),
                claims=claims,
                citations=citations,
                generation_mode="llm",
                llm_result=parsed.result.model_copy(deep=True),
                transmitted_evidence=tuple(
                    item.model_copy(deep=True) for item in projected
                ),
                public_evidence=_citation_bound_evidence(
                    projected,
                    citations,
                ),
                citation_rejection_count=validation.rejection_count,
            )
        except _GenerationFailure as exc:
            return _fixed_result(
                canonical_plan,
                canonical_evidence,
                llm_result=exc.result,
                citation_rejection_count=exc.rejection_count,
            )
        except LLMCallBudgetExceededError:
            return _fixed_result(
                canonical_plan,
                canonical_evidence,
            )
        except Exception:
            return _fixed_result(
                canonical_plan,
                canonical_evidence,
                llm_result=create_llm_result(
                    status=LLMStatus.INVALID_RESPONSE,
                    model="gemini/gemini-2.5-flash",
                    provider="gemini",
                    latency_ms=0.0,
                ),
            )

    def compose_fixed(
        self,
        *,
        plan: QueryPlan,
        selected_evidence: Sequence[Evidence],
        llm_result: LLMResult | None = None,
        fallback_reason: Literal[
            "blocked",
            "provider_failed",
            "no_evidence",
        ] | None = None,
    ) -> CompositionResult:
        return _fixed_result(
            _copy_plan(plan),
            _copy_evidence(selected_evidence),
            llm_result=llm_result,
            fallback_reason=fallback_reason,
        )

    def _audit_prompt(self, prompt_value: Any) -> Any:
        try:
            messages = prompt_value.to_messages()
        except (AttributeError, TypeError):
            raise AnswerCompositionError("rendered prompt is invalid") from None
        for message in messages:
            content = getattr(message, "content", None)
            if not isinstance(content, str) or _unsafe_prompt_string(content):
                raise AnswerCompositionError("rendered prompt failed safety validation")
        return prompt_value

    async def _call_client(
        self,
        prompt_value: Any,
        config: Mapping[str, Any],
    ) -> dict[str, Any]:
        messages = tuple(
            LLMMessage(
                role="user" if getattr(item, "type", "") == "human" else "system",
                content=item.content,
            )
            for item in prompt_value.to_messages()
        )
        request = LLMRequest(
            messages=messages,
            response_schema=StructuredAnswerDraft.model_json_schema(),
        )
        configurable = config.get("configurable", {})
        timeout_seconds = (
            configurable.get("timeout_seconds", 8.0)
            if isinstance(configurable, Mapping)
            else 8.0
        )
        call_budget = (
            configurable.get("call_budget")
            if isinstance(configurable, Mapping)
            else None
        )
        if not isinstance(call_budget, LLMCallBudget):
            raise AnswerCompositionError("LLM call budget is invalid")
        call_budget.reserve_call()
        result = await self._client.complete(
            request,
            timeout_seconds=timeout_seconds,
        )
        if result.status != LLMStatus.OK or result.content is None:
            raise _GenerationFailure(result)
        return {
            "content": result.content,
            "result": result,
        }

    def _raise_parse_failure(self, output: Mapping[str, Any]) -> None:
        result = output.get("result")
        if not isinstance(result, LLMResult):
            raise AnswerCompositionError("structured generation output is invalid")
        raise _GenerationFailure(_invalid_response_from(result))

    def _combine_output(self, output: Mapping[str, Any]) -> _ParsedOutput:
        draft = output.get("draft")
        result = output.get("result")
        if not isinstance(draft, StructuredAnswerDraft) or not isinstance(
            result,
            LLMResult,
        ):
            raise AnswerCompositionError("structured generation output is invalid")
        return _ParsedOutput(draft=draft, result=result)


def _validate_question(value: object) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 2000:
        raise AnswerCompositionError("question is invalid")
    return value.strip()


def _call_budget(value: LLMCallBudget | None) -> LLMCallBudget:
    if value is None:
        return LLMCallBudget(max_calls=1)
    if not isinstance(value, LLMCallBudget):
        raise AnswerCompositionError("LLM call budget is invalid")
    return value


def _boundary_content(value: object) -> str:
    if not isinstance(value, Mapping):
        raise AnswerCompositionError("structured generation output is invalid")
    content = value.get("content")
    if not isinstance(content, str) or not content.strip():
        raise AnswerCompositionError("structured generation output is invalid")
    return content


def _copy_plan(value: object) -> QueryPlan:
    if not isinstance(value, QueryPlan):
        raise AnswerCompositionError("plan is invalid")
    try:
        return QueryPlan.model_validate(value.model_dump(mode="python"), strict=True)
    except Exception:
        raise AnswerCompositionError("plan is invalid") from None


def _copy_evidence(value: object) -> tuple[Evidence, ...]:
    if isinstance(value, (str, bytes, bytearray, Mapping)) or not isinstance(value, Sequence):
        raise AnswerCompositionError("selected evidence is invalid")
    output: list[Evidence] = []
    for item in value:
        if not isinstance(item, Evidence):
            raise AnswerCompositionError("selected evidence is invalid")
        output.append(item.model_copy(deep=True))
    return tuple(output)


def _copy_documents(value: object) -> dict[str, FinancialDocument]:
    if not isinstance(value, Mapping):
        raise AnswerCompositionError("documents_by_id is invalid")
    output: dict[str, FinancialDocument] = {}
    for key, document in value.items():
        if (
            not isinstance(key, str)
            or not isinstance(document, FinancialDocument)
            or key != document.document_id
        ):
            raise AnswerCompositionError("documents_by_id is invalid")
        output[key] = document.model_copy(deep=True)
    return output


def _external_processing_eligible(
    evidence: tuple[Evidence, ...],
    documents_by_id: Mapping[str, FinancialDocument],
) -> tuple[Evidence, ...]:
    output: list[Evidence] = []
    for item in evidence:
        if item.source_type == "research_report":
            document = documents_by_id.get(item.document_id)
            if (
                document is None
                or document.metadata.get("external_llm_processing_allowed") is not True
            ):
                continue
        output.append(item.model_copy(deep=True))
    return tuple(output)


def _project_m3_evidence(
    plan: QueryPlan,
    evidence: tuple[Evidence, ...],
) -> tuple[Evidence, ...]:
    if plan.intent not in {"risk_factors", "multi_source_summary"}:
        return tuple(item.model_copy(deep=True) for item in evidence)

    selected_indexes: list[int] = []
    for source_type in plan.required_sources:
        index = next(
            (
                position
                for position, item in enumerate(evidence)
                if (
                    position not in selected_indexes
                    and item.source_type == source_type
                )
            ),
            None,
        )
        if index is not None:
            selected_indexes.append(index)
        if len(selected_indexes) == 3:
            break

    if len(selected_indexes) < 3:
        for index in range(len(evidence)):
            if index not in selected_indexes:
                selected_indexes.append(index)
            if len(selected_indexes) == 3:
                break

    return tuple(
        evidence[index].model_copy(deep=True)
        for index in selected_indexes
    )


def _prompt_evidence(evidence: tuple[Evidence, ...]) -> str:
    rendered = []
    for item in evidence:
        lines = [
            f"Evidence ID: {item.evidence_id}",
            f"Source type: {item.source_type}",
        ]
        if item.source_type == "glossary":
            lines.append(f"Glossary section: {item.locator.get('section')}")
        lines.append(f"Snippet: {item.snippet}")
        rendered.append("\n".join(lines))
    return "\n\n".join(rendered)


def _citation_claims(
    draft: StructuredAnswerDraft,
    evidence: tuple[Evidence, ...],
    result: LLMResult,
) -> tuple[CitationClaim, ...]:
    allowed_ids = {item.evidence_id for item in evidence}
    claims: list[CitationClaim] = []
    for item in draft.claims:
        if any(evidence_id not in allowed_ids for evidence_id in item.evidence_ids):
            raise _GenerationFailure(
                _invalid_response_from(result),
                rejection_count=1,
            )
        claims.append(
            CitationClaim(
                claim_id=item.claim_id,
                text=item.text,
                evidence_ids=tuple(item.evidence_ids),
            )
        )
    return tuple(claims)


def _validate_draft_structure(
    draft: StructuredAnswerDraft,
    plan: QueryPlan,
    evidence: tuple[Evidence, ...],
    result: LLMResult,
) -> None:
    sections = [item.section for item in draft.claims]
    summary_count = sections.count("summary")
    ordered = [_SECTION_ORDER[item] for item in sections]
    glossary_sections_valid = (
        plan.intent != "financial_term"
        or _glossary_claim_sections_valid(draft, evidence)
    )
    claims_are_unique = _claims_are_unique(draft)
    if (
        not sections
        or sections[0] != "summary"
        or summary_count != 1
        or ordered != sorted(ordered)
        or not glossary_sections_valid
        or not claims_are_unique
    ):
        raise _GenerationFailure(
            _invalid_response_from(result),
            rejection_count=1,
        )


def _claims_are_unique(draft: StructuredAnswerDraft) -> bool:
    section_by_text: dict[str, AnswerSectionName] = {}
    occurrences: set[tuple[str, tuple[str, ...]]] = set()
    for claim in draft.claims:
        normalized_text = " ".join(
            unicodedata.normalize("NFKC", claim.text).split()
        ).casefold()
        occurrence = (normalized_text, tuple(claim.evidence_ids))
        if occurrence in occurrences:
            return False
        occurrences.add(occurrence)
        prior_section = section_by_text.get(normalized_text)
        if prior_section is not None and prior_section != claim.section:
            return False
        section_by_text.setdefault(normalized_text, claim.section)
    return True


def _fixed_result(
    plan: QueryPlan,
    evidence: tuple[Evidence, ...],
    *,
    llm_result: LLMResult | None = None,
    citation_rejection_count: int = 0,
    fallback_reason: Literal[
        "blocked",
        "provider_failed",
        "no_evidence",
    ] | None = None,
) -> CompositionResult:
    if plan.intent == "prohibited_advice" or fallback_reason == "blocked":
        return _empty_fixed_result(
            plan,
            fallback_reason="blocked",
            llm_result=llm_result,
            citation_rejection_count=citation_rejection_count,
        )
    if not evidence:
        return _empty_fixed_result(
            plan,
            fallback_reason=fallback_reason or "no_evidence",
            llm_result=llm_result,
            citation_rejection_count=citation_rejection_count,
        )
    if plan.intent == "financial_term":
        return _fixed_glossary_result(
            plan,
            evidence,
            llm_result=llm_result,
            citation_rejection_count=citation_rejection_count,
        )

    accepted_claims: list[CitationClaim] = []
    accepted_citations: list[Citation] = []
    accepted_evidence: list[Evidence] = []
    fixed_rejection_count = 0
    for index, item in enumerate(evidence[:3]):
        if is_unsafe_answer_text(item.snippet, intent=plan.intent):
            fixed_rejection_count += 1
            continue
        claim = CitationClaim(
            claim_id=f"fixed-{index + 1}",
            text=item.snippet,
            evidence_ids=(item.evidence_id,),
        )
        try:
            validation = validate_citations((claim,), plan, (item,))
        except CitationValidationError:
            fixed_rejection_count += 1
            continue
        if validation.rejections or not validation.citations:
            fixed_rejection_count += max(1, len(validation.rejections))
            continue
        accepted_claims.append(claim)
        accepted_citations.extend(validation.citations)
        accepted_evidence.append(item.model_copy(deep=True))

    if not accepted_claims:
        return _empty_fixed_result(
            plan,
            fallback_reason="no_evidence",
            llm_result=llm_result,
            citation_rejection_count=(
                citation_rejection_count + fixed_rejection_count
            ),
        )

    draft_claims = tuple(
        DraftClaim(
            claim_id=claim.claim_id,
            section="summary" if index == 0 else "facts",
            text=claim.text,
            evidence_ids=claim.evidence_ids,
        )
        for index, claim in enumerate(accepted_claims)
    )
    return CompositionResult(
        answer_sections=AnswerSections.from_claims(draft_claims),
        claims=tuple(accepted_claims),
        citations=CitationValidationResult(
            tuple(accepted_citations),
            (),
        ),
        generation_mode="fixed_template",
        llm_result=llm_result.model_copy(deep=True) if llm_result else None,
        transmitted_evidence=(),
        public_evidence=tuple(accepted_evidence),
        citation_rejection_count=(
            citation_rejection_count + fixed_rejection_count
        ),
    )


def _fixed_glossary_result(
    plan: QueryPlan,
    evidence: tuple[Evidence, ...],
    *,
    llm_result: LLMResult | None,
    citation_rejection_count: int,
) -> CompositionResult:
    draft_claims: list[DraftClaim] = []
    claims: list[CitationClaim] = []
    citations: list[Citation] = []
    public_evidence: list[Evidence] = []
    for index, item in enumerate(evidence):
        section = _GLOSSARY_SECTION_MAP.get(
            item.locator.get("section")  # type: ignore[arg-type]
        )
        if (
            section is None
            or is_unsafe_answer_text(item.snippet, intent=plan.intent)
        ):
            return _empty_fixed_result(
                plan,
                fallback_reason="no_evidence",
                llm_result=llm_result,
                citation_rejection_count=citation_rejection_count + 1,
            )
        claim = CitationClaim(
            claim_id=f"fixed-{index + 1}",
            text=item.snippet,
            evidence_ids=(item.evidence_id,),
        )
        try:
            validation = validate_citations((claim,), plan, (item,))
        except CitationValidationError:
            validation = CitationValidationResult((), ())
        if validation.rejections or len(validation.citations) != 1:
            return _empty_fixed_result(
                plan,
                fallback_reason="no_evidence",
                llm_result=llm_result,
                citation_rejection_count=citation_rejection_count + 1,
            )
        draft_claims.append(
            DraftClaim(
                claim_id=claim.claim_id,
                section=section,
                text=claim.text,
                evidence_ids=claim.evidence_ids,
            )
        )
        claims.append(claim)
        citations.extend(validation.citations)
        public_evidence.append(item.model_copy(deep=True))

    if (
        not draft_claims
        or draft_claims[0].section != "summary"
        or sum(item.section == "summary" for item in draft_claims) != 1
    ):
        return _empty_fixed_result(
            plan,
            fallback_reason="no_evidence",
            llm_result=llm_result,
            citation_rejection_count=citation_rejection_count + 1,
        )
    return CompositionResult(
        answer_sections=AnswerSections.from_claims(tuple(draft_claims)),
        claims=tuple(claims),
        citations=CitationValidationResult(tuple(citations), ()),
        generation_mode="fixed_template",
        llm_result=llm_result.model_copy(deep=True) if llm_result else None,
        transmitted_evidence=(),
        public_evidence=tuple(public_evidence),
        citation_rejection_count=citation_rejection_count,
    )


def _empty_fixed_result(
    plan: QueryPlan,
    *,
    fallback_reason: Literal[
        "blocked",
        "provider_failed",
        "no_evidence",
    ],
    llm_result: LLMResult | None,
    citation_rejection_count: int,
) -> CompositionResult:
    return CompositionResult(
        answer_sections=AnswerSections(
            summary=[_SAFE_FALLBACKS[fallback_reason]]
        ),
        claims=(),
        citations=CitationValidationResult((), ()),
        generation_mode=(
            "blocked" if fallback_reason == "blocked" else "fixed_template"
        ),
        llm_result=llm_result.model_copy(deep=True) if llm_result else None,
        transmitted_evidence=(),
        public_evidence=(),
        citation_rejection_count=citation_rejection_count,
    )


def _glossary_claim_sections_valid(
    draft: StructuredAnswerDraft,
    evidence: tuple[Evidence, ...],
) -> bool:
    evidence_by_id = {item.evidence_id: item for item in evidence}
    for claim in draft.claims:
        expected_sections = {
            _GLOSSARY_SECTION_MAP.get(
                evidence_by_id[evidence_id].locator.get("section")  # type: ignore[arg-type]
            )
            for evidence_id in claim.evidence_ids
            if evidence_id in evidence_by_id
        }
        if expected_sections != {claim.section}:
            return False
    return True


def _citation_bound_evidence(
    evidence: tuple[Evidence, ...],
    citations: CitationValidationResult,
) -> tuple[Evidence, ...]:
    accepted_ids = {item.evidence_id for item in citations.citations}
    return tuple(
        item.model_copy(deep=True)
        for item in evidence
        if item.evidence_id in accepted_ids
    )


def _invalid_response_from(result: LLMResult) -> LLMResult:
    return create_llm_result(
        status=LLMStatus.INVALID_RESPONSE,
        model=result.model,
        provider=result.provider,
        latency_ms=result.latency_ms,
    )


def _unsafe_prompt_string(value: str) -> bool:
    return bool(
        _WINDOWS_PATH.search(value)
        or _UNC_PATH.search(value)
        or _POSIX_PATH.search(value)
        or _CREDENTIAL_VALUE.search(value)
        or _URL.search(value)
    )


__all__ = [
    "AnswerComposer",
    "AnswerCompositionError",
    "CompositionResult",
    "GenerationMode",
]
