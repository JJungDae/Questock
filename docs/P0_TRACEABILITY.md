# Questock P0 Traceability

## Scope

This matrix links active P0 capabilities to their canonical implementation and
verification evidence. A Task Card status is not a substitute for an unrun
test, CI job, deployment, or live-provider check.

| Capability | Implementation | Verification evidence | State |
|---|---|---|---|
| Core financial models and status contracts | `app/core/models.py`, `app/core/status.py` | M1-01 Task Card and unit tests | complete |
| Three-security resolution | `app/core/resolver.py`, `data/securities.json` | M1-02 Task Card and resolver tests | complete |
| Provider policy and safe config | `app/providers/base.py`, `app/config.py` | M1-03 Task Card and provider/config tests | complete |
| Recorded news normalization | `app/providers/news.py` | M1-04 Task Card and news tests | complete |
| Recorded disclosure normalization | `app/providers/disclosure.py` | M1-05 Task Card and disclosure tests | complete |
| Manual research ingest boundary | `app/ingest/reports.py` | M1-06 Task Card and report tests | complete |
| Approved glossary corpus | `app/ingest/glossary.py`, `data/glossary.json` | M1-07 Task Cards and glossary tests | complete |
| Health and secret safety | `app/health.py`, `scripts/secret_scan.py` | M1-08 Task Card and scanner tests | complete |
| Market snapshot gate | `app/providers/market.py` | M1-09 Task Card | final independent review pending |
| Query planning and hard filter | `app/planning/query_planner.py`, `app/retrieval/filters.py` | M2-01/M2-02 Task Cards and tests | complete |
| Retrieval and Evidence normalization | `app/retrieval/retriever.py`, `app/evidence/normalizer.py` | M2-03/M2-04 Task Cards and tests | complete |
| Freshness and EvidencePolicy | `app/evidence/freshness.py`, `app/evidence/policy.py` | M2-05/M2-06 Task Cards and tests | complete with recorded limits |
| Citation and context budget | `app/evidence/citations.py`, `app/evidence/budget.py` | M2-07/M2-08 Task Cards and tests | complete |
| LangChain schema and chat orchestration | `app/answer`, `app/services/chat_service.py` | M3-00/M3-01 Task Cards and tests | complete |
| Process visibility UI | `app/ui`, `app/services/observability.py` | M3-15/B7/B8 Task Cards and tests | complete |
| Golden quality and observability | `scripts/m3_gate.py`, B8 files | M3 Gate `34/34`, Critical `17/17`, exposure `0` | complete at B8 closure |
| CI and clean container foundation | CI workflow, Dockerfile, Compose | B9-A local checks plus PR/main CI | complete |
| Recorded release runtime | `app/runtime.py`, `app/services/demo_source_gateway.py`, `data/demo` | B9 unit/integration, clean Docker health, and 7-scenario release smoke | local PASS |
| Remote recorded deployment | manual GCE workflow | remote health, smoke, and rollback | NOT_RUN |
| M4 Gate | B9 release evidence | independent review | NOT_RUN |

## Safety Controls

| Control | Evidence |
|---|---|
| wrong-company exclusion | hard-filter tests and B9 wrong-company scenario |
| prohibited direct advice | QueryPlanner, answer validation, golden Critical cases, B9 blocked scenario |
| no invented citation locator | citation validation and verified receipt-only B9 disclosure |
| no secret or local path exposure | secret scanner, public payload tests, release asset scan |
| deterministic basis date | recorded manifest, runtime clock injection, API/UI integration tests |
| caller mutation isolation | gateway/runtime unit tests |
| no silent live fallback | explicit `unconfigured` and `recorded` mode tests |
| no automatic production deploy | manual-only GCE workflow |

## Open Closure Items

- exact B9 release-candidate SHA and image identifier
- release-candidate GitHub `quality-gate`
- separately approved GCE deployment and external UI smoke
- rollback evidence
- B9 independent implementation review
- M4 Gate independent review
- Human Owner three-minute flow confirmation

Until those items are observed, B9 and M4 are not complete.
