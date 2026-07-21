# RISK_RESPONSE_MATRIX.md

> 작성일: 2026-07-20  
> 개정일: 2026-07-21  
> 개정 사유: P0 지원 종목 확정과 공동 기사 Evidence 귀속 계약 정합성 보완  ; LiteLLM·Gemini 호출 및 환각 통제 위험 추가; 무료 Gemini 데이터 전송 위험 R61 추가
> 프로젝트: 증권 AI 투자 어시스턴트 프로토타입 개발  
> 기준 문서: `EXTENSION_COMPATIBILITY.md`, `FINANCIAL_CAPABILITY_BASELINE.md`, `REFERENCE_SYNTHESIS.md`, `EVALUATION_TAXONOMY_DRAFT.md`  
> 목적: 범위가 큰 MVP를 단계별로 구현하면서 일정 초과, 데이터 실패, 검색·생성 오류, UI 복잡도, 안전성 문제를 조기에 감지하고 **기능 축소 순서와 대체 경로를 미리 고정**한다.

---

# 1. 운영 원칙

## 1.1 위험 대응의 우선순위

문제가 발생했을 때 다음 순서로 대응한다.

```text
정확성·근거 보존
→ 핵심 RAG 흐름 보존
→ 시연 가능한 UI 보존
→ 지원 범위 축소
→ 고도화 기능 제거
```

다음 순서로 대응해서는 안 된다.

```text
기능 수를 유지하기 위해 정확성·출처·오류 처리를 포기
로그인·대시보드를 유지하기 위해 RAG 안정화 지연
근거가 없는데 답변을 생성하여 데모 성공처럼 보이기
```

## 1.2 반드시 보존할 프로젝트 핵심

일정이 부족해도 다음은 최종 MVP에서 유지한다.

1. 삼성전자·SK하이닉스·현대자동차 3개 보통주
2. 뉴스·공시·리서치 리포트 3종
3. 질문 의도와 자료 유형 라우팅
4. 종목·기간·자료 유형 filter
5. 근거 snippet과 원문 locator
6. 근거 부족 시 보류
7. 초보자용 명확한 답변 UI
8. 외부 API 장애와 자료 없음 구분
9. 직접 투자 조언·확정 예측 차단
10. 최소 회귀 테스트와 실행·배포 방법

## 1.3 먼저 줄일 범위

일정 또는 품질 위험이 커지면 다음 순서로 제거하거나 축소한다.

```text
P2 기능 전체
→ P1 기능 전체
→ P0 고도화 요소
→ 지원 질문 유형 수
→ retrieval·UI의 복잡한 구현
```

최종적으로도 뉴스·공시·리서치 리포트 3종과 근거 기반 답변 흐름은 유지한다.

---

# 2. 위험 평가 기준

## 2.1 발생 가능성

| 등급 | 의미 |
|---|---|
| `L` | 발생 가능성이 낮고 사전 통제가 쉬움 |
| `M` | 구현 중 발생할 가능성이 있으며 지속적인 확인 필요 |
| `H` | 현재 범위·경험·외부 의존성을 고려할 때 발생 가능성이 높음 |

## 2.2 영향도

| 등급 | 의미 |
|---|---|
| `L` | 일부 카드나 부가기능에만 영향 |
| `M` | 특정 질문 유형 또는 개발 단계가 지연 |
| `H` | 핵심 RAG, 시연, 제출 일정, 신뢰성에 직접 영향 |

## 2.3 대응 상태

| 상태 | 의미 |
|---|---|
| `예방` | 아직 발생하지 않았으며 사전 통제 중 |
| `감시` | 징후가 보이며 확인·테스트가 필요 |
| `대응` | 실제 문제가 발생하여 fallback 또는 범위 축소 실행 |
| `수용` | 이번 범위에서는 해결하지 않고 제한사항으로 명시 |
| `제외` | 기능을 현재 계획에서 제거 |

## 2.4 상태 계층과 `low_relevance`

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

`low_relevance`는 Retrieval 상태다. `EvidencePolicy`가 질문별 필수 근거와 provider 결과를 함께 고려하여 최종 `partial` 또는 `no_evidence`로 매핑한다.

## 2.5 PROJECT_PLAN에서 수치로 확정할 기준

다음 기준은 이 문서에서 임의로 확정하지 않고 `PROJECT_PLAN.md`에서 수치화한다.

- source별 freshness window와 stale 판정
- 종목별 뉴스·공시·리포트 최소 coverage
- Phase별 예정 작업 세션 또는 종료일
- Yellow·Red 전환 D-day와 최소 일정 버퍼
- 같은 오류를 “반복”으로 판정할 재발 횟수
- taxonomy별 fixture 수와 100% 통과 항목
- provider timeout·retry 상한
- top-k·context budget·LLM 호출 상한
- 최소 관측 필드

---

# 3. 최우선 위험 요약

아래 ID는 4장의 상세 매트릭스 ID와 동일하다.

| ID | 위험 | 가능성 | 영향 | 대응 우선순위 |
|---|---|---:|---:|---:|
| R01 | P0 범위 과다로 핵심 end-to-end 흐름이 미완성 | H | H | 1 |
| R06 | AI 코딩 도구 의존으로 코드 흐름을 설명하지 못함 | H | H | 2 |
| R08 | 리서치 리포트 확보·이용 조건 불명확 | H | H | 3 |
| R09 | 뉴스 provider의 종목·기간·본문 coverage 부족 | H | H | 4 |
| R15 | 외부 API timeout으로 전체 답변 실패 | H | H | 5 |
| R16 | 429·호출 한도 초과 | H | H | 6 |
| R25 | metadata filter 실패로 다른 기업 문서 검색 | M | H | 7 |
| R26 | 낮은 관련도의 검색 결과로 답변 생성 | H | H | 8 |
| R29 | citation이 실제 claim을 지지하지 않음 | M | H | 9 |
| R30 | 숫자·단위 또는 숫자의 귀속 회사가 변형됨 | H | H | 10 |
| R38 | 직접 투자 조언·목표가 출력 | M | H | 11 |
| R53 | golden set을 늦게 작성해 결함을 마지막에 발견 | H | H | 12 |
| R61 | 무료 Gemini에 민감정보·외부 처리 미허용 자료 전송 | M | H | 13 |

---

# 4. 전체 위험 대응 매트릭스

## 4.1 일정·범위·개발 운영

| ID | 위험 | 관련 단계 | 가능성/영향 | 조기 징후 | 예방 조치 | 발생 시 즉시 대응 | fallback·축소 기준 | 확인 증거 |
|---|---|---|---|---|---|---|---|---|
| R01 | P0 기능 수가 많아 핵심 흐름이 끝까지 연결되지 않음 | M0~M4 | H/H | 여러 모듈이 동시에 미완성, end-to-end 테스트 없음, UI만 먼저 확장 | M0에서 질문 유형·종목·source 확정, 매 Phase마다 vertical slice 유지 | 새로운 기능 작업 중단, 마지막 정상 end-to-end 경로부터 복구 | P2→P1 전부 보류, 세 종목 범위 유지, P0 고도화 카드 제거 | 하나의 질문이 API→검색→근거→답변→UI까지 통과 |
| R02 | 구현 순서가 뒤섞여 provider·retriever·UI가 서로 다른 계약 사용 | M1~M3 | M/H | dict field 불일치, 임시 변환 코드 증가, 테스트 fixture 중복 | `SecurityIdentifier`, `FinancialDocument`, `Evidence`, 상태 계약 먼저 고정 | 기능 개발 중단 후 contract와 adapter 정리 | LangGraph·복잡한 agent 제거, 일반 함수 workflow로 단순화 | schema test와 type check 통과 |
| R03 | P1 로그인 개발을 P0 완료 전에 시작 | A1 | M/H | 인증 화면은 있으나 RAG가 불안정, 사용자 DB 때문에 배포 지연 | P1 승격 조건을 체크리스트로 강제 | 로그인 branch 동결, 공개 익명 MVP 경로 복구 | P1 기능 전체 숨김 또는 제거 | P0 체크포인트 테스트 전부 통과 |
| R04 | 기술 선택을 오래 고민하여 실제 구현 시간이 줄어듦 | M0~M2 | H/M | vector DB·agent framework 비교만 반복, 코드 시작 지연 | 비교 기간과 결정 시한 설정, 작은 corpus benchmark만 수행 | 가장 단순한 검증 가능 조합 선택 | 규칙 router + 단일 retriever + 일반 Python workflow | 선택 이유·제외 이유 1페이지 기록 |
| R05 | 여러 코딩 에이전트가 서로 다른 구조로 코드를 생성 | 전 단계 | M/H | 동일 기능 중복, 파일명·schema 불일치, 수정 때마다 회귀 | 단계별 단일 작업지시, contract 문서를 항상 첨부, 한 branch 한 목적 | 코드 생성 중단, 현재 main 기준으로 diff 검토 | 미사용 abstraction·중복 모듈 삭제 | architecture note와 실제 폴더 구조 일치 |
| R06 | AI 코딩 도구에 의존해 발표 시 코드 흐름을 설명하지 못함 | 전 단계 | H/H | 실행 명령·오류 원인을 설명 못함, 에이전트 답변을 그대로 복사 | 매 Phase 종료 시 흐름도·입출력·실패 경로를 직접 정리 | 해당 기능 확장 중단 후 최소 재현 테스트를 직접 수행 | 이해하지 못한 고도화 기능 제거 | 본인이 3분 내 입력→출력 흐름 설명, 핵심 함수 위치 제시 |
| R07 | 문서와 실제 구현이 달라짐 | M1~M4 | M/M | 계획서는 P0인데 코드에는 P2 구조 존재, 완료 표시와 테스트 불일치 | Phase 종료 시 문서와 코드 동시 갱신 | 완료 체크를 되돌리고 차이 목록 작성 | 문서가 아니라 실제 작동 범위를 기준으로 발표 | README 실행 절차와 smoke test 일치 |

## 4.2 데이터 확보·이용·최신성

| ID | 위험 | 관련 단계 | 가능성/영향 | 조기 징후 | 예방 조치 | 발생 시 즉시 대응 | fallback·축소 기준 | 확인 증거 |
|---|---|---|---|---|---|---|---|---|
| R08 | 리서치 리포트 확보·이용 조건이 불명확 | M0~M1 | H/H | 원문 URL 만료, 재배포 가능 여부 불명, 자료 출처 누락 | 사용 가능한 자료 목록·usage note·manifest·file hash 작성 | 문제 자료 ingest 중단, 사용자 응답에서 원문 재배포 제외 | 리포트 수를 종목당 최소 문서로 축소, 수동 요약 corpus 사용 | manifest에 source·date·usage note·locator 존재 |
| R09 | 뉴스 provider가 원하는 기간·본문·종목 정보를 충분히 주지 않음 | M0~M2 | H/H | 제목만 제공, 중복 많음, 종목 무관 기사 비율 높음 | provider 후보를 실제 3개 종목 질문으로 사전 시험 | 제목+snippet 기반 제한 답변, 무관 기사 filter 강화 | source 수집 자동화 대신 검수된 최근 뉴스 적재 | entity·기간·관련성 fixture 통과 |
| R10 | DART corp code·ticker 연결 오류 | M1 | M/H | 공시가 없거나 계열사 공시 혼합 | security와 corporation ID 분리, exact match·후보 재질문 | provider 호출 중단 후 resolver 결과 확인 | 지원 종목을 명시적 mapping으로 제한 | 종목별 ticker·corp_code golden fixture |
| R11 | 자료가 오래됐는데 최신 분석처럼 보임 | M2~M4 | M/H | 기준일 누락, 한 달 전 문서로 “오늘” 설명 | published_at·fetched_at·basis_date 필수, 질문별 freshness rule | 확정 답변을 partial 또는 abstain으로 변경 | 최신 자료 없는 질문 유형 비활성화 | stale_data 테스트 통과 |
| R12 | 정정 공시보다 이전 공시가 우선 검색됨 | M1~M2 | M/H | 동일 공시 수치 충돌, correction 표시 누락 | receipt·correction status 보존, 최신 유효본 우선 | 해당 답변 보류, 두 버전 비교 표시 | correction chain이 불확실한 수치 질문 제한 | correction_disclosure fixture |
| R13 | PDF 텍스트·표가 깨져 리포트 내용이 왜곡됨 | M1 | H/M | 열 순서 뒤섞임, 숫자·단위 분리, 빈 chunk | MVP는 수동 정규화 text와 page locator 사용 | 문제 PDF 자동 파싱 중단, 수동 보정 | 표·그래프 자동 추출 전부 P3 유지 | 원문 페이지와 정규화 text 샘플 대조 |
| R14 | glossary 정의가 부정확하거나 과도하게 단순화됨 | M0~M3 | M/M | “PER 낮음=무조건 저평가” 같은 문구 | 정의·주의점·예시를 함께 검수, version 관리 | 해당 용어 비활성화 후 정의 수정 | 10~15개 핵심 용어만 유지 | 용어별 expected key point 테스트 |

## 4.3 Provider·API·인프라

| ID | 위험 | 관련 단계 | 가능성/영향 | 조기 징후 | 예방 조치 | 발생 시 즉시 대응 | fallback·축소 기준 | 확인 증거 |
|---|---|---|---|---|---|---|---|---|
| R15 | 외부 API timeout으로 전체 답변이 실패 | M1~M4 | H/H | 응답 지연, request hang, stream 중단 | 명시적 timeout, 제한 retry, 병렬 호출 상한 | 실패 provider status 기록 후 정상 source로 partial 응답 | API 대신 최근 적재 자료 또는 cache | timeout fake 테스트 |
| R16 | 429·호출 한도 초과 | M1~M4 | H/H | 반복 429, 데모 직전 quota 부족 | cache, 호출 간격, semaphore, Retry-After, 데모 사전 적재 | 재호출 중단, cache 사용, 사용자에게 누락 source 표시 | 실시간 갱신 중단하고 고정 demo dataset 사용 | rate_limit fixture와 호출 로그 |
| R17 | API key·secret 노출 | M1~M4 | M/H | `.env` commit, 로그·화면에 key 출력 | `.gitignore`, 환경변수, 로그 sanitizer, secret scan | key 폐기·재발급, git history 대응 | 해당 provider 임시 비활성화 | secret scan 0건 |
| R18 | provider가 빈 결과와 오류를 동일하게 반환 | M1~M2 | H/H | `[]`만 반환, UI에 “자료 없음” 오표시 | typed Provider status와 error_code 사용 | adapter 수정, 기존 응답을 신뢰하지 않음 | provider_failed로 표시하고 보류 | no_data·timeout·parse_error 개별 테스트 |
| R19 | cache가 오래된 자료를 최신처럼 반환 | M1~M4 | M/H | from_cache 표시 없음, fetched_at 갱신 안 됨 | TTL, fetched_at, from_cache, stale 정책 | stale warning 추가, 최신성 질문 보류 | cache 사용 중단 또는 수동 갱신 | stale cache test |
| R20 | 로컬에서는 되지만 배포 환경에서 실패 | M4 | M/H | 파일 경로·timezone·encoding 차이, startup API 호출 | Docker 또는 고정 실행환경, 상대 경로, startup 외부 호출 금지 | 배포 로그 기반으로 ingest와 app 분리 | 단일 인스턴스·로컬 데모 백업 준비 | clean environment smoke test |
| R21 | sync API와 SSE 응답 내용이 다름 | M3~M4 | M/M | streaming에서 경고·출처 누락 | 동일 orchestration 결과를 serializer만 분리 | 한 방식 비활성화 후 일관된 endpoint 사용 | 발표에서는 안정적인 한 방식만 사용 | sync/stream snapshot test |

## 4.4 종목 식별·라우팅·검색

| ID | 위험 | 관련 단계 | 가능성/영향 | 조기 징후 | 예방 조치 | 발생 시 즉시 대응 | fallback·축소 기준 | 확인 증거 |
|---|---|---|---|---|---|---|---|---|
| R22 | 모호한 회사명을 임의 종목으로 선택 | M1~M2 | M/H | “삼성”, “LG”, “SK”가 첫 후보로 자동 확정 | 후보 반환·재질문, 지원 종목 명시 | provider 호출 전에 clarification | 지원 종목 드롭다운 병행 | ambiguous_security 테스트 |
| R23 | 보통주·우선주 또는 법인·상장주 혼동 | M1 | M/H | ticker와 corp code가 뒤섞임 | security_type과 corp_code 분리 | 잘못 연결된 문서 폐기, resolver 수정 | 우선주 미지원 명시 | entity_resolution fixture |
| R24 | 질문 intent가 잘못 분류되어 잘못된 source 호출 | M2 | M/H | 용어 질문에 뉴스 API, 공시 질문에 glossary만 사용 | 규칙 기반 router와 required source matrix | LLM router 결과 무시하고 fallback rule 적용 | 초기 intent 수를 축소 | intent_routing 테스트 |
| R25 | 다른 기업 또는 공동 기사 속 타사 Evidence가 질문 종목에 혼입됨 | M1~M3 | H/H | 삼성전자·SK하이닉스 공동 기사에서 타사 사실·수치가 섞임, citation 기업 불일치 | 문서 primary/mentioned 종목과 Evidence subject/scope를 분리하고 retrieval 후 주체 filter 적용 | 답변 차단, 잘못 귀속된 Evidence 제외·재정규화 | 자동 귀속을 줄이고 명시 주체 문장만 사용 | wrong-company·cross-company attribution test |
| R26 | top-k 문서가 질문과 낮은 관련성인데 그대로 답변 | M2 | H/H | score는 있으나 snippet 무관, generic 문장 | empty와 low_relevance 구분, 최소 관련성·coverage 검사 | no_evidence 또는 partial로 변경 | lexical baseline·수동 keyword fallback | low_relevance fixture |
| R27 | query rewrite가 질문 의도를 바꿈 | M2 | M/M | “위험” 질문이 “전망” 검색으로 변환 | 원문 query 보존, rewrite 비교 테스트 | rewrite 비활성화 | 초기에는 rewrite 사용 안 함 | 원문·rewrite retrieval 비교 |
| R28 | hybrid·reranker 구현이 복잡해 일정 지연 | M2 | M/H | 실험은 많지만 end-to-end 없음 | lexical·dense·hybrid를 작은 subset에서만 비교 | 가장 단순한 통과 방식 고정 | keyword/TF-IDF 또는 단일 dense 사용 | benchmark 기록과 선택 근거 |

## 4.5 답변·근거·금융 정확성

| ID | 위험 | 관련 단계 | 가능성/영향 | 조기 징후 | 예방 조치 | 발생 시 즉시 대응 | fallback·축소 기준 | 확인 증거 |
|---|---|---|---|---|---|---|---|---|
| R29 | citation은 존재하지만 claim을 지지하지 않음 | M2~M4 | M/H | URL은 맞지만 snippet이 다른 내용 | Evidence snippet을 code-built citation과 함께 전달 | 해당 문장 제거 또는 표현 약화 | 문장별 citation 대신 섹션별 근거로 단순화 | citation_support test |
| R30 | 숫자·단위 또는 숫자의 귀속 회사가 변형됨 | M3 | H/H | 삼성전자 질문에 SK하이닉스 수치 사용, 억·조 단위·%·%p 혼동 | Evidence 숫자 literal·기간·단위·subject_security_ids 검증 | 해당 수치 문장 제거 후 원문값과 회사명 직접 표시 | 숫자 카드 숨김 | numeric_accuracy·cross-company attribution fixture |
| R31 | 사실·자료 해석·AI 추론이 섞임 | M3 | M/H | 추정이 사실처럼 표현 | 응답 schema와 고정 라벨, inference marker | validator가 확정 표현 수정 또는 차단 | 자유형 답변 대신 고정 template | section별 expected output |
| R32 | 근거 부족인데 답변을 강제로 생성 | M2~M3 | H/H | provider 호출 성공만으로 complete 처리 | EvidencePolicy를 tool completeness와 분리 | partial/no_evidence/blocked로 강등 | LLM 호출 없이 고정 보류 응답 | evidence_sufficiency·abstention test |
| R33 | 가격 변동 원인을 사후 기사로 설명 | M3~M4 | M/H | 장후 기사로 장중 상승 설명 | MarketSnapshot과 published_at·market_session 비교 | 선행 원인에서 제외하고 후속 배경 표시 | price-move 질문 비활성화 | price_move_reason fixture |
| R34 | 해외 요인이 빠졌는데 전체 원인처럼 단정 | M3 | H/M | 반도체·환율 이슈에서 국내 기사만 사용 | 국내 자료 기준이라는 범위 경고 | “확인 가능한 배경 후보”로 표현 | 글로벌 원인 분석은 P3로 유지 | missing source warning 확인 |
| R35 | 사업 전망 요약이 미래 실적·주가 예측으로 변질 | M3 | M/H | “성장할 것이다”, “오를 가능성” 단정 | 계획·조건·위험·예정 이벤트 중심 schema | 예측 문장 제거, 문서 표현으로 제한 | 전망 카드를 숨기고 최근 이슈 요약만 유지 | prohibited_advice test |
| R36 | 상충 자료 비교가 기사 수 다수결이 됨 | M3 | M/M | 동일 원출처 재배포가 여러 근거로 계산 | MVP는 양쪽 Evidence 병렬 표시, 자동 다수결 금지 | 중복 의심 자료를 한 그룹으로 표시 | 자동 grouping은 P1로 연기 | conflicting_sources fixture |
| R37 | glossary 근거 없이 LLM 일반지식으로 답함 | M3 | M/M | locator 없음, 매번 정의가 바뀜 | financial_term intent는 glossary required | glossary 미검색 시 보류 또는 일반 안내 | 지원 용어 외 질문은 범위 밖 표시 | glossary source test |

## 4.6 안전성·정책

| ID | 위험 | 관련 단계 | 가능성/영향 | 조기 징후 | 예방 조치 | 발생 시 즉시 대응 | fallback·축소 기준 | 확인 증거 |
|---|---|---|---|---|---|---|---|---|
| R38 | 매수·매도·보유·목표가를 직접 제시 | M3~M4 | M/H | “사세요”, “목표가”, “손절” 출력 | input/output policy, 금지 표현 validator, 안전 대체 template | 응답 차단 후 사실·위험·확인 조건으로 재작성 | 근거 기반 관점 모드 비활성화 | prohibited_advice golden set |
| R39 | “관점 모드”가 사실상 추천 모드가 됨 | M3 | M/H | 긍정/부정 점수로 행동 결론 | 점수·BUY/SELL field 금지, 긍정·위험·불확실성만 허용 | 모드를 사실 요약으로 강제 전환 | 관점 모드 제거 | 두 모드 사실 일치 test |
| R40 | 면책 문구만 붙이고 위험한 내용을 그대로 제공 | M3 | M/H | 추천 뒤 “투자 책임은 본인” 표시 | 내용 정책을 우선하고 고지는 보조로 사용 | 위험 문장 자체 삭제 | 고정 안전 응답 | validator test |
| R41 | 사용자 질문에 미래 가격 확률을 임의 생성 | M3 | M/H | 근거 없는 “70%” 등 출력 | 확률·목표가·예측 표현 금지 | 전체 응답 blocked | 예측 질문은 고정 거절 | pattern_analysis_limit test |

## 4.7 UI·사용성

| ID | 위험 | 관련 단계 | 가능성/영향 | 조기 징후 | 예방 조치 | 발생 시 즉시 대응 | fallback·축소 기준 | 확인 증거 |
|---|---|---|---|---|---|---|---|---|
| R42 | 카드가 많아 핵심 답변이 묻힘 | M3 | M/H | 첫 화면에 긴 텍스트·출처 전부 노출 | 핵심 요약 우선, 상세 근거 접기, 1화면 hierarchy | 카드 수 축소, 상세 영역으로 이동 | 핵심·위험·근거 3영역만 유지 | 초보 사용자 태스크 테스트 |
| R43 | 금융 용어를 쉽게 설명하다 핵심 정의가 누락 | M3 | M/M | 비유만 있고 정확한 정의 없음 | “한 줄 정의→왜 중요→주의점” 고정 구조 | glossary 원문 핵심 문장 복원 | 비유 제거 | glossary expected key point |
| R44 | 오류 상태가 기술 코드로만 표시 | M3 | M/M | `RATE_LIMITED`, stack trace 노출 | 사용자 메시지와 내부 진단 분리 | 일반 문장으로 변환, 상세는 개발 로그로 | 오류 상세 UI 제거 | 오류별 UI snapshot |
| R45 | 출처를 눌러도 원문 위치를 찾기 어려움 | M3 | M/H | URL만 있고 page·section 없음 | Evidence card에 title·date·page/section/receipt 표시 | locator 없는 citation 숨김·보류 | manual corpus는 page 기반으로 제한 | citation click-through 확인 |
| R46 | 모바일·발표 화면에서 레이아웃 붕괴 | M3~M4 | M/M | 카드 overflow, 긴 URL 노출 | 최소 두 화면 폭 테스트, URL 텍스트 축약 | 발표용 해상도 고정 layout | 모바일 최적화 P2로 이동 | 화면 캡처·smoke test |

## 4.8 세션·로그인·사용자 데이터

| ID | 위험 | 관련 단계 | 가능성/영향 | 조기 징후 | 예방 조치 | 발생 시 즉시 대응 | fallback·축소 기준 | 확인 증거 |
|---|---|---|---|---|---|---|---|---|
| R47 | 익명 멀티턴에서 이전 종목이 잘못 이어짐 | M3 | M/H | 새 질문에 오래된 종목 강제 | 명시 종목 우선, reset, 일반 질문에서 context 약화 | session context 초기화 | 최근 1개 종목만 유지 | multi_turn fixture |
| R48 | 서버 재시작으로 익명 세션이 사라짐 | M3~M4 | M/L | 데모 중 대화 초기화 | MVP 요구를 “현재 접속 중 세션”으로 명시 | 새 세션 안내 | persistence는 P1로 유지 | session lifecycle test |
| R49 | 사용자 A의 대화·관심 종목이 B에게 노출 | A1 | M/H | user_id filter 누락 | 모든 query에 authenticated owner filter, 격리 테스트 | P1 기능 즉시 비활성화 | 공개 익명 MVP만 제공 | user_isolation test |
| R50 | 로그인 구현으로 공개 데모 접근성이 떨어짐 | A1 | M/M | 가입 없이는 핵심 기능 사용 불가 | 공개 익명 경로 유지, 로그인은 optional | 인증 gate 제거 | 로그인 UI 숨김 | anonymous smoke test |
| R51 | 비밀번호·token 처리 오류 | A1 | M/H | 평문 저장, 만료 없음 | 검증된 auth library 또는 외부 인증, hash·expiry | 계정 기능 중단·credential 폐기 | P1 로그인 제외 | auth security checklist |
| R52 | 관심 종목이 지원하지 않는 시장 전체 기능으로 확장 | A1 | M/M | ticker 자유 입력, 데이터 없는 종목 저장 | 삼성전자·SK하이닉스·현대자동차 중 선택만 허용 | 잘못된 항목 제거 | watchlist 기능 숨김 | supported_security_only test |

## 4.9 평가·관측·품질 관리

| ID | 위험 | 관련 단계 | 가능성/영향 | 조기 징후 | 예방 조치 | 발생 시 즉시 대응 | fallback·축소 기준 | 확인 증거 |
|---|---|---|---|---|---|---|---|---|
| R53 | golden set을 마지막에 만들어 핵심 결함을 늦게 발견 | M0~M4 | H/H | 데모 질문만 수동 확인 | M0에서 핵심 질문·실패 질문 초안 작성 | 신규 기능 중단, 회귀셋부터 작성 | 문항 수를 줄이되 핵심 taxonomy 유지 | 자동 테스트 결과 |
| R54 | 테스트가 외부 API 상태에 따라 불안정 | M1~M4 | H/M | 같은 테스트가 랜덤 실패 | provider fake·recorded fixture 사용 | live test와 unit test 분리 | live integration은 smoke만 유지 | deterministic test run |
| R55 | LLM 응답 변동으로 pass 기준이 모호 | M3 | H/M | 문장 표현 차이로 실패 | 구조·필수 요소·금지 표현 기준으로 평가 | exact string test 제거 | 핵심 field 기반 validation | expected schema test |
| R56 | Langfuse 도입이 자체 목적이 되어 구현 지연 | M4 | M/M | tracing 설정에 시간 과다 | 관측 최소 범위: latency·provider·evidence·LLM call | 단순 구조 로그로 대체 | Langfuse P1로 이동 가능 | 요청별 trace 또는 JSON log |
| R57 | 로그에 원문·API key·사용자 대화가 과도하게 저장 | M4/A1 | M/H | 민감 정보 평문 trace | sanitizer, 최소 로그, secret 제거 | 해당 로그 삭제·관측 중단 | 사용자 기능 전에는 익명 최소 로그 | logging privacy test |
| R58 | README·보고서에 재현하지 않은 성능 수치를 기재 | M4 | M/H | 외부 저장소 수치 인용, 테스트 조건 없음 | 자체 측정값만 사용, 조건·표본 명시 | 수치 삭제 또는 “미재현” 표시 | 정성 평가와 test 통과율만 제시 | raw result·실행 명령 보존 |
| R59 | LiteLLM과 Gemini API의 요청·응답 옵션이 버전 차이로 불일치 | M3~M4 | M/H | structured output 인자 거부, 예외 mapping 변화, 응답 field 누락 | LiteLLM 버전 pin, adapter 단위 mock, 소수 live smoke, raw 객체 격리 | structured output 기능을 끄고 JSON-only + Pydantic parse로 축소 | LiteLLM adapter만 교체하고 composer 계약 유지 | compatibility unit·live smoke |
| R60 | Gemini가 schema에 맞지만 Evidence 밖 사실·수치·URL을 생성 | M3~M4 | H/H | JSON parse는 성공하지만 source ID·숫자·회사 귀속 불일치 | Evidence ID 제한, 종목·수치·citation validator, search grounding 금지 | 위반 문장 제거 또는 전체 `blocked`·고정 보류 | 핵심·위험·근거 template로 축소 | unsupported-claim·numeric·citation Critical fixture |
| R61 | 무료 Gemini API에 기밀·개인정보 또는 외부 처리 미허용 리포트가 전송됨 | M0·M1·M3 | M/H | prompt에 계좌·보유량·secret·전체 세션·미허용 리포트 원문 포함 | 최소 snippet 전송, UI 주의문, secret·path sanitizer, manifest `external_llm_processing_allowed` gate | 호출 차단, 해당 자료 제거, fixed template·비LLM 경로 사용 | 허용 여부 불명확 자료 전체를 LLM 경로에서 제외 | prompt sanitizer·manifest gate·privacy fixture |

---

# 5. Phase별 위험 게이트

## 5.1 Phase M0 — 범위 확정 게이트

다음이 결정되지 않으면 M1으로 넘어가지 않는다.

- [ ] 삼성전자·SK하이닉스·현대자동차 3개 보통주
- [ ] 뉴스 provider 또는 수동 fallback
- [ ] DART 공시 방식
- [ ] 사용 가능한 리서치 리포트 목록과 이용 조건
- [ ] glossary 10~30개 범위
- [ ] MVP 질문 intent
- [ ] UI 핵심 화면
- [ ] golden set 초안
- [ ] P1·P2 기능은 M4 이후라는 합의

### M0 실패 대응

- 지원 종목을 3개로 고정
- 질문 intent를 핵심 5~7개로 축소
- 리포트 자동 수집 포기
- UI를 질문·답변·근거의 단일 화면으로 고정

## 5.2 Phase M1 — 데이터·API 게이트

다음이 통과되어야 M2로 넘어간다.

- [ ] 종목 resolver fixture
- [ ] 뉴스·공시 provider 성공·no-data·timeout 구분
- [ ] 수동 리포트 ingest
- [ ] glossary ingest와 corpus locator 검증
- [ ] `FinancialDocument`의 primary/mentioned 종목과 `Evidence`의 subject/scope 계약
- [ ] `FinancialDocument`와 `Evidence` locator 보존
- [ ] API key 비노출
- [ ] clean environment에서 health 성공
- [ ] A15-M 조건부 P0 판단: MarketSnapshot adapter·timezone·market session 정상/실패 fixture 통과 또는 P1 이동 결정

### M1 실패 대응

- 외부 provider 하나를 recorded fixture로 대체
- 자동 ingest 대신 수동 corpus 사용
- 5종목을 3종목으로 축소
- 복잡한 DB 대신 JSON/SQLite 등 최소 저장 방식 사용

## 5.3 Phase M2 — 검색·근거 게이트

다음이 통과되어야 M3로 넘어간다.

- [ ] security·source·period hard filter
- [ ] empty와 low relevance 구분
- [ ] wrong-company 차단
- [ ] 삼성전자·SK하이닉스 공동 기사에서 타사 전용 Evidence 차단
- [ ] Evidence snippet·locator 반환
- [ ] Retrieval의 `low_relevance`를 Evidence Decision의 `partial` 또는 `no_evidence`로 매핑
- [ ] complete·partial·provider_failed·no_evidence·blocked 판정
- [ ] token·context budget과 LLM 호출 상한 적용
- [ ] citation support 기본 테스트

### M2 실패 대응

- hybrid·reranker 제거
- lexical 또는 단일 dense baseline으로 고정
- 질문 유형별 document filter를 더 강하게 적용
- 자유 agent 검색을 제거하고 deterministic workflow 사용

## 5.4 Phase M3 — 답변·UI 게이트

다음이 통과되어야 M4로 넘어간다.

- [ ] 초보자 설명
- [ ] 사실·해석·추론 구분
- [ ] 핵심·긍정·위험·불확실성 카드
- [ ] glossary 근거
- [ ] 익명 멀티턴
- [ ] 투자 조언 차단
- [ ] 근거 부족 보류
- [ ] 오류·누락 자료 UI
- [ ] 출처 상세 보기
- [ ] 기본 숫자·날짜·단위 literal 검증
- [ ] 숫자의 subject_security_ids와 질문 종목 일치 검증
- [ ] 상충 자료 제한형과 여러 자료 연결 제한형
- [ ] A15-M 승격 시 상승·하락 배경의 선행·장중·후속 구분
- [ ] A23-M 단일 안전 구조화 답변의 필수 section과 금지 표현 테스트
- [ ] LiteLLM→Gemini structured output compatibility와 parse failure 처리
- [ ] schema-valid 응답도 Evidence·수치·citation validator를 통과해야 함

- [ ] 외부 처리 허용 Evidence만 Gemini에 전송
- [ ] personal·secret·local path·전체 세션 전송 차단
- [ ] sanitized live smoke와 fixture 결과를 구분
- [ ] 무료 quota 실패 시 자동 billing·유료 전환 없음
- [ ] A17-M이 활성 P0이면 문서 근거·예측 금지 테스트

### M3 실패 대응

- 관점 모드 비활성화
- 카드 수를 핵심·위험·근거로 축소
- LiteLLM structured output이 불안정하면 JSON-only + Pydantic parse로 축소
- LLM 자유형 출력 대신 고정 구조 사용
- 상승·하락 원인 기능을 숨기고 최근 이슈·공시·리포트 요약을 우선 안정화

## 5.5 Phase M4 — 안정화·배포 게이트

MVP 완료 조건:

- [ ] 대표 질문 end-to-end 통과
- [ ] provider 장애 시 partial 또는 보류
- [ ] 안정적인 단일 응답 방식 동작. sync와 streaming을 모두 구현한 경우에만 consistency test 통과
- [ ] 회귀 테스트 통과
- [ ] 배포 환경 smoke test
- [ ] 한 가지 실행 방법 문서화
- [ ] 데모용 데이터 기준일 명시
- [ ] 최소 관측 필드(`request_id`, intent, security_id, provider status, evidence count, final decision, latency, LLM call count) 검증
- [ ] 발표자가 흐름과 제한을 설명 가능
- [ ] 모든 활성 P0 코어·아이디어 기능이 추적 표에 연결되어 있고, 각 기능의 완료 gate와 필수 taxonomy 테스트를 통과

### M4 실패 대응

- streaming 비활성화
- 공개 데모를 단일 안정 endpoint로 제한
- P1·P2 작업 취소
- 로컬 실행 가능한 백업 데모 준비
- 불안정 질문 유형 UI에서 숨김

## 5.6 Phase A1 — 추가 기능 승격 게이트

### 5.6.1 A1 공통 게이트

- [ ] M4 MVP 완료
- [ ] 공개 MVP 경로 보존
- [ ] `PROJECT_PLAN.md`에서 정한 최소 일정 버퍼 존재
- [ ] 독립 branch에서 구현하며 제거해도 P0가 유지됨
- [ ] 어느 P1 묶음을 먼저 진행할지 Human Owner가 결정

### 5.6.2 P1-RAG 품질 게이트

- [ ] 개선 대상 taxonomy와 실패 fixture가 명확함
- [ ] P0 baseline 결과가 보존되어 있음
- [ ] 개선 전후를 비교할 수 있는 pass 기준이 있음
- [ ] P0 회귀 테스트를 유지한 채 독립적으로 제거 가능함

### 5.6.3 P1-User 기능 게이트

- [ ] 공개 익명 경로 보존
- [ ] 사용자 DB schema 최소화
- [ ] user isolation test 계획
- [ ] 인증·영구 세션·관심 종목 기능을 제거해도 MVP가 유지됨

해당 묶음의 공통·전용 게이트 중 하나라도 충족하지 못하면 그 P1 묶음을 시작하지 않는다.

---

# 6. MVP 구조 구제 시나리오

## 6.1 정상 상태 — Green

- P0 전체 구현
- 삼성전자·SK하이닉스·현대자동차 3개 보통주
- 뉴스·공시·리포트 3종
- A15-M 승격 게이트를 통과한 경우 국내 근거 기반 상승·하락 배경
- A23-M 단일 안전 구조화 답변
- 익명 멀티턴
- 최소 관측과 회귀 테스트

## 6.2 일정 주의 — Yellow

`PROJECT_PLAN.md`가 정한 Phase effort·종료일·오류 재발 기준을 사용한다.

다음 중 하나가 발생하면 Yellow로 전환한다.

- 한 Phase가 `PROJECT_PLAN.md`의 예정 작업량 또는 종료일 대비 30% 이상 지연
- 외부 provider 한 곳이 반복 실패
- end-to-end 경로가 2일 이상 깨져 있음
- 테스트보다 신규 기능 구현이 앞서기 시작함

Yellow 대응:

- 지원 종목 3개로 고정
- P1·P2 작업 금지
- hybrid·reranker·query rewrite 제거 검토
- 카드 UI 단순화
- 상충 자료 자동 grouping 연기
- 리포트 자동화 없이 수동 corpus만 사용
- 가격 원인 분석을 대표 종목·질문으로 제한

## 6.3 완료 위험 — Red

Red 전환 D-day와 오류 반복 횟수는 `PROJECT_PLAN.md`에서 확정한다.

다음 중 하나가 발생하면 Red로 전환한다.

- 제출·발표 직전에도 end-to-end 경로가 안정적이지 않음
- citation·종목 혼입·숫자 오류가 반복
- 배포 환경에서 핵심 질문 실패
- provider 장애가 사용자 응답 전체를 중단시킴

Red 대응:

1. P1·P2 기능 전부 제거
2. 관점 모드·상승 원인 기능 등 불안정 P0 기능의 공식 범위 축소 검토
3. 지원 질문을 최근 이슈·공시 요약·리포트 요약·금융 용어·위험 요약으로 제한
4. 3개 종목과 검수된 demo dataset으로 고정
5. 외부 API 실패 시 적재 자료로만 답변
6. streaming이 구현된 경우 제거하고 안정적인 단일 응답 방식 유지
7. 단일 배포·실행 방식만 유지
8. 근거 없는 답변보다 보류 응답을 선택

Red 상태에서도 다음은 유지한다.

- 뉴스·공시·리포트 3종
- 근거 snippet과 locator
- 초보자 설명
- 오류·누락 표시
- 투자 조언 차단

P0 기능을 제거하려면 Human Owner가 `EXTENSION_COMPATIBILITY.md`와 `PROJECT_PLAN.md`의 우선순위·완료 기준을 함께 갱신해야 한다. 문서 갱신 전 결과물은 `scope-reduced MVP candidate`이며 P0 완료로 처리하지 않는다.

---

# 7. 중단·제거 기준

## 7.1 즉시 제거할 기능

다음 조건이면 해당 기능을 숨기거나 제거한다.

- 다른 종목 근거를 반환
- citation이 claim을 지지하지 않음
- 숫자 검증 실패가 반복
- 투자 조언·목표가를 출력
- 사용자 데이터 격리 실패
- API key 또는 로컬 경로 노출
- 배포 환경에서 무한 대기

## 7.2 P1·P2 중단 기준

- M4 회귀 테스트 미통과
- 남은 일정 버퍼 부족
- P1 때문에 공개 익명 MVP 경로가 깨짐
- DB migration이 코어 RAG schema를 흔듦
- 기능별 독립 제거가 불가능함
- 발표자가 구현 원리를 설명하지 못함

## 7.3 수용 가능한 제한

다음은 명확히 고지하면 MVP에서 수용할 수 있다.

- 지원 종목 3개로 제한
- 해외 뉴스 미지원
- 리서치 리포트 수동 적재
- 자동 PDF 표·그래프 해석 미지원
- 익명 세션이 브라우저·서버 재시작 후 유지되지 않음
- 시장 전체 종목 탐색 미지원
- 실시간이 아니라 기준일이 표시된 최신 자료 사용
- 상충 뉴스 중복 제거가 제한적임

---

# 8. 필수 테스트와 위험 연결

| 평가·테스트 | 방지하는 주요 위험 |
|---|---|
| `entity_resolution` | R10, R22, R23 |
| `ambiguous_security` | R22 |
| `intent_routing` | R24 |
| `source_selection` | R24, R34 |
| `price_move_reason` | R33, R34 |
| `conflicting_sources` | R36 |
| `financial_metric` | R30 |
| `numeric_accuracy` | R30 |
| `citation_support` | R25, R29, R45 |
| `evidence_sufficiency` | R26, R32 |
| `abstention` | R11, R26, R32 |
| `prohibited_advice` | R35, R38~R41 |
| `multi_turn` | R47 |
| `provider_timeout` | R15, R18 |
| `provider_rate_limit` | R16 |
| `stale_data` | R11, R19 |
| `correction_disclosure` | R12 |
| `pattern_analysis_limit` | R41 |
| `user_isolation` | R49 |
| `conversation_restore` | R48~R50 |
| `watchlist_ownership` | R49, R52 |
| secret scan | R17 |
| clean deploy smoke | R20, R21 |
| architecture explanation review | R06, R07 |

---

# 9. 일일 위험 점검표

전체 위험을 매일 모두 재검토하지 않는다. Human Owner는 당일 Phase와 Task에 직접 관련된 **활성 위험 3~5개**를 선택해 점검한다.

개발 종료 전 매일 다음 항목을 확인한다.

- [ ] 오늘도 하나 이상의 end-to-end 질문이 작동하는가?
- [ ] 새로운 기능 때문에 기존 회귀 테스트가 깨지지 않았는가?
- [ ] 외부 API 실패가 전체 앱 실패로 이어지지 않는가?
- [ ] 다른 종목 문서가 섞이지 않는가?
- [ ] 모든 주요 답변에 근거 snippet과 locator가 있는가?
- [ ] 숫자·날짜·단위를 원문과 대조했는가?
- [ ] 근거가 부족할 때 보류하는가?
- [ ] 매수·매도·목표가 표현이 없는가?
- [ ] 사용자가 첫 화면에서 핵심을 이해할 수 있는가?
- [ ] P1·P2 작업이 P0 안정화를 방해하지 않는가?
- [ ] 오늘 작성한 코드를 직접 설명할 수 있는가?
- [ ] 문서의 완료 상태와 실제 코드 상태가 일치하는가?

---

# 10. 최종 프로젝트 계획서 반영 규칙

최종 프로젝트 진행 계획서의 각 Step에는 반드시 다음을 포함한다.

1. 구현 목적
2. 입력과 출력
3. 선행 조건
4. 완료 기준
5. 대표 테스트
6. 주요 위험 ID
7. 예방 조치
8. 실패 시 fallback
9. 기능 제거 기준
10. 다음 Step 진입 조건

예시:

```text
Step M2-3: Evidence Sufficiency 구현

목적:
검색 결과가 답변에 충분한지 판단한다.

완료 기준:
complete / partial / provider_failed / no_evidence / blocked를 구분한다.

주요 위험:
R26, R29, R32

fallback:
판정 로직이 불안정하면 complete를 보수적으로 제한하고
근거 부족 질문은 고정 보류 응답으로 처리한다.

다음 Step 진입 조건:
low relevance·provider failure·wrong-company fixture가 통과한다.
```

---

# 11. 최종 결론

이 프로젝트의 가장 큰 위험은 개별 기술 부족보다 **넓은 P0 범위를 동시에 구현하다 핵심 흐름이 끝까지 안정화되지 않는 것**이다.

따라서 최종 계획서는 다음 원칙을 지켜야 한다.

```text
모든 Phase에서 동작하는 작은 전체 흐름을 유지
→ 각 기능에 테스트와 fallback을 함께 구현
→ P0 안정화 전 P1 금지
→ 일정 위험 시 기능 수보다 근거·정확성 보존
→ 불안정한 기능은 숨기고 안정된 MVP를 제출
```

로그인, 사용자별 세션, 이전 대화, 관심 종목은 실제 구현을 시도할 P1 기능이지만, P0 완료 조건을 통과하지 못하면 시작하지 않는다.

향후 계획 기능은 구조만 미리 만들지 않으며, 최종 발표에서 데이터·평가·안전성 조건과 함께 개선 방향으로 제시한다.
