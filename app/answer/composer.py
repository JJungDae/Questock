from __future__ import annotations

import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnableSequence

from app.answer.models import AnswerSections, DraftClaim, StructuredAnswerDraft
from app.core.models import Evidence, FinancialDocument, QueryPlan
from app.evidence.citations import (
    CitationClaim,
    CitationValidationResult,
    validate_citations,
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


class AnswerCompositionError(ValueError):
    """Raised for malformed composer inputs without exposing raw content."""


@dataclass(frozen=True)
class _BoundaryOutput:
    content: str
    result: LLMResult


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
                    "extract from every referenced evidence snippet.\n"
                    "{format_instructions}",
                ),
                (
                    "human",
                    "Question:\n{question}\n\nEligible evidence:\n{evidence}",
                ),
            ]
        ).partial(format_instructions=self._parser.get_format_instructions())
        self.chain: RunnableSequence = (
            self._prompt
            | RunnableLambda(self._audit_prompt)
            | RunnableLambda(self._call_client)
            | RunnableLambda(self._parse_output)
        )

    async def compose(
        self,
        *,
        question: str,
        plan: QueryPlan,
        selected_evidence: Sequence[Evidence],
        documents_by_id: Mapping[str, FinancialDocument],
        timeout_seconds: float,
    ) -> CompositionResult:
        canonical_question = _validate_question(question)
        canonical_plan = _copy_plan(plan)
        canonical_evidence = _copy_evidence(selected_evidence)
        canonical_documents = _copy_documents(documents_by_id)
        eligible = _external_processing_eligible(
            canonical_evidence,
            canonical_documents,
        )
        if not eligible:
            return _fixed_result(canonical_plan, canonical_evidence)

        payload = {
            "question": canonical_question,
            "evidence": _prompt_evidence(eligible),
            "timeout_seconds": timeout_seconds,
        }
        try:
            parsed = await self.chain.ainvoke(
                payload,
                config={
                    "callbacks": [],
                    "configurable": {"timeout_seconds": timeout_seconds},
                },
            )
            if not isinstance(parsed, _ParsedOutput):
                raise AnswerCompositionError("structured generation output is invalid")
            claims = _citation_claims(parsed.draft, eligible, parsed.result)
            citations = validate_citations(claims, canonical_plan, eligible)
            if citations.rejections:
                raise _GenerationFailure(
                    _invalid_response_from(parsed.result),
                    rejection_count=len(citations.rejections),
                )
            return CompositionResult(
                answer_sections=AnswerSections.from_claims(parsed.draft.claims),
                claims=claims,
                citations=citations,
                generation_mode="llm",
                llm_result=parsed.result.model_copy(deep=True),
                transmitted_evidence=tuple(
                    item.model_copy(deep=True) for item in eligible
                ),
                citation_rejection_count=0,
            )
        except _GenerationFailure as exc:
            return _fixed_result(
                canonical_plan,
                canonical_evidence,
                llm_result=exc.result,
                citation_rejection_count=exc.rejection_count,
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
    ) -> _BoundaryOutput:
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
        result = await self._client.complete(
            request,
            timeout_seconds=timeout_seconds,
        )
        if result.status != LLMStatus.OK or result.content is None:
            raise _GenerationFailure(result)
        return _BoundaryOutput(result.content, result)

    def _parse_output(self, output: _BoundaryOutput) -> _ParsedOutput:
        try:
            draft = self._parser.parse(output.content)
        except Exception:
            raise _GenerationFailure(_invalid_response_from(output.result)) from None
        return _ParsedOutput(draft=draft, result=output.result)


def _validate_question(value: object) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 2000:
        raise AnswerCompositionError("question is invalid")
    return value.strip()


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


def _prompt_evidence(evidence: tuple[Evidence, ...]) -> str:
    return "\n\n".join(
        f"Evidence ID: {item.evidence_id}\nSnippet: {item.snippet}"
        for item in evidence
    )


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
    if evidence:
        claims = tuple(
            CitationClaim(
                claim_id=f"fixed-{index + 1}",
                text=item.snippet,
                evidence_ids=(item.evidence_id,),
            )
            for index, item in enumerate(evidence[:3])
        )
        citations = validate_citations(claims, plan, evidence)
        draft_claims = tuple(
            DraftClaim(
                claim_id=claim.claim_id,
                section="summary" if index == 0 else "facts",
                text=claim.text,
                evidence_ids=claim.evidence_ids,
            )
            for index, claim in enumerate(claims)
        )
        sections = AnswerSections.from_claims(draft_claims)
    else:
        claims = ()
        citations = CitationValidationResult((), ())
        key = (
            "blocked"
            if plan.intent == "prohibited_advice"
            else fallback_reason or "no_evidence"
        )
        sections = AnswerSections(summary=[_SAFE_FALLBACKS[key]])
    return CompositionResult(
        answer_sections=sections,
        claims=claims,
        citations=citations,
        generation_mode="blocked" if plan.intent == "prohibited_advice" else "fixed_template",
        llm_result=llm_result.model_copy(deep=True) if llm_result else None,
        transmitted_evidence=(),
        citation_rejection_count=citation_rejection_count,
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
