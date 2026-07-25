from __future__ import annotations

from scripts.m3_gate import CAPABILITIES, run_gate


def test_executable_m3_gate_runs_real_local_pipeline() -> None:
    report = run_gate()

    assert report.gate_passed is True
    assert report.total == 29
    assert report.passed == 25
    assert report.failed == 4
    assert report.percentage >= 80
    assert report.critical_percentage == 100
    assert report.critical_failed_case_ids == ()
    assert report.exposure_count == 0
    assert report.m3_12_status == "NOT_ACTIVATED"
    assert set(report.capabilities) == CAPABILITIES
    assert report.failed_case_ids == (
        "B0-09",
        "B0-10",
        "B0-12",
        "B0-17",
    )


def test_gate_keeps_runtime_status_families_and_ui_projection_visible() -> None:
    report = run_gate()
    results = {result.case_id: result for result in report.case_results}

    for case_id in (
        "B0-01",
        "B0-04",
        "B0-15",
        "B0-20",
        "B0-21",
        "B0-22",
        "B0-24",
        "B7-25",
        "B7-26",
        "B7-27",
        "B7-28",
    ):
        assert results[case_id].passed is True
    assert report.capabilities["UI01"].percentage == 100
    assert report.capabilities["A17-M"].percentage == 100
