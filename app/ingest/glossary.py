from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, fields
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal, Mapping
from urllib.parse import parse_qsl, urlsplit, urlunsplit

GLOSSARY_SOURCE_TYPE = "glossary"
MANUAL_GLOSSARY_PROVIDER = "manual_glossary"
GLOSSARY_INGESTION_VERSION = "glossary-ingest-m1-07-v1"
MINIMUM_GLOSSARY_ENTRIES = 15
_ACTUAL_GLOSSARY_PATH = Path("data/glossary.json")
_ACTUAL_GLOSSARY_CORPUS_ID = "glossary-approved-v1"
_EXPECTED_ACTUAL_GLOSSARY_ENTRY_IDS = frozenset(
    {
        "glossary:per",
        "glossary:pbr",
        "glossary:roe",
        "glossary:eps",
        "glossary:market_cap",
        "glossary:revenue",
        "glossary:operating_profit",
        "glossary:net_income",
        "glossary:operating_margin",
        "glossary:rights_offering",
        "glossary:convertible_bond",
        "glossary:corporate_disclosure",
        "glossary:consensus",
        "glossary:consolidated_financial_statements",
        "glossary:separate_financial_statements",
    }
)

_WRAPPER_REQUIRED_FIELDS = frozenset({"schema_version", "corpus_type", "corpus_id", "language", "entries"})
_ENTRY_REQUIRED_FIELDS = frozenset(
    {
        "entry_id",
        "version",
        "canonical_term",
        "aliases",
        "definition",
        "why_it_matters",
        "caution",
        "language",
        "usage_review_status",
        "corpus_ingest_allowed",
        "external_llm_processing_allowed",
        "content_origin",
        "source_note",
        "permission_note",
        "ingestion_version",
    }
)
_ENTRY_OPTIONAL_FIELDS = frozenset(
    {"category", "formula", "example", "related_entry_ids", "source_url", "source_asset_id"}
)
_ENTRY_ALLOWED_FIELDS = _ENTRY_REQUIRED_FIELDS | _ENTRY_OPTIONAL_FIELDS

_CORPUS_TYPES = frozenset({"synthetic_unit", "review_corpus", "approved_corpus"})
_USAGE_REVIEW_STATUSES = frozenset({"synthetic", "pending", "approved", "rejected"})
_CONTENT_ORIGINS = frozenset({"synthetic", "user_authored", "external_source", "public_domain"})
_LOCATOR_SECTIONS = frozenset({"definition", "why_it_matters", "caution", "formula", "example"})
_ENTRY_ID_RE = re.compile(r"^glossary:[a-z0-9][a-z0-9._-]*$")
_OPAQUE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_SOURCE_ASSET_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")
_WINDOWS_ABSOLUTE_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")
_SECRET_QUERY_KEYS = {
    "token",
    "accesstoken",
    "authtoken",
    "bearertoken",
    "clientsecret",
    "apikey",
    "xapikey",
    "authorization",
    "credential",
    "signature",
    "xamzsignature",
}
_OVERCLAIM_PHRASES = tuple(
    _ for _ in (
        "무조건 저평가",
        "반드시 상승",
        "확실한 수익",
        "always undervalued",
        "guaranteed return",
    )
)


class GlossaryIngestValidationError(ValueError):
    """Raised when a glossary ingest contract is violated."""


class GlossaryEntryValidationError(GlossaryIngestValidationError):
    """Raised when one glossary entry is invalid."""


class GlossaryCorpusValidationError(GlossaryIngestValidationError):
    """Raised when a glossary corpus is invalid."""


class GlossaryLookupValidationError(GlossaryIngestValidationError):
    """Raised when glossary lookup input or state is invalid."""


@dataclass(frozen=True)
class GlossaryEntry:
    entry_id: str
    version: int
    canonical_term: str
    aliases: tuple[str, ...]
    definition: str
    why_it_matters: str
    caution: str
    language: str
    usage_review_status: str
    corpus_ingest_allowed: bool
    external_llm_processing_allowed: bool
    content_origin: str
    source_note: str
    permission_note: str
    ingestion_version: str
    category: str | None = None
    formula: str | None = None
    example: str | None = None
    related_entry_ids: tuple[str, ...] = ()
    source_url: str | None = None
    source_asset_id: str | None = None


@dataclass(frozen=True)
class GlossaryCorpusBundle:
    schema_version: int
    corpus_type: str
    corpus_id: str
    language: str
    entries: tuple[GlossaryEntry, ...]


@dataclass(frozen=True)
class GlossaryIndex:
    corpus_id: str
    corpus_type: str
    language: str
    _lookup: Mapping[str, tuple[GlossaryEntry, str, str]]

    @property
    def lookup_map(self) -> Mapping[str, tuple[GlossaryEntry, str, str]]:
        return self._lookup


@dataclass(frozen=True)
class GlossaryLocator:
    corpus_id: str
    entry_id: str
    version: int
    section: str
    source_type: str
    provider: str
    ingestion_version: str
    source_url: str | None
    source_asset_id: str | None


@dataclass(frozen=True)
class GlossaryLookupResult:
    status: Literal["found", "not_found"]
    query: str
    normalized_query: str
    matched_by: Literal["canonical", "alias"] | None
    matched_term: str | None
    entry: GlossaryEntry | None


@dataclass(frozen=True)
class GlossaryCoverage:
    total_entries: int
    approved_actual_entries: int
    synthetic_entries: int
    pending_entries: int
    rejected_entries: int
    minimum_required: int
    meets_minimum: bool
    actual_coverage_evaluated: bool


def load_glossary_entries(path: str | Path) -> GlossaryCorpusBundle:
    if not isinstance(path, (str, Path)):
        raise GlossaryCorpusValidationError("glossary corpus path is invalid")
    try:
        raw_bytes = Path(path).read_bytes()
    except OSError:
        raise GlossaryCorpusValidationError("glossary corpus could not be loaded") from None
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise GlossaryCorpusValidationError("glossary corpus is not valid UTF-8") from None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        raise GlossaryCorpusValidationError("glossary corpus JSON is malformed") from None
    return _validate_bundle(data, mode="load")


def validate_glossary_entry(raw_entry: Any) -> GlossaryEntry:
    try:
        return _validate_entry(raw_entry)
    except GlossaryIngestValidationError:
        raise
    except (AttributeError, KeyError, TypeError, ValueError):
        raise GlossaryEntryValidationError("glossary entry is invalid") from None


def validate_glossary_corpus(
    raw_or_bundle: Any,
    *,
    mode: Literal["load", "synthetic_unit", "corpus"],
) -> tuple[GlossaryEntry, ...]:
    return _validate_bundle(raw_or_bundle, mode=mode).entries


def build_glossary_index(
    raw_or_bundle: Any,
    *,
    mode: Literal["synthetic_unit", "corpus"],
) -> GlossaryIndex:
    if mode not in {"synthetic_unit", "corpus"}:
        raise GlossaryCorpusValidationError("glossary index mode is unsupported")
    bundle = _validate_bundle(raw_or_bundle, mode=mode)
    lookup: dict[str, tuple[GlossaryEntry, str, str]] = {}
    for entry in bundle.entries:
        lookup[_normalize_lookup(entry.canonical_term)] = (entry, "canonical", entry.canonical_term)
        for alias in entry.aliases:
            lookup[_normalize_lookup(alias)] = (entry, "alias", alias)
    return GlossaryIndex(
        corpus_id=bundle.corpus_id,
        corpus_type=bundle.corpus_type,
        language=bundle.language,
        _lookup=MappingProxyType(dict(lookup)),
    )


def lookup_glossary_entry(index: Any, query: str) -> GlossaryLookupResult:
    index = _validate_index(index)
    if not isinstance(query, str):
        raise GlossaryLookupValidationError("glossary lookup query must be a string")
    normalized_query = _normalize_lookup(query)
    if not normalized_query:
        return GlossaryLookupResult(
            status="not_found",
            query=query,
            normalized_query=normalized_query,
            matched_by=None,
            matched_term=None,
            entry=None,
        )
    match = index.lookup_map.get(normalized_query)
    if match is None:
        return GlossaryLookupResult(
            status="not_found",
            query=query,
            normalized_query=normalized_query,
            matched_by=None,
            matched_term=None,
            entry=None,
        )
    entry, matched_by, matched_term = match
    return GlossaryLookupResult(
        status="found",
        query=query,
        normalized_query=normalized_query,
        matched_by=matched_by,  # type: ignore[arg-type]
        matched_term=matched_term,
        entry=entry,
    )


def build_glossary_locator(bundle: Any, entry: Any, section: str) -> GlossaryLocator:
    bundle = _validate_bundle(bundle, mode="load")
    entry = validate_glossary_entry(entry)
    entries_by_id = {item.entry_id: item for item in bundle.entries}
    if entry.entry_id not in entries_by_id:
        raise GlossaryCorpusValidationError("glossary entry is not part of the corpus")
    entry = entries_by_id[entry.entry_id]
    if not isinstance(section, str):
        raise GlossaryCorpusValidationError("glossary locator section must be a string")
    if section not in _LOCATOR_SECTIONS:
        raise GlossaryCorpusValidationError("glossary locator section is unsupported")
    if section in {"formula", "example"} and getattr(entry, section) is None:
        raise GlossaryCorpusValidationError("glossary locator section is unavailable")
    return GlossaryLocator(
        corpus_id=bundle.corpus_id,
        entry_id=entry.entry_id,
        version=entry.version,
        section=section,
        source_type=GLOSSARY_SOURCE_TYPE,
        provider=MANUAL_GLOSSARY_PROVIDER,
        ingestion_version=entry.ingestion_version,
        source_url=entry.source_url,
        source_asset_id=entry.source_asset_id,
    )


def calculate_glossary_coverage(raw_or_bundle: Any) -> GlossaryCoverage:
    bundle = _validate_bundle(raw_or_bundle, mode="load")
    synthetic_entries = sum(1 for entry in bundle.entries if entry.usage_review_status == "synthetic")
    pending_entries = sum(1 for entry in bundle.entries if entry.usage_review_status == "pending")
    rejected_entries = sum(1 for entry in bundle.entries if entry.usage_review_status == "rejected")
    eligible_approved_count = sum(
        1
        for entry in bundle.entries
        if entry.usage_review_status == "approved"
        and entry.corpus_ingest_allowed
        and entry.content_origin != "synthetic"
    )
    approved_actual_entries = eligible_approved_count if bundle.corpus_type == "approved_corpus" else 0
    actual_coverage_evaluated = False
    return GlossaryCoverage(
        total_entries=len(bundle.entries),
        approved_actual_entries=approved_actual_entries,
        synthetic_entries=synthetic_entries,
        pending_entries=pending_entries,
        rejected_entries=rejected_entries,
        minimum_required=MINIMUM_GLOSSARY_ENTRIES,
        meets_minimum=actual_coverage_evaluated and approved_actual_entries >= MINIMUM_GLOSSARY_ENTRIES,
        actual_coverage_evaluated=actual_coverage_evaluated,
    )


def evaluate_actual_glossary_coverage(path: str | Path) -> GlossaryCoverage:
    path = _validate_actual_glossary_path(path)
    bundle = load_glossary_entries(path)
    entries = validate_glossary_corpus(bundle, mode="corpus")
    entry_ids = {entry.entry_id for entry in entries}
    if (
        bundle.schema_version != 1
        or bundle.corpus_id != _ACTUAL_GLOSSARY_CORPUS_ID
        or bundle.corpus_type != "approved_corpus"
        or bundle.language != "ko"
        or len(entries) != MINIMUM_GLOSSARY_ENTRIES
        or entry_ids != _EXPECTED_ACTUAL_GLOSSARY_ENTRY_IDS
        or any(
            entry.version != 1
            or entry.language != "ko"
            or entry.usage_review_status != "approved"
            or not entry.corpus_ingest_allowed
            or not entry.external_llm_processing_allowed
            or entry.content_origin != "user_authored"
            or entry.ingestion_version != GLOSSARY_INGESTION_VERSION
            or entry.source_url is not None
            or entry.source_asset_id is not None
            for entry in entries
        )
    ):
        raise GlossaryCorpusValidationError("actual glossary corpus identity is invalid")
    return GlossaryCoverage(
        total_entries=len(entries),
        approved_actual_entries=len(entries),
        synthetic_entries=0,
        pending_entries=0,
        rejected_entries=0,
        minimum_required=MINIMUM_GLOSSARY_ENTRIES,
        meets_minimum=True,
        actual_coverage_evaluated=True,
    )


def _validate_actual_glossary_path(path: str | Path) -> Path:
    if not isinstance(path, (str, Path)):
        raise GlossaryCorpusValidationError("actual glossary corpus path is invalid")
    path = Path(path)
    if path.is_absolute() or path != _ACTUAL_GLOSSARY_PATH:
        raise GlossaryCorpusValidationError("actual glossary coverage requires data/glossary.json")
    return path


def _validate_bundle(raw_or_bundle: Any, *, mode: str) -> GlossaryCorpusBundle:
    if mode not in {"load", "synthetic_unit", "corpus"}:
        raise GlossaryCorpusValidationError("glossary corpus mode is unsupported")
    try:
        bundle = _bundle_from_raw(raw_or_bundle)
        _validate_global_integrity(bundle.entries)
        _validate_corpus_type_rules(bundle)
        if mode == "synthetic_unit" and bundle.corpus_type != "synthetic_unit":
            raise GlossaryCorpusValidationError("synthetic glossary build requires synthetic_unit corpus")
        if mode == "corpus" and bundle.corpus_type != "approved_corpus":
            raise GlossaryCorpusValidationError("glossary corpus build requires approved_corpus")
        return bundle
    except GlossaryIngestValidationError:
        raise
    except (AttributeError, KeyError, TypeError, ValueError):
        raise GlossaryCorpusValidationError("glossary corpus is invalid") from None


def _bundle_from_raw(raw_or_bundle: Any) -> GlossaryCorpusBundle:
    from_bundle = isinstance(raw_or_bundle, GlossaryCorpusBundle)
    if from_bundle:
        raw = {field.name: getattr(raw_or_bundle, field.name) for field in fields(GlossaryCorpusBundle)}
    elif isinstance(raw_or_bundle, Mapping):
        raw = raw_or_bundle
    else:
        raise GlossaryCorpusValidationError("glossary corpus must be an object")

    missing = _WRAPPER_REQUIRED_FIELDS - set(raw)
    if missing:
        raise GlossaryCorpusValidationError("glossary corpus is missing required fields")
    extra = set(raw) - _WRAPPER_REQUIRED_FIELDS
    if extra:
        raise GlossaryCorpusValidationError("glossary corpus contains unsupported fields")

    schema_version = raw.get("schema_version")
    if type(schema_version) is not int or schema_version != 1:
        raise GlossaryCorpusValidationError("glossary schema_version is unsupported")
    corpus_type = _enum_value(raw.get("corpus_type"), _CORPUS_TYPES, "corpus_type", GlossaryCorpusValidationError)
    corpus_id = _required_text(raw, "corpus_id", GlossaryCorpusValidationError)
    if not _OPAQUE_ID_RE.fullmatch(corpus_id):
        raise GlossaryCorpusValidationError("glossary corpus_id must be a stable opaque id")
    language = _required_text(raw, "language", GlossaryCorpusValidationError)
    if language != "ko":
        raise GlossaryCorpusValidationError("glossary language is unsupported")
    raw_entries = raw.get("entries")
    if from_bundle:
        if not isinstance(raw_entries, (list, tuple)) or not raw_entries:
            raise GlossaryCorpusValidationError("glossary entries must be a non-empty sequence")
    elif not isinstance(raw_entries, list) or not raw_entries:
        raise GlossaryCorpusValidationError("glossary entries must be a non-empty list")
    entries = tuple(validate_glossary_entry(item) for item in raw_entries)
    if any(entry.language != language for entry in entries):
        raise GlossaryCorpusValidationError("glossary wrapper and entry language mismatch")
    return GlossaryCorpusBundle(
        schema_version=schema_version,
        corpus_type=corpus_type,
        corpus_id=corpus_id,
        language=language,
        entries=entries,
    )


def _validate_entry(raw_entry: Any) -> GlossaryEntry:
    if isinstance(raw_entry, GlossaryEntry):
        raw = {field.name: getattr(raw_entry, field.name) for field in fields(GlossaryEntry)}
    elif isinstance(raw_entry, Mapping):
        raw = raw_entry
    else:
        raise GlossaryEntryValidationError("glossary entry must be an object")

    missing = _ENTRY_REQUIRED_FIELDS - set(raw)
    if missing:
        raise GlossaryEntryValidationError("glossary entry is missing required fields")
    extra = set(raw) - _ENTRY_ALLOWED_FIELDS
    if extra:
        raise GlossaryEntryValidationError("glossary entry contains unsupported fields")

    entry_id = _required_text(raw, "entry_id", GlossaryEntryValidationError)
    if not _ENTRY_ID_RE.fullmatch(entry_id):
        raise GlossaryEntryValidationError("glossary entry_id is invalid")
    version = raw.get("version")
    if type(version) is not int or version != 1:
        raise GlossaryEntryValidationError("glossary version is unsupported")
    canonical_term = _required_text(raw, "canonical_term", GlossaryEntryValidationError)
    if not _normalize_lookup(canonical_term):
        raise GlossaryEntryValidationError("glossary canonical term is empty after normalization")
    aliases = _text_tuple(raw.get("aliases"), "aliases", GlossaryEntryValidationError)
    _validate_entry_aliases(canonical_term, aliases)
    definition = _required_text(raw, "definition", GlossaryEntryValidationError)
    why_it_matters = _required_text(raw, "why_it_matters", GlossaryEntryValidationError)
    caution = _required_text(raw, "caution", GlossaryEntryValidationError)
    language = _required_text(raw, "language", GlossaryEntryValidationError)
    if language != "ko":
        raise GlossaryEntryValidationError("glossary entry language is unsupported")
    usage_review_status = _enum_value(
        raw.get("usage_review_status"),
        _USAGE_REVIEW_STATUSES,
        "usage_review_status",
        GlossaryEntryValidationError,
    )
    corpus_ingest_allowed = _required_bool(raw, "corpus_ingest_allowed", GlossaryEntryValidationError)
    external_llm_processing_allowed = _required_bool(
        raw, "external_llm_processing_allowed", GlossaryEntryValidationError
    )
    content_origin = _enum_value(
        raw.get("content_origin"),
        _CONTENT_ORIGINS,
        "content_origin",
        GlossaryEntryValidationError,
    )
    source_note = _required_text(raw, "source_note", GlossaryEntryValidationError)
    permission_note = _required_text(raw, "permission_note", GlossaryEntryValidationError)
    ingestion_version = _required_text(raw, "ingestion_version", GlossaryEntryValidationError)
    if ingestion_version != GLOSSARY_INGESTION_VERSION:
        raise GlossaryEntryValidationError("glossary ingestion_version is unsupported")
    related_entry_ids = _related_id_tuple(raw.get("related_entry_ids", ()))
    category = _optional_text(raw.get("category"), GlossaryEntryValidationError)
    formula = _optional_text(raw.get("formula"), GlossaryEntryValidationError)
    example = _optional_text(raw.get("example"), GlossaryEntryValidationError)
    source_url = _optional_url(raw.get("source_url"), GlossaryEntryValidationError)
    source_asset_id = _optional_source_asset_id(raw.get("source_asset_id"), GlossaryEntryValidationError)
    _validate_origin_contract(
        content_origin=content_origin,
        usage_review_status=usage_review_status,
        corpus_ingest_allowed=corpus_ingest_allowed,
        external_llm_processing_allowed=external_llm_processing_allowed,
        source_url=source_url,
        source_asset_id=source_asset_id,
    )
    _validate_overclaim_text((definition, why_it_matters, caution, formula, example))
    return GlossaryEntry(
        entry_id=entry_id,
        version=version,
        canonical_term=canonical_term,
        aliases=aliases,
        definition=definition,
        why_it_matters=why_it_matters,
        caution=caution,
        language=language,
        usage_review_status=usage_review_status,
        corpus_ingest_allowed=corpus_ingest_allowed,
        external_llm_processing_allowed=external_llm_processing_allowed,
        content_origin=content_origin,
        source_note=source_note,
        permission_note=permission_note,
        ingestion_version=ingestion_version,
        category=category,
        formula=formula,
        example=example,
        related_entry_ids=related_entry_ids,
        source_url=source_url,
        source_asset_id=source_asset_id,
    )


def _validate_entry_aliases(canonical_term: str, aliases: tuple[str, ...]) -> None:
    canonical_key = _normalize_lookup(canonical_term)
    alias_keys: set[str] = set()
    for alias in aliases:
        alias_key = _normalize_lookup(alias)
        if not alias_key:
            raise GlossaryEntryValidationError("glossary alias is empty after normalization")
        if alias_key == canonical_key:
            raise GlossaryEntryValidationError("glossary alias must not duplicate canonical term")
        if alias_key in alias_keys:
            raise GlossaryEntryValidationError("glossary aliases must not contain duplicates")
        alias_keys.add(alias_key)


def _validate_global_integrity(entries: tuple[GlossaryEntry, ...]) -> None:
    entry_ids: set[str] = set()
    canonical_keys: dict[str, str] = {}
    alias_keys: dict[str, str] = {}
    for entry in entries:
        if entry.entry_id in entry_ids:
            raise GlossaryCorpusValidationError("glossary entry ids must be unique")
        entry_ids.add(entry.entry_id)

        canonical_key = _normalize_lookup(entry.canonical_term)
        if canonical_key in canonical_keys:
            raise GlossaryCorpusValidationError("glossary canonical terms must be unique")
        if canonical_key in alias_keys:
            raise GlossaryCorpusValidationError("glossary canonical term collides with alias")
        canonical_keys[canonical_key] = entry.entry_id

        for alias in entry.aliases:
            alias_key = _normalize_lookup(alias)
            if alias_key in canonical_keys:
                raise GlossaryCorpusValidationError("glossary alias collides with canonical term")
            if alias_key in alias_keys:
                raise GlossaryCorpusValidationError("glossary aliases must be globally unique")
            alias_keys[alias_key] = entry.entry_id

    for entry in entries:
        related_seen: set[str] = set()
        for related_id in entry.related_entry_ids:
            if related_id == entry.entry_id:
                raise GlossaryCorpusValidationError("glossary related entries must not self-reference")
            if related_id in related_seen:
                raise GlossaryCorpusValidationError("glossary related entries must not contain duplicates")
            if related_id not in entry_ids:
                raise GlossaryCorpusValidationError("glossary related entry id is unresolved")
            related_seen.add(related_id)


def _validate_corpus_type_rules(bundle: GlossaryCorpusBundle) -> None:
    statuses = {entry.usage_review_status for entry in bundle.entries}
    if bundle.corpus_type == "synthetic_unit":
        if statuses != {"synthetic"}:
            raise GlossaryCorpusValidationError("synthetic glossary corpus must contain only synthetic entries")
        for entry in bundle.entries:
            if entry.corpus_ingest_allowed or entry.external_llm_processing_allowed:
                raise GlossaryCorpusValidationError("synthetic glossary entries must not be corpus or LLM enabled")
    elif bundle.corpus_type == "review_corpus":
        if "synthetic" in statuses:
            raise GlossaryCorpusValidationError("review glossary corpus must not contain synthetic entries")
    elif bundle.corpus_type == "approved_corpus":
        if statuses != {"approved"}:
            raise GlossaryCorpusValidationError("approved glossary corpus must contain only approved entries")
        if any(not entry.corpus_ingest_allowed for entry in bundle.entries):
            raise GlossaryCorpusValidationError("approved glossary entries must allow corpus ingest")


def _validate_origin_contract(
    *,
    content_origin: str,
    usage_review_status: str,
    corpus_ingest_allowed: bool,
    external_llm_processing_allowed: bool,
    source_url: str | None,
    source_asset_id: str | None,
) -> None:
    if usage_review_status in {"synthetic", "pending", "rejected"}:
        if corpus_ingest_allowed or external_llm_processing_allowed:
            raise GlossaryEntryValidationError("unapproved glossary permissions must be closed")
    if external_llm_processing_allowed and (usage_review_status != "approved" or not corpus_ingest_allowed):
        raise GlossaryEntryValidationError("external LLM processing requires approved corpus ingest")

    if content_origin == "synthetic":
        if usage_review_status != "synthetic":
            raise GlossaryEntryValidationError("synthetic origin requires synthetic review status")
    elif usage_review_status == "synthetic":
        raise GlossaryEntryValidationError("synthetic review status requires synthetic content origin")

    if content_origin in {"external_source", "public_domain"} and source_url is None and source_asset_id is None:
        raise GlossaryEntryValidationError("external glossary entries require a source locator")


def _validate_index(index: Any) -> GlossaryIndex:
    try:
        if not isinstance(index, GlossaryIndex):
            raise GlossaryLookupValidationError("glossary index is invalid")
        corpus_id = _index_required_text(index.corpus_id, "corpus_id")
        if not _OPAQUE_ID_RE.fullmatch(corpus_id):
            raise GlossaryLookupValidationError("glossary index corpus_id is invalid")
        if index.corpus_type not in {"synthetic_unit", "approved_corpus"}:
            raise GlossaryLookupValidationError("glossary index corpus_type is unsupported")
        if index.language != "ko":
            raise GlossaryLookupValidationError("glossary index language is unsupported")
        if not isinstance(index.lookup_map, Mapping) or not index.lookup_map:
            raise GlossaryLookupValidationError("glossary index mapping is invalid")

        actual_lookup: dict[str, tuple[GlossaryEntry, str, str]] = {}
        unique_entries_by_id: dict[str, GlossaryEntry] = {}
        for key, value in index.lookup_map.items():
            if not isinstance(key, str) or not key.strip():
                raise GlossaryLookupValidationError("glossary index key is invalid")
            if _normalize_lookup(key) != key:
                raise GlossaryLookupValidationError("glossary index key must be normalized")
            if not isinstance(value, tuple) or len(value) != 3:
                raise GlossaryLookupValidationError("glossary index value is invalid")
            raw_entry, matched_by, matched_term = value
            entry = validate_glossary_entry(raw_entry)
            if matched_by not in {"canonical", "alias"}:
                raise GlossaryLookupValidationError("glossary index matched_by is invalid")
            if not isinstance(matched_term, str) or not matched_term.strip():
                raise GlossaryLookupValidationError("glossary index matched_term is invalid")
            if matched_by == "canonical":
                if matched_term != entry.canonical_term:
                    raise GlossaryLookupValidationError("glossary index canonical term is invalid")
                if key != _normalize_lookup(entry.canonical_term):
                    raise GlossaryLookupValidationError("glossary index canonical key is invalid")
            else:
                if matched_term not in entry.aliases:
                    raise GlossaryLookupValidationError("glossary index alias term is invalid")
                if key != _normalize_lookup(matched_term):
                    raise GlossaryLookupValidationError("glossary index alias key is invalid")

            existing_entry = unique_entries_by_id.get(entry.entry_id)
            if existing_entry is not None and existing_entry != entry:
                raise GlossaryLookupValidationError("glossary index entry content conflicts")
            unique_entries_by_id[entry.entry_id] = entry
            actual_lookup[key] = (entry, matched_by, matched_term)

        entries = tuple(unique_entries_by_id.values())
        if any(entry.language != index.language for entry in entries):
            raise GlossaryLookupValidationError("glossary index entry language mismatch")
        bundle = GlossaryCorpusBundle(
            schema_version=1,
            corpus_type=index.corpus_type,
            corpus_id=corpus_id,
            language=index.language,
            entries=entries,
        )
        try:
            _validate_global_integrity(bundle.entries)
            _validate_corpus_type_rules(bundle)
        except GlossaryIngestValidationError:
            raise GlossaryLookupValidationError("glossary index corpus integrity is invalid") from None

        expected_lookup = _expected_lookup_for_entries(entries)
        if actual_lookup != expected_lookup:
            raise GlossaryLookupValidationError("glossary index mapping is incomplete or forged")
        return GlossaryIndex(
            corpus_id=corpus_id,
            corpus_type=index.corpus_type,
            language=index.language,
            _lookup=MappingProxyType(dict(expected_lookup)),
        )
    except GlossaryLookupValidationError:
        raise
    except GlossaryIngestValidationError:
        raise GlossaryLookupValidationError("glossary index is invalid") from None
    except (AttributeError, KeyError, TypeError, ValueError, re.error):
        raise GlossaryLookupValidationError("glossary index is invalid") from None


def _expected_lookup_for_entries(entries: tuple[GlossaryEntry, ...]) -> dict[str, tuple[GlossaryEntry, str, str]]:
    expected_lookup: dict[str, tuple[GlossaryEntry, str, str]] = {}
    for entry in entries:
        expected_lookup[_normalize_lookup(entry.canonical_term)] = (entry, "canonical", entry.canonical_term)
        for alias in entry.aliases:
            expected_lookup[_normalize_lookup(alias)] = (entry, "alias", alias)
    return expected_lookup


def _index_required_text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise GlossaryLookupValidationError(f"glossary index {field} must be a string")
    value = value.strip()
    if not value:
        raise GlossaryLookupValidationError(f"glossary index {field} must not be blank")
    if _looks_like_local_absolute_path(value):
        raise GlossaryLookupValidationError(f"glossary index {field} must not expose a local absolute path")
    return value


def _required_text(raw: Mapping[str, Any], field: str, error_type: type[GlossaryIngestValidationError]) -> str:
    value = raw.get(field)
    if not isinstance(value, str):
        raise error_type(f"{field} must be a string")
    value = value.strip()
    if not value:
        raise error_type(f"{field} must not be blank")
    if _looks_like_local_absolute_path(value):
        raise error_type(f"{field} must not expose a local absolute path")
    return value


def _optional_text(value: Any, error_type: type[GlossaryIngestValidationError]) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise error_type("optional text fields must be strings or null")
    value = value.strip()
    if not value:
        raise error_type("optional text fields must not be blank")
    if _looks_like_local_absolute_path(value):
        raise error_type("optional text fields must not expose a local absolute path")
    return value


def _text_tuple(
    value: Any,
    field: str,
    error_type: type[GlossaryIngestValidationError],
) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise error_type(f"{field} must be a list or tuple")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise error_type(f"{field} values must be strings")
        item = item.strip()
        if not item:
            raise error_type(f"{field} values must not be blank")
        if _looks_like_local_absolute_path(item):
            raise error_type(f"{field} values must not expose a local absolute path")
        items.append(item)
    return tuple(items)


def _related_id_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise GlossaryEntryValidationError("related_entry_ids must be a list or tuple")
    related_ids: list[str] = []
    for item in value:
        if not isinstance(item, str) or not _ENTRY_ID_RE.fullmatch(item):
            raise GlossaryEntryValidationError("related_entry_ids values must be valid glossary ids")
        related_ids.append(item)
    return tuple(related_ids)


def _required_bool(
    raw: Mapping[str, Any],
    field: str,
    error_type: type[GlossaryIngestValidationError],
) -> bool:
    value = raw.get(field)
    if type(value) is not bool:
        raise error_type(f"{field} must be a boolean")
    return value


def _enum_value(
    value: Any,
    allowed: frozenset[str],
    field: str,
    error_type: type[GlossaryIngestValidationError],
) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise error_type(f"{field} is unsupported")
    return value


def _optional_url(value: Any, error_type: type[GlossaryIngestValidationError]) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise error_type("source_url must be a string or null")
    value = value.strip()
    if not value:
        raise error_type("source_url must not be blank")
    if _looks_like_local_absolute_path(value) or value.lower().startswith("file://"):
        raise error_type("source_url must be HTTP(S)")
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError:
        raise error_type("source_url is invalid") from None
    scheme = parts.scheme.lower()
    if scheme not in {"http", "https"}:
        raise error_type("source_url must be HTTP(S)")
    if not parts.hostname:
        raise error_type("source_url requires a host")
    if parts.username is not None or parts.password is not None:
        raise error_type("source_url must not include userinfo")
    if parts.fragment:
        raise error_type("source_url must not include a fragment")
    for key, _ in parse_qsl(parts.query, keep_blank_values=True):
        if _normalize_secret_key(key) in _SECRET_QUERY_KEYS:
            raise error_type("source_url must not include credential query keys")
    hostname = parts.hostname.lower()
    default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    netloc = hostname if port is None or default_port else f"{hostname}:{port}"
    return urlunsplit((scheme, netloc, parts.path, parts.query, ""))


def _optional_source_asset_id(value: Any, error_type: type[GlossaryIngestValidationError]) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise error_type("source_asset_id must be a string or null")
    value = value.strip()
    if not value:
        raise error_type("source_asset_id must not be blank")
    if _looks_like_local_absolute_path(value) or value.lower().startswith("file://"):
        raise error_type("source_asset_id must be an opaque id")
    if value in {".", ".."} or not _SOURCE_ASSET_ID_RE.fullmatch(value) or not re.search(r"[A-Za-z0-9]", value):
        raise error_type("source_asset_id must be an opaque id")
    return value


def _validate_overclaim_text(values: tuple[str | None, ...]) -> None:
    normalized_phrases = tuple(_normalize_lookup(phrase) for phrase in _OVERCLAIM_PHRASES)
    for value in values:
        if value is None:
            continue
        normalized_value = _normalize_lookup(value)
        if any(phrase in normalized_value for phrase in normalized_phrases):
            raise GlossaryEntryValidationError("glossary text contains a blocked overclaim phrase")


def _normalize_lookup(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    normalized = " ".join(normalized.strip().split())
    return normalized.casefold()


def _normalize_secret_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return re.sub(r"[\s_.-]+", "", normalized.casefold())


def _looks_like_local_absolute_path(value: str) -> bool:
    stripped = value.strip()
    lowered = stripped.lower()
    if lowered.startswith("file://"):
        return True
    if _WINDOWS_ABSOLUTE_PATH_RE.match(stripped):
        return True
    if stripped.startswith(("\\\\", "//")):
        return True
    return stripped.startswith("/")
