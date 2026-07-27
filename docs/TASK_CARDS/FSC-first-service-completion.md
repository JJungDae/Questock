# TASK CARD - First Service Completion

## 1. Status and Approval

- Project: `Questock`
- Repository: `JJungDae/Questock`
- Planning base branch: `main`
- Planning base SHA:
  `da03a6fb3be5c985cef7d5d1f0523827340fe088`
- Working branch:
  `fsc/fsc-0-preflight`
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
  `PLANNING/PREFLIGHT ALLOWED; implementation BLOCKED pending Gemini quota/billing confirmation, sanitized generation smoke, and approval`
- FSC-3:
  `BLOCKED by bundle order`
- Service Completion Gate:
  `NOT_RUN`
- A15-M:
  `BLOCKED until Service Completion Gate PASS`
- M1-09:
  `mandatory supplement implemented - final independent review pending`
- Commit/push/PR/merge/deploy:
  `NOT_RUN / NOT_APPROVED`

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
| `FSC-2` | `SC-05` | Gemini, model allowlist, request protection, session/cache | `PLANNING/PREFLIGHT ALLOWED` |
| `FSC-3` | `SC-06~07` | UI, 3-company E2E, CI/GCE release | `BLOCKED` |

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
- current LiteLLM requires a dependency update
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
  `NOT_RUN`
- push:
  `NOT_RUN`
- PR:
  `NOT_RUN`
- merge:
  `NOT_RUN`
- deploy:
  `NOT_RUN`
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
  `BLOCKED pending Gemini quota/billing confirmation, approved sanitized generation smoke, and separate implementation approval`
