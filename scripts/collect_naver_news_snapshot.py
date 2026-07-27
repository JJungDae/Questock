from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Protocol

from app.services.news_snapshot_schema import (
    NewsQuerySpec,
    NewsSearchQuery,
    NewsSnapshotConfig,
    NewsSnapshotValidationError,
    build_merged_news_candidate_payload,
    load_news_snapshot_config,
    write_utf8_json,
)

DEFAULT_CONFIG_PATH = Path("config/service_snapshot_news_queries.json")
DEFAULT_OUTPUT_DIR = Path("var/service_completion/news")
DEFAULT_RAW_DIR = Path("var/service_completion/raw/news")
FALLBACK_REQUIRED_EXIT = 3


class NewsCollectionError(ValueError):
    """Raised when the bounded NAVER collection call cannot complete."""


class NewsSearchTransport(Protocol):
    def search(
        self,
        *,
        query: str,
        display: int,
        start: int,
        sort: Literal["date", "sim"],
        timeout_seconds: float,
    ) -> dict[str, Any]: ...


class NaverApiHubNewsTransport:
    def __init__(
        self,
        *,
        endpoint: str,
        client_id: str,
        client_secret: str,
    ) -> None:
        if (
            not isinstance(endpoint, str)
            or not endpoint.startswith("https://")
            or not isinstance(client_id, str)
            or not client_id
            or not isinstance(client_secret, str)
            or not client_secret
        ):
            raise NewsCollectionError("news collection configuration is invalid")
        self._endpoint = endpoint
        self._client_id = client_id
        self._client_secret = client_secret

    def search(
        self,
        *,
        query: str,
        display: int,
        start: int,
        sort: Literal["date", "sim"],
        timeout_seconds: float,
    ) -> dict[str, Any]:
        request = build_naver_news_request(
            endpoint=self._endpoint,
            client_id=self._client_id,
            client_secret=self._client_secret,
            query=query,
            display=display,
            start=start,
            sort=sort,
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=timeout_seconds,
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError:
            raise NewsCollectionError("news collection request failed") from None
        except (urllib.error.URLError, TimeoutError):
            raise NewsCollectionError("news collection transport failed") from None
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise NewsCollectionError("news collection response is invalid") from None
        if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
            raise NewsCollectionError("news collection response is invalid")
        return payload


def build_naver_news_request(
    *,
    endpoint: str,
    client_id: str,
    client_secret: str,
    query: str,
    display: int,
    start: int,
    sort: Literal["date", "sim"],
) -> urllib.request.Request:
    if (
        not isinstance(query, str)
        or not query.strip()
        or not isinstance(display, int)
        or isinstance(display, bool)
        or display < 1
        or display > 100
        or not isinstance(start, int)
        or isinstance(start, bool)
        or start < 1
        or start > 1000
        or sort not in {"date", "sim"}
    ):
        raise NewsCollectionError("news collection request is invalid")
    parameters = urllib.parse.urlencode(
        {
            "query": query,
            "display": display,
            "start": start,
            "sort": sort,
            "format": "json",
        },
        encoding="utf-8",
        errors="strict",
    )
    return urllib.request.Request(
        f"{endpoint}?{parameters}",
        headers={
            "X-NCP-APIGW-API-KEY-ID": client_id,
            "X-NCP-APIGW-API-KEY": client_secret,
            "User-Agent": "Questock-FSC-News-Collector/1.0",
        },
        method="GET",
    )


def collect_news_pages(
    *,
    spec: NewsQuerySpec,
    config: NewsSnapshotConfig,
    transport: NewsSearchTransport,
) -> tuple[dict[str, Any], ...]:
    if (
        not isinstance(spec, NewsQuerySpec)
        or not isinstance(config, NewsSnapshotConfig)
    ):
        raise NewsCollectionError("news collection input is invalid")
    return collect_news_query_pages(
        query=spec.query,
        sort=spec.sort,
        display=config.display,
        max_calls=config.max_calls_per_security,
        timeout_seconds=config.timeout_seconds,
        transport=transport,
    )


def collect_news_query_pages(
    *,
    query: str,
    sort: Literal["date", "sim"],
    display: int,
    max_calls: int,
    timeout_seconds: float,
    transport: NewsSearchTransport,
) -> tuple[dict[str, Any], ...]:
    if (
        not isinstance(query, str)
        or not query.strip()
        or sort not in {"date", "sim"}
        or isinstance(display, bool)
        or not isinstance(display, int)
        or display < 1
        or display > 100
        or isinstance(max_calls, bool)
        or not isinstance(max_calls, int)
        or max_calls < 1
        or max_calls > 10
    ):
        raise NewsCollectionError("news collection input is invalid")
    pages: list[dict[str, Any]] = []
    for call_index in range(max_calls):
        start = 1 + call_index * display
        if start > 1000:
            break
        page = transport.search(
            query=query,
            display=display,
            start=start,
            sort=sort,
            timeout_seconds=timeout_seconds,
        )
        pages.append(dict(page))
        items = page.get("items")
        if not isinstance(items, list):
            raise NewsCollectionError("news collection response is invalid")
        if len(items) < display:
            break
    if not pages:
        raise NewsCollectionError("news collection returned no pages")
    return tuple(pages)


def run_collection(
    *,
    config_path: Path,
    output_dir: Path,
    raw_dir: Path,
    client_id: str,
    client_secret: str,
    collected_at: datetime | None = None,
) -> tuple[dict[str, Any], ...]:
    config = load_news_snapshot_config(config_path)
    transport = NaverApiHubNewsTransport(
        endpoint=config.endpoint,
        client_id=client_id,
        client_secret=client_secret,
    )
    collection_time = collected_at or datetime.now(UTC)
    summaries: list[dict[str, Any]] = []
    for spec in config.securities:
        base_pages = collect_news_pages(
            spec=spec,
            config=config,
            transport=transport,
        )
        query_runs: list[
            tuple[NewsSearchQuery, tuple[dict[str, Any], ...]]
        ] = [
            (NewsSearchQuery(spec.query, spec.sort), base_pages),
        ]
        for quality_query in spec.quality_queries:
            quality_pages = collect_news_query_pages(
                query=quality_query.query,
                sort=quality_query.sort,
                display=config.display,
                max_calls=config.max_calls_per_quality_query,
                timeout_seconds=config.timeout_seconds,
                transport=transport,
            )
            query_runs.append((quality_query, quality_pages))
        raw_payload = {
            "schema_version": "service-news-raw-v1",
            "snapshot_id": config.snapshot_id,
            "security_id": spec.security_id,
            "query_runs": [
                {
                    "query": query.query,
                    "sort": query.sort,
                    "pages": [dict(page) for page in pages],
                }
                for query, pages in query_runs
            ],
        }
        candidate_payload = build_merged_news_candidate_payload(
            spec=spec,
            query_runs=query_runs,
            collected_at=collection_time,
        )
        ticker = spec.security.ticker
        write_utf8_json(raw_dir / f"raw_news_{ticker}.json", raw_payload)
        write_utf8_json(
            output_dir / f"news_snapshot_candidates_{ticker}.json",
            candidate_payload,
        )
        coverage = candidate_payload["coverage"]
        retrieval_window = candidate_payload["retrieval_window"]
        rejection_reason = (
            "none"
            if coverage["ready"]
            else "automatic candidate coverage did not meet FSC-1 requirements"
        )
        _write_rejection_log(
            output_dir / f"news_rejection_log_{ticker}.md",
            security_id=spec.security_id,
            api_call_count=candidate_payload["api_call_count"],
            raw_item_count=retrieval_window["raw_item_count"],
            cutoff_window_item_count=(
                retrieval_window["cutoff_window_item_count"]
            ),
            candidate_count=coverage["total"],
            coverage_ready=coverage["ready"],
            reason=rejection_reason,
        )
        summaries.append(
            {
                "security_id": spec.security_id,
                "api_call_count": candidate_payload["api_call_count"],
                "raw_item_count": retrieval_window["raw_item_count"],
                "cutoff_window_item_count": (
                    retrieval_window["cutoff_window_item_count"]
                ),
                "candidate_count": coverage["total"],
                "pre_market_count": coverage["pre_market"],
                "intraday_count": coverage["intraday"],
                "coverage_ready": coverage["ready"],
            }
        )
    return tuple(summaries)


def build_collection_result(
    summaries: Sequence[dict[str, Any]],
) -> tuple[dict[str, Any], int]:
    if (
        isinstance(summaries, (str, bytes, bytearray))
        or not isinstance(summaries, Sequence)
        or not summaries
        or any(
            not isinstance(summary, dict)
            or not isinstance(summary.get("coverage_ready"), bool)
            for summary in summaries
        )
    ):
        raise NewsCollectionError("news collection result is invalid")
    ready = all(summary["coverage_ready"] for summary in summaries)
    payload: dict[str, Any] = {
        "status": "PASS" if ready else "INCOMPLETE",
        "results": [dict(summary) for summary in summaries],
    }
    if not ready:
        payload["reason"] = "fallback_required"
    return payload, 0 if ready else FALLBACK_REQUIRED_EXIT


def _write_rejection_log(
    path: Path,
    *,
    security_id: str,
    api_call_count: int,
    raw_item_count: int,
    cutoff_window_item_count: int,
    candidate_count: int,
    coverage_ready: bool,
    reason: str,
) -> None:
    status = "ready" if coverage_ready else "fallback_required"
    lines = [
        "# News Candidate Rejection Log",
        "",
        f"- security_id: `{security_id}`",
        f"- api_call_count: `{api_call_count}`",
        f"- raw_item_count: `{raw_item_count}`",
        f"- cutoff_window_item_count: `{cutoff_window_item_count}`",
        f"- candidate_count: `{candidate_count}`",
        f"- status: `{status}`",
        f"- reason: `{reason}`",
        "",
        "Article titles, descriptions, URLs, raw payloads, and credentials are "
        "not included.",
        "",
    ]
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    except OSError:
        raise NewsCollectionError("news rejection log could not be written") from None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect bounded NAVER API HUB news snapshot candidates.",
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    client_id = os.getenv("NAVER_CLIENT_ID", "")
    client_secret = os.getenv("NAVER_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        print(
            json.dumps(
                {
                    "status": "BLOCKED",
                    "reason": "credentials_not_configured",
                },
                sort_keys=True,
            )
        )
        return 2
    try:
        summaries = run_collection(
            config_path=args.config,
            output_dir=args.output_dir,
            raw_dir=args.raw_dir,
            client_id=client_id,
            client_secret=client_secret,
        )
    except (NewsCollectionError, NewsSnapshotValidationError):
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "reason": "collection_failed",
                },
                sort_keys=True,
            )
        )
        return 1
    try:
        result, exit_code = build_collection_result(summaries)
    except NewsCollectionError:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "reason": "collection_failed",
                },
                sort_keys=True,
            )
        )
        return 1
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
