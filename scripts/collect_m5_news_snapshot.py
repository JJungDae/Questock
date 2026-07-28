from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.services.m5_news_snapshot import (
    M5_NEWS_PATH,
    SECURITY_TERMS,
    M5NewsSnapshotError,
    build_m5_news_payload,
    curate_m5_news_items,
    load_m5_news_documents,
)
from scripts.collect_naver_news_snapshot import (
    NaverApiHubNewsTransport,
    NewsCollectionError,
    collect_news_query_pages,
)

DEFAULT_RAW_DIR = Path("var/service_completion/raw/news/m5")
NAVER_ENDPOINT = (
    "https://naverapihub.apigw.ntruss.com/search/v1/news"
)
COLLECTION_DATES = (
    "2026년 7월 24일",
    "2026년 7월 25일",
    "2026년 7월 26일",
    "2026년 7월 27일",
)
QUALITY_TERMS = {
    "KRX:005930": "반도체 HBM 수주 공급 실적",
    "KRX:000660": "HBM 실적 공급 투자 지분",
    "KRX:005380": "실적 생산 전기차 판매 AI",
}


def collect_m5_news(
    *,
    transport: NaverApiHubNewsTransport,
    raw_dir: Path,
) -> tuple[dict[str, Any], ...]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    output: list[dict[str, Any]] = []
    for security_id, (security_name, _aliases) in SECURITY_TERMS.items():
        items: list[dict[str, Any]] = []
        for day in COLLECTION_DATES:
            queries = (
                f"{security_name} {day}",
                (
                    f"{security_name} {QUALITY_TERMS[security_id]} "
                    f"{day}"
                ),
            )
            for query_index, query in enumerate(queries, start=1):
                pages = collect_news_query_pages(
                    query=query,
                    sort="date",
                    display=100,
                    max_calls=2,
                    timeout_seconds=15,
                    transport=transport,
                )
                safe_id = security_id.replace(":", "-")
                raw_path = raw_dir / (
                    f"{safe_id}-{day.replace(' ', '-')}"
                    f"-q{query_index}.json"
                )
                raw_path.write_text(
                    json.dumps(
                        {
                            "security_id": security_id,
                            "query": query,
                            "pages": pages,
                        },
                        ensure_ascii=False,
                        indent=2,
                        sort_keys=True,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                for page in pages:
                    raw_items = page.get("items")
                    if isinstance(raw_items, list):
                        items.extend(
                            item
                            for item in raw_items
                            if isinstance(item, dict)
                        )
        output.append(
            {
                "security_id": security_id,
                "items": items,
            }
        )
    return tuple(output)


def _dotenv(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        raise NewsCollectionError(
            "news credential file is unavailable"
        ) from None
    output: dict[str, str] = {}
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            output[key.strip()] = value.strip()
    return output


def _credential(
    name: str,
    dotenv: dict[str, str],
) -> str:
    value = os.getenv(name) or dotenv.get(name)
    if not isinstance(value, str) or not value.strip():
        raise NewsCollectionError(
            "news credentials are not configured"
        )
    return value.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--output", type=Path, default=M5_NEWS_PATH)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    arguments = parser.parse_args(argv)
    try:
        dotenv = _dotenv(arguments.env_file)
        transport = NaverApiHubNewsTransport(
            endpoint=NAVER_ENDPOINT,
            client_id=_credential("NAVER_CLIENT_ID", dotenv),
            client_secret=_credential("NAVER_CLIENT_SECRET", dotenv),
        )
        runs = collect_m5_news(
            transport=transport,
            raw_dir=arguments.raw_dir,
        )
        raw_items_by_security = {
            run["security_id"]: run["items"]
            for run in runs
        }
        documents = curate_m5_news_items(
            raw_items_by_security,
        )
        payload = build_m5_news_payload(
            documents,
            collected_at=datetime.now(UTC),
        )
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        load_m5_news_documents(arguments.output)
    except (NewsCollectionError, M5NewsSnapshotError, OSError):
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "reason": "m5_news_collection_failed",
                },
                separators=(",", ":"),
            )
        )
        return 1
    print(
        json.dumps(
            {
                "status": "PASS",
                "counts_by_security": payload[
                    "counts_by_security"
                ],
                "document_count": len(documents),
                "checksum": payload["documents_sha256"],
            },
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
