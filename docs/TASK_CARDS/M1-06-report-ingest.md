# TASK CARD - M1-06 Research Report Manual Ingest

## 1. Plan Linkage
- Task bundle: B3
- Step: M1-06 Research Report Manual Ingest
- Priority: P0
- Implementation base commit: `8aad027aa9eda6badb15a6a0b2e78674681c4764`
- Preconditions:
  - M1-01 core models/status contract: PASS
  - M1-02 SecurityResolver: PASS
  - M1-03 provider base/config/fake: PASS
  - M1-04 RecordedNewsProvider: PASS
  - M1-05 RecordedDisclosureProvider: PASS
- Related risk IDs: R02, R08, R13, R17, R25, R29, R30, R31, R32, R45, R54, R61
- Related taxonomy: source_selection, citation_support, evidence_sufficiency, stale_data, numeric_accuracy, wrong_company, abstention

## 2. Scope
Implemented:
- Report-level manifest validation.
- Section-level normalized document validation.
- Manifest/document bundle validation.
- Permission gate for synthetic, pending, approved, rejected usage states.
- Safe source locator validation.
- Publication date parsing and deterministic stale metadata.
- Text provenance and numeric claim metadata validation.
- File hash format and corpus-mode source byte verification.
- `FinancialDocument(source_type="research_report")` conversion.
- Synthetic unit fixture and tests.
- Coverage calculation that counts distinct eligible real manifests, not sections.

Excluded:
- Actual report PDFs, HTML, source URLs, copyrighted text, or real analyst report corpus.
- Usage approval decision or asset registry construction.
- Automatic segmentation, company detection, or numeric verification.
- Retrieval, EvidencePolicy, API, UI, LLM, provider, retry, timeout, cache, or live adapter code.
- M1-01 through M1-05 code contract changes.

## 3. Fixed Names
- Module: `app.ingest.reports`
- Provider field: `manual_manifest`
- Source type: `research_report`
- Ingestion version: `report-ingest-m1-06-v1`
- Public helpers:
  - `load_report_manifest`
  - `load_normalized_report_documents`
  - `validate_report_manifest`
  - `validate_report_bundle`
  - `normalize_manual_research_report`
  - `build_manual_research_documents`
  - `verify_manifest_source_hash`
  - `calculate_report_coverage`
- Build signature:
  - `build_manual_research_documents(manifest, documents, *, mode, as_of_date, source_bytes=None, available_asset_ids=None)`
- Allowed modes:
  - `synthetic_unit`
  - `corpus`

M1-06 is a manual ingest helper, not an M1-03 Provider implementation. It does not return `ProviderResult` and does not implement retry, timeout, or cache.

## 4. Manifest Contract
Required manifest fields:
- `manifest_id`
- `security_id`
- `title`
- `publisher`
- `published_at`
- `source_url`
- `source_asset_id`
- `access_note`
- `usage_note`
- `usage_review_status`
- `corpus_ingest_allowed`
- `external_llm_processing_allowed`
- `file_hash`
- `hash_scope`
- `hash_verification_status`
- `documents`
- `ingestion_version`

Optional report-level fields:
- `analyst`
- `report_type`
- `basis_date`
- `language`

Rules:
- `usage_review_status`: `synthetic`, `pending`, `approved`, `rejected`.
- `corpus_ingest_allowed` and `external_llm_processing_allowed` are strict booleans.
- `source_url` or `source_asset_id` is required.
- `access_note` alone is insufficient.
- Manifest is the single report-level truth source.
- Normalized documents must not repeat report-level fields.
- Supported securities are limited to `KRX:005930`, `KRX:000660`, `KRX:005380`.

## 5. Normalized Document Contract
Required document fields:
- `manifest_id`
- `segment_id`
- `document_id`
- `security_id`
- `mentioned_security_ids`
- `subject_scope`
- `page`
- `page_basis`
- `section`
- `text`
- `text_kind`
- `manual_verification_status`
- `contains_numeric_claims`
- `numeric_claims_verified`

Optional document fields:
- `summary_kind`

Rules:
- `document_id` is deterministic: `report:{manifest_id}:{segment_id}`.
- `segment_id` must be a stable opaque ID.
- `mentioned_security_ids` are explicit only; no auto extraction.
- `company_specific` requires no mentions.
- `company_centered_with_mentions` requires at least one mention.
- `multi_company` is rejected in P0.
- `page` is either a positive integer or null depending on `page_basis`.
- `pdf_1_based`: positive integer.
- `printed_page`: positive integer.
- `source_section_only`: null.
- `text_kind`: `source_excerpt`, `manual_summary`.
- `manual_verification_status`: `synthetic`, `pending`, `verified_against_source`.
- Numeric metadata is boolean only.
- If `contains_numeric_claims` is false, `numeric_claims_verified` must be false.

## 6. Synthetic And Corpus Separation
Bulk synthetic fixture build requires:
- Manifest `usage_review_status == "synthetic"`.
- Manifest `corpus_ingest_allowed is False`.
- Manifest `external_llm_processing_allowed is False`.
- Manifest `hash_verification_status == "synthetic"`.
- All documents `manual_verification_status == "synthetic"`.
- Synthetic wrapper fixture_type `synthetic_unit`.
- Plain list/tuple input is rejected for bulk synthetic build.

`normalize_manual_research_report()` is a documented single-document convenience exception and may operate without a wrapper after full manifest/document validation.

Corpus build requires:
- Manifest `usage_review_status == "approved"`.
- Manifest `corpus_ingest_allowed is True`.
- Manifest `hash_verification_status == "verified"`.
- All documents `manual_verification_status == "verified_against_source"`.
- Valid source URL or resolvable `source_asset_id`.
- `source_bytes` supplied and SHA-256 hash verified.
- All `NormalizedReportDocumentBundle` inputs are rejected in corpus mode.
- Corpus mode currently accepts a plain validated document sequence; a future corpus bundle requires separate approval.

Synthetic fixture output is unit-test evidence only. It is not recorded as real corpus coverage, permission approval, source hash verification, or asset availability.

## 7. Source Locator Contract
- `source_url` must be HTTP(S), include host, contain no userinfo, contain no fragment, and contain no credential-like query key.
- Credential-like query keys include case, separator, and percent-encoded variants of token, access token, auth token, bearer token, client secret, API key, x-api-key, authorization, credential, signature, and X-Amz-Signature.
- URL scheme and hostname are normalized to lowercase; default ports are removed.
- Local paths, `file://`, Windows absolute paths, POSIX absolute paths, UNC paths, and invalid ports are rejected.
- `source_asset_id` must be a registry-issued opaque ID and must not contain path semantics.
- `source_asset_id` uses only letters, digits, dot, hyphen, and underscore.
- `source_asset_id` must include at least one letter or digit.
- `"."`, `".."`, slash, backslash, drive path, whitespace, file URI, local absolute path, and temporary execution path semantics are rejected.
- Corpus mode with asset-only source requires `source_asset_id` to appear in `available_asset_ids`.
- FinancialDocument locator contains only:
  - `manifest_id`
  - `document_id`
  - `page`
  - `page_basis`
  - `section`
  - `publisher`
  - `source_url`
  - `source_asset_id`
  - `access_note`

## 8. Date And Stale Metadata
- Date-only `published_at` uses Asia/Seoul midnight and stores UTC.
- RFC3339 datetime requires timezone and stores UTC.
- Naive datetimes are rejected.
- `basis_date` is optional `YYYY-MM-DD`; no inference.
- Future publication dates are rejected at build time.
- Stale metadata uses explicit `as_of_date`.
- `age_days = as_of_date - local published date`.
- `age_days > 180` sets `is_stale_candidate=True`.
- Exactly 180 days is not stale.

## 9. Hash Contract
- `file_hash` is lowercase SHA-256, 64 hex characters.
- `hash_scope`: `source_asset_bytes`, `normalized_source_bytes`.
- `hash_verification_status`: `synthetic`, `format_only`, `verified`.
- `verify_manifest_source_hash(manifest, source_bytes)` calculates SHA-256 over supplied bytes.
- Corpus build requires supplied bytes and matching hash.
- Synthetic mode permits synthetic hash status but does not mark source hash verified.

## 10. FinancialDocument Conversion
- `document_id`: normalized deterministic document ID.
- `source_type`: `research_report`.
- `provider`: `manual_manifest`.
- `primary_security_ids`: manifest security ID.
- `mentioned_security_ids`: explicit normalized document list.
- `published_at`: manifest date normalized to timezone-aware UTC.
- `source_url`: manifest source URL or None.
- `text`: normalized section text.
- `title`: manifest title, or `{manifest.title} - {section}` when section differs.
- Title separator is fixed as ` - `.
- `metadata.content_level`: `research_report_section`.
- Metadata includes publisher, analyst, report type, basis date, language, usage fields, hash fields, publication precision/timezone, freshness fields, text provenance fields, subject scope, numeric flags, and build mode.

## 11. Synthetic Fixtures
- `tests/fixtures/reports/report_manifest_synthetic.json`
- `tests/fixtures/reports/normalized_report_synthetic.json`

Fixture limitations:
- Fake publisher/text only.
- No real URL.
- No real analyst.
- No real copyrighted report text.
- No real numeric claim evidence.
- `source_asset_id`: `synthetic-report-asset-001`.
- Usage status: synthetic.
- Corpus ingest: false.
- External LLM processing: false.
- Hash status: synthetic.

## 12. Tests
Targeted command:
```powershell
$env:PYTHONPATH = ".test_deps;."; python -m pytest tests/unit/test_report_ingest.py -q
```

Regression command:
```powershell
$env:PYTHONPATH = ".test_deps;."; python -m pytest tests/unit/test_core_models.py tests/unit/test_status_contracts.py tests/unit/test_security_resolver.py tests/unit/test_provider_base.py tests/unit/test_config.py tests/unit/test_news_provider.py tests/unit/test_disclosure_provider.py tests/unit/test_report_ingest.py -q
```

Smoke command:
```powershell
$env:PYTHONPATH = ".test_deps;."; python -c "from app.ingest.reports import load_report_manifest, normalize_manual_research_report, build_manual_research_documents; print('ok')"
```

## 13. Completion Criteria
- [x] Manifest schema implemented.
- [x] Normalized report fixture schema implemented.
- [x] Manifest validation tests passed.
- [x] Normalized document validation tests passed.
- [x] Manifest/document bundle validation tests passed.
- [x] `FinancialDocument(source_type="research_report")` conversion tests passed.
- [x] Page/section locator tests passed.
- [x] File hash verification tests passed.
- [x] Permission gate tests passed.
- [x] Source locator safety tests passed.
- [x] Security attribution tests passed.
- [x] Publication date and stale metadata tests passed.
- [x] Text provenance tests passed.
- [x] Numeric claim metadata tests passed.
- [x] Synthetic fixture and real coverage separation tests passed.
- [x] Targeted unit tests passed.
- [x] M1-01 through M1-06 regression tests passed.
- [x] Import smoke passed.
- [x] Real report corpus remains `NOT_RUN`.

## 14. Implementation Result Log
- Log date: 2026-07-22
- Implementation base commit: `8aad027aa9eda6badb15a6a0b2e78674681c4764`
- Modified files:
  - `app/ingest/__init__.py`
  - `app/ingest/reports.py`
  - `tests/unit/test_report_ingest.py`
  - `tests/fixtures/reports/report_manifest_synthetic.json`
  - `tests/fixtures/reports/normalized_report_synthetic.json`
  - `docs/TASK_CARDS/M1-05-disclosure-provider.md`
  - `docs/TASK_CARDS/M1-06-report-ingest.md`
- M1-05 status sync:
  - Base: `192207e35c902aded50d43facc3c67393f2eb3b7`
  - Initial SHA: `f20b33d7f77edc04f2c7b4599b2464c5f553d8be`
  - Supplement SHA: `8aad027aa9eda6badb15a6a0b2e78674681c4764`
  - Final independent review: `PASS`
  - M1-05 status: complete
  - M1-06 entry: possible
- Implementation status: complete, awaiting user review.
- Commit/push: `NOT_RUN`

## 14.1 Initial Review Status
- Initial implementation SHA: `b8c091c8c8ebc3651aa70c3a61768dc7cb302630`
- Initial main push: complete
- Independent review: `CONDITIONAL PASS`
- M1-06 status before supplement: mandatory supplement pending
- GitHub CI: `NOT_RUN`
- Independent pytest rerun: `NOT_RUN`

## 14.2 First CONDITIONAL PASS Supplement
- Supplement date: 2026-07-22
- Supplement SHA: `14d1013753db3de7407cf4365695fec1c7aee603`
- Supplement main push: complete
- Supplement independent review: `CONDITIONAL PASS`
- Supplement scope:
  - Corpus mode rejects `synthetic_unit` wrappers.
  - Corpus unit tests now use plain validated document sequences.
  - Coverage helper excludes synthetic wrappers from actual coverage.
  - Bundle wrapper `manifest_id` mismatch raises `ReportBundleValidationError`.
  - Wrapper `fixture_version` must be integer `1`; bool, string, and other versions fail.
  - `source_section_only` requires `page: null`; PDF/printed page bases require positive integer page.
  - `normalize_manual_research_report()` can convert a single document from a multi-section manifest without exact-set bundle validation.
  - Loader and hash errors are typed and sanitized.
  - `source_bytes` must be actual bytes.
  - Credential query key blocking covers required token/signature variants.
  - RFC3339 datetime validation is stricter and preserves input offset basis.
  - Manifest document ID suffix is validated against segment ID rules.
  - Title separator is centralized as ` - `.
- First supplement commit/push: complete

## 14.3 Second CONDITIONAL PASS Supplement
- Supplement date: 2026-07-22
- Supplement SHA: `05846bd1e8bbeef36ef7fa1fa08df378b89f13b8`
- Supplement main push: complete
- Supplement independent review: `CONDITIONAL PASS`
- Second supplement commit/push: complete
- M1-06 status after second supplement: final mandatory supplement pending

## 14.4 Final Type And Publication Supplement
- Supplement date: 2026-07-22
- Final type/publication supplement commit SHA: `56b9c607d23dd871f0d5187a5ab7ca5c6340e84b`
- Current status: complete
- Final independent review: `PASS`
- M1-07 implementation entry: allowed
- GitHub CI: `NOT_RUN`
- Independent pytest rerun: `NOT_RUN`
- Supplement scope:
  - Manifest direct dataclass malformed types are guarded before regex, enum, URL, and comparison checks.
  - Document direct dataclass malformed types are guarded before regex and enum checks.
  - Bundle direct dataclass malformed types are normalized to `ReportBundleValidationError`.
  - Public boundaries keep malformed direct instances as typed M1-06 validation errors.
  - Date precision and timezone basis combinations are validated for internal consistency.
  - Timezone offset basis is validated through Python timezone construction.
  - Coverage skips malformed direct manifest entries and continues with valid entries.
  - M16 manifest document element type checks now run before uniqueness checks, preventing raw `TypeError` for unhashable direct dataclass document IDs.

## 14.5 Final Review Sync
- Sync date: 2026-07-22
- Latest SHA: `56b9c607d23dd871f0d5187a5ab7ca5c6340e84b`
- Local HEAD verification: `56b9c607d23dd871f0d5187a5ab7ca5c6340e84b`
- Final independent review: `PASS`
- M1-06 status: complete
- M1-07 implementation entry: allowed
- Code/test changes in this sync: none; Task Card status only.

## 15. Actual Verification Results
- PYTHONPATH: `.test_deps;.`
- targeted first command: `python -m pytest tests/unit/test_report_ingest.py -q`
- targeted first exit code: `1`
- targeted first output: `No module named pytest.__main__; 'pytest' is a package and cannot be directly executed`
- targeted rerun command: `python -m pytest tests/unit/test_report_ingest.py -q`
- targeted rerun exit code: `0`
- targeted rerun passed count: `210`
- regression command: `python -m pytest tests/unit/test_core_models.py tests/unit/test_status_contracts.py tests/unit/test_security_resolver.py tests/unit/test_provider_base.py tests/unit/test_config.py tests/unit/test_news_provider.py tests/unit/test_disclosure_provider.py tests/unit/test_report_ingest.py -q`
- regression exit code: `0`
- regression passed count: `431`
- smoke first command: `python -c "from app.ingest.reports import load_report_manifest, normalize_manual_research_report, build_manual_research_documents; print('ok')"`
- smoke first exit code: `1`
- smoke first output: `ImportError: cannot import name 'BaseModel' from 'pydantic' (unknown location)`
- smoke rerun command: `python -c "from app.ingest.reports import load_report_manifest, normalize_manual_research_report, build_manual_research_documents; print('ok')"`
- smoke rerun exit code: `0`
- smoke rerun output: `ok`
- smoke passed count: `N/A`

## 16. NOT_RUN / BLOCKED
- Actual report source URLs/files: `NOT_RUN - user has not provided source corpus`
- Actual report usage approval: `NOT_RUN - user has not provided permission basis`
- Actual report asset registry resolution: `NOT_RUN`
- Actual corpus source hash verification: `NOT_RUN`
- Actual report coverage by security: `NOT_RUN`
- External LLM processing of report text: `NOT_RUN`
- Live adapter/API/retrieval/UI: `NOT_RUN`
- GitHub CI: `NOT_RUN`
- M1-07 implementation: allowed, not started in this status sync
- M2/LLM work: `NOT_RUN`

## 17. Known Limitations
- M1-06 validates manually supplied manifest and section documents only.
- It does not parse PDFs, HTML, tables, charts, or OCR.
- It does not infer report family, page numbers, company mentions, numeric truth, or latest valid source.
- It does not include real analyst report text or real coverage.
- Real corpus mode remains unusable until source files/URLs, permissions, source bytes, and asset resolution are supplied.

## 18. Review Status
- User implementation approval: `PASS`
- Independent review: `PASS`
- GitHub CI: `NOT_RUN`
- Final M1-06 status: complete.
- Completion SHA: `56b9c607d23dd871f0d5187a5ab7ca5c6340e84b`
- M1-07 implementation entry: allowed.
