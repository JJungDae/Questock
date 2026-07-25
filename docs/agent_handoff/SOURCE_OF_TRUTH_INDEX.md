# QUESTOCK SOURCE OF TRUTH INDEX

> 기준일: 2026-07-25
> 기준 branch: `main`
> Pre-B6 code baseline: `d937d625e26495a3ee8c5a5b2c327dfbd2512ea9`
> Docs update/review base: `f5b3c646ec8696ac5c70d0d700e6fd729fd83bc4`
> 상태: `B6 PASS / B7 IMPLEMENTED - INDEPENDENT REVIEW PENDING`

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
B6-REMAINDER

B6 구현:
PASS / complete

B6 완료 SHA:
60e6203b265a967a8b6ba45da2ba3128e1e1bcfe

다음 공식 bundle:
B7

B7 계획:
docs/TASK_CARDS/B7-integrated-implementation-plan.md

B7 구현:
보완 계획 승인 / B7-0 preflight PASS / B7-A~C 구현 완료
초기 독립 구현 검수 CONDITIONAL PASS
초기 독립 M3 Gate 검수 FAIL
focused supplement 로컬 full tests 연속 2회 1763 passed
focused supplement 로컬 M3 Gate PASS: full 88.24%, Critical 100%, exposure 0
focused supplement 독립 closure review NOT_RUN
focused supplement commit/push NOT_RUN
B8 진입 BLOCKED

B7 implementation SHA/main push:
833336a002b1e02070b35cd4afe9aff279752d61 / complete
```

## 5. 현재 bundle 문서

```text
completed:
docs/TASK_CARDS/B6-REMAINDER-integrated-implementation-plan.md

current closure pending:
docs/TASK_CARDS/B7-integrated-implementation-plan.md
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
