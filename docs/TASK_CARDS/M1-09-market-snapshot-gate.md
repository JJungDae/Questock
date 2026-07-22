# TASK CARD - M1-09 MarketSnapshot Stretch Qualification Gate

## 1. Status and Approval

- Task bundle: `Stretch M1-09`
- Step: `M1-09 MarketSnapshot adapter, timezone, market session fixture`
- Planning date: `2026-07-22`
- Planning base branch: `main`
- Planning base commit: `519e208fc4abdfc45d69418dc1cc60bb630011d8`
- M1-08 status: `PASS`
- M1-08 completion commit: `519e208fc4abdfc45d69418dc1cc60bb630011d8`
- Current status: `IMPLEMENTED - user review pending`
- Implementation approval: `APPROVED by user request`
- Commit/push/PR/merge/deploy: `NOT_APPROVED`
- Implementation SHA: `NOT_CREATED`
- Local gate decision: `A15-M data-qualified stretch candidate`
- GitHub CI: `NOT_RUN`
- Independent pytest rerun: `NOT_RUN`
- Live market data API: `OUT_OF_SCOPE`
- M2-09/M3-12 price-move implementation: `OUT_OF_SCOPE`

This Task Card is a planning artifact only. Approval of this plan may authorize M1-09 implementation and tests, but commit, push, PR, merge, deploy, live API calls, and M2/M3 work remain separate approval actions.

## 2. Goal and Boundary

M1-09 does not implement the final `price_move_reason` answer.

M1-09 only decides whether `A15-M` can remain a `data-qualified stretch candidate` by proving that the project can normalize deterministic market snapshots with:

- supported security identity
- price direction
- previous close
- change and change percent
- timezone-aware `observed_at`
- market session label
- normal, no-data, and timeout fixture paths

If this gate is not completed, `A15-M` remains P1 and `M2-09`, `M3-12`, and `price_move_reason` tests stay excluded.

## 3. Existing Verified Inputs

Use, do not redesign:

- `MarketSnapshot` model in `app/core/models.py`
- `ProviderStatus` in `app/core/status.py`
- `Provider` protocol, `create_provider_result()`, and `fetch_with_policy()` in `app/providers/base.py`
- canonical supported securities in `data/securities.json`
- M1-08 health/secret scan behavior

Do not change existing model fields or status enum values.

## 4. Fixed Scope

### Required

- `RecordedMarketSnapshotProvider`
- provider key: `recorded_market_snapshot`
- recorded fixture for all 3 supported common stocks
- at least one rising and one falling normal snapshot across the fixture set
- no-data fixture path
- timeout fixture path
- transport-independent market snapshot normalizer
- deterministic price direction helper for tests
- timezone-aware `observed_at`
- fixed market session validation
- security_id, ticker, market, security_name, and security_type validation against canonical fixture
- no live market API call
- no credential use

### Out of Scope

- live market data adapter
- provider credential configuration
- HTTP transport
- KRX calendar live validation
- historical OHLCV
- intraday charting
- technical indicators
- M2-09 temporal filter
- M3-12 price-move answer
- retrieval, EvidencePolicy, API, UI, LLM, Gemini, LiteLLM
- changing `MarketSnapshot`, `ProviderResult`, or status enums

## 5. Planned Files

### New files

- `app/providers/market.py`
- `tests/fixtures/market/market_snapshot_synthetic.json`
- `tests/unit/test_market_provider.py`

### Modified files

- `docs/TASK_CARDS/M1-09-market-snapshot-gate.md`
- `docs/TASK_CARDS/M1-08-health-config-phase-slice.md` for status-only synchronization
- `app/providers/__init__.py` for package export consistency

### Do not modify

- `app/core/models.py`
- `app/core/status.py`
- `app/providers/base.py`
- `app/config.py`
- `data/securities.json`
- M1-08 health/API/CLI files
- news, disclosure, report, glossary provider and ingest files

## 6. Contract

### 6.0 Fixture schema

The committed fixture uses the following fixed top-level structure:

```json
{
  "schema_version": 1,
  "snapshots": [
    {
      "security_id": "KRX:005930",
      "market": "KRX",
      "ticker": "005930",
      "security_name": "삼성전자",
      "security_type": "common_stock",
      "trading_date": "2026-07-21",
      "observed_at": "2026-07-21T15:30:00+09:00",
      "price": 71000,
      "previous_close": 70000,
      "change": 1000,
      "change_percent": 1.428571,
      "volume": 1000000,
      "market_session": "closing",
      "currency": "KRW"
    }
  ]
}
```

Fixture rules:

- top-level value must be an object
- `schema_version` must be real integer `1`; bool, string, and other integers fail
- `snapshots` must be a list
- every record must contain every field shown above
- record identity fields are validated before `MarketSnapshot` construction
- duplicate `(security_id, trading_date, observed_at)` records fail with `parse_error`
- unknown security IDs and identity drift from canonical security data fail with `parse_error`
- fixture records do not include provider status scenarios
- normalized output contains only existing `MarketSnapshot` fields; fixture-only identity fields are not added to the core model

### 6.1 Provider protocol

`RecordedMarketSnapshotProvider` implements the existing M1-03 provider protocol:

```python
async def fetch(
    self,
    security: SecurityIdentifier,
    query: str | None = None,
    date_range: DateRange | None = None,
    attempt_timeout_seconds: float = 8,
) -> ProviderResult[MarketSnapshot]:
    ...
```

`ProviderConfig` is not passed into `fetch()`. Retry, timeout, total deadline, and cache behavior remain owned by `fetch_with_policy()`.

The provider constructor must expose a testable boundary:

```python
def __init__(
    self,
    *,
    fixture_path: str | Path = DEFAULT_MARKET_FIXTURE_PATH,
    fixture_data: dict[str, Any] | None = None,
    fixture_status: ProviderStatus = ProviderStatus.OK,
    securities_path: str | Path = DEFAULT_SECURITIES_PATH,
    provider_key: str = RECORDED_MARKET_SNAPSHOT_PROVIDER_KEY,
) -> None:
    ...
```

Rules:

- `fixture_path` and `fixture_data` must not both be explicitly supplied
- `fixture_data` is used by tests without filesystem access
- `fixture_status` represents injected provider execution state, not snapshot content
- canonical security identity is validated through the existing `SecurityResolver` using `securities_path`

### 6.2 Result statuses

- `ok`: one normalized `MarketSnapshot`
- `no_data`: valid supported security, but no snapshot remains after security/date filtering
- `invalid_query`: normalized query is non-empty, the requested security is unsupported, the requested security is not `common_stock`, or the requested identity does not match canonical security data
- `timeout`: injected `fixture_status=ProviderStatus.TIMEOUT`
- `provider_unavailable`: fixture file missing, unreadable, or otherwise unavailable before schema parsing
- `parse_error`: JSON decoding, top-level schema, record schema, duplicate identity, numeric invariant, timezone, market-session, or fixture/canonical identity validation failure

All returned results must pass `create_provider_result()`.

The provider must not expose raw fixture paths, raw exception text, or failing record contents in `message`.

Fixture loading must not leak an exception from `fetch()`. File-access failures are normalized to `provider_unavailable`; decoded but malformed fixture content is normalized to `parse_error`.

### 6.3 Snapshot invariants

Identity:

- `security_id` equals `"{market}:{ticker}"` for the requested security
- requested security must be `common_stock`
- canonical identity is resolved from `data/securities.json` through the existing `SecurityResolver`
- requested and fixture `market`, `ticker`, `security_name`, and `security_type` must match canonical security data
- fixture-only identity fields are validated before normalization and are not added to `MarketSnapshot`
- unsupported ticker, preferred stock, unknown fixture security, or identity mismatch returns a sanitized failure status according to Section 6.2

Time:

- `trading_date` is a valid ISO date
- `observed_at` is an ISO-8601 timezone-aware datetime
- naive `observed_at` values fail
- output `observed_at` is normalized to UTC
- `trading_date` must equal the date obtained after converting `observed_at` to fixed KST `UTC+09:00`
- fixed KST uses `timezone(timedelta(hours=9))`; do not add timezone dependencies
- `market_session` is one of the project-owned fixture labels: `pre_market`, `regular`, `closing`, `after_close`, `closed`
- M1-09 validates label membership and KST date consistency only; it does not validate real KRX business days, holidays, official session hours, or temporary schedule changes

Numeric validation uses decimal strings before conversion to the existing float-based model:

```python
PRICE_CHANGE_TOLERANCE = Decimal("0.000001")
PERCENT_TOLERANCE = Decimal("0.000001")
```

- bool values are not accepted as numbers
- `NaN`, positive/negative infinity, and non-numeric strings fail
- `price > 0`
- `previous_close > 0`
- `change == price - previous_close` within `PRICE_CHANGE_TOLERANCE`
- `change_percent == change / previous_close * 100` within `PERCENT_TOLERANCE`
- `volume` is `None` or a real integer greater than or equal to 0; bool and fractional values fail
- `currency == "KRW"`
- normalized `source == provider.key`
- fixture `source` values, if present, are not trusted or copied
- local paths, raw fixture paths, credentials, failing values, and exception text are never exposed in provider messages

### 6.4 DateRange and deterministic selection

Selection order:

1. validate the complete fixture and canonical identities
2. select only records matching the requested `security_id`
3. apply `date_range.start` and `date_range.end` independently and inclusively when present
4. sort candidates by `(trading_date, observed_at)` ascending
5. return the final record
6. duplicate `(security_id, trading_date, observed_at)` records fail with `parse_error`

Behavior:

- `date_range=None`: return the latest fixture snapshot for the requested security
- start-only, end-only, and same-day ranges are supported
- no matching snapshot after filtering returns `no_data`
- malformed or reversed `DateRange` remains handled by existing model validation
- at least one supported security must have two fixture dates so latest selection and filtering are proven using the committed fixture

### 6.5 Query behavior

This provider is queryless and reuses `normalize_query()` from `app.providers.base`.

- `query is None` or `normalize_query(query) == ""`: allowed
- normalized non-empty query: `invalid_query`

Required cases include `None`, `""`, whitespace-only input, `"price"`, and `" 주가 "`.

### 6.6 Direction helper

Use a deterministic helper for tests only:

```text
change > 0  -> up
change < 0  -> down
change == 0 -> flat
```

Do not add a direction field to `MarketSnapshot`.

## 7. Fixture Plan

The primary synthetic recorded fixture should include:

- Samsung Electronics normal snapshot
- SK hynix normal snapshot
- Hyundai Motor normal snapshot
- at least one `up` case
- at least one `down` case
- at least one supported security with two different fixture dates
- no timeout, error, or status-only pseudo-records

Scenario representation:

- normal: committed `snapshots` records
- no data: valid security/date request with no matching record after filtering
- timeout: provider constructed with `fixture_status=ProviderStatus.TIMEOUT`
- provider unavailable: missing or unreadable temporary fixture path in tests
- malformed: temporary `fixture_data` or temporary fixture file generated in tests

Synthetic fixture success is not live market coverage. Live market data coverage remains `NOT_RUN`.

## 8. Tests

Targeted tests in `tests/unit/test_market_provider.py`:

- provider key is `recorded_market_snapshot`
- all 3 supported securities have canonical normal fixture coverage
- rising direction detected from `change`
- falling direction detected from `change`
- flat direction handled if fixture or synthetic test item uses zero change
- fixture top-level schema and `schema_version == 1` validated
- every required fixture field enforced
- duplicate `(security_id, trading_date, observed_at)` rejected
- timezone-aware `observed_at` is converted to UTC
- naive `observed_at` rejected
- KST date of `observed_at` matches `trading_date`
- market session labels validated without claiming live KRX calendar validation
- decimal tolerances are exactly `0.000001`
- `price`, `previous_close`, `change`, and `change_percent` invariants enforced
- bool, NaN, infinity, and non-numeric numeric inputs rejected
- `volume=None`, zero, and positive integer volume allowed
- negative, bool, and fractional volume rejected
- normalized `source` equals provider key
- fixture `source` is ignored or rejected rather than trusted
- requested security and fixture identity match canonical resolver data
- fixture identity drift returns `parse_error`
- preferred stock, unsupported ticker, wrong requested identity, or non-common-stock security returns `invalid_query`
- `None`, empty, and whitespace-only query allowed
- explicit normalized non-empty query returns `invalid_query`
- start-only, end-only, same-day, and both-boundary `date_range` filters are inclusive
- default selection returns deterministic latest `(trading_date, observed_at)` record
- no matching date returns `no_data`
- injected timeout status returns `timeout`
- missing/unreadable fixture returns `provider_unavailable`
- malformed JSON, top-level fixture, record, and numeric invariant return `parse_error`
- raw exception text, failing values, credentials, and local paths are not exposed
- repeated fixture load returns deterministic result
- caller mutation of `fixture_data` cannot change an already returned result
- provider output passes through `create_provider_result()`
- `fetch_with_policy()` can call the provider without changing provider signature
- direct module import and package-level export both succeed

Targeted:

```powershell
$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_market_provider.py -q
```

Regression scope:

```powershell
$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_core_models.py tests/unit/test_status_contracts.py tests/unit/test_security_resolver.py tests/unit/test_provider_base.py tests/unit/test_config.py tests/unit/test_news_provider.py tests/unit/test_disclosure_provider.py tests/unit/test_report_ingest.py tests/unit/test_glossary_ingest.py tests/unit/test_health_phase_slice.py tests/unit/test_phase_slice_cli.py tests/unit/test_secret_scan.py tests/unit/test_api_health.py tests/unit/test_market_provider.py -q
```

Smoke:

```powershell
$env:PYTHONPATH = ".deps;."; python -c "from app.providers.market import RecordedMarketSnapshotProvider; print('ok')"
```

Secret scan:

```powershell
python scripts/secret_scan.py
```

Compile:

```powershell
python -m compileall app tests scripts -q
```

## 9. Completion Criteria

- [x] `RecordedMarketSnapshotProvider` implemented
- [x] recorded market fixture created
- [x] all 3 supported securities covered by canonical normal snapshots
- [x] rising and falling fixture paths pass
- [x] no-data and timeout fixture paths pass
- [x] timezone-aware UTC `observed_at` enforced
- [x] market session labels validated
- [x] price/change/change_percent invariants enforced
- [x] provider output passes central `ProviderResult` factory
- [x] targeted tests pass
- [x] M1 regression passes
- [x] import smoke passes
- [x] secret scan passes
- [x] compile passes
- [x] M1-08 final status synchronization completed without changing its test/CI truth
- [x] GitHub CI accurately recorded
- [x] independent pytest rerun accurately recorded
- [x] commit/push state accurately recorded
- [x] live market data coverage recorded as `NOT_RUN`
- [x] A15-M status recorded as `data-qualified stretch candidate` or `P1 유지`

### 9.1 Gate decision rule

Record `A15-M: data-qualified stretch candidate` only when all of the following pass:

- canonical normal snapshots for all 3 supported securities
- at least one up and one down path
- deterministic latest and DateRange paths
- no-data, timeout, provider-unavailable, and parse-error paths
- canonical identity validation
- strict numeric invariants and fixed tolerances
- UTC normalization and KST trading-date consistency
- project-owned market-session labels
- targeted tests
- M1 regression
- compile
- direct and package import smoke
- secret scan

This decision does not mean:

- live market coverage
- real-time price support
- price-move causality support
- approval of M2-09 or M3-12
- P0 activation of A15-M

If any required gate item remains incomplete, record `A15-M: P1 유지`.

Either outcome completes the M1-09 qualification decision:

```text
qualified -> future M2-09/M3-12 planning may be considered separately
P1 유지   -> keep those tasks excluded and continue to B4
```

## 9.2 M1-08 status synchronization

Apply a status-only update to `docs/TASK_CARDS/M1-08-health-config-phase-slice.md`.

Record:

- Additional supplement SHA: `519e208fc4abdfc45d69418dc1cc60bb630011d8`
- Additional supplement main push: `complete`
- Final independent review: `PASS`
- M1-08 status: `complete`
- B3/M1-06~08 readiness completion: `PASS / complete`
- GitHub CI: preserve `NOT_RUN`
- Independent pytest rerun: preserve `NOT_RUN`

Do not alter M1-08 implementation contracts, test counts, or historical failure logs during this synchronization.

## 10. Risk IDs

- `R15` timeout
- `R18` provider status confusion
- `R33` post-event article causality
- `R34` missing external factor overclaim
- `R17` secret/local path exposure

## 11. Stop Conditions

Stop and report if:

- implementation requires changing `MarketSnapshot` fields
- implementation requires changing `ProviderStatus`
- implementation requires adding a dependency
- implementation requires live API credentials
- canonical security fixture conflicts with `data/securities.json`
- strict fixture schema or identity validation cannot be implemented without changing core models
- deterministic latest selection cannot be proven from the committed fixture
- numeric invariants require changing `MarketSnapshot`
- market session cannot be represented without official live calendar work
- tests require M2 retrieval, Evidence, API, UI, or LLM work
- synthetic fixture would be described as live market coverage
- A15-M activation would be claimed before M2-09/M3-12 approval

## 12. Fallback

If M1-09 cannot satisfy its gate within the approved scope:

- record `A15-M: P1 유지`
- exclude `M2-09`, `M3-12`, and `price_move_reason` from active scope
- continue to `B4: M2-01~03` with normal source routing, hard filter, and retrieval baseline

## 13. Implementation Order After Approval

1. Apply the status-only M1-08 completion synchronization.
2. Add the fixed-schema synthetic recorded market fixture.
3. Implement pure parser/normalizer helpers in `app/providers/market.py`.
4. Implement `RecordedMarketSnapshotProvider`.
5. Export the provider through `app/providers/__init__.py`.
6. Add targeted unit tests.
7. Run targeted tests.
8. Run M1 regression.
9. Run direct/package import smoke, secret scan, and compile.
10. Record actual results and the A15-M gate decision in this Task Card.
11. Report diff and results.
12. Wait for separate commit/push approval.

## 14. Implementation Result Log

- Implementation status: `PASS in local implementation environment - user review pending`
- Implementation SHA: `NOT_CREATED`
- Commit/push/PR/merge/deploy: `NOT_RUN`
- GitHub CI: `NOT_RUN`
- Independent pytest rerun: `NOT_RUN`
- Live market data coverage: `NOT_RUN`
- M2-09/M3-12/price_move_reason implementation: `NOT_RUN`
- A15-M gate decision: `data-qualified stretch candidate`

### 14.1 Modified Files

- `app/providers/market.py`
- `app/providers/__init__.py`
- `tests/fixtures/market/market_snapshot_synthetic.json`
- `tests/unit/test_market_provider.py`
- `docs/TASK_CARDS/M1-09-market-snapshot-gate.md`
- `docs/TASK_CARDS/M1-08-health-config-phase-slice.md`

### 14.2 Implemented Scope

- Added `RecordedMarketSnapshotProvider` with provider key `recorded_market_snapshot`.
- Added fixed-schema synthetic market snapshot fixture for Samsung Electronics, SK hynix, and Hyundai Motor.
- Added pure fixture parser/normalizer helpers with canonical security validation through `SecurityResolver`.
- Added Decimal-based price/change/change_percent validation with fixed `0.000001` tolerances.
- Added timezone-aware UTC normalization and fixed KST trading-date consistency checks.
- Added project-owned market session label validation without claiming live KRX calendar validation.
- Added no-data, timeout, provider-unavailable, invalid-query, and parse-error status paths.
- Exported `RecordedMarketSnapshotProvider` through `app.providers`.
- Did not add live market API, credentials, dependencies, M2-09, M3-12, retrieval, API, UI, LLM, Gemini, or LiteLLM code.

### 14.3 Verification Results

- Compile command: `python -m compileall app tests scripts -q`
  - exit code: `0`
- Targeted first command: `$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_market_provider.py -q`
  - execution: sandboxed run
  - exit code: `1`
  - output: `No module named pytest.__main__; 'pytest' is a package and cannot be directly executed`
- Targeted rerun command: `$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_market_provider.py -q`
  - execution: approved elevated run
  - exit code: `0`
  - passed count: `31 passed`
- Regression command: `$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_core_models.py tests/unit/test_status_contracts.py tests/unit/test_security_resolver.py tests/unit/test_provider_base.py tests/unit/test_config.py tests/unit/test_news_provider.py tests/unit/test_disclosure_provider.py tests/unit/test_report_ingest.py tests/unit/test_glossary_ingest.py tests/unit/test_health_phase_slice.py tests/unit/test_phase_slice_cli.py tests/unit/test_secret_scan.py tests/unit/test_api_health.py tests/unit/test_market_provider.py -q`
  - execution: approved elevated run
  - exit code: `0`
  - passed count: `753 passed`
  - warning: FastAPI TestClient emitted Starlette deprecation warning for `httpx`.
- Direct import smoke command: `$env:PYTHONPATH = ".deps;."; python -c "from app.providers.market import RecordedMarketSnapshotProvider; print('ok')"`
  - execution: approved elevated run
  - exit code: `0`
  - output: `ok`
- Package import smoke command: `$env:PYTHONPATH = ".deps;."; python -c "from app.providers import RecordedMarketSnapshotProvider; print('ok')"`
  - execution: approved elevated run
  - exit code: `0`
  - output: `ok`
- Secret scan command: `python scripts/secret_scan.py`
  - exit code: `0`
  - output: `[]`
- Compile final command: `python -m compileall app tests scripts -q`
  - exit code: `0`

### 14.4 Gate Decision

All M1-09 local implementation gate items passed in the local implementation environment.

Recorded status:

```text
A15-M: data-qualified stretch candidate
```

This does not activate A15-M as P0 and does not authorize M2-09 or M3-12. Future M2-09/M3-12 planning must be approved separately.
