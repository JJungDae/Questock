# EXTENSION_COMPATIBILITY.md

> 작성일: 2026-07-20  
> 개정일: 2026-07-21  
> 개정 사유: P0 지원 종목 확정과 공동 기사 Evidence 귀속 계약 정합성 보완  
> 프로젝트: 증권 AI 투자 어시스턴트 프로토타입 개발  
> 목적: `IDEA_BACKLOG.md`의 아이디어를 프로젝트 필수 체크포인트, 현재 금융 RAG 코어 계약, 데이터 준비도, 평가 가능성, 남은 개발 기간에 맞춰 다시 분류한다.  
> 입력 문서: `IDEA_BACKLOG.md`, `FINANCIAL_CAPABILITY_BASELINE.md`, `REFERENCE_SYNTHESIS.md`, `EVALUATION_TAXONOMY_DRAFT.md`  
> 주의: 이 문서는 구현 계획서를 대신하지 않는다. **어떤 기능을 MVP에 확정하고, 어떤 기능을 MVP 이후 실제로 구현 시도하며, 어떤 기능을 발표의 향후 계획으로 남길지 결정하는 기준 문서**다.

---

# 1. 프로젝트 필수 체크포인트

## 체크포인트 1 — 최신 금융 자료 기반 RAG API

주요 종목의 최신 리포트, 공시, 뉴스 데이터를 기반으로 질문에 답하는 RAG API를 안정적으로 구축해야 한다.

필수 증명 항목:

- 삼성전자·SK하이닉스·현대자동차 3개 보통주의 canonical 종목·법인 식별
- 뉴스·공시·리서치 리포트 3종 지원
- 질문 의도에 따른 데이터 유형 선택
- 종목·기간·자료 유형 hard filter
- 원문 locator와 근거 snippet 반환
- 근거 충분성 판단과 답변 보류
- 외부 API timeout·rate limit·no-data 구분
- 자료 기준일과 최신성 표시
- 안정적인 단일 응답 방식 제공. sync와 streaming을 모두 구현한 경우에만 동일 orchestration 결과의 일관성 검증
- 재현 가능한 최소 평가셋과 회귀 테스트

리서치 리포트는 초기부터 실시간 자동 수집할 필요가 없다. 이용 조건을 확인한 자료를 수동 정규화하여 corpus로 적재할 수 있다.

## 체크포인트 2 — 금융 정보를 누락 없이 명확하게 전달하는 UI

복잡한 금융 용어와 분석 정보가 초보 사용자에게 직관적이고 명확하게 전달되어야 한다.

MVP UI에서 우선 표시할 요소:

- 종목명과 ticker
- 분석 기준일
- 답변 모드
- 핵심 요약
- 확인된 사실
- 자료의 해석
- AI의 제한적 추론과 불확실성
- 긍정 요인
- 위험 요인
- 근거 강도 또는 판단 보류 상태
- 누락 자료와 provider 오류
- 짧은 근거와 원문 출처
- 어려운 금융 용어 설명

로그인·소셜·복잡한 대시보드보다 **질문→답변→근거 확인 흐름**을 먼저 완성한다.

## 체크포인트 3 — 핵심 가치 집중

프로토타입의 핵심 가치는 다음이다.

> 사용자가 선택한 종목에 대해 최신 리포트·공시·뉴스를 검색하고, 근거가 연결된 이해하기 쉬운 AI 답변을 제공한다.

MVP 완성 전에는 다음 작업이 핵심 흐름을 지연시키면 안 된다.

- 로그인·회원관리
- 관심 종목 영구 저장
- 소셜·친구 기능
- 시장 전체 스크리닝
- 고난도 시계열 분석
- 자동 PDF 표·그래프 해석
- 여러 알림 채널
- 정교한 투자 성향 개인화

단, MVP가 완료된 후 남은 기간에 실제 구현을 시도할 **추가 단계**에는 로그인, 사용자별 세션, 이전 대화 내역, 관심 종목 저장을 포함한다.

---

# 2. 단계와 최종 우선순위 정의

## 2.1 단계 정의

| 단계 | 의미 | 완료 원칙 |
|---|---|---|
| **MVP** | 최종 결과물에서 반드시 완성해야 하는 기능 | 시연·테스트·배포 경로가 모두 존재해야 한다. 미완성 기능을 포함하지 않는다. Red 대응으로 기능을 제거하려면 Human Owner가 범위를 공식 변경하고 완료 기준을 다시 잠가야 한다. |
| **추가 단계 — 우선** | MVP 완료 후 남은 기간에 가장 먼저 실제 구현을 시도할 기능 | 코어를 훼손하지 않는 독립 모듈로 추가하며, 구현 순서를 계획서에 포함한다. |
| **추가 단계 — 여유** | 우선 추가 기능 이후 시간이 남으면 구현할 기능 | 구현 실패 시 제거해도 MVP가 유지되어야 한다. |
| **향후 계획** | 이번 개발 기간에는 구현하지 않고 최종 발표의 개선 방향으로 제시할 기능 | 데이터·기술·안전성 계획만 남기며 코어 schema에 미리 반영하지 않는다. |
| **제외** | 직접 예측·매매 지시 등 프로젝트 목표와 안전 기준에 맞지 않는 기능 | 변형 가능한 경우 안전한 대체 아이디어만 별도 단계에 둔다. |

## 2.2 우선순위 코드

| 코드 | 의미 |
|---|---|
| `P0` | MVP 필수 |
| `P1` | 추가 단계에서 우선 구현 |
| `P2` | 추가 단계에서 여유가 있으면 구현 |
| `P3` | 향후 계획 |
| `X` | 현재 프로젝트에서 제외 |

기존 `#`, `##`, `*` 표시는 초기 사용자 선호를 보여주는 참고 자료로만 사용한다. 최종 우선순위는 필수 체크포인트, 데이터 준비도, 구현 난이도, 평가 가능성, 일정 적합성을 함께 반영한 `P0~P3/X`로 결정한다.

## 2.3 P0 공식 범위 변경 규칙

P0는 문서에 적힌 기능을 조용히 숨긴 상태로 완료 처리할 수 없다.

Red 상태에서 P0 기능을 제거하거나 P1으로 이동해야 할 경우:

```text
Human Owner 승인
→ EXTENSION_COMPATIBILITY와 PROJECT_PLAN의 우선순위·완료 기준 갱신
→ 관련 Task·테스트·UI 범위 갱신
→ scope-reduced MVP candidate로 표시
→ 갱신된 P0 기준으로 완료 여부 재판정
```

공식 문서 변경 없이 P0 기능을 숨긴 결과물은 `P0 완료`가 아니다.

---

# 3. 공통 구조 결정

## 3.1 로그인 없는 MVP 멀티턴

멀티턴은 로그인과 별개다. MVP에서는 익명 `session_id` 단위로 현재 대화의 문맥을 유지한다.

```text
Anonymous Session
├─ current_security_id
├─ current_date_range
├─ previous_intent
├─ previous_source_types
└─ 제한된 최근 대화
```

MVP에서 지원할 동작:

```text
사용자: 삼성전자 최근 이슈 알려줘
사용자: 그중 공시 위험만 정리해줘
```

두 번째 질문에서 현재 종목이 삼성전자라는 사실을 유지한다.

MVP에서는 다음을 요구하지 않는다.

- 사용자 계정
- 여러 기기 동기화
- 영구 대화 목록
- 사용자별 관심 종목
- 장기 투자 성향 프로필

## 3.2 로그인과 사용자별 데이터

로그인과 영구 사용자 데이터는 `P1` 추가 단계로 둔다.

```text
User
├─ Conversation
│  └─ Message
└─ Watchlist
   └─ Supported Security
```

추가 단계의 최소 범위:

- 회원가입·로그인
- 사용자별 대화 세션
- 이전 대화 목록
- 기존 대화 다시 열기
- 관심 종목 추가·삭제
- 관심 종목에서 새 질문 시작

지원 종목은 삼성전자·SK하이닉스·현대자동차 3개이므로 관심 종목은 지원 종목 중 선택하는 방식으로 제한한다. 복잡한 시장 전체 종목 검색과 포트폴리오 관리는 포함하지 않는다.

## 3.3 금융 용어 설명과 glossary corpus

금융 용어 설명을 LLM의 일반 지식에만 맡기지 않는다.

권장 흐름:

```text
검수된 glossary corpus
→ 정확한 정의·주의점·예시 검색
→ LLM이 초보자용 문장으로 재구성
→ corpus locator와 함께 응답
```

작은 glossary corpus를 사용하는 이유:

1. **정의 일관성**  
   같은 용어가 질문마다 다른 기준으로 설명되는 것을 줄인다.

2. **환각과 과도한 일반화 방지**  
   예: “PER이 낮으면 무조건 저평가”와 같은 부정확한 해석을 막는다.

3. **근거 원칙 통일**  
   뉴스·공시·리포트뿐 아니라 금융 용어도 출처와 버전을 관리한다.

4. **평가 가능성**  
   정의 핵심 요소, 혼동 용어, 주의 문구 누락 여부를 golden set으로 평가할 수 있다.

5. **낮은 구현 부담**  
   MVP에서는 10~30개 핵심 용어를 JSON 또는 Markdown으로 관리할 수 있다.

초기 용어 후보:

- PER
- PBR
- ROE
- EPS
- 시가총액
- 매출
- 영업이익
- 순이익
- 영업이익률
- 유상증자
- 전환사채
- 공시
- 컨센서스
- 연결·별도 재무제표

LLM은 설명을 자연스럽게 만드는 역할을 하지만, 정의의 기준 사실은 glossary corpus에서 가져온다.

## 3.4 “최신”의 범위

MVP에서 최신은 반드시 실시간 스트리밍을 의미하지 않는다.

MVP 요구:

- 자료의 `published_at`, `fetched_at`, 분석 기준일 표시
- 질문 유형별 최신성 기준 적용
- 오래된 자료 경고
- 지원 종목에 대해 최근 뉴스·공시를 조회하거나 적재
- 리서치 리포트 corpus의 기준일과 갱신 시점 표시

장중 실시간 시세·뉴스·공시의 완전한 통합은 `P2`로 둔다.

## 3.5 데이터 범위

MVP:

- 삼성전자·SK하이닉스·현대자동차 3개 보통주
- 뉴스
- 공시
- 수동 정규화 리서치 리포트
- 검수된 glossary
- A15-M을 P0로 확정하는 경우 종목별 `MarketSnapshot` 필수. M1 종료 전 adapter와 fixture를 확보하지 못하면 A15-M을 공식적으로 P1로 이동

추가·향후 단계에서도 데이터 범위를 무조건 시장 전체로 확장하지 않는다. 기능 검증에 필요한 최소 universe를 먼저 사용한다.

---

# 4. MVP 확정 범위 — `P0`

## 4.1 P0 기능 표

| ID | 기능 | 체크포인트 | MVP 최소 구현 | 데이터 준비도 | 코어 변경 | 평가 가능성 | 제거 비용 | 최종 판단 |
|---|---|---|---|---|---|---|---|---|
| A01 | 초보자 쉬운 설명 모드 | 2 | 초보자 문체, 용어 괄호 설명, “왜 중요한가” 한 문장 | 높음 | 낮음 | 높음 | 낮음 | 채택 |
| A02 | 사실·자료 해석·AI 추론 분리 | 1·2 | 응답을 `확인된 사실 / 자료의 해석 / AI 정리·불확실성`으로 구분 | 높음 | 중간 | 높음 | 중간 | 채택 |
| A03 | 핵심·긍정·위험·불확실성 카드 | 2 | 고정된 구조화 응답과 카드 UI | 높음 | 낮음 | 높음 | 낮음 | 채택 |
| A04 | 근거 강도 평가와 답변 보류 | 1·2 | `complete / partial / provider_failed / no_evidence / blocked` 판정 | 높음 | 중간 | 높음 | 높음 | 채택 |
| A05-M | 상충 자료 비교 최소 버전 | 1·2 | 검색된 근거를 공통 사실·긍정·위험·불확실성으로 나눔 | 중간 | 중간 | 중간 | 낮음 | 제한 채택 |
| A06-M | 여러 자료 연결 설명 최소 버전 | 1·2 | 뉴스·공시·리포트 연결, 사실과 추론 분리, 인과 확정 금지 | 중간 | 중간 | 중간 | 낮음 | 제한 채택 |
| A08-M | 익명 세션 멀티턴 | 2 | 세션 단위 현재 종목·기간·직전 intent 유지 | 높음 | 중간 | 높음 | 중간 | 채택 |
| A10 | 금융 용어 설명 | 2 | 검수된 작은 glossary corpus + LLM 쉬운 표현 | 높음 | 낮음 | 높음 | 낮음 | 채택 |
| A11 | 질문 의도·데이터 유형 라우팅 | 1·3 | 규칙 기반 intent와 required source 결정 | 높음 | 높음 | 높음 | 높음 | 채택 |
| A12 | 최신성 가중치·오래된 자료 경고 | 1·2 | 기준일 표시, stale 경고, 질문별 기간 정책 | 높음 | 중간 | 높음 | 중간 | 채택 |
| A13 | 근거 요약·원문 출처 연결 | 1·2 | Evidence snippet과 URL 또는 locator 카드 | 높음 | 높음 | 높음 | 높음 | 채택 |
| A15-M | 국내 근거 기반 상승·하락 배경 분석 | 1·2 | 실제 가격 방향 확인, 국내 뉴스·공시의 시간 정합성, 원인 후보 표시 | 중간 — MarketSnapshot 필수 | 중간 | 높음 | 낮음 | 조건부 P0 |
| A17-M | 사업 전망 요약 | 1·2 | 최근 공시·리포트의 성장 동력·위험·확인 이벤트 정리 | 높음 | 낮음 | 중간 | 낮음 | 제한 채택 |
| A18 | 외부 API 오류·한도·fallback | 1·3 | timeout, retry cap, 429, cache, partial response, typed status | 높음 | 높음 | 높음 | 높음 | 채택 |
| A19 | 토큰·문맥 예산 관리 | 1·3 | top-k 제한, 중복 제거, source별 context budget, LLM 호출 상한 | 높음 | 중간 | 높음 | 중간 | 채택 |
| A20-M | 최소 평가셋·회귀 테스트·관측 | 1·2·3 | 핵심 taxonomy golden set, provider fake, Langfuse 또는 동등 관측 | 높음 | 중간 | 높음 | 높음 | 채택 |
| A23-M | 단일 안전 구조화 답변 | 2·3 | 하나의 응답에서 사실·해석·긍정·위험·불확실성·근거를 제공 | 높음 | 낮음 | 높음 | 낮음 | 채택 |
| SAFE01 | 직접 투자 조언 차단 | 1·2·3 | 매수·매도·목표가·확정 예측 차단과 안전한 대체 응답 | 높음 | 높음 | 높음 | 높음 | 채택 |
| UI01 | 핵심 흐름 중심 UI | 2·3 | 질문 입력, 종목 표시, 답변 카드, 근거 상세, 경고 표시 | 높음 | 중간 | 높음 | 높음 | 채택 |

## 4.1.1 상태 계층과 `low_relevance`

상태는 다음 네 계층으로 유지한다.

```text
Resolution
- resolved
- ambiguous
- not_found
- unsupported

Provider
- ok
- no_data
- invalid_query
- unauthorized
- rate_limited
- timeout
- provider_unavailable
- parse_error

Retrieval
- ok
- empty
- low_relevance

Evidence Decision
- complete
- partial
- provider_failed
- no_evidence
- blocked
```

`low_relevance`는 Retrieval 결과다. `EvidencePolicy`는 질문의 필수 근거와 provider 결과를 함께 고려하여 이를 최종적으로 `partial` 또는 `no_evidence`에 매핑한다. provider 장애와 낮은 검색 관련도를 같은 상태로 합치지 않는다.

## 4.2 수치 검증의 MVP 범위

수치 검증은 다음 두 ID로 구분한다.

- `A07-M`: P0 기본 숫자·날짜·단위 literal 검증
- `A07-H`: P1 metric·기간·단위·연결/별도·실제/추정 고도화

A07 전체를 MVP에 넣지 않고 `A07-M`만 P0로 포함한다.

### P0 기본 검증 — `A07-M`

- 답변 숫자가 선택된 Evidence에 존재하는지
- 숫자의 `subject_security_ids`가 질문 종목과 일치하는지
- 산업 공통 수치를 기업 고유 수치로 바꾸지 않았는지
- 종목과 기간이 맞는지
- 원문 단위를 임의로 바꾸지 않았는지
- 퍼센트와 퍼센트포인트를 혼동하지 않았는지
- 존재하지 않는 숫자·URL을 생성하지 않았는지

### P1 고도화 — `A07-H`

- canonical metric name
- 연결·별도
- 분기·연간
- 실제·추정
- 통화·단위 변환
- 공식값과 리포트 추정치의 충돌 처리

## 4.3 상충 자료 비교의 MVP 범위

MVP에서는 다음까지만 요구한다.

```text
공통 사실
긍정 근거
위험 근거
불확실성
```

MVP에서 필수로 요구하지 않는 기능:

- 대규모 뉴스 자동 중복 제거
- 독립 출처 수 정밀 계산
- 이벤트 cluster 자동 생성
- 금융 특화 stance model 학습
- 시간에 따른 관점 변화 그래프

해당 기능은 P1로 확장한다.

## 4.4 오늘의 상승·하락 원인 분석 범위

A15-M은 문서 작성 시점의 **조건부 P0**다.

승격 게이트:

```text
M0에서 시세 provider 후보·timezone·market session 확인
→ M1 종료 전 MarketSnapshot adapter와 정상·실패 fixture 확보
→ 통과하면 P0 확정
→ 실패하면 Human Owner 승인과 문서 갱신 후 P1 이동
```

P0로 확정된 경우의 제한 버전:

- 사용자가 선택한 지원 종목만 분석
- `MarketSnapshot`으로 실제 상승·하락 확인
- 국내 뉴스·공시 자료 우선
- 가격 변화와 문서 공개 시각의 선후관계 확인
- 선행 원인, 장중 자료, 후속 배경 구분
- 인과가 아니라 “관련 배경 후보”로 표현
- 해외 자료가 없으면 분석 한계 표시

P3 고도화:

- 해외 뉴스
- 미국 시장·금리·환율
- 해외 동종기업
- 글로벌 산업 지표
- 다단계 장기 인과 경로

## 4.5 P0 완료 기준

### P0 최소 관측 기준

Langfuse는 필수 기술이 아니다. P0에서는 Langfuse 또는 구조화 로그로 다음 필드를 확인할 수 있어야 한다.

- `request_id`
- `intent`
- `security_id`
- provider별 status
- evidence count
- final evidence decision
- total latency
- LLM call count
- 오류 또는 fallback 여부


### 체크포인트 1

- [ ] 삼성전자·SK하이닉스·현대자동차를 정확히 식별한다.
- [ ] 뉴스·공시·리서치 리포트 3종을 조회 또는 검색한다.
- [ ] 질문별 required source가 동작한다.
- [ ] Evidence에 snippet과 locator가 존재한다.
- [ ] provider 오류와 자료 없음을 구분한다.
- [ ] 근거가 부족하면 보류한다.
- [ ] A15-M이 P0로 승격된 경우 “왜 올랐어?”에서 MarketSnapshot의 실제 방향과 문서 공개 시각·시장 세션의 시간 정합성을 검사한다.
- [ ] 핵심 회귀 테스트가 통과한다.

### 체크포인트 2

- [ ] 초보자 설명을 제공한다.
- [ ] 사실·해석·추론을 구분한다.
- [ ] 핵심·긍정·위험·불확실성 카드가 보인다.
- [ ] 기준일과 근거 강도가 보인다.
- [ ] 출처를 상세 보기로 확인할 수 있다.
- [ ] 오류·누락 자료가 사용자 문장으로 표시된다.
- [ ] 금융 용어를 glossary 근거로 설명한다.

### 체크포인트 3

- [ ] 로그인 없이 핵심 질문을 바로 사용할 수 있다.
- [ ] 인증·소셜 기능 없이도 전체 시연이 가능하다.
- [ ] 지원 종목과 source 범위를 통제한다.
- [ ] 선택하지 않은 확장 기능이 코어 schema에 들어가지 않는다.
- [ ] 한 가지 실행·배포 방법이 문서화되어 있다.

---

# 5. 추가 단계 — 우선 구현 `P1`

P1은 하나의 전역 1~8 순서를 사용하지 않는다.  
M4 종료 시 핵심 RAG의 품질 상태와 남은 일정 버퍼를 확인한 뒤 `P1-RAG 품질` 또는 `P1-User 기능` 중 먼저 진행할 묶음을 결정한다.

## 5.1 P1-RAG 품질 내부 순서

| 내부 순서 | ID | 기능 | 선행 조건 | 최소 구현 | 평가 방법 | 실패 시 처리 |
|---:|---|---|---|---|---|---|
| 1 | A16 | 분기별 매출·영업이익·순이익 추세 | 정형 재무 데이터와 기간 정규화 | 최근 4개 분기 표·간단 그래프·출처 | 숫자·기간·단위 fixture | 해당 카드 제거 |
| 2 | A07-H | 수치 검증 고도화 | A16 | metric·기간·단위·연결/별도·실제/추정 검증 | 공식값 대조 테스트 | P0 기본 검증 유지 |
| 3 | A05-H | 상충 자료 자동 비교 | P0 Evidence 구조 | topic/time/entity grouping, 긍정·위험 비교 | 중복·상충 fixture | P0 수동 구조 유지 |
| 4 | NEWS01 | 뉴스 중복 제거·event grouping | A05-H | content hash·제목 유사도·원출처 grouping | 재배포 기사 fixture | grouping 비활성화 |
| 5 | A23-H | 별도 사실 요약·근거 기반 관점 모드 | A23-M, P0 안정화 | 동일 Evidence를 공유하는 mode toggle | 두 모드 사실 일치·금지 표현 | 단일 안전 구조화 답변 유지 |

## 5.2 P1-User 기능 내부 순서

| 내부 순서 | ID | 기능 | 선행 조건 | 최소 구현 | 평가 방법 | 실패 시 처리 |
|---:|---|---|---|---|---|---|
| 1 | AUTH01 | 회원가입·로그인 | P0 API·UI 완료, 사용자 DB | 단순 가입·로그인·로그아웃, 비밀번호 안전 저장 또는 외부 인증 | 인증 성공·실패·권한 테스트 | 인증 없는 MVP 경로 유지 |
| 2 | AUTH02 | 사용자별 영구 세션 | AUTH01 | 사용자별 conversation 생성·조회 | 다른 사용자 데이터 격리 테스트 | 익명 세션만 유지 |
| 3 | AUTH03 | 이전 대화 목록·재열기 | AUTH02 | 대화 제목·시간·종목 표시, 기존 대화 열기 | 대화 복원과 문맥 일치 | 기능 숨김 |
| 4 | A14 | 관심 종목 저장 | AUTH01, 확정 지원 종목 3개 | 지원 종목 추가·삭제·목록, 관심 종목에서 질문 시작 | 사용자별 watchlist 격리 | 기능 숨김 |

어느 묶음을 먼저 진행할지는 M4 종료 시 다음 기준으로 결정한다.

```text
핵심 RAG의 numeric_accuracy·citation_support·conflicting_sources 결함이 남음
→ P1-RAG 품질 우선

핵심 RAG가 안정적이고 제품 사용성 보완이 더 중요함
→ 공개 익명 경로를 유지한 채 P1-User 기능 우선
```

## 5.3 로그인 구현 원칙

로그인은 핵심 RAG 흐름과 분리한다.

```text
Core RAG API
↑
Optional Auth Layer
↑
User / Conversation / Watchlist
```

원칙:

- 인증 실패가 공개 MVP 데모 전체를 막지 않게 한다.
- role·권한·소셜 관계를 복잡하게 만들지 않는다.
- 금융 계좌·보유 수량·실제 손익은 저장하지 않는다.
- 사용자별 대화와 관심 종목만 최소 저장한다.
- 비밀번호를 평문으로 저장하지 않는다.
- 세션 만료와 로그아웃을 제공한다.
- 사용자 A의 대화가 사용자 B에게 노출되지 않는지 테스트한다.

## 5.4 추가 단계 우선 기능의 승격 조건

P1 작업을 시작하려면 다음이 충족되어야 한다.

- P0 체크포인트 테스트 통과
- 뉴스·공시·리포트 기본 답변 동작
- Evidence와 locator 안정화
- provider 오류 처리 완료
- 핵심 UI가 시연 가능한 상태
- 배포 또는 최소 실행 환경 확정

P0가 불안정하면 P1 구현을 중단하고 코어 안정화로 돌아간다.

---

# 6. 추가 단계 — 여유 구현 `P2`

| ID | 기능 | 최소 구현 형태 | 필요한 데이터·의존성 | 코어 결합도 | 평가 가능성 | 최종 판단 |
|---|---|---|---|---|---|---|
| B01 | 실시간에 가까운 시세·뉴스·공시 통합 | 지원 종목 선택 시 최신 snapshot과 최근 자료 새로 조회 | 시세 API, 뉴스 API, DART, cache | 중간 | 높음 | 조건부 채택 |
| A09-I | 관심 분야에 따른 정보 강조 | 사용자가 선택한 관심 관점에 따라 카드 순서만 변경 | 사용자 설정, 기존 Evidence | 낮음 | 중간 | 조건부 채택 |
| A21 | 관심 분야 기반 종목 탐색 | 확정 지원 종목 3개 안에서 산업·키워드 관련 종목 탐색 | 소규모 industry mapping | 중간 | 중간 | 조건부 채택 |
| A22 | 산업·연관 종목 수혜 구조 설명 | 미리 정의한 일부 산업 관계를 근거와 함께 설명 | 산업 관계 자료 | 중간 | 중간 | 조건부 채택 |
| D01 | 상승 지속·하락 위험 조건·예정 이벤트 | 현재 자료에서 확인해야 할 조건을 시나리오 카드로 표시 | 공시·뉴스·리포트 | 낮음 | 중간 | 조건부 채택 |
| D05 | 단기 투자 체크리스트 | 변동성·거래량·이벤트 위험 확인 항목만 제시 | MarketSnapshot 또는 제한적 시세 | 낮음 | 중간 | 조건부 채택 |
| UX02 | 관심 종목 진입 화면 고도화 | watchlist에서 최신 이슈 표시 후 질문 시작 | AUTH·A14 | 낮음 | 높음 | 조건부 채택 |

P2는 구현 실패 시 사용자에게 노출하지 않고 제거할 수 있어야 한다.

---

# 7. 향후 계획 `P3`

다음 기능은 최종 발표에서 개선 방향으로 제시한다. 이번 개발 기간의 구현 대상이 아니다.

| ID | 기능 | 향후 계획으로 두는 이유 | 승격에 필요한 조건 |
|---|---|---|---|
| A09-P / B07 | 투자 성향 기반 개인화 | 개인정보·안전 정책·평가 복잡도 증가 | 사용자 동의, profile schema, 추천 금지 검증 |
| A15-G | 해외 자료 포함 상승·하락 원인 분석 | 해외 뉴스·시차·entity·시장 지표 필요 | 해외 데이터 provider, 번역·entity 평가 |
| B06 | 미국 금리→산업→국내 종목 장기 인과 | 다단계 근거와 거시 데이터 필요 | 사전 정의 시나리오, 단계별 citation |
| B08 | 리포트 PDF 표·그래프 자동 파싱 | 증권사별 형식, OCR·표 검증 부담 | parser benchmark, 수치 fixture, 이용 조건 |
| B10 / D02 | 과거 유사 차트 구간 탐색 | 별도 퀀트·시계열 영역 | adjusted OHLCV, leakage 방지, walk-forward |
| B02 / D03 | 호재 후 가격 반응이 작은 관찰 후보 | 시장 전체 이벤트 탐지와 추천 오해 가능성 | universe, event label, 상대수익률 평가 |
| B03 / D07 | 요일별 과거 통계 탐색 | 표본·기간 선택·유의성 문제 | 통계 검정, 시장 국면 분리 |
| B04 / D08 | 테마 내 상대 미반응 종목 비교 | 테마 taxonomy와 전체 종목 데이터 필요 | universe, theme mapping, 가격·뉴스 비교 |
| B09 | 관심 이벤트 알림 | scheduler·중복 제거·알림 채널 필요 | 안정적 ingest, notification service |
| B05 | 친구·관심 종목·수익률 공유 | 핵심 RAG와 거리가 크고 개인정보 부담 | 권한·신고·차단·민감정보 정책 |
| AUTH04 | 여러 기기 동기화 고도화 | 기본 로그인 이후 운영 기능 | token·session 정책, 보안 검토 |
| SOCIAL01 | 소셜 투자 기능 | 범위와 운영 위험이 큼 | 별도 제품 기획 |

향후 계획 기능은 현재 코어 model, graph node, DB table에 미리 반영하지 않는다.

---

# 8. 제외 `X`

| ID | 제외 기능 | 제외 이유 | 안전한 대체 |
|---|---|---|---|
| C01 | 오늘·내일 오를 종목 직접 예측 | 검증 어려움, 투자 추천 오해, RAG 가치 약화 | 최근 변동 배경과 예정 이벤트 |
| C02 | 차트 패턴으로 미래 방향 확정 | 과적합·look-ahead·시장 국면 위험 | P3 과거 유사 사례와 분포 |
| C03 | 단타 매매 타이밍·손절·익절 지시 | 직접 투자 행동 지시 | P2 단기 위험 체크리스트 |
| C04 | “아직 안 쐈으니 곧 오른다” 예측 | 상대 미상승이 미래 상승 근거가 아님 | P3 테마 내 상대 비교 |
| C05 | 확정적 매수·매도·보유 추천 | 금융·윤리 위험, 불완전한 자료 | P0 사실 요약·근거 기반 관점 |
| C06 | 요일만으로 다음 거래일 방향 추천 | 통계 탐색을 예측 신호로 오용 | P3 요일별 과거 분포 |
| C07 | 수익 보장·근거 없는 순위 | 재현 가능한 근거 없음 | 근거 강도·불확실성 표시 |

---

# 9. 아이디어별 최종 우선순위 요약

## 9.1 A 아이디어

| ID | 아이디어 | 최종 우선순위 | 적용 형태 |
|---|---|---|---|
| A01 | 초보자 쉬운 설명 | P0 | 그대로 채택 |
| A02 | 사실·해석·추론 분리 | P0 | 구조화 응답 |
| A03 | 긍정·위험·불확실성 카드 | P0 | 카드 UI |
| A04 | 근거 강도·보류 | P0 | Evidence Decision |
| A05 | 상충 뉴스·리포트 비교 | P0/P1 | 기본 비교 P0, 자동 grouping P1 |
| A06 | 여러 자료 연결 원인 설명 | P0/P3 | 국내 제한형 P0, 글로벌 장기 인과 P3 |
| A07 | 수치·단위·기간 검증 | P0/P1 | 기본 검증 P0, metric 정규화 P1 |
| A08 | 멀티턴 종목 문맥 | P0/P1 | 익명 세션 P0, 영구 세션 P1 |
| A09 | 관심 분야·성향 정보 강조 | P2/P3 | 관심 분야 강조 P2, 투자 성향 개인화 P3 |
| A10 | 금융 용어 설명 | P0 | glossary 기반 |
| A11 | 질문·데이터 라우팅 | P0 | 규칙 기반 우선 |
| A12 | 최신성·stale 경고 | P0 | 기준일·기간 정책 |
| A13 | 근거·원문 출처 | P0 | Evidence card |
| A14 | 관심 종목 저장 | P1 | 로그인 사용자별 watchlist |
| A15 | 상승·하락 원인 분석 | P0/P3 | 국내 제한형 P0, 해외 확장 P3 |
| A16 | 분기별 실적 추세 | P1 | 최근 4개 분기 |
| A17 | 사업 전망 요약 | P0 | 문서 기반 제한형 |
| A18 | API 오류·fallback | P0 | typed status와 partial response |
| A19 | 토큰·문맥 예산 | P0 | 호출·context 상한 |
| A20 | 평가·회귀·관측 | P0 | 최소 golden set부터 |
| A21 | 관심 분야 기반 종목 탐색 | P2 | 지원 종목 범위 제한 |
| A22 | 산업·연관 종목 수혜 구조 | P2 | 제한된 산업 관계 |
| A23-M | 단일 안전 구조화 답변 | P0 | 사실·해석·긍정·위험·불확실성 통합 |
| A23-H | 별도 사실 요약·근거 기반 관점 모드 | P1/M5 | P0 안정화 후 mode toggle |

## 9.2 B 아이디어

| ID | 아이디어 | 최종 우선순위 |
|---|---|---|
| B01 | 실시간 시세·뉴스·공시 통합 | P2 |
| B02 | 호재 후 가격 반응이 작은 종목 탐색 | P3 |
| B03 | 요일별 시장 패턴 | P3 |
| B04 | 테마 내 미반응 종목 비교 | P3 |
| B05 | 친구·수익률 공유 | P3 |
| B06 | 미국 금리→산업→국내 종목 | P3 |
| B07 | 투자 성향 기반 개인화 | P3 |
| B08 | 자동 PDF 표·그래프 파싱 | P3 |
| B09 | 관심 이벤트 알림 | P3 |
| B10 | 과거 유사 차트 구간 탐색 | P3 |

## 9.3 신규 사용자 기능

| ID | 기능 | 최종 우선순위 |
|---|---|---|
| AUTH01 | 회원가입·로그인 | P1 |
| AUTH02 | 사용자별 영구 세션 | P1 |
| AUTH03 | 이전 대화 목록·재열기 | P1 |
| A14 | 관심 종목 저장 | P1 |
| AUTH04 | 여러 기기 동기화 고도화 | P3 |

---

# 10. 평가 Taxonomy 연결

| 기능군 | 주요 평가 범주 |
|---|---|
| 종목 식별 | `entity_resolution`, `ambiguous_security` |
| 질문 라우팅 | `intent_routing`, `source_selection` |
| 상승·하락 배경 | `price_move_reason`, `stale_data`, `citation_support` |
| 상충 자료 | `conflicting_sources`, `evidence_sufficiency` |
| 수치·실적 | `financial_metric`, `numeric_accuracy` |
| 근거·출처 | `citation_support`, `evidence_sufficiency`, `abstention` |
| 투자 안전 | `prohibited_advice`, `pattern_analysis_limit` |
| 멀티턴 | `multi_turn` |
| provider 안정성 | `provider_timeout`, `provider_rate_limit` |
| 공시 최신성 | `correction_disclosure` |
| 여러 자료 연결 | `multi_hop_reasoning` |
| 사용자별 영구 세션 | 신규 평가: `conversation_ownership`, `conversation_restore` |
| 로그인 | 신규 평가: `auth_success_failure`, `session_expiry`, `user_isolation` |
| 관심 종목 | 신규 평가: `watchlist_ownership`, `supported_security_only` |

신규 사용자 기능 평가는 P1 구현을 시작할 때 구체화한다. MVP taxonomy에 미리 대량 추가하지 않는다.

---

# 11. 데이터·의존성·제거 비용 기준

## 11.1 데이터 준비도

| 수준 | 의미 |
|---|---|
| 높음 | 현재 지원 종목과 수동 corpus만으로 구현 가능 |
| 중간 | 외부 API 또는 추가 정규화가 필요하지만 범위를 제한할 수 있음 |
| 낮음 | 시장 전체·해외·대규모 시계열·라벨 데이터가 필요 |

## 11.2 코어 결합도

| 수준 | 의미 |
|---|---|
| 낮음 | composer, formatter, UI 카드처럼 독립적으로 추가 가능 |
| 중간 | provider·retriever·session 계약 일부 확장 필요 |
| 높음 | 전체 데이터 흐름·DB·평가 체계를 바꾸거나 별도 서비스 필요 |

## 11.3 제거 비용

| 수준 | 의미 |
|---|---|
| 낮음 | feature flag 또는 UI 숨김으로 제거 가능 |
| 중간 | 일부 API·DB migration이 필요하지만 코어 RAG는 유지 |
| 높음 | 제거하면 기본 답변 흐름이나 데이터 모델이 깨짐 |

P1·P2 기능은 가능하면 제거 비용이 낮거나 중간이어야 한다.

---

# 12. 권장 개발 순서

## 12.0 P0 코어 기능 추적 표

모든 P0 코어 기능과 아이디어 기능은 `PROJECT_PLAN.md`에서 아래 관계로 구체화해야 한다.

```text
기능 ID → Phase/Step → 완료 gate → 평가 taxonomy → fallback
```

연결되지 않은 P0 기능은 계획 확정 상태로 보지 않는다.

| 기능 ID | 코어 기능 | 구현 Phase·Task 후보 | 완료 gate | 주요 taxonomy | fallback |
|---|---|---|---|---|---|
| CORE01 | 종목·법인 resolver | M1-01~02 | 삼성전자·SK하이닉스·현대자동차 exact ticker·alias·ambiguous·unsupported fixture 통과 | `entity_resolution`, `ambiguous_security` | 지원 종목 명시 mapping |
| CORE02 | 뉴스·공시·리서치 리포트 3종 | M1-04~07 | 지원 종목별 3종 source 조회 또는 검색과 locator 확인 | `source_selection`, `citation_support` | recorded fixture·수동 corpus |
| CORE03 | ProviderResult와 상태 계약 | M1-03 | no_data·timeout·rate_limited·parse_error 분리 | `provider_timeout`, `provider_rate_limit` | typed partial response |
| CORE04 | security·source·period·Evidence 주체 hard filter | M2-02 | wrong-company·공동 기사 타사 Evidence·wrong-period 차단 | `entity_resolution`, `citation_support` | 명시 주체 Evidence만 사용 |
| CORE05 | retrieval baseline | M2-03 | empty·low_relevance 구분과 baseline benchmark 완료 | `evidence_sufficiency` | lexical 또는 단일 dense |
| CORE06 | Evidence 주체·범위와 원문 locator | M2-04, M2-07 | subject_security_ids·scope·snippet·locator 존재 | `citation_support` | 주체 또는 locator 불명 Evidence 제외 |
| CORE07 | EvidencePolicy와 abstention | M2-06 | complete·partial·provider_failed·no_evidence·blocked 판정 | `evidence_sufficiency`, `abstention` | 보수적 보류 |
| CORE08 | 안정적인 단일 응답 API | M3-01, M4-05 | 대표 질문의 단일 응답 방식 end-to-end 통과 | API smoke test | streaming 미사용 |
| CORE09 | 외부 API fallback | M1-03~05, M4-01 | cache·적재 자료·partial response 경로 통과 | `provider_timeout`, `provider_rate_limit` | 고정 보류 응답 |
| CORE10 | 실행·배포 경로 | M4-04~07 | clean environment 실행과 deployment smoke 통과 | deployment smoke | 로컬 실행 백업 |

## 12.1 P0 아이디어 기능 추적 표

| 기능 ID | 구현 Phase·Task 후보 | 완료 gate | 주요 taxonomy | fallback |
|---|---|---|---|---|
| A01 | M3-02 | 초보자 설명 핵심 요소 표시 | `citation_support`, UI task test | 고정 설명 template |
| A02 | M3-03 | 사실·해석·추론 라벨 분리 | `multi_hop_reasoning` | 추론 섹션 제거 |
| A03 | M3-04 | 핵심·긍정·위험·불확실성 UI | UI snapshot | 핵심·위험·근거 3영역 |
| A04 | M2-06 | Retrieval과 Evidence Decision 구분 | `evidence_sufficiency`, `abstention` | 보수적 `no_evidence` |
| A05-M | M3-10 | 양쪽 Evidence 병렬 표시 | `conflicting_sources` | 자동 비교 제거 |
| A06-M | M3-11 | 2~3개 근거 연결과 추론 표시 | `multi_hop_reasoning` | 단일 source 요약 |
| A07-M | M3-09 | 숫자·날짜·단위와 subject_security 귀속 일치 | `numeric_accuracy` | 타사·불명 수치 문장 제거 |
| A08-M | M3-06 | 종목·기간·intent 유지와 reset | `multi_turn` | 현재 종목만 유지 |
| A10 | M1-07, M3-05 | glossary locator와 핵심 정의 | glossary fixture | 미지원 용어 안내 |
| A11 | M2-01 | intent와 required source 결정 | `intent_routing`, `source_selection` | 규칙 router |
| A12 | M2-05 | basis date와 stale 경고 | `stale_data` | 최신성 질문 보류 |
| A13 | M2-04, M2-07 | snippet과 URL 또는 locator | `citation_support` | locator 없는 문서 제외 |
| A15-M | M1-09, M2-09, M3-12, M4-02 | 조건부 승격 gate와 시간 정합성 | `price_move_reason` | P1 이동 |
| A17-M | M3-14 | 문서 기반 전망·위험·이벤트 | `citation_support`, `prohibited_advice` | 최근 이슈 요약에 통합 |
| A18 | M1-03~05, M4-01 | timeout·429·no-data 분리 | `provider_timeout`, `provider_rate_limit` | cache·적재 자료 |
| A19 | M2-08 | top-k·context·LLM 호출 상한 | latency·call count | 더 작은 context |
| A20-M | M0 golden set, M4-02~03 | 핵심 fixture·구조 로그 | 전체 핵심 taxonomy | 구조 로그만 유지 |
| A23-M | M3-01~04 | 단일 구조화 응답의 필수 section·금지 표현 | `prohibited_advice` | 핵심·위험·근거 3영역 |
| A23-H | M5-06 | 두 모드 사실 일치·금지 표현 | `prohibited_advice` | A23-M 유지 |
| SAFE01 | M3-08 | 추천·목표가·확정 예측 차단 | `prohibited_advice` | 고정 안전 응답 |
| UI01 | M3-01~07 | 질문→답변→근거 1화면 흐름 | UI smoke test | 단일 화면 축소 |

## Phase M0 — 범위 확정

- 삼성전자·SK하이닉스·현대자동차 3개 보통주
- 뉴스 provider
- 공시 수집 방식
- 수동 리서치 리포트 목록
- glossary 용어 목록
- MVP 질문 유형
- UI 와이어프레임
- golden set 초안

## Phase M1 — 코어 데이터·API

- `SecurityIdentifier`
- `FinancialDocument`
- `Evidence`
- 상태 계층과 provider error taxonomy
- 뉴스·공시 provider adapter
- 수동 리서치 리포트·glossary ingest
- 기본 health·config·secret handling
- A15-M 조건부 승격을 위한 `MarketSnapshot` adapter·timezone·market session fixture

## Phase M2 — 검색·근거 정책

- intent routing
- hard filter
- retriever baseline
- Evidence 생성
- freshness
- Retrieval의 `low_relevance`와 Evidence Decision 매핑
- evidence sufficiency와 abstention
- citation validation
- token·context budget
- A15-M 승격 시 시장 세션 기반 시간 filter

## Phase M3 — 답변·UI

- 안정적인 단일 응답 방식과 answer schema
- 초보자 설명
- 사실·해석·추론
- 핵심·긍정·위험·불확실성 카드
- source card와 오류·누락 UI
- glossary
- 익명 세션 멀티턴
- 기본 숫자·날짜·단위 검증
- 상충 자료 제한형과 여러 자료 연결 제한형
- A15-M 승격 시 상승·하락 배경 응답
- 후반 순서로 사실 요약 / 근거 기반 관점 모드와 사업 전망 카드

## Phase M4 — 대표 데모와 안정화

- API timeout·rate limit·cache
- 가드레일
- golden set과 전체 회귀 테스트
- A15-M이 승격된 경우 `price_move_reason` 회귀 테스트
- 최소 관측 필드 검증
- P0 기능 추적 표 전체 gate 확인
- 배포·smoke test

## Phase A1 — 추가 단계 우선

P1은 두 묶음으로 관리한다.

### P1-RAG 품질

- 분기별 실적 추세
- 수치 검증 고도화
- 상충 자료 자동 비교
- 뉴스 중복 제거

### P1-User 기능

- 로그인
- 사용자별 영구 세션
- 이전 대화 목록·재열기
- 관심 종목 저장

M4 종료 시 RAG 품질 결함이 남아 있으면 `P1-RAG 품질`을 먼저 진행한다. 핵심 RAG가 안정적이고 제품 사용성 보완이 더 중요하면 공개 익명 경로를 보존한 상태에서 `P1-User 기능`을 먼저 진행한다.

## Phase A2 — 추가 단계 여유

- 실시간에 가까운 갱신
- 관심 분야 정보 강조
- 지원 종목 내 관심 분야 탐색
- 산업 수혜 구조
- 시나리오 조건 카드

---

# 13. 최종 결정

## MVP에 확정

- 최신 뉴스·공시·리서치 리포트 기반 RAG
- 질문 의도와 자료 유형 라우팅
- 근거·출처·최신성
- 근거 충분성·보류
- 초보자 설명
- 사실·해석·추론 분리
- 핵심·긍정·위험·불확실성 카드
- glossary 기반 금융 용어 설명
- 익명 세션 멀티턴
- 사실 요약 / 근거 기반 관점
- A15-M 승격 gate를 통과한 경우 국내 근거 기반 상승·하락 배경
- 기본 수치 검증
- 외부 API 안정성
- 토큰·문맥 예산
- 최소 평가·회귀·관측
- 로그인 없이 완성되는 핵심 UI

## MVP 이후 실제 구현 시도

- 로그인
- 사용자별 세션
- 이전 대화 내역 확인
- 관심 종목 저장
- 분기별 실적 추세
- 수치 검증 고도화
- 자동 상충 자료 비교
- 뉴스 중복 제거
- 여유 시 실시간 갱신·관심 분야 기능·산업 설명

## 발표의 향후 계획

- 해외 뉴스와 글로벌 원인 분석
- 투자 성향 기반 고도화 개인화
- 자동 PDF 표·그래프 파싱
- 과거 유사 차트
- 시장 전체 이벤트·미반응 종목 탐색
- 요일·테마 분석
- 알림
- 여러 기기 동기화 고도화
- 소셜·수익률 공유

## 제외

- 직접적인 미래 가격 예측
- 매수·매도·보유 추천
- 목표가·손절·익절 지시
- 검증되지 않은 차트·요일 신호
- 수익 보장 또는 근거 없는 종목 순위

---

# 14. 후속 문서 반영 지침

최종 프로젝트 진행 계획서는 이 문서의 분류를 기준으로 작성한다.

반드시 구분할 것:

1. **MVP 확정 범위**
2. **MVP 완료 기준**
3. **추가 단계 P1 구현 순서**
4. **추가 단계 P2 중단 기준**
5. **향후 계획**
6. **제외 기능**
7. **기능별 평가 항목**
8. **데이터 준비와 이용 조건**
9. **UI 시연 흐름**
10. **MVP를 완료하기 전 로그인 작업을 시작하지 않는 원칙**
11. **source별 freshness window와 종목별 최소 corpus coverage**
12. **Phase별 작업 세션·Yellow/Red 전환 시점·최소 일정 버퍼**
13. **taxonomy별 fixture 수와 안전·wrong-company·citation 필수 통과 기준**
14. **provider timeout·retry, top-k, context budget, LLM 호출 상한**
15. **단일 응답 방식과 선택적 streaming 범위**

아이디어가 새로 추가될 경우 다음 질문을 통과해야 한다.

```text
체크포인트 1·2·3 중 어디에 기여하는가?
현재 데이터로 검증 가능한가?
MVP를 지연시키는가?
독립 모듈로 제거 가능한가?
golden set이나 명확한 pass 기준을 만들 수 있는가?
```

이 질문에 답하지 못하면 P0 또는 P1로 승격하지 않는다.
