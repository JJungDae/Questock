# TASK CARD - M2-07 Citation Validation

## 1. Status and Approval

- Task bundle: `B5: M2-04~08`
- Step: `M2-07 Citation Validation`
- Planning date: `2026-07-24`
- Planning branch: `main`
- Planning base SHA: `a1fb43de8396d253b2350799b932195a9b59266e`
- Planning base commit: `m2-06 conditional pass2 updates`
- Planning base main push: `complete`
- M2-06 first implementation SHA: `45c5203f6c385626ca8a5db8cf8d28a7076f822e`
- M2-06 first implementation commit: `Implement m2-06`
- M2-06 first implementation main push: `complete`
- M2-06 first supplement SHA: `ebb481ae7ec1b749d7907ca59dd0a732211341c1`
- M2-06 first supplement commit: `m2-06 conditional pass updates`
- M2-06 first supplement main push: `complete`
- M2-06 second synchronization SHA: `a1fb43de8396d253b2350799b932195a9b59266e`
- M2-06 total closure review: `PASS - confirmed by total review`
- M2-06 Task Card final closure synchronization: `VERIFY IN PREFLIGHT; UPDATE ONLY IF STILL PENDING`
- M2-07 plan review: `CONDITIONAL PASS`
- M2-07 total re-review: `PASS AFTER REQUIRED API/SCOPE CORRECTIONS IN THIS FILE`
- M2-07 final plan approval: `APPROVED by user on 2026-07-24`
- M2-07 preflight: `PASS`
- M2-07 planning: `ALLOWED`
- M2-07 implementation: `IMPLEMENTED LOCALLY - USER REVIEW PENDING`
- M2-08 dedupe/context budget: `NOT_STARTED`
- M3 claim/answer composition: `NOT_STARTED`
- M1-09:
  `mandatory supplement implemented - final independent review pending`
- Further commit/push/PR/merge/deploy: `NOT_APPROVED`

This Task Card is the corrected final M2-07 implementation plan.

Approval of this plan may authorize only the isolated M2-07 implementation and
its local verification. It does not authorize Git operations, M2-08, M3 claim
generation, answer rendering, live URL checks, provider calls, API/UI/LLM work,
or dependency changes.

---

## 2. Goal

Add a deterministic, in-memory citation validation capability that validates
caller-supplied extractive claims against the exact Evidence sequence selected
for citation.

The boundary will:

- accept caller-supplied extractive claim references
- resolve references only against the supplied `selected_evidence`
- build Citation fields from validated Evidence
- never accept caller-supplied URL, locator, title, or snippet fields
- require an explicit extractive relationship between each claim and every
  cited snippet
- reject unsupported, unknown-Evidence, wrong-company, unsafe-URL, or invalid
  locator references without emitting a partial citation for that claim
- preserve selected Evidence occurrence order and duplicate occurrences
- preserve caller input immutability
- return deterministic, deep-copied citation outputs

M2-07 is not an answer composer and does not prove semantic entailment,
numerical correctness, permission approval, URL availability, or final response
quality.

---

## 3. Development Order and Runtime Order

### 3.1 Development Step order

The project develops capabilities in this order:

```text
M2-06 EvidencePolicy
→ M2-07 citation validation capability
→ M2-08 dedupe/context budget
→ M3 answer/claim generation
```

M2-07 may be implemented now with caller-supplied extractive claims and a caller-
supplied Evidence sequence.

### 3.2 Final runtime consumption order

The future production/runtime order must be:

```text
M2-04 normalize
→ M2-02 hard filter
→ M2-05 freshness
→ M2-03 retrieval
→ M2-06 EvidencePolicy
→ M2-08 final Evidence selection
→ M3 claim generation
→ M2-07 citation validation
→ M3 answer validation/rendering
```

Reasons:

- M2-08 may remove or reorder eligible Evidence under dedupe, source-cap, and
  context-budget rules.
- A citation must not point to Evidence removed from the final context.
- M2-07 claims do not exist until a caller or later M3 claim generator creates
  them.
- M2-07 must therefore accept the final selected Evidence directly rather than
  taking a pre-M2-08 `EvidenceDecision` object.

### 3.3 No false orchestration claim

M2-07 completion proves only:

- its public validation capability works in memory
- current `EvidenceDecision.evidence` can be passed as selected Evidence in a
  capability composition test
- a strict subset can be passed to simulate a later M2-08 result
- unsupported or removed Evidence IDs fail closed

M2-07 completion does not prove:

- production orchestration
- actual M2-08 output
- actual M3 claim generation
- rendered citation click-through
- live URL existence
- permission or external LLM transmission approval

---

## 4. Verified Input Contracts

### 4.1 QueryPlan

M2-07 uses `QueryPlan` only for citation-relevant cross-stage integrity:

- intent
- clarification state
- optional/required security target
- required sources
- financial-term glossary exception

M2-07 must not:

- read the raw query
- reclassify intent
- call the resolver
- reproduce the complete M2-01 planner
- reproduce M2-06 provider/source sufficiency policy

### 4.2 Selected Evidence

`selected_evidence` is the exact sequence the caller intends to expose to claim
generation and citation validation.

During current capability testing:

```python
selected_evidence = decision.evidence
```

During future runtime:

```python
selected_evidence = budget_result.evidence
```

M2-07 does not require or define the future M2-08 result dataclass.

### 4.3 Evidence

The existing `Evidence` model remains unchanged and supplies:

- `evidence_id`
- `document_id`
- `source_type`
- `title`
- optional `source_url`
- optional `published_at`
- `subject_security_ids`
- `mentioned_security_ids`
- `scope`
- `snippet`
- non-empty locator
- retrieval score

### 4.4 Current source producers

Current producer-shaped locators are used for:

- normal acceptance fixtures
- producer-contract drift detection
- cross-field equality tests

M2-07 runtime validity uses only the minimum stable retraceability fields defined
in Section 8. Producer-only descriptive fields must not become permanent
citation requirements unless a later approved contract explicitly promotes them.

---

## 5. Scope

### 5.1 Create

- `app/evidence/citations.py`
- `tests/unit/test_citation_validation.py`
- `docs/TASK_CARDS/M2-07-citation-validation.md`

### 5.2 Modify only if required

- `docs/TASK_CARDS/M2-06-evidence-policy.md`
  - only to synchronize M2-06 final closure `PASS` and M2-07 entry when the
    current GitHub file is still pending
- `docs/TASK_CARDS/M2-07-citation-validation.md`
  - actual implementation and verification result recording

### 5.3 Do not modify

- `app/evidence/__init__.py`
- `app/evidence/policy.py`
- `app/evidence/freshness.py`
- `app/evidence/normalizer.py`
- `app/core/**`
- `app/retrieval/**`
- `app/planning/**`
- `app/providers/**`
- `app/ingest/**`
- `app/api/**`
- `app/llm/**`
- existing fixture/data files
- dependency or lock files
- scripts
- M2-08 or later Task Cards
- M1-09 status

If implementation requires another file, stop and report before expanding scope.

---

## 6. Public API

Create step-local frozen dataclasses and one public function:

```python
@dataclass(frozen=True)
class CitationClaim:
    claim_id: str
    text: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class Citation:
    claim_id: str
    evidence_id: str
    document_id: str
    source_type: str
    title: str
    source_url: str | None
    snippet: str
    locator: Mapping[str, object]


@dataclass(frozen=True)
class CitationRejection:
    claim_id: str
    code: Literal[
        "unknown_evidence",
        "wrong_company",
        "invalid_locator",
        "unsafe_source_url",
        "unsupported_claim",
    ]


@dataclass(frozen=True)
class CitationValidationResult:
    citations: tuple[Citation, ...]
    rejections: tuple[CitationRejection, ...]


class CitationValidationError(ValueError):
    """Raised when public citation-validation input is malformed."""
    ...


def validate_citations(
    claims: Sequence[CitationClaim],
    plan: QueryPlan,
    selected_evidence: Sequence[Evidence],
) -> CitationValidationResult:
    ...
```

Import path:

```python
from app.evidence.citations import (
    Citation,
    CitationClaim,
    CitationRejection,
    CitationValidationError,
    CitationValidationResult,
    validate_citations,
)
```

Do not add root `app.evidence` exports.

---

## 7. Public Input Validation

Apply public structural validation before claim-level rejection semantics.

### 7.1 Claims sequence

- accept a non-string `Sequence[CitationClaim]`
- reject strings, bytes, bytearray, mappings, generators, and scalars
- every item must be an actual `CitationClaim`
- `claim_id` and `text` must be nonblank strings
- normalized text must contain at least one Unicode alphanumeric character
- `evidence_ids` must be a tuple
- it must contain at least one nonblank string
- IDs inside one claim must be unique
- claim IDs across the input sequence must be unique
- malformed public input raises sanitized `CitationValidationError`
- no partial result is returned on structural failure

An empty claims sequence is valid and returns an empty result after plan and
selected-Evidence structural validation.

### 7.2 QueryPlan minimum validation

- require an actual `QueryPlan`
- canonically revalidate its current fields
- require a nonblank supported intent
- `requires_clarification=True` is not citation-capable and requires an empty
  claims sequence
- retrievable non-financial-term intents require a valid supported security
- `financial_term` may have no security or a supported explicit security
- required sources must be unique supported source strings
- selected Evidence source types must appear in `plan.required_sources`
- do not recalculate M2-06 satisfied/missing/no-data/failed source tuples
- do not re-run provider or EvidenceDecision status logic

Supported retrievable intents:

```text
financial_term
recent_issue
disclosure_summary
research_report_summary
risk_factors
multi_source_summary
```

Non-retrieval/clarification plans with nonempty claims are invalid public input.

### 7.3 Selected Evidence sequence

- accept a non-string `Sequence[Evidence]`
- reject strings, bytes, bytearray, mappings, generators, and scalars
- every item must be an actual `Evidence`
- canonically revalidate each Evidence
- preserve occurrence order
- preserve duplicate occurrences
- do not mutate caller Evidence
- every output Citation uses a deep copy of source fields and locator
- an empty Evidence sequence is valid
- claims referencing absent IDs receive `unknown_evidence`

### 7.4 Duplicate Evidence IDs

Multiple occurrences with the same `evidence_id` are allowed only when their
complete canonical payloads are identical.

- identical duplicate occurrences are preserved
- conflicting payloads under one ID are malformed upstream input
- conflicting payloads raise sanitized `CitationValidationError`
- a claim may list one Evidence ID once and receive one Citation for every
  identical selected occurrence with that ID

---

## 8. Minimum Evidence and Locator Contract

### 8.1 Common Evidence fields

Each cited Evidence must have:

- nonblank `evidence_id`
- nonblank `document_id`
- supported nonblank `source_type`
- nonblank `title`
- nonblank `snippet`
- finite `retrieval_score`
- score greater than or equal to the existing M2-03 low-relevance threshold
- structurally valid attribution for its scope
- JSON-safe, path-safe locator

Supported citation sources:

```text
news
disclosure
research_report
glossary
```

### 8.2 QueryPlan target and source guard

For non-`financial_term` plans:

```text
company_specific:
subject_security_ids == [target]

multi_company:
target in subject_security_ids

industry_common:
subject_security_ids is empty
and target in mentioned_security_ids
```

For `financial_term`:

- `glossary` remains a generic source
- generic glossary Evidence is allowed whether plan security is absent or
  explicitly set to Samsung Electronics, SK hynix, or Hyundai Motor
- company target must not be imposed on generic glossary Evidence
- non-glossary Evidence is not accepted for `financial_term`

For every intent:

- Evidence source type must be listed in `plan.required_sources`
- M2-07 does not retrieve another source to satisfy the plan

### 8.3 News minimum runtime locator

Required:

- `provider`: nonblank string
- locator `source_url` must exactly equal `Evidence.source_url`

When `source_url` is present:

- shared URL safety applies

When `source_url` is absent:

- `published_at`: parseable timestamp or canonical timestamp string
- `raw_index`: nonnegative integer and not bool

Current producer fields such as `query` remain required in producer-shaped
acceptance/regression fixtures, but absence of a descriptive query field alone
does not make an otherwise retraceable runtime citation invalid.

### 8.4 Disclosure minimum runtime locator

Required:

- `provider`: nonblank string
- `receipt_no`: 14-digit string
- `viewer_url`: exactly equal to `Evidence.source_url`
- viewer URL exactly:
  `https://dart.fss.or.kr/dsaf001/main.do?rcpNo=<receipt_no>`

Current producer fields such as:

- `corp_code`
- `stock_code`
- `corp_name`
- `report_name`
- `received_date`

must be checked in producer-shaped regression fixtures when present, but they
are not all promoted to permanent citation-validity fields. Company attribution
is validated from Evidence scope/subject/mention fields.

### 8.5 Research report minimum runtime locator

Required:

- `manifest_id`: nonblank string
- `document_id`: exactly equal to `Evidence.document_id`
- `page_basis`: one of:
  - `pdf_1_based`
  - `printed_page`
  - `source_section_only`
- `section`: nonblank string

Page rules:

```text
pdf_1_based or printed_page:
page is a positive integer and not bool

source_section_only:
page is None
```

Source location:

- when `source_url` is present:
  - locator URL equals `Evidence.source_url`
  - shared URL safety applies
- when `source_url` is absent:
  - nonblank opaque `source_asset_id` is required

`publisher` and `access_note` are producer-regression fields, not permanent
runtime citation-validity requirements.

### 8.6 Glossary minimum runtime locator

Required:

- `corpus_id`: nonblank string
- `entry_id`: nonblank string
- `version`: integer and not bool
- `section`: nonblank string
- `source_type`: exactly `glossary`

An approved internal glossary locator may be valid without an external URL.

When a source URL is present:

- locator URL equals `Evidence.source_url`
- shared URL safety applies

Current `provider` and `ingestion_version` values should be verified in producer-
shaped regression tests but need not be duplicated as permanent minimum identity
fields when corpus/entry/version/section already provide stable retraceability.

---

## 9. Recursive Safety and Serialization

### 9.1 Locator structure

Before source-specific validation:

- locator must be a nonempty Mapping
- every mapping key at every depth must be a string
- permitted values:
  - `None`
  - bool
  - int
  - finite float
  - string
  - Mapping
  - list
  - tuple
- reject sets, bytes, bytearray, generators, custom objects, datetime objects
  not explicitly normalized by the source contract, and other non-JSON values
- reject `NaN`, positive infinity, and negative infinity
- recursively inspect nested mappings, lists, and tuples

### 9.2 Path safety

Reject standalone locator values that expose:

- Windows drive absolute paths
- UNC paths
- POSIX absolute paths
- `file://` URLs
- nested variants of the above

Do not misclassify the path component of an otherwise valid `http://` or
`https://` URL as a local filesystem path. URL strings are first validated by
the shared URL contract.

### 9.3 Shared URL safety

Any emitted HTTP(S) URL must:

- use `http` or `https`
- include a hostname
- contain no username or password
- contain no fragment
- use a valid port
- contain no credential-like query key, including normalized separator/case and
  percent-encoded variants protected by existing project safety rules
- contain no control character
- exactly match the corresponding validated locator URL
- be copied from Evidence; never synthesized from IDs

M2-07 does not verify online existence, DNS, redirects, HTTP status, or content.

### 9.4 JSON audit

Run:

```python
json.dumps(value, allow_nan=False)
```

on:

- each validated locator after converting tuples to JSON-equivalent lists for
  audit only
- the complete serialized `CitationValidationResult`

The audit must not mutate the returned object.

### 9.5 Final output audit

After building and deep-copying results, re-audit:

- Citation scalar strings
- Citation locator
- source URL
- rejection codes
- nested values
- JSON serialization
- local path and credential leakage

Expected validation failures become fixed sanitized errors or the documented
claim-level rejection. Unexpected internal exceptions propagate.

---

## 10. Claim Support Contract

Use a deterministic extractive P0 baseline:

1. normalize claim and snippet with Unicode NFKC
2. case-fold
3. collapse whitespace
4. trim leading/trailing whitespace
5. require the normalized claim to be a nonempty contiguous substring of every
   referenced Evidence snippet

Rules:

- title-only overlap is insufficient
- cross-Evidence token union is insufficient
- fuzzy matching is not allowed
- embedding or semantic inference is not allowed
- a claim referring to multiple Evidence IDs must be supported by every one
- if any referenced Evidence fails, emit no Citation for that claim
- numeric/date/unit consistency is deferred to M3
- unsupported paraphrase is rejected even when semantically plausible

---

## 11. Rejection Semantics

For a structurally valid claim, use this precedence:

1. `unknown_evidence`
2. `wrong_company`
3. `invalid_locator`
4. `unsafe_source_url`
5. `unsupported_claim`

Rules:

- at most one rejection per claim
- rejection order follows claim input order
- rejection contains only `claim_id` and fixed project code
- no raw claim text, ID lookup detail, URL, path, secret, locator, exception, or
  provider message is exposed
- any rejected claim emits zero Citation entries
- valid claims are unaffected by other rejected claims

Structural container/dataclass/payload conflicts raise `CitationValidationError`
rather than a semantic rejection.

---

## 12. Mutation, Copying, and Determinism

- do not mutate claims, plan, selected Evidence, locators, or nested values
- result, Citation, Claim, and Rejection containers are frozen dataclasses
- outer result collections are tuples
- Citation locator is a fresh deep copy
- repeated calls with equivalent inputs return equal serialized output
- preserve claim order
- for a valid claim, preserve matching selected Evidence occurrence order
- do not deduplicate Evidence or Citation occurrences
- no clock, random, hash-order, filesystem, registry, corpus, provider, or
  network dependency

---

## 13. Permission and External Processing Boundary

A valid Citation proves only:

- the claim has the defined extractive relationship to the cited snippet
- the selected Evidence has a valid retraceable locator
- URL/locator fields were not fabricated by M2-07
- target-company citation rules passed

A valid Citation does **not** prove:

- report ingestion permission
- redistribution permission
- external LLM processing permission
- `external_llm_processing_allowed=True`
- user-facing click-through success
- ownership or copyright clearance

Report permission remains on the linked original `FinancialDocument` or manifest.
Future M3/LLM orchestration must preserve the document/manifest join and apply
the permission gate separately.

M2-07 does not read, infer, or copy permission metadata into Citation.

---

## 14. Required Tests

Create:

```text
tests/unit/test_citation_validation.py
```

### 14.1 Public structure

- non-sequence claims rejected
- non-Claim item rejected
- blank/punctuation-only claim rejected
- malformed `evidence_ids` rejected
- duplicate claim ID rejected
- duplicate Evidence ID inside one claim rejected
- malformed QueryPlan rejected
- clarification/non-retrieval plan with claims rejected
- malformed selected Evidence sequence rejected
- bypass-created malformed Evidence canonically rejected
- unexpected injected `RuntimeError` propagates
- errors are sanitized and do not expose sentinel text/path/secret

### 14.2 QueryPlan and target rules

- actual QueryPlanner output accepted for every retrievable intent needed by
  this step
- selected source not in `required_sources` rejected
- supported security required for non-financial-term retrievable intents
- `financial_term` without security accepts generic glossary Evidence
- `financial_term` with Samsung security accepts the same generic glossary
  Evidence
- non-glossary Evidence rejected for `financial_term`
- wrong-company company-specific citation rejected
- multi-company target missing rejected
- industry-common target mention accepted
- industry-common target missing rejected

### 14.3 Claim support

- exact substring accepted
- NFKC normalization accepted
- case-fold normalization accepted
- collapsed whitespace accepted
- title-only match rejected
- unsupported paraphrase rejected
- one unsupported Evidence in a multi-Evidence claim rejects the whole claim
- mixed valid and rejected claims preserve deterministic output

### 14.4 Occurrences and selected-Evidence boundary

- identical duplicate Evidence occurrences preserved
- conflicting duplicate payload rejected
- only IDs in selected Evidence are resolvable
- Evidence omitted from selected subset returns `unknown_evidence`
- current `decision.evidence` can be passed directly
- strict subset simulating M2-08 output produces no citation for removed
  Evidence
- no Evidence input plus empty claims returns empty result
- no Evidence input plus referenced claims returns deterministic rejections

### 14.5 Locator and URL

Shared:

- nested non-string key
- nested Windows path
- nested UNC path
- nested POSIX path
- `file://`
- NaN/infinity
- set/bytes/custom object
- malformed URL
- URL username/password
- fragment
- invalid port
- credential-like query key
- percent-encoded credential key
- safe HTTP URL path not misclassified as a local path
- final serialized result audit

News:

- current producer-shaped valid locator
- valid URL citation
- valid URL-less recorded coordinates
- provider missing
- URL mismatch
- invalid published timestamp
- negative/bool raw index
- producer regression checks query when present without promoting it to the
  minimum runtime contract

Disclosure:

- current producer-shaped valid locator
- official receipt/viewer citation
- malformed receipt
- viewer mismatch
- arbitrary fixture URL
- producer descriptive fields preserved in regression fixtures but not required
  by the minimum validator

Research report:

- current producer-shaped URL locator
- current producer-shaped opaque-asset locator
- document ID mismatch
- blank manifest/section
- all page-basis boundaries
- bool/zero/negative page
- missing both URL and asset
- publisher/access note drift checked in producer fixture tests, but omission
  alone does not invalidate the minimum runtime locator

Glossary:

- current producer-shaped internal locator
- no-URL internal locator
- version bool rejected
- source type mismatch
- optional URL mismatch
- minimum corpus/entry/version/section/source identity accepted

### 14.6 Copy and determinism

- returned locator is deep copied
- nested result mutation cannot affect input or later calls
- input claims, plan, Evidence, lists, and locators unchanged
- repeated calls equal
- tuple outputs fresh
- no I/O, clock, registry, or network access

### 14.7 Capability composition

Use real public functions in memory:

```text
QueryPlanner.plan
→ normalize_financial_documents
→ filter_evidence
→ evaluate_freshness
→ retrieve_evidence
→ EvidencePolicy.evaluate
→ selected_evidence = decision.evidence
→ caller-supplied extractive CitationClaim
→ validate_citations
```

Assert:

- supported single-company recent-news plan
- wrong-company Evidence removed before policy
- stale Evidence removed before retrieval
- policy decision complete
- selected Evidence passed explicitly
- one exact extractive claim
- code-built Citation fields match selected Evidence
- all previous inputs remain unchanged
- this is capability composition, not production orchestration

Add a second selected-subset test:

```text
decision.evidence has multiple valid occurrences
→ selected_evidence is a strict subset
→ claim referencing retained Evidence succeeds
→ claim referencing removed Evidence receives unknown_evidence
```

This simulates the future M2-08-to-M2-07 boundary without implementing M2-08.

---

## 15. Required Preflight

Run from repository root after user approval and before code changes.

### 15.1 Git baseline

```powershell
git status --short
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
git log -2 --oneline --decorate
```

Expected:

```text
branch = main
HEAD = a1fb43de8396d253b2350799b932195a9b59266e
origin/main = a1fb43de8396d253b2350799b932195a9b59266e
latest commit = m2-06 conditional pass2 updates
```

Allowed initial dirty files:

- approved M2-07 final plan
- M2-06 Task Card final closure synchronization, only if still pending

Unexpected code, fixture, dependency, data, unrelated Task Card, or user files
require a stop report.

Do not use:

- reset
- restore
- checkout to discard files
- clean
- stash
- force push
- history rewrite

### 15.2 M2-06 closure synchronization

Inspect:

```text
docs/TASK_CARDS/M2-06-evidence-policy.md
```

Expected minimum final state:

```text
M2-06 final closure review: PASS
M2-06 targeted: 93 passed
M2 composition: 407 passed
full unit: 1168 passed
GitHub CI: NOT_RUN
Independent pytest rerun: NOT_RUN
M2-07 planning: ALLOWED
M2-07 implementation: ALLOWED after approved plan and preflight PASS
Further commit/push/PR/merge/deploy: NOT_APPROVED
```

If already accurate, do not rewrite.

If still pending, synchronize only the final closure and M2-07 entry. Do not
modify M2-06 policy code or tests.

### 15.3 Existing environment smoke

Use only the existing local interpreter:

```powershell
$python = ".\.venv\Scripts\python.exe"

& $python --version
& $python -m pytest --version
& $python -c "from zoneinfo import ZoneInfo; print(ZoneInfo('Asia/Seoul'))"
```

Do not install or change dependencies during M2-07.

### 15.4 Regression preflight

```powershell
& $python -m pytest tests/unit/test_evidence_policy.py -q
& $python -m pytest tests/unit/test_query_planner.py tests/unit/test_retrieval_filters.py tests/unit/test_retrieval_baseline.py tests/unit/test_evidence_normalization.py tests/unit/test_evidence_freshness.py tests/unit/test_evidence_policy.py -q
& $python -m pytest tests/unit -q
& $python -c "from app.evidence.policy import EvidenceDecision, EvidencePolicy, EvidencePolicyValidationError; print('ok')"
& $python scripts/secret_scan.py
& $python -m compileall app tests scripts -q
git diff --check
git status --short
```

Historical expected records:

```text
M2-06 targeted: 93 passed
M2 composition: 407 passed
full unit: 1168 passed
```

Actual current preflight results must be recorded separately.

If any command fails, stop before M2-07 code changes.

---

## 16. Implementation Order

1. Confirm latest main and working-tree scope.
2. Verify or minimally synchronize M2-06 final closure.
3. Run interpreter, pytest, ZoneInfo, regression, smoke, secret scan, and compile
   preflight.
4. Create final M2-07 Task Card from this approved plan.
5. Add frozen public dataclasses and sanitized exception.
6. Implement claims, QueryPlan-minimum, and selected-Evidence validation.
7. Implement duplicate occurrence/payload validation.
8. Implement target and source eligibility.
9. Implement recursive locator, URL, JSON, and final-output safety.
10. Implement minimum source-specific locator contracts.
11. Implement extractive support and rejection precedence.
12. Implement deep-copied deterministic output.
13. Add targeted tests.
14. Add current capability composition test.
15. Add strict-selected-subset simulation test.
16. Run all verification commands.
17. Record only actual results and limitations.
18. Report diff and wait for separate Git approval.

---

## 17. Verification Commands

```powershell
$python = ".\.venv\Scripts\python.exe"

& $python -m pytest tests/unit/test_citation_validation.py -q
& $python -m pytest tests/unit/test_evidence_policy.py tests/unit/test_citation_validation.py -q
& $python -m pytest tests/unit/test_query_planner.py tests/unit/test_retrieval_filters.py tests/unit/test_retrieval_baseline.py tests/unit/test_evidence_normalization.py tests/unit/test_evidence_freshness.py tests/unit/test_evidence_policy.py tests/unit/test_citation_validation.py -q
& $python -m pytest tests/unit -q
& $python -c "from app.evidence.citations import Citation, CitationClaim, CitationRejection, CitationValidationError, CitationValidationResult, validate_citations; print('ok')"
& $python -c "from zoneinfo import ZoneInfo; print(ZoneInfo('Asia/Seoul'))"
& $python scripts/secret_scan.py
& $python -m compileall app tests scripts -q
git diff --check
git diff --name-status
git diff --stat
git status --short
git log -2 --oneline --decorate
```

Record:

- exact command
- interpreter
- Python/pytest version
- exit code
- passed count
- warning
- approved local rerun context
- initial failure and corrected rerun
- changed files
- GitHub CI state
- independent rerun state
- Git operation state

Do not describe local or fixture tests as live verification, GitHub CI, M2-08
integration, M3 claim integration, or production orchestration.

---

## 18. Completion Criteria

### Planning

- [x] latest main SHA fixed
- [x] M2-06 closure disposition fixed
- [x] development order and runtime order separated
- [x] public API takes final selected Evidence directly
- [x] EvidenceDecision policy reimplementation removed
- [x] QueryPlan validation limited to citation-relevant integrity
- [x] locator runtime contract reduced to minimum retraceability
- [x] producer-shaped fixtures retained for drift detection
- [x] nested/JSON/final-output safety fixed
- [x] financial-term optional security fixed
- [x] permission non-approval boundary fixed
- [x] M2-08 and M3 non-completion boundary fixed
- [x] user approves this final plan

### Implementation

- [x] M2-06 final closure synchronized if required
- [x] preflight passes
- [x] only approved files changed
- [x] public API implemented exactly
- [x] selected-Evidence boundary implemented
- [x] minimum QueryPlan integrity implemented
- [x] source/target guards implemented
- [x] duplicate occurrences preserved
- [x] conflicting duplicate payload fails
- [x] extractive support implemented
- [x] all-or-nothing claim output implemented
- [x] minimum source locators implemented
- [x] producer regression fixtures pass
- [x] nested locator safety passes
- [x] final JSON audit passes
- [x] permission remains unimplemented and unclaimed
- [x] current capability composition passes
- [x] selected-subset simulation passes
- [x] targeted tests pass
- [x] M2 regression passes
- [x] full unit regression passes
- [x] import/ZoneInfo smoke passes
- [x] secret scan passes
- [x] compile passes
- [x] diff review passes
- [x] actual results recorded
- [x] commit/push/PR/merge/deploy remain NOT_RUN

---

## 19. Required Before M2 Milestone Close

M2-07 isolated completion does not close the M2 Gate.

Required later:

1. M2-08 dedupe, source cap, and context budget.
2. A phase slice that passes final selected Evidence into claim generation.
3. M3 claim generation followed by M2-07 citation validation.
4. Answer validation and citation rendering.
5. Actual click-through/live URL verification where approved.
6. Permission gate using original document/manifest joins.
7. Production orchestration.
8. Actual 365-day disclosure candidate acquisition.

Until those are demonstrated, describe M2-07 as an in-memory extractive citation
validation capability, not a completed user-facing citation pipeline.

---

## 20. Stop Conditions

Stop and report if:

- main SHA differs from the approved base
- M2-06 closure cannot be synchronized safely
- preflight fails
- unexpected dirty files exist
- core models or status enums must change
- M2-06 policy code must change
- M2-08 implementation becomes necessary
- M3 claim/answer implementation becomes necessary
- source minimum locator cannot support current producer outputs
- online URL checks or a new dependency become necessary
- semantic entailment becomes necessary
- permission must be inferred inside M2-07
- more than the allowed new files plus conditional M2-06 Task Card sync are
  required
- raw URL, secret, path, metadata, or exception text could enter a public error

Do not silently:

- accept pre-M2-08 Evidence as guaranteed final runtime Evidence
- reconstruct an EvidenceDecision
- re-run provider/source sufficiency policy
- promote every producer descriptive field to a permanent locator schema
- treat Citation validity as external-processing permission
- synthesize a URL
- perform network or filesystem I/O
- remove duplicate Evidence occurrences
- implement M2-08 or M3

---

## 21. Risks and Fallback

| Risk | Control | Fallback |
|---|---|---|
| citation references Evidence removed by budget | explicit `selected_evidence` input | unknown Evidence rejection |
| wrong-company citation | exact plan target/scope guard | reject claim |
| unsupported claim | normalized contiguous substring | reject claim; M3 may remove/weaken |
| unusable locator | minimum stable source contract | reject claim |
| fake/unsafe URL | copy only validated Evidence URL | locator-only result or rejection |
| producer drift | producer-shaped regression tests | stop and report contract difference |
| nested unsafe data | recursive/JSON/final-output audit | sanitized failure |
| duplicate occurrence loss | preserve selected occurrence order | no dedupe in M2-07 |
| permission confusion | explicit non-approval boundary | M3 applies original document join |
| semantic overclaim | label as extractive baseline | defer entailment |

Rollback after a future approved implementation is limited to the new M2-07
module/tests, the M2-07 Task Card result section, and any approved M2-06 closure
synchronization. Rollback requires separate user approval and non-destructive Git
operations.

---

## 22. Known Deferred Limits

- M2-08 dedupe/context budget: `NOT_STARTED`
- M3 claim generation: `NOT_STARTED`
- M3 answer validation/rendering: `NOT_STARTED`
- semantic paraphrase/entailment: `NOT_IMPLEMENTED`
- numeric/date/unit claim validation: `NOT_IMPLEMENTED`
- permission gate: `NOT_IMPLEMENTED - M3/orchestration`
- live URL existence/click-through: `NOT_RUN`
- production orchestration: `NOT_RUN`
- actual 365-day disclosure candidate completeness: `NOT_RUN`
- GitHub CI: `NOT_RUN`
- independent pytest rerun: `NOT_RUN`
- Windows clean-build `tzdata` declaration: `DEFERRED`
- M1-09:
  `mandatory supplement implemented - final independent review pending`

---

## 23. Result Log

- Planning base SHA: `a1fb43de8396d253b2350799b932195a9b59266e`
- Planning base commit: `m2-06 conditional pass2 updates`
- M2-06 final closure synchronization:
  `PASS - Task Card records total closure PASS and M2-07 implementation gate`
- Git baseline:
  `PASS - main; HEAD and origin/main a1fb43de8396d253b2350799b932195a9b59266e`
- Initial dirty scope:
  `M docs/TASK_CARDS/M2-07-citation-validation.md - approved corrected plan only`
- Destructive Git operation: `NOT_RUN`
- Interpreter: `C:\Users\USER\Questock\.venv\Scripts\python.exe`
- Interpreter smoke: `PASS - exit 0 - Python 3.14.3`
- Pytest smoke: `PASS - exit 0 - pytest 8.4.2`
- ZoneInfo smoke: `PASS - exit 0 - Asia/Seoul`
- Preflight M2-06 targeted:
  `PASS - exit 0 - 93 passed, 1 PytestCacheWarning`
- Preflight M2 composition:
  `PASS - exit 0 - 407 passed, 1 PytestCacheWarning`
- Preflight full unit:
  `PASS - exit 0 - 1168 passed, 1 existing StarletteDeprecationWarning`
- Preflight full unit execution context:
  `approved local execution because sandbox cannot access the user Temp pytest directory`
- Preflight import smoke: `PASS - exit 0 - ok`
- Preflight secret scan: `PASS - exit 0 - []`
- Preflight compile: `PASS - exit 0`
- Preflight diff check:
  `PASS - exit 0 - no whitespace errors; LF-to-CRLF working-copy warnings`
- M2-07 implementation:
  `IMPLEMENTED LOCALLY - USER REVIEW PENDING`
- Added `app/evidence/citations.py`.
- Added `tests/unit/test_citation_validation.py`.
- Added frozen Citation input/output/rejection/result dataclasses.
- Added selected-Evidence-only resolution, duplicate occurrence preservation,
  target/source guards, source-specific locator validation, recursive safety,
  exact extractive support, code-built deep-copy output, and sanitized errors.
- Initial targeted pytest:
  `FAIL - exit 1 - 106 passed, 5 failed, 2 PytestCacheWarnings`
- Initial targeted failure cause:
  `five path fixtures were rejected by the existing Evidence model before the M2-07 public boundary`
- Initial targeted correction:
  `tests now assert sanitized canonical-revalidation errors for bypass-mutated local paths; no core model change`
- Final targeted command:
  `.\.venv\Scripts\python.exe -m pytest tests/unit/test_citation_validation.py -q`
- Final targeted pytest:
  `PASS - exit 0 - 118 passed, 1 PytestCacheWarning`
- Policy/citation command:
  `.\.venv\Scripts\python.exe -m pytest tests/unit/test_evidence_policy.py tests/unit/test_citation_validation.py -q`
- Policy/citation regression:
  `PASS - exit 0 - 211 passed, 1 PytestCacheWarning`
- M2-01~07 command:
  `.\.venv\Scripts\python.exe -m pytest tests/unit/test_query_planner.py tests/unit/test_retrieval_filters.py tests/unit/test_retrieval_baseline.py tests/unit/test_evidence_normalization.py tests/unit/test_evidence_freshness.py tests/unit/test_evidence_policy.py tests/unit/test_citation_validation.py -q`
- M2-01~07 regression:
  `PASS - exit 0 - 525 passed, 1 PytestCacheWarning`
- Full unit command:
  `.\.venv\Scripts\python.exe -m pytest tests/unit -q`
- Full unit regression:
  `PASS - exit 0 - 1286 passed, 1 existing StarletteDeprecationWarning`
- Full unit execution context:
  `approved local execution because sandbox cannot access the user Temp pytest directory`
- Import smoke: `PASS - exit 0 - ok`
- Final ZoneInfo smoke: `PASS - exit 0 - Asia/Seoul`
- Secret scan: `PASS - exit 0 - []`
- Explicit untracked module/test secret scan: `PASS - exit 0 - []`
- Compile: `PASS - exit 0`
- Diff review:
  `PASS - only approved M2-06/M2-07 Task Cards and new M2-07 module/tests changed`
- Tracked diff stat:
  `2 Task Cards - 1068 insertions, 412 deletions; includes the user-supplied corrected final plan`
- New module size: `app/evidence/citations.py - 661 raw lines`
- New test size: `tests/unit/test_citation_validation.py - 1075 raw lines`
- Final changed files:
  `M docs/TASK_CARDS/M2-06-evidence-policy.md`;
  `M docs/TASK_CARDS/M2-07-citation-validation.md`;
  `?? app/evidence/citations.py`;
  `?? tests/unit/test_citation_validation.py`
- GitHub CI: `NOT_RUN`
- Independent pytest rerun: `NOT_RUN`
- Live URL/permission/M2-08/M3/production orchestration: `NOT_RUN`
- Commit/push/PR/merge/deploy: `NOT_RUN`

---

## 24. Approval Request

Requested:

- approval of this corrected final M2-07 plan
- permission to run the existing-environment preflight
- permission to implement only M2-07 when every preflight command passes
- permission to update M2-06 Task Card closure state only when it remains stale

Not requested:

- dependency installation or change
- commit
- push
- PR
- merge
- deploy
- live URL/API calls
- provider/ingest changes
- M2-08 implementation
- M3 claim/answer implementation
- API/UI/LLM work
