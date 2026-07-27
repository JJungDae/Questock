from __future__ import annotations

import asyncio
import inspect
from datetime import UTC, datetime

from app.api.schemas import ChatRequest
from app.services.chat_service import ChatService
from app.services.observability import InMemoryObservationSink
from app.ui.app import _append_transcript, run


NOW = datetime(2026, 7, 27, tzinfo=UTC)


def _response():
    return asyncio.run(
        ChatService(
            utc_now=lambda: NOW,
            observation_sink=InMemoryObservationSink(),
        ).chat(
            ChatRequest(
                message="\uc0bc\uc131\uc804\uc790 \ucd5c\uadfc \ub274\uc2a4",
                session_id="ui-transcript",
            )
        )
    )


def test_ui_transcript_keeps_four_deep_copied_current_session_entries() -> None:
    response = _response()
    entries = ()

    for index in range(5):
        entries = _append_transcript(
            entries,
            question=f"question-{index}",
            response=response,
        )

    response.warnings.append("caller-mutation")
    assert [item.question for item in entries] == [
        "question-1",
        "question-2",
        "question-3",
        "question-4",
    ]
    assert all(
        "caller-mutation" not in item.response.warnings
        for item in entries
    )
    assert len({id(item.response) for item in entries}) == 4


def test_invalid_transcript_state_is_replaced_not_extended() -> None:
    entries = _append_transcript(
        ("invalid-entry",),
        question="new-question",
        response=_response(),
    )

    assert len(entries) == 1
    assert entries[0].question == "new-question"


def test_transport_call_remains_inside_chat_input_submission() -> None:
    source = inspect.getsource(run)

    assert source.index("if submitted_question is not None:") < source.index(
        "active_transport.send"
    )
    assert "st.chat_input(" in source
    assert "st.form(" not in source
