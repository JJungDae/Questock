from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.services.m5_d1_evidence_comparison import (
    M5D1EvidenceComparisonStore,
)
from app.ui.projections import project_evidence_comparison
from scripts.evaluate_m5_d1_event_grouping import evaluate_event_pairs

SEOUL_TZ = ZoneInfo("Asia/Seoul")
ROOT = Path(__file__).resolve().parents[2]


def test_held_out_event_grouping_precision_gate() -> None:
    fixture = json.loads(
        (
            ROOT / "tests" / "fixtures" / "m5_d1_event_pairs.json"
        ).read_text(encoding="utf-8")
    )

    result = evaluate_event_pairs(fixture)

    assert result["evaluation_pair_count"] == 8
    assert result["precision"] >= 0.9
    assert result["false_positive"] == 0


def test_hbm5_comparison_is_temporal_and_lineage_conservative() -> None:
    store = M5D1EvidenceComparisonStore()
    cutoff = datetime(2026, 7, 27, 21, tzinfo=SEOUL_TZ)

    comparison = store.select(
        query="삼성전자 HBM5 2나노 이슈를 비교해줘",
        security_id="KRX:005930",
        as_of=cutoff,
    )

    assert comparison is not None
    assert "HBM5" in comparison.event_label
    assert comparison.common_facts == []
    assert (
        comparison.source_lineage_summary.confirmed_independent_count
        == 0
    )
    assert (
        comparison.source_lineage_summary.confirmed_republication_count
        == 0
    )
    assert comparison.source_lineage_summary.unknown_count == 27
    assert comparison.article_total_count == 27
    assert comparison.article_displayed_count == 20
    assert len(comparison.article_sources) == 20
    assert all(
        source.published_at <= cutoff
        for source in comparison.article_sources
    )
    assert comparison.different_interpretations
    assert all(
        item.source.source_type == "research_report"
        for item in comparison.different_interpretations
    )
    assert len(comparison.disclosure_links) == 1
    assert "HBM4" in comparison.disclosure_links[0].text
    assert "Tesla" not in comparison.disclosure_links[0].text
    view = project_evidence_comparison(comparison)
    assert view is not None
    assert view.article_count_text == "전체 27건 중 20건 표시"


def test_future_cluster_and_wrong_company_are_not_selected() -> None:
    store = M5D1EvidenceComparisonStore()

    before_event = store.select(
        query="삼성전자 HBM5 2나노 이슈",
        security_id="KRX:005930",
        as_of=datetime(2026, 7, 27, 10, tzinfo=SEOUL_TZ),
    )
    wrong_company = store.select(
        query="현대차 HBM5 2나노 이슈",
        security_id="KRX:005380",
        as_of=datetime(2026, 7, 27, 21, tzinfo=SEOUL_TZ),
    )
    unrelated_general_risk = store.select(
        query="삼성전자 위험요인을 알려줘",
        security_id="KRX:005930",
        as_of=datetime(2026, 7, 27, 21, tzinfo=SEOUL_TZ),
    )

    assert before_event is None
    assert wrong_company is None
    assert unrelated_general_risk is None


def test_public_sidecar_contains_all_verified_report_perspectives() -> None:
    payload = json.loads(
        (
            ROOT / "data" / "m5_d1_evidence_comparisons.json"
        ).read_text(encoding="utf-8")
    )

    assert payload["schema_version"] == "m5-d1-evidence-comparison-v2"
    assert len(payload["event_clusters"]) == 7
    assert sum(
        len(cluster["article_sources"])
        for cluster in payload["event_clusters"]
    ) == 43
    assert {
        cluster["security_id"]
        for cluster in payload["event_clusters"]
    } == {"KRX:005930", "KRX:005380"}
    assert all(
        cluster["security_match_basis"] == "title_alias_only"
        for cluster in payload["event_clusters"]
    )
    assert len(payload["report_perspectives"]) == 15
    assert {
        item["source"]["publisher"]
        for item in payload["report_perspectives"]
    } == {"삼성증권", "미래에셋증권", "키움증권"}
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "C:\\" not in serialized
    assert "page_text" not in serialized
    assert "api_key" not in serialized.casefold()


def test_event_links_require_event_specific_report_and_disclosure_topics() -> None:
    store = M5D1EvidenceComparisonStore()

    hyundai = store.select(
        query="현대차 왜 떨어졌어?",
        security_id="KRX:005380",
        as_of=datetime(2026, 7, 24, 19, tzinfo=SEOUL_TZ),
    )
    broadcom = store.select(
        query="삼성전자 브로드컴 협력 이슈",
        security_id="KRX:005930",
        as_of=datetime(2026, 7, 27, 21, tzinfo=SEOUL_TZ),
    )
    sk_hynix = store.select(
        query="SK하이닉스 최근 이슈 알려줘",
        security_id="KRX:000660",
        as_of=datetime(2026, 7, 27, 21, tzinfo=SEOUL_TZ),
    )

    assert hyundai is not None
    assert hyundai.different_interpretations
    assert any(
        item.source.title == "연결재무제표기준영업(잠정)실적(공정공시)"
        for item in hyundai.disclosure_links
        if item.source is not None
    )
    assert broadcom is not None
    assert broadcom.different_interpretations == []
    assert len(broadcom.disclosure_links) == 1
    assert broadcom.disclosure_links[0].role == "no_link"
    assert broadcom.disclosure_links[0].source is None
    assert sk_hynix is None


def test_cutoff_ranking_uses_latest_eligible_article(
    tmp_path: Path,
) -> None:
    payload = {
        "schema_version": "m5-d1-evidence-comparison-v2",
        "built_at": "2026-07-28T00:00:00Z",
        "source_inventory_sha256": "0" * 64,
        "report_inventory_sha256": "1" * 64,
        "event_clusters": [
            _cluster(
                event_id="event:future-tail",
                event_label="미래 기사 꼬리가 있는 사건",
                timestamps=(
                    "2026-07-27T01:00:00Z",
                    "2026-07-27T02:00:00Z",
                    "2026-07-27T09:00:00Z",
                ),
            ),
            _cluster(
                event_id="event:latest-eligible",
                event_label="기준시점 안의 최신 사건",
                timestamps=(
                    "2026-07-27T01:30:00Z",
                    "2026-07-27T02:30:00Z",
                ),
            ),
        ],
        "report_perspectives": [],
        "disclosure_backgrounds": [],
    }
    path = tmp_path / "comparison.json"
    path.write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )
    store = M5D1EvidenceComparisonStore(path)

    comparison = store.select(
        query="삼성전자 최근 이슈",
        security_id="KRX:005930",
        as_of=datetime(2026, 7, 27, 12, tzinfo=SEOUL_TZ),
    )

    assert comparison is not None
    assert comparison.event_id == "event:latest-eligible"


def _cluster(
    *,
    event_id: str,
    event_label: str,
    timestamps: tuple[str, ...],
) -> dict[str, object]:
    sources = [
        {
            "source_id": f"{event_id}:{index}",
            "source_type": "news",
            "title": f"{event_label} 기사 {index}",
            "publisher": f"publisher-{index}",
            "published_at": timestamp,
            "source_url": f"https://example.com/{event_id}/{index}",
        }
        for index, timestamp in enumerate(timestamps)
    ]
    return {
        "event_id": event_id,
        "security_id": "KRX:005930",
        "event_label": event_label,
        "event_terms": ["테스트사건"],
        "first_published_at": timestamps[0],
        "last_published_at": timestamps[-1],
        "article_sources": sources,
        "security_match_basis": "title_alias_only",
        "cluster_basis": "deterministic_title_similarity",
        "review_status": "conservative_automatic",
    }
