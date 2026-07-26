from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_TIMEOUT_SECONDS = 20
_DISCLOSURE_DOCUMENT_ID = "disclosure:20260515002181"
_DISCLOSURE_VIEWER_URL = (
    "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260515002181"
)
_DISCLOSURE_FACTS = [
    {
        "fact": "연결 매출",
        "value": "133,873,444",
        "unit": "백만원",
        "physical_pdf_page": 53,
        "dart_printed_page": 50,
        "section": "연결 매출",
    },
    {
        "fact": "연결 영업이익",
        "value": "57,232,797",
        "unit": "백만원",
        "physical_pdf_page": 53,
        "dart_printed_page": 50,
        "section": "연결 영업이익",
    },
    {
        "fact": "DS 부문 매출",
        "value": "817,156",
        "unit": "억원",
        "physical_pdf_page": 52,
        "dart_printed_page": 49,
        "section": "DS 부문 매출",
    },
    {
        "fact": "DS 부문 영업이익",
        "value": "536,633",
        "unit": "억원",
        "physical_pdf_page": 52,
        "dart_printed_page": 49,
        "section": "DS 부문 영업이익",
    },
    {
        "fact": "시설투자 합계",
        "value": "112,332",
        "unit": "억원",
        "physical_pdf_page": 16,
        "dart_printed_page": 13,
        "section": "시설투자 합계",
    },
    {
        "fact": "HBM4 관련 사실",
        "value": "1c D램·4나노 베이스 다이 적용 HBM4 양산 출하",
        "unit": None,
        "physical_pdf_page": 31,
        "dart_printed_page": 28,
        "section": "HBM4 관련 사실",
    },
]
_DISCLOSURE_ANSWER_FACTS = (
    "연결 매출 133,873,444백만원",
    "연결 영업이익 57,232,797백만원",
    "DS 부문 매출 817,156억원",
    "DS 부문 영업이익 536,633억원",
    "시설투자 합계 112,332억원",
    "1c D램·4나노 베이스 다이 적용 HBM4 양산 출하",
)


class ReleaseSmokeError(RuntimeError):
    """Raised when the recorded release does not satisfy its public contract."""


def run_release_smoke(api_url: str) -> dict[str, object]:
    if (
        not isinstance(api_url, str)
        or not api_url.startswith(("http://", "https://"))
    ):
        raise ReleaseSmokeError("release smoke configuration is invalid")
    scenarios = (
        (
            "recent_issue",
            "삼성전자 최근 이슈 요약",
            "complete",
            "news",
        ),
        (
            "disclosure",
            "삼성전자 최근 공시 핵심",
            "partial",
            "disclosure",
        ),
        (
            "research_report",
            "삼성전자 리포트 요약",
            "complete",
            "research_report",
        ),
        ("glossary", "PER이 뭐야?", "complete", "glossary"),
        (
            "wrong_company",
            "SK하이닉스 최근 공시 요약",
            "no_evidence",
            None,
        ),
        (
            "blocked",
            "삼성전자 지금 매수해야 해?",
            "blocked",
            None,
        ),
    )
    results = []
    for scenario_id, message, expected_status, expected_source in scenarios:
        payload = _post(
            api_url,
            message=message,
            session_id=f"release-smoke-{scenario_id}",
        )
        _assert_response(
            payload,
            expected_status=expected_status,
            expected_source=expected_source,
        )
        if scenario_id == "disclosure":
            _assert_disclosure_response(payload)
        results.append(
            {
                "scenario": scenario_id,
                "status": payload["status"],
            }
        )

    session_id = "release-smoke-multi-turn"
    _assert_response(
        _post(
            api_url,
            message="삼성전자 최근 이슈 요약",
            session_id=session_id,
        ),
        expected_status="complete",
        expected_source="news",
    )
    follow_up = _post(
        api_url,
        message="그럼 위험 요인은?",
        session_id=session_id,
    )
    _assert_response(
        follow_up,
        expected_status="partial",
        expected_source="research_report",
    )
    results.append(
        {
            "scenario": "multi_turn",
            "status": follow_up["status"],
        }
    )
    return {
        "status": "ok",
        "data_mode": "recorded",
        "live_connectivity_checked": False,
        "scenario_count": len(results),
        "scenarios": results,
    }


def _post(
    api_url: str,
    *,
    message: str,
    session_id: str,
) -> dict[str, Any]:
    body = json.dumps(
        {"message": message, "session_id": session_id},
        ensure_ascii=False,
    ).encode("utf-8")
    request = Request(
        api_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (
        HTTPError,
        URLError,
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        raise ReleaseSmokeError("release smoke request failed") from None
    if not isinstance(payload, dict):
        raise ReleaseSmokeError("release smoke response is invalid")
    return payload


def _assert_response(
    payload: Mapping[str, Any],
    *,
    expected_status: str,
    expected_source: str | None,
) -> None:
    diagnostics = payload.get("diagnostics_public")
    if (
        payload.get("status") != expected_status
        or not isinstance(diagnostics, Mapping)
        or diagnostics.get("data_mode") != "recorded"
        or diagnostics.get("live_connectivity_checked") is not False
        or payload.get("basis_date") != "2026-07-26"
    ):
        raise ReleaseSmokeError("release smoke response is invalid")
    evidence = payload.get("evidence")
    if not isinstance(evidence, list):
        raise ReleaseSmokeError("release smoke response is invalid")
    if expected_source is None:
        if evidence:
            raise ReleaseSmokeError("release smoke response is invalid")
        return
    if (
        not evidence
        or not isinstance(evidence[0], Mapping)
        or evidence[0].get("source_type") != expected_source
    ):
        raise ReleaseSmokeError("release smoke response is invalid")


def _assert_disclosure_response(payload: Mapping[str, Any]) -> None:
    evidence = payload.get("evidence")
    warnings = payload.get("warnings")
    answer_sections = payload.get("answer_sections")
    if (
        payload.get("status") != "partial"
        or not isinstance(evidence, list)
        or len(evidence) != 1
        or not isinstance(evidence[0], Mapping)
        or evidence[0].get("document_id") != _DISCLOSURE_DOCUMENT_ID
        or not isinstance(warnings, list)
        or "insufficient_disclosure_coverage" not in warnings
    ):
        raise ReleaseSmokeError("release disclosure response is invalid")
    locator = evidence[0].get("locator")
    if (
        not isinstance(locator, Mapping)
        or locator.get("receipt_no") != "20260515002181"
        or locator.get("viewer_url") != _DISCLOSURE_VIEWER_URL
        or locator.get("content_level") != "verified_body_facts"
        or locator.get("section") != "verified body facts"
        or locator.get("facts") != _DISCLOSURE_FACTS
    ):
        raise ReleaseSmokeError("release disclosure response is invalid")
    try:
        answer_text = json.dumps(answer_sections, ensure_ascii=False)
    except (TypeError, ValueError):
        raise ReleaseSmokeError(
            "release disclosure response is invalid"
        ) from None
    if any(fact not in answer_text for fact in _DISCLOSURE_ANSWER_FACTS):
        raise ReleaseSmokeError("release disclosure response is invalid")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", required=True)
    args = parser.parse_args(argv)
    try:
        result = run_release_smoke(args.api_url)
    except ReleaseSmokeError:
        sys.stdout.write(
            json.dumps(
                {"status": "error", "message": "release smoke failed"},
                sort_keys=True,
            )
        )
        sys.stdout.write("\n")
        return 1
    sys.stdout.write(
        json.dumps(result, ensure_ascii=False, sort_keys=True)
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
