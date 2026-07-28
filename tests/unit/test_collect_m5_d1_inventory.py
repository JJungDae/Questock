from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.services.m5_d1_inventory import (
    SECURITY_DART_IDENTITIES,
    M5D1InventoryError,
)
from scripts.collect_m5_d1_inventory import (
    OpenDartInventoryTransport,
    load_dart_inventory_from_raw,
    load_news_runs_from_raw,
)


def test_reused_news_raw_requires_complete_security_coverage(
    tmp_path: Path,
) -> None:
    for security_id in SECURITY_DART_IDENTITIES:
        safe_id = security_id.replace(":", "-")
        for query_index in range(1, 3):
            (tmp_path / f"{safe_id}-q{query_index}.json").write_text(
                json.dumps(
                    {
                        "security_id": security_id,
                        "query": f"query-{query_index}",
                        "pages": [
                            {
                                "items": [
                                    {
                                        "title": f"title-{query_index}",
                                    }
                                ]
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

    runs = load_news_runs_from_raw(
        tmp_path,
        expected_files_per_security=2,
    )

    assert len(runs) == 3
    assert all(run["api_call_count"] == 2 for run in runs)
    assert all(len(run["items"]) == 2 for run in runs)
    assert all(
        item["_questock_query_provenance"].endswith(
            "|reused_raw|start=1"
        )
        for run in runs
        for item in run["items"]
    )


def test_reused_news_raw_rejects_partial_collection(
    tmp_path: Path,
) -> None:
    (tmp_path / "KRX-005930-q1.json").write_text(
        json.dumps(
            {
                "security_id": "KRX:005930",
                "query": "삼성전자",
                "pages": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(M5D1InventoryError):
        load_news_runs_from_raw(
            tmp_path,
            expected_files_per_security=1,
        )


def test_opendart_list_query_is_type_bounded_and_collects_all_pages() -> None:
    transport = _FakeOpenDartTransport()

    pages = transport.disclosure_pages(
        corp_code="00126380",
        disclosure_type="I",
    )

    assert len(pages) == 2
    assert [call["page_no"] for call in transport.calls] == [1, 2]
    assert all(call["pblntf_ty"] == "I" for call in transport.calls)
    assert all(call["last_reprt_at"] == "N" for call in transport.calls)
    assert all("pblntf_detail_ty" not in call for call in transport.calls)


def test_reused_dart_raw_requires_filtered_query_coverage(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "dart"
    raw_dir.mkdir()
    corp_registry = {
        security_id: {
            "stock_code": stock_code,
            "corp_code": corp_code,
            "corp_name": name,
            "verification_status": "verified_official_api",
        }
        for security_id, (
            stock_code,
            corp_code,
            name,
        ) in SECURITY_DART_IDENTITIES.items()
    }
    inventory_path = tmp_path / "inventory.json"
    inventory_path.write_text(
        json.dumps(
            {
                "corp_registry": corp_registry,
                "provider_calls": {"naver": 1, "opendart": 16},
            }
        ),
        encoding="utf-8",
    )
    for _security_id, (
        stock_code,
        _corp_code,
        _name,
    ) in SECURITY_DART_IDENTITIES.items():
        for label in ("A", "B", "E", "I"):
            (raw_dir / f"KRX-{stock_code}-{label}-page-1.json").write_text(
                json.dumps({"status": "000", "list": []}),
                encoding="utf-8",
            )

    registry, disclosures, call_count = load_dart_inventory_from_raw(
        raw_dir,
        prior_inventory_path=inventory_path,
    )

    assert registry == corp_registry
    assert disclosures == {
        security_id: [] for security_id in SECURITY_DART_IDENTITIES
    }
    assert call_count == 16


class _FakeOpenDartTransport(OpenDartInventoryTransport):
    def __init__(self) -> None:
        super().__init__(api_key="test-only-placeholder")
        self.calls: list[dict[str, object]] = []

    def _request_json(
        self,
        endpoint: str,
        parameters: dict[str, object],
    ) -> dict[str, Any]:
        self.calls.append(dict(parameters))
        page_no = int(parameters["page_no"])
        return {
            "status": "000",
            "list": [{"rcept_no": f"2026072400000{page_no}"}],
            "total_page": 2,
        }
