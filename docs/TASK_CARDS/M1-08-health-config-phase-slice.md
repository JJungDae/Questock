# TASK CARD - M1-08 Health, Config, Phase Slice

## 1. Status and Approval

- Task bundle: `B3: M1-06~08`
- Step: `M1-08 health·config·phase slice`
- Planning date: `2026-07-22`
- Planning base branch: `main`
- Planning base commit: `40543c425b8f5c0d6987940536be83a5a7b7a96a`
- M1-07A status: `PASS`
- M1-07B status: `PASS`
- M1-07B completion commit: `40543c425b8f5c0d6987940536be83a5a7b7a96a`
- Current status: `IMPLEMENTED - USER REVIEW PENDING`
- Dependency changes in Section 6: `APPROVED`
- README creation: `APPROVED`
- CLI-only preliminary implementation: `NOT_USED`
- Commit/push/PR/merge/deploy: `NOT_APPROVED`
- Live API/LLM/retrieval/M2: `OUT_OF_SCOPE`

Adoption of this revised Task Card authorizes the M1-08 implementation, dependency changes, tests, README creation, and previous Task Card status synchronization described below. Commit and push remain separate approval actions.

## 2. Goal and Completion Boundary

M1-08 closes the `B3 / M1-06~08 ingestion and fixture-readiness gate` with a small deterministic integration slice.

It does **not** close the entire M1 milestone while `M1-09 MarketSnapshot` remains unfinished.

The phase-appropriate slice is:

```text
fixed reference security query
-> SecurityResolver
-> existing provider policy wrapper
-> recorded news/disclosure providers
-> synthetic manual report ingest
-> approved local glossary readiness
-> sanitized health payload
-> CLI and GET /health
```

M1-08 is not a retrieval, EvidencePolicy, answer-generation, UI, live-provider, or live-LLM task.

## 3. Re-review Decisions Incorporated

The initial independent review was appropriate and its mandatory findings are adopted:

- distinguish fixture readiness from live connectivity
- fix provider-specific query mapping
- limit the reference slice to Samsung Electronics
- fix dates and expected counts
- define aggregate status and HTTP behavior
- make async boundaries explicit
- define tracked-file secret scanning and safe findings
- add FastAPI and HTTP route tests
- create README
- synchronize M1-07/M1-07B status
- rename the completion boundary so M1-09 remains open

This revised plan also adds the following missing safeguards:

1. Add an ASGI server dependency so the approved FastAPI application can actually be run.
2. Call providers through the existing `fetch_with_policy()` wrapper so config timeout/retry/deadline behavior is integrated rather than merely displayed.
3. Require a side-effect-free API import and dependency-injectable phase-slice builder for deterministic failure tests.
4. Require explicit `JSONResponse` status mapping; returning a plain dict must not accidentally turn degraded/error responses into HTTP 200.
5. Separate repository-wide credential scanning from public-path scanning so historical internal Task Card logs do not create unavoidable path false positives.
6. Define phase-slice CLI exit codes and forbid arbitrary CLI security input in this reference-only task.

## 4. Existing Verified Inputs

Use, do not redesign:

- supported securities in `data/securities.json`
- `SecurityResolver` in `app/core/resolver.py`
- `ProviderConfig.from_env()` and `safe_summary()` in `app/config.py`
- `fetch_with_policy()` in `app/providers/base.py`
- `RecordedNewsProvider` in `app/providers/news.py`
- `RecordedDisclosureProvider` in `app/providers/disclosure.py`
- `build_manual_research_documents()` in `app/ingest/reports.py`
- `evaluate_actual_glossary_coverage()` and glossary lookup/locator helpers in `app/ingest/glossary.py`
- existing synthetic fixtures under `tests/fixtures/**`

The current runtime dependency list contains only Pydantic. The current dev dependency list contains pytest.

## 5. Fixed Scope

### 5.1 Required

- clean environment config load
- secret-safe config summary
- one deterministic Samsung Electronics reference slice
- three `FinancialDocument` source types:
  - news
  - disclosure
  - research_report
- approved local glossary readiness
- pure async payload builders
- CLI output
- `GET /health`
- tracked-file credential scan
- public-output local-path scan
- README usage and warning documentation
- M1-07/M1-07B status-only synchronization
- targeted, regression, API, CLI, scanner, and compile verification

### 5.2 Out of Scope

- live NAVER or OpenDART requests
- live report-source connectivity
- external LLM connectivity
- actual research-report corpus coverage
- M1-09 MarketSnapshot
- M2 QueryPlanner, filters, retrieval, Evidence normalization, EvidencePolicy, or citations
- prompts, answer composition, UI
- database or vector index
- API routes other than `/health`
- new financial source types
- modifying existing provider behavior
- modifying glossary content or report schema
- changing `FinancialDocument`, status enums, `ProviderResult`, or resolver contracts

## 6. Approved Dependency Changes

Update `pyproject.toml`.

### Runtime

```toml
dependencies = [
    "pydantic>=2.7,<3",
    "fastapi>=0.115,<1",
    "uvicorn>=0.30,<1",
]
```

### Dev

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8,<9",
    "httpx>=0.27,<1",
]
```

Reasons:

- FastAPI provides the approved `/health` route.
- Uvicorn provides an executable ASGI server for local use.
- HTTPX is required for actual ASGI request tests through FastAPI/Starlette test tooling.

Do not add `pytest-asyncio`; async unit tests may use `asyncio.run()`.

Record the actual dependency installation command and result. Do not claim dependency installation or API execution before it is run.

## 7. Approved Files

### 7.1 New files

- `app/health.py`
- `app/phase_slice.py`
- `app/api/__init__.py`
- `app/api/routes_health.py`
- `app/api/main.py`
- `scripts/__init__.py`
- `scripts/m1_phase_slice.py`
- `scripts/secret_scan.py`
- `tests/unit/test_health_phase_slice.py`
- `tests/unit/test_secret_scan.py`
- `tests/unit/test_api_health.py`
- `README.md`

### 7.2 Modified files

- `pyproject.toml`
- `docs/TASK_CARDS/M1-08-health-config-phase-slice.md`
- `docs/TASK_CARDS/M1-07-glossary-ingest.md` — status-only synchronization
- `docs/TASK_CARDS/M1-07B-glossary-corpus.md` — status-only synchronization

### 7.3 Do not modify

- `app/core/models.py`
- `app/core/status.py`
- `app/core/resolver.py`
- `app/providers/base.py`
- `app/providers/news.py`
- `app/providers/disclosure.py`
- `app/ingest/reports.py`
- `app/ingest/glossary.py`
- `app/config.py`
- `data/securities.json`
- `data/glossary.json`
- existing synthetic fixtures

If a fixture or existing contract appears defective, stop and report instead of changing it.

## 8. Reference Slice Constants

Fix the M1-08 reference slice to:

```python
REFERENCE_QUERY = "삼성전자"
REFERENCE_SECURITY_ID = "KRX:005930"
REFERENCE_SECURITY_NAME = "삼성전자"
REFERENCE_TICKER = "005930"

REFERENCE_DATE_RANGE = DateRange(
    start=date(2026, 7, 21),
    end=date(2026, 7, 21),
)

REFERENCE_REPORT_AS_OF_DATE = date(2026, 7, 22)

EXPECTED_DOCUMENT_COUNTS = {
    "news": 1,
    "disclosure": 1,
    "research_report": 2,
}
```

Expected total:

```text
financial_document_source_count = 3
financial_document_count = 4
```

The report fixture is synthetic and Samsung-specific. It must not be presented as actual report corpus coverage.

## 9. Resolver and Scope Contract

### 9.1 Pure builder input

`build_phase_slice()` may accept a query for unit tests and future internal reuse.

The following inputs resolve to the reference security and are eligible:

- `삼성전자`
- `005930`
- `KRX:005930`
- approved Samsung Electronics aliases in `data/securities.json`

### 9.2 Non-resolved input

If resolution is `ambiguous`, `not_found`, or `unsupported`:

- do not call any source
- do not load report/glossary data
- return a sanitized structured phase-slice failure
- include no raw resolver exception or local path

### 9.3 Other supported securities

If the resolver returns a supported security other than `KRX:005930`:

```json
{
  "status": "unsupported_for_fixture_slice",
  "resolved_security_id": "KRX:000660",
  "required_reference_security_id": "KRX:005930"
}
```

Do not create new SK hynix or Hyundai Motor report fixtures in M1-08.

### 9.4 CLI boundary

The M1-08 CLI uses only the fixed reference query:

```powershell
python scripts/m1_phase_slice.py
```

Do not expose a general `--query` option in M1-08. Query variants and out-of-scope securities are exercised through unit tests of the pure builder.

## 10. Provider and Ingest Mapping

Use the resolved `SecurityIdentifier`; do not hardcode one.

### News

Call through `fetch_with_policy()`:

```python
await fetch_with_policy(
    news_provider,
    security=resolved_security,
    config=config,
    query=None,
    date_range=REFERENCE_DATE_RANGE,
    cache=None,
)
```

`query=None` intentionally lets the existing news provider build its canonical Samsung query.

### Disclosure

Call through `fetch_with_policy()`:

```python
await fetch_with_policy(
    disclosure_provider,
    security=resolved_security,
    config=config,
    query=None,
    date_range=REFERENCE_DATE_RANGE,
    cache=None,
)
```

Do not pass `"삼성전자"` to disclosure query matching. Disclosure query matching applies to report name, submitter, and remark rather than company selection.

### Research report

- load the existing synthetic manifest and normalized documents
- require manifest security ID `KRX:005930`
- require every generated document to contain the selected security in `primary_security_ids`
- call:

```python
build_manual_research_documents(
    manifest,
    documents,
    mode="synthetic_unit",
    as_of_date=REFERENCE_REPORT_AS_OF_DATE,
)
```

### Glossary

- call `evaluate_actual_glossary_coverage(Path("data/glossary.json"))`
- load and build the approved corpus index
- lookup `PER`
- build the `definition` locator
- expose only readiness identity fields, not glossary definition text

### Provider policy

M1-08 does not reimplement timeout, retry, deadline, or cache logic. It reuses `fetch_with_policy()`.

Use `cache=None` in the reference slice so repeated public payloads do not vary because of `from_cache`.

## 11. Async and Dependency-Injection Contract

Define pure orchestration boundaries:

```python
async def build_phase_slice(
    query: str,
    *,
    config: ProviderConfig,
    dependencies: PhaseSliceDependencies | None = None,
) -> dict[str, object]:
    ...

async def build_health_payload(
    *,
    dependencies: PhaseSliceDependencies | None = None,
) -> dict[str, object]:
    ...
```

`PhaseSliceDependencies` may contain resolver/provider instances or factories and fixed fixture paths.

Requirements:

- default dependencies are created only when a builder is called
- importing `app.api.main` must not read fixtures, inspect environment variables, or run the event loop
- tests can inject fake providers/loaders without modifying existing provider modules
- news and disclosure calls execute in fixed order
- report and glossary checks execute after successful resolution
- no mutable global cache or accumulated state
- no `os.chdir()` or working-directory mutation

Project commands must be run from the repository root because the approved actual-glossary evaluator accepts the project-relative path `data/glossary.json`.

## 12. Document Selection and Sanitization

For every counted document:

- it must be a valid `FinancialDocument`
- selected security ID must be in `primary_security_ids`
- a wrong-company document must not be counted
- source type must match its source bucket

For each source:

1. sort documents by `document_id`
2. count all valid selected-security documents
3. choose the first document as the sample

`sample_documents` order is fixed:

1. news
2. disclosure
3. research_report

Each sample object has exactly these fields:

```json
{
  "document_id": "stable-id",
  "source_type": "news",
  "provider": "recorded_news",
  "title": "synthetic title"
}
```

Forbidden sample fields:

- `text`
- `locator`
- `metadata`
- `source_url`
- local path
- raw fixture item
- provider message
- exception or traceback

## 13. Health Payload Contract

Successful clean-environment reference payload:

```json
{
  "status": "ok",
  "version": "m1-08",
  "mode": "fixture_readiness",
  "live_connectivity_checked": false,
  "environment": {
    "status": "ok",
    "timeout_seconds": 8.0,
    "retry_count": 1,
    "total_deadline_seconds": 20.0,
    "cache_ttl_seconds": 300.0,
    "opendart_api_key_configured": false,
    "naver_client_id_configured": false,
    "naver_client_secret_configured": false
  },
  "sources": {
    "news": {
      "status": "ok",
      "mode": "recorded_fixture",
      "live_connectivity_checked": false,
      "document_count": 1,
      "expected_document_count": 1
    },
    "disclosure": {
      "status": "ok",
      "mode": "recorded_fixture",
      "live_connectivity_checked": false,
      "document_count": 1,
      "expected_document_count": 1
    },
    "research_report": {
      "status": "ok",
      "mode": "synthetic_manual_ingest",
      "document_count": 2,
      "expected_document_count": 2
    },
    "glossary": {
      "status": "ok",
      "mode": "approved_local_corpus",
      "actual_coverage": true,
      "meets_minimum": true,
      "lookup_status": "found",
      "entry_id": "glossary:per",
      "locator_section": "definition"
    }
  },
  "phase_slice": {
    "status": "ok",
    "scope": "representative_single_security",
    "query": "삼성전자",
    "security_id": "KRX:005930",
    "security_name": "삼성전자",
    "ticker": "005930",
    "date_start": "2026-07-21",
    "date_end": "2026-07-21",
    "financial_document_source_count": 3,
    "financial_document_count": 4,
    "sample_documents": []
  }
}
```

The actual successful `sample_documents` list contains exactly three sanitized sample objects.

M1-08 `/health` verifies local config and deterministic fixture readiness. It does not verify live NAVER, OpenDART, report-source, or external LLM connectivity.

Credential values are never included. Numeric config values may be included; credentials appear only as configured booleans.

## 14. Status Aggregation

### `ok`

All conditions hold:

- config valid
- default query resolved to `KRX:005930`
- provider status is `ok` for news and disclosure
- document counts equal `1`, `1`, and `2`
- all counted documents are selected-security documents
- distinct FinancialDocument source count is `3`
- total FinancialDocument count is `4`
- glossary actual coverage is true
- glossary minimum is met
- representative glossary lookup and locator succeed
- public payload safety validation succeeds

### `degraded`

Payload creation succeeds, but at least one readiness condition fails:

- provider `no_data`
- provider `invalid_query`
- provider `unauthorized`
- provider `rate_limited`
- provider `timeout`
- provider `provider_unavailable`
- provider `parse_error`
- unexpected document count
- report validation failure
- glossary readiness failure
- selected-security document filtering leaves a required source empty

Preserve provider status values for news/disclosure. For local checks use M1-08-only values such as:

- `validation_error`
- `not_ready`
- `unexpected_document_count`

Do not modify the core status enum.

### `error`

Use for:

- invalid config
- resolver initialization failure
- default reference query is not resolved
- unsupported reference identity
- health contract construction failure
- unexpected orchestration failure before a usable readiness payload exists

Do not include raw exception messages.

## 15. HTTP and CLI Status Contract

### FastAPI

`GET /health` has no query parameter.

Map payload status explicitly:

```text
ok       -> HTTP 200
degraded -> HTTP 503
error    -> HTTP 503
```

The route must use `JSONResponse` or an equivalent explicit status-code response. A plain returned dict that always produces HTTP 200 is not acceptable.

The route must defensively convert an unexpected builder exception into a sanitized `error` payload with HTTP 503.

### Phase-slice CLI

```text
0 -> ok
1 -> degraded
2 -> error
```

The CLI:

- calls `asyncio.run(build_health_payload())`
- writes JSON only
- does not print traceback, raw exception, credential, or absolute path
- uses deterministic key and list ordering
- may support formatting only if formatting does not alter semantics

## 16. API Application Contract

Create:

```python
# app/api/main.py
app = FastAPI(...)
app.include_router(health_router)
```

Requirements:

- only `/health` is introduced
- no startup live calls
- no startup fixture loads
- no startup credential validation
- no CORS/auth/database/vector configuration in M1-08
- import smoke must succeed without credentials
- route response body follows Section 13
- generated OpenAPI is incidental and not a separate scope item

Local run command documented in README:

```powershell
python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000
```

## 17. Public Payload Safety

Implement a recursive safety check for health and CLI payloads.

At minimum reject:

- Windows drive absolute paths
- UNC paths
- POSIX absolute paths
- `file://` paths
- known secret sentinel values used by tests
- forbidden sample keys listed in Section 12
- exception and traceback objects
- raw provider result messages

The safety checker itself must raise a typed M1-08 error with a fixed message and must not echo the unsafe value.

Tests must serialize the final payload to JSON and inspect the serialized form.

## 18. Secret Scan Contract

The scanner is a conservative committed-content check, not a replacement for GitHub secret scanning.

### 18.1 Tracked files

Use:

```text
git ls-files -z
```

Implementation boundary:

```python
def list_tracked_files(repo_root: Path) -> tuple[Path, ...]:
    ...

def scan_paths(
    paths: Iterable[Path],
    *,
    repo_root: Path,
) -> list[SecretFinding]:
    ...
```

Requirements:

- use `subprocess` with `shell=False`
- use repository root as `cwd`
- apply a finite timeout
- process NUL-separated bytes
- accept only relative tracked paths
- reject paths that escape the repository root
- inspect only approved text extensions
- a Git execution failure is scanner failure, not a clean result
- do not print raw Git stderr

Credential-scan text extensions:

- `.py`
- `.json`
- `.md`
- `.toml`
- `.example`
- `.yml`
- `.yaml`
- `.txt`
- `.ini`
- `.cfg`
- `.conf`
- `.env` and files whose name starts with `.env`

### 18.2 Credential rules

Detect non-empty assignments for at least:

- `OPENDART_API_KEY`
- `NAVER_CLIENT_ID`
- `NAVER_CLIENT_SECRET`
- `LLM_API_KEY`
- `api_key`
- `access_token`
- `auth_token`
- `bearer_token`
- `client_secret`
- `authorization`
- `x-api-key`

Allow empty placeholders, including:

```text
OPENDART_API_KEY=
NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=
LLM_API_KEY=
```

Assignment detection must distinguish committed credential values from arbitrary `key=value` substrings.

- For exact environment keys, recognize assignment forms such as `.env`/shell assignments and quoted JSON, YAML, TOML, or mapping keys.
- For generic or prefixed variable names such as `api_key`, `opendart_api_key`, `client_secret`, or `naver_client_secret`, report only a direct non-empty literal assignment. Runtime environment reads or references such as `os.getenv("OPENDART_API_KEY")`, `os.environ[...]`, `${OPENDART_API_KEY}`, and test-helper calls are not hardcoded credential findings by themselves.
- Do not treat URL query parameters, regex source text, prose, or a key embedded inside a larger unrelated token as credential assignments.
- Existing committed validation tests contain unsafe URL samples such as `...?api-key=secret` and `...?ACCESS_TOKEN=secret`. They must not be findings because they are string-literal URL query parameters used to test rejection, not configuration assignments.

Do not broadly exclude `tests/**`.

Sentinel tests should construct dangerous configuration assignments in temporary files without embedding a complete matching credential assignment as a contiguous committed source line. If an allowlist is unavoidable, it must be exact and include relative path, rule ID, and a stable normalized-line hash.

### 18.3 Public path rule

Do not run a blanket local-path regex across every Python file or historical internal Task Card. That would match validator patterns and audit logs rather than public exposure.

Apply the static public-path rule to these release/public surfaces:

- `README.md`
- `.env.example`
- `pyproject.toml`
- `data/**/*.json`
- `.github/**/*.yml`
- `.github/**/*.yaml`

Health and CLI JSON receive the separate recursive runtime check in Section 17.

Credential rules still apply to all approved tracked text extensions, including internal Task Cards.

### 18.4 Finding model

Output only:

```json
{
  "path": "relative/file",
  "line": 14,
  "rule_id": "non_empty_api_key_assignment"
}
```

Never output:

- full line
- credential value
- raw match
- surrounding context
- absolute repository path

Sort findings by:

```text
path, line, rule_id
```

### 18.5 Scanner exit codes

```text
0 -> no findings
1 -> one or more potential findings
2 -> scanner execution failure
```

Scanner errors use a fixed sanitized message.

## 19. README Requirements

`README.md` is required.

Include:

- project purpose in one short paragraph
- Python requirement
- dependency installation
- empty environment-variable placeholders
- fixture-readiness meaning
- explicit warning that live connectivity is not checked
- API run command
- `GET /health` example
- fixed phase-slice CLI command
- secret scan command and exit codes
- targeted/regression test commands
- repository-root execution requirement

Do not include:

- real credentials
- non-empty credential examples
- local absolute paths
- claims that recorded fixtures prove external API availability
- claims that synthetic research reports are actual corpus coverage
- M1 milestone completion while M1-09 is open

## 20. Previous Task Card Status Synchronization

Permit status-only changes.

### `docs/TASK_CARDS/M1-07-glossary-ingest.md`

Record:

- M1-07B final supplement SHA: `40543c425b8f5c0d6987940536be83a5a7b7a96a`
- M1-07B final supplement main push: `complete`
- M1-07B final independent review: `PASS`
- M1-07B: `complete`
- Actual glossary corpus: `PASS`
- Actual coverage 15+: `PASS`

### `docs/TASK_CARDS/M1-07B-glossary-corpus.md`

Record:

- Final supplement SHA: `40543c425b8f5c0d6987940536be83a5a7b7a96a`
- Final supplement main push: `complete`
- Final independent review: `PASS`
- M1-07B final status: `complete`
- GitHub CI: preserve `NOT_RUN`
- Independent pytest rerun: preserve the actual recorded state unless the review execution really occurred

Do not alter approved glossary content, fingerprint, or fact-check matrix during status synchronization.

## 21. Required Tests

### 21.1 Config

- clean environment defaults
- configured flags without credential values
- invalid float
- invalid integer
- non-finite numeric input
- invalid range
- response and serialized response exclude raw environment values
- config failure produces top-level `error`

### 21.2 Resolver and reference scope

- default query resolves to `KRX:005930`
- ticker, security ID, and approved Samsung aliases resolve to the same reference security
- ambiguous query returns structured failure without source calls
- not-found query returns structured failure without source calls
- unsupported query returns structured failure without source calls
- SK hynix and Hyundai Motor return `unsupported_for_fixture_slice`
- no report/glossary load occurs for rejected scope

Use injected spies/counters to prove sources were not called.

### 21.3 Provider policy and mapping

- news is called through the existing policy wrapper with `query=None`
- disclosure is called through the existing policy wrapper with `query=None`
- both use the fixed date range
- config timeout/retry/deadline values are passed through the existing wrapper
- no local cache changes public output
- report manifest security matches selected security
- every counted document has selected security in `primary_security_ids`
- wrong-company documents are excluded

### 21.4 Exact reference result

- news count is exactly `1`
- disclosure count is exactly `1`
- research report count is exactly `2`
- source count is exactly `3`
- total document count is exactly `4`
- samples are exactly three
- sample source order is news, disclosure, research_report
- each source selects the first `document_id` after sorting

### 21.5 Glossary

- actual coverage true
- minimum true
- lookup `PER` found
- returned entry ID `glossary:per`
- definition locator succeeds
- glossary content text is absent from public payload

### 21.6 Determinism

- repeated builder calls produce equal payloads in the same environment
- source order fixed
- sample selection fixed
- provider `fetched_at` and `from_cache` are not exposed
- no runtime timestamp is exposed
- caller mutation of injected source data does not change an already built payload

### 21.7 Failure normalization

At minimum:

- news `no_data`
- news `timeout`
- disclosure `parse_error`
- disclosure `provider_unavailable`
- unexpected provider exception
- report validation failure
- glossary readiness failure
- invalid config
- resolver initialization failure
- unexpected top-level builder exception

For each:

- correct top-level status
- correct source status
- zero count for failed source
- no raw message
- no exception type
- no traceback
- no local path
- no credential sentinel

### 21.8 Public payload safety

- exact sample key whitelist
- `text`, `locator`, `metadata`, and `source_url` absent
- recursive Windows/UNC/POSIX/file-URI rejection
- serialized JSON contains no test secret
- unsafe value is not echoed in error text

### 21.9 Secret scanner

- tracked-file-only behavior
- untracked secret file ignored
- non-empty credential assignment detected
- direct hardcoded literal assignment to a generic or prefixed credential variable is detected
- empty `.env.example` placeholder allowed
- `os.getenv(...)`, `os.environ[...]`, environment-reference syntax, and test-helper calls do not create credential false positives
- committed URL-query validation samples such as `api-key=secret` and `ACCESS_TOKEN=secret` do not create credential false positives
- redacted finding fields only
- deterministic finding order
- no raw match or value in JSON
- public-path rule detects a public absolute path
- Python validator regex does not create a path false positive
- internal Task Card audit path is outside the public-path rule
- Git command failure returns exit code `2`
- decode/read failure returns exit code `2`
- current repository scan returns `0`

### 21.10 API

Using an actual TestClient/HTTPX request:

- `GET /health` exists
- no query parameter required
- ok response returns HTTP `200`
- degraded response returns HTTP `503`
- invalid config/error returns HTTP `503`
- unexpected builder failure returns sanitized HTTP `503`
- response JSON contract matches Section 13
- `mode == "fixture_readiness"`
- `live_connectivity_checked is False`
- no credential value
- no local path
- API module import performs no source/config work

### 21.11 CLI

- fixed reference execution returns exit `0`
- degraded injected execution returns exit `1`
- error injected execution returns exit `2`
- output is valid JSON
- output contains no traceback, secret, or local path
- no arbitrary query argument is accepted

## 22. Verification Commands

Install/update the approved dependencies using the project’s selected environment and record the exact command.

### Targeted

```powershell
$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_health_phase_slice.py tests/unit/test_secret_scan.py tests/unit/test_api_health.py -q
```

### Regression

```powershell
$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_core_models.py tests/unit/test_status_contracts.py tests/unit/test_security_resolver.py tests/unit/test_provider_base.py tests/unit/test_config.py tests/unit/test_news_provider.py tests/unit/test_disclosure_provider.py tests/unit/test_report_ingest.py tests/unit/test_glossary_ingest.py tests/unit/test_health_phase_slice.py tests/unit/test_secret_scan.py tests/unit/test_api_health.py -q
```

### Phase-slice CLI smoke

```powershell
$env:PYTHONPATH = ".deps;."; python scripts/m1_phase_slice.py
```

Expected:

```text
exit code 0
status = ok
mode = fixture_readiness
financial_document_count = 4
```

### Secret scan

```powershell
python scripts/secret_scan.py
```

Expected exit code:

```text
0
```

### API request smoke

```powershell
$env:PYTHONPATH = ".deps;."; python -c "from fastapi.testclient import TestClient; from app.api.main import app; response=TestClient(app).get('/health'); body=response.json(); print(response.status_code, body['status'], body['mode'])"
```

Expected:

```text
200 ok fixture_readiness
```

### API import smoke

```powershell
$env:PYTHONPATH = ".deps;."; python -c "from app.api.main import app; print('ok')"
```

### Compile

```powershell
python -m compileall app tests scripts -q
```

Record commands, exit codes, passed counts, and smoke output. Record initial environment/dependency failures separately from successful reruns.

## 23. Completion Criteria

- [x] approved dependencies added
- [x] README created
- [x] side-effect-free FastAPI app import
- [x] `GET /health` implemented
- [x] fixture-readiness/live-connectivity distinction explicit
- [x] clean config summary passes
- [x] provider policy wrapper reused
- [x] Samsung reference scope enforced
- [x] provider-specific query mapping enforced
- [x] exact dates and exact document counts pass
- [x] three source samples sanitized and deterministic
- [x] glossary readiness and representative locator pass
- [x] top-level/HTTP/CLI statuses pass
- [x] runtime payload safety passes
- [x] tracked-file scanner passes with zero findings
- [x] scanner failure and redaction tests pass
- [x] M1-07/M1-07B status sync complete
- [x] targeted tests pass
- [x] M1 regression passes
- [x] CLI smoke passes
- [x] API request smoke passes
- [x] secret scan passes
- [x] compile passes
- [x] GitHub CI accurately recorded
- [x] commit/push accurately recorded
- [x] completion described as B3/M1-06~08 readiness completion, not entire M1 completion

## 24. Stop Conditions

Stop and report instead of guessing when:

- implementation requires core model/status/resolver/provider/ingest changes
- fixed fixtures do not produce exact counts `1/1/2`
- selected security cannot be proven primary for every counted document
- actual glossary readiness no longer passes
- a real credential or unsafe committed path is found
- secret scan cannot distinguish an actual finding from an unavoidable committed false positive without a narrow documented rule
- FastAPI, Uvicorn, or HTTPX cannot be installed compatibly
- `/health` would require live calls
- source behavior requires real data
- an unrelated previous regression fails
- M1-09, retrieval, Evidence, LLM, UI, deployment, or live API work becomes necessary

Do not modify fixtures or previous contracts to force the slice to pass.

## 25. Implementation Result Log

Current execution status after implementation:

- Implementation: `PASS`
- Dependency install: `PASS after sandbox/network retry`
- Targeted tests: `PASS`
- Regression tests: `PASS`
- CLI smoke: `PASS`
- API request smoke: `PASS`
- Secret scan: `PASS`
- Compile: `PASS`
- GitHub CI: `NOT_RUN`
- Independent pytest rerun: `NOT_RUN`
- Commit/push: `NOT_RUN`

Detailed executed commands and results are recorded below.

### 25.1 Implementation Result Log

- Implementation scope:
  - Added `app/phase_slice.py`, `app/health.py`, FastAPI `/health`, fixed phase-slice CLI, tracked-file secret scanner, README, and M1-08 unit tests.
  - Reused existing `SecurityResolver`, `ProviderConfig`, `fetch_with_policy()`, `RecordedNewsProvider`, `RecordedDisclosureProvider`, report ingest, and glossary ingest.
  - Did not modify core models/status, resolver, provider modules, config, ingest modules, data files, or fixtures.
- Dependency install first command: `python -m pip install --target .deps "pydantic>=2.7,<3" "fastapi>=0.115,<1" "uvicorn>=0.30,<1" "pytest>=8,<9" "httpx>=0.27,<1"`
  - exit code: `1`
  - result: package index access unavailable in sandbox; no dependency success claimed.
- Dependency install rerun command: `python -m pip install --target .deps "pydantic>=2.7,<3" "fastapi>=0.115,<1" "uvicorn>=0.30,<1" "pytest>=8,<9" "httpx>=0.27,<1"`
  - execution: approved elevated run
  - exit code: `0`
  - result: installed `fastapi-0.139.2`, `uvicorn-0.51.0`, `httpx-0.28.1`, and existing approved dependency set in `.deps`; pip warned that previously installed target directories already existed.
- Targeted first command: `$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_health_phase_slice.py tests/unit/test_secret_scan.py tests/unit/test_api_health.py -q`
  - exit code: `1`
  - result: sandbox denied access to `.deps\pytest\__init__.py`.
- Targeted second command: `$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_health_phase_slice.py tests/unit/test_secret_scan.py tests/unit/test_api_health.py -q`
  - execution: approved elevated run
  - exit code: `1`
  - passed count: `40 passed`
  - failure count: `2 failed`
  - fix: narrowed secret scanner to avoid typed attribute/runtime-variable false positives, added `X-Amz-Signature` normalization, and tightened runtime public payload safety to JSON-safe values.
- Targeted final command: `$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_health_phase_slice.py tests/unit/test_secret_scan.py tests/unit/test_api_health.py -q`
  - execution: approved elevated run
  - exit code: `0`
  - passed count: `42 passed`
  - warning: FastAPI TestClient emitted Starlette deprecation warning for `httpx`.
- Regression command: `$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_core_models.py tests/unit/test_status_contracts.py tests/unit/test_security_resolver.py tests/unit/test_provider_base.py tests/unit/test_config.py tests/unit/test_news_provider.py tests/unit/test_disclosure_provider.py tests/unit/test_report_ingest.py tests/unit/test_glossary_ingest.py tests/unit/test_health_phase_slice.py tests/unit/test_secret_scan.py tests/unit/test_api_health.py -q`
  - execution: approved elevated run
  - exit code: `0`
  - passed count: `657 passed`
  - warning: FastAPI TestClient emitted Starlette deprecation warning for `httpx`.
- Phase-slice CLI smoke command: `$env:PYTHONPATH = ".deps;."; python scripts/m1_phase_slice.py`
  - execution: approved elevated run
  - exit code: `0`
  - output summary: `status=ok`, `mode=fixture_readiness`, `financial_document_count=4`
- Secret scan command: `python scripts/secret_scan.py`
  - exit code: `0`
  - output: `[]`
- Additional prospective scan of approved new/modified files:
  - command: `python -c "from pathlib import Path; from scripts.secret_scan import scan_paths; paths=[Path(p) for p in [...approved new/modified files...]]; print(scan_paths(paths, repo_root=Path.cwd()))"`
  - exit code: `0`
  - output: `[]`
- API request smoke command: `$env:PYTHONPATH = ".deps;."; python -c "from fastapi.testclient import TestClient; from app.api.main import app; response=TestClient(app).get('/health'); body=response.json(); print(response.status_code, body['status'], body['mode'])"`
  - execution: approved elevated run
  - exit code: `0`
  - output: `200 ok fixture_readiness`
  - warning: FastAPI TestClient emitted Starlette deprecation warning for `httpx`.
- API import smoke command: `$env:PYTHONPATH = ".deps;."; python -c "from app.api.main import app; print('ok')"`
  - execution: approved elevated run
  - exit code: `0`
  - output: `ok`
- Compile command: `python -m compileall app tests scripts -q`
  - exit code: `0`
- GitHub CI: `NOT_RUN`
- Independent pytest rerun: `NOT_RUN`
- Commit/push: `NOT_RUN`
- B3/M1-06~08 readiness completion: `USER REVIEW PENDING`
- Full M1 milestone completion: `NOT_CLAIMED - M1-09 MarketSnapshot remains open`
