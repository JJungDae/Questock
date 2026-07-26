from __future__ import annotations

from uuid import uuid4

import streamlit as st
from pydantic import ValidationError

from app.api.schemas import ChatRequest, ChatResponse
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
    load_ui_config,
)

_SECURITY_CHOICES = (
    "선택 안 함",
    "삼성전자",
    "SK하이닉스",
    "현대자동차",
)
_INPUT_FAILURE = "질문을 한 글자 이상 입력해 주세요."
_PROJECTION_FAILURE = "응답을 화면에 표시할 수 없습니다."


def run(transport: ChatTransport | None = None) -> None:
    st.set_page_config(
        page_title="Questock",
        page_icon="Q",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _initialize_state()

    st.sidebar.title("Questock")
    selected_security = st.sidebar.selectbox(
        "지원 종목",
        _SECURITY_CHOICES,
        key="security_selector",
    )
    st.sidebar.caption(f"세션: {st.session_state.session_id}")
    if st.sidebar.button("새 세션", key="reset_session"):
        st.session_state.session_id = _new_session_id()
        st.session_state.response = None
        st.session_state.question = ""

    if (
        selected_security != _SECURITY_CHOICES[0]
        and not st.session_state.question.strip()
    ):
        st.session_state.question = f"{selected_security} "

    st.title("Questock")
    st.caption("근거 기반 국내 종목 질의")

    with st.form("chat_form", clear_on_submit=False):
        st.text_area(
            "질문",
            key="question",
            height=100,
            max_chars=2000,
        )
        submitted = st.form_submit_button("질문 보내기", type="primary")

    if submitted:
        try:
            request = ChatRequest(
                message=st.session_state.question,
                session_id=st.session_state.session_id,
            )
        except ValidationError:
            st.error(_INPUT_FAILURE)
        else:
            try:
                active_transport = transport or _default_transport()
                with st.spinner("답변을 확인하고 있습니다."):
                    st.session_state.response = active_transport.send(
                        request,
                        _transport_timeout(transport),
                    )
            except ChatTransportError as exc:
                st.session_state.response = None
                st.error(str(exc))

    response = st.session_state.response
    if isinstance(response, ChatResponse):
        _render_sidebar_status(response)
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


def _new_session_id() -> str:
    return f"anonymous-{uuid4()}"


def _default_transport() -> HttpChatTransport:
    config = load_ui_config()
    return HttpChatTransport(config.endpoint)


def _transport_timeout(transport: ChatTransport | None) -> float:
    if transport is not None:
        return load_ui_config(lambda _: None).timeout_seconds
    return load_ui_config().timeout_seconds


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


def _render_response(response: ChatResponse) -> None:
    answer = project_baseline_answer(response)
    st.subheader("답변")
    st.caption(f"상태: {answer.status_label}")
    if answer.security_name is not None:
        st.caption(f"종목: {answer.security_name}")
    st.caption(f"기준일: {answer.basis_date}")

    for card in answer.cards:
        with st.container(border=True):
            st.markdown(f"**{card.title}**")
            for item in card.items:
                if card.emphasis == "error":
                    st.error(item)
                else:
                    st.text(item)
    for warning in answer.warnings:
        st.warning(warning)
    if answer.missing_sources:
        st.warning(f"누락 자료: {', '.join(answer.missing_sources)}")

    sources = project_baseline_sources(response)
    if sources:
        st.subheader("근거")
        for source in sources:
            with st.container(border=True):
                st.text(source.title)
                detail = source.source_label
                if source.published_date is not None:
                    detail = f"{detail} · {source.published_date}"
                st.caption(detail)
                st.text(source.snippet)
                for field in source.details:
                    st.text(f"{field.label}: {field.value}")
                if source.link_url is not None:
                    st.link_button(
                        "원문 보기",
                        source.link_url,
                        icon=":material/open_in_new:",
                    )

    with st.expander("분석 과정 보기", expanded=False):
        for stage in project_process_stages(response.diagnostics_public):
            st.markdown(f"**{stage.title}**")
            for field in stage.fields:
                st.text(f"{field.label}: {field.value}")


__all__ = ["run"]
