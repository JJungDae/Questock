from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_TIMEOUT_SECONDS = 20


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
