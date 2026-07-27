# TASK CARD - First Service Completion

## 1. Status and Approval

- Project: `Questock`
- Repository: `JJungDae/Questock`
- Planning base branch: `main`
- Planning base SHA:
  `da03a6fb3be5c985cef7d5d1f0523827340fe088`
- Working branch:
  `docs/fsc-service-completion-closure`
- Priority: `P0 service completion`
- Current official bundle:
  `First Service Completion`
- M4 Gate:
  `PASS`
- FSC-0:
  `PASS / complete - Human Owner confirmed 2026-07-27`
- FSC-1:
  `PASS / complete - SC-01~04 complete; Human Owner requested closure 2026-07-27`
- FSC-2:
  `PASS / complete - Human Owner confirmed 2026-07-27`
- FSC-3:
  `PASS / complete - SC-06 and SC-07 local/remote closure complete`
- Service Completion Gate:
  `PASS / complete`
- A15-M:
  `activation check READY / implementation NOT_STARTED`
- M1-09:
  `mandatory supplement implemented - final independent review pending`
- Commit/push/PR/merge/deploy:
  `release PR #11 and #12 merged; exact-SHA GCE deploy complete`

## 2. Normative Sources

Read in this order:

1. `docs/agent_handoff/SOURCE_OF_TRUTH_INDEX.md`
2. `docs/agent_handoff/README_AGENT_RULES.md`
3. `docs/agent_handoff/PROJECT_PLAN_FINAL_PASS.md`
4. `docs/agent_handoff/PROJECT_PLAN_FINAL_PASS_POST_M3_01_ADDENDUM.md`
5. `docs/agent_handoff/POST_M3_01_EXECUTION_FLOW_DECISION_2026-07-25.md`
6. `docs/agent_handoff/FIRST_SERVICE_COMPLETION_EXECUTION_DECISION_2026-07-27.md`
7. `docs/agent_handoff/AGENT_WORKFLOW.md`
8. `docs/agent_handoff/AGENT_WORKFLOW_POST_M3_01_ADDENDUM.md`
9. this Task Card
10. current code, data contracts, tests, and release assets

External planning inputs:

- `QUESTOCK_FIRST_SERVICE_COMPLETION_BASELINE.md`
- `QUESTOCK_FIRST_SERVICE_COMPLETION_IMPLEMENTATION_PLAN_REVISED_V4.md`

The external planning files are inputs, not repository source-of-truth paths.
The execution decision and this Task Card make the approved FSC flow
repository-visible.

## 3. Goal

Complete the current MVP as a public first service before starting A15-M:

```text
Samsung Electronics, SK hynix, and Hyundai Motor
-> one immutable 2026-07-24 14:02 KST service snapshot
-> verified news, disclosure, and research-report evidence
-> Gemini 3.5 Flash generation or existing safe fallback
-> bounded request, session, and cache behavior
-> public UI and exact-SHA GCE release
```

This bundle preserves the existing financial reasoning, Evidence, freshness,
policy, citation, validation, safety, and public response contracts.

## 4. Bundle Boundaries

| Bundle | Checkpoints | Scope | Current status |
|---|---|---|---|
| `FSC-0` | `SC-00` | official flow, credential/API/source preflight | `PASS / complete` |
| `FSC-1` | `SC-01~04` | 3-company source work and immutable snapshot runtime | `PASS / complete` |
| `FSC-2` | `SC-05` | Gemini, model allowlist, request protection, session/cache | `PASS / complete` |
| `FSC-3` | `SC-06~07` | UI, 3-company E2E, CI/GCE release | `PASS / complete - local and remote closure complete` |

Bundle order is strict. A later bundle does not start from this Task Card
without the previous result confirmation and its own preflight.

## 5. FSC-0 Scope

Allowed files:

- `docs/agent_handoff/FIRST_SERVICE_COMPLETION_EXECUTION_DECISION_2026-07-27.md`
- `docs/TASK_CARDS/FSC-first-service-completion.md`
- `docs/agent_handoff/SOURCE_OF_TRUTH_INDEX.md`
- dated work log only after Human Owner result confirmation

Not allowed in FSC-0:

- code, tests, fixtures, source corpus
- dependency or lock changes
- public/core/status contract changes
- live provider, API, UI, or LLM runtime implementation
- commit, push, PR, merge, or deploy without separate approval

## 6. FSC-0 Preflight Results

### 6.1 Git and local baseline

| Check | Result |
|---|---|
| branch created from latest main | `PASS - fsc/fsc-0-preflight` |
| HEAD | `da03a6fb3be5c985cef7d5d1f0523827340fe088` |
| origin/main | `da03a6fb3be5c985cef7d5d1f0523827340fe088` |
| existing dirty state | user-owned untracked `.tmp/` only |
| destructive Git/filesystem action | `NOT_RUN` |
| docs outside FSC-0 ownership changed | `NO` |

### 6.2 Credential and secret boundary

| Item | Result |
|---|---|
| local `NAVER_CLIENT_ID` | `CONFIGURED` |
| local `NAVER_CLIENT_SECRET` | `CONFIGURED` |
| local `GEMINI_API_KEY` | `CONFIGURED` |
| GitHub Secret `GEMINI_API_KEY` | `CONFIGURED - name/status only` |
| tracked `.env` | `NO` |
| `.gitignore` excludes `.env` | `PASS` |
| `.dockerignore` excludes `.env` and `.env.*` | `PASS` |
| secret value output/log/commit | `NONE` |
| GCE `.env.runtime` | `NOT_CHECKED` |

### 6.3 Gemini

| Check | Result |
|---|---|
| official model metadata | `PASS - models/gemini-3.5-flash present` |
| `generateContent` metadata | `SUPPORTED` |
| LiteLLM `1.83.7` static routing | `PASS - provider gemini` |
| sanitized generation smoke | `FAIL - RateLimitError` |
| normalized status | `rate_limited` |
| structured output/usage/finish reason | `NOT_CONFIRMED` |
| `thinking_level=minimal` actual response | `NOT_CONFIRMED` |
| Human Owner free quota/billing check | `NOT_RUN` |
| dependency/model fallback | `NOT_APPROVED / NOT_RUN` |

Stop decision:

- keep `gemini/gemini-3.5-flash`
- do not change LiteLLM or dependencies
- do not send `thinking_budget` with `thinking_level`
- require Human Owner quota/billing confirmation and one separately approved
  sanitized generation rerun before FSC-2

The bullets above record the FSC-0 decision at the time it was observed. The
Human Owner later approved the repository-wide Gemini 3.5 contract migration.
That migration does not rewrite the prior rate-limit result.

Current normative contract:

- model: `gemini/gemini-3.5-flash`
- dependency: `litellm==1.84.1`, the smallest compared stable pin with the
  exact 3.5 model registration and minimal thinking-level mapping
- environment: `LLM_THINKING_LEVEL=minimal`,
  `LLM_MAX_OUTPUT_TOKENS=1024`, `LLM_TIMEOUT_SECONDS=10`
- adapter: `reasoning_effort=minimal`, retry `0`
- prohibited: `LLM_THINKING_BUDGET`, simultaneous level/budget,
  `drop_params`, undocumented `extra_body`, omitted thinking, or 2.5 fallback
- compatibility verification: local mock transport PASS plus one separately
  approved sanitized live Gemini smoke `PASS`; see section 13
- prior 1.83.7 `UnsupportedParamsError`: Human Owner-supplied local evidence;
  not reproduced in this migration

### 6.4 NAVER API HUB

| Check | Result |
|---|---|
| endpoint/header contract | `PASS` |
| credentials accepted | `PASS - HTTP 200` |
| top-level object and `items` list | `PASS` |
| initial piped Korean queries | `ENVIRONMENT_INVALID - PowerShell pipeline replaced Korean characters with ?` |
| UTF-8 official-example and generic queries | `PASS - HTTP 200, total > 0, items returned` |
| UTF-8 company queries | `PASS - Samsung Electronics, SK hynix, and Hyundai Motor returned items` |
| actual `pubDate`/`originallink` item | `PASS - present in UTF-8 revalidation results` |
| 2026-07-24 cutoff coverage of 15 news items | `NOT_CONFIRMED` |
| metadata storage/processing terms | `INITIAL REVIEW_REQUIRED; later APPROVED under existing policy` |
| FSC path | `automatic collection COMPATIBLE; PDF/URL Work fallback retained` |

The initial `0 items` responses are invalid API evidence because the Windows
PowerShell here-string pipeline changed the Korean query bytes before
`python -` received them. With PowerShell `$OutputEncoding` set to UTF-8, and
with a direct PowerShell call, the official example plus `커피`, `경제`,
`삼성전자`, `SK하이닉스`, and `현대차` returned `HTTP 200`, positive totals,
items, `pubDate`, and `originallink`. This proves API and credential
compatibility only. At FSC-0 it did not prove that the required 15 news items
satisfied the `2026-07-24` cutoff, attribution, dedupe, or permission gates.
SC-01 later resolved the storage/use boundary by applying the existing approved
policy: article metadata and Questock-authored short summaries only, with no
article body in runtime or Git.

### 6.5 DART source inventory

| Security | Receipt | Official viewer | Local PDF |
|---|---|---|---|
| `KRX:005930` | `20260515002181` | `HTTP 200 / receipt present` | `AVAILABLE` |
| `KRX:000660` | `20260515002287` | `HTTP 200 / receipt present` | `NOT_FOUND` |
| `KRX:005380` | `20260515002418` | `HTTP 200 / receipt present` | `NOT_FOUND` |

Acquisition path:

- official viewer/download
- Human Owner PDF fallback

Fact extraction, page/section locator verification, and actual coverage remain
`NOT_RUN`.

### 6.6 Research-report source inventory

| Security | Official report | PDF date | PDF/hash/locator | Permission |
|---|---|---|---|---|
| `KRX:005930` | `https://securities.miraeasset.com/bbs/board/message/view.do?categoryId=1800&messageId=2341060` | `2026-07-07` | `VERIFIED` | `approved / corpus true / external LLM false` |
| `KRX:000660` | `https://securities.miraeasset.com/bbs/board/message/view.do?categoryId=1533&messageId=2341215` | `2026-07-14` | `VERIFIED` | `approved / corpus true / external LLM false` |
| `KRX:005380` | `https://securities.miraeasset.com/bbs/board/message/view.do?categoryId=1800&messageId=2341441` | `2026-07-24` | `VERIFIED` | `approved / corpus true / external LLM false` |

The Human Owner supplied the structured extraction packages and approved the
use of PDF-verified metadata, facts, locators, and Questock-authored short
summaries for the internal corpus on `2026-07-27`. Official PDFs are used only
in the Git-ignored verification workspace. Source PDFs, report body, evidence
excerpts, and raw text are excluded from runtime, Git, and Gemini input.

### 6.7 Database

`NOT_USED`

## 7. Verification

| Command or check | Exit | Observed result |
|---|---:|---|
| `uv run --no-sync pytest tests -q --basetemp <dedicated-temp> -p no:cacheprovider` | `0` | `1852 passed, 2 warnings` |
| `uv run --no-sync python scripts/m3_gate.py` | `0` | `34/34; Critical 17/17; public exposure 0; M3-12 NOT_ACTIVATED` |
| `uv run --no-sync python scripts/secret_scan.py` | `0` | `[]` |
| `uv run --no-sync python -m compileall -q app tests scripts streamlit_app.py` | `0` | no output |
| GitHub CI | - | `NOT_RUN` |
| Docker build | - | `NOT_RUN` |
| GCE deploy | - | `NOT_RUN` |

Environment note:

The first sandboxed gate/scan/compile attempts exited before execution because
the default user uv cache was inaccessible. The same commands were rerun with
the repository-owned `.deps/b6-uv-cache`; gate, scan, and compile then passed.
This was an environment retry, not a code/test failure.

## 8. FSC-0 Completion Criteria

- [x] execution decision records FSC insertion and precedence
- [x] Source of Truth points to the FSC decision and Task Card
- [x] M4 Gate remains `PASS`
- [x] A15-M is blocked until Service Completion Gate PASS
- [x] local credential names are configured without value exposure
- [x] GitHub Gemini secret existence is checked without value exposure
- [x] Gemini model metadata and LiteLLM routing are checked
- [x] Gemini stop decision is explicit after sanitized rate-limit failure
- [x] NAVER automatic-or-fallback decision is explicit
- [x] three DART acquisition paths are identified
- [x] three report candidate/fallback paths are identified
- [x] DB is `NOT_USED`
- [x] regression, M3 Gate, secret scan, and compile pass
- [x] Human Owner confirms FSC-0 result
- [x] confirmed FSC-0 result is recorded in the dated work log

## 9. Required Follow-up

Before FSC-1 normalized snapshot acceptance:

- Human Owner reviews the implemented SC-03 report result
- SC-04 composes the confirmed SC-01~03 inputs into the immutable runtime
  snapshot after separate approval

Before FSC-2:

- Human Owner confirms Gemini project free quota and billing state
- one approved sanitized generation smoke confirms structured output,
  usage/finish reason, timeout, and `thinking_level=minimal`

## 10. Stop Conditions

Stop and report if:

- source requires an invented URL, receipt, page, section, permission, or value
- cutoff-after source is required
- copyrighted article/report body would be committed
- public schema shape or trace version must change
- M1/M2 freshness, coverage, Evidence, or policy contract must change
- a dependency update beyond approved `litellm==1.84.1` is required
- a model other than approved Gemini 3.5 Flash is proposed automatically
- secret, prompt, raw provider payload, raw IP, local path, or opaque client key
  would be exposed
- existing wrong-company, safety, M3 Gate, Critical, or public exposure
  behavior regresses
- a database or unbounded memory/cache is required

## 11. FSC-1 Progress

### 11.1 Implemented automatic path

Changed files:

- `config/service_snapshot_news_queries.json`
- `app/services/news_snapshot_schema.py`
- `scripts/collect_naver_news_snapshot.py`
- `tests/unit/test_news_snapshot_collector.py`
- `.gitignore`
- `.dockerignore`

The collector is a UTF-8 saved Python script. It does not accept source code
through Python stdin and does not use a PowerShell here-string. It enforces:

- exact NAVER API HUB endpoint and credential header names
- UTF-8 Korean query encoding
- per-security `date|sim` sort selected from validated config
- each query contains the canonical company name or an allowed alias under the
  existing news lexicon and `build_news_query()` contract
- at most 10 calls and 1,000 returned items per security
- existing transport-independent NAVER normalizer
- canonical company attribution, URL/title/time dedupe, KST cutoff
- ignored raw and candidate output under `var/service_completion/**`
- sanitized CLI output and rejection logs without article content, URL, raw
  payload, credential, or local path
- `PASS` only when all three security coverage requirements are met
- `INCOMPLETE / fallback_required` when automatic coverage is insufficient

### 11.2 Actual NAVER collection results

The finalized saved script was run with local process environment credentials.
No credential value was printed or written to a tracked file.

Initial broad canonical-name queries with latest-first sorting:

| Security | Calls | Raw items | Cutoff-window items | Candidates | Result |
|---|---:|---:|---:|---:|---|
| `KRX:005930` | 10 | 1,000 | 0 | 0 | `fallback_required` |
| `KRX:000660` | 10 | 1,000 | 0 | 0 | `fallback_required` |
| `KRX:005380` | 10 | 1,000 | 0 | 0 | `fallback_required` |

The minimum raw timestamps were:

- `KRX:005930`: `2026-07-26T23:20:00Z`
- `KRX:000660`: `2026-07-26T07:51:00Z`
- `KRX:005380`: `2026-07-24T23:10:00Z`

This result was caused by the broad canonical queries exhausting NAVER's
1,000-result ceiling before reaching the fixed snapshot window. It was not an
API, credential, date parsing, timezone, attribution, or dedupe failure.

The config was then narrowed to independently proven UTF-8 company/date queries
and per-security sorting:

| Security | Query | Sort |
|---|---|---|
| `KRX:005930` | `삼성전자 2026년 7월 24일` | `date` |
| `KRX:000660` | `SK하이닉스 7월24일` | `sim` |
| `KRX:005380` | `현대차 7월24일` | `date` |

Final saved-script rerun:

| Security | Calls | Raw items | Cutoff items | Normalized candidates | Pre-market | Intraday | Ready |
|---|---:|---:|---:|---:|---:|---:|---|
| `KRX:005930` | 10 | 1,000 | 16 | 16 | 7 | 9 | `true` |
| `KRX:000660` | 10 | 1,000 | 62 | 48 | 16 | 32 | `true` |
| `KRX:005380` | 10 | 1,000 | 15 | 14 | 4 | 10 | `true` |

Observed final collector status:

`PASS - exit 0`

All normalized candidate document IDs were unique and every candidate retained
a source URL. This is automatic candidate coverage, not final canonical
snapshot acceptance.

Generated raw responses, candidate JSON, and rejection logs are all ignored by
Git. No article body or generated candidate is part of the tracked diff.

### 11.3 Verification

| Command or check | Exit | Observed result |
|---|---:|---|
| FSC news targeted pytest after query/sort supplement | `0` | `52 passed, 1 warning` |
| full unit/integration pytest before query/sort supplement | `0` | `1865 passed, 2 warnings` |
| full unit/integration pytest after query/sort supplement | - | `NOT_RUN - not requested for this supplement` |
| M3 Gate | `0` | `34/34; Critical 17/17; public exposure 0` |
| docs/secret targeted pytest | `0` | `99 passed` |
| Ruff | `0` | `All checks passed!` |
| secret scan | `0` | `[]` |
| compile | `0` | no output |
| GitHub CI | - | `NOT_RUN` |

The first targeted attempt was environment-blocked by Windows temporary
directory access. The same tests passed in a new user Temp basetemp. This was
not a code assertion failure.

### 11.4 Deterministic curation

Implemented:

- `scripts/curate_news_snapshot.py`
- curation schema and fixed event rules in
  `app/services/news_snapshot_schema.py`
- `tests/integration/test_service_snapshot_news.py`

Selection order is independent of candidate input order. Each company has five
distinct project-owned event rules. Within each rule, selection prioritizes:

1. an unused source host
2. direct title match over description-only match
3. later eligible publication time
4. stable document ID order

Selected documents must have:

- canonical company attribution
- a timezone-aware publication time within the fixed cutoff
- a valid source URL
- unique document ID, URL, normalized title, and publication time
- at least one pre-market and two intraday items per company

Curated work output:

`var/service_completion/news/curated/news_snapshot_curated_<ticker>.json`

The output remains Git ignored until SC-04. Each selected item contains only:

- `document_id`
- `time_band`
- `source_locator` with provider, URL, and UTC publication time
- a fixed Questock-authored short summary

It does not contain article title, text, description, raw payload, query,
credential, or local path.

Initial deterministic curation result, superseded by the SC-01 quality
revision in section 11.5:

| Security | Selected | Pre-market | Intraday | Unique source hosts | Ready |
|---|---:|---:|---:|---:|---|
| `KRX:005930` | 5 | 1 | 4 | 5 | `true` |
| `KRX:000660` | 5 | 1 | 4 | 5 | `true` |
| `KRX:005380` | 5 | 1 | 4 | 5 | `true` |

Two consecutive builds returned exit `0` and byte-identical curated JSON for
this initial selection.
Existing news metadata storage and processing policy was applied. No new
copyright-wide review was opened, and no article body is stored or committed.

Supplement verification:

| Command or check | Exit | Observed result |
|---|---:|---|
| SC-01 targeted and integration pytest | `0` | `58 passed, 1 warning` |
| Ruff | `0` | `All checks passed!` |
| two-build deterministic curation | `0 / 0` | byte-identical; 5 per company |
| full regression after curation | - | `NOT_RUN - not requested for SC-01 supplement` |
| GitHub CI | - | `NOT_RUN` |

### 11.5 SC-01 quality revision

Human Owner review found that the first deterministic set over-prioritized
source-domain diversity and admitted weak items such as leverage-product
regulation, simple share-price updates, and broad market summaries. That set
was not accepted as SC-01 completion.

The revision fixes collection and curation boundaries as follows:

- base company/date query remains bounded to 10 calls
- at most 3 direct quality queries per security
- at most 2 calls per quality query
- every query must contain the canonical name or an approved alias under the
  existing news lexicon and `build_news_query()` contract
- merged candidates are deduped deterministically by canonical document ID and
  source URL
- selection priority is company directness and explanatory value, distinct
  events, time distribution, then source diversity
- simple price-only, broad-market-only, leverage regulation, affiliate-only,
  promotion/peripheral, and accidental date-query matches are excluded from
  the selected set
- source-domain diversity is a tie-breaker, not a five-domain hard contract

Revised actual candidate pools:

| Security | API calls | Raw items | Normalized candidates | Pre-market | Intraday |
|---|---:|---:|---:|---:|---:|
| `KRX:005930` | 16 | 1,600 | 24 | 13 | 11 |
| `KRX:000660` | 16 | 1,600 | 48 | 16 | 32 |
| `KRX:005380` | 14 | 1,253 | 14 | 4 | 10 |

The Hyundai direct-query supplement did not add a new eligible normalized
document. The revised selection therefore uses the strongest available direct
earnings, production/labor, and technology/investment items while minimizing
repetition without admitting weaker broad-market or affiliate-only items.

Revised selected set:

| Security | Selected | Pre-market | Intraday | Unique source hosts | Ready |
|---|---:|---:|---:|---:|---|
| `KRX:005930` | 5 | 2 | 3 | 5 | `true` |
| `KRX:000660` | 5 | 1 | 4 | 5 | `true` |
| `KRX:005380` | 5 | 2 | 3 | 5 | `true` |

The runtime curation payload still contains only document ID, time band, source
locator, and Questock-authored short summary. Title and URL crosswalks are
written only to the Git-ignored Human Owner review area. Two consecutive builds
of all six curated runtime/review outputs were byte-identical.

SC-01 status:
`PASS / complete - Human Owner confirmed 2026-07-27`

### 11.6 SC-02 disclosure implementation

Implemented:

- `app/services/disclosure_snapshot_schema.py`
- `scripts/curate_disclosure_snapshot.py`
- `tests/integration/test_service_snapshot_disclosure.py`

Input assets were read from the three Human Owner-provided disclosure folders.
PDFs, fact matrices, rejected-item notes, raw viewer HTML, and working copies
remain under the input folders or `var/service_completion/**`; none is a
tracked runtime asset.

The importer enforces:

- fixed security/receipt pairs:
  - `KRX:005930 / 20260515002181`
  - `KRX:000660 / 20260515002287`
  - `KRX:005380 / 20260515002418`
- one receipt equals one `FinancialDocument`
- PDF company/report identity plus fixed project security mapping
- `ticker` and `corp_code` are project-mapping values, with corp code remaining
  `candidate`; they are not represented as PDF-verified values
- actual fact-list recount rather than matrix coverage-field trust
- minimum 10 facts and all 10 V4 required categories
- value, unit, period, physical PDF page, printed DART page, section, and basis
- page bounds against observed PDF counts
- exact receipt-based official viewer URL and receipt-only document ID
- existing M1-05 `rm` semantics through `parse_report_markers()`
- output exclusion of verification excerpts, source filenames, local absolute
  paths, credentials, PDFs, and long source text

Actual result:

| Security | Receipt | Documents | Facts | Required categories | PDF pages | Official remark |
|---|---|---:|---:|---:|---:|---|
| `KRX:005930` | `20260515002181` | 1 | 18 | 10/10 | 323 | `유` |
| `KRX:000660` | `20260515002287` | 1 | 21 | 10/10 | 236 | `유` |
| `KRX:005380` | `20260515002418` | 1 | 20 | 10/10 | 286 | `유` |

`OPENDART_API_KEY` is present by name but has no configured value in the local
environment, so the OpenDART list API verification was `NOT_RUN`. Exact receipt,
corp code, company name, quarterly-report marker, and visible `rm` badges were
verified from each official DART viewer instead. All three showed only `유`;
current-item correction, subsequent correction, and withdrawal are therefore
all false under the existing M1-05 contract.

The Hyundai segment and R&D definition differences are retained in each
fact's section, basis, verification status, and conflict note. Values from
different definitions are not combined.

SC-02 status:
`PASS / complete - Human Owner confirmed 2026-07-27`

### 11.7 Current gate

SC-01 quality revision and SC-02 implementation were confirmed by the Human
Owner on 2026-07-27 and are recorded as completed Steps in the dated Work Log.

SC-03 and SC-04 subsequently completed with the approved source and permission
package. FSC-1 is now `PASS / complete`; FSC-2 planning/preflight is allowed
and its implementation remains blocked by the recorded Gemini follow-up.

### 11.8 SC-01/SC-02 verification

| Command or check | Exit | Observed result |
|---|---:|---|
| news/disclosure provider + SC-01/SC-02 targeted pytest | `0` | `151 passed, 1 warning` |
| changed-file Ruff | `0` | `All checks passed!` |
| `python -m compileall -q app tests scripts` | `0` | no output |
| secret scanner targeted pytest | `0` | `82 passed` |
| tracked secret scan | `0` | `[]` |
| changed tracked+untracked focused secret scan | `0` | `[]` |
| curated output credential/local-path/excerpt scan | `0` | `NO_MATCH` |
| tracked `git diff --check` | `0` | no whitespace errors |
| untracked diff check | `0` | `11 files checked` |
| new module/script import smoke | `0` | `ok` |
| SC-01 repeated build | `0` | `6 files byte-identical` |
| SC-02 repeated actual build | `0` | `3 files byte-identical` |
| full regression after SC-01 quality and SC-02 | - | `NOT_RUN - not required for this scoped source work` |
| GitHub CI | - | `NOT_RUN` |

### 11.9 SC-03 research-report implementation

Implemented:

- `app/services/report_snapshot_schema.py`
- `scripts/curate_report_snapshot.py`
- `tests/integration/test_service_snapshot_report.py`

Permission boundary confirmed by the Human Owner on `2026-07-27`:

- `usage_review_status=approved`
- `corpus_ingest_allowed=true`
- `external_llm_processing_allowed=false`
- allowed corpus content:
  PDF-verified metadata, structured facts, locator, and Questock-authored short
  summaries
- excluded:
  source PDF, report body, evidence excerpt, raw text, and any of those source
  materials as Gemini input

The implementation reuses the existing M1-06 corpus mode and requires:

- exact source package and official PDF SHA-256
- observed PDF page count
- fixed security, title, publisher, analyst, publication date, source URL, and
  source asset identity
- `verified` source hash and `verified_against_source` manual verification
- exact 12-section set per security with physical PDF page and section locator
- source-attributed opinion and target price, never a Questock investment
  opinion
- deterministic JSON and recomputed saved-payload validation
- output exclusion of source filenames, local paths, PDF bytes, report body,
  evidence excerpts, and raw text

Actual result:

| Security | PDF date | PDF pages | Documents | Distinct verified pages | Ready |
|---|---|---:|---:|---:|---|
| `KRX:005930` | `2026-07-07` | 8 | 12 | 4 | `true` |
| `KRX:000660` | `2026-07-14` | 9 | 12 | 4 | `true` |
| `KRX:005380` | `2026-07-24` | 12 | 12 | 5 | `true` |

The official Samsung PDF fixes the NAND shipment-growth sign to `+3%`. The
official SK hynix PDF uses generic `HBM`, not `HBM1`. The Hyundai publication
date is `2026-07-24` from the report cover and page marks; the later local
filename date is not used.

SC-03 status:
`PASS / complete - Human Owner confirmed 2026-07-27`

### 11.10 SC-03 verification

| Command or check | Exit | Observed result |
|---|---:|---|
| SC-03 targeted pytest | `0` | `21 passed, 1 warning` |
| SC-01~03 plus M1-04~M1-06 regression | `0` | `382 passed, 1 warning` |
| actual three-report curation | `0` | `PASS; 12 documents per security` |
| repeated actual curation | `0 / 0` | `3 files byte-identical` |
| changed-file Ruff | `0` | `All checks passed!` |
| changed-file compile | `0` | no output |
| import smoke | `0` | `3 True` |
| secret scanner targeted pytest | `0` | `82 passed` |
| tracked secret scan | `0` | `[]` |
| curated forbidden-content/local-path scan | `0` | `NO_MATCH` |
| `git diff --check` | `0` | no whitespace errors |
| full regression | - | `NOT_RUN - not required for SC-03 source work` |
| GitHub CI | - | `NOT_RUN` |

Two sandboxed targeted attempts were blocked by Windows pytest temporary-path
cleanup with `WinError 5`. The same targeted test was rerun outside that
sandbox boundary and passed; this was an environment retry, not a changed
assertion.

### 11.11 SC-04 immutable snapshot runtime

Implemented:

- `app/services/service_snapshot.py`
- `app/services/service_snapshot_gateway.py`
- `scripts/build_service_snapshot.py`
- `scripts/validate_service_snapshot.py`
- `app/runtime.py`
- `data/service_snapshot/svc-20260724-1402/**`
- `tests/unit/test_service_snapshot.py`
- `tests/integration/test_service_snapshot_runtime.py`

Canonical bundle:

- schema: `service-snapshot-v1`
- snapshot ID: `svc-20260724-1402`
- fixed basis: `2026-07-24T05:02:00Z`
- supported securities: exactly `KRX:005930`, `KRX:000660`, `KRX:005380`
- news: `15` documents, exactly `5` per security
- news pre-market/intraday: `2/3`, `1/4`, `2/3`
- disclosures: `3` documents, exactly one fixed receipt per security
- disclosure verified facts: `18 / 21 / 20`
- research reports: `3` manifests and `36` verified section documents
- documents after basis: `0`
- global document IDs: `54 / 54` unique
- documents checksum:
  `54a57430f228d0b6305fff979beefeed8da0ebcdfdcbcd92544cc17575bdcf83`

Canonical files:

- `manifest.json`
- `documents.json`
- `coverage_matrix.json`
- `permission_register.json`

Generated evidence:

- `snapshot_checksum.txt`
- `validation_report.json`

The four canonical JSON files use UTF-8 without BOM, LF, sorted keys, compact
separators, and one final newline. Two independent output directories produced
all six files byte-identically.

Runtime:

- existing `QUESTOCK_SOURCE_MODE=recorded` without a snapshot ID still loads
  the B9 demo unchanged
- `QUESTOCK_SNAPSHOT_ID=svc-20260724-1402` selects the approved service
  snapshot
- the process singleton loads the snapshot once and uses its fixed basis clock
- gateway fetches return deep copies
- invalid snapshot selection and data failure expose sanitized errors
- report Evidence with
  `external_llm_processing_allowed=false` uses the existing fixed template
  and is not sent to an external LLM

SC-04 status:
`PASS / complete - local implementation verification PASS; Human Owner requested FSC-1 closure 2026-07-27`

### 11.12 SC-04 and FSC-1 verification

| Command or check | Exit | Observed result |
|---|---:|---|
| canonical snapshot build | `0` | `PASS; 54 documents; 15 news; 3 disclosures; 3 reports / 36 sections` |
| canonical snapshot validator | `0` | `PASS` |
| two independent builds | `0 / 0` | `6 files byte-identical` |
| SC-04 targeted plus B9 runtime compatibility | `0` | `41 passed, 2 warnings` |
| full pytest regression | `0` | `1946 passed, 2 warnings` |
| full Ruff | `0` | `All checks passed!` |
| full compile | `0` | no output |
| tracked secret/local-path scan | `0` | `[]` |
| `git diff --check` | `0` | no whitespace errors; line-ending warnings only |
| independent pytest rerun | - | `NOT_RUN` |
| GitHub CI | - | `NOT_RUN` |

Observed implementation retries:

- direct file invocation of the builder exited `1` because the repository root
  was not on the import path; module invocation was used for the recorded
  successful builds
- the first canonical validation detected provider news IDs shared across
  securities; snapshot news IDs are now deterministic SHA-256 IDs derived from
  security ID and source document ID, with source URL and time preserved
- the initial generic-news retrieval test had two low-relevance results; a
  project-owned representative query label was added to one summary document
  per security without changing source content or the M2 retrieval contract

FSC-1 status:
`PASS / complete - SC-01~04 complete`

## 12. Git and Review State

- FSC-0 implementation diff:
  `docs-only`
- work log:
  `UPDATED - WORK_LOG_2026-07-27.md`
- commit:
  `c18dad90f293b50f3e258c37907bd6b79cac8e6b - FSC-1 backup`;
  `25cac10030800f08d4167b9f7739d06b3d1492ca - FSC-2 implementation`;
  release implementation head
  `8d1b9521fdbef003cb84708b6aa7b47d01d8dc8a`;
  release hotfix commits `499bf03`, `bed5684`
- push:
  `complete for release implementation and hotfix branches`
- PR:
  `#10 - https://github.com/JJungDae/Questock/pull/10 - MERGED`;
  head SHA `25cac10030800f08d4167b9f7739d06b3d1492ca`;
  `#11 - https://github.com/JJungDae/Questock/pull/11 - MERGED`;
  `#12 - https://github.com/JJungDae/Questock/pull/12 - MERGED`
- merge:
  `#10 92561e34b4839d32a9bdac979c6c471da8e56923`;
  `#11 6affd27f4f95aae438268acd2bc4fa7733346b5d`;
  `#12 2adcc787a803996d4a181a6cd3faa3158602660a`
- deploy:
  `PASS - exact-SHA GCE deploy run 30274651799`
- FSC-1 automatic start:
  `APPROVED - Human Owner instructed FSC-1 start on 2026-07-27`
- SC-01 result confirmation:
  `PASS / complete - Human Owner confirmed 2026-07-27`
- SC-02 result confirmation:
  `PASS / complete - Human Owner confirmed 2026-07-27`
- SC-03 input and permission:
  `APPROVED - Human Owner confirmed 2026-07-27`
- SC-03 implementation:
  `PASS / complete - Human Owner confirmed 2026-07-27`
- FSC-1 completion:
  `PASS / complete - Human Owner requested closure 2026-07-27`
- FSC-2 planning/preflight:
  `ALLOWED`
- FSC-2 implementation:
  `PASS / complete - Human Owner confirmed 2026-07-27`
- Gemini 3.5 contract migration commit/push:
  `complete - 25cac10030800f08d4167b9f7739d06b3d1492ca`

## 13. FSC-2 / SC-05 Implementation Result

### 13.1 Approved sanitized Gemini smoke

- Human Owner billing confirmation:
  `CONFIRMED - Human Owner authorized the approved smoke after the billing and local runtime preparation check`
- live generation calls in this step:
  `exactly 1`
- status:
  `ok`
- model:
  `gemini/gemini-3.5-flash`
- request contract:
  `reasoning_effort=minimal`, provider `thinkingLevel=minimal`,
  strict JSON schema, max output `1024`, timeout `10`, retry `0`
- structured parse:
  `PASS`
- usage present:
  `true`
- finish reason:
  `stop`
- sanitized latency:
  `1854.106 ms`
- raw prompt, raw provider response, credential, provider error, local path:
  `NOT_OUTPUT / NOT_RECORDED`
- additional live Gemini calls:
  `0`

The smoke used only a short synthetic input through the actual `LLMConfig` and
`LiteLLMClient` path. News, disclosure, research-report, session, and local
source data were not transmitted.

### 13.2 Implemented contract

- runtime mode:
  `QUESTOCK_LLM_MODE=disabled|gemini`; default `disabled`
- request protection:
  10 attempts per 5 minutes and 50 per KST day per client; global concurrency
  2 and 100 attempts per KST day; bounded 1024 client buckets with 24-hour TTL
- client identity:
  canonical IP or session fallback is converted to an opaque HMAC-SHA256 key;
  raw IP and raw identity are not sent to the API
- session memory:
  4 recent exchanges, 2,000 characters per user/assistant side, 16,000
  characters per session, and at most 2 exchanges / 4,000 characters in LLM
  context
- response cache:
  session-scoped 90-second TTL, global 256, per-session 4, resulting-revision
  lookup, deep-copy return, and no duplicate quota/history/revision use on hit
- browser transcript:
  current-session entries are deep-copied and bounded to 4; a new session
  clears the transcript, and transport remains inside explicit form submission
- permission:
  report content without exact external processing permission remains
  fixed-only and consumes no Gemini admission
- deployment contract:
  `.env.runtime` is attached only to the API service; atomic mode-600 install
  and one-generation environment rollback precede image/SHA rollback

### 13.3 Local verification

| Check | Result |
|---|---|
| FSC-2 targeted | `PASS - 227 passed, 2 warnings` |
| affected integration | `PASS - 73 passed, 2 warnings` |
| M3 Gate | `PASS - 34/34; Critical 17/17; public exposure 0` |
| full regression | `PASS - 1999 passed, 2 warnings` |
| Ruff | `PASS - All checks passed` |
| compile | `PASS - exit 0` |
| secret/local-path scan | `PASS - []` |
| diff check | `PASS - no whitespace errors; line-ending warnings only` |
| GitHub CI | `NOT_RUN` |
| independent pytest rerun | `NOT_RUN` |
| deploy/runtime secret install | `NOT_RUN` |

The first affected-integration attempt was invalidated by a Windows temporary
directory access error during pytest cleanup. The same test selection was
rerun outside that sandbox interference and passed 73 tests.

### 13.4 FSC-2 closure boundary (historical snapshot)

- FSC-2 code status:
  `PASS / complete`
- Human Owner implementation review:
  `PASS - Human Owner confirmed 2026-07-27`
- FSC-3:
  `SC-06 PASS / complete; SC-07 local gate PASS; remote release closure
  pending`
- current FSC-2 commit/push/PR/merge/deploy:
  `commit/push complete; PR #10 merged; deploy NOT_RUN`

## 14. FSC-3 / SC-06 Local Implementation Result

### 14.1 Implemented scope

- removed the supported-security selector and replaced it with one display-only
  recorded snapshot status
- displayed snapshot `svc-20260724-1402`, basis
  `2026-07-24 14:02 KST`, and news collection range
  `2026-07-24 00:00~14:00 KST`
- displayed actual Gemini/fixed generation mode plus the report permission,
  disclosure coverage, application quota fallback, and personal-financial-data
  warning boundaries
- preserved the current-browser transcript at four entries, isolated a new
  session, and kept transport calls inside explicit form submission
- added `tests/fixtures/service_acceptance/fsc_v1.json` with the exact 15
  approved questions, 12 LLM-eligible cases, and 3 Critical cases
- added a strict, sanitized, immutable schema/loader/inventory validator
- verified representative recorded/fixed API and UI flows for all three
  supported securities without a live provider or Gemini call

The public `ChatRequest`, `ChatResponse`, Evidence, citation, validator, core
model, status, and provider contracts were not changed. The focused supplement
in section 14.3 changes only the internal lexical token, Korean period, and
required-source selection behavior described there.

### 14.2 Local verification

| Check | Result |
|---|---|
| SC-06 targeted | `PASS - 32 passed, 2 warnings` |
| affected UI/API/FSC regression | `PASS - 266 passed, 2 warnings` |
| full regression | `PASS - 2020 passed, 2 warnings` |
| M3 Gate | `PASS - 34/34; Critical 17/17; public exposure 0` |
| Ruff changed files | `PASS - All checks passed` |
| compile | `PASS - exit 0` |
| tracked secret scan | `PASS - []` |
| explicit changed-file secret/local-path scan | `PASS - []` |
| acceptance JSON parse | `PASS` |
| diff check | `PASS - no whitespace errors; line-ending warnings only` |
| additional live Gemini calls | `0` |
| 15-case live acceptance | `NOT_RUN - separate Human Owner approval required` |
| GitHub CI / independent rerun | `NOT_RUN / NOT_RUN` |
| SC-07 / deploy | `NOT_RUN / NOT_RUN` |

The first command did not start because the user-level uv cache was not
readable. A repository-local uv cache was used. The first valid targeted run
reported `29 passed, 3 failed`: the three exact dated recent-issue questions
returned `no_evidence`. The representative local-flow test was then returned
to its approved mock/fixed purpose using the existing recorded representative
queries; the exact 15 questions remained unchanged in the fixture. The
targeted rerun passed 32 tests.

### 14.3 Focused root supplement result

The approved supplement addressed the diagnostic failures through general
runtime contracts rather than acceptance-question or snapshot-label exceptions:

- query and document tokenization now apply the same deterministic Hangul-only
  suffix normalization; supported request endings are `해주세요`, `주세요`,
  `해줘`, `해요`, `줘`, and `해`, and the bounded particle set includes
  `은/는`, `이/가`, `을/를`, `와/과`, `의`, `에/에서`, `으로/로`,
  `도`, `만`, `부터/까지`, `에게/에게서`, and `께서`
- a suffix is removed only when at least two Hangul characters remain;
  retrieval threshold `0.5`, document weighting, hard filter, score formula,
  wrong-company rules, and strategy identifier remain unchanged
- Korean `YYYY년 M월` and `YYYY년 M월 D일` periods are parsed strictly;
  month end and leap years are calendar-derived, invalid month/day values fail,
  and existing ISO/session inheritance contracts remain active
- when multiple required sources are requested, threshold-passing Evidence is
  ordered by one representative per required source before remaining score
  order; a missing or low-scoring source is never fabricated
- retrieval, context budget, and fixed composition share the source-diverse
  projection rule; the fixed response still caps the public projection at
  three Evidence items
- acceptance `required_evidence_sources` is validated against
  `EvidenceDecision.satisfied_sources`; final `ChatResponse.evidence` remains
  the citation-bound public subset
- report `external_llm_processing_allowed=false` remains fixed-only;
  mixed eligible requests transmit news/disclosure Evidence only, report-only
  requests make zero LLM calls, and mixed fixed/LLM composition was not added

The exact 15 questions and canonical snapshot content were not changed.
Two generated snapshot builds were byte-identical and matched the tracked
canonical files; document checksum remained
`54a57430f228d0b6305fff979beefeed8da0ebcdfdcbcd92544cc17575bdcf83`.

Supplement verification:

| Check | Result |
|---|---|
| focused targeted | `PASS - 347 passed, 2 warnings` |
| M3 Gate tests | `PASS - 9 passed, 1 warning` |
| full regression | `PASS - 2048 passed, 2 warnings` |
| M3 Gate | `PASS - 34/34; Critical 17/17; public exposure 0` |
| snapshot validator | `PASS - 54 documents` |
| two-build and tracked canonical identity | `PASS` |
| additional live Gemini/provider calls | `0` |
| 15-case live acceptance | `NOT_RUN - separate Human Owner approval required` |

The fixed/mock acceptance pass now confirms the three dated recent-issue cases
as `complete` with news, the six risk/multi-source cases with all required
policy sources satisfied, and the January 2025 disclosure case as
`no_evidence`. The inventory remains 12 LLM-eligible cases without violating
the report permission boundary.

### 14.4 SC-06 closure boundary (historical snapshot)

- SC-06:
  `PASS / complete - live acceptance passed 2026-07-27`
- Human Owner SC-06 review:
  `execution and up to 30 provider attempts approved`
- SC-07:
  `local release checkpoint PASS; remote CI/GCE/exact-SHA release NOT_RUN`
- current SC-06 commit/push/PR update/merge/deploy:
  `NOT_RUN`

### 14.5 Sanitized 15-case live acceptance

- approved provider-attempt ceiling: `30`
- actual provider attempts: `26`
- unused attempts: `4`
- primary batch: `2 / 12` LLM-eligible cases succeeded
- first focused batch: `5 / 10` succeeded
- final focused batch: `3 / 4` succeeded and stopped immediately at the
  required cumulative threshold
- cumulative LLM success: `10 / 12`
- remaining safe fallback cases: `FSC-02`, `FSC-11`
- Critical cases: `3 / 3 PASS`, Gemini calls `0`
- all 15 public response validations: `PASS`
- unsupported number, wrong-company, uncited core number, direct advice:
  `0 / 0 / 0 / 0`
- report source material sent to Gemini: `0`
- raw prompt, raw provider response, credential, raw error, local path:
  `NOT_OUTPUT / NOT_RECORDED`

The shared failure was a mismatch between model paraphrasing and the existing
extractive citation boundary. The focused fix keeps the initial safety and
numeric checks, then projects a non-exact single-Evidence draft claim onto the
canonical referenced snippet before a second validation and citation pass.
Unknown Evidence IDs, unsupported numbers, unsafe advice, conflicting duplicate
Evidence payloads, and multi-Evidence causal claims keep their previous
fail-closed behavior.

## 15. FSC-3 / SC-07 Local Release Preparation

### 15.1 Implemented scope

- CI now has an explicit `FSC release contracts` gate for the public model
  allowlist, LiteLLM request mapping, request protection, bounded session and
  cache behavior, snapshot checksum, acceptance fixture, rerun/F5 no-call,
  and release/rollback static contracts
- the GCE workflow keeps the exact active recorded snapshot, Gemini 3.5,
  request-protection, response-cache, timeout, and output-token environment
  contract
- Gemini credential installation remains API-only through atomic mode-600
  `.env.runtime`
- rollback restores the prior environment before image/SHA and health
  restoration

### 15.2 Local verification

| Check | Result |
|---|---|
| focused FSC release contracts | `PASS - 139 passed, 1 warning` |
| claim/citation targeted | `PASS - 127 passed, 2 warnings` |
| citation/ChatService/adapter/context regression | `PASS - 302 passed, 1 warning` |
| final focused claim/runner tests | `PASS - 54 passed, 1 warning` |
| full regression | `PASS - 2062 passed, 2 warnings` |
| M3 Gate | `PASS - 34/34; Critical 17/17; public exposure 0` |
| snapshot validator | `PASS - 54 documents` |
| two-build and tracked canonical identity | `PASS - all 6 files` |
| Ruff | `PASS - All checks passed!` |
| compile | `PASS - exit 0` |
| secret/local-path scan | `PASS - []` |
| Docker engine | `PASS - server 29.6.2` |
| Docker clean locked build | `PASS - image questock:fsc-sc07-local-25cac100; sha256:ad8d753d78a0b84fa3321f225188d567fc1940df5e5dac38c6b075ff50384bf4` |
| container security | `PASS - non-root questock; read-only rootfs; all capabilities dropped; no-new-privileges` |
| API health | `PASS - HTTP 200; recorded snapshot svc-20260724-1402; 54 documents` |
| UI health/root | `PASS - HTTP 200 / HTTP 200` |
| recorded release smoke | `PASS - 7/7 scenarios; live connectivity false` |
| release-smoke focused regression | `PASS - 28 passed, 1 warning` |
| additional Gemini/provider attempts | `0 - cumulative total remains 26/30` |
| GitHub CI | `NOT_RUN` |
| GCE remote smoke | `NOT_RUN` |
| exact-SHA deployment | `NOT_RUN` |

The first container smoke exposed an obsolete B9-only assertion in
`scripts/release_smoke.py`: it expected the prior `2026-07-26` demo basis and
treated SK hynix disclosure as absent. The focused correction uses the FSC
snapshot basis, the versioned FSC wrong-company case, and verifies that the
expanded disclosure fact inventory contains the required value, unit,
physical-PDF page, printed-DART page, and section locators. It does not relax
the no-evidence, citation, company-attribution, or disclosure-body checks.

### 15.3 Current boundary

- SC-07 local release preparation:
  `PASS / complete`
- SC-07 local gate:
  `PASS`
- SC-07 remote gate:
  `PASS`
- FSC-3:
  `PASS / complete`
- Service Completion Gate:
  `PASS / complete`
- remote release closure:
  `complete`
- A15-M:
  `activation check READY / implementation NOT_STARTED`
- commit/push/PR/merge/deploy:
  `complete / complete / complete / complete / complete for the release`

## 16. FSC Remote Release Closure

### 16.1 CI and merge history

- implementation PR:
  `#11`; head `8d1b9521fdbef003cb84708b6aa7b47d01d8dc8a`
- first PR #11 CI:
  `30273039760 - FAILED`; Python 3.11 could not resolve the extracted
  Streamlit helper's non-standalone type annotation
- focused fix:
  `8d1b952`
- successful PR #11 CI:
  `30273607080 - PASS`
- PR #11 merge:
  `6affd27f4f95aae438268acd2bc4fa7733346b5d`
- hotfix PR:
  `#12`; commits `499bf03`, `bed5684`
- first PR #12 CI:
  `30274239625 - FAILED`; the legacy B9 static test still expected the old
  Gemini-key allowlist
- focused contract after synchronization:
  `139 passed`
- successful PR #12 CI:
  `30274469379 - PASS`
- PR #12 merge and deployed main:
  `2adcc787a803996d4a181a6cd3faa3158602660a`

### 16.2 Deployment and rollback evidence

- first deploy:
  `30273898079 - FAILED before runtime write or deploy`; the anchored key
  allowlist excluded one dot in the already-live-verified 53-character Gemini
  key
- first-deploy impact:
  existing service and image unchanged; rollback execution `NOT_RUN`
- successful exact-SHA deploy:
  `30274651799 - PASS (3m32s)`
- release SHA:
  `2adcc787a803996d4a181a6cd3faa3158602660a`
- release image:
  `sha256:53628bacc40f2329bc3f7dfcb6771aeee2e5fd83a1a44592ee08bbc950daf138`
- previous rollback target SHA:
  `67fa43dd5a7ec74e7785713eb1adcfa402baab85`
- previous rollback target image:
  `sha256:56df8f16ed3ed58de659e9ec46c9e24b7d3ddc896dc8a022102f68f351d7b928`
- rollback execution:
  `NOT_RUN - successful deployment did not require rollback`

### 16.3 Remote runtime result

- health:
  `PASS - status ok; snapshot svc-20260724-1402; 54 documents`
- source inventory:
  `news 15 / disclosure 3 / research_report 36`
- live connectivity:
  `live_connectivity_checked=false`
- recorded smoke:
  `PASS - 7/7`; recent issue `complete`, disclosure `partial`, research report
  `complete`, glossary `complete`, wrong-company `no_evidence`, blocked
  `blocked`, multi-turn `partial`
- workflow external UI health:
  `PASS`
- independent interactive visual check:
  `LIMITED / non-gate`; a separate reviewer browser attempt to the registered
  host on port 8501 timed out, so interactive visual rendering is not claimed
- Gemini provider attempts:
  cumulative `26/30`; deployment smoke used the fixed/disabled recorded path
  and added `0` calls

FSC-3 and the Service Completion Gate are `PASS / complete`. A15-M activation
and entry are now `READY / ALLOWED`, but A15-M has not been implemented or
started. Stretch M2-09, M5-01, and later P1 ordering remains unchanged.
