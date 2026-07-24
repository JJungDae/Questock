# TASK CARD - M3-01 Answer Schema, LangChain Boundary, and ChatService

## 1. Status and Approval

- Task bundle: `B6: M3-01~05, M3-07, M3-15, and deployment scaffold`
- Step: `M3-01 Answer Schema and ChatService`
- Priority: `P0`
- Planning date: `2026-07-24`
- Planning branch: `main`
- Planning base SHA:
  `866dbb2a349e54b59f8dec1f9b770bc4ee68729b`
- Planning base commit: `add m2 test`
- Planning base main push: `complete`
- M2 individual capabilities: `PASS`
- M2 integrated phase slice: `PASS`
- M2 Gate: `PASS`
- M2-09:
  `NOT_STARTED / not required without separate A15-M gate`
- M1-09:
  `mandatory supplement implemented - final independent review pending`
- M3-01 planning: `DRAFT - user review required`
- M3-01 implementation: `NOT_APPROVED`
- Dependency installation or lock generation: `NOT_APPROVED`
- Gemini live call: `NOT_APPROVED`
- Commit, push, PR, merge, deploy: `NOT_APPROVED`

Before this card was created, the working tree contained only the user-approved
M2 closure status updates in:

- `docs/TASK_CARDS/M2-INTEGRATION-CLOSURE.md`
- `docs/TASK_CARDS/M2-08-context-budget.md`

No M3 application code or dependency has been changed. Approval of this Task
Card may authorize only the exact M3-01 implementation and verification scope
listed below. Git operations, live API calls, paid usage, and later M3 steps
remain separate approvals.

## 2. Goal

Implement the first non-streaming answer vertical slice:

```text
POST /api/chat
-> ChatService
-> existing M1/M2 pipeline
-> permission-limited prompt construction
-> LangChain prompt and structured-output boundary
-> project-owned LLMClient
-> LiteLLM Python SDK adapter
-> Gemini API
-> Pydantic parse
-> existing citation validation
-> stable public response
```

The implementation must preserve all completed M1 and M2 contracts. It must
also keep model/provider SDK objects, raw exceptions, prompts, credentials,
local paths, and unapproved source content outside the public API.

M3-01 establishes a safe extractive answer baseline. Beginner explanation,
multi-turn memory, full answer acceptance rules, numeric validation, advice
validation, source-detail UI, and context UI remain their assigned later M3
steps.

## 3. Verified Current State

| Area | Verified file | Current state |
|---|---|---|
| API app | `app/api/main.py` | only the health router is registered |
| public health route | `app/api/routes_health.py` | async route with sanitized fallback |
| provider config | `app/config.py` | `ProviderConfig` only; credentials are private |
| LLM code | `app/llm/` | does not exist |
| answer service | `app/services/` | does not exist |
| current answer model | `app/core/models.py` | `FinancialAnswer` has the M2 fixed-answer surface |
| planner | `app/planning/query_planner.py` | deterministic `QueryPlanner` |
| M2 pipeline | `app/evidence/**`, `app/retrieval/**` | normalization through context budget is implemented |
| citation boundary | `app/evidence/citations.py` | validates caller claims only against selected Evidence |
| call budget | `app/evidence/budget.py` | request-scoped maximum of two LLM calls |
| report permission | `app/ingest/reports.py` | document metadata carries `external_llm_processing_allowed` |
| current dependencies | `pyproject.toml` | Pydantic, FastAPI, Uvicorn; no LLM or LangChain package |
| lock artifact | repository root | no package lock file currently exists |
| environment template | `.env.example` | generic LLM placeholders exist but M3 variables are incomplete |
| production source repository | `app/repositories/` | does not exist |
| live Gemini status | project decision document | credential, quota, and live call are unverified |

The M2 integration test proves the internal phase slice with synthetic inputs.
It does not prove production source loading, actual 365-day source coverage, a
live provider, or a live LLM.

## 4. Locked Architecture

### 4.1 Runtime order

```text
validate ChatRequest
-> resolve and plan
-> fetch required sources through an injected source gateway
-> normalize documents
-> hard filter
-> freshness
-> retrieval
-> EvidencePolicy
-> final context budget
-> EvidenceDecision gate
-> external-processing and prompt-safety gate
-> compose one structured LLM request
-> parse and validate the structured draft
-> validate citations against the final selected Evidence
-> serialize ChatResponse
```

The exact completed M2 order is not changed. Permission is not a retrieval,
IDF, scoring, freshness, or policy signal. It is checked only after final
Evidence selection and before external transmission.

### 4.2 LLM boundary

The project-owned boundary remains:

```text
AnswerComposer
-> LLMClient
-> LiteLLMClient
-> LiteLLM Python SDK
-> Gemini API
```

`AnswerComposer` and `ChatService` must not import or consume LiteLLM or Gemini
response classes. Only `LiteLLMClient` may import the LiteLLM SDK.

### 4.3 LangChain application

M3-01 will use `langchain-core` only for:

- a local, version-controlled `ChatPromptTemplate`
- deterministic formatting instructions for the Pydantic draft schema
- parsing the normalized `LLMResult.content` into the Pydantic draft

The project-owned `LLMClient` remains the only model-call interface. LangChain
must not call Gemini directly or replace the current retrieval and evidence
pipeline.

The following are excluded:

- `create_agent`
- LangGraph
- LangChain retrievers or vector stores
- LangChain memory or session persistence
- LangChain tools
- LangChain Hub or runtime prompt downloads
- provider routing or automatic model fallback
- hidden parser retries or hidden additional LLM calls

If the selected `langchain-core` version cannot operate behind the project
`LLMClient` without bypassing this boundary, implementation stops. Replacing
the boundary, adding full `langchain`, or dropping LangChain requires a revised
plan and user approval.

## 5. Public and Internal Contracts

### 5.1 Public request

`POST /api/chat` accepts:

```json
{
  "message": "삼성전자 최근 위험 요인 알려줘",
  "session_id": "anonymous-uuid"
}
```

Contract:

- `message` is a required, trimmed, non-blank string with a fixed upper bound.
- `session_id` is a required, trimmed, non-blank opaque identifier with a fixed
  upper bound.
- M3-01 does not persist or replay session history.
- Unknown fields are rejected.
- Invalid input returns a sanitized validation response without echoing the raw
  message, credential-like text, or internal exception.

### 5.2 Public response

The non-streaming response is one stable JSON object:

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

`answer_sections` contains:

```text
summary
facts
interpretation
inference
positive_factors
risk_factors
uncertainty
```

M3-01 keeps interpretation and inference empty unless their text passes the
same extractive citation boundary as facts. Later M3 steps may expand these
sections only with their own approved validators.

The existing `FinancialAnswer`, `EvidenceDecisionStatus`, `ProviderStatus`,
`RetrievalStatus`, `ProviderResult`, `Evidence`, and `QueryPlan` contracts are
not modified.

### 5.3 Structured draft

The LLM returns a project-owned Pydantic draft containing only:

- a bounded sequence of claims
- for each claim:
  - stable claim ID
  - allowed section label
  - claim text
  - one or more Evidence IDs

Each claim text must be an extractive substring supported by every referenced
Evidence snippet because that is the existing M2-07 contract. Unknown Evidence
IDs, malformed schema, unsupported claims, and any citation rejection fail the
LLM answer as a whole. M3-01 then uses a deterministic local fallback; it does
not return partially accepted free text.

No model-supplied URL, title, locator, security, source, date, status, warning,
or diagnostic field is accepted.

### 5.4 LLM interface

Add a separate project-owned `LLMStatus` with exactly:

```text
ok
timeout
rate_limited
authentication_error
provider_unavailable
invalid_response
content_blocked
```

The project-owned `LLMResult` carries only:

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

- `ok` requires non-blank content and a sanitized usage mapping.
- failure statuses have no usable content.
- `invalid_response` covers schema or parse failure.
- `content_blocked` remains distinct from parse failure.
- no provider exception text or raw SDK object is stored in any field.
- `LLMStatus` never changes provider status, `missing_sources`, or
  `EvidenceDecision`.
- inputs and outputs are deep-copied at public boundaries.

The interface is async internally so it can respect cancellation and remaining
deadline. "Sync response" means a single completed HTTP JSON response, not SSE,
WebSocket, or token streaming.

### 5.5 Config

Add a separate `LLMConfig` without changing `ProviderConfig`.

Environment names:

```text
GEMINI_API_KEY
LLM_MODEL
LLM_THINKING_BUDGET
LLM_MAX_OUTPUT_TOKENS
LLM_TIMEOUT_SECONDS
```

Rules:

- default model is exactly `gemini/gemini-2.5-flash`
- preview, `latest`, paid fallback, and runtime user model selection are rejected
- thinking budget is explicit; no dynamic provider default
- fixture evaluation compares `0` and `1024`
- the smallest value that passes the approved compatibility and quality fixture
  is pinned
- timeout is finite and positive
- max output tokens is a bounded positive integer
- fake and unit environments load without a credential
- constructing the live adapter requires a configured credential
- secret value is absent from `repr`, `str`, serialization, safe summary,
  exceptions, logs, and test output
- invalid environment values produce fixed sanitized messages without the raw
  value

`.env.example` contains names with empty values only. Existing generic
`LLM_API_KEY` must not become a second credential source.

### 5.6 LiteLLM mapping

`LiteLLMClient` will:

- use the Python SDK, not Proxy or Router
- make at most the call reserved by `LLMCallBudget`
- pass the configured stable model, timeout, max output tokens, explicit
  thinking setting, and structured-output request
- normalize supported SDK responses into `LLMResult`
- normalize timeout, rate limit, authentication, provider availability,
  blocked content, and malformed responses to `LLMStatus`
- use project-owned fixed messages only
- never perform an automatic model switch, paid fallback, or billing action

The exact LiteLLM option names and response shape must be proven by focused
compatibility tests for the selected version. They must not be guessed from a
different SDK or older release.

## 6. Source and Permission Boundary

### 6.1 Source gateway

`ChatService` receives an injected project-owned source gateway that returns:

- requested documents
- provider results keyed by the existing required source names
- the document index needed by M2 filters and permission checks

The gateway must preserve all requested source keys. It may delegate external
calls to the existing M1-03 policy helper and local corpus reads to existing
ingest outputs. M3-01 does not reimplement provider retry, cache, or attempt
timeout.

No application module may import `tests/fixtures` or treat synthetic fixtures
as production corpus. Unit and integration tests inject a fake gateway.
Production source loading and live source coverage remain separately recorded
if no approved runtime corpus or live adapter is available.

### 6.2 External processing eligibility

The prompt may contain only:

- the current user question
- opaque selected Evidence IDs
- the selected Evidence snippets needed for the answer

It must not contain:

- session history
- full documents or report files
- source URLs or locator payloads
- provider raw responses or exceptions
- manifest notes
- credentials or credential-like values
- local absolute paths

For `research_report` Evidence, the linked `FinancialDocument.metadata` value
`external_llm_processing_allowed` must be the literal boolean `true`.
Missing, false, malformed, or unavailable linked metadata excludes that report
Evidence from the external prompt. It remains available only to a deterministic
local fixed-template path.

This eligibility check occurs after M2 context selection and does not alter
retrieval score, freshness, EvidenceDecision, or the public Evidence record.
LLM-generated claims may cite only Evidence actually sent to the LLM. Local
fixed-template claims may cite any final selected Evidence without transmitting
it externally. If no selected Evidence is externally eligible, no LLM call
occurs.

### 6.3 Prompt safety

Before the call, a project-owned sanitizer checks the exact rendered messages.
A credential-like key/value, local absolute path, internal exception text, raw
URL/locator, or unsupported payload type fails closed. It is not silently sent
or written to logs.

## 7. Decision and Fallback Rules

| Evidence decision | LLM call | Result |
|---|---:|---|
| `blocked` | no | fixed blocked response |
| `no_evidence` | no | fixed no-evidence response |
| `provider_failed` | no | fixed provider-failed response |
| `complete` or `partial`, empty budget | no | public `no_evidence` fixed response; original decision retained internally |
| `complete` or `partial`, no externally eligible Evidence | no | local extractive fixed response |
| `complete` or `partial`, eligible Evidence | at most one initial call | structured composition path |
| any LLM failure | no additional call in the baseline | local extractive fixed response |
| invalid schema or citation rejection | no additional call in the baseline | local extractive fixed response |

M3-01 reserves one call per request. The existing maximum of two remains
unchanged, leaving a later explicitly approved correction call possible. No
hidden retry is allowed in LangChain or LiteLLM.

For a nonempty final budget, public `status` continues to reflect
`EvidenceDecision`, not LLM availability. An empty final budget always
abstains with public `no_evidence`; the original decision object is retained
unchanged for safe internal diagnostics. An LLM failure adds only a stable
user-safe degradation warning; it does not fabricate provider failure or
missing sources. Internal diagnostics retain the separate `LLMStatus` without
exposing exception text.

The fixed path is deterministic and extractive. It may use the selected
Evidence snippets locally, but it may not invent facts, numbers, URLs, causes,
or investment advice.

## 8. Deadline Contract

- One monotonic request deadline bounds the complete chat operation.
- Default total chat deadline remains 20 seconds.
- independent providers execute concurrently through the source gateway
- each provider policy receives no more than the remaining request time
- the LLM timeout is capped by the remaining request time
- retry is not started when the remaining time cannot accommodate it
- pending cancellable work is cancelled at deadline
- one source failure does not discard completed source results
- completed Evidence can produce `partial` or a fixed response
- no operation waits indefinitely after timeout

Tests use injected clocks and cancellable tasks. They do not sleep for the real
8- or 20-second limits.

## 9. Allowed Files

Expected new files:

- `app/api/schemas.py`
- `app/api/routes_chat.py`
- `app/answer/__init__.py`
- `app/answer/models.py`
- `app/answer/composer.py`
- `app/llm/__init__.py`
- `app/llm/base.py`
- `app/llm/litellm_client.py`
- `app/services/__init__.py`
- `app/services/chat_service.py`
- `tests/unit/test_llm_config.py`
- `tests/unit/test_llm_base.py`
- `tests/unit/test_litellm_client.py`
- `tests/unit/test_answer_composer.py`
- `tests/unit/test_chat_service.py`
- `tests/unit/test_api_chat.py`
- `tests/integration/test_m3_chat_phase_slice.py`
- focused structured-output fixtures under `tests/fixtures/llm/`
- this Task Card

Expected modified files:

- `app/api/main.py`
- `app/config.py`
- `.env.example`
- `pyproject.toml`
- one separately approved deterministic dependency lock artifact

An `app/services/source_gateway.py` file may be added only if keeping the source
protocol in `chat_service.py` would create a circular import or mix orchestration
with source contracts. No provider or repository implementation is added under
that allowance.

## 10. Forbidden Changes

- M1/M2 core models or status enums
- provider, ingest, planner, retrieval, freshness, policy, citation, or budget
  behavior
- provider retry/cache/deadline reimplementation
- live NAVER or OpenDART adapters
- M1-09, M2-09, price-move logic
- M3-02 or later answer features
- session memory or persistence
- API streaming, WebSocket, SSE
- UI
- dense/vector retrieval or reranking
- LangGraph, agents, tools, or model routing
- paid model selection or automatic billing
- logging framework integration
- deployment

## 11. Implementation Sequence

### Gate 0 - approved-base preflight

1. Confirm `HEAD` and `origin/main` are the expected planning base.
2. Confirm the only pre-existing changes are the approved M2 status-sync docs
   and this approved Task Card.
3. Run the M2 integration, M2 regression, full test suite, import smoke, secret
   scan, compile, and `git diff --check`.
4. Stop before M3 code if any code assertion fails or unrelated changes appear.

### Gate 1 - dependency compatibility

1. Obtain explicit approval for dependency installation and lock generation.
2. Check Python 3.14 compatibility for candidate `litellm` and
   `langchain-core` versions.
3. Verify imports, license metadata, transitive dependency diff, startup/import
   impact, and structured-output APIs in an isolated environment.
4. Select exact versions and produce the approved lock artifact.
5. Stop if the SDK option mapping, wheel support, or lock process is
   incompatible. Do not silently add another model SDK or package manager.

### Stage 2 - contracts and config

1. Add `LLMStatus`, `LLMResult`, request protocol, and central invariant
   factory.
2. Add `LLMConfig` with private credential handling.
3. Add API and structured-draft schemas.
4. Add exhaustive serialization, invariants, secret non-disclosure, and invalid
   config tests.

### Stage 3 - composer and adapter

1. Add the local LangChain prompt template and Pydantic parser.
2. Add prompt eligibility and sanitizer checks.
3. Add `LiteLLMClient` with a mocked SDK transport boundary.
4. Verify all SDK statuses and raw-object non-leakage.
5. Compare thinking budgets `0` and `1024` with the same structured fixtures and
   pin the smallest passing value.

### Stage 4 - ChatService and API

1. Add the injected source gateway and request deadline.
2. Compose the existing M1/M2 functions in their locked order.
3. Add EvidenceDecision and fixed-response gates.
4. Call the composer only for externally eligible selected Evidence.
5. Validate claims with the existing M2-07 function.
6. Add the non-streaming route and sanitized error mapping.

### Stage 5 - verification and report

1. Run targeted M3-01 tests.
2. Run the M2 integration and regression unchanged.
3. Run the full unit/integration suite.
4. Run import smoke, secret scan, compile, and diff checks.
5. Record fixture and live outcomes separately.
6. Report changed files and actual results; do not commit or push.

### Separate live gate

Only after explicit approval and local `.env` credential setup:

- make one sanitized Gemini free-tier smoke call
- confirm actual model ID, structured parse, timeout, and normalized usage
- record only configured state, status, model ID, latency, and numeric usage
- never print request content, response content, credential, or raw exception
- do not enable billing or switch to a paid model

Without this approval or credential, record:

```text
Gemini live smoke: NOT_RUN - approval or credential unavailable
Gemini live integration: NOT_VERIFIED
```

## 12. Test Plan

### Contract and config

- all `LLMStatus` values and state invariants
- JSON round-trip for new Pydantic models
- caller input and returned nested payload mutation isolation
- fake/unit config without credential
- live adapter rejection without credential
- invalid, blank, negative, NaN, Infinity, and out-of-range config
- secret absent from repr, str, JSON, safe summary, exception, and captured output

### LiteLLM adapter

- stable model and explicit option mapping
- successful structured content and normalized usage
- timeout
- rate limit
- authentication error
- provider unavailable
- content blocked
- malformed response
- raw exception and sentinel secret non-disclosure
- no fallback model, Router, Proxy, retry, or extra call
- cancellation at timeout

### LangChain and composer

- direct structured parser compatibility
- exact rendered prompt contains only question, Evidence IDs, and snippets
- no session history, full document, URL, locator, metadata, or provider payload
- report permission true inclusion
- report permission false, missing, malformed, and missing-document exclusion
- mixed eligible and ineligible Evidence
- no eligible Evidence skips LLM
- local-path and credential sentinel fail closed
- valid extractive claims
- invalid JSON and wrong schema become `invalid_response`
- unknown Evidence ID and unsupported claim cause whole-draft fallback
- deterministic fixture output
- thinking budget `0` and `1024` comparison with separate latency and pass record

### ChatService and API

- supported resolved question complete path
- partial path preserves completed source results
- no-data and provider-failure distinction
- blocked and no-evidence paths make zero LLM calls
- LLM failure uses Evidence-backed fixed output
- `missing_sources` is not changed by LLM status
- source gateway key completeness
- hard filter and wrong-company regression
- M2 context-selected Evidence only
- citation validation only against transmitted Evidence
- total deadline, provider concurrency, pending cancellation, and no late wait
- request sequence and intermediate object immutability
- identical fixture input produces identical public JSON
- malformed request receives sanitized response
- LiteLLM, Gemini, LangChain, prompt, and exception objects absent from public JSON
- route returns one non-streaming JSON response

### Regression and smoke

- M2 targeted integration remains `5 passed` or higher without weakening tests
- M2 unit plus integration remains `659 passed` or higher
- full suite remains `1420 passed` or higher
- imports include new `LLMConfig`, `LiteLLMClient`, `AnswerComposer`,
  `ChatService`, and API app
- secret scan reports no findings
- compile exits zero
- `git diff --check` exits zero

Passed counts are evidence only after the commands are actually run. Existing
counts are pre-M3 baselines, not predicted M3 results.

## 13. Verification Commands

Preflight reuses the exact M2 closure commands:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/integration/test_m2_phase_slice.py -q

.\.venv\Scripts\python.exe -m pytest `
  tests/unit/test_query_planner.py `
  tests/unit/test_retrieval_filters.py `
  tests/unit/test_retrieval_baseline.py `
  tests/unit/test_evidence_normalization.py `
  tests/unit/test_evidence_freshness.py `
  tests/unit/test_evidence_policy.py `
  tests/unit/test_citation_validation.py `
  tests/unit/test_context_budget.py `
  tests/integration/test_m2_phase_slice.py `
  -q

.\.venv\Scripts\python.exe -m pytest tests -q

.\.venv\Scripts\python.exe -c "from app.core.models import FinancialAnswer; from app.planning.query_planner import QueryPlanner; from app.retrieval import filter_evidence, retrieve_evidence; from app.evidence.normalizer import normalize_financial_documents; from app.evidence.freshness import evaluate_freshness; from app.evidence.policy import EvidencePolicy; from app.evidence.budget import select_evidence_context; from app.evidence.citations import validate_citations; print('m2-phase-slice-import-ok')"

.\.venv\Scripts\python.exe scripts/secret_scan.py
.\.venv\Scripts\python.exe -m compileall app tests scripts -q
git diff --check
git diff --name-status
git status --short
```

Final targeted commands will name only the approved M3-01 test files plus the
same M2 and full-suite regression commands. Exact dependency inspection and
lock commands must be added after the lock mechanism is approved.

## 14. Stop Conditions

Stop and report evidence before further edits if:

- preflight code regression fails
- the working tree contains unapproved code, fixture, or dependency changes
- a core model/status or completed M1/M2 contract change appears necessary
- LangChain requires direct provider access or bypasses `LLMClient`
- LiteLLM structured output or thinking configuration cannot be proven for the
  selected version
- Python 3.14 compatibility or deterministic lock generation fails
- an SDK response cannot be sanitized without retaining raw provider data
- report permission cannot be resolved from the linked document
- a secret, local path, full source document, or unapproved report would enter
  the prompt
- total deadline requires changing provider retry/cache behavior
- representative fixture flow requires importing `tests/fixtures` from app code
- live verification requires billing, paid fallback, or unapproved network use
- M3-02 or later behavior is required to make M3-01 pass
- expected file or test scope grows materially

## 15. Risks and Fallback

| Risk | M3-01 control | Fallback |
|---|---|---|
| `R31` fact, interpretation, inference mixing | typed section labels and extractive claims | empty unsupported sections |
| `R32` answer forced without evidence | EvidenceDecision gate before composer | fixed no-evidence response |
| `R38` investment advice | preserve QueryPlanner blocked route; no new advice generation | fixed blocked response |
| `R59` LiteLLM/Gemini option drift | exact-version compatibility fixture and live gate | stop before adapter claim |
| `R60` schema-valid unsupported facts | existing citation validator against transmitted Evidence | reject whole draft |
| `R61` unapproved or sensitive external transmission | linked-document permission and prompt sanitizer | local fixed template |
| provider or LLM timeout | monotonic deadline and cancellation | partial or fixed response |
| dependency expansion | `langchain-core` only and adapter isolation | remove adapter without changing core service contracts |

## 16. Completion Criteria

M3-01 can be marked implementation-complete only when:

- [ ] approved preflight passes
- [ ] dependency and lock change is separately reviewed
- [ ] `/api/chat` returns the stable non-streaming schema
- [ ] existing M1/M2 contracts remain unchanged
- [ ] project-owned `LLMClient`, `LLMResult`, and separate `LLMStatus` pass tests
- [ ] LiteLLM/Gemini raw objects never cross the adapter
- [ ] LangChain remains limited to local prompt and structured parsing
- [ ] structured-output parse and citation failures fail closed
- [ ] report external-processing permission is enforced before prompt creation
- [ ] only question and selected snippets are sent
- [ ] blocked, no-evidence, provider-failed, and LLM-failure fixed paths pass
- [ ] provider partial and deadline behavior passes deterministically
- [ ] thinking budget `0` and `1024` fixture results are recorded and a value is pinned
- [ ] targeted, M2 regression, full suite, smoke, secret scan, compile, and diff checks pass
- [ ] live Gemini smoke is either approved and passed, or M3-01 remains
      `CONDITIONAL / LIVE NOT_VERIFIED`
- [ ] fixture and live evidence are reported separately
- [ ] no automatic billing or paid fallback exists
- [ ] user reviews the implementation result

M3-02 implementation is not allowed until M3-01 receives its required review.

## 17. Decisions Required Before Implementation

- approve or revise this M3-01 scope
- approve adding `litellm` and `langchain-core`
- choose and approve a deterministic lock mechanism; `uv.lock` is recommended
  only if `uv` is already available or its installation is separately approved
- decide whether dependency installation may access the package index
- separately approve any Gemini live smoke after local credential setup
- separately approve commit and push after implementation review

## 18. Result Log

- Plan created: `2026-07-24`
- M3 code changes: `NOT_RUN`
- Dependency changes: `NOT_RUN`
- Preflight: `NOT_RUN`
- Targeted tests: `NOT_RUN`
- M2 regression: `NOT_RUN`
- Full suite: `NOT_RUN`
- Import smoke: `NOT_RUN`
- Secret scan: `NOT_RUN`
- Compile: `NOT_RUN`
- Gemini live smoke: `NOT_RUN`
- GitHub CI: `NOT_RUN`
- Commit/push: `NOT_RUN`
