from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.core.models import FinancialDocument, QueryPlan
from app.core.status import ProviderStatus
from app.providers.base import create_provider_result
from app.services.source_gateway import (
    SourceGatewayResult,
    SourceGatewayTimeoutDescriptor,
    validate_source_gateway_result,
)

_CORPUS_TYPE = "recorded_demo"
_SCHEMA_VERSION = "b9-recorded-v1"
_DOCUMENTS_FILE = "documents.json"
_INGESTION_VERSION = "demo-corpus-b9-v1"
_SUPPORTED_SOURCES = frozenset({"news", "disclosure", "research_report"})
_SYNTHETIC_ORIGIN = "synthetic_project_owned"
_VERIFIED_ORIGIN = "verified_public_recorded"
_DEFAULT_MANIFEST_PATH = Path("data/demo/manifest.json")
_DEFAULT_DOCUMENTS_PATH = Path("data/demo/documents.json")
_RECEIPT_NO = re.compile(r"^\d{14}$")


class DemoCorpusValidationError(ValueError):
    """Raised when recorded demo data violates the project-owned contract."""


@dataclass(frozen=True)
class DemoCorpus:
    corpus_type: str
    schema_version: str
    basis_at: datetime
    documents: tuple[FinancialDocument, ...]


def load_demo_corpus(
    manifest_path: Path = _DEFAULT_MANIFEST_PATH,
    documents_path: Path = _DEFAULT_DOCUMENTS_PATH,
) -> DemoCorpus:
    manifest = _load_json_object(manifest_path)
    payload = _load_json_object(documents_path)
    return build_demo_corpus(manifest, payload)


def build_demo_corpus(
    manifest: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> DemoCorpus:
    canonical_manifest = _validate_manifest(manifest)
    canonical_payload = _validate_payload(payload)
    documents = tuple(
        _validate_document(item)
        for item in canonical_payload["documents"]
    )
    document_ids = tuple(item.document_id for item in documents)
    if (
        len(document_ids) != len(set(document_ids))
        or document_ids != tuple(canonical_manifest["document_ids"])
    ):
        raise DemoCorpusValidationError("demo document identity is invalid")
    return DemoCorpus(
        corpus_type=_CORPUS_TYPE,
        schema_version=_SCHEMA_VERSION,
        basis_at=canonical_manifest["basis_at"],
        documents=tuple(item.model_copy(deep=True) for item in documents),
    )


class RecordedDemoSourceGateway:
    timeout_descriptor = SourceGatewayTimeoutDescriptor(
        data_mode="recorded",
        live_connectivity_checked=False,
    )

    def __init__(self, corpus: DemoCorpus) -> None:
        self._corpus = _copy_corpus(corpus)

    async def fetch(
        self,
        plan: QueryPlan,
        *,
        query: str,
        timeout_seconds: float,
    ) -> SourceGatewayResult:
        _validate_fetch_input(
            plan,
            query=query,
            timeout_seconds=timeout_seconds,
        )
        security_id = _security_id(plan)
        selected = tuple(
            item.model_copy(deep=True)
            for item in self._corpus.documents
            if item.source_type in plan.required_sources
            and security_id is not None
            and security_id in item.security_ids
        )
        results = {}
        for source in plan.required_sources:
            source_documents = tuple(
                item for item in selected if item.source_type == source
            )
            if source_documents:
                results[source] = create_provider_result(
                    status=ProviderStatus.OK,
                    data={
                        "document_ids": [
                            item.document_id for item in source_documents
                        ]
                    },
                    fetched_at=self._corpus.basis_at,
                )
            else:
                results[source] = create_provider_result(
                    status=ProviderStatus.NO_DATA,
                    fetched_at=self._corpus.basis_at,
                )
        result = SourceGatewayResult(
            documents=selected,
            provider_results_by_source=results,
            documents_by_id={
                item.document_id: item.model_copy(deep=True)
                for item in selected
            },
            data_mode="recorded",
            live_connectivity_checked=False,
        )
        return validate_source_gateway_result(
            result,
            required_sources=plan.required_sources,
        )


def _load_json_object(path: Path) -> dict[str, Any]:
    if not isinstance(path, Path):
        raise DemoCorpusValidationError("demo data input is invalid")
    try:
        text = path.read_text(encoding="utf-8")
        value = json.loads(text)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise DemoCorpusValidationError("demo data could not be loaded") from None
    if not isinstance(value, dict):
        raise DemoCorpusValidationError("demo data schema is invalid")
    return value


def _validate_manifest(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {
        "corpus_type",
        "schema_version",
        "basis_at",
        "documents_file",
        "document_ids",
    }:
        raise DemoCorpusValidationError("demo manifest is invalid")
    if (
        value.get("corpus_type") != _CORPUS_TYPE
        or value.get("schema_version") != _SCHEMA_VERSION
        or value.get("documents_file") != _DOCUMENTS_FILE
    ):
        raise DemoCorpusValidationError("demo manifest is invalid")
    raw_ids = value.get("document_ids")
    if (
        not isinstance(raw_ids, list)
        or not raw_ids
        or any(
            not isinstance(item, str) or not item.strip()
            for item in raw_ids
        )
        or len(raw_ids) != len(set(raw_ids))
    ):
        raise DemoCorpusValidationError("demo manifest is invalid")
    basis_at = _parse_basis_at(value.get("basis_at"))
    return {
        **dict(value),
        "basis_at": basis_at,
        "document_ids": list(raw_ids),
    }


def _validate_payload(value: Mapping[str, Any]) -> dict[str, Any]:
    if (
        not isinstance(value, Mapping)
        or set(value) != {"schema_version", "documents"}
        or value.get("schema_version") != _SCHEMA_VERSION
        or not isinstance(value.get("documents"), list)
        or not value["documents"]
    ):
        raise DemoCorpusValidationError("demo document payload is invalid")
    return dict(value)


def _validate_document(value: object) -> FinancialDocument:
    if not isinstance(value, dict) or set(value) != set(
        FinancialDocument.model_fields
    ):
        raise DemoCorpusValidationError("demo document is invalid")
    try:
        document = FinancialDocument.model_validate(value)
    except (TypeError, ValueError, ValidationError):
        raise DemoCorpusValidationError("demo document is invalid") from None
    if (
        not isinstance(document.published_at, datetime)
        or document.published_at.tzinfo is None
        or document.published_at.utcoffset() is None
        or document.source_type not in _SUPPORTED_SOURCES
        or document.provider != "recorded_demo"
        or document.ingestion_version != _INGESTION_VERSION
    ):
        raise DemoCorpusValidationError("demo document is invalid")
    _validate_provenance(document)
    return document.model_copy(deep=True)


def _validate_provenance(document: FinancialDocument) -> None:
    metadata = document.metadata
    if not isinstance(metadata, dict):
        raise DemoCorpusValidationError("demo provenance is invalid")
    origin = metadata.get("content_origin")
    required_strings = (
        "verification_status",
        "reference_title",
        "reference_publisher",
        "reference_url",
        "reference_published_at",
        "reference_section",
        "summary_author",
        "usage_note",
    )
    if any(
        not isinstance(metadata.get(key), str)
        or not metadata[key].strip()
        for key in required_strings
    ):
        raise DemoCorpusValidationError("demo provenance is invalid")
    if (
        metadata["summary_author"] != "Questock"
        or metadata["reference_url"] != document.source_url
    ):
        raise DemoCorpusValidationError("demo provenance is invalid")
    try:
        reference_date = date.fromisoformat(
            metadata["reference_published_at"]
        )
    except ValueError:
        raise DemoCorpusValidationError("demo provenance is invalid") from None
    if reference_date.isoformat() != metadata["reference_published_at"]:
        raise DemoCorpusValidationError("demo provenance is invalid")
    if document.source_type == "disclosure":
        _validate_disclosure_provenance(document, origin)
    elif (
        origin != _SYNTHETIC_ORIGIN
        or metadata["verification_status"] != "project_owned"
    ):
        raise DemoCorpusValidationError("demo provenance is invalid")


def _validate_disclosure_provenance(
    document: FinancialDocument,
    origin: object,
) -> None:
    receipt_no = document.locator.get("receipt_no")
    expected_url = (
        "https://dart.fss.or.kr/dsaf001/main.do"
        f"?rcpNo={receipt_no}"
    )
    if (
        origin != _VERIFIED_ORIGIN
        or document.metadata.get("verification_status") != "human_approved"
        or not isinstance(receipt_no, str)
        or _RECEIPT_NO.fullmatch(receipt_no) is None
        or document.document_id != f"disclosure:{receipt_no}"
        or document.source_url != expected_url
        or document.locator.get("viewer_url") != expected_url
        or document.metadata.get("content_level") != "listing_metadata"
        or document.metadata.get("is_correction") is not False
        or document.metadata.get("has_subsequent_correction") is not False
        or document.metadata.get("is_withdrawn") is not False
    ):
        raise DemoCorpusValidationError("demo provenance is invalid")


def _parse_basis_at(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise DemoCorpusValidationError("demo basis timestamp is invalid")
    try:
        parsed = datetime.fromisoformat(f"{value[:-1]}+00:00")
    except ValueError:
        raise DemoCorpusValidationError("demo basis timestamp is invalid") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise DemoCorpusValidationError("demo basis timestamp is invalid")
    return parsed.astimezone(UTC)


def _copy_corpus(value: object) -> DemoCorpus:
    if not isinstance(value, DemoCorpus):
        raise DemoCorpusValidationError("demo corpus is invalid")
    try:
        if (
            value.corpus_type != _CORPUS_TYPE
            or value.schema_version != _SCHEMA_VERSION
            or not isinstance(value.basis_at, datetime)
            or value.basis_at.tzinfo is None
            or value.basis_at.utcoffset() != timedelta(0)
            or not isinstance(value.documents, tuple)
            or not value.documents
            or any(
                not isinstance(item, FinancialDocument)
                for item in value.documents
            )
        ):
            raise DemoCorpusValidationError("demo corpus is invalid")
        documents = tuple(
            _validate_document(item.model_dump(mode="json"))
            for item in value.documents
        )
        if len({item.document_id for item in documents}) != len(documents):
            raise DemoCorpusValidationError("demo corpus is invalid")
        return DemoCorpus(
            corpus_type=value.corpus_type,
            schema_version=value.schema_version,
            basis_at=value.basis_at.astimezone(UTC),
            documents=documents,
        )
    except DemoCorpusValidationError:
        raise
    except (AttributeError, TypeError, ValueError):
        raise DemoCorpusValidationError("demo corpus is invalid") from None


def _validate_fetch_input(
    plan: object,
    *,
    query: object,
    timeout_seconds: object,
) -> None:
    if (
        not isinstance(plan, QueryPlan)
        or not isinstance(query, str)
        or not query.strip()
        or isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, (int, float))
        or not math.isfinite(timeout_seconds)
        or timeout_seconds <= 0
    ):
        raise DemoCorpusValidationError("recorded source request is invalid")


def _security_id(plan: QueryPlan) -> str | None:
    if plan.security is None:
        return None
    return f"{plan.security.market}:{plan.security.ticker}"


__all__ = [
    "DemoCorpus",
    "DemoCorpusValidationError",
    "RecordedDemoSourceGateway",
    "build_demo_corpus",
    "load_demo_corpus",
]
