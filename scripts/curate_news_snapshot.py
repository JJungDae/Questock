from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from app.services.news_snapshot_schema import (
    NewsCurationError,
    NewsSnapshotValidationError,
    build_curated_news_payload,
    load_news_candidate_documents,
    load_news_snapshot_config,
    write_utf8_json,
)

DEFAULT_CONFIG_PATH = Path("config/service_snapshot_news_queries.json")
DEFAULT_INPUT_DIR = Path("var/service_completion/news")
DEFAULT_OUTPUT_DIR = Path("var/service_completion/news/curated")


def run_curation(
    *,
    config_path: Path,
    input_dir: Path,
    output_dir: Path,
) -> tuple[dict[str, Any], ...]:
    config = load_news_snapshot_config(config_path)
    summaries: list[dict[str, Any]] = []
    for spec in config.securities:
        ticker = spec.security.ticker
        documents = load_news_candidate_documents(
            input_dir / f"news_snapshot_candidates_{ticker}.json",
            spec=spec,
        )
        payload = build_curated_news_payload(
            documents,
            security_id=spec.security_id,
        )
        write_utf8_json(
            output_dir / f"news_snapshot_curated_{ticker}.json",
            payload,
        )
        _write_human_review_crosswalk(
            output_dir / f"news_snapshot_human_review_{ticker}.md",
            payload=payload,
            documents=documents,
            security_id=spec.security_id,
        )
        coverage = payload["coverage"]
        source_hosts = {
            _safe_source_host(item["source_locator"]["source_url"])
            for item in payload["documents"]
        }
        summaries.append(
            {
                "security_id": spec.security_id,
                "selected_count": coverage["total"],
                "pre_market_count": coverage["pre_market"],
                "intraday_count": coverage["intraday"],
                "source_host_count": len(source_hosts),
                "coverage_ready": coverage["ready"],
            }
        )
    return tuple(summaries)


def _safe_source_host(source_url: object) -> str:
    if not isinstance(source_url, str):
        raise NewsCurationError("news curation output is invalid")
    try:
        host = urlsplit(source_url).hostname
    except ValueError:
        raise NewsCurationError("news curation output is invalid") from None
    if host is None:
        raise NewsCurationError("news curation output is invalid")
    return host.lower()


def _write_human_review_crosswalk(
    path: Path,
    *,
    payload: dict[str, Any],
    documents: Sequence[Any],
    security_id: str,
) -> None:
    documents_by_id = {
        document.document_id: document
        for document in documents
    }
    lines = [
        "# News Snapshot Human Review",
        "",
        f"- security_id: `{security_id}`",
        "- status: `Human Owner review pending`",
        "- scope: `Git ignored review artifact; not runtime input`",
        "",
        "| document_id | published_at | title | source_url |",
        "|---|---|---|---|",
    ]
    for selected in payload["documents"]:
        document = documents_by_id.get(selected["document_id"])
        if (
            document is None
            or document.published_at is None
            or document.source_url is None
        ):
            raise NewsCurationError("news curation output is invalid")
        title = document.title.replace("|", "\\|").replace("\n", " ")
        source_url = document.source_url.replace("|", "%7C")
        lines.append(
            f"| `{document.document_id}` | "
            f"`{document.published_at.isoformat()}` | "
            f"{title} | {source_url} |"
        )
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    except OSError:
        raise NewsCurationError(
            "news human review output could not be written"
        ) from None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Curate deterministic FSC news snapshot inputs.",
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summaries = run_curation(
            config_path=args.config,
            input_dir=args.input_dir,
            output_dir=args.output_dir,
        )
    except (NewsCurationError, NewsSnapshotValidationError):
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "reason": "curation_failed",
                },
                sort_keys=True,
            )
        )
        return 1
    print(
        json.dumps(
            {
                "status": "PASS",
                "results": list(summaries),
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
