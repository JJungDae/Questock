import copy
import json
import traceback
from dataclasses import replace
from pathlib import Path

import pytest

import app.ingest.glossary as glossary_module
from app.ingest.glossary import (
    GLOSSARY_INGESTION_VERSION,
    GLOSSARY_SOURCE_TYPE,
    MANUAL_GLOSSARY_PROVIDER,
    GlossaryCorpusBundle,
    GlossaryCorpusValidationError,
    GlossaryEntryValidationError,
    GlossaryIndex,
    GlossaryIngestValidationError,
    GlossaryLookupValidationError,
    build_glossary_index,
    build_glossary_locator,
    calculate_glossary_coverage,
    load_glossary_entries,
    lookup_glossary_entry,
    validate_glossary_corpus,
    validate_glossary_entry,
)

FIXTURE_PATH = Path("tests/fixtures/glossary/glossary_synthetic.json")


def corpus_data(**updates):
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    data.update(updates)
    return data


def entry_data(index=0, **updates):
    raw = json.loads(json.dumps(corpus_data()["entries"][index]))
    raw.update(updates)
    return raw


def approved_entry(number=1, **updates):
    raw = entry_data(
        0,
        entry_id=f"glossary:approved_{number}",
        canonical_term=f"승인용어{number}",
        aliases=[f"approved alias {number}"],
        usage_review_status="approved",
        corpus_ingest_allowed=True,
        external_llm_processing_allowed=False,
        content_origin="user_authored",
        source_note="User authored reviewed glossary text.",
        permission_note="User approved this glossary entry for corpus ingest.",
        source_url=None,
        source_asset_id=None,
        related_entry_ids=[],
    )
    raw.update(updates)
    return raw


def approved_ascii_entry(number=1, **updates):
    raw = approved_entry(
        number,
        canonical_term=f"approved term {number}",
        aliases=[f"approved alias {number}", f"approved alt {number}"],
    )
    raw.update(updates)
    return raw


def review_entry(status, number=1, **updates):
    raw = approved_entry(number, usage_review_status=status, corpus_ingest_allowed=status == "approved")
    raw.update(updates)
    return raw


def approved_corpus(entries=None, **updates):
    data = {
        "schema_version": 1,
        "corpus_type": "approved_corpus",
        "corpus_id": "glossary-approved-memory-v1",
        "language": "ko",
        "entries": entries or [approved_entry(1)],
    }
    data.update(updates)
    return data


def review_corpus(entries=None, **updates):
    data = {
        "schema_version": 1,
        "corpus_type": "review_corpus",
        "corpus_id": "glossary-review-memory-v1",
        "language": "ko",
        "entries": entries
        or [
            review_entry("pending", 1, corpus_ingest_allowed=False),
            review_entry("approved", 2),
            review_entry("rejected", 3, corpus_ingest_allowed=False),
        ],
    }
    data.update(updates)
    return data


def test_load_synthetic_fixture_index_lookup_locator_and_coverage():
    bundle = load_glossary_entries(FIXTURE_PATH)
    entries = validate_glossary_corpus(bundle, mode="synthetic_unit")
    index = build_glossary_index(bundle, mode="synthetic_unit")

    canonical = lookup_glossary_entry(index, "알파비율")
    alias = lookup_glossary_entry(index, " alpha   ratio ")
    locator = build_glossary_locator(bundle, entries[0], "definition")
    coverage = calculate_glossary_coverage(bundle)

    assert bundle.schema_version == 1
    assert bundle.corpus_type == "synthetic_unit"
    assert len(entries) == 3
    assert canonical.status == "found"
    assert canonical.matched_by == "canonical"
    assert canonical.matched_term == "알파비율"
    assert alias.status == "found"
    assert alias.matched_by == "alias"
    assert alias.matched_term == "ALPHA Ratio"
    assert locator.corpus_id == "glossary-synthetic-v1"
    assert locator.source_type == GLOSSARY_SOURCE_TYPE
    assert locator.provider == MANUAL_GLOSSARY_PROVIDER
    assert coverage.total_entries == 3
    assert coverage.synthetic_entries == 3
    assert coverage.approved_actual_entries == 0
    assert coverage.minimum_required == 15
    assert coverage.meets_minimum is False
    assert coverage.actual_coverage_evaluated is False


@pytest.mark.parametrize("field", ["schema_version", "corpus_type", "corpus_id", "language", "entries"])
def test_wrapper_missing_required_field(field):
    raw = corpus_data()
    raw.pop(field)

    with pytest.raises(GlossaryCorpusValidationError):
        validate_glossary_corpus(raw, mode="load")


@pytest.mark.parametrize("schema_version", [True, "1", 0, 2])
def test_wrapper_schema_version_boundaries(schema_version):
    with pytest.raises(GlossaryCorpusValidationError):
        validate_glossary_corpus(corpus_data(schema_version=schema_version), mode="load")


@pytest.mark.parametrize(
    "updates",
    [
        {"extra": "nope"},
        {"corpus_type": "fixture_type"},
        {"language": "en"},
        {"entries": []},
    ],
)
def test_wrapper_extra_unsupported_and_empty_boundaries(updates):
    with pytest.raises(GlossaryCorpusValidationError):
        validate_glossary_corpus(corpus_data(**updates), mode="load")


def test_wrapper_and_entry_language_mismatch_fails():
    raw = corpus_data()
    raw["entries"][0]["language"] = "en"

    with pytest.raises(GlossaryEntryValidationError):
        validate_glossary_corpus(raw, mode="load")


def test_synthetic_wrapper_rejects_approved_entry_mix():
    raw = corpus_data()
    raw["entries"][0] = approved_entry(1)

    with pytest.raises(GlossaryCorpusValidationError):
        validate_glossary_corpus(raw, mode="synthetic_unit")


def test_review_corpus_loads_but_production_index_fails():
    raw = review_corpus()

    entries = validate_glossary_corpus(raw, mode="load")

    assert [entry.usage_review_status for entry in entries] == ["pending", "approved", "rejected"]
    with pytest.raises(GlossaryCorpusValidationError):
        build_glossary_index(raw, mode="corpus")


def test_approved_corpus_contract_builds_index_but_is_not_actual_coverage_completion():
    raw = approved_corpus(entries=[approved_entry(number) for number in range(1, 16)])

    entries = validate_glossary_corpus(raw, mode="corpus")
    index = build_glossary_index(raw, mode="corpus")
    coverage = calculate_glossary_coverage(raw)

    assert len(entries) == 15
    assert lookup_glossary_entry(index, "승인용어1").status == "found"
    assert coverage.approved_actual_entries == 15
    assert coverage.actual_coverage_evaluated is False
    assert coverage.meets_minimum is False


@pytest.mark.parametrize(
    "entries",
    [
        [approved_entry(1), review_entry("pending", 2, corpus_ingest_allowed=False)],
        [approved_entry(1, corpus_ingest_allowed=False)],
    ],
)
def test_approved_corpus_rejects_pending_rejected_or_permission_false(entries):
    with pytest.raises(GlossaryCorpusValidationError):
        validate_glossary_corpus(approved_corpus(entries=entries), mode="corpus")


@pytest.mark.parametrize(
    "updates",
    [
        {"usage_review_status": "synthetic", "corpus_ingest_allowed": True},
        {"usage_review_status": "synthetic", "external_llm_processing_allowed": True},
        {
            "usage_review_status": "pending",
            "content_origin": "user_authored",
            "corpus_ingest_allowed": True,
        },
        {
            "usage_review_status": "pending",
            "content_origin": "user_authored",
            "external_llm_processing_allowed": True,
        },
        {
            "usage_review_status": "rejected",
            "content_origin": "user_authored",
            "corpus_ingest_allowed": True,
        },
        {
            "usage_review_status": "rejected",
            "content_origin": "user_authored",
            "external_llm_processing_allowed": True,
        },
        {"corpus_ingest_allowed": False, "external_llm_processing_allowed": True},
    ],
)
def test_permission_gate_rejects_unapproved_or_llm_without_corpus(updates):
    with pytest.raises(GlossaryEntryValidationError):
        validate_glossary_entry(approved_entry(1, **updates))


@pytest.mark.parametrize(
    "updates",
    [
        {"usage_review_status": "pending", "content_origin": "user_authored", "corpus_ingest_allowed": False},
        {"usage_review_status": "rejected", "content_origin": "user_authored", "corpus_ingest_allowed": False},
        {"corpus_ingest_allowed": False, "external_llm_processing_allowed": False},
        {"corpus_ingest_allowed": True, "external_llm_processing_allowed": False},
        {"corpus_ingest_allowed": True, "external_llm_processing_allowed": True},
    ],
)
def test_permission_gate_allows_supported_review_and_approved_combinations(updates):
    entry = validate_glossary_entry(approved_entry(1, **updates))

    assert entry.external_llm_processing_allowed is updates.get("external_llm_processing_allowed", False)


@pytest.mark.parametrize(
    "field",
    [
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
    ],
)
def test_entry_missing_required_field(field):
    raw = entry_data()
    raw.pop(field)

    with pytest.raises(GlossaryEntryValidationError):
        validate_glossary_entry(raw)


@pytest.mark.parametrize(
    "updates",
    [
        {"extra": "nope"},
        {"entry_id": "bad:id"},
        {"version": True},
        {"version": "1"},
        {"version": 2},
        {"canonical_term": "   "},
        {"aliases": ["   "]},
        {"aliases": ["알파비율"]},
        {"aliases": ["dup", " DUP "]},
        {"formula": ""},
        {"example": ""},
        {"ingestion_version": "future"},
        {"content_origin": "scraped"},
        {"content_origin": "external_source", "source_url": None, "source_asset_id": None},
        {"definition": "무조건 저평가 상태를 뜻한다."},
        {"source_note": "C:\\secret\\source.txt"},
    ],
)
def test_entry_validation_boundaries(updates):
    with pytest.raises(GlossaryEntryValidationError):
        validate_glossary_entry(entry_data(**updates))


@pytest.mark.parametrize(
    "updates",
    [
        {"source_url": "HTTPS://Example.COM:443/path?q=1"},
        {"source_asset_id": "asset.glossary-001"},
    ],
)
def test_entry_source_url_and_asset_success_boundaries(updates):
    raw = approved_entry(1, content_origin="user_authored", **updates)

    entry = validate_glossary_entry(raw)

    if updates.get("source_url"):
        assert entry.source_url == "https://example.com/path?q=1"
    if updates.get("source_asset_id"):
        assert entry.source_asset_id == "asset.glossary-001"


@pytest.mark.parametrize("source_url", ["https://example.com/path", "HTTPS://Example.COM:443/path?q=1"])
def test_entry_source_url_userinfo_success_baseline(source_url):
    entry = validate_glossary_entry(approved_entry(1, source_url=source_url))

    assert entry.source_url in {"https://example.com/path", "https://example.com/path?q=1"}


@pytest.mark.parametrize(
    "source_url",
    [
        "https://example.com/path?api-key=secret",
        "https://example.com/path?ACCESS_TOKEN=secret",
        "https://example.com/path?client%2Esecret=secret",
        "https://example.com/path?X-Amz-Signature=secret",
        "https://@example.com/path",
        "https://:@example.com/path",
        "https://user:@example.com/path",
        "https://:pass@example.com/path",
        "https://user:pass@example.com/path",
        "https://example.com/path#fragment",
        "https://example.com:bad/path",
        "file:///C:/secret/glossary.json",
        "C:\\secret\\glossary.json",
    ],
)
def test_entry_source_url_rejects_unsafe_values(source_url):
    with pytest.raises(GlossaryEntryValidationError):
        validate_glossary_entry(approved_entry(1, source_url=source_url))


@pytest.mark.parametrize("source_asset_id", [".", "..", "bad/id", "bad\\id", "C:\\asset\\id", "file://asset", "   "])
def test_entry_source_asset_id_rejects_unsafe_values(source_asset_id):
    with pytest.raises(GlossaryEntryValidationError):
        validate_glossary_entry(approved_entry(1, source_asset_id=source_asset_id))


@pytest.mark.parametrize(
    "mutate",
    [
        lambda raw: raw["entries"].append(copy.deepcopy(raw["entries"][0])),
        lambda raw: raw["entries"].__setitem__(1, {**raw["entries"][1], "canonical_term": "알파비율"}),
        lambda raw: raw["entries"].__setitem__(1, {**raw["entries"][1], "aliases": ["알파비율"]}),
        lambda raw: raw["entries"].__setitem__(1, {**raw["entries"][1], "aliases": ["ALPHA Ratio"]}),
        lambda raw: raw["entries"].__setitem__(0, {**raw["entries"][0], "related_entry_ids": ["glossary:alpha_ratio"]}),
        lambda raw: raw["entries"].__setitem__(
            0, {**raw["entries"][0], "related_entry_ids": ["glossary:beta_base", "glossary:beta_base"]}
        ),
        lambda raw: raw["entries"].__setitem__(
            0, {**raw["entries"][0], "related_entry_ids": ["glossary:missing"]}
        ),
    ],
)
def test_global_integrity_failures(mutate):
    raw = corpus_data()
    mutate(raw)

    with pytest.raises(GlossaryIngestValidationError):
        validate_glossary_corpus(raw, mode="load")


def test_direct_dataclass_malformed_entry_and_bundle_are_deep_validated():
    entry = validate_glossary_entry(entry_data())
    bundle = load_glossary_entries(FIXTURE_PATH)

    malformed_entry = replace(entry, aliases=(["bad"],))
    malformed_bundle = replace(bundle, entries=({"bad": "value"},))

    with pytest.raises(GlossaryEntryValidationError):
        validate_glossary_entry(malformed_entry)
    with pytest.raises(GlossaryIngestValidationError):
        validate_glossary_corpus(malformed_bundle, mode="load")


@pytest.mark.parametrize("raw", ["bad", b"bad", ["bad"], object()])
def test_public_corpus_boundary_rejects_raw_objects_with_typed_error(raw):
    with pytest.raises(GlossaryCorpusValidationError):
        validate_glossary_corpus(raw, mode="load")


def test_lookup_normalization_not_found_and_type_boundaries():
    index = build_glossary_index(load_glossary_entries(FIXTURE_PATH), mode="synthetic_unit")

    nfkc = lookup_glossary_entry(index, "ＡＬＰＨＡ　Ratio")
    whitespace = lookup_glossary_entry(index, "  알파   비율  ")
    blank = lookup_glossary_entry(index, "   ")
    unknown = lookup_glossary_entry(index, "없는 용어")

    assert nfkc.status == "found"
    assert nfkc.matched_by == "alias"
    assert whitespace.status == "found"
    assert whitespace.matched_term == "알파 비율"
    assert blank.status == "not_found"
    assert unknown.status == "not_found"
    with pytest.raises(GlossaryLookupValidationError):
        lookup_glossary_entry(index, 123)  # type: ignore[arg-type]


def test_index_is_copy_safe_and_mapping_is_read_only():
    raw = corpus_data()
    index = build_glossary_index(raw, mode="synthetic_unit")
    raw["entries"][0]["canonical_term"] = "변경된용어"
    raw["entries"][0]["aliases"].append("새별칭")

    assert lookup_glossary_entry(index, "알파비율").status == "found"
    assert lookup_glossary_entry(index, "변경된용어").status == "not_found"
    with pytest.raises(TypeError):
        index.lookup_map["new"] = index.lookup_map["알파비율"]  # type: ignore[index]


def direct_index(entries, *, corpus_id="glossary-direct-v1", corpus_type="synthetic_unit", language="ko", mutate=None):
    lookup = {}
    for entry in entries:
        lookup[glossary_module._normalize_lookup(entry.canonical_term)] = (entry, "canonical", entry.canonical_term)
        for alias in entry.aliases:
            lookup[glossary_module._normalize_lookup(alias)] = (entry, "alias", alias)
    if mutate is not None:
        mutate(lookup, entries)
    return GlossaryIndex(corpus_id=corpus_id, corpus_type=corpus_type, language=language, _lookup=lookup)


def synthetic_entries():
    return load_glossary_entries(FIXTURE_PATH).entries


def approved_entries(count=1):
    return tuple(validate_glossary_entry(approved_ascii_entry(number)) for number in range(1, count + 1))


@pytest.mark.parametrize(
    "index",
    [
        GlossaryIndex("glossary-direct-v1", "synthetic_unit", "ko", {}),
        GlossaryIndex("bad/id", "synthetic_unit", "ko", {"key": "bad"}),
        GlossaryIndex(123, "synthetic_unit", "ko", {"key": "bad"}),  # type: ignore[arg-type]
        GlossaryIndex("glossary-direct-v1", "unsupported", "ko", {"key": "bad"}),
        GlossaryIndex("glossary-direct-v1", "review_corpus", "ko", {"key": "bad"}),
        GlossaryIndex("glossary-direct-v1", "synthetic_unit", "en", {"key": "bad"}),
        GlossaryIndex("glossary-direct-v1", "synthetic_unit", "ko", "bad"),  # type: ignore[arg-type]
        GlossaryIndex("glossary-direct-v1", "synthetic_unit", "ko", {"": "bad"}),
        GlossaryIndex("glossary-direct-v1", "synthetic_unit", "ko", {123: "bad"}),  # type: ignore[dict-item]
        GlossaryIndex("glossary-direct-v1", "synthetic_unit", "ko", {"key": ("bad",)}),
    ],
)
def test_direct_index_basic_boundaries_fail_with_lookup_error(index):
    with pytest.raises(GlossaryLookupValidationError):
        lookup_glossary_entry(index, "anything")


def test_direct_index_malformed_entry_fails_with_lookup_error():
    entry = replace(synthetic_entries()[0], aliases=(["bad"],))
    index = GlossaryIndex(
        "glossary-direct-v1",
        "synthetic_unit",
        "ko",
        {glossary_module._normalize_lookup(entry.canonical_term): (entry, "canonical", entry.canonical_term)},
    )

    with pytest.raises(GlossaryLookupValidationError):
        lookup_glossary_entry(index, entry.canonical_term)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda lookup, entries: lookup.__setitem__("forged", (entries[0], "canonical", entries[0].canonical_term)),
        lambda lookup, entries: lookup.__setitem__("forgedalias", (entries[0], "alias", entries[0].aliases[0])),
        lambda lookup, entries: lookup.__setitem__(
            glossary_module._normalize_lookup(entries[0].canonical_term), (entries[0], "canonical", entries[0].aliases[0])
        ),
        lambda lookup, entries: lookup.__setitem__(
            glossary_module._normalize_lookup(entries[0].aliases[0]), (entries[0], "alias", entries[0].canonical_term)
        ),
        lambda lookup, entries: lookup.__setitem__(
            glossary_module._normalize_lookup("missing alias"), (entries[0], "alias", "missing alias")
        ),
        lambda lookup, entries: lookup.__setitem__("ALPHA Ratio", (entries[0], "alias", entries[0].aliases[0])),
        lambda lookup, entries: lookup.__setitem__(
            glossary_module._normalize_lookup(entries[0].aliases[0]), (entries[1], "alias", entries[0].aliases[0])
        ),
    ],
)
def test_direct_index_semantic_tuple_failures(mutate):
    index = direct_index(synthetic_entries(), mutate=mutate)

    with pytest.raises(GlossaryLookupValidationError):
        lookup_glossary_entry(index, "anything")


def test_direct_index_same_entry_id_with_different_content_fails():
    first = synthetic_entries()[0]
    second = replace(first, canonical_term="different direct term", aliases=())
    index = GlossaryIndex(
        "glossary-direct-v1",
        "synthetic_unit",
        "ko",
        {
            glossary_module._normalize_lookup(first.canonical_term): (first, "canonical", first.canonical_term),
            glossary_module._normalize_lookup(first.aliases[0]): (first, "alias", first.aliases[0]),
            glossary_module._normalize_lookup(first.aliases[1]): (first, "alias", first.aliases[1]),
            glossary_module._normalize_lookup(second.canonical_term): (second, "canonical", second.canonical_term),
        },
    )

    with pytest.raises(GlossaryLookupValidationError):
        lookup_glossary_entry(index, first.canonical_term)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda lookup, entries: lookup.pop(glossary_module._normalize_lookup(entries[0].canonical_term)),
        lambda lookup, entries: lookup.pop(glossary_module._normalize_lookup(entries[0].aliases[0])),
        lambda lookup, entries: lookup.pop(glossary_module._normalize_lookup(entries[0].aliases[1])),
        lambda lookup, entries: lookup.__setitem__("extra", (entries[0], "canonical", entries[0].canonical_term)),
    ],
)
def test_direct_index_key_completeness_failures(mutate):
    index = direct_index(synthetic_entries(), mutate=mutate)

    with pytest.raises(GlossaryLookupValidationError):
        lookup_glossary_entry(index, "anything")


@pytest.mark.parametrize(
    "index",
    [
        direct_index(approved_entries(), corpus_type="synthetic_unit"),
        direct_index(synthetic_entries(), corpus_type="approved_corpus"),
        direct_index(
            (validate_glossary_entry(approved_ascii_entry(1, corpus_ingest_allowed=False)),),
            corpus_type="approved_corpus",
        ),
        direct_index((replace(synthetic_entries()[0], language="en"),), language="ko"),
        direct_index(
            (validate_glossary_entry(approved_ascii_entry(1, related_entry_ids=["glossary:missing"])),),
            corpus_type="approved_corpus",
        ),
    ],
)
def test_direct_index_corpus_entry_mismatch_failures(index):
    with pytest.raises(GlossaryLookupValidationError):
        lookup_glossary_entry(index, "anything")


def test_direct_index_global_collision_failure():
    first, second = approved_entries(2)
    second = replace(second, aliases=(first.canonical_term,))
    index = direct_index((first, second), corpus_type="approved_corpus")

    with pytest.raises(GlossaryLookupValidationError):
        lookup_glossary_entry(index, first.canonical_term)


def test_direct_index_valid_synthetic_success():
    entry = synthetic_entries()[0]
    index = direct_index(synthetic_entries(), corpus_type="synthetic_unit")

    result = lookup_glossary_entry(index, entry.canonical_term)

    assert result.status == "found"


def test_direct_index_valid_approved_success():
    entry = approved_entries()[0]
    index = direct_index((entry,), corpus_type="approved_corpus")

    result = lookup_glossary_entry(index, entry.canonical_term)

    assert result.status == "found"


def test_validate_index_returns_sanitized_immutable_copy():
    raw_lookup = {}
    entries = synthetic_entries()
    entry = entries[0]
    for indexed_entry in entries:
        raw_lookup[glossary_module._normalize_lookup(indexed_entry.canonical_term)] = (
            indexed_entry,
            "canonical",
            indexed_entry.canonical_term,
        )
        for alias in indexed_entry.aliases:
            raw_lookup[glossary_module._normalize_lookup(alias)] = (indexed_entry, "alias", alias)
    direct = GlossaryIndex("glossary-direct-v1", "synthetic_unit", "ko", raw_lookup)

    sanitized = glossary_module._validate_index(direct)
    raw_lookup.clear()

    assert sanitized is not direct
    assert lookup_glossary_entry(sanitized, entry.canonical_term).status == "found"
    with pytest.raises(TypeError):
        sanitized.lookup_map["new"] = sanitized.lookup_map[glossary_module._normalize_lookup(entry.canonical_term)]  # type: ignore[index]


@pytest.mark.parametrize("section", ["definition", "why_it_matters", "caution", "formula", "example"])
def test_locator_success_sections(section):
    bundle = load_glossary_entries(FIXTURE_PATH)
    entry = bundle.entries[0]

    locator = build_glossary_locator(bundle, entry, section)

    assert locator.corpus_id == bundle.corpus_id
    assert locator.entry_id == entry.entry_id
    assert locator.version == 1
    assert locator.section == section
    assert locator.source_type == GLOSSARY_SOURCE_TYPE
    assert locator.provider == MANUAL_GLOSSARY_PROVIDER
    assert locator.ingestion_version == GLOSSARY_INGESTION_VERSION
    assert "C:\\" not in str(locator)
    assert "secret" not in str(locator).casefold()


@pytest.mark.parametrize("section", ["formula", "example"])
def test_locator_missing_optional_section_fails(section):
    bundle = load_glossary_entries(FIXTURE_PATH)
    entry_without_optional_sections = bundle.entries[1]

    with pytest.raises(GlossaryCorpusValidationError):
        build_glossary_locator(bundle, entry_without_optional_sections, section)


def test_locator_unsupported_or_foreign_entry_fails():
    bundle = load_glossary_entries(FIXTURE_PATH)
    foreign_entry = validate_glossary_entry(entry_data(entry_id="glossary:foreign", canonical_term="외부항목"))

    with pytest.raises(GlossaryCorpusValidationError):
        build_glossary_locator(bundle, bundle.entries[0], "summary")
    with pytest.raises(GlossaryCorpusValidationError):
        build_glossary_locator(bundle, foreign_entry, "definition")


def test_coverage_counts_review_statuses_and_keeps_actual_coverage_not_run():
    raw = review_corpus()

    coverage = calculate_glossary_coverage(raw)

    assert coverage.total_entries == 3
    assert coverage.pending_entries == 1
    assert coverage.approved_actual_entries == 0
    assert coverage.rejected_entries == 1
    assert coverage.synthetic_entries == 0
    assert coverage.minimum_required == 15
    assert coverage.actual_coverage_evaluated is False
    assert coverage.meets_minimum is False


@pytest.mark.parametrize(
    "writer",
    [
        lambda path: path.write_text("{not json", encoding="utf-8"),
        lambda path: path.write_bytes(b"\xff\xfe\x00"),
        lambda path: path.write_text('["not-object"]', encoding="utf-8"),
    ],
)
def test_loader_errors_are_typed_and_sanitized(tmp_path, writer):
    path = tmp_path / "sentinel_secret_fixture.json"
    writer(path)

    with pytest.raises(GlossaryIngestValidationError) as exc_info:
        load_glossary_entries(path)

    rendered = "".join(traceback.format_exception_only(type(exc_info.value), exc_info.value)).casefold()
    assert "sentinel" not in rendered
    assert "secret" not in rendered
    assert str(path).casefold() not in rendered
    assert "not json" not in rendered


def test_loader_missing_file_is_typed_and_sanitized(tmp_path):
    path = tmp_path / "sentinel_secret_missing.json"

    with pytest.raises(GlossaryCorpusValidationError) as exc_info:
        load_glossary_entries(path)

    rendered = "".join(traceback.format_exception_only(type(exc_info.value), exc_info.value)).casefold()
    assert "sentinel" not in rendered
    assert "secret" not in rendered
    assert str(path).casefold() not in rendered


@pytest.mark.parametrize(
    "phrase",
    ["무조건 저평가", "반드시 상승", "확실한 수익", "always undervalued", "guaranteed return"],
)
def test_fixed_overclaim_blocklist_rejects_configured_phrases(phrase):
    with pytest.raises(GlossaryEntryValidationError):
        validate_glossary_entry(entry_data(definition=f"이 문장은 {phrase} 표현을 포함합니다."))


def test_smoke_public_import_surface_is_available():
    bundle = load_glossary_entries(FIXTURE_PATH)
    index = build_glossary_index(bundle, mode="synthetic_unit")
    result = lookup_glossary_entry(index, "감마노트")
    locator = build_glossary_locator(bundle, result.entry, "example")

    assert result.status == "found"
    assert locator.section == "example"
