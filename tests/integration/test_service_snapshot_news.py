from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from app.core.models import FinancialDocument
from app.services.news_snapshot_schema import (
    NEWS_CANDIDATE_SCHEMA_VERSION,
    NEWS_CURATED_SCHEMA_VERSION,
    SERVICE_SNAPSHOT_ID,
    NewsCurationError,
    NewsQuerySpec,
    build_curated_news_payload,
    calculate_news_coverage,
    load_news_snapshot_config,
)
from scripts.curate_news_snapshot import run_curation

CONFIG_PATH = Path("config/service_snapshot_news_queries.json")
SEOUL_TZ = timezone(timedelta(hours=9))
EVENTS = {
    "KRX:005930": (
        ("AI 공급 부족과 삼성전자", 7),
        ("삼성전자 실적 발표가 예정", 8),
        ("돌아온 외국인 반도체부터 샀다", 10),
        ("구글 AI 투자와 삼성전자", 11),
        ("아이폰 성장 사이클과 삼성전자", 12),
    ),
    "KRX:000660": (
        ("AI 공급 부족과 SK하이닉스", 8),
        ("반도체 피크아웃 우려와 돌아온 외인", 10),
        ("구글 AI 투자와 SK하이닉스", 11),
        ("개인과 외국인 엇갈린 베팅 SK하이닉스", 9),
        ("아이폰 성장 사이클과 SK하이닉스", 12),
    ),
    "KRX:005380": (
        ("현대차 2분기 부진", 8),
        ("현대차 파업 장기화와 생산 손실", 9),
        ("현대차 실적 부진에 하락세", 10),
        ("현대차 실적은 노이즈 CID 행사", 7),
        ("현대차 수소·로봇 특화 로봇 부품", 12),
    ),
}


def _document(
    spec: NewsQuerySpec,
    *,
    index: int,
    title: str,
    hour: int,
) -> FinancialDocument:
    published_at = datetime(2026, 7, 24, hour, 10, tzinfo=SEOUL_TZ)
    source_url = f"https://source-{index}.{spec.security.ticker}.example/news"
    return FinancialDocument(
        document_id=f"news:{spec.security.ticker}:{index}",
        source_type="news",
        provider="naver_api_hub_news",
        primary_security_ids=[spec.security_id],
        mentioned_security_ids=[],
        title=title,
        published_at=published_at.astimezone(UTC),
        source_url=source_url,
        text=f"{title}\nsynthetic metadata",
        locator={
            "provider": "naver_api_hub_news",
            "source_url": source_url,
            "published_at": published_at.astimezone(UTC).isoformat(),
            "raw_index": index,
            "query": spec.query,
        },
        metadata={"query": spec.query},
        ingestion_version="news-snapshot-fsc-v1",
    )


def _documents(spec: NewsQuerySpec) -> tuple[FinancialDocument, ...]:
    return tuple(
        _document(
            spec,
            index=index,
            title=title,
            hour=hour,
        )
        for index, (title, hour) in enumerate(
            EVENTS[spec.security_id],
            start=1,
        )
    )


def _candidate_payload(
    spec: NewsQuerySpec,
    documents: tuple[FinancialDocument, ...],
) -> dict[str, object]:
    coverage = calculate_news_coverage(
        documents,
        security_id=spec.security_id,
    )
    return {
        "schema_version": NEWS_CANDIDATE_SCHEMA_VERSION,
        "snapshot_id": SERVICE_SNAPSHOT_ID,
        "security_id": spec.security_id,
        "query": spec.query,
        "sort": spec.sort,
        "query_runs": [
            {
                "query": spec.query,
                "sort": spec.sort,
                "api_call_count": 1,
                "raw_item_count": len(documents),
                "cutoff_window_item_count": len(documents),
                "normalized_candidate_count": len(documents),
            }
        ],
        "collection_start": "2026-07-23T15:00:00Z",
        "collection_cutoff": "2026-07-24T05:00:00Z",
        "collected_at": "2026-07-27T03:00:00Z",
        "api_call_count": 1,
        "retrieval_window": {
            "raw_item_count": len(documents),
            "valid_published_at_count": len(documents),
            "invalid_published_at_count": 0,
            "cutoff_window_item_count": len(documents),
            "oldest_published_at": documents[0].published_at.isoformat(),
            "newest_published_at": documents[-1].published_at.isoformat(),
        },
        "coverage": {
            "total": coverage.total,
            "pre_market": coverage.pre_market,
            "intraday": coverage.intraday,
            "ready": coverage.ready,
        },
        "documents": [
            document.model_dump(mode="json")
            for document in documents
        ],
    }


def test_curated_output_is_exact_diverse_deterministic_and_body_free() -> None:
    config = load_news_snapshot_config(CONFIG_PATH)

    for spec in config.securities:
        documents = _documents(spec)
        first = build_curated_news_payload(
            documents,
            security_id=spec.security_id,
        )
        second = build_curated_news_payload(
            tuple(reversed(documents)),
            security_id=spec.security_id,
        )

        assert first == second
        assert first["schema_version"] == NEWS_CURATED_SCHEMA_VERSION
        assert first["summary_author"] == "Questock"
        assert first["coverage"]["total"] == 5
        assert first["coverage"]["pre_market"] >= 1
        assert first["coverage"]["intraday"] >= 2
        assert first["coverage"]["ready"] is True
        selected = first["documents"]
        assert len(selected) == 5
        assert len({item["document_id"] for item in selected}) == 5
        assert len(
            {
                item["source_locator"]["published_at"]
                for item in selected
            }
        ) == 5
        assert len(
            {
                urlsplit(item["source_locator"]["source_url"]).hostname
                for item in selected
            }
        ) == 5
        assert len({item["summary"] for item in selected}) == 5
        assert all(
            set(item) == {
                "document_id",
                "time_band",
                "source_locator",
                "summary",
            }
            for item in selected
        )
        assert all(
            set(item["source_locator"])
            == {"provider", "source_url", "published_at"}
            for item in selected
        )
        serialized = json.dumps(first, ensure_ascii=False)
        assert '"title"' not in serialized
        assert '"text"' not in serialized
        assert '"description"' not in serialized
        assert "synthetic metadata" not in serialized


def test_wrong_company_candidate_is_rejected() -> None:
    spec = load_news_snapshot_config(CONFIG_PATH).securities[0]
    documents = list(_documents(spec))
    documents[0] = documents[0].model_copy(
        update={"primary_security_ids": ["KRX:000660"]},
        deep=True,
    )

    with pytest.raises(NewsCurationError):
        build_curated_news_payload(
            documents,
            security_id=spec.security_id,
        )


def test_direct_title_match_wins_before_source_diversity() -> None:
    spec = load_news_snapshot_config(CONFIG_PATH).securities[0]
    documents = list(_documents(spec))
    documents[1] = documents[1].model_copy(
        update={
            "title": "삼성전자 전망",
            "text": "삼성전자 실적 발표가 예정된 전망 설명",
        },
        deep=True,
    )
    direct_match = _document(
        spec,
        index=6,
        title="삼성전자 실적 발표가 예정된 직접 보도",
        hour=8,
    )
    duplicate_url = (
        f"https://source-1.{spec.security.ticker}.example/duplicate-event"
    )
    direct_match = direct_match.model_copy(
        update={
            "source_url": duplicate_url,
            "locator": {
                **direct_match.locator,
                "source_url": duplicate_url,
            },
        },
        deep=True,
    )

    payload = build_curated_news_payload(
        [*documents, direct_match],
        security_id=spec.security_id,
    )

    assert len(payload["documents"]) == 5
    assert payload["documents"][1]["document_id"] == direct_match.document_id
    assert documents[1].document_id not in {
        item["document_id"] for item in payload["documents"]
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_url", None),
        (
            "published_at",
            datetime(2026, 7, 24, 14, 1, tzinfo=SEOUL_TZ).astimezone(UTC),
        ),
    ],
)
def test_missing_source_url_and_after_cutoff_candidate_are_rejected(
    field: str,
    value: object,
) -> None:
    spec = load_news_snapshot_config(CONFIG_PATH).securities[0]
    documents = list(_documents(spec))
    documents[0] = documents[0].model_copy(
        update={field: value},
        deep=True,
    )

    with pytest.raises(NewsCurationError):
        build_curated_news_payload(
            documents,
            security_id=spec.security_id,
        )


def test_run_curation_writes_byte_identical_three_company_outputs(
    tmp_path: Path,
) -> None:
    config = load_news_snapshot_config(CONFIG_PATH)
    input_dir = tmp_path / "input"
    first_output = tmp_path / "first"
    second_output = tmp_path / "second"
    input_dir.mkdir()
    for spec in config.securities:
        payload = _candidate_payload(spec, _documents(spec))
        (input_dir / f"news_snapshot_candidates_{spec.security.ticker}.json").write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )

    first_summary = run_curation(
        config_path=CONFIG_PATH,
        input_dir=input_dir,
        output_dir=first_output,
    )
    second_summary = run_curation(
        config_path=CONFIG_PATH,
        input_dir=input_dir,
        output_dir=second_output,
    )

    assert first_summary == second_summary
    assert all(item["selected_count"] == 5 for item in first_summary)
    assert all(item["source_host_count"] == 5 for item in first_summary)
    for spec in config.securities:
        name = f"news_snapshot_curated_{spec.security.ticker}.json"
        assert (first_output / name).read_bytes() == (
            second_output / name
        ).read_bytes()
        review_name = (
            f"news_snapshot_human_review_{spec.security.ticker}.md"
        )
        assert (first_output / review_name).read_bytes() == (
            second_output / review_name
        ).read_bytes()
        review_text = (first_output / review_name).read_text(encoding="utf-8")
        assert "Human Owner review pending" in review_text
        assert EVENTS[spec.security_id][0][0] in review_text
