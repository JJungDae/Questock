# Questock Recorded MVP Release

## Release State

| Item | State |
|---|---|
| Foundation main SHA | `1a14efbb85669a03340442e1a73b6416adbf2bed` |
| Foundation implementation | `71ac117690f494f05a337d852abc917b5b2addd8` |
| Python 3.11 CI compatibility fix | `0e703b6fd0bcc13b33c39ff539a27c523176fe0d` |
| Foundation PR and main `quality-gate` | `PASS` |
| Main protection Ruleset | `active` |
| B9-B merged main SHA | `c807be1d4b62acd0d45dea42b884bd16dd366652` |
| Recorded release candidate SHA | `67fa43dd5a7ec74e7785713eb1adcfa402baab85` |
| Release image ID | `sha256:56df8f16ed3ed58de659e9ec46c9e24b7d3ddc896dc8a022102f68f351d7b928` |
| Release `quality-gate` | `PASS - run 30207273750` |
| Remote deployment | `PASS - run 30207335981` |
| M4 Gate | `NOT_RUN` |

This document describes a remotely deployed recorded-only MVP. It is not
evidence of live provider connectivity, production coverage, or live LLM
operation.

## Environment Matrix

| Environment | Mode | Evidence status |
|---|---|---|
| local Python | recorded | targeted and full regression executed locally |
| local Docker | recorded | clean build, API/UI health, and 7-scenario smoke PASS |
| GitHub Actions | recorded image build | exact release SHA quality-gate PASS |
| GCE | recorded | exact-SHA deploy, API/UI health, and 7-scenario smoke PASS |

The Windows local environment may need an installed `tzdata` package for
`ZoneInfo("Asia/Seoul")`; B9 adds no dependency for that deferred clean-build
environment concern.

## Data Manifest

- corpus type: `recorded_demo`
- schema: `b9-recorded-v1`
- basis timestamp: `2026-07-26T00:00:00Z`
- document count: 3
- supported demo security: Samsung Electronics (`KRX:005930`)

Data usage:

- Samsung Newsroom item: short Questock-authored Korean summary
- Samsung IR earnings material: short Questock-authored research note
- DART receipt `20260515002181`: receipt plus six verified body facts

The corpus stores public reference URLs but not source PDF bodies. The DART
record preserves the approved values/units, physical PDF pages, DART printed
pages, and fact-specific section labels. It does not include the full filing
body, inferred report-family links, or actual disclosure coverage.

## Health and Smoke

Required local and remote health:

```text
API: http://127.0.0.1:8000/health
UI:  http://127.0.0.1:8501/_stcore/health
```

Required recorded smoke is implemented in `scripts/release_smoke.py`. The local
Docker run passed all seven scenarios, including the anonymous two-turn flow.
The approved GCE deployment also passed all seven scenarios. The disclosure
scenario remains `partial` with `insufficient_disclosure_coverage`; M4 Gate
remains `NOT_RUN`.

## GCE Runbook

Target:

- Google Compute Engine
- deployment user: `user`
- repository directory: `/home/user/Questock`
- external UI port: `8501`
- API port: loopback-only `8000`

The canonical deploy mechanism is the manual `deploy-recorded-gce` workflow.
The Human Owner first confirms that the exact 40-character release SHA is on
`main` and has a successful `quality-gate`, then separately approves the
`workflow_dispatch` action.

The workflow:

1. validates the release SHA
2. requires a clean remote worktree
3. verifies the SHA is an ancestor of `origin/main`
4. builds the immutable `questock:<release_sha>` image before replacement
5. starts explicit recorded mode
6. checks internal API/UI health and recorded scenarios
7. checks the external UI health endpoint
8. records release and image identifiers without credential values

It does not auto-deploy on a main push and does not expose the API host port.

## Rollback

If Compose startup, API/UI health, recorded smoke, or external UI health fails:

- use the previous clean Git SHA and immutable image when available
- capture the previous immutable image ID before rebuilding, including when
  the previous SHA equals the requested release SHA
- restore recorded mode and recheck previous API/UI health
- on the first failed deployment with no previous image, remove only the
  Questock Compose services
- fail remote preflight before entering the rollback guard
- do not reset the repository, prune global Docker resources, or expose secrets

The successful deployment captured previous release
`331c41cbf09cc5541f03a17feb9194c0e442e81b` and immutable previous image
`sha256:a9168da00ebbbe9157e6b235c86e3600a58aaa2e470cb0001484f6fd66b480ae`
as the rollback target. Rollback execution remains `NOT_RUN` because the
deployment and smoke passed and did not enter the failure path.

## Quality Evidence

Foundation evidence already observed:

- local full pytest: `1809 passed`
- M3 Gate: `34/34`
- Critical: `17/17`
- public exposure: `0`
- foundation PR and main CI: `PASS`

B9-B local results:

- targeted pytest: `42 passed, 2 warnings`
- full pytest: `1836 passed, 2 warnings`
- no-cache image build and Python 3.11.15 non-root runtime inspection: `PASS`
- API/UI health and seven recorded smoke scenarios: `PASS`
- Ruff, secret/path scans, and compile: `PASS`
- M3 Gate: `34/34`, Critical `17/17`, public exposure `0`

Focused closure local results:

- M4-06 disclosure scenario:
  `PASS WITH DECLARED COVERAGE LIMITATION`
- final disclosure status:
  `partial` with `insufficient_disclosure_coverage`
- focused targeted pytest:
  `41 passed, 2 warnings`
- full pytest:
  `1851 passed, 2 warnings`
- rollback workflow static tests:
  `16 passed, 1 cache warning`
- release hotfix targeted/full local regression:
  `17 passed`; `1826 passed, 2 warnings`
- exact release quality-gate:
  `PASS - 1852 passed, 1 warning; M3 Gate 34/34; Critical 17/17; exposure 0`
- remote deployment and health:
  `PASS - run 30207335981; internal API/UI and external UI health`
- remote recorded smoke:
  `PASS - 7 scenarios; data_mode recorded; live connectivity false`
- remote rollback:
  `target captured; execution NOT_RUN because deployment passed`

Local results remain distinct from the observed GitHub CI and remote evidence.
Independent B9 review, M4 Gate, and Human Owner flow confirmation remain open.

## Known Risks and Deferrals

- live Gemini, news, OpenDART, and report adapters: `NOT_ACTIVATED`
- actual news/report/disclosure coverage: `NOT_RUN`
- production orchestration and real 365-day disclosure completeness:
  `NOT_RUN`
- M1-09 final independent review: pending
- M3-12: `NOT_ACTIVATED`
- GCE external IP may be ephemeral and is not documented as a permanent URL
- rollback execution, independent B9 review, Human Owner flow confirmation,
  and M4 Gate remain separate closure evidence
