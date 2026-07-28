# QUESTOCK SOURCE OF TRUTH INDEX

> 기준일: 2026-07-29
> 기준 branch: canonical `main`; deployed runtime release `373ea00d4e06526a98898e9c38f4d4a7871b1a8f`
> Pre-B6 code baseline: `d937d625e26495a3ee8c5a5b2c327dfbd2512ea9`
> Docs update/review base: `f5b3c646ec8696ac5c70d0d700e6fd729fd83bc4`
> B9 planning base: `b9ddf7461306d16cf1da14634ce458050d78f7bc`
> 상태: `B9 PASS / M4 Gate PASS / FSC-0~FSC-4 PASS / complete; M5-01 PASS / DEPLOYED / COMPLETE; M5-01-HR1 PASS / DEPLOYED / COMPLETE; M5-D1 PASS / DEPLOYED / COMPLETE at 373ea00d4e06526a98898e9c38f4d4a7871b1a8f; M5-E1 REMEDIATION EVALUATION COMPLETE / QUALITY GATE PASS; publication and deployment pending`

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
B9, First Service Completion, M5-01, M5-01-HR1, M5-D1,
M5-E1 quality remediation and evaluation gate

M5-D1 Evidence Cross-check:
M5-D1-0~M5-D1-6 `PASS / DEPLOYED / COMPLETE`;
release SHA `373ea00d4e06526a98898e9c38f4d4a7871b1a8f`

현재 차별화 후보:
동일 사건의 반복 보도를 독립 근거로 과장하지 않고,
뉴스의 공통 사실·다른 해석과 DART 공식 자료의 역할,
미확인·자료 부족을 초보자에게 설명하는 `근거 대조형 답변`

현재 checkpoint:
M5-D1 publication and GCE deployment complete;
M5-E1 frozen answers and hard gate complete;
earlier DeepEval built-in held-out run remains a historical quota partial;
Gemini 3.1 Pro Batch evaluation completed with 120/120 responses;
the original Batch FAIL remains historical;
remediation hard gate passed at 24/24;
Answer Relevancy 24/24, Faithfulness 24/24,
Beginner Usefulness 20/24 and aggregate quality gate PASS;
publication and deployment are pending

M5-E1 실행 기준:
docs/TASK_CARDS/M5-E1-deepeval-quality-evaluation.md

M5-E1 부분 종료 기록:
docs/agent_handoff/M5_E1_EVALUATION_PARTIAL_2026-07-28.md

M5-E1 Batch 평가 기록:
docs/agent_handoff/M5_E1_BATCH_EVALUATION_2026-07-29.md

M5-D1 실행 기준:
docs/TASK_CARDS/M5-D1-evidence-crosscheck.md

M5-01 실행 기준:
docs/TASK_CARDS/M5-01-as-of-price-grounded-answer.md

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

FSC-4 post-deployment answer-presentation follow-up:
local PASS; implementation commit `edb46ae`; remote branch pushed;
PR #18 MERGED
<https://github.com/JJungDae/Questock/pull/18>;
merge SHA `6f50ee922c2a1c74278ead2f679472ba3e19bc8b`;
focused publish-preflight `85 passed, 2 warnings`;
quality-gate run `30323480083` PASS; deployment NOT_STARTED

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
activation prerequisites reviewed; M5-01 PASS / DEPLOYED / COMPLETE

M5-01:
`PASS / DEPLOYED / COMPLETE`;
Task Card `docs/TASK_CARDS/M5-01-as-of-price-grounded-answer.md`;
implementation PR #19 and UI closure PRs #20, #21, #22 MERGED;
final merge/deployed release
`824f06f014415fd66ad9bbd1c9743f03be02efcc`;
final PR quality-gate run `30329244843` PASS;
final merged-main quality-gate run `30329322602` PASS;
final deployment run `30329400059` PASS;
deployed image
`sha256:b91c9ec9bf6cada77167c68606a565c0854f06ac168fa4d9f321934c5e9df42a`;
API/UI health, 54-document recorded snapshot, and 7-scenario smoke PASS;
production browser PASS for trading-day price, checkpoint conversation clear,
weekend closed-market status, actual prior observation time, and completed
answer/loading separation;
rollback target `40dca28ed9c9a93d6ebf7c95161fda52ec1e01ef` /
`sha256:f0283455a40679c405ed1ae5489d2444de199f31bbdba97675a029509a52b359`;
rollback execution `NOT_RUN` because deployment passed

M5-01 post-deployment answer-quality closure:
`LOCAL PASS / HUMAN OWNER APPROVED`;
same-day news-first price-move retrieval, optional-source warning suppression,
bounded non-repeating price context, natural title-only fallback, HBM variant
retrieval, narrowed direct-price classification, and completed-loading cleanup;
focused `258 passed`, Streamlit `13 passed`, full regression `2122 passed`,
Ruff PASS, local disabled-Gemini browser PASS;
commit/push/PR/merge/deployment `NOT_RUN`

M5-01-HR1:
Hybrid Intent Router
`INDEPENDENT REVIEW PASS / DEPLOYMENT AUTHORIZED`;
rules remain the deterministic first route, only ambiguous or conflicting
questions may use Gemini classification, and classifier failure must return to
the deterministic rule result;
classifier maximum `1` call per request, answer composer maximum `1` additional
call, timeout `3` seconds, retry `0`;
focused `115 passed`, affected regression `435 passed`, release-contract
regression `61 passed`, full regression `2148 passed`, Ruff PASS;
M3 Gate `34/34`, Critical `17/17`, public exposure `0`;
tracked and new-file secret scans PASS with findings `[]`; diff check PASS;
bounded live classifier smoke `2/2 PASS`, actual provider calls `2`,
answer-generation calls `0`;
GCE contract includes `QUESTOCK_HYBRID_ROUTER_ENABLED=true`;
pre-review commit/push/PR/merge/deployment state `NOT_RUN`

M5-01-HR1 independent review:
`PASS WITH REQUIRED FIX / FIX CLOSED`;
classifier-reclassified price-only responses now emit sanitized observations;
`intent_classifier_status` records allowlisted accepted/failure state without
prompt, response, question, credential, or session content;
affected regression `164 passed`, full regression `2158 passed`, Ruff and
compile PASS, M3 Gate `34/34`, Critical `17/17`, public exposure `0`, tracked
and new-file secret scans findings `[]`, diff check PASS;
Human Owner authorized GitHub publication, merge, and deployment on
`2026-07-28`;
implementation commit `2eb29bd8e090e0a950238f95a394470ed33723fb`;
PR `#24`, merge/release SHA
`c96008229cae34c4c3243a4cbfe099c98cc594c5`;
PR quality-gate run `30338001377` PASS;
merged-main quality-gate run `30338154423` PASS;
deployment run `30338271294` PASS;
release image
`sha256:ca844177af644501e28406012f22c5d91d08f1bea0afb6658ce0c4c319373602`;
API/UI health, external UI health, and recorded 7-scenario smoke PASS;
rollback target
`824f06f014415fd66ad9bbd1c9743f03be02efcc` /
`sha256:b91c9ec9bf6cada77167c68606a565c0854f06ac168fa4d9f321934c5e9df42a`;
rollback execution `NOT_RUN` because deployment passed;
production browser verified ambiguous risk routing, explicit price routing,
answer completion/loading cleanup, and cleared question input;
M5-01-HR1 `PASS / DEPLOYED / COMPLETE`

Competitive differentiation review:
`docs/agent_handoff/COMPETITIVE_DIFFERENTIATION_REVIEW_2026-07-28.md`;
official public pages confirm overlap in story clustering, source navigation,
research plans, positive/risk/event summaries, filing audit links, and
cross-publisher views;
`As-of Replay` is superseded as a differentiation candidate because the
selected-time UI is a temporary demo constraint, while temporal filtering
remains a correctness contract;
the current candidate is the combined `근거 대조형 답변`: event clusters,
conservative source lineage, DART confirmation/background roles,
common facts, different interpretations, unconfirmed/missing evidence, and a
beginner-facing answer;
this is a plausible differentiation target, not proof of market exclusivity

M5-D1 planning and implementation:
`docs/TASK_CARDS/M5-D1-evidence-crosscheck.md`;
phase 1 uses news, DART disclosures, and short verified report perspectives;
Human Owner reported `OPENDART_API_KEY` ready locally;
research-report originals and extracted text remain Git-ignored and excluded
from ordinary runtime evidence and external LLM input;
current repository disclosure corpus is one fixed 2026 Q1 quarterly report per
security;
plan status `APPROVED / IMPLEMENTATION AUTHORIZED`;
Human Owner implementation approval recorded 2026-07-28;
M5-D1-0~M5-D1-6 `PASS / DEPLOYED / COMPLETE`;
coverage result:
`docs/agent_handoff/M5_D1_COLLECTION_COVERAGE_2026-07-28.md`;
retained local source inventory:
news `300`, OpenDART disclosures `205`;
SK hynix news coverage repair:
`8` to `54` retained candidates from existing raw responses;
`41` description-assisted candidates remain explicitly labeled for later
event-membership validation; second provider `NOT_ADDED`;
multi-publisher report preparation:
`docs/agent_handoff/M5_D1_REPORT_FIRST_PASS_2026-07-28.md`;
15 PDFs selected; Samsung Securities `6`, Mirae Asset Securities `6`, Kiwoom
Securities `3`; five per security; all first pages visually verified;
raw report runtime-ready `0`; Questock-authored comparison perspectives `15`;
implementation review:
`docs/agent_handoff/M5_D1_IMPLEMENTATION_REVIEW_2026-07-28.md`;
bounded M5-D1-1 and M5-D1-1R scope `PASS`;
completion record:
`docs/agent_handoff/M5_D1_COMPLETION_2026-07-28.md`;
accepted-review closure:
`docs/agent_handoff/M5_D1_REVIEW_FIX_CLOSURE_2026-07-28.md`;
deployment closure:
`docs/agent_handoff/M5_D1_DEPLOYMENT_CLOSURE_2026-07-28.md`;
direct-company event clusters `7`, clustered article instances `43`;
description-only company matches remain indirect candidates and cannot enter
direct event clusters;
confirmed independent and confirmed republication counts remain `0`;
DART background records `34`;
report and DART display links require event-specific topic overlap;
held-out event-pair evaluation `8`, precision `1.00`, recall `1.00`;
focused M5-D1/report tests `18 passed`;
affected regression `193 passed`; full regression `2189 passed, 2 warnings`;
Gemini classifier calls `0`;
OpenDART credential preflight `PASS`;
implementation commit
`95b98555bd588134148a9104f733d6f85f00480b`;
PR `#26`;
PR quality gate `30362235377` `PASS`;
release SHA `373ea00d4e06526a98898e9c38f4d4a7871b1a8f`;
merged-main quality gate `30362397614` `PASS`;
GCE deployment `30362550006` `PASS`;
release image
`sha256:e8480098951728eeb4c2a5cb83a36bc5c03c5ee9b40c9286a10d212713ee57b5`;
rollback `NOT_RUN` because deployment passed

B6 구현:
PASS / complete

B6 완료 SHA:
60e6203b265a967a8b6ba45da2ba3128e1e1bcfe

다음 공식 checkpoint:
Human Owner production UI review or next-scope direction

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
docs/TASK_CARDS/M5-01-as-of-price-grounded-answer.md

completed M5-D1:
docs/TASK_CARDS/M5-D1-evidence-crosscheck.md

current status:
M5-D1-0~M5-D1-6 `PASS / DEPLOYED / COMPLETE`;
release SHA `373ea00d4e06526a98898e9c38f4d4a7871b1a8f`

current evaluation standard:
docs/TASK_CARDS/M5-E1-deepeval-quality-evaluation.md

evaluation status:
M5-E1 `REMEDIATION EVALUATION COMPLETE / QUALITY GATE PASS`;
earlier DeepEval built-in run remains `PARTIAL / JUDGE_QUOTA_STOP`;
the original Gemini 3.1 Pro Batch FAIL remains historical;
final Gemini 3.1 Pro Batch G-Eval-style fixed-rubric run `120/120`;
hard gate `24/24 PASS`;
Answer Relevancy `24/24 PASS`;
Faithfulness `24/24 PASS`;
Contextual Relevancy `REPORT_ONLY`;
Beginner Usefulness `20/24 PASS`;
Gemini generator-model comparison remains `NOT_RUN`

completed M5 extension:
docs/TASK_CARDS/M5-01-hybrid-intent-router.md

completed FSC execution standard:
docs/TASK_CARDS/FSC-4-beginner-grounded-chat.md

current execution decision:
docs/agent_handoff/FIRST_SERVICE_COMPLETION_EXECUTION_DECISION_2026-07-27.md

next:
publish, merge, deploy, and run production demo verification
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
