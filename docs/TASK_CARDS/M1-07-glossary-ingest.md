# TASK CARD - M1-07A Glossary Ingest

## 1. Plan Linkage
- Task bundle: B3
- Step: M1-07 glossary ingest
- Priority: P0
- Implementation base commit: `56b9c607d23dd871f0d5187a5ab7ca5c6340e84b`
- Preconditions:
  - M1-01 core models/status contract: PASS
  - M1-02 SecurityResolver: PASS
  - M1-03 provider base/config/fake: PASS
  - M1-04 RecordedNewsProvider: PASS
  - M1-05 RecordedDisclosureProvider: PASS
  - M1-06 completion SHA: `56b9c607d23dd871f0d5187a5ab7ca5c6340e84b`
  - M1-06 final independent review: `PASS`
  - M1-06 status: complete
  - M1-07A implementation entry: allowed
- Related risk IDs: R13, R14, R17, R24, R37, R43, R45, R54
- Related taxonomy: financial_term, source_selection, citation_support, intent_routing, evidence_sufficiency, abstention

## 2. Objective
Implement M1-07A, a deterministic manual glossary ingest boundary for synthetic fixtures and future reviewed glossary corpus files.

M1-07A provides schema validation, exact lookup, section locators, and coverage accounting. It does not answer questions and does not convert glossary entries into `FinancialDocument`.

## 3. Scope
Implemented in M1-07A:
- `M1-07-glossary-ingest.md` contract update.
- Top-level glossary corpus schema.
- Synthetic glossary fixture.
- Entry and corpus validation.
- Immutable or copy-safe index.
- Deterministic exact lookup.
- Section-level locator.
- Coverage calculation.
- Typed and sanitized loader errors.
- Unit tests.
- M1-01 through M1-07 regression.
- Import smoke.

Excluded from M1-07A:
- Actual glossary corpus with 15 or more real financial terms.
- Actual external source wording.
- Actual permission approval.
- Actual `data/glossary.json`.
- Retrieval, EvidencePolicy, router, API, UI, LLM, Provider protocol.
- `FinancialDocument` conversion.
- Fuzzy matching.
- Automatic semantic overclaim detection outside the fixed phrase blocklist.
- Existing M1-01 through M1-06 contract changes.

M1-07B may start only after the user separately approves the real term list, reviewed Korean definition/why/caution content, content origins, source and permission basis, and actual corpus file creation.

## 4. Fixed Names
- Module: `app.ingest.glossary`
- Source type: `glossary`
- Provider/corpus key: `manual_glossary`
- Ingestion version: `glossary-ingest-m1-07-v1`

M1-07A is not an M1-03 Provider implementation:
- It does not return `ProviderResult`.
- It does not implement retry, timeout, deadline, or cache.
- It does not attach fake security IDs to general glossary entries.
- It does not convert entries to `FinancialDocument`.

## 5. Top-Level Corpus Contract
Required wrapper fields:
- `schema_version`
- `corpus_type`
- `corpus_id`
- `language`
- `entries`

Allowed `corpus_type` values:
- `synthetic_unit`
- `review_corpus`
- `approved_corpus`

Rules:
- `schema_version` must be real int `1`; bool, string, `0`, and `2+` fail.
- `corpus_id` is a stable opaque ID.
- P0 `language` is exactly `ko`.
- Missing wrapper field fails.
- Extra wrapper field fails.
- Wrapper language and every entry language must match.
- `entries` must be a non-empty list in JSON input.
- Synthetic, review, and approved states are not mixed in one wrapper.
- `fixture_version` and `fixture_type` are not used in M1-07A.

`synthetic_unit` rules:
- Every entry has `usage_review_status == "synthetic"`.
- Every entry has `corpus_ingest_allowed is False`.
- Every entry has `external_llm_processing_allowed is False`.

`review_corpus` rules:
- Load is allowed for review.
- Entries may be pending, approved, or rejected.
- Production index creation is not allowed.
- Actual coverage completion is not recorded.

`approved_corpus` rules:
- Every entry has `usage_review_status == "approved"`.
- Every entry has `corpus_ingest_allowed is True`.
- It is a production corpus candidate.
- M1-07A uses only in-memory contract tests for approved corpus behavior.
- It is not recorded as actual corpus completion.

## 6. Public Types And Helpers
Public types:
- `GlossaryEntry`
- `GlossaryCorpusBundle`
- `GlossaryIndex`
- `GlossaryLocator`
- `GlossaryLookupResult`
- `GlossaryCoverage`

Public helpers:
- `load_glossary_entries(path) -> GlossaryCorpusBundle`
- `validate_glossary_entry(raw_entry) -> GlossaryEntry`
- `validate_glossary_corpus(raw_or_bundle, *, mode) -> tuple[GlossaryEntry, ...]`
- `build_glossary_index(raw_or_bundle, *, mode) -> GlossaryIndex`
- `lookup_glossary_entry(index, query) -> GlossaryLookupResult`
- `build_glossary_locator(bundle, entry, section) -> GlossaryLocator`
- `calculate_glossary_coverage(raw_or_bundle) -> GlossaryCoverage`

Allowed `validate_glossary_corpus` modes:
- `load`
- `synthetic_unit`
- `corpus`

Typed errors:
- `GlossaryIngestValidationError`
- `GlossaryEntryValidationError`
- `GlossaryCorpusValidationError`
- `GlossaryLookupValidationError`

All public build, lookup, locator, and coverage boundaries deep-validate public dataclass instances. Raw `TypeError`, `AttributeError`, `KeyError`, and JSON exceptions must not leak from public helpers.

## 7. Entry Contract
Required entry fields:
- `entry_id`
- `version`
- `canonical_term`
- `aliases`
- `definition`
- `why_it_matters`
- `caution`
- `language`
- `usage_review_status`
- `corpus_ingest_allowed`
- `external_llm_processing_allowed`
- `content_origin`
- `source_note`
- `permission_note`
- `ingestion_version`

Optional entry fields:
- `category`
- `formula`
- `example`
- `related_entry_ids`
- `source_url`
- `source_asset_id`

Rules:
- `entry_id` must match `^glossary:[a-z0-9][a-z0-9._-]*$`.
- `version` must be real int `1`; bool, string, and other integers fail.
- Required text fields are non-blank strings and must not expose local absolute paths.
- Optional text fields are `None` or non-blank strings; empty strings fail.
- `aliases` is a list or tuple of non-blank strings and may be empty.
- Alias/canonical collisions and duplicate aliases fail.
- `related_entry_ids` is a list or tuple of valid glossary IDs and may be empty.
- Related entry self-reference, duplicate related ID, and unresolved related ID fail at corpus validation.
- P0 `language` is `ko`.
- `ingestion_version` must be `glossary-ingest-m1-07-v1`.

## 8. Normalization And Collision
Lookup normalization order:
1. `unicodedata.normalize("NFKC", value)`
2. trim
3. collapse internal whitespace to one space
4. casefold

Corpus validation rejects:
- duplicate `entry_id`
- duplicate normalized canonical term
- alias matching its own normalized canonical term
- duplicate normalized alias within one entry
- cross-entry canonical/alias collisions
- cross-entry alias/alias collisions
- canonical or alias that is blank after normalization

Collisions are never represented as ambiguous lookup results; they fail before index creation.

## 9. Source And Permission
Allowed `content_origin` values:
- `synthetic`
- `user_authored`
- `external_source`
- `public_domain`

Rules:
- `synthetic` requires `usage_review_status == "synthetic"`, `corpus_ingest_allowed is False`, and `external_llm_processing_allowed is False`.
- Non-synthetic entries cannot use `usage_review_status == "synthetic"`.
- `external_source` requires source note, permission note, and either `source_url` or `source_asset_id`.
- `public_domain` requires source note, permission note, and either `source_url` or `source_asset_id`.
- `user_authored` actual corpus candidates require permission note.
- Source note alone, for example `Investopedia reference`, is not permission basis.
- Permission truth is stored at the entry level, not duplicated at wrapper level.

## 10. Source URL And Asset ID
`source_url` rules:
- `None` or HTTP(S) URL.
- Scheme and hostname normalized to lowercase.
- Default ports removed.
- Userinfo, fragment, invalid port, local path, and `file://` are rejected.
- Credential-like query keys are rejected across case, underscore, hyphen, dot, and percent-encoded separator variants.

Credential key targets:
- `token`
- `access_token`
- `auth_token`
- `bearer_token`
- `client_secret`
- `api_key`
- `x_api_key`
- `authorization`
- `credential`
- `signature`
- `x_amz_signature`

`source_asset_id` rules:
- Opaque registry ID using only letters, digits, dot, hyphen, and underscore.
- Contains at least one letter or digit.
- `"."`, `".."`, slash, backslash, whitespace, drive path, `file://`, and local absolute path are rejected.

## 11. Index And Lookup
Index keys:
- normalized canonical term
- normalized alias

Each key points to exactly one entry. The index must be immutable or copy-safe, and mutating the original raw input or bundle after index creation must not change lookup results. Fuzzy matching is not implemented.

Lookup result rules:
- `found`: exactly one entry, with `matched_by` equal to `canonical` or `alias`.
- `not_found`: blank query or unknown query.
- Non-string query raises `GlossaryLookupValidationError`.
- Internal mapping first-match behavior is forbidden because collisions are blocked at corpus validation.

## 12. Locator
Allowed sections:
- `definition`
- `why_it_matters`
- `caution`
- `formula`
- `example`

Locator fields:
- `corpus_id`
- `entry_id`
- `version`
- `section`
- `source_type`
- `provider`
- `ingestion_version`
- `source_url`
- `source_asset_id`

Rules:
- `definition`, `why_it_matters`, and `caution` are always locatable.
- `formula` and `example` are locatable only when the entry has a value for the requested section.
- Unsupported section and missing optional section both raise typed validation errors.
- Citation identity is `corpus_id + entry_id + version + section`.
- Locator must not contain local paths or secrets.

## 13. Coverage
Coverage fields:
- `total_entries`
- `approved_actual_entries`
- `synthetic_entries`
- `pending_entries`
- `rejected_entries`
- `minimum_required`
- `meets_minimum`
- `actual_coverage_evaluated`

Rules:
- Counts are based on distinct entry IDs after validation.
- Minimum required is 15.
- Synthetic entries are not counted as actual coverage.
- Review corpus is not actual coverage completion.
- Approved corpus is only a future actual coverage candidate in M1-07A.
- Since no real corpus is provided in M1-07A, `actual_coverage_evaluated` remains false and actual coverage is `NOT_RUN`.
- Synthetic fixture and in-memory approved-like tests must not be recorded as actual corpus completion.

## 14. Overclaim Blocklist
M1-07A implements only a fixed normalized phrase blocklist, not semantic overclaim detection.

Blocked phrases:
- `무조건 저평가`
- `반드시 상승`
- `확실한 수익`
- `always undervalued`
- `guaranteed return`

Semantic overclaim review remains a manual review responsibility.

## 15. Synthetic Fixture
Fixture path:
- `tests/fixtures/glossary/glossary_synthetic.json`

Rules:
- Uses fictional or short synthetic wording only.
- Does not copy real website text.
- Does not include real copyrighted wording.
- Every entry has `content_origin=synthetic`.
- Every entry has `usage_review_status=synthetic`.
- Every entry has `corpus_ingest_allowed=false`.
- Every entry has `external_llm_processing_allowed=false`.
- Synthetic fixture does not count as actual coverage.
- Fixture includes canonical lookup, alias lookup, formula-present, formula-absent, example-present, and related-entry cases.

## 16. Test Plan
Required targeted coverage:
- Wrapper missing/extra fields and schema version boundaries.
- Unsupported corpus type/language and empty entries.
- Wrapper/entry language mismatch.
- Synthetic, review, and approved mode contracts.
- Entry missing/extra field, invalid ID, version boundaries, blank required and optional text, invalid ingestion version, unsupported content origin, and permission basis.
- Global duplicate/collision and related-entry validation.
- Public boundary typed failures for malformed direct dataclasses and raw objects.
- Index canonical/alias/NFKC/whitespace/casefold lookup behavior.
- Index immutability and caller mapping mutation rejection.
- Locator sections and fixed identity fields.
- Coverage counts and actual coverage separation.
- Loader missing file, malformed JSON, invalid UTF-8, non-object JSON, and sanitized messages.
- M1-01 through M1-06 regression remains passing.

## 17. Verification Commands
Targeted:
```powershell
$env:PYTHONPATH = ".test_deps;."; python -m pytest tests/unit/test_glossary_ingest.py -q
```

Regression:
```powershell
$env:PYTHONPATH = ".test_deps;."; python -m pytest tests/unit/test_core_models.py tests/unit/test_status_contracts.py tests/unit/test_security_resolver.py tests/unit/test_provider_base.py tests/unit/test_config.py tests/unit/test_news_provider.py tests/unit/test_disclosure_provider.py tests/unit/test_report_ingest.py tests/unit/test_glossary_ingest.py -q
```

Smoke:
```powershell
$env:PYTHONPATH = ".test_deps;."; python -c "from app.ingest.glossary import load_glossary_entries, build_glossary_index, lookup_glossary_entry, build_glossary_locator; print('ok')"
```

## 18. Stop Conditions
- Implementing M1-07A requires changes to M1-01 through M1-06 contracts.
- Implementing M1-07A requires `FinancialDocument`, `Evidence`, Provider, retrieval, API, UI, or LLM changes.
- Actual glossary corpus content or permission decisions become necessary.
- Multiple unrelated files need modification outside the approved file list.
- Existing M1-01 through M1-06 regression fails for reasons unrelated to M1-07A.

## 19. Status
- Task Card created: 2026-07-22
- Implementation base commit: `56b9c607d23dd871f0d5187a5ab7ca5c6340e84b`
- Modified files:
  - `docs/TASK_CARDS/M1-07-glossary-ingest.md`
  - `app/ingest/glossary.py`
  - `tests/unit/test_glossary_ingest.py`
  - `tests/fixtures/glossary/glossary_synthetic.json`
- M1-07A schema: complete
- Synthetic fixture: complete
- Implementation status: complete, awaiting user review
- Targeted tests:
  - first command: `$env:PYTHONPATH = ".test_deps;."; python -m pytest tests/unit/test_glossary_ingest.py -q`
  - first exit code: `1`
  - first output: `No module named pytest.__main__; 'pytest' is a package and cannot be directly executed`
  - rerun reason: sandbox denied access to `.test_deps`; same command rerun with approved elevated test execution
  - rerun command: `$env:PYTHONPATH = ".test_deps;."; python -m pytest tests/unit/test_glossary_ingest.py -q`
  - rerun exit code: `0`
  - rerun passed count: `102`
- Regression tests:
  - command: `$env:PYTHONPATH = ".test_deps;."; python -m pytest tests/unit/test_core_models.py tests/unit/test_status_contracts.py tests/unit/test_security_resolver.py tests/unit/test_provider_base.py tests/unit/test_config.py tests/unit/test_news_provider.py tests/unit/test_disclosure_provider.py tests/unit/test_report_ingest.py tests/unit/test_glossary_ingest.py -q`
  - exit code: `0`
  - passed count: `533`
- Import smoke:
  - command: `$env:PYTHONPATH = ".test_deps;."; python -c "from app.ingest.glossary import load_glossary_entries, build_glossary_index, lookup_glossary_entry, build_glossary_locator; print('ok')"`
  - exit code: `0`
  - output: `ok`
- Actual glossary corpus: `NOT_RUN`
- Actual permission approval: `NOT_RUN`
- Actual coverage 15+: `NOT_RUN`
- Retrieval/Evidence/LLM integration: `NOT_RUN`
- GitHub CI: `NOT_RUN`
- Independent pytest rerun: `NOT_RUN`
- Commit/push: `NOT_RUN`

## 20. Git Boundary
Commit, push, PR, merge, live API calls, actual glossary corpus creation, M2 work, and LLM work require separate user approval.
