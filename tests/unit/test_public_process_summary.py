from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.api.schemas import ChatRequest, PublicProcessSummary
from app.services.chat_service import ChatService

BASIS_AT = datetime(2026, 7, 25, 3, tzinfo=UTC)


def _summary() -> PublicProcessSummary:
    response = asyncio.run(
        ChatService(utc_now=lambda: BASIS_AT).chat(
            ChatRequest(
                message="삼성전자 최근 뉴스",
                session_id="process-summary-unit",
            )
        )
    )
    return response.diagnostics_public


def test_top_level_and_nested_fields_are_exact() -> None:
    summary = _summary()
    payload = summary.model_dump(mode="json")

    assert list(payload) == [
        "trace_version",
        "data_mode",
        "live_connectivity_checked",
        "security",
        "query_plan",
        "sources",
        "evidence_pipeline",
        "decision",
        "context_budget",
        "citation",
        "generation",
    ]
    assert list(payload["security"]) == ["resolution_status", "security_id"]
    assert list(payload["query_plan"]) == [
        "intent",
        "required_sources",
        "date_start",
        "date_end",
    ]
    assert list(payload["sources"][0]) == [
        "source_type",
        "provider_status",
        "document_count",
        "from_cache",
    ]
    assert payload["generation"] == {
        "mode": "fixed_template",
        "llm_status": None,
        "model": None,
        "live_verified": False,
    }


def test_public_summary_does_not_expose_private_content() -> None:
    serialized = _summary().model_dump_json()
    lowered = serialized.casefold()

    for forbidden in (
        "삼성전자 최근 뉴스",
        "session_id",
        "evidence:",
        "http://",
        "https://",
        "locator",
        "snippet",
        "api_key",
        "permission",
        "raw",
        "callback",
    ):
        assert forbidden.casefold() not in lowered


def test_summary_is_deterministic_and_nested_collections_are_fresh() -> None:
    first = _summary()
    second = _summary()

    assert first.model_dump_json() == second.model_dump_json()
    assert first is not second
    assert first.sources is not second.sources
    first.sources[0].source_type = "changed"
    assert second.sources[0].source_type == "news"


def test_unknown_public_field_is_rejected() -> None:
    payload = _summary().model_dump(mode="python")
    payload["rendered_prompt"] = "forbidden"

    with pytest.raises(ValidationError):
        PublicProcessSummary.model_validate(payload)

    assert "rendered_prompt" not in json.dumps(
        _summary().model_dump(mode="json"),
        ensure_ascii=False,
    )


@pytest.mark.parametrize(
    ("message", "expected_status", "expected_security_id"),
    [
        ("삼성전자 최근 뉴스", "resolved", "KRX:005930"),
        ("삼성 최근 뉴스", "ambiguous", None),
        ("005935 최근 뉴스", "unsupported", None),
        ("카카오 최근 뉴스", "not_found", None),
        ("삼성전자 지금 매수해야 하나", "resolved", "KRX:005930"),
        ("삼성전자 왜 올랐어", "resolved", "KRX:005930"),
        (
            "삼성전자와 SK하이닉스 최근 뉴스",
            "ambiguous",
            None,
        ),
    ],
)
def test_public_security_resolution_is_truthful(
    message: str,
    expected_status: str,
    expected_security_id: str | None,
) -> None:
    response = asyncio.run(
        ChatService(utc_now=lambda: BASIS_AT).chat(
            ChatRequest(
                message=message,
                session_id="security-resolution-unit",
            )
        )
    )

    assert (
        response.diagnostics_public.security.resolution_status
        == expected_status
    )
    assert (
        response.diagnostics_public.security.security_id
        == expected_security_id
    )
