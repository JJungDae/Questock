# TASK CARD — M5-01 As-of Price-Grounded Answer

## 1. Status and authority

- Planning date: `2026-07-28`
- Planning base: `bbcdc7352cf6791624b5de74ef7dc05ae6ecde88`
- Implementation base: PR `#18` merge
  `6f50ee922c2a1c74278ead2f679472ba3e19bc8b`
- Product scope: Samsung Electronics, SK hynix, Hyundai Motor
- Current status: `PASS / DEPLOYED / COMPLETE`
- API preflight: `PASS`
- Human Owner direction:
  - expose five selectable checkpoints for each date
  - add price-grounded answers after the FSC-4 answer-presentation follow-up
  - expand news after `2026-07-24 14:00 KST` through `2026-07-27`
  - prove that an answer never uses information later than the selected time
  - finish feature validation before optional model comparison

This Task Card is the execution standard for the M5-01 insertion scope. It
supplements the older M5-01 and Stretch M2-09 sections of
`PROJECT_PLAN_FINAL_PASS.md`. When those sections conflict with this Task Card
inside this scope, this Task Card and the latest
`SOURCE_OF_TRUTH_INDEX.md` take precedence.

This plan authorizes planning and later in-scope implementation only after the
Human Owner starts that implementation. Commit, push, PR, merge, deployment,
live API calls, and paid LLM calls remain separately recorded actions.

---

## 2. Goal

For one of the three supported stocks, a reviewer can select a historical date
and one of five checkpoints, ask an ordinary beginner question, and receive an
answer grounded only in:

- the latest valid market observation at or before the checkpoint
- news, disclosures, and report material available at or before the checkpoint
- the existing glossary and safety rules

M5-01 adds price, direction, change, and carefully worded price-move
background. It does not add prediction, target price, buy/sell/hold advice,
technical indicators, charting, new securities, or real-time streaming.

---

## 3. Fixed checkpoint matrix

The UI uses two controls: `date` and `checkpoint`. It must not expose one flat
twenty-item list.

Dates:

- `2026-07-24` — Friday, trading day
- `2026-07-25` — Saturday, closed
- `2026-07-26` — Sunday, closed
- `2026-07-27` — Monday, trading day

Five selectable checkpoints per date:

| UI label | checkpoint time | market meaning |
|---|---:|---|
| 장 전·프리마켓 | `08:30 KST` | NXT pre-market is already open |
| 장중 | `10:00 KST` | regular-session checkpoint |
| 장중 | `14:00 KST` | regular-session checkpoint |
| 애프터마켓 | `19:00 KST` | NXT after-market checkpoint |
| 전체 장 종료 후 | `21:00 KST` | query time after NXT closes; not a 21:00 trade |

Canonical checkpoint ID:

```text
YYYYMMDDTHHMMKST
```

Examples:

```text
20260724T0830KST
20260727T2100KST
```

The full matrix is `4 dates × 5 checkpoints = 20 checkpoints`. Across three
stocks the acceptance matrix is `60 stock/checkpoint cases`.

NXT officially operates pre-market `08:00~08:50`, main market
`09:00:30~15:20`, and after-market trading `15:40~20:00`. Therefore:

- `08:30` must not be described as a time before all trading
- `19:00` can contain NXT trades
- `21:00` uses the last real observation at or before market closure and keeps
  that observation's actual `observed_at`

On `2026-07-25` and `2026-07-26`, all five choices remain available for the
demo. They return:

- `market_status=closed`
- the latest valid observation from the preceding trading day
- the original observation time, not a fabricated weekend timestamp
- a plain-language closed-market notice
- news and other documents cut off at the selected weekend time

---

## 4. Market data source decision

### Primary source

Use Korea Investment & Securities Open API with a price-only REST adapter.

Relevant official interfaces:

- Open API setup and App Key/App Secret:
  <https://github.com/koreainvestment/open-trading-api#34-kis-open-api-%EC%8B%A0%EC%B2%AD-%EB%B0%8F-%EC%84%A4%EC%A0%95>
- historical minute bars:
  <https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/domestic_stock/inquire_time_dailychartprice/inquire_time_dailychartprice.py>
- current-day minute bars:
  <https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/domestic_stock/inquire_time_itemchartprice/inquire_time_itemchartprice.py>
- NXT market hours:
  <https://www.nextrade.co.kr/menu/transactionSys.do>

The official historical example accepts date and time, retains up to one year
of minute data, and exposes `J` (KRX), `NX` (NXT), and `UN` (integrated) market
codes. This is a better fit than a streaming feed for recorded historical
checkpoints.

### User preparation

Required:

1. Open or use an existing Korea Investment & Securities account and connect
   its ID.
2. Apply for the KIS Open API service.
3. Issue a production App Key and App Secret. A production key is required for
   the historical-data preflight; it does not authorize Questock to place
   orders.
4. Add the values to the existing local `.env` without sending them through
   chat:

```text
KIS_APP_KEY=<secret>
KIS_APP_SECRET=<secret>
```

Already available and retained:

```text
NAVER_CLIENT_ID
NAVER_CLIENT_SECRET
GEMINI_API_KEY
```

Not requested for the Questock price-only runtime:

- brokerage account number
- trading PIN
- order permission
- WebSocket key
- a separate paid stock-data subscription

The KIS signup or official sample configuration may ask for an account number
or HTS ID. Keep those outside Questock unless the focused price-only preflight
proves that a quotation endpoint technically requires one. Never log, commit,
or display credential values.

### Focused preflight gate

Before building the corpus, make the smallest possible live verification:

1. obtain one access token
2. query `005930`, `000660`, and `005380`
3. verify historical results for `2026-07-24` and `2026-07-27`
4. verify the `UN`, `NX`, and `J` market-code behavior around `08:30`, `10:00`,
   `14:00`, and `19:00`
5. verify that the latest observation at or before `21:00` is a real trade no
   later than the market close
6. record only sanitized counts, timestamps, and schema results

Preflight PASS requires:

- all three securities resolve
- price, previous close, change, percent, volume when available, and timestamp
  can be normalized
- timestamps are timezone-aware
- NXT/integrated observations are distinguishable
- no credential, token, account value, or raw response is logged

If historical NXT or integrated bars are missing, do not silently substitute a
KRX value at an NXT checkpoint. Record `no_data` for that route and use a
Human-Owner-approved recorded fallback only after the gap is explicit.

---

## 5. Recorded market snapshot contract

Raw KIS responses stay in a Git-ignored work area. Only normalized,
reproducible records and safe provenance metadata may enter the committed
service snapshot.

Each selected record contains at least:

```text
security_id
ticker
checkpoint_id
requested_as_of
observed_at
price
previous_close
change
change_percent
volume
market_code
market_session
market_status
currency
source
```

Selection rules:

1. convert the selected checkpoint to timezone-aware KST
2. select only observations with `observed_at <= requested_as_of`
3. use the latest valid observation at or before that time
4. never replace `observed_at` with the requested checkpoint
5. if an open market has not traded the stock yet, return `no_trade_yet` with
   an explicit prior-close reference
6. if the market is closed, keep the last valid prior observation and mark
   `market_status=closed`
7. provider timeout and empty data remain different statuses

The existing `MarketSnapshot` fields should be extended only where the
checkpoint contract cannot be expressed safely. Do not redesign unrelated
provider models.

---

## 6. Temporal evidence and future-information contract

`as_of` is a hard filter, not an LLM instruction.

Before ranking, composing, caching, or generating:

```text
market observation: observed_at <= as_of
news/disclosure/report evidence: published_at <= as_of
```

Rules:

- filtering happens before retrieval ranking
- an item with missing or unverified `published_at` is excluded from
  time-sensitive price-move reasoning
- the LLM receives only already-filtered evidence
- citations and public source links must obey the same cutoff
- the response exposes `basis_at` while retaining `basis_date` compatibility
- cache identity includes snapshot/corpus version and `checkpoint_id`
- changing the checkpoint starts a new time context or partitions session
  memory so a later answer cannot leak into an earlier checkpoint
- changing back to an earlier checkpoint must not reuse a later cached answer
- logs contain checkpoint ID and filtered counts, not raw prompts or evidence
  bodies

For price-move explanations:

- preceding or same-checkpoint material may be presented as a possible
  background factor
- do not claim one definitive cause
- do not use material later than the checkpoint, even as “subsequent
  background” in that answer
- separate verified price facts from interpretation
- retain direct-investment-advice and unsupported-number validation

---

## 7. News expansion

Retain the approved `2026-07-24 00:00~14:00 KST` corpus and collect:

- `2026-07-24 14:00~23:59:59 KST`
- all of `2026-07-25`
- all of `2026-07-26`
- all of `2026-07-27`

Replace the old five-news-per-stock service cap with:

```text
normalized storage cap: at most 15 relevant, deduplicated news items
                        per stock per calendar date
period cap:             at most 60 news items per stock for the four dates
answer retrieval cap:   at most 6 news Evidence items per request
```

These are maxima, not quotas. Do not add irrelevant market commentary merely
to fill a count. Prefer direct company, business, contract, product, earnings,
regulatory, supply-chain, and analyst-event coverage. Retain exact publication
timestamps and source URLs. Raw candidates and rejection files remain
Git-ignored.

The system uses one expanded corpus plus time filtering. It does not create
twenty copied news corpora.

---

## 8. Answer and UI behavior

### UI

- date selector plus five checkpoint buttons/options
- selected `기준 시점`, `시장 상태`, and actual `가격 관측 시각` visible near
  the answer
- price summary shown only when a valid snapshot exists
- weekend and after-close wording must be explicit
- changing the checkpoint clears or separates the visible conversation
- question input remains at the bottom and clears after submission
- the completed answer must not coexist with a loading message
- sources remain compact title/link rows

### Answer types

Simple price question:

- selected-time price
- change and change percent against the correct previous close
- market status and observation time

Price-move/background question:

- short conclusion
- verified price movement
- one or more relevant candidate factors when available
- uncertainty and missing coverage
- compact source links

General company, disclosure, report, and glossary questions:

- preserve the FSC-4 question-adaptive answer contract
- do not force a price section when it does not help the question

“오늘”, “현재”, and “최근” are interpreted relative to the selected
checkpoint, not the machine clock.

---

## 9. Implementation sequence

### M5-00 — base and API preflight

- integrate the FSC-4 answer-presentation follow-up before branching M5 work
- inspect current Source of Truth and clean implementation base
- add KIS config names and secret-safe health status
- run the focused historical minute-bar preflight

Stop if the required checkpoint data cannot be obtained or safely normalized.

### M5-01A — data collection and normalization

- add a KIS price-only collector/normalizer
- create the 60-case checkpoint fixture
- expand and curate the news window
- rebuild the deterministic service snapshot
- prove repeated builds are byte-identical

Likely target areas:

- `scripts/`
- `app/providers/market.py`
- `app/services/service_snapshot.py`
- `app/services/service_snapshot_gateway.py`
- `tests/fixtures/market/`
- service snapshot manifests and validators

### M5-01B — hard temporal filtering

- add timezone-aware `as_of` to request/retrieval contracts
- filter documents and market observations before ranking
- isolate cache and session state by checkpoint
- expose `basis_at` safely

Likely target areas:

- `app/api/schemas.py`
- `app/retrieval/filters.py`
- `app/services/chat_service.py`
- `app/services/response_cache.py`
- `app/services/session_store.py`

### M5-01C — answer composition and UI

- route price and price-move questions
- join MarketSnapshot with filtered Evidence
- add candidate-factor wording and uncertainty
- implement the date/checkpoint controls and price context
- preserve the FSC-4 conversational presentation

Likely target areas:

- query planning and retrieval
- answer composer and validators
- `app/ui/app.py`
- `app/ui/projections.py`

### M5-01D — evaluation, closure, and deployment

- pass focused, Critical, golden, and full regression
- run a bounded Gemini acceptance only after deterministic tests pass
- update Task Card, work log, Source of Truth, and presentation evidence
- deploy only after explicit Human Owner approval

### M5-01E — optional model comparison

Run Flash versus Pro only if all required M5-01 gates have passed and at least
90 minutes of presentation buffer remains. Model comparison must not delay
future-leakage, price-accuracy, UI, or deployment validation.

---

## 10. Required tests and evaluation

### Deterministic contract tests

- all 60 stock/checkpoint cases resolve to the expected status and observation
- exact `08:30`, `10:00`, `14:00`, `19:00`, and `21:00` boundaries
- Friday and Monday trading behavior
- Saturday and Sunday closed-market behavior
- integrated/NXT/KRX source distinction
- `no_trade_yet`, `no_data`, timeout, parse error, and unavailable paths
- exact price, previous close, change, percent, sign, and observation time
- document at exactly `as_of` included
- document one second after `as_of` excluded
- evidence, citation, cache, and session future leakage: zero
- selecting a later checkpoint and returning to an earlier one remains clean
- “오늘/현재/최근” resolves against selected time
- no completed-answer/loading-message overlap

### Golden evaluation

Add a time-aware set covering:

- direct price questions
- rise/fall/background questions
- weekend and after-market questions
- general company questions where price is not forced
- follow-up questions after changing checkpoints
- no-evidence and provider-failure cases

Required hard metrics:

```text
future-information leakage: 0
wrong-company evidence: 0
unsupported price/percent/time: 0
direct investment advice: 0
price/direction/percent deterministic accuracy: 100%
Critical set: 100%
```

Quality metrics, scored separately:

- question relevance
- evidence groundedness
- citation support
- beginner clarity
- sufficient detail without forced section counts
- uncertainty calibration

Do not treat LLM rubric scores alone as proof of temporal or numeric
correctness. Those are deterministic gates.

---

## 11. Time and stop rules

Required order for the remaining implementation day:

1. FSC-4 presentation follow-up integration
2. KIS preflight
3. price/news data build
4. temporal filter and state isolation
5. answer/UI integration
6. deterministic and golden evaluation
7. documentation and deployment
8. optional model comparison

If time slips:

- drop model comparison first
- reduce live LLM samples before reducing deterministic coverage
- do not drop future-information tests
- do not silently replace missing NXT data
- do not expand beyond the three stocks or add charts
- use additional presentation time only for a blocking M5 correctness issue,
  not optional polish

---

## 12. Completion criteria

M5-01 is complete only when:

- KIS preflight is PASS or an explicit approved recorded fallback is used
- the three stocks × twenty checkpoints matrix is present
- price facts and observation times are correct
- future-information leakage is zero across retrieval, cache, session, answer,
  and citation output
- the expanded news corpus is deterministic and time-filterable
- price questions and ordinary FSC-4 questions both remain useful
- weekend, no-data, and provider-failure behavior is understandable
- Critical, golden, full regression, and deployment smoke satisfy their gates
- the Human Owner approves deployment
- Source of Truth and work logs match the actual Git and deployment state

---

## 13. Implementation and release evidence

Status as of `2026-07-28`:

- PR `#18` was merged before M5 implementation:
  - merge SHA:
    `6f50ee922c2a1c74278ead2f679472ba3e19bc8b`
  - quality-gate run `30323480083`: `PASS`
  - PR `#18` deployment: `NOT_STARTED`
- KIS historical minute-bar preflight: `PASS`
  - production quotation credentials present locally
  - all three securities resolved
  - raw responses and token cache remain Git-ignored
  - credential, token, account, article body, and raw response exposure: `0`
- normalized market snapshot:
  - three stocks × twenty checkpoints = `60` records
  - future observation count: `0`
  - weekend closed-market records: `30`
  - checksum:
    `438138c4be2da03c170787376d56367ea27cdf1f551b2f80f6f4cfbf85f14849`
- expanded title-only news:
  - collection window: after `2026-07-24 14:00 KST` through
    `2026-07-27`
  - retained after deterministic relevance filtering: `7`
  - Samsung Electronics `4`, SK hynix `1`, Hyundai Motor `2`
  - checksum:
    `c963ba0d909b0866185169eccf165bea0b50b449d32a935ed8170f64b8cc1a90`
- temporal and state contract:
  - exact `as_of` evidence included
  - one-second-future evidence excluded
  - response cache and session memory partitioned by checkpoint
  - weekend and after-close answers retain the actual prior observation time
- answer and UI:
  - direct selected-time price and previous-close comparison implemented
  - price-move answers separate verified movement from possible background
  - date and five-checkpoint selectors implemented
  - checkpoint changes clear the visible conversation and change session scope
  - interactive local browser checks passed for trading-day and weekend cases
- deterministic validation:
  - M5 golden set: `8 passed`
  - full regression: `2111 passed, 2 warnings`
  - Ruff over `app`, `scripts`, and `tests`: `PASS`
  - tracked and new M5-file secret scans: `PASS`, findings `[]`
  - M3 executable gate: `34/34`, with the prior M3-12 inactive price boundary
    explicitly promoted to `ACTIVATED_IN_M5`
- bounded live Gemini acceptance:
  - provider calls: `2`
  - model: `gemini/gemini-3.5-flash`
  - recent-issue answer: `PASS`, public status `complete`
  - price-move answer: `PASS`, public status `partial`
  - live verified: `2/2`
  - future evidence count: `0`
- optional Flash-versus-Pro comparison: `NOT_RUN`
- implementation release:
  - implementation commit:
    `eb72b91b27fa7d6885551a6be255faf6ef6007d1`
  - PR `#19`: `MERGED`
  - merge SHA:
    `d6a5b6a9f7cd7e3027e5842693fcab6aca312127`
  - PR quality-gate run `30327176594`: `PASS`
  - merged-main quality-gate run `30327274970`: `PASS`
- deployed-browser closure:
  - the first production browser pass verified the selected-time price and a
    Gemini price-move answer, then exposed a stale prior-chat render after a
    checkpoint change
  - PRs `#20` and `#21` added checkpoint state reset and callback handling;
    production verification showed that state changed but the old Streamlit
    chat DOM could still remain
  - PR `#22` added an explicitly cleared conversation placeholder
  - PR `#22` merge/deployed SHA:
    `824f06f014415fd66ad9bbd1c9743f03be02efcc`
  - PR quality-gate run `30329244843`: `PASS`
  - merged-main quality-gate run `30329322602`: `PASS`
  - deployment run `30329400059`: `PASS`
  - deployed image:
    `sha256:b91c9ec9bf6cada77167c68606a565c0854f06ac168fa4d9f321934c5e9df42a`
  - API/UI health, recorded snapshot `54` documents, and `7` release-smoke
    scenarios: `PASS`
  - final production browser:
    - `2026-07-27 14:00 KST` Samsung Electronics price answer: `PASS`
    - switching to `2026-07-25` removed the prior question and answer from the
      DOM and changed the session: `PASS`
    - `2026-07-25 21:00 KST` closed-market answer used the
      `2026-07-24 19:59 KST` last trade, `252,500` KRW and `-6.48%`: `PASS`
    - completed-answer/loading-message overlap: `0`
  - rollback target:
    `40dca28ed9c9a93d6ebf7c95161fda52ec1e01ef` /
    `sha256:f0283455a40679c405ed1ae5489d2444de199f31bbdba97675a029509a52b359`
  - rollback execution: `NOT_RUN` because the final deployment passed

M5-01 satisfies its required implementation, validation, deployment, smoke,
and documentation criteria. Optional Flash-versus-Pro comparison remains
outside completion and was not run.
