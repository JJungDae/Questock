from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from app.services.report_snapshot_schema import (
    REPORT_INPUT_SPECS,
    ReportInputSpec,
    ReportSnapshotValidationError,
    build_report_snapshot_payload,
    file_sha256,
    load_report_extract,
    validate_report_snapshot_payload,
    write_report_snapshot_json,
)

DEFAULT_SOURCE_PDF_DIR = Path("var/service_completion/reports/source")
DEFAULT_OUTPUT_DIR = Path("var/service_completion/reports/curated")
_PAGES_RE = re.compile(r"^Pages:\s*(\d+)\s*$", re.MULTILINE)


class ReportSnapshotCurationError(ValueError):
    """Raised when local report curation cannot complete safely."""


def read_pdf_page_count(
    path: Path,
    *,
    executable: str = "pdfinfo",
) -> int:
    if (
        not isinstance(path, Path)
        or not isinstance(executable, str)
        or not executable.strip()
    ):
        raise ReportSnapshotCurationError("report PDF inspection failed")
    try:
        completed = subprocess.run(
            [executable, str(path)],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise ReportSnapshotCurationError(
            "report PDF inspection failed"
        ) from None
    match = _PAGES_RE.search(completed.stdout)
    if completed.returncode != 0 or match is None:
        raise ReportSnapshotCurationError("report PDF inspection failed")
    return int(match.group(1))


def run_curation(
    *,
    input_dirs: Mapping[str, Path],
    source_pdf_dir: Path,
    output_dir: Path,
    page_counter: Callable[[Path], int] = read_pdf_page_count,
    specs: Sequence[ReportInputSpec] = REPORT_INPUT_SPECS,
) -> tuple[dict[str, Any], ...]:
    if (
        not isinstance(input_dirs, Mapping)
        or not isinstance(source_pdf_dir, Path)
        or not isinstance(output_dir, Path)
        or not callable(page_counter)
        or isinstance(specs, (str, bytes, bytearray))
        or not isinstance(specs, Sequence)
        or not specs
    ):
        raise ReportSnapshotCurationError(
            "report curation input is invalid"
        )
    summaries: list[dict[str, Any]] = []
    for spec in specs:
        if not isinstance(spec, ReportInputSpec):
            raise ReportSnapshotCurationError(
                "report curation input is invalid"
            )
        input_dir = input_dirs.get(spec.security_id)
        if not isinstance(input_dir, Path):
            raise ReportSnapshotCurationError(
                "report curation input is invalid"
            )
        extract_path = input_dir / spec.input_extract_filename
        pdf_path = source_pdf_dir / f"{spec.ticker}.pdf"
        try:
            source_pdf_bytes = pdf_path.read_bytes()
        except OSError:
            raise ReportSnapshotCurationError(
                "report source could not be read"
            ) from None
        try:
            extract = load_report_extract(extract_path)
            observed_page_count = page_counter(pdf_path)
            payload = build_report_snapshot_payload(
                extract,
                spec=spec,
                source_pdf_bytes=source_pdf_bytes,
                source_extract_sha256=file_sha256(extract_path),
                observed_pdf_page_count=observed_page_count,
            )
            documents = validate_report_snapshot_payload(payload, spec=spec)
            write_report_snapshot_json(
                output_dir / f"report_snapshot_curated_{spec.ticker}.json",
                payload,
            )
        except ReportSnapshotValidationError:
            raise ReportSnapshotCurationError(
                "report curation failed"
            ) from None
        summaries.append(
            {
                "security_id": spec.security_id,
                "document_count": len(documents),
                "verified_pdf_page_count": len(
                    payload["coverage"]["verified_pdf_pages"]
                ),
                "usage_review_status": "approved",
                "external_llm_processing_allowed": False,
                "ready": payload["coverage"]["ready"],
            }
        )
    return tuple(summaries)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Curate verified FSC research-report snapshot inputs.",
    )
    parser.add_argument("--samsung-dir", type=Path, required=True)
    parser.add_argument("--sk-hynix-dir", type=Path, required=True)
    parser.add_argument("--hyundai-dir", type=Path, required=True)
    parser.add_argument(
        "--source-pdf-dir",
        type=Path,
        default=DEFAULT_SOURCE_PDF_DIR,
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--pdfinfo-executable", default="pdfinfo")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_dirs = {
        "KRX:005930": args.samsung_dir,
        "KRX:000660": args.sk_hynix_dir,
        "KRX:005380": args.hyundai_dir,
    }

    def page_counter(path: Path) -> int:
        return read_pdf_page_count(
            path,
            executable=args.pdfinfo_executable,
        )

    try:
        summaries = run_curation(
            input_dirs=input_dirs,
            source_pdf_dir=args.source_pdf_dir,
            output_dir=args.output_dir,
            page_counter=page_counter,
        )
    except ReportSnapshotCurationError:
        print(
            json.dumps(
                {"status": "FAIL", "reason": "report_curation_failed"},
                sort_keys=True,
            )
        )
        return 1
    print(
        json.dumps(
            {"status": "PASS", "results": list(summaries)},
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
