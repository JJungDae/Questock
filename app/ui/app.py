from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import date, datetime, time
from functools import cache
from uuid import uuid4
from zoneinfo import ZoneInfo

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
SEOUL_TZ = ZoneInfo("Asia/Seoul")
_CHECKPOINT_DATES = (
    date(2026, 7, 24),
    date(2026, 7, 25),
    date(2026, 7, 26),
    date(2026, 7, 27),
)
_CHECKPOINT_OPTIONS = (
    ("장 전·프리마켓 (08:30)", time(8, 30)),
    ("장중 (10:00)", time(10, 0)),
    ("장중 (14:00)", time(14, 0)),
    ("애프터마켓 (19:00)", time(19, 0)),
    ("전체 장 종료 후 (21:00)", time(21, 0)),
)
_NEWS_COLLECTION_LABEL = "2026-07-24 00:00~2026-07-27 23:59 KST"


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

    st.title("Questock")
    st.caption("근거 기반 국내 종목 질의")
    st.warning(
        "계좌번호, 인증정보, 거래내역 등 개인 금융정보를 입력하지 마세요."
    )
    selected_as_of = _render_checkpoint_controls()
    _apply_checkpoint_context(selected_as_of)

    st.sidebar.title("Questock")
    _render_snapshot_status(selected_as_of)
    st.sidebar.caption(f"세션: {st.session_state.session_id}")
    if st.sidebar.button("새 세션", key="reset_session"):
        st.session_state.session_id = _new_session_id()
        st.session_state.response = None
        st.session_state.question = ""
        st.session_state.question_input = None
        st.session_state.transcript = ()

    conversation_placeholder = st.empty()
    loading_placeholder = st.empty()
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
                as_of=selected_as_of,
            )
        except ValidationError:
            st.error(_INPUT_FAILURE)
        else:
            try:
                active_transport = transport or _default_transport(
                    st.session_state.session_id
                )
                with loading_placeholder.container():
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
                loading_placeholder.empty()
                st.rerun()
            except ChatTransportError as exc:
                st.session_state.response = None
                st.error(str(exc))
            finally:
                loading_placeholder.empty()

    response = st.session_state.response
    if isinstance(response, ChatResponse):
        _render_sidebar_status(response)
    transcript = st.session_state.transcript
    if isinstance(transcript, tuple) and transcript:
        try:
            with conversation_placeholder.container():
                _render_transcript(transcript)
        except ProjectionError:
            with conversation_placeholder.container():
                st.error(_PROJECTION_FAILURE)
    elif isinstance(response, ChatResponse):
        try:
            with conversation_placeholder.container():
                _render_response(response)
        except ProjectionError:
            with conversation_placeholder.container():
                st.error(_PROJECTION_FAILURE)
    else:
        conversation_placeholder.empty()


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


def _render_checkpoint_controls() -> datetime:
    first, second = st.columns(2)
    with first:
        selected_date = st.selectbox(
            "기준 날짜",
            _CHECKPOINT_DATES,
            index=3,
            format_func=lambda value: value.isoformat(),
            key="checkpoint_date",
            on_change=_reset_checkpoint_conversation,
        )
    with second:
        selected_label = st.selectbox(
            "기준 시점",
            tuple(label for label, _ in _CHECKPOINT_OPTIONS),
            index=2,
            key="checkpoint_time",
            on_change=_reset_checkpoint_conversation,
        )
    checkpoint_time = dict(_CHECKPOINT_OPTIONS)[selected_label]
    return datetime.combine(
        selected_date,
        checkpoint_time,
        tzinfo=SEOUL_TZ,
    )


def _apply_checkpoint_context(selected_as_of: datetime) -> None:
    checkpoint = selected_as_of.strftime("%Y%m%dT%H%MKST")
    previous = st.session_state.get("active_checkpoint_id")
    if previous is not None and previous != checkpoint:
        _reset_checkpoint_conversation()
    st.session_state.active_checkpoint_id = checkpoint


def _reset_checkpoint_conversation() -> None:
    st.session_state.session_id = _new_session_id()
    st.session_state.response = None
    st.session_state.question = ""
    st.session_state.transcript = ()
    st.session_state.active_checkpoint_id = None


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


def _render_snapshot_status(selected_as_of: datetime) -> None:
    st.sidebar.markdown("**고정 스냅샷**")
    st.sidebar.caption(f"Snapshot ID: {SERVICE_SNAPSHOT_ID}")
    st.sidebar.caption(
        "선택 기준 시점: "
        f"{selected_as_of.strftime('%Y-%m-%d %H:%M KST')}"
    )
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
    if response.market_snapshot is not None:
        market = response.market_snapshot
        market_status = (
            "장 운영 중"
            if market.market_status == "open"
            else "장 종료·휴장"
            if market.market_status == "closed"
            else "체결 전"
            if market.market_status == "no_trade_yet"
            else "가격 자료 없음"
        )
        st.caption(
            "기준 시점 "
            f"{market.requested_as_of.astimezone(SEOUL_TZ):%Y-%m-%d %H:%M KST}"
            f" · 시장 상태 {market_status}"
            " · 가격 관측 "
            f"{market.observed_at.astimezone(SEOUL_TZ):%Y-%m-%d %H:%M KST}"
        )
    for card in answer.cards:
        st.markdown(f"**{card.title}**")
        if card.emphasis == "error":
            for item in card.items:
                st.error(item)
        elif len(card.items) == 1:
            st.markdown(_escape_markdown_text(card.items[0]))
        else:
            for item in card.items:
                st.markdown(f"- {_escape_markdown_text(item)}")

    status_parts = []
    if answer.security_name is not None:
        status_parts.append(answer.security_name)
    if response.basis_at is not None:
        status_parts.append(
            response.basis_at.astimezone(SEOUL_TZ).strftime(
                "%Y-%m-%d %H:%M KST 기준"
            )
        )
    else:
        status_parts.append(f"{answer.basis_date} 기준")
    status_parts.append(answer.status_label)
    st.caption(" · ".join(status_parts))

    notices = list(answer.warnings)
    if answer.missing_sources:
        notices.append(
            f"확인하지 못한 자료: {', '.join(answer.missing_sources)}"
        )
    if notices:
        st.info(f"참고: {' · '.join(notices)}")

    sources = project_baseline_sources(response)
    if sources:
        st.caption("참고한 자료")
        for source in _compact_sources(sources):
            title = _compact_source_title(source)
            label = f"{source.source_label} · {title}"
            if source.link_url is None:
                st.markdown(f"- {_escape_markdown_text(label)}")
            else:
                safe_label = _escape_markdown_label(label)
                st.markdown(f"- [{safe_label}]({source.link_url})")

    with st.expander("답변이 만들어진 과정", expanded=False):
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


def _escape_markdown_text(value: str) -> str:
    escaped = _escape_markdown_label(value)
    for character in ("|", "~"):
        escaped = escaped.replace(character, f"\\{character}")
    return escaped


__all__ = ["run"]
