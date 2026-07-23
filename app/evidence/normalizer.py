from __future__ import annotations

import copy
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import parse_qsl, unquote_plus, urlsplit

from pydantic import ValidationError

from app.core.models import Evidence, FinancialDocument, ensure_evidence_matches_document

_WINDOWS_DRIVE_PATH = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z]:[\\/]")
_BACKSLASH_UNC_PATH = re.compile(r"\\\\[^\\/\s]+[\\/][^\\/\s]+")
_FORWARD_UNC_PATH = re.compile(r"(?<![A-Za-z0-9_:])//[^/\s]+/[^/\s]+")
_FILE_URL = re.compile(r"file://", re.IGNORECASE)
_POSIX_ABSOLUTE_PATH = re.compile(r"(?:^|[\s\"'()=\[\]{},;])/(?![/\s])")
_WHITESPACE = re.compile(r"\s+")
_QUERY_KEY_NORMALIZER = re.compile(r"[^a-z0-9]")
_CREDENTIAL_QUERY_KEYS = frozenset(
    {
        "accesstoken",
        "apikey",
        "authorization",
        "authtoken",
        "bearertoken",
        "clientsecret",
        "credential",
        "secret",
        "signature",
        "token",
        "xamzsignature",
        "xapikey",
    }
)


class EvidenceNormalizationError(ValueError):
    """Raised for malformed or unsafe public normalization inputs."""


def normalize_financial_document(document: FinancialDocument) -> Evidence:
    """Map one validated financial document to one evidence object."""
    if not isinstance(document, FinancialDocument):
        raise EvidenceNormalizationError("document must be a FinancialDocument")
    return _build_evidence(document)


def normalize_financial_documents(documents: Sequence[FinancialDocument]) -> list[Evidence]:
    """Normalize a document sequence without partial results on public failures."""
    if isinstance(documents, (str, bytes, bytearray, Mapping)) or not isinstance(documents, Sequence):
        raise EvidenceNormalizationError("documents must be a sequence")

    normalized: list[Evidence] = []
    for document in documents:
        if not isinstance(document, FinancialDocument):
            raise EvidenceNormalizationError("documents items are invalid")
        try:
            normalized.append(normalize_financial_document(document))
        except EvidenceNormalizationError:
            raise EvidenceNormalizationError("documents items are invalid") from None
    return normalized


def _build_evidence(document: FinancialDocument) -> Evidence:
    validated_document = _canonical_revalidate(document)
    _validate_document_scalars(validated_document)
    locator = _copy_and_validate_locator(validated_document.locator)
    scope, subject_security_ids = _map_attribution(validated_document)
    snippet = _normalize_snippet(validated_document.text)
    evidence_id = f"evidence:{validated_document.document_id}"
    _validate_emitted_values(validated_document, evidence_id, snippet, locator)

    try:
        evidence = Evidence(
            evidence_id=evidence_id,
            document_id=validated_document.document_id,
            source_type=validated_document.source_type,
            title=validated_document.title,
            source_url=validated_document.source_url,
            published_at=validated_document.published_at,
            subject_security_ids=subject_security_ids,
            mentioned_security_ids=list(validated_document.mentioned_security_ids),
            scope=scope,
            snippet=snippet,
            locator=locator,
            retrieval_score=None,
        )
    except ValidationError:
        raise EvidenceNormalizationError("evidence construction failed") from None

    ensure_evidence_matches_document(evidence, validated_document)
    _validate_final_output(evidence)
    return evidence


def _canonical_revalidate(document: FinancialDocument) -> FinancialDocument:
    try:
        values = {field_name: getattr(document, field_name) for field_name in FinancialDocument.model_fields}
    except AttributeError:
        raise EvidenceNormalizationError("financial document is invalid") from None

    try:
        return FinancialDocument.model_validate(values, strict=True)
    except ValidationError:
        raise EvidenceNormalizationError("financial document is invalid") from None


def _validate_document_scalars(document: FinancialDocument) -> None:
    if not isinstance(document.document_id, str) or not document.document_id.strip():
        raise EvidenceNormalizationError("financial document is invalid")
    if not isinstance(document.source_type, str) or not document.source_type.strip():
        raise EvidenceNormalizationError("financial document is invalid")
    if not isinstance(document.title, str) or not isinstance(document.text, str):
        raise EvidenceNormalizationError("financial document is invalid")
    if document.source_url is not None and not isinstance(document.source_url, str):
        raise EvidenceNormalizationError("financial document is invalid")


def _copy_and_validate_locator(locator: object) -> dict[str, Any]:
    if not isinstance(locator, Mapping) or not locator:
        raise EvidenceNormalizationError("document locator is invalid")
    try:
        json.dumps(locator, allow_nan=False)
    except (TypeError, ValueError):
        raise EvidenceNormalizationError("document locator is invalid") from None

    _validate_safe_value(locator, "document locator is invalid")
    copied = copy.deepcopy(locator)
    if not isinstance(copied, dict):
        raise EvidenceNormalizationError("document locator is invalid")
    return copied


def _map_attribution(document: FinancialDocument) -> tuple[str, list[str]]:
    primary_security_ids = document.primary_security_ids
    if len(primary_security_ids) == 1:
        return "company_specific", list(primary_security_ids)
    if len(primary_security_ids) >= 2:
        return "multi_company", list(primary_security_ids)
    return "industry_common", []


def _normalize_snippet(text: str) -> str:
    snippet = _WHITESPACE.sub(" ", text).strip()
    if not snippet:
        raise EvidenceNormalizationError("document text must not be blank")
    return snippet[:500]


def _validate_emitted_values(
    document: FinancialDocument,
    evidence_id: str,
    snippet: str,
    locator: dict[str, Any],
) -> None:
    for value in (document.document_id, evidence_id, document.source_type, document.title, snippet):
        _validate_safe_string(value, "document output is unsafe")
    if document.source_url is not None:
        _validate_safe_string(document.source_url, "document output is unsafe")
        _validate_source_url_safety(document.source_url)
    _validate_safe_value(locator, "document output is unsafe")


def _validate_source_url_safety(source_url: str) -> None:
    try:
        parsed = urlsplit(source_url)
    except ValueError:
        raise EvidenceNormalizationError("document output is unsafe") from None
    if parsed.username is not None or parsed.password is not None:
        raise EvidenceNormalizationError("document output is unsafe")
    for key, _ in parse_qsl(parsed.query, keep_blank_values=True):
        if _normalized_query_key(key) in _CREDENTIAL_QUERY_KEYS:
            raise EvidenceNormalizationError("document output is unsafe")


def _normalized_query_key(value: str) -> str:
    return _QUERY_KEY_NORMALIZER.sub("", unquote_plus(value).casefold())


def _validate_final_output(evidence: Evidence) -> None:
    serialized = evidence.model_dump(mode="json")
    _validate_safe_value(serialized, "document output is unsafe")
    try:
        json.dumps(serialized, allow_nan=False)
    except (TypeError, ValueError):
        raise EvidenceNormalizationError("document output is unsafe") from None


def _validate_safe_value(value: Any, message: str) -> None:
    if isinstance(value, str):
        _validate_safe_string(value, message)
        return
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if not isinstance(key, str):
                raise EvidenceNormalizationError(message)
            _validate_safe_string(key, message)
            _validate_safe_value(nested, message)
        return
    if isinstance(value, (list, tuple)):
        for nested in value:
            _validate_safe_value(nested, message)


def _validate_safe_string(value: str, message: str) -> None:
    if _contains_local_absolute_path(value):
        raise EvidenceNormalizationError(message)


def _contains_local_absolute_path(value: str) -> bool:
    return bool(
        _WINDOWS_DRIVE_PATH.search(value)
        or _BACKSLASH_UNC_PATH.search(value)
        or _FORWARD_UNC_PATH.search(value)
        or _FILE_URL.search(value)
        or _POSIX_ABSOLUTE_PATH.search(value)
    )


__all__ = [
    "EvidenceNormalizationError",
    "normalize_financial_document",
    "normalize_financial_documents",
]
