import json
import subprocess
from pathlib import Path

import pytest

from scripts import secret_scan

PLACEHOLDER_AND_REFERENCE_LINES = [
    "OPENDART_" + "API_KEY=\n",
    "NAVER_" + 'CLIENT_SECRET = ""\n',
    'value = os.getenv("OPENDART_API_KEY")\n',
    'value = os.environ["NAVER_CLIENT_ID"]\n',
    "api_key = ${OPENDART_API_KEY}\n",
    'url = "https://example.com/path?api-key=secret&ACCESS_TOKEN=secret"\n',
    'make_env("OPENDART_API_KEY", "secret")\n',
]


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_scan_detects_non_empty_credential_assignment_and_redacts_value(tmp_path):
    tracked = tmp_path / "settings.py"
    dangerous = "OPENDART_" + "API_KEY"
    write(tracked, f"{dangerous} = " + '"secret-value"\n')

    findings = secret_scan.scan_paths([tracked], repo_root=tmp_path)

    assert findings == [secret_scan.SecretFinding(path="settings.py", line=1, rule_id="non_empty_credential_assignment")]
    rendered = json.dumps([finding.__dict__ for finding in findings])
    assert "secret-value" not in rendered


@pytest.mark.parametrize("line", PLACEHOLDER_AND_REFERENCE_LINES)
def test_scan_allows_placeholders_runtime_reads_and_url_query_samples(tmp_path, line):
    path = tmp_path / "sample.py"
    write(path, line)

    assert secret_scan.scan_paths([path], repo_root=tmp_path) == []


@pytest.mark.parametrize(
    "key",
    ["api_key", "opendart_api_key", "client-secret", "x-api-key", "access%5Ftoken", "X-Amz-Signature"],
)
def test_scan_detects_generic_prefixed_and_encoded_direct_literal_assignments(tmp_path, key):
    path = tmp_path / f"{key.replace('%', '')}.toml"
    write(path, f"{key} = " + '"literal"\n')

    findings = secret_scan.scan_paths([path], repo_root=tmp_path)

    assert len(findings) == 1
    assert findings[0].rule_id == "non_empty_credential_assignment"


@pytest.mark.parametrize(
    ("relative_path", "content"),
    [
        (".env", "api_key=secret\n"),
        ("config.yaml", "client_secret: secret\n"),
        ("settings.ini", "access_token=tokenvalue\n"),
        ("module.py", "api_key = " + '"secret"\n'),
        ("config.json", '{"api_key":"secret","mode":"test"}\n'),
    ],
)
def test_file_aware_scanner_detects_direct_generic_credentials(tmp_path, relative_path, content):
    path = tmp_path / relative_path
    write(path, content)

    findings = secret_scan.scan_paths([path], repo_root=tmp_path)

    assert findings == [
        secret_scan.SecretFinding(
            path=Path(relative_path).as_posix(),
            line=1,
            rule_id="non_empty_credential_assignment",
        )
    ]


@pytest.mark.parametrize(
    ("relative_path", "content"),
    [
        ("module.py", "api_key = SECRET_FROM_RUNTIME\n"),
        ("module.py", 'api_key = os.getenv("API_KEY")\n'),
        ("module.py", 'api_key = os.environ["API_KEY"]\n'),
        (".env.example", "OPENDART_API_KEY=\n"),
        ("config.yaml", "client_secret: ${CLIENT_SECRET}\n"),
    ],
)
def test_file_aware_scanner_allows_runtime_references_and_empty_placeholders(tmp_path, relative_path, content):
    path = tmp_path / relative_path
    write(path, content)

    assert secret_scan.scan_paths([path], repo_root=tmp_path) == []


@pytest.mark.parametrize(
    "public_relative_path",
    [
        "README.md",
        ".env.example",
        "pyproject.toml",
        "data/public.json",
        ".github/workflows/ci.yml",
        ".github/workflows/ci.yaml",
    ],
)
@pytest.mark.parametrize(
    "unsafe_path",
    [
        "/mnt/data/secret",
        "/srv/app/config",
        "/usr/local/private",
        "/app/file",
        "/media/user/file",
        "/custom/root/file",
        "prefix /srv/app/config",
    ],
)
def test_public_path_rule_detects_general_posix_paths_on_public_surfaces(tmp_path, public_relative_path, unsafe_path):
    path = tmp_path / public_relative_path
    write(path, f"public text {unsafe_path}\n")

    findings = secret_scan.scan_paths([path], repo_root=tmp_path)

    assert findings == [
        secret_scan.SecretFinding(
            path=Path(public_relative_path).as_posix(),
            line=1,
            rule_id="public_absolute_path",
        )
    ]


@pytest.mark.parametrize(
    "allowed",
    [
        "/health",
        "GET /health",
        "`GET /health` reports fixture readiness",
        "http://127.0.0.1:8000/health",
        "https://example.com/path",
    ],
)
def test_public_path_rule_allows_route_tokens_and_urls(tmp_path, allowed):
    path = tmp_path / "README.md"
    write(path, f"{allowed}\n")

    assert secret_scan.scan_paths([path], repo_root=tmp_path) == []


def test_python_parse_failure_falls_back_to_line_based_credential_scan(tmp_path):
    path = tmp_path / "broken.py"
    write(path, 'api_key = "secret"\n\nif (\n')

    findings = secret_scan.scan_paths([path], repo_root=tmp_path)

    assert findings == [
        secret_scan.SecretFinding(path="broken.py", line=1, rule_id="non_empty_credential_assignment")
    ]


def test_python_mapping_exact_credential_key_literal_is_detected(tmp_path):
    path = tmp_path / "settings.py"
    write(
        path,
        "CONFIG = {\n"
        '    "OPENDART_API_KEY": "secret",\n'
        '    "NAVER_CLIENT_SECRET": "secret",\n'
        "}\n",
    )

    findings = secret_scan.scan_paths([path], repo_root=tmp_path)

    assert findings == [
        secret_scan.SecretFinding(path="settings.py", line=2, rule_id="non_empty_credential_assignment"),
        secret_scan.SecretFinding(path="settings.py", line=3, rule_id="non_empty_credential_assignment"),
    ]


def test_python_mapping_environment_reference_value_is_allowed(tmp_path):
    path = tmp_path / "settings.py"
    write(
        path,
        "import os\n"
        "CONFIG = {\n"
        '    "OPENDART_API_KEY": os.getenv("OPENDART_API_KEY"),\n'
        "}\n",
    )

    assert secret_scan.scan_paths([path], repo_root=tmp_path) == []


def test_scan_sorts_findings_and_uses_relative_paths(tmp_path):
    first = tmp_path / "b.py"
    second = tmp_path / "a.py"
    write(first, "api_key = " + '"one"\n')
    write(second, "client_secret = " + '"two"\n')

    findings = secret_scan.scan_paths([first, second], repo_root=tmp_path)

    assert [(finding.path, finding.line) for finding in findings] == [("a.py", 1), ("b.py", 1)]


def test_public_path_rule_only_checks_public_surfaces(tmp_path):
    readme = tmp_path / "README.md"
    validator = tmp_path / "app" / "validator.py"
    task_card = tmp_path / "docs" / "TASK_CARDS" / "internal.md"
    write(readme, "Do not expose /workspace/secret\n")
    write(validator, r"pattern = r'/workspace/[A-Za-z]+'\n")
    write(task_card, "Audit mentioned C:/Users/name/file.txt\n")

    findings = secret_scan.scan_paths([readme, validator, task_card], repo_root=tmp_path)

    assert findings == [secret_scan.SecretFinding(path="README.md", line=1, rule_id="public_absolute_path")]


def test_untracked_secret_file_is_ignored_by_tracked_file_listing(tmp_path):
    tracked = tmp_path / "tracked.py"
    untracked = tmp_path / "untracked.py"
    write(tracked, "SAFE = 1\n")
    write(untracked, "api_key = " + '"secret"\n')

    findings = secret_scan.scan_paths([tracked], repo_root=tmp_path)

    assert findings == []


def test_list_tracked_files_uses_git_nul_output_and_rejects_escape(monkeypatch, tmp_path):
    tracked = tmp_path / "tracked.py"
    write(tracked, "SAFE = 1\n")

    class Completed:
        returncode = 0
        stdout = b"tracked.py\0"

    monkeypatch.setattr(secret_scan.subprocess, "run", lambda *args, **kwargs: Completed())

    assert secret_scan.list_tracked_files(tmp_path) == (tracked.resolve(),)

    class BadCompleted:
        returncode = 0
        stdout = b"../outside.py\0"

    monkeypatch.setattr(secret_scan.subprocess, "run", lambda *args, **kwargs: BadCompleted())
    with pytest.raises(secret_scan.SecretScanError):
        secret_scan.list_tracked_files(tmp_path)


def test_git_failure_and_decode_failure_are_scanner_failures(monkeypatch, tmp_path):
    class Failed:
        returncode = 1
        stdout = b""

    monkeypatch.setattr(secret_scan.subprocess, "run", lambda *args, **kwargs: Failed())
    with pytest.raises(secret_scan.SecretScanError):
        secret_scan.list_tracked_files(tmp_path)

    class BadBytes:
        returncode = 0
        stdout = b"\xff\0"

    monkeypatch.setattr(secret_scan.subprocess, "run", lambda *args, **kwargs: BadBytes())
    with pytest.raises(secret_scan.SecretScanError):
        secret_scan.list_tracked_files(tmp_path)


def test_read_decode_failure_is_scanner_failure(tmp_path):
    path = tmp_path / "bad.py"
    path.write_bytes(b"\xff")

    with pytest.raises(secret_scan.SecretScanError):
        secret_scan.scan_paths([path], repo_root=tmp_path)


def test_main_returns_two_on_scanner_failure(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(secret_scan, "list_tracked_files", lambda _root: (_ for _ in ()).throw(secret_scan.SecretScanError("raw")))

    exit_code = secret_scan.main([str(tmp_path)])
    output = capsys.readouterr().out

    assert exit_code == 2
    assert "secret scan failed" in output
    assert "raw" not in output


def test_current_repository_scan_is_clean():
    repo_root = Path.cwd()
    findings = secret_scan.scan_paths(secret_scan.list_tracked_files(repo_root), repo_root=repo_root)

    assert findings == []
