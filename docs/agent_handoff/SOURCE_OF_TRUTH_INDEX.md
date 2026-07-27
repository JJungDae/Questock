# QUESTOCK SOURCE OF TRUTH INDEX

> 기준일: 2026-07-28
> 기준 branch: canonical `main`; deployed runtime release `136271ea80802a39f1981e539f183d544d95e23a`
> Pre-B6 code baseline: `d937d625e26495a3ee8c5a5b2c327dfbd2512ea9`
> Docs update/review base: `f5b3c646ec8696ac5c70d0d700e6fd729fd83bc4`
> B9 planning base: `b9ddf7461306d16cf1da14634ce458050d78f7bc`
> 상태: `B9 PASS / M4 Gate PASS / FSC-0~FSC-4 PASS / complete; FSC-4 deployed at 136271ea80802a39f1981e539f183d544d95e23a; A15-M activation check READY / NOT_STARTED`

## 1. 목적

이 문서는 M3-01 이후 변경된 실행 순서와 검수 경계를 여러 에이전트가
대화 기억 없이 동일하게 읽도록 하는 최상위 안내 문서다.

이 문서 묶음이 프로젝트에 반영된 뒤에는 이전 대화의 권장 순서,
구버전 M3 실행 순서, 동명 파일의 오래된 사본을 실행 기준으로 사용하지 않는다.

## 2. 읽기 순서

에이전트는 M3-01 이후 작업 전에 다음 순서로 읽는다.

1. `docs/agent_handoff/README_AGENT_RULES.md`
2. `docs/agent_handoff/PROJECT_PLAN_FINAL_PASS.md`
3. `docs/agent_handoff/PROJECT_PLAN_FINAL_PASS_POST_M3_01_ADDENDUM.md`
4. `docs/agent_handoff/POST_M3_01_EXECUTION_FLOW_DECISION_2026-07-25.md`
5. `docs/agent_handoff/FIRST_SERVICE_COMPLETION_EXECUTION_DECISION_2026-07-27.md`
6. 현재 bundle의 Task Card 또는 통합 계획
7. `docs/agent_handoff/AGENT_WORKFLOW.md`
8. `docs/agent_handoff/AGENT_WORKFLOW_POST_M3_01_ADDENDUM.md`
9. 관련 도메인·위험·평가 문서
10. 실제 최신 코드와 테스트

## 3. 문서 효력

### 기존 문서 유지

다음 기존 문서는 삭제하거나 전면 교체하지 않는다.

- `README_AGENT_RULES.md`
- `PROJECT_PLAN_FINAL_PASS.md`
- `AGENT_WORKFLOW.md`
- 기존 M1·M2·M3 Task Card

### 이 묶음이 우선하는 범위

다음 내용이 기존 문서와 충돌하면 이 묶음의 최신 addendum과 결정 기록을 따른다.

- M3-01의 최종 완료 상태
- M3-15A와 M3-15B 분리
- B6·B7·B8·B9의 checkpoint 순서
- bundle별 계획 검수와 구현 검수 경계
- golden/Critical 평가 자산 확인 시점
- Streamlit dependency governance
- M4 이후 First Service Completion 삽입과 bundle 순서
- Service Completion Gate 이후 A15-M, Stretch M2-09, M5-01, P1 순서

## 4. 현재 상태 요약

```text
M3-01:
PASS / complete
코드 BLOCKER 전부 CLOSED
Task Card 사실 동기화 완료, B6-0에서 상태 확인

현재 완료 bundle:
B9, First Service Completion

현재 공식 bundle:
FSC-4 beginner grounded chat stabilization - PASS / deployed / complete

현재 checkpoint:
A15-M activation check - READY / NOT_STARTED

FSC 실행 결정:
docs/agent_handoff/FIRST_SERVICE_COMPLETION_EXECUTION_DECISION_2026-07-27.md

FSC Task Card:
docs/TASK_CARDS/FSC-first-service-completion.md

FSC-0:
PASS / complete - Human Owner confirmed 2026-07-27

FSC-1:
PASS / complete - SC-01~04 complete; Human Owner requested closure 2026-07-27

FSC-1 backup:
`c18dad90f293b50f3e258c37907bd6b79cac8e6b` pushed to
`fsc/fsc-0-preflight`

Current LLM contract:
`gemini/gemini-3.5-flash`; `LLM_THINKING_LEVEL=minimal`;
`LLM_MAX_OUTPUT_TOKENS=4096`; `LLM_TIMEOUT_SECONDS=15`; retry `0`;
`litellm==1.84.1`; legacy `LLM_THINKING_BUDGET` rejected;
concise JSON instructions with project-side Pydantic/citation/safety
validation; provider-side JSON-schema-constrained decoding disabled after
FSC-4 live repeated-output reproduction; final FSC-4 live acceptance PASS

SC-01 automatic result:
initial broad canonical queries exhausted the 1,000-result ceiling before the
cutoff; validated company/date query and per-security sort rerun returned
16 / 48 / 14 normalized candidates and PASS; direct quality supplements revised
the candidate pools to 24 / 48 / 14

SC-01 quality result:
5 documents per security; pre-market/intraday 2/3, 1/4, 2/3;
PASS / complete - Human Owner confirmed 2026-07-27

SC-02 result:
PASS / complete; one document per fixed receipt; 18 / 21 / 20 facts;
all required categories 10/10; official viewer rm 유 / 유 / 유;
Human Owner confirmed 2026-07-27

SC-03 report result:
Human Owner approved the source and permission package on 2026-07-27;
M1-06 corpus normalization produced 12 PDF-verified sections per security;
source PDF/body/excerpt/raw text are excluded from runtime, Git, and Gemini;
PASS / complete - Human Owner confirmed 2026-07-27

SC-04 snapshot result:
PASS / complete; snapshot `svc-20260724-1402`;
fixed basis `2026-07-24T05:02:00Z`; 54 unique documents;
news 15, disclosures 3 with 18 / 21 / 20 facts,
research reports 3 manifests / 36 sections; two builds produced all six files
byte-identically; targeted 41 passed; full regression 1946 passed;
GitHub CI and independent pytest rerun NOT_RUN

FSC-2:
PASS / complete - Human Owner confirmed 2026-07-27; Human Owner billing
confirmation and one sanitized Gemini smoke PASS

FSC-2 Git:
commit/push `25cac10030800f08d4167b9f7739d06b3d1492ca` / complete;
PR #10 `MERGED`; https://github.com/JJungDae/Questock/pull/10;
merge SHA `92561e34b4839d32a9bdac979c6c471da8e56923`

FSC-2 smoke:
exactly one live call; status ok; model gemini/gemini-3.5-flash;
structured parse PASS; usage present; finish reason stop; no raw payload,
credential, provider error, or local path recorded

FSC-2 verification:
targeted 227 passed; affected integration 73 passed; full regression 1999
passed; M3 Gate 34/34; Critical 17/17; public exposure 0; Ruff, compile,
secret/local-path scan, and diff check PASS; GitHub CI/deploy NOT_RUN

FSC-3:
PASS / complete - SC-06 and SC-07 local/remote closure complete

FSC-4:
`PASS / DEPLOYED / COMPLETE`;
Task Card `docs/TASK_CARDS/FSC-4-beginner-grounded-chat.md`;
120-case beginner-QA deterministic acceptance PASS;
Ruff PASS; full regression 2086 passed, 2 warnings;
M3 Gate 34/34; Critical 17/17; public exposure 0;
snapshot validation PASS with 54 documents; secret scan and diff check PASS;
final live acceptance PASS with Gemini success 10/12, all 15 public
validations PASS, Critical provider attempts 0, and unsupported number,
wrong-company, uncited core-number, and direct-advice failures 0;
Human Owner approved deployment;
implementation PR #14 and smoke hotfix PR #15 MERGED;
final quality-gate run 30300234890 PASS;
deployment run 30300383109 PASS;
deployed release SHA 136271ea80802a39f1981e539f183d544d95e23a;
deployed image
sha256:bda18d4456742b59f2ac0e44877fe5544ccac7d54d4438b83d64e2c6768ce3b9;
API/UI health and 7-scenario release smoke PASS;
initial deployment smoke failure auto-rollback PASS to
2adcc787a803996d4a181a6cd3faa3158602660a

SC-06 verification:
live acceptance PASS; cumulative LLM success 10/12; Critical 3/3 with zero
Gemini calls; actual provider attempts 26/30; all 15 public validations PASS;
unsupported number, wrong-company, uncited core number, and direct advice 0

SC-06 focused root supplement:
symmetric Korean query/document token normalization; strict Korean month/day
periods; threshold-only required-source-aware retrieval/context/fixed
projection; policy `satisfied_sources` acceptance validation; citation-bound
public Evidence; report fixed-only and mixed prompt exclusion preserved

SC-06 focused verification:
targeted 347 passed; M3 Gate tests 9 passed; full regression 2048 passed;
M3 Gate 34/34; Critical 17/17; public exposure 0; snapshot validator 54
documents; two builds byte-identical and equal to tracked canonical output;
additional live Gemini/provider calls 0 before live acceptance

SC-07 local release preparation:
explicit CI release-contract gate added; focused 139 passed; full regression
2062 passed; M3 Gate 34/34; Critical 17/17; public exposure 0; snapshot
validator 54 documents; two-build and tracked canonical identity PASS; Ruff,
compile, and secret/local-path scan PASS; Docker server 29.6.2; clean locked
image `sha256:ad8d753d78a0b84fa3321f225188d567fc1940df5e5dac38c6b075ff50384bf4`;
non-root/read-only/capability-drop boundary PASS; API/UI HTTP 200; recorded
release smoke 7/7 PASS; release-smoke focused regression 28 passed; additional
Gemini/provider attempts 0 and cumulative total remains 26/30

SC-07 remote release closure:
PR #11 head `8d1b9521fdbef003cb84708b6aa7b47d01d8dc8a`; first CI
`30273039760` failed on the Python 3.11 Streamlit extracted-helper annotation;
fix `8d1b952`; CI `30273607080` passed; merge
`6affd27f4f95aae438268acd2bc4fa7733346b5d`.
PR #12 commits `499bf03`, `bed5684`; first CI `30274239625` failed on the
legacy B9 old-regex expectation; focused contracts `139 passed`; CI
`30274469379` passed; merge and deployed main
`2adcc787a803996d4a181a6cd3faa3158602660a`.
First deploy `30273898079` failed before runtime write/deploy because the
anchored allowlist excluded one dot in the already-live-verified 53-character
Gemini key; the existing service/image stayed unchanged and rollback was not
executed. Exact-SHA deploy `30274651799` passed in `3m32s`; release image
`sha256:53628bacc40f2329bc3f7dfcb6771aeee2e5fd83a1a44592ee08bbc950daf138`.
The previous rollback target is SHA
`67fa43dd5a7ec74e7785713eb1adcfa402baab85` and image
`sha256:56df8f16ed3ed58de659e9ec46c9e24b7d3ddc896dc8a022102f68f351d7b928`;
rollback execution was `NOT_RUN` because deployment passed.
The recorded runtime reported status ok, snapshot `svc-20260724-1402`, 54
documents (news 15 / disclosure 3 / research_report 36), and
`live_connectivity_checked=false`. Remote recorded smoke passed 7/7 and the
workflow external UI health check passed. A separate non-gate reviewer browser
attempt to the registered host on port 8501 timed out, so interactive visual
rendering is not claimed. Deployment smoke used the fixed/disabled path and
added 0 Gemini calls; the cumulative total remains 26/30.

Service Completion Gate:
PASS / complete

A15-M:
activation and entry READY / implementation NOT_STARTED

B6 구현:
PASS / complete

B6 완료 SHA:
60e6203b265a967a8b6ba45da2ba3128e1e1bcfe

다음 공식 checkpoint:
A15-M activation check - READY / implementation NOT_STARTED

B9 계획:
docs/TASK_CARDS/B9-release-deployment-traceability.md
B9 독립 계획 검수:
PASS WITH REQUIRED FOLLOW-UP
B9 계획 필수 보완:
반영 완료
B9 계획 보완 commit/push:
74214b75575fd9f1594ac545b42bbf3908066e77 / complete
B9 추가 계획 검수:
NOT_REQUIRED
B9-0:
PASS / complete - 1802 passed, M3 Gate 34/34, Critical 17/17, public exposure 0
B9 remaining implementation plan:
REVIEWED V2 / current execution supplement
B9 implementation base:
74214b75575fd9f1594ac545b42bbf3908066e77
B9-A1+A2 foundation:
PASS / implementation and main merge complete
B9-A foundation implementation SHA:
71ac117690f494f05a337d852abc917b5b2addd8
B9-A Python 3.11 CI compatibility fix:
0e703b6fd0bcc13b33c39ff539a27c523176fe0d
B9-A merge/main SHA:
1a14efbb85669a03340442e1a73b6416adbf2bed
B9-A 완료:
local Ruff, regression, M3 Gate, secret/compile, locked Docker build,
API/UI health and smoke PASS
PR quality-gate and merged-main quality-gate PASS
main protection Ruleset active
B9 GitHub CI:
PASS - B9-A PR and merged main runs observed
B9 implementation SHA:
1a14efbb85669a03340442e1a73b6416adbf2bed - B9-A merge baseline
B9-B:
main merge complete; focused closure and remote recorded release PASS
B9-B local verification:
targeted/full regression, M3 Gate 34/34, Critical 17/17, public exposure 0,
Ruff, secret/compile, clean Docker build, API/UI health, and 7-scenario smoke PASS
B9-B release-candidate commit/PR/CI:
implementation commit 6ed6c13a143f5798157aed2344d09ae126ced00b
release branch push complete
PR #2 / main merge complete
merged main SHA c807be1d4b62acd0d45dea42b884bd16dd366652
B9-B merged-main GitHub CI was not independently queried in this focused
closure
B9 focused closure:
single verified disclosure body-fact supplement and post-startup rollback
local targeted/full regression, M3 Gate, Ruff, secret/compile PASS
M4-06 disclosure scenario PASS WITH DECLARED COVERAGE LIMITATION
final status partial with insufficient_disclosure_coverage
implementation SHA d70e17a95046f5ebcbca05970ff574c1121acb1c
implementation commit and origin/fix/b9-focused-closure push complete
focused closure PR #3 / merge SHA
8dc9c322af89e395aa62e614c69b0840e7aedbae / quality-gate PASS
B9 deployment hotfixes:
PR #4 merge SHA 331c41cbf09cc5541f03a17feb9194c0e442e81b
PR #5 merge/release SHA 67fa43dd5a7ec74e7785713eb1adcfa402baab85
release quality-gate run 30207273750 PASS - 1852 passed, M3 Gate 34/34,
Critical 17/17, public exposure 0
B9-B 원격 배포:
PASS - deploy run 30207335981
release image sha256:56df8f16ed3ed58de659e9ec46c9e24b7d3ddc896dc8a022102f68f351d7b928
recorded API/UI health and external UI health PASS
7-scenario recorded smoke PASS; disclosure remains partial with
insufficient_disclosure_coverage
rollback target captured; rollback execution NOT_RUN because deployment passed
B9 independent review:
PASS WITH REQUIRED FOLLOW-UP - required follow-up CLOSED
B9 M4 Gate closure implementation SHA:
76d8ad2fc3a2565e022774333f1958ebbbae709f
B9 M4 Gate closure PR/main merge:
PR #7 / c97f1af461753c7d05fb8ed9a9f7365182d91f2b
B9 M4 Gate merged-main quality-gate:
PASS - run 30210025937
Human Owner confirmation:
PASS - 2026-07-27
B9 final status:
PASS / complete
M4 Gate:
PASS
next:
First Service Completion

B8 구현:
PASS WITH REQUIRED FOLLOW-UP / complete
focused closure fix PASS
B8 code blockers CLOSED
M4 quality 34/34 = 100%
Critical 17/17 = 100%
public exposure 0
closure SHA/main push:
b9ddf7461306d16cf1da14634ce458050d78f7bc / complete
B9 계획 ALLOWED
B9-0 PASS / complete
B9-A1+A2 foundation 구현과 local verification ALLOWED
B9 current implementation commit/main push는 승인 완료
B9-B remote deploy PASS; independent review follow-up CLOSED; PR #7 merged-main
quality-gate PASS; Human Owner confirmation PASS; B9 complete; M4 Gate PASS

M1-09:
mandatory supplement implemented - final independent review pending
```

## 5. 현재 bundle 문서

```text
completed:
docs/TASK_CARDS/B6-REMAINDER-integrated-implementation-plan.md
docs/TASK_CARDS/B7-integrated-implementation-plan.md
docs/TASK_CARDS/B8-quality-observability.md
docs/TASK_CARDS/B9-release-deployment-traceability.md

current:
docs/TASK_CARDS/FSC-4-beginner-grounded-chat.md

current execution decision:
docs/agent_handoff/FIRST_SERVICE_COMPLETION_EXECUTION_DECISION_2026-07-27.md

next:
A15-M activation check - implementation NOT_STARTED
```

## 6. 금지

- 대화 요약만 보고 구현 시작
- 이 인덱스에 없는 구버전 흐름 문서를 우선
- B6 전에 M3-06 또는 M3-08~11 구현
- M3-12 가격 기능 선행 구현
- 승인 없이 Streamlit 또는 다른 dependency 추가
- bundle 내부 checkpoint마다 임의 main push
- Task Card 상태와 실제 Git 상태 불일치 방치
- Service Completion Gate 전에 A15-M·Stretch M2-09·M5-01 진입

## 7. 향후 갱신

새로운 계획 결정이 생기면 최소한 다음을 함께 갱신한다.

- 이 Source of Truth Index
- 실행 흐름 결정 기록
- Project Plan addendum 또는 본문
- Agent Workflow addendum 또는 본문
- 현재 Task Card
- 다음 bundle 계획
