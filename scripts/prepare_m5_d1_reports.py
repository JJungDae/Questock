from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.services.m5_d1_report_inventory import (
    M5_D1_REPORT_INVENTORY_PATH,
    M5_D1_REPORT_LOCAL_EXTRACT_SCHEMA_VERSION,
    M5D1ReportInventoryError,
    SUPPORTED_REPORT_SECURITIES,
    build_report_inventory_payload,
    write_report_inventory,
)

DEFAULT_REPORT_SOURCE_ROOT = Path("docs/questock_reports")
DEFAULT_LOCAL_EXTRACT_ROOT = Path(
    "var/service_completion/m5_d1/reports/extracted"
)
_REPORT_FILENAME_RE = re.compile(
    r"^(?P<date>\d{6}|\d{8})_"
    r"(?P<publisher>삼성증권|미래에셋증권|키움증권)_"
    r"\((?P<analyst>[^)]+)\)"
    r"(?P<title>.+)\.pdf$"
)


class M5D1ReportPreparationError(ValueError):
    """Raised when local M5-D1 report preparation fails."""


def extract_pdf_pages(path: Path) -> tuple[str, ...]:
    try:
        from pypdf import PdfReader
    except ImportError:
        return _extract_pdf_pages_with_local_python(path)
    try:
        reader = PdfReader(str(path))
        pages = tuple(
            page.extract_text() or "" for page in reader.pages
        )
    except Exception:
        raise M5D1ReportPreparationError(
            "local PDF extraction failed"
        ) from None
    if not pages:
        raise M5D1ReportPreparationError(
            "local PDF extraction failed"
        )
    return pages


def _extract_pdf_pages_with_local_python(path: Path) -> tuple[str, ...]:
    executable = os.environ.get("QUESTOCK_LOCAL_PDF_PYTHON", "").strip()
    if not executable:
        raise M5D1ReportPreparationError(
            "local PDF extraction dependency is unavailable"
        )
    helper = (
        "import json,sys;"
        "from pypdf import PdfReader;"
        "r=PdfReader(sys.argv[1]);"
        "print(json.dumps([p.extract_text() or '' for p in r.pages],"
        "ensure_ascii=True))"
    )
    try:
        completed = subprocess.run(
            [executable, "-c", helper, str(path)],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise M5D1ReportPreparationError(
            "local PDF extraction failed"
        ) from None
    try:
        pages = json.loads(completed.stdout)
    except json.JSONDecodeError:
        raise M5D1ReportPreparationError(
            "local PDF extraction failed"
        ) from None
    if (
        completed.returncode != 0
        or not isinstance(pages, list)
        or not pages
        or any(not isinstance(page, str) for page in pages)
    ):
        raise M5D1ReportPreparationError(
            "local PDF extraction failed"
        )
    return tuple(pages)


def prepare_report_inventory(
    *,
    source_root: Path,
    local_extract_root: Path,
    output_path: Path,
    visual_review_confirmed: bool,
    page_extractor: Callable[[Path], tuple[str, ...]] = extract_pdf_pages,
    prepared_at: datetime,
) -> dict[str, Any]:
    if (
        not isinstance(source_root, Path)
        or not isinstance(local_extract_root, Path)
        or not isinstance(output_path, Path)
        or not callable(page_extractor)
    ):
        raise M5D1ReportPreparationError(
            "report preparation input is invalid"
        )
    ticker_to_security = {
        ticker: (security_id, security_name)
        for security_id, (
            ticker,
            security_name,
        ) in SUPPORTED_REPORT_SECURITIES.items()
    }
    raw_reports: list[dict[str, Any]] = []
    local_extracts: list[tuple[str, dict[str, Any]]] = []
    try:
        ticker_dirs = sorted(
            path
            for path in source_root.iterdir()
            if path.is_dir()
        )
    except OSError:
        raise M5D1ReportPreparationError(
            "report source root is unavailable"
        ) from None
    for ticker_dir in ticker_dirs:
        identity = ticker_to_security.get(ticker_dir.name)
        if identity is None:
            raise M5D1ReportPreparationError(
                "report source ticker is invalid"
            )
        security_id, security_name = identity
        source_map = _load_source_map(ticker_dir / "sources.txt")
        pdf_paths = sorted(ticker_dir.glob("*.pdf"))
        if not pdf_paths:
            raise M5D1ReportPreparationError(
                "report source coverage is invalid"
            )
        if set(source_map) != {path.stem for path in pdf_paths}:
            raise M5D1ReportPreparationError(
                "report source map is invalid"
            )
        for path in pdf_paths:
            match = _REPORT_FILENAME_RE.fullmatch(path.name)
            if match is None:
                raise M5D1ReportPreparationError(
                    "report source filename is invalid"
                )
            try:
                pdf_bytes = path.read_bytes()
                page_texts = page_extractor(path)
            except OSError:
                raise M5D1ReportPreparationError(
                    "report source is unavailable"
                ) from None
            pdf_sha256 = hashlib.sha256(pdf_bytes).hexdigest()
            raw_reports.append(
                {
                    "security_id": security_id,
                    "ticker": ticker_dir.name,
                    "security_name": security_name,
                    "publisher": match.group("publisher"),
                    "analyst": match.group("analyst").strip(),
                    "title": match.group("title").strip(),
                    "published_date": datetime.strptime(
                        (
                            match.group("date")
                            if len(match.group("date")) == 8
                            else f"20{match.group('date')}"
                        ),
                        "%Y%m%d",
                    )
                    .date()
                    .isoformat(),
                    "source_url": source_map[path.stem],
                    "pdf_sha256": pdf_sha256,
                    "page_texts": page_texts,
                }
            )
            local_extracts.append(
                (
                    pdf_sha256,
                    {
                        "schema_version": (
                            M5_D1_REPORT_LOCAL_EXTRACT_SCHEMA_VERSION
                        ),
                        "pdf_sha256": pdf_sha256,
                        "pages": [
                            {"page": index, "text": text}
                            for index, text in enumerate(
                                page_texts,
                                start=1,
                            )
                        ],
                    },
                )
            )
    try:
        payload = build_report_inventory_payload(
            raw_reports,
            prepared_at=prepared_at,
            visual_review_confirmed=visual_review_confirmed,
        )
        local_extract_root.mkdir(parents=True, exist_ok=True)
        for pdf_sha256, extract in local_extracts:
            extract_path = (
                local_extract_root / f"{pdf_sha256}.json"
            )
            serialized_extract = (
                json.dumps(
                    extract,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            )
            if extract_path.exists():
                try:
                    existing = extract_path.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    raise M5D1ReportPreparationError(
                        "existing local report extract is invalid"
                    ) from None
                if existing != serialized_extract:
                    raise M5D1ReportPreparationError(
                        "existing local report extract is invalid"
                    )
            else:
                extract_path.write_text(
                    serialized_extract,
                    encoding="utf-8",
                    newline="\n",
                )
        write_report_inventory(payload, output_path)
    except M5D1ReportInventoryError:
        raise M5D1ReportPreparationError(
            "report inventory build failed"
        ) from None
    return payload


def _load_source_map(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        raise M5D1ReportPreparationError(
            "report source map is unavailable"
        ) from None
    output: dict[str, str] = {}
    for line in lines:
        if not line.strip():
            continue
        parts = line.split(" : ", 1)
        if (
            len(parts) != 2
            or not parts[0].strip()
            or not parts[1].strip()
            or parts[0].strip() in output
        ):
            raise M5D1ReportPreparationError(
                "report source map is invalid"
            )
        output[parts[0].strip()] = parts[1].strip()
    if not output:
        raise M5D1ReportPreparationError(
            "report source map is invalid"
        )
    return output


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prepare the local-only M5-D1 report inventory.",
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=DEFAULT_REPORT_SOURCE_ROOT,
    )
    parser.add_argument(
        "--local-extract-root",
        type=Path,
        default=DEFAULT_LOCAL_EXTRACT_ROOT,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=M5_D1_REPORT_INVENTORY_PATH,
    )
    parser.add_argument(
        "--visual-review-confirmed",
        action="store_true",
    )
    arguments = parser.parse_args(argv)
    try:
        payload = prepare_report_inventory(
            source_root=arguments.source_root,
            local_extract_root=arguments.local_extract_root,
            output_path=arguments.output,
            visual_review_confirmed=(
                arguments.visual_review_confirmed
            ),
            prepared_at=datetime.now(UTC),
        )
    except (
        M5D1ReportPreparationError,
        OSError,
        ValueError,
    ):
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "reason": "m5_d1_report_preparation_failed",
                },
                separators=(",", ":"),
            )
        )
        return 1
    print(
        json.dumps(
            {
                "status": "PASS",
                "discovered_count": payload["coverage"][
                    "discovered_count"
                ],
                "selected_count": payload["coverage"][
                    "selected_count"
                ],
                "excluded_count": payload["coverage"][
                    "excluded_count"
                ],
                "runtime_ready_count": payload["coverage"][
                    "runtime_ready_count"
                ],
                "source_sha256": payload["source_sha256"],
            },
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
