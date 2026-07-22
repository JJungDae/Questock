from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from app.core.models import FinancialDocument

MANUAL_REPORT_PROVIDER = "manual_manifest"
REPORT_SOURCE_TYPE = "research_report"
REPORT_INGESTION_VERSION = "report-ingest-m1-06-v1"
SUPPORTED_SECURITY_IDS = frozenset({"KRX:005930", "KRX:000660", "KRX:005380"})
SEOUL_TZ = timezone(timedelta(hours=9))
FRESHNESS_POLICY_DAYS = 180

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MANIFEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")
_SEGMENT_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")
_SOURCE_ASSET_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_WINDOWS_ABSOLUTE_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")
_SECRET_QUERY_KEYS = {"api_key", "apikey", "token", "secret", "key", "auth", "credential"}

_MANIFEST_REQUIRED_FIELDS = frozenset(
    {
        "manifest_id",
        "security_id",
        "title",
        "publisher",
        "published_at",
        "source_url",
        "source_asset_id",
        "access_note",
        "usage_note",
        "usage_review_status",
        "corpus_ingest_allowed",
        "external_llm_processing_allowed",
        "file_hash",
        "hash_scope",
        "hash_verification_status",
        "documents",
        "ingestion_version",
    }
)
_MANIFEST_OPTIONAL_FIELDS = frozenset({"analyst", "report_type", "basis_date", "language"})
_MANIFEST_ALLOWED_FIELDS = _MANIFEST_REQUIRED_FIELDS | _MANIFEST_OPTIONAL_FIELDS

_DOCUMENT_REQUIRED_FIELDS = frozenset(
    {
        "manifest_id",
        "segment_id",
        "document_id",
        "security_id",
        "mentioned_security_ids",
        "subject_scope",
        "page",
        "page_basis",
        "section",
        "text",
        "text_kind",
        "manual_verification_status",
        "contains_numeric_claims",
        "numeric_claims_verified",
    }
)
_DOCUMENT_OPTIONAL_FIELDS = frozenset({"summary_kind"})
_DOCUMENT_ALLOWED_FIELDS = _DOCUMENT_REQUIRED_FIELDS | _DOCUMENT_OPTIONAL_FIELDS
_FORBIDDEN_DOCUMENT_REPORT_FIELDS = frozenset(
    {
        "title",
        "publisher",
        "published_at",
        "source_url",
        "source_asset_id",
        "access_note",
        "usage_note",
        "usage_review_status",
        "corpus_ingest_allowed",
        "external_llm_processing_allowed",
        "file_hash",
        "hash_scope",
        "hash_verification_status",
        "analyst",
        "report_type",
        "basis_date",
        "language",
        "ingestion_version",
    }
)

_USAGE_REVIEW_STATUSES = frozenset({"synthetic", "pending", "approved", "rejected"})
_HASH_SCOPES = frozenset({"source_asset_bytes", "normalized_source_bytes"})
_HASH_VERIFICATION_STATUSES = frozenset({"synthetic", "format_only", "verified"})
_SUBJECT_SCOPES = frozenset({"company_specific", "company_centered_with_mentions", "multi_company"})
_PAGE_BASES = frozenset({"pdf_1_based", "printed_page", "source_section_only"})
_TEXT_KINDS = frozenset({"source_excerpt", "manual_summary"})
_MANUAL_VERIFICATION_STATUSES = frozenset({"synthetic", "pending", "verified_against_source"})
_BUILD_MODES = frozenset({"synthetic_unit", "corpus"})


class ReportIngestValidationError(ValueError):
    """Raised when a manual research report ingest contract is violated."""


class ReportManifestValidationError(ReportIngestValidationError):
    """Raised when a manifest is invalid."""


class ReportDocumentValidationError(ReportIngestValidationError):
    """Raised when a normalized report section is invalid."""


class ReportBundleValidationError(ReportIngestValidationError):
    """Raised when a manifest/document bundle is inconsistent."""


@dataclass(frozen=True)
class ParsedPublicationDate:
    published_at: datetime
    precision: str
    timezone_basis: str
    local_date: date


@dataclass(frozen=True)
class ReportManifest:
    manifest_id: str
    security_id: str
    title: str
    publisher: str
    published_at: datetime
    published_at_precision: str
    published_at_timezone_basis: str
    published_local_date: date
    source_url: str | None
    source_asset_id: str | None
    access_note: str
    usage_note: str
    usage_review_status: str
    corpus_ingest_allowed: bool
    external_llm_processing_allowed: bool
    file_hash: str
    hash_scope: str
    hash_verification_status: str
    documents: tuple[str, ...]
    ingestion_version: str
    analyst: str | None = None
    report_type: str | None = None
    basis_date: date | None = None
    language: str | None = None


@dataclass(frozen=True)
class NormalizedReportDocument:
    manifest_id: str
    segment_id: str
    document_id: str
    security_id: str
    mentioned_security_ids: tuple[str, ...]
    subject_scope: str
    page: int
    page_basis: str
    section: str
    text: str
    text_kind: str
    manual_verification_status: str
    contains_numeric_claims: bool
    numeric_claims_verified: bool
    summary_kind: str | None = None


@dataclass(frozen=True)
class NormalizedReportDocumentBundle:
    manifest_id: str
    fixture_type: str
    documents: tuple[NormalizedReportDocument, ...]


def load_report_manifest(path: str | Path) -> ReportManifest:
    data = _load_json_object(path)
    return validate_report_manifest(data)


def load_normalized_report_documents(path: str | Path) -> NormalizedReportDocumentBundle:
    data = _load_json_object(path)
    missing = {"fixture_version", "fixture_type", "manifest_id", "documents"} - set(data)
    if missing:
        raise ReportDocumentValidationError("normalized report wrapper is missing required fields")
    extra = set(data) - {"fixture_version", "fixture_type", "manifest_id", "documents"}
    if extra:
        raise ReportDocumentValidationError("normalized report wrapper contains unsupported fields")
    fixture_type = _required_str(data, "fixture_type", ReportDocumentValidationError)
    manifest_id = _required_str(data, "manifest_id", ReportDocumentValidationError)
    if fixture_type != "synthetic_unit":
        raise ReportDocumentValidationError("normalized report fixture_type is not supported")
    raw_documents = data["documents"]
    if not isinstance(raw_documents, list) or not raw_documents:
        raise ReportDocumentValidationError("normalized report documents must be a non-empty list")
    documents = tuple(validate_normalized_report_document(item) for item in raw_documents)
    if any(document.manifest_id != manifest_id for document in documents):
        raise ReportDocumentValidationError("normalized report document manifest_id mismatch")
    return NormalizedReportDocumentBundle(manifest_id=manifest_id, fixture_type=fixture_type, documents=documents)


def validate_report_manifest(raw_manifest: Mapping[str, Any]) -> ReportManifest:
    if not isinstance(raw_manifest, Mapping):
        raise ReportManifestValidationError("report manifest must be an object")
    missing = _MANIFEST_REQUIRED_FIELDS - set(raw_manifest)
    if missing:
        raise ReportManifestValidationError("report manifest is missing required fields")
    extra = set(raw_manifest) - _MANIFEST_ALLOWED_FIELDS
    if extra:
        raise ReportManifestValidationError("report manifest contains unsupported fields")

    manifest_id = _required_str(raw_manifest, "manifest_id", ReportManifestValidationError)
    if not _MANIFEST_ID_RE.fullmatch(manifest_id):
        raise ReportManifestValidationError("report manifest_id must be a stable opaque id")
    security_id = _supported_security_id(raw_manifest.get("security_id"), ReportManifestValidationError)
    title = _required_str(raw_manifest, "title", ReportManifestValidationError)
    publisher = _required_str(raw_manifest, "publisher", ReportManifestValidationError)
    parsed_date = _parse_published_at(raw_manifest.get("published_at"))
    source_url = _optional_url(raw_manifest.get("source_url"), ReportManifestValidationError)
    source_asset_id = _optional_source_asset_id(raw_manifest.get("source_asset_id"), ReportManifestValidationError)
    if source_url is None and source_asset_id is None:
        raise ReportManifestValidationError("source_url or source_asset_id is required")
    access_note = _required_str(raw_manifest, "access_note", ReportManifestValidationError)
    usage_note = _required_str(raw_manifest, "usage_note", ReportManifestValidationError)
    usage_review_status = _enum_value(
        raw_manifest.get("usage_review_status"),
        _USAGE_REVIEW_STATUSES,
        "usage_review_status",
        ReportManifestValidationError,
    )
    corpus_ingest_allowed = _required_bool(raw_manifest, "corpus_ingest_allowed", ReportManifestValidationError)
    external_llm_processing_allowed = _required_bool(
        raw_manifest, "external_llm_processing_allowed", ReportManifestValidationError
    )
    _validate_permission_gate(
        usage_review_status=usage_review_status,
        corpus_ingest_allowed=corpus_ingest_allowed,
        external_llm_processing_allowed=external_llm_processing_allowed,
    )
    file_hash = _required_str(raw_manifest, "file_hash", ReportManifestValidationError)
    if not _SHA256_RE.fullmatch(file_hash):
        raise ReportManifestValidationError("file_hash must be lowercase SHA-256")
    hash_scope = _enum_value(raw_manifest.get("hash_scope"), _HASH_SCOPES, "hash_scope", ReportManifestValidationError)
    hash_verification_status = _enum_value(
        raw_manifest.get("hash_verification_status"),
        _HASH_VERIFICATION_STATUSES,
        "hash_verification_status",
        ReportManifestValidationError,
    )
    raw_documents = raw_manifest.get("documents")
    if not isinstance(raw_documents, list) or not raw_documents:
        raise ReportManifestValidationError("manifest documents must be a non-empty list")
    document_ids = tuple(_required_list_str(value, ReportManifestValidationError) for value in raw_documents)
    if len(set(document_ids)) != len(document_ids):
        raise ReportManifestValidationError("manifest documents must not contain duplicates")
    if any(not document_id.startswith(f"report:{manifest_id}:") for document_id in document_ids):
        raise ReportManifestValidationError("manifest document ids must be deterministic report ids")
    ingestion_version = _required_str(raw_manifest, "ingestion_version", ReportManifestValidationError)
    if ingestion_version != REPORT_INGESTION_VERSION:
        raise ReportManifestValidationError("report manifest ingestion_version is unsupported")
    basis_date = _optional_date(raw_manifest.get("basis_date"), ReportManifestValidationError)
    return ReportManifest(
        manifest_id=manifest_id,
        security_id=security_id,
        title=title,
        publisher=publisher,
        published_at=parsed_date.published_at,
        published_at_precision=parsed_date.precision,
        published_at_timezone_basis=parsed_date.timezone_basis,
        published_local_date=parsed_date.local_date,
        source_url=source_url,
        source_asset_id=source_asset_id,
        access_note=access_note,
        usage_note=usage_note,
        usage_review_status=usage_review_status,
        corpus_ingest_allowed=corpus_ingest_allowed,
        external_llm_processing_allowed=external_llm_processing_allowed,
        file_hash=file_hash,
        hash_scope=hash_scope,
        hash_verification_status=hash_verification_status,
        documents=document_ids,
        ingestion_version=ingestion_version,
        analyst=_optional_str(raw_manifest.get("analyst"), ReportManifestValidationError),
        report_type=_optional_str(raw_manifest.get("report_type"), ReportManifestValidationError),
        basis_date=basis_date,
        language=_optional_str(raw_manifest.get("language"), ReportManifestValidationError),
    )


def validate_normalized_report_document(raw_document: Mapping[str, Any]) -> NormalizedReportDocument:
    if not isinstance(raw_document, Mapping):
        raise ReportDocumentValidationError("normalized report document must be an object")
    if _FORBIDDEN_DOCUMENT_REPORT_FIELDS & set(raw_document):
        raise ReportDocumentValidationError("normalized report document must not repeat report-level fields")
    missing = _DOCUMENT_REQUIRED_FIELDS - set(raw_document)
    if missing:
        raise ReportDocumentValidationError("normalized report document is missing required fields")
    extra = set(raw_document) - _DOCUMENT_ALLOWED_FIELDS
    if extra:
        raise ReportDocumentValidationError("normalized report document contains unsupported fields")

    manifest_id = _required_str(raw_document, "manifest_id", ReportDocumentValidationError)
    if not _MANIFEST_ID_RE.fullmatch(manifest_id):
        raise ReportDocumentValidationError("document manifest_id must be a stable opaque id")
    segment_id = _required_str(raw_document, "segment_id", ReportDocumentValidationError)
    if not _SEGMENT_ID_RE.fullmatch(segment_id):
        raise ReportDocumentValidationError("segment_id must be a stable opaque id")
    expected_document_id = f"report:{manifest_id}:{segment_id}"
    document_id = _required_str(raw_document, "document_id", ReportDocumentValidationError)
    if document_id != expected_document_id:
        raise ReportDocumentValidationError("document_id must be deterministic")
    security_id = _supported_security_id(raw_document.get("security_id"), ReportDocumentValidationError)
    mentioned_security_ids = _security_id_tuple(raw_document.get("mentioned_security_ids"))
    if security_id in mentioned_security_ids:
        raise ReportDocumentValidationError("primary security_id must not appear in mentioned_security_ids")
    subject_scope = _enum_value(
        raw_document.get("subject_scope"), _SUBJECT_SCOPES, "subject_scope", ReportDocumentValidationError
    )
    if subject_scope == "multi_company":
        raise ReportDocumentValidationError("multi_company report sections are excluded in P0")
    if subject_scope == "company_specific" and mentioned_security_ids:
        raise ReportDocumentValidationError("company_specific report sections must not have mentions")
    if subject_scope == "company_centered_with_mentions" and not mentioned_security_ids:
        raise ReportDocumentValidationError("company_centered_with_mentions sections require mentions")
    page = _positive_int(raw_document.get("page"), "page", ReportDocumentValidationError)
    page_basis = _enum_value(raw_document.get("page_basis"), _PAGE_BASES, "page_basis", ReportDocumentValidationError)
    section = _required_str(raw_document, "section", ReportDocumentValidationError)
    text = _required_str(raw_document, "text", ReportDocumentValidationError)
    text_kind = _enum_value(raw_document.get("text_kind"), _TEXT_KINDS, "text_kind", ReportDocumentValidationError)
    manual_verification_status = _enum_value(
        raw_document.get("manual_verification_status"),
        _MANUAL_VERIFICATION_STATUSES,
        "manual_verification_status",
        ReportDocumentValidationError,
    )
    contains_numeric_claims = _required_bool(raw_document, "contains_numeric_claims", ReportDocumentValidationError)
    numeric_claims_verified = _required_bool(raw_document, "numeric_claims_verified", ReportDocumentValidationError)
    if not contains_numeric_claims and numeric_claims_verified:
        raise ReportDocumentValidationError("numeric_claims_verified requires numeric claims")
    return NormalizedReportDocument(
        manifest_id=manifest_id,
        segment_id=segment_id,
        document_id=document_id,
        security_id=security_id,
        mentioned_security_ids=mentioned_security_ids,
        subject_scope=subject_scope,
        page=page,
        page_basis=page_basis,
        section=section,
        text=text,
        text_kind=text_kind,
        manual_verification_status=manual_verification_status,
        contains_numeric_claims=contains_numeric_claims,
        numeric_claims_verified=numeric_claims_verified,
        summary_kind=_optional_str(raw_document.get("summary_kind"), ReportDocumentValidationError),
    )


def validate_report_bundle(
    manifest: ReportManifest,
    documents: NormalizedReportDocumentBundle | Sequence[NormalizedReportDocument],
) -> tuple[NormalizedReportDocument, ...]:
    normalized_documents = _document_tuple(documents)
    if not normalized_documents:
        raise ReportBundleValidationError("report bundle must include documents")
    if len({document.document_id for document in normalized_documents}) != len(normalized_documents):
        raise ReportBundleValidationError("report bundle document ids must be unique")
    by_id = {document.document_id: document for document in normalized_documents}
    if set(by_id) != set(manifest.documents):
        raise ReportBundleValidationError("report bundle documents must match manifest document list")
    ordered = tuple(by_id[document_id] for document_id in manifest.documents)
    for document in ordered:
        if document.manifest_id != manifest.manifest_id:
            raise ReportBundleValidationError("report document manifest_id mismatch")
        if document.security_id != manifest.security_id:
            raise ReportBundleValidationError("report document security_id mismatch")
    return ordered


def verify_manifest_source_hash(manifest: ReportManifest, source_bytes: bytes | None) -> bool:
    if source_bytes is None:
        raise ReportManifestValidationError("source bytes are required for hash verification")
    return hashlib.sha256(source_bytes).hexdigest() == manifest.file_hash


def normalize_manual_research_report(
    manifest: ReportManifest,
    document: NormalizedReportDocument,
    *,
    mode: str,
    as_of_date: date,
    source_bytes: bytes | None = None,
    available_asset_ids: set[str] | None = None,
) -> FinancialDocument:
    wrapped_documents: NormalizedReportDocumentBundle | list[NormalizedReportDocument]
    if mode == "synthetic_unit":
        wrapped_documents = NormalizedReportDocumentBundle(
            manifest_id=document.manifest_id,
            fixture_type="synthetic_unit",
            documents=(document,),
        )
    else:
        wrapped_documents = [document]
    return build_manual_research_documents(
        manifest,
        wrapped_documents,
        mode=mode,
        as_of_date=as_of_date,
        source_bytes=source_bytes,
        available_asset_ids=available_asset_ids,
    )[0]


def build_manual_research_documents(
    manifest: ReportManifest,
    documents: NormalizedReportDocumentBundle | Sequence[NormalizedReportDocument],
    *,
    mode: str,
    as_of_date: date,
    source_bytes: bytes | None = None,
    available_asset_ids: set[str] | None = None,
) -> list[FinancialDocument]:
    if mode not in _BUILD_MODES:
        raise ReportIngestValidationError("report build mode is unsupported")
    if not isinstance(as_of_date, date) or isinstance(as_of_date, datetime):
        raise ReportIngestValidationError("as_of_date must be a date")
    ordered_documents = validate_report_bundle(manifest, documents)
    if manifest.published_local_date > as_of_date:
        raise ReportIngestValidationError("published_at must not be in the future")
    if mode == "synthetic_unit":
        _validate_synthetic_build(manifest, ordered_documents, documents)
    else:
        _validate_corpus_build(
            manifest,
            ordered_documents,
            source_bytes=source_bytes,
            available_asset_ids=available_asset_ids,
        )
    return [
        _build_financial_document(manifest, document, mode=mode, as_of_date=as_of_date)
        for document in ordered_documents
    ]


def calculate_report_coverage(
    manifests: Iterable[ReportManifest],
    documents_by_manifest: Mapping[str, NormalizedReportDocumentBundle | Sequence[NormalizedReportDocument]],
    *,
    as_of_date: date,
    source_bytes_by_manifest: Mapping[str, bytes] | None = None,
    available_asset_ids: set[str] | None = None,
) -> dict[str, int]:
    coverage = {security_id: 0 for security_id in sorted(SUPPORTED_SECURITY_IDS)}
    seen_manifest_ids: set[str] = set()
    for manifest in manifests:
        if manifest.manifest_id in seen_manifest_ids:
            continue
        seen_manifest_ids.add(manifest.manifest_id)
        documents = documents_by_manifest.get(manifest.manifest_id)
        if documents is None:
            continue
        source_bytes = None if source_bytes_by_manifest is None else source_bytes_by_manifest.get(manifest.manifest_id)
        try:
            build_manual_research_documents(
                manifest,
                documents,
                mode="corpus",
                as_of_date=as_of_date,
                source_bytes=source_bytes,
                available_asset_ids=available_asset_ids,
            )
        except ReportIngestValidationError:
            continue
        coverage[manifest.security_id] += 1
    return coverage


def _load_json_object(path: str | Path) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReportIngestValidationError("report ingest JSON is malformed") from exc
    if not isinstance(data, dict):
        raise ReportIngestValidationError("report ingest JSON must be an object")
    return data


def _required_str(raw: Mapping[str, Any], field: str, error_type: type[ReportIngestValidationError]) -> str:
    value = raw.get(field)
    if not isinstance(value, str):
        raise error_type(f"{field} must be a string")
    cleaned = value.strip()
    if not cleaned:
        raise error_type(f"{field} must not be blank")
    if _looks_like_local_absolute_path(cleaned):
        raise error_type(f"{field} must not expose a local absolute path")
    return cleaned


def _required_list_str(value: Any, error_type: type[ReportIngestValidationError]) -> str:
    if not isinstance(value, str):
        raise error_type("list item must be a string")
    cleaned = value.strip()
    if not cleaned:
        raise error_type("list item must not be blank")
    if _looks_like_local_absolute_path(cleaned):
        raise error_type("list item must not expose a local absolute path")
    return cleaned


def _optional_str(value: Any, error_type: type[ReportIngestValidationError]) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise error_type("optional string field must be a string or null")
    cleaned = value.strip()
    if not cleaned:
        return None
    if _looks_like_local_absolute_path(cleaned):
        raise error_type("optional string field must not expose a local absolute path")
    return cleaned


def _required_bool(raw: Mapping[str, Any], field: str, error_type: type[ReportIngestValidationError]) -> bool:
    value = raw.get(field)
    if type(value) is not bool:
        raise error_type(f"{field} must be a boolean")
    return value


def _enum_value(
    value: Any,
    allowed: frozenset[str],
    field: str,
    error_type: type[ReportIngestValidationError],
) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise error_type(f"{field} is unsupported")
    return value


def _supported_security_id(value: Any, error_type: type[ReportIngestValidationError]) -> str:
    if not isinstance(value, str) or value not in SUPPORTED_SECURITY_IDS:
        raise error_type("security_id is unsupported")
    return value


def _security_id_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ReportDocumentValidationError("mentioned_security_ids must be a list")
    security_ids = tuple(_supported_security_id(item, ReportDocumentValidationError) for item in value)
    if len(set(security_ids)) != len(security_ids):
        raise ReportDocumentValidationError("mentioned_security_ids must not contain duplicates")
    return security_ids


def _positive_int(value: Any, field: str, error_type: type[ReportIngestValidationError]) -> int:
    if type(value) is not int or value <= 0:
        raise error_type(f"{field} must be a positive integer")
    return value


def _parse_published_at(value: Any) -> ParsedPublicationDate:
    if not isinstance(value, str) or not value.strip():
        raise ReportManifestValidationError("published_at must be a string")
    text = value.strip()
    if _DATE_RE.fullmatch(text):
        try:
            local_day = date.fromisoformat(text)
        except ValueError as exc:
            raise ReportManifestValidationError("published_at date is invalid") from exc
        published_at = datetime.combine(local_day, time.min, tzinfo=SEOUL_TZ).astimezone(UTC)
        return ParsedPublicationDate(
            published_at=published_at,
            precision="date",
            timezone_basis="Asia/Seoul",
            local_date=local_day,
        )
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReportManifestValidationError("published_at datetime is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ReportManifestValidationError("published_at datetime must include timezone")
    published_at = parsed.astimezone(UTC)
    return ParsedPublicationDate(
        published_at=published_at,
        precision="datetime",
        timezone_basis="RFC3339",
        local_date=published_at.astimezone(SEOUL_TZ).date(),
    )


def _optional_date(value: Any, error_type: type[ReportIngestValidationError]) -> date | None:
    if value is None:
        return None
    if not isinstance(value, str) or not _DATE_RE.fullmatch(value):
        raise error_type("basis_date must be YYYY-MM-DD or null")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise error_type("basis_date is invalid") from exc


def _optional_url(value: Any, error_type: type[ReportIngestValidationError]) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise error_type("source_url must be an HTTP(S) URL or null")
    text = value.strip()
    if _looks_like_local_absolute_path(text):
        raise error_type("source_url must not expose a local absolute path")
    try:
        parts = urlsplit(text)
    except ValueError as exc:
        raise error_type("source_url is invalid") from exc
    scheme = parts.scheme.lower()
    if scheme not in {"http", "https"}:
        raise error_type("source_url must be HTTP(S)")
    if parts.hostname is None:
        raise error_type("source_url must include a host")
    if parts.username is not None or parts.password is not None:
        raise error_type("source_url must not include userinfo")
    try:
        port = parts.port
    except ValueError as exc:
        raise error_type("source_url port is invalid") from exc
    if parts.fragment:
        raise error_type("source_url must not include a fragment")
    for key, _ in parse_qsl(parts.query, keep_blank_values=True):
        if key.strip().casefold() in _SECRET_QUERY_KEYS:
            raise error_type("source_url must not include credential query parameters")
    host = parts.hostname.lower()
    default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    netloc = host if port is None or default_port else f"{host}:{port}"
    return urlunsplit((scheme, netloc, parts.path, parts.query, ""))


def _optional_source_asset_id(value: Any, error_type: type[ReportIngestValidationError]) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise error_type("source_asset_id must be a stable opaque id or null")
    source_asset_id = value.strip()
    if not _SOURCE_ASSET_ID_RE.fullmatch(source_asset_id) or _looks_like_local_absolute_path(source_asset_id):
        raise error_type("source_asset_id must be a stable opaque id")
    return source_asset_id


def _looks_like_local_absolute_path(value: str) -> bool:
    normalized = value.replace("\\", "/")
    return (
        value.startswith("file://")
        or value.startswith("\\\\")
        or bool(_WINDOWS_ABSOLUTE_PATH_RE.match(value))
        or normalized.startswith("/")
    )


def _validate_permission_gate(
    *,
    usage_review_status: str,
    corpus_ingest_allowed: bool,
    external_llm_processing_allowed: bool,
) -> None:
    if usage_review_status in {"synthetic", "pending", "rejected"}:
        if corpus_ingest_allowed or external_llm_processing_allowed:
            raise ReportManifestValidationError("unapproved report permissions must be closed")
    if external_llm_processing_allowed and (usage_review_status != "approved" or not corpus_ingest_allowed):
        raise ReportManifestValidationError("external LLM processing requires approved corpus ingest")


def _document_tuple(
    documents: NormalizedReportDocumentBundle | Sequence[NormalizedReportDocument],
) -> tuple[NormalizedReportDocument, ...]:
    if isinstance(documents, NormalizedReportDocumentBundle):
        return documents.documents
    return tuple(documents)


def _validate_synthetic_build(
    manifest: ReportManifest,
    documents: Sequence[NormalizedReportDocument],
    raw_documents: NormalizedReportDocumentBundle | Sequence[NormalizedReportDocument],
) -> None:
    if not isinstance(raw_documents, NormalizedReportDocumentBundle) or raw_documents.fixture_type != "synthetic_unit":
        raise ReportBundleValidationError("synthetic build requires synthetic_unit fixture")
    if manifest.usage_review_status != "synthetic":
        raise ReportBundleValidationError("synthetic build requires synthetic usage review status")
    if manifest.corpus_ingest_allowed or manifest.external_llm_processing_allowed:
        raise ReportBundleValidationError("synthetic build permissions must be closed")
    if manifest.hash_verification_status != "synthetic":
        raise ReportBundleValidationError("synthetic build requires synthetic hash status")
    if any(document.manual_verification_status != "synthetic" for document in documents):
        raise ReportBundleValidationError("synthetic build requires synthetic document verification")


def _validate_corpus_build(
    manifest: ReportManifest,
    documents: Sequence[NormalizedReportDocument],
    *,
    source_bytes: bytes | None,
    available_asset_ids: set[str] | None,
) -> None:
    if manifest.usage_review_status != "approved":
        raise ReportBundleValidationError("corpus build requires approved usage review")
    if not manifest.corpus_ingest_allowed:
        raise ReportBundleValidationError("corpus build requires corpus ingest permission")
    if manifest.hash_verification_status != "verified":
        raise ReportBundleValidationError("corpus build requires verified source hash")
    if any(document.manual_verification_status != "verified_against_source" for document in documents):
        raise ReportBundleValidationError("corpus build requires source-verified documents")
    if manifest.source_url is None and (
        manifest.source_asset_id is None or available_asset_ids is None or manifest.source_asset_id not in available_asset_ids
    ):
        raise ReportBundleValidationError("corpus build requires resolvable source locator")
    if not verify_manifest_source_hash(manifest, source_bytes):
        raise ReportBundleValidationError("corpus build source hash mismatch")


def _build_financial_document(
    manifest: ReportManifest,
    document: NormalizedReportDocument,
    *,
    mode: str,
    as_of_date: date,
) -> FinancialDocument:
    age_days = (as_of_date - manifest.published_local_date).days
    title = manifest.title if document.section == manifest.title else f"{manifest.title} - {document.section}"
    locator = {
        "manifest_id": manifest.manifest_id,
        "document_id": document.document_id,
        "page": document.page,
        "page_basis": document.page_basis,
        "section": document.section,
        "publisher": manifest.publisher,
        "source_url": manifest.source_url,
        "source_asset_id": manifest.source_asset_id,
        "access_note": manifest.access_note,
    }
    metadata = {
        "content_level": "research_report_section",
        "publisher": manifest.publisher,
        "analyst": manifest.analyst,
        "report_type": manifest.report_type,
        "basis_date": manifest.basis_date.isoformat() if manifest.basis_date is not None else None,
        "language": manifest.language,
        "usage_note": manifest.usage_note,
        "usage_review_status": manifest.usage_review_status,
        "corpus_ingest_allowed": manifest.corpus_ingest_allowed,
        "external_llm_processing_allowed": manifest.external_llm_processing_allowed,
        "file_hash": manifest.file_hash,
        "hash_scope": manifest.hash_scope,
        "hash_verification_status": manifest.hash_verification_status,
        "published_at_precision": manifest.published_at_precision,
        "timezone_basis": manifest.published_at_timezone_basis,
        "freshness_as_of": as_of_date.isoformat(),
        "age_days": age_days,
        "freshness_policy_days": FRESHNESS_POLICY_DAYS,
        "is_stale_candidate": age_days > FRESHNESS_POLICY_DAYS,
        "text_kind": document.text_kind,
        "manual_verification_status": document.manual_verification_status,
        "summary_kind": document.summary_kind,
        "subject_scope": document.subject_scope,
        "contains_numeric_claims": document.contains_numeric_claims,
        "numeric_claims_verified": document.numeric_claims_verified,
        "build_mode": mode,
    }
    return FinancialDocument(
        document_id=document.document_id,
        source_type=REPORT_SOURCE_TYPE,
        provider=MANUAL_REPORT_PROVIDER,
        primary_security_ids=[manifest.security_id],
        mentioned_security_ids=list(document.mentioned_security_ids),
        title=title,
        published_at=manifest.published_at,
        source_url=manifest.source_url,
        text=document.text,
        locator=locator,
        metadata=metadata,
        ingestion_version=REPORT_INGESTION_VERSION,
    )


__all__ = [
    "FRESHNESS_POLICY_DAYS",
    "MANUAL_REPORT_PROVIDER",
    "REPORT_INGESTION_VERSION",
    "REPORT_SOURCE_TYPE",
    "SUPPORTED_SECURITY_IDS",
    "NormalizedReportDocument",
    "NormalizedReportDocumentBundle",
    "ReportBundleValidationError",
    "ReportDocumentValidationError",
    "ReportIngestValidationError",
    "ReportManifest",
    "ReportManifestValidationError",
    "build_manual_research_documents",
    "calculate_report_coverage",
    "load_normalized_report_documents",
    "load_report_manifest",
    "normalize_manual_research_report",
    "validate_report_bundle",
    "validate_report_manifest",
    "validate_normalized_report_document",
    "verify_manifest_source_hash",
]
