# TASK CARD - M2-07 Citation Validation

## 1. Status and Approval

- Task bundle: `B5: M2-04~08`
- Step: `M2-07 Citation Validation`
- Planning date: `2026-07-24`
- Planning branch: `main`
- Planning base SHA: `ebb481ae7ec1b749d7907ca59dd0a732211341c1`
- Planning base commit: `m2-06 conditional pass updates`
- Planning base main push: `complete`
- M2-06 required supplement: `implemented and pushed`
- M2-06 final closure review: `PENDING`
- M2-07 planning: `ALLOWED`
- M2-07 implementation:
  `BLOCKED - M2-06 final closure PASS, M2-07 plan approval, and preflight PASS required`
- M1-09:
  `mandatory supplement implemented - final independent review pending`
- Further commit/push/PR/merge/deploy: `NOT_APPROVED`

This Task Card is a plan only. It does not mark M2-06 complete and does not
authorize M2-07 implementation or any Git operation.

---

## 2. Goal

Add a deterministic, in-memory citation validation boundary after
`EvidencePolicy` and before M2-08 context budgeting or any M3 answer
composition.

The boundary will:

- accept caller-supplied extractive claim references
- resolve every reference only against Evidence returned by the supplied
  `EvidenceDecision`
- build citation fields from validated Evidence rather than accepting a
  caller-supplied URL, locator, title, or snippet
- require an explicit relation between each claim and every cited snippet
- reject unsupported, unknown-Evidence, wrong-company, unsafe-URL, or invalid
  locator references without emitting a citation for that claim
- preserve deterministic order, duplicate Evidence occurrences, and caller
  input immutability

M2-07 is not an answer composer and does not prove broad semantic entailment.
Its P0 support rule is deliberately extractive and fail-closed.

---

## 3. Verified Current Contracts

### 3.1 Existing pipeline boundary

The verified M2 order is:

```text
M2-04 normalize FinancialDocument to Evidence
-> M2-02 hard filter
-> M2-05 freshness
-> M2-03 lexical retrieval
-> M2-06 EvidencePolicy
-> M2-07 citation validation
-> M2-08 dedupe/context budget
```

`EvidencePolicy.evaluate()` returns a frozen step-local `EvidenceDecision` with:

- `status`
- ordered Evidence tuple
- ordered freshness warnings
- satisfied, missing, no-data, and failed source tuples

`complete` and `partial` are the only statuses that may carry Evidence.
`provider_failed`, `no_evidence`, and `blocked` carry no Evidence.

### 3.2 Existing Evidence contract

The existing `Evidence` model already carries:

- `evidence_id`
- `document_id`
- `source_type`
- `title`
- optional `source_url`
- optional timezone-aware `published_at`
- subject and mentioned security IDs
- `scope`
- `snippet`
- non-empty locator mapping
- optional retrieval score

M2-07 must not change `Evidence`, `FinancialDocument`, `FinancialAnswer`,
`EvidenceDecision`, or any status enum.

### 3.3 Verified source locator shapes

| Source | Current locator evidence | M2-07 minimum provenance check |
|---|---|---|
| `news` | provider, source URL or recorded response coordinates, published time, raw index, query | provider and recorded coordinates must be internally consistent; any URL must equal the Evidence URL |
| `disclosure` | provider, receipt number, official viewer URL, company and report fields | receipt number and viewer URL must agree with each other and the Evidence URL |
| `research_report` | manifest ID, document ID, page/page basis, section, source URL or opaque source asset ID | document ID must match; page contract and source locator must be valid |
| `glossary` | corpus ID, entry ID, version, section, source/provider/ingestion identity, optional URL or asset ID | corpus entry identity and section must form a stable internal locator |

Live URL existence is not verified in M2-07. “No fake URL” means M2-07 never
accepts a caller-supplied citation URL and never synthesizes one; any emitted
URL must be a structurally safe URL copied from Evidence and must agree with its
source locator.

### 3.4 Evaluation and risk contract

- Project completion criteria: claim/snippet relationship, locator existence,
  zero fabricated URLs, and zero wrong-company citations.
- Evaluation taxonomy `citation_support`: source URL or locator, related
  snippet, correct page/section, and correct Evidence subject.
- Active risks:
  - `R25` wrong-company evidence/citation
  - `R29` citation does not support the claim
  - `R45` source cannot be located from citation detail
- `R29` fallback: remove the unsupported claim or weaken the later answer.
  M2-07 implements the validation signal only; M3 owns answer rewriting.

---

## 4. Scope

### 4.1 Planned files

Create:

- `app/evidence/citations.py`
- `tests/unit/test_citation_validation.py`
- `docs/TASK_CARDS/M2-07-citation-validation.md`

Modify only for factual result recording after approved implementation:

- `docs/TASK_CARDS/M2-07-citation-validation.md`

Do not modify `app/evidence/__init__.py`; the initial import path will be
`app.evidence.citations`.

### 4.2 Explicit exclusions

Do not modify or implement:

- `app/core/models.py`
- `app/core/status.py`
- `app/evidence/policy.py`
- M2-02 through M2-05 code
- providers, ingest, resolver, planner, retrieval, or freshness
- Evidence normalization or attribution
- Evidence dedupe, source caps, token counting, or context budget
- `FinancialAnswer`, AnswerComposer, AnswerValidator, or ChatService
- API, UI, LLM, LiteLLM, Gemini, or live HTTP
- numeric/date/unit claim validation
- paraphrase or semantic-entailment models
- online URL existence checks, DNS, HEAD, or GET requests
- M2-08 or later implementation
- dependency changes

---

## 5. Planned Public API

Implement step-local frozen dataclasses and one public function:

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
    ...


def validate_citations(
    claims: Sequence[CitationClaim],
    plan: QueryPlan,
    decision: EvidenceDecision,
) -> CitationValidationResult:
    ...
```

The implementation may use equivalent private helpers but must preserve these
public meanings. New project-wide models or enums are not allowed.

---

## 6. Input and Output Invariants

### 6.1 Public input validation

- `claims` must be a non-string sequence.
- Every item must be an actual `CitationClaim`.
- `claim_id` and `text` must be non-blank strings.
- Normalized claim text must contain at least one Unicode alphanumeric
  character; punctuation-only text is invalid.
- `evidence_ids` must be a non-empty tuple of non-blank strings.
- Claim IDs must be unique.
- Evidence IDs within one claim must be unique.
- `plan` must be an actual `QueryPlan`.
- `decision` must be an actual `EvidenceDecision`.
- Directly constructed malformed dataclasses must produce only
  `CitationValidationError` with a fixed sanitized message.
- Raw claim text, URLs, local paths, secrets, Pydantic details, and nested
  exception text must not appear in errors.

### 6.2 Decision boundary

- Citation lookup uses only `decision.evidence`.
- No provider result, corpus, global registry, or live source may add Evidence.
- `complete` and `partial` require at least one claim for citation validation.
- `provider_failed`, `no_evidence`, and `blocked` accept only an empty claim
  sequence and produce empty citations and rejections.
- A claim rejected for any reason emits no partial citations.
- A valid claim emits one code-built Citation per matching Evidence occurrence,
  in claim order and then decision Evidence order.
- Duplicate Evidence occurrences are not removed or reordered in M2-07.
- Conflicting payloads under one duplicated `evidence_id` are malformed
  upstream input and fail with sanitized `CitationValidationError`.

### 6.3 Claim-to-snippet support

Use a deterministic extractive baseline:

1. normalize claim and snippet with NFKC
2. case-fold
3. collapse whitespace
4. require the normalized claim to be a non-empty contiguous substring of
   every cited Evidence snippet

Title-only overlap is insufficient. Cross-Evidence token union, fuzzy matching,
embeddings, reranking, or semantic inference is not allowed.

This intentionally rejects unsupported paraphrases. M3 may remove or weaken the
claim but must not bypass this M2-07 result.

### 6.4 Evidence and security eligibility

Each cited Evidence must:

- have a non-blank ID, document ID, source type, title, and snippet
- use one of `news`, `disclosure`, `research_report`, or `glossary`
- have a finite retrieval score at or above the M2-03 threshold when carried
  by `complete` or `partial`
- satisfy the QueryPlan target rule:
  - `company_specific`: exact target as the sole subject
  - `multi_company`: target included in subjects
  - `industry_common`: no subjects and target included in mentions
- use `glossary` without a company target only for the existing
  `financial_term` plan

M2-07 validates only Evidence selected by M2-06 and does not refilter or rescore
the corpus.

---

## 7. Source and Locator Validation

### 7.1 Shared URL safety

Any emitted URL must:

- use HTTP or HTTPS
- include a hostname
- contain no username or password
- contain no fragment
- have a valid port
- contain no credential-like query key, including case, separator, and
  percent-encoded variants already protected elsewhere in the project
- contain no local absolute path or `file://` reference
- equal the corresponding URL field in the Evidence locator

M2-07 copies the URL from Evidence after validation. It never accepts a URL from
`CitationClaim` and never derives one from an ID.

### 7.2 News

- `provider` must be a non-blank string.
- Locator `source_url` must exactly equal `Evidence.source_url`.
- With a URL, shared URL safety applies.
- Without a URL, the existing recorded locator must include a parseable
  published timestamp, non-negative integer raw index, and non-blank query.
- A URL-less citation remains a recorded locator citation and must not be
  described as a live or clickable origin URL.

### 7.3 Disclosure

- `receipt_no` must be a 14-digit string.
- `viewer_url` must equal `Evidence.source_url`.
- The viewer URL must exactly equal
  `https://dart.fss.or.kr/dsaf001/main.do?rcpNo=<receipt_no>`.
- Fixture-supplied arbitrary URLs must never be emitted.

### 7.4 Research report

- Locator `document_id` must equal `Evidence.document_id`.
- `manifest_id` and `section` must be non-blank.
- `pdf_1_based` and `printed_page` require a positive integer page; bool is
  rejected.
- `source_section_only` requires `page is None`.
- `source_url`, when present, must equal `Evidence.source_url` and pass shared
  URL safety.
- If `source_url` is absent, a non-blank opaque `source_asset_id` is required.
- Local filesystem paths must never be accepted as source assets or locators.

### 7.5 Glossary

- `corpus_id`, `entry_id`, `section`, `source_type`, `provider`, and
  `ingestion_version` must be non-blank.
- `version` must be an integer and must not be a bool.
- Locator `source_type` must be `glossary`.
- Optional source URL must equal `Evidence.source_url` and pass shared URL
  safety.
- A reviewed internal glossary entry may use the stable
  corpus/entry/version/section locator without an external URL.

---

## 8. Rejection Semantics

For a structurally valid claim, apply this fixed precedence:

1. `unknown_evidence`
2. `wrong_company`
3. `invalid_locator`
4. `unsafe_source_url`
5. `unsupported_claim`

Emit at most one rejection per claim. Rejection order follows claim input
order. Rejection codes are fixed project-owned literals; no raw message is
returned.

Malformed public containers, malformed dataclasses, inconsistent duplicate
Evidence IDs, or impossible decision/status combinations raise
`CitationValidationError` instead of returning a semantic rejection.

---

## 9. Mutation and Determinism

- Do not mutate claims, plan, decision, Evidence, locator, or nested values.
- Citation locator values must be deep copies.
- Repeated calls with equivalent inputs must return equal results.
- Preserve claim order.
- Preserve Evidence occurrence order within each claim.
- Do not deduplicate Evidence or citations.
- Do not use current time, random values, Python hash, filesystem state, or
  network state.

---

## 10. Test Plan

### 10.1 Targeted unit tests

Add tests for:

- valid news citation with code-built URL and locator
- valid URL-less recorded news locator
- valid official disclosure receipt/viewer citation
- valid research report URL locator
- valid research report opaque asset locator
- valid glossary internal locator
- NFKC, case-fold, and whitespace-normalized extractive support
- title-only match rejected as `unsupported_claim`
- unsupported paraphrase rejected
- unknown Evidence ID rejected
- wrong-company `company_specific` rejected
- target absent from `multi_company` subjects rejected
- target present only as the correct `industry_common` mention accepted
- caller-supplied citation URL impossible by public schema
- mismatched locator/Evidence URL rejected
- disclosure receipt/viewer mismatch rejected
- report document ID mismatch rejected
- all report page-basis boundaries
- malformed and unsafe URL variants
- credential query keys and percent-encoded key variants
- missing/blank/source-incompatible locators
- duplicate claim ID and duplicate claim Evidence ID failure
- duplicate Evidence occurrences preserved
- conflicting duplicate Evidence payload failure
- mixed valid/rejected claims with all-or-nothing claim output
- no-Evidence decision with empty claims
- no-Evidence decision with claims rejected as malformed/inconsistent input
- direct dataclass malformed scalar/container types
- deep nested locator mutation isolation
- deterministic repeated output
- fixed sanitized errors without sentinel secret or local path leakage

### 10.2 Cross-stage composition

Use actual public functions in-memory:

```text
QueryPlanner.plan
-> normalize_financial_documents
-> filter_evidence
-> evaluate_freshness
-> retrieve_evidence
-> EvidencePolicy.evaluate
-> validate_citations
```

The composition test must assert:

- supported single-company recent-news plan
- wrong-company and stale Evidence absent before citation validation
- final policy decision `complete`
- one exact extractive claim
- citation uses only the selected target Evidence
- citation URL/locator/title/snippet are copied from Evidence
- all prior-stage inputs remain unchanged
- duplicate removal, production orchestration, live URL existence, and answer
  composition are not claimed

### 10.3 Regression

Run M2-01 through M2-07 unit coverage and the full unit suite. Existing M2-06
absent-from-freshness and public composition tests must remain unchanged and
passing.

---

## 11. Preflight Gate

Implementation may begin only after:

1. the user records M2-06 final closure review `PASS`
2. the user approves this M2-07 plan
3. HEAD and `origin/main` are confirmed at the approved implementation base
4. the working tree contains only approved Task Card planning changes
5. all commands below pass

Use the existing local environment without installing dependencies:

```powershell
$python = ".\.venv\Scripts\python.exe"

& $python -m pytest tests/unit/test_evidence_policy.py -q
& $python -m pytest tests/unit/test_query_planner.py tests/unit/test_retrieval_filters.py tests/unit/test_retrieval_baseline.py tests/unit/test_evidence_normalization.py tests/unit/test_evidence_freshness.py tests/unit/test_evidence_policy.py -q
& $python -m pytest tests/unit -q
& $python -c "from app.evidence.policy import EvidenceDecision, EvidencePolicy, EvidencePolicyValidationError; print('ok')"
& $python scripts/secret_scan.py
& $python -m compileall app tests scripts -q
git diff --check
git status --short
```

Expected current regression baseline from the M2-06 supplement:

- M2-06 targeted: `93 passed`
- M2 composition: `407 passed`
- full unit: `1168 passed`

These are historical local results, not a claim about the future preflight,
independent pytest, or GitHub CI.

If any preflight command fails, stop before M2-07 code changes and report the
failure.

---

## 12. Implementation Order

After all gates pass:

1. Add frozen step-local input/output dataclasses and sanitized exception.
2. Add strict canonical validation for public containers and direct
   dataclasses.
3. Validate EvidenceDecision status/evidence shape without changing policy.
4. Resolve claim Evidence IDs against decision Evidence occurrences.
5. Apply target-security eligibility.
6. Apply source-specific locator and URL checks.
7. Apply exact extractive claim/snippet support.
8. Build deep-copied code-owned Citation outputs.
9. Add targeted and cross-stage composition tests.
10. Run targeted, M2 regression, full unit, smoke, secret scan, compile, and
    diff review.
11. Record only actual results in this Task Card.
12. Report diff and verification results without commit or push.

---

## 13. Verification Commands

```powershell
$python = ".\.venv\Scripts\python.exe"

& $python -m pytest tests/unit/test_citation_validation.py -q
& $python -m pytest tests/unit/test_evidence_policy.py tests/unit/test_citation_validation.py -q
& $python -m pytest tests/unit/test_query_planner.py tests/unit/test_retrieval_filters.py tests/unit/test_retrieval_baseline.py tests/unit/test_evidence_normalization.py tests/unit/test_evidence_freshness.py tests/unit/test_evidence_policy.py tests/unit/test_citation_validation.py -q
& $python -m pytest tests/unit -q
& $python -c "from app.evidence.citations import Citation, CitationClaim, CitationRejection, CitationValidationError, CitationValidationResult, validate_citations; print('ok')"
& $python scripts/secret_scan.py
& $python -m compileall app tests scripts -q
git diff --check
git diff --name-status
git diff --stat
git status --short
```

Record each command, exit code, passed count, warnings, and execution context.
Do not describe local or fixture results as GitHub CI, live URL verification, or
production orchestration success.

---

## 14. Stop Conditions

Stop and report before expanding scope if:

- M2-06 closure is not `PASS`
- preflight fails
- a core model or status enum change appears necessary
- EvidencePolicy must be rewritten
- current source locator shapes differ from this Task Card
- valid citation support requires an online request or new dependency
- claim support cannot be implemented without semantic inference
- M2-08 dedupe/context budget becomes necessary
- AnswerComposer, AnswerValidator, API, UI, or LLM code becomes necessary
- a raw URL, secret, credential, local path, or nested exception could enter a
  public error
- more than the three planned files require modification

Report the problem, verified evidence, smallest correction, alternatives, and
test/schedule impact.

---

## 15. Risks and Fallback

| Risk | Control | Fallback |
|---|---|---|
| R25 wrong-company citation | exact Evidence scope/target check | reject the claim |
| R29 unsupported citation | exact normalized claim substring in every cited snippet | reject the claim; M3 may remove/weaken it |
| R45 unusable locator | source-specific required fields and cross-field checks | omit citation and retain rejection |
| fabricated URL | build URL only from validated Evidence | locator-only citation or rejection |
| malformed public input | strict revalidation and sanitized typed error | fail closed |
| caller mutation | deep-copy output locator and immutable tuples | reject non-copyable unsafe input |
| accidental M2-08 work | preserve duplicates and order | defer dedupe/budget |
| no semantic entailment | label as extractive baseline | do not claim paraphrase support |

Rollback after approved implementation is limited to removing the new M2-07
module/tests and reverting this Task Card result section through a separately
approved non-destructive Git operation.

---

## 16. Known Deferred Limits

- M2-06 final closure review: `PENDING`
- Semantic paraphrase/entailment validation: `NOT_IMPLEMENTED`
- Numeric/date/unit claim validation: `NOT_IMPLEMENTED - M3 scope`
- Live URL existence and click-through: `NOT_RUN`
- Production orchestration: `NOT_RUN`
- Actual 365-day provider candidate completeness: `NOT_RUN`
- M2-08 dedupe/context budget: `NOT_STARTED`
- Answer composition and AnswerValidator: `NOT_STARTED`
- LLM/LiteLLM/Gemini: `NOT_STARTED`
- GitHub CI: `NOT_RUN`
- Independent pytest rerun: `NOT_RUN`
- Windows clean-build `tzdata` decision: `DEFERRED`
- M1-09:
  `mandatory supplement implemented - final independent review pending`

---

## 17. Completion Criteria

Planning:

- [x] current Evidence, EvidenceDecision, locator, and status contracts checked
- [x] source-specific locator shapes checked
- [x] R25, R29, R45 and citation taxonomy checked
- [x] extractive claim support rule fixed
- [x] URL provenance and no-live-check boundary fixed
- [x] wrong-company citation rule fixed
- [x] mutation, duplicate, ordering, and sanitized-error rules fixed
- [x] M2-08 and M3 exclusions fixed
- [ ] M2-06 final closure review PASS recorded
- [ ] user approves M2-07 plan

Implementation after approval:

- [ ] preflight passes
- [ ] public API implemented
- [ ] claim/snippet extractive support passes
- [ ] locator and URL provenance tests pass
- [ ] wrong-company citation tests pass
- [ ] malformed public input tests pass
- [ ] duplicate preservation and mutation tests pass
- [ ] public-function composition passes
- [ ] targeted tests pass
- [ ] M2 regression passes
- [ ] full unit regression passes
- [ ] import smoke passes
- [ ] secret scan passes
- [ ] compile passes
- [ ] diff review passes
- [ ] actual results recorded
- [ ] user reviews implementation result

---

## 18. Approval Request

Requested:

- M2-06 final closure status confirmation
- review and approval of this M2-07 plan
- after both approvals, permission to run the preflight gate
- M2-07 implementation only if every preflight command passes

Not requested:

- commit
- push
- PR
- merge
- deploy
- dependency installation or change
- live URL/API calls
- M2-08 or later implementation
