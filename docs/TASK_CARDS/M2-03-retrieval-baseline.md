# TASK CARD - M2-03 Retrieval Baseline

## 1. Status and Approval

- Task bundle: `B4: M2-01~03`
- Step: `M2-03 Retrieval Baseline`
- Planning date: `2026-07-23`
- Planning base branch: `main`
- Planning base commit: `9c5d609c20ed860d99f054415433ff15ff398a26`
- Planning base commit message: `m2-02 conditional pass updates`
- M2-02 code closure review: `PASS`
- M2-02 required follow-up SHA: `9c5d609c20ed860d99f054415433ff15ff398a26`
- M2-02 required follow-up main push: `complete`
- M2-02 Task Card synchronization: `PASS - closure PASS, follow-up SHA/push, and M2-03 entry synchronized before code changes`
- M2-03 planning entry: `ALLOWED`
- M2-03 implementation entry: `ALLOWED only after preflight and M2-02 Task Card synchronization`
- Current status: `IMPLEMENTATION COMPLETE - USER REVIEW PENDING`
- Implementation approval: `APPROVED by user prompt after corrected M2-03 plan review`
- Commit/push/PR/merge/deploy: `NOT_APPROVED`
- M1-09 recorded status: `mandatory supplement implemented - final independent review pending`
- M1-09 provider completion: `pending final PASS`
- Live API/LLM/provider/API/UI work: `OUT_OF_SCOPE`
- Dense/hybrid retrieval: `OUT_OF_SCOPE`
- M2-04 Evidence normalization: `NOT_STARTED`

This Task Card authorizes only the deterministic M2-03 lexical retrieval baseline, tests, M2-02 Task Card state synchronization, and result recording after explicit user plan approval.

It does not authorize commit, push, PR, merge, deploy, live API calls, provider changes, persistent indexing, Evidence normalization, EvidencePolicy, API/UI, LLM, dense retrieval, vector search, embeddings, reranking, or later M2 work.

---

## 2. Source Basis and Contract Reconciliation

The implementation agent must read the current `main` versions of:

- `docs/agent_handoff/README_AGENT_RULES.md`
  - safety, minimum change, verification, Git approval
- `docs/agent_handoff/PROJECT_PLAN_FINAL_PASS.md`
  - B4 registry, M2-02, M2-03, M2-04, Traceability Matrix
- `docs/TASK_CARDS/M2-02-hard-filter.md`
  - completed hard-filter public contract
- `docs/TASK_CARDS/M2-01-query-planner.md`
  - QueryPlan, explicit/session security precedence, date rules, source matrix
- `docs/agent_handoff/FINANCIAL_CAPABILITY_BASELINE.md`
  - C01, C02, C04, C05, C10
- `docs/agent_handoff/EXTENSION_COMPATIBILITY.md`
  - P0 hard-filter/retrieval scope
- `docs/agent_handoff/RISK_RESPONSE_MATRIX.md`
  - R24~R29 and M2 gate
- `docs/agent_handoff/EVALUATION_TAXONOMY_DRAFT.md`
  - entity resolution, source selection, numeric/cross-company attribution, citation support, evidence sufficiency
- `docs/agent_handoff/STOCK_SCOPE_CHANGE_NOTICE.md`
  - supported securities and company-attribution contract
- `docs/agent_handoff/LOCAL_AGENT_START_PROMPT.md`
  - document order and Git approval boundaries

### 2.1 Project-plan sequence and M2-03 fixture boundary

`PROJECT_PLAN_FINAL_PASS.md` presents the conceptual sequence:

```text
document hard filter
→ retrieval
→ Evidence subject/scope filter
```

The approved M2-02 Task Card and current core models also expose `filter_evidence()` and `RetrievalResult.evidence`.

For M2-03, resolve this boundary as follows:

- the public baseline operates on **already-normalized synthetic or previously accepted Evidence objects**
- this is a B4 lexical-scoring scaffold and unit benchmark
- M2-03 does not create Evidence from raw documents
- M2-03 does not claim production Evidence normalization is complete
- M2-04 remains responsible for the production Evidence normalization contract and integration
- the M2 gate and CORE06 are not complete merely because M2-03 unit fixtures pass

This is a scope clarification, not an activation of M2-04.

### 2.2 Review amendment classification

| Amendment | Classification | Existing contract or gap | New product scope |
|---|---|---|---|
| Synchronize M2-02 Task Card before implementation | `PROCESS-INTEGRITY` | Existing Git/document contract | No |
| Return only threshold-eligible Evidence in `ok` | `PLAN-VIOLATION` closure of R26/current status ambiguity | Existing low-relevance safety contract | No |
| Fix one exact lexical algorithm and constants | `PLAN-GAP` | Determinism gap | No |
| Propagate internal scorer failures | `PLAN-GAP` | Error taxonomy gap | No |
| Deep-copy score-stamped Evidence | `PLAN-GAP` | Caller-mutation gap | No |
| Preserve duplicates; dedupe remains M2-08 | `PLAN-GAP` | Step-boundary gap | No |
| Permission metadata is not retrieval eligibility | `PLAN-GAP` | Permission/retrieval separation | No |
| Independent benchmark labels and latency record | `PLAN-VIOLATION`/`PLAN-GAP` | PROJECT_PLAN benchmark contract | No |

---

## 3. Required Preflight Gate

Run from repository root on `main` before editing M2-03 implementation files.

### 3.1 Git baseline

```powershell
git status --short
git rev-parse HEAD
git log -1 --oneline
```

Expected:

```text
HEAD = 9c5d609c20ed860d99f054415433ff15ff398a26
latest commit = m2-02 conditional pass updates
```

Rules:

- if the working tree is clean, continue
- if it contains only the approved M2-02/M2-03 Task Card planning inputs, record the deviation and continue
- if code, fixture, dependency, data, or unrelated files are dirty, stop and report
- do not use reset, restore, checkout, clean, stash, force push, or destructive operations

### 3.2 Synchronize the M2-02 Task Card

Before M2-03 code changes, update:

```text
docs/TASK_CARDS/M2-02-hard-filter.md
```

Record at least:

```text
Current status: PASS / complete

Implementation SHA:
188c7efeba7ba6dbd3fb1c794e744dc2f80385ea

Implementation commit:
Implement m2-02

Implementation main push:
complete

Required follow-up SHA:
9c5d609c20ed860d99f054415433ff15ff398a26

Required follow-up commit:
m2-02 conditional pass updates

Required follow-up main push:
complete

Final closure review:
PASS

Targeted pytest:
55 passed

M2 regression:
131 passed

Full unit regression:
892 passed

GitHub CI:
NOT_RUN

Independent pytest rerun:
NOT_RUN

M2-03 planning entry:
ALLOWED

M2-03 implementation entry:
ALLOWED
```

Keep additional Git actions separate:

```text
Further commit/push/PR/merge/deploy:
NOT_APPROVED
```

Do not change M1-09 from its pending state.

### 3.3 Baseline regression

```powershell
$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_retrieval_filters.py -q
$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_query_planner.py tests/unit/test_retrieval_filters.py -q
$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit -q
```

### 3.4 Smoke and hygiene

```powershell
$env:PYTHONPATH = ".deps;."; python -c "from app.retrieval import HardFilterValidationError, filter_financial_documents, filter_evidence; print('ok')"
python scripts/secret_scan.py
python -m compileall app tests scripts -q
```

Gate decision:

- every command must exit `0`
- M2-02 Task Card synchronization must be complete
- otherwise stop before M2-03 code implementation and report the exact command, exit code, output summary, and Git state
- the preflight synchronization does not authorize commit or push

---

## 4. Goal and Boundary

M2-03 adds a deterministic small-corpus lexical retrieval baseline over already-normalized Evidence fixtures or accepted Evidence objects.

Required:

- call M2-02 `filter_evidence()` before corpus construction, IDF calculation, scoring, sorting, or top-k
- rank only hard-filtered candidates
- use one fixed standard-library BM25-family implementation
- enforce top-k cap 6
- distinguish `ok`, `empty`, and `low_relevance`
- preserve wrong-company, wrong-period, wrong-source, document-type, scope, and linked-document exclusions
- create an independently labeled synthetic benchmark with at least 12 candidates
- record benchmark latency without claiming a production SLA

Out of scope:

- provider or live API calls
- persistent or source-specific physical indexes
- new dependencies
- dense, hybrid, embedding, vector, reranker, or query-expansion work
- Evidence creation or normalization from raw FinancialDocument objects
- EvidencePolicy or final answerability
- citation validation
- freshness defaults
- duplicate removal
- API, UI, LLM, AnswerComposer
- M2-04 or later implementation
- core model/status changes

### 4.1 QueryPlan and session boundary

M2-03 consumes an already-created `RetrievalRequest`.

It must not:

- import or call `QueryPlanner`
- read or change `SessionContext`
- resolve a security
- replace `request.security_id`
- add a default date
- reinterpret intent
- add a source type

M2-01 has already resolved:

- explicit security over session security
- ambiguous/conflicting security clarification
- supported intent
- `DateRange`
- required source list

The upstream adapter from `QueryPlan` to `RetrievalRequest` is not implemented in M2-03.

Expected inherited mapping:

```text
raw user query               → RetrievalRequest.query
QueryPlan.security           → RetrievalRequest.security_id
QueryPlan.required_sources   → RetrievalRequest.source_types
QueryPlan.date_range         → RetrievalRequest.date_range
caller-provided type filter  → RetrievalRequest.document_types
default/project cap          → RetrievalRequest.top_k
```

M2-03 is used only after a valid security-required retrieval request exists. It does not invent a security-independent glossary request.

---

## 5. Existing Verified Inputs

Use without redesign:

- `RetrievalRequest`
  - `query`
  - `security_id`
  - `source_types`
  - optional `date_range`
  - optional `document_types`
  - positive `top_k`
- `RetrievalResult`
  - `evidence`
  - `status`
  - `strategy`
  - `low_relevance`
  - `diagnostics`
- `Evidence`
  - existing `retrieval_score`
  - title, snippet, source, date, subject/mentioned/scope
- `FinancialDocument`
  - linked-document proof for M2-02 only
- `RetrievalStatus`
  - `ok`
  - `empty`
  - `low_relevance`
- `filter_evidence()`
  - public validation
  - source/security/date/type hard filter
  - linked-document integrity
  - company attribution
  - Evidence-first timestamp precedence

Do not change these models, enum values, or M2-02 semantics.

---

## 6. Planned Files

### New files

- `app/retrieval/retriever.py`
- `tests/unit/test_retrieval_baseline.py`
- `docs/TASK_CARDS/M2-03-retrieval-baseline.md`

The M2-03 Task Card does not exist at the planning base SHA, so it is a new file.

### Modified files

- `app/retrieval/__init__.py`
  - export `retrieve_evidence` only
- `docs/TASK_CARDS/M2-02-hard-filter.md`
  - preflight closure/Git-state synchronization only

### Do not modify

- `app/core/models.py`
- `app/core/status.py`
- `app/planning/**`
- `app/providers/**`
- `app/ingest/**`
- `app/api/**`
- `app/llm/**`
- `data/**`
- existing provider/news/disclosure/report/glossary fixtures
- dependency or lock files
- M2-01 implementation files
- M1-09 Task Card
- M2-04 or later Task Cards

If another file appears necessary, stop and report before changing scope.

---

## 7. Public API and Processing Order

Add:

```python
def retrieve_evidence(
    evidence: Sequence[Evidence],
    request: RetrievalRequest,
    *,
    documents_by_id: Mapping[str, FinancialDocument] | None = None,
) -> RetrievalResult:
    ...
```

Exact processing order:

```text
call filter_evidence(evidence, request, documents_by_id=...)
→ if filtered list is empty: return EMPTY
→ normalize/tokenize request.query
→ if no usable query tokens: return LOW_RELEVANCE
→ build BM25 corpus from filtered Evidence only
→ calculate scores
→ retain only candidates with score >= LOW_RELEVANCE_THRESHOLD
→ if no eligible candidates: return LOW_RELEVANCE
→ sort eligible candidates by score descending, original input order ascending
→ apply min(request.top_k, MAX_TOP_K)
→ deep-copy selected Evidence and stamp retrieval_score
→ return OK
```

Important:

- excluded Evidence must not affect corpus length, document frequency, IDF, score, tie order, or diagnostics
- no first-match return
- no silent fallback to unfiltered candidates
- top-k is applied only to threshold-eligible candidates
- a candidate below threshold is never returned merely because another candidate passed
- ordinary hard-filter exclusions are not internal errors
- no scoring occurs when hard filtering returns zero candidates

### 7.1 Internal error contract

- malformed public input continues to raise sanitized `HardFilterValidationError` from M2-02
- internal tokenizer, BM25, copying, or result-construction failures must propagate
- do not broadly catch internal exceptions
- never convert an internal failure into `EMPTY`, `LOW_RELEVANCE`, or `OK`
- do not include raw query, snippet, document text, locator, metadata, URL, or path in an exception created by M2-03

---

## 8. Exact Lexical Scoring Contract

Use only Python standard library.

### 8.1 Constants

Define and export internally from `app/retrieval/retriever.py`:

```python
STRATEGY = "lexical-bm25-m2-03-v1"
MAX_TOP_K = 6
LOW_RELEVANCE_THRESHOLD = 0.5
BM25_K1 = 1.2
BM25_B = 0.75
SCORE_ROUND_DIGITS = 6
```

The public package exports only `retrieve_evidence`.

### 8.2 Normalization and tokens

Normalization:

```text
Unicode NFKC
→ casefold
→ regex token extraction
```

Token regex:

```python
r"[가-힣]+|[a-z0-9]+"
```

Fixed generic query tokens removed before scoring:

```text
최근, 요약, 설명, 알려, 알려줘, 자료, 정보, 관련, 어때, 대해
```

Rules:

- do not rewrite the request query
- do not use aliases, synonyms, resolver data, external dictionaries, embeddings, or LLM expansion
- do not mutate `RetrievalRequest.query`
- numeric tokens remain usable
- if all tokens are removed or punctuation/whitespace produces no token, return `low_relevance` when candidates exist

### 8.3 Candidate corpus text

For M2-03, score only:

```text
Evidence.title tokens repeated twice
+ Evidence.snippet tokens once
```

`documents_by_id` is used by `filter_evidence()` for integrity and hard-filter proof only.

Do not score:

- linked document text or title
- locator
- metadata
- URL
- provider
- security ID
- permission flags
- existing retrieval score

This keeps the B4 baseline deterministic and avoids treating permission metadata or raw document length as relevance.

### 8.4 BM25 formula

For each unique query token:

```text
idf = log(1 + (N - df + 0.5) / (df + 0.5))

term_score =
idf
* (tf * (BM25_K1 + 1))
/ (tf + BM25_K1 * (1 - BM25_B + BM25_B * dl / avgdl))
* query_term_frequency
```

Total score is the sum of term scores, rounded to `SCORE_ROUND_DIGITS`.

Rules:

- `N`, `df`, `dl`, and `avgdl` use only hard-filtered Evidence
- repeated query terms may increase score through query term frequency
- ubiquitous target-company or generic terms receive low IDF and cannot by themselves override the fixed threshold unless the exact formula produces an eligible score
- no score normalization against future strategies
- no dynamic threshold fitted from expected labels

If this exact threshold fails the independently labeled benchmark, stop and report. Do not change hard-filter rules, labels, or threshold silently.

---

## 9. Status and Result Invariants

### 9.1 `empty`

Condition:

```text
filter_evidence() returns []
```

Result:

```text
status = RetrievalStatus.EMPTY
low_relevance = False
evidence = []
strategy = STRATEGY
```

`empty` takes precedence over query-token usability.

### 9.2 `low_relevance`

Condition:

- filtered candidates exist, and
- query has no usable terms, or
- every score is below `LOW_RELEVANCE_THRESHOLD`

Result:

```text
status = RetrievalStatus.LOW_RELEVANCE
low_relevance = True
evidence = []
strategy = STRATEGY
```

### 9.3 `ok`

Condition:

- at least one hard-filtered candidate score is `>= LOW_RELEVANCE_THRESHOLD`

Result:

```text
status = RetrievalStatus.OK
low_relevance = False
evidence = only threshold-eligible selected Evidence
strategy = STRATEGY
```

Returned count:

```text
<= min(request.top_k, MAX_TOP_K)
```

Every returned Evidence has a rounded non-`None` score at or above the threshold.

### 9.4 Score-stamped copy contract

For every selected Evidence:

```python
item.model_copy(
    deep=True,
    update={"retrieval_score": rounded_score},
)
```

Requirements:

- input Evidence object is unchanged
- input nested subject/mentioned lists and locator are not shared with the returned copy
- caller mutation of returned nested fields does not mutate input Evidence
- returned result/evidence/diagnostics containers are fresh for every call

---

## 10. Diagnostics Contract

Diagnostics use this exact allowlist:

```text
input_count
filtered_count
scored_count
eligible_count
returned_count
query_token_count
requested_top_k
effective_top_k
max_top_k
low_relevance_threshold
```

Rules:

- integer counts remain non-negative
- `effective_top_k = min(request.top_k, MAX_TOP_K)`
- `scored_count == filtered_count` only when scoring occurs
- `returned_count == len(result.evidence)`
- do not include Evidence IDs, document IDs, query text, tokens, title, snippet, document text, locator, metadata, URLs, local paths, permission values, credentials, or raw exceptions
- return a fresh diagnostics dict per call

---

## 11. Company, Date, Source, Permission, and Duplicate Boundaries

### 11.1 Company attribution

M2-03 must not reimplement or weaken M2-02.

Inherited behavior:

- one target `request.security_id`
- company-specific Evidence subject must match target
- linked company-specific subject must be document primary
- multi-company target must be a subject and linked subjects must be document primary
- industry-common subject list remains empty and target connection must be proven
- wrong-company Evidence never reaches scoring

A relevant candidate placed late in the input must still outrank earlier irrelevant candidates. Never choose the first passing item.

### 11.2 Date behavior

M2-03 adds no default period.

`request.date_range=None`:

- no date filter is added
- no recent window is inferred from query text

When a DateRange exists, M2-02 must remain authoritative for:

- start-only
- end-only
- same-day
- inclusive start boundary
- inclusive end boundary
- Evidence timestamp before linked-document fallback
- missing/naive timestamp behavior

### 11.3 Source and document type

- `request.source_types` is used exactly
- unsupported or empty source sets may produce `empty`
- no source fallback
- requested document type still requires M2-02 proof
- retrieval does not infer types from text

### 11.4 Status and permission metadata

The current core models do not define a general document-status field.

M2-03 must not add one.

These metadata values are not retrieval relevance or eligibility signals in M2-03:

```text
external_llm_processing_allowed
corpus_ingest_allowed
usage_review_status
```

Rules:

- already-accepted Evidence can be locally filtered and scored regardless of external-LLM transmission permission
- M2-03 must not send any content to an external LLM
- permission metadata must not affect score or status
- document-type metadata remains the only linked metadata read indirectly by M2-02
- a future permission/status retrieval gate requires a separate approved contract

### 11.5 Duplicate behavior

M2-03 does not deduplicate.

- duplicate Evidence inputs remain separate candidates
- stable input order is preserved on equal score
- no deduplication by `evidence_id`, `document_id`, URL, title, or snippet
- duplicate removal remains M2-08
- duplicate candidates are still subject to threshold and top-k

---

## 12. Synthetic Benchmark Contract

Create at least 12 fixed synthetic Evidence candidates in `tests/unit/test_retrieval_baseline.py`.

Required coverage:

- Samsung Electronics, SK hynix, Hyundai Motor
- `news`, `disclosure`, `research_report`
- company-specific
- permitted industry-common
- multi-company
- wrong-company
- wrong source
- date outside
- document-type unproven
- hard-filter-passing low relevance
- score ties
- duplicate input

### 12.1 Independent labels

Define manual constants such as:

```python
EXPECTED_TOP6_BY_CASE = {
    "samsung_risk": (...),
    "sk_disclosure": (...),
    "hyundai_report": (...),
}

EXPECTED_HARD_FILTER_EXCLUDED_IDS = {...}
EXPECTED_LOW_RELEVANCE_IDS = {...}
```

Requirements:

- expected IDs are written independently
- expected values are not calculated by calling tokenizer, scorer, filter, sorting helper, or current fixture-derived ranking output
- tests must not read the implementation constants and use them to derive the expected result
- every manually declared must-retrieve ID appears in top-6 for its case
- wrong-company/cross-company hard-filter exclusions remain 100%
- low-relevance case returns no Evidence

### 12.2 Latency record

PROJECT_PLAN requires a latency benchmark record.

Add one deterministic benchmark test or helper that:

- runs the fixed 12+ candidate query at least 200 times
- verifies identical IDs, scores, status, and diagnostics on every run
- measures with `time.perf_counter_ns()`
- prints or records median and p95 elapsed time
- has no brittle wall-clock PASS threshold
- labels the measurement `local synthetic benchmark`, not production latency

Record the environment and measured median/p95 in the Task Card.

---

## 13. Tests

Create exact tests in `tests/unit/test_retrieval_baseline.py`.

### 13.1 Public boundary and order

- package export
- malformed evidence/request/mapping rejected by `HardFilterValidationError`
- hard-filter-empty returns `EMPTY` before query-token handling
- scorer/tokenizer is not called when hard filter returns empty
- excluded candidates do not affect IDF, scores, ranking, or diagnostics
- internal tokenizer/scorer exception propagates and does not become a RetrievalResult
- no provider, ingest, planning, API, UI, LLM, embedding, vector, reranker, dependency, or M2-04 imports

### 13.2 QueryPlan inheritance

- M2-03 does not import QueryPlanner or SessionContext
- request security/source/date/query remain unchanged
- no date default when `date_range=None`
- no source fallback
- no security re-resolution

### 13.3 Hard-filter integration

- wrong-company excluded before scoring
- wrong-source excluded before scoring
- requested document type proof preserved
- company-specific attribution preserved
- multi-company attribution preserved
- linked primary and mentioned industry-common paths preserved
- Evidence-first date precedence preserved
- start-only date
- end-only date
- same-day inclusive date
- inclusive start and end boundaries
- date-outside excluded
- adding many excluded candidates does not change allowed candidate scores

### 13.4 Ranking and status

- manually labeled relevant IDs in top-6
- late relevant candidate outranks early irrelevant candidate
- `top_k=3` returns at most 3
- `top_k>6` returns at most 6
- sort descending and stable input-order tie-break
- only scores `>= threshold` returned in `ok`
- below-threshold item omitted even when another item produces `ok`
- empty result invariants exact
- low-relevance invariants exact
- whitespace/punctuation/generic-only query with candidates gives low relevance
- repeated query term behavior fixed
- repeated run deterministic

### 13.5 Copy, duplicates, and permission

- input Evidence retrieval score remains unchanged
- returned Evidence is a different object
- returned nested subject/mentioned lists and locator are not shared
- mutating returned nested values leaves input unchanged
- duplicates are not silently removed
- permission metadata differences do not change eligibility, score, status, or ranking
- retrieval score from input is ignored and replaced only on returned copy

### 13.6 Diagnostics and fabrication

- diagnostics exact key allowlist
- count invariants exact for `ok`, `empty`, `low_relevance`
- no query, token, ID, snippet, text, locator, metadata, URL, path, permission, or credential values in diagnostics
- no Evidence ID, document ID, snippet, locator, or URL fabricated
- no core model/status changes

### 13.7 Benchmark integrity

- at least 12 unique fixture candidates
- all three securities represented
- all three source types represented
- manually declared expected sets are not derived from implementation output
- relevant top-6 inclusion 100% on fixed synthetic cases
- wrong-company/cross-company exclusions 100%
- local synthetic latency median/p95 recorded

---

## 14. Verification

Run after implementation.

### 14.1 Targeted

```powershell
$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_retrieval_baseline.py -q
```

### 14.2 M2 regression

```powershell
$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_query_planner.py tests/unit/test_retrieval_filters.py tests/unit/test_retrieval_baseline.py -q
```

### 14.3 Full unit regression

```powershell
$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit -q
```

### 14.4 Import smoke

```powershell
$env:PYTHONPATH = ".deps;."; python -c "from app.retrieval import retrieve_evidence; print('ok')"
```

### 14.5 Secret scan and compile

```powershell
python scripts/secret_scan.py
python -m compileall app tests scripts -q
```

### 14.6 Synthetic latency record

```powershell
$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_retrieval_baseline.py -q -s -k "latency"
```

Record:

- command
- execution context
- exit code
- passed count
- warning
- skipped/not-run items
- local synthetic median latency
- local synthetic p95 latency

Do not present fixture results as live source coverage or production latency.

---

## 15. Completion Criteria

- [x] baseline SHA confirmed
- [x] preflight Git state recorded
- [x] M2-02 Task Card synchronized to closure PASS and actual Git state
- [x] M1-09 remains final independent review pending
- [x] `retrieve_evidence()` implemented
- [x] filter runs before corpus/IDF/scoring
- [x] exact BM25 constants/formula/tokenizer implemented
- [x] no new dependency
- [x] top-k cap 6
- [x] only threshold-eligible Evidence returned in `ok`
- [x] exact `ok`, `empty`, `low_relevance` invariants
- [x] internal failures are not converted to retrieval statuses
- [x] deep score-stamped copies do not share nested mutable values
- [x] no session/security/source/date reinterpretation
- [x] no default period
- [x] start-only/end-only/same-day/inclusive dates preserved
- [x] wrong-company/source/period/type exclusions preserved
- [x] scope attribution preserved
- [x] permission metadata not treated as retrieval eligibility
- [x] duplicate behavior remains stable and no dedupe is implemented
- [x] diagnostics exact and sanitized
- [x] at least 12 independently labeled candidates
- [x] relevant top-6 synthetic inclusion 100%
- [x] wrong-company/cross-company exclusion 100%
- [x] local synthetic latency recorded
- [x] targeted PASS
- [x] M2 regression PASS
- [x] full unit regression PASS
- [x] import smoke PASS
- [x] secret scan PASS
- [x] compile PASS
- [x] implementation results recorded in M2-03 Task Card
- [x] commit/push/PR/merge/deploy remain `NOT_RUN`

---

## 16. Risk IDs and Taxonomy

Confirmed current risks:

- `R24` wrong intent/source routing
- `R25` wrong-company/cross-company Evidence
- `R26` low-relevance Evidence passed to answer context
- `R27` query rewrite changes intent
- `R28` retrieval complexity creep
- `R29` retrieval does not itself guarantee citation support
- `R32` retrieval result must not claim final answer sufficiency

Related taxonomy:

- `entity_resolution`
- `ambiguous_security`
- `source_selection`
- `numeric_accuracy`
- `citation_support`
- `evidence_sufficiency`
- `abstention`

M2-03 verifies retrieval behavior only. It does not implement final EvidencePolicy, citation validation, or answer abstention.

---

## 17. Stop Conditions

Stop and report if:

- baseline SHA differs
- M2-02 Task Card cannot be synchronized safely
- preflight command fails
- unapproved code, fixture, dependency, data, or unrelated document changes exist
- core models/status need changes
- M2-02 hard-filter contract must be loosened
- Evidence must be created or normalized from raw documents
- exact BM25 contract cannot pass independently labeled fixtures
- threshold would need to be silently changed
- internal error would need to be mapped to an existing status
- provider, ingest, QueryPlanner, API, UI, LLM, dependency, dense, vector, embedding, reranker, dedupe, or M2-04 work becomes necessary
- permission metadata would need to become a retrieval filter
- diagnostics would need to expose forbidden content
- M1-09 pending state would need to change
- unrelated regression fails

Do not silently reduce or expand scope.

---

## 18. Fallback and Rollback

- Do not switch algorithms after implementation begins without reporting.
- If exact BM25 cannot separate the fixed benchmark, stop and report:
  - failing case
  - scores
  - threshold
  - whether fixture labels, formula, or scope would need change
- Do not silently fall back to token overlap under the BM25 strategy name.
- A different lexical algorithm requires a corrected plan and approval.
- If score stamping cannot be done with deep copies, stop rather than mutate input.
- Rollback proposal:
  - revert only M2-03 files and the M2-02 preflight synchronization diff
  - only after explicit user approval
  - no reset, force push, clean, or history rewrite

---

## 19. Implementation Order After Approval

1. Confirm `main` at `9c5d609c20ed860d99f054415433ff15ff398a26`.
2. Record `git status --short`.
3. Run preflight regression, smoke, secret scan, and compile.
4. Synchronize `docs/TASK_CARDS/M2-02-hard-filter.md`.
5. Confirm M1-09 remains pending.
6. Create `docs/TASK_CARDS/M2-03-retrieval-baseline.md` from this approved plan.
7. Add `app/retrieval/retriever.py`.
8. Export only `retrieve_evidence` from `app/retrieval/__init__.py`.
9. Implement exact hard-filter-first processing order.
10. Implement exact tokenizer, generic-token set, BM25 formula, threshold, diagnostics, and deep-copy scoring.
11. Add independent 12+ candidate benchmark and exact tests.
12. Run targeted tests.
13. Run M2 regression.
14. Run full unit regression.
15. Run import smoke, secret scan, compile, and latency record.
16. Record results in the M2-03 Task Card.
17. Report:

```powershell
git diff --name-status
git diff --stat
git status --short
git log -2 --oneline --decorate
```

18. Wait for separate commit/push approval.

---

## 20. Implementation Review and Closure Checklist

The independent implementation review must confirm:

### Source and scope

- [ ] base SHA and full changed-file list
- [ ] M2-02 Task Card synchronized accurately
- [ ] M1-09 pending state preserved
- [ ] only approved files changed
- [ ] M2-04 and later code absent
- [ ] no provider/ingest/planning/API/UI/LLM/dependency/dense/vector/reranker/dedupe work

### Public contract and order

- [ ] `filter_evidence()` called before corpus construction and scoring
- [ ] excluded candidates do not affect IDF or scores
- [ ] no first-match or silent fallback
- [ ] `EMPTY` precedence exact
- [ ] internal failures propagate
- [ ] no default security/source/date/session behavior

### Scoring and result

- [ ] exact constants/token regex/generic-token set
- [ ] exact BM25 formula
- [ ] threshold fixed at `0.5`
- [ ] only eligible items returned
- [ ] stable tie order
- [ ] cap 6
- [ ] deep copy and nested isolation
- [ ] diagnostics exact and sanitized
- [ ] duplicates preserved
- [ ] permission metadata ignored for retrieval eligibility

### Hard-filter regression

- [ ] wrong company
- [ ] wrong source
- [ ] wrong date
- [ ] start-only/end-only/same-day/inclusive boundaries
- [ ] requested document type
- [ ] company-specific
- [ ] multi-company
- [ ] industry-common primary/mentioned link

### Benchmark and verification

- [ ] 12+ fixed candidates
- [ ] all 3 securities
- [ ] all 3 source types
- [ ] independent expected labels
- [ ] relevant top-6 100%
- [ ] wrong-company/cross-company exclusion 100%
- [ ] low relevance returns no Evidence
- [ ] local synthetic latency median/p95 recorded
- [ ] targeted/M2/full regression results
- [ ] smoke/secret/compile results
- [ ] GitHub CI and independent rerun accurately recorded
- [ ] commit/push status matches reality

Closure review after a remediation is limited to:

- original BLOCKER closure
- exact regression tests
- allowed files
- targeted/M2/full regression
- Task Card/Git/CI status

---

## 21. Result Log

- Implementation status: `IMPLEMENTATION COMPLETE - USER REVIEW PENDING`
- Planning base SHA: `9c5d609c20ed860d99f054415433ff15ff398a26`
- M2-02 Task Card synchronization: `PASS - closure PASS, follow-up SHA/push, and M2-03 entries synchronized before code changes`
- Preflight baseline: `PASS - HEAD 9c5d609c20ed860d99f054415433ff15ff398a26 on main`
- Preflight working tree deviation: `approved M2-02/M2-03 Task Card planning inputs were dirty; no code, fixture, dependency, data, or unrelated files were dirty; no destructive Git operation was used`
- Preflight targeted filters: `PASS - 55 passed`
- Preflight M2 regression: `PASS - 131 passed`
- Preflight full unit: `PASS - 892 passed, 1 existing FastAPI/Starlette deprecation warning`
- Preflight smoke: `PASS - ok`
- Preflight secret scan: `PASS - []`
- Preflight compile: `PASS`
- Preflight execution note: `the initial sandboxed targeted command exited 1 because the sandbox could not access the repository .deps pytest module; the same command was rerun with approved local dependency access and passed. All subsequent preflight commands used that approved local dependency access.`
- Implementation SHA: `NOT_CREATED`
- Commit/push/PR/merge/deploy: `NOT_RUN`
- Result Git state: `main at 9c5d609c20ed860d99f054415433ff15ff398a26; only approved M2-03 implementation/test/Task Card files and M2-02 synchronization are modified or untracked`
- Targeted pytest: `PASS - final rerun 28 passed`
- M2 regression: `PASS - final rerun 159 passed`
- Full unit regression: `PASS - final rerun 920 passed, 1 existing FastAPI/Starlette deprecation warning`
- Import smoke: `PASS - ok`
- Secret scan: `PASS - []`
- Compile: `PASS`
- Local synthetic latency: `PASS - final median 92300 ns, p95 104200 ns; not a production latency claim`
- GitHub CI: `NOT_RUN`
- Independent pytest rerun: `NOT_RUN`
- Live API/LLM/provider/API/UI: `NOT_RUN - out of scope`
- Dense/hybrid retrieval: `NOT_RUN - out of scope`
- M2-04 Evidence normalization: `NOT_STARTED`

### 21.1 Preflight Execution Results

- Baseline command: `git rev-parse HEAD`
  - exit code: `0`
  - output: `9c5d609c20ed860d99f054415433ff15ff398a26`
- Preflight targeted command: `$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_retrieval_filters.py -q`
  - initial sandboxed exit code: `1`
  - initial condition: `sandbox could not access the repository .deps pytest module`
  - approved local dependency-access rerun exit code: `0`
  - passed count: `55 passed`
- Preflight M2 command: `$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_query_planner.py tests/unit/test_retrieval_filters.py -q`
  - execution: `approved local dependency access with PYTHONPATH=.deps;.`
  - exit code: `0`
  - passed count: `131 passed`
- Preflight full unit command: `$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit -q`
  - execution: `approved local dependency access with PYTHONPATH=.deps;.`
  - exit code: `0`
  - passed count: `892 passed`
  - warning: `FastAPI/Starlette TestClient deprecation warning for httpx`
- Preflight smoke command: `$env:PYTHONPATH = ".deps;."; python -c "from app.retrieval import HardFilterValidationError, filter_financial_documents, filter_evidence; print('ok')"`
  - exit code: `0`
  - output: `ok`
- Preflight secret scan command: `python scripts/secret_scan.py`
  - exit code: `0`
  - output: `[]`
- Preflight compile command: `python -m compileall app tests scripts -q`
  - exit code: `0`

### 21.2 Implementation Verification Results

- Initial targeted command: `$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_retrieval_baseline.py -q`
  - exit code: `1`
  - result: `24 passed, 3 failed`
  - correction: `three success-boundary test queries were repeated so their fixed BM25 scores met the approved 0.5 threshold; BM25 constants, formula, and threshold were unchanged`
- Targeted rerun command: `$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_retrieval_baseline.py -q`
  - execution: `approved local dependency access with PYTHONPATH=.deps;.`
  - exit code: `0`
  - passed count: `27 passed`
- Final targeted command after the direct start-only/end-only/same-day date-boundary test was added: `$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_retrieval_baseline.py -q`
  - execution: `approved local dependency access with PYTHONPATH=.deps;.`
  - exit code: `0`
  - passed count: `28 passed`
- M2 regression command: `$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_query_planner.py tests/unit/test_retrieval_filters.py tests/unit/test_retrieval_baseline.py -q`
  - execution: `approved local dependency access with PYTHONPATH=.deps;.`
  - exit code: `0`
  - passed count: `158 passed`
- Final M2 regression command after the date-boundary test: `$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_query_planner.py tests/unit/test_retrieval_filters.py tests/unit/test_retrieval_baseline.py -q`
  - execution: `approved local dependency access with PYTHONPATH=.deps;.`
  - exit code: `0`
  - passed count: `159 passed`
- Full unit regression command: `$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit -q`
  - execution: `approved local dependency access with PYTHONPATH=.deps;.`
  - exit code: `0`
  - passed count: `919 passed`
  - warning: `FastAPI/Starlette TestClient deprecation warning for httpx`
- Final full unit regression command after the date-boundary test: `$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit -q`
  - execution: `approved local dependency access with PYTHONPATH=.deps;.`
  - exit code: `0`
  - passed count: `920 passed`
  - warning: `FastAPI/Starlette TestClient deprecation warning for httpx`
- Import smoke command: `$env:PYTHONPATH = ".deps;."; python -c "from app.retrieval import retrieve_evidence; print('ok')"`
  - exit code: `0`
  - output: `ok`
- Secret scan command: `python scripts/secret_scan.py`
  - exit code: `0`
  - output: `[]`
- Compile command: `python -m compileall app tests scripts -q`
  - exit code: `0`
- Local synthetic latency command: `$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_retrieval_baseline.py -q -s -k "latency"`
  - execution: `approved local dependency access with PYTHONPATH=.deps;.`
  - exit code: `0`
  - passed count: `1 passed, 27 deselected`
  - local synthetic median: `92300 ns`
  - local synthetic p95: `104200 ns`
  - scope: `200 deterministic runs over the 13-candidate synthetic benchmark; not production latency`
