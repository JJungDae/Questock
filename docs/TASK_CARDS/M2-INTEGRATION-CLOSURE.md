# TASK CARD - M2 Integration Closure

## 1. Status

- Task: `M2 Gate persistent integration phase slice`
- Priority: `P0 closure`
- Date: `2026-07-24`
- Branch: `main`
- Base SHA: `d5f564daebded7f47339c02d2f6b7a3a54e1ee90`
- Base commit: `Record m2-08 sync push`
- Base `origin/main`: `d5f564daebded7f47339c02d2f6b7a3a54e1ee90`
- Working tree before implementation: `clean`
- M2 individual capability: `PASS`
- M2 independent regression: `PASS`
- M2 integration fix: `IMPLEMENTED LOCALLY`
- M2 Gate: `CONDITIONAL PASS`
- M2 Gate closure: `USER/INDEPENDENT REVIEW PENDING`
- M3 implementation: `BLOCKED pending closure review PASS`
- Closure review: `PENDING`
- Commit/push: `NOT_RUN - separate approval required`

`PASS` is not recorded for the integrated closure until the implementation is
pushed and the user or an independent reviewer approves it.

## 2. Purpose And Blocker

`docs/agent_handoff/PROJECT_PLAN_FINAL_PASS.md` requires this M2 Gate evidence:

```text
actual retrieval
-> Evidence
-> minimal fixed response phase slice
```

M2-01 through M2-08 have approved isolated capabilities and composition tests,
but the prior read-only review found no single persistent test that called the
complete public M2 chain and returned a minimal `FinancialAnswer`.

Classification: `PLAN-VIOLATION`

This task adds only the missing integration evidence. It does not add production
orchestration or new application behavior.

## 3. Scope

Allowed:

- `tests/integration/test_m2_phase_slice.py`
- `docs/TASK_CARDS/M2-INTEGRATION-CLOSURE.md`
- `docs/TASK_CARDS/M2-08-context-budget.md` only after implementation review,
  and only for the status wording authorized by the instruction

Not allowed and unchanged:

- `app/**`
- `tests/unit/**`
- `scripts/**`
- `data/**`
- fixtures, providers, dependencies, lock files, and workflows
- M2-01 through M2-07 Task Cards
- M1-09 Task Card
- M2-09, M3, API, UI, LLM, LangChain, and deployment code

## 4. Public Phase Slice

The persistent test calls the current public boundaries in this order:

```text
raw query
-> QueryPlanner.plan
-> RetrievalRequest
-> normalize_financial_documents
-> filter_evidence with documents_by_id
-> evaluate_freshness
-> retrieve_evidence
-> EvidencePolicy.evaluate
-> select_evidence_context
-> CitationClaim from selected Evidence
-> validate_citations
-> FinancialAnswer
```

The test uses in-memory `FinancialDocument` fixtures, a typed
`create_provider_result()` result, and a fixed timezone-aware UTC basis. It does
not monkeypatch any M2 stage and does not replace planner, retrieval, policy, or
other stage output with a fake.

The minimal response is test-local:

- `complete` or `partial`: first retained Evidence snippet
- `no_evidence`: `답변에 사용할 근거를 확인하지 못했습니다.`
- `provider_failed`: `자료 제공 오류로 답변을 보류합니다.`
- `blocked`: `안전 정책에 따라 이 요청에는 답변할 수 없습니다.`

No LLM, prompt, `AnswerComposer`, or new response model is used.

## 5. Integration Cases

- IT-01: recent-news complete path
  - wrong-company Evidence removed by hard filter
  - 31-day-old news removed by freshness
  - current target Evidence retrieved, selected, cited, and returned
- IT-02: structurally valid but lexically irrelevant news
  - retrieval `low_relevance`
  - decision `no_evidence`
  - empty citations and fixed abstention response
- IT-03: provider timeout with no usable Evidence
  - decision remains `provider_failed`
  - fixed safe response
  - raw provider message, secret sentinel, and local path are not exposed
- IT-04: four relevant news Evidence items
  - policy retains all four
  - M2-08 source cap retains the first three
  - citation references only retained Evidence
  - a removed ID is `unknown_evidence`
- IT-05: repeated execution
  - equal answer JSON, citation result, and budget diagnostics
  - original documents, request, intermediate models, and nested locators are
    not mutated
  - returned nested Evidence is isolated by deep copy

## 6. Preflight Results

Git:

- `git status --short`: `PASS - exit 0 - clean`
- `git branch --show-current`: `PASS - exit 0 - main`
- `git rev-parse HEAD`: `PASS - exit 0 - base SHA matched`
- `git rev-parse origin/main`: `PASS - exit 0 - base SHA matched`
- `git log -3 --oneline --decorate`: `PASS - expected latest commit`

Environment:

- Python: `PASS - exit 0 - Python 3.14.3`
- pytest: `PASS - exit 0 - pytest 8.4.2`
- ZoneInfo Asia/Seoul: `PASS - exit 0`

Regression:

- M2 targeted:
  `PASS - exit 0 - 654 passed, 1 PytestCacheWarning`
- Full unit first sandbox run:
  `ENVIRONMENT FAILURE - exit 1 - 1312 passed, 103 setup errors,
  3 warnings; pytest Temp directory PermissionError; 0 assertion failures`
- Full unit approved local rerun:
  `PASS - exit 0 - 1415 passed, 1 existing StarletteDeprecationWarning`

No dependency or environment change was made.

## 7. Verification Commands

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
git diff --stat
git status --short
```

## 8. Implementation Results

- Changed files:
  - `A tests/integration/test_m2_phase_slice.py`
  - `A docs/TASK_CARDS/M2-INTEGRATION-CLOSURE.md`
- Targeted integration:
  `PASS - exit 0 - 5 passed, 1 PytestCacheWarning`
- M2 unit plus integration:
  `PASS - exit 0 - 659 passed, 1 PytestCacheWarning`
- Full tests first sandbox run:
  `ENVIRONMENT FAILURE - exit 1 - 1317 passed, 103 setup errors,
  3 warnings; pytest Temp directory PermissionError; 0 assertion failures`
- Full tests approved local rerun:
  `PASS - exit 0 - 1420 passed,
  1 existing StarletteDeprecationWarning`
- Public import smoke:
  `PASS - exit 0 - m2-phase-slice-import-ok`
- Secret scan: `PASS - exit 0 - []`
- Compile: `PASS - exit 0`
- Diff check: `PASS - exit 0 - no whitespace errors`
- Working tree after:
  `only the two approved untracked files; no tracked file changes`
- App code changes: `none`
- Dependency changes: `none`
- M2 integration fix: `IMPLEMENTED LOCALLY`
- M2 Gate closure: `USER/INDEPENDENT REVIEW PENDING`
- M3 implementation: `BLOCKED pending closure review PASS`
- GitHub CI: `NOT_RUN`
- Independent pytest rerun: `NOT_RUN`

## 9. Deferred And Not Run

- live provider and live URL: `NOT_RUN`
- production orchestration: `NOT_IMPLEMENTED`
- API/UI: `NOT_STARTED`
- LLM/LangChain: `NOT_STARTED`
- M2-09: `NOT_STARTED / not required`
- M3: `BLOCKED`
- PR/merge/deploy: `NOT_RUN`
- commit/push: `NOT_RUN`
