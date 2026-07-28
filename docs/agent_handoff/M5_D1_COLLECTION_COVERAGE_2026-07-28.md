# M5-D1-1 Collection Coverage — 2026-07-28

> Branch: `feature/m5-d1-evidence-crosscheck`
> Base: `40f58b3df7a53c3386e9653fd3b061f010b31335`
> Result: `LOCAL PASS / HUMAN OWNER REVIEW REQUIRED`
> Runtime, Git publication, and deployment: `NOT_CHANGED / NOT_RUN`

## 1. Scope and artifact boundary

This checkpoint implements only the news and OpenDART source inventory needed
before event discovery.

- news cutoff:
  `2026-07-24 00:00 KST` through `2026-07-27 21:00 KST`
- disclosures:
  `2026-01-01` through `2026-07-27`
- securities:
  Samsung Electronics, SK hynix, Hyundai Motor
- raw responses and the generated full inventory:
  Git-ignored local working storage
- committed surfaces:
  collector, normalized inventory contract, tests, and this coverage summary
- event selection, event grouping, Gemini classification, DART full-document
  download, answer integration, and UI integration:
  `NOT_RUN`

Collection remained provider-first:

```text
broad company, alias, and business-keyword queries
→ temporal and security normalization
→ coverage inventory
→ later event discovery
```

No event was chosen before collection.

## 2. News coverage

Normalization removed only exact canonical-URL duplicates and tracking-only URL
variants. Equal titles from different publisher hosts remain eligible.

| Security | Total | Publisher hosts | 07-24 | 07-25 | 07-26 | 07-27 |
|---|---:|---:|---:|---:|---:|---:|
| Samsung Electronics | 79 | 65 | 5 | 3 | 1 | 70 |
| SK hynix | 54 | 36 | 10 | 8 | 13 | 23 |
| Hyundai Motor | 167 | 105 | 53 | 24 | 24 | 66 |

Rejection inventory:

- outside the allowed time window: `9,353`
- security relevance not established: `1,107`
- exact canonical-URL duplicate: `301`
- retained: `300`

The retained inventory uses source titles and link metadata only. It does not
claim article-body coverage.

### SK hynix coverage repair

The initial `8`-item result was caused mainly by normalization, not by the
absence of collected candidates. The original Naver responses contained
additional articles whose titles were event-focused but identified SK hynix
in the provider description instead of the title.

The bounded repair retains:

- title alias match:
  `13`
- provider-description alias match:
  `41`

The description fallback applies only to SK hynix, requires the exact company
alias within the first `100` normalized description characters, and also
requires a stock, semiconductor, memory, earnings, or directly related event
term in the title. The provider description is used only for relevance
matching and is not stored in the normalized public inventory.

These `41` items are candidates, not claim evidence. M5-D1-2 must still reject
context-only or unrelated event members. No second provider and no additional
API request were used for this repair.

## 3. OpenDART coverage

Official corporation-code mappings were checked for:

- Samsung Electronics:
  stock code `005930`, corporation code `00126380`
- SK hynix:
  stock code `000660`, corporation code `00164779`
- Hyundai Motor:
  stock code `005380`, corporation code `00164742`

The retained metadata query uses official disclosure groups `A`, `B`, `C`,
`E`, and `I`: periodic reports, material reports, issuance disclosures, other
material disclosures, and exchange disclosures. Bulk ownership-only collection
was not used for this bounded event-background inventory.

| Security | Total | Periodic | Material event | Securities | Ownership-like | Other |
|---|---:|---:|---:|---:|---:|---:|
| Samsung Electronics | 65 | 2 | 21 | 0 | 12 | 30 |
| SK hynix | 77 | 2 | 25 | 10 | 5 | 35 |
| Hyundai Motor | 63 | 2 | 24 | 0 | 3 | 34 |

`Ownership-like` is a local report-name classification of items actually
returned inside the selected official query groups. It is not proof that an
item is event-relevant.

Correction state inventory:

| Security | Original | Correction | Superseded | Withdrawal |
|---|---:|---:|---:|---:|
| Samsung Electronics | 51 | 8 | 6 | 0 |
| SK hynix | 47 | 19 | 11 | 0 |
| Hyundai Motor | 57 | 3 | 3 | 0 |

OpenDART list metadata exposes the filing date but not a trustworthy
time-of-day for this collector. The inventory therefore marks each filing as
available only at `23:59:59 KST` on its filing date. This conservative rule
prevents a same-day earlier checkpoint from using a filing whose exact
publication time is unknown.

Correction lineage remains `candidate_only` until receipt-level predecessor
relationships are verified. An `rm=정` original is marked `superseded`; a
report-name correction prefix is marked `correction`; `rm=철` is marked
`withdrawal`.

## 4. Provider calls and failed attempts

The retained inventory records its acquisition provenance as:

- Naver API: `114` requests
- OpenDART API: `16` requests
- Gemini: `0` requests

Actual OpenDART development attempts during this checkpoint were higher than
the planned `30`-request budget:

- first unfiltered attempt:
  stopped at `30` requests because Samsung Electronics alone returned
  `2,692` entries across `27` pages, dominated by non-target ownership data
- second filtered attempt:
  `22` requests; failed locally because unsupported detail filtering caused
  the same exchange disclosures to be returned three times
- filtered retained collection:
  `16` requests
- news-expansion rebuild before raw reuse existed:
  another `16` OpenDART requests
- final schema regeneration:
  `0` external requests; preserved raw files reused

Total OpenDART HTTP attempts in this implementation checkpoint: `84`, plus the
earlier one-call credential preflight already recorded in the Task Card.

Corrective action:

- official top-level query groups replace the unfiltered list call
- exchange disclosures are requested once
- complete news and filtered OpenDART raw inputs can now be replayed with
  `--reuse-news-raw --reuse-dart-raw`
- subsequent schema and normalization checks do not require provider calls

No credential value, article body, or external URL list is written to logs or
committed artifacts.

## 5. Validation

- source inventory live build:
  `PASS`
- no-provider raw replay:
  `PASS`
- retained counts:
  news `300`, disclosures `205`
- source inventory checksum:
  `338f2caed9757ab09024819f9cb333b74754f1d90399ef7869441eacb69c3124`
- repeated no-provider builds:
  same source checksum `PASS`
- focused unit tests:
  `24 passed`
- affected unit and integration tests:
  `255 passed`
- Ruff:
  `PASS`
- Python syntax compile:
  `PASS`
- warning:
  existing Python `3.14` / LangChain Pydantic V1 compatibility warning remains

This result proves the bounded collection and inventory contract only. It does
not prove event grouping, source independence, DART fact extraction, answer
quality, UI behavior, CI, deployment, or production behavior.

## 6. M5-D1-2 input decision

M5-D1-2 may use this inventory to build deterministic event candidates and
conservative source-lineage states after Human Owner approval.

The `41` provider-description candidates must remain separately labeled during
golden-set selection. They must not be treated as claim support or independent
sources until event membership and source lineage are verified.
