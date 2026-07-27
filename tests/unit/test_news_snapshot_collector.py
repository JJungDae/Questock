from __future__ import annotations

import json
import urllib.parse
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.services.news_snapshot_schema import (
    COLLECTION_CUTOFF,
    COLLECTION_START,
    NEWS_CANDIDATE_SCHEMA_VERSION,
    SERVICE_SNAPSHOT_ID,
    NewsSnapshotValidationError,
    build_news_candidate_payload,
    calculate_news_coverage,
    load_news_snapshot_config,
    normalize_collected_news_pages,
    summarize_collected_news_window,
    write_utf8_json,
)
from scripts.collect_naver_news_snapshot import (
    FALLBACK_REQUIRED_EXIT,
    NewsCollectionError,
    build_collection_result,
    build_naver_news_request,
    collect_news_pages,
    collect_news_query_pages,
)

CONFIG_PATH = Path("config/service_snapshot_news_queries.json")


def _item(
    title: str,
    *,
    pub_date: str,
    url: str,
    description: str = "",
) -> dict[str, str]:
    return {
        "title": title,
        "description": description,
        "pubDate": pub_date,
        "originallink": url,
        "link": url,
    }


def _page(items: list[dict[str, str]]) -> dict[str, object]:
    return {
        "lastBuildDate": "Mon, 27 Jul 2026 12:00:00 +0900",
        "total": len(items),
        "start": 1,
        "display": len(items),
        "items": items,
    }


def test_query_config_is_fixed_to_three_proven_utf8_queries_and_sorts() -> None:
    config = load_news_snapshot_config(CONFIG_PATH)

    assert config.snapshot_id == SERVICE_SNAPSHOT_ID
    assert config.display == 100
    assert config.max_calls_per_security == 10
    assert config.max_quality_queries_per_security == 3
    assert config.max_calls_per_quality_query == 2
    assert [spec.security_id for spec in config.securities] == [
        "KRX:005930",
        "KRX:000660",
        "KRX:005380",
    ]
    assert [spec.query for spec in config.securities] == [
        "삼성전자 2026년 7월 24일",
        "SK하이닉스 7월24일",
        "현대차 7월24일",
    ]
    assert [spec.sort for spec in config.securities] == ["date", "sim", "date"]
    assert [len(spec.quality_queries) for spec in config.securities] == [3, 3, 3]
    assert [
        item.query
        for item in config.securities[0].quality_queries
    ] == [
        "삼성전자 7월24일 실적 전망",
        "삼성전자 7월24일 반도체 수요 공급",
        "삼성전자 7월24일 HBM 투자",
    ]
    assert "삼성전자".encode("utf-8") in CONFIG_PATH.read_bytes()


def test_config_loader_failure_is_typed_and_sanitized(tmp_path: Path) -> None:
    sentinel = tmp_path / "private-sentinel.json"

    with pytest.raises(NewsSnapshotValidationError) as exc_info:
        load_news_snapshot_config(sentinel)

    assert "sentinel" not in str(exc_info.value)
    assert str(sentinel) not in str(exc_info.value)


def test_config_rejects_query_without_canonical_name_or_allowed_alias(
    tmp_path: Path,
) -> None:
    payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    payload["securities"][0]["query"] = "2026년 7월 24일"
    path = tmp_path / "queries.json"
    path.write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(NewsSnapshotValidationError):
        load_news_snapshot_config(path)


def test_config_rejects_unsupported_sort(tmp_path: Path) -> None:
    payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    payload["securities"][0]["sort"] = "recent"
    path = tmp_path / "queries.json"
    path.write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(NewsSnapshotValidationError):
        load_news_snapshot_config(path)


def test_config_rejects_quality_query_without_company_term(
    tmp_path: Path,
) -> None:
    payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    payload["securities"][0]["quality_queries"][0]["query"] = "실적 전망"
    path = tmp_path / "queries.json"
    path.write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(NewsSnapshotValidationError):
        load_news_snapshot_config(path)


def test_quality_query_call_limit_is_enforced() -> None:
    calls: list[int] = []

    class FakeTransport:
        def search(self, *, query, display, start, sort, timeout_seconds):
            calls.append(start)
            return _page(
                [
                    _item(
                        f"삼성전자 품질 후보 {start}",
                        pub_date="Fri, 24 Jul 2026 10:00:00 +0900",
                        url=f"https://news.example.com/{start}",
                    )
                    for _ in range(display)
                ]
            )

    pages = collect_news_query_pages(
        query="삼성전자 7월24일 실적 전망",
        sort="sim",
        display=2,
        max_calls=2,
        timeout_seconds=15,
        transport=FakeTransport(),
    )

    assert len(pages) == 2
    assert calls == [1, 3]


def test_request_uses_utf8_query_and_exact_api_hub_headers() -> None:
    request = build_naver_news_request(
        endpoint="https://naverapihub.apigw.ntruss.com/search/v1/news",
        client_id="client-id",
        client_secret="client-secret",
        query="SK하이닉스",
        display=100,
        start=1,
        sort="sim",
    )
    parsed = urllib.parse.urlsplit(request.full_url)
    query = urllib.parse.parse_qs(parsed.query, encoding="utf-8")

    assert query["query"] == ["SK하이닉스"]
    assert query["sort"] == ["sim"]
    assert request.get_header("X-ncp-apigw-api-key-id") == "client-id"
    assert request.get_header("X-ncp-apigw-api-key") == "client-secret"
    assert request.method == "GET"


def test_bounded_pagination_preserves_unicode_query_and_stops_on_short_page() -> None:
    config = load_news_snapshot_config(CONFIG_PATH)
    config = replace(config, display=2, max_calls_per_security=3)
    spec = config.securities[0]

    class FakeTransport:
        def __init__(self) -> None:
            self.calls: list[tuple[str, int, str]] = []

        def search(self, *, query, display, start, sort, timeout_seconds):
            self.calls.append((query, start, sort))
            count = 2 if start == 1 else 1
            return _page(
                [
                    _item(
                        f"삼성전자 item {start}-{index}",
                        pub_date="Fri, 24 Jul 2026 10:00:00 +0900",
                        url=f"https://news.example.com/{start}/{index}",
                    )
                    for index in range(count)
                ]
            )

    transport = FakeTransport()
    pages = collect_news_pages(
        spec=spec,
        config=config,
        transport=transport,
    )

    assert len(pages) == 2
    assert transport.calls == [
        ("삼성전자 2026년 7월 24일", 1, "date"),
        ("삼성전자 2026년 7월 24일", 3, "date"),
    ]


def test_normalizer_enforces_cutoff_attribution_dedupe_and_coverage() -> None:
    spec = load_news_snapshot_config(CONFIG_PATH).securities[0]
    items = [
        _item(
            "삼성전자 장전 1",
            pub_date="Fri, 24 Jul 2026 08:30:00 +0900",
            url="https://news.example.com/pre",
        ),
        _item(
            "삼성전자 장중 1",
            pub_date="Fri, 24 Jul 2026 09:00:00 +0900",
            url="https://news.example.com/a",
        ),
        _item(
            "삼성전자 장중 2",
            pub_date="Fri, 24 Jul 2026 10:00:00 +0900",
            url="https://news.example.com/b",
        ),
        _item(
            "삼성전자 장중 3",
            pub_date="Fri, 24 Jul 2026 12:00:00 +0900",
            url="https://news.example.com/c",
        ),
        _item(
            "삼성전자 cutoff",
            pub_date="Fri, 24 Jul 2026 14:00:00 +0900",
            url="https://news.example.com/d",
        ),
        _item(
            "삼성전자 duplicate",
            pub_date="Fri, 24 Jul 2026 13:00:00 +0900",
            url="https://news.example.com/d#fragment",
        ),
        _item(
            "삼성전자 after cutoff",
            pub_date="Fri, 24 Jul 2026 14:01:00 +0900",
            url="https://news.example.com/after",
        ),
        _item(
            "SK하이닉스 wrong company",
            description="삼성전자는 description에만 언급",
            pub_date="Fri, 24 Jul 2026 11:00:00 +0900",
            url="https://news.example.com/wrong",
        ),
    ]

    documents = normalize_collected_news_pages([_page(items)], spec=spec)
    coverage = calculate_news_coverage(
        documents,
        security_id=spec.security_id,
    )

    assert len(documents) == 5
    assert coverage.total == 5
    assert coverage.pre_market == 1
    assert coverage.intraday == 4
    assert coverage.ready is True
    assert all(
        COLLECTION_START
        <= document.published_at.astimezone(COLLECTION_START.tzinfo)
        <= COLLECTION_CUTOFF
        for document in documents
        if document.published_at is not None
    )
    assert all("wrong" not in document.source_url for document in documents)


def test_candidate_payload_is_deterministic_and_does_not_claim_raw_coverage() -> None:
    spec = load_news_snapshot_config(CONFIG_PATH).securities[0]
    page = _page(
        [
            _item(
                "삼성전자 candidate",
                pub_date="Fri, 24 Jul 2026 10:00:00 +0900",
                url="https://news.example.com/candidate",
            )
        ]
    )
    collected_at = datetime(2026, 7, 27, 3, 0, tzinfo=UTC)

    first = build_news_candidate_payload(
        spec=spec,
        pages=[page],
        collected_at=collected_at,
    )
    second = build_news_candidate_payload(
        spec=spec,
        pages=[page],
        collected_at=collected_at,
    )

    assert first == second
    assert first["schema_version"] == NEWS_CANDIDATE_SCHEMA_VERSION
    assert first["coverage"] == {
        "total": 1,
        "pre_market": 0,
        "intraday": 1,
        "ready": False,
    }
    assert first["retrieval_window"]["raw_item_count"] == 1
    assert first["retrieval_window"]["cutoff_window_item_count"] == 1
    assert first["query_runs"] == [
        {
            "query": spec.query,
            "sort": spec.sort,
            "api_call_count": 1,
            "raw_item_count": 1,
            "cutoff_window_item_count": 1,
            "normalized_candidate_count": 1,
        }
    ]


def test_collection_window_reports_bounded_history_without_exposing_items() -> None:
    pages = [
        _page(
            [
                _item(
                    "삼성전자 current",
                    pub_date="Mon, 27 Jul 2026 10:00:00 +0900",
                    url="https://news.example.com/current",
                ),
                _item(
                    "삼성전자 cutoff",
                    pub_date="Fri, 24 Jul 2026 08:30:00 +0900",
                    url="https://news.example.com/cutoff",
                ),
            ]
        )
    ]

    window = summarize_collected_news_window(pages)

    assert window.raw_item_count == 2
    assert window.valid_published_at_count == 2
    assert window.invalid_published_at_count == 0
    assert window.cutoff_window_item_count == 1
    assert window.oldest_published_at == datetime(
        2026, 7, 23, 23, 30, tzinfo=UTC
    )
    assert window.newest_published_at == datetime(
        2026, 7, 27, 1, 0, tzinfo=UTC
    )


def test_incomplete_coverage_requires_fallback_instead_of_claiming_pass() -> None:
    payload, exit_code = build_collection_result(
        [
            {
                "security_id": "KRX:005930",
                "coverage_ready": False,
            }
        ]
    )

    assert exit_code == FALLBACK_REQUIRED_EXIT
    assert payload == {
        "status": "INCOMPLETE",
        "reason": "fallback_required",
        "results": [
            {
                "security_id": "KRX:005930",
                "coverage_ready": False,
            }
        ],
    }


def test_complete_coverage_is_the_only_pass_result() -> None:
    payload, exit_code = build_collection_result(
        [
            {
                "security_id": "KRX:005930",
                "coverage_ready": True,
            }
        ]
    )

    assert exit_code == 0
    assert payload["status"] == "PASS"
    assert "reason" not in payload


def test_utf8_writer_uses_no_bom_and_one_final_newline(tmp_path: Path) -> None:
    output = tmp_path / "후보.json"
    write_utf8_json(output, {"query": "현대자동차"})

    raw = output.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert raw.endswith(b"\n")
    assert not raw.endswith(b"\n\n")
    assert "현대자동차" in raw.decode("utf-8")


@pytest.mark.parametrize(
    "query",
    ["", " ", None],
)
def test_request_rejects_invalid_query_without_raw_value(query) -> None:
    with pytest.raises(NewsCollectionError) as exc_info:
        build_naver_news_request(
            endpoint="https://naverapihub.apigw.ntruss.com/search/v1/news",
            client_id="client-id",
            client_secret="client-secret",
            query=query,
            display=10,
            start=1,
            sort="date",
        )

    assert "client-secret" not in str(exc_info.value)
