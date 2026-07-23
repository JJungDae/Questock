# TASK CARD - M2-05 Freshness

## 1. Status and Approval

- Task bundle: `B5: M2-04~08`
- Step: `M2-05 Freshness`
- Planning date: `2026-07-23`
- Planning base branch: `main`
- Planning base SHA: `726bb633d1c5c935f04c9f691a97e966fbdcd0fc`
- Planning base commit message: `m2-04 conditional pass updates`
- M2-01 final code line: `5ffef6ca47c1ad8961bd717bb5623742bab8ddcb`
- M2-02 final code line: `9c5d609c20ed860d99f054415433ff15ff398a26`
- M2-03 implementation SHA: `008fd4ad27ffab638a6eb95b205f2ed6436b305d`
- M2-04 first implementation SHA: `d6c410b836334cbb267b70116c098c30fe624dc2`
- M2-04 supplement SHA: `726bb633d1c5c935f04c9f691a97e966fbdcd0fc`
- M2-04 code closure: `PASS`
- M2-04 Task Card Git synchronization: `PASS - approved closure synchronization already present and verified`
- M1-09 recorded status: `mandatory supplement implemented - final independent review pending`
- M1-09 provider completion: `pending final PASS`
- M2-05 plan review: `RE-REVIEWED - corrected final plan supplied`
- M2-05 planning entry: `ALLOWED`
- M2-05 implementation entry: `PASS - complete`
- Current status: `PASS / complete`
- Implementation SHA: `df20eae6457ac852e622b4006084acc16d1220fb`
- Implementation commit: `Implement m2-05`
- Implementation main push: `complete`
- Independent implementation review: `PASS WITH REQUIRED FOLLOW-UP`
- Further commit/push/PR/merge/deploy: `NOT_APPROVED`
- Live provider/API/UI/LLM work: `OUT_OF_SCOPE`
- M2-06 planning: `ALLOWED`
- M2-06 implementation: `ALLOWED only after approved M2-06 plan and preflight PASS`
- M2-07 citation validation and M2-08 dedupe/context budget: `NOT_STARTED`

The user approved this corrected final plan and the required preflight passed. The approved local implementation and verification are complete; Git operations remain separately gated.

The approved implementation scope was:

- deterministic in-memory freshness evaluation
- source-specific default windows
- disclosure 180-day → maximum 365-day policy expansion
- structured stale, date-quality, correction, window-expansion, and remaining-coverage warnings
- explicit disclosure correction/withdrawal handling
- unit and composition tests
- minimal M2-04 Task Card Git-state synchronization when still stale
- M2-05 Task Card result recording

It does not authorize commit, push, PR, merge, deploy, provider calls, live APIs, provider re-query, cache implementation, current-clock access, core-model changes, retrieval changes, API/UI, LLM, or later M2 implementation.

---

## 2. Source Basis and Requirement Provenance

The implementation agent must read the current `main` versions of the following before implementation.

| Source | Required Section | Contract used by M2-05 |
|---|---|---|
| `docs/agent_handoff/README_AGENT_RULES.md` | §§1.1~3.5 | minimum scope, real verification evidence, non-destructive Git, separate Git approval |
| `docs/agent_handoff/PROJECT_PLAN_FINAL_PASS.md` | §5.1, §5.2, M2-05, M2 Gate, §8.5 Traceability, B5 registry | basis date, default windows, stale warnings, correction priority, user period priority, disclosure fallback and shortage warning |
| `docs/TASK_CARDS/M2-01-query-planner.md` | period and source routing contracts | explicit date/today range versus default `recent` behavior |
| `docs/TASK_CARDS/M2-02-hard-filter.md` | source/security/date/document-type filtering | caller-owned hard-filter stage and user-range ownership |
| `docs/TASK_CARDS/M2-03-retrieval-baseline.md` | filter-before-score public behavior | M2-05 output must reach lexical ranking before stale/superseded items can occupy top-k |
| `docs/TASK_CARDS/M2-04-evidence-normalization.md` | status/result log and join contract | M2-04 closure, `document_id` join, exact Evidence mapping |
| `docs/TASK_CARDS/M1-05-disclosure-provider.md` | §§11~14 | receipt-only IDs, explicit `correction_of`, marker semantics, no report-family inference |
| `docs/agent_handoff/FINANCIAL_CAPABILITY_BASELINE.md` | C04~C06 | publication time, locator, snippet, retrieval and policy boundaries |
| `docs/agent_handoff/EXTENSION_COMPATIBILITY.md` | checkpoint 1 and P0 scope | basis/latestness evidence and reproducible regression |
| `docs/agent_handoff/RISK_RESPONSE_MATRIX.md` | R11, R12, R19, status hierarchy | stale data, correction priority, cache boundary |
| `docs/agent_handoff/EVALUATION_TAXONOMY_DRAFT.md` | `stale_data`, `correction_disclosure` | expected behavior and failure cases |
| `docs/agent_handoff/STOCK_SCOPE_CHANGE_NOTICE.md` | company-attribution contract | single-security P0 and no cross-company correction effects |
| `app/core/models.py` | `DateRange`, `Evidence`, `FinancialDocument`, `RetrievalRequest`, `ensure_evidence_matches_document()` | existing model and link contracts |
| `app/planning/query_planner.py` | `_parse_period()` and `SOURCE_EVIDENCE_MATRIX` | current explicit-period/default-period behavior |
| `app/evidence/normalizer.py` | M2-04 public output | one-to-one Evidence, exact timestamp and `document_id` join |
| `app/retrieval/filters.py` | `filter_evidence()` and effective-date fallback | M2-02 ownership and Evidence-first/document-fallback date semantics |
| `app/retrieval/retriever.py` | `retrieve_evidence()` | existing filter-before-score and deep score-copy behavior |
| `app/providers/disclosure.py` | disclosure document construction and marker metadata | exact metadata types and receipt relations |
| `app/ingest/reports.py` | report publication metadata | report source/date input only |

No live source, actual provider coverage, GitHub CI, independent test environment, cache state, external LLM, production orchestration, or user-facing UI is M2-05 completion evidence.

### 2.1 Review findings adopted

| Finding | Classification | Required effect |
|---|---|---|
| Original plan omitted the disclosure 180→365 fallback | `PLAN-VIOLATION` | add deterministic fallback policy |
| Original plan did not report shortage after fallback | `PLAN-VIOLATION` closure completion | add `insufficient_disclosure_coverage` warning when the 365-day result remains below 5 unique effective disclosures |
| Freshness position relative to hard filter and ranking was open | `PLAN-GAP` | define composition order without claiming production orchestration exists |
| Default-window boundary and stale boundary had a one-day gap | `PLAN-GAP` | use explicit inclusive maximum-age semantics |
| Effective timestamp precedence and future time were incomplete | `PLAN-GAP` | Evidence-first/document-fallback; compare future against `basis_at` |
| Empty `DateRange`, duplicate sources, and warning order were open | `PLAN-GAP` | define deterministic behavior |
| Disclosure correction/withdrawal edge cases were open | `PLAN-GAP` | define explicit graph and fail-closed cases |
| Reviewed plan claimed full hard-filter precondition detection without owning M2-02 logic | `REVIEW-SCOPE-CORRECTION` | treat full hard filtering as a caller precondition; validate only M2-05-owned consistency |
| Reviewed plan treated frozen containers as fully immutable | `REVIEW-SCOPE-CORRECTION` | describe tuple/frozen containers plus isolated mutable Evidence copies accurately |
| Reviewed plan did not distinguish policy expansion from provider re-query | `PLAN-GAP` | document candidate-horizon requirement and milestone follow-up |
| M2-04 Git Task Card may remain stale | `PROCESS-INTEGRITY` | verify and minimally synchronize during preflight |
| Prior M2 task logs established `.test_deps;.deps;.` as the working test path | `PROCESS-INTEGRITY` | use the established path instead of intentionally rerunning the known failing `.deps;.`-only command |

---

## 3. Goal and Boundary

### 3.1 Goal

Add a deterministic, in-memory freshness policy for M2-02-filtered Evidence and the caller-owned linked `FinancialDocument` map.

M2-05 provides:

- an injected basis timestamp and Asia/Seoul basis date
- source-specific default windows
- a disclosure fallback window decision
- stale, date-quality, correction, window-expansion, and remaining-coverage warnings
- explicit disclosure correction/withdrawal priority
- frozen result containers containing isolated deep-copied Evidence
- a tested composition contract for M2-03 and M2-06

### 3.2 Composition order

The phase-appropriate composition contract is:

```text
M2-04 normalize FinancialDocument → Evidence
→ M2-02 filter_evidence with the same RetrievalRequest/documents_by_id
→ M2-05 evaluate_freshness
→ M2-03 retrieve_evidence
→ M2-06 EvidencePolicy
```

Reasons:

- M2-02 owns security, source, user date range, document type, and Evidence scope filtering.
- M2-05 applies default freshness and correction policy before ranking.
- M2-03 may repeat its existing hard-filter validation internally; M2-05 does not modify M2-03.
- M2-06 may consume M2-05 warnings and the later retrieval result to decide final Evidence status.

### 3.3 No false orchestration claim

No production orchestration function currently wires all stages together.

M2-05 completion proves:

- the public freshness function is deterministic
- the result composes with the existing M2-02 and M2-03 public functions
- the required order is fixed by integration tests

M2-05 completion does **not** claim that the deployed runtime already calls the stages in this order.

Actual application/service wiring remains a later orchestration or phase-slice responsibility.

### 3.4 Hard-filtered input precondition

`evaluate_freshness()` accepts Evidence that the caller has already passed through `filter_evidence()` using the same:

- `RetrievalRequest`
- `documents_by_id`

M2-05 validates only its owned boundary:

- public input types
- canonical model validity
- mapping key/document identity
- exact Evidence/document link integrity
- Evidence/document source-type equality
- every input Evidence source is present in `request.source_types`
- correction metadata and relation safety

M2-05 does **not** duplicate or claim to fully detect:

- request security filtering
- Evidence scope filtering
- user date-range filtering
- document-type filtering

The full precondition is proven through integration tests, not by reimplementing M2-02.

### 3.5 Candidate-horizon limitation

The disclosure fallback is an in-memory policy over the candidate Evidence supplied by the caller.

M2-05:

- does not call a provider
- does not re-query from 180 to 365 days
- does not know whether the caller supplied a complete 365-day corpus
- does not claim actual-source coverage

For default disclosure mode, the caller should supply candidates covering up to 365 days when available.

If the 365-day policy result remains below 5 unique effective disclosures, M2-05 emits `insufficient_disclosure_coverage`.

Provider/repository orchestration that guarantees or re-fetches the 365-day candidate horizon is required before the M2 milestone is represented as a complete live-data fallback.

### 3.6 Out of scope

- core model/status/schema changes
- root `app.evidence` export changes
- QueryPlanner or session changes
- changes to M2-02 or M2-03
- production orchestration wiring
- provider, ingest, repository, cache, retry, or live API work
- `ProviderResult.fetched_at` or `from_cache` policy
- system-clock access
- market-session or M1-09 logic
- title/text/date/order-based disclosure-family inference
- report permission decisions
- EvidencePolicy decisions
- citation validation
- numeric validation
- duplicate removal or context budget
- API/UI/LLM work
- new dependencies, fixture-data files, or scripts

---

## 4. Proposed Public API

Create only:

```text
app/evidence/freshness.py
```

Do not modify `app/evidence/__init__.py`.

```python
class FreshnessValidationError(ValueError):
    """Raised for malformed public freshness-policy inputs."""
    ...


@dataclass(frozen=True)
class FreshnessWindow:
    source_type: str
    start: date | None
    end: date | None
    applied_by: Literal["default", "fallback", "user", "none"]


@dataclass(frozen=True)
class FreshnessWarning:
    code: Literal[
        "missing_published_at",
        "future_published_at",
        "stale_news",
        "stale_research_report",
        "disclosure_window_extended",
        "insufficient_disclosure_coverage",
        "unresolved_disclosure_correction",
    ]
    source_type: str


@dataclass(frozen=True)
class FreshnessResult:
    basis_at: datetime
    basis_date: date
    windows: tuple[FreshnessWindow, ...]
    evidence: tuple[Evidence, ...]
    warnings: tuple[FreshnessWarning, ...]
    latest_effective_disclosure_at: datetime | None


def evaluate_freshness(
    evidence: Sequence[Evidence],
    request: RetrievalRequest,
    *,
    documents_by_id: Mapping[str, FinancialDocument],
    basis_at: datetime,
) -> FreshnessResult:
    ...
```

Public import:

```python
from app.evidence.freshness import (
    FreshnessResult,
    FreshnessValidationError,
    FreshnessWarning,
    FreshnessWindow,
    evaluate_freshness,
)
```

No root-package export is added.

`FreshnessResult` is a frozen container, but `Evidence` remains a mutable Pydantic model. Returned Evidence must therefore be deep-copied and isolated rather than described as intrinsically immutable.

---

## 5. Exact Validation and Processing Order

Apply this order.

```text
top-level evidence/request/mapping/basis validation
→ canonical revalidation of RetrievalRequest
→ validate and canonicalize basis_at
→ validate mapping key/value/document-ID identity
→ canonical revalidation of input Evidence and referenced FinancialDocument
→ verify Evidence/document link, source equality, and requested-source consistency
→ determine first-occurrence unique requested-source order
→ determine meaningful user date range
→ resolve effective timestamp for each Evidence
→ validate disclosure metadata
→ build explicit active correction graph
→ apply withdrawal and explicit replacement
→ determine default/fallback/user windows
→ calculate stale/date/correction/window/coverage warnings
→ apply effective windows
→ deep-copy retained Evidence
→ calculate latest effective disclosure timestamp
→ return FreshnessResult
```

Rules:

- no provider, file, manifest, registry, repository, cache, clock, or network I/O
- no early successful return before required validation completes
- no broad exception catch
- expected Pydantic/link/metadata failures become fixed sanitized `FreshnessValidationError`
- unexpected internal exceptions propagate
- raw IDs, titles, metadata, URLs, paths, and raw exception text never appear in public errors or warnings

---

## 6. Public Input Contract

### 6.1 Evidence sequence

- accept a non-string `Sequence[Evidence]`
- reject `str`, `bytes`, `bytearray`, mappings, generators, and scalars
- reject invalid items
- an empty sequence returns a valid result
- no partial result is returned on invalid input
- canonical revalidate each item
- do not mutate the input sequence or Evidence

### 6.2 RetrievalRequest

Canonical revalidate the complete current request values.

`source_types`:

- each item must be a nonblank string
- output windows use first-occurrence unique order
- duplicates do not create duplicate windows or warnings
- input request is not mutated

Meaningful user range:

```text
request.date_range is not None
and at least one of request.date_range.start / request.date_range.end is not None
```

`DateRange(start=None, end=None)` is treated as no explicit user range.

### 6.3 documents_by_id

- require a Mapping
- keys must be strings
- values must be `FinancialDocument`
- each key must equal `document.document_id`
- every input Evidence must have an exact linked document
- canonical revalidate every Evidence-linked document
- unrelated extra valid documents do not affect windows, warnings, counts, or output

Exception:

- a document explicitly referenced by a disclosure `correction_of` relation may be read from the mapping solely to validate relation identity and cross-company safety
- it does not become output Evidence unless an input Evidence for it exists

### 6.4 Source consistency

- each Evidence source type must equal its linked document source type
- each Evidence source type must appear in the unique requested sources
- otherwise fail with a sanitized validation error
- no alias or source fallback is added

### 6.5 basis_at

- must be a `datetime`
- must be timezone-aware
- `utcoffset()` must equal zero
- UTC-equivalent zero-offset tzinfo values are accepted
- result `basis_at` is normalized to `datetime.timezone.utc`
- system clock is never read
- `basis_date` is the Asia/Seoul date derived from canonical UTC `basis_at`

---

## 7. Effective Timestamp Contract

Use the same precedence as M2-02:

```text
aware Evidence.published_at
→ otherwise aware linked FinancialDocument.published_at
→ otherwise unavailable
```

Rules:

- if Evidence has an aware timestamp, do not fall back merely because it is future or out of window
- canonicalize only for comparison; do not rewrite the stored Evidence timestamp
- age windows use the Asia/Seoul calendar date
- an effective timestamp is future when its UTC instant is later than `basis_at`, including later on the same Seoul date
- a supported-source item with no usable timestamp is omitted and produces one `missing_published_at` warning for that source
- a supported-source item with a future timestamp is omitted and produces one `future_published_at` warning
- missing/future handling applies in default and user-range modes
- missing or future items do not suppress a stale warning derived from older valid items
- output deep copies preserve the original Evidence timestamp
- `latest_effective_disclosure_at` is normalized to UTC

Supported freshness sources:

```text
news
disclosure
research_report
```

Other source types receive no date policy and pass through after common validation.

---

## 8. Window Contract

### 8.1 Inclusive maximum-age semantics

```text
age_days = basis_date - effective_timestamp.astimezone(Asia/Seoul).date()
```

A supported item is inside a default/fallback window when:

```text
0 <= age_days <= max_age_days
```

| source | maximum age | window start | window end |
|---|---:|---|---|
| `news` | 30 | `basis_date - 30 days` | `basis_date` |
| `disclosure` | 180 | `basis_date - 180 days` | `basis_date` |
| `research_report` | 180 | `basis_date - 180 days` | `basis_date` |

This is a deliberate maximum-age contract. It avoids a silent gap where an exactly 180-day-old report would be outside the default window but not yet meet the “older than 180 days” stale rule.

### 8.2 User period priority

When a meaningful user range exists:

- create one exact copied user window per unique requested source
- `applied_by="user"`
- do not apply default/fallback age omission
- do not apply default stale thresholds
- correction, withdrawal, missing-date, and future-time policy still applies
- M2-02 remains the owner of inclusive user-range filtering
- M2-05 does not expand, narrow, substitute, or normalize the user range

### 8.3 Unknown sources

For an unknown requested source:

```text
start=None
end=None
applied_by="none"
```

Unknown-source Evidence passes through unchanged after common validation.

### 8.4 Empty source list

If `request.source_types` is empty:

- `windows=()`
- no source-specific warnings
- empty Evidence returns a valid empty result
- nonempty Evidence fails requested-source consistency validation

---

## 9. Disclosure 180→365 Fallback and Coverage

Apply only when:

- no meaningful user range exists
- `disclosure` is requested

### 9.1 Count basis

After:

- common validation
- missing/future-date exclusion
- withdrawal exclusion
- explicit correction replacement

count unique retained disclosure `document_id` values with:

```text
0 <= age_days <= 180
```

Duplicate Evidence occurrences do not inflate the count.

### 9.2 Expansion

If the unique 180-day count is fewer than 5:

```text
maximum age = 365
window start = basis_date - 365 days
window end = basis_date
applied_by = "fallback"
warning = disclosure_window_extended
```

Otherwise use the 180-day default window.

Rules:

- do not include disclosures older than 365 days
- do not include another source or company to reach 5
- do not run or claim a provider re-query
- do not infer document families
- retained duplicate occurrences remain in output order

### 9.3 Remaining shortage

After applying the actual disclosure window, count unique retained disclosure IDs again.

If the count remains below 5, emit once:

```text
FreshnessWarning(
    code="insufficient_disclosure_coverage",
    source_type="disclosure",
)
```

This structured warning fulfills the project requirement to expose remaining data shortage.

M2-05 does not convert it into a final EvidenceDecision status.

### 9.4 User range

A meaningful user range disables:

- automatic 180→365 fallback
- `disclosure_window_extended`
- minimum-five coverage enforcement and `insufficient_disclosure_coverage`

The user-selected period remains authoritative.

---

## 10. Stale Warning Contract

Apply stale thresholds only when no meaningful user range exists.

Candidate dates:

- valid
- nonfuture
- requested
- M2-02-filtered
- evaluated before default-window omission

### 10.1 News

```text
newest valid news age <= 14:
    no stale_news

newest valid news age > 14:
    stale_news
```

### 10.2 Research report

```text
newest valid report age <= 180:
    no stale_research_report

newest valid report age > 180:
    stale_research_report
```

Age exactly 180 remains inside the default window and is not stale.

### 10.3 Disclosure

There is no generic disclosure stale warning.

M2-05 exposes:

- actual disclosure window
- `disclosure_window_extended`
- `insufficient_disclosure_coverage`
- `latest_effective_disclosure_at`
- unresolved correction warning

---

## 11. Disclosure Correction Contract

Only linked documents with:

```text
source_type == "disclosure"
```

participate.

### 11.1 Identity

A participating disclosure must use:

```text
document_id = "disclosure:<14-digit receipt>"
```

Metadata is read from the linked `FinancialDocument` only.

### 11.2 Metadata validation

Optional boolean keys:

```text
is_correction
has_subsequent_correction
is_withdrawn
```

- missing means `False`
- present value must be exactly `bool`
- `None`, integer, string, or another type fails closed

`correction_of`:

- missing or `None` is allowed
- otherwise must be a nonblank 14-digit receipt string
- maps to `document_id=f"disclosure:{receipt}"`
- requires `is_correction is True`
- self-reference is invalid

### 11.3 Withdrawal-first

- omit every occurrence of an `is_withdrawn=True` disclosure
- a withdrawn correction does not replace an original
- a withdrawn original remains omitted
- a relation to a withdrawn correction does not resolve `has_subsequent_correction`

### 11.4 Explicit active graph

Build edges only from nonwithdrawn correction Evidence:

```text
correction document → explicitly replaced document
```

Rules:

- no title, text, date, receipt order, `rm`, or report-family inference
- cycles among available active graph nodes fail closed
- when a referenced target document is available in `documents_by_id`, cross-company primary-security mismatch fails closed
- a valid target receipt absent from input Evidence is not omitted because no target occurrence exists
- a valid target document absent from `documents_by_id` does not by itself make the correction unresolved
- an explicit correction with an absent target remains a terminal correction
- every available document ID replaced by an active correction is omitted
- intermediate corrections are omitted when explicitly replaced by a later active correction
- terminal correction Evidence is retained
- all duplicate occurrences of a replaced or withdrawn ID are omitted
- duplicates of a retained ID remain in input order

### 11.5 Unresolved correction

Emit one `unresolved_disclosure_correction` warning and set `latest_effective_disclosure_at=None` if any retained disclosure has one of these conditions:

- `has_subsequent_correction=True` and no active explicit replacement Evidence is present
- `is_correction=True` with no explicit `correction_of`
- more than one terminal active correction points to the same explicitly linked root without an explicit chain ordering them

A referenced original being absent from input does not alone create an unresolved condition.

Visible nonwithdrawn, nonreplaced documents remain; M2-06 decides answer strength.

### 11.6 Latest effective disclosure timestamp

If no unresolved condition remains:

- calculate after withdrawal, replacement, missing/future exclusion, and effective-window omission
- use retained disclosure Evidence only
- return the latest timestamp normalized to UTC
- return `None` when no retained disclosure remains

---

## 12. Warning Determinism

Warnings are:

- unique by `(code, source_type)`
- grouped by first-occurrence unique requested-source order
- ordered within each source by this fixed order:

```text
missing_published_at
future_published_at
stale_news
stale_research_report
disclosure_window_extended
insufficient_disclosure_coverage
unresolved_disclosure_correction
```

Warnings for unrequested sources are not produced.

No warning includes:

- document/evidence ID
- title
- URL
- metadata
- receipt
- path
- raw exception
- provider message

---

## 13. Copy, Mutation, and Determinism

- `FreshnessResult`, `FreshnessWindow`, and `FreshnessWarning` are frozen dataclasses
- tuple fields are fresh tuples
- every returned Evidence is a deep copy
- retrieval score and locator are preserved
- subject and mentioned lists are isolated
- Evidence elements remain mutable Pydantic objects, but mutation cannot affect input or later calls
- input Evidence, linked documents, metadata, request, mapping, and source lists are not mutated
- input order and duplicate occurrences are preserved except explicit replacement/withdrawal
- repeated calls with equal input produce equal serialized output
- no global cache, registry, repository, or mutable singleton
- no I/O occurs

---

## 14. Error Contract

Use a small fixed sanitized message set:

```text
evidence must be a sequence
evidence items are invalid
request must be a RetrievalRequest
documents_by_id must be a mapping
documents_by_id is invalid
linked document is missing
linked evidence is invalid
evidence source is not requested
basis_at must be an aware UTC datetime
freshness timestamp is invalid
disclosure metadata is invalid
disclosure correction relation is invalid
```

Convert only expected public-input failures:

- explicit M2-05 validation failures
- Pydantic `ValidationError` from canonical revalidation
- `ensure_evidence_matches_document()` failures
- malformed correction metadata or active graph

Do not expose or implement a generic:

```text
freshness input is not hard-filtered
```

M2-05 does not own enough M2-02 logic to prove that condition without duplication.

Do not broadly catch:

- `RuntimeError`
- `MemoryError`
- programmer errors
- unexpected standard-library failures

Raw values and raw exceptions must not leak.

---

## 15. Planned Files

### New

- `app/evidence/freshness.py`
- `tests/unit/test_evidence_freshness.py`
- `docs/TASK_CARDS/M2-05-freshness.md`

### Modified only when required

- `docs/TASK_CARDS/M2-04-evidence-normalization.md`
  - synchronize actual M2-04 supplement SHA, push, closure, and M2-05 entry only when still stale
- `docs/TASK_CARDS/M2-05-freshness.md`
  - implementation and verification result recording

### Do not modify

- `app/evidence/__init__.py`
- `app/evidence/normalizer.py`
- `app/core/**`
- `app/retrieval/**`
- `app/providers/**`
- `app/ingest/**`
- `app/planning/**`
- `app/api/**`
- `app/llm/**`
- `data/**`
- existing fixtures
- dependency and lock files
- scripts
- `docs/TASK_CARDS/M1-09-market-snapshot-gate.md`
- M2-06 and later Task Cards

If another file is required, stop and report before expanding scope.

---

## 16. Required Preflight

Run from repository root after plan approval and before M2-05 code changes.

### 16.1 Git baseline

```powershell
git status --short
git rev-parse HEAD
git log -1 --oneline
```

Expected:

```text
HEAD = 726bb633d1c5c935f04c9f691a97e966fbdcd0fc
latest commit = m2-04 conditional pass updates
```

Rules:

- approved M2-04 closure synchronization and M2-05 planning file may already be dirty
- record document-only deviations
- unexpected code, fixture, dependency, data, unrelated Task Card, or user files stop implementation
- do not use reset, restore, checkout, clean, stash, force push, or history rewrite

### 16.2 M2-04 Task Card synchronization

Inspect:

```text
docs/TASK_CARDS/M2-04-evidence-normalization.md
```

Expected final record:

```text
Current status: PASS - complete
First implementation SHA: d6c410b836334cbb267b70116c098c30fe624dc2
First implementation commit: Implement m2-04
First implementation main push: complete
Supplement SHA: 726bb633d1c5c935f04c9f691a97e966fbdcd0fc
Supplement commit: m2-04 conditional pass updates
Supplement main push: complete
Final closure review: PASS
Targeted pytest: 67 passed
M2 integration regression: 226 passed
Full unit regression: 987 passed
GitHub CI: NOT_RUN
Independent pytest rerun: NOT_RUN
M2-05 planning: ALLOWED
M2-05 implementation: ALLOWED after approved plan and preflight PASS
Further commit/push/PR/merge/deploy: NOT_APPROVED
```

If already accurate, do not rewrite.

If stale, apply only this synchronization.

Keep M1-09 pending.

### 16.3 Baseline regression

Use the test dependency path established by M2-04 results.

```powershell
$env:PYTHONPATH = ".test_deps;.deps;."; python -m pytest tests/unit/test_evidence_normalization.py -q
$env:PYTHONPATH = ".test_deps;.deps;."; python -m pytest tests/unit/test_query_planner.py tests/unit/test_retrieval_filters.py tests/unit/test_retrieval_baseline.py tests/unit/test_evidence_normalization.py -q
$env:PYTHONPATH = ".test_deps;.deps;."; python -m pytest tests/unit -q
$env:PYTHONPATH = ".test_deps;.deps;."; python -c "from app.evidence import EvidenceNormalizationError, normalize_financial_document, normalize_financial_documents; print('ok')"
python scripts/secret_scan.py
python -m compileall app tests scripts -q
```

Expected baseline record from M2-04:

```text
M2-04 targeted: 67 passed
M2 integration: 226 passed
full unit: 987 passed
existing FastAPI/Starlette warning: 1
```

Every final command must exit `0`.

If the established dependency path is unavailable, stop and report rather than inventing a new environment or rewriting a failure as success.

---

## 17. Required Tests

Create:

```text
tests/unit/test_evidence_freshness.py
```

Use synthetic in-memory M2-04-normalized Evidence and linked documents.

### 17.1 Public boundary

- root package exports remain unchanged
- submodule public import works
- malformed sequence/request/mapping/key/value/link uses sanitized `FreshnessValidationError`
- invalid item returns no partial result
- bypass-created malformed Evidence/FinancialDocument/Request is canonically revalidated
- mapping key/document ID mismatch fails
- linked source mismatch fails
- Evidence source not requested fails
- extra unrelated mapping items do not affect result
- referenced correction target may be inspected only for relation integrity
- zero-offset UTC-equivalent basis is accepted and normalized
- naive/nonzero-offset/non-datetime basis fails
- unexpected injected `RuntimeError` propagates
- no I/O or clock access

### 17.2 Composition order

Build:

```text
M2-04 normalize
→ M2-02 filter_evidence
→ M2-05 evaluate_freshness
→ M2-03 retrieve_evidence
```

Verify:

- wrong-company, wrong-source, wrong-date, and document-type exclusions remain absent
- M2-05 does not claim direct detection of every unfiltered-input violation
- stale or superseded items do not occupy M2-03 top-k
- M2-03 score-stamps another deep copy
- M2-05 output scores and original Evidence remain unchanged
- tests prove composability only, not production orchestration wiring

### 17.3 Source and user-range behavior

- duplicate requested sources create one window each in first-occurrence order
- `DateRange(None, None)` uses defaults
- start-only, end-only, same-day, and both-bound user ranges are copied exactly
- meaningful user range disables defaults, fallback, stale thresholds, and minimum-five coverage warnings
- empty source list plus empty Evidence returns empty result
- empty source list plus nonempty Evidence fails
- unknown requested source uses `applied_by="none"` and passes through
- request and DateRange remain unchanged

### 17.4 Timestamp and default boundaries

- Asia/Seoul basis-date boundary around UTC date change
- news age 30 included, age 31 omitted
- disclosure age 180 included under normal default
- report age 180 included, age 181 omitted
- basis date included
- same-Seoul-date timestamp later than `basis_at` is future and omitted
- future-date item omitted
- Evidence-aware timestamp wins
- linked-document aware timestamp is fallback
- both missing/naive produces `missing_published_at`
- future Evidence timestamp does not fall back to an older document timestamp

### 17.5 Stale warnings

- news age 14 no warning
- news age 15 stale
- report age 180 no warning
- report age 181 stale
- old-only source warns before omission
- missing/future items do not suppress stale warning from older valid items
- no valid dated item means no stale warning
- warnings are unique and deterministic

### 17.6 Disclosure fallback and shortage

- 5 unique valid disclosures inside age 180 keep default window
- 4 unique valid disclosures trigger 365 fallback
- duplicate occurrences do not count toward 5
- age 365 included under fallback; age 366 omitted
- fallback warning emitted once
- after fallback count 5 or more produces no shortage warning
- after fallback count below 5 produces `insufficient_disclosure_coverage`
- unrelated source/company Evidence is never added
- no provider/repository call occurs
- test documents the candidate-horizon limitation
- meaningful user range disables fallback and shortage warning

### 17.7 Disclosure correction

- exact correction replaces exact available original only
- explicit chain retains only terminal correction
- unrelated same-title disclosures remain
- withdrawn original omitted
- withdrawn correction does not replace original
- unresolved `has_subsequent_correction` warns and nulls latest effective date
- `is_correction=True` without `correction_of` warns and nulls latest date
- correction with valid relation but absent original remains terminal without unresolved warning solely for absence
- available cross-company target fails closed
- absent target does not create output or affect count
- resolved explicit correction permits latest effective date
- multiple unordered terminal corrections warn and null latest date
- self-link fails
- active cycle fails
- malformed bool/correction receipt fails sanitized
- duplicates of replaced/withdrawn IDs all omitted
- duplicates of retained IDs preserve order
- no title/date/receipt-order family inference

### 17.8 Copy and output

- result/window/warning dataclasses are frozen
- outer fields are tuples
- returned Evidence and nested locator/security lists are isolated
- caller can mutate returned Evidence without affecting input or a later call
- retrieval scores are preserved
- `basis_at` and latest disclosure timestamp are UTC
- warnings expose no IDs, titles, metadata, URLs, receipts, paths, or raw exceptions

### 17.9 Scope guard

Source inspection confirms no imports of:

```text
provider
ingest
retrieval implementation
planner
API
LLM
cache
repository
vector
reranker
dedupe
```

Importing core models and standard-library modules is allowed.

---

## 18. Verification After Implementation

### 18.1 Targeted

```powershell
$env:PYTHONPATH = ".test_deps;.deps;."; python -m pytest tests/unit/test_evidence_freshness.py -q
```

### 18.2 M2 composition regression

```powershell
$env:PYTHONPATH = ".test_deps;.deps;."; python -m pytest tests/unit/test_query_planner.py tests/unit/test_retrieval_filters.py tests/unit/test_retrieval_baseline.py tests/unit/test_evidence_normalization.py tests/unit/test_evidence_freshness.py -q
```

### 18.3 Full unit

```powershell
$env:PYTHONPATH = ".test_deps;.deps;."; python -m pytest tests/unit -q
```

### 18.4 Import smoke

```powershell
$env:PYTHONPATH = ".test_deps;.deps;."; python -c "from app.evidence.freshness import FreshnessResult, FreshnessValidationError, FreshnessWarning, FreshnessWindow, evaluate_freshness; print('ok')"
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

- exact command
- environment
- exit code
- pass count
- warning
- initial failure and corrected rerun
- skipped/not-run checks
- GitHub CI state
- independent rerun state
- final changed files

Do not claim:

- live data
- actual provider coverage
- complete 365-day upstream candidate coverage
- cache freshness
- production orchestration
- UI behavior
- production latency

---

## 19. Completion Criteria

- [x] planning base SHA confirmed
- [x] M2-04 Task Card synchronized only if stale
- [x] M1-09 remains pending
- [x] only approved files changed
- [x] root package exports unchanged
- [x] public freshness submodule created
- [x] exact validation/processing order implemented
- [x] caller-owned M2-02 precondition documented
- [x] M2-02 precondition not falsely claimed as fully detectable
- [x] composition order tested
- [x] production orchestration not falsely claimed
- [x] basis_at canonical UTC and basis_date Seoul
- [x] meaningful user-range behavior exact
- [x] duplicate source ordering exact
- [x] Evidence/document timestamp precedence exact
- [x] same-day and later-date future handling exact
- [x] news/report default boundaries exact
- [x] stale thresholds exact
- [x] disclosure 180→365 fallback exact
- [x] fallback count uses unique effective disclosure IDs
- [x] remaining shortage warning exact
- [x] candidate-horizon limitation documented
- [x] correction graph/withdrawal order exact
- [x] absent correction target behavior exact
- [x] unresolved correction rules exact
- [x] latest effective disclosure timestamp exact
- [x] warnings deterministic and sanitized
- [x] frozen containers and deep-copy isolation exact
- [x] no I/O, cache, clock, provider, repository, API/UI/LLM
- [x] no core/retrieval/producer modifications
- [x] M2-02/M2-03 compatibility passes
- [x] targeted tests pass
- [x] M2 composition regression passes
- [x] full unit regression passes
- [x] import smoke passes
- [x] secret scan passes
- [x] compile passes
- [x] diff review passes
- [x] Task Card records actual results
- [x] commit/push/PR/merge/deploy remain `NOT_RUN`

---

## 20. Required Before M2 Milestone Close

These do not block the isolated M2-05 implementation but must not be forgotten:

1. A real orchestration/phase-slice path must call:

```text
normalize → hard filter → freshness → retrieval → EvidencePolicy
```

2. Default disclosure acquisition must make up-to-365-day candidates available or perform an approved re-query when the fallback is requested.

3. M2-05 warnings must be consumed by M2-06 without converting provider failure into no-data.

4. User-facing period and shortage wording remains M3/UI responsibility.

Until items 1 and 2 are demonstrated, describe M2-05 as an in-memory policy and composition contract, not a completed live fallback pipeline.

---

## 21. Stop Conditions

Stop and report if:

- planning base SHA differs
- M2-04 Task Card cannot be synchronized safely
- preflight fails
- unexpected dirty files exist
- core models/status must change
- M2-02/M2-03 code must change
- provider/ingest/repository/cache code must change
- a system clock or live call becomes necessary
- correction policy requires title/text/date/order family inference
- a new source fixture or dependency becomes necessary
- M2-06 status decisions become necessary
- citation/numeric/dedupe/API/UI/LLM work becomes necessary
- M1-09 pending state must change
- unrelated regression fails

Do not silently:

- expand beyond 365 days
- claim the caller supplied a complete 365-day candidate corpus
- include another company/source to reach disclosure count 5
- infer correction relations
- treat an empty `DateRange` as a user override
- return future supporting Evidence
- map warnings to final EvidenceDecision status
- claim production orchestration exists
- modify the root package export contract

---

## 22. Fallback and Rollback

- malformed public input → sanitized `FreshnessValidationError`
- missing/unusable timestamp → omit affected supported Evidence and warn
- future timestamp → omit affected supported Evidence and warn
- fewer than 5 unique effective disclosures within 180 days → apply maximum 365-day window and warn
- fewer than 5 after 365-day policy → emit remaining coverage warning
- unresolved correction → retain nonwithdrawn, nonreplaced facts; null latest disclosure timestamp; warn
- no eligible Evidence → return empty Evidence tuple and warnings; M2-06 decides status
- rollback after future approved implementation:
  - revert only M2-05 files and any M2-04 Task Card synchronization
  - explicit user approval required
  - no reset, clean, force push, or history rewrite

---

## 23. Implementation Order After Approval

1. Confirm `main` at `726bb633d1c5c935f04c9f691a97e966fbdcd0fc`.
2. Record initial Git status.
3. Read required source sections.
4. Synchronize M2-04 Task Card only if stale.
5. Run baseline regression, smoke, secret scan, and compile.
6. Create `docs/TASK_CARDS/M2-05-freshness.md` from this approved plan.
7. Create `app/evidence/freshness.py`.
8. Implement public validation and canonical revalidation.
9. Implement effective timestamp resolution and future-instant checks.
10. Implement correction metadata validation and active graph.
11. Implement default/user/fallback windows.
12. Implement expansion and remaining-coverage warnings.
13. Implement warning ordering and deep-copy output.
14. Add exact unit and composition tests.
15. Run targeted tests.
16. Run M2 composition regression.
17. Run full unit regression.
18. Run smoke, secret scan, compile, and diff checks.
19. Record actual results in the M2-05 Task Card.
20. Report changed files, commands, results, limitations, and rollback.
21. Wait for separate commit/push approval.

---

## 24. Implementation Review Checklist

### Source and scope

- [x] planning base and latest SHA
- [x] M2-01~04 inherited contracts
- [x] M2-04 Task Card final state
- [x] M1-09 pending
- [x] full changed-file list
- [x] only approved files
- [x] no core/retrieval/provider/ingest/repository/cache/API/UI/LLM changes
- [x] root package exports unchanged

### Public boundary

- [x] sequence/request/mapping/basis validation
- [x] canonical revalidation
- [x] mapping identity and exact links
- [x] source consistency
- [x] hard-filter precondition documented but not duplicated
- [x] expected errors sanitized
- [x] unexpected errors propagate
- [x] no partial result

### Date and windows

- [x] zero-offset basis accepted/canonicalized
- [x] Seoul basis date
- [x] Evidence-first/document-fallback timestamp
- [x] same-day future instant handling
- [x] missing/future policy
- [x] meaningful user-range detection
- [x] user-range priority
- [x] age 30/180/365 boundaries
- [x] unknown sources
- [x] duplicate source ordering

### Disclosure

- [x] fallback unique-count rule
- [x] fallback warning/window
- [x] remaining shortage warning
- [x] candidate-horizon limitation
- [x] withdrawal-first
- [x] explicit graph only
- [x] absent target behavior
- [x] chain terminal handling
- [x] cycle/self-link/cross-company failures
- [x] unresolved conditions
- [x] duplicate occurrence behavior
- [x] latest effective UTC timestamp

### Warnings and copies

- [x] fixed warning code order
- [x] uniqueness
- [x] no raw data leakage
- [x] frozen containers
- [x] deep Evidence copies
- [x] score and locator preservation
- [x] no input mutation
- [x] deterministic rerun

### Verification

- [x] targeted result
- [x] M2 composition result
- [x] full unit result
- [x] import smoke
- [x] secret scan
- [x] compile
- [x] diff check
- [x] GitHub CI accurately recorded
- [x] independent rerun accurately recorded
- [x] commit/push state matches reality

---

## 25. Result Log

- Planning base SHA: `726bb633d1c5c935f04c9f691a97e966fbdcd0fc`
- Planning base commit: `m2-04 conditional pass updates`
- M2-04 Task Card synchronization: `PASS - pre-existing approved closure synchronization verified accurate; no additional rewrite required`
- M1-09 state: `mandatory supplement implemented - final independent review pending`
- Initial dependency-path preflight: `FAIL - exit 1 - PYTHONPATH=.test_deps;.deps;. exposed an unreadable pytest package; python -m pytest reported No module named pytest.__main__`
- Initial `.venv` state: `Python 3.14.3 available; pip unavailable; only Python 3.14 registered by py launcher; uv not installed`
- Environment recovery: `PASS - .venv ensurepip installed pip 25.3; editable install exited 1 because existing setuptools discovery found app and data; declared runtime/dev dependencies were installed directly without changing pyproject.toml; tzdata 2026.3 was added for Windows Asia/Seoul ZoneInfo`
- Environment recovery execution context: `sandbox ensurepip exited 1 on user Temp access; approved local ensurepip rerun exited 0; initial targeted rerun exited 1 on missing tzdata; approved local tzdata install exited 0`
- Final interpreter: `C:\Users\USER\Questock\.venv\Scripts\python.exe`
- Final Python: `3.14.3`
- Final pip: `25.3`
- Final pytest: `8.4.2`
- Environment recovery tracked-file changes: `none; .venv remains ignored`
- Preflight targeted normalization: `PASS - exit 0 - 67 passed, 1 PytestCacheWarning`
- Preflight M2 regression: `PASS - exit 0 - 226 passed, 1 PytestCacheWarning`
- Preflight full unit initial sandbox run: `FAIL - exit 1 - 884 passed, 103 setup errors caused by denied pytest user-Temp access`
- Preflight full unit approved local rerun: `PASS - exit 0 - 987 passed, 1 existing FastAPI/Starlette deprecation warning`
- Preflight smoke: `PASS - exit 0 - ok`
- Preflight secret scan: `PASS - exit 0 - []`
- Preflight compile: `PASS - exit 0`
- M2-05 implementation: `PASS / complete`
- Implementation SHA: `df20eae6457ac852e622b4006084acc16d1220fb`
- Implementation commit: `Implement m2-05`
- Implementation main push: `complete`
- Independent implementation review: `PASS WITH REQUIRED FOLLOW-UP`
- Targeted pytest: `PASS - exit 0 - 88 passed, 1 PytestCacheWarning`
- M2 composition regression: `PASS - exit 0 - 314 passed, 1 PytestCacheWarning`
- Full unit regression: `PASS - exit 0 - 1075 passed, 1 existing FastAPI/Starlette deprecation warning`
- Import smoke: `PASS - exit 0 - ok`
- Secret scan: `PASS - exit 0 - []`
- Compile: `PASS - exit 0`
- Diff check: `PASS - git diff --check exit 0; no whitespace errors; M2-04 LF-to-CRLF working-copy warning only`
- Implementation changed files: `A app/evidence/freshness.py; M docs/TASK_CARDS/M2-04-evidence-normalization.md; A docs/TASK_CARDS/M2-05-freshness.md; A tests/unit/test_evidence_freshness.py`
- GitHub CI: `NOT_RUN`
- Independent pytest rerun: `NOT_RUN`
- 365-day candidate completeness: `NOT_RUN - required before M2 milestone close`
- Live provider/actual source/cache/API/UI/LLM: `NOT_RUN - out of scope`
- Production orchestration: `NOT_RUN - required before M2 milestone close`
- M2-06 planning: `ALLOWED`
- M2-06 implementation: `ALLOWED only after approved M2-06 plan and preflight PASS`
- Further commit/push/PR/merge/deploy: `NOT_APPROVED`
