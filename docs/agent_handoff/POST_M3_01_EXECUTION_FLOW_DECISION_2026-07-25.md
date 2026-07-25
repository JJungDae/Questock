# POST-M3-01 EXECUTION FLOW DECISION

> Decision ID: `QUESTOCK-FLOW-2026-07-25`
> 상태: `APPROVED FLOW / IMPLEMENTATION REQUIRES BUNDLE PLAN APPROVAL`
> 기준 SHA: `d937d625e26495a3ee8c5a5b2c327dfbd2512ea9`
> 기준 commit: `m3-01 conditional pass2 updates`

## 1. 결정 배경

M3-01 이후 남은 M3·M4 작업은 개별 Step마다 외부 검수를 반복하면
검수 비용이 커지고 P1 구현 가능성이 낮아진다.

반대로 남은 M3 전체를 한 번에 구현하면 다음 위험이 커진다.

- 동일 파일 충돌
- schema drift
- validator와 UI의 동시 확장
- 회귀 원인 추적 실패
- 로컬 에이전트가 중간 실패를 숨긴 채 다음 기능으로 진행
- 최종 검수에서 대규모 재작업 발생

따라서 공식 bundle은 유지하되, bundle 내부를 로컬 checkpoint로 나누고
외부 검수는 bundle 종료 시 통합 수행하는 방식을 채택한다.

## 2. M3-01 최종 상태

```text
Second supplement SHA:
d937d625e26495a3ee8c5a5b2c327dfbd2512ea9

Second supplement commit:
m3-01 conditional pass2 updates

Code blockers:
CLOSED

Final closure review:
PASS WITH REQUIRED FOLLOW-UP

Required follow-up:
Task Card factual synchronization only

M3-01 final state:
PASS / complete
```

M3-01에 대한 추가 코드 closure review는 요구하지 않는다.

## 3. 최종 실행 순서

```text
B6-0
M3-01 factual sync
→ M3-01 schema freeze
→ evaluation-asset inventory

B6-A
M3-15A Streamlit shell/scaffold

B6-B
M3-02 beginner structure
→ M3-03 fact/interpretation/inference
→ M3-14 report integration criterion

B6-C1
M3-05 glossary answer path

B6-C2
M3-04 answer cards
→ M3-07 source/error/stale projection

B6 implementation review
→ 같은 요청에서 B7 plan review 가능

B7-A
M3-06 anonymous session/reset

B7-B1
M3-08 safety validator
→ M3-09 number/date/unit/company validator

B7-B2
M3-10 conflicting Evidence
→ M3-11 limited multi-source connection
→ M3-15B final UI connection

B7-C
golden/Critical runner가 미준비일 때만 evaluation closure

B7 implementation review
+ M3 Gate
(같은 요청, 판정은 분리)

B8
M4-01~03 failure/golden/observability
→ B8 review

B9-A
M4-04 CI
→ M4-05 clean local Docker/container

B9-B
M4-05 remote deployment
→ M4-06 demo
→ M4-07 docs/presentation
→ M4-08 traceability
→ B9 review + M4 Gate

M4 PASS
→ A15-M activation check
→ 필요 시 Stretch M2-09
→ M5-01

M5-01 완료 또는 Human Owner의 명시적 생략
+ 최종 회귀·문서화 버퍼 1세션
+ 최소 3개 전체 세션 잔여
→ P1 시작 가능
```

## 4. M3-15 분리 결정

### M3-15A — B6 소유

- Streamlit entry point
- 질문 입력
- 지원 종목 selector shell
- 안정적인 `ChatResponse + PublicProcessSummary` 소비
- 답변·source component interface
- 분석 과정 expander
- data mode와 status family 표시
- AppTest와 startup smoke

### M3-15B — B7 소유

- M3-06의 실제 session/reset 연결
- M3-10·11 결과 표시
- 최종 source·answer 통합
- M3 Gate UI closure

B6 종료 시 M3-15 전체를 `complete`로 표시하지 않는다.

## 5. 검수 운영 결정

### 계획 검수

- B6 시작 전 1회
- B7 시작 전 1회
- B8 시작 전 1회
- B9 시작 전 1회

### 구현 결과 검수

- B6 통합 1회
- B7 통합 + M3 Gate 1회
- B8 통합 1회
- B9 통합 + M4 Gate 1회

이전 bundle의 결과 검수와 다음 bundle의 계획 검수는 같은 요청으로 묶을 수 있다.

### 로컬 checkpoint 자체 검수

각 checkpoint는 다음을 남긴다.

- 시작 SHA
- 변경 파일
- targeted test
- 이전 checkpoint regression
- vertical-slice 또는 UI smoke
- secret scan
- compile
- `git diff --check`
- BLOCKER / deferred note
- 다음 checkpoint 진입 판정
- HANDOFF

## 6. 즉시 외부 검수로 전환하는 trigger

- `ChatResponse` 또는 `PublicProcessSummary` 변경
- core/shared API 변경
- M1/M2 코드 변경
- 승인되지 않은 dependency 또는 lock 변경
- DB·migration·영구 persistence
- provider/live source 추가
- 외부 전송 permission 변경
- Critical test 실패
- wrong-company·fake locator·직접 투자 조언 재발
- raw prompt·secret·exception·local path 노출
- 하나의 checkpoint가 세 개 이상의 독립 code boundary로 확장
- checkpoint 간 central file 충돌
- 기존 계획 범위를 넘어서는 새 기능

## 7. Golden/Critical 평가 자산 결정

- B6 Gate 0에서 존재·경로·case count를 inventory한다.
- B7 Gate 0에서 실제 실행 가능성과 taxonomy 집계를 검증한다.
- 미준비 시 B7-C를 추가한다.
- M3 Gate에 필요한 자산을 B8의 M4-02로 미루지 않는다.
- B6에서는 M3 Gate 점수를 주장하지 않는다.

## 8. Dependency 결정

B6는 Streamlit 영구 dependency를 추가할 수 있으므로 총괄 계획 검수가 필요하다.

계획 검수에서 확인할 내용:

- exact stable/non-yanked version
- Python 호환성
- license
- direct/transitive lock diff
- clean install
- AppTest
- startup smoke
- rollback

승인된 exact version과 lock 범위가 유지되는 동안 같은 dependency 이유로
checkpoint마다 총괄 재검수를 반복하지 않는다.

## 9. UI 파일 ownership

```text
M3-15A:
entry point, shell, transport boundary, component interface, process expander

M3-04:
AnswerSections → answer-card projection

M3-07:
Evidence → safe source-detail projection, 오류·stale wording
```

UI orchestration·transport·projection을 하나의 central file에 합치지 않는다.

## 10. M3-12와 M5-01

M3-12는 현재 M3에서 `NOT_ACTIVATED`다.

금지:

- price response schema
- MarketSnapshot 연결
- 가격 원인 prompt
- 가격 UI
- M2-09 우회 구현

M4 Gate 후 activation check에서만 재검토한다.

## 11. 세션 예상

```text
B6:
3~4 local checkpoints

B7:
3~4 local checkpoints

B8:
1 local bundle session

B9:
2 local checkpoints

안전 추정:
전체 8~9 local sessions
```

세션 수는 품질 gate를 생략하기 위한 상한이 아니다.

## 12. 이 결정이 대체하는 내용

이 결정은 다음과 충돌하는 이전 제안을 대체한다.

- M3-15를 B6에서 한 번에 최종 완료 처리
- M3-02~11을 각각 단독 외부 검수
- B7 validator와 advanced answer 전체를 한 checkpoint에 구현
- M3 Gate 평가 자산을 M4에서 처음 준비
- M3-12를 현재 M3에서 조건부 선행 구현
- M3-01에 추가 코드 closure를 요구하는 구버전 상태
