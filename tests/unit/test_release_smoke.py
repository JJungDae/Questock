from __future__ import annotations

from typing import Any

import pytest

from scripts import release_smoke
from scripts.release_smoke import ReleaseSmokeError, run_release_smoke


def _payload(status: str, source_type: str | None) -> dict[str, Any]:
    return {
        "status": status,
        "basis_date": "2026-07-26",
        "evidence": (
            [] if source_type is None else [{"source_type": source_type}]
        ),
        "diagnostics_public": {
            "data_mode": "recorded",
            "live_connectivity_checked": False,
        },
    }


def test_release_smoke_runs_deterministic_recorded_scenarios(
    monkeypatch,
) -> None:
    calls: list[tuple[str, str]] = []

    def fake_post(
        api_url: str,
        *,
        message: str,
        session_id: str,
    ) -> dict[str, Any]:
        calls.append((message, session_id))
        if message == "삼성전자 최근 공시 핵심":
            return _payload("partial", "disclosure")
        if message == "삼성전자 리포트 요약":
            return _payload("complete", "research_report")
        if message == "PER이 뭐야?":
            return _payload("complete", "glossary")
        if message == "SK하이닉스 최근 공시 요약":
            return _payload("no_evidence", None)
        if message == "삼성전자 지금 매수해야 해?":
            return _payload("blocked", None)
        if message == "그럼 위험 요인은?":
            return _payload("partial", "research_report")
        return _payload("complete", "news")

    monkeypatch.setattr(release_smoke, "_post", fake_post)

    result = run_release_smoke("http://127.0.0.1:8000/api/chat")

    assert result == {
        "status": "ok",
        "data_mode": "recorded",
        "live_connectivity_checked": False,
        "scenario_count": 7,
        "scenarios": [
            {"scenario": "recent_issue", "status": "complete"},
            {"scenario": "disclosure", "status": "partial"},
            {"scenario": "research_report", "status": "complete"},
            {"scenario": "glossary", "status": "complete"},
            {"scenario": "wrong_company", "status": "no_evidence"},
            {"scenario": "blocked", "status": "blocked"},
            {"scenario": "multi_turn", "status": "partial"},
        ],
    }
    assert len(calls) == 8
    assert calls[-2:] == [
        ("삼성전자 최근 이슈 요약", "release-smoke-multi-turn"),
        ("그럼 위험 요인은?", "release-smoke-multi-turn"),
    ]


def test_release_smoke_rejects_live_or_malformed_public_result() -> None:
    bad = _payload("complete", "news")
    bad["diagnostics_public"]["data_mode"] = "live"

    with pytest.raises(ReleaseSmokeError):
        release_smoke._assert_response(
            bad,
            expected_status="complete",
            expected_source="news",
        )
