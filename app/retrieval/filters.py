from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import TypeVar
from zoneinfo import ZoneInfo

from app.core.models import Evidence, FinancialDocument, RetrievalRequest, ensure_evidence_matches_document

SEOUL_TZ = ZoneInfo("Asia/Seoul")
DOCUMENT_TYPE_METADATA_KEYS = ("document_type", "report_type", "content_level")

T = TypeVar("T")


class HardFilterValidationError(ValueError):
    """Raised when the public hard-filter input boundary is malformed."""


def filter_financial_documents(
    documents: Sequence[FinancialDocument],
    request: RetrievalRequest,
) -> list[FinancialDocument]:
    validated_request = _validate_request(request)
    validated_documents = _validate_sequence(documents, FinancialDocument, "documents")
    return [
        document
        for document in validated_documents
        if _document_structural_match(document, validated_request)
        and _date_in_range(document.published_at, validated_request)
    ]


def filter_evidence(
    evidence: Sequence[Evidence],
    request: RetrievalRequest,
    *,
    documents_by_id: Mapping[str, FinancialDocument] | None = None,
) -> list[Evidence]:
    validated_request = _validate_request(request)
    validated_evidence = _validate_sequence(evidence, Evidence, "evidence")
    validated_documents = _validate_documents_by_id(documents_by_id)

    filtered: list[Evidence] = []
    for item in validated_evidence:
        linked_document = _linked_document_for(item, validated_documents)
        if validated_documents is not None and linked_document is None:
            continue
        if item.source_type not in validated_request.source_types:
            continue
        if linked_document is not None and not _linked_document_integrity_match(item, linked_document, validated_request):
            continue
        if not _evidence_scope_match(item, validated_request, linked_document):
            continue
        if not _evidence_date_match(item, validated_request, linked_document):
            continue
        if not _evidence_document_type_match(validated_request, linked_document):
            continue
        filtered.append(item)
    return filtered


def _validate_request(request: RetrievalRequest) -> RetrievalRequest:
    if not isinstance(request, RetrievalRequest):
        raise HardFilterValidationError("request must be a RetrievalRequest")
    return request


def _validate_sequence(value: object, item_type: type[T], name: str) -> list[T]:
    if isinstance(value, (str, bytes, bytearray, Mapping)) or not isinstance(value, Sequence):
        raise HardFilterValidationError(f"{name} must be a sequence")
    items: list[T] = []
    for item in value:
        if not isinstance(item, item_type):
            raise HardFilterValidationError(f"{name} items are invalid")
        items.append(item)
    return items


def _validate_documents_by_id(
    documents_by_id: Mapping[str, FinancialDocument] | None,
) -> Mapping[str, FinancialDocument] | None:
    if documents_by_id is None:
        return None
    if not isinstance(documents_by_id, Mapping):
        raise HardFilterValidationError("documents_by_id must be a mapping")
    for key, document in documents_by_id.items():
        if not isinstance(key, str):
            raise HardFilterValidationError("documents_by_id keys are invalid")
        if not isinstance(document, FinancialDocument):
            raise HardFilterValidationError("documents_by_id values are invalid")
        if key != document.document_id:
            raise HardFilterValidationError("documents_by_id keys must match document IDs")
    return documents_by_id


def _document_structural_match(document: FinancialDocument, request: RetrievalRequest) -> bool:
    return (
        document.source_type in request.source_types
        and _document_has_target_connection(document, request.security_id)
        and _document_type_match(document, request)
    )


def _document_has_target_connection(document: FinancialDocument, security_id: str) -> bool:
    return security_id in document.primary_security_ids or security_id in document.mentioned_security_ids


def _document_type_match(document: FinancialDocument, request: RetrievalRequest) -> bool:
    if request.document_types is None:
        return True
    if not request.document_types:
        return False
    for key in DOCUMENT_TYPE_METADATA_KEYS:
        value = document.metadata.get(key)
        if isinstance(value, str) and value and value in request.document_types:
            return True
    return False


def _date_in_range(value: datetime | None, request: RetrievalRequest) -> bool:
    if request.date_range is None:
        return True
    if not _is_aware_datetime(value):
        return False
    local_day = value.astimezone(SEOUL_TZ).date()
    if request.date_range.start is not None and local_day < request.date_range.start:
        return False
    if request.date_range.end is not None and local_day > request.date_range.end:
        return False
    return True


def _linked_document_for(
    evidence: Evidence,
    documents_by_id: Mapping[str, FinancialDocument] | None,
) -> FinancialDocument | None:
    if documents_by_id is None:
        return None
    return documents_by_id.get(evidence.document_id)


def _linked_document_integrity_match(
    evidence: Evidence,
    linked_document: FinancialDocument,
    request: RetrievalRequest,
) -> bool:
    if evidence.source_type != linked_document.source_type:
        return False
    try:
        ensure_evidence_matches_document(evidence, linked_document)
    except ValueError:
        return False
    return _document_structural_match(linked_document, request)


def _evidence_scope_match(
    evidence: Evidence,
    request: RetrievalRequest,
    linked_document: FinancialDocument | None,
) -> bool:
    target = request.security_id
    if evidence.scope == "company_specific":
        return evidence.subject_security_ids == [target] and (
            linked_document is None or target in linked_document.primary_security_ids
        )
    if evidence.scope == "multi_company":
        return target in evidence.subject_security_ids and (
            linked_document is None
            or all(security_id in linked_document.primary_security_ids for security_id in evidence.subject_security_ids)
        )
    if evidence.scope == "industry_common":
        if evidence.subject_security_ids:
            return False
        if target in evidence.mentioned_security_ids:
            return True
        return linked_document is not None and _document_has_target_connection(linked_document, target)
    return False


def _evidence_date_match(
    evidence: Evidence,
    request: RetrievalRequest,
    linked_document: FinancialDocument | None,
) -> bool:
    if request.date_range is None:
        return True
    effective_timestamp = evidence.published_at if _is_aware_datetime(evidence.published_at) else None
    if effective_timestamp is None and linked_document is not None and _is_aware_datetime(linked_document.published_at):
        effective_timestamp = linked_document.published_at
    return _date_in_range(effective_timestamp, request)


def _evidence_document_type_match(
    request: RetrievalRequest,
    linked_document: FinancialDocument | None,
) -> bool:
    if request.document_types is None:
        return True
    return linked_document is not None and _document_type_match(linked_document, request)


def _is_aware_datetime(value: datetime | None) -> bool:
    return value is not None and value.tzinfo is not None and value.utcoffset() is not None


__all__ = [
    "HardFilterValidationError",
    "filter_evidence",
    "filter_financial_documents",
]
