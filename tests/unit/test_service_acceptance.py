from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from app.services.service_acceptance import (
    SERVICE_ACCEPTANCE_BASIS_AT,
    SERVICE_ACCEPTANCE_FIXTURE_ID,
    SERVICE_ACCEPTANCE_SCHEMA_VERSION,
    ServiceAcceptanceFixtureError,
    load_service_acceptance_fixture,
    validate_service_acceptance_fixture,
)
from app.services.service_snapshot import SERVICE_SNAPSHOT_ID

FIXTURE_PATH = Path("tests/fixtures/service_acceptance/fsc_v1.json")


def _payload() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_canonical_fsc_v1_fixture_has_exact_versioned_inventory() -> None:
    fixture = load_service_acceptance_fixture(FIXTURE_PATH)

    assert fixture.schema_version == SERVICE_ACCEPTANCE_SCHEMA_VERSION
    assert fixture.fixture_id == SERVICE_ACCEPTANCE_FIXTURE_ID
    assert fixture.snapshot_id == SERVICE_SNAPSHOT_ID
    assert fixture.basis_at == SERVICE_ACCEPTANCE_BASIS_AT
    assert len(fixture.cases) == 15
    assert [item.case_id for item in fixture.cases] == [
        f"FSC-{index:02d}" for index in range(1, 16)
    ]
    assert sum(item.llm_eligible for item in fixture.cases) == 12
    assert [item.case_id for item in fixture.cases if item.critical] == [
        "FSC-13",
        "FSC-14",
        "FSC-15",
    ]
    assert len({item.session_id for item in fixture.cases}) == 15


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.update(schema_version=True),
        lambda value: value.update(schema_version=2),
        lambda value: value.update(snapshot_id="other"),
        lambda value: value["cases"].pop(),
        lambda value: value["cases"].reverse(),
        lambda value: value["cases"][0].update(question="changed"),
        lambda value: value["cases"][0].update(session_id="shared"),
        lambda value: value["cases"][0].update(llm_eligible=1),
        lambda value: value["cases"][0].update(critical="false"),
        lambda value: value["cases"][0].update(required_sources=["market"]),
        lambda value: value["cases"][0].update(
            required_evidence_sources=["disclosure"]
        ),
        lambda value: value["cases"][0].update(allowed_statuses=[]),
        lambda value: value["cases"][0].update(forbidden_patterns=[]),
        lambda value: value["cases"][0].update(extra="not-allowed"),
    ],
)
def test_fixture_rejects_schema_and_inventory_drift(mutate) -> None:
    payload = copy.deepcopy(_payload())
    mutate(payload)

    with pytest.raises(
        ServiceAcceptanceFixtureError,
        match="service acceptance fixture",
    ):
        validate_service_acceptance_fixture(payload)


def test_fixture_loader_errors_are_typed_and_sanitized(tmp_path: Path) -> None:
    local_path = tmp_path / "private-invalid.json"
    local_path.write_text("{", encoding="utf-8")

    with pytest.raises(ServiceAcceptanceFixtureError) as exc_info:
        load_service_acceptance_fixture(local_path)

    rendered = str(exc_info.value)
    assert str(local_path) not in rendered
    assert "private-invalid" not in rendered


def test_fixture_return_is_immutable_and_detached_from_payload() -> None:
    payload = _payload()
    fixture = validate_service_acceptance_fixture(payload)
    payload["cases"][0]["question"] = "caller mutation"

    assert fixture.cases[0].question.startswith("삼성전자")
    with pytest.raises(AttributeError):
        fixture.cases[0].question = "mutation"  # type: ignore[misc]
