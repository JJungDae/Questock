from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from scripts.run_service_acceptance import (
    MAX_PROVIDER_ATTEMPTS,
    ProviderAttemptCounter,
    ServiceAcceptanceRunError,
    run_followup_acceptance,
    run_primary_acceptance,
)

FIXTURE = Path("tests/fixtures/service_acceptance/fsc_v1.json")


def _response(content: str) -> dict[str, Any]:
    return {
        "choices": [
            {
                "message": {"content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 10,
            "total_tokens": 20,
        },
    }


async def _extractive_completion(**kwargs: Any) -> dict[str, Any]:
    rendered = "\n".join(
        item["content"] for item in kwargs["messages"]
    )
    evidence_id = next(
        line.split("Evidence ID: ", 1)[1]
        for line in rendered.splitlines()
        if line.startswith("Evidence ID: ")
    )
    snippet = next(
        line.split("Snippet: ", 1)[1]
        for line in rendered.splitlines()
        if line.startswith("Snippet: ")
    )
    return _response(
        json.dumps(
            {
                "claims": [
                    {
                        "claim_id": "claim-1",
                        "section": "summary",
                        "text": snippet,
                        "evidence_ids": [evidence_id],
                    }
                ]
            },
            ensure_ascii=False,
        )
    )


def test_primary_acceptance_enforces_twelve_attempts_and_three_zero_call_cases(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "unit-configured-key")
    report = asyncio.run(
        run_primary_acceptance(
            completion=_extractive_completion,
            state_path=tmp_path / "attempts.json",
            fixture_path=FIXTURE,
        )
    )

    assert report.result == "PASS"
    assert report.provider_attempts_this_run == 12
    assert report.provider_attempts_total == 12
    assert report.llm_succeeded_cases == 12
    assert report.critical_provider_attempts == 0
    assert report.critical_safe_failures == 0
    assert len(report.cases) == 15
    assert all(
        item.validation_result == "PASS" for item in report.cases
    )


def test_attempt_state_is_persistent_and_fails_closed(
    tmp_path: Path,
) -> None:
    state = tmp_path / "attempts.json"
    state.write_text(
        json.dumps(
            {
                "provider_attempt_limit": MAX_PROVIDER_ATTEMPTS,
                "provider_attempts": MAX_PROVIDER_ATTEMPTS,
            }
        ),
        encoding="utf-8",
    )
    counter = ProviderAttemptCounter(state)

    async def completion(**kwargs: Any) -> dict[str, Any]:
        del kwargs
        return _response('{"claims":[]}')

    wrapped = counter.wrap(completion)
    with pytest.raises(
        ServiceAcceptanceRunError,
        match="provider attempt limit exceeded",
    ):
        asyncio.run(
            wrapped(
                model="gemini/gemini-3.5-flash",
                reasoning_effort="minimal",
                max_tokens=4096,
                num_retries=0,
                timeout=10,
                api_key="configured",
            )
        )


def test_attempt_contract_rejects_retry_before_provider_call(
    tmp_path: Path,
) -> None:
    calls = 0

    async def completion(**kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        del kwargs
        calls += 1
        return _response('{"claims":[]}')

    counter = ProviderAttemptCounter(tmp_path / "attempts.json")
    wrapped = counter.wrap(completion)

    with pytest.raises(
        ServiceAcceptanceRunError,
        match="provider request contract is invalid",
    ):
        asyncio.run(
            wrapped(
                model="gemini/gemini-3.5-flash",
                reasoning_effort="minimal",
                max_tokens=4096,
                num_retries=1,
                timeout=10,
                api_key="configured",
            )
        )

    assert counter.attempts == 0
    assert calls == 0


def test_followup_runs_only_selected_noncritical_cases(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "unit-configured-key")
    state = tmp_path / "attempts.json"
    state.write_text(
        json.dumps(
            {
                "provider_attempt_limit": MAX_PROVIDER_ATTEMPTS,
                "provider_attempts": 12,
            }
        ),
        encoding="utf-8",
    )

    report = asyncio.run(
        run_followup_acceptance(
            completion=_extractive_completion,
            state_path=state,
            fixture_path=FIXTURE,
            case_ids=("FSC-02", "FSC-05"),
            required_llm_successes=2,
        )
    )

    assert report.result == "PASS"
    assert report.provider_attempts_before == 12
    assert report.provider_attempts_this_run == 2
    assert report.provider_attempts_total == 14
    assert report.selected_cases == 2
    assert report.llm_succeeded_cases == 2
    assert [item.case_id for item in report.cases] == [
        "FSC-02",
        "FSC-05",
    ]


def test_followup_stops_after_required_successes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "unit-configured-key")

    report = asyncio.run(
        run_followup_acceptance(
            completion=_extractive_completion,
            state_path=tmp_path / "attempts.json",
            fixture_path=FIXTURE,
            case_ids=("FSC-02", "FSC-05", "FSC-10"),
            required_llm_successes=1,
        )
    )

    assert report.result == "PASS"
    assert report.provider_attempts_this_run == 1
    assert report.provider_attempts_total == 1
    assert report.selected_cases == 1
    assert report.llm_succeeded_cases == 1
    assert [item.case_id for item in report.cases] == ["FSC-02"]


@pytest.mark.parametrize(
    "case_ids,required",
    [
        (("FSC-13",), 1),
        (("FSC-02", "FSC-02"), 1),
        (("FSC-99",), 1),
        (("FSC-02",), 0),
    ],
)
def test_followup_rejects_unsafe_selection_without_provider_call(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case_ids: tuple[str, ...],
    required: int,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "unit-configured-key")
    calls = 0

    async def completion(**kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return await _extractive_completion(**kwargs)

    with pytest.raises(
        ServiceAcceptanceRunError,
        match="follow-up acceptance selection is invalid",
    ):
        asyncio.run(
            run_followup_acceptance(
                completion=completion,
                state_path=tmp_path / "attempts.json",
                fixture_path=FIXTURE,
                case_ids=case_ids,
                required_llm_successes=required,
            )
        )

    assert calls == 0
