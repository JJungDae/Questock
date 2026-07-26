from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
CI_PATH = ROOT / ".github" / "workflows" / "ci.yml"
DEPLOY_PATH = ROOT / ".github" / "workflows" / "deploy-gce.yml"
DOCKERFILE_PATH = ROOT / "Dockerfile"
COMPOSE_PATH = ROOT / "compose.yaml"
DOCKERIGNORE_PATH = ROOT / ".dockerignore"
PYPROJECT_PATH = ROOT / "pyproject.toml"
LOCK_PATH = ROOT / "uv.lock"
ENV_EXAMPLE_PATH = ROOT / ".env.example"
DEMO_MANIFEST_PATH = ROOT / "data" / "demo" / "manifest.json"
MVP_RELEASE_PATH = ROOT / "docs" / "MVP_RELEASE.md"
DEMO_SCENARIOS_PATH = ROOT / "docs" / "DEMO_SCENARIOS.md"
TRACEABILITY_PATH = ROOT / "docs" / "P0_TRACEABILITY.md"

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
    assert "QUESTOCK_SOURCE_MODE: ${QUESTOCK_SOURCE_MODE:-recorded}" in compose
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


def test_gce_deploy_is_manual_exact_sha_recorded_and_scoped() -> None:
    workflow = _read(DEPLOY_PATH)

    assert "workflow_dispatch:" in workflow
    assert "release_sha:" in workflow
    assert "^[0-9a-f]{40}$" in workflow
    assert 'repo_dir="$HOME/Questock"' in workflow
    assert "git fetch origin main" in workflow
    assert "git cat-file -e" in workflow
    assert "git merge-base --is-ancestor" in workflow
    assert "git switch --detach" in workflow
    assert "QUESTOCK_SOURCE_MODE=recorded" in workflow
    assert "docker compose build --pull --no-cache" in workflow
    assert "docker compose up -d --wait" in workflow
    assert "docker compose exec -T api python -" in workflow
    assert "< scripts/release_smoke.py" in workflow
    assert "127.0.0.1:8000/health" in workflow
    assert "8501/_stcore/health" in workflow
    assert "rollback_release()" in workflow
    assert 'git switch --detach "$previous_sha"' in workflow
    assert "previous_image_id" in workflow
    assert "docker compose rm --stop --force" in workflow
    assert "rollback_result=failed" in workflow
    assert "push:" not in workflow
    assert "git reset" not in workflow
    assert "docker system prune" not in workflow
    assert "GEMINI_API_KEY" not in workflow
    assert "OPENDART_API_KEY" not in workflow


@pytest.mark.parametrize(
    "failure_stage",
    [
        "docker compose up -d --wait",
        "http://127.0.0.1:8000/health",
        "http://127.0.0.1:8501/_stcore/health",
        "docker compose exec -T api python -",
        '"http://$GCE_HOST:8501/_stcore/health"',
    ],
)
def test_each_deploy_failure_stage_is_inside_rollback_guard(
    failure_stage: str,
) -> None:
    workflow = _read(DEPLOY_PATH)
    guarded = workflow.split("deployment_failed=0", maxsplit=1)[1].split(
        'if [ "$deployment_failed" -ne 0 ]; then',
        maxsplit=1,
    )[0]
    failure_branch = workflow.split(
        'if [ "$deployment_failed" -ne 0 ]; then',
        maxsplit=1,
    )[1]

    assert failure_stage in guarded
    assert "deployment_failed=1" in guarded
    assert "rollback_release" in failure_branch
    assert "exit 1" in failure_branch


def test_remote_failure_cannot_be_masked_by_external_ui_health() -> None:
    workflow = _read(DEPLOY_PATH)
    deployment = workflow.split("deployment_failed=0", maxsplit=1)[1]
    remote, after_remote = deployment.split("REMOTE\n          then", maxsplit=1)
    external, failure_branch = after_remote.split(
        'if [ "$deployment_failed" -ne 0 ]; then',
        maxsplit=1,
    )

    assert "if ! ssh" in remote
    assert "deployment_failed=1" in after_remote
    assert 'if [ "$deployment_failed" -eq 0 ]; then' in external
    assert '"http://$GCE_HOST:8501/_stcore/health"' in external
    assert "deployment_failed=1" in external
    assert "rollback_release" in failure_branch
    assert "if ! (" not in deployment


def test_rollback_restores_previous_health_or_removes_failed_release() -> None:
    workflow = _read(DEPLOY_PATH)
    rollback = workflow.split("rollback_release() {", maxsplit=1)[1].split(
        "ROLLBACK\n          }",
        maxsplit=1,
    )[0]

    assert 'docker image inspect "$previous_image_id"' in rollback
    assert (
        'docker image tag "$previous_image_id" "questock:$previous_sha"'
        in rollback
    )
    assert 'git switch --detach "$previous_sha"' in rollback
    assert 'export QUESTOCK_IMAGE_TAG="$previous_sha"' in rollback
    assert "docker compose up -d --wait" in rollback
    assert "http://127.0.0.1:8000/health" in rollback
    assert "http://127.0.0.1:8501/_stcore/health" in rollback
    assert "docker compose rm --stop --force" in rollback
    assert "docker system prune" not in rollback


def test_deploy_preflight_fails_before_the_rollback_guard() -> None:
    workflow = _read(DEPLOY_PATH)
    preflight = workflow.split("rollback_release() {", maxsplit=1)[0]
    guarded = workflow.split("deployment_failed=0", maxsplit=1)[1]

    assert 'test -z "$(git status --porcelain)"' in preflight
    assert "git fetch origin main" in preflight
    assert "git cat-file -e" in preflight
    assert "git merge-base --is-ancestor" in preflight
    assert 'test -z "$(git status --porcelain)"' not in guarded
    assert "git fetch origin main" not in guarded


def test_previous_image_id_is_captured_before_build_and_used_for_rollback() -> None:
    workflow = _read(DEPLOY_PATH)
    pre_guard = workflow.split("deployment_failed=0", maxsplit=1)[0]
    guarded = workflow.split("deployment_failed=0", maxsplit=1)[1]

    assert "previous_image_id=\"$(" in pre_guard
    image_capture = pre_guard.split("<<'IMAGE_ID'", maxsplit=1)[1].split(
        "IMAGE_ID",
        maxsplit=1,
    )[0]
    assert 'if image_id="$(' in image_capture
    assert 'docker image inspect "questock:$previous_sha"' in image_capture
    assert 'printf \'%s\\n\' "$image_id"' in image_capture
    assert "printf 'NONE\\n'" in image_capture
    assert "|| printf 'NONE\\n'" not in image_capture
    assert "sha256:[0-9a-f]{64}" in pre_guard
    assert "'$previous_image_id'" in guarded
    assert (
        'docker image tag "$previous_image_id" "questock:$previous_sha"'
        in pre_guard
    )


def test_recorded_release_manifest_and_docs_are_versioned_and_truthful() -> None:
    manifest = json.loads(_read(DEMO_MANIFEST_PATH))
    env_example = _read(ENV_EXAMPLE_PATH)
    release = _read(MVP_RELEASE_PATH)
    scenarios = _read(DEMO_SCENARIOS_PATH)
    traceability = _read(TRACEABILITY_PATH)

    assert manifest == {
        "corpus_type": "recorded_demo",
        "schema_version": "b9-recorded-v1",
        "basis_at": "2026-07-26T00:00:00Z",
        "documents_file": "documents.json",
        "document_ids": [
            "demo:news:samsung-broadcom-20260725",
            "demo:research-report:samsung-1q26",
            "disclosure:20260515002181",
        ],
    }
    assert "QUESTOCK_SOURCE_MODE=" in env_example
    assert "QUESTOCK_IMAGE_TAG=" in env_example
    assert "Remote deployment | `NOT_RUN" in release
    assert "M4 Gate | `NOT_RUN`" in release
    assert "no live connectivity" in scenarios
    assert "Remote recorded deployment" in traceability
    assert "NOT_RUN" in traceability
