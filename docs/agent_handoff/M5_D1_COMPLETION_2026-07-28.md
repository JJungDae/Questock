# M5-D1 Local Completion — 2026-07-28

## Result

`LOCAL PASS / REVIEW FINDINGS CLOSED / HUMAN OWNER CHECK READY`

M5-D1 now adds a collapsed `근거 대조 보기` to eligible answers while keeping
the existing conversational answer as the primary response.

## Implemented scope

- retained source inventory:
  news `300`, OpenDART disclosure metadata `205`
- conservative multi-publisher event clusters:
  `7` direct-company clusters, `43` clustered article instances
- source lineage:
  unverified origin remains `unknown`; confirmed independent and confirmed
  republication counts remain `0`
- research reports:
  Samsung Securities `6`, Mirae Asset Securities `6`, Kiwoom Securities `3`
- company coverage:
  Samsung Electronics `5`, SK hynix `5`, Hyundai Motor `5`
- report handling:
  all `15` first pages visually verified; local text extraction status was
  full text `9`, partial text `4`, image-only `2`
- comparison-ready report layer:
  one Questock-authored page-1 perspective per report, `15` total
- DART comparison background:
  `34` records consisting of existing page-verified quarterly-report facts and
  event-window official list metadata

No event-window filing body fact was inferred from a report title. When only
DART list metadata is available, the UI says only that the filing was
submitted and treats it as official background, not direct confirmation.

## Public behavior

The collapsed section may show:

- articles grouped as the same event
- the conservative lineage lower bound
- Questock-authored perspectives from relevant verified reports
- DART official background or explicit `no_link`
- limitations caused by title-only news or unknown source origin

Title-only articles do not create `common_facts`, conflicts, or independent
confirmation. The section is omitted when fewer than two eligible articles
exist at the selected checkpoint or when a recognized event belongs to a
different company.

## Review hardening

The accepted implementation review findings were closed as follows:

- direct company-event clusters now require a company alias in the article
  title; description-only SK hynix matches remain indirect candidates and are
  not promoted to direct SK hynix evidence
- report and DART links now require event-specific topic overlap rather than
  broad sector or category similarity
- Hyundai Motor's `2026-07-24 19:00 KST` fall-event comparison links to the
  `2026-07-23` second-quarter preliminary earnings filing instead of first-
  quarter figures
- the Samsung Electronics–Broadcom event returns no report perspective and an
  explicit DART `no_link` because no event-specific link was verified
- cluster ranking uses the latest article eligible at the selected cutoff,
  not a later article in the full cluster
- the HBM5 cluster reports `전체 27건 중 20건 표시`, so the lineage total and
  visible link count are no longer ambiguous

## Data boundary

- report PDFs, raw extracted text, evidence excerpts, and local paths:
  Git ignored
- report originals or raw text in external LLM input:
  prohibited
- ordinary report runtime corpus ingest:
  `0`
- comparison runtime:
  short Questock-authored perspectives only
- Gemini event-classifier calls:
  `0`

## Evaluation

- held-out labeled title pairs:
  `8`
- pairwise precision:
  `1.00`
- pairwise recall:
  `1.00`
- false positive event merges:
  `0`
- false independent-source claims:
  `0`
- future-evidence failures in focused tests:
  `0`
- wrong-company comparison failures in focused tests:
  `0`
- focused M5-D1 and report tests:
  `18 passed`
- affected chat/runtime/UI/M5 regression:
  `193 passed`
- full regression:
  `2189 passed, 2 warnings`
- Ruff:
  `PASS`
- Python syntax compile:
  `PASS`
- scoped secret scan:
  `PASS`, findings `0`
- diff whitespace check:
  `PASS`; line-ending conversion warnings only

The labeled evaluation set is intentionally small and supports only this
bounded three-security demo window. It is not a claim of general market-wide
accuracy.

## Artifacts

- execution standard:
  `docs/TASK_CARDS/M5-D1-evidence-crosscheck.md`
- accepted-review closure:
  `docs/agent_handoff/M5_D1_REVIEW_FIX_CLOSURE_2026-07-28.md`
- report inventory:
  `data/m5_d1_report_inventory.json`
- public comparison sidecar:
  `data/m5_d1_evidence_comparisons.json`
- event-pair fixture:
  `tests/fixtures/m5_d1_event_pairs.json`

File SHA-256:

- report inventory:
  `22ff6aabbdb89c701e00b22f5f4559bf2d1f093647f68af7e261afcfabbcf928`
- comparison sidecar:
  `9d8a246181b39058ac9c35d2750ea19aba48de058fad0929874748295add0148`

## Publication boundary

- commit:
  `NOT_RUN`
- push:
  `NOT_RUN`
- PR:
  `NOT_RUN`
- merge:
  `NOT_RUN`
- deployment:
  `NOT_RUN`

These remain separate Human Owner-authorized stages.
