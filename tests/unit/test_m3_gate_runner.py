from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.m3_gate import (
    CAPABILITIES,
    M3GateFixtureError,
    load_golden_cases,
    main,
    run_gate,
)


def test_golden_fixture_migrates_all_b0_cases_and_coverage_matrix() -> None:
    cases = load_golden_cases()

    assert len(cases) == 29
    assert [case.origin for case in cases if case.origin != "additional"] == [
        f"B0-{index:02d}" for index in range(1, 25)
    ]
    bucket_counts = {
        bucket: sum(case.bucket == bucket for case in cases)
        for bucket in {case.bucket for case in cases}
    }
    assert all(count >= 4 for count in bucket_counts.values())
    assert {
        capability
        for case in cases
        for capability in case.capabilities
    } == CAPABILITIES
    assert {
        case.coverage for case in cases if case.coverage is not None
    }.issuperset(
        {
            (security_id, source_type)
            for security_id in (
                "KRX:005930",
                "KRX:000660",
                "KRX:005380",
            )
            for source_type in (
                "news",
                "disclosure",
                "research_report",
            )
        }
    )


def test_gate_report_is_deterministic() -> None:
    first = run_gate().to_dict()
    second = run_gate().to_dict()

    assert first == second


def test_malformed_fixture_fails_with_typed_sanitized_error(
    tmp_path: Path,
) -> None:
    fixture = tmp_path / "malformed.json"
    fixture.write_text('{"schema_version": 1}', encoding="utf-8")

    with pytest.raises(M3GateFixtureError) as exc_info:
        load_golden_cases(fixture)

    assert str(exc_info.value) == "M3 gate fixture is invalid"
    assert str(fixture) not in str(exc_info.value)


def test_main_returns_two_without_raw_fixture_or_path(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fixture = tmp_path / "credential-sentinel.json"
    fixture.write_text("{", encoding="utf-8")

    exit_code = main(["--fixture", str(fixture)])
    output = capsys.readouterr().out

    assert exit_code == 2
    assert json.loads(output) == {
        "error": "M3 gate could not be evaluated"
    }
    assert "credential-sentinel" not in output
    assert str(tmp_path) not in output


def test_main_returns_zero_for_approved_local_gate(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main([])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["gate_passed"] is True
    assert output["percentage"] >= 80
    assert output["critical"]["percentage"] == 100

