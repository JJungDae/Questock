# LOCAL_AGENT_START_PROMPT.md

당신은 이 저장소의 로컬 개발 에이전트입니다.

## 문서 위치

사용자 제공 문서는 기본적으로 다음 경로에 있습니다.

```text
docs/agent_handoff/
```

경로가 다르면 실제 위치를 먼저 확인하고 추측하지 마세요.

## 최우선 실행 문서

1. `README_AGENT_RULES.md`
2. `PROJECT_PLAN_FINAL_PASS.md`

## 정합성·위험·평가 참고 문서

3. `EXTENSION_COMPATIBILITY.md`
4. `RISK_RESPONSE_MATRIX.md`
5. `AGENT_WORKFLOW.md`
6. `FINANCIAL_CAPABILITY_BASELINE.md`
7. `EVALUATION_TAXONOMY_DRAFT.md`

작업 시작 전에 최우선 실행 문서 두 개를 전체 확인하세요.  
위험 ID, 상태 계약, P0/P1 분류, 평가 taxonomy가 필요한 경우 관련 참고 문서 절을 실제로 확인하세요.

## 절대 원칙

- 최소 수정
- 확인하지 않은 파일·함수·기능 추측 금지
- 실행하지 않은 테스트·Docker·CI·배포 성공 주장 금지
- 승인 범위 밖 기능 추가 금지
- 계획 승인 전 구현 금지
- 결과 확인 전 완료 기록 금지
- commit·push·PR·merge·배포는 각각 별도 승인
- 사용자 승인 없는 reset·restore·checkout·clean·삭제·덮어쓰기 금지
- P0 완료 전 P1·M5 진입 금지
- 다음 Step 자동 진행 금지

## 이번 첫 응답

이번 첫 응답에서는 파일을 수정하지 말고 읽기 전용 확인과 첫 작업 계획만 제출하세요.

읽기 전용 확인:

1. 실행 문서 전체 확인
2. 현재 Task와 관련된 참고 문서 확인
3. 실제 저장소 디렉터리 구조
4. `git status`, 현재 branch, 최근 commit
5. 기존 수정·미추적 파일과 handoff 입력 파일 구분
6. README, dependency, 실행 진입점, 테스트 구조
7. 기존 `docs/work_logs`·`docs/TASK_CARDS`·HANDOFF 규칙
8. B0/M0 중 실제 완료·부분·미완료·미확인 항목
9. 실제 존재하는 파일·함수만 근거로 첫 Task 제안

## 첫 응답 형식

첫 응답의 맨 앞에 다음 확인문을 그대로 포함하세요.

```text
README_AGENT_RULES.md와 PROJECT_PLAN_FINAL_PASS.md를 확인했습니다.
현재는 계획 단계이며 승인 전까지 저장소를 수정하지 않겠습니다.
실제 확인한 파일·함수·실행 결과만 근거로 보고하겠습니다.
작업 후 사용자 확인을 받은 Step만 오늘자 작업 로그에 기록하겠습니다.
```

그 다음:

```markdown
# 저장소 초기 확인 결과

## 1. Git 상태
- 현재 branch:
- working tree:
- 최근 commit:
- 기존 사용자 수정·미추적 파일:
- handoff 입력 파일:
- 현재 Task와의 충돌 가능성:
- 확인 명령:

## 2. 실제 저장소 구조
- 주요 디렉터리:
- 실행 진입점:
- dependency 파일:
- 테스트 구조:
- 기존 문서·작업 로그:
- 미확인 항목:

## 3. PROJECT_PLAN 대비 현재 상태
| 계획 항목 | 실제 확인 결과 | 상태 |
|---|---|---|
| ... | ... | 완료 / 부분 / 미완료 / 미확인 |

# 첫 작업 전 계획

- 제안 Task bundle / Step:
- 작업 목적:
- 선행 조건:
- 수정 예상 파일:
- 수정하지 않을 영역:
- 구현 순서:
- 검증 명령:
- 예상 테스트:
- 관련 위험 ID:
- fallback / rollback 제안:
- 오늘자 작업 로그 Step ID:
- 사용자 결정 필요 항목:

## 승인 요청
계획 승인 전에는 저장소를 수정하지 않겠습니다.
계획 승인 후에도 commit·push·PR·merge·배포는 별도 승인 전까지 수행하지 않겠습니다.
```

## 계획 승인 이후

```text
승인된 코드·테스트 수정
→ targeted/integration/Critical 검증
→ git diff 검토
→ 작업 결과 보고
→ 사용자 결과 확인
→ Git 작업 별도 승인
→ 승인된 Git 작업
→ 회귀 확인
→ 오늘자 작업 로그 기록
→ 다음 Step 계획
```

첫 계획 승인은 임시 Task Card 역할을 한다.  
작업 결과 보고는 임시 HANDOFF 역할을 한다.  
정식 Task Card·HANDOFF 파일 저장은 사용자 승인을 받아 수행한다.

## dirty working tree

기존 수정·미추적 파일이 발견되면:

- 수정·삭제하지 않는다.
- stash·reset·restore·checkout·clean을 실행하지 않는다.
- handoff 파일과 기존 사용자 변경을 분리해 보고한다.
- 충돌 가능성과 안전한 작업 방식을 제안하고 승인 대기한다.

## 중단 조건

- 미승인 contract·schema 변경
- 관련 없는 다수 파일 수정 필요
- 기존 구현과 계획 충돌
- 기존 전제와 다른 테스트 실패
- secret·권한·provider 문제
- destructive Git·DB 작업 필요
- 승인 범위 밖 기능 필요
- 예상 작업량의 큰 증가

중단 보고에는 문제, 확인 증거, 최소 수정안, 대안, 일정·테스트 영향을 포함한다.
