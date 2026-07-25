# TASK CARD - B9 Release, Deployment, Demo, and Traceability

## 1. Status and Approval

- Project: `Questock`
- Repository: `JJungDae/Questock`
- Branch: `main`
- Bundle: `B9`
- Included checkpoints:
  - `B9-0` preflight and B8 closure verification
  - `B9-A` M4-04 CI and M4-05 clean local Docker/container
  - `B9-B` M4-05 remote deployment, M4-06 demo, M4-07 release
    documentation, M4-08 P0 traceability, and M4 Gate
- Priority: `P0`
- Planning date: `2026-07-26`
- Planning base SHA:
  `b9ddf7461306d16cf1da14634ce458050d78f7bc`
- Planning base commit:
  `Fix B8 observability token validation`
- Planning base main push:
  `complete`
- B8 implementation:
  `PASS WITH REQUIRED FOLLOW-UP / complete`
- B8 focused closure fix:
  `PASS`
- B8 code blockers:
  `CLOSED`
- B8 final quality:
  `34/34 = 100%`
- B8 final Critical:
  `17/17 = 100%`
- B8 final public exposure:
  `0`
- M1-09:
  `mandatory supplement implemented - final independent review pending`
- M3-12:
  `NOT_ACTIVATED`
- B9 planning:
  `ALLOWED`
- B9 plan review:
  `SELF-REVIEW CONDITIONAL PASS`
- B9 plan supplement:
  `IMPLEMENTED - external plan approval pending`
- B9 implementation:
  `NOT_APPROVED - allowed only after plan approval and B9-0 PASS`
- B9-A local Docker verification:
  `BLOCKED - Docker executable not found in the planning environment`
- B9-B remote deployment:
  `BLOCKED - deployment target and deploy approval are not provided`
- GitHub CI:
  `NOT_RUN - workflow does not exist at planning time`
- Dependency and lock change:
  `PROPOSED - exact Ruff addition requires plan approval`
- Commit, push, PR, merge, deploy:
  `NOT_APPROVED`

This is the canonical B9 plan. Planning does not authorize implementation,
dependency installation, a commit, a push, a PR, a merge, or deployment.

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
11. `docs/agent_handoff/MENTORING_SCOPE_DECISION_2026-07-24.md`
12. `docs/TASK_CARDS/B8-quality-observability.md`
13. this Task Card
14. current code, fixtures, tests, and release assets

The latest addendum controls the execution order:

```text
B8 PASS
-> B9-A: M4-04 CI + M4-05 clean local container
-> B9-B: remote deployment + demo + docs + P0 traceability
-> B9 independent implementation review
-> M4 Gate
-> A15-M activation check
-> optional Stretch M2-09
-> M5-01
-> later P1 eligibility check
```

M4 Gate must not be marked complete while local clean-container verification or
the separately approved remote deployment smoke remains blocked.

---

## 3. Verified Planning Baseline

The planning inspection found:

- `HEAD` and `origin/main` both point to
  `b9ddf7461306d16cf1da14634ce458050d78f7bc`.
- The only observed working-tree items are pre-existing untracked B7 review
  bundle artifacts. They are user-owned and must remain untouched.
- No `.github/` workflow, `Dockerfile`, Compose file, or `.dockerignore`
  currently exists.
- The repository has `pyproject.toml` and `uv.lock`.
- The declared Python floor is `>=3.11`.
- The approved local tools include:
  - Python at `.deps/b6-streamlit-clean/Scripts/python.exe`
  - uv at `.deps/b6-lock-tool/Scripts/uv.exe`
- Docker was not found in the planning environment.
- `README.md` describes an older M1-08 slice and is not an accurate P0 release
  runbook.
- The current FastAPI entry point is `app.api.main:app`.
- The current Streamlit entry point is `streamlit_app.py`.
- Streamlit calls the API through `QUESTOCK_API_URL`, with a local default of
  `http://127.0.0.1:8000/api/chat`.
- `app/api/routes_chat.py` currently constructs `ChatService()` with the
  explicit unconfigured source gateway.
- `app/services/source_gateway.py` already owns the approved
  `recorded`, `live`, and `unconfigured` data-mode boundary.
- No application-owned `data/demo/**` corpus or recorded runtime gateway
  exists.
- Existing provider and ingest fixtures are test evidence. They are not an
  approved application demo corpus and must not be imported into production
  runtime code.
- No canonical remote deployment target is recorded in the repository.
- There is no persistent database in the current P0 runtime. Session state is
  in memory, and approved source/glossary data is file-backed.
- No project lint dependency or lint configuration currently exists.
- B8 closed with:
  - full golden `34/34 = 100%`
  - Critical `17/17 = 100%`
  - public exposure `0`

These are planning observations. Docker, GitHub Actions, remote deployment, and
live-source behavior were not executed or verified during planning.

### 3.1 Frozen baseline objects

Record these Git object IDs at B9-0. Unexpected changes require review before
implementation:

| Object | Planning blob SHA |
|---|---|
| `app/api/schemas.py` | `c10da0270e00105a4f375ba79a2aac5451730a4a` |
| `app/core/models.py` | `54397337c3b3e152de247e585494ef4a6c92ef1a` |
| `app/core/status.py` | `28c1f25545d8d71e1645f15c94d4f5729ac8574e` |
| `app/services/source_gateway.py` | `e4be1b31687a1c579072bc28458eacc088ad2590` |
| `app/answer/models.py` | `660563e4859c6301f709c1e2574828eb143781e0` |
| `pyproject.toml` | `bb68add158277379f6ddfe3c96f737f9cd264f1b` |
| `uv.lock` | `7a74ba524631b8b89ab5d9e592957adfa6094783` |
| `tests/fixtures/evaluation/m3_golden_cases.json` | `32f30aadabc5a990c20a1ddca645b083e8648c10` |
| `scripts/m3_gate.py` | `a488fdcd4deaa9a76618737f15f323f97f4655ab` |

The `pyproject.toml` and `uv.lock` hashes may change only for the approved Ruff
addition. The other listed objects are regression-only and must remain
unchanged unless a stop condition is reported and separately approved.

---

## 4. Goal

Complete the P0 release-readiness bundle without changing the approved
financial reasoning contracts:

```text
reproducible CI
-> clean local two-service container
-> explicit recorded demo runtime
-> separately approved remote deployment smoke
-> operator/demo documentation
-> P0 requirement traceability
-> B9 review + M4 Gate
```

The completed bundle must:

- run deterministic unit, integration, gate, secret, and syntax checks in CI
- build one immutable application image and run API and UI as separate services
- verify API and UI health in a clean container environment
- keep credentials out of images, workflows, logs, docs, and public responses
- provide an explicit recorded demo mode without claiming live connectivity
- retain the unconfigured mode when recorded mode is not selected
- expose no local path, raw exception, prompt, secret, or raw source payload
- preserve B8 full golden, Critical, and public-exposure results
- document one repeatable local run method and one rollback method
- run a separately approved smoke check against the selected remote target
- map active P0 requirements to implementation, tests, fallback, API, and UI
  evidence

---

## 5. Non-Goals

Do not implement:

- a live OpenDART, NAVER, research-report, price, or Gemini call
- a live provider adapter or live source gateway
- real credential values or credential logging
- a public request, response, process-summary, or error schema change
- a core model, status enum, ProviderResult, Evidence, or answer model change
- M1 or M2 implementation or contract changes
- QueryPlanner, retrieval, ranking, Evidence policy, citation, dedupe, or
  context-budget changes
- LLM prompt, validator, model, retry, or provider changes
- a database, migration, persistent chat store, queue, worker, or new volume
- a UI redesign or a new product feature
- CI-triggered production deployment
- a cloud-provider SDK
- an invented source URL, DART receipt, research page, section, permission, or
  actual coverage claim
- reuse of `tests/**` fixtures from runtime code
- M3-12, M5-01, Stretch M2-09, or P1 work
- edits to golden fixtures or the M3 Gate runner
- score improvement through fixture deletion, threshold changes, or assertion
  weakening

The only planned dependency change is the exact Ruff development dependency
defined below. Any other dependency or lock change is a stop condition.

The exact Ruff pin and its direct/transitive lock diff are part of B9 plan
approval. An unapproved version or wider lock change is not covered by this
plan.

---

## 6. Fixed B9 Contracts

### 6.1 CI contract

Create `.github/workflows/ci.yml` with:

- triggers:
  - `push` to `main`
  - `pull_request`
  - `workflow_dispatch`
- top-level `permissions: contents: read`
- no `pull_request_target`
- no production environment
- no live credential or secret context
- concurrency cancellation for superseded branch or PR runs
- bounded job timeout
- Python `3.11`, matching the declared minimum supported runtime
- uv `0.11.32`, matching the approved local lock tool
- locked installation:

```text
uv sync --locked --all-extras --dev
```

- checks, in this order:
  1. Ruff static lint
  2. full pytest
  3. direct M3 Gate
  4. project secret scan
  5. Python compile
  6. container image build after the Dockerfile exists

Third-party actions must be official project actions and pinned by full commit
SHA. Candidate pins identified during planning are:

- `actions/checkout`:
  `de0fac2e4500dabe0009e67214ff5f5447ce83dd`
- `astral-sh/setup-uv`:
  `08807647e7069bb48b6ef5acd8ec9567f424441b`

B9-0 must verify each candidate against its official release before adding the
workflow. A mismatch or unavailable official record is a stop condition; do not
replace a full SHA with a mutable tag.

GitHub CI remains `NOT_RUN` until the workflow is committed, pushed, and the
exact run is observed. Local execution must not be described as CI success.

### 6.2 Ruff contract

Add exactly:

```text
ruff==0.15.22
```

as a development dependency and update `uv.lock` with the approved uv tool.
Do not add a formatter, mypy, pyright, pre-commit, or another lint dependency.

The initial rule set is deliberately bounded:

```text
ruff check --select E4,E7,E9,F app tests scripts streamlit_app.py
```

Run the exact command before any unrelated cleanup. Do not run `--fix`.
If the baseline requires broad unrelated edits, do not weaken the rules or
mass-edit the repository. Stop and report the findings.

`compileall` is a syntax/importability check. It must not be reported as lint or
static type checking.

### 6.3 Container contract

Use one image and two Compose services:

- `api`
  - command: Uvicorn serving `app.api.main:app`
  - listen: `0.0.0.0:8000`
  - health: `/health`
- `ui`
  - command: Streamlit serving `streamlit_app.py`
  - listen: `0.0.0.0:8501`
  - internal API URL: `http://api:8000/api/chat`
  - health: `/_stcore/health`

Requirements:

- multi-stage build
- Python `3.11` slim runtime
- uv and base images pinned by version and verified digest
- locked, non-development dependency installation
- non-root runtime user
- one immutable image reused by both services
- `.env`, `.git`, `.deps`, caches, local review bundles, and temporary files
  excluded from build context
- no credential in an image layer, build argument, Compose file, health output,
  or public response
- no startup dependency on a live provider, LLM, or external network
- deterministic startup with source mode defaulting to `unconfigured`
- no database or persistent-data volume added

The legacy `PROJECT_PLAN_FINAL_PASS.md` M4-05 checklist mentions
`SQLite·data volume`. The newer post-M3-01 addendum classifies
DB/migration/persistence as a scope-change trigger. B9 therefore records this
legacy item as:

```text
N/A - superseded by the post-M3-01 addendum;
P0 uses immutable repository data and in-memory anonymous sessions.
```

Do not silently mark the legacy checkbox complete. If an independent review
requires SQLite or persistence despite the addendum, stop for a plan amendment.

Image digests must be obtained from official registries during implementation.
Do not invent a digest in the Task Card.

### 6.4 Runtime source-mode contract

Use:

```text
QUESTOCK_SOURCE_MODE=unconfigured|recorded
```

Rules:

- missing value defaults to `unconfigured`
- invalid values fail startup with a project-owned sanitized error
- no arbitrary local manifest path is accepted from the environment
- recorded assets load only from the fixed repository path `data/demo/**`
- `unconfigured` keeps `ExplicitUnconfiguredSourceGateway`
- `recorded` creates an application-owned recorded gateway
- recorded results use:
  - `data_mode="recorded"`
  - `live_connectivity_checked=False`
- recorded mode must pass through the existing SourceGateway,
  ProviderResult, FinancialDocument, retrieval, Evidence, policy, citation, and
  answer boundaries
- runtime code must not import from `tests/**`
- the current API and public response schemas remain unchanged

The runtime factory may supply the existing glossary service in recorded mode.
It must not silently enable a live source or LLM.

### 6.5 Demo corpus contract

Create a small, application-owned corpus under `data/demo/**`.

The corpus must:

- use structured JSON validated through existing project models
- have a schema/version marker
- use deterministic IDs and timestamps
- identify itself as `synthetic_demo`
- record one timezone-aware UTC `basis_at`
- derive the displayed Asia/Seoul basis date from that timestamp
- use only the three supported securities
- include no copyrighted report body supplied without permission
- include no invented public URL, DART receipt, page, section, or coverage claim
- include no local absolute path or credential-shaped value
- remain deterministic and immutable at runtime
- be deep-copied before returning through the gateway

Synthetic news and research-report examples may omit `source_url` and use the
existing stable locator contract. A disclosure fallback test must return
`no_data` without inventing a receipt or viewer URL.

The required M4-06 normal scenario, `최근 공시 핵심`, is different from that
fallback test. It requires a user-supplied and independently verified recorded
disclosure item with its real receipt number and official viewer URL. Until
that input is available:

```text
Recorded disclosure fallback test: ALLOWED
M4-06 normal disclosure demo: BLOCKED
B9 completion: BLOCKED
M4 Gate: BLOCKED
```

Do not substitute a synthetic receipt, a test fixture, or a fabricated URL.
Alternatively, changing the M4-06 normal scenario requires a separate Project
Plan amendment and user approval.

Documentation and UI-visible demo wording must say:

- recorded
- synthetic project-owned demo data
- not live connectivity
- not actual source coverage
- fixed basis date

Failure behavior must be exercised through deterministic test doubles or
unconfigured mode. Do not add hidden query text that switches fake scenarios.

In recorded mode, the runtime factory must inject the manifest `basis_at` as
`ChatService.utc_now`. The injected value must be timezone-aware UTC and must
remain identical across repeated demo runs. Query planning, freshness,
EvidencePolicy, diagnostics, and displayed basis date must therefore share one
clock. Unconfigured mode continues to use the actual current UTC time. File
timestamps, process start time, and the local timezone must not determine the
recorded demo clock.

### 6.6 Remote deployment contract

Remote deployment is a separately approved important action.

Before deployment:

- the user selects the target platform
- target-specific config is documented without secret values
- B9-A is complete
- an immutable release candidate SHA and image digest are recorded
- API and UI service topology is supported by the selected target
- rollback to a previous image digest or release is defined

Deployment must be manual. CI must not auto-deploy on push.

Remote smoke must verify:

- API health
- UI health
- the primary release deployment runs explicitly in `recorded` mode
- one recorded API request completes within a bounded timeout
- one recorded Streamlit flow completes against the deployed API
- a separate unconfigured/failure-path check is labeled truthfully
- no live connectivity is claimed unless separately executed and verified
- no secret, local path, raw exception, prompt, or raw source payload appears
  in responses or sampled logs
- provider failure or unconfigured mode remains distinguishable from no data
- rollback target is available

If no target or deployment approval is provided, record `BLOCKED`; do not mark
M4 Gate or B9 complete.

After target selection, `docs/MVP_RELEASE.md` must contain exactly one canonical
deployment command for that target. It must identify the immutable release
candidate and must not include secret values. Provider-specific alternatives
and CI-triggered deployment are out of scope.

### 6.7 Traceability contract

Create `docs/P0_TRACEABILITY.md` from actual source documents and code.

Each active P0 row must contain:

- requirement or risk ID
- owning bundle/checkpoint
- implementation file or explicit non-code control
- targeted test or gate case
- fallback or failure behavior
- API behavior
- UI behavior
- current verification status
- limitation or deferred note

The matrix must not convert:

- local tests into GitHub CI
- recorded mode into live connectivity
- synthetic demo data into actual coverage
- a Task Card PASS into deployment evidence
- an unrun remote smoke into release completion

M1-09 remains `mandatory supplement implemented - final independent review
pending`. M3-12 remains `NOT_ACTIVATED`.

### 6.8 Release evidence and Git order

The evidence-producing order is fixed:

```text
local implementation
-> targeted/full/gate/secret/compile/container verification
-> implementation result and diff report
-> implementation commit approval
-> implementation commit
-> push approval
-> main push
-> GitHub CI observation on the exact pushed SHA
-> deployment target and deploy approval
-> immutable-SHA/image remote deployment
-> remote smoke and rollback evidence
-> Task Card/release/traceability factual synchronization
-> closure docs commit approval
-> closure docs commit
-> closure docs push approval
-> closure docs main push
-> B9 independent implementation review + M4 Gate review
-> user result confirmation
-> today work-log entry
```

Local success must not be reported as GitHub CI success. A deployment from an
uncommitted or unrecorded source state is prohibited. CI, deploy, rollback, and
closure-doc evidence must name the exact SHA or immutable image digest.

### 6.9 Post-B9 activation boundary

B9 and M4 Gate completion do not authorize M5 or P1 implementation.

```text
M4 Gate PASS
-> M5-01 activation-check planning only
-> if the market-session temporal filter is absent, plan Stretch M2-09 first
-> separately approve M5-01 or an explicit Human Owner skip
-> preserve one final regression/docs/presentation buffer
-> require at least three whole sessions before any P1 start
```

M1-09 remains pending until its recorded independent-review status changes.

---

## 7. B9-0 Preflight Gate

Use the approved local tools:

```powershell
$python = ".deps/b6-streamlit-clean/Scripts/python.exe"
$uv = ".deps/b6-lock-tool/Scripts/uv.exe"
```

### 7.1 Git and scope

Run:

```powershell
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
git log -5 --oneline
git diff --check
git diff --name-status
```

Confirm:

- branch is `main`
- `HEAD` equals `origin/main`
- B8 closure SHA is
  `b9ddf7461306d16cf1da14634ce458050d78f7bc`
- the approved B9 Task Card is present
- no newer commit changes a B9 contract
- existing user-owned untracked artifacts remain untouched
- there is no unexpected dirty code, fixture, dependency, or lock change

Recheck the frozen objects with:

```powershell
git hash-object app/api/schemas.py
git hash-object app/core/models.py
git hash-object app/core/status.py
git hash-object app/services/source_gateway.py
git hash-object app/answer/models.py
git hash-object pyproject.toml
git hash-object uv.lock
git hash-object tests/fixtures/evaluation/m3_golden_cases.json
git hash-object scripts/m3_gate.py
```

### 7.2 Tool inventory

Run:

```powershell
& $python --version
& $uv --version
docker --version
docker compose version
gh --version
```

Missing Docker blocks B9-A container implementation and verification. Do not
install Docker without explicit user approval.

### 7.3 Regression

Run before any B9 implementation:

```powershell
& $python -m pytest tests -q
& $python scripts/m3_gate.py
& $python scripts/secret_scan.py
& $python -m compileall app tests scripts streamlit_app.py -q
```

All must exit `0`. The M3 Gate must remain:

- fixture total `34`, unchanged
- fixture content unchanged
- runner threshold unchanged
- full `34/34`
- Critical `17/17`
- public exposure `0`

Any failure blocks implementation. Do not update expected values to pass.

### 7.4 Preflight result

Record:

- command
- exit code
- passed count or gate score
- tool version
- blocked command and exact environment limitation
- Git status and deviations

Do not write `PASS` for an unrun command.

The normal secret scanner reads tracked files. Before the first B9 commit,
`tests/unit/test_release_assets.py` must call the project-owned
`scan_paths()` function with an explicit list containing every new or modified
B9 text asset. The test must separately reject public local absolute paths and
non-empty credential assignments in:

- `README.md`
- `.env.example`
- `.github/workflows/ci.yml`
- `compose.yaml`
- `Dockerfile`
- `.dockerignore`
- `data/demo/**/*.json`
- `docs/MVP_RELEASE.md`
- `docs/DEMO_SCENARIOS.md`
- `docs/P0_TRACEABILITY.md`
- the B9 Task Card

Required container-internal paths in `Dockerfile` are not public paths, but
credential literals remain forbidden. After the implementation files are
committed, rerun the normal tracked-file secret scan on the exact commit.

---

## 8. B9-A - CI and Clean Local Container

### 8.1 A1 - M4-04 CI

Implementation order:

1. Verify the official action release-to-SHA mappings.
2. Add exact Ruff dependency and update only the approved lock entries.
3. Run the bounded Ruff audit before application edits.
4. Add the least-privilege CI workflow.
5. Add release-asset tests that parse the workflow and reject:
   - mutable action tags
   - `pull_request_target`
   - write permissions
   - live credential use
   - missing locked install
   - missing required checks
6. Run the explicit pre-commit release-asset secret/path scan.
7. Run targeted and full regression locally.
8. Record GitHub CI as `NOT_RUN` until a later approved push and observed run.

Targeted checks:

```powershell
& $python -m pytest tests/unit/test_release_assets.py -q
& $python -m ruff check --select E4,E7,E9,F app tests scripts streamlit_app.py
```

Checkpoint A1 cannot independently claim CI success. It proves only local
workflow structure and local command results until the workflow runs on GitHub.

### 8.2 A2 - M4-05 clean local Docker/container

Implementation order:

1. Add `.dockerignore`.
2. Add the digest-pinned multi-stage `Dockerfile`.
3. Add `compose.yaml` with API and UI services.
4. Add static tests for release assets and secret exclusions.
5. Build without cache in the clean Docker environment.
6. Start both services and wait for health.
7. Run bounded API and UI smoke.
8. inspect rendered Compose config and image history for forbidden values.
9. Stop only the B9-created services and network after verification.

Planned commands, subject to Docker availability:

```powershell
docker compose config
docker build --pull --no-cache -t questock:b9-local .
docker compose up --detach --wait
& $python scripts/release_smoke.py --api-url http://127.0.0.1:8000 --ui-url http://127.0.0.1:8501
docker compose ps
docker image inspect questock:b9-local
docker history --no-trunc questock:b9-local
docker compose down --remove-orphans
```

Before cleanup, confirm the Compose project name and service names are the
B9-created resources. Do not remove unrelated containers, images, networks, or
volumes. B9 does not create a persistent application volume.

Checkpoint A acceptance:

- local CI-equivalent commands pass
- release asset tests pass
- image builds from locked dependencies
- API and UI become healthy
- smoke completes
- image and rendered config expose no credential or local path
- B8 regression remains green
- checkpoint HANDOFF records actual Docker and GitHub CI status

If Docker remains unavailable, Checkpoint A is `BLOCKED`, not `PASS`.

---

## 9. B9-B - Demo, Remote Deployment, Docs, and Traceability

### 9.1 B1 - Recorded demo runtime

Implementation order:

1. Add the versioned `data/demo/**` corpus.
2. Add a pure loader and `RecordedDemoSourceGateway`.
3. Add a runtime factory for `unconfigured` and `recorded`.
4. Wire the API dependency to the runtime factory without changing public
   schemas.
5. Add deterministic unit tests for loader, gateway, mode selection, mutation
   isolation, and sanitized failure.
6. Add integration tests for representative API and Streamlit flows.

Required scenarios:

- recent-company issue summary from recorded news
- research-report summary or risk explanation from recorded report metadata
- financial-term explanation through the approved glossary
- multi-turn follow-up through the existing session behavior
- disclosure `no_data` fallback without an invented receipt
- normal recent-disclosure summary only after a verified recorded disclosure
  input is approved
- unconfigured-provider failure and fixed-template behavior
- blocked advice behavior
- wrong-company and unsupported-security protection
- process visibility for wrong-company, stale, low relevance, provider failure,
  budget, and fallback

Every recorded scenario must use the manifest `basis_at`, not the wall clock.
The scenario set is demo evidence, not actual source coverage. The normal
recent-disclosure scenario is mandatory for M4-06 completion.

### 9.2 B2 - M4-05 remote deployment

After separate target and deploy approvals:

1. freeze the release candidate SHA and image digest
2. record one canonical target-specific deploy command
3. create API and UI services on the approved target
4. configure the primary release in explicit `recorded` mode
5. inject any later-approved secrets only
   through the platform secret manager
6. run remote health and representative smoke
7. inspect sanitized logs
8. record target, region, release identifier, mode, command, exit/status, and
   timestamp without credential values
9. exercise or document the verified rollback command

No target is selected in this plan. Target-specific files or SDKs are not
approved.

### 9.3 B3 - M4-06 demo

Create a repeatable operator script in `docs/DEMO_SCENARIOS.md`:

- prerequisites
- source mode
- data basis date
- startup steps
- representative prompts
- expected status and evidence behavior
- failure/fallback scenario
- UI process visibility checks
- known limitations
- cleanup
- a three-minute input-to-output code-flow explanation

The demo must not depend on a live provider or LLM. If a live check is later
approved, record it separately from the recorded demo.

### 9.4 B4 - M4-07 release documentation

Update or create:

- `README.md`
  - current architecture and status
  - architecture flow from API input through source, retrieval, Evidence,
    policy, citation, answer, and UI
  - one locked local run method
  - container run method
  - configuration names without values
  - recorded versus unconfigured mode
  - API and UI endpoints
  - test and gate commands
  - limitations and non-advice notice
- `docs/MVP_RELEASE.md`
  - release candidate SHA/image
  - environment matrix
  - data manifest and data-usage note
  - health and smoke evidence
  - deployment and rollback runbook
  - CI and M4 Gate evidence
  - evaluation report with measured denominators and environment
  - known risks and accepted limitations
  - deferred live and coverage work
- `docs/DEMO_SCENARIOS.md`
  - operator and presentation-ready demo flow
  - three-minute code-flow explanation with key function locations

No canonical presentation deck is currently verified in the repository.
M4-07 produces presentation-ready notes; editing an external deck requires a
separately supplied artifact and approval.

### 9.5 B5 - M4-08 P0 traceability and M4 Gate

Create and validate `docs/P0_TRACEABILITY.md`.

Then run:

```powershell
& $python -m pytest tests/unit/test_release_assets.py tests/integration/test_b9_release_phase_slice.py -q
& $python -m pytest tests -q
& $python scripts/m3_gate.py
& $python scripts/secret_scan.py
& $python -m compileall app tests scripts streamlit_app.py -q
```

Repeat the clean-container and approved remote smoke commands. Record all
results in this Task Card and `docs/MVP_RELEASE.md`.

Checkpoint B acceptance:

- recorded demo mode is explicit and deterministic
- no runtime import from test fixtures
- disclosure no-data does not fabricate a locator
- a verified normal recent-disclosure scenario passes
- API/UI representative flow passes
- remote deployment and rollback evidence exist
- docs match the exact release candidate
- every active P0 requirement has traceability evidence or an explicit blocker
- full golden `34/34`
- Critical `17/17`
- public exposure `0`
- no secret, prompt, raw exception, local path, or raw payload exposure
- GitHub CI passes on the exact release candidate SHA
- the Human Owner confirms the three-minute code-flow explanation
- M4 Gate result is independently reviewed

---

## 10. Expected Files

### 10.1 Expected additions

- `.github/workflows/ci.yml`
- `.dockerignore`
- `Dockerfile`
- `compose.yaml`
- `app/runtime.py`
- `app/services/demo_source_gateway.py`
- `data/demo/manifest.json`
- `data/demo/documents.json`
- `scripts/release_smoke.py`
- `tests/unit/test_demo_source_gateway.py`
- `tests/unit/test_runtime.py`
- `tests/unit/test_release_assets.py`
- `tests/integration/test_b9_release_phase_slice.py`
- `docs/MVP_RELEASE.md`
- `docs/DEMO_SCENARIOS.md`
- `docs/P0_TRACEABILITY.md`

### 10.2 Expected modifications

- `pyproject.toml`
- `uv.lock`
- `.env.example`
- `app/api/routes_chat.py`
- `README.md`
- `docs/TASK_CARDS/B9-release-deployment-traceability.md`
- `docs/agent_handoff/SOURCE_OF_TRUTH_INDEX.md`

### 10.3 Regression-only files

- `app/api/schemas.py`
- `app/core/models.py`
- `app/core/status.py`
- `app/services/source_gateway.py`
- `app/answer/models.py`
- all provider and ingest implementations
- all QueryPlanner, retrieval, Evidence, policy, citation, and context modules
- `tests/fixtures/evaluation/m3_golden_cases.json`
- `scripts/m3_gate.py`

If implementation requires changing a regression-only file, stop and report
the contract conflict before editing.

### 10.4 Conditional closure record

After the user confirms the final B9/M4 Gate result, update only the approved
Step in:

- `docs/work_logs/WORK_LOG_YYYY-MM-DD.md`

Do not create the final work-log entry before user result confirmation.

---

## 11. Test Matrix

### CI and release assets

- workflow uses full action SHAs
- workflow has read-only permissions
- workflow excludes `pull_request_target`
- workflow uses locked uv sync
- workflow runs Ruff, full tests, gate, secret scan, compile, and image build
- `.dockerignore` excludes secret and local-only files
- Docker runtime user is non-root
- Compose has separate API/UI services and health checks
- no credential value is baked into release files
- explicit pre-commit scanning covers every new or modified B9 text asset
- tracked-file secret scan is rerun after the implementation commit

### Recorded runtime

- missing source mode selects unconfigured
- explicit recorded mode selects recorded gateway
- invalid mode is a sanitized startup error
- missing, malformed, wrong-version, duplicate, or wrong-type demo data fails
  with a project-owned sanitized error
- no raw exception, payload, or path is exposed
- source results have requested keys in requested order
- recorded status/data invariants pass through the existing factory
- data mode is recorded and live connectivity is false
- recorded `ChatService.utc_now` equals the manifest timezone-aware UTC
  `basis_at`
- diagnostics and displayed basis date derive from that same clock
- returned documents are deep copies
- repeated runs are deterministic
- runtime has no `tests` import
- no invented URL or disclosure receipt exists
- verified recorded disclosure input is required for the normal disclosure demo

### API/UI integration

- API `/health`
- API `/api/chat`
- Streamlit health
- Streamlit recorded answer
- Streamlit unconfigured/fallback answer
- process visibility remains accurate
- wrong-company, stale, low relevance, provider failure, budget, and fallback
  are each visible in the approved process-summary boundary
- complete, partial, no-evidence, provider-failed, and blocked public states do
  not regress
- evidence cards and citations preserve existing validation

### Release regression

- full unit and integration suite
- direct M3 Gate
- Critical cases
- public exposure scanner
- secret scan
- compile
- Ruff
- clean image build
- local API/UI smoke
- approved remote API/UI smoke
- rollback evidence

---

## 12. Risk Mapping

| Risk | B9 control |
|---|---|
| `R17` secret exposure | least-privilege CI, `.dockerignore`, secret scan, no secret values, image/config/log inspection |
| `R20` local works but deploy fails | clean Docker build, health smoke, approved remote smoke, rollback |
| `R53` no quality evidence | exact test/gate commands and release-candidate evidence |
| `R54` evaluation boundary ambiguity | unchanged fixture, runner, threshold, and explicit recorded/live labels |
| `R55` misleading final score | full and Critical denominators recorded |
| `R56` critical safety regression | Critical `17/17` gate remains mandatory |
| `R57` raw output exposure | public exposure `0`, release smoke, secret/path/raw-payload checks |
| `R58` unsupported performance claim | report only locally or remotely measured latency with environment and timestamp |

---

## 13. Stop Conditions

Stop implementation and report:

- any B9-0 regression, gate, secret-scan, or compile failure
- a new commit after the approved plan that changes a B9 contract
- dirty code, fixture, dependency, or lock changes that overlap this task
- unavailable or unverifiable official action/image pin
- Ruff baseline requiring broad unrelated cleanup
- any dependency or lock change beyond exact Ruff approval
- the explicit pre-commit release-asset scan does not cover all B9 text assets
- Docker unavailable when entering container verification
- a required destructive container action that cannot be scoped to B9 resources
- remote target, permissions, or deploy approval missing
- a target requiring a new SDK or architecture change
- a frozen public schema, core model/status, M1, or M2 change
- a live provider, LLM, credential, or external corpus requirement
- a need to invent a URL, receipt, page, section, permission, or actual coverage
- no verified recorded disclosure input for the required normal M4-06 scenario
- demo data license or provenance uncertainty
- recorded demo planning or freshness uses wall-clock time instead of manifest
  `basis_at`
- a test import in production runtime
- loss of wrong-company, prohibited-advice, citation, or source validation
- golden below `34/34`, Critical below `17/17`, or public exposure above `0`
- startup depending on live external network
- a secret or local path in image layers, Compose output, docs, logs, or public
  responses
- remote smoke or rollback failure
- the primary remote release is not explicitly configured as `recorded`

The report must include the problem, evidence, minimum safe change, alternatives,
schedule impact, test impact, and current Git state.

---

## 14. Rollback and Fallback

### Code and configuration

- `QUESTOCK_SOURCE_MODE` defaults to `unconfigured`.
- Recorded mode can be disabled without changing public contracts.
- If recorded data validation fails, startup fails safely; it does not fall back
  silently to live mode.
- CI and release assets can be reverted as a dedicated release bundle after
  user approval. Do not use reset, restore, checkout, or clean.

### Container

- retain the previous approved image digest
- deploy by immutable digest, not a mutable tag alone
- rollback by selecting the previous digest/release
- verify API and UI health after rollback

### Remote deployment

- stop rollout on failed health or smoke
- do not migrate persistent data because B9 adds no database
- never solve deployment failure by exposing a credential in config, logs, or
  source files

---

## 15. Completion Criteria

B9 may be recorded `PASS / complete` only when:

- [ ] B9 plan is approved
- [ ] B9-0 preflight passes
- [ ] exact Ruff dependency and lock change are approved and verified
- [ ] local Ruff passes
- [ ] pre-commit release-asset secret/path scan passes
- [ ] GitHub CI passes on the exact release candidate SHA
- [ ] clean local image build passes
- [ ] local API and UI health/smoke pass
- [ ] recorded demo mode passes without live claims or invented locators
- [ ] recorded runtime uses manifest `basis_at` consistently
- [ ] verified recent-disclosure normal scenario passes
- [ ] remote target is separately approved
- [ ] one canonical target deployment command is documented
- [ ] the primary remote release runs in `recorded` mode
- [ ] remote deployment and smoke pass
- [ ] rollback method is verified
- [ ] README and release/demo docs match the release candidate
- [ ] P0 traceability is complete
- [ ] full tests pass
- [ ] M3 Gate remains `34/34`
- [ ] Critical remains `17/17`
- [ ] public exposure remains `0`
- [ ] secret scan passes
- [ ] compile passes
- [ ] implementation diff is reviewed
- [ ] B9 independent implementation review passes
- [ ] M4 Gate independent review passes
- [ ] the Human Owner confirms the three-minute code-flow explanation
- [ ] user confirms the result
- [ ] the confirmed Step is recorded in the dated work log
- [ ] any commit, push, PR, merge, or deploy has its own approval

An unavailable Docker runtime, unselected remote target, or missing verified
recorded disclosure input leaves B9 and M4 Gate blocked. Documentation alone
cannot close those items.

---

## 16. Required User Decisions

Before implementation:

1. approve or reject `ruff==0.15.22` and the corresponding lock update
2. approve or reject the application-owned `synthetic_demo` recorded corpus and
   runtime gateway
3. provide or approve access to a Docker-capable environment for B9-A
4. provide one independently verified recorded disclosure item with its real
   receipt number and official viewer URL, or separately approve an M4-06 plan
   amendment

Before remote deployment:

5. select the deployment target
6. approve target-specific configuration work, if any
7. approve the deploy action separately

Git actions remain separately gated:

8. implementation commit approval
9. implementation push approval
10. closure docs commit approval
11. closure docs push approval
12. PR approval
13. merge approval

---

## 17. Result Log

### Planning

- Planning inspection:
  `PASS`
- Plan self-review:
  `CONDITIONAL PASS`
- Mandatory plan supplement:
  `IMPLEMENTED`
- External plan approval:
  `NOT_RUN`
- Code changes:
  `NOT_RUN`
- Dependency changes:
  `NOT_RUN`
- Tests:
  `NOT_RUN`
- Docker:
  `NOT_RUN - executable not found`
- GitHub CI:
  `NOT_RUN`
- Remote deployment:
  `NOT_RUN - target and approval absent`
- Commit/push:
  `NOT_RUN`

### B9-0

- Start SHA:
  `NOT_RUN`
- Git/preflight:
  `NOT_RUN`
- Full pytest:
  `NOT_RUN`
- M3 Gate:
  `NOT_RUN`
- Secret scan:
  `NOT_RUN`
- Compile:
  `NOT_RUN`
- Tool inventory:
  `NOT_RUN`

### B9-A

- Ruff:
  `NOT_RUN`
- CI structure:
  `NOT_RUN`
- GitHub CI:
  `NOT_RUN`
- Docker build:
  `NOT_RUN`
- Local API/UI smoke:
  `NOT_RUN`
- Checkpoint HANDOFF:
  `NOT_RUN`

### B9-B

- Recorded demo:
  `NOT_RUN`
- Remote target:
  `NOT_SELECTED`
- Remote deployment:
  `NOT_RUN`
- Remote smoke:
  `NOT_RUN`
- Rollback:
  `NOT_RUN`
- Release docs:
  `NOT_RUN`
- P0 traceability:
  `NOT_RUN`
- B9 review:
  `NOT_RUN`
- M4 Gate:
  `NOT_RUN`
