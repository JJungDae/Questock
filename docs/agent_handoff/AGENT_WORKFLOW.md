# AGENT_WORKFLOW.md

> 작성일: 2026-07-20  
> 개정일: 2026-07-21  
> 개정 사유: P0 지원 종목 확정과 공동 기사 Evidence 귀속 계약 정합성 보완  
> 프로젝트: 증권 AI 투자 어시스턴트 프로토타입 개발  
> 목적: 여러 AI 코딩·문서 에이전트를 사용하더라도 프로젝트 범위, 코드 구조, 테스트 기준, Git 이력을 일관되게 유지하고, 사용자가 핵심 흐름을 직접 이해할 수 있도록 표준 작업 절차를 정의한다.  
> 기준 문서: `EXTENSION_COMPATIBILITY.md`, `RISK_RESPONSE_MATRIX.md`, `FINANCIAL_CAPABILITY_BASELINE.md`, `REFERENCE_SYNTHESIS.md`, `EVALUATION_TAXONOMY_DRAFT.md`

---

# 1. 핵심 원칙

## 1.1 사람의 역할

프로젝트의 최종 의사결정자는 사용자다.

AI 에이전트는 다음을 대신 결정하지 않는다.

- MVP 범위 변경
- P0·P1·P2 우선순위 변경
- 지원 종목 추가
- 데이터 provider 교체
- 새로운 DB·framework·agent framework 도입
- 투자 조언 정책 완화
- 테스트 실패를 무시한 merge
- 향후 계획 기능의 조기 구현

사용자는 최소한 다음 흐름을 직접 이해하고 승인해야 한다.

```text
질문이 어떤 intent로 분류되는가
→ 어떤 provider와 corpus를 사용하는가
→ 어떤 filter와 retrieval을 거치는가
→ Evidence가 어떻게 만들어지는가
→ 답변이 어떻게 검증되는가
→ 실패 시 어떤 fallback으로 이동하는가
```

## 1.2 에이전트 사용 목적

AI 에이전트는 개발 속도를 높이기 위한 도구다. 에이전트가 프로젝트 구조와 판단을 대신 소유하게 해서는 안 된다.

좋은 사용 방식:

- 범위가 고정된 작은 작업
- 명확한 입력·출력 계약이 있는 구현
- 반복 테스트와 문서화
- diff 검토가 가능한 수정
- 실패 조건이 명시된 실험
- 코드 흐름 설명과 handoff 작성

피해야 할 방식:

- “프로젝트 전체를 알아서 완성해줘”
- 여러 기능을 한 branch에서 동시에 구현
- 계획 없이 framework부터 도입
- 테스트 없이 대규모 리팩터링
- 한 에이전트가 만든 코드를 다른 에이전트가 무조건 덮어쓰기
- 사용자 검토 없이 자동 merge
- 문제 발생 시 기존 구조를 버리고 새로운 구조를 다시 생성

## 1.3 항상 작은 전체 흐름을 유지한다

각 Phase에서도 최소 하나의 end-to-end 흐름이 계속 동작해야 한다.

```text
입력
→ 종목 식별
→ intent routing
→ provider 또는 corpus
→ retrieval
→ Evidence
→ 답변
→ validation
→ UI
```

새 기능 때문에 이 흐름이 깨지면 신규 개발을 중단하고 복구를 우선한다.

초기 Phase에는 모든 실제 기능과 UI가 완성되어 있을 필요는 없다. 각 Phase는 다음 수준의 **phase-appropriate vertical slice**를 유지한다.

```text
M1: fake 또는 recorded fixture → provider/model → CLI·임시 API smoke
M2: 실제 filter·retrieval·Evidence → 최소 고정 응답
M3: 실제 AnswerComposer·Validator → 사용자 UI
M4: 배포 환경의 대표 질문 end-to-end
```

---

# 2. 문서 우선순위

에이전트는 다음 문서를 우선순위 순서대로 따른다.

| 순위 | 문서 | 역할 |
|---:|---|---|
| 1 | `PROJECT_PLAN.md` | 최종 일정·Step·완료 기준 |
| 2 | `EXTENSION_COMPATIBILITY.md` | P0·P1·P2·P3·X 기능 범위 |
| 3 | `RISK_RESPONSE_MATRIX.md` | 위험, fallback, 제거·중단 기준 |
| 4 | `FINANCIAL_CAPABILITY_BASELINE.md` | 코어 모델·인터페이스·상태 계약 |
| 5 | `EVALUATION_TAXONOMY_DRAFT.md` | 테스트 범주와 실패 조건 |
| 6 | `REFERENCE_SYNTHESIS.md` | 외부 저장소 참고·반면교사 |
| 7 | `IDEA_BACKLOG.md` | 아직 채택되지 않은 아이디어 |
| 8 | 개별 `TASK_CARD.md` | 이번 작업 범위와 명령 |

문서가 충돌하면 상위 문서를 따른다.

`IDEA_BACKLOG.md`에 존재한다는 이유만으로 기능을 구현하지 않는다. 최종 우선순위가 P0·P1·P2로 확정되고 `PROJECT_PLAN.md`의 Step에 포함된 기능만 구현한다.

---

# 3. 권장 에이전트 역할

한 에이전트에게 모든 역할을 맡기지 않는다. 같은 AI 제품을 사용하더라도 대화와 작업 단위를 분리한다.

이 문서의 Planning·Implementation·Review·Integration·Documentation·Release는 별도 인력 조직이 아니라 **솔로 개발자가 필요에 따라 전환하는 작업 모드**다. 저위험 작업까지 항상 별도 에이전트와 별도 문서를 요구하지 않는다.

## 3.1 Human Owner

책임:

- 범위·우선순위 승인
- 작업 카드 작성 또는 승인
- 에이전트 결과의 핵심 흐름 확인
- 테스트 결과 확인
- merge 승인
- 발표 대비 설명 정리
- 위험 상태 Green·Yellow·Red 판단

반드시 확인할 질문:

```text
이 변경은 어느 Step을 완료하는가?
P0에 꼭 필요한가?
어떤 입력과 출력을 갖는가?
어떤 테스트로 맞음을 증명하는가?
실패하면 어떻게 제거하는가?
기존 end-to-end 흐름에 어떤 영향을 주는가?
```

## 3.2 Planning Agent

사용 시점:

- 새로운 Phase 시작
- 큰 Step을 작은 Task로 분해
- 일정·의존성 검토
- 구현 순서와 중단 기준 정리

허용 작업:

- task 분해
- dependency map
- 파일 예상 변경 범위
- 테스트 계획
- risk ID 연결
- 완료 기준 작성

금지 작업:

- 승인 없이 코드 구현
- 새 framework 채택
- P1·P2 기능을 P0로 승격
- 저장소 전체 리팩터링 제안

출력:

- `TASK_BREAKDOWN.md`
- 개별 `TASK_CARD_*.md`
- 예상 branch 순서

## 3.3 Implementation Agent

사용 시점:

- 하나의 `TASK_CARD`가 승인된 후
- 변경 파일과 테스트 범위가 정해진 후

책임:

- 지정된 파일만 수정
- 기존 계약 준수
- 단위 테스트·fixture 작성
- 실행 결과 기록
- 변경 이유 설명
- handoff 작성

금지 작업:

- 범위 밖 파일 수정
- 새 기능 추가
- 다른 Task의 코드 선행 구현
- 임의 schema 변경
- 테스트 실패 숨김
- 직접 merge 또는 main push

## 3.4 Test and Review Agent

사용 시점:

- Implementation Agent의 self-test 완료 후
- merge 전

책임:

- 요구사항과 실제 diff 비교
- 회귀 테스트
- 실패 경로 테스트
- wrong-company·no-data·timeout·citation 검증
- 문서와 코드 일치 확인
- 과도한 abstraction·범위 확장 탐지

원칙:

- 구현 에이전트 설명을 신뢰하지 않고 실제 diff와 테스트로 검증
- 코드를 다시 대규모 수정하지 않음
- 수정이 필요하면 review report를 작성하고 구현 에이전트에게 반환

출력:

- `REVIEW_REPORT.md`
- PASS / CONDITIONAL PASS / FAIL
- 발견된 위험 ID
- 재작업 범위

## 3.5 Integration Agent

사용 시점:

- 독립 작업이 두 개 이상 merge될 때
- contract·import·migration 충돌 가능성이 있을 때

책임:

- main 최신화
- branch 순서 결정
- conflict 해결
- 전체 smoke test
- schema·migration 순서 확인
- 문서·실행 명령 갱신

금지 작업:

- 기능 요구사항 변경
- conflict 해결을 이유로 구현 새로 작성
- 테스트를 삭제해 merge 성공 처리

## 3.6 Documentation Agent

책임:

- 실제 구현 기준으로 README·architecture·runbook 갱신
- 실행 방법
- 환경변수
- API 입출력
- 제한사항
- 테스트 방법
- 현재 완료 범위와 미완료 범위 구분

금지 작업:

- 구현되지 않은 기능을 완료로 표현
- 외부 저장소 성능 수치를 자체 결과처럼 표현
- 테스트하지 않은 배포 성공 주장

## 3.7 Release Agent

사용 시점:

- Phase M4
- 배포·발표 후보 버전 생성

책임:

- clean environment 실행
- Docker 또는 지정 실행방법 확인
- health·smoke test
- demo dataset 기준일 확인
- secret·local path 노출 확인
- rollback 방법 기록
- release tag 후보 작성

---

# 4. 에이전트 작업 단위

## 4.1 한 Task의 적절한 크기

하나의 Task는 다음 조건을 만족해야 한다.

- 목적이 한 문장으로 설명됨
- 주된 출력이 하나임
- 수정 파일이 대체로 1~5개
- 테스트가 명확함
- 1회 agent session에서 완료 가능
- 실패 시 branch를 버릴 수 있음
- 다른 Task와 동일 파일 동시 수정이 최소화됨

좋은 Task 예:

```text
SecurityResolver에 exact ticker와 alias resolution을 추가하고
ambiguous candidate fixture를 통과시킨다.
```

나쁜 Task 예:

```text
RAG 백엔드, DB, UI, 로그인, 배포를 전부 구현한다.
```

## 4.2 하나의 Task에 포함하지 않을 조합

다음은 분리한다.

- provider 구현 + UI 디자인
- DB migration + 대규모 리팩터링
- retrieval 실험 + 답변 prompt 고도화
- 로그인 + RAG core 수정
- PDF parser + 수치 검증 + 그래프 UI
- 새로운 framework 도입 + 기능 구현
- 배포 설정 + 데이터 schema 변경

---

# 5. Git과 branch 운영

## 5.1 기본 규칙

```text
main
└─ phase/<phase-name>
   └─ task/<task-id>-<short-name>
```

권장 예:

```text
phase/m1-core-data
task/m1-01-security-models
task/m1-02-dart-provider
task/m1-03-report-ingest
```

혼자 작업하고 branch가 지나치게 많아지면 `phase/*`를 생략하고 `task/*`만 사용할 수 있다.

## 5.2 한 branch 한 목적

한 branch에는 하나의 Task만 포함한다.

금지:

- “나중에 필요할 것 같아서” 추가한 코드
- unrelated formatting
- 다른 기능의 schema
- 미완성 실험 파일
- 개인 환경 설정
- API key
- 생성형 AI 대화 로그

## 5.3 동시 작업

두 에이전트가 동시에 작업할 때:

- 같은 파일을 수정하지 않는 Task 우선
- 동일 contract에 의존하면 contract Task를 먼저 merge
- worktree 또는 별도 clone 사용
- branch 시작 전 main 최신화
- merge 순서를 `TASK_BREAKDOWN.md`에 기록

예:

```text
Task A: FinancialDocument model
→ 먼저 merge

Task B: NewsProvider
Task C: Report ingest
→ A merge 이후 병렬 가능
```

## 5.4 commit 원칙

한 commit은 한 의미를 가진다.

권장:

```text
feat(resolver): add ticker and alias resolution
test(resolver): add ambiguous security fixtures
docs(resolver): document supported universe
```

피해야 할 예:

```text
fix stuff
update
final
final2
```

## 5.5 merge 조건

다음이 모두 충족되어야 merge한다.

- Task 완료 기준 충족
- self-test 통과
- review pass 또는 conditional pass 해결
- main과 conflict 해결
- 전체 smoke test 통과
- 문서 갱신
- secret·temporary file 없음
- 사용자가 변경 흐름 이해

---

# 6. 표준 Task 생명주기

```text
Backlog
→ Ready
→ In Progress
→ Self-Test
→ Review
→ Rework 또는 Approved
→ Merge
→ Regression
→ Done
```

## 6.1 Backlog

아이디어 또는 미분해 작업 상태다. 구현하지 않는다.

필수 정보:

- 기능 이름
- P0·P1·P2·P3·X
- 관련 체크포인트
- 예상 데이터
- 관련 위험

## 6.2 Ready

다음이 확정된 상태다.

- 입력·출력
- 수정 허용 파일
- 완료 기준
- 테스트
- fallback
- 선행 Task
- branch 이름

## 6.3 In Progress

에이전트가 구현 중인 상태다.

중간에 새로운 요구가 발견되면 즉시 구현하지 않고 `OPEN_QUESTION`으로 기록한다.

## 6.4 Self-Test

Implementation Agent가 다음을 수행한다.

- unit test
- lint 또는 type check
- task-specific fixture
- 실패 경로
- 실행 명령 기록
- 실제 출력 요약

## 6.5 Review

독립 Review Agent 또는 사용자가 다음을 확인한다.

- 요구사항 누락
- 범위 밖 변경
- 기존 contract 위반
- 회귀
- 위험 대응 누락
- 이해하기 어려운 코드
- 불필요한 abstraction

## 6.6 Merge

사용자 승인 후 merge한다. 에이전트가 임의로 main에 merge하지 않는다.

## 6.7 Regression

merge 후 전체 핵심 테스트를 실행한다. 실패하면 다음 Task로 넘어가지 않고 rollback 또는 hotfix를 수행한다.

---

# 7. TASK_CARD 표준 양식

## 7.1 정식 절차와 간소 절차

### 정식 절차

다음 작업은 정식 `TASK_CARD → 구현 → Self-Test → Review → HANDOFF`를 사용한다.

- core model·interface
- provider·retrieval·Evidence
- 금융 답변·수치 검증·가드레일
- 인증·DB migration
- 배포·secret·관측
- 여러 파일 또는 contract에 영향을 주는 작업

### 간소 절차

다음과 같은 저위험 작업은 짧은 기록으로 대체할 수 있다.

- UI 문구·CSS
- 소규모 문서 수정
- 기존 contract를 바꾸지 않는 fixture 추가
- 단순 설정값 수정
- 1~2개 파일의 국소 변경

간소 기록 필수 항목:

```text
목적
변경 파일
검증 명령
결과
```

간소 절차도 main 자동 merge, 테스트 삭제, 범위 밖 변경은 허용하지 않는다.

각 작업 전 다음 형식의 파일을 만든다.

```markdown
# TASK_CARD — <TASK_ID> <제목>

## 1. 목적
이번 작업이 해결하는 문제를 한 문장으로 작성한다.

## 2. 관련 계획
- Phase:
- Step:
- 우선순위: P0/P1/P2
- 체크포인트:
- 관련 위험 ID:

## 3. 입력
- 사용 모델·interface:
- 사용 데이터:
- 선행 구현:

## 4. 출력
- 생성·수정할 API:
- 생성·수정할 파일:
- 반환 구조:

## 5. 수정 허용 범위
- 수정 가능:
- 수정 금지:

## 6. 구현 요구사항
1.
2.
3.

## 7. 비기능 요구사항
- timeout:
- error handling:
- logging:
- security:
- token/context budget:

## 8. 완료 기준
- [ ]
- [ ]
- [ ]

## 9. 테스트
- 정상:
- no-data:
- timeout:
- invalid input:
- regression:

## 10. fallback
기능이 실패할 경우 사용할 단순 대체 경로.

## 11. 중단 기준
어떤 조건에서 이 작업을 중단하거나 범위를 줄이는가.

## 12. 최종 반환물
- 변경 파일
- 테스트 결과
- HANDOFF
- 미해결 질문
```

---

# 8. Implementation Agent 프롬프트 템플릿

```markdown
당신은 증권 AI 투자 어시스턴트 프로젝트의 구현 에이전트입니다.

첨부 문서 우선순위:
1. PROJECT_PLAN.md
2. EXTENSION_COMPATIBILITY.md
3. RISK_RESPONSE_MATRIX.md
4. FINANCIAL_CAPABILITY_BASELINE.md
5. 현재 TASK_CARD

이번 작업은 TASK_CARD에 정의된 범위만 수행하세요.

필수 규칙:
- 수정 허용 파일 밖을 변경하지 마세요.
- 새로운 framework나 dependency를 임의로 추가하지 마세요.
- P1·P2·P3 기능을 선행 구현하지 마세요.
- TASK_CARD에 승인되지 않은 model·interface 변경이 필요하면 즉시 중단하고 이유를 보고하세요. 승인된 contract Task에서는 변경 전후 schema test와 영향 파일 목록을 제공하세요.
- 테스트를 삭제하거나 완화해 성공 처리하지 마세요.
- 외부 API 오류와 no-data를 구분하세요.
- 근거 없는 금융 답변이나 직접 투자 조언을 추가하지 마세요.
- main에 merge하거나 push하지 마세요.

작업 순서:
1. TASK_CARD와 관련 코드를 읽습니다.
2. 현재 흐름과 예상 변경 파일을 10줄 이내로 요약합니다.
3. 구현합니다.
4. 지정 테스트와 실패 경로 테스트를 실행합니다.
5. diff를 자체 검토합니다.
6. HANDOFF_TEMPLATE 형식으로 결과를 반환합니다.

완료 응답에는 다음을 포함하세요.
- 변경 파일
- 핵심 구현
- 실행한 명령
- 테스트 결과
- 남은 문제
- 위험 ID
- 사용자에게 설명할 코드 흐름
```

`TASK_CARD`가 명확하면 계획 승인 요청을 반복하지 말고 바로 작업한다. 단, TASK_CARD에 승인되지 않은 contract 변경이나 범위 확장이 필요하면 구현하지 말고 중단 보고한다.

---

# 9. Review Agent 프롬프트 템플릿

```markdown
당신은 독립 코드 리뷰·테스트 에이전트입니다.

구현 에이전트의 설명을 사실로 간주하지 말고
TASK_CARD, 실제 diff, 테스트 결과를 기준으로 검증하세요.

검토 항목:
1. TASK_CARD 완료 기준 충족
2. 범위 밖 파일 변경
3. core contract 위반
4. P1·P2 기능의 조기 구현
5. no-data·timeout·low relevance 혼합
6. wrong-company evidence 가능성
7. citation locator 보존
8. 숫자·날짜 변형
9. 투자 조언·예측 표현
10. 회귀 테스트
11. secret·local path 노출
12. 과도한 abstraction
13. 사용자가 설명하기 어려운 코드

직접 대규모 수정하지 마세요.
문제가 있으면 정확한 파일·함수·재현 단계와 함께
REVIEW_REPORT를 작성하세요.

최종 판정:
- PASS
- CONDITIONAL PASS
- FAIL
```

---

# 10. HANDOFF 표준 양식

Implementation Agent는 작업 종료 시 다음을 작성한다.

```markdown
# HANDOFF — <TASK_ID>

## 1. 작업 결과
- 완료:
- 미완료:
- 범위 변경:

## 2. 변경 파일
| 파일 | 변경 이유 |
|---|---|

## 3. 코드 흐름
입력부터 출력까지 순서대로 설명한다.

## 4. 실행 명령
```bash
...
```

## 5. 테스트 결과
| 테스트 | 결과 | 비고 |
|---|---|---|

## 6. 실패 경로
- no-data:
- timeout:
- invalid input:
- fallback:

## 7. 관련 위험
- 예방한 위험:
- 남은 위험:

## 8. 사용자 확인 필요
1.
2.

## 9. 다음 Task의 선행 조건
-
```

Handoff 없이 “완료했습니다”만 반환한 작업은 완료로 인정하지 않는다.

---

# 11. Phase별 에이전트 운영

## 11.1 Phase M0 — 범위 확정

주 에이전트:

- Planning Agent
- Documentation Agent

작업:

- 삼성전자·SK하이닉스·현대자동차 3개 보통주 확정
- provider 후보 결정
- 리포트와 glossary 목록
- intent 범위
- UI wireframe
- golden set 초안
- Task 분해

완료 산출물:

- `PROJECT_PLAN.md`
- `TASK_BREAKDOWN_M0_M4.md`
- 초기 `TASK_CARD`
- 데이터 manifest 초안

## 11.2 Phase M1 — 데이터·API

주 에이전트:

- Implementation Agent
- Test and Review Agent
- Integration Agent

권장 Task 순서:

```text
M1-01 core models — multi-company document/Evidence attribution fields 포함
M1-02 security resolver
M1-03 provider result·error taxonomy
M1-04 news adapter
M1-05 disclosure adapter
M1-06 research report manual ingest
M1-07 glossary ingest
M1-08 health·config·secret handling
M1-09 MarketSnapshot adapter·timezone·market session fixture — A15-M 조건부 P0 gate
```

병렬 작업은 core models와 contract merge 이후에만 허용한다.

## 11.3 Phase M2 — retrieval·evidence

권장 Task:

```text
M2-01 intent routing
M2-02 hard filter — document 관련 종목과 Evidence 주체 종목을 단계적으로 검증
M2-03 retrieval baseline
M2-04 Evidence normalization — subject_security_ids·mentioned_security_ids·scope
M2-05 freshness
M2-06 EvidencePolicy와 low_relevance→partial/no_evidence 매핑
M2-07 citation validation
M2-08 token·context budget
M2-09 market-session temporal filter — A15-M 승격 시
```

hybrid·reranker는 baseline이 안정된 후 별도 실험 Task로 둔다.

## 11.4 Phase M3 — answer·UI

권장 Task:

```text
M3-01 answer schema와 안정적인 단일 응답 방식
M3-02 beginner explanation
M3-03 fact·interpretation·inference
M3-04 positive·risk·uncertainty cards
M3-05 glossary answer
M3-06 anonymous multi-turn
M3-07 source detail·error·missing-source UI
M3-08 policy validator
M3-09 basic numeric·date·unit·subject-security attribution validation
M3-10 conflicting evidence minimal view
M3-11 multi-source explanation minimal flow
M3-12 price-move background response — A15-M 승격 시
M3-13 second viewpoint mode
M3-14 business outlook limited card
```

UI와 backend contract를 동시에 임의 변경하지 않는다. 먼저 API response schema를 고정하고 UI가 이를 소비한다.

## 11.5 Phase M4 — 안정화·배포

권장 Task:

```text
M4-01 provider failure tests
M4-02 golden set regression — A15-M 승격 시 price_move_reason 포함
M4-03 minimum observability fields
M4-04 Docker or fixed runtime
M4-05 deployment smoke
M4-06 demo scenario
M4-07 documentation
M4-08 active P0 traceability gate review
```

M4에서는 새로운 P0 기능을 추가하지 않는다.

## 11.6 Phase A1 — P1 추가 구현

P0가 완성된 후 두 묶음 중 하나를 먼저 선택한다.

### P1-RAG 품질

```text
A1-R01 financial metric trend
A1-R02 numeric validation advanced
A1-R03 conflicting evidence grouping
A1-R04 news deduplication
```

### P1-User 기능

```text
A1-U01 auth design
A1-U02 user model·migration
A1-U03 signup/login/logout
A1-U04 user conversation persistence
A1-U05 conversation list·restore
A1-U06 watchlist
A1-U07 user isolation tests
```

선택 규칙:

```text
M4 종료 후 RAG 품질 결함이 남음
→ P1-RAG 품질 우선

핵심 RAG가 안정적이고 제품 사용성 보완이 더 중요함
→ 공개 익명 경로를 유지한 채 P1-User 기능 우선
```

로그인과 재무 추세 기능은 서로 다른 branch와 Task로 분리한다.

---

# 12. 충돌 방지와 통합 규칙

## 12.1 동일 파일 잠금

다음 파일은 동시에 여러 에이전트가 수정하지 않는다.

- core models
- API schema
- DB migration
- central config
- workflow orchestration
- main UI response renderer
- dependency lock file

`TASK_BREAKDOWN`에 파일 소유 Task를 명시한다.

## 12.2 Contract-first 순서

다음 순서를 지킨다.

```text
model/interface
→ fake·fixture
→ provider/repository
→ service/workflow
→ API
→ UI
→ integration test
```

UI가 필요하다는 이유로 backend model을 임의 생성하지 않는다.

## 12.3 Migration 순서

DB migration은 한 branch에서 순차적으로 관리한다.

- migration 번호 중복 금지
- 이전 migration 수정 금지
- 사용자 데이터 기능은 P1 branch에서만 추가
- migration rollback 또는 초기화 방법 기록

## 12.4 Dependency 추가

새 dependency는 다음을 기록한 뒤 승인한다.

- 필요한 이유
- 표준 라이브러리나 기존 dependency로 불가능한 이유
- license
- 배포 영향
- 제거 방법
- lock file 변화

---

# 13. 에이전트 오작동 대응

## 13.1 다음 징후가 있으면 즉시 중단한다

- 계획에 없는 파일을 대량 수정
- 기존 문서를 무시하고 architecture를 다시 설계
- 빈 class·table·graph node를 대량 생성
- 테스트 삭제
- 외부 저장소 코드를 통째로 복사
- GitHub를 다시 조사하기 시작
- 직접 투자 추천 기능 추가
- main에 자동 merge
- “모든 작업 완료”라고 하지만 파일·테스트가 없음
- 같은 수정 전 파일을 반복 반환

## 13.2 복구 절차

```text
1. 현재 branch 작업 중단
2. git diff와 생성 파일 목록 저장
3. 정상 commit으로 reset
4. 문제 원인을 TASK_CARD와 비교
5. Task를 더 작게 분해
6. 새로운 에이전트에게 clean branch 제공
7. 수정 대상·금지 파일·문자열 검증 명시
```

큰 문제가 있는 결과를 수동으로 조금씩 고쳐 살리려 하지 않는다. 재작업 비용이 낮으면 branch를 폐기하고 더 작은 Task로 다시 수행한다.

## 13.3 새 에이전트 handoff

새 에이전트에는 필요한 자료만 전달한다.

필수:

- 현재 `TASK_CARD`
- 관련 contract 문서
- 수정 대상 파일
- 직전 HANDOFF 또는 REVIEW_REPORT
- 실행 명령
- 실패 재현 방법

불필요:

- 전체 과거 대화
- 모든 연구 ZIP
- 관련 없는 Phase 문서
- 이전 에이전트의 장황한 추론
- 아직 채택하지 않은 아이디어 전체

자료가 많을수록 에이전트가 범위를 재해석할 가능성이 커진다.

---

# 14. 사용자의 코드 이해 절차

각 Task merge 전 사용자는 다음을 직접 확인한다.

## 14.1 5문장 설명

1. 이 기능은 어떤 입력을 받는가?
2. 어느 파일·함수에서 시작하는가?
3. 어떤 데이터 또는 provider를 사용하는가?
4. 성공 시 무엇을 반환하는가?
5. 실패 시 어떤 상태와 fallback을 반환하는가?

## 14.2 직접 실행

최소 한 번은 에이전트가 아닌 사용자가 직접 실행한다.

```text
서버 실행
→ 대표 요청
→ 로그 확인
→ 테스트 한 개 실행
→ 실패 fixture 한 개 실행
```

## 14.3 발표 대비 기록

Task마다 다음을 개인 노트에 남긴다.

- 구현 목적
- 핵심 파일 1~3개
- 중요한 model
- 정상 흐름
- 실패 흐름
- 실제 해결한 문제
- 남은 제한

---

# 15. 5시간 작업 운영 예시

사용자가 하루 5시간 정도 프로젝트 작업을 진행하는 경우 권장 흐름이다.

| 시간 | 활동 |
|---|---|
| 0:00~0:20 | 전날 상태·회귀 테스트·오늘 Task 확정 |
| 0:20~0:50 | TASK_CARD 작성·에이전트 프롬프트 준비 |
| 0:50~2:20 | Implementation Agent 작업과 사용자 코드 읽기 |
| 2:20~2:40 | 휴식·진행 상태 정리 |
| 2:40~3:30 | self-test·직접 실행·오류 재현 |
| 3:30~4:15 | Review Agent 검수·재작업 |
| 4:15~4:40 | merge·전체 회귀 테스트 |
| 4:40~5:00 | HANDOFF·일일 기록·다음 Task 준비 |

원칙:

- 하루에 큰 Task 하나 또는 작은 Task 두 개만 완료
- merge되지 않은 작업을 여러 개 쌓지 않음
- 마지막 45분은 신규 개발이 아니라 검증·문서화에 사용
- 당일 end-to-end 흐름이 깨졌다면 복구 후 종료

---

# 16. Definition of Done

Task는 **공통 필수 항목**과 **해당 Task에 적용되는 조건부 항목**을 만족해야 완료다.

## 16.1 공통 필수

- [ ] TASK_CARD 또는 간소 기록의 범위만 구현
- [ ] 정상 검증 또는 테스트 통과
- [ ] 기존 회귀 테스트에 악영향 없음
- [ ] secret·local absolute path 미노출
- [ ] 문서와 실제 코드 일치
- [ ] 사용자가 변경 목적과 흐름을 설명 가능

## 16.2 조건부 항목

다음은 해당 Task에 적용될 때만 요구한다.

- [ ] model·API Task: 입력·출력 contract와 schema test
- [ ] provider Task: no-data·timeout·provider error 구분
- [ ] retrieval·답변 Task: Evidence·locator와 wrong-company 검증
- [ ] 금융 답변 Task: 숫자·날짜·단위와 투자 조언 정책 검증
- [ ] 정식 절차 Task: HANDOFF 작성
- [ ] merge Task: merge 후 phase-appropriate vertical slice 또는 end-to-end smoke
- [ ] P0 UI 기능: 실제 사용자 화면에서 확인

backend 코드만 존재하거나 최종 Phase에서도 mock 응답만 반환하면 P0 완료로 보지 않는다.

---

# 17. 최종 프로젝트 계획서와의 연결

`PROJECT_PLAN.md`의 각 Step에는 다음을 포함한다.

```text
Step ID
목적
우선순위
선행 조건
담당 에이전트 역할
수정 예상 영역
입력·출력
구현 Task
완료 기준
테스트
위험 ID
fallback
중단 기준
다음 Step 진입 조건
```

모든 활성 P0 코어·아이디어 기능은 `EXTENSION_COMPATIBILITY.md`의 두 추적 표에 따라 하나 이상의 Step·gate·taxonomy에 연결되어야 한다. 연결되지 않은 P0 기능은 계획 확정 상태로 보지 않는다.

예시:

```markdown
## Step M2-04 — Evidence Normalization

- 우선순위: P0
- 담당: Implementation Agent → Review Agent
- 선행: provider adapter와 FinancialDocument 완료
- 입력: ProviderResult[FinancialDocument]
- 출력: Evidence
- 주요 위험: R25, R29, R45
- 완료 기준:
  - security_id 일치
  - snippet 존재
  - URL 또는 locator 존재
  - local absolute path 미노출
- 테스트:
  - news URL
  - DART receipt locator
  - report manifest ID와 page
- fallback:
  - locator 없는 문서는 답변 근거에서 제외
- 다음 Step:
  - citation validation
```

---

# 18. 최종 원칙

```text
계획 문서가 범위를 정한다.
TASK_CARD 또는 간소 기록이 이번 작업의 범위를 정한다.
한 에이전트는 한 Task만 수행한다.
구현 에이전트와 리뷰 에이전트를 분리한다.
모든 작업에는 검증 기록이 필요하다.
정식 절차 작업에는 HANDOFF가 필요하다.
P0 완료 전 P1을 시작하지 않는다.
사용자가 설명하지 못하는 코드는 merge하지 않는다.
```

에이전트의 목적은 코드를 대신 소유하는 것이 아니라, 사용자가 통제 가능한 작은 단위로 프로젝트를 완성하도록 돕는 것이다.
