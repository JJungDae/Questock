from __future__ import annotations

import asyncio
import json
from datetime import date
from pathlib import Path

import pytest

from app.planning.query_planner import QueryPlanner
from app.services.demo_source_gateway import (
    DemoCorpus,
    DemoCorpusValidationError,
    RecordedDemoSourceGateway,
    build_demo_corpus,
    load_demo_corpus,
)

MANIFEST_PATH = Path("data/demo/manifest.json")
DOCUMENTS_PATH = Path("data/demo/documents.json")


def _raw_corpus() -> tuple[dict[str, object], dict[str, object]]:
    return (
        json.loads(MANIFEST_PATH.read_text(encoding="utf-8")),
        json.loads(DOCUMENTS_PATH.read_text(encoding="utf-8")),
    )


def _plan(query: str):
    return QueryPlanner(basis_date=date(2026, 7, 26)).plan(query)


def test_load_demo_corpus_has_fixed_version_basis_and_origins() -> None:
    corpus = load_demo_corpus()

    assert corpus.corpus_type == "recorded_demo"
    assert corpus.schema_version == "b9-recorded-v1"
    assert corpus.basis_at.isoformat() == "2026-07-26T00:00:00+00:00"
    assert [item.source_type for item in corpus.documents] == [
        "news",
        "research_report",
        "disclosure",
    ]
    assert [
        item.metadata["content_origin"] for item in corpus.documents
    ] == [
        "synthetic_project_owned",
        "synthetic_project_owned",
        "verified_public_recorded",
    ]


@pytest.mark.parametrize(
    ("target", "mutation"),
    [
        ("manifest", lambda value: value.pop("basis_at")),
        (
            "manifest",
            lambda value: value.__setitem__(
                "schema_version",
                "future-version",
            ),
        ),
        (
            "manifest",
            lambda value: value["document_ids"].append(
                value["document_ids"][0]
            ),
        ),
        (
            "payload",
            lambda value: value.__setitem__("documents", "invalid"),
        ),
        (
            "payload",
            lambda value: value["documents"][0].__setitem__(
                "published_at",
                None,
            ),
        ),
        (
            "payload",
            lambda value: value["documents"][0]["metadata"].__setitem__(
                "content_origin",
                "verified_public_recorded",
            ),
        ),
    ],
)
def test_build_demo_corpus_rejects_malformed_data(
    target: str,
    mutation,
) -> None:
    manifest, payload = _raw_corpus()
    mutation(manifest if target == "manifest" else payload)

    with pytest.raises(DemoCorpusValidationError):
        build_demo_corpus(manifest, payload)


def test_loader_failure_is_typed_and_does_not_expose_path() -> None:
    sentinel = Path("data/demo/sentinel-private-demo.json")

    with pytest.raises(DemoCorpusValidationError) as exc_info:
        load_demo_corpus(sentinel, sentinel)

    assert str(sentinel) not in str(exc_info.value)
    assert "sentinel" not in str(exc_info.value)


def test_recorded_gateway_preserves_order_status_and_deep_copy() -> None:
    gateway = RecordedDemoSourceGateway(load_demo_corpus())
    plan = _plan("삼성전자 위험 요인 알려줘")

    first = asyncio.run(
        gateway.fetch(
            plan,
            query="삼성전자 위험 요인 알려줘",
            timeout_seconds=8,
        )
    )
    first.documents[0].metadata["mutated"] = True
    second = asyncio.run(
        gateway.fetch(
            plan,
            query="삼성전자 위험 요인 알려줘",
            timeout_seconds=8,
        )
    )

    assert tuple(first.provider_results_by_source) == tuple(
        plan.required_sources
    )
    assert [item.status for item in second.provider_results_by_source.values()] == [
        "ok",
        "ok",
        "ok",
    ]
    assert len(second.documents) == 3
    assert all("mutated" not in item.metadata for item in second.documents)
    assert second.data_mode == "recorded"
    assert second.live_connectivity_checked is False
    assert (
        second.documents[0].model_dump(mode="json")
        == load_demo_corpus().documents[0].model_dump(mode="json")
    )


def test_wrong_company_disclosure_is_no_data_without_receipt() -> None:
    gateway = RecordedDemoSourceGateway(load_demo_corpus())
    plan = _plan("SK하이닉스 최근 공시 요약")

    result = asyncio.run(
        gateway.fetch(
            plan,
            query="SK하이닉스 최근 공시 요약",
            timeout_seconds=8,
        )
    )

    assert result.documents == ()
    assert result.documents_by_id == {}
    assert result.provider_results_by_source["disclosure"].status == "no_data"
    assert "20260515002181" not in str(
        result.provider_results_by_source["disclosure"].model_dump(mode="json")
    )


def test_gateway_rejects_invalid_public_fetch_input() -> None:
    gateway = RecordedDemoSourceGateway(load_demo_corpus())
    plan = _plan("삼성전자 최근 뉴스")

    with pytest.raises(DemoCorpusValidationError):
        asyncio.run(
            gateway.fetch(
                plan,
                query=" ",
                timeout_seconds=8,
            )
        )


def test_gateway_rejects_direct_malformed_corpus_with_typed_error() -> None:
    valid = load_demo_corpus()
    malformed = DemoCorpus(
        corpus_type=valid.corpus_type,
        schema_version=valid.schema_version,
        basis_at=valid.basis_at,
        documents=(["invalid"],),  # type: ignore[arg-type]
    )

    with pytest.raises(DemoCorpusValidationError):
        RecordedDemoSourceGateway(malformed)
