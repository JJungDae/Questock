# M5-D1 Deployment Closure — 2026-07-28

## Result

`PASS / DEPLOYED / COMPLETE`

## GitHub publication

- implementation commit:
  `95b98555bd588134148a9104f733d6f85f00480b`
- implementation branch:
  `feature/m5-d1-evidence-crosscheck`
- pull request:
  `#26`
- PR quality-gate run:
  `30362235377`, `PASS`
- merged-main release SHA:
  `373ea00d4e06526a98898e9c38f4d4a7871b1a8f`
- merged-main quality-gate run:
  `30362397614`, `PASS`

## GCE deployment

- workflow:
  `deploy-recorded-gce`
- workflow run:
  `30362550006`, `PASS`
- deployed release SHA:
  `373ea00d4e06526a98898e9c38f4d4a7871b1a8f`
- release image:
  `sha256:e8480098951728eeb4c2a5cb83a36bc5c03c5ee9b40c9286a10d212713ee57b5`
- previous release SHA:
  `c96008229cae34c4c3243a4cbfe099c98cc594c5`
- previous image:
  `sha256:ca844177af644501e28406012f22c5d91d08f1bea0afb6658ce0c4c319373602`
- rollback execution:
  `NOT_RUN` because deployment passed

## Deployment verification

- API container health:
  `PASS`
- UI container health:
  `PASS`
- external UI health:
  `PASS`
- recorded release smoke:
  `PASS`, `7` scenarios
- snapshot:
  `svc-20260724-1402`
- recorded document counts:
  news `15`, disclosure `3`, research report `36`, total `54`
- live data connectivity check:
  `false`, as required by the recorded deployment contract

The deployment smoke completed these expected public states:

- recent issue:
  `complete`
- disclosure:
  `partial`
- research report:
  `complete`
- glossary:
  `complete`
- wrong company:
  `no_evidence`
- blocked request:
  `blocked`
- multi-turn:
  `partial`

No independent browser-based visual or question-quality review was performed
in this deployment closure. The Human Owner may now perform the planned
production UI review.
