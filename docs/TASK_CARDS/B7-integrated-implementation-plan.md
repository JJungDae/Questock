# TASK CARD - B7 Integrated Implementation Plan

## 1. Status and Approval

- Project: `Questock`
- Repository: `JJungDae/Questock`
- Branch: `main`
- Bundle: `B7`
- Included checkpoints:
  - `B7-0` preflight, B6/M3-15 factual sync, evaluation readiness
  - `B7-A` M3-06 anonymous session and reset
  - `B7-B1` M3-08 safety and M3-09 numeric validation
  - `B7-B2` M3-10 conflicting Evidence, M3-11 limited multi-source,
    and M3-15B UI closure
  - `B7-C` executable golden/Critical evaluation and M3 Gate evidence
- Priority: `P0`
- Planning date: `2026-07-25`
- Planning base SHA:
  `60e6203b265a967a8b6ba45da2ba3128e1e1bcfe`
- Planning base commit:
  `Fix B6 review findings`
- Planning base main push:
  `complete`
- B6 implementation:
  `PASS / complete`
- B6 final review:
  `PASS WITH REQUIRED FOLLOW-UP`
- B6 required follow-up:
  `factual Task Card synchronization and B7 integrated planning`
- M3-15A:
  `COMPLETE`
- M3-15B:
  `PENDING B7`
- B7-C:
  `REQUIRED - executable golden/Critical assets are absent`
- M3 Gate:
  `NOT_CLAIMED`
- M3-12:
  `NOT_ACTIVATED`
- M1-09:
  `mandatory supplement implemented - final independent review pending`
- B7 plan review:
  `PENDING`
- B7 implementation:
  `BLOCKED pending plan approval and B7-0 preflight PASS`
- Dependency or lock change:
  `NOT_APPROVED / NOT_EXPECTED`
- Live Gemini:
  `NOT_INCLUDED / NOT_APPROVED`
- Live source provider work:
  `NOT_INCLUDED / NOT_APPROVED`
- Commit, push, PR, merge, deploy:
  `NOT_APPROVED`

This Task Card is the canonical B7 bundle plan after the completed
`B6-REMAINDER` bundle.

---

## 2. Normative Sources

Read in this order before implementation:

1. `docs/agent_handoff/SOURCE_OF_TRUTH_INDEX.md`
2. `docs/agent_handoff/README_AGENT_RULES.md`
3. `docs/agent_handoff/PROJECT_PLAN_FINAL_PASS.md`
4. `docs/agent_handoff/PROJECT_PLAN_FINAL_PASS_POST_M3_01_ADDENDUM.md`
5. `docs/agent_handoff/POST_M3_01_EXECUTION_FLOW_DECISION_2026-07-25.md`
6. this Task Card
7. `docs/agent_handoff/AGENT_WORKFLOW.md`
8. `docs/agent_handoff/AGENT_WORKFLOW_POST_M3_01_ADDENDUM.md`
9. `docs/agent_handoff/LLM_STACK_DECISION.md`
10. `docs/agent_handoff/FINANCIAL_CAPABILITY_BASELINE.md`
11. `docs/agent_handoff/RISK_RESPONSE_MATRIX.md`
12. `docs/agent_handoff/EVALUATION_TAXONOMY_DRAFT.md`
13. `docs/agent_handoff/MENTORING_SCOPE_DECISION_2026-07-24.md`
14. `docs/TASK_CARDS/B6-REMAINDER-integrated-implementation-plan.md`
15. `docs/TASK_CARDS/M3-15-process-visibility-ui.md`
16. `docs/TASK_CARDS/M3-15-DIRECTION-AND-SPLIT.md`
17. actual current code and tests

If an older M3 sequence conflicts with the post-M3-01 addenda, the addenda and
execution-flow decision control.

---

## 3. Verified Planning-Base State

The following facts were verified at planning base
`60e6203b265a967a8b6ba45da2ba3128e1e1bcfe`:

| Area | Verified state |
|---|---|
| branch | `main` |
| HEAD | `60e6203b265a967a8b6ba45da2ba3128e1e1bcfe` |
| origin/main | same SHA |
| working tree before docs update | clean |
| first B6 implementation | `b7ddcd9eec9fe551fd9e6ab337de6a4d8e64c4fd` |
| B6 supplement | `60e6203b265a967a8b6ba45da2ba3128e1e1bcfe` |
| final B6 full unit result | `1669 passed, 2 warnings` |
| B6 AppTest | `6 passed, 1 warning` |
| B6 Streamlit startup | HTTP 200, finite process stopped |
| public schema blob | `c10da0270e00105a4f375ba79a2aac5451730a4a` |
| Evidence model blob | `54397337c3b3e152de247e585494ef4a6c92ef1a` |
| AnswerSections model blob | `660563e4859c6301f709c1e2574828eb143781e0` |
| trace version | `m3-01-v1` |
| existing session model | `app.core.models.SessionContext` |
| existing planner session input | `QueryPlanner.plan(..., session=...)` |
| ChatRequest session ID | exists and is not returned publicly |
| server session persistence | not implemented |
| UI session ID/reset shell | implemented; backend context not connected |
| output safety | partial pattern checks in `app/answer/composer.py` |
| exact extract citation gate | implemented in `app/evidence/citations.py` |
| numeric token/unit validator | not implemented |
| conflict/limited multi-source acceptance contract | not implemented |
| executable full golden fixture | absent |
| executable Critical subset | absent |
| M3 Gate runner/aggregation | absent |
| GitHub CI for B6 | `NOT_RUN` |
| independent pytest rerun for B6 | `NOT_RUN` |

Environment deviation carried from B6:

- repository `.venv` did not contain Streamlit during the B6 supplement
  targeted command
- the existing task-local clean B6 environment used Python 3.14.3 and
  Streamlit 1.60.0 and passed all final verification
- B7 must establish one explicit locked test interpreter before code changes
- no dependency or `uv.lock` change is authorized to resolve this environment
  issue

---

## 4. Bundle Goal

Complete the remaining active M3 behavior without changing the frozen M3-01
public response contract:

```text
anonymous session context
→ safe query planning
→ existing source/retrieval/Evidence pipeline
→ safety and numeric validation
→ conservative conflict/multi-source composition
→ M3-15B session/reset and result display
→ executable M3 Gate evidence
```

B7 completes:

- M3-06
- M3-08
- M3-09
- M3-10
- M3-11
- M3-15B

B7 does not implement:

- M3-12
- price-move response fields
- MarketSnapshot connection
- live providers
- live Gemini
- database or persistent conversation history
- authentication
- streaming
- dense/vector retrieval
- reranking
- automatic stance detection
- event grouping
- news deduplication extension
- M4 or M5 work

---

## 5. Frozen Contracts

The following remain unchanged throughout B7:

- `app/api/schemas.py`
- `ChatRequest`
- `ChatResponse`
- `PublicProcessSummary`
- every nested public summary model
- `trace_version="m3-01-v1"`
- `app/core/models.py`
- `SecurityIdentifier`
- `Evidence`
- `QueryPlan`
- `SessionContext` fields
- `AnswerSections` fields
- all status enums
- provider protocols and status mapping
- M1 ingest/provider behavior
- M2 filter, freshness, retrieval, EvidencePolicy, citation, and context budget
- `MAX_EVIDENCE_PER_SOURCE == 3`
- `MAX_EVIDENCE_COUNT == 6`
- one LLM call maximum

If any frozen contract must change, stop and request external plan review.

---

## 6. B7-0 Preflight and Factual Gate

No B7 production code may be edited before all preflight items pass.

### 6.1 Git gate

Verify:

```text
branch == main
HEAD == 60e6203b265a967a8b6ba45da2ba3128e1e1bcfe
origin/main == HEAD
working tree contains only the approved docs-only planning changes
```

If main is newer, inspect every new commit and stop if it changes B6, public
contracts, dependencies, or B7 assumptions.

Do not use reset, restore, checkout, clean, or stash.

### 6.2 Environment gate

Preferred interpreter:

```text
.\.venv\Scripts\python.exe
```

Required imports:

```text
pydantic
langchain_core
litellm
streamlit==1.60.0
tzdata-backed ZoneInfo("Asia/Seoul")
```

If `.venv` remains incomplete:

1. do not alter `pyproject.toml` or `uv.lock`
2. do not install an unpinned or new dependency
3. a locked offline reconciliation using the existing approved lock/cache may
   be proposed only within the approved implementation scope
4. if no reproducible locked interpreter can be established without network
   or dependency changes, record `BLOCKED` and stop

### 6.3 Contract gate

Recompute and compare:

```text
app/api/schemas.py:
c10da0270e00105a4f375ba79a2aac5451730a4a

app/core/models.py:
54397337c3b3e152de247e585494ef4a6c92ef1a

app/answer/models.py:
660563e4859c6301f709c1e2574828eb143781e0

trace_version:
m3-01-v1
```

### 6.4 B6 regression gate

Run:

```powershell
& $python -m pytest `
  tests/unit/test_glossary_service.py `
  tests/unit/test_ui_projections.py `
  tests/integration/test_streamlit_app.py `
  tests/unit/test_answer_composer.py `
  tests/unit/test_chat_service.py `
  -q

& $python -m pytest tests -q

& $python -c "from app.services.chat_service import ChatService; from app.answer.composer import AnswerComposer; from app.ui.app import run; print('b7-preflight-import-ok')"

& $python scripts/secret_scan.py
& $python -m compileall app tests scripts -q
git diff --check
```

Expected planning-base evidence:

```text
targeted: 104 passed
full: 1669 passed
secret scan: []
```

Counts may differ only because of factual environment collection differences.
Any test failure blocks B7 implementation.

### 6.5 Evaluation inventory gate

Confirm:

```text
golden draft:
docs/TASK_CARDS/B0-M0-01-03-planning.md

draft case count:
24

executable fixture:
absent

Critical subset:
absent

runner:
absent

taxonomy aggregation:
absent

B7-C:
REQUIRED
```

### 6.6 B7-0 docs

Before B7-A:

- confirm this plan is approved
- confirm the B6 Task Card says `PASS / complete`
- synchronize the canonical M3-15 Task Card to:
  - `M3-15A COMPLETE`
  - `M3-15B PENDING B7`
  - B6 supplement SHA and main push complete
- preserve `M3-15 overall: not complete`
- record the locked interpreter actually used

---

## 7. B7-A - M3-06 Anonymous Session and Reset

## 7.1 Existing boundary

Reuse:

- `ChatRequest.session_id`
- `SessionContext`
- `QueryPlanner.plan(..., session=...)`
- FastAPI's process-local singleton `ChatService`
- Streamlit's current generated anonymous session ID

Do not add a public session endpoint or response field.

## 7.2 In-memory session store

Add a small M3-owned process-local store.

Required behavior:

- key: validated `ChatRequest.session_id`
- value: existing `SessionContext`
- store only:
  - current canonical security ID
  - current date range
  - previous intent
  - previous source types
- never store:
  - raw question
  - answer text
  - Evidence snippet
  - prompt
  - provider payload
  - credential
  - local path
- `get` and `put` return/store deep copies
- bounded number of sessions
- finite TTL based on an injectable monotonic clock
- deterministic oldest-entry eviction when the bound is reached
- malformed internal state fails with a fixed sanitized service error
- no DB, file, browser storage, cookie, account, or cross-process persistence

Default constants must be conservative and local to the M3 session module.
They are not public API or environment configuration.

## 7.3 Planning with session context

The existing QueryPlanner session parameter is the only planning interface.

Rules:

1. explicit supported security in the new question wins
2. explicit ambiguous or unsupported security fails closed and must not fall
   back to the old security
3. when no security is stated, a supported follow-up may inherit the current
   security
4. an explicit valid date/date range wins
5. no explicit period may inherit the current date range only where the
   existing planner permits it
6. an explicit recent/today cue must not accidentally retain an old date range
7. a curated follow-up cue with no new intent may inherit the previous
   security-required intent
8. explicit new intent always wins over previous intent
9. `financial_term`, `prohibited_advice`, and `out_of_scope` never inherit a
   security-required previous intent
10. an ordinary unrelated question must not receive the stale security,
    period, or intent

Curated intent-follow-up cues must be deterministic and narrow. At minimum test:

- `그중 공시만`
- `같은 기간 위험 요인은?`
- `2026-07-01~2026-07-10 기간은?`
- `이어서 알려줘`

Do not use an LLM to resolve session context.

`app/planning/query_planner.py` is an M2-owned file. B7 may modify only the
already-existing `session` behavior needed for M3-06. It must not change:

- intent names
- source/evidence matrix
- non-session routing results
- security resolver behavior
- date parsing outside session fallback

This limited planning-file change requires explicit approval in the B7 plan
review. If approval is not granted, B7-A is blocked.

## 7.4 Session update policy

Update the stored context only after a valid non-clarification plan is built.

Allowed updates:

- canonical security ID from the accepted plan
- plan date range
- accepted intent
- required source types

Do not replace valid prior context after:

- malformed request
- ambiguous or unsupported explicit security
- clarification-required plan
- `prohibited_advice`
- `out_of_scope`
- internal service exception

A provider failure after a valid plan may preserve the accepted planning
context. Provider success is not required to remember what the user asked.

Session read/update must not change the public response or diagnostics schema.

## 7.5 Reset

The current UI reset creates a new anonymous session ID.

B7 reset contract:

- current UI response cleared
- question cleared
- new session ID differs from old ID
- next request uses the new ID
- backend does not inherit the old ID's context
- old process-local state expires through TTL/eviction
- no destructive global session-store clear

## 7.6 B7-A files

Production:

- add `app/services/session_store.py`
- modify `app/services/chat_service.py`
- modify `app/services/planning_observation.py`
- modify `app/planning/query_planner.py` only for approved existing-session
  semantics
- modify `app/ui/app.py` only if reset wiring needs a local correction
- modify `app/services/__init__.py` only if an existing export pattern requires
  it

Tests:

- add `tests/unit/test_session_store.py`
- modify `tests/unit/test_query_planner.py`
- modify `tests/unit/test_chat_service.py`
- modify `tests/unit/test_api_chat.py`
- modify `tests/integration/test_m3_chat_phase_slice.py`
- modify `tests/integration/test_streamlit_app.py`

## 7.7 B7-A required tests

- same session inherits security
- explicit new security wins
- ambiguous new security does not inherit
- unsupported new security does not inherit
- explicit date range wins
- safe no-cue date fallback
- recent/today clears incompatible old date
- narrow follow-up inherits previous intent
- explicit intent wins
- financial term does not inherit security/intent
- unrelated question does not inherit
- invalid stored security clarifies safely
- independent session IDs are isolated
- reset creates a new ID and loses old context
- raw question and Evidence are absent from store
- deep-copy and caller non-mutation
- TTL expiration
- deterministic capacity eviction
- concurrent same-session requests are serialized or otherwise deterministic
- no public session ID in response
- fixed sanitized errors

---

## 8. B7-B1 - M3-08 Safety and M3-09 Numeric Validation

## 8.1 Central validation boundary

Add one project-owned answer validation module and call it from the existing
`AnswerComposer` boundary.

The validator consumes only copied:

- `QueryPlan`
- parsed structured draft claims
- eligible Evidence

The validator must not:

- call an LLM
- call a provider
- change retrieval
- change Evidence
- mutate caller objects
- expose raw claim text in errors
- add a public status or schema

All validation remains after LLM parsing and before public response assembly.

## 8.2 Safety contract

Block generated content that gives or directs:

- specific buy, sell, or hold action
- target price
- stop-loss or take-profit price/timing
- guaranteed return
- unsupported probability
- certain future price direction
- disclaimer-wrapped advice

Permit neutral source-grounded facts such as:

- an institution's or foreign investor's trading trend
- a company's treasury-share acquisition or disposal
- a report's stated investment opinion as a reported fact
- a company's cash or asset holding

Safety matching must use normalized Korean/ASCII text and action context. A
bare source word such as `매수 의견` must not automatically become advice.

Any safety violation fails the generated draft closed to the existing fixed
safe/citation-bound path. It must not trigger a second LLM call.

The fixed path must also apply the same safety boundary before showing a source
snippet.

## 8.3 Numeric/date/unit contract

For every generated claim:

1. extract numeric literals with token boundaries
2. preserve sign, decimal point, comma grouping, currency/unit, `%`, and `%p`
3. treat `%` and `%p` as different units
4. prevent `10` from matching inside `100`
5. preserve Korean units such as `원`, `만원`, `억원`, and `조원`
6. preserve explicit dates and periods
7. require every claim numeric/date token to occur exactly in every referenced
   Evidence snippet
8. require referenced Evidence company attribution to pass the existing M2
   citation company rule
9. do not promote a mentioned company to subject
10. do not convert units, round, calculate, or infer a missing value

The validator does not introduce a general financial-metric model.

## 8.4 Claim disposition

- safety violation: reject the generated draft and use the existing safe fixed
  response
- unsupported numeric/date/unit claim: remove that claim
- after removal, rerun section-order, summary, citation, and duplicate guards
- if the only summary or all claims are removed, use the existing
  citation-bound fixed fallback
- count deterministic claim rejection in existing diagnostics
- never return an unsupported numeric sentence
- never call the LLM again

## 8.5 B7-B1 files

Production:

- add `app/answer/validators.py`
- modify `app/answer/composer.py`
- modify `app/answer/__init__.py` only if an existing export pattern requires it

Tests:

- add `tests/unit/test_answer_validators.py`
- modify `tests/unit/test_answer_composer.py`
- modify `tests/unit/test_chat_service.py`
- modify `tests/integration/test_m3_chat_phase_slice.py`

## 8.6 B7-B1 required tests

Safety:

- direct buy/sell/hold instruction blocked
- target price blocked
- stop-loss/take-profit timing blocked
- certain future direction blocked
- unsupported probability/guarantee blocked
- disclaimer does not make unsafe advice valid
- neutral institutional/foreign trading fact allowed
- neutral treasury-share fact allowed
- neutral report opinion fact allowed
- no second LLM call
- fixed sanitized fallback

Numeric:

- integer exact match
- decimal exact match
- comma-grouped number exact match
- negative/sign preservation
- `10` versus `100`
- `%` versus `%p`
- KRW/Korean unit preservation
- date and period preservation
- wrong-company numeric Evidence rejected
- mentioned-only company not promoted
- claim removal preserves other valid claims
- removed summary causes fixed fallback
- deterministic repeated result
- caller objects unchanged

---

## 9. B7-B2 - M3-10, M3-11, and M3-15B

## 9.1 M3-only Evidence projection

M2 context-budget output remains authoritative and unchanged.

For `risk_factors` and `multi_source_summary`, the M3 composer may transmit a
deep-copied subset of at most three already-selected Evidence items.

Deterministic projection:

1. preserve requested source order from `QueryPlan.required_sources`
2. take the first eligible Evidence occurrence for each available requested
   source
3. stop at three
4. if fewer than three source types are available, fill remaining positions
   from the original M2-selected order
5. do not rerank, deduplicate, merge, or modify Evidence

The existing `PublicContextBudgetSummary` continues to describe M2 context
selection. Public/citation Evidence describes final accepted cited Evidence.
The UI must not recompute either count.

## 9.2 Conflicting Evidence acceptance contract

P0 behavior:

- common fact may be shown only when citation-supported
- positive factor may be shown only with its supporting Evidence
- risk factor may be shown only with its supporting Evidence
- when both positive and risk sections are present, they must not silently use
  the same unsupported claim/evidence occurrence
- uncertainty is required when an accepted response presents both sides
- no article-count majority
- no sentiment score
- no automatic winner
- no buy/sell conclusion
- no unsupported compromise conclusion

B7 does not attempt automatic stance discovery. It validates a structured
draft against deterministic synthetic conflict fixtures and existing
Evidence/citation contracts.

Do not add:

- `ContradictionGroup`
- stance enum
- event model
- duplicate-group metadata
- `evidence_comparison` production module

## 9.3 Limited multi-source connection contract

- use two or three Evidence items when available
- every step/claim retains existing Evidence IDs and source details
- facts remain source-grounded
- interpretation and inference remain separately labeled
- a multi-Evidence claim must reference only supplied Evidence
- referenced dated Evidence must be in nondecreasing UTC order
- if a causal step lacks Evidence, date, or company continuity, omit that
  causal claim
- missing intermediate support must not be replaced with model knowledge
- source-specific independent summaries remain allowed
- no long causal chain
- no future price certainty

The exact-extract and citation gates remain in force. B7 must not weaken M2-07.

## 9.4 M3-15B UI closure

Use the existing UI and frozen response:

- stable anonymous session ID across turns
- reset creates a new ID
- same-session follow-up is visible through the resulting response
- positive, risk, and uncertainty cards use existing card slots
- two or three final source cards display existing safe details
- process expander remains collapsed by default
- public process counts/statuses are consumed, not recomputed
- dynamic values remain plain text
- only validated `source_url` creates a link
- no prompt, chain-of-thought, secret, raw exception, or local path

No new public route or response field is allowed for UI closure.

## 9.5 B7-B2 files

Production:

- modify `app/answer/composer.py`
- modify `app/answer/validators.py`
- modify `app/services/chat_service.py` only for final composer input wiring
- modify `app/ui/projections.py` only if existing cards/source projections need
  a safe B7 mapping
- modify `app/ui/app.py` only for M3-15B session/reset/result wiring

Tests:

- modify `tests/unit/test_answer_composer.py`
- modify `tests/unit/test_answer_validators.py`
- modify `tests/unit/test_chat_service.py`
- modify `tests/unit/test_ui_projections.py`
- modify `tests/integration/test_m3_chat_phase_slice.py`
- modify `tests/integration/test_streamlit_app.py`

## 9.6 B7-B2 required tests

- deterministic source-diverse selection
- at most three transmitted Evidence items
- M2 budget diagnostics unchanged
- positive and risk claims cite supporting Evidence
- uncertainty required for accepted two-sided result
- no article-count majority output
- unsupported common conclusion rejected
- source-specific summaries accepted
- two-source and three-source accepted paths
- chronological cited order
- missing date breaks causal claim
- wrong-company step rejected
- interrupted causal chain omitted
- no second LLM call
- public/cited Evidence contains accepted final Evidence only
- UI displays positive/risk/uncertainty cards
- UI displays two/three source cards
- same session ID across turns
- reset uses new ID and no old context
- process expander unchanged
- malicious source metadata remains plain text/hidden

---

## 10. B7-C - Executable Evaluation Closure

B7-C is mandatory because B6 inventory found only a documentation draft.

## 10.1 Assets

Add:

- `tests/fixtures/evaluation/m3_golden_cases.json`
- `scripts/m3_gate.py`
- `tests/unit/test_m3_gate_runner.py`
- `tests/integration/test_m3_gate.py`

Additional test-only helper modules under `tests/` are allowed only when they
remove real duplication and are not imported by application code.

## 10.2 Golden fixture contract

The fixture must contain at least 24 independent cases and preserve the six
approved groups with at least four cases each:

1. resolution / ambiguous
2. intent / source routing
3. retrieval / wrong-company / low relevance
4. citation / Evidence sufficiency
5. numeric / date / stale / correction
6. safety / multi-turn / provider failure

Each case must contain validated:

- stable case ID
- taxonomy labels
- question or turn sequence
- synthetic scenario ID
- expected resolution/intent/source/status
- expected/forbidden security IDs
- expected/forbidden Evidence IDs or source types where applicable
- required warning/fallback behavior
- Critical membership

Do not store:

- credential
- live URL requiring network
- local absolute path
- copyrighted report text
- raw prompt
- expected free-form LLM prose

## 10.3 M3-12 case

The existing draft price-move case remains in the 24-case inventory but its M3
expectation is:

```text
M3-12 NOT_ACTIVATED
→ no price response schema
→ no MarketSnapshot call
→ safe out-of-scope/abstention behavior
```

Do not activate M3-12 to make the case pass.

## 10.4 Critical set

Critical coverage must include all approved failure families:

- wrong-company Evidence blocked
- fake URL/locator blocked
- ambiguous security not auto-resolved
- timeout distinct from no-data
- no unsupported `complete`
- direct buy/sell/hold advice blocked
- target/stop-loss/take-profit/certain prediction/probability blocked
- secret and local absolute path not exposed

Critical cases must all pass.

## 10.5 Runner contract

The runner:

- uses fake/recorded synthetic inputs only
- makes no network call
- makes no live Gemini call
- uses deterministic fake LLM output
- validates fixture schema before execution
- aggregates by taxonomy
- records passed, failed, total, percentage, and failed case IDs
- does not print raw exception, prompt, secret, or local path
- returns exit code:
  - `0`: full golden >= 80% and Critical == 100%
  - `1`: valid run below a gate threshold
  - `2`: malformed fixture or sanitized internal runner failure
- produces equal output for equal inputs

M3 Gate prose and LLM sentence exact matching are not required. Evaluate
structured fields, forbidden behavior, status, source/Evidence relationship,
and deterministic fallback.

## 10.6 M3 Gate

B7 implementation review and M3 Gate may be requested together, but record two
separate judgments:

```text
B7 implementation review:
PASS / CONDITIONAL PASS / FAIL

M3 Gate:
PASS / FAIL / NOT_RUN
```

M3 Gate PASS requires:

- CORE08
- A01 through A04
- A05-M
- A06-M
- A07-M
- A08-M
- A10
- SAFE01
- UI01
- PublicProcessSummary UI smoke
- full golden set >= 80%
- Critical set == 100%
- prompt/secret/raw exception/local path exposure == 0
- M3-12 remains `NOT_ACTIVATED`

Do not claim M3 Gate PASS from unit tests alone.

---

## 11. Allowed Files

Production:

- `app/services/session_store.py`
- `app/services/chat_service.py`
- `app/services/planning_observation.py`
- `app/services/__init__.py` only if needed
- `app/planning/query_planner.py` only for approved existing-session behavior
- `app/answer/validators.py`
- `app/answer/composer.py`
- `app/answer/__init__.py` only if needed
- `app/ui/app.py`
- `app/ui/projections.py`

Evaluation tooling:

- `scripts/m3_gate.py`

Tests and synthetic fixtures:

- `tests/unit/test_session_store.py`
- `tests/unit/test_query_planner.py`
- `tests/unit/test_answer_validators.py`
- `tests/unit/test_answer_composer.py`
- `tests/unit/test_chat_service.py`
- `tests/unit/test_api_chat.py`
- `tests/unit/test_ui_projections.py`
- `tests/unit/test_m3_gate_runner.py`
- `tests/integration/test_m3_chat_phase_slice.py`
- `tests/integration/test_streamlit_app.py`
- `tests/integration/test_m3_gate.py`
- `tests/fixtures/evaluation/m3_golden_cases.json`
- narrowly scoped test-only helpers under `tests/` when justified

Documentation:

- this Task Card
- `docs/TASK_CARDS/B6-REMAINDER-integrated-implementation-plan.md`
- `docs/TASK_CARDS/M3-15-process-visibility-ui.md`
- checkpoint HANDOFF files only if separately approved
- final work log only after user result confirmation

Any additional production file requires a stop report and approval.

---

## 12. Forbidden Files and Work

Do not modify:

- `app/api/schemas.py`
- `app/core/**`
- `app/core/status.py`
- `app/providers/**`
- `app/ingest/**`
- `app/retrieval/**`
- `app/evidence/**`
- `app/services/source_gateway.py`
- `app/llm/**`
- `app/phase_slice.py`
- `data/glossary.json`
- `data/securities.json`
- existing M1/M2 fixtures
- `pyproject.toml`
- `uv.lock`
- `.env.example`
- Docker files
- CI workflows

Do not add:

- dependency
- public schema/status
- provider/live adapter
- database/migration
- authentication
- persistent chat history
- user profile
- streaming
- LangGraph
- dense/vector retrieval
- reranker
- remote tracing
- automatic stance/sentiment model
- price feature
- M3-12
- M4/B8/B9 implementation
- M5/P1 implementation

---

## 13. Checkpoint Verification

## 13.1 B7-A targeted

```powershell
& $python -m pytest `
  tests/unit/test_session_store.py `
  tests/unit/test_query_planner.py `
  tests/unit/test_chat_service.py `
  tests/unit/test_api_chat.py `
  tests/integration/test_m3_chat_phase_slice.py `
  tests/integration/test_streamlit_app.py `
  -q
```

## 13.2 B7-B1 targeted

```powershell
& $python -m pytest `
  tests/unit/test_answer_validators.py `
  tests/unit/test_answer_composer.py `
  tests/unit/test_chat_service.py `
  tests/integration/test_m3_chat_phase_slice.py `
  -q
```

## 13.3 B7-B2 targeted

```powershell
& $python -m pytest `
  tests/unit/test_answer_validators.py `
  tests/unit/test_answer_composer.py `
  tests/unit/test_chat_service.py `
  tests/unit/test_ui_projections.py `
  tests/integration/test_m3_chat_phase_slice.py `
  tests/integration/test_streamlit_app.py `
  -q
```

## 13.4 B7-C targeted

```powershell
& $python -m pytest `
  tests/unit/test_m3_gate_runner.py `
  tests/integration/test_m3_gate.py `
  -q

& $python scripts/m3_gate.py
```

## 13.5 B7 full regression

```powershell
& $python -m pytest `
  tests/unit/test_query_planner.py `
  tests/unit/test_answer_composer.py `
  tests/unit/test_chat_service.py `
  tests/unit/test_api_chat.py `
  tests/unit/test_ui_projections.py `
  tests/integration/test_m2_phase_slice.py `
  tests/integration/test_m3_chat_phase_slice.py `
  tests/integration/test_streamlit_app.py `
  tests/integration/test_m3_gate.py `
  -q

& $python -m pytest tests -q
```

## 13.6 Smoke and hygiene

```powershell
& $python -c "from app.services.session_store import InMemorySessionStore; from app.answer.validators import validate_answer_draft; from app.services.chat_service import ChatService; from app.ui.app import run; print('b7-import-ok')"

& $python scripts/secret_scan.py
& $python -m compileall app tests scripts -q

git diff --check
git diff --name-status
git diff --stat
git status --short --branch
```

Also run:

- finite Streamlit headless startup and HTTP health 200
- AppTest multi-turn/reset/conflict/multi-source paths
- local fake/recorded API vertical slice
- public payload secret/path/prompt scan

Record the first failed command and every rerun. Do not replace an initial
failure with only the final PASS.

---

## 14. Checkpoint HANDOFF

After every checkpoint record:

- bundle/checkpoint
- starting SHA
- current HEAD
- changed files
- unexpected files
- frozen contract hashes
- targeted result
- previous checkpoint regression
- vertical/UI smoke
- full suite state
- secret scan
- compile
- diff check
- BLOCKER
- required follow-up
- deferred note
- next checkpoint `ALLOWED` or `BLOCKED`

Do not push main after each checkpoint.

---

## 15. Stop Conditions

Stop and report if:

- planning base changed materially
- public schema/status change is needed
- `SessionContext` field change is needed
- M1/M2 Evidence/filter/retrieval/policy/citation/budget change is needed
- QueryPlanner requires more than the approved existing-session change
- dependency or lock change is needed
- no reproducible locked interpreter is available
- provider/live source work is needed
- live Gemini is needed
- DB/persistence/authentication is needed
- automatic stance/grouping/dedupe is needed
- numeric validation requires a new financial metric model
- Critical fixture fails after scoped correction
- wrong-company Evidence reaches output
- direct advice reaches output
- fake URL/locator reaches output
- raw prompt, secret, exception, or local path reaches output
- UI requires a public schema change
- M3-12/price functionality becomes necessary
- a checkpoint expands beyond three independent production boundaries
- changed files exceed the approved list

Stop report must include:

- problem
- evidence
- smallest safe correction
- alternatives
- test impact
- schedule impact
- whether external plan review is required

---

## 16. Risk and Taxonomy Mapping

| Area | Risk | Taxonomy | Control |
|---|---|---|---|
| session | R47, R48 | `multi_turn` | explicit security precedence, reset, bounded process-local store |
| safety | R35, R38-R41 | `prohibited_advice` | output validator and fixed safe fallback |
| numeric | R30, R60 | `numeric_accuracy` | exact literal/unit/date and company attribution |
| conflict | R36 | `conflicting_sources` | supported parallel views, no majority/winner |
| multi-source | R31, R32 | `multi_hop_reasoning`, `evidence_sufficiency` | 2-3 Evidence, causal break, uncertainty |
| citation | R25, R29 | `citation_support` | existing M2 citation gate unchanged |
| evaluation | R53, R58 | all active M3 taxonomy | executable fixture, deterministic aggregation |
| privacy | R57, R61 | Critical safety | no raw session/question/prompt/secret/path |
| UI | R42 | `UI01` | existing cards and collapsed process panel |

---

## 17. Fallback and Rollback

Session fallback:

- disable session inheritance and retain explicit single-turn behavior
- keep new UI session IDs as request correlation only

Safety/numeric fallback:

- existing citation-bound fixed response
- remove invalid claim
- hide unsupported numeric card/section

Conflict/multi-source fallback:

- source-specific independent summaries
- omit causal connection
- show uncertainty and missing source

Evaluation fallback:

- B7-C remains incomplete
- M3 Gate remains `NOT_RUN` or `FAIL`
- do not proceed to B8

Rollback proposal after an approved Git operation:

- revert only the B7 bundle commit through a new revert commit
- never reset or rewrite main history

---

## 18. Completion Criteria

### Governance

- [ ] B7 plan independently approved
- [ ] B7-0 preflight PASS
- [ ] locked interpreter recorded
- [ ] no dependency/lock change
- [ ] no forbidden file change

### B7-A

- [ ] process-local bounded session store
- [ ] security/date/intent/source context
- [ ] explicit security/intent precedence
- [ ] ambiguous/unsupported fail closed
- [ ] stale context not forced
- [ ] reset isolation
- [ ] no raw conversation persistence

### B7-B1

- [ ] direct advice blocked
- [ ] target/stop-loss/take-profit/certainty/probability blocked
- [ ] neutral facts allowed
- [ ] numeric/date/unit exact validation
- [ ] company attribution preserved
- [ ] invalid numeric claim removed
- [ ] fixed safe fallback
- [ ] one LLM call maximum

### B7-B2

- [ ] source-diverse 2-3 Evidence projection
- [ ] conflicting views remain parallel
- [ ] no majority/winner/investment conclusion
- [ ] limited multi-source chronology
- [ ] broken causal chain omitted
- [ ] M3-15B session/reset UI
- [ ] conflict/multi-source AppTest
- [ ] M3-15 overall closure evidence

### B7-C and M3 Gate

- [ ] 24+ executable golden cases
- [ ] six groups with 4+ cases each
- [ ] Critical failure families identified
- [ ] deterministic runner
- [ ] taxonomy aggregation
- [ ] full golden >= 80%
- [ ] Critical == 100%
- [ ] exposure count == 0
- [ ] M3-12 remains NOT_ACTIVATED
- [ ] B7 review and M3 Gate judgments recorded separately

### Regression

- [ ] checkpoint targeted tests PASS
- [ ] M2 regression PASS
- [ ] B6 regression PASS
- [ ] full unit PASS
- [ ] AppTest PASS
- [ ] finite Streamlit startup PASS
- [ ] local fake/recorded vertical slice PASS
- [ ] secret scan PASS
- [ ] compile PASS
- [ ] diff check PASS
- [ ] GitHub CI accurately recorded
- [ ] independent rerun accurately recorded

---

## 19. Final Result Record

Record after implementation:

```text
Planning base SHA:
60e6203b265a967a8b6ba45da2ba3128e1e1bcfe

B7 plan review:

Locked interpreter:

B7-0:

B7-A:

B7-B1:

B7-B2:

B7-C:

Targeted counts:

B7 regression:

Full unit:

AppTest:

Streamlit startup:

M3 Gate runner:

Full golden:

Critical:

Exposure findings:

Secret scan:

Compile:

Diff:

Public schema changed:
NO

Core models/status changed:
NO

M1/M2 changed:
NO, except separately approved existing QueryPlanner session behavior if used

Dependency/lock changed:
NO

Live Gemini:
NOT_RUN / NOT_APPROVED

Live sources:
NOT_RUN / NOT_APPROVED

GitHub CI:

Independent pytest:

B7 implementation SHA:
not created before separate approval

B7 implementation review:

M3-15:

M3 Gate:

B8 planning:
ALLOWED only after B7 PASS and M3 Gate PASS

Commit/push/PR/merge/deploy:
NOT_APPROVED until separately requested
```

---

## 20. Approval Request

Plan review must explicitly decide:

1. B7-A process-local bounded session-store contract
2. limited modification of existing QueryPlanner session behavior
3. central M3 answer validator file
4. claim-removal behavior for unsupported numeric/date/unit content
5. at-most-three M3 multi-source Evidence projection after M2 budget
6. conflict and causal-chain acceptance rules
7. B7-C fixture/runner file locations
8. locked environment reconciliation without dependency/lock changes
9. all allowed production/test files

Approval of this plan authorizes only:

- approved B7 code/test/fixture/docs edits
- local fake/recorded tests
- local AppTest/startup smoke
- secret/compile/diff verification
- an offline locked environment reconciliation when explicitly included in
  the approval

It does not authorize:

- dependency/lock changes
- package-index/network access
- live Gemini
- live providers
- commit
- push
- PR
- merge
- deployment
- B8 implementation
