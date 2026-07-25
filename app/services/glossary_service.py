from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from app.core.models import Evidence, ProviderResult
from app.core.status import ProviderStatus, RetrievalStatus
from app.evidence.budget import (
    ContextBudgetResult,
    select_evidence_context,
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
_UNICODE_ALNUM = r"[^\W_]"
_GRAMMATICAL_PARTICLES = (
    "에서",
    "으로",
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "와",
    "과",
    "의",
    "에",
    "로",
)

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
        self._lookup_terms: tuple[tuple[str, str, str], ...] = ()
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
        matches: list[tuple[str, int, int, str, str]] = []
        for normalized_term, term, entry_id in self._lookup_terms:
            position = _candidate_position(normalized_query, normalized_term)
            if position is not None:
                matches.append(
                    (
                        entry_id,
                        -len(normalized_term),
                        position,
                        normalized_term,
                        term,
                    )
                )
        if not matches:
            return None
        entry_ids = {item[0] for item in matches}
        if len(entry_ids) != 1:
            return None
        return min(matches, key=lambda item: item[1:])[4]

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
    """Apply the completed M2 context-budget contract to glossary evidence."""
    return select_evidence_context(evidence)


def _build_lookup_terms(
    bundle: GlossaryCorpusBundle,
) -> tuple[tuple[str, str, str], ...]:
    values: dict[tuple[str, str], str] = {}
    for entry in bundle.entries:
        for term in (entry.canonical_term, *entry.aliases):
            values.setdefault((_normalize(term), entry.entry_id), term)
    return tuple(
        sorted(
            (
                normalized_term,
                term,
                entry_id,
            )
            for (normalized_term, entry_id), term in values.items()
        )
    )


def _candidate_position(query: str, term: str) -> int | None:
    particles = "|".join(
        re.escape(item)
        for item in _GRAMMATICAL_PARTICLES
    )
    pattern = re.compile(
        rf"(?<!{_UNICODE_ALNUM}){re.escape(term)}"
        rf"(?:(?:{particles})(?!{_UNICODE_ALNUM})|(?!{_UNICODE_ALNUM}))"
    )
    match = pattern.search(query)
    return match.start() if match is not None else None


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
