# TASK CARD - B8 Quality Stabilization and Observability

## 1. Status and Approval

- Project: `Questock`
- Repository: `JJungDae/Questock`
- Branch: `main`
- Bundle: `B8`
- Included checkpoints:
  - `B8-0` preflight and B7/M3 Gate factual verification
  - `M4-01` provider failure and fallback regression
  - `M4-02` full golden quality stabilization
  - `M4-03` minimum structured observability
- Priority: `P0`
- Planning date: `2026-07-25`
- Planning base SHA:
  `52c015569111493f83ab27983839d18136da5655`
- Planning base commit:
  `docs: sync B7 supplement status`
- Planning base main push:
  `complete`
- B7 implementation SHA:
  `833336a002b1e02070b35cd4afe9aff279752d61`
- B7 focused supplement SHA:
  `b068868f2be33a4a2ec0b48a6a90b96c461bf862`
- B7 focused supplement main push:
  `complete`
- B7 independent implementation review:
  `PASS WITH REQUIRED FOLLOW-UP`
- B7 code blockers:
  `CLOSED`
- M3-15B:
  `PASS / complete`
- M3 Gate independent review:
  `PASS`
- M3 Gate result:
  `30/34 = 88.24%`
- M3 Gate Critical:
  `17/17 = 100%`
- M3 Gate public exposure:
  `0`
- M1-09:
  `mandatory supplement implemented - final independent review pending`
- M3-12:
  `NOT_ACTIVATED`
- B8 planning:
  `ALLOWED`
- B8 plan review:
  `PASS WITH REQUIRED FOLLOW-UP`
- B8 implementation:
  `IMPLEMENTED - local verification PASS - user review pending`
- B8 implementation review:
  `NOT_RUN`
- Dependency or lock change:
  `NOT_APPROVED / NOT_EXPECTED`
- Live provider or live Gemini work:
  `NOT_INCLUDED / NOT_APPROVED`
- Commit, push, PR, merge, deploy:
  `implementation commit/push NOT_RUN - separate user approval required`

This Task Card is the canonical B8 plan. It treats the four remaining HBM
golden failures as B8 quality stabilization work. They do not reopen B7.

---

## 2. Normative Sources

Read in this order before implementation:

1. `docs/agent_handoff/SOURCE_OF_TRUTH_INDEX.md`
2. `docs/agent_handoff/README_AGENT_RULES.md`
3. `docs/agent_handoff/PROJECT_PLAN_FINAL_PASS.md`
4. `docs/agent_handoff/PROJECT_PLAN_FINAL_PASS_POST_M3_01_ADDENDUM.md`
5. `docs/agent_handoff/POST_M3_01_EXECUTION_FLOW_DECISION_2026-07-25.md`
6. `docs/agent_handoff/AGENT_WORKFLOW.md`
7. `docs/agent_handoff/AGENT_WORKFLOW_POST_M3_01_ADDENDUM.md`
8. `docs/agent_handoff/FINANCIAL_CAPABILITY_BASELINE.md`
9. `docs/agent_handoff/RISK_RESPONSE_MATRIX.md`
10. `docs/agent_handoff/EVALUATION_TAXONOMY_DRAFT.md`
11. `docs/TASK_CARDS/B7-integrated-implementation-plan.md`
12. this Task Card
13. current code, fixtures, and tests

The post-M3-01 addendum controls the bundle order:

```text
B7 PASS
-> M3 Gate PASS
-> B8 M4-01~03
-> B8 implementation review
-> B9 only after B8 PASS
```

---

## 3. Verified Baseline

The planning inspection found:

- `app/providers/base.py` already owns provider status normalization, retry,
  attempt timeout, total deadline, parallel cancellation, and TTL cache.
- `app/services/source_gateway.py` already validates project-owned source
  results and distinguishes timeout from unconfigured provider state.
- `app/services/chat_service.py` already composes provider, retrieval,
  EvidenceDecision, LLM, fallback, and `PublicProcessSummary` state.
- `app/planning/query_planner.py` treats any standalone uppercase ASCII token
  matching `^[A-Z]{1,5}([.-][A-Z])?$` as a foreign ticker candidate.
- `HBM` therefore reaches `SecurityResolver` as an unsupported candidate.
  When a supported company is also resolved, the mixed resolved/unsupported
  candidates force clarification.
- `app/core/resolver.py` has the approved foreign-ticker boundary. B8 must not
  weaken or rewrite this resolver contract.
- There is no current internal structured JSON request log. The existing
  `PublicProcessSummary` is a public UI contract and must not be reused as the
  internal log model.
- The recorded M3 Gate failures are:
  - `B0-09`
  - `B0-10`
  - `B0-12`
  - `B0-17`
- Current recorded gate:
  - full golden `30/34 = 88.24%`
  - Critical `17/17 = 100%`
  - public exposure `0`

These are planning observations, not a new test execution.

---

## 4. Goal

Complete the P0 stabilization slice without adding a new product feature:

```text
provider failure and fallback regression
-> HBM/domain-token resolution stabilization
-> full golden >= 90% with Critical 100%
-> private minimum structured JSON logging
```

The completed bundle must:

- preserve provider failure versus normal no-data distinctions
- preserve partial results when at least one required source remains usable
- prevent raw exceptions, secrets, prompts, paths, or source payloads from
  entering user responses or logs
- preserve supported-company and wrong-company safety
- distinguish `HBM` as a domain token from actual foreign uppercase tickers
- retain the frozen public API and core model/status contracts
- produce one bounded internal request observation for completed requests
- leave CI, Docker, deployment, demo packaging, and traceability to B9

---

## 5. Non-Goals

Do not implement:

- a live provider, live source adapter, or credential use
- provider schema or status enum changes
- `SecurityResolver` contract changes
- public `ChatRequest`, `ChatResponse`, or `PublicProcessSummary` changes
- core model or Evidence model changes
- M1 or M2 implementation or contract changes, except for the explicitly
  approved narrow `HBM` candidate-eligibility correction in
  `app/planning/query_planner.py`
- new retrieval, ranking, normalization, dedupe, or context-budget behavior
- LLM model, prompt, validator, or provider changes
- Langfuse, OpenTelemetry, remote tracing, or a new dependency
- user question, session, prompt, document, Evidence text, or raw payload logs
- API or UI feature work
- CI, Docker, deployment, or remote smoke
- M3-12, M5-01, or P1 work

---

## 6. B8-0 Preflight Gate

Use the approved locked interpreter:

```powershell
$python = ".deps/b6-streamlit-clean/Scripts/python.exe"
```

### 6.1 Git and scope verification

Confirm:

- branch is `main`
- `HEAD` equals `origin/main`
- the approved B8 Task Card is present
- no commit after the approved plan changes a B8 contract
- no code, fixture, dependency, or lock change is already dirty
- user-owned review bundle files remain untouched and unstaged
- `pyproject.toml` and `uv.lock` are unchanged

Commands:

```powershell
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
git log -5 --oneline
git diff --check
git diff --name-status
```

### 6.2 Regression preflight

```powershell
& $python -m pytest `
  tests/unit/test_provider_base.py `
  tests/unit/test_source_gateway.py `
  tests/unit/test_query_planner.py `
  tests/unit/test_chat_service.py `
  tests/unit/test_answer_composer.py `
  tests/unit/test_answer_validators.py `
  tests/unit/test_ui_projections.py `
  tests/unit/test_m3_gate_runner.py `
  tests/integration/test_m2_phase_slice.py `
  tests/integration/test_m3_chat_phase_slice.py `
  tests/integration/test_streamlit_app.py `
  tests/integration/test_m3_gate.py `
  -q

& $python -m pytest tests -q
& $python scripts/m3_gate.py
& $python -c "from app.services.chat_service import ChatService; from app.planning.query_planner import QueryPlanner; print('b8-preflight-import-ok')"
& $python scripts/secret_scan.py
& $python -m compileall app tests scripts -q
```

Preflight passes only if:

- all commands exit `0`
- full golden remains at least `30/34`
- Critical remains `17/17`
- public exposure remains `0`
- no unexpected warning, contract drift, or unrelated failure appears

If any item fails, stop before B8 implementation and report the evidence.

---

## 7. M4-01 - Provider Failure and Fallback Regression

## 7.1 Contract

Exercise existing provider and orchestration behavior end to end. Do not
reimplement provider policy.

Required distinctions:

| Provider condition | Required public behavior |
|---|---|
| all required sources `no_data` | `no_evidence`, not `provider_failed` |
| all required sources fail | `provider_failed`, fixed safe fallback |
| one source `ok`, another `no_data` | usable Evidence preserved; decision follows existing EvidencePolicy |
| one source `ok`, another failure | usable Evidence preserved; `partial` when required-source coverage is incomplete |
| `timeout` | remains timeout in process state; never reported as no-data |
| `rate_limited` | remains rate-limited; no unbounded retry |
| `provider_unavailable` | remains provider-unavailable; safe message only |
| `parse_error` | remains parse-error; safe message only |
| total deadline | pending work cancelled; safe timeout fallback |
| expired cache entry | treated as miss; stale value not returned |
| valid cache hit | original `fetched_at` retained and `from_cache=True` |

The whole request must not crash for expected provider failures. Unexpected
project-boundary violations must remain sanitized errors and must not be
misreported as normal no-data or low relevance.

## 7.2 Tests

Add deterministic fake/recorded tests for:

- timeout
- rate limit
- no-data
- parse error
- provider unavailable
- expired cache
- one failed source with another successful source
- all sources failed
- all sources no-data
- total deadline and cancellation
- fixed fallback with no raw provider message
- provider status, retrieval status, EvidenceDecision, and LLM status remaining
  distinct in the public process summary

Do not use live calls or long sleeps.

---

## 8. M4-02 - Golden Quality Stabilization

## 8.1 Root-cause boundary

The correction belongs in query candidate eligibility, not in the canonical
resolver:

```text
supported company + HBM topic token
-> resolve supported company
-> do not send HBM to SecurityResolver as a foreign ticker candidate

supported company + actual uppercase foreign ticker
-> preserve the existing conflicting-security clarification behavior

standalone actual uppercase foreign ticker
-> preserve unsupported behavior
```

Use a narrow, project-owned domain-token allowlist in
`app/planning/query_planner.py`. For this checkpoint the required token is
exactly `HBM`. Do not broadly exempt uppercase words and do not add `HBM` as a
security alias.

## 8.2 Required exact tests

Add or preserve exact tests for:

- Samsung Electronics plus `HBM` resolves to `KRX:005930`
- SK Hynix plus `HBM` resolves to `KRX:000660`
- `HBM` without a supported security does not resolve to a company
- standalone `AAPL` remains unsupported
- Samsung Electronics plus `AAPL` still requires clarification
- canonical name, ticker, security ID, and approved aliases still resolve
- ambiguous `삼성`, `SK`, and `현대` still require clarification
- multiple supported companies still do not first-match
- wrong-company Evidence remains fully blocked
- `B0-09`, `B0-10`, `B0-12`, and `B0-17` no longer fail because `HBM` was
  classified as a foreign ticker

Do not weaken fixture expectations, forbidden-company assertions, numeric
validation, or safety assertions to increase the score.

## 8.3 Gate

Required B8 quality result:

- fixture total remains exactly `34`
- fixture content remains unchanged
- existing M3 runner threshold remains unchanged
- full golden at least `31/34` (`>= 90%`)
- Critical exactly `17/17` (`100%`)
- public exposure exactly `0`
- wrong-company blocking `100%`

The implementation target is to close all four shared-root-cause HBM failures.
If a case still fails for an independent downstream reason, record that failure
taxonomy explicitly. The bundle still cannot pass below `31/34`.

---

## 9. M4-03 - Minimum Structured Observability

## 9.1 Ownership

Create a private internal observation boundary:

- `app/services/observability.py`
- an immutable internal request-observation record
- a small sink protocol
- a standard-library JSON logging sink
- an injectable in-memory sink for deterministic tests

This internal record is not a public API model and must not be added to
`PublicProcessSummary`.

## 9.2 Minimum fields

One completed-request observation contains only:

- `request_id`
- `intent`
- `security_id`
- provider status by requested source
- selected Evidence count
- `retrieval_strategy`
- final EvidenceDecision status
- total latency in milliseconds
- LLM call count
- `fallback_used`

`retrieval_strategy` must be copied directly from the request pipeline's
validated internal `RetrievalResult.strategy`. Do not infer it from the user
question, reparse public-summary wording, create a new strategy label, or
serialize the full retrieval result.

`fallback_used` is fixed as:

```text
generation_mode == "fixed_template"
```

| generation mode | fallback_used |
|---|---|
| `llm` | `false` |
| `fixed_template` | `true` |
| `blocked` | `false` |
| `not_called` | `false` |

Additional bounded fields are allowed only when needed to distinguish a
sanitized terminal outcome. Do not log content-bearing fields.

## 9.3 Request ID and determinism

- generate an opaque request ID per request
- do not derive it from `session_id`, message text, or a local path
- inject the request-ID factory in tests
- inject or reuse the existing monotonic clock for latency tests
- serialize JSON with stable key ordering
- do not mutate `ChatRequest`, `ChatResponse`, or pipeline inputs

## 9.4 Default sink and terminal emission

`ChatService` defaults to `JsonLogObservationSink` backed by a project-owned
standard-library logger. The runtime default must not be a no-op sink.

Tests inject `InMemoryObservationSink`. A custom sink remains injectable so
tests do not depend on process-global log capture.

Exactly one terminal observation is emitted for every returned `ChatResponse`
with one of these statuses:

- `complete`
- `partial`
- `no_evidence`
- `provider_failed`
- `blocked`

Requests that fail before a `ChatResponse` can be built are outside the M4-03
terminal-observation scope. They continue to surface only the existing
sanitized `ChatServiceError`.

## 9.5 Privacy and failure behavior

The log must never contain:

- user message or session ID
- prompt or hidden reasoning
- answer text
- document or Evidence text/snippet
- raw provider payload
- raw exception
- credential or authorization value
- local absolute path
- source URL or locator

Use an allowlist projection from already validated internal state. Do not run
generic object serialization on request, response, provider result, Evidence,
or exceptions.

Observation emission failure must not replace an otherwise valid user response.
It may be swallowed at the sink boundary without logging the raw exception.

## 9.6 Required tests

Verify:

- exact JSON keys and value types
- provider statuses remain per source
- `no_data` and provider failures remain distinct
- `retrieval_strategy` is exactly the internal `RetrievalResult.strategy`
- EvidenceDecision and fallback are correct
- `fallback_used` is true only for `fixed_template`
- `llm`, `blocked`, and `not_called` record `fallback_used=false`
- LLM call count is `0` or `1` from the request-owned call budget
- latency is finite and non-negative
- fixed request ID and clock produce deterministic output
- caller inputs and returned response are not mutated
- sentinel message, session ID, prompt, Evidence text, exception, secret,
  source URL, and local path do not appear
- sink failure does not crash a completed request
- the default runtime sink is `JsonLogObservationSink`, not a no-op
- each returned complete, partial, no_evidence, provider_failed, or blocked
  response emits exactly one terminal observation
- a request that raises before creating `ChatResponse` emits no terminal
  observation

---

## 10. File Ownership

Expected implementation files:

- `app/planning/query_planner.py`
- `app/services/chat_service.py`
- `app/services/observability.py`
- `tests/unit/test_query_planner.py`
- `tests/unit/test_chat_service.py`
- `tests/unit/test_observability.py`
- `tests/integration/test_b8_quality_phase_slice.py`
- `tests/integration/test_m3_gate.py`
- `docs/TASK_CARDS/B8-quality-observability.md`

Regression-only files, not expected to change:

- `app/core/resolver.py`
- `app/providers/base.py`
- `app/services/source_gateway.py`
- `scripts/m3_gate.py`
- `tests/fixtures/evaluation/m3_golden_cases.json`
- existing M1/M2 tests

If changing a regression-only file becomes necessary, stop and report the
specific contract gap before editing it.

Forbidden changes:

- `app/core/models.py`
- `app/core/status.py`
- `app/api/schemas.py`
- provider adapters
- ingest modules
- retrieval and Evidence modules
- answer prompt/model/validator code
- UI code
- `pyproject.toml`
- `uv.lock`
- `.env.example`
- CI or Docker files

---

## 11. Implementation Order

1. Run B8-0 preflight.
2. Add failing M4-01 end-to-end failure/fallback tests.
3. Confirm whether existing provider/service behavior already passes.
4. Make only the minimum service-boundary correction if an approved M4-01
   test exposes a defect.
5. Add HBM and foreign-ticker negative tests.
6. Add the narrow `HBM` domain-token eligibility rule.
7. Run the four exact golden cases, then the full gate.
8. Add the private observability module and deterministic unit tests.
9. Wire one terminal observation into `ChatService`.
10. Run targeted, composition, full, gate, smoke, privacy, compile, and diff
    checks.
11. Review the complete diff and report results.
12. Do not commit or push without a separate user approval.

---

## 12. Verification

## 12.1 M4-01 targeted

```powershell
& $python -m pytest `
  tests/unit/test_provider_base.py `
  tests/unit/test_source_gateway.py `
  tests/unit/test_chat_service.py `
  tests/integration/test_b8_quality_phase_slice.py `
  -q
```

## 12.2 M4-02 targeted and gate

```powershell
& $python -m pytest `
  tests/unit/test_security_resolver.py `
  tests/unit/test_query_planner.py `
  tests/unit/test_m3_gate_runner.py `
  tests/integration/test_m3_gate.py `
  -q

& $python scripts/m3_gate.py
```

Record:

- each of `B0-09`, `B0-10`, `B0-12`, and `B0-17`
- full numerator, denominator, and percentage
- Critical numerator, denominator, and percentage
- public exposure count

## 12.3 M4-03 targeted

```powershell
& $python -m pytest `
  tests/unit/test_observability.py `
  tests/unit/test_chat_service.py `
  tests/integration/test_b8_quality_phase_slice.py `
  -q
```

## 12.4 B8 composition and full regression

```powershell
& $python -m pytest `
  tests/unit/test_provider_base.py `
  tests/unit/test_source_gateway.py `
  tests/unit/test_security_resolver.py `
  tests/unit/test_query_planner.py `
  tests/unit/test_answer_composer.py `
  tests/unit/test_answer_validators.py `
  tests/unit/test_chat_service.py `
  tests/unit/test_observability.py `
  tests/unit/test_ui_projections.py `
  tests/unit/test_m3_gate_runner.py `
  tests/integration/test_m2_phase_slice.py `
  tests/integration/test_m3_chat_phase_slice.py `
  tests/integration/test_streamlit_app.py `
  tests/integration/test_m3_gate.py `
  tests/integration/test_b8_quality_phase_slice.py `
  -q

& $python -m pytest tests -q
```

## 12.5 Smoke and hygiene

```powershell
& $python -c "from app.planning.query_planner import QueryPlanner; from app.services.observability import JsonLogObservationSink; from app.services.chat_service import ChatService; print('b8-import-ok')"
& $python scripts/secret_scan.py
& $python -m compileall app tests scripts -q

git diff --check
git diff --name-status
git diff --stat
git status --short --branch
```

After the `ChatService` observation wiring, run the existing Streamlit AppTest
suite and a finite headless startup with HTTP health `200`. The observation
path must not change the current UI response or startup behavior.

---

## 13. Stop Conditions

Stop implementation and report evidence if:

- preflight fails
- the approved B7 or M3 Gate baseline cannot be reproduced
- a public schema, core model, or status change appears necessary
- `SecurityResolver` must be weakened to handle `HBM`
- an M1 provider change appears necessary
- an M2 change beyond the single approved QueryPlanner `HBM` domain-token
  eligibility correction appears necessary
- a new dependency or lock update appears necessary
- a golden expected value must be weakened to pass
- wrong-company or any Critical case regresses
- full golden remains below `31/34`
- public exposure is nonzero
- raw content, secret, exception, or local path appears in a log
- live provider, credential, deployment, or B9 work is required
- the diff expands beyond the listed ownership without approval

The stop report must include:

- problem
- observed command or code evidence
- minimum correction
- alternative
- test and schedule impact

---

## 14. Risks and Fallback

Active risks:

- `R15` provider timeout causes whole-answer failure
- `R16` provider rate limit is confused with no-data or retried without bound
- `R25` wrong-company Evidence enters an answer
- `R30` numeric or company attribution changes
- `R53` golden defects are deferred until the final gate
- `R54` tests depend on live provider state
- `R55` LLM phrasing is mistaken for a stable evaluation contract
- `R56` observability scope expands into remote tracing
- `R57` logs expose user content, secrets, or raw source material
- `R58` unobserved quality numbers are reported as verified

Fallback:

- keep fake/recorded provider scenarios only
- preserve fixed safe fallback instead of forcing a generated answer
- keep the exact narrow `HBM` domain token rule
- use standard-library one-line JSON logging only
- omit optional observation fields rather than logging content
- disable the sink if logging itself threatens request stability
- stop new feature work when Critical or wrong-company tests fail

Rollback proposal:

- revert only the B8 implementation commit through a new revert commit
- never reset, restore, clean, or rewrite main history
- preserve B7 and M3 Gate artifacts

---

## 15. Completion Criteria

### Governance

- [x] B8 plan approved
- [x] B8-0 preflight PASS
- [x] locked interpreter and base SHA recorded
- [x] no dependency or lock change
- [x] no forbidden production file change
- [x] no live provider or live Gemini call

### M4-01

- [x] expected provider failures do not crash the request
- [x] provider failure and no-data remain distinct
- [x] partial usable Evidence is preserved
- [x] timeout, rate limit, provider unavailable, and parse error remain distinct
- [x] cache expiry and cache-hit contracts pass
- [x] total deadline cancellation passes
- [x] user-facing fallback is fixed and sanitized

### M4-02

- [x] `HBM` is treated as a domain token, not a foreign ticker candidate
- [x] actual foreign uppercase ticker behavior remains unchanged
- [x] supported security resolution remains exact
- [x] wrong-company regression remains fully blocked
- [x] four recorded HBM failures no longer fail for the original cause
- [x] full golden is at least `31/34`
- [x] Critical is `17/17`
- [x] public exposure is `0`

### M4-03

- [x] internal observation model remains separate from public UI schema
- [x] minimum fields are emitted once per completed request
- [x] request ID and clock are injectable in tests
- [x] default runtime sink is project-owned `JsonLogObservationSink`
- [x] returned ChatResponse statuses emit exactly one terminal observation
- [x] retrieval strategy equals the internal RetrievalResult strategy
- [x] LLM call count is bounded and accurate
- [x] fallback is true only for fixed-template generation
- [x] log output is deterministic apart from injected runtime values
- [x] no user content, prompt, secret, raw payload, exception, URL, or path
- [x] sink failure does not replace a valid response
- [x] no remote tracing or dependency added

### Verification

- [x] M4-01 targeted PASS
- [x] M4-02 targeted PASS
- [x] M4-03 targeted PASS
- [x] B8 composition regression PASS
- [x] full unit PASS
- [x] direct M3 Gate runner PASS
- [x] import smoke PASS
- [x] Streamlit AppTest and finite startup PASS
- [x] secret scan PASS
- [x] compile PASS
- [x] diff check PASS
- [x] GitHub CI accurately recorded
- [x] independent pytest rerun accurately recorded

---

## 16. Result Log

```text
B8 planning base:
52c015569111493f83ab27983839d18136da5655

B8 approved plan supplement SHA:
e53110ef19173f97eefc511ca7bc9c8a37aa786b

B8 approved plan supplement commit:
docs: refine B8 implementation contract

B8 approved plan supplement main push:
complete

B8 plan review:
PASS WITH REQUIRED FOLLOW-UP

B8 implementation approval:
APPROVED after required plan supplement and B8-0 preflight PASS

B8-0 preflight:
PASS
Initial sandbox run: environment failure - pytest temp directory PermissionError
Approved out-of-sandbox rerun: PASS
Focused: 309 passed, 1 warning
Full: 1763 passed, 2 warnings
Gate: 30/34 = 88.24%, Critical 17/17 = 100%, exposure 0
Import: b8-preflight-import-ok
Secret scan: []
Compile: exit code 0
Diff: exit code 0

M4-01 targeted:
PASS - final rerun 98 passed, 1 warning

M4-02 targeted:
PASS - 135 passed, 1 warning

M4-03 targeted:
Initial run: 46 passed / 9 failed because ProviderResult status was already a
string under QuestockModel use_enum_values and emission safely failed
Rerun: PASS - 55 passed, 1 warning

B8 composition regression:
Initial run: 381 passed / 1 failed because the approved default JSON sink made
the old direct-gate stderr-empty assertion obsolete
Gate runner observability rerun: 7 passed, 1 warning
Final rerun: PASS - 382 passed, 1 warning

Full unit:
PASS - 1795 passed, 2 warnings

M3 Gate:
baseline 30/34 = 88.24%
baseline Critical 17/17 = 100%
baseline public exposure 0
fixture total 34 unchanged
fixture content unchanged
runner threshold unchanged
B8 acceptance 31/34 or better
B8 rerun PASS - 34/34 = 100%
B8 Critical 17/17 = 100%
B8 public exposure 0
B0-09, B0-10, B0-12, B0-17 PASS

Import smoke:
PASS - b8-import-ok

Secret scan:
PASS - []

Compile:
PASS - exit code 0

Diff:
PASS - git diff --check exit code 0; CRLF conversion warnings only

GitHub CI:
NOT_RUN

Independent pytest rerun:
NOT_RUN

Streamlit AppTest:
PASS - 8 passed, 1 warning

Streamlit finite startup:
PASS - headless port 8521, /_stcore/health HTTP 200, process stopped after
verification

Scope deviation:
`tests/unit/test_m3_gate_runner.py` now validates allowlisted JSON observation
lines on stderr instead of requiring empty stderr. Production default logging
made the old assertion incompatible with M4-03. The M3 runner, fixture total,
fixture content, threshold, and production gate behavior were not changed.

Dependency/lock:
unchanged

Live provider/Gemini:
NOT_RUN / NOT_APPROVED

Implementation SHA:
not created

Commit/push/PR/merge/deploy:
implementation commit/push NOT_RUN - separate user approval required
PR/merge/deploy NOT_RUN / NOT_APPROVED

B9 planning:
BLOCKED until B8 implementation review PASS
```

---

## 17. Approval Request

Plan approval must explicitly cover:

1. the narrow `HBM` domain-token exclusion in QueryPlanner candidate selection
2. M4-01 deterministic provider-failure integration tests
3. the private standard-library JSON observation boundary
4. the listed implementation and test files
5. full golden `>= 31/34`, Critical `17/17`, and public exposure `0`

Approval of this Task Card authorizes implementation and local verification
only after B8-0 preflight passes. It does not authorize commit, push, PR, merge,
deployment, live provider calls, credentials, or B9 implementation.
