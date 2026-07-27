from __future__ import annotations

import secrets
from dataclasses import dataclass
from functools import cache
from uuid import uuid4

import streamlit as st
from pydantic import ValidationError

from app.api.schemas import ChatRequest, ChatResponse
from app.services.service_snapshot import SERVICE_SNAPSHOT_ID
from app.ui.projections import (
    ProjectionError,
    project_baseline_answer,
    project_baseline_sources,
    project_process_stages,
)
from app.ui.transport import (
    ChatTransport,
    ChatTransportError,
    HttpChatTransport,
    build_opaque_client_key,
    load_ui_config,
)

_INPUT_FAILURE = "질문을 한 글자 이상 입력해 주세요."
_PROJECTION_FAILURE = "응답을 화면에 표시할 수 없습니다."
_MAX_UI_TRANSCRIPT_ENTRIES = 4
_SNAPSHOT_BASIS_LABEL = "2026-07-24 14:02 KST"
_NEWS_COLLECTION_LABEL = "2026-07-24 00:00~14:00 KST"


@dataclass(frozen=True)
class _UITranscriptEntry:
    question: str
    response: ChatResponse


def run(transport: ChatTransport | None = None) -> None:
    st.set_page_config(
        page_title="Questock",
        page_icon="Q",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _initialize_state()
    _clear_chat_input_if_requested()

    st.sidebar.title("Questock")
    _render_snapshot_status()
    st.sidebar.caption(f"세션: {st.session_state.session_id}")
    if st.sidebar.button("새 세션", key="reset_session"):
        st.session_state.session_id = _new_session_id()
        st.session_state.response = None
        st.session_state.question = ""
        st.session_state.question_input = None
        st.session_state.transcript = ()

    st.title("Questock")
    st.caption("근거 기반 국내 종목 질의")
    st.warning(
        "계좌번호, 인증정보, 거래내역 등 개인 금융정보를 입력하지 마세요."
    )

    submitted_question = st.chat_input(
        "종목에 대해 궁금한 점을 물어보세요",
        max_chars=2000,
        key="question_input",
    )

    if submitted_question is not None:
        try:
            request = ChatRequest(
                message=submitted_question,
                session_id=st.session_state.session_id,
            )
        except ValidationError:
            st.error(_INPUT_FAILURE)
        else:
            try:
                active_transport = transport or _default_transport(
                    st.session_state.session_id
                )
                with st.spinner("답변을 확인하고 있습니다."):
                    response = active_transport.send(
                        request,
                        _transport_timeout(transport),
                    )
                st.session_state.response = response
                st.session_state.question = ""
                st.session_state.transcript = _append_transcript(
                    st.session_state.transcript,
                    question=request.message,
                    response=response,
                )
                st.session_state.clear_question_input = True
                st.rerun()
            except ChatTransportError as exc:
                st.session_state.response = None
                st.error(str(exc))

    response = st.session_state.response
    if isinstance(response, ChatResponse):
        _render_sidebar_status(response)
    transcript = st.session_state.transcript
    if isinstance(transcript, tuple) and transcript:
        try:
            _render_transcript(transcript)
        except ProjectionError:
            st.error(_PROJECTION_FAILURE)
    elif isinstance(response, ChatResponse):
        try:
            _render_response(response)
        except ProjectionError:
            st.error(_PROJECTION_FAILURE)


def _initialize_state() -> None:
    if "session_id" not in st.session_state:
        st.session_state.session_id = _new_session_id()
    if "response" not in st.session_state:
        st.session_state.response = None
    if "question" not in st.session_state:
        st.session_state.question = ""
    if "transcript" not in st.session_state:
        st.session_state.transcript = ()


def _clear_chat_input_if_requested() -> None:
    if st.session_state.pop("clear_question_input", False):
        st.session_state.question_input = None


def _append_transcript(
    entries: object,
    *,
    question: str,
    response: ChatResponse,
) -> tuple[_UITranscriptEntry, ...]:
    canonical_entries = (
        entries
        if isinstance(entries, tuple)
        and all(isinstance(item, _UITranscriptEntry) for item in entries)
        else ()
    )
    updated = (
        *canonical_entries,
        _UITranscriptEntry(
            question=question,
            response=response.model_copy(deep=True),
        ),
    )
    return updated[-_MAX_UI_TRANSCRIPT_ENTRIES:]


def _render_transcript(entries: tuple[_UITranscriptEntry, ...]) -> None:
    for entry in entries:
        with st.chat_message("user"):
            st.text(entry.question)
        with st.chat_message("assistant"):
            _render_response(entry.response)


def _new_session_id() -> str:
    return f"anonymous-{uuid4()}"


def _default_transport(session_id: str) -> HttpChatTransport:
    config = load_ui_config()
    try:
        ip_address_value = st.context.ip_address
    except Exception:
        ip_address_value = None
    client_key = build_opaque_client_key(
        ip_address_value=ip_address_value,
        session_id=session_id,
        secret=_client_hmac_secret(),
    )
    return HttpChatTransport(
        config.endpoint,
        client_key=client_key,
    )


@cache
def _client_hmac_secret() -> bytes:
    return secrets.token_bytes(32)


def _transport_timeout(transport: ChatTransport | None) -> float:
    if transport is not None:
        return load_ui_config(lambda _: None).timeout_seconds
    return load_ui_config().timeout_seconds


def _render_snapshot_status() -> None:
    st.sidebar.markdown("**고정 스냅샷**")
    st.sidebar.caption(f"Snapshot ID: {SERVICE_SNAPSHOT_ID}")
    st.sidebar.caption(f"기준 시점: {_SNAPSHOT_BASIS_LABEL}")
    st.sidebar.caption(f"뉴스 수집 범위: {_NEWS_COLLECTION_LABEL}")
    st.sidebar.caption("자료 모드: recorded")
    st.sidebar.caption(
        "답변 생성: Gemini 3.5 Flash 또는 근거 기반 고정 응답"
    )
    st.sidebar.caption(
        "리포트: Questock 검증 요약 사용 · 외부 LLM 전송 안 함"
    )
    st.sidebar.caption(
        "공시: 종목별 단일 분기보고서 · 범위 부족 시 경고"
    )
    st.sidebar.caption(
        "요청 한도 도달 시: 한도 안내와 함께 근거 기반 고정 응답"
    )


def _render_sidebar_status(response: ChatResponse) -> None:
    process = response.diagnostics_public
    mode_labels = {
        "recorded": "기록 자료",
        "live": "실시간 자료",
        "mixed": "혼합 자료",
        "unconfigured": "자료 미연결",
    }
    st.sidebar.caption(f"자료 모드: {mode_labels[process.data_mode]}")
    live_label = "확인됨" if process.live_connectivity_checked else "확인 안 함"
    st.sidebar.caption(f"실시간 연결: {live_label}")
    if process.data_mode == "recorded":
        st.sidebar.caption("고정 데모 자료 · 실시간 연결 아님")
    generation_labels = {
        "llm": "Gemini 3.5 Flash",
        "fixed_template": "근거 기반 고정 응답",
        "blocked": "정책에 따른 제공 제한",
        "not_called": "생성 호출 없음",
    }
    st.sidebar.caption(
        f"현재 답변 생성: {generation_labels[process.generation.mode]}"
    )


def _render_response(response: ChatResponse) -> None:
    answer = project_baseline_answer(response)
    for card in answer.cards:
        with st.container(border=True):
            st.markdown(f"**{card.title}**")
            for item in card.items:
                if card.emphasis == "error":
                    st.error(item)
                else:
                    st.text(item)
    status_parts = [f"상태: {answer.status_label}"]
    if answer.security_name is not None:
        status_parts.append(f"종목: {answer.security_name}")
    status_parts.append(f"기준일: {answer.basis_date}")
    st.caption(" · ".join(status_parts))
    for warning in answer.warnings:
        st.warning(warning)
    if answer.missing_sources:
        st.warning(f"누락 자료: {', '.join(answer.missing_sources)}")

    sources = project_baseline_sources(response)
    if sources:
        st.caption("근거")
        for source in _compact_sources(sources):
            title = _compact_source_title(source)
            label = f"{source.source_label} · {title}"
            if source.link_url is None:
                st.text(label)
            else:
                safe_label = _escape_markdown_label(label)
                st.markdown(f"[{safe_label}]({source.link_url})")

    with st.expander("분석 과정 보기", expanded=False):
        for stage in project_process_stages(response.diagnostics_public):
            st.markdown(f"**{stage.title}**")
            for field in stage.fields:
                st.text(f"{field.label}: {field.value}")


def _compact_sources(sources: tuple[object, ...]) -> tuple[object, ...]:
    output = []
    seen: set[tuple[object, object]] = set()
    for source in sources:
        key = (
            getattr(source, "source_type", None),
            getattr(source, "link_url", None)
            or getattr(source, "title", None),
        )
        if key in seen:
            continue
        seen.add(key)
        output.append(source)
    return tuple(output)


def _compact_source_title(source: object) -> str:
    title = getattr(source, "title", "")
    source_type = getattr(source, "source_type", "")
    if not isinstance(title, str):
        return "원문"
    if source_type == "research_report" and " - " in title:
        return title.split(" - ", 1)[0]
    return title


def _escape_markdown_label(value: str) -> str:
    escaped = value.replace("\\", "\\\\")
    for character in ("`", "*", "_", "{", "}", "[", "]", "<", ">", "#"):
        escaped = escaped.replace(character, f"\\{character}")
    return escaped


__all__ = ["run"]
