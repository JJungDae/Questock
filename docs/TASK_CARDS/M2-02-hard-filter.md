# TASK CARD - M2-02 Hard Filter

## 1. Status and Approval

- Task bundle: `B4: M2-01~03`
- Step: `M2-02 Hard Filter`
- Planning date: `2026-07-23`
- Planning base branch: `main`
- Planning base commit: `5ffef6ca47c1ad8961bd717bb5623742bab8ddcb`
- M2-01 status at planning time: `PASS WITH REQUIRED FOLLOW-UP`
- M2-01 final closure fix SHA: `5ffef6ca47c1ad8961bd717bb5623742bab8ddcb`
- M2-01 final closure fix main push: `complete`
- M1-09 recorded status: `mandatory supplement implemented - final independent review pending`
- M1-09 provider completion: `pending final PASS`
- Current status: `PASS in local implementation environment - user review pending`
- Implementation approval: `APPROVED by user request after corrected M2-02 plan review`
- Commit/push/PR/merge/deploy: `NOT_APPROVED`
- Live API/LLM/provider/retrieval ranking/API/UI work: `OUT_OF_SCOPE`
- M2-03 retrieval baseline: `NOT_STARTED`

This Task Card plans only the deterministic M2-02 hard-filter layer and the required M2-01 preflight synchronization. It does not authorize commit, push, PR, merge, deploy, live API calls, provider changes, retrieval ranking, Evidence generation, API/UI work, or LLM work.

---

## 2. Required Preflight Gate

Run this gate from repository root on `main` before editing M2-02 implementation files.

### 2.1 Git baseline

```powershell
git status --short
git rev-parse HEAD
git log -1 --oneline
```

Expected:

```text
HEAD = 5ffef6ca47c1ad8961bd717bb5623742bab8ddcb
latest commit = m2-01 conditional pass2 updates
```

If the working tree is not clean, do not use reset, restore, checkout, clean, stash, or another destructive operation. Record the existing changes and stop.

### 2.2 M2-01 targeted pytest

```powershell
$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_query_planner.py -q
```

### 2.3 Full unit regression

```powershell
$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit -q
```

### 2.4 QueryPlanner import smoke

```powershell
$env:PYTHONPATH = ".deps;."; python -c "from app.planning.query_planner import QueryPlanner; print('ok')"
```

### 2.5 Secret scan

```powershell
python scripts/secret_scan.py
```

### 2.6 Compile

```powershell
python -m compileall app tests scripts -q
```

### 2.7 M2-01 Task Card final synchronization

After every preflight command exits `0`, update `docs/TASK_CARDS/M2-01-query-planner.md` as a preflight-only synchronization.

Record at least:

```text
Current status: PASS / complete
Final closure fix SHA: 5ffef6ca47c1ad8961bd717bb5623742bab8ddcb
Final closure fix commit: m2-01 conditional pass2 updates
Final closure fix main push: complete
Final closure review: PASS WITH REQUIRED FOLLOW-UP
Final preflight verification: PASS
M2-02 planning entry: ALLOWED
M2-02 implementation entry: ALLOWED
GitHub CI: NOT_RUN
Independent pytest rerun: NOT_RUN
```

Also record the actual targeted/full-regression pass counts and the exit codes for smoke, secret scan, and compile.

Keep the M1-09 state unchanged:

```text
mandatory supplement implemented - final independent review pending
provider completion pending final PASS
A15-M remains data-qualified stretch candidate
```

### 2.8 Gate decision

- If every command exits `0` and the M2-01 Task Card synchronization is complete, M2-02 implementation may begin without another M2-01 review.
- If any command fails, the baseline SHA differs, the working tree is unexpectedly dirty, or synchronization cannot be completed safely, stop before editing M2-02 implementation files and report the exact result.
- The preflight synchronization does not authorize commit or push.

---

## 3. Goal and Boundary

M2-02 adds a deterministic hard filter that excludes `FinancialDocument` and already-normalized `Evidence` objects that cannot safely be used for a `RetrievalRequest`.

It filters by:

- target `security_id`
- requested source types
- optional `DateRange`
- optional `document_types`
- document primary/mentioned security metadata
- Evidence subject/mentioned/scope metadata
- linked-document integrity when `documents_by_id` is supplied

M2-02 does not score, rank, search, chunk, generate Evidence, call providers, call LLMs, compose answers, or change core models.

---

## 4. Existing Verified Inputs

Use, do not redesign:

- `FinancialDocument`, `Evidence`, `RetrievalRequest`, and `DateRange` in `app/core/models.py`
- `EvidenceScope`: `company_specific`, `industry_common`, `multi_company`
- source type strings: `news`, `disclosure`, `research_report`, `glossary`
- `ensure_evidence_matches_document()` for the existing document/evidence ID-union contract
- M2-01 `QueryPlanner` output and `required_sources`
- standard-library `zoneinfo.ZoneInfo` for `Asia/Seoul`

Current metadata observations that the filter must tolerate:

- recorded news documents may have no supported document-type metadata field
- disclosure documents use `metadata["content_level"] == "listing_metadata"`
- research-report documents use `metadata["content_level"] == "research_report_section"`

Do not add new status enum values, model fields, dependencies, provider logic, corpus loaders, or a second metadata schema.

---

## 5. Planned Files

### New files

- `app/retrieval/__init__.py`
- `app/retrieval/filters.py`
- `tests/unit/test_retrieval_filters.py`

### Modified files

- `docs/TASK_CARDS/M2-01-query-planner.md`
  - preflight result and final status synchronization only
- `docs/TASK_CARDS/M2-02-hard-filter.md`
  - implementation result recording only

### Do not modify

- `app/core/models.py`
- `app/core/status.py`
- `app/core/resolver.py`
- `app/planning/query_planner.py`
- `app/providers/**`
- `app/ingest/**`
- `data/**`
- provider/news/disclosure/report/glossary fixture files
- API/UI/LLM files
- dependency files

If another file appears necessary, stop and report why. Do not expand scope implicitly.

---

## 6. Contract

### 6.1 Public API

```python
def filter_financial_documents(
    documents: Sequence[FinancialDocument],
    request: RetrievalRequest,
) -> list[FinancialDocument]:
    ...

def filter_evidence(
    evidence: Sequence[Evidence],
    request: RetrievalRequest,
    *,
    documents_by_id: Mapping[str, FinancialDocument] | None = None,
) -> list[Evidence]:
    ...
```

Define:

```python
class HardFilterValidationError(ValueError):
    """Raised when the public hard-filter input boundary is malformed."""
```

Export `HardFilterValidationError`, `filter_financial_documents`, and `filter_evidence` from `app/retrieval/__init__.py`.

### 6.2 Public-boundary validation

Validate before ordinary filtering:

- `request` must be a `RetrievalRequest`
- `documents` and `evidence` must be non-string `Sequence` objects
- reject `str`, `bytes`, `bytearray`, and mappings as the sequence input
- every document item must be a `FinancialDocument`
- every evidence item must be an `Evidence`
- `documents_by_id`, when supplied, must be a `Mapping`
- every mapping key must be a `str`
- every mapping value must be a `FinancialDocument`
- each mapping key must equal the mapped document's `document_id`

Malformed public inputs raise sanitized `HardFilterValidationError`.

Error messages must not include:

- local paths
- raw exception text
- document text
- Evidence snippets
- locator values
- metadata values
- credentials or raw serialized objects

Do not broadly catch unrelated internal exceptions.

### 6.3 Output and mutation contract

- return a fresh outer `list`
- preserve input order
- return the original validated model objects; do not deep-copy or reconstruct them
- do not mutate the input sequence, request, models, metadata, locator, or nested lists
- mutation of the returned outer list must not change the input sequence
- the contract does not promise isolation from a caller later mutating the returned model object itself

### 6.4 Shared document structural gate

Use one internal deterministic structural check for a document:

- source type exact match
- target security connection
- requested document type proof

This structural gate does **not** apply the date range. Date is handled separately so Evidence can follow the Evidence-first date precedence in section 6.6.

### 6.5 FinancialDocument filter

A `FinancialDocument` passes only if every applicable rule passes:

1. `document.source_type` is exactly in `request.source_types`.
2. `request.security_id` is present in either:
   - `document.primary_security_ids`, or
   - `document.mentioned_security_ids`.
3. If `request.document_types is None`, no document-type filter is applied.
4. If `request.document_types == []`, no document can prove a requested type, so the result is empty.
5. If document types are requested, at least one of these metadata fields must be a string exactly contained in `request.document_types`:
   - `document_type`
   - `report_type`
   - `content_level`
6. Missing, blank, non-string, or unsupported document-type metadata does not match.
7. If `request.date_range` is present:
   - `document.published_at` must be present
   - it must be timezone-aware
   - its `Asia/Seoul` local date must be inside the inclusive range
8. If no date range is requested, a missing or naive `published_at` does not by itself exclude the document.

Other rules:

- empty `request.source_types` returns an empty result
- unsupported source types match nothing
- do not infer document types from title, text, provider, locator, or source type
- do not determine relevance, top-k, freshness warnings, legal validity, latest effective disclosure, or answerability

A naive datetime must never be interpreted through the machine's local timezone.

### 6.6 Evidence filter and linked-document integrity

`filter_evidence()` accepts only existing `Evidence` objects. It does not create, normalize, score, or rewrite Evidence.

#### Base Evidence rules

An Evidence item must satisfy:

- `evidence.source_type` is exactly in `request.source_types`
- its scope-specific target-security contract in section 6.7
- its effective date contract in section 6.8
- its document-type proof contract in section 6.9

#### When `documents_by_id` is supplied

The Evidence is excluded unless all are true:

1. `evidence.document_id` exists in the mapping.
2. The mapping key equals the linked document's `document_id`.
3. `evidence.source_type == linked_document.source_type`.
4. `ensure_evidence_matches_document(evidence, linked_document)` passes.
5. The linked document passes the shared **structural** document gate:
   - source
   - target connection
   - document type
   - not the document date gate
6. The stronger subject-attribution rules in section 6.7 pass.

`ensure_evidence_matches_document()` failure is a normal exclusion, not a public validation exception. Do not expose its raw exception.

The linked document's date must not independently override or double-filter an Evidence object that has its own `published_at`.

#### When `documents_by_id` is omitted

- Evidence may be filtered using only its own validated fields.
- If a requested property cannot be proven without a linked document, exclude rather than guess.
- In particular, requested `document_types` cannot be proven without a linked document.

### 6.7 Scope and company-attribution rules

#### `company_specific`

Pass only when:

- `subject_security_ids == [request.security_id]`
- if a linked document exists, `request.security_id` is in the linked document's `primary_security_ids`

A document that merely mentions the target cannot support company-specific Evidence claiming the target as subject.

#### `multi_company`

Pass only when:

- `request.security_id` is in `subject_security_ids`
- if a linked document exists, every Evidence `subject_security_id` is in the linked document's `primary_security_ids`

Mention-only company IDs cannot be promoted to Evidence subjects.

#### `industry_common`

Pass only when:

- `subject_security_ids` is empty
- target connection is proven by at least one of:
  - `request.security_id` in `evidence.mentioned_security_ids`
  - a linked document that passes the structural gate and contains the target in either primary or mentioned security IDs

Evidence connected only to another company is excluded.

### 6.8 Evidence date precedence

When `request.date_range` is present, determine exactly one effective timestamp:

1. use `evidence.published_at` when it is present and timezone-aware
2. otherwise use linked-document `published_at` when a linked document exists and its timestamp is timezone-aware
3. otherwise exclude

Convert the effective timestamp to the `Asia/Seoul` local date and apply inclusive start/end boundaries.

Important:

- Evidence timestamp is authoritative when present.
- Evidence inside range + linked document outside range passes if every non-date rule passes.
- Evidence outside range + linked document inside range is excluded.
- Evidence with no timestamp may fall back to the linked document timestamp.
- naive timestamps are treated as unavailable, never as system-local time.
- without a requested date range, missing or naive timestamps do not by themselves exclude Evidence.

### 6.9 Evidence document-type proof

- If `request.document_types is None`, no Evidence document-type filter is applied.
- If document types are requested, `documents_by_id` and a valid linked document are required.
- The linked document must prove at least one requested type through the exact metadata fields defined in section 6.5.
- Evidence is excluded when the requested document type cannot be proven.
- Do not infer a document type from Evidence title, snippet, locator, or source type.

### 6.10 Glossary contract

Glossary corpus items are not `FinancialDocument` retrieval candidates in M2-02.

- `financial_term` routing remains owned by M2-01 and glossary ingest.
- M2-02 does not change glossary lookup behavior.
- If a future glossary Evidence object is passed, the same public-boundary, source, scope, date, and linked-document proof rules apply.
- Because `RetrievalRequest.security_id` is required, M2-02 does not invent a security-independent glossary retrieval request.

---

## 7. Tests

Create exact tests in `tests/unit/test_retrieval_filters.py`.

### 7.1 Public input validation

- non-`RetrievalRequest` request raises sanitized `HardFilterValidationError`
- `str`, `bytes`, mapping, generator, and scalar sequence inputs are rejected according to the declared `Sequence` API
- wrong document item type raises sanitized error
- wrong Evidence item type raises sanitized error
- non-mapping `documents_by_id` raises sanitized error
- non-string mapping key raises sanitized error
- non-`FinancialDocument` mapping value raises sanitized error
- mapping key/document ID mismatch raises sanitized error
- no error contains raw text, snippet, locator, metadata, or path content

### 7.2 Document filtering

- source type filter keeps only requested sources
- empty source types return empty
- unsupported source type matches nothing
- target in `primary_security_ids` passes
- target in `mentioned_security_ids` passes at document level
- wrong-company document is excluded
- multiple input documents preserve input order and do not first-match
- date start boundary inclusive
- date end boundary inclusive
- out-of-range document excluded
- `published_at=None` excluded with date range
- naive `published_at` excluded with date range
- `published_at=None` allowed without date range
- naive `published_at` allowed without date range
- UTC timestamp crossing midnight uses Asia/Seoul date
- open start-only range
- open end-only range
- `document_types=None` does not filter
- `document_types=[]` returns empty
- exact `document_type` match
- exact `report_type` match
- exact `content_level` match
- missing metadata field excludes when type requested
- blank or non-string metadata value excludes
- title/text/provider/locator are not used to guess type
- result outer list is fresh
- original order and model identity are preserved
- request and nested model fields are not mutated

### 7.3 Evidence scope and attribution

- company-specific target passes
- company-specific other company excluded
- company-specific target with linked target-primary document passes
- company-specific target with linked target-mentioned-only document excluded
- multi-company Evidence containing target passes
- multi-company Evidence not containing target excluded
- linked multi-company Evidence passes only when every subject is document-primary
- subject present only as linked-document mention is excluded
- industry-common mentioned target passes without linked document
- industry-common target connection through valid linked document passes
- industry-common wrong-company-only Evidence excluded
- Evidence with linked wrong-company document excluded
- Evidence source type differing from linked document excluded
- missing linked document ID excludes
- `ensure_evidence_matches_document()` security mismatch excludes without leaking raw exception

### 7.4 Evidence date precedence

- Evidence timestamp inside range passes even if linked document timestamp is outside
- Evidence timestamp outside range excludes even if linked document timestamp is inside
- missing Evidence timestamp falls back to linked document timestamp
- missing both timestamps excludes with date range
- naive Evidence timestamp falls back to aware linked timestamp
- naive Evidence timestamp with no usable linked timestamp excludes
- Asia/Seoul inclusive boundaries are used
- without date range, missing/naive timestamps do not exclude by themselves

### 7.5 Evidence document type

- `document_types=None` works without linked mapping
- requested document type with valid linked metadata passes
- requested document type without `documents_by_id` excludes
- requested type with missing linked metadata excludes
- requested type with non-string linked metadata excludes
- type is not inferred from Evidence title/snippet/locator/source type

### 7.6 Boundary and non-goals

- output list is fresh and preserves Evidence order and identity
- filtering does not mutate request, Evidence, or linked documents
- filtering does not create or score Evidence
- retrieval score is not used as a filter
- `top_k` is not applied by M2-02
- module does not import provider, ingest, API, UI, LLM, ranking, or search modules
- core model fields remain unchanged

---

## 8. Verification

After implementation, run in this order.

### 8.1 Targeted

```powershell
$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_retrieval_filters.py -q
```

### 8.2 M2 regression

```powershell
$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_query_planner.py tests/unit/test_retrieval_filters.py -q
```

### 8.3 Full unit regression

```powershell
$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit -q
```

### 8.4 Import smoke

```powershell
$env:PYTHONPATH = ".deps;."; python -c "from app.retrieval import HardFilterValidationError, filter_financial_documents, filter_evidence; print('ok')"
```

### 8.5 Secret scan

```powershell
python scripts/secret_scan.py
```

### 8.6 Compile

```powershell
python -m compileall app tests scripts -q
```

Record every command, execution context, exit code, pass count, and warning.

If an initial command fails, preserve the failure record and add the rerun result after correction.

---

## 9. Completion Criteria

- [x] baseline SHA confirmed; pre-implementation working tree differences were limited to approved Task Card docs
- [x] M2-01 preflight targeted test passes
- [x] preflight full unit regression passes
- [x] preflight import, secret scan, and compile pass
- [x] M2-01 Task Card synchronized to actual final SHA, push, review, and preflight state
- [x] M1-09 remains final independent review pending
- [x] public input boundary validation implemented
- [x] `filter_financial_documents()` implemented
- [x] `filter_evidence()` implemented
- [x] source hard filter passes
- [x] security hard filter passes
- [x] date hard filter passes with timezone-aware deterministic behavior
- [x] document-type proof rules pass
- [x] company-specific primary-subject attribution passes
- [x] multi-company primary-subject attribution passes
- [x] industry-common target connection passes
- [x] linked Evidence source/document integrity passes
- [x] Evidence-first date precedence passes
- [x] no ranking, scoring, provider, ingest, API, UI, LLM, or dependency work added
- [x] targeted tests pass
- [x] M2 regression passes
- [x] full unit regression passes
- [x] import smoke passes
- [x] secret scan passes
- [x] compile passes
- [x] actual commands, exit codes, warnings, and pass counts are recorded
- [x] supplement commit/push remains `NOT_RUN` pending separate user approval

---

## 10. Risk IDs and Taxonomy

Risk IDs:

- `R24` wrong intent routing spillover into source selection
- `R25` wrong-company or cross-company Evidence
- `R26` low relevance conflation with hard filter
- `R27` query rewrite changes intent
- `R28` retrieval complexity creep
- `R32` answer generated with insufficient Evidence
- linked-document source mismatch
- subject promotion from mentioned company
- naive-timezone nondeterminism
- unproven document-type routing

Related taxonomy:

- `entity_resolution`
- `source_selection`
- `wrong_company`
- `cross_company_attribution`
- `wrong_period`
- `citation_support`
- `evidence_sufficiency`
- `public_boundary_validation`

---

## 11. Stop Conditions

Stop and report if:

- any preflight gate command fails
- planning base SHA differs
- the working tree is unexpectedly dirty
- M2-01 Task Card synchronization cannot be completed safely
- implementation requires changing core model fields or status enums
- implementation requires provider, ingest, corpus loader, API, UI, LLM, or dependency changes
- hard filter needs scoring, ranking, chunking, lexical search, vector search, or top-k application
- Evidence generation or snippet construction becomes necessary
- source-specific freshness defaults become necessary
- M1-09 pending state would need to change
- the Evidence subject/document-primary contract cannot be represented with existing models
- linked-document and Evidence date precedence cannot be implemented deterministically
- unrelated regression fails

Do not proceed by silently reducing the contract.

---

## 12. Fallback and Failure State

- If Evidence filtering cannot be implemented safely, stop and report `M2-02 INCOMPLETE`.
- A document-only implementation does not satisfy this Task Card and does not authorize M2-03.
- Local partial work may be reported, but must not be marked `PASS`, committed, or pushed without a separately approved reduced-scope plan.
- If document-type metadata cannot be proven, exclude rather than infer.
- If date handling is ambiguous, treat the timestamp as unavailable; with a requested date range, exclude.
- Do not use reset, restore, checkout, clean, stash, force push, or destructive file operations.

---

## 13. Implementation Order After Approval

1. Confirm clean baseline at `5ffef6ca47c1ad8961bd717bb5623742bab8ddcb`.
2. Run every M2-01 preflight verification command.
3. Synchronize `docs/TASK_CARDS/M2-01-query-planner.md`.
4. Confirm M1-09 remains pending.
5. Add `app/retrieval/__init__.py`.
6. Implement public validation and shared structural helpers in `app/retrieval/filters.py`.
7. Implement document filtering.
8. Implement Evidence filtering with scope attribution, linked integrity, date precedence, and type proof.
9. Add exact targeted tests.
10. Run targeted tests.
11. Run M2 regression.
12. Run full unit regression.
13. Run import smoke, secret scan, and compile.
14. Record actual results in the M2-02 Task Card.
15. Run and report:

```powershell
git diff --name-status
git diff --stat
git status --short
git log -2 --oneline --decorate
```

16. Wait for separate commit/push approval.

---

## 14. Implementation Review Checklist

The independent implementation review must confirm:

- base SHA and changed files
- M2-01 preflight results and final Task Card synchronization
- M1-09 pending state preservation
- only approved files changed
- public input validation and sanitized errors
- no path/text/snippet/locator/metadata leakage
- exact source/security/document-type filters
- aware Asia/Seoul date handling and naive timestamp behavior
- Evidence-first date precedence without linked-document double filtering
- company-specific subject requires linked document primary target
- multi-company subjects require linked document primary identities
- industry-common connection rules
- Evidence/document source-type equality
- requested document types cannot pass without linked-document proof
- fresh outer lists, stable order, no input mutation
- no top-k, score, ranking, provider, ingest, API, UI, or LLM work
- targeted, M2 regression, full regression, smoke, secret scan, and compile results
- Task Card, commit, push, CI, and independent rerun statuses match reality

---

## 15. Result Log

- Implementation status: `PASS in local implementation environment - user review pending`
- Preflight baseline SHA: `5ffef6ca47c1ad8961bd717bb5623742bab8ddcb`
- Preflight baseline commit: `m2-01 conditional pass2 updates`
- Preflight working tree note: `approved Task Card docs were present before implementation; no code files were dirty`
- M2-01 Task Card synchronization: `PASS`
- M1-09 state: `mandatory supplement implemented - final independent review pending`
- Implementation SHA: `NOT_CREATED`
- Commit/push/PR/merge/deploy: `NOT_RUN`
- GitHub CI: `NOT_RUN`
- Independent pytest rerun: `NOT_RUN`

### 15.1 Preflight Verification Results

- Baseline command: `git rev-parse HEAD`
  - exit code: `0`
  - output: `5ffef6ca47c1ad8961bd717bb5623742bab8ddcb`
- Baseline command: `git log -3 --oneline --decorate`
  - exit code: `0`
  - latest commit: `5ffef6c (HEAD -> main, origin/main, origin/HEAD) m2-01 conditional pass2 updates`
- Preflight M2-01 targeted command: `$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_query_planner.py -q`
  - execution: approved elevated run
  - exit code: `0`
  - passed count: `76 passed`
- Preflight full unit regression command: `$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit -q`
  - execution: approved elevated run
  - exit code: `0`
  - passed count: `837 passed`
  - warning: FastAPI TestClient emitted Starlette deprecation warning for `httpx`.
- Preflight import smoke command: `$env:PYTHONPATH = ".deps;."; python -c "from app.planning.query_planner import QueryPlanner; print('ok')"`
  - execution: approved elevated run
  - exit code: `0`
  - output: `ok`
- Preflight secret scan command: `python scripts/secret_scan.py`
  - exit code: `0`
  - output: `[]`
- Preflight compile command: `python -m compileall app tests scripts -q`
  - exit code: `0`

### 15.2 Implemented Scope

- Added `app.retrieval` exports for `HardFilterValidationError`, `filter_financial_documents`, and `filter_evidence`.
- Added public-boundary validation for request, sequence inputs, mapping inputs, and item types with sanitized `HardFilterValidationError`.
- Added document structural hard filter for source, target security, and document-type proof.
- Added document date filtering using timezone-aware Asia/Seoul local dates.
- Added Evidence filtering with linked-document source/integrity checks, scope attribution rules, document-type proof, and Evidence-first date precedence.
- Preserved input order and model identity while returning fresh outer lists.
- Did not add provider, ingest, core model, planning, API/UI, LLM, ranking, top-k, dependency, or retrieval scoring work.

### 15.3 Implementation Verification Results

- Targeted command: `$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_retrieval_filters.py -q`
  - execution: approved elevated run
  - exit code: `0`
  - passed count: `53 passed`
- M2 regression command: `$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_query_planner.py tests/unit/test_retrieval_filters.py -q`
  - execution: approved elevated run
  - exit code: `0`
  - passed count: `129 passed`
- Full unit regression command: `$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit -q`
  - execution: approved elevated run
  - exit code: `0`
  - passed count: `890 passed`
  - warning: FastAPI TestClient emitted Starlette deprecation warning for `httpx`.
- Import smoke command: `$env:PYTHONPATH = ".deps;."; python -c "from app.retrieval import HardFilterValidationError, filter_financial_documents, filter_evidence; print('ok')"`
  - execution: approved elevated run
  - exit code: `0`
  - output: `ok`
- Secret scan command: `python scripts/secret_scan.py`
  - exit code: `0`
  - output: `[]`
- Compile command: `python -m compileall app tests scripts -q`
  - exit code: `0`

### 15.4 Modified Files

- `app/retrieval/__init__.py`
- `app/retrieval/filters.py`
- `tests/unit/test_retrieval_filters.py`
- `docs/TASK_CARDS/M2-01-query-planner.md`
- `docs/TASK_CARDS/M2-02-hard-filter.md`

### 15.5 Final Local State

```text
M2-02 implementation local PASS
commit/push NOT_RUN
GitHub CI NOT_RUN
independent pytest rerun NOT_RUN
M2-03 NOT_STARTED
```
