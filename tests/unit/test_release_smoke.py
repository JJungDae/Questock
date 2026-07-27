from __future__ import annotations

from typing import Any

import pytest

from scripts import release_smoke
from scripts.release_smoke import ReleaseSmokeError, run_release_smoke


def _payload(status: str, source_type: str | None) -> dict[str, Any]:
    payload = {
        "status": status,
        "basis_date": "2026-07-24",
        "evidence": (
            [] if source_type is None else [{"source_type": source_type}]
        ),
        "diagnostics_public": {
            "data_mode": "recorded",
            "live_connectivity_checked": False,
        },
    }
    if source_type == "disclosure":
        payload["warnings"] = ["insufficient_disclosure_coverage"]
        payload["answer_sections"] = {
            "summary": " ".join(release_smoke._DISCLOSURE_ANSWER_FACTS)
        }
        payload["evidence"] = [
            {
                "source_type": "disclosure",
                "document_id": release_smoke._DISCLOSURE_DOCUMENT_ID,
                "locator": {
                    "receipt_no": "20260515002181",
                    "viewer_url": release_smoke._DISCLOSURE_VIEWER_URL,
                    "content_level": "verified_body_facts",
                    "verification_status": "verified_against_source",
                    "section": "III. 재무에 관한 사항 > 1. 요약재무정보",
                    **fact,
                },
            }
            for fact in release_smoke._REQUIRED_DISCLOSURE_FACTS
        ]
    return payload


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
        if (
            message
            == "SK하이닉스 공시를 삼성전자 분기보고서로 설명해줘."
        ):
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


def test_release_smoke_accepts_expected_source_after_other_evidence() -> None:
    payload = _payload("partial", "research_report")
    payload["evidence"].insert(0, {"source_type": "news"})

    release_smoke._assert_response(
        payload,
        expected_status="partial",
        expected_source="research_report",
    )


def test_release_smoke_rejects_metadata_only_disclosure() -> None:
    bad = _payload("partial", "disclosure")
    bad["answer_sections"] = {"summary": "접수번호 20260515002181"}

    with pytest.raises(ReleaseSmokeError):
        release_smoke._assert_disclosure_response(bad)


def test_release_smoke_allows_expanded_fsc_disclosure_fact_inventory() -> None:
    payload = _payload("partial", "disclosure")
    payload["evidence"].append(
        {
            "source_type": "disclosure",
            "document_id": release_smoke._DISCLOSURE_DOCUMENT_ID,
            "locator": {
                "receipt_no": "20260515002181",
                "viewer_url": release_smoke._DISCLOSURE_VIEWER_URL,
                "content_level": "verified_body_facts",
                "verification_status": "verified_against_source",
                "section": "II. 사업의 내용 > 위험관리",
                "fact_id": "samsung-electronics-disc-014",
                "category": "risk_or_uncertainty",
                "value": None,
                "unit": None,
                "physical_pdf_page": 23,
                "dart_printed_page": 20,
            },
        }
    )

    release_smoke._assert_disclosure_response(payload)


def test_release_smoke_rejects_missing_required_fsc_disclosure_fact() -> None:
    bad = _payload("partial", "disclosure")
    bad["evidence"] = bad["evidence"][1:]

    with pytest.raises(ReleaseSmokeError):
        release_smoke._assert_disclosure_response(bad)


def test_release_smoke_rejects_non_list_disclosure_warning() -> None:
    bad = _payload("partial", "disclosure")
    bad["warnings"] = "insufficient_disclosure_coverage"

    with pytest.raises(ReleaseSmokeError):
        release_smoke._assert_disclosure_response(bad)
