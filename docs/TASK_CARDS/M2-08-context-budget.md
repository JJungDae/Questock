# TASK CARD - M2-08 Token and Context Budget

## 1. Status and Approval

- Task bundle: `B5: M2-04~08`
- Step: `M2-08 Token and Context Budget`
- Priority: `P0`
- Planning date: `2026-07-24`
- Planning branch: `main`
- Planning base SHA: `0711d62cd62f86d71c4a712b6205f7643f5f9209`
- Planning base commit: `m2-07 conditional pass updates`
- Planning base main push: `complete`
- GitHub latest main SHA at review:
  `03d2f982ddada67c767a02fad380b85a2980a8a3`
- M2-07 first implementation SHA:
  `7e952d10eb29eebf29f2c0ac657a484914b53ae7`
- M2-07 supplement SHA:
  `0711d62cd62f86d71c4a712b6205f7643f5f9209`
- M2-07 independent final closure review: `PASS`
- M2-07 code status: `PASS / complete`
- M2-07 Task Card closure synchronization:
  `COMPLETE - included in M2-08 implementation commit and main push`
- M2-08 first plan review:
  `CONDITIONAL PASS - corrected final plan supplied`
- M2-08 corrected final plan approval:
  `APPROVED by user on 2026-07-24`
- M2-08 preflight: `PASS`
- M2-08 implementation SHA:
  `03d2f982ddada67c767a02fad380b85a2980a8a3`
- M2-08 implementation commit: `Implement m2-08`
- M2-08 implementation main push: `complete`
- M2-08 independent implementation review: `PASS`
- M2-08 current status: `PASS / complete`
- M2 integrated review:
  `ALLOWED - required before M3 implementation`
- M2-09 implementation:
  `NOT_ALLOWED without separate A15-M gate`
- M3 implementation:
  `BLOCKED pending M2 integrated review PASS`
- M1-09:
  `mandatory supplement implemented - final independent review pending`
- M2-08 status synchronization approval:
  `APPROVED by user on 2026-07-24`
- M2-08 status synchronization SHA:
  `db542bbc1bd356ef967ef49d907f7cac684a2576`
- M2-08 status synchronization commit: `Sync m2-08 pass status`
- M2-08 status synchronization main push: `complete`
- Further PR/merge/deploy: `NOT_APPROVED`

The corrected final plan, isolated implementation, verification, main push, and
independent implementation review are complete. Dependency changes, external
calls, actual logging integration, PR, merge, and deploy remain unapproved.

## 2. Goal

Add a deterministic, in-memory final Evidence selection boundary after
`EvidencePolicy` and before future M3 claim generation.

The boundary will:

- remove exact duplicate Evidence occurrences
- preserve retrieval/policy priority order
- keep at most 3 Evidence items per source
- keep at most 6 Evidence items in total
- enforce both:
  - an approximate 3,000-token context ceiling
  - the project tokenizer-unavailable fallback of 4,500 serialized characters
- remove lower-priority Evidence first when a count or context limit is exceeded
- return safe, count-only diagnostics that are ready for later request logging
- provide a separate request-scoped LLM-call counter capped at 2 calls
- deep-copy all returned Evidence

M2-08 will not:

- rank, normalize, hard-filter, or rescore Evidence
- change `EvidenceDecision` status or source-sufficiency fields
- generate claims or answers
- validate citations
- call an LLM
- emit application logs
- decide permission or external-LLM eligibility
- implement production orchestration

Actual application log emission, permission filtering, prompt construction, and
LLM integration remain M3/M4 work.

## 3. Verified Current Contracts

### 3.1 Existing runtime order

The final runtime order remains:

```text
M2-04 normalize
-> M2-02 hard filter
-> M2-05 freshness
-> M2-03 retrieval
-> M2-06 EvidencePolicy
-> M2-08 final Evidence selection
-> M3 claim generation
-> M2-07 citation validation
-> M3 answer validation/rendering
```

M2-08 consumes the ordered `decision.evidence` sequence. It does not reconstruct
or re-evaluate the `EvidenceDecision`.

### 3.2 Existing code that must be reused

| Contract | Verified file | Current behavior used by M2-08 |
|---|---|---|
| `Evidence` | `app/core/models.py` | Pydantic model and deep-copy boundary |
| retrieval cap | `app/retrieval/retriever.py` | `MAX_TOP_K = 6` |
| retrieval order | `app/retrieval/retriever.py` | descending BM25 score, stable input tie order |
| retrieval eligibility | `app/retrieval/retriever.py` | only score at or above current threshold |
| policy output | `app/evidence/policy.py` | immutable ordered `EvidenceDecision.evidence` |
| citation input | `app/evidence/citations.py` | accepts final selected Evidence directly |
| citation occurrence rule | `app/evidence/citations.py` | conflicting duplicate IDs fail closed |

### 3.3 Project-plan limits

The M2-08 initial limits are:

```text
retrieval top-k: 6
per-source Evidence: 3
final Evidence: 6
approximate context: 3,000 tokens
LLM calls per request: 2
```

No core model or status enum change is required.

### 3.4 M2-07 join contract

The actual current M2-07 public API is:

```python
validate_citations(
    claims: Sequence[CitationClaim],
    plan: QueryPlan,
    selected_evidence: Sequence[Evidence],
) -> CitationValidationResult
```

Future composition must therefore use this exact argument order:

```python
budget_result = select_evidence_context(decision.evidence)
claims = claim_generator(budget_result.evidence)
citations = validate_citations(claims, plan, budget_result.evidence)
```

A claim may never cite Evidence removed by M2-08.

This is a future integration example only. M2-08 does not implement
`claim_generator`, M3, or production wiring.

### 3.5 Review findings incorporated

| Finding | Classification | Source and Section | Corrected contract |
|---|---|---|---|
| M2-07 function arguments were reversed | `PLAN-VIOLATION` | `app/evidence/citations.py` public API; M2-07 Task Card §6 | use `(claims, plan, selected_evidence)` |
| tokenizer-unavailable 4,500-character fallback was omitted | `PLAN-VIOLATION` | `PROJECT_PLAN_FINAL_PASS.md` §6.5 | enforce both approximate token and 4,500-character Evidence projection caps |
| diagnostics did not define exact counter equations or token meaning | `PLAN-GAP` | M2-08 output contract | define stage counts, total-token meaning, and `budget_exhausted` exactly |
| duplicate fingerprint serialization was underspecified | `PLAN-GAP` | M2-08 dedupe contract; R25 Critical attribution | canonical JSON fingerprint; attribution remains part of identity |
| `max_llm_calls` existed in two independent limit objects | `PLAN-GAP` | M2-08 proposed API | remove it from `ContextBudgetLimits`; validate it only in `LLMCallBudget` |
| previous Task Card is stale after the pushed supplement | `PROCESS-INTEGRITY` | latest M2-07 Task Card and Git main | synchronize M2-07 closure before code changes |
| M2 completion must be followed by integrated review | `PLAN-GAP` | Project M2 Gate and project review workflow | M3 implementation remains blocked until M2 integrated review PASS |

All corrections remain inside M2-08's step-local module, tests, and Task Card,
plus the already authorized M2-07 Task Card status synchronization. No completed
Task code, core/shared API, dependency, provider, API, UI, or LLM implementation
is changed.

## 4. Scope

### 4.1 Files allowed

- `app/evidence/budget.py` - new
- `tests/unit/test_context_budget.py` - new
- `docs/TASK_CARDS/M2-08-context-budget.md`
- `docs/TASK_CARDS/M2-07-citation-validation.md` only for the already approved
  final closure synchronization if still stale at implementation preflight

### 4.2 Files and areas not allowed

- `app/core/models.py`
- `app/core/status.py`
- existing retrieval, filter, freshness, policy, normalizer, and citation code
- planner, resolver, provider, ingest, config, API, UI, and LLM code
- M2-09 market-session logic
- M3 claim generation, answer composition, or answer validation
- dense, vector, hybrid, reranker, query rewrite, or score changes
- semantic/news/event deduplication
- dependency, lock, environment, fixture-data, or workflow files
- actual logging integration

If another file is required, stop and report before expanding scope.

---

## 5. Proposed Public API

Create only `app/evidence/budget.py`.

```python
MAX_EVIDENCE_COUNT = 6
MAX_EVIDENCE_PER_SOURCE = 3
MAX_CONTEXT_TOKENS = 3000
MAX_CONTEXT_CHARS = 4500
MAX_LLM_CALLS = 2
TOKEN_ESTIMATOR_VERSION = "utf8-bytes-div-3-v1"


class ContextBudgetValidationError(ValueError):
    ...


class LLMCallBudgetExceededError(ContextBudgetValidationError):
    ...


@dataclass(frozen=True)
class ContextBudgetLimits:
    max_evidence_count: int = MAX_EVIDENCE_COUNT
    max_evidence_per_source: int = MAX_EVIDENCE_PER_SOURCE
    max_context_tokens: int = MAX_CONTEXT_TOKENS
    max_context_chars: int = MAX_CONTEXT_CHARS


@dataclass(frozen=True)
class ContextBudgetDiagnostics:
    input_count: int
    unique_count: int
    duplicate_drop_count: int
    source_cap_drop_count: int
    count_cap_drop_count: int
    context_drop_count: int
    selected_count: int
    estimated_context_tokens: int
    estimated_evidence_chars: int
    reserved_tokens: int
    max_evidence_count: int
    max_evidence_per_source: int
    max_context_tokens: int
    max_context_chars: int
    estimator_version: str
    budget_exhausted: bool


@dataclass(frozen=True)
class ContextBudgetResult:
    evidence: tuple[Evidence, ...]
    diagnostics: ContextBudgetDiagnostics


@dataclass(frozen=True)
class LLMCallBudgetSnapshot:
    calls_used: int
    calls_remaining: int
    max_calls: int


class LLMCallBudget:
    def __init__(self, max_calls: int = MAX_LLM_CALLS) -> None:
        ...

    def reserve_call(self) -> int:
        ...

    def snapshot(self) -> LLMCallBudgetSnapshot:
        ...


def select_evidence_context(
    evidence: Sequence[Evidence],
    *,
    limits: ContextBudgetLimits = ContextBudgetLimits(),
    reserved_tokens: int = 0,
) -> ContextBudgetResult:
    ...
```

Public boundary rules:

- `evidence` accepts only a materialized `list` or `tuple`
- strings, bytes, bytearray, mappings, sets, generators, and custom sequences
  are rejected
- `ContextBudgetLimits.max_llm_calls` does not exist
- context selection never constructs or mutates an `LLMCallBudget`
- the future caller creates one request-scoped call budget separately
- no symbol is added to `app/evidence/__init__.py`
- direct module imports are used

## 6. Input Validation

### 6.1 Context limits

Every numeric value must be an exact `int`; `bool` is rejected.

- `1 <= max_evidence_count <= 6`
- `1 <= max_evidence_per_source <= 3`
- `1 <= max_context_tokens <= 3000`
- `1 <= max_context_chars <= 4500`
- `0 <= reserved_tokens <= max_context_tokens`

`ContextBudgetLimits` must be an actual instance. Its fields are revalidated
inside `select_evidence_context()` so directly constructed malformed values fail
closed.

Malformed public values raise a fixed sanitized
`ContextBudgetValidationError`. Raw values and nested exception strings are not
included in messages.

### 6.2 LLM call limit

`LLMCallBudget(max_calls=...)` validates its own independent limit:

- exact integer, not bool
- `1 <= max_calls <= 2`

There is one source of truth per call tracker. Context selection limits do not
contain a second `max_llm_calls` value.

### 6.3 Evidence

Each occurrence must:

- be an actual `Evidence`
- survive strict model reconstruction
- have nonblank `evidence_id`, `document_id`, `source_type`, `title`, and
  `snippet`
- use one current source:
  `news`, `disclosure`, `research_report`, or `glossary`
- have a finite, non-boolean retrieval score at or above the existing M2-03
  threshold

The boundary does not repeat company, period, provider, freshness, permission,
or source-sufficiency decisions. Those remain earlier-stage or future
orchestration responsibilities.

Direct malformed/model-constructed input must fail with a typed sanitized
M2-08 error, never a raw `TypeError`, `KeyError`, Pydantic message, secret,
local path, URL, or caller value.

## 7. Exact Duplicate Contract

### 7.1 Repeated Evidence ID consistency

Before content deduplication, build a canonical full-payload representation for
each occurrence.

Canonical full payload:

- comes from strict `Evidence.model_validate(...)`
- uses `model_dump(mode="json")`
- is serialized with:
  - `sort_keys=True`
  - `ensure_ascii=False`
  - compact separators
  - `allow_nan=False`
- preserves list order
- ignores mapping insertion order

Rules:

- repeated `evidence_id` with an identical full payload is valid
- repeated `evidence_id` with any difference, including retrieval score,
  locator, attribution, or snippet, raises:

```text
ContextBudgetValidationError("evidence occurrences are inconsistent")
```

### 7.2 Exact-content fingerprint

M2-08 removes only exact canonical content duplicates.

Build the content fingerprint from the canonical JSON payload after removing
only:

- `evidence_id`
- `retrieval_score`

The fingerprint therefore still includes:

- `document_id`
- `source_type`
- `title`
- `source_url`
- `published_at`
- `subject_security_ids`
- `mentioned_security_ids`
- `scope`
- `snippet`
- the complete locator

Use the canonical serialized string or its deterministic cryptographic digest.
Do not use Python's process-randomized `hash()`.

Consequences:

- identical content under different Evidence IDs collapses to the first
  occurrence
- retrieval-score differences alone do not preserve a later content duplicate
- the retained item keeps the first occurrence's original Evidence ID and score
- different company attribution or scope is never deduplicated
- equivalent locator mappings with different key insertion order are exact
  duplicates

### 7.3 Explicit non-goals

These are not exact duplicates:

- the same document with different snippets
- the same text with different subject/mentioned security attribution
- different documents with similar titles
- different URLs covering the same event
- republished or semantically similar news
- Evidence with merely similar text

News/event/semantic deduplication remains later scope.

### 7.4 Order

The first exact occurrence wins. Relative order of all surviving items never
changes.

## 8. Selection and Budget Algorithm

Apply these stages in this exact order:

```text
public input validation and canonical deep copy
→ repeated-ID consistency validation
→ exact-content deduplication
→ per-source cap
→ final count cap
→ dual context cap
→ final deep-copy and invariant audit
```

The input order is the only priority order. M2-08 does not sort by score,
freshness, date, source, title, permission, or Evidence ID.

### 8.1 Per-source and count caps

- keep the earliest `max_evidence_per_source` items for each source
- then keep the earliest `max_evidence_count` items overall
- every dropped occurrence belongs to exactly one stage
- no item is counted twice in diagnostics

### 8.2 Context stage

Calculate the canonical selected Evidence projection described in Section 9.

The selected sequence fits only when both are true:

```text
reserved_tokens + estimated_evidence_tokens <= max_context_tokens
estimated_evidence_chars <= max_context_chars
```

If either limit is exceeded:

1. remove the last item
2. recompute both estimates
3. repeat until both fit or no Evidence remains

Do not truncate or rewrite any title, snippet, ID, URL, locator, or Evidence
object.

### 8.3 Empty and exhausted behavior

An empty valid input returns an empty result with:

- all counts `0`
- `estimated_context_tokens == reserved_tokens`
- `estimated_evidence_chars == 0`
- `budget_exhausted == False`

For a nonempty sequence reaching the context stage:

- if one or more Evidence items remain, `budget_exhausted=False`
- if every post-count-cap Evidence item is removed by the context stage,
  return an empty Evidence tuple and set `budget_exhausted=True`

M2-08 does not change the upstream EvidenceDecision status. Future M3
orchestration must abstain when an upstream nonempty decision produces an empty
budget result.

## 9. Context Estimate Contract

### 9.1 Exact Evidence projection

For every selected Evidence occurrence, serialize one mapping with this exact
field order:

```text
evidence_id
source_type
title
published_at
subject_security_ids
mentioned_security_ids
scope
snippet
```

Values:

- `published_at` is `None` or the canonical datetime `isoformat()` string
- security-ID lists preserve their existing order
- Evidence occurrence order is preserved

The projection excludes:

- source URL and locator
- retrieval score
- provider metadata
- permission metadata
- original document text

URL/locator remain code-side citation data. Exclusion from the projection does
not authorize external transmission of any field.

### 9.2 Canonical serialization

Serialize the projection as compact JSON using:

- UTF-8
- `ensure_ascii=False`
- stable field insertion order
- compact separators
- `allow_nan=False`

The exact serialized string is used for both token and character estimates.

### 9.3 Approximate token estimate

```text
estimated_evidence_tokens =
    0 for an empty projection
    otherwise ceil(UTF-8 byte length / 3)

estimated_context_tokens =
    reserved_tokens + estimated_evidence_tokens
```

`ContextBudgetDiagnostics.estimated_context_tokens` always means the total
approximate context after adding the caller's reservation. It never means the
Evidence-only estimate.

This is an explicit dependency-free approximation, not a Gemini/LiteLLM
tokenizer claim.

### 9.4 Tokenizer-unavailable character fallback

The project fallback is:

```text
max_context_chars = 4500
```

Define:

```text
estimated_evidence_chars = len(canonical_projection_json)
```

The Evidence projection must satisfy both the token estimate and character
fallback. The character count applies only to the Evidence projection because
the current API receives only token reservations for future query/system/schema
content.

Until M3 constructs the complete prompt, M2-08 proves only:

- Evidence projection approximate-token compliance
- Evidence projection 4,500-character fallback compliance

It does not prove actual total prompt tokens or characters.

## 10. LLM Call Cap Contract

`LLMCallBudget` is a separate request-scoped in-memory counter.

- constructor default maximum: `2`
- constructor accepts exact integers `1` or `2`; bool is rejected
- first reservation returns `1`
- second reservation returns `2`
- the next reservation raises:
  `LLMCallBudgetExceededError("LLM call budget exceeded")`
- a rejected reservation does not increment the counter
- `snapshot()` returns a fresh frozen snapshot
- snapshots contain counts only
- independent instances share no state
- no prompt, response, exception, credential, Evidence, or user text is stored
- no logger, network, LiteLLM, Gemini, retry, or fallback code is added

`ContextBudgetLimits` does not carry an independent LLM call limit.

Actual LLM orchestration and request-log emission remain M3/M4 work. M2-08
completion proves only the cap primitive and log-ready count snapshot.

## 11. Output and Diagnostic Invariants

Every successful `ContextBudgetResult` must satisfy:

- Evidence is a tuple of deep copies
- caller input and nested locators are unchanged
- output count is at most the configured count cap
- each source count is at most the configured per-source cap
- output contains no exact-content duplicate
- output is an ordered subsequence of canonical input
- `estimated_context_tokens <= max_context_tokens`
- `estimated_evidence_chars <= max_context_chars`
- repeated calls with equal input return equal values
- mutating one returned nested locator cannot affect the caller or another result

### 11.1 Exact diagnostic equations

Let:

- `input_count` = canonical input occurrence count
- `unique_count` = count after exact-content deduplication
- `after_source_cap_count` = private stage count after source caps
- `after_count_cap_count` = private stage count after total count cap
- `selected_count` = final output count

Diagnostics must satisfy:

```text
duplicate_drop_count = input_count - unique_count
source_cap_drop_count = unique_count - after_source_cap_count
count_cap_drop_count = after_source_cap_count - after_count_cap_count
context_drop_count = after_count_cap_count - selected_count

input_count
= duplicate_drop_count
+ source_cap_drop_count
+ count_cap_drop_count
+ context_drop_count
+ selected_count
```

Additional invariants:

- all counts are exact nonnegative integers
- `selected_count == len(result.evidence)`
- `estimated_context_tokens == reserved_tokens + token_estimate(result.evidence)`
- `estimated_evidence_chars == char_estimate(result.evidence)`
- diagnostics repeat the validated effective limits
- `estimator_version == TOKEN_ESTIMATOR_VERSION`
- `budget_exhausted` follows Section 8.3 exactly

Final audit failure raises:

```text
ContextBudgetValidationError("context budget output is invalid")
```

No diagnostic or snapshot includes Evidence IDs, titles, snippets, URLs,
locator values, queries, credentials, paths, raw exceptions, or permission
metadata.

## 12. Required Tests

Use literal expected limits, formulas, field order, and counts rather than
deriving expected values from implementation constants when testing contract
drift.

### 12.1 Public boundary

- list and tuple accepted
- empty sequence returns deterministic empty result
- string, bytes, bytearray, mapping, set, generator, and custom sequence rejected
- non-Evidence item rejected
- direct malformed/model-constructed Evidence rejected with typed sanitized
  error
- blank required values and unsupported source rejected
- missing, boolean, NaN, infinity, negative, or below-threshold score rejected
- invalid ContextBudgetLimits type and every field boundary rejected
- invalid reserved-token type/range rejected
- raw caller values do not appear in exceptions

### 12.2 Duplicate identity and fingerprint

- identical occurrence with the same ID keeps the first
- conflicting payload with the same ID fails closed
- same ID with a different retrieval score fails closed
- exact content under different IDs keeps the first
- retrieval-score difference under different IDs does not create a new item
- equivalent locator mappings with different insertion order deduplicate
- same document with different snippets remains distinct
- same apparent content with different subject IDs remains distinct
- same apparent content with different scope remains distinct
- similar title, same URL, and same event are not semantically deduplicated
- first-occurrence ID, score, and order are retained
- no Python randomized hash affects output

### 12.3 Source and count caps

- fourth item from one source is dropped
- all four sources are capped independently
- mixed sources preserve input order
- source cap runs before final count cap
- final count never exceeds the configured limit
- lower-priority tail is removed first
- every occurrence is attributed to exactly one diagnostic drop stage

### 12.4 Token and character context

- empty Evidence projection token estimate is zero
- empty input with nonzero reservation reports only reserved tokens
- ASCII and Korean estimates match exact UTF-8 byte/3 formula
- projection field order and `published_at` representation are literal
- exact token boundary is included
- one-token-over boundary removes the lowest-priority item
- exact 4,500-character boundary is included
- one-character-over fallback removes the lowest-priority item
- whichever of token/character caps is stricter controls selection
- multiple tail removals stop as soon as both limits fit
- reserved tokens reduce token capacity
- one oversized item returns empty output with `budget_exhausted=True`
- empty input has `budget_exhausted=False`
- partial context drops with retained Evidence have `budget_exhausted=False`
- titles and snippets are never truncated

### 12.5 Diagnostics and mutation

- every diagnostic equation in Section 11.1 is checked literally
- diagnostics contain no raw Evidence content
- caller Evidence and nested locator remain unchanged
- returned nested mutation cannot affect caller input or a second result
- equal repeated calls return equal values
- monkeypatched inconsistent counts, estimate, order, or unsafe output are
  caught by final audit

### 12.6 LLM call budget

- default two reservations succeed in order
- third reservation raises the fixed typed error
- rejected reservation leaves count at two
- explicit max `1` allows one reservation only
- invalid max-call values reject bool, zero, negative, and values above two
- snapshot reports used, remaining, and maximum exactly
- snapshots are fresh frozen values
- independent request trackers do not share state
- no prompt, Evidence, secret, or raw value is stored or exposed

### 12.7 Composition

Use current public APIs with exact argument order:

```python
decision = EvidencePolicy().evaluate(...)
budget_result = select_evidence_context(decision.evidence)
citations = validate_citations(claims, plan, budget_result.evidence)
```

Test:

- real `EvidencePolicy.evaluate(...).evidence` feeds M2-08
- retained Evidence can be cited
- removed duplicate/source-cap/count-cap/context-cap Evidence is
  `unknown_evidence` at M2-07
- claims are created only after budget selection in the test
- policy status, warnings, source decisions, Evidence order, scores, and
  attribution are not mutated or recalculated
- no M3 claim generator or production orchestration is claimed

## 13. Required Preflight

Run from repository root only after the user approves this corrected M2-08 plan.

### 13.1 Git and document gate

```powershell
git rev-parse HEAD
git rev-parse origin/main
git status --short --branch
git log -3 --oneline --decorate
```

Expected planning base:

```text
HEAD = origin/main = 0711d62cd62f86d71c4a712b6205f7643f5f9209
latest commit = m2-07 conditional pass updates
```

Allowed initial dirty documents:

- this approved M2-08 Task Card
- M2-07 Task Card final closure synchronization only if still stale

No code, test, fixture, dependency, environment, workflow, or unrelated Task
Card may be dirty.

If HEAD differs, inspect the new commit. Stop if it changes an M2 public
contract.

Never use reset, restore, checkout to discard work, clean, stash, force push, or
history rewrite.

### 13.2 M2-07 closure synchronization

The latest GitHub Task Card is stale even though the independent closure passed.

Synchronize only these factual fields when still stale:

```text
M2-07 first implementation SHA:
7e952d10eb29eebf29f2c0ac657a484914b53ae7

M2-07 supplement SHA:
0711d62cd62f86d71c4a712b6205f7643f5f9209

M2-07 supplement commit:
m2-07 conditional pass updates

M2-07 supplement main push:
complete

M2-07 final closure review:
PASS

M2-07 status:
PASS / complete

Targeted:
145 passed

Policy/citation:
238 passed

M2-01~07:
552 passed

Full unit:
1313 passed

GitHub CI:
NOT_RUN

Independent pytest rerun:
NOT_RUN

M2-08 planning:
ALLOWED

M2-08 implementation:
ALLOWED only after approved plan and preflight PASS
```

If already accurate, do not rewrite. Keep M1-09 pending.

### 13.3 Regression gate

Use only the existing interpreter:

```powershell
$python = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "approved test interpreter is missing"
}

& $python --version
& $python -m pytest --version
& $python -c "from zoneinfo import ZoneInfo; print(ZoneInfo('Asia/Seoul').key)"
& $python -m pytest tests/unit/test_citation_validation.py -q
& $python -m pytest tests/unit/test_query_planner.py tests/unit/test_retrieval_filters.py tests/unit/test_retrieval_baseline.py tests/unit/test_evidence_normalization.py tests/unit/test_evidence_freshness.py tests/unit/test_evidence_policy.py tests/unit/test_citation_validation.py -q
& $python -m pytest tests/unit -q
& $python -c "from app.evidence.citations import validate_citations; from app.evidence.policy import EvidencePolicy; from app.retrieval.retriever import retrieve_evidence; print('ok')"
& $python scripts/secret_scan.py
& $python -m compileall app tests scripts -q
git diff --check
git status --short
```

Historical local baseline:

```text
M2-07 targeted: 145 passed
M2-01~07: 552 passed
full unit: 1313 passed
```

Record new actual results separately. If any command fails, stop before M2-08
code changes.

Do not install or change dependencies.

## 14. Implementation Order

1. Confirm HEAD/origin/main and approved dirty scope.
2. Synchronize M2-07 final closure only if stale.
3. Run and record the exact preflight.
4. Save this corrected Task Card as the approved M2-08 contract.
5. Add fixed context constants, typed errors, and frozen result/diagnostic
   dataclasses.
6. Add strict limits and Evidence canonical validation.
7. Add repeated-ID consistency using canonical full payloads.
8. Add deterministic exact-content fingerprints.
9. Add source-cap and count-cap stages.
10. Add canonical projection, approximate token estimator, and 4,500-character
    fallback.
11. Add deterministic tail removal and exact diagnostics.
12. Add final deep-copy and invariant audit.
13. Add the separate request-scoped LLM call counter.
14. Add boundary, fingerprint, attribution, cap, context, diagnostics, mutation,
    call-count, and composition tests.
15. Run all verification commands.
16. Review diff and changed-file scope.
17. Record only actual results.
18. Report for independent first implementation review.
19. Wait for separate Git approval.

## 15. Verification After Implementation

### Targeted

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_context_budget.py -q
```

### Policy, budget, and citation composition

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_evidence_policy.py tests/unit/test_context_budget.py tests/unit/test_citation_validation.py -q
```

### M2-01 through M2-08 regression

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_query_planner.py tests/unit/test_retrieval_filters.py tests/unit/test_retrieval_baseline.py tests/unit/test_evidence_normalization.py tests/unit/test_evidence_freshness.py tests/unit/test_evidence_policy.py tests/unit/test_citation_validation.py tests/unit/test_context_budget.py -q
```

### Full unit

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit -q
```

### Import smoke

```powershell
.\.venv\Scripts\python.exe -c "from app.evidence.budget import ContextBudgetLimits, LLMCallBudget, select_evidence_context; print('ok')"
```

### Secret scan and compile

```powershell
.\.venv\Scripts\python.exe scripts/secret_scan.py
```

```powershell
.\.venv\Scripts\python.exe -m compileall app tests scripts -q
```

### Diff

```powershell
git diff --check
git diff --stat
git status --short
```

Record exact commands, exit codes, passed counts, warnings, and any corrected
rerun. Local results must not be described as GitHub CI or independent pytest.

---

## 16. Completion Criteria

- [x] corrected final plan approved
- [x] preflight PASS
- [x] M2-07 closure synchronized if stale
- [x] only approved files changed
- [x] exact repeated-ID consistency enforced
- [x] canonical exact-content fingerprint implemented
- [x] attribution differences never deduplicated
- [x] source cap 3 enforced
- [x] final Evidence cap 6 enforced
- [x] approximate total token cap enforced
- [x] 4,500-character Evidence fallback enforced
- [x] lower-priority Evidence removed first
- [x] no title or snippet truncation
- [x] exact diagnostic equations pass
- [x] count-only log-ready diagnostics returned
- [x] separate request-scoped two-call LLM budget implemented
- [x] deep-copy and caller immutability verified
- [x] M2-06 decision → M2-08 → M2-07 composition verified
- [x] targeted and M2 regression PASS
- [x] full unit regression PASS
- [x] import smoke, ZoneInfo, secret scan, and compile PASS
- [x] diff and status reviewed
- [x] actual CI and independent rerun state recorded
- [x] independent first implementation review requested

M2-08 isolated completion does not prove:

- production orchestration
- actual Gemini/LiteLLM token count
- complete prompt size
- actual LLM call enforcement
- application log emission
- permission approval
- M2 Gate completion

After M2-08 closure, the next required activity is the M2 integrated review.
M3 implementation remains blocked until that integrated review passes.

## 17. Risks and Fallback

| Risk ID | Risk | Control | Fallback |
|---|---|---|---|
| R01 | budget work expands into M3 | isolated pure capability | keep M3 blocked |
| R02 | policy/retrieval contracts diverge | consume ordered Evidence only | stop on contract mismatch |
| R26 | low-relevance Evidence reintroduced | no scoring or new eligibility | use policy output only |
| R29 | citation points to removed Evidence | citation receives budget output | reject as unknown Evidence |
| R32 | empty budget still treated complete | explicit `budget_exhausted` | M3 must abstain |
| R54 | nondeterministic tests | no clock/network/tokenizer | recorded fixture tests only |
| R56 | logging/LLM work expands scope | counters only | defer integration to M3/M4 |
| R57 | diagnostics expose content | count-only diagnostics | fixed sanitized errors |

Fallback after an approved implementation:

- retain M2-03 top-k 6 and M2-06 policy output unchanged
- remove only the new M2-08 module/tests and its Task Card result changes
- perform rollback only with separate user approval and non-destructive Git
  operations

---

## 18. Stop Conditions

Stop and report if:

- preflight SHA or regression differs from the approved baseline
- dirty code, fixture, dependency, environment, workflow, or unrelated files
  exist before work
- core model or status enum changes appear necessary
- M2-03 scoring/order or M2-06 policy must change
- M2-07 public API or citation behavior must change
- semantic/news/event deduplication becomes necessary
- exact Gemini/LiteLLM tokenizer or a new dependency becomes necessary
- actual LLM, logger, provider, API, UI, or M3 integration becomes necessary
- permission eligibility must be inferred from Evidence alone
- a nonempty policy result cannot be handled without inventing a public status
- the 4,500-character fallback cannot be enforced within `budget.py`
- raw Evidence, path, secret, URL, permission value, or exception text could
  enter an error, diagnostic, or call-budget snapshot
- files outside the approved scope must change
- an existing regression fails

Report:

- verified problem
- source and Section
- smallest safe correction
- alternatives
- test and schedule impact

Do not commit or push without separate user approval.

## 19. Deferred and Not Run

- actual Gemini/LiteLLM tokenizer: `NOT_IMPLEMENTED`
- actual total prompt token/character count: `NOT_RUN`
- actual LLM call integration: `NOT_RUN`
- application structured log emission: `NOT_RUN`
- permission and external-transmission gate: `NOT_IMPLEMENTED`
- M2 integrated review:
  `NOT_RUN - ALLOWED and required before M3 implementation`
- production orchestration: `NOT_RUN - required before M2 milestone close`
- actual 365-day disclosure candidate completeness:
  `NOT_RUN - required before M2 milestone close`
- live provider/API/UI/LLM: `NOT_RUN`
- GitHub CI: `NOT_RUN`
- independent pytest rerun: `NOT_RUN`
- M2-09: `NOT_STARTED - conditional A15-M work`
- M3: `BLOCKED pending M2 integrated review PASS`

## 20. Implementation Review Checklist

### Source and scope

- [ ] planning base and latest main match
- [ ] M2-07 closure Task Card synchronized
- [ ] M1-09 remains pending
- [ ] only allowed files changed
- [ ] package root export unchanged
- [ ] no core/status/dependency/provider/API/UI/LLM changes
- [ ] no M2-09 or M3 implementation

### Input and duplicate contract

- [ ] list/tuple boundary
- [ ] limits and reserved-token validation
- [ ] LLM max-call validation separated
- [ ] strict Evidence reconstruction
- [ ] repeated-ID full-payload consistency
- [ ] canonical JSON fingerprint
- [ ] attribution and scope preserved
- [ ] first occurrence/order preserved

### Budget and diagnostics

- [ ] source cap before count cap
- [ ] token and character caps both enforced
- [ ] tail removal only
- [ ] no field truncation
- [ ] exact count equations
- [ ] exact total-token meaning
- [ ] exact character meaning
- [ ] exact `budget_exhausted` behavior
- [ ] diagnostics contain counts only

### Safety and determinism

- [ ] deep-copy isolation
- [ ] nested locator mutation isolation
- [ ] no hash-order dependence
- [ ] no I/O, clock, network, logger, or global mutable state
- [ ] sanitized typed errors
- [ ] unexpected internal failures not broadly swallowed

### Composition and verification

- [ ] exact M2-07 argument order
- [ ] removed Evidence becomes unknown at citation boundary
- [ ] policy status/warnings remain unchanged
- [ ] targeted test
- [ ] policy/budget/citation test
- [ ] M2-01~08 regression
- [ ] full unit
- [ ] import and ZoneInfo smoke
- [ ] secret scan and compile
- [ ] diff/status review
- [ ] CI and independent rerun accurately separated

---

## 21. Approval Request

Requested:

- no further M2-08 implementation or implementation review
- M2 integrated review only under a separate user instruction

Not requested:

- dependency installation or change
- actual logging integration
- live API, provider, URL, permission, or LLM work
- M2 integrated review in this synchronization task
- M2-09 or M3 implementation
- commit
- push
- PR
- merge
- deploy

## 22. Implementation Result

### 22.1 Preflight

- HEAD:
  `0711d62cd62f86d71c4a712b6205f7643f5f9209`
- origin/main:
  `0711d62cd62f86d71c4a712b6205f7643f5f9209`
- latest commit: `m2-07 conditional pass updates`
- initial dirty scope:
  `M docs/TASK_CARDS/M2-07-citation-validation.md`;
  `?? docs/TASK_CARDS/M2-08-context-budget.md`
- Python: `PASS - exit 0 - Python 3.14.3`
- pytest: `PASS - exit 0 - pytest 8.4.2`
- ZoneInfo: `PASS - exit 0 - Asia/Seoul`
- M2-07 targeted:
  `PASS - exit 0 - 145 passed, 1 PytestCacheWarning`
- M2-01~07:
  `PASS - exit 0 - 552 passed, 1 PytestCacheWarning`
- Full unit initial sandbox run:
  `ENVIRONMENT FAILURE - exit 1 - 1210 passed, 103 setup errors,
  3 warnings; pytest Temp directory PermissionError`
- Full unit approved local rerun:
  `PASS - exit 0 - 1313 passed, 1 existing StarletteDeprecationWarning`
- Existing-module import smoke: `PASS - exit 0 - ok`
- Secret scan: `PASS - exit 0 - []`
- Compile: `PASS - exit 0`
- Diff check:
  `PASS - exit 0 - no whitespace errors; tracked-file LF-to-CRLF warning`
- Preflight conclusion:
  `PASS after approved local rerun of the sandbox-blocked full unit command`

No dependency, code, fixture, workflow, or unrelated Task Card was dirty before
implementation. No destructive Git operation was used.

### 22.2 Implementation

- Added `app/evidence/budget.py`.
- Added `tests/unit/test_context_budget.py`.
- Preserved `app/evidence/__init__.py`, core models/status, retrieval, policy,
  citation, provider, API, UI, LLM, M2-09, and M3 code unchanged.
- Implemented exact repeated-ID consistency using canonical full JSON payloads.
- Implemented exact-content deduplication excluding only Evidence ID and score.
- Preserved attribution, scope, first occurrence ID/score, and input order.
- Implemented source cap, total count cap, approximate token cap, and
  4,500-character fallback in the approved stage order.
- Implemented exact count-only diagnostics and final output audit.
- Implemented a separate request-scoped two-call `LLMCallBudget`.
- Actual logging, tokenizer, permission, LLM, and production orchestration:
  `NOT_IMPLEMENTED / NOT_RUN`

### 22.3 Verification

- Targeted initial run:
  `FAIL - exit 1 - 97 passed, 1 failed, 2 warnings`
- Initial failure:
  `new composition fixture used a generic news locator and M2-07 correctly
  returned invalid_locator`
- Correction:
  `changed only the new test fixture to use the existing M2-07 news locator
  minimum; no production assertion was removed or weakened`
- Targeted corrected run before final audit strengthening:
  `PASS - exit 0 - 98 passed, 1 PytestCacheWarning`
- Targeted final:
  `PASS - exit 0 - 102 passed, 1 PytestCacheWarning`
- Policy/budget/citation final:
  `PASS - exit 0 - 340 passed, 1 PytestCacheWarning`
- M2-01~08 final:
  `PASS - exit 0 - 654 passed, 1 PytestCacheWarning`
- Full unit final approved local run:
  `PASS - exit 0 - 1415 passed, 1 existing StarletteDeprecationWarning`
- M2-08 import smoke: `PASS - exit 0 - ok`
- ZoneInfo final: `PASS - exit 0 - Asia/Seoul`
- Secret scan final: `PASS - exit 0 - []`
- Compile final: `PASS - exit 0`
- Trailing whitespace scan: `PASS - no findings`
- Diff check:
  `PASS - exit 0 - no whitespace errors; tracked-file LF-to-CRLF warning`

### 22.4 Git and Review State

- Planning/implementation base SHA:
  `0711d62cd62f86d71c4a712b6205f7643f5f9209`
- Implementation SHA:
  `03d2f982ddada67c767a02fad380b85a2980a8a3`
- Implementation commit: `Implement m2-08`
- Implementation main push: `complete`
- Implementation PR/merge/deploy: `NOT_RUN`
- Status synchronization SHA:
  `db542bbc1bd356ef967ef49d907f7cac684a2576`
- Status synchronization commit: `Sync m2-08 pass status`
- Status synchronization main push: `complete`
- GitHub CI: `NOT_RUN`
- Independent pytest rerun: `NOT_RUN`
- Independent implementation review: `PASS`
- Current M2-08 status: `PASS / complete`
- M2 integrated review:
  `ALLOWED - required before M3 implementation`
- M3 implementation:
  `BLOCKED pending M2 integrated review PASS`
- M1-09:
  `mandatory supplement implemented - final independent review pending`

Implementation commit files:

```text
A app/evidence/budget.py
M docs/TASK_CARDS/M2-07-citation-validation.md
A docs/TASK_CARDS/M2-08-context-budget.md
A tests/unit/test_context_budget.py
```
