# TASK CARD — M5-D1 Evidence Cross-check

> Planning date: `2026-07-28`
> Planning base: `40f58b3df7a53c3386e9653fd3b061f010b31335`
> Status: `PASS / DEPLOYED / COMPLETE`
> Implementation:
> `M5-D1-0~M5-D1-6 PASS / DEPLOYED / COMPLETE`
> Git and deployment: `COMPLETE`

## 1. Authority and purpose

This Task Card is the execution standard for the proposed M5 differentiation
bundle. It may be implemented only after Human Owner approval.

The bundle adds a beginner-facing `근거 대조형 답변`:

- group coverage of the same company event
- avoid treating every republished article as independent confirmation
- distinguish common facts, differing interpretations, and unconfirmed parts
- link relevant DART disclosures as official confirmation or background
- explain evidence limits in natural Korean

This is a bounded extension of the current three-stock service. It is not a
general news search engine, a market-wide research platform, or an investment
recommendation feature.

## 2. Human Owner decisions recorded

- `OPENDART_API_KEY` is prepared locally. Its value must never be copied into
  a document, log, fixture, commit, prompt, or answer.
- Full research-report originals may be handled locally by work agents during
  preprocessing.
- On `2026-07-28`, the Human Owner supplied Samsung Securities report PDFs
  under `docs/questock_reports` and authorized a first-pass application after
  the SK hynix news coverage fix.
- The Human Owner later added Mirae Asset Securities and Kiwoom Securities
  reports, including the previously used Mirae Asset reports, and authorized
  report processing plus completion through M5-D1.
- The first pass may extract full PDF text only to Git-ignored local storage
  and may commit verified metadata, stable source URLs, hashes, page locators,
  and later Questock-authored summaries.
- Report originals, raw text, excerpts, and PDF bytes remain excluded from
  Git, runtime, and external LLM input.
- Verified Questock-authored report perspectives may be shown only in the
  collapsed evidence-comparison view. Raw report text, excerpts, PDF bytes,
  and target-price recommendations remain excluded.
- The selected-time UI and temporal cutoff remain correctness and demo
  contracts, not product differentiation. `As-of Replay` is not the
  differentiation target.
- Commit, push, PR, merge, deployment, paid provider calls, and new provider
  adoption require their normal separate authorization and record.

## 3. Current verified starting point

Repository inspection at the planning base found:

- supported securities:
  Samsung Electronics, SK hynix, Hyundai Motor
- current M5 news scope:
  Naver API title-only documents for `2026-07-24` through `2026-07-27`
- current normalization:
  exact URL duplicates and equal normalized titles are both removed before
  runtime corpus construction
- consequence:
  same-title coverage from different publishers can be lost before source
  lineage and event clustering are evaluated
- current disclosure scope:
  one fixed `2026 Q1` quarterly report per security, with hard-coded receipt
  numbers and a manually prepared fact matrix
- current DART transport:
  list API verification exists, but broad metadata collection, correction
  lineage, generic source-document parsing, and event linkage do not
- current answer system:
  source diversity, citations, missing-source states, hybrid routing, and
  temporal filtering exist
- missing differentiation model:
  no canonical event cluster, source-lineage status, or explicit
  consensus/conflict/unconfirmed comparison object exists

The current repository therefore contains quarterly reports, not a half-year
report. M5-D1 preserves those verified facts and adds only selected,
event-relevant disclosures.

## 4. Competitive conclusion and claim boundary

The detailed review is:

`docs/agent_handoff/COMPETITIVE_DIFFERENTIATION_REVIEW_2026-07-28.md`

Public official pages already confirm that other products provide individual
parts of the proposed feature:

- story clustering and cross-publisher comparison
- research plans, citations, and source-document navigation
- positive/negative factors, risks, events, and sentiment
- filing-backed numbers and audit links

M5-D1 must therefore not claim uniqueness for any single part. The defensible
product target is the combined flow:

```text
Korean stock event cluster
→ conservative source-lineage lower bound
→ DART official confirmation/background link
→ common fact / different interpretation / unconfirmed / missing
→ beginner-facing conversational answer
```

Allowed description:

> Questock aims to avoid overstating repeated coverage as independent evidence
> and explains what news and DART material agree on, interpret differently, or
> still do not establish.

Forbidden descriptions:

- industry first or market exclusive
- exact independent-source count without verified lineage
- a filing proves that a news event caused a price move
- consensus from one publisher or one source family

## 5. Phase 1 scope

### 5.1 Securities and answer dates

- Samsung Electronics
- SK hynix
- Hyundai Motor
- news event window:
  `2026-07-24 00:00 KST` through `2026-07-27 21:00 KST`
- every answer and comparison remains bounded by its existing selected
  checkpoint
- material published after the checkpoint is excluded even when it belongs to
  the same later-known event

### 5.2 News collection

Use the existing Naver API first.

Collection expands coverage by:

- company aliases and product/business keywords
- date-aware queries
- event-neutral broad queries before event discovery
- pagination within provider limits
- publisher host and publication time inventory
- per-security, per-day, per-checkpoint coverage reporting

Do not select an event first and then collect only confirming articles. The
required order is:

```text
broad collection
→ normalization
→ event discovery
→ evidence comparison
```

A second news provider is not included automatically. It may be proposed only
when the coverage report demonstrates a material Naver gap, with a separate
credential, terms, data-use, and implementation decision.

### 5.3 DART collection

Use official OpenDART interfaces:

- corporation code:
  `https://opendart.fss.or.kr/api/corpCode.xml`
- disclosure list:
  `https://opendart.fss.or.kr/api/list.json`
- original filing package for selected receipts:
  `https://opendart.fss.or.kr/api/document.xml`

Inventory all disclosure metadata for the three official corporation codes
from `2026-01-01` through each answer cutoff. This current-fiscal-year lookback
is for background linkage, not for claiming that old disclosures directly
caused a July price move.

Download and preprocess full filing bodies only for:

1. the current verified quarterly report
2. filings within the event window
3. earlier filings selected by a documented relevance rule for an identified
   news event

Candidate report names may include periodic reports, material contracts,
investment or production decisions, preliminary earnings, dividends,
securities/capital decisions, and other material filings actually returned by
the DART list. Do not invent coverage categories or assume that every filing is
relevant.

Required DART safeguards:

- verify stock code to official corporation code mapping
- preserve receipt number, filing time/date, report name, submitter, and viewer
  URL
- retain correction, withdrawal, and supersession lineage
- use the latest valid version at the answer cutoff
- exclude later corrections from earlier-checkpoint answers
- keep full source packages and extracted raw text in Git-ignored local
  working storage
- commit only verified facts, short Questock-authored summaries, stable
  locators, metadata, and permitted source links

### 5.4 Research reports

The final supplied report set is:

- publishers:
  Samsung Securities `6`, Mirae Asset Securities `6`, Kiwoom Securities `3`
- securities:
  Samsung Electronics `5`, SK hynix `5`, Hyundai Motor `5`
- supplied and selected:
  `15`
- date boundary:
  every supplied report available no later than `2026-07-27`; the SK hynix
  report dated `2026-06-25` is retained as valid background
- local preprocessing:
  full page text extraction in Git-ignored storage
- visual identity review:
  first page of all `15` PDFs rendered and checked; two image-only PDFs were
  accepted only after this visual check
- commit-safe inventory:
  verified identity metadata, official source URL, PDF hash, page count, and
  page-text checksums
- ordinary runtime corpus ingest:
  `0`
- comparison-ready Questock-authored perspectives:
  `15`, one per verified report, with a page-1 locator

Only the short Questock-authored perspective is available to the collapsed
comparison view. Report originals, extracted text, source excerpts, and PDF
bytes remain outside Git, ordinary runtime evidence, and external LLM input.
`external_llm_processing_allowed=false` remains fixed.

## 6. Data and processing design

### 6.1 Layered data flow

```text
provider raw inputs
→ normalized publisher instances
→ deterministic event candidates
→ bounded ambiguous-pair classification
→ conservative source-lineage status
→ DART relevance and role linking
→ EvidenceComparison
→ retrieval, composer, citations, and collapsed UI detail
```

### 6.2 Raw and normalized news

Raw responses remain immutable and Git-ignored.

Normalization may remove:

- exact provider item duplicates
- exact canonical URL duplicates
- tracking-only URL variants proven to resolve to the same article

Normalization must not remove an item only because another publisher used the
same normalized title. Same-title, different-publisher records remain available
for event grouping and lineage review.

Required normalized fields:

- `news_id`
- `security_id`
- `title`
- `publisher`
- `publisher_host`
- `published_at`
- `canonical_url`
- `provider_item_id` when available
- `content_level`
- `security_match_basis`
- `collected_at`
- `query_provenance`

### 6.3 Event cluster

Create a sidecar model instead of forcing event data into the existing
`FinancialDocument` contract.

Minimum `EventCluster` fields:

- `event_id`
- `security_ids`
- `event_label`
- `first_published_at`
- `last_published_at`
- `member_news_ids`
- `cluster_basis`
- `review_status`
- `cutoff_eligibility`

Deterministic similarity produces candidates. An optional bounded Gemini
classifier may decide only ambiguous same-event pairs. It must:

- use strict structured output
- receive only the minimum permitted title/metadata context
- create no facts, summaries, sources, or price explanations
- make at most one batch classification call per build partition
- use retry `0`
- fall back to conservative separate clusters on failure
- remain fake-client or disabled in deterministic CI

### 6.4 Source lineage

Source relationship status is:

- `confirmed_original`
- `confirmed_republication`
- `independent_candidate`
- `unknown`

The system must record the basis for every non-unknown status. Matching title,
publisher count, or similar wording alone cannot prove independent reporting.

Public wording uses a lower bound:

```text
확인된 독립 근거 N건 · 재배포 확인 M건 · 원출처 관계 미확인 K건
```

If origin is not verifiable, use `unknown`. Never convert `unknown` to an
independent count for presentation.

### 6.5 DART fact and link

Use a generic verified claim record instead of adding another fixed
event-specific fact matrix:

- `topic`
- `claim_type`
- `claim_text`
- `value`, `unit`, and `period` when applicable
- `actual_or_estimate`
- `stance`
- `receipt_no`
- `source_locator`
- `verified_against_source`

Each event-to-disclosure link has one role:

- `official_confirmation`
- `official_background`
- `official_conflict`
- `no_link`

An old quarterly report normally supplies background. It becomes direct
confirmation only when the filing itself contains the same event fact and was
available before the answer cutoff.

### 6.6 Evidence comparison

`EvidenceComparison` contains:

- `event_id`
- `common_facts`
- each common fact's `corroboration_status`:
  `independently_corroborated`, `same_lineage_repeated`, or `lineage_unknown`
- `different_interpretations`
- `unconfirmed_claims`
- `missing_evidence`
- `disclosure_links`
- `source_lineage_summary`
- claim-level citations
- `comparison_status`

Rules:

- one publisher or one source family cannot create a consensus
- `common_facts` require at least two eligible articles and claim-level support
- repeated claims from one confirmed source family may be described only as
  `여러 기사에 반복 보도됨`, not independently confirmed
- `독립적으로 확인됨` requires at least two eligible, separately supported
  source families or one eligible source plus matching official DART
  confirmation
- unknown lineage cannot be promoted to independent corroboration
- wording differences alone are not a conflict
- a conflict requires incompatible claims about the same attribute, entity,
  and period
- missing DART linkage is `no_link`, not evidence that the news is false
- no numeric confidence score is shown unless a later calibrated evaluation
  authorizes one

## 7. Answer and UI contract

Keep the existing natural answer as the primary UI. Do not return a rigid
source dump.

When comparison evidence exists, add one collapsed section:

`근거 대조 보기`

It may contain only the applicable items:

- 이 사건을 다룬 기사
- 확인된 독립 근거와 원출처 미확인 건
- 공통으로 확인된 사실
- 기사마다 다른 해석
- DART에서 확인되는 공식 배경
- 아직 확인되지 않은 점

The section must not force a fixed number of bullets. Source links remain
compact and claim-linked. If no valid cluster or DART link exists, the current
answer path remains available and states the evidence limitation without
fabrication.

## 8. Work bundles

### M5-D1-0 — plan approval and contract freeze

- Human Owner approves or revises this Task Card
- freeze schemas, raw/runtime boundary, and evaluation labels
- record provider-call budget before any live collection or Gemini use

Exit:

`PLAN APPROVED / IMPLEMENTATION AUTHORIZED`

### M5-D1-1 — collection and coverage inventory

- verify official DART corporation codes
- collect broad Naver raw inputs
- collect DART metadata inventory
- produce coverage reports by company, day, publisher, and time
- preserve existing corpus and runtime behavior

Exit:

- credential-safe preflight
- deterministic inventory artifacts
- no event selected before collection

### M5-D1-1R — bounded report first pass

- discover supplied PDFs across the three approved publishers and official
  source maps
- select every supplied report available through the phase-1 cutoff
- visually verify first-page identity
- extract full page text to Git-ignored local storage
- emit only commit-safe metadata and page checksums
- keep corpus ingest, external LLM processing, runtime, and event linking
  disabled

Exit:

- selected reports: `15`
- excluded outside-window reports: `0`
- runtime-ready reports: `0`
- no PDF, raw text, excerpt, or local path in the public inventory

### M5-D1-2 — normalization, event grouping, and lineage

- retain same-title different-publisher instances
- implement event sidecar schema
- implement deterministic grouping and conservative lineage
- add optional ambiguous-pair classifier only if needed

Exit:

- labeled grouping set
- no unsupported independent-source claim

### M5-D1-3 — DART preprocessing and event linkage

- select event-relevant filing packages from the metadata inventory
- parse full local originals
- create verified generic fact records and locators
- classify disclosure role per event

Exit:

- every committed fact has a source locator
- corrections and temporal cutoffs pass

### M5-D1-4 — retrieval, answer, and UI integration

- retrieve cluster and disclosure sidecars
- add comparison context without destabilizing ordinary answers
- render the optional collapsed comparison section
- preserve hybrid routing, citation, and safety contracts

Exit:

- natural answer quality retained
- comparison claims are citation-bound

### M5-D1-5 — evaluation and regression

- freeze the labeled golden set
- run focused, affected, full regression, Ruff, compile, secret scan, and diff
  check
- perform a bounded Human Owner demo only after local gates pass

Exit:

`LOCAL PASS / HUMAN OWNER REVIEW READY`

### M5-D1-6 — publication and deployment

Only after separate authorization:

- commit
- push
- PR and CI
- merge
- deployment
- production verification

Each stage is recorded separately. A passed local evaluation is not a deployed
result.

## 9. Parallel work boundary

After M5-D1-0 schema freeze, work agents may run these independent lanes:

- Naver collection and coverage inventory
- OpenDART metadata, correction, and source-package inventory
- golden-set labeling and evaluation fixtures

One integration owner must control shared schemas, runtime corpus changes,
retrieval, composer, and UI. Multiple agents must not edit the same corpus,
schema, or Source of Truth file concurrently.

Research-report preprocessing is not one of the phase 1 lanes.

## 10. Acceptance tests

### News and event tests

- exact URL duplicate is removed
- same title from different publishers survives normalization
- same event is grouped
- similar keywords from different events remain separate
- post-cutoff article is absent
- one publisher cannot produce consensus
- one confirmed source family repeated by several publishers cannot produce
  independent corroboration
- republication is not claimed without evidence
- unknown lineage is not counted as independent

### DART tests

- official stock-to-corporation mapping matches
- all returned pages are collected for the bounded period
- current valid correction is selected
- later correction is absent from an earlier answer
- withdrawn or superseded filing is not treated as current
- old filing is background, not a direct price-move cause
- selected full-body fact matches its committed locator
- no relevant filing produces explicit `no_link`

### Comparison and answer tests

- wrong-company comparison claims: `0`
- unsupported common-fact claims: `0`
- unsupported conflict claims: `0`
- future evidence: `0`
- direct investment advice: `0`
- every displayed comparison claim has supporting citation(s)
- comparison absence falls back without breaking ordinary Q&A
- price, price-move, issue, risk, disclosure, term, and follow-up regressions
  preserve current behavior
- loading and cleared-input UI regressions preserve current behavior

## 11. Evaluation

Build a small manually labeled set from all three securities. Separate build
examples from held-out evaluation events.

Report:

- pairwise event-grouping precision
- pairwise event-grouping recall
- source-lineage claimed precision
- DART role accuracy
- claim citation support
- unsupported consensus/conflict count
- temporal leakage count
- abstention/unknown rate
- ordinary-answer regression failures

Initial release gates:

- pairwise event-grouping precision: at least `0.90`
- recall: reported, with no initial minimum; under-grouping is safer than
  merging unrelated events
- false `confirmed_original` or `confirmed_republication`: `0`
- false independent-source claim: `0`
- unsupported comparison claim: `0`
- wrong-company claim: `0`
- future evidence: `0`
- citation support for public comparison claims: `100%`
- all current critical safety and release regressions pass

The same event cases must not be used both to tune thresholds and to claim
held-out performance.

## 12. Stop conditions

Stop and return to Human Owner review when:

- title/snippet-only news cannot support a requested factual comparison
- source origin cannot be verified
- DART parsing cannot preserve a stable locator
- an additional news API or dependency appears necessary
- report data becomes necessary for the phase 1 acceptance gate
- scope expands to real-time streaming, new securities, prediction, or advice
- implementation would require weakening citation, temporal, safety, or secret
  controls

Required degradation:

- insufficient article content:
  show cluster/coverage only, not a fabricated agreement or conflict
- unverified source origin:
  `unknown`
- DART parser uncertainty:
  metadata and manually verified facts only
- no relevant disclosure:
  `no_link`

## 13. Expected implementation surfaces

Exact filenames are finalized in M5-D1-0. The expected bounded surfaces are:

- news collector and normalization service
- new event-cluster and evidence-comparison sidecar schemas
- OpenDART metadata/source-package collector and curator
- retrieval/context/composer integration
- optional collapsed Streamlit comparison view
- unit, integration, UI, evaluation, and release-contract tests
- task card, work log, and Source of Truth synchronization

Do not replace the whole `FinancialDocument`, query planner, hybrid router, or
answer system unless a focused proof shows that a sidecar extension cannot
meet the acceptance contract.

## 14. Current execution record

- competitive recheck: `COMPLETE`
- planning: `COMPLETE`
- Human Owner plan approval: `APPROVED on 2026-07-28`
- implementation branch:
  `feature/m5-d1-evidence-crosscheck`
- implementation:
  `M5-D1-0~M5-D1-6 PASS / DEPLOYED / COMPLETE`
- M5-D1-1 collection and coverage inventory:
  `LOCAL PASS`
- M5-D1-1R multi-publisher report preparation:
  `LOCAL PASS / RAW REPORT RUNTIME NOT ENABLED`
- coverage record:
  `docs/agent_handoff/M5_D1_COLLECTION_COVERAGE_2026-07-28.md`
- report first-pass record:
  `docs/agent_handoff/M5_D1_REPORT_FIRST_PASS_2026-07-28.md`
- implementation review:
  `docs/agent_handoff/M5_D1_IMPLEMENTATION_REVIEW_2026-07-28.md`;
  `PASS` for the bounded M5-D1-1 and M5-D1-1R scope
- provider-call budget:
  - Naver API: maximum `120` requests for the initial inventory
  - OpenDART API: maximum `30` requests for the initial inventory and selected
    source-package checks
  - Gemini event classifier: `0` calls until deterministic grouping has been
    evaluated
- live OpenDART credential preflight: `PASS`; one successful official
  `list.json` request; key value not printed or recorded
- retained source inventory:
  - Naver news: `300`
  - OpenDART disclosures: `205`
  - checksum:
    `338f2caed9757ab09024819f9cb333b74754f1d90399ef7869441eacb69c3124`
- retained provider-call provenance:
  - Naver API: `114`
  - OpenDART API: `16`
- actual OpenDART implementation attempts:
  `84` requests in this checkpoint, plus the earlier one-call credential
  preflight; this exceeded the planned `30` request budget during two failed
  collection designs and one pre-reuse rebuild
- raw replay without external calls: `PASS`
- SK hynix coverage repair:
  `8 → 54`; `13` title-alias matches and `41` bounded provider-description
  matches; no second provider and no additional API request
- final supplied report inventory:
  `15` discovered and selected; Samsung Securities `6`, Mirae Asset
  Securities `6`, Kiwoom Securities `3`; five reports per security;
  ordinary runtime-ready raw reports `0`
- report extraction:
  text `9`, partial text `4`, image-only `2`; all `15` first pages visually
  verified
- report inventory source checksum:
  `a6de59840104c49554fc4686f1907504727576e8cb1335b76cfc0578961ebe62`
- report inventory file checksum:
  `22ff6aabbdb89c701e00b22f5f4559bf2d1f093647f68af7e261afcfabbcf928`
- M5-D1-2 event grouping and conservative lineage:
  `LOCAL PASS`; direct event clusters `7`, clustered article instances `43`,
  confirmed independent `0`, confirmed republication `0`
- post-review direct-evidence boundary:
  an article may enter a company event cluster only when the company alias is
  present in the title; description-only matches remain available as indirect
  source candidates but cannot act as direct company-event evidence
- M5-D1-3 DART and report linkage:
  `LOCAL PASS`; comparison-ready Questock-authored report perspectives `15`,
  DART background records `34`; event-window title metadata is background
  only, while concrete facts remain limited to existing page-verified
  quarterly-report facts
- post-review relevance boundary:
  report and DART links require event-specific topic overlap; broad sector or
  category similarity alone is insufficient
- M5-D1-4 runtime and collapsed UI integration:
  `LOCAL PASS`; a cluster with more than `20` eligible articles reports both
  the total count and the displayed count
- M5-D1-5 held-out event-pair evaluation:
  `8` pairs, precision `1.00`, recall `1.00`, false positives `0`
- comparison sidecar checksum:
  `9d8a246181b39058ac9c35d2750ea19aba48de058fad0929874748295add0148`
- completion record:
  `docs/agent_handoff/M5_D1_COMPLETION_2026-07-28.md`
- live Naver collection: `PASS`
- Gemini event-classifier calls: `NOT_RUN`
- latest focused report and M5-D1 tests: `18 passed`
- latest affected chat/runtime/UI/M5 tests: `193 passed`
- latest full regression: `2189 passed, 2 warnings`
- Ruff: `PASS`
- Python syntax compile: `PASS`
- scoped secret scan: `PASS / findings 0`
- existing Python `3.14` / LangChain Pydantic V1 warning:
  `OPEN / NON-BLOCKING FOR THIS CHECKPOINT`
- documentation diff check: `PASS`
- implementation commit:
  `95b98555bd588134148a9104f733d6f85f00480b`
- pull request:
  `#26`
- release SHA:
  `373ea00d4e06526a98898e9c38f4d4a7871b1a8f`
- PR quality gate:
  `30362235377`, `PASS`
- merged-main quality gate:
  `30362397614`, `PASS`
- deployment:
  run `30362550006`, `PASS`
- release image:
  `sha256:e8480098951728eeb4c2a5cb83a36bc5c03c5ee9b40c9286a10d212713ee57b5`
- rollback:
  `NOT_RUN` because deployment passed
- deployment closure:
  `docs/agent_handoff/M5_D1_DEPLOYMENT_CLOSURE_2026-07-28.md`
