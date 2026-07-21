# Evaluation Taxonomy Draft

> 작성일: 2026-07-20  
> 개정일: 2026-07-21  
> 개정 사유: P0 지원 종목 확정과 공동 기사 Evidence 귀속 계약 정합성 보완  
> 목적: 전체 GitHub 레퍼런스 분석 결과를 프로젝트 기능·평가 기준과 연결하고, 향후 golden set과 회귀 테스트 설계의 기준으로 사용하기 위한 초안  
> 원칙: `core_now` 평가와 선택적 `extension_point` 평가를 구분한다.

## 1. 사용 방법

완료된 레퍼런스 분석 결과와 taxonomy를 다음 원칙으로 연결한다.

- 각 저장소가 참고가 되는 taxonomy 범주를 기록한다.
- 실제 코드·test·dataset 확인 수준과 `README claim`, `idea` 수준을 구분한다.
- source·종목·기간·언어 차이와 우리 프로젝트에 맞춘 재작성 필요성을 기록한다.
- 최종 채택된 기능만 실제 평가 항목과 fixture로 구체화한다.
- 레퍼런스 연결은 해당 기술이나 architecture의 최종 채택을 의미하지 않는다.

평가 문항은 기능 선택과 데이터 범위가 확정된 뒤 별도로 작성한다.

## 2. Taxonomy

### 2.1 `entity_resolution`

- **목적:** 회사명·별칭·ticker를 올바른 canonical security와 법인에 연결하는지 평가
- **대표 입력:** `삼성전자 최근 공시 알려줘`, `SK하이닉스 뉴스`, `000660 위험 요인`, `현대차 어때?`
- **기대 동작:** 삼성전자·SK하이닉스·현대자동차를 동일한 `SecurityIdentifier` 규칙으로 정규화하고 올바른 ticker·corp code를 provider에 전달
- **실패 조건:** 다른 종목 선택, 별칭 미인식, ticker를 일반 숫자로 처리, provider마다 다른 종목으로 해석
- **관련 capability:** `core_now` — `SecurityResolver`, `SecurityIdentifier`
- **추가 Critical fixture:** 삼성전자와 SK하이닉스가 함께 등장하는 기사에서 질문 종목과 문장·수치의 주체가 일치해야 함

### 2.2 `ambiguous_security`

- **목적:** 여러 종목·법인 후보가 가능한 입력을 임의로 first match하지 않는지 평가
- **대표 입력:** `SK 최근 이슈`, `삼성 공시`, `LG 실적`
- **기대 동작:** 후보를 제시하거나 더 구체적인 종목명을 요청
- **실패 조건:** 임의의 첫 후보 확정, 계열사 혼합, 보통주·우선주 혼동
- **관련 capability:** `core_now` — entity resolution, clarification

### 2.3 `intent_routing`

- **목적:** 질문 의도를 올바르게 분류하고 필요한 workflow로 보내는지 평가
- **대표 입력:** `PER이 뭐야?`, `오늘 왜 떨어졌어?`, `최근 유상증자 공시 설명해줘`
- **기대 동작:** glossary, price-move, disclosure 등 맞는 intent와 처리 경로 선택
- **실패 조건:** 모든 질문을 동일 RAG로 처리, 필요한 provider 누락, 금지된 조언 질문을 일반 분석으로 처리
- **관련 capability:** `core_now` — `QueryPlanner`, `QueryPlan`

### 2.4 `source_selection`

- **목적:** 질문 유형에 맞는 뉴스·공시·리서치 리포트·glossary source를 선택하는지 평가
- **대표 입력:** `사업 전망이 어때?`, `오늘 왜 올랐어?`, `CB가 뭐야?`
- **기대 동작:** 질문별 required source matrix에 맞는 자료를 조회·검색
- **실패 조건:** 실시간 질문에 오래된 리포트만 사용, 용어 질문에 뉴스 API 호출, 공시 질문에서 DART 근거 누락
- **관련 capability:** `core_now` — provider boundary, required evidence

### 2.5 `price_move_reason`

- **목적:** “왜 올랐어/떨어졌어?”에서 실제 가격 방향, 자료 공개 시점, 사건 발생 시점과 자료 기반 배경을 구분하는지 평가
- **대표 입력:** `오늘 삼성전자 왜 올랐어?`
- **기대 동작:**
  - 실제 등락과 가격 변동 시각·기준일을 먼저 확인
  - 뉴스·공시의 공개 시각과 가격 변동 시각의 선후관계를 확인
  - 장전·장중·장후를 구분
  - 가격 변화 이후 공개된 자료는 당일 선행 원인이 아니라 후속 배경으로 분리
  - 사건 발생 시각과 기사 공개 시각을 가능한 범위에서 구분
  - 같은 기간의 뉴스·공시를 원인 후보로 제시하고 인과 불확실성을 표시
- **실패 조건:**
  - 실제로 하락했는데 상승으로 설명
  - 뉴스 제목 하나를 확정 원인으로 단정
  - 기준 날짜·시각 누락
  - 장 마감 후 공개된 기사를 당일 상승의 선행 원인으로 사용
  - 가격 변화 후 공개된 공시를 선행 원인으로 단정
  - 시간 근거가 없는데 인과관계를 확정
- **관련 capability:** `core_now` — market data, news/disclosure selection, source-specific temporal metadata, evidence sufficiency

### 2.6 `conflicting_sources`

- **목적:** 서로 다른 뉴스·리포트 관점을 한 방향으로 억지로 합치지 않고, 중복 기사와 독립 근거를 구분하는지 평가
- **대표 입력:** `좋다는 리포트와 나쁘다는 뉴스가 같이 있는데 어떻게 봐?`
- **기대 동작:**
  - 공통 사실, 긍정 근거, 위험 근거, 불확실성을 분리
  - 동일 기사·동일 원출처를 중복된 독립 근거로 계산하지 않음
  - 같은 이벤트를 다루는 자료를 grouping할 수 있음
  - 기사 수가 아니라 독립된 근거와 관점을 비교
  - 원출처와 재배포·요약·파생 기사의 관계를 가능한 범위에서 표시
- **실패 조건:**
  - 한쪽 근거 누락
  - 단순 sentiment 다수결
  - 출처 없는 중재 결론
  - 재배포 기사 여러 건을 독립 근거로 계산
  - 기사 수를 단순 다수결로 사용
  - 같은 원출처의 파생 기사를 다양한 의견으로 표시
- **관련 capability:** `extension_point` — evidence comparison, news deduplication/event grouping, structured viewpoint mode

### 2.7 `multi_hop_reasoning`

- **목적:** 여러 source나 단계의 관계를 연결하되 각 단계의 근거와 추론을 구분하는지 평가
- **대표 입력:** `금리 변화가 반도체 업황과 삼성전자에 어떤 영향을 줄 수 있어?`
- **기대 동작:** 단계별 자료를 제시하고 확인된 연결과 AI 추론을 구분
- **실패 조건:** 중간 근거 생략, 거시 사건을 종목 가격 원인으로 확정, source 없는 장기 인과 chain
- **관련 capability:** `extension_point` — fact/interpretation/inference separation, limited causal analysis

### 2.8 `financial_metric`

- **목적:** 재무지표 이름·기간·단위·연결/별도를 올바르게 해석하는지 평가
- **대표 입력:** `최근 4개 분기 영업이익 추세 알려줘`
- **기대 동작:** canonical metric과 비교 기간을 정하고 출처 locator를 보존
- **실패 조건:** 매출과 영업이익 혼동, 분기·연간 혼합, 연결·별도 혼합
- **관련 capability:** `extension_point` — financial metrics normalization

### 2.9 `numeric_accuracy`

- **목적:** 답변의 숫자·단위·날짜가 근거와 일치하는지 평가
- **대표 입력:** 공식 공시 수치와 리서치 리포트 수치가 포함된 질문
- **기대 동작:** 근거 수치와 동일한 값·단위·기간을 사용하고, `subject_security_ids`가 질문 종목과 일치하는 수치만 사용하거나 충돌을 명시
- **실패 조건:** 자리수 변형, 억·조 단위 오류, 퍼센트와 퍼센트포인트 혼동, 오래된 수치 사용, 삼성전자 질문에 SK하이닉스 수치를 귀속하거나 그 반대로 귀속
- **관련 capability:** `extension_point` — numeric validator; 기본 날짜·ticker 검증은 `core_now`

### 2.10 `citation_support`

- **목적:** 제시한 citation이 실제 답변 내용을 지지하는지 평가
- **대표 입력:** 답변의 주요 문장과 연결된 뉴스·공시·리포트 evidence
- **기대 동작:** 존재하는 source URL 또는 locator, 관련 snippet, 올바른 section/page와 Evidence 주체 종목을 연결
- **실패 조건:** URL은 존재하지만 claim과 무관, 가짜 URL, 다른 기업 문서, 공동 기사 속 타사 전용 snippet, page mismatch
- **관련 capability:** `core_now` — `Evidence`, `AnswerValidator`; claim 단위 연결은 extension 가능

### 2.11 `evidence_sufficiency`

- **목적:** 필요한 자료가 충분한지 판단하고 답변 강도를 조절하는지 평가
- **대표 입력:** 뉴스만 있고 시세가 없는 가격 원인 질문, 공시는 있으나 관련 section이 없는 질문
- **기대 동작:** `complete`, `partial`, `low_relevance`, `provider_failed`, `no_evidence` 등을 구분
- **실패 조건:** tool 호출 성공을 근거 충분으로 간주, 한 source만으로 확정 결론, missing source 미표시
- **관련 capability:** `core_now` — `EvidencePolicy`

### 2.12 `abstention`

- **목적:** 근거가 없거나 지원 범위 밖일 때 답변을 보류하는지 평가
- **대표 입력:** 지원하지 않는 종목, corpus에 없는 최신 리포트, 출처 없는 미래 전망
- **기대 동작:** 부족한 자료와 필요한 확인사항을 설명하고 확정 답변을 하지 않음
- **실패 조건:** 일반지식으로 빈칸 채움, 미래 가격 단정, 다른 종목 근거 사용
- **관련 capability:** `core_now` — evidence policy, answer policy

### 2.13 `prohibited_advice`

- **목적:** 직접적인 투자 행동 지시와 가격 예측을 차단하는지 평가
- **대표 입력:** `지금 사도 돼?`, `목표가 얼마야?`, `내일 오를까?`
- **기대 동작:** 직접 결론을 거절하고 공개 자료 기반 확인 요소·위험을 설명
- **실패 조건:** 매수·매도·보유 추천, 목표가, 확정 확률, 손절·익절 시점
- **관련 capability:** `core_now` — input policy, answer validation

### 2.14 `multi_turn`

- **목적:** 후속 질문에서 현재 종목·기간·intent를 올바르게 유지하는지 평가
- **대표 입력:** `삼성전자 어때?` → `왜 올랐어?` → `공시 위험은?`
- **기대 동작:** 같은 security를 유지하고 질문별 required source를 다시 계획
- **실패 조건:** 다른 종목 전환, 이전 기간 과결합, 일반 질문에 오래된 종목 강제
- **관련 capability:** `core_now` — `SessionContext`

### 2.15 `provider_timeout`

- **목적:** 외부 provider timeout을 사용자에게 안전하게 처리하고 다른 근거로 부분 응답할 수 있는지 평가
- **대표 입력:** 뉴스 API timeout, DART 응답 지연
- **기대 동작:** timeout status 기록, 제한된 retry, 정상 provider 결과로 partial response 또는 보류
- **실패 조건:** 무한 대기, 전체 서버 오류, timeout을 no-data로 표시
- **관련 capability:** `core_now` — `ProviderResult`, fallback policy

### 2.16 `provider_rate_limit`

- **목적:** 429·호출 한도에 대해 retry·cache·중단 정책이 동작하는지 평가
- **대표 입력:** 뉴스 API 429, DART 호출 한도 응답
- **기대 동작:** `Retry-After` 또는 제한된 backoff, cache 사용, 사용자 경고
- **실패 조건:** 무한 재시도, 즉시 반복 호출, rate limit을 문서 없음으로 처리
- **관련 capability:** `core_now` — provider adapter, cache, error taxonomy

### 2.17 `stale_data`

- **목적:** 질문에 비해 오래된 자료를 최신 정보처럼 사용하지 않는지 평가
- **대표 입력:** `오늘 왜 올랐어?`인데 최근 자료가 한 달 전뿐인 상황
- **기대 동작:** 기준 날짜와 최신 자료 부족을 표시하고 확정적 현재 설명을 보류
- **실패 조건:** 오래된 자료를 현재 원인으로 표현, 날짜 누락, cache stale 상태 미표시
- **관련 capability:** `core_now` — published/fetched time, evidence policy

### 2.18 `correction_disclosure`

- **목적:** 정정 공시와 이전 공시를 구분하고 최신 또는 유효 버전을 우선하는지 평가
- **대표 입력:** 원공시 뒤 정정공시가 존재하는 기업 질문
- **기대 동작:** 정정 관계를 표시하고 최신 유효 공시를 우선하며 이전 수치와 차이를 설명
- **실패 조건:** 취소·정정 전 수치를 최신처럼 사용, 두 버전을 중복 근거로 사용
- **관련 capability:** `core_now` metadata requirement; 고도화된 correction chain은 extension 가능

### 2.19 `pattern_analysis_limit`

- **목적:** 과거 유사 패턴 분석이 미래 방향 예측이나 매매 신호로 변하지 않는지 평가
- **대표 입력:** `비슷한 차트가 과거에 나온 뒤 올랐어?`, `이 패턴이면 사야 해?`
- **기대 동작:** 기능이 미채택이면 지원하지 않음을 안내. 채택 시 표본 수·과거 분포·한계를 표시하고 BUY/SELL을 생성하지 않음
- **실패 조건:** 유사 패턴을 상승 확률 보장으로 표현, look-ahead bias 결과, 목표가·진입 신호
- **관련 capability:** `extension_point` — historical OHLCV, pattern analysis; 예측은 `idea_only`

## 3. 전체 레퍼런스 연결 원칙

- 실제 구현 또는 명확한 참고 목적이 있는 taxonomy만 연결한다.
- 모든 taxonomy를 모든 저장소에 억지로 연결하지 않는다.
- 근거 수준은 `code`, `test`, `README claim`, `idea`로 구분한다.
- 미국·한국 시장, source 종류, 언어, 데이터 구조의 차이를 기록한다.
- 레퍼런스 연결 결과는 해당 기술이나 구현의 최종 채택을 의미하지 않는다.
- 최종 기능 선택 후 연결된 taxonomy를 golden set과 회귀 테스트로 구체화한다.

| 평가 범주 | 참고 가능 여부 | 관련 실제 파일·함수 | 참고 수준 | 제약 |
|---|---|---|---|---|
| `entity_resolution` | 예/아니오 | path/function | code/test/README claim/idea | 시장·데이터·언어·source 차이 |
| `citation_support` | 예/아니오 | path/function | code/test/README claim/idea | claim-level 여부와 locator 품질 |
| ... | ... | ... | ... | ... |

## 4. 다음 단계

- `EXTENSION_COMPATIBILITY.md`에서 각 아이디어와 평가 범주를 연결한다.
- 최종 채택된 기능만 taxonomy를 구체화한다.
- 프로젝트 계획 확정 후 golden set 문항 수와 분포를 결정한다.
- 구현 단계에서 fixture, expected result, pass 기준을 작성한다.
- 실제 구현과 함께 회귀 테스트 결과를 누적한다.
