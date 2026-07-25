# TASK CARD - B6-REMAINDER Integrated Implementation Plan

## 1. Status and Approval

- Project: `Questock`
- Repository: `JJungDae/Questock`
- Branch: `main`
- Bundle: `B6 remainder`
- Included Steps:
  - `M3-15A` process-visible Streamlit UI scaffold
  - `M3-02` beginner-oriented answer structure
  - `M3-03` fact / interpretation / inference separation
  - `M3-14` report-plan integration criterion
  - `M3-05` glossary answer path
  - `M3-04` answer-card projection
  - `M3-07` source / error / stale projection
- Planning date: `2026-07-25`
- Pre-B6 code baseline:
  `d937d625e26495a3ee8c5a5b2c327dfbd2512ea9`
- Pre-B6 code baseline commit:
  `m3-01 conditional pass2 updates`
- Docs update and plan-review base:
  `f5b3c646ec8696ac5c70d0d700e6fd729fd83bc4`
- Final approved-plan document SHA:
  `cc9ff7e5951330ae34973d48abf0f065ac515576`
- B6 implementation base:
  `cc9ff7e5951330ae34973d48abf0f065ac515576`
- M2 Gate:
  `PASS`
- M3-00:
  `PASS / complete`
- M3-01 code blockers:
  `CLOSED`
- M3-01 final independent closure:
  `PASS WITH REQUIRED FOLLOW-UP`
- M3-01 remaining follow-up:
  `factual Task Card synchronization completed in this correction`
- B6 plan review:
  `FINAL APPROVED FOR IMPLEMENTATION`
- B6 plan closure:
  `NOT_REQUIRED`
- Total-agent re-review:
  `NOT_REQUIRED`
- User final plan approval:
  `APPROVED`
- B6 implementation:
  `PASS / complete`
- First B6 implementation SHA:
  `b7ddcd9eec9fe551fd9e6ab337de6a4d8e64c4fd`
- First B6 implementation commit:
  `Implement B6 remainder`
- First B6 implementation main push:
  `complete`
- First B6 implementation review:
  `CONDITIONAL PASS`
- B6 supplement SHA:
  `60e6203b265a967a8b6ba45da2ba3128e1e1bcfe`
- B6 supplement commit:
  `Fix B6 review findings`
- B6 supplement main push:
  `complete`
- B6 supplement review:
  `PASS WITH REQUIRED FOLLOW-UP`
- Required follow-up:
  `B6 factual Task Card synchronization and B7 integrated planning; no further B6 code correction requested`
- B7 planning:
  `ALLOWED`
- B7 implementation:
  `BLOCKED pending approved B7 plan and preflight PASS`
- Package-index access:
  `AUTHORIZED for streamlit==1.60.0 and its declared transitive closure`
- Dependency installation and lock update:
  `AUTHORIZED in Gate 1`
- Live Gemini:
  `NOT_INCLUDED / NOT_APPROVED`
- Live news, disclosure, or research-report provider work:
  `NOT_INCLUDED`
- Further commit, push, PR, merge, deployment:
  `NOT_APPROVED`

This document is the completed B6 implementation record after M3-01.
The next official implementation plan is
`docs/TASK_CARDS/B7-integrated-implementation-plan.md`.

It consumes the canonical project documentation:

- `docs/agent_handoff/SOURCE_OF_TRUTH_INDEX.md`
- `docs/agent_handoff/POST_M3_01_EXECUTION_FLOW_DECISION_2026-07-25.md`
- `docs/agent_handoff/PROJECT_PLAN_FINAL_PASS.md`
- `docs/agent_handoff/PROJECT_PLAN_FINAL_PASS_POST_M3_01_ADDENDUM.md`
- `docs/agent_handoff/AGENT_WORKFLOW.md`
- `docs/agent_handoff/AGENT_WORKFLOW_POST_M3_01_ADDENDUM.md`
- `docs/TASK_CARDS/M3-01-CLOSURE-STATUS-SYNC.md`
- `docs/TASK_CARDS/M3-15-DIRECTION-AND-SPLIT.md`
- the current M3-01 and canonical M3-15 Task Cards

Conversation-only summaries and older post-M3-01 flow drafts must not override
these repository documents after approval.

---

## 2. Quick Execution Flow

```text
Gate 0
latest main / clean tree / M3-01 regression / evaluation-asset inventory

B6-0
confirm M3-01 factual status sync
→ freeze ChatResponse and PublicProcessSummary

Gate 1
streamlit==1.60.0 dependency and uv.lock
→ clean Python 3.14 install
→ import / AppTest / startup smoke

B6-A
M3-15A Streamlit shell
→ transport boundary
→ answer/source component interfaces
→ process expander
→ UI smoke

B6-B
M3-02 beginner structure
→ M3-03 section separation
→ M3-14 report acceptance criterion

B6-C1
M3-05 glossary recorded path
→ approved data/glossary.json only
→ glossary answer behavior

B6-C2
M3-04 answer-card projection
→ M3-07 source/error/stale projection
→ B6 integration and UI closure

B6 Exit Gate
full regression
→ AppTest and startup smoke
→ Task Card result sync
→ external B6 implementation review
```

B6 completion does not close all of M3-15.

At B6 exit:

```text
M3-15A scaffold:
complete

M3-04 / M3-07 connection:
complete

M3-06 session semantics:
pending B7

M3-15B final closure:
pending B7
```

---

## 3. Normative Sources

### 3.1 Project governance

- `docs/agent_handoff/README_AGENT_RULES.md`
- `docs/agent_handoff/PROJECT_PLAN_FINAL_PASS.md`
- `docs/agent_handoff/AGENT_WORKFLOW.md`
- `docs/agent_handoff/LLM_STACK_DECISION.md`
- `docs/agent_handoff/FINANCIAL_CAPABILITY_BASELINE.md`
- `docs/agent_handoff/RISK_RESPONSE_MATRIX.md`
- `docs/agent_handoff/EXTENSION_COMPATIBILITY.md`
- `docs/agent_handoff/EVALUATION_TAXONOMY_DRAFT.md`
- `docs/agent_handoff/MENTORING_SCOPE_DECISION_2026-07-24.md`

### 3.2 Current Task Cards

- `docs/TASK_CARDS/M3-00-langchain-integration-spike.md`
- `docs/TASK_CARDS/M3-01-answer-schema-chat-service.md`
- `docs/TASK_CARDS/M3-15-process-visibility-ui.md`

Canonical M3-15 path:

```text
docs/TASK_CARDS/M3-15-process-visibility-ui.md
```

Document title:

```text
TASK CARD - M3-15 Process-Visible Streamlit UI
```

Do not create another similarly named M3-15 Task Card.

### 3.3 Official Streamlit metadata checked for this plan

Selected candidate:

```text
streamlit==1.60.0
```

Verified official metadata as of 2026-07-25:

- release date: `2026-07-21`
- release status: PEP 440 final, non-yanked
- project classifier: `Development Status :: 5 - Production/Stable`
- Python requirement: `>=3.10`
- Python classifier includes `3.14`
- license expression: `Apache-2.0`
- wheel: universal `py3-none-any`
- native test API:
  `streamlit.testing.v1.AppTest`
- extras:
  none selected

No Streamlit extra is approved.

---

## 4. Verified Current Repository State

At pre-B6 code baseline
`d937d625e26495a3ee8c5a5b2c327dfbd2512ea9` and docs update/review base
`f5b3c646ec8696ac5c70d0d700e6fd729fd83bc4`:

| Area | Verified state |
|---|---|
| docs update/review main | `f5b3c646...` |
| direct runtime dependencies | Pydantic, FastAPI, Uvicorn, LangChain Core, LiteLLM, tzdata |
| Streamlit dependency | absent |
| `app/ui/` | absent |
| root `streamlit_app.py` | absent |
| API endpoint | `POST /api/chat` exists |
| default external source state | explicit unconfigured for unsupported runtime source paths |
| approved local glossary | `data/glossary.json`, 15 approved entries |
| glossary ingest/index/locator | implemented under `app/ingest/glossary.py` |
| answer schema | stable M3-01 schema |
| PublicProcessSummary | stable `trace_version="m3-01-v1"` |
| current schema file blob | `c10da0270e00105a4f375ba79a2aac5451730a4a` |
| M3-15 Task Card blob | `a8cea6c9a629d9acafdcf87576ff3976110afa3c` |
| M3-01 Task Card | stale second-supplement status remains |
| full-suite historical result | `1573 passed, 2 warnings` in implementation environment |
| GitHub CI | `NOT_RUN` |
| independent pytest | `NOT_RUN` |
| golden / Critical executable assets | `UNVERIFIED` during remote planning audit |

The absence of remote code-search results for golden/Critical terms does not
prove that the assets do not exist. Gate 0 performs a local filesystem
inventory and records the exact result.

---

## 5. Bundle Goal

Complete the remaining B6 user-facing vertical slice without changing the
frozen M3-01 public API.

The completed B6 slice must provide:

```text
User question
→ Streamlit shell
→ UI-to-chat transport boundary
→ POST /api/chat
→ existing M3-01 pipeline
→ ChatResponse validation
→ beginner-oriented answer cards
→ citation-bound source details
→ collapsed PublicProcessSummary process panel
```

The same bundle must also establish:

- beginner-first answer ordering
- clear fact / interpretation / inference labels
- conservative report-plan presentation
- approved local glossary answers
- safe source links and locator summaries
- provider/no-data/timeout/stale user wording
- deterministic fixture and AppTest coverage
- no hidden raw diagnostics

---

## 6. Frozen Public Contracts

### 6.1 Freeze target

The following file is frozen for B6:

```text
app/api/schemas.py
```

Planning blob:

```text
c10da0270e00105a4f375ba79a2aac5451730a4a
```

Frozen public contracts:

- `ChatRequest`
- `ChatResponse`
- `PublicProcessSummary`
- every nested public summary model
- `trace_version="m3-01-v1"`
- `AnswerSections` public field names
- `Evidence` public field names

### 6.2 Freeze rule

B6 must not add, remove, rename, or change the type of a frozen public field.

B6 may:

- consume the fields
- project them into UI view models
- hide empty sections
- add internal, non-public helper models
- add internal prompt or acceptance rules
- add a new local source-gateway implementation that returns existing
  `FinancialDocument` and `SourceGatewayResult` contracts

### 6.3 Immediate stop triggers

Stop before further implementation if any checkpoint requires:

- `ChatRequest` field change
- `ChatResponse` field change
- `PublicProcessSummary` field change
- `trace_version` change
- `Evidence` schema change
- core model or status change
- M1/M2 behavior change

Such a change requires a new reviewed contract plan.

---

## 7. Streamlit Dependency Contract

## 7.1 Direct dependency

Add exactly:

```text
streamlit==1.60.0
```

to `[project].dependencies`.

Do not add:

- Streamlit extras
- a separate browser-testing framework
- Selenium
- Playwright
- a second HTTP client dependency
- a second package manager

### 7.2 Why Streamlit is required

M3-15 explicitly assigns the actual MVP UI to Streamlit and requires:

- answer cards
- source details
- process expander
- selector and question input
- AppTest or equivalent UI smoke
- clean Streamlit startup

The existing FastAPI API alone cannot satisfy UI01.

### 7.3 HTTP transport dependency decision

Do not add another runtime HTTP package.

The production UI transport uses Python standard-library HTTP facilities:

```text
urllib.request
urllib.parse
json
```

The transport must be injectable for deterministic tests.

`httpx` remains a dev dependency and must not be moved to runtime in B6.

Do not import `requests` merely because Streamlit installs it transitively.

### 7.4 Expected Streamlit dependency family

The official Streamlit metadata declares dependencies including families such
as:

- Altair
- Blinker
- Click
- GitPython
- NumPy
- Pandas
- Pillow
- PyDeck
- Protobuf
- PyArrow
- Requests
- Tenacity
- Toml
- Starlette
- Uvicorn
- AnyIO
- Python Multipart
- WebSockets
- Watchdog on non-Darwin platforms

The actual lock diff may contain only:

1. the direct project edge for `streamlit==1.60.0`
2. Streamlit's exact transitive closure
3. resolver metadata strictly required by that closure

### 7.5 Lock stop conditions

Stop and report rather than accepting the lock when:

- an existing direct pin changes
- `langchain-core==1.5.1` changes
- `litellm==1.83.7` changes
- `tzdata==2026.3` changes
- Pydantic or FastAPI direct constraints change
- another direct dependency is proposed
- a Streamlit extra appears
- an existing package outside Streamlit's declared dependency closure moves
  version
- an existing package inside Streamlit's declared dependency closure moves
  without a recorded package-specific resolver reason
- any package movement remains unexplained, regardless of count
- an exact pin or additional dependency differs from the reviewed plan
- clean Python 3.14 install fails
- `AppTest` import fails
- full M3-01 regression fails

Lock acceptance occurs only after the actual diff and clean-environment tests
pass. Record:

```text
existing locked packages moved:
per-package resolver reason:
outside declared closure:
lock accepted:
```

### 7.6 Removal and rollback

B6 UI code must remain isolated under `app/ui/` plus one root entry point.

Rollback:

1. remove `streamlit==1.60.0`
2. restore the pre-B6 `uv.lock`
3. remove only B6 UI files
4. keep M3-01 API and backend behavior intact

---

## 8. UI Ownership and Component Boundaries

## 8.1 M3-15A owns

- `streamlit_app.py` entry point
- page layout shell
- UI-to-chat transport protocol
- standard-library HTTP transport
- supported-security selector shell
- question input and submit
- loading and sanitized error states
- session-ID display and shell reset button
- generic answer component interface
- generic source component interface
- process-summary renderer
- process expander
- data-mode badge
- live-verification badge
- provider / retrieval / EvidenceDecision / LLMStatus visual separation

M3-15A does not decide answer-section semantics.

M3-15A does not interpret raw locator contents.

## 8.2 M3-04 owns

- `AnswerSections` to answer-card projection
- answer-card ordering
- Korean card labels
- empty-section hide/show
- explicit inference-card labeling
- basis-date and status presentation
- Red fallback:
  summary / risks / evidence

## 8.3 M3-07 owns

- `Evidence` to safe source-detail projection
- safe HTTP(S) link validation
- source-type-specific locator summary
- disclosure receipt presentation
- report page/section presentation
- glossary entry/section presentation
- missing-source wording
- provider failure wording
- no-data wording
- timeout / rate-limit wording
- freshness warning wording
- no raw locator dump

## 8.4 Central-file conflict rule

`app/ui/app.py` owns orchestration only.

Projection rules live in `app/ui/projections.py`.

Transport behavior lives in `app/ui/transport.py`.

Do not place all UI, HTTP, answer mapping, and locator mapping in one file.

If the proposed implementation cannot preserve these boundaries, stop before
adding more code.

---

## 9. UI Transport Contract

Define an internal protocol similar to:

```text
ChatTransport
  send(ChatRequest, timeout_seconds) -> ChatResponse
```

Production implementation:

```text
HttpChatTransport
```

Fixed limit:

```text
MAX_CHAT_RESPONSE_BYTES = 1_048_576
```

Rules:

- default endpoint:
  `http://127.0.0.1:8000/api/chat`
- endpoint may be overridden only through one B6-owned environment variable
- endpoint scheme is HTTP or HTTPS only
- embedded username or password is rejected
- query string, fragment, and empty host are rejected
- finite positive timeout
- default UI timeout:
  `21 seconds`
- request JSON contains exactly:
  - `message`
  - `session_id`
- response is validated with `ChatResponse.model_validate`
- unknown or invalid schema fails safely
- automatic redirects are disabled with an explicit no-redirect handler or
  equivalent standard-library boundary
- every 3xx response, including 301, 302, 307, and 308, uses a fixed sanitized
  failure
- `Content-Type` is required; its case-insensitive media type must be exactly
  `application/json`
- the only allowed optional content-type parameter is case-insensitive
  `charset=utf-8`; unknown or duplicate parameters are rejected
- when `Content-Length` exists and exceeds `MAX_CHAT_RESPONSE_BYTES`, reject
  before reading the body
- streamed reading always stops at `MAX_CHAT_RESPONSE_BYTES + 1`, so absent or
  inaccurate `Content-Length` cannot bypass the cap
- exactly `MAX_CHAT_RESPONSE_BYTES` is allowed; any larger body uses a fixed
  sanitized failure
- invalid content type, oversized response, invalid JSON, invalid
  `ChatResponse`, HTTP error, and socket error use fixed user messages
- partial or oversized response bodies are never logged or shown
- raw URL, response body, exception, path, or request data is not displayed
- no retry
- no background polling
- no infinite wait

Suggested environment names:

```text
QUESTOCK_API_URL
QUESTOCK_UI_TIMEOUT_SECONDS
```

Do not add these to `ProviderConfig` or `LLMConfig`.

Use a small B6-owned UI config object or local validation helper.

Tests inject a fake `ChatTransport`; application code must not import
`tests/fixtures`.

---

## 10. Supported-Security Selector Rule

The selector is an input convenience, not a second resolver.

Rules:

- choices:
  - 선택 안 함
  - 삼성전자
  - SK하이닉스
  - 현대자동차
- the submitted backend contract remains only `message + session_id`
- selecting a company may prefill an empty question input
- after the user edits the question, submit the user's exact text
- the UI must not silently replace a company explicitly written in the question
- the UI must not claim resolution before receiving backend
  `PublicSecuritySummary`
- backend resolution status remains the source of truth

---

## 11. B6-0 — Process-Integrity Sync and Preflight Freeze

## 11.1 Purpose

Synchronize M3-01 facts and freeze the contract before UI and answer changes.

Run B6-0 only after Gate 0 passes. The section order in this document does not
authorize B6-0 before the baseline check.

## 11.2 Required document updates

Confirm `docs/TASK_CARDS/M3-01-answer-schema-chat-service.md` already records:

```text
Second supplement SHA:
d937d625e26495a3ee8c5a5b2c327dfbd2512ea9

Second supplement commit:
m3-01 conditional pass2 updates

Second supplement main push:
complete

Final closure review:
PASS WITH REQUIRED FOLLOW-UP

Code blockers:
CLOSED

Required follow-up:
factual synchronization complete

M3-01 status:
PASS / complete

M3-02 and B6 planning:
ALLOWED
```

Update `docs/TASK_CARDS/M3-15-process-visibility-ui.md` with:

- planning base:
  the final approved-plan document SHA
- M3-01 prerequisite:
  `PASS / complete`
- frozen schema file blob:
  `c10da0270e00105a4f375ba79a2aac5451730a4a`
- trace version:
  `m3-01-v1`
- planning:
  `PENDING B6 plan review`
- implementation:
  `BLOCKED pending B6 plan approval and Gate 0/1`

Do not mark M3-15 complete.

At B6-0, also record the Gate 0-resolved B6 implementation base in:

- the Gate 0 result
- the B6 result log
- the first checkpoint HANDOFF
- the relevant Task Card status

## 11.3 Evaluation-asset inventory

Search locally for:

- full golden fixtures
- Critical subset
- taxonomy mapping
- runner or pytest marker
- M3 Gate result aggregation

Record:

```text
golden fixture path:
Critical subset path:
runner:
taxonomy mapping:
current case count:
B7-C required:
```

Rules:

- missing assets do not automatically block B6 UI work
- missing or non-executable assets set:
  `B7-C REQUIRED`
- do not implement the missing M3 Gate runner during B6
- do not claim an M3 Gate score during B6

## 11.4 Exit criteria

- M3-01 factual state synchronized locally
- M3-15 canonical path confirmed
- schema blob unchanged
- Gate 0-resolved B6 implementation base recorded
- evaluation inventory recorded
- no application code change yet

---

## 12. B6-A — M3-15A Streamlit UI Scaffold

## 12.1 Purpose

Create the actual Streamlit shell around the frozen M3-01 response contract.

## 12.2 Expected new files

- `streamlit_app.py`
- `app/ui/__init__.py`
- `app/ui/app.py`
- `app/ui/transport.py`
- `app/ui/projections.py`
- `tests/unit/test_ui_transport.py`
- `tests/unit/test_ui_projections.py`
- `tests/integration/test_streamlit_app.py`

A smaller equivalent split is allowed when ownership remains clear.

## 12.3 Expected modified files

- `.env.example`
- `docs/TASK_CARDS/M3-15-process-visibility-ui.md`
- the approved B6 Task Card/result log

## 12.4 Layout

### Sidebar

- project title
- supported-security selector
- session ID
- scaffold reset/new-session button
- data-mode badge after response
- live-verification badge after response

The button may replace the local UUID. It does not implement M3-06 backend
context retention.

### Main area

- question input
- submit
- loading state
- fixed validation/error message
- one non-streaming result

### Baseline answer area

At B6-A, render:

- response status
- resolved security
- basis date
- summary
- warnings
- missing sources
- a generic container for later answer cards

Do not implement the final M3-04 card semantics yet.

### Baseline source frame

At B6-A, render only citation-bound public Evidence already present in
`ChatResponse.evidence`:

- title
- source type
- published date
- snippet

Do not render raw locator or final source-specific locator rules yet.

### Process expander

Collapsed by default.

Render the fixed order:

1. security resolution
2. query plan
3. required source status
4. normalization / hard filter / freshness counts
5. retrieval
6. EvidenceDecision
7. context budget
8. citation counts
9. generation path

Do not display:

- raw question in diagnostics
- prompt
- format instructions
- chain-of-thought
- Evidence ID
- raw locator
- full document
- provider payload
- raw exception
- credential
- permission note
- local path

## 12.5 UI safety

- no `unsafe_allow_html=True`
- user and source text rendered as text, not executable HTML
- no raw Markdown injection from source data
- no internal stack trace
- no endpoint URL display
- no hidden test fixture in application code

## 12.6 B6-A tests

- pure transport success
- HTTP error
- timeout
- invalid URL
- embedded credential URL rejection
- invalid JSON
- invalid ChatResponse
- response exactly at `MAX_CHAT_RESPONSE_BYTES`
- response at `MAX_CHAT_RESPONSE_BYTES + 1`
- oversized `Content-Length`
- no-`Content-Length` streamed overflow
- redirect 301, 302, 307, and 308
- endpoint URL with query string
- endpoint URL with fragment
- endpoint URL with userinfo
- invalid content type
- raw response body, endpoint URL, and exception non-exposure
- secret/raw exception non-exposure
- projection exact field consumption
- unknown trace version safe failure
- AppTest initial render
- AppTest question input and submit with fake transport
- AppTest unconfigured result
- AppTest provider failure result
- process expander exists
- process stage order exact
- no prompt/reasoning/path/secret
- clean Streamlit headless startup
- M3-01 API regression
- full suite

## 12.7 B6-A exit status

```text
M3-15A shell:
complete locally

M3-04 cards:
not started

M3-07 source projection:
not started

M3-15 final closure:
pending
```

---

## 13. B6-B — M3-02, M3-03, and M3-14

## 13.1 Purpose

Improve answer organization without changing the public response schema or
weakening citation safety.

## 13.2 Core safety decision

B6 does not introduce unrestricted model paraphrasing.

Beginner-friendly behavior is produced through:

- fixed answer ordering
- clear Korean labels
- model selection of citation-bound Evidence text
- omission of unsupported sections
- approved beginner-authored glossary content
- deterministic missing-source and uncertainty wording

Any future non-extractive rewrite requires a separately approved support
validator contract.

## 13.3 M3-02 structure

Target presentation order:

```text
한 줄 결론
→ 왜 중요한가
→ 확인된 위험
→ 더 확인할 것
```

Internal section mapping:

| Beginner concept | Existing field |
|---|---|
| 한 줄 결론 | `summary` |
| 확인된 사실 | `facts` |
| 왜 중요한가 | `interpretation` |
| AI 정리·추론 | `inference` |
| 긍정 요인 | `positive_factors` |
| 확인된 위험 | `risk_factors` |
| 더 확인할 것 | `uncertainty` |

Rules:

- summary is short and first
- empty sections remain empty
- no unsupported section filler
- no direct investment action
- no future price or earnings certainty
- section placement never bypasses citation validation

## 13.4 M3-03 fact / interpretation / inference

- `facts`:
  direct Evidence text only
- `interpretation`:
  citation-bound material displayed under an interpretation label
- `inference`:
  optional, explicitly labeled, citation-bound, and omitted when unsupported
- `uncertainty`:
  fixed limitations, missing source, or conditional wording

The section label is the inference marker.

Do not prepend unsupported model-generated explanations to accepted claim text.

## 13.5 M3-14 report integration criterion

For `research_report_summary` and report Evidence, existing sections represent:

| Report content | Existing field |
|---|---|
| stated plan | `facts` |
| scheduled event | `facts` |
| growth condition | `positive_factors` or `interpretation` |
| risk condition | `risk_factors` |
| conditionality / missing confirmation | `uncertainty` |

Rules:

- no separate report API
- no new public field
- no future price prediction
- no guaranteed performance
- no model-supplied report metadata or URL
- report permission gate remains unchanged
- report text remains citation-bound

## 13.6 Expected files

Modified:

- `app/answer/models.py` only if an internal validation rule is needed
- `app/answer/composer.py`
- `tests/unit/test_answer_composer.py`
- `tests/unit/test_chat_service.py`
- `tests/integration/test_m3_chat_phase_slice.py`
- B6 result log

Do not modify `app/api/schemas.py`.

## 13.7 B6-B tests

- exact section allow-list
- section order projection input
- fact remains fact
- inference is explicitly separate
- inference omitted when unsupported
- malformed or extra structured field fails closed
- unknown Evidence ID rejected
- citation rejection rejects the whole LLM draft
- no second LLM call
- report plan / event / condition / risk fixtures
- report future certainty rejected
- direct advice rejected or absent
- equal fixture result deterministic
- M3-01 regression
- B6-A UI smoke remains passing

---

## 14. B6-C1 — M3-05 Glossary Answer Path

## 14.1 Why C1 is an internal sub-checkpoint

Glossary backend integration and UI projection are distinct code boundaries.

They remain within one B6 plan and one external B6 review, but local Codex must
finish and self-review C1 before C2.

## 14.2 Approved data source

Use only:

```text
data/glossary.json
```

Current approved identity:

- corpus type: approved corpus
- language: Korean
- approved entries: 15
- content origin: project user-authored
- corpus ingest allowed: true
- external LLM processing allowed: true
- source URL: absent
- source asset ID: absent

Use existing validation:

- `load_glossary_entries`
- `validate_glossary_corpus`
- `evaluate_actual_glossary_coverage`
- `build_glossary_index`
- `build_glossary_locator`

Do not import `tests/fixtures`.

## 14.3 M3-owned security-free glossary boundary

`financial_term` does not enter the generic `FinancialDocument` pipeline.

```text
financial_term QueryPlan
→ approved data/glossary.json load and fingerprint validation
→ canonical or alias direct lookup
→ existing Evidence objects constructed directly
→ M3-owned internal glossary result
→ existing citation validation
→ answer composition
→ existing ChatResponse + PublicProcessSummary
```

The branch must:

- consume only the approved corpus
- load and index once per glossary service/helper instance
- perform no per-section repeated file I/O
- validate the approved fingerprint before lookup
- use `lookup_glossary_entry` for canonical and alias matching
- construct no `FinancialDocument`
- bypass the generic M2 hard filter, freshness evaluator, and lexical retriever
- assign no fallback or sentinel security, including `KRX:005930`
- perform no network request
- import nothing from `tests/fixtures`
- remain deterministic

Every direct glossary `Evidence` uses the unchanged core model:

```text
source_type:
glossary

scope:
industry_common

subject_security_ids:
[]

mentioned_security_ids:
[]

document_id:
stable glossary document/section identifier

evidence_id:
stable glossary evidence/section identifier

locator:
corpus_id
entry_id
version
section
source_type
provider
ingestion_version

source_url:
None unless the approved corpus later supplies a safe HTTP(S) URL
```

IDs are derived deterministically from corpus ID, entry ID, version, and
section. They do not use a runtime index, execution time, local path, or Python
hash.

Available sections:

- definition
- why_it_matters
- caution
- formula when present
- example when present

## 14.4 Internal result and ChatService integration

Use an M3-owned internal result such as `GlossaryPipelineResult`, or an
equivalent private helper contract, containing:

- glossary `ProviderResult`
- direct `Evidence` tuple
- existing `RetrievalStatus`
- selected count
- lookup found/not-found state
- `data_mode="recorded"`
- `live_connectivity_checked=false`
- stable fields needed to construct the existing `PublicProcessSummary`

The provider result passes the existing centralized ProviderResult contract:

- found lookup: `ok`
- unknown lookup: `no_data`
- load, fingerprint, or validation failure: an existing typed failure status
  with a fixed sanitized message

For policy composition, the M3-owned branch may construct existing internal
M2 result objects without invoking their security-dependent generic
evaluators:

- a glossary `FreshnessResult` with one `FreshnessWindow` using
  `applied_by="none"`, direct Evidence, and no fabricated warning
- a `RetrievalResult` using existing `OK` for selected Evidence or `EMPTY` for
  no match, with a stable glossary-direct strategy label
- an `EvidenceDecision` produced by the existing `EvidencePolicy` from the
  actual provider, freshness, and retrieval results
- an existing context-budget result from the decision Evidence

`ChatService` handles `financial_term` in this private M3-owned branch before
the generic `FinancialDocument` pipeline. Non-glossary plans continue through
the existing `SourceGateway` path and remain explicitly unconfigured where
they are unconfigured today.

Do not:

- change the `SourceGateway` public protocol
- add a new public route or schema
- change core/shared models
- add an M1/M2 hard-filter special case
- change non-glossary provider behavior

The existing public summary fields have these exact meanings for glossary:

```text
sources.glossary.document_count:
matched glossary section count

normalized_count:
directly constructed valid glossary Evidence count

hard_filtered_count:
security-free glossary eligibility checks passed count

freshness_retained_count:
count retained by the glossary non-temporal policy

retrieval_selected_count:
final selected glossary Evidence count

retrieval_status:
existing OK when selected, otherwise existing EMPTY

EvidenceDecision:
actual provider, lookup, freshness, and retrieval result
```

No count is filled with a fabricated zero or success value.

Composer and citation rules:

- pass `documents_by_id={}` for direct glossary Evidence
- keep the research-report external-processing permission rule unchanged
- allow only security-free glossary Evidence for `financial_term` citations
- preserve whole-draft citation fail-closed behavior
- make no second LLM call
- return a fixed no-evidence/unsupported response for an unknown term

## 14.5 Glossary answer behavior

Citation-bound selected glossary sections map deterministically:

| Glossary section | Answer section |
|---|---|
| definition | `summary` |
| why_it_matters | `interpretation` |
| caution | `uncertainty` |
| formula | `facts` |
| example | `facts` |

Rules:

- definition first
- why it matters second
- caution always visible when selected
- formula/example shown only when present
- no general-knowledge completion when glossary retrieval is empty
- unsupported term returns a fixed unsupported/no-evidence message
- no security is required for `financial_term`
- locator remains citation-valid
- no raw corpus permission note reaches UI

## 14.6 Expected files

New or modified, subject to local preflight:

- one M3-owned glossary service/orchestrator under `app/services/`
- `app/services/chat_service.py` for the private `financial_term` branch
- `app/answer/composer.py` or one glossary projector helper
- one focused glossary service/orchestrator unit test
- `tests/unit/test_chat_service.py`
- `tests/unit/test_answer_composer.py`
- `tests/integration/test_m3_chat_phase_slice.py`
- B6 result log

Do not modify the glossary corpus content in B6.

## 14.7 B6-C1 tests

- approved corpus fingerprint
- 15-entry coverage
- no empty-security `FinancialDocument` construction
- no fallback `KRX:005930` in glossary response or Evidence
- `scope="industry_common"`
- empty subject and mentioned security IDs
- canonical term
- alias
- unknown term
- stable document IDs
- stable Evidence IDs
- valid locator with corpus/entry/version/section/provider/ingestion version
- one load/index per service or helper instance
- actual process-summary counts
- existing retrieval status and EvidenceDecision mapping
- citation validation with `documents_by_id={}`
- whole-draft citation failure remains fail-closed
- no public schema or route change
- no local path
- no test fixture import
- formula absent/present
- no security required
- default non-glossary remains unconfigured
- deterministic equal output
- prompt permission remains literal true
- M1 glossary ingest tests unchanged
- M2 retrieval/citation regression
- B6-A/B regression

---

## 15. B6-C2 — M3-04 and M3-07 UI Projection

## 15.1 M3-04 answer cards

Final order:

1. 한 줄 결론
2. 확인된 사실
3. 왜 중요한가
4. 긍정 요인
5. 확인된 위험
6. AI 정리·추론
7. 더 확인할 것
8. 근거

Rules:

- hide empty cards
- inference card always has an explicit AI/inference label
- no card invented from missing data
- no duplicate claim across cards unless it exists in separate approved sections
- basis date visible
- response status visible
- Red fallback:
  - summary
  - risk
  - evidence

## 15.2 M3-07 source details

Common fields:

- title
- source type
- published date
- snippet

Safe link:

- HTTP(S) only
- no embedded credentials
- no secret-like query key
- no local path
- missing URL is allowed
- no raw locator JSON

Source-specific summary:

### News

- provider label
- published date
- approved original link when safe

Do not show internal search query or raw index.

### Disclosure

- receipt/report identifier
- section when present
- approved DART link when safe

### Research report

- publisher
- title
- published date
- manifest/document ID
- page
- section

No local file path or permission note.

### Glossary

- canonical title
- entry ID
- version
- section
- no original link when absent

## 15.3 Stable error and warning wording

Map only fixed codes.

Examples:

| Code/status | UI wording intent |
|---|---|
| `no_data` | 자료가 확인되지 않음 |
| `timeout` | 자료 확인 시간이 초과됨 |
| `rate_limited` | 자료 제공 한도에 도달함 |
| `provider_unavailable` | 자료 제공 경로가 구성되지 않았거나 이용 불가 |
| `parse_error` | 자료 형식을 확인하지 못함 |
| `stale_news` | 뉴스 기준 기간이 오래됨 |
| `stale_research_report` | 리포트 기준 기간이 오래됨 |
| `missing_published_at` | 게시일을 확인하지 못함 |
| `llm_generation_degraded` | AI 정리 대신 근거 기반 고정 응답 사용 |
| `request_deadline_exceeded` | 전체 요청 시간 제한에 도달함 |

Do not display raw provider messages or error codes as the primary user text.

## 15.4 Expected files

Modified:

- `app/ui/projections.py`
- `app/ui/app.py`
- `tests/unit/test_ui_projections.py`
- `tests/integration/test_streamlit_app.py`
- `docs/TASK_CARDS/M3-15-process-visibility-ui.md`
- B6 result log

The UI transport should not require modification unless a proven bug exists.

## 15.5 B6-C2 tests

- all answer card labels and order
- empty section hidden
- inference visibly marked
- Red fallback
- safe source URL
- credential URL hidden
- local path hidden
- type-specific locator projection
- missing URL
- no raw locator dump
- warning/status wording
- malicious Markdown/HTML rendered safely
- AppTest complete answer
- AppTest glossary answer
- AppTest provider failure
- AppTest unconfigured path
- AppTest LLM fallback
- process panel remains correct
- no prompt/secret/raw exception/path
- M3-01 API regression
- full suite

---

## 16. Allowed Files by Checkpoint

## B6-0

- `docs/TASK_CARDS/M3-01-answer-schema-chat-service.md`
- `docs/TASK_CARDS/M3-15-process-visibility-ui.md`
- approved B6 Task Card/result log

## Gate 1

- `pyproject.toml`
- `uv.lock`
- task-local dependency verification records
- B6 Task Card/result log

## B6-A

- `streamlit_app.py`
- `app/ui/**`
- `tests/unit/test_ui_*.py`
- `tests/integration/test_streamlit_app.py`
- `.env.example`
- M3-15 and B6 Task Cards

## B6-B

- `app/answer/models.py`
- `app/answer/composer.py`
- related answer/service/integration tests
- B6 result log

## B6-C1

- one or two M3-owned glossary service/orchestrator files
- `app/services/chat_service.py` when required
- one glossary answer projector helper when required
- `tests/unit/test_glossary_service.py` and related answer/service tests
- B6 result log

## B6-C2

- `app/ui/app.py`
- `app/ui/projections.py`
- UI tests
- M3-15 and B6 Task Cards

A file not listed above requires a stop-and-report decision before editing.

---

## 17. Forbidden Changes

- `app/api/schemas.py`
- `app/core/models.py`
- `app/core/status.py`
- existing resolver and QueryPlanner behavior
- M1 provider behavior
- M2 filter, retrieval, freshness, policy, citation, or budget behavior
- existing LangChain/LiteLLM/tzdata pins
- live Gemini
- live NAVER/OpenDART provider work
- research-report corpus changes
- glossary corpus text changes
- DB, migration, authentication, login
- persistent conversation storage
- M3-06 backend multi-turn semantics
- M3-08~11
- M3-12 or M5-01
- price schema or UI
- LangGraph, agents, tools, retrievers, vector stores
- streaming, SSE, WebSocket chat
- raw HTML rendering
- hidden chain-of-thought or prompt display
- application imports from `tests/fixtures`
- Docker implementation beyond an already approved B6 scaffold note
- actual deployment
- commit, push, PR, merge, deploy
- destructive Git operations

---

## 18. Local Checkpoint Workflow

Local Codex may proceed from one checkpoint to the next without external review
only when the checkpoint exit gate passes and no stop trigger occurs.

At every checkpoint, record:

```text
1. checkpoint ID
2. starting SHA
3. current branch
4. dirty files before work
5. changed files
6. changed classes/functions
7. targeted test command and result
8. prior-checkpoint regression
9. vertical-slice or AppTest smoke
10. secret scan
11. compile
12. git diff --check
13. remaining risk
14. deferred note
15. next-checkpoint decision
```

### HANDOFF format

```markdown
# B6 CHECKPOINT HANDOFF

## Checkpoint
- ID:
- Starting SHA:
- Current HEAD:
- Branch:

## Scope
- Completed:
- Not completed:
- Deferred:

## Files
- Added:
- Modified:
- Unexpected:

## Contract
- Public schema changed: NO
- M1/M2 changed: NO
- Dependency changed:
- Lock changed:

## Tests
- Targeted:
- Regression:
- UI/AppTest:
- Full:
- Secret scan:
- Compile:
- Diff check:

## Findings
- BLOCKER:
- Required follow-up:
- Deferred note:

## Next checkpoint
- ALLOWED / BLOCKED
- Reason:
```

Do not hide a failed command by rerunning only a narrower subset.

Record every failed command, correction, and rerun.

---

## 19. Immediate External Review Triggers

Stop local checkpoint progression and request review when:

- frozen public schema must change
- core/shared API must change
- M1/M2 code must change
- another dependency is required
- Streamlit version must change
- unexpected large lock movement occurs
- clean Python 3.14 install fails
- application needs test fixtures
- glossary needs a new public route or schema
- SourceGateway public contract must change
- actual live source/provider work is needed
- DB/migration/persistence becomes necessary
- external-processing permission changes
- Critical regression fails
- wrong-company Evidence reaches output
- unsafe/fake locator reaches output
- direct investment advice appears
- raw prompt, secret, exception, or path appears
- central UI files cannot preserve ownership
- B6-C1 and C2 require conflicting redesigns

---

## 20. Gate 0 — Latest Main and Baseline

Confirm:

```text
branch = main or approved task branch
HEAD = origin/main
HEAD contains the final approved B6 plan
no unreviewed commit exists after the approved-plan SHA
```

Resolve the B6 implementation base from the current `origin/main` only after
those checks pass, then record it in the Gate 0 result, B6 result log, first
checkpoint HANDOFF, and relevant Task Card status.

If commits exist after the approved-plan SHA:

1. inspect every intervening commit
2. compare their diffs with the approved plan
3. rerun contract freeze
4. stop when a material plan, schema, dependency, or ownership change exists

Allowed initial dirty scope:

- none; Gate 0 requires a clean working tree

### Baseline commands

```powershell
git status --short --branch
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
git log -5 --oneline --decorate

$python = ".\.venv\Scripts\python.exe"

& $python --version
& $python -m pytest --version
& $python -m pytest `
  tests/unit/test_answer_composer.py `
  tests/unit/test_source_gateway.py `
  tests/unit/test_public_process_summary.py `
  tests/unit/test_chat_service.py `
  tests/integration/test_m2_phase_slice.py `
  tests/integration/test_m3_chat_phase_slice.py `
  -q

& $python -m pytest tests -q

& $python -c "from app.api.schemas import ChatResponse, PublicProcessSummary; print('m3-01-schema-ok')"
& $python -c "from app.api.main import app; print('m3-01-api-ok')"
& $python scripts/secret_scan.py
& $python -m compileall app tests scripts -q
git diff --check
```

Historical implementation-environment reference:

```text
full suite:
1573 passed, 2 warnings
```

This historical count is not a substitute for Gate 0 rerun.

### Evaluation inventory commands

```powershell
$searchRoots = @("tests", "data", "docs", "scripts")

Get-ChildItem $searchRoots -Recurse -File |
  Where-Object {
    $_.Name -match "golden|critical|taxonomy|evaluation|gate"
  } |
  Select-Object FullName

rg -n `
  "full golden|golden set|Critical set|critical_set|taxonomy|M3 Gate" `
  tests data docs scripts
```

If `rg` is unavailable, use PowerShell `Select-String`.

Record missing tools as `NOT_AVAILABLE`; do not install an unapproved search
tool.

---

## 21. Gate 1 — Streamlit Dependency and Clean Lock

Gate 1 exclusively owns `pyproject.toml`, `uv.lock`, and task-local dependency
verification records. B6-A must not edit dependency or lock files.

## 21.1 Approved tool boundary

Prefer the existing approved `uv`.

When no approved uv executable exists, request approval before creating:

```text
.deps/b6-lock-tool
uv==0.11.32
```

Do not install or upgrade global Python, pip, uv, Rust, or another package
manager.

## 21.2 Lock commands

After adding `streamlit==1.60.0`:

```powershell
& $uv lock
& $uv lock --check
git diff -- pyproject.toml uv.lock
```

Review:

- direct pins unchanged
- Streamlit exact pin
- no extras
- only expected transitive closure
- no unexplained package movement

## 21.3 Clean environment

```powershell
$env:UV_PROJECT_ENVIRONMENT = ".deps\b6-streamlit-clean"

& $uv sync `
  --locked `
  --extra dev `
  --python .\.venv\Scripts\python.exe `
  --no-python-downloads

$cleanPython = ".\.deps\b6-streamlit-clean\Scripts\python.exe"

& $cleanPython -c "import streamlit; assert streamlit.__version__ == '1.60.0'; print(streamlit.__version__)"
& $cleanPython -c "from streamlit.testing.v1 import AppTest; print('streamlit-apptest-ok')"
& $cleanPython -c "from app.api.schemas import ChatResponse, PublicProcessSummary; print('schema-ok')"

& $cleanPython -m pytest `
  tests/unit/test_answer_composer.py `
  tests/unit/test_source_gateway.py `
  tests/unit/test_public_process_summary.py `
  tests/unit/test_chat_service.py `
  tests/integration/test_m2_phase_slice.py `
  tests/integration/test_m3_chat_phase_slice.py `
  -q

& $cleanPython -m pytest tests -q
& $cleanPython scripts/secret_scan.py
& $cleanPython -m compileall app tests scripts -q
```

Do not begin B6-A code until Gate 1 passes.

Cleanup only task-created `.deps/b6-*` paths after results are recorded.

---

## 22. Streamlit Startup Smoke

After B6-A entry point exists, run a finite startup check.

Example PowerShell outline:

```powershell
$streamlit = ".\.venv\Scripts\streamlit.exe"

$process = Start-Process `
  -FilePath $streamlit `
  -ArgumentList @(
    "run",
    "streamlit_app.py",
    "--server.headless=true",
    "--server.address=127.0.0.1",
    "--server.port=8501",
    "--browser.gatherUsageStats=false"
  ) `
  -PassThru

try {
  $deadline = (Get-Date).AddSeconds(15)
  $healthy = $false

  while ((Get-Date) -lt $deadline) {
    try {
      $response = Invoke-WebRequest `
        "http://127.0.0.1:8501/_stcore/health" `
        -UseBasicParsing `
        -TimeoutSec 2
      if ($response.StatusCode -eq 200) {
        $healthy = $true
        break
      }
    } catch {
      Start-Sleep -Milliseconds 500
    }
  }

  if (-not $healthy) {
    throw "Streamlit startup smoke failed."
  }
}
finally {
  if (-not $process.HasExited) {
    Stop-Process -Id $process.Id -Force
  }
}
```

Do not leave the process running.

Do not print environment secrets or raw app response data.

---

## 23. Targeted Verification Commands

Paths may be adjusted only to match the final approved file names.

### B6-A

```powershell
& $python -m pytest `
  tests/unit/test_ui_transport.py `
  tests/unit/test_ui_projections.py `
  tests/integration/test_streamlit_app.py `
  tests/unit/test_api_chat.py `
  tests/unit/test_public_process_summary.py `
  -q
```

### B6-B

```powershell
& $python -m pytest `
  tests/unit/test_answer_composer.py `
  tests/unit/test_chat_service.py `
  tests/integration/test_m3_chat_phase_slice.py `
  -q
```

### B6-C1

```powershell
& $python -m pytest `
  tests/unit/test_glossary_ingest.py `
  tests/unit/test_glossary_service.py `
  tests/unit/test_answer_composer.py `
  tests/unit/test_chat_service.py `
  tests/integration/test_m3_chat_phase_slice.py `
  -q
```

### B6-C2

```powershell
& $python -m pytest `
  tests/unit/test_ui_projections.py `
  tests/unit/test_ui_transport.py `
  tests/integration/test_streamlit_app.py `
  -q
```

### B6 focused integration

```powershell
& $python -m pytest `
  tests/unit/test_m3_langchain_stack.py `
  tests/unit/test_answer_composer.py `
  tests/unit/test_glossary_ingest.py `
  tests/unit/test_glossary_service.py `
  tests/unit/test_source_gateway.py `
  tests/unit/test_public_process_summary.py `
  tests/unit/test_chat_service.py `
  tests/unit/test_api_chat.py `
  tests/unit/test_ui_transport.py `
  tests/unit/test_ui_projections.py `
  tests/integration/test_m2_phase_slice.py `
  tests/integration/test_m3_chat_phase_slice.py `
  tests/integration/test_streamlit_app.py `
  -q
```

### Final

```powershell
& $python -m pytest tests -q

& $python -c "import streamlit; from streamlit.testing.v1 import AppTest; from app.api.schemas import ChatResponse, PublicProcessSummary; from app.api.main import app; print('b6-import-ok')"

& $python scripts/secret_scan.py
& $python -m compileall app tests scripts -q

git diff --check
git diff --name-status
git diff --stat
git status --short
```

---

## 24. B6 Exit Gate

B6 implementation is complete only when all conditions pass.

### Governance

- [x] total-agent plan review complete
- [x] user final approval complete
- [x] package-index and lock scope approved
- [x] no unapproved Git operation
- [x] canonical M3-15 path used

### M3-01 sync and freeze

- [x] second supplement SHA recorded
- [x] M3-01 `PASS / complete`
- [x] `app/api/schemas.py` unchanged
- [x] schema blob/fingerprint recorded
- [x] `trace_version="m3-01-v1"` unchanged

### Dependency

- [x] `streamlit==1.60.0` direct pin
- [x] no Streamlit extras
- [x] existing direct pins unchanged
- [x] lock diff reviewed
- [x] clean Python 3.14 install
- [x] Streamlit import
- [x] AppTest import
- [x] clean full regression

### M3-15A

- [x] Streamlit entry point
- [x] selector shell
- [x] question submit
- [x] finite transport timeout
- [x] injectable test transport
- [x] baseline answer frame
- [x] baseline source frame
- [x] process expander
- [x] status-family separation
- [x] no prompt/reasoning/secret/path/raw exception
- [x] headless startup smoke

### M3-02 / M3-03 / M3-14

- [x] beginner-oriented order
- [x] fact / interpretation / inference separation
- [x] inference explicitly labeled
- [x] unsupported section omitted
- [x] citation validation unchanged
- [x] report plan/event/condition/risk criterion
- [x] no future certainty
- [x] no direct investment advice
- [x] no second LLM call

### M3-05

- [x] approved `data/glossary.json` only
- [x] fingerprint verified
- [x] recorded M3-owned glossary service/orchestrator
- [x] section locator
- [x] term/alias retrieval
- [x] unsupported term safe fallback
- [x] default non-glossary remains unconfigured
- [x] no local path or permission note

### M3-04 / M3-07

- [x] final card order and labels
- [x] empty section hidden
- [x] inference marker
- [x] safe source link
- [x] type-specific locator summary
- [x] missing/no-data/timeout/stale wording
- [x] no raw locator
- [x] malicious HTML/Markdown safe

### Regression

- [x] checkpoint targeted tests
- [x] B6 focused integration
- [x] M2 phase slice
- [x] M3-01 phase slice
- [x] full suite
- [x] AppTest
- [x] Streamlit startup
- [x] secret scan
- [x] compile
- [x] diff check
- [x] clean-lock result separated
- [x] GitHub CI accurately recorded
- [x] independent test accurately recorded
- [x] live Gemini accurately recorded

### Final status

- [x] `M3-15A: complete`
- [x] `M3-04: complete`
- [x] `M3-05: complete`
- [x] `M3-07: complete`
- [x] `M3-15B: pending B7`
- [x] `M3 Gate: not yet claimed`
- [x] `B7-C required` accurately recorded from inventory

---

## 25. Stop Conditions

Stop B6 and report when:

- Gate 0 baseline fails
- latest main changed materially
- Streamlit 1.60.0 is unavailable or yanked
- Python 3.14 clean install fails
- lock diff changes existing direct pins
- additional dependency is needed
- public response schema must change
- M1/M2 code must change
- SourceGateway public contract must change
- test fixture must enter application code
- glossary approved fingerprint fails
- glossary requires a new public API route
- UI needs raw internal objects
- process panel requires recomputing backend state
- wrong-company Evidence appears
- unsafe URL or locator appears
- direct investment advice appears
- hidden reasoning or prompt appears
- raw secret, exception, or local path appears
- B6 checkpoint regression cannot be isolated
- full suite falls below the current unweakened baseline
- a checkpoint requires M3-06 or M3-08~11
- live provider or live Gemini becomes necessary
- file scope grows materially
- user approval boundary is reached

Report:

- finding
- classification
- source
- smallest safe correction
- alternatives
- test impact
- schedule impact
- whether total-agent review is triggered

---

## 26. Risk Mapping

| Risk | B6 control | Fallback |
|---|---|---|
| R01 scope overload | checkpoint boundaries and file ownership | split C1/C2, defer styling |
| R02 contract drift | frozen M3-01 schema blob | stop before schema edit |
| R07 docs/code mismatch | B6-0 sync and final result log | factual sync only |
| R20 UI/deployment complexity | Streamlit shell only, no deploy | local AppTest/startup |
| R29 unsupported citation | existing M2-07 unchanged | omit claim / fixed fallback |
| R31 section mixing | fixed section policy and labels | empty unsupported sections |
| R32 answer without Evidence | EvidenceDecision and citation gate | no-evidence response |
| R38 investment advice | existing block plus B6 tests | blocked/fixed response |
| R42 UI overload | answer first, process expander collapsed | summary/risk/evidence only |
| R56 observability overdesign | consume PublicProcessSummary only | omit optional presentation |
| R59 dependency/API drift | exact Streamlit pin and clean lock | remove Streamlit |
| R60 structured unsupported content | whole-draft citation rejection | deterministic fixed response |
| R61 external transmission | existing permission and prompt gates | local extractive fallback |

---

## 27. Result Log Template

```text
Pre-B6 code baseline:
d937d625e26495a3ee8c5a5b2c327dfbd2512ea9

Docs update/review base:
f5b3c646ec8696ac5c70d0d700e6fd729fd83bc4

Corrected plan:
complete and approved

Final approved-plan SHA:
cc9ff7e5951330ae34973d48abf0f065ac515576

B6 implementation base:
cc9ff7e5951330ae34973d48abf0f065ac515576

Documentation review:
PASS WITH REQUIRED FOLLOW-UP

B6 initial plan review:
CONDITIONAL PASS

B6 plan closure:
NOT_REQUIRED

User approval:
APPROVED

Gate 0:
PASS

Gate 0 focused regression:
89 passed

Gate 0 full regression:
1573 passed, 2 warnings

Gate 0 schema blob:
c10da0270e00105a4f375ba79a2aac5451730a4a

Gate 0 Evidence model blob:
54397337c3b3e152de247e585494ef4a6c92ef1a

Gate 0 AnswerSections model blob:
660563e4859c6301f709c1e2574828eb143781e0

trace_version:
m3-01-v1

Golden/Critical inventory:
24-question draft only in docs/TASK_CARDS/B0-M0-01-03-planning.md;
no executable golden fixture, Critical subset, runner, or aggregation

B7-C required:
REQUIRED

Streamlit metadata:
PASS - 1.60.0 / final / non-yanked / Apache-2.0 / Python >=3.10 / Python 3.14 classifier

Package-index access:
PASS - used for task-local uv==0.11.32 and the approved Streamlit closure

pyproject update:
PASS - added streamlit==1.60.0 only

uv.lock update:
PASS - resolved 97 packages

existing locked packages moved:
none

per-package resolver reason:
not applicable to movement; all 21 added name/version entries are in the
Streamlit 1.60.0 dependency tree

outside declared closure:
none

lock accepted:
yes - actual diff, locked check, clean imports, and clean regression passed

Clean Python 3.14 sync:
PASS - task-local .deps/b6-streamlit-clean using Python 3.14.3

AppTest import:
PASS - streamlit-apptest-ok

Gate 1 focused regression:
89 passed

Gate 1 clean full regression:
1573 passed, 2 warnings

Streamlit startup:
PASS - headless health returned HTTP 200 and process was stopped

B6-0 factual sync:
PASS - canonical M3-01 factual synchronization completed

B6-0 contract freeze:
PASS - ChatResponse, PublicProcessSummary, Evidence, AnswerSections, and
trace_version recorded without application-code changes

B6-A:
PASS - shell, transport, baseline projection, process panel, and AppTest

B6-A targeted:
57 passed

B6-A full regression:
1615 passed, 2 warnings

B6-B:
PASS - beginner section structure, report criterion, and safety validator

B6-B targeted:
51 passed

B6-B UI regression:
7 passed

B6-C1:
PASS - approved glossary direct path, Evidence/citation composition, and
sanitized provider-state mapping

B6-C1 targeted:
242 passed, 1 warning

B6-C1 M2/B6-A regression:
410 passed, 1 warning

B6-C2:
PASS - ordered answer cards, safe source details, fixed status wording, and
malicious-content-safe Streamlit projection

B6-C2 targeted:
54 passed, 1 warning

B6 focused:
358 passed, 2 warnings

Full suite:
1641 passed, 2 warnings

B6 first implementation SHA:
b7ddcd9eec9fe551fd9e6ab337de6a4d8e64c4fd

B6 first implementation commit:
Implement B6 remainder

B6 first implementation main push:
complete

B6 first implementation review:
CONDITIONAL PASS

B6 supplement scope:
M2 context-budget reuse for glossary; boundary-aware glossary attribution;
UI local-path/Markdown safety; answer-section duplicate-claim guard

B6 supplement targeted:
104 passed, 1 warning

B6 supplement focused:
386 passed, 2 warnings

B6 supplement context-budget regression:
122 passed, 2 warnings

B6 supplement full suite:
1669 passed, 2 warnings

B6 supplement AppTest:
6 passed, 1 warning

B6 supplement Streamlit startup:
PASS - headless health returned HTTP 200 and process was stopped

B6 supplement import smoke:
PASS - b6-fix-import-ok

B6 supplement secret scan:
PASS - []

B6 supplement compile:
PASS

B6 supplement diff check:
PASS - no whitespace errors; Git emitted LF-to-CRLF working-copy notices

B6 supplement environment deviation:
the repository .venv lacked Streamlit and the first targeted collection
failed; final verification used the existing task-local clean B6 environment
with Python 3.14.3 and Streamlit 1.60.0

B6 supplement SHA:
60e6203b265a967a8b6ba45da2ba3128e1e1bcfe

B6 supplement commit:
Fix B6 review findings

B6 supplement main push:
complete

B6 supplement independent review:
PASS WITH REQUIRED FOLLOW-UP

B6 required follow-up:
factual Task Card synchronization and B7 integrated planning only

Secret scan:
PASS - []

Compile:
PASS

Diff check:
PASS - no whitespace errors; Git emitted existing LF-to-CRLF working-copy
notices

Lock check:
PASS - 97 packages resolved, no lock drift

Import smoke:
PASS - b6-import-ok / streamlit 1.60.0

First implementation local API/UI smoke:
PASS - API health 200; glossary chat complete with 4 pre-supplement Evidence;
Streamlit health 200

Supplement final glossary contract:
PASS - 4 source sections, 4 normalized/hard-filtered/freshness/retrieval
items, 3 context-selected/public/cited Evidence, source-cap drop count 1

Pixel screenshot:
NOT_VERIFIED - Chrome headless captured the Streamlit shell before websocket
content rendering; AppTest remains the verified UI behavior evidence

Live Gemini:
NOT_RUN / NOT_APPROVED

Live source providers:
NOT_RUN / OUT_OF_SCOPE

GitHub CI:
NOT_RUN

Independent pytest:
NOT_RUN

B6 implementation commit/push:
b7ddcd9eec9fe551fd9e6ab337de6a4d8e64c4fd / complete

B6 supplement commit/push:
60e6203b265a967a8b6ba45da2ba3128e1e1bcfe / complete

B6 implementation review:
PASS WITH REQUIRED FOLLOW-UP

B6 implementation:
PASS / complete

M3-15A:
COMPLETE

M3-15B:
PENDING B7

M3 Gate:
NOT_CLAIMED

B7-C:
REQUIRED

Final local verdict:
B6 PASS / COMPLETE - B7 PLANNING ALLOWED
```

---

## 28. Approval Request

Requested after plan review:

- approve this B6-REMAINDER scope
- approve permanent direct dependency:
  `streamlit==1.60.0`
- approve package-index access for that exact release
- approve updating the existing `uv.lock`
- approve task-local `uv==0.11.32` only when no approved uv exists
- approve task-local clean Python environment creation and cleanup
- approve B6-0, B6-A, B6-B, B6-C1, and B6-C2 files
- approve local fixture/mock/AppTest/startup verification
- approve local documentation synchronization

Not requested:

- live Gemini
- credentials or billing
- live news, disclosure, or research-report providers
- M3-06
- M3-08~11
- M3-12 or M5-01
- DB or authentication
- streaming
- Docker deployment
- remote deployment
- commit
- push
- PR
- merge

---

## 29. Review Request

The review should independently determine:

1. whether `streamlit==1.60.0` is an acceptable exact dependency
2. whether the allowed lock boundary is sufficiently narrow
3. whether the frozen M3-01 schema is preserved
4. whether B6-A/B/C1/C2 ownership is clear
5. whether glossary recorded wiring is within B6 scope
6. whether M3-02/03 remain citation-safe
7. whether M3-15A and M3-15B statuses are separated
8. whether golden/Critical inventory is early enough
9. whether the checkpoint HANDOFF permits one final B6 review
10. whether any total-agent trigger remains unresolved

Implementation must not start until the reviewed plan and requested permission
scope are explicitly approved.
