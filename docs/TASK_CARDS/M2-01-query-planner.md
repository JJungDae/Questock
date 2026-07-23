# TASK CARD - M2-01 QueryPlanner

## 1. Status and Approval

- Task bundle: `B4: M2-01~03`
- Step: `M2-01 QueryPlanner`
- Planning date: `2026-07-22`
- Planning base branch: `main`
- Planning base commit: `4c7b2d58e11f7e9b83b48614aa271a277ad26d37`
- M1 core gate status: `PASS`
- M1-09 GitHub-recorded status: `mandatory supplement implemented - final independent review pending`
- M1-09 provider completion: `pending final PASS`
- M1-09 recorded gate decision: `A15-M remains a data-qualified stretch candidate`
- M2-01 dependency on M1-09: `NONE - price_move_reason remains inactive`
- Current status: `PASS / complete`
- Implementation approval: `APPROVED for the corrected M2-01 implementation and tests`
- Initial implementation SHA: `1192fcd769b43b7c72e23b2095cbe7f58861b2c4`
- Initial implementation commit: `Implement m2-01`
- Initial implementation main push: `complete`
- Initial independent review: `CONDITIONAL PASS`
- Supplement implementation: `PASS in local implementation environment`
- Supplement SHA: `a11a539da93226338662996da0cd933c7221bab7`
- Supplement main push: `complete`
- Final closure fix SHA: `5ffef6ca47c1ad8961bd717bb5623742bab8ddcb`
- Final closure fix commit: `m2-01 conditional pass2 updates`
- Final closure fix main push: `complete`
- Final closure review: `PASS WITH REQUIRED FOLLOW-UP`
- Final preflight verification: `PASS`
- M2-02 planning entry: `ALLOWED`
- M2-02 implementation entry: `ALLOWED`
- Commit/push/PR/merge/deploy: `NOT_APPROVED`
- GitHub CI: `NOT_RUN`
- Independent pytest rerun: `NOT_RUN`
- Live API/LLM/retrieval/API/UI work: `OUT_OF_SCOPE`
- Stretch `price_move_reason`: `NOT_ACTIVATED - M2-09/M3-12 separate approval required`

This Task Card authorizes only the corrected M2-01 implementation and its local tests. Commit, push, PR, merge, deploy, live API calls, retrieval implementation, API/UI work, and LLM work remain separate approval actions.

M1-09 closure is not a prerequisite for this Task because M2-01 must return a blocked `out_of_scope` plan for price-move questions and must not call the market provider.

## 2. Goal and Boundary

M2-01 implements a deterministic, rule-based query planner that maps a user question to the existing `QueryPlan` model.

It decides:

- one resolved explicit or session-filled `SecurityIdentifier`
- one fixed P0 intent
- `DateRange` only for a supported deterministic period
- required source types
- required evidence categories
- whether clarification is required

M2-01 does not retrieve documents, rank documents, create `Evidence`, call providers, call an LLM, answer the user, or activate a price-move workflow.

P0 remains single-security. A query that explicitly names multiple supported securities or requests a direct comparison/ranking must not select the first match.

## 3. Existing Verified Inputs

Use, do not redesign:

- `QueryPlan`, `DateRange`, `SecurityIdentifier`, and `SessionContext` in `app/core/models.py`
- `SecurityResolver`, `ResolutionResult`, `FixtureValidationError`, `security_id_for()`, and `ResolutionStatus`
- existing source type strings: `news`, `disclosure`, `research_report`, `glossary`
- B0 intent list:
  - `recent_issue`
  - `disclosure_summary`
  - `research_report_summary`
  - `risk_factors`
  - `financial_term`
  - `multi_source_summary`
  - conditional `price_move_reason`
- current P0 supported securities:
  - 삼성전자
  - SK하이닉스
  - 현대자동차
- M1 provider/corpus outputs remain fixture-backed and are not invoked in M2-01

Do not access `SecurityResolver` private indexes or duplicate `data/securities.json` as a second canonical registry.

## 4. Fixed Scope

### Required

- Rule-based `QueryPlanner`
- Deterministic query normalization using NFKC, whitespace collapse, and casefold-style matching
- Explicit processing precedence for blank, prohibited advice, inactive price-move, supported intent, date, and security
- Security mention extraction from a full user question through the public `SecurityResolver.resolve()` boundary
- Longest valid mention wins over a nested ambiguous subterm belonging to the same mention
- Multiple or conflicting explicit security mentions must not first-match
- Explicit supported security wins over session context
- Session `current_security_id` is used only for security-required intents and only when the query has no explicit security mention
- Ambiguous, unsupported, missing, multiple, and conflicting security cases return a non-retrievable clarification plan
- Fixed intent precedence and exact required source/evidence mapping
- Prohibited advice detection before ordinary intent routing
- Conditional `price_move_reason` remains blocked as exact `out_of_scope`
- Deterministic date parsing with explicit session-fallback suppression rules
- No query rewrite that changes user intent
- No LLM planner

### Out of Scope

- M2-02 hard filter
- M2-03 retrieval baseline
- Evidence normalization
- EvidencePolicy
- freshness/staleness warnings and source-specific default lookback windows
- citation validation
- token/context budget
- market-session temporal filter
- provider calls
- live API calls
- API/UI changes
- LLM, Gemini, LiteLLM
- new dependencies
- changing existing core model fields or status enums
- modifying the canonical security registry or resolver contract
- multi-security comparison, ranking, or joint analysis

## 5. Planned Files

### New files

- `app/planning/__init__.py`
- `app/planning/query_planner.py`
- `tests/unit/test_query_planner.py`

### Modified files

- `docs/TASK_CARDS/M2-01-query-planner.md`

### Do not modify

- `app/core/models.py`
- `app/core/status.py`
- `app/core/resolver.py`
- `app/providers/**`
- `app/ingest/**`
- `app/phase_slice.py`
- `data/securities.json`
- existing provider/report/news/disclosure/glossary fixtures
- API/UI/LLM/retrieval files

## 6. Contract

### 6.1 Public API and Constructor Contract

Implementation shape:

```python
class QueryPlanner:
    def __init__(
        self,
        resolver: SecurityResolver | None = None,
        *,
        basis_date: date | None = None,
    ) -> None:
        ...

    def plan(
        self,
        query: str,
        *,
        session: SessionContext | None = None,
    ) -> QueryPlan:
        ...
```

Rules:

- omitted `resolver` and explicit `resolver=None` both construct one default `SecurityResolver` during planner construction
- an injected resolver is reused and is not replaced or mutated
- the default resolver is not reconstructed on each `plan()` call
- omitted `basis_date` and explicit `basis_date=None` capture `date.today()` once during planner construction
- injected `basis_date` is used unchanged for deterministic tests
- non-`date` non-`None` `basis_date` raises `TypeError` with a fixed sanitized message
- non-string `query` raises `TypeError` with a fixed sanitized message and does not call the resolver
- non-`SessionContext` non-`None` `session` raises `TypeError` with a fixed sanitized message and does not call the resolver
- empty or whitespace-only query returns the fixed empty-query plan defined below
- raw query text is not rewritten into a different search meaning
- normalization is used only for matching
- every call returns a new `QueryPlan` and fresh source/evidence lists
- the planner must not mutate the supplied `SessionContext`, `DateRange`, or resolver
- resolver construction or resolver execution errors must not be converted into a successful or clarification `QueryPlan`; no `QueryPlan` is returned for an internal resolver failure
- raw exception text, fixture paths, or registry contents must never be copied into a `QueryPlan`
- no diagnostics, metadata, candidates, or new model fields are added to `QueryPlan`

### 6.2 Overall Processing Order

The planner must apply this order:

```text
query/session type validation
→ blank-query check
→ normalization for matching only
→ prohibited-advice detection
→ inactive price_move_reason detection
→ supported P0 intent classification
→ unsupported-intent return
→ deterministic period parsing / period-cue detection
→ explicit security mention extraction and resolution
→ session security fallback for security-required intent only
→ session date fallback when allowed
→ exact source/evidence mapping
→ QueryPlan construction
```

Early-return invariants:

- blank, prohibited-advice, inactive price-move, and unsupported-intent paths do not call `resolver.resolve()`
- these paths do not call providers, corpus loaders, retrieval, API, or LLM boundaries
- security clarification paths do not populate required sources or required evidence

### 6.3 Fixed Output Invariants

| case | security | intent | date_range | required_sources | required_evidence | requires_clarification |
|---|---|---|---|---|---|---|
| empty/blank query | `None` | `out_of_scope` | `None` | `[]` | `[]` | `True` |
| prohibited advice or future price prediction | `None` | `prohibited_advice` | `None` | `[]` | `[]` | `True` |
| inactive price-move reason | `None` | `out_of_scope` | `None` | `[]` | `[]` | `True` |
| unsupported intent | `None` | `out_of_scope` | `None` | `[]` | `[]` | `True` |
| multiple supported securities or direct comparison/ranking | `None` | `out_of_scope` | parsed date or `None` | `[]` | `[]` | `True` |
| ambiguous/unsupported/conflicting/missing security for a supported intent | `None` | detected supported intent | parsed/fallback date or `None` | `[]` | `[]` | `True` |
| successful supported intent | resolved security or allowed `None` | detected supported intent | parsed/fallback date or `None` | exact matrix copy | exact matrix copy | `False` |

A plan with `requires_clarification=True` must never contain non-empty `required_sources` or `required_evidence`.

### 6.4 Security Mention and Session Contract

#### Explicit mention extraction

- extract candidate phrases from the normalized full question by punctuation/whitespace token spans
- evaluate contiguous spans longest-first through `SecurityResolver.resolve()`
- allow deterministic stripping of these Korean edge particles for candidate lookup only: `은`, `는`, `이`, `가`, `을`, `를`, `의`, `에서`
- preserve the original query; stripping is not a query rewrite
- support canonical name, 6-digit ticker, `security_id`, and approved aliases
- multi-token English aliases such as `Samsung Electronics` and `SK hynix` must resolve
- ordinary lowercase English words such as `news`, `report`, and `risk` must not be treated as foreign ticker mentions
- an uppercase 1-5 letter standalone token may be evaluated as a foreign/unsupported ticker through the existing resolver rule
- do not inspect resolver private indexes and do not read the registry separately

#### Longest-match and conflict rules

- a resolved longer span suppresses an ambiguous or unsupported strict subspan contained inside the same character range
- example: `SK하이닉스` or `SK 하이닉스` resolves to SK하이닉스 and must not be blocked by nested `SK`
- one explicit supported security plus a different explicit ambiguous/unsupported security-like term is a conflicting query and requires clarification
- two or more distinct supported `security_id` values return the fixed multi-security `out_of_scope` plan
- direct comparison, superiority, ranking, or joint analysis wording with more than one named security is out of P0
- never choose the first match

#### Session rules

- one explicit supported security overrides `session.current_security_id`
- explicit ambiguous, unsupported, multiple, or conflicting mentions must not fall back to session security
- session security fallback is used only for these security-required intents:
  - `recent_issue`
  - `disclosure_summary`
  - `research_report_summary`
  - `risk_factors`
  - `multi_source_summary`
- `financial_term` does not inherit session security; it may have `security=None`
- a valid explicit security in a `financial_term` query may be preserved, but it does not change glossary routing
- invalid/unresolvable session security causes clarification only for a security-required intent
- an invalid session security is ignored for `financial_term`
- resolver errors are propagated as internal failures and are not swallowed as a valid or clarification plan

### 6.5 Intent Classification and Precedence

Intent detection is deterministic. Fixed precedence:

```text
prohibited_advice
→ inactive price_move_reason
→ financial_term
→ risk_factors
→ multi_source_summary
→ disclosure_summary
→ research_report_summary
→ recent_issue
→ out_of_scope
```

Minimum fixed trigger contract:

| intent | required matching condition |
|---|---|
| `prohibited_advice` | direct buy/sell/hold recommendation, target price, stop-loss/take-profit timing, guaranteed return, or future direction/probability request such as `내일 오를까`, `상승 확률`, `목표가`, `사도 돼`, `팔아야` |
| inactive `price_move_reason` | present/past reason wording such as `왜 올랐`, `왜 내렸`, `왜 떨어졌`, `상승 이유`, `하락 이유`; it returns exact `out_of_scope` until separate activation |
| `financial_term` | a definition cue such as `뭐야`, `무슨 뜻`, `정의`, `용어 설명` together with an approved P0 financial-term marker |
| `risk_factors` | `위험`, `위험 요인`, `리스크`, `우려`, `악재` |
| `multi_source_summary` | explicit multi-source/combined cue such as `종합`, `여러 자료`, `뉴스와 공시`, `전체 자료`, `한번에 요약` |
| `disclosure_summary` | `공시`, `정정공시`, `사업보고서`, `반기보고서`, `분기보고서` |
| `research_report_summary` | `리서치`, `증권사 리포트`, `애널리스트 리포트`, `리포트 요약`, `투자의견 보고서` |
| `recent_issue` | `최근 이슈`, `최근 뉴스`, `뉴스 이슈`, `주요 이슈` |

Approved P0 financial-term routing markers include at least:

```text
PER, PBR, ROE, EPS, 시가총액, 매출, 영업이익, 순이익,
영업이익률, 유상증자, 전환사채, 공시, 컨센서스,
연결재무제표, 별도재무제표
```

The marker set is only a routing vocabulary and must not contain glossary definitions. Future marker additions require synchronized tests.

Collision examples:

- `유상증자가 뭐야?` → `financial_term`
- `삼성전자 최근 공시 위험 알려줘` → `risk_factors`
- `삼성전자 뉴스와 공시를 종합해줘` → `multi_source_summary`
- `삼성전자 내일 오를까?` → `prohibited_advice`
- `삼성전자 오늘 왜 올랐어?` → `out_of_scope` until price-move activation
- `삼성전자 알려줘` → `out_of_scope`

### 6.6 Exact Intent, Source, and Evidence Matrix

The following strings and list order are fixed:

| intent | required_sources | required_evidence | security |
|---|---|---|---|
| `financial_term` | `['glossary']` | `['definition']` | optional; no session fallback |
| `disclosure_summary` | `['disclosure']` | `['disclosure']` | required |
| `research_report_summary` | `['research_report']` | `['research_report']` | required |
| `recent_issue` | `['news']` | `['recent_news']` | required |
| `risk_factors` | `['news', 'disclosure', 'research_report']` | `['risk', 'recent_news', 'disclosure', 'research_report']` | required |
| `multi_source_summary` | `['news', 'disclosure', 'research_report']` | `['recent_news', 'disclosure', 'research_report']` | required |
| `prohibited_advice` | `[]` | `[]` | not resolved |
| `out_of_scope` | `[]` | `[]` | not resolved |

Do not use parallel synonyms such as `filing` for `disclosure` or `report` for `research_report` in `required_evidence`.

### 6.7 Period and Session Date Rules

M2-01 supports only:

- explicit ISO date `YYYY-MM-DD` → inclusive one-day `DateRange`
- simple inclusive range `YYYY-MM-DD ~ YYYY-MM-DD`, allowing surrounding whitespace
- `오늘` → `DateRange(start=basis_date, end=basis_date)`

Rules:

- a valid explicit period overrides `session.current_date_range`
- an ISO-like but invalid date, invalid calendar date, reversed range, or multiple conflicting explicit ranges produces `date_range=None` without raising from `plan()`
- any explicit but invalid period cue suppresses session date fallback; do not silently reuse an old period
- `최근` is a vague period cue in M2-01: leave `date_range=None` and suppress session date fallback
- source-specific recent defaults such as 30 or 180 days belong to M2-05, not M2-01
- session date fallback is allowed only when:
  - the intent is a normal date-aware supported intent
  - the query has no explicit valid, invalid, or vague period cue
  - `session.current_date_range` is present
- `financial_term`, prohibited, inactive price-move, and out-of-scope plans do not inherit session date
- the supplied session `DateRange` is not mutated

### 6.8 Clarification and Non-Retrieval Rules

`requires_clarification=True` when:

- query is empty
- required security is missing
- security is ambiguous
- security is unsupported
- explicit security mentions conflict
- more than one supported security is named
- direct comparison/ranking is requested
- question is out of current scope
- direct investment advice or future price prediction is requested
- inactive `price_move_reason` is requested

For every clarification plan:

- `required_sources=[]`
- `required_evidence=[]`
- no provider, corpus, retrieval, API, or LLM boundary is called

## 7. Tests

Create `tests/unit/test_query_planner.py` with exact assertions rather than open alternatives.

### 7.1 Constructor, input, mutation, and repeatability

- omitted resolver and explicit `None` use one default resolver per planner instance
- injected resolver is reused
- omitted/explicit-`None` basis date captures one construction date
- injected basis date drives `오늘`
- invalid basis date type raises fixed `TypeError`
- non-string query raises fixed `TypeError` before resolver use
- invalid session type raises fixed `TypeError` before resolver use
- repeated identical calls return equal plans
- returned source/evidence lists are fresh and mutation of one result does not affect another
- planner does not mutate `SessionContext` or its `DateRange`
- resolver exception does not return a `QueryPlan`

### 7.2 Processing precedence and early return

Use an injected spy resolver and assert no `resolve()` call for:

- empty/blank query
- prohibited advice
- inactive price-move reason
- unsupported intent

Assert exact full `QueryPlan` values for each path.

### 7.3 Security resolution

- canonical name in a full sentence
- canonical name with Korean particle, such as `삼성전자의 최근 이슈`
- ticker in a full sentence
- `security_id` in a full sentence
- approved Korean alias
- approved multi-token English alias
- repeated whitespace/NFKC normalization
- explicit security overrides session security
- session security fills only a security-required intent
- financial-term query does not inherit session security
- nested `SK` does not block `SK하이닉스`
- ordinary lowercase English words do not become unsupported tickers
- ambiguous `삼성`, `SK`, `현대` requires clarification
- unsupported/preferred-stock input requires clarification
- supported plus conflicting unsupported/ambiguous mention requires clarification
- two supported securities do not first-match and return exact multi-security `out_of_scope`
- direct comparison/ranking returns exact multi-security `out_of_scope`
- invalid session security clarifies a security-required intent
- invalid session security is ignored for `financial_term`
- missing security for a security-required intent clarifies

### 7.4 Intent and exact matrix

- one positive fixture for every supported intent
- collision/precedence fixtures listed in section 6.5
- direct buy/sell/hold/target-price/future-probability requests route to `prohibited_advice`
- benign historical probability wording that is not a direct investment/future-price request is not prohibited solely because it contains `확률`
- price-move reason always returns exact `out_of_scope` before M2-09 approval
- unsupported question returns exact `out_of_scope`
- all successful plans assert exact source list, evidence list, order, and clarification flag
- all clarification plans assert empty source/evidence lists

### 7.5 Period handling

- explicit ISO one-day date
- valid inclusive range with and without spaces around `~`
- `오늘` with injected basis date
- explicit valid period overrides session period
- no period cue uses session fallback for date-aware intent
- `최근` returns `None` and suppresses session fallback
- invalid calendar date returns `None` and suppresses session fallback
- reversed range returns `None` and suppresses session fallback
- multiple conflicting ranges return `None` and suppress session fallback
- financial term does not inherit session date

### 7.6 Boundary and regression

- planner does not import or call provider, ingest, retrieval, API, UI, or LLM boundaries
- `QueryPlan` model fields remain unchanged
- `SecurityResolver` public behavior remains unchanged

Targeted:

```powershell
$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_query_planner.py -q
```

Full unit regression:

```powershell
$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit -q
```

Import smoke:

```powershell
$env:PYTHONPATH = ".deps;."; python -c "from app.planning.query_planner import QueryPlanner; print('ok')"
```

Secret scan and compile:

```powershell
python scripts/secret_scan.py
python -m compileall app tests scripts -q
```

If the full unit command includes an unrelated pre-existing failure, stop and record the exact failing test and baseline evidence. Do not mark regression PASS.

## 8. Completion Criteria

- [x] `QueryPlanner` implemented in approved files only
- [x] existing `QueryPlan` model reused without field changes
- [x] public constructor/input/error contract passes
- [x] fixed processing order and early returns pass
- [x] supported full-question security mention resolution passes
- [x] nested ambiguity, multiple security, conflict, and session rules pass
- [x] fixed intent precedence passes
- [x] exact source/evidence vocabulary and order pass
- [x] clarification plans cannot route to retrieval
- [x] prohibited advice and future prediction do not route to normal retrieval
- [x] `price_move_reason` returns exact inactive `out_of_scope`
- [x] deterministic date parsing and session suppression rules pass
- [x] no provider/retrieval/API/UI/LLM calls
- [x] targeted tests pass
- [x] full unit regression passes or an unrelated baseline failure is accurately recorded
- [x] import smoke passes
- [x] secret scan passes
- [x] compile passes
- [x] actual test commands, exit codes, and counts are recorded
- [x] implementation result log and Git status are accurate

## 9. Risk IDs and Taxonomy

Risk IDs:

- `R22` ambiguous company selection
- `R24` wrong intent routing
- `R27` query rewrite changes intent
- `R28` retrieval complexity creep
- `R38` direct investment advice

Related taxonomy:

- `entity_resolution`
- `ambiguous_security`
- `intent_routing`
- `source_selection`
- `multi_turn`
- `prohibited_advice`

## 10. Stop Conditions

Stop and report if:

- implementation requires changing existing core model fields or status enums
- safe full-question security extraction cannot be implemented through the existing public resolver boundary
- implementation would require resolver private indexes or a second canonical registry
- planner needs provider/retrieval/API/UI/LLM code
- multiple security handling cannot be represented by the fixed clarification/out-of-scope contract
- source routing needs live API/corpus calls
- date parsing grows beyond the deterministic rules in this Task
- a new dependency appears necessary
- `price_move_reason` activation is requested without separate M2-09 approval
- unrelated regression fails
- implementation would add an unapproved intent or evidence vocabulary

## 11. Fallback and Rollback

- If a safe mention extractor cannot satisfy the approved fixtures without private resolver access, stop M2-01 and request a separate resolver public-boundary plan. Do not duplicate registry content.
- If an intent phrase is not covered by the fixed rules, return `out_of_scope`; do not guess with a broad fallback.
- If period parsing is uncertain, return `date_range=None` and suppress unsafe session fallback when a period cue was present.
- Rollback is a normal reverse patch limited to the approved M2-01 files.
- Do not use reset, force push, clean, checkout-based destruction, or delete unrelated files.

## 12. Implementation Order After Approval

1. Add `app/planning` package.
2. Implement fixed constants, normalization, and immutable routing tables.
3. Implement input validation and early-return precedence.
4. Implement deterministic period cue/parser helpers.
5. Implement public-resolver-based mention candidate extraction and conflict handling.
6. Implement session fallback rules.
7. Construct fresh `QueryPlan` outputs using exact matrix copies.
8. Add targeted unit tests in the same order as the contract.
9. Run targeted tests.
10. Run full unit regression.
11. Run import smoke, secret scan, and compile.
12. Record actual results and Git status in this Task Card.
13. Report diff and results.
14. Wait for separate commit/push approval.

## 13. Implementation Review Checklist

The implementation review must confirm:

- base commit and changed files
- no changes outside approved files
- no resolver private-index access or duplicated registry
- exact early-return precedence
- exact blocked-plan values
- longest-match and multiple-security behavior
- explicit security/session precedence
- financial-term session isolation
- exact source/evidence vocabulary and order
- `최근` and invalid-period session suppression
- fresh result lists and no caller mutation
- resolver/internal errors do not become valid plans
- targeted, full regression, smoke, secret scan, and compile records
- Task Card, commit, push, CI, and independent rerun statuses match reality

## 14. Initial Implementation Result Log

- Implementation status: `initial implementation pushed - independent review CONDITIONAL PASS`
- Initial implementation SHA: `1192fcd769b43b7c72e23b2095cbe7f58861b2c4`
- Initial implementation commit: `Implement m2-01`
- Initial implementation main push: `complete`
- Initial independent review: `CONDITIONAL PASS`
- Supplement implementation: `PASS in local implementation environment`
- Supplement SHA: `a11a539da93226338662996da0cd933c7221bab7`
- Supplement main push: `complete`
- Final closure fix SHA: `5ffef6ca47c1ad8961bd717bb5623742bab8ddcb`
- Final closure fix commit: `m2-01 conditional pass2 updates`
- Final closure fix main push: `complete`
- Final closure review: `PASS WITH REQUIRED FOLLOW-UP`
- Final preflight verification: `PASS`
- M2-02 planning entry: `ALLOWED`
- M2-02 implementation entry: `ALLOWED`
- GitHub CI: `NOT_RUN`
- Independent pytest rerun: `NOT_RUN`
- Live API/LLM/retrieval/API/UI: `NOT_RUN`

### 14.1 Initial Changed Files

- `app/planning/__init__.py`
- `app/planning/query_planner.py`
- `tests/unit/test_query_planner.py`
- `docs/TASK_CARDS/M2-01-query-planner.md`
- `docs/TASK_CARDS/M1-09-market-snapshot-gate.md`

### 14.2 Implemented Scope

- Added deterministic rule-based `QueryPlanner`.
- Reused existing `QueryPlan`, `DateRange`, `SecurityIdentifier`, and `SessionContext` without model changes.
- Added public-resolver-based full-question security mention extraction.
- Added early-return handling for blank, prohibited advice, inactive price-move, and unsupported intent paths.
- Added exact intent/source/evidence matrix for M2-01.
- Added deterministic date parsing and session fallback suppression rules.
- Kept provider, ingest, retrieval, API, UI, LLM, live API, and new dependency work out of scope.

### 14.3 Initial Verification Results

- Targeted command: `$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_query_planner.py -q`
  - execution: approved elevated run
  - first result: exit code `1`, `46 passed`, `1 failed`
  - failure fixed: uppercase foreign ticker conflict detection after query normalization
  - rerun exit code: `0`
  - passed count: `47 passed`
- Full unit regression command: `$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit -q`
  - execution: approved elevated run
  - exit code: `0`
  - passed count: `808 passed`
  - warning: FastAPI TestClient emitted Starlette deprecation warning for `httpx`.
- Import smoke command: `$env:PYTHONPATH = ".deps;."; python -c "from app.planning.query_planner import QueryPlanner; print('ok')"`
  - execution: approved elevated run
  - exit code: `0`
  - output: `ok`
- Secret scan command: `python scripts/secret_scan.py`
  - exit code: `0`
  - output: `[]`
- Compile command: `python -m compileall app tests scripts -q`
  - exit code: `0`

## 15. Final Preflight Verification For M2-02

- Preflight baseline SHA: `5ffef6ca47c1ad8961bd717bb5623742bab8ddcb`
- Preflight baseline commit: `m2-01 conditional pass2 updates`
- M2-01 Task Card final synchronization: `PASS`
- M1-09 state: `mandatory supplement implemented - final independent review pending`
- M1-09 provider completion: `pending final PASS`
- GitHub CI: `NOT_RUN`
- Independent pytest rerun: `NOT_RUN`

### 15.1 Preflight Results

- M2-01 targeted command: `$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_query_planner.py -q`
  - execution: approved elevated run
  - exit code: `0`
  - passed count: `76 passed`
- Full unit regression command: `$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit -q`
  - execution: approved elevated run
  - exit code: `0`
  - passed count: `837 passed`
  - warning: FastAPI TestClient emitted Starlette deprecation warning for `httpx`.
- QueryPlanner import smoke command: `$env:PYTHONPATH = ".deps;."; python -c "from app.planning.query_planner import QueryPlanner; print('ok')"`
  - execution: approved elevated run
  - exit code: `0`
  - output: `ok`
- Secret scan command: `python scripts/secret_scan.py`
  - exit code: `0`
  - output: `[]`
- Compile command: `python -m compileall app tests scripts -q`
  - exit code: `0`

### 15.2 Final State

```text
M2-01 PASS / complete
final closure fix main push complete
final closure review PASS WITH REQUIRED FOLLOW-UP
final preflight verification PASS
M2-02 planning ALLOWED
M2-02 implementation ALLOWED
```

### 15.3 Git Status at Report Time

- `M docs/TASK_CARDS/M2-01-query-planner.md`
- `?? docs/TASK_CARDS/M2-02-hard-filter.md`

Supplement PR, merge, deploy, provider, retrieval, API, UI, LLM, and live API work remain `NOT_RUN`. M2-02 implementation is allowed because the M2-01 preflight gate passed.

## 16. Historical Supplement Result Log

- Supplement status: `PASS in local implementation environment`
- Supplement SHA: `a11a539da93226338662996da0cd933c7221bab7`
- Supplement main push: `complete`
- Final closure fix SHA: `5ffef6ca47c1ad8961bd717bb5623742bab8ddcb`
- Final closure fix commit: `m2-01 conditional pass2 updates`
- Final closure fix main push: `complete`
- Final closure review: `PASS WITH REQUIRED FOLLOW-UP`
- Final preflight verification: `PASS`
- M2-02 planning entry: `ALLOWED`
- M2-02 implementation entry: `ALLOWED`
- GitHub CI: `NOT_RUN`
- Independent pytest rerun: `NOT_RUN`
- Live API/LLM/retrieval/API/UI: `NOT_RUN`

### 16.1 Supplement Modified Files

- `app/planning/query_planner.py`
- `tests/unit/test_query_planner.py`
- `docs/TASK_CARDS/M2-01-query-planner.md`
- `docs/TASK_CARDS/M1-09-market-snapshot-gate.md`

### 16.2 Supplement Implemented Scope

- Narrowed prohibited-advice detection to direct buy/sell/hold, target-price request, stop-loss/take-profit, guaranteed return, and future direction/probability requests.
- Preserved normal routing for benign disclosure and research report phrases containing hold, tomorrow, buy opinion, or target-price report wording.
- Split casefolded intent matching from case-preserving security candidate extraction.
- Kept uppercase standalone foreign ticker conflict detection while ignoring ordinary lowercase English words such as `stock`, `brief`, and lowercase `aapl`.
- Added financial-term routing markers for `순이익` and `영업이익률`.
- Reworked period parsing to collect ISO range/date, today, recent, malformed, and conflicting cues before applying session fallback.
- Did not implement provider, ingest, retrieval, API, UI, LLM, dependency, or M2-02 work.

### 16.3 Supplement Verification Results

- Targeted first command: `$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_query_planner.py -q`
  - execution: sandboxed run
  - exit code: `1`
  - output: `No module named pytest.__main__; 'pytest' is a package and cannot be directly executed`
- Targeted second command: `$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_query_planner.py -q`
  - execution: approved elevated run
  - exit code: `1`
  - result: `69 passed`, `3 failed`
  - failure fixed: P0 glossary acronyms `PER`, `PBR`, `ROE`, and `EPS` were being treated as uppercase foreign ticker candidates.
- Targeted rerun command: `$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_query_planner.py -q`
  - execution: approved elevated run
  - exit code: `0`
  - passed count: `72 passed`
- Full unit regression command: `$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit -q`
  - execution: approved elevated run
  - exit code: `0`
  - passed count: `833 passed`
  - warning: FastAPI TestClient emitted Starlette deprecation warning for `httpx`.
- Import smoke command: `$env:PYTHONPATH = ".deps;."; python -c "from app.planning.query_planner import QueryPlanner; print('ok')"`
  - execution: approved elevated run
  - exit code: `0`
  - output: `ok`
- Secret scan command: `python scripts/secret_scan.py`
  - exit code: `0`
  - output: `[]`
- Compile command: `python -m compileall app tests scripts -q`
  - exit code: `0`
