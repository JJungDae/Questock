# TASK CARD - M3-00 LangChain and LiteLLM Integration Spike

## 1. Status and Approval

- Task bundle: `B6 pre-step`
- Step: `M3-00 LangChain and LiteLLM Integration Spike`
- Priority: `P0 enablement`
- Planning date: `2026-07-24`
- Planning branch: `main`
- Approved implementation base candidate SHA:
  `f1e45c197b6962d38cfa03c469d32540b5edf472`
- Latest reviewed commit: `fix docs`
- M2 individual capabilities: `PASS`
- M2 integrated phase-slice implementation: `PASS / complete`
- M2 integrated closure review: `PASS`
- M2 Gate: `PASS`
- M2 closure status synchronization:
  `complete at f1e45c197b6962d38cfa03c469d32540b5edf472`
- M2-09: `NOT_STARTED / not required without separate A15-M gate`
- M3 planning: `ALLOWED`
- M3-00 independent plan review:
  `CONDITIONAL PASS - corrected plan supplied`
- M3-00 total-agent re-review:
  `PASS WITH REQUIRED MINIMUM EDITS`
- M3-00 final plan approval: `APPROVED by user`
- M3-00 implementation:
  `IMPLEMENTED - local regression PASS; independent review pending`
- Package-index access: `APPROVED / used for isolated evaluation`
- Dependency installation:
  `APPROVED / isolated comparison plus selected pins in project .venv`
- Lock generation: `PASS - uv.lock generated and checked`
- Gemini live call: `OUT_OF_SCOPE / NOT_APPROVED`
- Repository M3-01 draft:
  `DRAFT / implementation and dependency installation NOT_APPROVED`
- M3-01 implementation:
  `BLOCKED pending M3-00 independent PASS and clean-Windows tzdata decision`
- Commit, push, PR, merge, deploy: `NOT_APPROVED`

This is a framework-and-dependency compatibility Task only. It does not
implement ChatService, `/api/chat`, AnswerComposer, a live LLM call, or M3
financial-answer behavior.

M2 closure synchronization is complete at
`f1e45c197b6962d38cfa03c469d32540b5edf472`.

Before any package-index access, package installation, lock generation, or
repository edit, Gate 0 must confirm:

1. `HEAD == origin/main == f1e45c197b6962d38cfa03c469d32540b5edf472`.
2. The working tree is clean except for the approved M3-00 Task Card.
3. M2 closure documents still record `PASS`.
4. The user has explicitly approved the package-index, isolated-install,
   temp-tool, lock-adoption, cleanup, and local-verification scope in Section 26.

The repository draft
`docs/TASK_CARDS/M3-01-answer-schema-chat-service.md` is planning input only.
Its framework, package, version, lock, and tracing decisions are superseded by
the final M3-00 result. M3-01 implementation remains blocked until M3-00 PASS.

---

## 2. Why M3-00 Exists

The current project plan assigns AnswerComposer, the project-owned `LLMClient`,
LiteLLM, Gemini integration, ChatService, and `/api/chat` to M3-01.

A new approved direction requires LangChain to participate in the actual M3
RAG execution path. Project workflow also requires framework introduction to
be separated from user-facing feature implementation.

M3-00 therefore resolves only the framework and dependency boundary before
M3-01.

M3-00 must prove:

- the minimum LangChain package surface required
- whether M3 should use a project-owned direct LiteLLM adapter or
  `ChatLiteLLM`
- how a real LangChain `RunnableSequence` remains behind the project-owned
  orchestration and safety boundaries
- Python compatibility in the actual local runtime
- deterministic async, parser, timeout, cancellation, usage, and error behavior
- exactly one requested model operation per invocation
- no hidden retry, model fallback, Router, Proxy, callback logging, tracing, or
  extra network request
- exact stable direct dependency versions
- one deterministic lock artifact and clean install path
- one selected architecture and a precise M3-01 handoff

M3-00 does not implement ChatService, `/api/chat`, AnswerComposer, live Gemini,
permission filtering, production source orchestration, or answer behavior.

---

## 3. Source Basis

### 3.1 Normative repository documents

Read current `main` versions of:

- `docs/agent_handoff/README_AGENT_RULES.md`
  - safety, minimum changes, verification, Git approval
- `docs/agent_handoff/PROJECT_PLAN_FINAL_PASS.md`
  - B6, M3-01, M3 Gate, Traceability Matrix
- `docs/agent_handoff/AGENT_WORKFLOW.md`
  - Human Owner framework decision, framework/function separation, dependency
    approval, Task lifecycle
- `docs/agent_handoff/LLM_STACK_DECISION.md`
  - project-owned LLM boundary, LiteLLM SDK, Gemini model, statuses, free-tier
    restrictions, permission rules
- `docs/agent_handoff/FINANCIAL_CAPABILITY_BASELINE.md`
  - answer, validation, failure, and provider boundaries
- `docs/agent_handoff/RISK_RESPONSE_MATRIX.md`
  - R01, R02, R31, R32, R38, R57, R59, R60, R61
- `docs/agent_handoff/EXTENSION_COMPATIBILITY.md`
  - P0 RAG and UI boundary
- `docs/TASK_CARDS/M2-INTEGRATION-CLOSURE.md`
- `docs/TASK_CARDS/M2-08-context-budget.md`

### 3.2 Current repository state

Inspect:

- `pyproject.toml`
- `.gitignore`
- `.env.example`
- existing lock artifacts
- `app/config.py`
- `app/core/models.py`
- `app/evidence/budget.py`
- `tests/integration/test_m2_phase_slice.py`

### 3.3 Planning input

- repository draft:
  `docs/TASK_CARDS/M3-01-answer-schema-chat-service.md`
  - use only to identify work that belongs in M3-00
  - do not treat its framework, package, version, lock, or tracing choice as
    approved
  - M3-01 implementation and dependency installation remain blocked until
    M3-00 PASS

### 3.4 External primary references

Use current official documentation and official package/repository metadata
only for:

- LangChain Core Runnables and `RunnableSequence`
- `ChatPromptTemplate`
- Pydantic/JSON output parsers
- `langchain-litellm` and `ChatLiteLLM`
- LiteLLM Python SDK and Gemini option mapping
- package Python requirements, release status, licenses, and dependency metadata
- LangSmith/LangChain tracing environment behavior and explicit tracing-disable
  mechanisms

Do not copy option names from a blog, an old release, or another model
integration.

---

## 4. Goal and Locked Runtime Boundary

Produce a verified, locked, presentation-defensible LangChain integration
boundary for M3-01.

The final M3 runtime must include a real LangChain chain:

```text
selected Questock Evidence
→ project-owned Evidence/context adapter
→ ChatPromptTemplate
→ project-owned LLMClient model boundary
→ structured Pydantic parser
→ Questock citation/numeric/safety validators
```

The prompt, model-boundary, and parser stages must compose as a real LangChain
`RunnableSequence` or equivalent pipe-created sequence whose logical stages
can be inspected and tested.

LangChain must not replace:

- QueryPlanner
- providers or repositories
- hard filtering
- freshness
- retrieval
- EvidencePolicy
- context budgeting
- citation validation
- numeric/company-attribution validation
- permission decisions
- public API status contracts

M1/M2 remain project-owned and unchanged.

---

## 5. Architecture Candidates

M3-00 evaluates exactly two candidates.

### Candidate A - LangChain Core plus project-owned direct LiteLLM adapter

```text
RunnableSequence
→ ChatPromptTemplate
→ RunnableLambda(project-owned LLMClient async call)
→ Pydantic structured parser

LLMClient
→ LiteLLMClient
→ LiteLLM Python SDK
→ Gemini
```

Permanent direct dependencies:

```text
langchain-core
litellm
```

Candidate A:

- preserves the current `LLM_STACK_DECISION.md` boundary
- gives LangChain ownership only of local composition, prompt representation,
  and parsing
- keeps provider option mapping, status normalization, usage normalization, and
  exception containment in project code
- does not use `langchain-litellm`

### Candidate B - LangChain Core plus ChatLiteLLM behind LLMClient

```text
RunnableSequence
→ ChatPromptTemplate
→ project-owned LLMClient
→ ChatLiteLLM
→ LiteLLM transport
→ Gemini
→ Pydantic structured parser
```

Initial permanent direct dependencies:

```text
langchain-core
langchain-litellm
```

`litellm` may be added as an additional permanent direct dependency only if at
least one of these is proven and documented:

- Questock production or persistent compatibility-test code imports `litellm`
  directly
- an exact direct constraint is required to make the tested ChatLiteLLM
  behavior reproducible and the reason cannot be represented safely through
  the `langchain-litellm` dependency and lock alone

Otherwise LiteLLM remains a locked transitive dependency under Candidate B.

Candidate B must keep `ChatLiteLLM`, `AIMessage`, and provider response objects
adapter-internal. `ChatLiteLLMRouter`, automatic model routing, and provider
fallback remain forbidden.

### LangSmith dependency ownership

The selected architecture must not rely on an undeclared transitive package for
a direct import.

- If persistent production code under `app/**` directly imports
  `langsmith.tracing_context` or another LangSmith symbol, `langsmith` must be
  recorded and pinned as a permanent direct runtime dependency.
- If only persistent repository tests directly import LangSmith, `langsmith`
  must be recorded and pinned as a direct development dependency rather than
  silently relying on a transitive install.
- If no direct LangSmith import is added, the compatibility result must identify
  and prove another supported exact-version mechanism that disables ambient
  tracing without an undeclared direct import.
- The deterministic lock must record the resolved LangSmith version in every
  architecture because LangChain may resolve it transitively.
- Ambient tracing must remain explicitly disabled in the future M3-01 runtime
  path, not only in the M3-00 compatibility fixture.

---

## 6. Candidate Selection and Evaluation Rule

### 6.1 Candidate A first

Candidate A is the default minimal architecture because it preserves the
already approved project-owned LiteLLM SDK boundary with fewer permanent direct
packages.

Candidate A is evaluated first against every required compatibility check.

If Candidate A passes every required check and no unresolved M3-01 capability
creates a material-benefit trigger:

```text
select Candidate A
→ mark Candidate B NOT_EVALUATED
→ record reason: no unresolved capability or material-benefit trigger
```

Candidate B is not evaluated merely to produce a comparison table.

### 6.2 Candidate B evaluation trigger

Evaluate Candidate B only when at least one of these is recorded after the
Candidate A run:

- Candidate A fails a required compatibility check
- Candidate A cannot satisfy a concrete required M3-01 capability within the
  approved project-owned LiteLLM boundary
- Candidate A leaves a measured adapter, async, structured-output, usage, or
  error-normalization risk that Candidate B could materially reduce

When Candidate B is evaluated, use a distinct isolated environment.

### 6.3 Candidate B selection gate

Candidate B may be selected only when all required compatibility checks pass
and it demonstrates a concrete benefit that Candidate A does not provide or
cannot provide within M3-01 safely.

A valid Candidate B benefit must be evidenced by at least one of:

- materially simpler and more reliable structured-output handling
- materially safer async cancellation or timeout behavior
- materially more complete usage/finish-reason normalization
- materially lower project-owned adapter/error-mapping complexity
- a required M3-01 capability that Candidate A cannot satisfy through the
  approved direct LiteLLM SDK boundary

The benefit must outweigh:

- the extra package surface
- transitive dependency and import/startup impact
- ChatLiteLLM/AIMessage containment burden
- upgrade and removal cost

If Candidate A and an evaluated Candidate B meet M3-01 requirements without a
material difference, select Candidate A.

Passing alone is not sufficient reason to prefer Candidate B.

If Candidate A fails and Candidate B is either not viable or also fails, set
M3-00 to `HOLD`. Do not invent a third architecture.

---

## 7. Release and Version Rules

Release stability is determined by the PEP 440 version identifier, not by the
PyPI project-level Development Status classifier.

Allowed for candidate comparison and permanent adoption:

- final public releases whose normalized PEP 440 version has no `.dev`, `.a`,
  `.b`, or `.rc` segment
- distributions that are not yanked

Record as dependency-risk metadata, but do not reject automatically:

- a PyPI Development Status classifier such as `4 - Beta`

Forbidden:

- development, alpha, beta-suffixed, release-candidate, nightly, preview, or
  local builds
- yanked distributions
- use of `--pre`

Additional rules:

- exact direct versions must be pinned in `pyproject.toml`
- transitive versions and distribution hashes must be fixed by the approved
  lock artifact
- record the normalized PEP 440 version, prerelease/development/local status,
  yanked status, installed distribution name, and import path
- record Python requirements and test against the actual project interpreter
- official metadata is evidence, but clean install and import in the actual
  runtime are the final compatibility proof

If only a forbidden release works, stop with `HOLD` and request a revised plan.

Do not add the full `langchain` meta-package unless an essential required API
is proven unavailable from the selected minimal packages and a revised plan is
approved.

---

## 8. Locked Non-Goals

M3-00 must not implement:

- `/api/chat`
- public request/response schemas
- ChatService
- AnswerComposer
- production `LLMClient`, `LLMResult`, `LLMStatus`, or `LLMConfig`
- live Gemini calls
- credential creation, reading, or validation
- financial-answer prompt content
- report permission filtering
- source gateway
- provider concurrency or deadline orchestration
- session memory
- M3-02 or later answer behavior
- UI
- LangGraph
- agents, tools, MCP, or A2A
- LangChain retrievers or vector stores
- embeddings, dense retrieval, reranking, or query rewriting
- LangChain Hub or remote prompt downloads
- LangSmith/Langfuse logging
- streaming
- model Router, Proxy, or fallback
- paid model or billing

No `app/**` or completed M1/M2 code may change.

---

## 9. Required Outputs

### 9.1 Dependency and lock decision

Record:

- Candidate A result
- Candidate B result as either `EVALUATED` or `NOT_EVALUATED`
- Candidate B trigger and material-benefit evidence when evaluated
- selected architecture
- rejected or not-evaluated candidate and exact reason
- exact direct runtime and development package versions
- exact locked LiteLLM and LangSmith versions, whether direct or transitive
- LangSmith direct-import ownership decision
- actual Python path and version
- package Python requirements
- PEP 440 final-release and non-yanked confirmation
- PyPI Development Status classifier as risk metadata
- package licenses
- direct and transitive distribution counts
- installed distribution names
- imports actually used
- package size/import-time observations
- lock mechanism and commands
- clean install command
- package removal path
- evaluated-candidate cleanup state

### 9.2 Persistent compatibility test

Create a selected-candidate repository test proving, without a live model call:

```text
typed input mapping
→ ChatPromptTemplate
→ real RunnableSequence
→ one fake async project model-boundary call
→ Pydantic structured parse
→ typed output
```

The test must prove logical stages:

```text
prompt
model boundary
parser
```

### 9.3 Architecture document update

After a candidate passes, update these documents to one selected architecture:

- `LLM_STACK_DECISION.md`
- `PROJECT_PLAN_FINAL_PASS.md`
- `AGENT_WORKFLOW.md`
- M3-00 Task Card

### 9.4 M3-01 handoff

Provide a copy-ready M3-01 checklist containing:

- new planning base SHA placeholder
- selected packages and exact versions
- lock artifact and clean install command
- selected architecture
- exact imports allowed
- compatibility-test file
- tracing-disable contract
- removed M3-00 concerns
- remaining M3-01 behavior and files

M3-01 must not repeat candidate or lock selection.

---

## 10. Allowed and Forbidden Files

### 10.1 New

- `docs/TASK_CARDS/M3-00-langchain-integration-spike.md`
- `tests/unit/test_m3_langchain_stack.py`
- one deterministic lock artifact
  - preferred: `uv.lock`
  - fallback: another explicitly approved project lock

### 10.2 Modified after compatibility PASS

- `pyproject.toml`
- `docs/agent_handoff/LLM_STACK_DECISION.md`
- `docs/agent_handoff/PROJECT_PLAN_FINAL_PASS.md`
- `docs/agent_handoff/AGENT_WORKFLOW.md`

### 10.3 Conditional

- `docs/agent_handoff/FINANCIAL_CAPABILITY_BASELINE.md`
  - only a C12/framework-boundary diagram when needed for consistency
- `docs/TASK_CARDS/M3-01-answer-schema-chat-service.md`
  - do not edit during candidate comparison
  - treat as repository planning input only
  - revise its framework, package, lock, tracing, and planning-base fields only
    after the M3-00 implementation receives independent review PASS

### 10.4 Forbidden

- `app/**`
- existing `tests/unit/**` except the new M3-00 test
- existing `tests/integration/**`
- `.env.example`
- providers, ingest, planning, retrieval, Evidence, citation, or budget code
- data and fixtures
- API/UI/LLM production modules
- M1/M2 Task Cards after the implementation base is locked

If another file is required, stop before expanding scope.

---

## 11. Lock Mechanism

A permanent dependency update requires one deterministic project lock.

### Preferred path

If `uv` is already installed and usable:

```text
pyproject.toml exact direct pins
→ uv lock
→ uv.lock
```

Required clean verification:

```text
uv sync --locked
```

Record the exact commands actually supported by the observed uv version.

### If uv is unavailable

Do not install a global tool silently.

M3-00 approval may authorize executing or installing uv only inside an
M3-00-created isolated temporary environment. If no approved deterministic lock
can be generated, stop after candidate comparison and report the lock decision
as unresolved.

Do not use broad developer-machine `pip freeze` output as the project lock. Do
not include editable local paths, credentials, or machine-specific file URLs.

---

## 12. Isolated Compatibility Environments

Do not mutate the project `.venv` during comparison.

Use one Task-created directory for Candidate A. Create a separate Candidate B
directory only when the Section 6.2 trigger is met. For example:

```powershell
$compatRoot = Join-Path $env:TEMP "questock-m3-00-compat"
$candidateA = Join-Path $compatRoot "candidate-a"
$candidateB = Join-Path $compatRoot "candidate-b"  # conditional
```

Rules:

- use the current project-compatible Python executable
- record `sys.executable`, Python, pip, and uv versions
- do not copy `.env`
- do not set or read a real `GEMINI_API_KEY`
- no live model call
- no repository fixture import from application code
- do not delete or alter the existing `.venv`
- do not overwrite an existing unrelated temp directory
- capture package reports before cleanup

Cleanup authorization is limited to directories created by this exact M3-00
run after results are captured. If deletion is not explicitly approved, leave
them and report their paths. Never use `git clean` for temp cleanup.

Installation failure is compatibility evidence, not permission to alter system
Python or install a global package.

---

## 13. Compatibility Matrix

Run and record every cell for Candidate A. Run Candidate B cells only when the
Section 6.2 trigger is met. Every evaluated candidate uses a distinct isolated
environment.

| Check | Candidate A | Candidate B when triggered |
|---|---|---|
| stable non-yanked exact releases | required | required |
| clean install under actual Python | required | required |
| `pip check` / resolver consistency | required | required |
| selected package imports | required | required |
| license metadata | required | required |
| direct/transitive dependency impact | required | required |
| import/startup impact | required | required |
| real RunnableSequence | required | required |
| async `ainvoke` | required | required |
| Pydantic structured parse | required | required |
| malformed output fails closed | required | required |
| one invoke equals one fake model call | required | required |
| no hidden retry | required | required |
| outer timeout and cancellation | required | required |
| cancellation causes no second call | required | required |
| exact model/options observable | direct SDK | ChatLiteLLM transport |
| usage and finish reason normalizable | required | required |
| raw object containment | required | required |
| no Router/Proxy/model fallback | required | required |
| ambient tracing disabled | required | required |
| zero callback/tracing network call | required | required |
| no real model/network call | required | required |

A candidate with an unverified required cell does not pass.

---

## 14. LangSmith and Callback Network Safety

M3-00 must not assume that the developer shell has tracing disabled.

The compatibility test must run under a hostile ambient configuration that
would normally request tracing, including applicable current and legacy
LangChain/LangSmith variables such as:

```text
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=dummy
LANGSMITH_ENDPOINT=http://127.0.0.1:9
LANGSMITH_PROJECT=questock-m3-00-test
LANGCHAIN_TRACING_V2=true
```

The selected implementation/test must explicitly disable tracing for the chain
scope using the supported mechanism of the selected exact version.

Prove:

- one chain invocation makes exactly one fake model-boundary call
- no LangSmith/callback HTTP request occurs
- no prompt, Evidence snippet, parser output, exception, or sentinel enters a
  callback/tracing record
- no global callback manager or tracing client is silently installed on the
  runnable
- the M3-01 handoff contains the same explicit tracing-disable requirement

Block socket/HTTP access or inject a failing tracing transport in tests so zero
unexpected network calls are observable.

---

## 15. Persistent Test Contract

Create:

```text
tests/unit/test_m3_langchain_stack.py
```

The permanent test covers only the selected candidate.

### 15.1 Runtime dependency availability

- selected imports work
- installed direct versions exactly match pins
- lock resolves the expected LiteLLM version
- rejected candidate package is absent as a direct dependency
- no agent, LangGraph, vector-store, retriever, Router, Proxy, or callback-
  logging import

### 15.2 Runnable composition

Build:

```text
input dict
→ ChatPromptTemplate
→ fake project-owned async model boundary
→ Pydantic parser
```

Verify:

- object is a Runnable sequence
- logical prompt/model/parser steps are inspectable
- `ainvoke()` returns the exact typed model
- input mapping is not mutated
- repeated calls return equal typed values
- fake model call count is exactly one per invocation
- no `.with_retry()` or fallback branch

### 15.3 Prompt boundary

Synthetic prompt may contain only:

- synthetic user question
- synthetic Evidence ID
- synthetic Evidence snippet
- local parser format instructions

It must not contain:

- source URL or locator
- document/provider/permission metadata
- local path
- secret sentinel
- raw exception
- full source document
- session history

### 15.4 Structured output

- valid JSON parses into a Pydantic model configured to reject extras
- malformed JSON fails
- wrong field type fails
- extra fields fail
- partial free text is not accepted
- parser failure does not trigger another model call

### 15.5 Async, timeout, and cancellation

- normal fake async call completes
- slow fake call is cancelled by an outer timeout
- cancellation produces no second call
- timeout/cancellation error is fixed and sanitized
- prompt and sentinel are absent from error text

### 15.6 Candidate A specific

- direct LiteLLM transport is mocked at the selected version's real boundary
- exact names and shapes for model, timeout, output limit, structured output,
  and thinking configuration are recorded
- supported LiteLLM exceptions can be mapped without raw messages
- direct SDK call count is exactly one

### 15.7 Candidate B specific

- ChatLiteLLM transport is mocked at the selected version's real boundary
- retry count is explicitly zero through the proven public option
- option forwarding and metadata shape are recorded
- `AIMessage` remains adapter-internal
- ChatLiteLLMRouter is absent
- ChatLiteLLM invocation produces exactly one mocked transport call

The permanent M3-00 test does not implement production `LLMClient`; it proves
the exact package APIs that M3-01 may consume.

---

## 16. Dependency Approval Record

For every permanent direct runtime or development dependency record:

- package and exact PEP 440 final version
- why required
- why existing packages/standard library are insufficient
- why it must be direct rather than transitive
- whether ownership is runtime or development-only
- license
- Python compatibility evidence
- PyPI Development Status classifier as risk metadata
- direct and transitive package impact
- import/startup impact
- deployment/image effect
- removal path
- lock-file effect

Candidate A expected direct runtime packages:

```text
langchain-core
litellm
```

Candidate B expected direct runtime packages:

```text
langchain-core
langchain-litellm
```

Candidate B adds direct `litellm` only under the explicit justification in
Section 5.

LangSmith ownership:

```text
app/** directly imports langsmith
→ permanent direct runtime dependency

tests/** directly import langsmith, app/** does not
→ direct development dependency

no repository code directly imports langsmith
→ keep transitive, but lock exact resolved version and prove another supported
  exact-version tracing-disable mechanism
```

Do not import LangSmith directly from persistent code or tests while leaving it
undeclared.

---

## 17. Document Update Contract

After candidate selection passes, minimally update:

### PROJECT_PLAN_FINAL_PASS.md

Add:

```text
Step M3-00 - LangChain/LiteLLM compatibility and dependency lock
```

M3-00 output:

- selected architecture
- exact dependency pins
- deterministic lock
- real Runnable compatibility fixture
- ambient tracing disabled and zero unexpected network
- no live Gemini
- M3-01 entry gate

Update B6 predecessor:

```text
M2 Gate
→ M3-00 PASS
→ M3-01
```

Add traceability:

```text
FRAME01 LangChain Runnable boundary
→ M3-00 compatibility fixture
→ M3-01 actual ChatService path
```

Do not change M3 functional scope.

### AGENT_WORKFLOW.md

Record:

```text
M3-00 introduces and locks the LangChain/LiteLLM framework boundary.
M3-01 consumes that approved boundary to implement ChatService and
AnswerComposer.
```

Retain the Human Owner framework decision and dependency approval rules.

### LLM_STACK_DECISION.md

Record exactly one final stack. Retain:

- `gemini/gemini-2.5-flash`
- free-tier-first policy
- no automatic billing
- no model fallback
- no Router/Proxy
- permission gate
- prompt minimization
- raw object/exception containment
- explicit tracing disabled
- sanitized live smoke remains a later separate gate

---

## 18. Implementation Sequence

### Gate -1 - Review closure and user approval

The total-agent plan re-review is complete with
`PASS WITH REQUIRED MINIMUM EDITS`. This final corrected plan incorporates those
edits.

Before implementation:

1. Confirm the M2 closure synchronization commit remains
   `f1e45c197b6962d38cfa03c469d32540b5edf472` or stop and inspect any newer main
   commit.
2. Obtain explicit user approval for:
   - this final plan scope
   - package-index access
   - Candidate A isolated installation
   - Candidate B isolated installation only when Section 6.2 triggers
   - temp-only lock-tool execution/installation if needed
   - repository dependency and lock adoption only after compatibility PASS
   - Task-created temp-directory cleanup after reports are captured
   - local verification

No package access occurs before this gate.

### Gate 0 - Git and M2 baseline

Confirm:

- branch `main`
- `HEAD == origin/main == approved implementation base`
- clean working tree except the approved M3-00 Task Card
- M2 closure documents record final PASS

Run:

- M2 phase slice
- M2 unit plus integration regression
- full tests
- public import smoke
- secret scan
- compile
- `git diff --check`

Stop on any code assertion failure.

### Gate 1 - Read-only environment audit

Record:

- Python executable and exact version
- pip version
- uv presence/version
- current `pyproject.toml`
- current lock artifact state
- current direct dependencies
- current M2 baseline counts
- package-index reachability without installing packages

### Gate 2 - Isolated candidate evaluation

1. Create the Candidate A environment.
2. Resolve allowed exact versions and install Candidate A.
3. Run the full Candidate A compatibility matrix and capture reports.
4. If Candidate A passes and no Section 6.2 trigger exists:
   - select Candidate A
   - record Candidate B as `NOT_EVALUATED`
   - do not create or install Candidate B
5. If Candidate A fails a required check or a Section 6.2 material-benefit
   trigger exists:
   - create a distinct Candidate B environment
   - resolve allowed exact versions and install Candidate B
   - run the full Candidate B compatibility matrix and capture reports
6. Do not use a live key or provider call.

### Gate 3 - Architecture decision

Apply Section 6 exactly.

Record:

- selected candidate
- rejected or `NOT_EVALUATED` candidate and reason
- exact versions
- exact APIs/options
- material benefit analysis if B is selected
- dependency/license reports
- tracing-disable mechanism
- lock path and M3-01 handoff

If neither passes, stop with `HOLD`.

### Gate 4 - Repository adoption

After compatibility PASS:

1. Add only selected exact direct pins to `pyproject.toml`.
2. Generate the approved lock artifact.
3. Create the selected-candidate persistent compatibility test.
4. Update the approved architecture documents.
5. Update M3-00 Task Card results.
6. Clean-install from the lock in a new isolated environment.
7. Rerun targeted, M2, and full regression.

### Gate 5 - Result report

Report:

- changed files
- selected/rejected architecture and evidence
- exact versions
- dependency and license impact
- lock and clean-install commands
- tracing/network results
- compatibility and regression results
- M3-01 revisions
- NOT_RUN items
- Git status

Wait for separate commit/push approval.

---

## 19. Verification Commands

Exact package install and lock commands are recorded after the environment
audit. Do not invent commands for unavailable tools.

### Existing baseline

```powershell
git status --short
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
git log -3 --oneline --decorate

$python = ".\.venv\Scripts\python.exe"

& $python --version
& $python -m pytest --version
& $python -m pytest tests/integration/test_m2_phase_slice.py -q

& $python -m pytest `
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

& $python -m pytest tests -q
& $python scripts/secret_scan.py
& $python -m compileall app tests scripts -q
git diff --check
```

### After adoption

```powershell
& $python -m pytest tests/unit/test_m3_langchain_stack.py -q
& $python -m pytest `
  tests/integration/test_m2_phase_slice.py `
  tests/unit/test_m3_langchain_stack.py `
  -q
& $python -m pytest tests -q
& $python -c "from langchain_core.prompts import ChatPromptTemplate; from langchain_core.runnables import RunnableLambda, RunnableSequence; print('langchain-core-ok')"
& $python scripts/secret_scan.py
& $python -m compileall app tests scripts -q
git diff --check
git diff --name-status
git diff --stat
git status --short
```

Candidate A additionally imports the selected LiteLLM SDK.
Candidate B additionally imports `ChatLiteLLM` from the proven selected import
path.

Clean-install from the lock and rerun:

- M3-00 targeted test
- M2 phase-slice test
- `pip check` or lock-tool equivalent
- import smoke

---

## 20. Completion Criteria

M3-00 completes only when:

- [ ] M2 closure PASS remains recorded and pushed
- [ ] `HEAD == origin/main` matches the approved implementation base at Gate 0
- [ ] total-agent required minimum edits are incorporated
- [ ] user approves package-index and installation scope
- [ ] clean preflight passes
- [ ] Candidate A is evaluated in an isolated environment
- [ ] Candidate B is evaluated only when a Section 6.2 trigger exists
- [ ] every evaluated candidate uses a distinct isolated environment
- [ ] all required compatibility cells pass for the selected candidate
- [ ] Candidate B is recorded as `NOT_EVALUATED` when no trigger exists
- [ ] Candidate B, if selected, has a material-benefit record
- [ ] one candidate is selected by the fixed rule
- [ ] direct-versus-transitive and runtime-versus-dev dependency decisions are
      justified
- [ ] LangSmith direct-import ownership is explicit
- [ ] selected versions satisfy the PEP 440 final/non-yanked contract
- [ ] PyPI Development Status classifiers are recorded as risk metadata
- [ ] one deterministic lock artifact exists
- [ ] the lock records exact LiteLLM and LangSmith versions
- [ ] clean install from lock passes
- [ ] real RunnableSequence compatibility test exists
- [ ] prompt/model/parser stages are proven
- [ ] async and cancellation pass
- [ ] one invocation equals one fake model call
- [ ] malformed structured output fails closed
- [ ] ambient tracing is explicitly disabled
- [ ] zero callback/tracing network calls are proven
- [ ] no live Gemini call occurs
- [ ] no raw provider/message/prompt leak
- [ ] no `app/**` or M1/M2 code changes
- [ ] M2 phase-slice and full regression pass
- [ ] secret scan, compile, and diff checks pass
- [ ] architecture documents agree
- [ ] M3-01 handoff is complete
- [ ] commit/push remain NOT_RUN until separately approved

M3-01 implementation is blocked until M3-00 receives implementation review
PASS and its final result is pushed on the approved base.

---

## 21. M3-01 Handoff Requirements

After M3-00 PASS, revise M3-01 before implementation review:

1. Replace planning base with the M3-00 final SHA.
2. Record M3-00 and compatibility as PASS.
3. Remove candidate, package-version, and lock selection.
4. Consume only the selected exact imports and versions.
5. Require a real RunnableSequence in the actual ChatService path.
6. Keep the project-owned LLMClient and all M1/M2 financial safety contracts.
7. Enforce explicit tracing disabled and zero callback/logging transport.
8. Keep LangGraph, agents, tools, vector stores, Router, Proxy, and model fallback
   excluded.
9. Keep live Gemini as a separately approved gate.
10. Retain permission, prompt minimization, LLMStatus, deadline, fallback,
    citation, numeric, and safety requirements.
11. Recalculate allowed files after M3-00 dependency/test/doc files exist.

---

## 22. Stop Conditions

Stop and report if:

- latest main differs from the approved base after implementation starts
- M2 closure status regresses from PASS or no longer matches the approved base
- this final total-reviewed plan lacks explicit user approval
- working tree contains unapproved code or dependency changes
- package-index access is unavailable or unapproved
- stable versions cannot install under the actual Python runtime
- only prerelease versions work
- system Python or a global tool must be modified
- deterministic lock generation cannot complete
- exact option mapping cannot be proven
- one invocation cannot be guaranteed to one model call
- hidden retry, fallback, Router, Proxy, callback logging, or tracing cannot be
  disabled
- ambient LangSmith settings can cause a network request or prompt leak
- persistent code directly imports LangSmith without the required runtime or dev declaration
- raw provider/AIMessage/prompt content cannot be contained
- a live Gemini call is required
- `app/**` or completed M1/M2 code changes appear necessary
- existing M2 tests need modification
- full `langchain`, LangGraph, agents, retrievers, or vector stores appear
  necessary
- M3-01 behavior is needed to make the spike pass
- dependency scope materially exceeds the selected candidate

Do not silently choose a third architecture.

---

## 23. Fallback and Rollback

### Candidate fallback

```text
Candidate A passes all required checks and no material-benefit trigger exists
→ select Candidate A
→ Candidate B NOT_EVALUATED

Candidate A fails or leaves a Section 6.2 material-benefit trigger
→ evaluate Candidate B in a separate environment

Candidate B fails or lacks material benefit
→ M3-00 HOLD
→ no third architecture
→ no M3-01 implementation
```

### Repository rollback

After future approved implementation, rollback is limited to:

- selected direct dependency lines
- lock artifact
- M3-00 compatibility test
- M3-00 Task Card
- exact architecture-document edits

Rollback requires separate user approval and non-destructive Git operations.

Never use:

- `git reset --hard`
- `git clean`
- force push
- history rewrite

---

## 24. Deferred and Not Run

- actual production `LLMClient`: `NOT_IMPLEMENTED`
- ChatService and `/api/chat`: `NOT_IMPLEMENTED`
- financial prompt: `NOT_IMPLEMENTED`
- permission filtering: `NOT_IMPLEMENTED`
- actual Gemini call: `NOT_RUN`
- credential/quota/billing: `NOT_RUN`
- full M3 behavior: `NOT_STARTED`
- production orchestration: `NOT_RUN`
- GitHub CI: `NOT_RUN`
- commit/push/PR/merge/deploy: `NOT_RUN`

---

## 24.1 Implementation Result Log

### Gate 0

- Implementation base, `HEAD`, and `origin/main`:
  `f1e45c197b6962d38cfa03c469d32540b5edf472`
- Branch: `main`
- Initial working tree:
  only the approved untracked M3-00 Task Card
- M2 closure records: `PASS`
- M2 phase slice: `5 passed - exit 0`
- M2 unit and integration regression: `659 passed - exit 0`
- Full baseline: `1420 passed - exit 0`
- Public import smoke: `PASS - exit 0`
- Secret scan: `PASS - [] - exit 0`
- Compile: `PASS - exit 0`
- Git diff check: `PASS - exit 0`

### Environment

- Actual interpreter:
  `C:\Users\USER\Questock\.venv\Scripts\python.exe`
- Python: `3.14.3`
- pip: `25.3`
- Existing global/project uv at audit: `NOT_AVAILABLE`
- Existing deterministic lock at audit: `NONE`
- Project environment distributions before adoption: `24`
- Temporary lock tool: `uv 0.11.32`
- Temporary directories were created only under:
  `.deps/m3-00-compat-20260724`
- Evaluated-candidate and lock-tool cleanup:
  `PASS - Task-created temporary directory removed after result capture`

### Candidate Decision

- Candidate A:
  `PASS - selected`
- Candidate B:
  `NOT_EVALUATED`
- Candidate B reason:
  Candidate A passed every required compatibility cell and left no M3-01
  capability or material-benefit trigger.
- Selected architecture:
  `langchain-core` composition with a project-owned direct LiteLLM adapter
  behind `RunnableLambda`.
- Full `langchain`, `langchain-litellm`, LangGraph, Router, Proxy, fallback,
  retriever, vector store, agent, tool, and callback logging:
  `NOT_INSTALLED / NOT_USED`

### Exact Dependency Record

| Ownership | Distribution | Version | Python | License | Release state |
|---|---|---:|---|---|---|
| direct runtime | `langchain-core` | `1.5.1` | `>=3.10,<4` | MIT | final, non-yanked, Production/Stable classifier |
| direct runtime | `litellm` | `1.83.7` | `>=3.9,<4` | MIT | final, non-yanked, no Development Status classifier |
| locked transitive | `langsmith` | `0.10.10` | `>=3.10` | MIT | final |
| locked transitive | `pydantic` | `2.12.5` | `>=3.9` | MIT | final, Production/Stable classifier |

- Imports used:
  `ChatPromptTemplate`, `RunnableLambda`, `RunnableSequence`,
  `PydanticOutputParser`, `litellm.acompletion`, LiteLLM exception classes,
  and LiteLLM `AsyncHTTPHandler` only in the mocked compatibility boundary.
- LangSmith ownership:
  transitive only; no persistent direct import.
- Candidate environment distributions: `69`
- Locked development environment distributions: `74`
- Candidate site-packages observed size: `184460309 bytes`
- Observed package directory sizes:
  `langchain_core 5242758 bytes`,
  `litellm 76303238 bytes`,
  `langsmith 6074799 bytes`.
- Warm-cache import observation with local cost map enabled:
  `langchain_core 67.881 ms`, `litellm 1451.334 ms`.
- `litellm 1.93.0` was evaluated for installation first but had no usable
  Windows Python 3.14 binary on this runtime and attempted a Rust source build;
  it was rejected without changing system Python or installing Cargo.
- `litellm 1.83.7` is the latest observed final universal wheel that installed
  on this Windows Python 3.14 runtime.
- PyPI security metadata for `litellm 1.83.7` lists issues in LiteLLM Proxy
  paths. Proxy is prohibited and not used by Questock, but the pin must be
  re-evaluated before any future Proxy use or dependency upgrade.
- `langchain-core 1.5.1` emits a Python 3.14 warning from its Pydantic v1
  compatibility import. The persistent fixture uses Pydantic v2 and passed;
  retain the warning as upgrade risk metadata.
- LiteLLM attempted remote model-cost-map access when imported without a local
  map setting. M3-01 must set `LITELLM_LOCAL_MODEL_COST_MAP=True` before the
  first LiteLLM import.

### Compatibility Evidence

- Real sequence stages:
  `ChatPromptTemplate`, `RunnableLambda`, `PydanticOutputParser`
- Async `ainvoke`, deterministic typed result, and input immutability: `PASS`
- One invocation to one fake model-boundary call: `PASS`
- Malformed JSON, wrong type, extra field, and free text fail closed: `PASS`
- Parser failure creates no retry: `PASS`
- Outer timeout cancellation:
  one call, one cancellation, fixed sanitized error: `PASS`
- Hostile LangSmith/LangChain tracing environment with explicit false values
  and `callbacks=[]`: `PASS`
- Unexpected tracing/callback network attempts: `0`
- Mocked LiteLLM SDK calls per requested model operation: `1`
- Model: `gemini/gemini-2.5-flash`
- Timeout option: `timeout=1.5`
- Output limit:
  `max_tokens=256` -> Gemini `generationConfig.max_output_tokens=256`
- Structured output:
  JSON schema -> `response_mime_type=application/json` and
  `response_json_schema`
- Thinking:
  `{"type":"enabled","budget_tokens":1024}` ->
  `thinkingConfig={"thinkingBudget":1024,"includeThoughts":true}`
- Retry: `num_retries=0`
- Usage normalization:
  prompt `11`, completion `7`, total `18`
- Finish reason normalization: `STOP` -> `stop`
- HTTP 401, 429, 503, and transport timeout:
  fixed status mapping, one SDK call, raw sentinel absent: `PASS`
- Live Gemini/network/credential use: `NOT_RUN`

### Lock and Verification

- Lock artifact: `uv.lock`
- Lock revision: `3`
- Lock resolved packages: `75`, including the local project
- Locked versions:
  `langchain-core 1.5.1`, `litellm 1.83.7`, `langsmith 0.10.10`
- Lock command:
  `.deps/m3-00-compat-20260724/lock-tool/Scripts/uv.exe lock`
- Lock check:
  `uv lock --check - PASS - exit 0`
- Clean install command:
  `uv sync --locked --extra dev --python .venv/Scripts/python.exe
  --no-python-downloads` with a Task-local `UV_PROJECT_ENVIRONMENT`
- Clean locked installation:
  `PASS - 74 distributions installed`
- Clean locked M3-00 targeted:
  `13 passed - exit 0`
- Clean locked M2 phase slice:
  `BLOCKED - existing deferred Windows tzdata declaration is absent from
  pyproject.toml and uv.lock`
- Clean locked M2 error:
  sanitized `ZoneInfoNotFoundError` for `Asia/Seoul`
- Scope decision:
  M3-00 did not add `tzdata`; M2-06 and M2-07 already defer that dependency
  decision to clean-build work.
- Project `.venv` retained its previously installed `tzdata 2026.3`; only the
  selected M3-00 pins were installed for local regression.
- Project `.venv` resolver check: `PASS - exit 0`
- Project `.venv` ZoneInfo smoke: `PASS - Asia/Seoul - exit 0`
- M3-00 targeted: `13 passed - exit 0`
- M2 phase slice plus M3-00: `18 passed - exit 0`
- Full unit/integration regression: `1433 passed - exit 0`
- Import smoke:
  `langchain-core-ok`, `litellm-ok` - exit `0`
- Secret scan: `PASS - [] - exit 0`
- Compile: `PASS - exit 0`
- Git diff check: `PASS - exit 0`
- GitHub CI: `NOT_RUN`
- Independent pytest rerun: `NOT_RUN`

### M3-01 Copy-Ready Handoff

- Planning base SHA:
  `<M3-00 final independently reviewed and pushed SHA>`
- M3-00 gate:
  must be independent `PASS` before implementation.
- Selected direct packages:
  `langchain-core==1.5.1`, `litellm==1.83.7`
- Lock:
  repository `uv.lock`; use `uv sync --locked --extra dev`.
- Clean Windows dependency gate:
  resolve the existing deferred `tzdata` declaration before claiming a clean
  M3-01 environment.
- Architecture:
  Evidence/context adapter -> `ChatPromptTemplate` ->
  `RunnableLambda(project-owned LLMClient async call)` -> Pydantic parser ->
  project-owned validators.
- Allowed LangChain imports:
  `langchain_core.prompts.ChatPromptTemplate`,
  `langchain_core.runnables.RunnableLambda`,
  `langchain_core.runnables.RunnableSequence`,
  `langchain_core.output_parsers.PydanticOutputParser`.
- LiteLLM:
  direct SDK inside the project-owned adapter only; raw responses and
  exceptions remain adapter-internal.
- Compatibility test:
  `tests/unit/test_m3_langchain_stack.py`
- Import safety:
  set `LITELLM_LOCAL_MODEL_COST_MAP=True` before importing LiteLLM.
- Tracing safety:
  set `LANGSMITH_TRACING=false`, `LANGCHAIN_TRACING_V2=false`, and use
  `callbacks=[]`; do not import LangSmith directly.
- Fixed exclusions:
  full `langchain`, `langchain-litellm`, LangGraph, agents, tools, retrievers,
  vector stores, Router, Proxy, model fallback, remote prompts, callback
  logging, and live Gemini unless separately approved.
- Removed from M3-01:
  framework candidate comparison, package version choice, and lock choice.
- Remaining M3-01 work:
  production LLM contracts/config, direct LiteLLM adapter, AnswerComposer,
  ChatService, structured output behavior, permission/prompt minimization,
  timeout/deadline and fixed fallback behavior, citation/numeric/safety
  validators, tests, and separately approved sanitized live smoke.

### Current Assessment

- Changed files:
  `pyproject.toml`, `uv.lock`,
  `tests/unit/test_m3_langchain_stack.py`,
  `docs/TASK_CARDS/M3-00-langchain-integration-spike.md`,
  `docs/agent_handoff/LLM_STACK_DECISION.md`,
  `docs/agent_handoff/PROJECT_PLAN_FINAL_PASS.md`,
  `docs/agent_handoff/AGENT_WORKFLOW.md`
- Forbidden-file changes: `NONE`
- Final branch/base:
  `main` at `f1e45c197b6962d38cfa03c469d32540b5edf472`,
  matching `origin/main`
- Final working tree:
  four approved tracked files modified and three approved files untracked
- Candidate A compatibility: `PASS`
- Repository implementation: `COMPLETE for approved M3-00 files`
- Local regression: `PASS`
- Clean-lock Windows M2 regression: `BLOCKED by pre-existing deferred tzdata`
- Independent implementation review: `NOT_RUN`
- M3-00 final status: `IMPLEMENTED / independent review pending`
- M3-01 implementation: `BLOCKED`
- Commit/push/PR/merge/deploy: `NOT_RUN`

---

## 25. Implementation Review Checklist

### Governance and source

- [x] M2 closure PASS is current on GitHub
- [x] implementation base and latest main match
- [x] total-agent required minimum edits incorporated
- [x] package-index/install/lock scope explicitly approved
- [x] only allowed files changed
- [x] no `app/**` or M1/M2 changes

### Dependency and architecture

- [x] Candidate A isolated report
- [x] Candidate B report only when triggered, otherwise `NOT_EVALUATED` reason
- [x] default-A/conditional-B selection rule followed
- [x] selected versions satisfy PEP 440 final/non-yanked rules
- [x] PyPI Development Status classifier recorded separately
- [x] Candidate B direct LiteLLM pin justified if present
- [x] LangSmith runtime/dev/transitive ownership recorded
- [x] exact direct pins and deterministic lock
- [x] lock records exact LiteLLM and LangSmith versions
- [x] clean install and resolver check
- [x] licenses and dependency/import impact recorded

### Runnable and safety

- [x] real prompt/model/parser sequence
- [x] async invoke
- [x] one invoke equals one fake model call
- [x] no retry/fallback/router/proxy
- [x] timeout and cancellation
- [x] typed parser and malformed-output failure
- [x] prompt minimization
- [x] raw provider/message/prompt containment
- [x] hostile ambient tracing test
- [x] zero tracing/callback network calls

### Regression and process

- [x] targeted M3-00 test
- [x] M2 phase slice unchanged and PASS in the project environment
- [x] full suite PASS in the project environment
- [x] secret scan and compile PASS
- [x] diff/status review
- [x] fixture versus live status separated
- [x] architecture documents agree
- [x] M3-01 handoff complete
- [x] Git operations accurately recorded

---

## 26. Approval Request

Requested after this final corrected plan is delivered:

- approve this final M3-00 scope
- approve read-only preflight and environment audit
- approve package-index access in one Candidate A isolated temporary environment
- approve Candidate B isolated installation only when Section 6.2 triggers
- approve Task-created temp-directory cleanup only after results are captured
- approve temp-only uv execution/installation when required
- approve repository adoption only after compatibility PASS
- approve `pyproject.toml`, one lock artifact, one persistent compatibility test,
  and the listed architecture-document changes
- approve local verification

Not requested:

- live Gemini
- credentials
- ChatService
- `/api/chat`
- AnswerComposer
- API/UI
- provider or M1/M2 changes
- LangGraph/agent/tool/vector DB work
- commit
- push
- PR
- merge
- deploy
