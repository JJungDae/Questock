from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.api.schemas import PublicGenerationSummary


ROOT = Path(__file__).resolve().parents[2]
CI_PATH = ROOT / ".github" / "workflows" / "ci.yml"
DEPLOY_PATH = ROOT / ".github" / "workflows" / "deploy-gce.yml"
COMPOSE_PATH = ROOT / "compose.yaml"

FOCUSED_TESTS = (
    "tests/unit/test_llm_config.py",
    "tests/unit/test_litellm_client.py",
    "tests/unit/test_request_protection.py",
    "tests/unit/test_session_store.py",
    "tests/unit/test_response_cache.py",
    "tests/unit/test_service_snapshot.py",
    "tests/unit/test_service_acceptance.py",
    "tests/unit/test_service_acceptance_live_runner.py",
    "tests/unit/test_b9_release_assets.py",
    "tests/unit/test_fsc_sc07_release_contract.py",
    "tests/integration/test_streamlit_app.py",
)
ACTIVE_RUNTIME_SETTINGS = (
    "QUESTOCK_SOURCE_MODE=recorded",
    "QUESTOCK_SNAPSHOT_ID=svc-20260724-1402",
    "QUESTOCK_LLM_MODE=gemini",
    "QUESTOCK_REQUEST_PROTECTION_ENABLED=true",
    "QUESTOCK_RESPONSE_CACHE_ENABLED=true",
    "LLM_MODEL=gemini/gemini-3.5-flash",
    "LLM_THINKING_LEVEL=minimal",
    "LLM_TIMEOUT_SECONDS=10",
    "LLM_MAX_OUTPUT_TOKENS=1024",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_public_generation_model_allowlist_is_exact() -> None:
    approved = PublicGenerationSummary(
        mode="llm",
        llm_status="ok",
        model="gemini/gemini-3.5-flash",
        live_verified=True,
    )

    assert approved.model == "gemini/gemini-3.5-flash"
    with pytest.raises(ValidationError):
        PublicGenerationSummary(
            mode="llm",
            llm_status="ok",
            model="gemini/gemini-2.5-flash",  # type: ignore[arg-type]
            live_verified=True,
        )


def test_ci_has_explicit_fsc_release_contract_gate() -> None:
    workflow = _read(CI_PATH)
    focused = workflow.split(
        "- name: FSC release contracts",
        maxsplit=1,
    )[1].split("- name: Full pytest", maxsplit=1)[0]

    assert "uv run --no-sync pytest" in focused
    for test_path in FOCUSED_TESTS:
        assert focused.count(test_path) == 1
    assert focused.rstrip().endswith("-q")


def test_gce_runtime_environment_has_exact_active_nonsecret_contract() -> None:
    workflow = _read(DEPLOY_PATH)
    install = workflow.split(
        "- name: Install API runtime environment",
        maxsplit=1,
    )[1].split("- name: Deploy and verify", maxsplit=1)[0]

    for setting in ACTIVE_RUNTIME_SETTINGS:
        assert install.count(setting) == 1
    assert "LLM_THINKING_BUDGET" not in install
    assert "thinking_budget" not in install
    assert "gemini-2.5" not in install
    assert "GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}" in install
    assert "printf 'GEMINI_API_KEY=%s\\n' \"$GEMINI_API_KEY\"" in install


def test_secret_and_joint_rollback_contract_remain_api_only() -> None:
    workflow = _read(DEPLOY_PATH)
    compose = _read(COMPOSE_PATH)
    api = compose.split("  api:", maxsplit=1)[1].split(
        "\n  ui:",
        maxsplit=1,
    )[0]
    ui = compose.split("\n  ui:", maxsplit=1)[1]
    rollback = workflow.split("rollback_release() {", maxsplit=1)[1].split(
        "ROLLBACK\n          }",
        maxsplit=1,
    )[0]

    assert "path: .env.runtime" in api
    assert ".env.runtime" not in ui
    assert "GEMINI_API_KEY" not in compose
    env_restore = rollback.index(
        "if [ -f .env.runtime.rollback ]; then"
    )
    image_restore = rollback.index(
        'if [ "$previous_image_id" != "NONE" ]'
    )
    assert env_restore < image_restore
    assert 'git switch --detach "$previous_sha"' in rollback
    assert 'export QUESTOCK_IMAGE_TAG="$previous_sha"' in rollback
    assert (
        'docker image tag "$previous_image_id" '
        '"questock:$previous_sha"'
    ) in rollback
