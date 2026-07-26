from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import parse_qsl, unquote_plus, urlsplit

from app.api.schemas import ChatResponse, PublicProcessSummary
from app.core.models import Evidence

_HIDDEN_TEXT = "안전하게 표시할 수 없는 내용입니다."
_CONTROL_CHARACTER = re.compile(r"[\x00-\x1f\x7f]")
_WINDOWS_PATH = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z]:[\\/]")
_BACKSLASH_UNC_PATH = re.compile(r"\\\\[^\\/\s]+[\\/][^\\/\s]+")
_FORWARD_UNC_PATH = re.compile(
    r"(?<![A-Za-z0-9_:])//[^/\s]+/[^/\s]+"
)
_FILE_URL = re.compile(r"file://", re.IGNORECASE)
_POSIX_PATH = re.compile(r"(?:^|[\s\"'()=\[\]{},;])/(?![/\s])")
_CREDENTIAL_VALUE = re.compile(
    r"(?i)(?:api[-_]?key|client[-_]?secret|access[-_]?token|"
    r"auth[-_]?token|bearer[-_]?token|authorization|credential|signature)"
    r"\s*[:=]\s*\S+"
)
_QUERY_KEY_NORMALIZER = re.compile(r"[^a-z0-9]")
_CREDENTIAL_QUERY_KEYS = frozenset(
    {
        "accesstoken",
        "apikey",
        "authorization",
        "authtoken",
        "bearertoken",
        "clientsecret",
        "credential",
        "secret",
        "signature",
        "token",
        "xamzsignature",
        "xapikey",
    }
)
_SOURCE_LABELS = {
    "news": "뉴스",
    "disclosure": "공시",
    "research_report": "리서치 리포트",
    "glossary": "금융 용어",
}
_INTENT_LABELS = {
    "recent_issue": "최근 이슈",
    "disclosure_summary": "공시 요약",
    "research_report_summary": "리포트 요약",
    "risk_factors": "위험 요인",
    "financial_term": "금융 용어",
    "multi_source_summary": "통합 요약",
    "prohibited_advice": "제공 제한 질문",
    "out_of_scope": "지원 범위 밖 질문",
}
_RESOLUTION_LABELS = {
    "resolved": "종목 확인 완료",
    "ambiguous": "종목 추가 확인 필요",
    "not_found": "종목 지정 없음",
    "unsupported": "지원 종목 아님",
}
_PROVIDER_LABELS = {
    "ok": "자료 확인 완료",
    "no_data": "자료가 확인되지 않음",
    "invalid_query": "자료 요청 형식 확인 필요",
    "unauthorized": "자료 접근 권한 확인 필요",
    "rate_limited": "자료 제공 한도에 도달함",
    "timeout": "자료 확인 시간이 초과됨",
    "provider_unavailable": "자료 제공 경로가 구성되지 않았거나 이용 불가",
    "parse_error": "자료 형식을 확인하지 못함",
}
_RETRIEVAL_LABELS = {
    "ok": "관련 근거 선택됨",
    "empty": "관련 근거 없음",
    "low_relevance": "관련성 기준 미달",
}
_DECISION_LABELS = {
    "complete": "근거 충족",
    "partial": "일부 근거 충족",
    "provider_failed": "자료 제공 실패",
    "no_evidence": "사용할 근거 없음",
    "blocked": "답변 제공 제한",
}
_GENERATION_LABELS = {
    "llm": "AI 구조화 응답",
    "fixed_template": "근거 기반 고정 응답",
    "blocked": "제공 제한 응답",
    "not_called": "생성 호출 없음",
}
_CONTENT_ORIGIN_LABELS = {
    "synthetic_project_owned": "Questock 작성 요약",
    "verified_public_recorded": "검증된 공개 기록",
}
_LLM_LABELS = {
    "ok": "AI 정리 완료",
    "timeout": "AI 정리 시간 초과",
    "rate_limited": "AI 제공 한도 도달",
    "authentication_error": "AI 연결 권한 확인 필요",
    "provider_unavailable": "AI 연결 이용 불가",
    "invalid_response": "AI 응답 형식 오류",
    "content_blocked": "AI 응답 제공 제한",
}
_WARNING_LABELS = {
    "missing_published_at": "게시일을 확인하지 못함",
    "future_published_at": "기준일 이후 자료가 제외됨",
    "stale_news": "뉴스 기준 기간이 오래됨",
    "stale_research_report": "리포트 기준 기간이 오래됨",
    "disclosure_window_extended": "공시 확인 기간을 확장함",
    "insufficient_disclosure_coverage": "공시 자료 범위가 충분하지 않음",
    "unresolved_disclosure_correction": "공시 정정 이력을 추가 확인해야 함",
    "llm_generation_degraded": "AI 정리 대신 근거 기반 고정 응답 사용",
    "request_deadline_exceeded": "전체 요청 시간 제한에 도달함",
}
_ANSWER_CARDS = (
    ("summary", "한 줄 결론"),
    ("facts", "확인된 사실"),
    ("interpretation", "왜 중요한가"),
    ("positive_factors", "긍정 요인"),
    ("risk_factors", "확인된 위험"),
    ("inference", "AI 정리·추론"),
    ("uncertainty", "더 확인할 것"),
)


class ProjectionError(RuntimeError):
    """Sanitized public-projection failure."""


@dataclass(frozen=True)
class AnswerCardView:
    key: str
    title: str
    items: tuple[str, ...]
    emphasis: str


@dataclass(frozen=True)
class BaselineAnswerView:
    status: str
    status_label: str
    security_name: str | None
    basis_date: str
    summary: tuple[str, ...]
    cards: tuple[AnswerCardView, ...]
    warnings: tuple[str, ...]
    missing_sources: tuple[str, ...]


@dataclass(frozen=True)
class ProcessField:
    label: str
    value: str


@dataclass(frozen=True)
class BaselineSourceView:
    title: str
    source_type: str
    source_label: str
    published_date: str | None
    snippet: str
    details: tuple[ProcessField, ...]
    link_url: str | None


@dataclass(frozen=True)
class ProcessStageView:
    key: str
    title: str
    fields: tuple[ProcessField, ...]


def project_baseline_answer(response: ChatResponse) -> BaselineAnswerView:
    if not isinstance(response, ChatResponse):
        raise ProjectionError("응답을 화면에 표시할 수 없습니다.")
    red_fallback = response.status in {
        "provider_failed",
        "no_evidence",
        "blocked",
    }
    cards = []
    for key, title in _ANSWER_CARDS:
        values = tuple(
            _safe_text(item)
            for item in getattr(response.answer_sections, key)
        )
        if not values:
            continue
        cards.append(
            AnswerCardView(
                key=key,
                title=title,
                items=values,
                emphasis=(
                    "error"
                    if red_fallback
                    and key in {"summary", "risk_factors"}
                    else "normal"
                ),
            )
        )
    return BaselineAnswerView(
        status=response.status,
        status_label=_DECISION_LABELS[response.status],
        security_name=(
            _safe_text(response.security.security_name)
            if response.security is not None
            else None
        ),
        basis_date=response.basis_date.isoformat(),
        summary=tuple(
            _safe_text(item) for item in response.answer_sections.summary
        ),
        cards=tuple(cards),
        warnings=tuple(_warning_label(item) for item in response.warnings),
        missing_sources=tuple(
            _SOURCE_LABELS.get(item, "기타 자료")
            for item in response.missing_sources
        ),
    )


def project_baseline_sources(
    response: ChatResponse,
) -> tuple[BaselineSourceView, ...]:
    if not isinstance(response, ChatResponse):
        raise ProjectionError("응답을 화면에 표시할 수 없습니다.")
    return tuple(_project_source(item) for item in response.evidence)


def project_process_stages(
    summary: PublicProcessSummary,
) -> tuple[ProcessStageView, ...]:
    if (
        not isinstance(summary, PublicProcessSummary)
        or summary.trace_version != "m3-01-v1"
    ):
        raise ProjectionError("지원하지 않는 분석 정보 형식입니다.")

    source_fields = tuple(
        ProcessField(
            label=_SOURCE_LABELS[item.source_type],
            value=(
                f"{_PROVIDER_LABELS[item.provider_status]} · "
                f"문서 {item.document_count} · "
                f"캐시 {'사용' if item.from_cache else '미사용'}"
            ),
        )
        for item in summary.sources
    )
    if not source_fields:
        source_fields = (ProcessField("자료", "요청 자료 없음"),)

    pipeline = summary.evidence_pipeline
    decision = summary.decision
    budget = summary.context_budget
    citation = summary.citation
    generation = summary.generation
    plan = summary.query_plan

    return (
        ProcessStageView(
            key="security",
            title="1. 종목 식별",
            fields=(
                ProcessField(
                    "상태",
                    _RESOLUTION_LABELS[summary.security.resolution_status],
                ),
                ProcessField(
                    "종목 ID",
                    summary.security.security_id or "지정 없음",
                ),
            ),
        ),
        ProcessStageView(
            key="query_plan",
            title="2. 질문 계획",
            fields=(
                ProcessField("의도", _INTENT_LABELS[plan.intent]),
                ProcessField(
                    "자료",
                    ", ".join(
                        _SOURCE_LABELS[item]
                        for item in plan.required_sources
                    )
                    or "요청 자료 없음",
                ),
                ProcessField(
                    "기간",
                    _date_range(plan.date_start, plan.date_end),
                ),
            ),
        ),
        ProcessStageView(
            key="sources",
            title="3. 자료 상태",
            fields=source_fields,
        ),
        ProcessStageView(
            key="filtering",
            title="4. 필터·최신성",
            fields=(
                ProcessField("정규화", str(pipeline.normalized_count)),
                ProcessField(
                    "종목·기간 필터",
                    str(pipeline.hard_filtered_count),
                ),
                ProcessField(
                    "최신성",
                    str(pipeline.freshness_retained_count),
                ),
                ProcessField(
                    "경고",
                    ", ".join(
                        _warning_label(item)
                        for item in pipeline.freshness_warning_codes
                    )
                    or "경고 없음",
                ),
            ),
        ),
        ProcessStageView(
            key="retrieval",
            title="5. 검색",
            fields=(
                ProcessField(
                    "상태",
                    _RETRIEVAL_LABELS[pipeline.retrieval_status],
                ),
                ProcessField(
                    "선택 근거",
                    str(pipeline.retrieval_selected_count),
                ),
            ),
        ),
        ProcessStageView(
            key="decision",
            title="6. 근거 충분성",
            fields=(
                ProcessField(
                    "상태",
                    _DECISION_LABELS[decision.evidence_decision_status],
                ),
                ProcessField(
                    "충족 자료",
                    _source_list(decision.satisfied_sources),
                ),
                ProcessField(
                    "누락 자료",
                    _source_list(decision.missing_sources),
                ),
                ProcessField(
                    "자료 없음",
                    _source_list(decision.no_data_sources),
                ),
                ProcessField(
                    "실패 자료",
                    _source_list(decision.failed_sources),
                ),
            ),
        ),
        ProcessStageView(
            key="context_budget",
            title="7. 문맥 예산",
            fields=(
                ProcessField("입력", str(budget.input_count)),
                ProcessField("고유", str(budget.unique_count)),
                ProcessField("선택", str(budget.selected_count)),
                ProcessField(
                    "중복 제외",
                    str(budget.duplicate_drop_count),
                ),
                ProcessField(
                    "자료별 한도 제외",
                    str(budget.source_cap_drop_count),
                ),
                ProcessField(
                    "개수 한도 제외",
                    str(budget.count_cap_drop_count),
                ),
                ProcessField(
                    "문맥 한도 제외",
                    str(budget.context_drop_count),
                ),
                ProcessField(
                    "예상 토큰",
                    str(budget.estimated_context_tokens),
                ),
                ProcessField(
                    "예상 문자",
                    str(budget.estimated_context_chars),
                ),
            ),
        ),
        ProcessStageView(
            key="citation",
            title="8. 인용",
            fields=(
                ProcessField("주장", str(citation.claim_count)),
                ProcessField("인용", str(citation.citation_count)),
                ProcessField("거부", str(citation.rejection_count)),
            ),
        ),
        ProcessStageView(
            key="generation",
            title="9. 생성 경로",
            fields=(
                ProcessField(
                    "방식",
                    _GENERATION_LABELS[generation.mode],
                ),
                ProcessField(
                    "AI 상태",
                    (
                        _LLM_LABELS[generation.llm_status]
                        if generation.llm_status is not None
                        else "AI 호출 없음"
                    ),
                ),
                ProcessField(
                    "모델",
                    generation.model or "호출 없음",
                ),
                ProcessField(
                    "실시간 확인",
                    "확인됨" if generation.live_verified else "확인 안 함",
                ),
            ),
        ),
    )


def _project_source(evidence: Evidence) -> BaselineSourceView:
    if (
        not isinstance(evidence, Evidence)
        or evidence.source_type not in _SOURCE_LABELS
    ):
        raise ProjectionError("근거를 화면에 표시할 수 없습니다.")
    details: list[ProcessField] = []
    locator = evidence.locator
    origin = locator.get("content_origin")
    if origin in _CONTENT_ORIGIN_LABELS:
        details.append(
            ProcessField(
                "자료 성격",
                _CONTENT_ORIGIN_LABELS[origin],
            )
        )
    if evidence.source_type == "news":
        _append_text_detail(details, "제공자", locator.get("provider"))
    elif evidence.source_type == "disclosure":
        receipt_no = locator.get("receipt_no")
        if (
            isinstance(receipt_no, str)
            and re.fullmatch(r"\d{14}", receipt_no)
        ):
            details.append(ProcessField("접수번호", receipt_no))
        _append_text_detail(details, "보고서", locator.get("report_name"))
        _append_text_detail(details, "구간", locator.get("section"))
    elif evidence.source_type == "research_report":
        _append_text_detail(details, "발행기관", locator.get("publisher"))
        _append_text_detail(details, "매니페스트", locator.get("manifest_id"))
        _append_text_detail(details, "문서 ID", locator.get("document_id"))
        page = locator.get("page")
        if type(page) is int and page > 0:
            details.append(ProcessField("페이지", str(page)))
        _append_text_detail(details, "구간", locator.get("section"))
    elif evidence.source_type == "glossary":
        _append_text_detail(details, "항목 ID", locator.get("entry_id"))
        version = locator.get("version")
        if type(version) is int and version > 0:
            details.append(ProcessField("버전", str(version)))
        _append_text_detail(details, "구간", locator.get("section"))

    return BaselineSourceView(
        title=_safe_text(evidence.title),
        source_type=evidence.source_type,
        source_label=_SOURCE_LABELS[evidence.source_type],
        published_date=(
            evidence.published_at.date().isoformat()
            if evidence.published_at is not None
            else None
        ),
        snippet=_safe_text(evidence.snippet),
        details=tuple(details),
        link_url=_safe_http_url(evidence.source_url),
    )


def _append_text_detail(
    output: list[ProcessField],
    label: str,
    value: object,
) -> None:
    if not isinstance(value, str) or not value.strip():
        return
    safe = _safe_text(value)
    if safe != _HIDDEN_TEXT:
        output.append(ProcessField(label, safe))


def _safe_http_url(value: object) -> str | None:
    if (
        not isinstance(value, str)
        or not value
        or _CONTROL_CHARACTER.search(value)
        or any(character.isspace() for character in value)
    ):
        return None
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme.casefold() not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or port is not None
        and not 0 < port <= 65535
    ):
        return None
    for key, nested_value in parse_qsl(parsed.query, keep_blank_values=True):
        if (
            _normalized_key(key) in _CREDENTIAL_QUERY_KEYS
            or _unsafe_text(unquote_plus(nested_value))
        ):
            return None
    return value


def _safe_text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        return _HIDDEN_TEXT
    stripped = value.strip()
    return _HIDDEN_TEXT if _unsafe_text(stripped) else stripped


def _unsafe_text(value: str) -> bool:
    if value.casefold().startswith(("http://", "https://")):
        return _safe_http_url(value) is None
    return bool(
        _CONTROL_CHARACTER.search(value)
        or _WINDOWS_PATH.search(value)
        or _BACKSLASH_UNC_PATH.search(value)
        or _FORWARD_UNC_PATH.search(value)
        or _FILE_URL.search(value)
        or _POSIX_PATH.search(value)
        or _CREDENTIAL_VALUE.search(value)
    )


def _normalized_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", unquote_plus(value))
    return _QUERY_KEY_NORMALIZER.sub("", normalized.casefold())


def _warning_label(value: str) -> str:
    return _WARNING_LABELS.get(value, "추가 확인이 필요함")


def _source_list(values: list[str]) -> str:
    return ", ".join(_SOURCE_LABELS[item] for item in values) or "없음"


def _date_range(start: object | None, end: object | None) -> str:
    start_value = start.isoformat() if hasattr(start, "isoformat") else "미지정"
    end_value = end.isoformat() if hasattr(end, "isoformat") else "미지정"
    return f"{start_value} ~ {end_value}"


__all__ = [
    "AnswerCardView",
    "BaselineAnswerView",
    "BaselineSourceView",
    "ProcessField",
    "ProcessStageView",
    "ProjectionError",
    "project_baseline_answer",
    "project_baseline_sources",
    "project_process_stages",
]
