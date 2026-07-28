# M5-D1-1R Multi-publisher Report Preparation — 2026-07-28

> Branch: `feature/m5-d1-evidence-crosscheck`
> Base: `40f58b3df7a53c3386e9653fd3b061f010b31335`
> Result: `LOCAL PASS / RAW REPORT RUNTIME NOT ENABLED`
> External LLM report processing: `PROHIBITED`

## 1. Human Owner instruction

The Human Owner first supplied Samsung Securities PDFs and later added Mirae
Asset Securities and Kiwoom Securities reports, including the previously used
Mirae Asset reports. The requested boundary became:

```text
local PDF inspection and full-page text extraction
→ verified metadata and page checksum inventory
→ one short Questock-authored page-1 perspective per report
→ relevant perspectives available only in the collapsed M5-D1 comparison
```

Report originals, raw text, excerpts, and PDF bytes remain excluded from Git,
ordinary runtime evidence, and external LLM input.

## 2. Final report coverage

| Security | Samsung Securities | Mirae Asset Securities | Kiwoom Securities | Total |
|---|---:|---:|---:|---:|
| SK hynix | 3 | 2 | 0 | 5 |
| Hyundai Motor | 1 | 2 | 2 | 5 |
| Samsung Electronics | 2 | 2 | 1 | 5 |
| Total | 6 | 6 | 3 | 15 |

Observed totals:

- PDFs discovered and selected: `15`
- outside-cutoff PDFs excluded: `0`
- fully extractable reports: `9`
- partially extractable reports: `4`
- image-only reports requiring visual review: `2`
- ordinary runtime-ready raw reports: `0`
- comparison-ready Questock-authored perspectives: `15`

The `2026-06-25` SK hynix report is retained because it was supplied and was
already available before the phase-1 answer cutoff.

All first pages were rendered and visually checked for publisher, security,
title, analyst, and publication date. The two image-only reports were accepted
only after this visual identity check.

## 3. Storage and permission boundary

Local only and Git-ignored:

- supplied PDFs
- extracted page text
- source filenames and local paths
- any evidence excerpt used during manual verification

Commit-safe inventory:

- security and ticker
- publisher and analyst
- report title and publication date
- official publisher source URL
- PDF SHA-256
- PDF page count
- page-text SHA-256 and character count when text extraction was possible
- extraction, selection, and preprocessing status

Permissions remain:

- `local_preprocessing_allowed=true`
- `corpus_ingest_allowed=false`
- `external_llm_processing_allowed=false`
- `runtime_source_pdf_allowed=false`
- `runtime_raw_text_allowed=false`
- `runtime_evidence_excerpt_allowed=false`

The short Questock-authored perspective is a separate comparison sidecar
record and does not change these raw-report permissions.

## 4. Implementation

- public schema:
  `app/services/m5_d1_report_inventory.py`
- local preparation:
  `scripts/prepare_m5_d1_reports.py`
- public inventory:
  `data/m5_d1_report_inventory.json`
- source checksum:
  `a6de59840104c49554fc4686f1907504727576e8cb1335b76cfc0578961ebe62`
- inventory file checksum:
  `22ff6aabbdb89c701e00b22f5f4559bf2d1f093647f68af7e261afcfabbcf928`
- PDF and raw extraction ignore rules:
  `.gitignore`

The local extractor first uses project `pypdf` when available and otherwise
invokes the isolated Codex-bundled PDF Python runtime. No project runtime
dependency was added.

## 5. Validation and runtime use

- 15-PDF preparation:
  `PASS`
- public inventory load and recomputed validation:
  `PASS`
- raw text, excerpt, local path, and PDF bytes in public inventory:
  `0`
- first-page visual identity checks:
  `15/15 PASS`
- one bounded page-1 perspective per selected report:
  `15/15`
- external LLM processing:
  `0`

At answer time, a report perspective is shown only when its security, topic,
publication cutoff, and event/query terms match. At most three perspectives
are shown. Target prices are not promoted as recommendations, and raw report
content is not sent to Gemini.
