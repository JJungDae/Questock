from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.services.disclosure_snapshot_schema import DISCLOSURE_INPUT_SPECS
from app.services.report_snapshot_schema import REPORT_INPUT_SPECS
from app.services.service_snapshot import (
    SERVICE_SNAPSHOT_CHECKSUM_FILE,
    SERVICE_SNAPSHOT_COVERAGE_FILE,
    SERVICE_SNAPSHOT_DOCUMENTS_FILE,
    SERVICE_SNAPSHOT_ID,
    SERVICE_SNAPSHOT_PERMISSION_FILE,
    SERVICE_SNAPSHOT_VALIDATION_FILE,
    SnapshotSourcePayload,
    ServiceSnapshotValidationError,
    build_service_snapshot,
    build_service_snapshot_payloads,
    build_snapshot_checksum,
    build_snapshot_validation_report,
    load_snapshot_source,
    serialize_service_snapshot_json,
)

DEFAULT_INPUT_ROOT = Path("var/service_completion")
DEFAULT_OUTPUT_ROOT = Path("data/service_snapshot")


def run_build(
    *,
    input_root: Path = DEFAULT_INPUT_ROOT,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> dict[str, object]:
    if not isinstance(input_root, Path) or not isinstance(output_root, Path):
        raise ServiceSnapshotValidationError("snapshot build input is invalid")
    sources: list[SnapshotSourcePayload] = []
    for spec in REPORT_INPUT_SPECS:
        ticker = spec.ticker
        inputs = (
            (
                "news",
                input_root
                / "news"
                / "curated"
                / f"news_snapshot_curated_{ticker}.json",
            ),
            (
                "disclosure",
                input_root
                / "disclosure"
                / "curated"
                / f"disclosure_snapshot_curated_{ticker}.json",
            ),
            (
                "research_report",
                input_root
                / "reports"
                / "curated"
                / f"report_snapshot_curated_{ticker}.json",
            ),
        )
        for source_type, path in inputs:
            payload, sha256 = load_snapshot_source(path)
            sources.append(
                SnapshotSourcePayload(
                    source_type=source_type,
                    security_id=spec.security_id,
                    sha256=sha256,
                    payload=payload,
                )
            )
    if {item.security_id for item in sources} != {
        item.security_id for item in DISCLOSURE_INPUT_SPECS
    }:
        raise ServiceSnapshotValidationError("snapshot build input is invalid")
    (
        manifest,
        documents,
        coverage,
        permissions,
    ) = build_service_snapshot_payloads(sources)
    canonical_files = {
        "manifest.json": serialize_service_snapshot_json(manifest),
        SERVICE_SNAPSHOT_DOCUMENTS_FILE: serialize_service_snapshot_json(
            documents
        ),
        SERVICE_SNAPSHOT_COVERAGE_FILE: serialize_service_snapshot_json(
            coverage
        ),
        SERVICE_SNAPSHOT_PERMISSION_FILE: serialize_service_snapshot_json(
            permissions
        ),
    }
    snapshot = build_service_snapshot(
        manifest,
        documents,
        documents_bytes=canonical_files[SERVICE_SNAPSHOT_DOCUMENTS_FILE],
        coverage_payload=coverage,
        coverage_bytes=canonical_files[SERVICE_SNAPSHOT_COVERAGE_FILE],
        permission_payload=permissions,
        permission_bytes=canonical_files[SERVICE_SNAPSHOT_PERMISSION_FILE],
    )
    checksum_bytes = build_snapshot_checksum(canonical_files)
    validation_bytes = serialize_service_snapshot_json(
        build_snapshot_validation_report(snapshot)
    )
    output_dir = output_root / SERVICE_SNAPSHOT_ID
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        for name, raw in canonical_files.items():
            (output_dir / name).write_bytes(raw)
        (output_dir / SERVICE_SNAPSHOT_CHECKSUM_FILE).write_bytes(
            checksum_bytes
        )
        (output_dir / SERVICE_SNAPSHOT_VALIDATION_FILE).write_bytes(
            validation_bytes
        )
    except OSError:
        raise ServiceSnapshotValidationError(
            "snapshot output could not be written"
        ) from None
    return {
        "status": "PASS",
        "snapshot_id": SERVICE_SNAPSHOT_ID,
        "document_count": len(documents["documents"]),
        "news_document_count": coverage["coverage"]["news"][
            "document_count"
        ],
        "disclosure_document_count": coverage["coverage"]["disclosure"][
            "document_count"
        ],
        "report_count": coverage["coverage"]["research_report"][
            "report_count"
        ],
        "report_section_document_count": coverage["coverage"][
            "research_report"
        ]["section_document_count"],
        "documents_sha256": manifest["documents_sha256"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the immutable FSC recorded service snapshot.",
    )
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = run_build(
            input_root=args.input_root,
            output_root=args.output_root,
        )
    except ServiceSnapshotValidationError:
        print(json.dumps({"status": "FAIL", "reason": "snapshot_build_failed"}))
        return 1
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
