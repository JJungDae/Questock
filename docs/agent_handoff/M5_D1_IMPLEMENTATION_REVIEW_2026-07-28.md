# M5-D1-1 / M5-D1-1R Implementation Review — 2026-07-28

> Branch: `feature/m5-d1-evidence-crosscheck`
> Base: `40f58b3df7a53c3386e9653fd3b061f010b31335`
> Result: `IMPLEMENTATION REVIEW PASS / M5-D1 OVERALL IN PROGRESS`
> Commit, push, PR, merge, deployment: `NOT_RUN`

## 1. Reviewed scope

This review covers only:

- broad Naver news and OpenDART metadata inventory
- the SK hynix coverage repair
- Samsung Securities July-report local preprocessing and public inventory
- source boundaries, deterministic validation, and affected regression

Event grouping, source independence decisions, DART body extraction, report
fact verification, answer integration, UI integration, evaluation, and
deployment remain outside this checkpoint.

## 2. Implementation corrections closed

The review found and closed these implementation risks:

1. SK hynix coverage collapsed to `8` because title-only company matching
   discarded already-collected event titles whose provider description named
   SK hynix.
   - repaired to `54` candidates from existing raw responses
   - `13` title-alias matches and `41` bounded description-assisted matches
   - the match basis remains explicit; description text is not stored publicly
2. An exact-URL duplicate could retain the weaker description-assisted match
   even when another copy established a title match.
   - duplicate consolidation now promotes `title_alias`
3. The source checksum included the collection execution time.
   - repeated raw replays now produce the same source checksum
4. A saved report payload could pass incomplete derived-field validation.
   - URL host, identity, hash, date cutoff, scope, selection, page totals,
     permissions, coverage, and source checksum are recomputed
5. Report preparation could write the public inventory before all local
   extracts were safely established, or overwrite a differing existing
   extract.
   - local extracts are checked first; mismatches fail closed
6. `[연장결정]` could be misclassified as a correction disclosure.
   - it now remains an original status while sharing the stripped lineage key
7. Local PDF and source-map files could be included by a broad Git add.
   - both are explicitly Git-ignored

No provider call or Gemini call was needed for these review corrections.

## 3. Verified results

- retained news:
  `300`
- retained SK hynix news candidates:
  `54`
- SK hynix publisher hosts:
  `36`
- retained OpenDART disclosures:
  `205`
- stable source checksum:
  `338f2caed9757ab09024819f9cb333b74754f1d90399ef7869441eacb69c3124`
- Samsung Securities PDFs discovered:
  `6`
- July reports selected:
  `5`
- outside-July reports excluded:
  `1`
- report pages extracted locally:
  `49 / 49 non-empty`
- report runtime-ready count:
  `0`
- stable report checksum:
  `ac36732e95a69bb13121ae7d39820040e9647718249a54c7a5f41683f1cbfb17`
- M5-D1 focused tests:
  `24 passed`
- affected unit and integration tests:
  `255 passed`
- Ruff:
  `PASS`
- inventory revalidation, Git ignore checks, secret/local-path scan, and
  diff check:
  `PASS`

The only observed warning is the existing Python `3.14` / LangChain Pydantic
V1 compatibility warning. It did not fail this checkpoint.

## 4. Required next-stage boundaries

The `41` description-assisted SK hynix records are broad collection
candidates, not established claim evidence or independent sources. M5-D1-2
must review event membership and discard contextual or unrelated items before
any answer use.

The five selected July reports contain verified metadata and local full-text
extraction only. Their facts, numbers, page locators, Questock-authored
summaries, and event roles are not yet approved. They must remain excluded
from runtime until that verification and a later integration decision.

OpenDART correction lineage also remains `candidate_only`; this review does
not claim receipt-level predecessor verification.

## 5. Review verdict

M5-D1-1 and M5-D1-1R have no remaining implementation blocker within their
bounded inventory and preprocessing scope.

M5-D1 as a whole is not complete. The next authorized implementation
checkpoint is M5-D1-2 deterministic event grouping and conservative source
lineage.
