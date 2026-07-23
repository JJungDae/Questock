# TASK CARD - M2-06 EvidencePolicy

## 1. Status and Approval

- Task bundle: `B5: M2-04~08`
- Step: `M2-06 EvidencePolicy`
- Planning date: `2026-07-23`
- Planning base branch: `main`
- Planning base SHA: `df20eae6457ac852e622b4006084acc16d1220fb`
- Planning base commit: `Implement m2-05`
- M2-05 implementation review: `PASS WITH REQUIRED FOLLOW-UP`
- M2-05 code status: `PASS / complete`
- M2-05 main push: `complete`
- M2-05 Task Card Git synchronization: `PASS - approved dirty synchronization verified current`
- M1-09 recorded status: `mandatory supplement implemented - final independent review pending`
- M2-06 first plan review: `CONDITIONAL PASS - corrected plan supplied`
- M2-06 total re-review: `PASS - matrix-mirror and retrieval-only target guard corrections incorporated`
- M2-06 final plan approval: `APPROVED by user on 2026-07-24`
- M2-06 preflight: `PASS`
- M2-06 implementation: `IMPLEMENTED LOCALLY - USER REVIEW PENDING`
- M2-07 citation validation: `NOT_STARTED`
- M2-08 dedupe/context budget: `NOT_STARTED`
- Further commit/push/PR/merge/deploy: `NOT_APPROVED`

The user approved this corrected final plan. The preflight and local
implementation are complete. Dependency installation and Git operations remain
unapproved.

The corrected plan preserves the existing core/status models and adds only
step-local validation needed to prevent an inconsistent QueryPlan, wrong-company
returned Evidence, or a mismatched explicit period from being returned as
`complete`.

## 2. Goal

Implement a deterministic in-memory EvidencePolicy that consumes the already
ordered M2 pipeline outputs and maps them to the existing
`EvidenceDecisionStatus` values:

- `complete`
- `partial`
- `provider_failed`
- `no_evidence`
- `blocked`

The policy must distinguish provider execution state, retrieval relevance,
required-source coverage, and M2-05 freshness limitations. It must never infer
that a successful provider call is sufficient evidence.

The policy is an abstention boundary. It does not compose an answer, validate a
citation, deduplicate Evidence, or allocate a context budget.

---

## 3. Verified Current Contracts

### 3.1 Existing code that must be reused

| Contract | Verified location | Current behavior used by M2-06 |
|---|---|---|
| `QueryPlan` | `app/core/models.py` | carries `intent`, ordered `required_sources`, ordered `required_evidence`, and `requires_clarification` |
| `ProviderResult` | `app/core/models.py` | carries provider status, data/error state, safe message, UTC `fetched_at`, and cache flag |
| `RetrievalResult` | `app/core/models.py` | carries ordered Evidence, retrieval status, strategy, low-relevance flag, and diagnostics |
| `Evidence` | `app/core/models.py` | carries source, security scope, locator, timestamp, snippet, and optional retrieval score |
| `EvidenceDecisionStatus` | `app/core/status.py` | exact final values are `complete`, `partial`, `provider_failed`, `no_evidence`, and `blocked` |
| provider result factory | `app/providers/base.py` | separates `ok`, `no_data`, and typed failure states and fixes stable error codes |
| lexical retrieval | `app/retrieval/retriever.py` | hard filter precedes scoring; `ok` has threshold-eligible Evidence; `empty` and `low_relevance` return no Evidence |
| freshness result | `app/evidence/freshness.py` | returns retained Evidence, ordered warnings, source windows, and disclosure effective-date information |
| planner matrix | `app/planning/query_planner.py` | fixes P0 intents and ordered required source/evidence lists |

There is no current public `EvidenceDecision` model. `FinancialAnswer` exists,
but it is an answer schema and is not the M2-06 policy result. M2-06 must not
change `FinancialAnswer`, any core model, or any status enum.

### 3.2 Existing status layers

These layers must remain separate.

#### Retrieval status

| Status | Existing meaning |
|---|---|
| `ok` | hard-filtered candidates met the lexical threshold and ordered Evidence is returned |
| `empty` | hard filtering left no eligible candidate; Evidence is empty and `low_relevance=False` |
| `low_relevance` | candidates existed but usable query tokens or threshold-eligible scores did not; Evidence is empty and `low_relevance=True` |

#### Provider status

| Status | M2-06 classification |
|---|---|
| `ok` | provider execution succeeded; this alone does not satisfy a required source |
| `no_data` | provider executed normally but returned no data; it is not a provider failure |
| `timeout` | provider failure |
| `rate_limited` | provider failure |
| `provider_unavailable` | provider failure |
| `parse_error` | provider failure |
| `unauthorized` | existing provider failure status; preserve even though it is not in the minimum M2-06 review list |
| `invalid_query` | existing provider failure status; preserve even though it is not in the minimum M2-06 review list |

The policy must not collapse `no_data` into a failure and must not turn any
failure status into normal absence.

#### Evidence decision status

| Status | Exact M2-06 invariant |
|---|---|
| `complete` | non-empty threshold-eligible Evidence; every required source is represented; no required-source failure/no-data result; no limiting freshness warning |
| `partial` | non-empty threshold-eligible Evidence, but at least one required source, provider state, or limiting freshness condition prevents `complete` |
| `provider_failed` | no usable Evidence and at least one required source has a provider failure |
| `no_evidence` | no usable Evidence and no required-source provider failure; includes normal no-data, retrieval empty, and aggregate low relevance |
| `blocked` | exact M2-01 `prohibited_advice` plan; no Evidence is returned |

`partial` always has Evidence. `provider_failed`, `no_evidence`, and `blocked`
always have an empty Evidence tuple.

### 3.3 M2 composition order

M2-06 consumes results only after this caller-owned order:

```text
M2-04 FinancialDocument -> Evidence normalization
-> M2-02 hard filter
-> M2-05 freshness
-> M2-03 lexical retrieval
-> M2-06 EvidencePolicy
```

M2-06 does not call these stages and does not recreate their rules. Its public
input order must reflect the same order: freshness result before retrieval
result.

Production orchestration wiring has not been implemented or verified. A unit
composition test is not production orchestration evidence.

---

### 3.4 Review Amendments and Provenance

| Finding | Classification | Existing source contract | Required correction |
|---|---|---|---|
| QueryPlan intent/source/evidence/clarification combinations were not checked against the fixed M2-01 matrix | `PLAN-GAP` | M2-01 §§6.3, 6.6 | validate an exact read-only matrix mirror and add planner-to-policy drift tests |
| The policy could return Evidence for a different security than the QueryPlan target | `PLAN-GAP` | README §2.5, STOCK_SCOPE_CHANGE_NOTICE, R25 | add a final target-security eligibility guard for returned retrieval Evidence only |
| QueryPlan explicit dates and FreshnessWindow user dates could disagree | `PLAN-GAP` | M2-01 §6.7 and M2-05 user-period contract | add cross-stage date-window consistency validation |
| Freshness warnings could use an incompatible source or malformed structure | `PLAN-GAP` | M2-05 warning contract | validate code/source compatibility and structural determinism |
| Duplicate or out-of-order warnings were not rejected | `CONTRACT-HARDENING` | M2-05 deterministic warning contract | validate uniqueness and fixed ordering in the same implementation |
| Blocked/clarification outputs did not define whether valid but irrelevant downstream values are copied | `PLAN-GAP` | M2-01 non-retrieval contract | structurally validate inputs, then return empty decision collections |
| GitHub M2-05 Task Card still records local/unpushed state | `PROCESS-INTEGRITY` | README §§2.6, 3 | verify and minimally synchronize during preflight |
| Preflight commands used the already-failed `.test_deps` path instead of the verified `.venv` interpreter | `PROCESS-INTEGRITY` | M2-05 Result Log | use the existing verified `.venv` without installing dependencies |

These corrections do not add a new intent, source, core field, status, provider,
dependency, API/UI/LLM feature, or later-Step behavior.

---

## 4. Scope

### 4.1 Planned files

Create:

- `app/evidence/policy.py`
- `tests/unit/test_evidence_policy.py`
- `docs/TASK_CARDS/M2-06-evidence-policy.md`

Modify only when required:

- `docs/TASK_CARDS/M2-05-freshness.md`
  - verify current GitHub content first
  - if stale, synchronize only the implementation SHA/commit/push, independent
    review result, test counts, M2-06 entry, and remaining milestone limits
- `docs/TASK_CARDS/M2-06-evidence-policy.md`
  - implementation and verification result recording

Do not modify `app/evidence/__init__.py`. The initial public import path remains
`app.evidence.policy`.

### 4.2 Explicit exclusions

Do not modify or add:

- `app/core/models.py`
- `app/core/status.py`
- planner, resolver, provider, ingest, hard-filter, retrieval, normalization,
  or freshness code
- provider/live API orchestration
- API, UI, LLM, answer composition, or answer validation
- M2-07 claim/citation support validation
- M2-08 Evidence dedupe, per-source quota, context budget, or top-k trimming
- dense retrieval, vector storage, reranker, or semantic classifier
- dependency files or environment packages

No Evidence is removed as a duplicate in M2-06. Repeated Evidence occurrences
that legitimately survive M2-03 are preserved in their existing order.

If another file or dependency becomes necessary, stop and report before
expanding scope.

## 5. Planned Public API

`app/evidence/policy.py` will own the following step-local API.

```python
from dataclasses import dataclass
from typing import Any, Mapping


class EvidencePolicyValidationError(ValueError):
    """Raised for malformed or inconsistent public policy inputs."""


@dataclass(frozen=True)
class EvidenceDecision:
    status: EvidenceDecisionStatus
    evidence: tuple[Evidence, ...]
    warnings: tuple[FreshnessWarning, ...]
    satisfied_sources: tuple[str, ...]
    missing_sources: tuple[str, ...]
    no_data_sources: tuple[str, ...]
    failed_sources: tuple[str, ...]


class EvidencePolicy:
    def evaluate(
        self,
        plan: QueryPlan,
        provider_results_by_source: Mapping[str, ProviderResult[Any]],
        freshness: FreshnessResult,
        retrieval: RetrievalResult,
    ) -> EvidenceDecision:
        ...
```

Rules:

- mapping keys are canonical P0 source types, not provider implementation keys
  such as `recorded_news`
- one mapping entry represents the provider outcome supplied by the caller for
  that source
- a missing mapping entry is not automatically a provider failure because
  `glossary` and `research_report` may be backed by validated local corpus
- every supplied mapping key and value is still validated, including entries
  not required by the current plan
- extra valid provider entries do not affect the decision
- the class has no clock, I/O, cache, network, or mutable state
- no default global singleton is introduced

### 5.1 Result field meaning

- `evidence`: deep copies of retrieval Evidence only
- `warnings`: ordered copies of all M2-05 warnings, including informational
  warnings
- `satisfied_sources`: unique required sources represented by returned
  retrieval Evidence
- `missing_sources`: unique required sources not represented by returned
  retrieval Evidence
- `no_data_sources`: required sources whose supplied provider result is
  `no_data`
- `failed_sources`: required sources whose supplied provider result is any
  provider failure status

All source tuples follow the first-occurrence order in
`QueryPlan.required_sources`. `satisfied_sources` and `missing_sources` are
disjoint. Provider-state tuples may overlap `satisfied_sources` when a caller
has usable corpus/cache Evidence in addition to a failed or no-data provider
attempt; such a conflict prevents `complete`.

---

## 6. Public Input Validation

All public failures must raise `EvidencePolicyValidationError` with a fixed,
project-owned message. Raw Pydantic text, exception text, mapping values,
queries, source payloads, paths, credentials, and secret sentinels must not be
included.

### 6.1 QueryPlan

Validate by reconstructing a strict canonical `QueryPlan` from all declared
fields without mutating the caller object.

Reject:

- non-`QueryPlan` input
- malformed direct/model-constructed fields
- blank/non-string or unsupported intent
- non-string, blank, duplicate, or unsupported required source
- non-string, blank, duplicate, or unsupported required-evidence entry
- non-boolean clarification flag
- an intent/source/evidence/clarification combination that differs from the
  fixed M2-01 contract
- a security-required retrievable plan with `security=None`
- an unsupported or malformed supplied `SecurityIdentifier`

Allowed P0 source vocabulary:

```text
news
disclosure
research_report
glossary
```

The exact non-clarification matrix is:

| intent | required_sources | required_evidence | security |
|---|---|---|---|
| `financial_term` | `['glossary']` | `['definition']` | optional |
| `disclosure_summary` | `['disclosure']` | `['disclosure']` | required |
| `research_report_summary` | `['research_report']` | `['research_report']` | required |
| `recent_issue` | `['news']` | `['recent_news']` | required |
| `risk_factors` | `['news', 'disclosure', 'research_report']` | `['risk', 'recent_news', 'disclosure', 'research_report']` | required |
| `multi_source_summary` | `['news', 'disclosure', 'research_report']` | `['recent_news', 'disclosure', 'research_report']` | required |

Clarification contract:

- `requires_clarification=True`
- `required_sources=[]`
- `required_evidence=[]`
- `security=None`
- allowed intent is `prohibited_advice`, `out_of_scope`, or any supported
  retrievable intent when an explicit mention is ambiguous, unsupported,
  conflicting, or otherwise requires clarification
- `prohibited_advice` and `out_of_scope` may never be non-clarification plans
- `financial_term` normally retrieves without security, but an explicit
  ambiguous/unsupported/conflicting security-like mention may still produce the
  exact M2-01 `financial_term` clarification plan

The supported security IDs remain:

```text
KRX:005930
KRX:000660
KRX:005380
```

If `security` is present, derive `security_id=f"{market}:{ticker}"` and require
one of these IDs. M2-06 does not resolve names or read the security registry.

M2-06 does not reclassify intent, rewrite the QueryPlan, infer
`required_evidence` from title/snippet text, call the resolver, or re-run
planner query analysis.

The exact M2-01 matrix is a read-only cross-stage integrity mirror, not a second
planner implementation.

Contract-drift tests must generate canonical plans through the actual
`QueryPlanner`, verify that the M2-06 mirror accepts those outputs, and then
change one source/evidence/clarification field at a time to verify that policy
validation rejects the drift.

### 6.1.1 Target-security Evidence guard

For these security-required intents:

```text
recent_issue
disclosure_summary
research_report_summary
risk_factors
multi_source_summary
```

every Evidence returned in `retrieval.evidence` must be eligible for the
canonical plan target:

- `company_specific`: `subject_security_ids == [target_security_id]`
- `multi_company`: target is in `subject_security_ids`
- `industry_common`: target is in `mentioned_security_ids`

Otherwise raise the fixed `policy inputs are inconsistent` error.

Each returned retrieval occurrence must already match a corresponding
freshness occurrence under the count-aware comparison in §6.4. This proves the
selected output's connection to the preceding freshness stage.

Freshness candidates that were not selected by retrieval are not re-filtered or
rejected by M2-06. Full candidate eligibility remains owned by M2-02.

This guard is a final returned-output invariant, not a replacement for M2-02.
M2-06 still does not repeat source/date/document-type filtering or
linked-document lookup.

For `financial_term`, security is optional and glossary Evidence remains a
generic source contract; do not add company-specific glossary filtering.

### 6.2 Provider result mapping

Reject:

- non-mapping input
- non-string or blank source key
- unsupported source key
- non-`ProviderResult` value
- malformed direct/model-constructed ProviderResult
- status/data/error-code combinations that violate the M1-03 factory contract
- naive or non-UTC `fetched_at`
- non-boolean `from_cache`

Recheck the existing status invariants:

- `ok`: data is non-`None`, `error_code=None`
- `no_data`: data is `None`, `error_code=None`
- failure: data is `None`, fixed status error code
- `timeout`: `attempt_timeout` or `total_deadline_exceeded`

The M2-06 result does not copy provider messages or data. This prevents raw
provider content from reaching a policy validation error or decision.

### 6.3 FreshnessResult

Reject malformed direct dataclass construction, including:

- non-`FreshnessResult`
- naive/non-UTC `basis_at`
- `basis_date` inconsistent with `basis_at` in Asia/Seoul
- non-tuple windows, Evidence, or warnings
- malformed window/warning items
- duplicate or unsupported window source types
- warning source not present in freshness windows
- duplicate `(warning.code, warning.source_type)` pairs
- a warning code used for an incompatible source
- warnings not grouped by freshness-window source order and the fixed M2-05
  warning-code order
- malformed Evidence
- invalid `latest_effective_disclosure_at`

Allowed warning/source combinations:

- `missing_published_at`, `future_published_at`: `news`, `disclosure`,
  `research_report`
- `stale_news`: `news`
- `stale_research_report`: `research_report`
- `disclosure_window_extended`, `insufficient_disclosure_coverage`,
  `unresolved_disclosure_correction`: `disclosure`

For a non-clarification plan:

- ordered freshness-window sources must equal ordered unique required sources
- if `plan.date_range` has at least one bound, every window must have
  `applied_by="user"` and exactly the same `start`/`end`
- if `plan.date_range` has no meaningful bound, no window may have
  `applied_by="user"`
- with no meaningful user range, `glossary` uses `applied_by="none"`
- with no meaningful user range, supported source windows may use only their
  existing M2-05 `default`/`fallback` modes

This proves source and explicit-period consistency without recalculating M2-05
age, correction, or provider-candidate policy.

For a clarification plan, freshness is structurally validated but its semantic
windows/warnings/Evidence are ignored because M2-01 declares the path
non-retrievable.

### 6.4 RetrievalResult

Reconstruct and validate without mutating the caller.

Exact invariants:

| Retrieval status | Evidence | `low_relevance` |
|---|---|---|
| `ok` | one or more valid items | `False` |
| `empty` | empty | `False` |
| `low_relevance` | empty | `True` |

For `ok`:

- every Evidence has a finite numeric `retrieval_score`
- every score is at least the existing M2-03
  `LOW_RELEVANCE_THRESHOLD`
- strategy is a non-blank string
- returned Evidence order is preserved

For a non-clarification plan, every retrieval Evidence must be
occurrence-bounded by freshness Evidence after ignoring only
`retrieval_score`. A scored copy may match an unscored freshness item; an item
absent from freshness fails as inconsistent input. The check is count-aware and
does not deduplicate equal Evidence.

The target-security guard in §6.1.1 applies to canonical retrieval Evidence
after canonical freshness/retrieval validation and before any decision status
is returned.

For a clarification plan, RetrievalResult is structurally validated but valid
downstream Evidence is discarded by the conservative clarification/blocked
decision.

## 7. Required-Source and Provider Classification

### 7.1 Required-source coverage

Coverage is determined only from final threshold-eligible retrieval Evidence:

```text
required source S is satisfied
iff at least one returned Evidence has source_type == S
```

The following do not satisfy a source by themselves:

- provider status `ok`
- provider data presence
- freshness candidates that retrieval did not return
- retrieval diagnostics counts
- a document or Evidence from a different source
- permission metadata
- title/snippet keyword inference outside M2-03

An absent provider-result mapping does not make a represented local-corpus
source missing. Conversely, `ProviderResult.ok` with no returned Evidence does
not prevent the source from being listed in `missing_sources`.

### 7.2 Provider failure set

The failure set is fixed to:

```text
invalid_query
unauthorized
rate_limited
timeout
provider_unavailable
parse_error
```

`no_data` remains separate. `low_relevance` is never a provider status.

### 7.3 Limiting freshness warnings

The following warning codes prevent `complete` when they apply to a required
source:

```text
stale_news
stale_research_report
insufficient_disclosure_coverage
unresolved_disclosure_correction
```

Consumption rules:

| Warning | Policy effect |
|---|---|
| `stale_news` | `partial` if usable Evidence remains; otherwise normal no-Evidence/provider-failure precedence |
| `stale_research_report` | same |
| `insufficient_disclosure_coverage` | `partial` if usable Evidence remains; otherwise normal no-Evidence/provider-failure precedence |
| `unresolved_disclosure_correction` | `partial` if usable Evidence remains; otherwise normal no-Evidence/provider-failure precedence |
| `disclosure_window_extended` | informational only; does not by itself prevent `complete` |
| `missing_published_at` | preserve warning; malformed-date candidate was already excluded by M2-05 and does not by itself downgrade sufficient valid Evidence |
| `future_published_at` | preserve warning; future candidate was already excluded by M2-05 and does not by itself downgrade sufficient valid Evidence |

Because a non-clarification input requires freshness window sources to match
the required-source order exactly, a warning for any other source is an
inconsistent public input rather than an ignorable warning.

M2-06 does not resolve correction graphs again and does not invent a latest
valid disclosure when M2-05 reports an unresolved correction.

---

## 8. Exact Decision Order

After all public inputs have been sanitized and canonicalized:

```text
1. exact prohibited-advice safety block
2. non-prohibited clarification/non-retrievable plan
3. retrieval/provider/source/freshness classification
4. construct an invariant-checked EvidenceDecision
```

### 8.1 Blocked

Return `blocked` only for the exact canonical M2-01 plan:

```text
plan.intent == "prohibited_advice"
plan.requires_clarification is True
plan.required_sources == []
plan.required_evidence == []
plan.security is None
```

All public inputs are structurally validated first. Valid but irrelevant
provider/freshness/retrieval values are not copied into the blocked result.

The blocked result contains:

```text
evidence=()
warnings=()
satisfied_sources=()
missing_sources=()
no_data_sources=()
failed_sources=()
```

### 8.2 Non-prohibited clarification

Any other canonical clarification plan returns `no_evidence`.

All decision collections are empty, as in the blocked result. Ordinary
clarification is never relabeled as a safety violation. Valid but irrelevant
downstream results are ignored after structural validation.

### 8.3 Retrieval `empty` or `low_relevance`

Both statuses have no returned Evidence under the current M2-03 aggregate
contract.

- if any required source has a provider failure: `provider_failed`
- otherwise: `no_evidence`

`low_relevance` is recorded through the consumed RetrievalResult and maps to
`no_evidence`, not provider failure. A `partial` low-relevance result is not
possible with the current single aggregate RetrievalResult because it contains
no usable Evidence. M2-06 must not revive below-threshold candidates merely to
produce `partial`.

### 8.4 Retrieval `ok`

With non-empty threshold-eligible Evidence:

- return `complete` only if all required sources are satisfied, no required
  source has `no_data` or a provider failure, and no limiting freshness warning
  applies
- otherwise return `partial`

A plan with no required sources can never return `complete`. It returns
`no_evidence` and discards supplied Evidence.

### 8.5 Decision matrix

| Usable Evidence | Required-source provider failure | Required-source no-data/missing | Limiting freshness warning | Result |
|---|---:|---:|---:|---|
| none | yes | any | any | `provider_failed` |
| none | no | yes or no | any | `no_evidence` |
| some | yes | any | any | `partial` |
| some | no | yes | any | `partial` |
| some | no | no | yes | `partial` |
| some | no | no | no | `complete` |

Safety-block and clarification rules precede this table.

---

## 9. Output Integrity

`EvidenceDecision` construction must pass one central internal invariant
boundary.

### 9.1 Status invariants

- `complete`
  - Evidence is non-empty
  - required sources are non-empty
  - `missing_sources`, `no_data_sources`, and `failed_sources` are empty
  - all required sources are satisfied
  - no limiting required-source warning exists
- `partial`
  - Evidence is non-empty
  - at least one incomplete-source, provider-state, or limiting-warning
    condition exists
- `provider_failed`
  - Evidence is empty
  - `failed_sources` is non-empty
- `no_evidence`
  - Evidence is empty
  - no required-source provider failure exists
- `blocked`
  - Evidence is empty
  - every decision collection is empty
  - the canonical plan is exact prohibited advice

Before `complete` or `partial`, the central invariant boundary must also prove:

- exact M2-01 intent/source/evidence/security contract
- freshness-window source and explicit-period consistency
- retrieval occurrence-boundedness against freshness
- target-security eligibility for every returned retrieval Evidence

### 9.2 Mutation isolation and determinism

- deep-copy every returned Evidence
- do not mutate QueryPlan lists
- do not mutate ProviderResult data/messages
- do not mutate FreshnessResult Evidence
- do not mutate RetrievalResult Evidence or scores
- use tuples for all decision collections
- preserve retrieval order, required-source order, and M2-05 warning order
- do not sort by sets or mapping iteration order
- do not read current time, environment variables, filesystem, network, or
  randomness
- identical canonical inputs produce equal decisions

### 9.3 Sanitized errors

Use short fixed messages such as:

```text
plan must be a QueryPlan
provider results must be a source mapping
provider results are invalid
freshness result is invalid
retrieval result is invalid
policy inputs are inconsistent
```

Never include raw source values, query text, error messages, local paths,
provider payloads, or exception representations.

---

## 10. Test Plan

Create `tests/unit/test_evidence_policy.py`.

### 10.1 Status-layer separation

- provider `ok` plus retrieval `empty` -> `no_evidence`
- provider `no_data` plus retrieval `empty` -> `no_evidence`
- each provider failure plus no Evidence -> `provider_failed`
- `low_relevance` plus no provider failure -> `no_evidence`
- `low_relevance` plus provider failure -> `provider_failed`
- provider failure is never reported as no-data
- low relevance is never reported as provider failure without an actual
  required-source provider failure

### 10.2 Required-source coverage

- one required source represented -> `complete`
- all three multi-source required sources represented -> `complete`
- one of three sources missing with remaining Evidence -> `partial`
- all sources missing -> `no_evidence`
- provider `ok` without Evidence does not satisfy a source
- local `glossary` or `research_report` Evidence can satisfy a source without a
  provider mapping entry
- extra provider result does not affect the decision
- source order is deterministic

### 10.3 Provider and no-data behavior

- `timeout`
- `rate_limited`
- `provider_unavailable`
- `parse_error`
- existing `unauthorized`
- existing `invalid_query`
- `no_data`
- `ok`
- failure with Evidence -> `partial`
- no-data with Evidence -> `partial`
- stable timeout error-code variants accepted
- malformed provider status/data/error/time combinations rejected

### 10.4 Freshness warning consumption

- `stale_news` prevents `complete`
- `stale_research_report` prevents `complete`
- `insufficient_disclosure_coverage` prevents `complete`
- `unresolved_disclosure_correction` prevents `complete`
- each warning with usable Evidence -> `partial`
- `disclosure_window_extended` alone may remain `complete`
- missing/future timestamp warning is preserved and does not alone downgrade
  otherwise sufficient valid Evidence
- warning for a source outside the required freshness windows is rejected
- warning code/source compatibility is enforced
- duplicate or out-of-order warnings are rejected
- warning order is preserved

### 10.5 QueryPlan, safety, clarification, and matrix drift

- actual `QueryPlanner` output for each six-intent non-clarification route is
  accepted only with its exact required-source/evidence order
- actual `QueryPlanner` clarification outputs are accepted only with empty
  required-source/evidence lists and `security=None`
- changing one source, evidence, clarification flag, or required-security field
  from an actual planner output is rejected
- the policy does not parse query text, call a resolver, or reclassify intent
- prohibited/out-of-scope non-clarification plan is rejected
- security-required plan with `security=None` is rejected
- unsupported security ID is rejected
- exact prohibited-advice plan -> `blocked`
- blocked decision returns all-empty collections even when structurally valid
  downstream results are supplied
- out-of-scope clarification -> `no_evidence` with all-empty collections
- ambiguous/missing-security clarification, including a financial-term query
  with an explicit conflicting security-like mention, -> `no_evidence` with
  all-empty collections
- ordinary clarification is not `blocked`
- no-required-source plan never returns `complete`

### 10.6 Freshness/retrieval/security integrity

- scored retrieval copy matches an unscored freshness Evidence
- retrieval Evidence absent from freshness is rejected
- more retrieval occurrences than freshness occurrences are rejected
- retrieval `ok` with below-threshold/non-finite/missing score is rejected
- retrieval `empty` carrying Evidence is rejected
- retrieval `low_relevance` carrying Evidence is rejected
- retrieval `low_relevance` with flag false is rejected
- freshness source-window order mismatch is rejected
- explicit QueryPlan DateRange with non-user or unequal windows is rejected
- no meaningful QueryPlan range with a user window is rejected
- duplicate, out-of-order, unsupported, or source-incompatible freshness
  warnings are rejected
- Samsung plan with SK Hynix `company_specific` retrieval Evidence is rejected
- target absent from returned `multi_company.subject_security_ids` is rejected
- target absent from returned `industry_common.mentioned_security_ids` is rejected
- valid company-specific, multi-company, and industry-common retrieval Evidence
  remains accepted
- a wrong-company freshness candidate that is not selected by retrieval is not
  independently re-filtered by M2-06
- every returned retrieval occurrence remains count-bounded by freshness

### 10.7 Mutation, duplicates, and determinism

- returned Evidence is a deep copy
- mutating a returned Evidence does not mutate retrieval or freshness input
- mutating caller inputs after one result does not mutate that result
- duplicate Evidence occurrences are preserved, not deduplicated
- repeated evaluation returns equal decisions
- mapping insertion order does not change the result

### 10.8 Sanitized validation

Direct malformed public inputs:

- wrong plan type
- malformed model-constructed QueryPlan
- intent/source/evidence/clarification matrix mismatch
- unsupported or missing required security
- wrong mapping type
- blank/unsupported mapping key
- wrong ProviderResult item type
- malformed FreshnessResult containers/items/timestamps
- duplicate/out-of-order/source-incompatible FreshnessWarning
- QueryPlan DateRange/FreshnessWindow mismatch
- wrong-company returned retrieval Evidence
- wrong RetrievalResult type
- malformed model-constructed RetrievalResult

For every failure:

- exact exception type is `EvidencePolicyValidationError`
- no raw exception text
- no sentinel secret
- no local absolute path

### 10.9 Regression preservation

The M2 composition regression must retain:

- actual M2-01 routing and planner-to-policy matrix compatibility
- M2-02 wrong-company blocking
- M2-03 threshold and retrieval-status contracts
- M2-04 Evidence normalization
- M2-05 freshness/correction/warning behavior
- M2-06 decision mapping

No M1-09 status assertion may be changed from
`mandatory supplement implemented - final independent review pending`.

---

## 11. Preflight Gate

Implementation may begin only after the user approves this corrected Task Card
and every preflight command passes at the approved main SHA.

### 11.1 Git and scope check

```powershell
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
git status --short
git log -2 --oneline --decorate
```

Expected:

- branch `main`
- HEAD and `origin/main` at
  `df20eae6457ac852e622b4006084acc16d1220fb`
- only the approved M2-05 status synchronization and M2-06 planning file may be
  dirty
- no code, fixture, dependency, secret, or unrelated user change

Do not reset, restore, checkout, clean, stash, delete, or overwrite any dirty
file.

### 11.2 Synchronize M2-05 Task Card if stale

Inspect:

```text
docs/TASK_CARDS/M2-05-freshness.md
```

Expected minimum final record:

```text
Current status: PASS / complete
Implementation SHA: df20eae6457ac852e622b4006084acc16d1220fb
Implementation commit: Implement m2-05
Implementation main push: complete
Independent implementation review: PASS WITH REQUIRED FOLLOW-UP
Targeted pytest: 88 passed
M2 composition regression: 314 passed
Full unit regression: 1075 passed
GitHub CI: NOT_RUN
Independent pytest rerun: NOT_RUN
Production orchestration: NOT_RUN - required before M2 milestone close
365-day candidate completeness: NOT_RUN - required before M2 milestone close
M2-06 planning: ALLOWED
M2-06 implementation: ALLOWED after approved plan and preflight PASS
Further commit/push/PR/merge/deploy: NOT_APPROVED
```

If the file already contains this state, do not rewrite it. If stale, apply only
this synchronization. Keep M1-09 pending.

### 11.3 Verified test interpreter

M2-05 established this local interpreter:

```powershell
$python = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "approved test interpreter is missing"
}
& $python --version
& $python -m pytest --version
& $python -c "from zoneinfo import ZoneInfo; print(ZoneInfo('Asia/Seoul'))"
```

Do not intentionally rerun the already-failed `.test_deps;.deps;.` path. Do not
install or change dependencies in M2-06.

### 11.4 M2-05 targeted

```powershell
& $python -m pytest tests/unit/test_evidence_freshness.py -q
```

### 11.5 Existing M2 composition regression

```powershell
& $python -m pytest tests/unit/test_query_planner.py tests/unit/test_retrieval_filters.py tests/unit/test_retrieval_baseline.py tests/unit/test_evidence_normalization.py tests/unit/test_evidence_freshness.py -q
```

### 11.6 Full unit regression

```powershell
& $python -m pytest tests/unit -q
```

### 11.7 Import smoke, secret scan, and compile

```powershell
& $python -c "from app.evidence.freshness import FreshnessResult, evaluate_freshness; from app.retrieval.retriever import retrieve_evidence; print('ok')"
& $python scripts/secret_scan.py
& $python -m compileall app tests scripts -q
```

If any command fails:

- stop before M2-06 code
- preserve the working tree
- report the exact command, exit code, and sanitized failure
- do not install or change dependencies without separate approval

## 12. Implementation Order After Approval and Preflight PASS

1. Reconfirm Git SHA, branch, and approved dirty documents.
2. Verify or minimally synchronize the M2-05 Task Card.
3. Run and record every preflight command with the verified `.venv` interpreter.
4. Create `EvidencePolicyValidationError`.
5. Create the frozen step-local `EvidenceDecision`.
6. Implement strict QueryPlan canonical validation and exact M2-01 matrix mirror checks.
7. Add actual-`QueryPlanner` contract-drift tests without calling the planner at runtime.
8. Implement target-security eligibility checks for returned retrieval Evidence.
9. Implement ProviderResult contract validation and failure/no-data grouping.
10. Implement FreshnessResult structural, warning-order, and period-window
    validation.
11. Implement RetrievalResult status/score validation.
12. Implement count-aware freshness-to-retrieval occurrence validation.
13. Implement required-source coverage and limiting-warning classification.
14. Implement exact blocked/clarification/decision priority.
15. Route every result through one central decision invariant boundary.
16. Add targeted tests for every status, warning, source, returned security,
    period, and malformed input.
17. Add composition tests with M2-01 through M2-05 public outputs.
18. Run targeted, M2 composition, full unit, smoke, secret scan, compile, and
    diff checks.
19. Record only actual results in this Task Card.
20. Report the diff and wait for separate commit/push approval.

## 13. Verification After Implementation

Use the preflight `$python` interpreter.

### 13.1 Targeted

```powershell
& $python -m pytest tests/unit/test_evidence_policy.py -q
```

### 13.2 M2 composition regression

```powershell
& $python -m pytest tests/unit/test_query_planner.py tests/unit/test_retrieval_filters.py tests/unit/test_retrieval_baseline.py tests/unit/test_evidence_normalization.py tests/unit/test_evidence_freshness.py tests/unit/test_evidence_policy.py -q
```

### 13.3 Full unit regression

```powershell
& $python -m pytest tests/unit -q
```

### 13.4 Import smoke

```powershell
& $python -c "from app.evidence.policy import EvidenceDecision, EvidencePolicy, EvidencePolicyValidationError; print('ok')"
```

### 13.5 Hygiene and diff

```powershell
& $python scripts/secret_scan.py
& $python -m compileall app tests scripts -q
git diff --check
git diff --name-status
git diff --stat
git status --short
git log -2 --oneline --decorate
```

Record exact commands, execution context, exit codes, pass counts, warnings,
skipped checks, GitHub CI state, independent rerun state, and final changed
files.

## 14. Stop Conditions

Stop and report before implementation or further edits if:

- preflight HEAD is not the approved SHA
- code, fixture, dependency, or unrelated dirty changes appear
- an existing regression, smoke, secret scan, or compile command fails
- the current code/status contract differs from this Task Card
- EvidencePolicy requires a core model or enum change
- a new dependency appears necessary
- M2-05 freshness output cannot be validated without changing M2-05
- the exact M2-01 intent/source/evidence/security matrix cannot be preserved
- target-security eligibility for returned retrieval Evidence cannot be checked
  from existing Evidence fields
- QueryPlan explicit period cannot be matched to the FreshnessWindow contract
- complete/partial cannot be decided without inventing an evidence category
- production orchestration or real 365-day candidate fetching becomes required
- M2-07 citation logic or M2-08 dedupe/context budget becomes necessary
- a raw secret, credential, local path, provider payload, wrong-company returned
  Evidence, or mismatched-period Evidence could enter a public decision/error

Report:

- problem
- verified evidence
- smallest safe correction
- alternatives
- test/schedule impact

---

## 15. Risks and Fallback

| Risk | Control | Fallback |
|---|---|---|
| R18 provider failure confused with no-data | exact provider grouping and tests | conservative `provider_failed` or `no_evidence` |
| R24 intent/source matrix drift | read-only exact M2-01 matrix mirror plus actual-planner drift tests | reject inconsistent public input |
| R25 wrong-company Evidence reaches policy output | returned-retrieval target-security output invariant | reject inconsistent public input |
| R26 low relevance treated as sufficient | accept only M2-03 `ok` Evidence above threshold | `no_evidence` |
| R11 stale data treated as current | consume M2-05 stale warnings | `partial` or no-Evidence path |
| R12 correction ambiguity | consume unresolved-correction warning without re-inference | `partial` or no-Evidence path |
| R29 unsupported citation/evidence | M2-06 does not validate claims or locators beyond existing Evidence contract | defer to M2-07 |
| R32 unsupported `complete` | central complete invariant requires exact plan/source/security/period consistency, Evidence, and all required sources | conservative `partial`/`no_evidence` |
| Caller mutation | deep-copy output and tuple containers | reject malformed input |
| Error leakage | fixed sanitized exception messages | fail closed |
| Missing production pipeline | document as NOT_RUN | unit composition only; milestone remains open |

Rollback after an approved implementation is limited to reverting the new
M2-06 files and the M2-06 result-log section through a separately approved,
non-destructive Git operation. Do not roll back M2-05 or earlier code.

---

## 16. Known Deferred Limits

- Production orchestration: `NOT_RUN - required before M2 milestone close`
- Actual 365-day provider candidate completeness:
  `NOT_RUN - required before M2 milestone close`
- Live provider calls: `NOT_RUN - out of M2-06 scope`
- GitHub CI: `NOT_RUN`
- Independent pytest rerun: `NOT_RUN`
- M2-07 citation validation: `NOT_STARTED`
- M2-08 dedupe/context budget: `NOT_STARTED`
- M1-09 final independent review:
  `mandatory supplement implemented - final independent review pending`

On a clean Windows environment, `ZoneInfo("Asia/Seoul")` previously required a
separate `tzdata` installation. Preserve this as a deferred clean-build note.
M2-06 does not approve a dependency change. If the existing environment cannot
load the zone, stop at preflight and leave dependency policy to the separately
approved clean-build stage.

---

## 17. Completion Criteria

Planning completion:

- [x] M2-05 Task Card verified and synchronized if stale
- [x] actual core/status/provider/retrieval/freshness contracts rechecked
- [x] retrieval, provider, and EvidenceDecision status layers separated
- [x] required-source fulfillment rule fixed
- [x] stale/coverage/correction warning consumption fixed
- [x] provider failure and normal no-data separated
- [x] no unsupported `complete` rule fixed
- [x] exact M2-01 intent/source/evidence/clarification matrix fixed as a read-only mirror
- [x] actual QueryPlanner-to-policy drift test requirement fixed
- [x] target-security output invariant limited to returned retrieval Evidence
- [x] QueryPlan explicit-period/FreshnessWindow consistency fixed
- [x] freshness warning code/source compatibility fixed
- [x] freshness warning uniqueness/order hardening fixed
- [x] freshness-before-retrieval input order fixed
- [x] production orchestration and 365-day limitations recorded
- [x] mutation, determinism, and sanitized-error contracts fixed
- [x] M2-07 and M2-08 exclusions fixed
- [x] Windows `tzdata` issue retained as a deferred clean-build note
- [x] user approves M2-06 final plan

Implementation completion after approval:

- [x] approved SHA and dirty-tree preflight passes
- [x] new policy/result API implemented without core changes
- [x] exact status and decision invariants pass
- [x] provider failure/no-data mapping passes
- [x] required-source coverage tests pass
- [x] actual planner outputs match the read-only matrix mirror
- [x] modified planner-output drift is rejected
- [x] returned wrong-company Evidence rejection tests pass
- [x] unselected freshness candidates are not redundantly re-filtered
- [x] explicit-period/FreshnessWindow consistency tests pass
- [x] freshness warning structural/order tests pass
- [x] freshness warning consumption tests pass
- [x] low-relevance mapping tests pass
- [x] blocked versus ordinary clarification tests pass
- [x] malformed public inputs produce sanitized typed errors
- [x] caller mutation and deterministic-output tests pass
- [x] duplicate Evidence remains preserved
- [x] targeted tests pass
- [x] M2 composition regression passes
- [x] full unit regression passes
- [x] import smoke passes
- [x] secret scan passes
- [x] compile passes
- [x] diff review passes
- [x] actual results recorded
- [ ] user reviews implementation result

---

## 18. Approval Request

Requested approval:

- approve this M2-06 final Task Card
- after approval, allow the preflight gate
- allow M2-06 implementation only if every preflight command passes

Not requested:

- commit
- push
- PR
- merge
- deploy
- dependency installation/change
- M2-07 or later implementation

---

## 19. Implementation Result Log

### 19.1 Preflight

- Execution date: `2026-07-24`
- Branch: `main`
- Approved base SHA: `df20eae6457ac852e622b4006084acc16d1220fb`
- HEAD: `df20eae6457ac852e622b4006084acc16d1220fb`
- origin/main: `df20eae6457ac852e622b4006084acc16d1220fb`
- Initial dirty files:
  `M docs/TASK_CARDS/M2-05-freshness.md`;
  `?? docs/TASK_CARDS/M2-06-evidence-policy.md`
- Dirty-tree classification:
  `PASS - only approved M2-05 synchronization and M2-06 plan`
- Destructive Git operation: `NOT_RUN`
- M2-05 Task Card synchronization:
  `PASS - requested SHA/push/review/test/milestone state already present; no further rewrite`
- Interpreter: `C:\Users\USER\Questock\.venv\Scripts\python.exe`
- Python: `3.14.3`
- pytest: `8.4.2`
- `ZoneInfo("Asia/Seoul")`: `PASS - Asia/Seoul`
- Preflight M2-05 targeted:
  `PASS - exit 0 - 88 passed, 1 PytestCacheWarning`
- Preflight M2 composition:
  `PASS - exit 0 - 314 passed, 1 PytestCacheWarning`
- Preflight full unit sandbox run:
  `FAIL - exit 1 - 972 passed, 103 setup errors, 3 warnings`
- Preflight sandbox failure cause:
  `pytest tmp_path setup could not access the user Temp pytest directory`
- Preflight full unit approved local rerun:
  `PASS - exit 0 - 1075 passed, 1 existing StarletteDeprecationWarning`
- Preflight import smoke: `PASS - exit 0 - ok`
- Preflight secret scan: `PASS - exit 0 - []`
- Preflight compile: `PASS - exit 0`
- Dependency installation/change: `NOT_RUN`

### 19.2 Implemented Scope

- Added `app/evidence/policy.py`.
- Added frozen step-local `EvidenceDecision`.
- Added sanitized `EvidencePolicyValidationError`.
- Added strict `EvidencePolicy.evaluate()` public boundary.
- Added exact M2-01 matrix mirror without a runtime planner import.
- Added provider failure/no-data separation.
- Added FreshnessResult warning/source/order and explicit-period validation.
- Added retrieval status, score, and count-aware occurrence validation.
- Added returned-Evidence target-security validation.
- Added required-source and freshness-warning decision mapping.
- Added central output invariants, deep-copy isolation, deterministic ordering,
  and duplicate preservation.
- Added `tests/unit/test_evidence_policy.py`.
- Core models/status, planner, provider, retrieval, normalization, freshness,
  dependency, API/UI/LLM, M2-07, and M2-08 code were not changed.

### 19.3 Final Verification

- Targeted command:
  `.\.venv\Scripts\python.exe -m pytest tests/unit/test_evidence_policy.py -q`
- Targeted result:
  `PASS - exit 0 - 92 passed, 1 PytestCacheWarning`
- M2 composition command:
  `.\.venv\Scripts\python.exe -m pytest tests/unit/test_query_planner.py tests/unit/test_retrieval_filters.py tests/unit/test_retrieval_baseline.py tests/unit/test_evidence_normalization.py tests/unit/test_evidence_freshness.py tests/unit/test_evidence_policy.py -q`
- M2 composition result:
  `PASS - exit 0 - 406 passed, 1 PytestCacheWarning`
- Full unit command:
  `.\.venv\Scripts\python.exe -m pytest tests/unit -q`
- Full unit execution context:
  `approved local rerun because the sandbox cannot access the user Temp pytest directory`
- Full unit result:
  `PASS - exit 0 - 1167 passed, 1 existing StarletteDeprecationWarning`
- Import smoke:
  `PASS - exit 0 - ok`
- Secret scan:
  `PASS - exit 0 - []`
- Explicit untracked-file secret scan:
  `PASS - exit 0 - [] for policy, policy tests, and M2-06 Task Card`
- Compile:
  `PASS - exit 0`
- Diff check:
  `PASS - git diff --check exit 0; no whitespace errors; M2-05 LF-to-CRLF working-copy warning only`
- Explicit trailing-whitespace scan:
  `PASS - rg returned no matches for all four changed files`
- Tracked diff stat:
  `docs/TASK_CARDS/M2-05-freshness.md | 35 lines changed, 23 insertions, 12 deletions`
- Untracked policy stat:
  `app/evidence/policy.py | 759 insertions`
- Untracked test stat:
  `tests/unit/test_evidence_policy.py | 940 insertions`
- Untracked M2-06 Task Card stat:
  `docs/TASK_CARDS/M2-06-evidence-policy.md | 1290 insertions before this result entry`
- Final changed files:
  `M docs/TASK_CARDS/M2-05-freshness.md`;
  `?? app/evidence/policy.py`;
  `?? tests/unit/test_evidence_policy.py`;
  `?? docs/TASK_CARDS/M2-06-evidence-policy.md`
- GitHub CI: `NOT_RUN`
- Independent pytest rerun: `NOT_RUN`
- Production orchestration:
  `NOT_RUN - required before M2 milestone close`
- Actual 365-day provider candidate completeness:
  `NOT_RUN - required before M2 milestone close`
- Live provider/API/UI/LLM: `NOT_RUN - out of scope`
- M2-07 citation validation: `NOT_STARTED`
- M2-08 dedupe/context budget: `NOT_STARTED`
- M1-09:
  `mandatory supplement implemented - final independent review pending`

### 19.4 Git State

- Implementation SHA: `NOT_CREATED`
- Commit: `NOT_RUN`
- Push: `NOT_RUN`
- PR: `NOT_RUN`
- Merge: `NOT_RUN`
- Deploy: `NOT_RUN`
- Current implementation status:
  `IMPLEMENTED LOCALLY - USER REVIEW PENDING`
