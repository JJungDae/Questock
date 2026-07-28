# M5-D1 Review Fix Closure — 2026-07-28

## Result

`LOCAL PASS / REVIEW FINDINGS CLOSED / HUMAN OWNER CHECK READY`

## Accepted findings and closure

### 1. SK hynix direct-evidence misclassification

The article was relevant to the broader AI semiconductor environment but did
not identify SK hynix or Samsung Electronics in its title. It was therefore
not suitable as direct company-event evidence.

Closure:

- direct event clusters accept only `title_alias` company matches
- `provider_description_alias` items remain in the collected inventory as
  indirect candidates
- no direct SK hynix event cluster is emitted from the current data

### 2. Report and DART links were too loose

Broad sector and category topics had allowed unrelated quarterly figures,
reports, and filing facts to appear beside an event.

Closure:

- event links require at least one event-specific topic after generic topics
  are removed
- verified filing-body facts derive specific topics from the actual committed
  claim text
- filing-list metadata is separately labeled as
  `official_list_metadata`
- the Hyundai Motor fall event links to the second-quarter preliminary
  earnings filing available at the cutoff
- the Samsung Electronics–Broadcom event has no report perspective and an
  explicit DART `no_link`

### 3. Evaluation did not detect generated-data relevance defects

Closure:

- generated sidecar tests require schema v2, `7` direct clusters, `43`
  article members, and `title_alias_only` for every cluster
- regression tests cover the SK hynix abstention, Hyundai filing link,
  Samsung–Broadcom no-link behavior, and the Samsung HBM4 background link

### 4. Cutoff ranking used a later cluster timestamp

Closure:

- candidate ranking now uses the latest article eligible at the selected
  cutoff
- a synthetic future-tail regression test verifies that a later ineligible
  article cannot make an older event win

### 5. Total article count and displayed links were ambiguous

Closure:

- the public contract exposes `article_total_count` and
  `article_displayed_count`
- the UI displays `전체 27건 중 20건 표시` for the HBM5 event
- the lineage total remains the full eligible count

## Validation

- focused report and M5-D1 tests:
  `18 passed, 1 warning`
- full regression:
  `2189 passed, 2 warnings`
- Ruff:
  `PASS`
- Python syntax compile:
  `PASS`
- tracked-file and changed/new-file scoped secret scans:
  `PASS`, findings `0`
- diff whitespace check:
  `PASS`; line-ending conversion warnings only
- external API and Gemini calls:
  `NOT_RUN`

The Python `3.14` / LangChain Pydantic V1 and Starlette/httpx warnings are
pre-existing and did not fail this checkpoint.

## Current artifact

- comparison sidecar:
  `data/m5_d1_evidence_comparisons.json`
- SHA-256:
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

## Later publication and deployment

The Human Owner subsequently authorized the remaining stages.

- implementation commit:
  `95b98555bd588134148a9104f733d6f85f00480b`
- PR and merge:
  `#26` / `373ea00d4e06526a98898e9c38f4d4a7871b1a8f`
- PR and merged-main quality gates:
  `30362235377` / `30362397614`, both `PASS`
- GCE deployment:
  `30362550006`, `PASS`
- final status:
  `PASS / DEPLOYED / COMPLETE`
- deployment closure:
  `docs/agent_handoff/M5_D1_DEPLOYMENT_CLOSURE_2026-07-28.md`
