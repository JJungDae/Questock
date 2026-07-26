# TASK CARD - B9 Release, Deployment, Demo, and Traceability

## 1. Status and Approval

- Project: `Questock`
- Repository: `JJungDae/Questock`
- Branch: `fix/b9-m4-gate-closure`
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
- Plan publication SHA:
  `8db690b80b7d117e32b6fcd4986d4bfbecc602b1`
- Plan publication commit:
  `docs: plan B9 release bundle`
- Plan publication main push:
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
  `PASS WITH REQUIRED FOLLOW-UP`
- B9 required plan corrections:
  `IMPLEMENTED`
- Additional external plan review:
  `NOT_REQUIRED`
- B9-0:
  `PASS / complete - preflight executed at 8db690b80b7d117e32b6fcd4986d4bfbecc602b1`
- B9 remaining implementation plan:
  `REVIEWED V2 / approved as the current execution supplement`
- B9 implementation base:
  `74214b75575fd9f1594ac545b42bbf3908066e77`
- B9 implementation:
  `B9-A1+A2 PASS / B9-B remote recorded release PASS / B9 review PASS WITH REQUIRED FOLLOW-UP / M4 Gate HOLD`
- B9-A local Docker verification:
  `PASS - locked image build, API/UI health, smoke, and runtime inspection complete`
- B9-B remote deployment:
  `PASS - exact release SHA deployed in recorded mode; run 30207335981`
- GitHub CI:
  `PASS - PR and main quality-gate observed on B9-A foundation merge`
- Dependency and lock change:
  `APPROVED - exact ruff==0.15.22 delta only`
- Current B9 plan/B9-0 docs-only commit and push:
  `complete - 74214b75575fd9f1594ac545b42bbf3908066e77`
- B9 implementation commit/main push:
  `complete - 71ac117690f494f05a337d852abc917b5b2addd8`
- B9-A CI compatibility fix:
  `complete - 0e703b6fd0bcc13b33c39ff539a27c523176fe0d`
- B9-A PR merge/main SHA:
  `complete - 1a14efbb85669a03340442e1a73b6416adbf2bed`
- B9-B implementation SHA:
  `6ed6c13a143f5798157aed2344d09ae126ced00b`
- B9-B implementation commit:
  `complete - Implement B9 recorded release runtime`
- B9-B release branch push:
  `complete - origin/release/b9-recorded-deployment`
- B9-B release PR and main merge:
  `complete - PR #2; merged main SHA c807be1d4b62acd0d45dea42b884bd16dd366652`
- B9 focused closure base:
  `c807be1d4b62acd0d45dea42b884bd16dd366652`
- B9 focused closure implementation SHA:
  `d70e17a95046f5ebcbca05970ff574c1121acb1c`
- B9 focused closure:
  `PASS - PR #3 merged at 8dc9c322af89e395aa62e614c69b0840e7aedbae`
- Main protection Ruleset:
  `active - PR, quality-gate, deletion, and force-push protections`
- B9-B remote deploy:
  `PASS - release SHA 67fa43dd5a7ec74e7785713eb1adcfa402baab85`
- B9 M4 Gate closure base:
  `390c248a47032c3babe07eb6dbbc111668a17ead`
- B9 independent implementation review:
  `PASS WITH REQUIRED FOLLOW-UP`
- M4 Gate:
  `HOLD - CI/document closure and Human Owner confirmation pending`

This is the canonical B9 plan. The implementation instruction authorized B9-A1
and B9-A2 foundation work through merge and observed CI. B9-B local
implementation was merged before this focused closure. The focused closure and
two deployment hotfixes were merged through reviewed PRs. The approved
exact-SHA remote deployment and recorded smoke passed. Independent B9 review
is `PASS WITH REQUIRED FOLLOW-UP`. M4 Gate remains `HOLD` until this
CI/document closure is merged, its quality gate passes, and the Human Owner
confirms the required release explanation.

### 1.1 Reviewed V2 execution supplement

The reviewed V2 supplement fixes the remaining execution order:

```text
Gate B9-R0
-> B9-A1 Ruff and CI
-> B9-A2 Dockerfile and Compose foundation
-> unconfigured local image build and health
-> local full verification
-> Human Owner approval
-> implementation commit and first main push
-> exact-SHA quality-gate SUCCESS
-> Ruleset activation
-> release/b9-recorded-deployment branch
-> B9-B1 through B9-B4
-> B9 independent review
-> M4 Gate
```

B9-A1 and A2 foundation are one first-push lifecycle checkpoint. The first CI
push must contain the Dockerfile and release-asset tests, so CI cannot fail
merely because the container foundation is absent.

Confirmed product and provenance boundary:

- B9 is a `recorded-only MVP`.
- live Gemini, news, DART, and research-report providers remain
  `NOT_IMPLEMENTED`.
- post-B9 live integration remains `PROPOSAL ONLY / NOT_ACTIVATED`.
- approved synthetic news and Questock research-note records must cite
  inspectable public references and use `synthetic_project_owned`.
- the approved Samsung Electronics DART receipt
  `20260515002181` uses `verified_public_recorded` for its approved receipt and
  six separately supplied verified body facts. The fixture preserves the
  approved values and units, physical PDF pages, DART printed pages, and
  fact-specific section labels without converting them.
- this one-item fixture is not actual disclosure coverage. The scenario remains
  `partial` with `insufficient_disclosure_coverage`.
- the full DART PDF and copyrighted report bodies must not be committed.

Confirmed deployment boundary:

- target platform: Google Compute Engine
- deployment user: `user`
- external UI port: `8501`
- API host binding: `127.0.0.1:8000`
- UI host binding: `0.0.0.0:8501`
- Compose UI endpoint: `http://api:8000/api/chat`
- GitHub deployment secrets are configured by the Human Owner, but values are
  never read, logged, or committed by this task.
- remote deployment, Ruleset mutation, Git operations, and firewall changes
  retain their explicit lifecycle approvals.

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

The review inspection found:

- `HEAD` and `origin/main` both point to
  `8db690b80b7d117e32b6fcd4986d4bfbecc602b1`.
- At review start, the only observed working-tree items were pre-existing
  untracked B7 review bundle artifacts.
- This review then modified only this B9 Task Card and
  `docs/agent_handoff/SOURCE_OF_TRUTH_INDEX.md`; those approved plan corrections
  remain uncommitted until a separate Git approval.
- The B7 artifacts are user-owned and must remain untouched.
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
- runner: `ubuntu-24.04`
- Python `3.11`, matching the declared minimum supported runtime
- uv `0.11.32`, matching the approved local lock tool
- locked installation:

```text
uv sync --locked --extra dev
```

- exact setup:

```yaml
- uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6.0.2
- uses: astral-sh/setup-uv@08807647e7069bb48b6ef5acd8ec9567f424441b # v8.1.0
  with:
    version: "0.11.32"
    python-version: "3.11"
    enable-cache: true
- run: uv sync --locked --extra dev
- run: >-
    uv run --no-sync python -c
    "import sys; assert sys.version_info[:2] == (3, 11)"
```

- checks, in this order:
  1. Ruff static lint
  2. full pytest
  3. direct M3 Gate
  4. project secret scan
  5. Python compile
  6. container image build after the Dockerfile exists

Third-party actions must be official project actions and pinned by full commit
SHA. Independent review verified these immutable release pins:

- `actions/checkout`:
  `de0fac2e4500dabe0009e67214ff5f5447ce83dd`
- `astral-sh/setup-uv`:
  `08807647e7069bb48b6ef5acd8ec9567f424441b`

Do not repeat version exploration during B9-0. Reverification is required only
if the approved full SHA, version, or workflow contract changes. Do not replace
a full SHA with a mutable tag.

GitHub CI remains `NOT_RUN` until the workflow is committed, pushed, and the
exact run is observed. Local execution must not be described as CI success.

### 6.2 Ruff contract

Add exactly:

```text
ruff==0.15.22
```

as a development dependency and update `uv.lock` with the approved uv tool.
Do not add a formatter, mypy, pyright, pre-commit, or another lint dependency.

The only approved dependency and lock delta is:

```text
pyproject.toml:
  add ruff==0.15.22 to project.optional-dependencies.dev

uv.lock:
  add the ruff 0.15.22 package entry and hashes
  add ruff to questock package.optional-dependencies.dev
  add the matching questock package.metadata requires-dist entry

existing third-party package version/source movement:
  0 allowed

additional direct dependency:
  0 allowed

unexpected new transitive package:
  0 allowed
```

Compare parsed package name, version, and source tuples before and after the
lock update. Any existing package movement, unrelated lock reformat, or wider
root metadata change is a stop condition. The exact expected delta needs no
additional dependency review.

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

The Docker builder dependency command is fixed:

```text
uv sync --locked --no-dev --no-install-project
```

Rules:

- bind or copy only `pyproject.toml` and `uv.lock` for this dependency layer
- do not use `--all-extras`, `--extra dev`, or `--dev`
- do not modify the lockfile
- copy the application source into a later image layer
- copy only the locked runtime environment and application source into the
  non-root runtime image
- verify Ruff and pytest are absent from the runtime environment

Do not assert that `httpx` is absent. It is a required transitive runtime
dependency of the approved LiteLLM pin even when the Questock `dev` extra is
not selected. Release-asset tests must distinguish a transitive runtime package
from selection of the direct `dev` extra.

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

Runtime lifetime is fixed:

- validate runtime configuration once per API process at import/startup
- load and validate the demo manifest/corpus once per API process
- create one `RecordedDemoSourceGateway` over an immutable corpus
- create one `InMemorySessionStore`
- create one `ChatService` singleton per API process
- make `get_chat_service()` return that same singleton for every request
- deep-copy recorded documents and provider payloads on each gateway fetch

Do not rebuild `ChatService`, session state, the manifest, or the corpus per
request. Tests must assert singleton identity across dependency calls and
preservation of an anonymous multi-turn session across two API requests.

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
fallback test. It requires an independently verified recorded disclosure item
with its real receipt number and official viewer URL. The item may be:

- supplied by the user, or
- found through separately approved read-only research of the official DART
  public site

The Human Owner must approve the exact receipt number, official URL, report
title, company attribution, and recorded content before corpus inclusion.
OpenDART API calls, credentials, bulk collection, and unapproved external
network access remain outside B9. The Human Owner supplied one approved item
and six body facts for the focused closure:

```text
Recorded disclosure fallback test: ALLOWED
M4-06 normal disclosure demo: PASS WITH DECLARED COVERAGE LIMITATION
B9 focused closure local verification: PASS
B9 remote deployment and recorded smoke: PASS
B9 rollback target: VERIFIED; execution NOT_RUN
M4 Gate: HOLD - CI/document closure and Human Owner confirmation pending
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

Use three lifecycle checkpoints while keeping each important Git and deployment
action separately approved:

1. local B9 implementation result
   - approve implementation commit
   - after the commit exists, separately approve main push
   - record commit and push as separate actions and outcomes
   - observe GitHub CI only after the push
2. deployment target and configuration
   - separately approve remote deploy
   - run smoke and rollback verification
3. final B9/M4 result
   - approve closure-doc commit
   - after the commit exists, separately approve closure-doc main push
   - record closure commit and push as separate actions and outcomes

PR and merge are `N/A` while the approved workflow commits directly to `main`.
They become separately approved actions only if the user selects a branch/PR
workflow.

The evidence-producing order is:

```text
local implementation
-> targeted/full/gate/secret/compile/container verification
-> implementation result and diff report
-> implementation commit approval
-> implementation commit
-> implementation push approval
-> main push
-> GitHub CI observation on the exact pushed SHA
-> deployment target/config review and deploy approval
-> immutable-SHA/image remote deployment
-> remote smoke and rollback evidence
-> Task Card/release/traceability factual synchronization
-> closure-doc commit approval
-> closure docs commit
-> closure-doc push approval
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

B9-0 is a preflight, not CI/Docker/demo implementation. It performs no
application-code, fixture, dependency, lock, workflow, or container-file
change. The only permitted write is factual B9-0 result logging in this Task
Card after commands finish.

B9-0 begins only after the user explicitly approves its execution. It may
observe the approved plan-follow-up edits to this Task Card and
`SOURCE_OF_TRUTH_INDEX.md`, but any dirty code, fixture, `pyproject.toml`, or
`uv.lock` blocks the preflight.

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
- B9 plan publication SHA is
  `8db690b80b7d117e32b6fcd4986d4bfbecc602b1`
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

Missing Docker does not block B9-A1 CI/Ruff/release-asset preparation. It blocks
B9-A2 container execution and B9-A completion. Do not install Docker without
explicit user approval.

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

The prior B8 closure recorded `1802 passed`; this is a reference, not a B9-0
result. B9-0 reports the actual rerun count. Any count difference requires
test-collection and Git-diff investigation before B9-A.

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

1. Use the already verified full action SHAs and exact setup inputs.
2. Add exact Ruff dependency and update only the approved lock entries.
3. Compare parsed pre/post lock package tuples and root metadata against the
   approved Ruff-only delta.
4. Run the bounded Ruff audit before application edits.
5. Add the least-privilege CI workflow.
6. Add release-asset tests that parse the workflow and reject:
   - mutable action tags
   - `pull_request_target`
   - write permissions
   - live credential use
   - runner other than `ubuntu-24.04`
   - uv version other than `0.11.32`
   - Python version other than `3.11`
   - missing Python 3.11 runtime assertion
   - missing locked install
   - missing required checks
7. Run the explicit pre-commit release-asset secret/path scan.
8. Run targeted and full regression locally.
9. Record GitHub CI as `NOT_RUN` until a later approved push and observed run.

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
4. Add static tests that require the exact runtime sync command, reject every
   dev-extra flag, and verify Ruff/pytest are absent without incorrectly
   rejecting transitive runtime `httpx`.
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
4. Construct runtime configuration, corpus, gateway, session store, and
   `ChatService` once per API process.
5. Wire the API dependency to return the same singleton without changing
   public schemas.
6. Add deterministic unit tests for loader, gateway, singleton identity,
   one-time load, mode selection, mutation isolation, and sanitized failure.
7. Add an exact two-request anonymous multi-turn API test.
8. Add integration tests for representative API and Streamlit flows.

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
- workflow pins `ubuntu-24.04`, uv `0.11.32`, and Python `3.11`
- workflow asserts the effective Python runtime is exactly `3.11`
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
- lock diff contains only Ruff plus the expected `questock` dev-extra metadata
- every pre-existing third-party package keeps the same version and source
- Docker uses
  `uv sync --locked --no-dev --no-install-project`
- Docker runtime excludes Ruff and pytest
- Docker validation permits transitive runtime `httpx`

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
- `get_chat_service()` returns one process-level singleton
- runtime config and demo corpus load once per process
- two API requests preserve one anonymous multi-turn session
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

- [x] B9 plan is approved
- [x] B9-0 preflight passes
- [x] exact Ruff dependency and lock change are approved and verified
- [x] local Ruff passes
- [x] pre-commit release-asset secret/path scan passes
- [x] GitHub CI passes on the exact release candidate SHA
- [x] clean local image build passes
- [x] local API and UI health/smoke pass
- [x] recorded demo mode passes without live claims or invented locators
- [x] recorded runtime uses manifest `basis_at` consistently
- [x] verified recent-disclosure normal scenario passes
- [x] remote target is separately approved
- [x] one canonical target deployment command is documented
- [x] the primary remote release runs in `recorded` mode
- [x] remote deployment and smoke pass
- [x] rollback method and immutable target are verified; execution was not triggered
- [x] README and release/demo docs match the local implementation candidate
- [x] P0 traceability records the observed remote result and remaining gates
- [x] full local tests pass
- [x] M3 Gate remains `34/34`
- [x] Critical remains `17/17`
- [x] public exposure remains `0`
- [x] secret scan passes
- [x] compile passes
- [ ] implementation diff is reviewed
- [ ] B9 independent implementation review passes
- [ ] M4 Gate independent review passes
- [ ] the Human Owner confirms the three-minute code-flow explanation
- [ ] user confirms the result
- [ ] the confirmed Step is recorded in the dated work log
- [x] any commit, push, PR, merge, or deploy has its own approval

An unavailable Docker runtime, unselected remote target, or missing verified
recorded disclosure input leaves B9 and M4 Gate blocked. Documentation alone
cannot close those items.

---

## 16. Required User Decisions

Before B9-0:

1. approve read-only B9-0 preflight execution and factual Task Card result
   logging

After B9-0 PASS, before B9-A implementation:

2. approve execution of the technically reviewed `ruff==0.15.22` lock update
   and CI/release-asset work
3. provide or approve access to a Docker-capable environment before B9-A2

Before B9-B:

4. approve the application-owned `synthetic_demo` recorded corpus and runtime
   gateway
5. provide one independently verified recorded disclosure item with its real
   receipt number and official viewer URL, or separately approve an M4-06 plan
   amendment

Before remote deployment:

6. select the deployment target
7. approve target-specific configuration work, if any
8. approve the deploy action separately

Git actions remain separately gated:

9. implementation commit approval
10. implementation push approval
11. closure docs commit approval
12. closure docs push approval
13. PR approval only if a branch/PR workflow is selected; otherwise `N/A`
14. merge approval only if a branch/PR workflow is selected; otherwise `N/A`

---

## 17. Result Log

### Planning

- Planning inspection:
  `PASS`
- Plan self-review:
  `CONDITIONAL PASS`
- Mandatory plan supplement:
  `IMPLEMENTED`
- Independent plan review:
  `PASS WITH REQUIRED FOLLOW-UP`
- Independent plan corrections:
  `IMPLEMENTED`
- Additional plan review:
  `NOT_REQUIRED`
- Official checkout/setup-uv/uv/Ruff verification:
  `PASS - official release and action contracts checked`
- Reviewer corrections accepted:
  `CI inputs, singleton lifetime, Docker runtime sync, three lifecycle checkpoints`
- Reviewer corrections refined:
  `Ruff lock root metadata allowed; runtime httpx allowed as LiteLLM dependency; Git actions remain separately approved`
- B9-0 launch:
  `APPROVED / COMPLETE`
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
- Plan-correction commit/push:
  `APPROVED - current docs-only changeset`

### B9-0

- Start SHA:
  `8db690b80b7d117e32b6fcd4986d4bfbecc602b1`
- Git/preflight:
  `PASS - main; HEAD equals origin/main; only approved B9 docs and existing user-owned B7 review artifacts were dirty; all nine frozen blob SHAs matched`
- Full pytest:
  `PASS - final exit 0; 1802 passed, 2 warnings`
  - Initial exact command:
    `ENVIRONMENT_INVALID - exit 1; the existing pytest temp root was inaccessible`
  - First fresh-temp retry:
    `ENVIRONMENT_INVALID - exit 1; sandbox ACL made generated temp children inaccessible`
  - Final rerun:
    `task-scoped fresh temp parent, explicit --basetemp, cache provider disabled, sandbox escalation; no code or test expectation changes`
- M3 Gate:
  `PASS - exit 0; 34/34, Critical 17/17, public exposure 0, M3-12 NOT_ACTIVATED`
- Secret scan:
  `PASS - exit 0; []`
- Compile:
  `PASS - exit 0; no output`
- Tool inventory:
  - Python:
    `3.14.3`
  - uv:
    `0.11.32`
  - GitHub CLI:
    `2.93.0`
  - Docker:
    `NOT_AVAILABLE - command not found`
  - Docker Compose:
    `NOT_AVAILABLE - Docker command not found`
- B9-0 final status:
  `PASS / complete`
- B9-A1 implementation:
  `READY after separate user approval`
- B9-A2 implementation:
  `BLOCKED - Docker/Compose unavailable`
- Code, fixture, dependency, lock, workflow, and container changes:
  `NOT_RUN`

### B9-A

- B9-A1 launch:
  `APPROVED / COMPLETE - local implementation and verification`
- B9-A2 launch:
  `APPROVED / COMPLETE - local implementation and verification`
- Implementation base:
  `74214b75575fd9f1594ac545b42bbf3908066e77`
- Implementation SHA:
  `71ac117690f494f05a337d852abc917b5b2addd8`
- Python 3.11 CI compatibility fix SHA:
  `0e703b6fd0bcc13b33c39ff539a27c523176fe0d`
- PR merge/main SHA:
  `1a14efbb85669a03340442e1a73b6416adbf2bed`
- Dependency/lock delta:
  `PASS - ruff==0.15.22 only; existing package name/version/source records unchanged`
- Ruff:
  `PASS - exact E4,E7,E9,F command; baseline-only unused imports and one E731 were corrected without behavior changes`
- CI structure:
  `PASS - immutable actions, uv 0.11.32, Python 3.11 assertion, locked dev sync, required checks, and Docker build command`
- GitHub CI:
  `PASS - B9-A PR and merged-main quality-gate runs observed`
- Release-asset targeted pytest:
  `PASS - exit 0; 11 passed, 3 warnings on final post-document recheck`
- Full pytest:
  `PASS - exit 0; 1809 passed, 2 warnings`
- M3 Gate:
  `PASS - exit 0; 34/34, Critical 17/17, public exposure 0, M3-12 NOT_ACTIVATED`
- Secret scan:
  `PASS - exit 0; tracked scan [] and explicit untracked release-asset scan []`
- Compile:
  `PASS - exit 0; no output`
- Docker build:
  `PASS - docker compose build --pull --no-cache and CI-equivalent docker build --pull --no-cache --tag questock:ci . both exit 0`
- Docker runtime:
  `PASS - Python 3.11.15, uid/gid questock 999, Ruff and pytest absent, no local review/test/docs assets in /app`
- Compose:
  `PASS - one shared image; API 127.0.0.1:8000; UI 8501; no volumes or live credentials`
- Local API/UI smoke:
  `PASS - API /health 200 in explicit unconfigured mode; UI health ok; chat returned sanitized provider_failed with data_mode unconfigured and live_connectivity_checked false`
- Docker verification deviation:
  `Initial compose wait returned unhealthy because the existing fixture-readiness /health contract expected test fixtures excluded from the image. A narrow explicit QUESTOCK_SOURCE_MODE=unconfigured health branch was added; default fixture-readiness behavior and tests remain unchanged. Rebuild, health, and smoke then passed.`
- Python environments:
  `Local uv environment 3.14.3; Docker runtime 3.11.15; GitHub CI Python 3.11 NOT_RUN`
- Checkpoint HANDOFF:
  `THIS RESULT LOG plus the implementation result report serve as the temporary HANDOFF; no separate formal HANDOFF file created`
- Scoped Docker cleanup:
  `PASS - questock-api-1, questock-ui-1, and questock_default removed; images and unrelated Docker resources preserved`
- Final recheck environment note:
  `The sandboxed uv wrapper could not initialize the user uv cache and exited before test execution. The same locked .venv executables then passed targeted pytest, Ruff, secret scan, and compile; this is an environment retry, not a code/test failure.`
- Implementation commit/main push:
  `complete`
- Ruleset activation:
  `PASS - main PR, quality-gate, deletion, and force-push protections active`
- B9-A final status:
  `PASS / complete`

### B9-B

- Recorded demo:
  `LOCAL PASS - deterministic recorded corpus and runtime verified`
- Implementation base:
  `1a14efbb85669a03340442e1a73b6416adbf2bed`
- Implementation branch:
  `release/b9-recorded-deployment`
- Implementation SHA:
  `6ed6c13a143f5798157aed2344d09ae126ced00b`
- Implementation commit:
  `complete - Implement B9 recorded release runtime`
- Release branch push:
  `complete - origin/release/b9-recorded-deployment`
- PR/merge:
  `NOT_RUN - separate approval required`
- Local targeted pytest:
  `PASS - exit 0; 42 passed, 2 warnings`
- Full local pytest:
  `PASS - exit 0; 1836 passed, 2 warnings`
- Local Python environment:
  `3.14.3; local results are not Python 3.11 CI evidence`
- M3 Gate:
  `PASS - 34/34, Critical 17/17, public exposure 0, M3-12 NOT_ACTIVATED`
- Ruff:
  `PASS - exact E4,E7,E9,F scope`
- Secret/path scan:
  `PASS - project scanner [] and explicit modified/new B9 text scan []`
- Compile:
  `PASS - no output`
- Clean Docker build:
  `PASS - no-cache build; runtime Python 3.11.15`
- Docker runtime inspection:
  `PASS - uid/gid 999, pytest and Ruff absent, corpus schema b9-recorded-v1`
- Local API/UI health:
  `PASS - API recorded health and Streamlit health`
- Local recorded release smoke:
  `PASS - 7 scenarios: recent issue, disclosure, research report, glossary, wrong company, blocked advice, and multi-turn`
- Runtime follow-up correction:
  `Blocked/no-source responses now inherit the configured gateway data_mode; the recorded blocked scenario exposes recorded rather than unconfigured. Existing public schemas and source contracts are unchanged.`
- Startup validation:
  `PASS - FastAPI lifespan initializes the process singleton; invalid source mode fails startup with a sanitized RuntimeConfigurationError`
- Log inspection:
  `PASS - structured observation fields only; no question text, secret, raw exception, source payload, or local filesystem path observed`
- Scoped Docker cleanup:
  `PASS - B9 API/UI containers and Compose network removed; images and unrelated resources preserved`
- Remote target:
  `GCE SELECTED / deployment approved and executed`
- Deployment workflow:
  `PASS - manual exact-SHA workflow; deploy run 30207335981`
- Remote deployment:
  `PASS - release SHA 67fa43dd5a7ec74e7785713eb1adcfa402baab85`
- Remote smoke:
  `PASS - API/UI health, external UI health, and 7 recorded scenarios`
- Rollback:
  `READY - previous SHA/image captured; execution NOT_RUN because deploy passed`
- Release docs:
  `LOCAL PASS - README, MVP release, demo scenarios, and runbook drafted`
- P0 traceability:
  `REMOTE RESULT SYNCED - independent B9 and M4 Gate rows remain open`
- GitHub CI for B9-B:
  `PASS - exact release quality-gate run 30207273750`
- B9 review:
  `PASS WITH REQUIRED FOLLOW-UP`
- M4 Gate:
  `HOLD - CI/document closure and Human Owner confirmation pending`
- B9-B current status:
  `remote release PASS / B9 review PASS WITH REQUIRED FOLLOW-UP / M4 Gate HOLD`

### B9 Focused Closure

- Focused closure base:
  `c807be1d4b62acd0d45dea42b884bd16dd366652`
- Focused closure branch:
  `fix/b9-focused-closure`
- Focused closure implementation SHA:
  `d70e17a95046f5ebcbca05970ff574c1121acb1c`
- Focused closure implementation commit:
  `Fix B9 focused closure`
- Focused closure branch push:
  `complete - origin/fix/b9-focused-closure`
- Disclosure prompt:
  `삼성전자 최근 공시 핵심 - unchanged`
- Disclosure provenance:
  `receipt 20260515002181; official viewer URL; verified_body_facts`
- Verified body-fact boundary:
  `six approved facts with exact values/units, physical PDF pages, DART printed pages, and fact-specific section labels; full filing body excluded`
- EvidenceDecision:
  `partial - unchanged M2-05/M2-06 contracts`
- Coverage warning:
  `insufficient_disclosure_coverage`
- M4-06 local disclosure scenario:
  `PASS WITH DECLARED COVERAGE LIMITATION`
- Wrong-company/no-evidence:
  `PASS - Samsung receipt and locator remain absent from the SK Hynix response`
- Rollback supplement:
  `IMPLEMENTED - compose startup, API health, UI health, recorded smoke, and external UI health share one rollback guard`
- Rollback safety:
  `preflight failures occur before the rollback guard; the pre-deploy immutable image ID is retagged to restore the previous SHA and API/UI health, otherwise only the failed Compose release is stopped and removed`
- Focused targeted initial run:
  `ENVIRONMENT_INVALID - 37 passed, 1 Streamlit Temp PermissionError`
- Focused targeted rerun:
  `PASS - exit 0; 41 passed, 2 warnings; sandbox escalation used only for Streamlit temporary-file access`
- Deployment workflow targeted:
  `PASS - exit 0; 16 passed, 1 cache warning`
- Full pytest:
  `PASS - exit 0; 1851 passed, 2 warnings`
- Ruff:
  `PASS - exact E4,E7,E9,F scope`
- M3 Gate:
  `PASS - 34/34, Critical 17/17, public exposure 0, M3-12 NOT_ACTIVATED`
- Secret scan:
  `PASS - exit 0; []`
- Compile:
  `PASS - exit 0; no output`
- Workflow YAML parse:
  `PASS`
- Remote deployment, remote smoke, and remote rollback:
  `deployment and smoke PASS; rollback target captured; execution NOT_RUN`
- Focused closure PR, CI, merge:
  `PASS - PR #3 merged; exact main quality-gate passed`
- Focused closure status:
  `PASS / complete`

### B9 Remote Release Closure

- First deployment preflight correction:
  `PR #4; merge SHA 331c41cbf09cc5541f03a17feb9194c0e442e81b`
- Recorded smoke propagation correction:
  `PR #5; release SHA 67fa43dd5a7ec74e7785713eb1adcfa402baab85`
- Release quality-gate:
  `PASS - run 30207273750; 1852 passed, 1 warning`
- Release M3 Gate:
  `PASS - 34/34; Critical 17/17; public exposure 0; M3-12 NOT_ACTIVATED`
- Deployment workflow:
  `PASS - run 30207335981`
- Release image:
  `sha256:56df8f16ed3ed58de659e9ec46c9e24b7d3ddc896dc8a022102f68f351d7b928`
- Previous release:
  `331c41cbf09cc5541f03a17feb9194c0e442e81b`
- Previous immutable image:
  `sha256:a9168da00ebbbe9157e6b235c86e3600a58aaa2e470cb0001484f6fd66b480ae`
- Remote mode:
  `recorded; live_connectivity_checked=false; basis_at=2026-07-26T00:00:00Z`
- Remote API/UI health:
  `PASS - internal API, internal Streamlit, and external Streamlit`
- Remote recorded smoke:
  `PASS - 7 scenarios: recent_issue complete, disclosure partial, research_report complete, glossary complete, wrong_company no_evidence, blocked blocked, multi_turn partial`
- M4-06 remote disclosure:
  `PASS WITH DECLARED COVERAGE LIMITATION - receipt 20260515002181, verified body facts, and insufficient_disclosure_coverage`
- Rollback readiness:
  `PASS - previous immutable target captured and rollback path retained`
- Rollback execution:
  `NOT_RUN - successful deployment did not enter the failure path`
- Remote release closure:
  `PASS`
- B9 independent implementation review:
  `PASS WITH REQUIRED FOLLOW-UP`
- M4 Gate independent review:
  `HOLD - CI/document closure and Human Owner confirmation pending`
- B9 current status:
  `REMOTE RELEASE PASS / B9 review PASS WITH REQUIRED FOLLOW-UP / M4 Gate HOLD`
