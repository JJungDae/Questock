# TASK CARD - M2-04 Evidence Normalization

## 1. Status and Approval

- Task bundle: `B5: M2-04~08`
- Step: `M2-04 Evidence Normalization`
- Planning date: `2026-07-23`
- Planning base branch: `main`
- Planning base commit: `008fd4ad27ffab638a6eb95b205f2ed6436b305d`
- Planning base commit message: `Implement m2-03`
- M2-03 code closure review: `PASS WITH REQUIRED FOLLOW-UP`
- M2-03 implementation SHA: `008fd4ad27ffab638a6eb95b205f2ed6436b305d`
- M2-03 implementation main push: `complete`
- M2-03 Task Card final synchronization: `PASS - stale independent implementation-review entry synchronized in preflight`
- M1-09 recorded status: `mandatory supplement implemented - final independent review pending`
- M1-09 provider completion: `pending final PASS`
- M2-04 plan review: `PASS WITH REQUIRED FOLLOW-UP - required clarifications incorporated`
- M2-04 planning entry: `ALLOWED`
- M2-04 implementation entry: `ALLOWED only after this final plan is approved and preflight passes`
- Current status: `IMPLEMENTATION COMPLETE - USER REVIEW PENDING`
- Implementation approval: `APPROVED by user instruction using this final Task Card`
- Commit/push/PR/merge/deploy: `NOT_APPROVED`
- Live API/provider/API/UI/LLM work: `OUT_OF_SCOPE`
- M2-05 freshness, M2-06 EvidencePolicy, M2-07 citation validation, M2-08 dedupe/context budget: `NOT_STARTED`

This Task Card authorizes only:

- deterministic `FinancialDocument` → `Evidence` normalization
- unit and integration tests
- verification of the local M2-03 Task Card state, with a minimal update only when it is still stale
- M2-04 Task Card result recording

It does not authorize commit, push, PR, merge, deploy, provider calls, live APIs, producer changes, core-model changes, retrieval changes, freshness, EvidencePolicy, citation validation, dedupe, API/UI, or LLM work.

---

## 2. Source Basis

The implementation agent must read the current `main` versions of the following before implementation.

| Source | Required Section | Contract used by M2-04 |
|---|---|---|
| `docs/agent_handoff/README_AGENT_RULES.md` | §§1.1~3.5 | minimum change, validation evidence, non-destructive Git, separate Git approval |
| `docs/agent_handoff/PROJECT_PLAN_FINAL_PASS.md` | M2-04, M2 Gate, §8.2, §8.5 Traceability, B5 registry | Evidence fields, locator, local-path safety, next-step boundary |
| `docs/TASK_CARDS/M2-03-retrieval-baseline.md` | status/result log, Evidence input scaffold | previous public consumer and actual Git/test state |
| `docs/TASK_CARDS/M2-02-hard-filter.md` | Evidence scope/date/document linkage | downstream filter compatibility |
| `docs/agent_handoff/FINANCIAL_CAPABILITY_BASELINE.md` | C04, C05 | normalized document fields, locator, snippet, retrieval result contract |
| `docs/agent_handoff/EXTENSION_COMPATIBILITY.md` | checkpoint 1, P0 scope | news/disclosure/report Evidence flow |
| `docs/agent_handoff/RISK_RESPONSE_MATRIX.md` | R25, R29, R32, R45 | attribution, snippet/locator, sufficiency separation, source location |
| `docs/agent_handoff/EVALUATION_TAXONOMY_DRAFT.md` | entity resolution, numeric accuracy, citation support, evidence sufficiency | failure fixtures |
| `docs/agent_handoff/STOCK_SCOPE_CHANGE_NOTICE.md` | company-attribution contract | primary/mentioned → subject/mentioned/scope |
| `docs/agent_handoff/AGENT_WORKFLOW.md` | task lifecycle and review | formal Evidence task workflow |
| `app/core/models.py` | `FinancialDocument`, `Evidence`, `ensure_evidence_matches_document()` | existing model and validation contract |
| `app/retrieval/filters.py` | `filter_evidence()` | linked-document and scope compatibility |
| `app/retrieval/retriever.py` | `retrieve_evidence()` | score initialization and downstream retrieval compatibility |
| `app/providers/news.py` | `FinancialDocument` construction | current news locator shape |
| `app/providers/disclosure.py` | `_build_document()` | current DART locator shape |
| `app/ingest/reports.py` | `_build_financial_document()` | current report locator and permission metadata |

No live provider, actual external source, GitHub CI, external LLM, or independent review environment is used as M2-04 completion evidence.

---

## 3. Review Amendments and Provenance

| Amendment | Classification | Evidence file / Section | Required effect |
|---|---|---|---|
| Verify local M2-03 Task Card state and update only if stale | `PROCESS-INTEGRITY` preflight note | README §§2.6·3; M2-03 result log | Do not rewrite an already synchronized local card |
| Define empty batch and observable atomic failure | `PLAN-GAP` / required follow-up | AGENT_WORKFLOW Ready criteria; public boundary | Empty input returns a fresh empty list; invalid input returns no partial list |
| Clarify canonical revalidation and expected exception conversion | existing contract clarification | original M2-04 plan; Pydantic boundary | Do not mandate one internal revalidation implementation |
| Audit locator mapping keys and nested tuple-like values | `PLAN-GAP` / required follow-up | PROJECT critical local-path rule; CORE06 locator | Preserve the current core local-path safety rule without route-specific exceptions |
| Preserve producer-shaped locators by exact round-trip tests | existing integration clarification | Baseline C04/C05; actual producer code; R45 | Do not duplicate producer-specific runtime schemas in M2-04 |
| Keep permission/provenance outside Evidence normalization | existing contract clarification | PROJECT §5.3; report ingest permission gate | Preserve the `document_id` join to the original document |
| Preserve source type exactly | existing contract reaffirmation | original field-mapping contract | No alias, fallback, or allowlist conversion |
| Preserve one-to-one baseline without claim extraction | existing Step boundary | PROJECT M2-04; M2-07 owns citation validation | No claim-level citation validation in M2-04 |

---

## 4. Required Preflight Gate

Run from repository root on `main` before editing M2-04 implementation files.

### 4.1 Git baseline

```powershell
git status --short
git rev-parse HEAD
git log -1 --oneline
```

Expected:

```text
HEAD = 008fd4ad27ffab638a6eb95b205f2ed6436b305d
latest commit = Implement m2-03
```

Rules:

- a clean working tree may continue
- approved M2-03 closure synchronization and M2-04 planning files may already be dirty; record that deviation
- unexpected code, fixture, dependency, data, unrelated Task Card, or user files require a stop report
- do not use reset, restore, checkout, clean, stash, force push, history rewrite, or destructive file operations

### 4.2 Baseline regression and hygiene

```powershell
$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_retrieval_filters.py tests/unit/test_retrieval_baseline.py -q
$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_query_planner.py tests/unit/test_retrieval_filters.py tests/unit/test_retrieval_baseline.py -q
$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit -q
$env:PYTHONPATH = ".deps;."; python -c "from app.core.models import FinancialDocument, Evidence; from app.retrieval import retrieve_evidence; print('ok')"
python scripts/secret_scan.py
python -m compileall app tests scripts -q
```

Every command must exit `0`. Record actual pass counts, warnings, execution context, and any initial failed attempt followed by a rerun.

### 4.3 Verify the local M2-03 Task Card state

After baseline commands pass and before M2-04 code edits, inspect:

```text
docs/TASK_CARDS/M2-03-retrieval-baseline.md
```

Expected synchronized content includes:

```text
Current status: PASS / complete
Implementation SHA: 008fd4ad27ffab638a6eb95b205f2ed6436b305d
Implementation commit: Implement m2-03
Implementation main push: complete
Independent implementation review: PASS WITH REQUIRED FOLLOW-UP
Final code closure: PASS
Targeted pytest: 28 passed
M2 regression: 159 passed
Full unit regression: 920 passed
GitHub CI: NOT_RUN
Independent pytest rerun: NOT_RUN
M2-04 planning entry: ALLOWED
M2-04 implementation entry: ALLOWED after approved plan and preflight PASS
Further commit/push/PR/merge/deploy: NOT_APPROVED
```

Rules:

- if the local Task Card already contains the accurate synchronized state, do not rewrite it
- record it as an approved pre-existing document change in `git status`
- if it is still stale, apply only the minimum synchronization above
- keep M1-09 pending
- verification or synchronization does not authorize commit or push

---

## 5. Goal and Step Boundary

### 5.1 Goal

Add a deterministic, in-memory boundary that maps each validated `FinancialDocument` to exactly one existing `Evidence` object.

The boundary bridges current M1 document producers to the existing M2-02 filter and M2-03 lexical retriever.

### 5.2 Required

- one validated document maps to one Evidence
- deterministic Evidence ID derived from `document_id`
- deterministic non-empty snippet
- exact preservation of document ID, source type, title, source URL, published timestamp, and source locator
- structural company-attribution mapping
- `retrieval_score=None`
- deep-copy mutable output values
- no input mutation
- sanitized typed errors for malformed public input
- order and duplicates preserved
- no file, registry, manifest, corpus, provider, or network I/O

### 5.3 Out of scope

- provider result unwrapping or provider status mapping
- provider calls, retry, cache, credential, fixture loading, or live API work
- changing M1 producers
- core model/status/schema changes
- QueryPlanner or session handling
- M2-02 filtering logic
- M2-03 BM25/ranking logic
- text entity extraction, aliases, resolver lookup, LLM inference, claim extraction, source summarization, chunking, OCR, or query rewriting
- freshness/staleness decisions
- EvidencePolicy
- citation-support validation
- correction-chain decisions
- numeric validation
- duplicate removal/context budget
- API/UI/LLM work
- dependency or data additions

### 5.4 M2-04 / M2-05~07 join contract

`Evidence` does not contain document metadata such as:

- document type
- correction status
- report usage permission
- publication precision
- source-specific freshness metadata

Therefore:

- M2-04 preserves `document_id` as the join key
- callers must retain the original `FinancialDocument` objects and construct `documents_by_id` outside the normalizer
- M2-05~07 may use that linked document map for metadata-dependent policy
- M2-04 does not create a global document registry, repository, cache, or mapping service
- the normalizer returns only Evidence or a list of Evidence

### 5.5 Provider and provenance boundary

The public normalizer accepts only `FinancialDocument` inputs.

It does not accept or unwrap:

- `ProviderResult`
- raw news responses
- raw DART responses
- report manifests
- report JSON documents
- provider error objects

Provider failures, no-data, recorded/actual/live distinctions, and permission-to-ingest decisions remain upstream.

---

## 6. Existing Model Contract

### 6.1 FinancialDocument input

Use existing fields only:

```text
document_id
source_type
provider
primary_security_ids
mentioned_security_ids
title
published_at
source_url
text
locator
metadata
ingestion_version
```

The normalizer must not access a registry, resolver, manifest file, provider, or corpus to reinterpret them.

### 6.2 Evidence output

Use the existing model unchanged:

```text
evidence_id
document_id
source_type
title
source_url
published_at
subject_security_ids
mentioned_security_ids
scope
snippet
locator
retrieval_score
```

Do not add:

- metadata
- permission fields
- status
- confidence
- claim ID
- chunk offsets
- freshness
- correction state
- diagnostics

### 6.3 Source type

`source_type` is preserved exactly after validation as a non-blank string.

M2-04 does not:

- introduce a new source
- map aliases
- convert `report` to `research_report`
- maintain a source allowlist
- silently replace unsupported values

Source eligibility remains owned by M2-02 and the caller's `RetrievalRequest`.

---

## 7. Public API

Create:

```python
# app/evidence/normalizer.py

class EvidenceNormalizationError(ValueError):
    """Raised for malformed or unsafe public normalization inputs."""
    ...

def normalize_financial_document(
    document: FinancialDocument,
) -> Evidence:
    ...

def normalize_financial_documents(
    documents: Sequence[FinancialDocument],
) -> list[Evidence]:
    ...
```

Export only these names from `app/evidence/__init__.py`.

Do not change `app.core` or `app.retrieval` exports.

---

## 8. Exact Processing Order

### 8.1 Single document

Apply this order exactly:

```text
top-level type validation
→ canonical revalidation of FinancialDocument
→ scalar and structural field validation
→ locator copy and safety validation
→ structural attribution mapping
→ snippet whitespace normalization
→ snippet non-empty check
→ 500-character truncation
→ emitted title/snippet/ID/URL/locator safety audit
→ Evidence construction
→ final serialized-output safety audit
→ return Evidence
```

Rules:

- no early Evidence object is returned before every validation passes
- no field is silently repaired except snippet whitespace collapse
- no first-match or fallback attribution
- no provider or retrieval call

### 8.2 Canonical revalidation

An existing model instance is not sufficient evidence of current validity because assignment and `model_construct()` can bypass normal validation.

The implementation must perform canonical public-boundary revalidation using Pydantic validation of the complete current field values. The plan does not mandate one specific dump/validate expression.

Contract:

- expected Pydantic `ValidationError` is converted to a fixed sanitized `EvidenceNormalizationError`
- raw Pydantic error text is not included
- field values are not silently repaired except for the approved snippet whitespace normalization
- unexpected internal errors are not converted to input-validation errors

### 8.3 Batch behavior

`normalize_financial_documents()`:

- accepts a non-string `Sequence[FinancialDocument]`
- rejects `str`, `bytes`, `bytearray`, mappings, generators, and scalars
- returns a new empty list for an empty sequence
- if any item is invalid, raises `EvidenceNormalizationError` and returns no partial list to the caller
- preserves input order
- preserves duplicate inputs
- returns distinct Evidence objects for repeated inputs
- does not mutate input objects
- performs no I/O

The observable atomicity contract does not require a two-pass implementation. Internal objects may be constructed in any safe deterministic order because the function has no file, database, network, or global-state side effects.

---

## 9. Exact Field Mapping

| Evidence field | Rule |
|---|---|
| `evidence_id` | `f"evidence:{validated_document.document_id}"` |
| `document_id` | exact validated `document_id` |
| `source_type` | exact validated `source_type` |
| `title` | exact validated title; no rewriting or stripping in output |
| `source_url` | exact validated URL; `None` stays `None` |
| `published_at` | exact value; no timezone conversion or freshness logic |
| `subject_security_ids` | section 10 mapping, fresh list |
| `mentioned_security_ids` | fresh copy of document mentions |
| `scope` | section 10 mapping |
| `snippet` | section 11 |
| `locator` | deep copy of validated locator |
| `retrieval_score` | always `None` |

The following are intentionally dropped because Evidence has no matching field:

```text
provider
metadata
ingestion_version
```

Their information remains available through the original linked document.

---

## 10. Structural Attribution

Map only existing structural fields.

| Document structure | Evidence scope | Subjects | Mentions |
|---|---|---|---|
| one primary | `company_specific` | the one primary ID | exact document mentions |
| two or more primaries | `multi_company` | all primaries, original order | exact document mentions |
| no primary, one or more mentions | `industry_common` | `[]` | exact document mentions |

Rules:

- title, text, metadata, aliases, provider name, and resolver data are not used
- mentioned IDs are never promoted to subjects
- primary IDs are never demoted to mentions
- order is preserved
- fresh lists are returned
- the resulting Evidence must satisfy `ensure_evidence_matches_document()`

Research report metadata:

```text
subject_scope="company_centered_with_mentions"
```

does not create a new Evidence scope. The already-normalized core fields determine:

```text
one primary + mentions
→ company_specific
```

Do not read `metadata["subject_scope"]` for attribution.

---

## 11. Snippet Contract

Normalize only `document.text`.

Exact behavior:

```text
re.sub(r"\s+", " ", text).strip()
→ reject if empty
→ first 500 Python characters
→ no suffix
```

Do not:

- NFKC-normalize source content
- summarize
- translate
- extract claims
- add an ellipsis
- prepend the title
- repair numeric text
- alter units
- infer a company
- select a query-dependent span

One-to-one first-500-character Evidence is the M2-04 baseline. Claim-aware or query-aware extraction requires a separately approved plan.

---

## 12. Locator Contract

### 12.1 Runtime common contract

- locator must be a non-empty mapping
- locator is deep copied
- locator must be JSON-serializable using standard JSON-compatible output
- no locator key or nested string value may expose a local absolute path
- nested mapping keys, lists, and tuples from bypass-created input are included in the safety audit
- no key or value is fabricated, deleted, renamed, or transformed
- no locator is derived from title text
- no missing locator is replaced with a URL

M2-04 owns structural safety and exact preservation, not source-specific citation semantics.

### 12.2 Producer-shaped exact round-trip coverage

Use representative current producer-shaped documents in integration tests:

- news locator from `app/providers/news.py`
- disclosure locator from `app/providers/disclosure.py`
- research-report locator from `app/ingest/reports.py`

For each valid case:

```text
Evidence.locator == FinancialDocument.locator
```

and the two mappings must not be the same mutable object.

The M2-04 runtime must not introduce its own source-specific required-key allowlist or repeat provider/ingest validation for:

- news `raw_index`
- DART receipt format
- report page basis
- source asset or access-note policy

A non-empty, JSON-serializable, local-path-safe locator is handled by the common normalizer contract. Claim-level and source-specific citation validity remains M2-07.

---

## 13. Safety and Error Contract

### 13.1 Sanitized error messages

Use a small fixed message set. Messages must not contain:

- document ID
- title
- text or snippet
- URL
- locator key/value
- metadata
- provider message
- secret
- local path
- raw Pydantic error
- raw exception text
- serialized model

Recommended fixed messages:

```text
document must be a FinancialDocument
documents must be a sequence
documents items are invalid
financial document is invalid
document text must not be blank
document locator is invalid
document output is unsafe
evidence construction failed
```

### 13.2 Exception conversion

Convert only expected public-input failures:

- explicit boundary validation failures
- Pydantic `ValidationError` from document revalidation
- Pydantic `ValidationError` from Evidence construction
- JSON-serialization failure caused by locator input
- private safety-guard failures

Do not broadly catch unrelated internal exceptions.

Unexpected internal failures such as a deliberate `RuntimeError`, `MemoryError`, or programmer error must propagate and must not return Evidence.

### 13.3 Local-path and URL audit

Audit:

- input `document_id`
- generated Evidence ID
- title
- emitted snippet
- source URL
- locator mapping keys and nested string values
- final serialized Evidence output

Recognize at least:

- Windows drive paths
- UNC paths
- `file://`
- POSIX absolute paths

Normal HTTP(S) URLs remain allowed.

Validate nested:

- mappings
- list
- tuple
- mapping keys as well as values

For `source_url`, also reject embedded user information or credential-bearing query parameters. Do not inspect ordinary financial source text for credential-related vocabulary.

### 13.4 Secret and raw internal data

M2-04 does not copy:

- provider errors
- metadata
- credentials
- manifest permission notes
- raw API objects

Do not implement a redaction pipeline or reject financial text merely because it discusses an API key, authorization event, bearer token, or client secret.

Safety validation is limited to:

- actual local-path exposure
- unsafe `source_url` user information or credential query parameters
- raw internal objects or errors being copied into Evidence

Expected input failures use sanitized messages; ordinary source-content vocabulary is preserved.

---

## 14. Permission and Provenance Boundary

M2-04 does not decide:

- corpus ingest permission
- external LLM processing permission
- usage review approval
- recorded vs actual provider success
- live coverage
- answer eligibility

For an already-produced valid `FinancialDocument`:

- permission metadata does not change field mapping
- metadata is not copied into Evidence
- external LLM permission must later be checked through the linked document/manifest using `document_id`
- M2-04 performs no external transmission

Tests may use:

- synthetic unit documents
- producer-shaped synthetic documents
- recorded provider-shaped documents

Result reports must not describe those as:

- actual source coverage
- live provider success
- production citation validation
- external LLM eligibility

---

## 15. Copy, Mutation, Determinism, and I/O

- every Evidence is a fresh object
- subject/mentioned lists are fresh
- locator is deep copied
- batch outer list is fresh
- input documents and nested values are never mutated
- mutating returned Evidence or locator does not change input or a later normalization result
- same valid input produces the same serialized Evidence
- repeated documents produce repeated Evidence with the same deterministic ID
- no dedupe occurs before M2-08
- no file, registry, manifest, corpus, provider, cache, or network I/O
- no global mutable cache or singleton state

---

## 16. Planned Files

### New

- `app/evidence/__init__.py`
- `app/evidence/normalizer.py`
- `tests/unit/test_evidence_normalization.py`
- `docs/TASK_CARDS/M2-04-evidence-normalization.md`

### Modified when necessary

- `docs/TASK_CARDS/M2-03-retrieval-baseline.md`
  - verify the existing local synchronization first
  - modify only if it is still stale
- `docs/TASK_CARDS/M2-04-evidence-normalization.md`
  - implementation result recording after it is created

### Do not modify

- `app/core/**`
- `app/retrieval/**`
- `app/providers/**`
- `app/ingest/**`
- `app/planning/**`
- `app/api/**`
- `app/llm/**`
- `data/**`
- existing source fixtures
- existing source/provider/retrieval tests
- `docs/TASK_CARDS/M1-09-market-snapshot-gate.md`
- M2-05 and later Task Cards
- dependency and lock files
- scripts

If another file is needed, stop and report before changing scope.

---

## 17. Required Tests

Create exact tests in:

```text
tests/unit/test_evidence_normalization.py
```

### 17.1 Public API and validation boundary

- package exports exactly the planned three names
- wrong single input raises `EvidenceNormalizationError`
- invalid batch categories are rejected
- invalid batch items raise `EvidenceNormalizationError`
- empty batch returns a fresh empty list
- valid + invalid + valid batch returns no partial list
- bypass-created malformed FinancialDocument is canonically revalidated
- expected Pydantic failures become sanitized typed errors
- injected internal RuntimeError propagates

### 17.2 Exact field mapping

- deterministic ID
- document ID exact
- source type exact, no alias conversion
- title exact, including preserved ordinary surrounding content
- URL exact and nullable
- published timestamp exact
- score always `None`
- provider, metadata, and ingestion version are not added to Evidence

### 17.3 Snippet

- whitespace collapse exact
- empty/whitespace-only text rejected
- exactly 500 characters
- no suffix
- no title prepend
- numeric/unit text preserved
- repeated runs identical

### 17.4 Attribution

- one primary, no mention
- one primary with mention
- multiple primary
- mention-only industry common
- no primary/mention invalid through revalidation
- duplicate or overlapping security IDs invalid through revalidation
- mentioned company never promoted
- report company-centered-with-mentions uses core fields only
- `ensure_evidence_matches_document()` passes

### 17.5 Locator and output safety

- current producer-shaped news locator is preserved exactly
- current producer-shaped disclosure locator is preserved exactly
- current report page locator is preserved exactly
- current report source-section-only locator is preserved exactly
- valid generic non-empty locator is not rejected merely for lacking producer-specific keys
- missing/empty locator rejected
- locator is deep copied
- nested local path in locator value rejected
- local path in locator key rejected
- tuple-contained local path rejected
- Windows/UNC/file/POSIX path rejected
- HTTP(S) URL allowed
- source URL user information and credential query parameters rejected
- ordinary title/snippet text discussing credential-related topics is preserved
- no raw value appears in exception message or formatted exception
- locator output is JSON-serializable

### 17.6 Copy, duplicate, permission, provenance

- output nested mutation does not affect input
- later call is unaffected by previous output mutation
- duplicate inputs remain duplicate outputs in order
- permission metadata changes do not change normalization mapping
- synthetic/recorded labels are not added to Evidence
- normalizer performs no I/O

### 17.7 M2 integration

- normalized Evidence passes M2-02 with linked document map
- company-specific, multi-company, and industry-common behavior remains correct
- requested document type remains provable only through linked document metadata
- M2-03 ranks normalized Evidence and score-stamps a copy
- original normalized Evidence score remains `None`
- normalized document timestamp remains available for M2-05
- source code does not import provider, ingest, retrieval, planning, API, LLM, embedding, vector, reranker, dedupe, or source-specific parser modules

---

## 18. Verification After Implementation

Run in order.

### 18.1 Targeted

```powershell
$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_evidence_normalization.py -q
```

### 18.2 M2 integration regression

```powershell
$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_query_planner.py tests/unit/test_retrieval_filters.py tests/unit/test_retrieval_baseline.py tests/unit/test_evidence_normalization.py -q
```

### 18.3 Full unit

```powershell
$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit -q
```

### 18.4 Import smoke

```powershell
$env:PYTHONPATH = ".deps;."; python -c "from app.evidence import EvidenceNormalizationError, normalize_financial_document, normalize_financial_documents; print('ok')"
```

### 18.5 Hygiene and diff

```powershell
python scripts/secret_scan.py
python -m compileall app tests scripts -q
git diff --check
git diff --name-status
git diff --stat
git status --short
git log -2 --oneline --decorate
```

Record:

- every command
- execution context
- exit code
- pass count
- warning
- initial failure and corrected rerun
- skipped/not-run items
- GitHub CI state
- independent rerun state

Do not claim live or actual source coverage.

---

## 19. Completion Criteria

- [x] base SHA confirmed
- [x] preflight passes
- [x] M2-03 Task Card verified; updated only if stale
- [x] M1-09 remains pending
- [x] only approved files changed
- [x] no core/retrieval/producer changes
- [x] public package and three names created
- [x] single and batch public boundaries exact
- [x] empty batch and atomic failure exact
- [x] canonical document revalidation implemented
- [x] expected validation failures sanitized
- [x] unexpected internal failures propagate
- [x] one document maps to one Evidence
- [x] field mapping exact
- [x] source type pass-through exact
- [x] attribution mapping exact
- [x] snippet exact
- [x] producer-shaped locator exact round-trip passes without runtime schema duplication
- [x] nested output/path safety exact
- [x] source URL userinfo/credential query safety passes without scanning ordinary source text
- [x] locator serialized safely
- [x] score initialized to None
- [x] deep-copy and mutation isolation pass
- [x] duplicates preserved
- [x] no I/O
- [x] permission/provenance not reinterpreted
- [x] original document join retained for later steps
- [x] M2-02 integration passes
- [x] M2-03 integration passes
- [x] targeted tests pass
- [x] M2 regression passes
- [x] full unit regression passes
- [x] import smoke passes
- [x] secret scan passes
- [x] compile passes
- [x] diff review passes
- [x] results recorded truthfully
- [x] commit/push/PR/merge/deploy remain `NOT_RUN`

---

## 20. Stop Conditions

Stop and report if:

- planning base SHA differs
- M2-03 Task Card cannot be synchronized safely
- preflight fails
- unexpected dirty files exist
- core models/status must change
- retrieval/filter/ranker must change
- producer or ingest code must change
- provider result unwrapping becomes necessary
- text attribution, claim extraction, chunking, freshness, EvidencePolicy, citation validation, numeric validation, dedupe, API/UI/LLM, dependency, or live call becomes necessary
- a new Evidence field or status is needed
- output safety requires weakening existing project safety
- linked document join cannot preserve metadata needed by later steps
- M1-09 pending state must change
- unrelated regression fails

Do not silently skip an invalid document, reduce tests, loosen attribution, invent a locator, or return partial batch output.

---

## 21. Fallback and Rollback

- invalid or insufficient document → sanitized `EvidenceNormalizationError`
- no locator → reject, do not invent
- blank text → reject, do not substitute title
- source-specific runtime locator schema or parser requirement → stop, do not implement
- claim-aware extraction requirement → separate plan
- model/schema change requirement → separate approval
- rollback after a future approved implementation:
  - revert only M2-04 files and M2-03 synchronization diff
  - only after explicit user approval
  - no reset, clean, force push, or history rewrite

---

## 22. Implementation Order After Approval

1. Confirm `main` at `008fd4ad27ffab638a6eb95b205f2ed6436b305d`.
2. Record initial Git status.
3. Run all preflight tests and hygiene commands.
4. Verify `docs/TASK_CARDS/M2-03-retrieval-baseline.md`; update it only if the local card is still stale.
5. Confirm M1-09 remains pending.
6. Create `docs/TASK_CARDS/M2-04-evidence-normalization.md` from this approved plan.
7. Create `app/evidence/__init__.py`.
8. Implement public validation and safety helpers in `app/evidence/normalizer.py`.
9. Implement document canonical revalidation.
10. Implement attribution mapping.
11. Implement snippet and locator mapping.
12. Implement single and batch APIs with no partial result returned on failure.
13. Add exact unit and integration tests.
14. Run targeted tests.
15. Run M2 integration regression.
16. Run full unit regression.
17. Run import smoke, secret scan, compile, and diff review.
18. Record actual results in the M2-04 Task Card.
19. Report changed files, commands, results, limitations, rollback, and next-step permission.
20. Wait for separate commit/push approval.

---

## 23. Implementation Review Checklist

### Source and Git

- [x] base SHA and latest commit
- [x] full changed-file list
- [x] M2-03 Task Card verified and updated only if stale
- [x] M1-09 pending preserved
- [x] only allowed files changed
- [x] GitHub CI and independent rerun status accurate
- [x] commit/push state accurate

### Public boundary

- [x] single type validation
- [x] batch Sequence validation
- [x] empty batch
- [x] atomic batch failure
- [x] canonical model revalidation
- [x] sanitized expected errors
- [x] unexpected errors propagate

### Mapping

- [x] deterministic ID
- [x] exact field preservation
- [x] source type pass-through
- [x] one/multi/industry attribution
- [x] report metadata not used for attribution
- [x] snippet 500-character contract
- [x] score None

### Locator and safety

- [x] news/disclosure/report producer-shaped locators round-trip exactly
- [x] no producer-specific runtime key allowlist was introduced
- [x] valid generic locator remains supported
- [x] no invented locator
- [x] deep copy
- [x] nested key/value and tuple path scan
- [x] serialized-output scan
- [x] HTTP(S) URL handling remains valid
- [x] source URL userinfo/credential query safety
- [x] ordinary source text is not filtered by credential vocabulary
- [x] no raw values in errors

### Step boundaries

- [x] no ProviderResult handling
- [x] no file/registry/manifest/corpus I/O
- [x] no filter/ranking implementation
- [x] no freshness/EvidencePolicy/citation/dedupe
- [x] permission metadata not copied or reinterpreted
- [x] linked document join retained
- [x] synthetic/recorded/live states not conflated

### Verification

- [x] targeted result
- [x] M2 integration result
- [x] full unit result
- [x] import smoke
- [x] secret scan
- [x] compile
- [x] diff check
- [x] no regression of wrong-company or locator safety

Closure review after remediation is limited to:

- original BLOCKER closure
- exact targeted/integration/regression tests
- allowed files
- Task Card/Git/CI status
- new regression, security, permission, data-loss, or wrong-attribution defects only

---

## 24. Result Log

- Planning base SHA: `008fd4ad27ffab638a6eb95b205f2ed6436b305d`
- Planning base commit: `Implement m2-03`
- Preflight Git baseline: `PASS - main at 008fd4ad27ffab638a6eb95b205f2ed6436b305d; latest commit Implement m2-03`
- Preflight working-tree deviation: `approved M2-03 closure synchronization and M2-04 Task Card plan were already dirty; no unexpected code, fixture, dependency, data, unrelated Task Card, or user files were present; no destructive Git operation was used`
- M2-03 Task Card verification / conditional synchronization: `PASS - implementation SHA, commit, main push, final closure, test results, and M2-04 entries were already present; added the stale independent implementation-review record only`
- M1-09 state: `mandatory supplement implemented - final independent review pending`
- Preflight targeted retrieval: `PASS - exit 0 - 83 passed`
- Preflight M2 regression: `PASS - exit 0 - 159 passed`
- Preflight full unit: `PASS - exit 0 - 920 passed, 1 existing FastAPI/Starlette deprecation warning`
- Preflight smoke: `PASS - exit 0 - ok`
- Preflight secret scan: `PASS - exit 0 - []`
- Preflight compile: `PASS - exit 0 - no output`
- Preflight execution context: `initial PYTHONPATH=.deps;. command exited 1 because pytest.__main__ was unavailable; corrected PYTHONPATH=.test_deps;.deps;. sandbox command exited 1 on dependency-file access; approved local dependency access reruns used the corrected PYTHONPATH and passed`
- Implementation status: `IMPLEMENTATION COMPLETE - USER REVIEW PENDING`
- Implementation SHA: `NOT_CREATED - commit is not approved`
- Allowed implementation files: `app/evidence/__init__.py, app/evidence/normalizer.py, tests/unit/test_evidence_normalization.py, docs/TASK_CARDS/M2-04-evidence-normalization.md, and the allowed stale M2-03 Task Card synchronization`
- Targeted pytest: `PASS - exit 0 - 55 passed`
- M2 integration regression: `PASS - exit 0 - 214 passed`
- Full unit regression: `PASS - exit 0 - 975 passed, 1 existing FastAPI/Starlette deprecation warning`
- Import smoke: `PASS - exit 0 - ok`
- Secret scan: `PASS - exit 0 - []`
- Compile: `PASS - exit 0 - no output`
- Diff check: `PASS - exit 0 - no whitespace errors; Git reported only the existing M2-03 LF-to-CRLF working-copy warning`
- Final Git working tree: `M docs/TASK_CARDS/M2-03-retrieval-baseline.md; ?? app/evidence/; ?? docs/TASK_CARDS/M2-04-evidence-normalization.md; ?? tests/unit/test_evidence_normalization.py`
- GitHub CI: `NOT_RUN`
- Independent pytest rerun: `NOT_RUN`
- Live provider/actual source/API/UI/LLM: `NOT_RUN - out of scope`
- M2-05 freshness: `NOT_STARTED`
- Commit/push/PR/merge/deploy: `NOT_RUN`
