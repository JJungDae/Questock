from __future__ import annotations

import hashlib
import json
import math
import unicodedata
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from app.core.models import Evidence, ProviderResult
from app.core.status import ProviderStatus, RetrievalStatus
from app.evidence.budget import (
    ContextBudgetDiagnostics,
    ContextBudgetResult,
    MAX_CONTEXT_CHARS,
    MAX_CONTEXT_TOKENS,
    MAX_EVIDENCE_COUNT,
    TOKEN_ESTIMATOR_VERSION,
)
from app.ingest import glossary as glossary_ingest
from app.ingest.glossary import (
    GlossaryCorpusBundle,
    GlossaryIndex,
    GlossaryIngestValidationError,
    build_glossary_index,
    build_glossary_locator,
    load_glossary_entries,
    lookup_glossary_entry,
    validate_glossary_corpus,
)
from app.providers.base import create_provider_result

_APPROVED_GLOSSARY_PATH = Path("data/glossary.json")
_SECTION_ORDER = (
    "definition",
    "why_it_matters",
    "caution",
    "formula",
    "example",
)
_DIRECT_STRATEGY = "glossary-direct-m3-05-v1"
_RETRIEVAL_SCORE = 1.0

GlossaryLookupState = Literal["found", "not_found", "unavailable"]


@dataclass(frozen=True)
class GlossaryPipelineResult:
    provider_result: ProviderResult[dict[str, object]]
    evidence: tuple[Evidence, ...]
    retrieval_status: RetrievalStatus
    strategy: str
    selected_count: int
    lookup_state: GlossaryLookupState
    data_mode: Literal["recorded"]
    live_connectivity_checked: Literal[False]


class GlossaryService:
    """Serve the approved local glossary without entering document retrieval."""

    def __init__(self) -> None:
        self._bundle: GlossaryCorpusBundle | None = None
        self._index: GlossaryIndex | None = None
        self._lookup_terms: tuple[tuple[str, str], ...] = ()
        self._available = False
        self._initialize()

    def lookup(
        self,
        query: str,
        *,
        fetched_at: datetime,
    ) -> GlossaryPipelineResult:
        canonical_fetched_at = _aware_utc(fetched_at)
        if not isinstance(query, str) or not query.strip():
            return self._empty_result(
                status=ProviderStatus.INVALID_QUERY,
                lookup_state="not_found",
                fetched_at=canonical_fetched_at,
            )
        if not self._available or self._bundle is None or self._index is None:
            return self._empty_result(
                status=ProviderStatus.PARSE_ERROR,
                lookup_state="unavailable",
                fetched_at=canonical_fetched_at,
            )

        lookup_query = self._lookup_query(query)
        if lookup_query is None:
            return self._empty_result(
                status=ProviderStatus.NO_DATA,
                lookup_state="not_found",
                fetched_at=canonical_fetched_at,
            )
        try:
            lookup = lookup_glossary_entry(self._index, lookup_query)
            if lookup.status != "found" or lookup.entry is None:
                return self._empty_result(
                    status=ProviderStatus.NO_DATA,
                    lookup_state="not_found",
                    fetched_at=canonical_fetched_at,
                )
            evidence = self._evidence_for(lookup.entry)
        except (GlossaryIngestValidationError, TypeError, ValueError):
            return self._empty_result(
                status=ProviderStatus.PARSE_ERROR,
                lookup_state="unavailable",
                fetched_at=canonical_fetched_at,
            )

        provider_result = create_provider_result(
            status=ProviderStatus.OK,
            data={
                "entry_id": lookup.entry.entry_id,
                "evidence_ids": [item.evidence_id for item in evidence],
            },
            fetched_at=canonical_fetched_at,
        )
        return GlossaryPipelineResult(
            provider_result=provider_result,
            evidence=evidence,
            retrieval_status=RetrievalStatus.OK,
            strategy=_DIRECT_STRATEGY,
            selected_count=len(evidence),
            lookup_state="found",
            data_mode="recorded",
            live_connectivity_checked=False,
        )

    def _initialize(self) -> None:
        try:
            bundle = load_glossary_entries(_APPROVED_GLOSSARY_PATH)
            entries = validate_glossary_corpus(bundle, mode="corpus")
            fingerprint = (
                glossary_ingest._calculate_approved_glossary_snapshot_sha256(
                    entries
                )
            )
            if (
                bundle.schema_version != 1
                or bundle.corpus_type != "approved_corpus"
                or bundle.corpus_id != "glossary-approved-v1"
                or bundle.language != "ko"
                or len(entries) != 15
                or fingerprint
                != glossary_ingest._APPROVED_ACTUAL_GLOSSARY_SNAPSHOT_SHA256
            ):
                raise ValueError
            index = build_glossary_index(bundle, mode="corpus")
            lookup_terms = _build_lookup_terms(bundle)
        except (GlossaryIngestValidationError, OSError, TypeError, ValueError):
            return
        self._bundle = bundle
        self._index = index
        self._lookup_terms = lookup_terms
        self._available = True

    def _lookup_query(self, query: str) -> str | None:
        normalized_query = _normalize(query)
        matches: list[tuple[int, int, str]] = []
        for normalized_term, term in self._lookup_terms:
            position = normalized_query.find(normalized_term)
            if position >= 0:
                matches.append((position, -len(normalized_term), term))
        if not matches:
            return None
        return min(matches)[2]

    def _evidence_for(self, entry: object) -> tuple[Evidence, ...]:
        assert self._bundle is not None
        evidence: list[Evidence] = []
        for section in _SECTION_ORDER:
            snippet = getattr(entry, section)
            if snippet is None:
                continue
            locator = build_glossary_locator(self._bundle, entry, section)
            locator_payload = {
                key: value
                for key, value in asdict(locator).items()
                if key not in {"source_url", "source_asset_id"}
            }
            identity = (
                locator.corpus_id,
                locator.entry_id,
                locator.version,
                locator.section,
            )
            evidence.append(
                Evidence(
                    evidence_id=_stable_id("evidence", identity),
                    document_id=_stable_id("document", identity),
                    source_type="glossary",
                    title=getattr(entry, "canonical_term"),
                    source_url=locator.source_url,
                    published_at=None,
                    subject_security_ids=[],
                    mentioned_security_ids=[],
                    scope="industry_common",
                    snippet=snippet,
                    locator=locator_payload,
                    retrieval_score=_RETRIEVAL_SCORE,
                )
            )
        return tuple(evidence)

    @staticmethod
    def _empty_result(
        *,
        status: ProviderStatus,
        lookup_state: GlossaryLookupState,
        fetched_at: datetime,
    ) -> GlossaryPipelineResult:
        return GlossaryPipelineResult(
            provider_result=create_provider_result(
                status=status,
                fetched_at=fetched_at,
            ),
            evidence=(),
            retrieval_status=RetrievalStatus.EMPTY,
            strategy=_DIRECT_STRATEGY,
            selected_count=0,
            lookup_state=lookup_state,
            data_mode="recorded",
            live_connectivity_checked=False,
        )


def select_glossary_context(
    evidence: tuple[Evidence, ...],
) -> ContextBudgetResult:
    """Preserve all approved sections in the private glossary branch."""
    selected = tuple(item.model_copy(deep=True) for item in evidence)
    if len(selected) > MAX_EVIDENCE_COUNT:
        selected = selected[:MAX_EVIDENCE_COUNT]
    estimated_tokens, estimated_chars = _estimate_projection(selected)
    while selected and (
        estimated_tokens > MAX_CONTEXT_TOKENS
        or estimated_chars > MAX_CONTEXT_CHARS
    ):
        selected = selected[:-1]
        estimated_tokens, estimated_chars = _estimate_projection(selected)
    input_count = len(evidence)
    selected_count = len(selected)
    diagnostics = ContextBudgetDiagnostics(
        input_count=input_count,
        unique_count=input_count,
        duplicate_drop_count=0,
        source_cap_drop_count=0,
        count_cap_drop_count=max(0, input_count - MAX_EVIDENCE_COUNT),
        context_drop_count=min(input_count, MAX_EVIDENCE_COUNT) - selected_count,
        selected_count=selected_count,
        estimated_context_tokens=estimated_tokens,
        estimated_evidence_chars=estimated_chars,
        reserved_tokens=0,
        max_evidence_count=MAX_EVIDENCE_COUNT,
        max_evidence_per_source=MAX_EVIDENCE_COUNT,
        max_context_tokens=MAX_CONTEXT_TOKENS,
        max_context_chars=MAX_CONTEXT_CHARS,
        estimator_version=TOKEN_ESTIMATOR_VERSION,
        budget_exhausted=bool(input_count and not selected),
    )
    return ContextBudgetResult(evidence=selected, diagnostics=diagnostics)


def _build_lookup_terms(
    bundle: GlossaryCorpusBundle,
) -> tuple[tuple[str, str], ...]:
    values: dict[str, str] = {}
    for entry in bundle.entries:
        for term in (entry.canonical_term, *entry.aliases):
            values.setdefault(_normalize(term), term)
    return tuple(sorted(values.items()))


def _stable_id(
    kind: Literal["document", "evidence"],
    identity: tuple[str, str, int, str],
) -> str:
    payload = json.dumps(
        identity,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    return f"glossary:{kind}:{digest}"


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return " ".join(normalized.split()).casefold()


def _estimate_projection(
    evidence: tuple[Evidence, ...],
) -> tuple[int, int]:
    if not evidence:
        return 0, 0
    payload = [
        {
            "evidence_id": item.evidence_id,
            "source_type": item.source_type,
            "title": item.title,
            "published_at": (
                item.published_at.isoformat()
                if item.published_at is not None
                else None
            ),
            "subject_security_ids": list(item.subject_security_ids),
            "mentioned_security_ids": list(item.mentioned_security_ids),
            "scope": item.scope,
            "snippet": item.snippet,
        }
        for item in evidence
    ]
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    byte_count = len(serialized.encode("utf-8"))
    return math.ceil(byte_count / 3), len(serialized)


def _aware_utc(value: object) -> datetime:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError("glossary fetched_at is invalid")
    return value.astimezone(UTC)


__all__ = [
    "GlossaryPipelineResult",
    "GlossaryService",
    "select_glossary_context",
]
