from __future__ import annotations

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CI_PATH = ROOT / ".github" / "workflows" / "ci.yml"
DOCKERFILE_PATH = ROOT / "Dockerfile"
COMPOSE_PATH = ROOT / "compose.yaml"
DOCKERIGNORE_PATH = ROOT / ".dockerignore"
PYPROJECT_PATH = ROOT / "pyproject.toml"
LOCK_PATH = ROOT / "uv.lock"

CHECKOUT_SHA = "de0fac2e4500dabe0009e67214ff5f5447ce83dd"
SETUP_UV_SHA = "08807647e7069bb48b6ef5acd8ec9567f424441b"
PYTHON_IMAGE_DIGEST = (
    "sha256:db3ff2e1800a8581e2c48a27c3995339d47bdf046da21c7627accd3d51053a93"
)
UV_IMAGE_DIGEST = (
    "sha256:df4cae8f3a96d175e2e5f992e597550000edbe78fdc2594d5cd8de1a217f504c"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_ci_uses_immutable_actions_and_exact_toolchain() -> None:
    workflow = _read(CI_PATH)

    assert "quality-gate:" in workflow
    assert "runs-on: ubuntu-24.04" in workflow
    assert f"actions/checkout@{CHECKOUT_SHA}" in workflow
    assert f"astral-sh/setup-uv@{SETUP_UV_SHA}" in workflow
    assert 'version: "0.11.32"' in workflow
    assert 'python-version: "3.11"' in workflow
    assert "permissions:\n  contents: read" in workflow
    assert "pull_request_target" not in workflow


def test_ci_runs_exact_install_and_required_quality_checks() -> None:
    workflow = _read(CI_PATH)

    assert "uv sync --locked --extra dev" in workflow
    assert "--all-extras" not in workflow
    assert "uv sync --locked --dev" not in workflow
    assert (
        "ruff check --select E4,E7,E9,F app tests scripts streamlit_app.py"
        in workflow
    )
    assert "pytest tests -q" in workflow
    assert "python scripts/m3_gate.py" in workflow
    assert "python scripts/secret_scan.py" in workflow
    assert "python -m compileall app tests scripts -q" in workflow
    assert "docker build --pull --tag questock:ci ." in workflow


def test_dev_extra_and_lock_contain_exact_ruff_version() -> None:
    pyproject = tomllib.loads(_read(PYPROJECT_PATH))
    dev = pyproject["project"]["optional-dependencies"]["dev"]
    lock = _read(LOCK_PATH)

    assert "ruff==0.15.22" in dev
    assert 'name = "ruff"' in lock
    assert 'version = "0.15.22"' in lock


def test_dockerfile_is_digest_pinned_locked_and_non_root() -> None:
    dockerfile = _read(DOCKERFILE_PATH)

    assert f"python:3.11-slim@{PYTHON_IMAGE_DIGEST}" in dockerfile
    assert f"ghcr.io/astral-sh/uv:0.11.32@{UV_IMAGE_DIGEST}" in dockerfile
    assert "uv sync --locked --no-dev --no-install-project" in dockerfile
    assert "--extra dev" not in dockerfile
    assert "--all-extras" not in dockerfile
    assert "USER questock" in dockerfile
    assert "USER root" not in dockerfile
    assert "--mount=type=secret" not in dockerfile
    for credential_name in (
        "GEMINI_API_KEY",
        "OPENDART_API_KEY",
        "NAVER_CLIENT_ID",
        "NAVER_CLIENT_SECRET",
    ):
        assert credential_name not in dockerfile


def test_compose_uses_one_image_and_safe_host_bindings() -> None:
    compose = _read(COMPOSE_PATH)

    assert "image: questock:${QUESTOCK_IMAGE_TAG:-b9-local}" in compose
    assert '"127.0.0.1:8000:8000"' in compose
    assert '"8501:8501"' in compose
    assert "QUESTOCK_API_URL: http://api:8000/api/chat" in compose
    assert "QUESTOCK_UI_TIMEOUT_SECONDS: \"21\"" in compose
    assert "QUESTOCK_SOURCE_MODE: ${QUESTOCK_SOURCE_MODE:-unconfigured}" in compose
    assert "API_BASE_URL" not in compose
    assert "GEMINI_API_KEY" not in compose
    assert "OPENDART_API_KEY" not in compose
    assert "NAVER_CLIENT_SECRET" not in compose
    assert "volumes:" not in compose


def test_dockerignore_excludes_local_and_secret_bearing_assets() -> None:
    patterns = {
        line.strip()
        for line in _read(DOCKERIGNORE_PATH).splitlines()
        if line.strip()
    }

    assert {
        ".git",
        ".env",
        ".env.*",
        ".venv",
        ".deps",
        ".tmp",
        ".b9-preflight-temp",
        "b7_review_bundle",
        "*.zip",
        "*.sha256",
        "tests",
        "docs",
    } <= patterns
