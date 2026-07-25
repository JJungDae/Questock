# AGENT_WORKFLOW — BUNDLE CHECKPOINT ADDENDUM

> 기준일: 2026-07-25
> 적용 범위: B6 이후 bundle 단위 개발

## 1. 목적

하나의 bundle을 여러 로컬 checkpoint로 구현하면서도,
외부 검수 횟수를 줄이고 계약·테스트·Git 정합성을 보존한다.

## 2. 기본 원칙

```text
bundle 계획 검수
→ checkpoint 구현
→ checkpoint self-test
→ HANDOFF
→ 다음 checkpoint
→ bundle full regression
→ Git push
→ bundle 외부 구현 검수
```

## 3. checkpoint 진입 조건

다음 checkpoint는 모두 충족할 때만 시작한다.

- 현재 checkpoint targeted PASS
- 이전 checkpoint regression PASS
- vertical slice 또는 UI smoke PASS
- secret scan PASS
- compile PASS
- `git diff --check` PASS
- public schema 변경 없음
- 금지 파일 변경 없음
- BLOCKER 없음
- HANDOFF 작성 완료

## 4. checkpoint HANDOFF 필수 항목

```markdown
# BUNDLE CHECKPOINT HANDOFF

## Identity
- Bundle:
- Checkpoint:
- Starting SHA:
- Current HEAD:
- Branch:

## Scope
- Completed:
- Not completed:
- Deferred:

## Files
- Added:
- Modified:
- Unexpected:

## Contracts
- Public schema changed:
- Core/shared API changed:
- M1/M2 changed:
- Dependency changed:
- Lock changed:

## Verification
- Targeted:
- Previous checkpoint regression:
- Vertical slice/UI smoke:
- Full suite:
- Secret scan:
- Compile:
- Diff check:

## Findings
- BLOCKER:
- Required follow-up:
- Deferred note:

## Next checkpoint
- ALLOWED / BLOCKED
- Reason:
```

## 5. 외부 검수 trigger

다음은 로컬 자체 판정으로 넘기지 않는다.

- public schema
- core/shared API
- M1/M2 코드
- dependency/lock
- DB/migration/persistence
- provider/live source
- permission 정책
- Critical 실패
- wrong-company
- fake locator
- 직접 투자 조언
- raw prompt/secret/exception/path
- central file ownership 충돌
- 승인 범위 밖 기능

## 6. Git 운영

- checkpoint마다 main push하지 않는다.
- 로컬 commit 또는 diff snapshot은 허용 범위와 사용자 승인에 따른다.
- bundle 종료 전 full regression을 실행한다.
- bundle push 후 Task Card에 실제 SHA·commit·push를 기록한다.
- Git 작업은 별도 승인 원칙을 유지한다.
- 여러 checkpoint가 같은 파일을 수정하면 HANDOFF에서 ownership과 누적 변경을 기록한다.

## 7. 검수 결합

다음 조합은 허용한다.

```text
이전 bundle 구현 검수
+
다음 bundle 계획 검수
```

단, 응답에는 두 판정을 분리한다.

## 8. 실패 기록

- 첫 실패 명령을 삭제하지 않는다.
- 수정 이유와 rerun을 기록한다.
- 좁은 테스트만 통과시켜 전체 성공으로 표현하지 않는다.
- 환경 BLOCKED와 코드 FAIL을 구분한다.
- fixture/mock/live/CI/independent 결과를 구분한다.

## 9. 문서 갱신

bundle 완료 시 최소 갱신:

- 현재 Task Card
- 다음 Task 계획
- Source of Truth Index
- 계획 변경이 있으면 Decision Record
- Project Plan/Workflow addendum 또는 본문
