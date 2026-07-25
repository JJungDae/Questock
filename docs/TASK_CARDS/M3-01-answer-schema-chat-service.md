# TASK CARD - M3-01 Answer Schema, Public Process Summary, LangChain Boundary, and ChatService

## 1. Status and Approval

- Task bundle: `B6: M3-01~05, M3-07, M3-15, and deployment scaffold`
- Step: `M3-01 Answer Schema and ChatService`
- Priority: `P0`
- Planning date: `2026-07-24`
- Planning branch: `main`
- Planning base SHA:
  `a3cb8e6de5309bc68ac6856648d275883ec9407f`
- Planning base commit: `Implement m3-00`
- M2 individual capabilities: `PASS`
- M2 integrated phase slice: `PASS`
- M2 Gate: `PASS`
- M3-00 implementation:
  `IMPLEMENTED AND PUSHED`
- M3-00 independent implementation review:
  `PASS - confirmed by user`
- Selected architecture:
  `Candidate A - langchain-core plus project-owned direct LiteLLM adapter`
- Selected direct pins:
  - `langchain-core==1.5.1`
  - `litellm==1.83.7`
- Existing lock:
  `uv.lock`
- Clean Windows timezone follow-up:
  `PASS - tzdata==2026.3 locked and clean-environment verified`
- M3-01 plan review:
  `CONDITIONAL PASS - required mentoring and integration corrections incorporated in this file`
- M3-01 final plan approval:
  `APPROVED by user`
- M3-01 implementation:
  `PASS / complete`
- First implementation SHA:
  `9b92d1b9923b74a2f3ea55f51c82fc2c731e83fc`
- First implementation commit:
  `Implement m3-01`
- First implementation main push:
  `complete`
- First implementation review:
  `CONDITIONAL PASS`
- First supplement SHA:
  `5433616bbf4d61f29fae11c86c770be80d69e750`
- First supplement commit:
  `m3-01 conditional pass updates`
- First supplement main push:
  `complete`
- First supplement closure review:
  `CONDITIONAL PASS - timeout status regression correction required`
- Second supplement SHA:
  `d937d625e26495a3ee8c5a5b2c327dfbd2512ea9`
- Second supplement commit:
  `m3-01 conditional pass2 updates`
- Second supplement main push:
  `complete`
- Final closure review:
  `PASS WITH REQUIRED FOLLOW-UP`
- Code blockers:
  `CLOSED`
- Required follow-up:
  `factual synchronization complete`
- Package-index access for the exact `tzdata` addition:
  `APPROVED / used only for exact tzdata lock update`
- Gemini live call:
  `SEPARATE APPROVAL / NOT INCLUDED`
- Further M3-01 code commit, push, PR, merge, deploy:
  `NOT_RUN / NOT_APPROVED`
- M3-12 price-move stretch:
  `NOT_ACTIVATED - post-M4 M5-01 owns the mentor-selected extension`
- UI implementation:
  `OUT_OF_SCOPE - M3-01 creates only the stable API and PublicProcessSummary contract`

This Task Card supersedes the framework, package-selection, lock-selection,
tracing, response-diagnostics, and source-gateway portions of all earlier
M3-01 drafts.

M3-00 already selected and pinned the framework boundary. M3-01 must not:

- repeat candidate comparison
- change the selected LangChain/LiteLLM versions
- introduce `langchain-litellm`
- generate a second lock
- add LangGraph, agents, retrievers, or vector stores

Approval of this plan may authorize only:

- the exact `tzdata==2026.3` dependency and existing `uv.lock` update
- the listed M3-01 application, schema, and test files
- the two implementation checkpoints in this Task Card
- fixture, mock, clean-lock, and regression verification
- factual Task Card and approved architecture-document synchronization after
  tests pass

Approval does not authorize:

- live Gemini or credential use
- paid usage or automatic billing
- another model or provider
- Streamlit or another UI implementation
- M3-02 or later behavior
- M3-12 or M5-01 price-move behavior
- commit, push, PR, merge, or deploy

---

## 2. Why M3-01 Exists

M3-00 proved the minimum framework boundary:

```text
project-owned Evidence/context adapter
→ ChatPromptTemplate
→ RunnableLambda(project-owned async LLMClient call)
→ PydanticOutputParser
→ project-owned validators
```

M3-01 turns that compatibility boundary into the first non-streaming answer
vertical slice:

```text
POST /api/chat
→ ChatService
→ completed M1/M2 pipeline
→ final selected Evidence
→ external-processing and prompt-safety gate
→ real LangChain RunnableSequence
→ project-owned LLMClient
→ direct LiteLLM Python SDK adapter
→ structured Pydantic draft
→ existing citation validation
→ stable public JSON response
```

The mentoring direction adds one presentation-critical requirement:

```text
The UI must later be able to show the observable M1/M2 processing stages
without exposing chain-of-thought, raw prompts, secrets, or internal exceptions.
```

M3-01 therefore also defines `PublicProcessSummary`, a sanitized and
deterministic public provenance contract. M3-15 will render that contract; it
does not invent another diagnostics schema.

M3-01 remains an extractive answer baseline. Beginner explanation, multi-turn,
numeric validation, policy validation, advanced source-detail UI, and final
visual styling remain later M3 Steps.

---

## 3. Normative Sources and Current Repository State

### 3.1 Normative documents

Use the latest project copies of:

- `docs/agent_handoff/README_AGENT_RULES.md`
- `docs/agent_handoff/PROJECT_PLAN_FINAL_PASS.md`
- `docs/agent_handoff/AGENT_WORKFLOW.md`
- `docs/agent_handoff/LLM_STACK_DECISION.md`
- `docs/agent_handoff/FINANCIAL_CAPABILITY_BASELINE.md`
- `docs/agent_handoff/RISK_RESPONSE_MATRIX.md`
- `docs/agent_handoff/EXTENSION_COMPATIBILITY.md`
- `docs/agent_handoff/EVALUATION_TAXONOMY_DRAFT.md`
- `docs/agent_handoff/MENTORING_SCOPE_DECISION_2026-07-24.md`
- `docs/TASK_CARDS/M2-INTEGRATION-CLOSURE.md`
- `docs/TASK_CARDS/M2-08-context-budget.md`
- `docs/TASK_CARDS/M3-00-langchain-integration-spike.md`

Older same-name copies must not be used when a 2026-07-24 revised copy exists.

### 3.2 Verified planning-base state

At planning base `a3cb8e6de5309bc68ac6856648d275883ec9407f`:

| Area | Current state |
|---|---|
| API app | health router only |
| provider policy | M1 owns timeout, retry, cache, and typed ProviderResult |
| config | ProviderConfig exists; LLMConfig does not |
| answer package | does not exist |
| LLM package | does not exist |
| service package | does not exist |
| M2 pipeline | normalization through citation/context budget implemented |
| M2 phase slice | persistent integration test exists |
| report permission | linked document metadata carries `external_llm_processing_allowed` |
| framework pins | `langchain-core==1.5.1`, `litellm==1.83.7` |
| lock | `uv.lock` exists |
| persistent framework test | `tests/unit/test_m3_langchain_stack.py` |
| clean Windows timezone | blocked because `tzdata` is not declared |
| existing project `.venv` | local tzdata is present |
| live Gemini | not run and not verified |
| production source gateway | does not exist |
| UI | not implemented |

The M2 integration test proves the internal pipeline with synthetic inputs. It
does not prove production source coverage, live provider access, a live LLM, or
a deployed UI.

---

## 4. Locked Architecture

### 4.1 Runtime order

```text
validate ChatRequest
→ QueryPlanner
→ injected SourceGateway
→ normalize documents
→ hard filter
→ freshness
→ retrieval
→ EvidencePolicy
→ context budget
→ EvidenceDecision gate
→ external-processing and prompt-safety gate
→ one structured LLM request when allowed
→ parse and validate structured draft
→ validate citations against transmitted final Evidence
→ build ChatResponse and PublicProcessSummary
```

M1/M2 order and responsibilities do not change.

### 4.2 Selected LLM boundary

```text
AnswerComposer
→ LangChain RunnableSequence
   ├─ ChatPromptTemplate
   ├─ RunnableLambda(project-owned LLMClient call)
   └─ PydanticOutputParser
→ project-owned LLMClient
→ LiteLLMClient
→ LiteLLM Python SDK
→ Gemini API
→ project-owned validators
```

Only `LiteLLMClient` may import LiteLLM. LangChain and provider raw objects
remain internal.

### 4.3 Fixed exclusions

- full `langchain`
- `langchain-litellm`
- LangGraph
- agents and tools
- LangChain retriever/vector store/memory
- prompt hub or remote prompt
- Router, Proxy, model fallback
- hidden retry
- tracing or callback logging
- streaming
- paid model or billing
- M1/M2 rewrites

### 4.4 Tracing and import safety

Before importing LiteLLM in the adapter:

```text
LITELLM_LOCAL_MODEL_COST_MAP=True
```

For every chain invocation:

```text
LANGSMITH_TRACING=false
LANGCHAIN_TRACING_V2=false
callbacks=[]
```

No direct LangSmith import is added. Hostile ambient tracing tests must prove
zero unexpected tracing/callback network calls.

---

## 5. Two Implementation Checkpoints

M3-01 remains one Task Card and receives one final implementation review, but
the implementation must be divided into two internal checkpoints.

## Checkpoint A - Runtime and generation core

Scope:

- `tzdata==2026.3` clean-lock correction
- `LLMStatus`
- `LLMRequest`, `LLMResult`, `LLMClient`
- `LLMConfig`
- `LiteLLMClient`
- structured draft models
- `AnswerComposer`
- real LangChain RunnableSequence
- external-processing eligibility
- prompt minimization and sanitizer
- citation-bound draft acceptance
- deterministic fixed fallback

Exit gate:

- all Checkpoint A targeted tests pass
- M3-00 compatibility test passes unchanged
- M2 phase slice passes unchanged
- secret scan and compile pass
- no M1/M2 or API/UI changes

## Checkpoint B - Chat vertical slice

Scope:

- `SourceGateway` protocol
- `ExplicitUnconfiguredSourceGateway`
- `ChatService`
- `ChatRequest`
- `ChatResponse`
- `PublicProcessSummary`
- `/api/chat`
- request deadline and cancellation
- M3 chat integration phase slice

Entry:

- Checkpoint A exit gate passes

No separate plan review occurs between A and B. Stop only when:

- core/shared contract change is required
- M1/M2 code must change
- a new dependency is required
- the approved file scope materially expands

If Git commits are later approved, A and B should be separate semantic commits.
This statement does not authorize commits.

---

## 6. Public Request and Response

## 6.1 ChatRequest

```json
{
  "message": "삼성전자 최근 위험 요인 알려줘",
  "session_id": "anonymous-uuid"
}
```

Rules:

- both fields are required nonblank strings
- fixed maximum lengths
- trim outer whitespace
- reject unknown fields
- M3-01 does not persist or replay session history
- validation errors do not echo raw message, credential-like content, or raw
  exception

## 6.2 ChatResponse

```text
status
security
basis_date
answer_sections
evidence
warnings
missing_sources
diagnostics_public
```

`diagnostics_public` is exactly one `PublicProcessSummary`.

`answer_sections`:

```text
summary
facts
interpretation
inference
positive_factors
risk_factors
uncertainty
```

M3-01 accepts only extractive claims that pass the existing M2 citation
contract. Unsupported sections remain empty.

Existing M1/M2 core models and enums are not modified.

---

## 7. PublicProcessSummary Contract

`PublicProcessSummary` is public provenance, not model chain-of-thought.

### 7.1 Top-level fields

```text
trace_version
data_mode
live_connectivity_checked
security
query_plan
sources
evidence_pipeline
decision
context_budget
citation
generation
```

### 7.2 Allowed values

```text
data_mode:
recorded | live | mixed | unconfigured

generation.mode:
llm | fixed_template | blocked | not_called
```

### 7.3 Security summary

```text
resolution_status
security_id
```

No candidate aliases or raw resolver diagnostics.

The M3-owned planning observation wrapper delegates to `SecurityResolver`
through the existing `QueryPlanner(resolver=...)` injection point.
`QueryPlanner` remains the only `QueryPlan` producer. The public status is:

- `resolved` for one accepted canonical security
- `ambiguous` for a true ambiguity or multiple resolved canonical securities
- `unsupported` for an explicit unsupported candidate without ambiguity
- `not_found` otherwise

Early blocked and out-of-scope plans retain a supported canonical observation
without exposing the raw query or candidate text.

### 7.4 Query-plan summary

```text
intent
required_sources
date_start
date_end
```

Do not echo the raw user question.

### 7.5 Source summaries

One entry per required source in request order:

```text
source_type
provider_status
document_count
from_cache
```

Do not include provider messages, raw payloads, query strings, credentials, or
internal error text.

### 7.6 Evidence-pipeline summary

```text
normalized_count
hard_filtered_count
freshness_retained_count
freshness_warning_codes
retrieval_status
retrieval_selected_count
```

Warning codes are stable project codes only.

### 7.7 Decision summary

```text
evidence_decision_status
satisfied_sources
missing_sources
no_data_sources
failed_sources
```

### 7.8 Context-budget summary

```text
input_count
unique_count
selected_count
duplicate_drop_count
source_cap_drop_count
count_cap_drop_count
context_drop_count
estimated_context_tokens
estimated_context_chars
```

### 7.9 Citation summary

```text
claim_count
citation_count
rejection_count
```

No claim text or rejected raw ID detail.

### 7.10 Generation summary

```text
mode
llm_status
model
live_verified
```

Rules:

- no call: `llm_status=None`, `model=None`
- fixture/mock call is never marked live
- `live_verified=true` only after a separately approved sanitized live smoke
- fallback does not change provider or EvidenceDecision status

### 7.11 Public safety

The summary must never expose:

- LLM chain-of-thought or hidden reasoning
- rendered prompt or format instructions
- raw user question
- full document or snippet text
- Evidence IDs
- URL or locator
- provider raw response or raw message
- credentials
- permission notes
- local path
- raw exception
- private diagnostics
- SDK or LangChain objects

### 7.12 Determinism

- stage order is fixed
- required source order follows QueryPlan
- counts match actual stage outputs
- equal fixture input produces equal JSON
- returned nested collections are fresh and isolated

M3-15 must consume this contract and must not recreate counts from raw internal
objects.

---

## 8. LLM Contracts

## 8.1 LLMStatus

Exactly:

```text
ok
timeout
rate_limited
authentication_error
provider_unavailable
invalid_response
content_blocked
```

It remains separate from ProviderStatus, RetrievalStatus, and
EvidenceDecisionStatus.

## 8.2 LLMResult

```text
content
model
provider
usage
finish_reason
latency_ms
status
```

Invariants:

- `ok` requires nonblank content
- failure statuses have no usable content
- usage is numeric, finite, sanitized, and deep-copied
- raw provider response and exception are never stored
- `invalid_response` covers parse/schema failure
- `content_blocked` remains distinct
- LLM status never changes `missing_sources`, ProviderStatus, or
  EvidenceDecision

## 8.3 LLMConfig

Environment names:

```text
GEMINI_API_KEY
LLM_MODEL
LLM_THINKING_BUDGET
LLM_MAX_OUTPUT_TOKENS
LLM_TIMEOUT_SECONDS
```

Rules:

- default model exactly `gemini/gemini-2.5-flash`
- reject preview/latest aliases and user-selected models
- explicit thinking budget only
- compare fixture values `0` and `1024`
- pin the smallest passing value
- bounded finite timeout and output-token count
- fake/unit mode loads without credential
- live adapter construction requires credential
- no secret appears in repr, str, JSON, summary, exception, log, or test output
- existing generic `LLM_API_KEY` is not a second credential source

`.env.example` contains names with empty values only.

## 8.4 LiteLLM mapping

- Python SDK only
- one request-scoped `LLMCallBudget(max_calls=1)` created by `ChatService`
- the exact budget is passed to `AnswerComposer`
- reservation occurs immediately before `LLMClient.complete()`
- parser, citation, prompt, timeout, and fallback paths never reserve a second
  call
- explicit model, timeout, max output tokens, thinking, response format, and
  retry-zero mapping
- normalize usage and finish reason
- normalize supported exceptions to LLMStatus
- no Router, Proxy, fallback model, hidden retry, or billing
- exactly one SDK operation per call
- cancellation produces no second operation
- raw SDK object never leaves adapter

---

## 9. Structured Draft and Composer

The LLM draft contains only a bounded sequence of:

```text
claim_id
section
text
evidence_ids
```

Rules:

- unknown fields rejected
- only allowed section labels
- claim text must pass existing extractive citation validation
- every referenced ID must be among externally transmitted selected Evidence
- any malformed JSON, wrong type, unknown ID, unsupported claim, or citation
  rejection invalidates the whole draft
- no partially accepted free text
- no model-supplied URL, locator, title, security, date, status, warning, or
  diagnostic
- parse/citation failure produces no second model call
- fallback is deterministic and local

The prompt contains only:

- current user question
- externally eligible selected Evidence IDs
- required snippets
- local parser format instructions

It must not contain session history, full documents, URLs, locators, metadata,
permission notes, provider payloads, raw exceptions, credentials, or paths.

---

## 10. SourceGateway Contract

## 10.1 SourceGateway protocol

`ChatService` receives an injected project-owned gateway returning:

```text
documents
provider_results_by_source
documents_by_id
data_mode
live_connectivity_checked
```

It must preserve every source key required by QueryPlan.

Validation also requires:

- documents only for requested sources whose ProviderResult is `ok`
- non-OK sources contribute zero documents
- `unconfigured` has zero documents, no live check, and only
  `provider_unavailable` results
- `recorded` has no live check
- `live` has a completed live-connectivity check
- `mixed` remains unavailable until an approved private provenance contract can
  prove both recorded and live document origins

Every gateway declares one immutable M3-owned timeout descriptor. On an elapsed
ChatService gateway deadline:

- configured `recorded` returns `timeout/total_deadline_exceeded`, keeps
  `data_mode=recorded`, and keeps `live_connectivity_checked=false`
- configured `live` returns `timeout/total_deadline_exceeded`, keeps
  `data_mode=live`, and keeps `live_connectivity_checked=true`
- explicit `unconfigured` remains `provider_unavailable`, `unconfigured`, and
  not live-checked

The timeout factory returns zero documents, preserves required source order,
passes `validate_source_gateway_result()`, and never exposes a raw timeout
exception or private descriptor.

The gateway may call existing provider policy helpers and existing local ingest
outputs. It must not reimplement retry, cache, deadline, or provider status
normalization.

## 10.2 ExplicitUnconfiguredSourceGateway

M3-01 must provide an explicit safe default.

When runtime data sources are not configured:

- do not import `tests/fixtures`
- do not silently treat synthetic fixtures as application data
- return every required source key
- return typed `provider_unavailable` results with stable sanitized errors
- return no documents
- set `data_mode="unconfigured"`
- set `live_connectivity_checked=false`
- allow ChatService to produce the existing provider-failed/fixed response
- expose only count/status summary through `PublicProcessSummary`

This permits a safe API process to exist without falsely claiming source
coverage.

## 10.3 Fake gateway in tests

Unit/integration tests inject a fake gateway explicitly.

Fake/recorded/live/unconfigured results must remain distinguishable. Test
fixtures do not become production source loaders.

## 10.4 Later demo/runtime gateway

A recorded demonstration gateway and application-owned demo corpus are deferred
to M3-15 or M4 demo preparation.

Requirements when later added:

- use an application-owned path such as `data/demo/**`
- do not read `tests/fixtures/**` from app code
- label the mode `recorded`
- preserve provider and Evidence contracts
- receive a separate plan and review

M3-01 completion does not claim meaningful live or recorded source coverage.

---

## 11. External Processing Eligibility

For `research_report` Evidence:

```text
linked FinancialDocument.metadata["external_llm_processing_allowed"] is True
```

must be proven.

Missing, false, malformed, or unavailable metadata excludes the Evidence from
the external prompt.

Rules:

- permission check occurs after context selection
- it does not alter retrieval score, freshness, or EvidenceDecision
- externally generated claims cite only transmitted Evidence
- local fixed templates may use final selected Evidence without transmitting it
- no eligible Evidence means zero LLM calls
- a project sanitizer audits the exact rendered messages
- unsafe content fails closed

---

## 12. Decision and Fallback

| Evidence decision / condition | LLM call | Public behavior |
|---|---:|---|
| blocked | no | fixed blocked response |
| no_evidence | no | fixed no-evidence response |
| provider_failed | no | fixed provider-failed response |
| complete/partial with empty budget | no | public no-evidence fallback; internal decision retained |
| complete/partial with no external-eligible Evidence | no | local extractive fixed response |
| complete/partial with eligible Evidence | at most one | structured LangChain path |
| any LLM failure | no second call | local extractive fixed response |
| parse/citation failure | no second call | local extractive fixed response |

Public status continues to reflect EvidenceDecision when selected Evidence
exists. LLM failure adds only a stable degradation warning.

For mixed valid and invalid fixed claims, M3-01 retains only claims whose
citations pass M2-07, preserving selected Evidence order. If none remain, it
returns the fixed no-evidence response. `ChatResponse.evidence` contains only
deep-copied Evidence referenced by accepted public citations; the
PublicProcessSummary context-budget counts remain the original M2 counts.

Generation mode in `PublicProcessSummary` must match the actual path.

---

## 13. Deadline Contract

- one monotonic 20-second request deadline
- providers execute concurrently through SourceGateway
- each operation receives no more than remaining time
- LLM timeout capped by remaining time
- no retry when remaining time is insufficient
- pending cancellable work cancelled at deadline
- completed source results preserved
- one source failure does not discard other results
- no operation waits after deadline
- tests use injected clocks/tasks, not real long sleeps

The service audits the deadline after the gateway, after the synchronous M2
pipeline, before model invocation, after composition, and after initial response
assembly. An expiry before model invocation adds
`request_deadline_exceeded`, performs no reservation or call, and uses the
decision-specific or citation-bound fixed response. If response assembly crosses
the deadline after an LLM call, the final audit replaces model output with the
citation-bound fixed response, records sanitized LLM `timeout`, and preserves
completed provider and M2 outputs.

---

## 14. Allowed Files

### New application files

- `app/api/schemas.py`
- `app/api/routes_chat.py`
- `app/answer/__init__.py`
- `app/answer/models.py`
- `app/answer/composer.py`
- `app/llm/__init__.py`
- `app/llm/base.py`
- `app/llm/litellm_client.py`
- `app/services/__init__.py`
- `app/services/planning_observation.py`
- `app/services/source_gateway.py`
- `app/services/chat_service.py`

### New tests

- `tests/unit/test_llm_config.py`
- `tests/unit/test_llm_base.py`
- `tests/unit/test_litellm_client.py`
- `tests/unit/test_answer_composer.py`
- `tests/unit/test_source_gateway.py`
- `tests/unit/test_public_process_summary.py`
- `tests/unit/test_security_planning_observation.py`
- `tests/unit/test_chat_service.py`
- `tests/unit/test_api_chat.py`
- `tests/integration/test_m3_chat_phase_slice.py`
- focused structured-output fixtures under `tests/fixtures/llm/`

### Modified

- `app/api/main.py`
- `app/config.py`
- `.env.example`
- `pyproject.toml`
- `uv.lock`
- this Task Card
- M3-00 Task Card status only after independent review result is known
- `LLM_STACK_DECISION.md` only for `tzdata` and factual implementation status
- `PROJECT_PLAN_FINAL_PASS.md` and `AGENT_WORKFLOW.md` only through the approved
  mentoring update bundle

No UI file is modified in M3-01.

---

## 15. Forbidden Changes

- M1/M2 core models or status enums
- provider, ingest, planner, retrieval, freshness, policy, citation, or budget
  behavior
- provider retry/cache/deadline reimplementation
- live NAVER/OpenDART adapters
- production use of test fixtures
- M1-09 or M2-09 code
- M3-12/M5-01 price logic or schema
- M3-02 or later answer behavior
- session persistence
- Streamlit or other UI
- streaming/WebSocket/SSE
- dense/vector retrieval
- LangGraph, agent, tools, routing
- paid model or automatic billing
- logging framework integration
- deployment

---

## 16. Implementation Sequence

## Gate 0 - Approved base and M3-00 closure

1. Confirm `HEAD == origin/main`.
2. Confirm current latest main includes `a3cb8e6...` or inspect any newer commit.
3. Confirm M3-00 independent implementation review is `PASS`.
4. Confirm working tree contains only approved planning files.
5. Run:
   - M3-00 targeted compatibility
   - M2 phase slice
   - M2 unit+integration
   - full tests
   - import smoke
   - secret scan
   - compile
   - `git diff --check`
6. Stop on code assertion failure or unrelated changes.

## Gate 1 - Clean Windows timezone dependency

After plan and package-index approval:

1. add exact `tzdata==2026.3`
2. update existing `uv.lock`
3. prove no unrelated direct pin changes
4. `uv lock --check`
5. clean `uv sync --locked --extra dev`
6. force `PYTHONTZPATH=""`
7. prove `ZoneInfo("Asia/Seoul")`
8. rerun M2 phase slice and full suite in the clean lock environment

Do not begin application code until Gate 1 passes.

## Checkpoint A

1. add LLMStatus, request/result/client contracts
2. add LLMConfig
3. add structured draft and answer models
4. add LiteLLMClient
5. add LangChain composer
6. add permission and prompt safety
7. add fixed fallback
8. run Checkpoint A exit gate

## Checkpoint B

1. add SourceGateway protocol and explicit unconfigured default
2. add ChatService
3. add API request/response and PublicProcessSummary
4. add `/api/chat`
5. add deadline/cancellation
6. add integration phase slice
7. run full M3-01 verification

## Final documentation

After tests pass:

- record actual results
- synchronize factual M3-00 status
- record selected pins and `tzdata`
- update approved mentoring decision references
- do not mark live Gemini verified when not run
- do not commit or push without separate approval

## Separate live gate

Only under separate explicit approval and local credential setup:

- one sanitized free-tier Gemini call
- verify actual model ID, structured parse, timeout, numeric usage
- print no prompt, response content, credential, raw exception, URL, or locator
- no billing and no model switch

Otherwise record:

```text
Gemini live smoke: NOT_RUN
Gemini live integration: NOT_VERIFIED
```

---

## 17. Test Plan

### 17.1 Timezone and lock

- exact `tzdata==2026.3`
- exact installed metadata
- LangChain/LiteLLM pins unchanged
- lock includes tzdata and hashes
- no unrelated lock movement
- `uv lock --check`
- clean `uv sync --locked --extra dev`
- forced empty timezone path
- Seoul ZoneInfo
- clean M2 phase slice and full suite

### 17.2 LLM contracts/config

- every LLMStatus
- success/failure invariants
- strict exact types and finite numbers
- JSON round-trip
- deep-copy isolation
- fake config without credential
- live client rejection without credential
- exact stable model
- explicit thinking `0` and `1024`
- no secret/raw invalid value exposure

### 17.3 LiteLLM adapter

- exact installed version
- no import-time network
- exact option mapping
- success and normalized usage
- authentication/rate-limit/timeout/unavailable/blocked/malformed
- exactly one SDK operation
- no retry/router/proxy/fallback
- cancellation
- no raw object or sentinel exposure

### 17.4 LangChain/composer

- exact chain step types
- async ainvoke
- callbacks empty
- hostile tracing environment and zero trace network
- one invoke equals one LLMClient call
- deterministic result
- prompt projection contains only allowed fields
- permission true/false/missing/malformed cases
- no eligible Evidence means zero calls
- malformed output fails closed
- unknown ID and unsupported claim reject whole draft
- no retry after parser/citation failure

### 17.5 SourceGateway

- required keys always present
- fake gateway explicit injection
- unconfigured gateway returns typed unavailable results
- unconfigured mode never reads tests/fixtures
- no raw provider messages in public output
- recorded/live/unconfigured labels exact
- caller inputs unmodified

### 17.6 PublicProcessSummary

- exact top-level fields
- fixed stage/source order
- counts equal actual outputs
- complete/partial/provider_failed/no_evidence/blocked
- LLM/fixed/blocked/not_called modes
- fixture is never marked live
- live_verified false without live smoke
- equal input equal JSON
- nested output isolation
- no question/snippet/Evidence ID/URL/locator/prompt/secret/path/raw exception
- no chain-of-thought field or text

### 17.7 ChatService/API

- complete path
- partial source path
- no-data vs provider failure
- blocked/no-evidence make zero LLM calls
- no external-eligible Evidence uses local fallback
- LLM failure preserves EvidenceDecision and source state
- selected/transmitted Evidence only for citation
- deadline and cancellation
- intermediate object immutability
- identical fixture input identical public JSON
- malformed request sanitized
- one non-streaming response
- unconfigured default returns stable safe response and process summary

### 17.8 Regression

Pre-M3 baselines are evidence, not predicted results:

- M2 integration: at least current unweakened tests
- M2 unit plus integration: at least current unweakened tests
- full suite: at least current unweakened tests
- M3-00 compatibility unchanged
- import smoke
- secret scan
- compile
- diff check

---

## 18. Verification Commands

Use the existing locked environment tooling. Exact commands must be recorded in
the result log.

Minimum preflight:

```powershell
git status --short
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main

$python = ".\.venv\Scripts\python.exe"

& $python -m pytest tests/unit/test_m3_langchain_stack.py -q
& $python -m pytest tests/integration/test_m2_phase_slice.py -q
& $python -m pytest tests -q
& $python scripts/secret_scan.py
& $python -m compileall app tests scripts -q
git diff --check
```

Checkpoint A:

```powershell
& $python -m pytest `
  tests/unit/test_llm_config.py `
  tests/unit/test_llm_base.py `
  tests/unit/test_litellm_client.py `
  tests/unit/test_answer_composer.py `
  -q
```

Checkpoint B:

```powershell
& $python -m pytest `
  tests/unit/test_source_gateway.py `
  tests/unit/test_public_process_summary.py `
  tests/unit/test_chat_service.py `
  tests/unit/test_api_chat.py `
  tests/integration/test_m3_chat_phase_slice.py `
  -q
```

Final:

```powershell
& $python -m pytest tests/unit/test_m3_langchain_stack.py tests/integration/test_m2_phase_slice.py tests/integration/test_m3_chat_phase_slice.py -q
& $python -m pytest tests -q
& $python -c "from app.llm.base import LLMStatus; from app.llm.litellm_client import LiteLLMClient; from app.answer.composer import AnswerComposer; from app.services.chat_service import ChatService; from app.api.main import app; print('m3-01-import-ok')"
& $python scripts/secret_scan.py
& $python -m compileall app tests scripts -q
git diff --check
git diff --name-status
git diff --stat
git status --short
```

Clean-lock commands and actual pass counts must be added to the result log after
execution.

---

## 19. Completion Criteria

### Checkpoint A

- [x] M3-00 independent PASS
- [x] clean tzdata lock PASS
- [x] LLM contracts and config PASS
- [x] LiteLLM adapter PASS
- [x] real LangChain RunnableSequence PASS
- [x] prompt permission/safety PASS
- [x] citation-bound structured draft PASS
- [x] fixed fallback PASS
- [x] M2/M3-00 regression PASS

### Checkpoint B

- [x] SourceGateway protocol PASS
- [x] ExplicitUnconfiguredSourceGateway PASS
- [x] stable ChatRequest/ChatResponse
- [x] PublicProcessSummary exact contract PASS
- [x] `/api/chat` non-streaming response PASS
- [x] deadline/cancellation PASS
- [x] complete/partial/failure/blocked paths PASS
- [x] process summary safety/determinism PASS
- [x] full regression/smoke/hygiene PASS

### Final state

- [x] existing M1/M2 contracts unchanged
- [x] no UI or price-move implementation
- [x] live Gemini either separately passed or accurately NOT_RUN
- [x] fixture/recorded/live/unconfigured states separated
- [x] first implementation review completed with CONDITIONAL PASS
- [x] first supplement closure review completed with CONDITIONAL PASS
- [x] second supplement final closure review completed with PASS WITH REQUIRED
  FOLLOW-UP
- [x] second supplement commit and main push complete
- [x] M3-01 code blockers closed
- [x] required factual synchronization complete
- [x] M3-01 status recorded as PASS / complete

M3-02 and B6 planning are allowed. B6 implementation remains governed by its
separate plan approval and Gate 0/1 requirements.

---

## 20. Stop Conditions

Stop and report if:

- M3-00 review is not PASS
- preflight code regression fails
- working tree contains unapproved code/dependency changes
- core or completed M1/M2 contract changes are needed
- new dependency beyond exact tzdata is needed
- LangChain bypasses LLMClient
- selected LiteLLM mapping cannot be proven
- clean lock cannot reproduce timezone
- raw SDK data cannot be contained
- report permission cannot be resolved
- unsafe prompt content would be sent
- application code needs tests/fixtures
- actual source gateway requires unapproved provider work
- UI is required to make backend tests pass
- M3-12/M5-01 behavior is required
- file scope grows materially
- live test requires billing or unapproved network

---

## 21. Risks and Fallback

| Risk | Control | Fallback |
|---|---|---|
| R31 fact/interpretation/inference mixing | typed extractive draft | leave unsupported sections empty |
| R32 answer without evidence | EvidenceDecision before composer | fixed no-evidence |
| R38 investment advice | preserve blocked plan | fixed blocked |
| R42 UI information overload | concise PublicProcessSummary + later expander | show answer/source only |
| R56 observability overdesign | public count/status schema only | omit optional process rows |
| R59 SDK option drift | exact-version mocked transport | stop adapter claim |
| R60 unsupported structured claim | citation validation | reject whole draft |
| R61 external transmission | permission + prompt sanitizer | local fixed template |
| no runtime source | explicit unconfigured gateway | safe provider-failed response |
| provider/LLM timeout | monotonic deadline | partial/fixed response |

---

## 22. Deferred and Not Run

- Gemini credential/quota/live behavior
- recorded application demo gateway
- live NAVER/OpenDART gateway
- Streamlit UI
- M3-02~11 answer enhancements
- M3-12 price-move behavior
- M5-01
- M4 clean Docker/deploy
- GitHub CI
- commit/push/PR/merge/deploy

---

## 23. Result Log

- Planning base SHA:
  `a3cb8e6de5309bc68ac6856648d275883ec9407f`
- M3-00 implementation SHA:
  `a3cb8e6de5309bc68ac6856648d275883ec9407f`
- M3-00 independent review: `PASS - confirmed by user`
- Final plan approval: `APPROVED by user`
- Gate 0: `PASS`
  - M3-00 targeted: `13 passed`
  - M2 phase slice: `5 passed`
  - M2 unit/integration regression: `659 passed`
  - pre-implementation full suite after scanner closure: `1433 passed`
  - import smoke, secret scan, compile, and diff check: `PASS`
  - initial secret scan found two direct fixture credential literals in
    committed M3-00 test/document examples
  - user approved the minimal fixture-only remediation
  - no scanner rule was weakened
- Gate 1 tzdata lock: `PASS`
  - exact dependency: `tzdata==2026.3`
  - lock tool: task-local `uv==0.11.32`
  - lock diff: only project tzdata reference and tzdata package/hashes
  - clean locked environment ZoneInfo smoke:
    `tzdata 2026.3 / Asia/Seoul / PASS`
  - clean M2 phase slice: `5 passed`
  - clean pre-implementation full suite: `1433 passed`
  - task-created temporary environment cleanup: `PASS`
- Checkpoint A: `PASS`
- Checkpoint A targeted: `56 passed`
- Checkpoint B: `PASS`
- Checkpoint B targeted: `23 passed`
- M3 integration: `1 passed`
- M3-00 + M2 phase + M3 phase composition: `19 passed`
- M2 regression: `659 passed during Gate 0`
- Full suite: `1512 passed`
- Clean locked M3-01 targeted: `78 passed`
- PublicProcessSummary tests: `4 passed within Checkpoint B`
- Unconfigured gateway tests: `PASS within Checkpoint B`
- Import smoke:
  `PASS - m3-01-import-ok`
- Secret scan: `PASS - []`
- Compile: `PASS`
- Git diff check: `PASS`
- Known non-failing warnings:
  `LangChain Core Pydantic V1 compatibility warning on Python 3.14;
  Starlette TestClient httpx deprecation warning`
- First implementation SHA:
  `9b92d1b9923b74a2f3ea55f51c82fc2c731e83fc`
- First implementation commit:
  `Implement m3-01`
- First implementation main push:
  `complete`
- First implementation review:
  `CONDITIONAL PASS`
- First supplement SHA:
  `5433616bbf4d61f29fae11c86c770be80d69e750`
- First supplement commit:
  `m3-01 conditional pass updates`
- First supplement main push:
  `complete`
- First supplement targeted:
  `PASS - 85 passed`
  - command included answer composer, source gateway, public process summary,
    ChatService, M3-owned security planning observation, and M3 chat phase
    slice tests
- M3-00 + M2 phase + M3 phase composition after first supplement:
  `PASS - 19 passed`
- M2/M3 focused regression after first supplement:
  `PASS - 757 passed`
- Full suite after first supplement:
  `PASS - 1564 passed, 2 warnings`
  - first sandbox run:
    `ENVIRONMENT_BLOCKED - 1461 passed, 103 setup errors`
  - repository-local basetemp retry:
    `ENVIRONMENT_BLOCKED - 1461 passed, 103 setup errors`
  - both blocked runs failed only because the managed sandbox denied pytest
    temporary-directory creation
  - same full command rerun with normal local temp permission:
    `exit code 0 - 1564 passed, 2 warnings`
- First supplement import smoke:
  `PASS - m3-01-supplement-import-ok`
- First supplement ZoneInfo smoke:
  `PASS - Asia/Seoul`
- First supplement secret scan:
  `PASS - []`
  - direct `scan_paths` check for the two new untracked supplement files:
    `PASS - []`
- First supplement compile:
  `PASS`
- First supplement diff check:
  `PASS`
- First supplement clean-lock rerun:
  `NOT_RUN - prior task-created clean environment was removed after its
  approved verification`
- First supplement closure review:
  `CONDITIONAL PASS - timeout status regression correction required`
- Second supplement:
  `complete and pushed`
- Second supplement targeted:
  - source gateway, public process summary, ChatService, M3 chat phase slice:
    `exit code 0 - 62 passed`
  - answer composer, planning observation, source gateway, public process
    summary, ChatService, M2 phase slice, M3 phase slice:
    `exit code 0 - 99 passed`
- Second supplement full suite:
  `exit code 0 - 1573 passed, 2 warnings`
- Second supplement import smoke:
  `PASS - m3-01-timeout-status-fix-ok`
- Second supplement secret scan:
  `PASS - []`
- Second supplement compile:
  `PASS`
- Second supplement diff check:
  `PASS`
- Second supplement clean-lock rerun:
  `NOT_RUN - clean-lock environment not retained`
- Gemini live smoke: `NOT_RUN`
- GitHub CI: `NOT_RUN`
- UI: `NOT_STARTED`
- M3-12/M5-01: `NOT_STARTED`
- Second supplement SHA:
  `d937d625e26495a3ee8c5a5b2c327dfbd2512ea9`
- Second supplement commit:
  `m3-01 conditional pass2 updates`
- Second supplement main push:
  `complete`
- Independent implementation review:
  `PASS WITH REQUIRED FOLLOW-UP`
- Code blockers: `CLOSED`
- Required follow-up: `factual synchronization complete`
- M3-01 status: `PASS / complete`
- Independent pytest rerun: `NOT_RUN`
- Further M3-01 code commit/push/PR/merge/deploy:
  `NOT_RUN / NOT_APPROVED`

---

## 24. Approval Request

Requested:

- approval of this corrected M3-01 plan
- approval of exact `tzdata==2026.3` package-index access and lock update
- approval of Checkpoint A then B implementation
- approval of listed local tests and clean-lock verification
- approval of factual document synchronization after tests pass

Not requested:

- live Gemini or credential use
- UI
- recorded/live source implementation
- M3-02 or later behavior
- M3-12 or M5-01
- commit, push, PR, merge, deploy
