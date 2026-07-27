from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from app.services.disclosure_snapshot_schema import (
    DISCLOSURE_INPUT_SPECS,
    DisclosureCorrectionVerification,
    DisclosureInputSpec,
    DisclosureSnapshotValidationError,
    build_disclosure_snapshot_payload,
    file_sha256,
    load_disclosure_fact_matrix,
    validate_disclosure_snapshot_payload,
    write_disclosure_snapshot_json,
)

DEFAULT_OUTPUT_DIR = Path("var/service_completion/disclosure/curated")
DEFAULT_WORKING_DIR = Path("var/service_completion/disclosure/input")
OPENDART_LIST_ENDPOINT = "https://opendart.fss.or.kr/api/list.json"
DART_VIEWER_BASE_URL = "https://dart.fss.or.kr/dsaf001/main.do"
CORRECTION_PENDING_EXIT = 3
_PAGES_RE = re.compile(r"^Pages:\s*(\d+)\s*$", re.MULTILINE)
_TAG_RE = re.compile(r"<[^>]+>")
_NAME_WRAP_RE = re.compile(
    r'<div class="nameWrap">(?P<body>.*?)</div>',
    re.DOTALL,
)
_BADGE_RE = re.compile(
    r'<span class="tagCom_[^"]+"[^>]*>\s*([^<]+?)\s*</span>',
    re.DOTALL,
)


class DisclosureSnapshotCurationError(ValueError):
    """Raised when local disclosure curation cannot complete safely."""


@runtime_checkable
class OpenDartTransport(Protocol):
    def search(
        self,
        *,
        api_key: str,
        corp_code: str,
        submitted_date: str,
        timeout_seconds: float,
    ) -> dict[str, Any]: ...


@runtime_checkable
class DartViewerTransport(Protocol):
    def fetch(self, *, receipt_no: str, timeout_seconds: float) -> str: ...


class UrllibOpenDartTransport:
    def search(
        self,
        *,
        api_key: str,
        corp_code: str,
        submitted_date: str,
        timeout_seconds: float,
    ) -> dict[str, Any]:
        if (
            not isinstance(api_key, str)
            or not api_key
            or not isinstance(corp_code, str)
            or not corp_code
        ):
            raise DisclosureSnapshotCurationError(
                "OpenDART verification input is invalid"
            )
        query = urllib.parse.urlencode(
            {
                "crtfc_key": api_key,
                "corp_code": corp_code,
                "bgn_de": submitted_date,
                "end_de": submitted_date,
                "last_reprt_at": "N",
                "page_no": 1,
                "page_count": 100,
                "sort": "date",
                "sort_mth": "desc",
            }
        )
        request = urllib.request.Request(
            f"{OPENDART_LIST_ENDPOINT}?{query}",
            headers={"User-Agent": "Questock-FSC-Disclosure-Preflight/1.0"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=timeout_seconds,
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (
            urllib.error.HTTPError,
            urllib.error.URLError,
            TimeoutError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            raise DisclosureSnapshotCurationError(
                "OpenDART verification failed"
            ) from None
        if not isinstance(payload, dict):
            raise DisclosureSnapshotCurationError(
                "OpenDART verification failed"
            )
        return payload


class UrllibDartViewerTransport:
    def fetch(self, *, receipt_no: str, timeout_seconds: float) -> str:
        request = urllib.request.Request(
            f"{DART_VIEWER_BASE_URL}?rcpNo={receipt_no}",
            headers={"User-Agent": "Questock-FSC-Disclosure-Preflight/1.0"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=timeout_seconds,
            ) as response:
                return response.read().decode("utf-8")
        except (
            urllib.error.HTTPError,
            urllib.error.URLError,
            TimeoutError,
            UnicodeDecodeError,
        ):
            raise DisclosureSnapshotCurationError(
                "DART viewer verification failed"
            ) from None


def verify_opendart_correction_state(
    *,
    spec: DisclosureInputSpec,
    api_key: str,
    transport: OpenDartTransport,
) -> DisclosureCorrectionVerification:
    if (
        not isinstance(spec, DisclosureInputSpec)
        or not isinstance(transport, OpenDartTransport)
    ):
        raise DisclosureSnapshotCurationError(
            "OpenDART verification input is invalid"
        )
    try:
        payload = transport.search(
            api_key=api_key,
            corp_code=spec.corp_code,
            submitted_date="20260515",
            timeout_seconds=15,
        )
    except Exception:
        raise DisclosureSnapshotCurationError(
            "OpenDART verification failed"
        ) from None
    if payload.get("status") != "000" or not isinstance(payload.get("list"), list):
        raise DisclosureSnapshotCurationError("OpenDART verification failed")
    matches = [
        item
        for item in payload["list"]
        if isinstance(item, dict)
        and item.get("rcept_no") == spec.receipt_no
        and item.get("corp_code") == spec.corp_code
        and item.get("stock_code") == spec.ticker
    ]
    if len(matches) != 1:
        raise DisclosureSnapshotCurationError("OpenDART verification failed")
    item = matches[0]
    report_name = _clean_text(item.get("report_nm"))
    remark = _clean_text(item.get("rm"), allow_empty=True)
    if not report_name or "분기보고서" not in report_name:
        raise DisclosureSnapshotCurationError("OpenDART verification failed")
    return DisclosureCorrectionVerification(
        receipt_no=spec.receipt_no,
        status="verified_official_api",
        remark=remark,
        report_name=report_name,
    )


def verify_dart_viewer_correction_state(
    *,
    spec: DisclosureInputSpec,
    transport: DartViewerTransport,
) -> DisclosureCorrectionVerification:
    if (
        not isinstance(spec, DisclosureInputSpec)
        or not isinstance(transport, DartViewerTransport)
    ):
        raise DisclosureSnapshotCurationError(
            "DART viewer verification input is invalid"
        )
    try:
        text = transport.fetch(
            receipt_no=spec.receipt_no,
            timeout_seconds=15,
        )
    except Exception:
        raise DisclosureSnapshotCurationError(
            "DART viewer verification failed"
        ) from None
    receipt_marker = f'node1[\'rcpNo\'] = "{spec.receipt_no}";'
    corp_marker = f"openCorpInfoNew('{spec.corp_code}'"
    name_match = _NAME_WRAP_RE.search(text)
    if (
        receipt_marker not in text
        or corp_marker not in text
        or name_match is None
        or spec.security_name not in _clean_text(name_match.group("body"))
        or "분 기 보 고 서" not in text
    ):
        raise DisclosureSnapshotCurationError(
            "DART viewer verification failed"
        )
    badges = tuple(
        _clean_text(value)
        for value in _BADGE_RE.findall(name_match.group("body"))
    )
    remark = "".join(badges)
    if (
        "유" not in remark
        or not remark
        or any(marker not in {"유", "정", "철"} for marker in remark)
    ):
        raise DisclosureSnapshotCurationError(
            "DART viewer verification failed"
        )
    return DisclosureCorrectionVerification(
        receipt_no=spec.receipt_no,
        status="verified_official_viewer",
        remark=remark,
        report_name="분기보고서",
    )


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
        raise DisclosureSnapshotCurationError(
            "disclosure PDF inspection failed"
        )
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
        raise DisclosureSnapshotCurationError(
            "disclosure PDF inspection failed"
        ) from None
    match = _PAGES_RE.search(completed.stdout)
    if completed.returncode != 0 or match is None:
        raise DisclosureSnapshotCurationError(
            "disclosure PDF inspection failed"
        )
    return int(match.group(1))


def run_curation(
    *,
    input_dirs: Mapping[str, Path],
    output_dir: Path,
    working_dir: Path,
    api_key: str | None,
    page_counter: Callable[[Path], int] = read_pdf_page_count,
    transport: OpenDartTransport | None = None,
    viewer_transport: DartViewerTransport | None = None,
) -> tuple[dict[str, Any], ...]:
    if (
        not isinstance(input_dirs, Mapping)
        or not isinstance(output_dir, Path)
        or not isinstance(working_dir, Path)
        or not callable(page_counter)
    ):
        raise DisclosureSnapshotCurationError(
            "disclosure curation input is invalid"
        )
    live_transport = transport or UrllibOpenDartTransport()
    live_viewer_transport = viewer_transport or UrllibDartViewerTransport()
    summaries: list[dict[str, Any]] = []
    for spec in DISCLOSURE_INPUT_SPECS:
        source_dir = input_dirs.get(spec.security_id)
        if not isinstance(source_dir, Path):
            raise DisclosureSnapshotCurationError(
                "disclosure curation input is invalid"
            )
        matrix_path = _single_source_file(
            source_dir,
            "disclosure_fact_matrix_*.json",
        )
        pdf_path = _single_source_file(source_dir, "*.pdf")
        working_pdf = working_dir / f"disclosure_{spec.ticker}.pdf"
        try:
            working_pdf.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(pdf_path, working_pdf)
        except OSError:
            raise DisclosureSnapshotCurationError(
                "disclosure source could not be prepared"
            ) from None
        observed_page_count = page_counter(working_pdf)
        correction = _pending_correction(spec)
        if api_key:
            try:
                correction = verify_opendart_correction_state(
                    spec=spec,
                    api_key=api_key,
                    transport=live_transport,
                )
            except DisclosureSnapshotCurationError:
                pass
        if correction.status == "pending":
            try:
                correction = verify_dart_viewer_correction_state(
                    spec=spec,
                    transport=live_viewer_transport,
                )
            except DisclosureSnapshotCurationError:
                pass

        matrix = load_disclosure_fact_matrix(matrix_path)
        payload = build_disclosure_snapshot_payload(
            matrix,
            spec=spec,
            source_pdf_sha256=file_sha256(working_pdf),
            source_matrix_sha256=file_sha256(matrix_path),
            observed_pdf_page_count=observed_page_count,
            correction=correction,
        )
        validate_disclosure_snapshot_payload(payload, spec=spec)
        write_disclosure_snapshot_json(
            output_dir / f"disclosure_snapshot_curated_{spec.ticker}.json",
            payload,
        )
        summaries.append(
            {
                "security_id": spec.security_id,
                "receipt_no": spec.receipt_no,
                "document_count": 1,
                "fact_count": payload["coverage"]["fact_count"],
                "required_category_count": len(
                    payload["coverage"]["required_categories"]
                ),
                "pdf_page_count": observed_page_count,
                "correction_verification_status": correction.status,
                "ready": (
                    payload["coverage"]["ready"]
                    and correction.status
                    in {
                        "verified_official_api",
                        "verified_official_viewer",
                    }
                ),
            }
        )
    return tuple(summaries)


def build_curation_result(
    summaries: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], int]:
    if (
        isinstance(summaries, (str, bytes, bytearray))
        or not isinstance(summaries, Sequence)
        or len(summaries) != len(DISCLOSURE_INPUT_SPECS)
        or any(
            not isinstance(item, Mapping)
            or not isinstance(item.get("ready"), bool)
            for item in summaries
        )
    ):
        raise DisclosureSnapshotCurationError(
            "disclosure curation result is invalid"
        )
    ready = all(item["ready"] for item in summaries)
    return (
        {
            "status": "PASS" if ready else "BLOCKED",
            "results": [dict(item) for item in summaries],
            **(
                {}
                if ready
                else {"reason": "correction_verification_pending"}
            ),
        },
        0 if ready else CORRECTION_PENDING_EXIT,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Curate verified FSC disclosure snapshot inputs.",
    )
    parser.add_argument("--samsung-dir", type=Path, required=True)
    parser.add_argument("--sk-hynix-dir", type=Path, required=True)
    parser.add_argument("--hyundai-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--working-dir", type=Path, default=DEFAULT_WORKING_DIR)
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
            output_dir=args.output_dir,
            working_dir=args.working_dir,
            api_key=os.getenv("OPENDART_API_KEY") or None,
            page_counter=page_counter,
        )
        result, exit_code = build_curation_result(summaries)
    except (
        DisclosureSnapshotCurationError,
        DisclosureSnapshotValidationError,
    ):
        print(
            json.dumps(
                {"status": "FAIL", "reason": "disclosure_curation_failed"},
                sort_keys=True,
            )
        )
        return 1
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return exit_code


def _single_source_file(directory: Path, pattern: str) -> Path:
    if not isinstance(directory, Path):
        raise DisclosureSnapshotCurationError(
            "disclosure curation input is invalid"
        )
    try:
        matches = tuple(
            item
            for item in directory.glob(pattern)
            if item.is_file()
        )
    except OSError:
        raise DisclosureSnapshotCurationError(
            "disclosure source could not be inspected"
        ) from None
    if len(matches) != 1:
        raise DisclosureSnapshotCurationError(
            "disclosure source inventory is invalid"
        )
    return matches[0]


def _pending_correction(
    spec: DisclosureInputSpec,
) -> DisclosureCorrectionVerification:
    return DisclosureCorrectionVerification(
        receipt_no=spec.receipt_no,
        status="pending",
        remark=None,
        report_name=None,
    )


def _clean_text(value: object, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise DisclosureSnapshotCurationError("OpenDART verification failed")
    normalized = " ".join(
        _TAG_RE.sub(" ", html.unescape(value)).split()
    )
    if not normalized and not allow_empty:
        raise DisclosureSnapshotCurationError("OpenDART verification failed")
    return normalized


if __name__ == "__main__":
    sys.exit(main())
