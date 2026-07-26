# QUESTOCK SOURCE OF TRUTH INDEX

> 기준일: 2026-07-26
> 기준 branch: `main`
> Pre-B6 code baseline: `d937d625e26495a3ee8c5a5b2c327dfbd2512ea9`
> Docs update/review base: `f5b3c646ec8696ac5c70d0d700e6fd729fd83bc4`
> B9 planning base: `b9ddf7461306d16cf1da14634ce458050d78f7bc`
> 상태: `B8 complete / B9-0 PASS / B9-A merged and CI PASS / B9-B local PASS, remote closure pending`

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
5. 현재 bundle의 Task Card 또는 통합 계획
6. `docs/agent_handoff/AGENT_WORKFLOW.md`
7. `docs/agent_handoff/AGENT_WORKFLOW_POST_M3_01_ADDENDUM.md`
8. 관련 도메인·위험·평가 문서
9. 실제 최신 코드와 테스트

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
- M4 이후 A15-M, Stretch M2-09, M5-01, P1 순서

## 4. 현재 상태 요약

```text
M3-01:
PASS / complete
코드 BLOCKER 전부 CLOSED
Task Card 사실 동기화 완료, B6-0에서 상태 확인

현재 완료 bundle:
B8

B6 구현:
PASS / complete

B6 완료 SHA:
60e6203b265a967a8b6ba45da2ba3128e1e1bcfe

다음 공식 bundle:
B9

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
LOCAL PASS on release/b9-recorded-deployment
B9-B local verification:
targeted/full regression, M3 Gate 34/34, Critical 17/17, public exposure 0,
Ruff, secret/compile, clean Docker build, API/UI health, and 7-scenario smoke PASS
B9-B release-candidate commit/PR/CI:
implementation commit 6ed6c13a143f5798157aed2344d09ae126ced00b
release branch push complete
PR / merge / B9-B GitHub CI NOT_RUN
B9-B 원격 배포:
GCE target selected / deployment approval pending
M4 Gate:
B9 전체 완료 전까지 BLOCKED

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
B9-B remote deploy는 별도 승인 필요

M1-09:
mandatory supplement implemented - final independent review pending
```

## 5. 현재 bundle 문서

```text
completed:
docs/TASK_CARDS/B6-REMAINDER-integrated-implementation-plan.md
docs/TASK_CARDS/B7-integrated-implementation-plan.md
docs/TASK_CARDS/B8-quality-observability.md

current planning:
docs/TASK_CARDS/B9-release-deployment-traceability.md
```

## 6. 금지

- 대화 요약만 보고 구현 시작
- 이 인덱스에 없는 구버전 흐름 문서를 우선
- B6 전에 M3-06 또는 M3-08~11 구현
- M3-12 가격 기능 선행 구현
- 승인 없이 Streamlit 또는 다른 dependency 추가
- bundle 내부 checkpoint마다 임의 main push
- Task Card 상태와 실제 Git 상태 불일치 방치

## 7. 향후 갱신

새로운 계획 결정이 생기면 최소한 다음을 함께 갱신한다.

- 이 Source of Truth Index
- 실행 흐름 결정 기록
- Project Plan addendum 또는 본문
- Agent Workflow addendum 또는 본문
- 현재 Task Card
- 다음 bundle 계획
