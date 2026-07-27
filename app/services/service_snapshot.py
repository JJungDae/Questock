from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal
from urllib.parse import parse_qsl, unquote_plus, urlsplit

from pydantic import ValidationError

from app.core.models import FinancialDocument
from app.services.disclosure_snapshot_schema import (
    DISCLOSURE_INPUT_SPECS,
    DISCLOSURE_SNAPSHOT_SCHEMA_VERSION,
    DisclosureSnapshotValidationError,
    validate_disclosure_snapshot_payload,
)
from app.services.news_snapshot_schema import (
    COLLECTION_CUTOFF,
    COLLECTION_START,
    NEWS_CURATED_SCHEMA_VERSION,
)
from app.services.report_snapshot_schema import (
    REPORT_INPUT_SPECS,
    REPORT_SNAPSHOT_SCHEMA_VERSION,
    ReportSnapshotValidationError,
    validate_report_snapshot_payload,
)

SERVICE_SNAPSHOT_TYPE = "questock_service_snapshot"
SERVICE_SNAPSHOT_SCHEMA_VERSION = "service-snapshot-v1"
SERVICE_SNAPSHOT_ID = "svc-20260724-1402"
SERVICE_SNAPSHOT_BASIS_AT = datetime(2026, 7, 24, 5, 2, tzinfo=UTC)
SERVICE_SNAPSHOT_INGESTION_VERSION = "service-snapshot-fsc-v1"
SERVICE_SNAPSHOT_DOCUMENTS_FILE = "documents.json"
SERVICE_SNAPSHOT_COVERAGE_FILE = "coverage_matrix.json"
SERVICE_SNAPSHOT_PERMISSION_FILE = "permission_register.json"
SERVICE_SNAPSHOT_CHECKSUM_FILE = "snapshot_checksum.txt"
SERVICE_SNAPSHOT_VALIDATION_FILE = "validation_report.json"
SERVICE_SNAPSHOT_ROOT = Path("data/service_snapshot")
SUPPORTED_SECURITY_IDS = (
    "KRX:005930",
    "KRX:000660",
    "KRX:005380",
)
SnapshotSourceType = Literal["news", "disclosure", "research_report"]

_SECURITY_NAMES = {
    "KRX:005930": "삼성전자",
    "KRX:000660": "SK하이닉스",
    "KRX:005380": "현대자동차",
}
_SOURCE_ORDER = {"news": 0, "disclosure": 1, "research_report": 2}
_EXPECTED_SOURCE_SCHEMAS = {
    "news": NEWS_CURATED_SCHEMA_VERSION,
    "disclosure": DISCLOSURE_SNAPSHOT_SCHEMA_VERSION,
    "research_report": REPORT_SNAPSHOT_SCHEMA_VERSION,
}
_NEWS_PROVIDER = "naver_api_hub_news"
_NEWS_SUMMARY_KIND = "project_owned_short_summary"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_NEWS_DOCUMENT_ID_RE = re.compile(r"^news:[0-9a-f]{64}$")
_WINDOWS_ABSOLUTE_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")
_FORBIDDEN_PUBLIC_KEYS = frozenset(
    {
        "articlebody",
        "description",
        "evidenceexcerpt",
        "pdfbytes",
        "raw",
        "rawtext",
        "reportbody",
        "sourcefile",
        "sourcepdf",
        "sourcepdfbytes",
        "verificationexcerpt",
        "viewerpdfurl",
    }
)
_CREDENTIAL_QUERY_KEYS = frozenset(
    {
        "accesstoken",
        "apikey",
        "authorization",
        "authtoken",
        "bearertoken",
        "clientsecret",
        "credential",
        "signature",
        "xamzsignature",
        "xapikey",
    }
)


class ServiceSnapshotValidationError(ValueError):
    """Raised when an immutable FSC service snapshot is invalid."""


@dataclass(frozen=True)
class SnapshotSourcePayload:
    source_type: SnapshotSourceType
    security_id: str
    sha256: str
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class ServiceSnapshot:
    snapshot_type: str
    schema_version: str
    snapshot_id: str
    basis_at: datetime
    documents: tuple[FinancialDocument, ...]
    coverage: Mapping[str, Any]
    source_artifacts: tuple[Mapping[str, Any], ...]


def load_snapshot_source(path: str | Path) -> tuple[dict[str, Any], str]:
    try:
        raw = Path(path).read_bytes()
        payload = json.loads(raw.decode("utf-8"))
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        TypeError,
    ):
        raise ServiceSnapshotValidationError(
            "snapshot source could not be loaded"
        ) from None
    if not isinstance(payload, dict):
        raise ServiceSnapshotValidationError("snapshot source is invalid")
    return payload, hashlib.sha256(raw).hexdigest()


def build_service_snapshot_payloads(
    sources: Sequence[SnapshotSourcePayload],
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    canonical_sources = _validate_source_set(sources)
    documents: list[FinancialDocument] = []
    artifacts: list[dict[str, Any]] = []
    for source in canonical_sources:
        source_documents = _documents_from_source(source)
        report_count = 1 if source.source_type == "research_report" else 0
        documents.extend(source_documents)
        artifacts.append(
            {
                "source_type": source.source_type,
                "security_id": source.security_id,
                "schema_version": _EXPECTED_SOURCE_SCHEMAS[
                    source.source_type
                ],
                "sha256": source.sha256,
                "document_count": len(source_documents),
                "report_count": report_count,
            }
        )
    canonical_documents = tuple(documents)
    coverage = _calculate_coverage(canonical_documents)
    documents_payload = {
        "schema_version": SERVICE_SNAPSHOT_SCHEMA_VERSION,
        "snapshot_id": SERVICE_SNAPSHOT_ID,
        "documents": [
            document.model_dump(mode="json")
            for document in canonical_documents
        ],
    }
    documents_bytes = serialize_service_snapshot_json(documents_payload)
    coverage_payload = {
        "schema_version": SERVICE_SNAPSHOT_SCHEMA_VERSION,
        "snapshot_id": SERVICE_SNAPSHOT_ID,
        "coverage": coverage,
    }
    permission_payload = _permission_register()
    coverage_bytes = serialize_service_snapshot_json(coverage_payload)
    permission_bytes = serialize_service_snapshot_json(permission_payload)
    manifest = {
        "snapshot_type": SERVICE_SNAPSHOT_TYPE,
        "schema_version": SERVICE_SNAPSHOT_SCHEMA_VERSION,
        "snapshot_id": SERVICE_SNAPSHOT_ID,
        "basis_at": _utc_timestamp(SERVICE_SNAPSHOT_BASIS_AT),
        "documents_file": SERVICE_SNAPSHOT_DOCUMENTS_FILE,
        "coverage_file": SERVICE_SNAPSHOT_COVERAGE_FILE,
        "permission_register_file": SERVICE_SNAPSHOT_PERMISSION_FILE,
        "documents_sha256": hashlib.sha256(documents_bytes).hexdigest(),
        "coverage_sha256": hashlib.sha256(coverage_bytes).hexdigest(),
        "permission_register_sha256": hashlib.sha256(
            permission_bytes
        ).hexdigest(),
        "security_ids": list(SUPPORTED_SECURITY_IDS),
        "source_artifacts": artifacts,
        "document_ids": [
            document.document_id for document in canonical_documents
        ],
    }
    build_service_snapshot(
        manifest,
        documents_payload,
        documents_bytes=documents_bytes,
        coverage_payload=coverage_payload,
        coverage_bytes=coverage_bytes,
        permission_payload=permission_payload,
        permission_bytes=permission_bytes,
    )
    return (
        manifest,
        documents_payload,
        coverage_payload,
        permission_payload,
    )


def load_service_snapshot(
    snapshot_id: str = SERVICE_SNAPSHOT_ID,
    *,
    root: Path = SERVICE_SNAPSHOT_ROOT,
) -> ServiceSnapshot:
    if snapshot_id != SERVICE_SNAPSHOT_ID or not isinstance(root, Path):
        raise ServiceSnapshotValidationError("snapshot selection is invalid")
    directory = root / SERVICE_SNAPSHOT_ID
    try:
        manifest_bytes = (directory / "manifest.json").read_bytes()
        documents_bytes = (
            directory / SERVICE_SNAPSHOT_DOCUMENTS_FILE
        ).read_bytes()
        coverage_bytes = (
            directory / SERVICE_SNAPSHOT_COVERAGE_FILE
        ).read_bytes()
        permission_bytes = (
            directory / SERVICE_SNAPSHOT_PERMISSION_FILE
        ).read_bytes()
        checksum_bytes = (
            directory / SERVICE_SNAPSHOT_CHECKSUM_FILE
        ).read_bytes()
        validation_bytes = (
            directory / SERVICE_SNAPSHOT_VALIDATION_FILE
        ).read_bytes()
        manifest = json.loads(manifest_bytes.decode("utf-8"))
        payload = json.loads(documents_bytes.decode("utf-8"))
        coverage_payload = json.loads(coverage_bytes.decode("utf-8"))
        permission_payload = json.loads(permission_bytes.decode("utf-8"))
        validation_payload = json.loads(validation_bytes.decode("utf-8"))
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        TypeError,
    ):
        raise ServiceSnapshotValidationError(
            "service snapshot could not be loaded"
        ) from None
    snapshot = build_service_snapshot(
        manifest,
        payload,
        documents_bytes=documents_bytes,
        coverage_payload=coverage_payload,
        coverage_bytes=coverage_bytes,
        permission_payload=permission_payload,
        permission_bytes=permission_bytes,
    )
    _validate_generated_evidence(
        directory=directory,
        checksum_bytes=checksum_bytes,
        validation_payload=validation_payload,
        snapshot=snapshot,
    )
    return snapshot


def build_service_snapshot(
    manifest: object,
    payload: object,
    *,
    documents_bytes: bytes | None = None,
    coverage_payload: object | None = None,
    coverage_bytes: bytes | None = None,
    permission_payload: object | None = None,
    permission_bytes: bytes | None = None,
) -> ServiceSnapshot:
    canonical_manifest = _validate_manifest(manifest)
    canonical_payload = _validate_documents_payload(payload)
    if documents_bytes is None:
        documents_bytes = serialize_service_snapshot_json(canonical_payload)
    if (
        type(documents_bytes) is not bytes
        or hashlib.sha256(documents_bytes).hexdigest()
        != canonical_manifest["documents_sha256"]
    ):
        raise ServiceSnapshotValidationError(
            "service snapshot checksum is invalid"
        )
    documents = _validate_documents(
        canonical_payload["documents"],
        basis_at=canonical_manifest["basis_at"],
    )
    document_ids = tuple(document.document_id for document in documents)
    if (
        document_ids != tuple(canonical_manifest["document_ids"])
        or len(document_ids) != len(set(document_ids))
    ):
        raise ServiceSnapshotValidationError(
            "service snapshot document identity is invalid"
        )
    coverage = _calculate_coverage(documents)
    canonical_coverage_payload = (
        {
            "schema_version": SERVICE_SNAPSHOT_SCHEMA_VERSION,
            "snapshot_id": SERVICE_SNAPSHOT_ID,
            "coverage": coverage,
        }
        if coverage_payload is None
        else coverage_payload
    )
    if (
        not isinstance(canonical_coverage_payload, Mapping)
        or set(canonical_coverage_payload)
        != {"schema_version", "snapshot_id", "coverage"}
        or canonical_coverage_payload.get("schema_version")
        != SERVICE_SNAPSHOT_SCHEMA_VERSION
        or canonical_coverage_payload.get("snapshot_id")
        != SERVICE_SNAPSHOT_ID
        or canonical_coverage_payload.get("coverage") != coverage
    ):
        raise ServiceSnapshotValidationError(
            "service snapshot coverage is invalid"
        )
    if coverage_bytes is None:
        coverage_bytes = serialize_service_snapshot_json(
            canonical_coverage_payload
        )
    expected_permissions = _permission_register()
    canonical_permissions = (
        expected_permissions
        if permission_payload is None
        else permission_payload
    )
    if canonical_permissions != expected_permissions:
        raise ServiceSnapshotValidationError(
            "service snapshot permission register is invalid"
        )
    if permission_bytes is None:
        permission_bytes = serialize_service_snapshot_json(
            canonical_permissions
        )
    if (
        type(coverage_bytes) is not bytes
        or hashlib.sha256(coverage_bytes).hexdigest()
        != canonical_manifest["coverage_sha256"]
        or type(permission_bytes) is not bytes
        or hashlib.sha256(permission_bytes).hexdigest()
        != canonical_manifest["permission_register_sha256"]
    ):
        raise ServiceSnapshotValidationError(
            "service snapshot checksum is invalid"
        )
    _validate_source_artifacts(
        canonical_manifest["source_artifacts"],
        documents=documents,
    )
    _assert_safe_public_payload(canonical_manifest)
    _assert_safe_public_payload(canonical_payload)
    _assert_safe_public_payload(canonical_coverage_payload)
    _assert_safe_public_payload(canonical_permissions)
    return ServiceSnapshot(
        snapshot_type=SERVICE_SNAPSHOT_TYPE,
        schema_version=SERVICE_SNAPSHOT_SCHEMA_VERSION,
        snapshot_id=SERVICE_SNAPSHOT_ID,
        basis_at=canonical_manifest["basis_at"],
        documents=tuple(item.model_copy(deep=True) for item in documents),
        coverage=json.loads(
            json.dumps(coverage, ensure_ascii=False)
        ),
        source_artifacts=tuple(
            json.loads(json.dumps(item, ensure_ascii=False))
            for item in canonical_manifest["source_artifacts"]
        ),
    )


def serialize_service_snapshot_json(value: Mapping[str, Any]) -> bytes:
    if not isinstance(value, Mapping):
        raise ServiceSnapshotValidationError("snapshot output is invalid")
    try:
        text = json.dumps(
            dict(value),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError):
        raise ServiceSnapshotValidationError(
            "snapshot output is invalid"
        ) from None
    return f"{text}\n".encode("utf-8")


def build_snapshot_checksum(
    canonical_files: Mapping[str, bytes],
) -> bytes:
    expected_names = {
        "manifest.json",
        SERVICE_SNAPSHOT_DOCUMENTS_FILE,
        SERVICE_SNAPSHOT_COVERAGE_FILE,
        SERVICE_SNAPSHOT_PERMISSION_FILE,
    }
    if (
        not isinstance(canonical_files, Mapping)
        or set(canonical_files) != expected_names
        or any(type(value) is not bytes for value in canonical_files.values())
    ):
        raise ServiceSnapshotValidationError(
            "snapshot checksum input is invalid"
        )
    manifest_text = "".join(
        f"{name}\t{hashlib.sha256(canonical_files[name]).hexdigest()}\n"
        for name in sorted(expected_names)
    )
    bundle_sha256 = hashlib.sha256(manifest_text.encode("utf-8")).hexdigest()
    return (
        f"{manifest_text}bundle_sha256\t{bundle_sha256}\n"
    ).encode("utf-8")


def build_snapshot_validation_report(
    snapshot: ServiceSnapshot,
) -> dict[str, Any]:
    canonical = copy_service_snapshot(snapshot)
    return {
        "schema_version": SERVICE_SNAPSHOT_SCHEMA_VERSION,
        "snapshot_id": SERVICE_SNAPSHOT_ID,
        "status": "PASS",
        "document_count": len(canonical.documents),
        "checks": {
            "attribution_and_permission": True,
            "basis_cutoff": True,
            "checksum_format": True,
            "disclosure_fact_coverage": True,
            "document_id_uniqueness": True,
            "local_path_secret_raw_content_absent": True,
            "news_coverage": True,
            "report_coverage": True,
            "supported_securities": True,
            "url_receipt_page_section": True,
        },
    }


def copy_service_snapshot(value: object) -> ServiceSnapshot:
    if (
        not isinstance(value, ServiceSnapshot)
        or value.snapshot_type != SERVICE_SNAPSHOT_TYPE
        or value.schema_version != SERVICE_SNAPSHOT_SCHEMA_VERSION
        or value.snapshot_id != SERVICE_SNAPSHOT_ID
        or not isinstance(value.basis_at, datetime)
        or value.basis_at != SERVICE_SNAPSHOT_BASIS_AT
        or not isinstance(value.documents, tuple)
        or not value.documents
        or not isinstance(value.coverage, Mapping)
        or not isinstance(value.source_artifacts, tuple)
    ):
        raise ServiceSnapshotValidationError("service snapshot is invalid")
    try:
        source_artifacts = [
            json.loads(json.dumps(item, ensure_ascii=False))
            for item in value.source_artifacts
        ]
    except (TypeError, ValueError):
        raise ServiceSnapshotValidationError(
            "service snapshot is invalid"
        ) from None
    manifest = {
        "snapshot_type": value.snapshot_type,
        "schema_version": value.schema_version,
        "snapshot_id": value.snapshot_id,
        "basis_at": _utc_timestamp(value.basis_at),
        "documents_file": SERVICE_SNAPSHOT_DOCUMENTS_FILE,
        "coverage_file": SERVICE_SNAPSHOT_COVERAGE_FILE,
        "permission_register_file": SERVICE_SNAPSHOT_PERMISSION_FILE,
        "documents_sha256": "",
        "coverage_sha256": "",
        "permission_register_sha256": "",
        "security_ids": list(SUPPORTED_SECURITY_IDS),
        "source_artifacts": source_artifacts,
        "document_ids": [item.document_id for item in value.documents],
    }
    payload = {
        "schema_version": SERVICE_SNAPSHOT_SCHEMA_VERSION,
        "snapshot_id": SERVICE_SNAPSHOT_ID,
        "documents": [
            item.model_dump(mode="json") for item in value.documents
        ],
    }
    raw = serialize_service_snapshot_json(payload)
    manifest["documents_sha256"] = hashlib.sha256(raw).hexdigest()
    coverage_payload = {
        "schema_version": SERVICE_SNAPSHOT_SCHEMA_VERSION,
        "snapshot_id": SERVICE_SNAPSHOT_ID,
        "coverage": json.loads(
            json.dumps(value.coverage, ensure_ascii=False)
        ),
    }
    permission_payload = _permission_register()
    coverage_raw = serialize_service_snapshot_json(coverage_payload)
    permission_raw = serialize_service_snapshot_json(permission_payload)
    manifest["coverage_sha256"] = hashlib.sha256(coverage_raw).hexdigest()
    manifest["permission_register_sha256"] = hashlib.sha256(
        permission_raw
    ).hexdigest()
    return build_service_snapshot(
        manifest,
        payload,
        documents_bytes=raw,
        coverage_payload=coverage_payload,
        coverage_bytes=coverage_raw,
        permission_payload=permission_payload,
        permission_bytes=permission_raw,
    )


def _validate_source_set(
    sources: Sequence[SnapshotSourcePayload],
) -> tuple[SnapshotSourcePayload, ...]:
    if (
        isinstance(sources, (str, bytes, bytearray))
        or not isinstance(sources, Sequence)
    ):
        raise ServiceSnapshotValidationError("snapshot sources are invalid")
    expected = {
        (source_type, security_id)
        for security_id in SUPPORTED_SECURITY_IDS
        for source_type in _SOURCE_ORDER
    }
    by_key: dict[tuple[str, str], SnapshotSourcePayload] = {}
    for source in sources:
        if (
            not isinstance(source, SnapshotSourcePayload)
            or source.source_type not in _SOURCE_ORDER
            or source.security_id not in SUPPORTED_SECURITY_IDS
            or _SHA256_RE.fullmatch(source.sha256) is None
            or not isinstance(source.payload, Mapping)
        ):
            raise ServiceSnapshotValidationError(
                "snapshot sources are invalid"
            )
        key = (source.source_type, source.security_id)
        if key in by_key:
            raise ServiceSnapshotValidationError(
                "snapshot sources are invalid"
            )
        by_key[key] = source
    if set(by_key) != expected:
        raise ServiceSnapshotValidationError("snapshot sources are incomplete")
    return tuple(
        by_key[(source_type, security_id)]
        for security_id in SUPPORTED_SECURITY_IDS
        for source_type in _SOURCE_ORDER
    )


def _documents_from_source(
    source: SnapshotSourcePayload,
) -> tuple[FinancialDocument, ...]:
    try:
        if source.source_type == "news":
            return _build_news_documents(
                source.payload,
                security_id=source.security_id,
            )
        if source.source_type == "disclosure":
            spec = next(
                item
                for item in DISCLOSURE_INPUT_SPECS
                if item.security_id == source.security_id
            )
            return (
                validate_disclosure_snapshot_payload(
                    source.payload,
                    spec=spec,
                ),
            )
        spec = next(
            item
            for item in REPORT_INPUT_SPECS
            if item.security_id == source.security_id
        )
        return validate_report_snapshot_payload(source.payload, spec=spec)
    except (
        DisclosureSnapshotValidationError,
        ReportSnapshotValidationError,
        StopIteration,
        TypeError,
        ValueError,
    ):
        raise ServiceSnapshotValidationError(
            "snapshot source validation failed"
        ) from None


def _build_news_documents(
    payload: Mapping[str, Any],
    *,
    security_id: str,
) -> tuple[FinancialDocument, ...]:
    if (
        set(payload)
        != {
            "coverage",
            "documents",
            "schema_version",
            "security_id",
            "selection_policy",
            "snapshot_id",
            "summary_author",
            "summary_kind",
        }
        or payload.get("schema_version") != NEWS_CURATED_SCHEMA_VERSION
        or payload.get("snapshot_id") != SERVICE_SNAPSHOT_ID
        or payload.get("security_id") != security_id
        or payload.get("selection_policy") != "deterministic-event-diverse-v1"
        or payload.get("summary_author") != "Questock"
        or payload.get("summary_kind") != _NEWS_SUMMARY_KIND
    ):
        raise ServiceSnapshotValidationError("news snapshot source is invalid")
    raw_documents = payload.get("documents")
    if not isinstance(raw_documents, list) or len(raw_documents) != 5:
        raise ServiceSnapshotValidationError("news snapshot source is invalid")
    documents: list[FinancialDocument] = []
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    seen_times: set[datetime] = set()
    band_counts = {"pre_market": 0, "intraday": 0}
    security_name = _SECURITY_NAMES[security_id]
    for index, raw in enumerate(raw_documents, start=1):
        if (
            not isinstance(raw, Mapping)
            or set(raw)
            != {
                "document_id",
                "source_locator",
                "source_title",
                "summary",
                "time_band",
            }
        ):
            raise ServiceSnapshotValidationError(
                "news snapshot source is invalid"
            )
        document_id = raw.get("document_id")
        locator = raw.get("source_locator")
        source_title = raw.get("source_title")
        summary = raw.get("summary")
        time_band = raw.get("time_band")
        if (
            not isinstance(document_id, str)
            or _NEWS_DOCUMENT_ID_RE.fullmatch(document_id) is None
            or document_id in seen_ids
            or not isinstance(locator, Mapping)
            or set(locator) != {"provider", "published_at", "source_url"}
            or locator.get("provider") != _NEWS_PROVIDER
            or not isinstance(source_title, str)
            or not source_title.strip()
            or len(source_title) > 300
            or not isinstance(summary, str)
            or not summary.strip()
            or len(summary) > 300
            or time_band not in band_counts
        ):
            raise ServiceSnapshotValidationError(
                "news snapshot source is invalid"
            )
        source_url = locator.get("source_url")
        published_at = _parse_utc_timestamp(locator.get("published_at"))
        _validate_public_url(source_url)
        if (
            source_url in seen_urls
            or published_at in seen_times
            or not COLLECTION_START.astimezone(UTC)
            <= published_at
            <= COLLECTION_CUTOFF.astimezone(UTC)
            or published_at > SERVICE_SNAPSHOT_BASIS_AT
        ):
            raise ServiceSnapshotValidationError(
                "news snapshot source is invalid"
            )
        expected_band = (
            "pre_market"
            if published_at.astimezone(COLLECTION_START.tzinfo).hour < 9
            else "intraday"
        )
        if time_band != expected_band:
            raise ServiceSnapshotValidationError(
                "news snapshot source is invalid"
            )
        snapshot_document_id = (
            f"news:{security_id.split(':', 1)[1]}:"
            f"{hashlib.sha256(f'{security_id}|{document_id}'.encode()).hexdigest()}"
        )
        document = FinancialDocument(
            document_id=snapshot_document_id,
            source_type="news",
            provider=_NEWS_PROVIDER,
            primary_security_ids=[security_id],
            mentioned_security_ids=[],
            title=source_title.strip(),
            published_at=published_at,
            source_url=source_url,
            text=f"{security_name}: {summary.strip()}",
            locator={
                "provider": _NEWS_PROVIDER,
                "source_url": source_url,
                "published_at": _utc_timestamp(published_at),
                "time_band": time_band,
                "section": "Questock short summary",
            },
            metadata={
                "document_type": "article",
                "content_origin": _NEWS_SUMMARY_KIND,
                "verification_status": "human_approved",
                "summary_author": "Questock",
                "summary_kind": _NEWS_SUMMARY_KIND,
                "snapshot_sequence": index,
                "usage_note": (
                    "Source title and Questock-authored short summary only; "
                    "article body, description, and raw response are excluded."
                ),
            },
            ingestion_version=SERVICE_SNAPSHOT_INGESTION_VERSION,
        )
        documents.append(document)
        seen_ids.add(document_id)
        seen_urls.add(source_url)
        seen_times.add(published_at)
        band_counts[time_band] += 1
    expected_coverage = {
        "total": 5,
        "pre_market": band_counts["pre_market"],
        "intraday": band_counts["intraday"],
        "ready": (
            band_counts["pre_market"] >= 1
            and band_counts["intraday"] >= 2
        ),
    }
    if payload.get("coverage") != expected_coverage or not expected_coverage[
        "ready"
    ]:
        raise ServiceSnapshotValidationError(
            "news snapshot coverage is invalid"
        )
    return tuple(documents)


def _validate_manifest(value: object) -> dict[str, Any]:
    required = {
        "snapshot_type",
        "schema_version",
        "snapshot_id",
        "basis_at",
        "documents_file",
        "coverage_file",
        "permission_register_file",
        "documents_sha256",
        "coverage_sha256",
        "permission_register_sha256",
        "security_ids",
        "source_artifacts",
        "document_ids",
    }
    if (
        not isinstance(value, Mapping)
        or set(value) != required
        or value.get("snapshot_type") != SERVICE_SNAPSHOT_TYPE
        or value.get("schema_version") != SERVICE_SNAPSHOT_SCHEMA_VERSION
        or value.get("snapshot_id") != SERVICE_SNAPSHOT_ID
        or value.get("documents_file") != SERVICE_SNAPSHOT_DOCUMENTS_FILE
        or value.get("coverage_file") != SERVICE_SNAPSHOT_COVERAGE_FILE
        or value.get("permission_register_file")
        != SERVICE_SNAPSHOT_PERMISSION_FILE
        or value.get("security_ids") != list(SUPPORTED_SECURITY_IDS)
        or _SHA256_RE.fullmatch(str(value.get("documents_sha256"))) is None
        or _SHA256_RE.fullmatch(str(value.get("coverage_sha256"))) is None
        or _SHA256_RE.fullmatch(
            str(value.get("permission_register_sha256"))
        )
        is None
        or not isinstance(value.get("source_artifacts"), list)
        or not isinstance(value.get("document_ids"), list)
    ):
        raise ServiceSnapshotValidationError(
            "service snapshot manifest is invalid"
        )
    basis_at = _parse_utc_timestamp(value.get("basis_at"))
    if basis_at != SERVICE_SNAPSHOT_BASIS_AT:
        raise ServiceSnapshotValidationError(
            "service snapshot manifest is invalid"
        )
    document_ids = value["document_ids"]
    if (
        not document_ids
        or any(not isinstance(item, str) or not item for item in document_ids)
        or len(document_ids) != len(set(document_ids))
    ):
        raise ServiceSnapshotValidationError(
            "service snapshot manifest is invalid"
        )
    return {
        **dict(value),
        "basis_at": basis_at,
    }


def _validate_documents_payload(value: object) -> dict[str, Any]:
    if (
        not isinstance(value, Mapping)
        or set(value) != {"schema_version", "snapshot_id", "documents"}
        or value.get("schema_version") != SERVICE_SNAPSHOT_SCHEMA_VERSION
        or value.get("snapshot_id") != SERVICE_SNAPSHOT_ID
        or not isinstance(value.get("documents"), list)
        or not value["documents"]
    ):
        raise ServiceSnapshotValidationError(
            "service snapshot documents are invalid"
        )
    return dict(value)


def _validate_documents(
    values: Sequence[object],
    *,
    basis_at: datetime,
) -> tuple[FinancialDocument, ...]:
    documents: list[FinancialDocument] = []
    for value in values:
        if not isinstance(value, Mapping) or set(value) != set(
            FinancialDocument.model_fields
        ):
            raise ServiceSnapshotValidationError(
                "service snapshot document is invalid"
            )
        try:
            document = FinancialDocument.model_validate(value)
        except (ValidationError, TypeError, ValueError):
            raise ServiceSnapshotValidationError(
                "service snapshot document is invalid"
            ) from None
        if (
            document.primary_security_ids
            not in ([item] for item in SUPPORTED_SECURITY_IDS)
            or document.mentioned_security_ids
            or document.source_type not in _SOURCE_ORDER
            or document.published_at is None
            or document.published_at.tzinfo is None
            or document.published_at.utcoffset() != timedelta(0)
            or document.published_at > basis_at
        ):
            raise ServiceSnapshotValidationError(
                "service snapshot document is invalid"
            )
        if document.source_type == "news":
            _validate_final_news_document(document)
        elif document.source_type == "disclosure":
            _validate_final_disclosure_document(document)
        else:
            _validate_final_report_document(document)
        documents.append(document.model_copy(deep=True))
    if len(documents) != 54:
        raise ServiceSnapshotValidationError(
            "service snapshot document count is invalid"
        )
    return tuple(documents)


def _validate_final_news_document(document: FinancialDocument) -> None:
    security_id = document.primary_security_ids[0]
    sequence = document.metadata.get("snapshot_sequence")
    if (
        document.provider != _NEWS_PROVIDER
        or document.ingestion_version != SERVICE_SNAPSHOT_INGESTION_VERSION
        or not isinstance(sequence, int)
        or isinstance(sequence, bool)
        or sequence not in range(1, 6)
        or not document.title.strip()
        or len(document.title) > 300
        or not document.text.startswith(f"{_SECURITY_NAMES[security_id]}: ")
        or document.metadata.get("document_type") != "article"
        or document.metadata.get("content_origin") != _NEWS_SUMMARY_KIND
        or document.metadata.get("verification_status") != "human_approved"
        or document.metadata.get("summary_author") != "Questock"
        or document.metadata.get("summary_kind") != _NEWS_SUMMARY_KIND
        or set(document.locator)
        != {
            "provider",
            "source_url",
            "published_at",
            "time_band",
            "section",
        }
        or document.locator.get("source_url") != document.source_url
        or document.locator.get("provider") != _NEWS_PROVIDER
        or document.locator.get("section") != "Questock short summary"
        or document.locator.get("published_at")
        != _utc_timestamp(document.published_at)
        or document.locator.get("time_band")
        not in {"pre_market", "intraday"}
    ):
        raise ServiceSnapshotValidationError(
            "service snapshot news document is invalid"
        )
    _validate_public_url(document.source_url)


def _validate_final_disclosure_document(
    document: FinancialDocument,
) -> None:
    facts = document.locator.get("facts")
    receipt_no = document.locator.get("receipt_no")
    expected = next(
        (
            item
            for item in DISCLOSURE_INPUT_SPECS
            if item.security_id == document.primary_security_ids[0]
        ),
        None,
    )
    if (
        expected is None
        or document.provider != "recorded_disclosure"
        or document.ingestion_version != "disclosure-snapshot-fsc-v1"
        or receipt_no != expected.receipt_no
        or document.document_id != f"disclosure:{expected.receipt_no}"
        or document.source_url != expected.viewer_url
        or document.locator.get("viewer_url") != expected.viewer_url
        or document.locator.get("content_level")
        != "verified_body_facts"
        or not isinstance(facts, list)
        or len(facts) < 10
        or document.metadata.get("is_correction") is not False
        or document.metadata.get("has_subsequent_correction") is not False
        or document.metadata.get("is_withdrawn") is not False
    ):
        raise ServiceSnapshotValidationError(
            "service snapshot disclosure document is invalid"
        )
    _validate_public_url(document.source_url)
    for fact in facts:
        if (
            not isinstance(fact, Mapping)
            or not isinstance(fact.get("physical_pdf_page"), int)
            or fact["physical_pdf_page"] < 1
            or fact["physical_pdf_page"] > expected.pdf_page_count
            or not isinstance(fact.get("dart_printed_page"), int)
            or fact["dart_printed_page"] < 1
            or fact["dart_printed_page"] > expected.pdf_page_count
            or not isinstance(fact.get("section_path"), list)
            or not fact["section_path"]
        ):
            raise ServiceSnapshotValidationError(
                "service snapshot disclosure locator is invalid"
            )


def _validate_final_report_document(document: FinancialDocument) -> None:
    expected = next(
        (
            item
            for item in REPORT_INPUT_SPECS
            if item.security_id == document.primary_security_ids[0]
        ),
        None,
    )
    if (
        expected is None
        or document.provider != "manual_manifest"
        or document.ingestion_version != "report-ingest-m1-06-v1"
        or document.locator.get("manifest_id") != expected.manifest_id
        or not isinstance(document.locator.get("page"), int)
        or document.locator["page"] < 1
        or document.locator["page"] > expected.pdf_page_count
        or not isinstance(document.locator.get("section"), str)
        or not document.locator["section"].strip()
        or document.metadata.get("usage_review_status") != "approved"
        or document.metadata.get("corpus_ingest_allowed") is not True
        or document.metadata.get("external_llm_processing_allowed") is not False
        or document.metadata.get("hash_verification_status") != "verified"
        or document.metadata.get("manual_verification_status")
        != "verified_against_source"
    ):
        raise ServiceSnapshotValidationError(
            "service snapshot report document is invalid"
        )
    _validate_public_url(document.source_url)


def _calculate_coverage(
    documents: Sequence[FinancialDocument],
) -> dict[str, Any]:
    news_by_security: dict[str, dict[str, int]] = {}
    disclosure_by_security: dict[str, dict[str, int]] = {}
    report_by_security: dict[str, dict[str, int]] = {}
    for security_id in SUPPORTED_SECURITY_IDS:
        news = [
            item
            for item in documents
            if item.source_type == "news"
            and item.primary_security_ids == [security_id]
        ]
        disclosure = [
            item
            for item in documents
            if item.source_type == "disclosure"
            and item.primary_security_ids == [security_id]
        ]
        reports = [
            item
            for item in documents
            if item.source_type == "research_report"
            and item.primary_security_ids == [security_id]
        ]
        news_by_security[security_id] = {
            "document_count": len(news),
            "pre_market": sum(
                item.locator.get("time_band") == "pre_market"
                for item in news
            ),
            "intraday": sum(
                item.locator.get("time_band") == "intraday"
                for item in news
            ),
        }
        disclosure_by_security[security_id] = {
            "document_count": len(disclosure),
            "fact_count": sum(
                len(item.locator.get("facts", [])) for item in disclosure
            ),
        }
        report_by_security[security_id] = {
            "report_count": len(
                {
                    item.locator.get("manifest_id")
                    for item in reports
                }
            ),
            "section_document_count": len(reports),
        }
    coverage = {
        "news": {
            "document_count": sum(
                item["document_count"] for item in news_by_security.values()
            ),
            "per_security": news_by_security,
        },
        "disclosure": {
            "document_count": sum(
                item["document_count"]
                for item in disclosure_by_security.values()
            ),
            "per_security": disclosure_by_security,
        },
        "research_report": {
            "report_count": sum(
                item["report_count"] for item in report_by_security.values()
            ),
            "section_document_count": sum(
                item["section_document_count"]
                for item in report_by_security.values()
            ),
            "per_security": report_by_security,
        },
    }
    if (
        coverage["news"]["document_count"] != 15
        or coverage["disclosure"]["document_count"] != 3
        or coverage["research_report"]["report_count"] != 3
        or coverage["research_report"]["section_document_count"] != 36
        or any(
            value["document_count"] != 5
            or value["pre_market"] < 1
            or value["intraday"] < 2
            for value in news_by_security.values()
        )
        or any(
            value["document_count"] != 1 or value["fact_count"] < 10
            for value in disclosure_by_security.values()
        )
        or any(
            value["report_count"] != 1
            or value["section_document_count"] != 12
            for value in report_by_security.values()
        )
    ):
        raise ServiceSnapshotValidationError(
            "service snapshot coverage is incomplete"
        )
    return coverage


def _validate_source_artifacts(
    values: Sequence[object],
    *,
    documents: Sequence[FinancialDocument],
) -> None:
    if not isinstance(values, list) or len(values) != 9:
        raise ServiceSnapshotValidationError(
            "service snapshot source artifacts are invalid"
        )
    expected = _source_artifacts_from_documents(documents)
    for observed, canonical in zip(values, expected, strict=True):
        if (
            not isinstance(observed, Mapping)
            or set(observed) != set(canonical)
            or observed.get("source_type") != canonical["source_type"]
            or observed.get("security_id") != canonical["security_id"]
            or observed.get("schema_version") != canonical["schema_version"]
            or observed.get("document_count") != canonical["document_count"]
            or observed.get("report_count") != canonical["report_count"]
            or _SHA256_RE.fullmatch(str(observed.get("sha256"))) is None
        ):
            raise ServiceSnapshotValidationError(
                "service snapshot source artifacts are invalid"
            )


def _source_artifacts_from_documents(
    documents: Sequence[FinancialDocument],
) -> list[dict[str, Any]]:
    artifacts = []
    for security_id in SUPPORTED_SECURITY_IDS:
        for source_type in _SOURCE_ORDER:
            selected = [
                item
                for item in documents
                if item.source_type == source_type
                and item.primary_security_ids == [security_id]
            ]
            artifacts.append(
                {
                    "source_type": source_type,
                    "security_id": security_id,
                    "schema_version": _EXPECTED_SOURCE_SCHEMAS[source_type],
                    "sha256": "0" * 64,
                    "document_count": len(selected),
                    "report_count": (
                        len(
                            {
                                item.locator.get("manifest_id")
                                for item in selected
                            }
                        )
                        if source_type == "research_report"
                        else 0
                    ),
                }
            )
    return artifacts


def _permission_register() -> dict[str, Any]:
    return {
        "schema_version": SERVICE_SNAPSHOT_SCHEMA_VERSION,
        "snapshot_id": SERVICE_SNAPSHOT_ID,
        "sources": {
            "news": {
                "allowed_content": (
                    "source_title_and_questock_project_owned_short_summary"
                ),
                "article_body_runtime": "excluded",
                "human_owner_review_status": "approved",
                "raw_response_runtime": "excluded",
            },
            "disclosure": {
                "allowed_content": "verified_public_facts",
                "full_filing_body_runtime": "excluded",
                "human_owner_review_status": "approved",
            },
            "research_report": {
                "allowed_content": (
                    "metadata_verified_structured_facts_and_"
                    "questock_short_summaries"
                ),
                "corpus_ingest_allowed": True,
                "external_llm_processing_allowed": False,
                "source_excerpt_runtime": "excluded",
                "source_pdf_runtime": "excluded",
                "usage_review_status": "approved",
            },
        },
    }


def _validate_generated_evidence(
    *,
    directory: Path,
    checksum_bytes: bytes,
    validation_payload: object,
    snapshot: ServiceSnapshot,
) -> None:
    try:
        canonical_files = {
            name: (directory / name).read_bytes()
            for name in (
                "manifest.json",
                SERVICE_SNAPSHOT_DOCUMENTS_FILE,
                SERVICE_SNAPSHOT_COVERAGE_FILE,
                SERVICE_SNAPSHOT_PERMISSION_FILE,
            )
        }
    except OSError:
        raise ServiceSnapshotValidationError(
            "service snapshot evidence could not be loaded"
        ) from None
    if (
        type(checksum_bytes) is not bytes
        or checksum_bytes != build_snapshot_checksum(canonical_files)
        or validation_payload != build_snapshot_validation_report(snapshot)
    ):
        raise ServiceSnapshotValidationError(
            "service snapshot generated evidence is invalid"
        )


def _assert_safe_public_payload(value: object) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if _normalized_key(str(key)) in _FORBIDDEN_PUBLIC_KEYS:
                raise ServiceSnapshotValidationError(
                    "service snapshot contains forbidden source content"
                )
            _assert_safe_public_payload(nested)
        return
    if isinstance(value, list):
        for nested in value:
            _assert_safe_public_payload(nested)
        return
    if isinstance(value, str):
        if _looks_like_local_absolute_path(value):
            raise ServiceSnapshotValidationError(
                "service snapshot contains a local absolute path"
            )
        if value.startswith(("http://", "https://")):
            _validate_public_url(value)


def _validate_public_url(value: object) -> None:
    if not isinstance(value, str):
        raise ServiceSnapshotValidationError(
            "service snapshot public URL is invalid"
        )
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        _ = parsed.port
        query = parse_qsl(parsed.query, keep_blank_values=True)
    except (TypeError, ValueError):
        raise ServiceSnapshotValidationError(
            "service snapshot public URL is invalid"
        ) from None
    if (
        parsed.scheme not in {"http", "https"}
        or host is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise ServiceSnapshotValidationError(
            "service snapshot public URL is invalid"
        )
    for key, _value in query:
        if _normalized_key(unquote_plus(key)) in _CREDENTIAL_QUERY_KEYS:
            raise ServiceSnapshotValidationError(
                "service snapshot public URL is invalid"
            )


def _looks_like_local_absolute_path(value: str) -> bool:
    normalized = value.replace("\\", "/")
    return (
        value.startswith("file://")
        or value.startswith("\\\\")
        or bool(_WINDOWS_ABSOLUTE_PATH_RE.match(value))
        or normalized.startswith("/")
    )


def _normalized_key(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def _news_title(security_name: str, sequence: int) -> str:
    if sequence == 1:
        return f"{security_name} 최근 이슈 요약"
    return f"{security_name} 뉴스 근거 {sequence}"


def _parse_utc_timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ServiceSnapshotValidationError(
            "service snapshot timestamp is invalid"
        )
    try:
        parsed = datetime.fromisoformat(f"{value[:-1]}+00:00")
    except ValueError:
        raise ServiceSnapshotValidationError(
            "service snapshot timestamp is invalid"
        ) from None
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ServiceSnapshotValidationError(
            "service snapshot timestamp is invalid"
        )
    return parsed.astimezone(UTC)


def _utc_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "SERVICE_SNAPSHOT_BASIS_AT",
    "SERVICE_SNAPSHOT_CHECKSUM_FILE",
    "SERVICE_SNAPSHOT_COVERAGE_FILE",
    "SERVICE_SNAPSHOT_DOCUMENTS_FILE",
    "SERVICE_SNAPSHOT_ID",
    "SERVICE_SNAPSHOT_PERMISSION_FILE",
    "SERVICE_SNAPSHOT_ROOT",
    "SERVICE_SNAPSHOT_SCHEMA_VERSION",
    "SERVICE_SNAPSHOT_TYPE",
    "SERVICE_SNAPSHOT_VALIDATION_FILE",
    "SUPPORTED_SECURITY_IDS",
    "ServiceSnapshot",
    "ServiceSnapshotValidationError",
    "SnapshotSourcePayload",
    "build_service_snapshot",
    "build_service_snapshot_payloads",
    "build_snapshot_checksum",
    "build_snapshot_validation_report",
    "copy_service_snapshot",
    "load_service_snapshot",
    "load_snapshot_source",
    "serialize_service_snapshot_json",
]
