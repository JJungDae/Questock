import json

from scripts import m1_phase_slice

SENTINEL = "SENTINEL_SECRET_DO_NOT_LEAK"


def _payload(status):
    return {
        "status": status,
        "version": "m1-08",
        "mode": "fixture_readiness",
        "live_connectivity_checked": False,
    }


def _assert_json_output(captured, *, expected_status):
    assert captured.err == ""
    body = json.loads(captured.out)
    rendered = json.dumps(body, ensure_ascii=False)
    assert body["status"] == expected_status
    assert "Traceback" not in rendered
    assert "RuntimeError" not in rendered
    assert SENTINEL not in rendered
    assert "C:/Users" not in rendered
    assert "/workspace" not in rendered
    return body


def test_cli_ok_exit_zero(monkeypatch, capsys):
    async def fake_builder():
        return _payload("ok")

    monkeypatch.setattr(m1_phase_slice, "build_health_payload", fake_builder)

    exit_code = m1_phase_slice.main([])

    assert exit_code == 0
    _assert_json_output(capsys.readouterr(), expected_status="ok")


def test_cli_degraded_exit_one(monkeypatch, capsys):
    async def fake_builder():
        return _payload("degraded")

    monkeypatch.setattr(m1_phase_slice, "build_health_payload", fake_builder)

    exit_code = m1_phase_slice.main([])

    assert exit_code == 1
    _assert_json_output(capsys.readouterr(), expected_status="degraded")


def test_cli_error_exit_two(monkeypatch, capsys):
    async def fake_builder():
        return _payload("error")

    monkeypatch.setattr(m1_phase_slice, "build_health_payload", fake_builder)

    exit_code = m1_phase_slice.main([])

    assert exit_code == 2
    _assert_json_output(capsys.readouterr(), expected_status="error")


def test_cli_builder_exception_is_sanitized_json_error(monkeypatch, capsys):
    async def fake_builder():
        raise RuntimeError(f"raw {SENTINEL} C:/Users/name/secret")

    monkeypatch.setattr(m1_phase_slice, "build_health_payload", fake_builder)

    exit_code = m1_phase_slice.main([])

    assert exit_code == 2
    _assert_json_output(capsys.readouterr(), expected_status="error")


def test_cli_rejects_arbitrary_arguments_without_echoing_them(capsys):
    exit_code = m1_phase_slice.main(["--query", "SK\ud558\uc774\ub2c9\uc2a4"])
    captured = capsys.readouterr()
    body = _assert_json_output(captured, expected_status="error")

    assert exit_code == 2
    assert "SK\ud558\uc774\ub2c9\uc2a4" not in captured.out
    assert "--query" not in captured.out
    assert body["phase_slice"]["status"] == "error"
