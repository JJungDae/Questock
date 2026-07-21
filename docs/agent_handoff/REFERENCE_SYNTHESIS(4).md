# Reference Synthesis

> 작성일: 2026-07-20  
> 분석 범위: `REFERENCE_INDEX.md`에 지정된 1~3차 GitHub 레퍼런스  
> 목적: 특정 저장소를 그대로 선택하지 않고, 전체 레퍼런스에서 반복 확인된 공통 패턴·반면교사·extension 후보를 종합한다.  
> 실행 여부: 저장소별 정적 코드 분석을 수행했으며 README의 성능·배포 수치는 직접 재현하지 않았다.  
> 기술 선택 상태: 최종 framework, vector DB, agent framework, LLM, cloud는 확정하지 않는다.

## 1. 최종 결론

전체 레퍼런스에서 가장 일관되게 확인된 결론은 다음이다.

### 1.1 금융 RAG의 핵심은 agent framework가 아니다

기본 품질을 결정하는 요소는 다음이다.

1. 올바른 종목·법인 식별
2. 뉴스·공시·리서치 리포트의 source 역할 분리
3. 종목·기간·자료 유형 metadata
4. 검색된 근거의 원문 locator
5. 질문별 필요한 근거의 충분성
6. 근거가 부족한 경우의 보류
7. 가격·뉴스·공시의 시간 정합성
8. 투자 조언과 예측을 제한하는 정책
9. 실제 답변과 citation의 연결 검증
10. provider 장애와 자료 없음의 구분

LangGraph, ReAct, multi-agent, vector DB 종류는 이 조건을 구현하는 수단이다.

### 1.2 하나의 저장소를 기준 architecture로 사용할 수 없다

각 저장소의 장점은 서로 다른 계층에 있다.

- StockPilot: 질문별 provider completeness와 투자 정책
- OpenDartReader·Korean DART MCP: OpenDART provider
- SEC Insights: document metadata와 code-built citation
- PDF Assistant RAG: PDF page/table traceability와 hybrid retrieval
- FinanceRAG: company→document→section schema와 low-result 흐름
- lawHelp-agent: FastAPI·SSE·retry·observability·test·CI/CD utility
- FinRobot: report output structure와 deterministic number / LLM narration 원칙
- Deep RAG: multi-agent 도입 조건과 tool-call budget 사례

따라서 저장소 단위가 아니라 **interface·utility·evaluation pattern 단위**로 참고해야 한다.

### 1.3 초기 코어와 최종 프로토타입을 구분해야 한다

초기 코어 검증:

- source 2종 이상
- 수집·적재 → 검색·provider → evidence → 답변 → validation 전체 흐름
- 3~5개 지원 종목
- 기본 evaluation taxonomy

최종 프로토타입:

- 뉴스
- 공시
- 리서치 리포트

세 자료를 지원한다.

세 자료의 수집을 모두 자동화할 필요는 없다. 리서치 리포트는 수동 정규화 corpus로 시작할 수 있다.

## Reference Confidence Matrix

아래 확인 수준은 기존 1~3차 정적 분석에서 실제로 열람한 범위를 뜻한다. 저장소 실행 성공, 배포 상태, README 성능 수치의 재현을 새로 주장하지 않는다.

| 레퍼런스 | 확인 수준 | 확인 제약 | 우리 프로젝트 사용 수준 |
|---|---|---|---|
| lawHelp-agent | 실제 주요 코드 확인 | 실행·배포·README 테스트 및 threshold 수치 미재현 | FastAPI·SSE·retry·observability·test·CI/CD utility 선별 재사용 후보 |
| StockPilot | 실제 주요 코드 확인 | 실행하지 않았고 README 정확도·latency·테스트 통과 수 미재현 | 경쟁 기준, provider completeness와 투자 정책 참고, 구조 종속은 제외 |
| OpenDartReader | 실제 주요 코드 확인 | OpenDART 실호출·전체 endpoint·현재 HTML 호환성 미검증 | DART provider adapter와 corp code cache 참고 |
| Korean DART MCP | 실제 주요 코드 확인 | 모든 15개 tool을 같은 깊이로 보지 않았고 live test·README 수치 미재현 | 종목·법인 식별, 공시 wrapper, correction·error 처리 참고; MCP 전체 도입 제외 |
| SEC Insights | 실제 주요 코드 확인 | frontend·전체 test·배포·관측성 동작 및 평가 결과 미확인 | citation schema, document metadata, 정형·비정형 경계 참고 |
| PDF Assistant RAG | 실제 주요 코드 확인 | 전체 제품 stack·운영 성능 미재현, 금융 metadata는 별도 보강 필요 | PDF page·bbox traceability, 수동 corpus ingest, hybrid retrieval 참고 |
| FinanceRAG | 실제 주요 코드 확인 | endpoint·test suite·README 성능 미재현, filtering·context 결함 존재 | company→document→section schema와 low-result 흐름 참고, 결함은 반면교사 |
| News Sentiment | 핵심 코드 접근 불가 | notebook·dataset이 Git LFS pointer여서 구현·평가·중복 처리 검증 불가 | sentiment·event grouping 아이디어와 negative case만 참고 |
| RAG Financial Chatbot | 부분 코드 확인 | README와 실제 요청 경로 차이, citation·주가·forecasting 주장 미검증 | README-구현 불일치와 data overwrite 위험의 반면교사 |
| FinRobot | 부분 코드 확인 | 대규모 codebase 중 보고서·도구 분리·agent 비용 관련 부분만 선택 검토 | report section 구조와 deterministic number / LLM narration 분리 아이디어 |
| Deep RAG | 부분 코드 확인 | 일부 orchestrator·retrieval·prompt만 확인, runtime budget enforcement와 README 평가 수치 미검증 | multi-agent 도입 조건, tool-call budget, 복잡도 비용 참고 |

## 2. 권장 시스템 경계

전체 레퍼런스를 종합한 최소 흐름은 다음이다.

```text
User Message
→ Input Policy
→ Security Resolver
→ Query Planner
→ Provider Calls / Document Retrieval
→ Evidence Normalization
→ Evidence Sufficiency Policy
→ Answer Composer
→ Answer Validator
→ FinancialAnswer
→ Session Context Update
```

### 2.1 framework 독립성

이 흐름은 일반 Python service로도 구현할 수 있어야 한다.

LangGraph가 필요한 조건:

- route가 실제로 여러 갈래로 늘어남
- provider 호출과 검증을 state로 추적해야 함
- retry·partial result·human review가 graph로 명확해짐
- 일반 함수보다 graph가 설명과 test를 단순하게 만듦

단순히 “agent를 사용했다”는 이유로 graph를 도입하지 않는다.

### 2.2 agent 사용 경계

결정 가능한 질문:

- “최근 공시 요약”
- “오늘 왜 올랐어?”
- “이 리포트 핵심”
- “PER이 뭐야?”

은 required source와 workflow를 코드가 정할 수 있다.

자유 agent 후보:

- 여러 기업·여러 해·여러 관점의 장문 report
- 독립적으로 병렬 가능한 여러 research task
- tool 선택을 고정하기 어려운 deep research

agent를 채택하더라도 호출 상한과 evidence requirement가 필요하다.

## 3. 금융 자료 전략

### 3.1 최소 source type

`FinancialDocument.source_type`:

- `news`
- `disclosure`
- `research_report`
- `glossary`

### 3.2 뉴스

core 요구:

- canonical security
- title
- published_at
- nullable `source_url` — 뉴스는 보통 URL을 사용한다.
- 비어 있지 않은 locator — URL과 publisher·published_at 등으로 구성한다.
- publisher
- text/snippet
- fetched_at
- relevance

optional extension metadata:

- `event_at`
- `market_session`
- `content_hash`
- `duplicate_group_id`
- `event_tag`
- `original_source`

뉴스 sentiment와 event grouping은 core 필수 기능이 아니다.

### 3.3 공시

core 요구:

- corp code
- ticker/security relation
- report title
- receipt number
- received/published date
- nullable `source_url` — DART는 보통 receipt number와 원문 URL을 함께 사용한다.
- document type
- final/correction status
- receipt number·section 등 비어 있지 않은 text locator

`Korean DART MCP`와 `OpenDartReader`는 provider 참고 자료지만 entity ambiguity·retry·429는 wrapper에서 보완해야 한다.

### 3.4 리서치 리포트

초기 방식:

```text
이용 조건 확인
→ PDF·text 수동 확보
→ manifest 작성
→ 정규화
→ corpus repository
→ Retriever
```

manifest 후보:

- document ID
- ticker
- publisher
- title
- published_at
- nullable `source_url` 또는 `access_note`
- manifest ID와 page 등 사용자에게 제시할 안전한 locator
- local path — 내부 관리 필드로만 사용하며 최종 사용자에게 직접 노출하지 않는다.
- file hash
- usage note
- parser version

자동 crawler, 증권사별 parser, PDF graph 해석은 extension이다.

### 3.5 glossary

검수된 작은 corpus로 시작할 수 있다. 일반 금융 지식을 LLM이 즉석에서 생성하는 것보다 source와 version을 관리하는 편이 적합하다. glossary citation은 URL이 없어도 `corpus_id`, `section`, `version`으로 재탐색 가능해야 한다.

## 4. 종목·법인 식별 패턴

### 4.1 공통 요구

- company name
- common alias
- six-digit ticker
- security type
- corp code
- corporation name
- supported universe
- ambiguity candidates

### 4.2 참고할 패턴

Korean DART MCP:

- OpenDART corp dump
- SQLite cache
- stock code·corp code 분리
- exact·prefix·listed ordering

StockPilot:

- user-friendly alias
- preferred/common stock handling 경험
- session ticker

### 4.3 반면교사

- `search(..., 1)[0]`
- partial first match
- file name을 company identity로 사용
- embedding이 회사명을 알아서 구분할 것으로 기대
- provider마다 alias dictionary 중복
- 법인과 상장 security를 같은 ID로 사용

### 4.4 결론

`SecurityResolver`는 provider 밖의 공통 core module이어야 한다. provider는 canonical security를 입력받는다.

## 5. 시간 정합성 패턴

“왜 올랐어?” 품질은 sentiment model보다 시간 정합성에 더 직접적으로 의존한다.

### 5.1 필요한 시각

- 가격 변화 기준 시각
- news `published_at`
- disclosure receipt/publication time
- optional `event_at`
- optional `effective_at`
- optional `market_session`

복잡한 범용 `Event` class를 만들 필요는 없다. source-specific metadata와 evaluation으로 시작한다.

### 5.2 답변 구분

1. 확인된 가격 움직임
2. 가격 움직임 전 공개된 자료
3. 가격 움직임 중 공개된 자료
4. 가격 움직임 뒤 공개된 후속 배경
5. 사건 발생 시각은 빠르지만 기사 공개가 늦은 경우
6. 시간 정보가 없어 인과를 확정할 수 없는 경우

### 5.3 반면교사

- 같은 날짜라는 이유로 인과관계 확정
- 장후 기사를 장중 상승 원인으로 사용
- 가격 움직임 후 공시를 선행 원인으로 사용
- historical corpus를 현재 원인으로 사용
- timezone과 market session 누락

## 6. 뉴스 중복·독립성·상충 자료

### 6.1 핵심 원칙

기사 수는 독립 근거 수가 아니다.

같은 보도자료·원문을 여러 매체가 재배포하면 하나의 원출처 cluster로 취급해야 한다.

### 6.2 extension 후보

뉴스 비교 기능을 선택할 때:

- normalized URL
- content hash
- title/body similarity
- original source
- duplicate group
- event tag
- publish/update time
- entity list
- stance

를 사용할 수 있다.

이 field를 core schema에 의무화하지 않는다.

### 6.3 상충 의견 응답

```text
공통 사실
긍정 근거
위험 근거
독립 source 수
중복·파생 source
불확실성
추가 확인 조건
```

단순 positive/negative 기사 수 다수결은 사용하지 않는다.

### 6.4 뉴스 sentiment 결론

3차 뉴스 sentiment 저장소는 notebook·dataset이 Git LFS pointer라 dedup·event grouping·평가 code를 검증할 수 없었다.

sentiment는 채택 시:

- retrieval 보조
- view tag
- evaluation feature

로만 사용하고, price cause·future return·buy/sell signal로 사용하지 않는다.

## 7. 문서 ingest·metadata·traceability

### 7.1 가장 강한 공통 pattern

```text
source document
→ stable document ID
→ source-specific metadata
→ page/section/table extraction
→ stable chunk ID
→ retrieval
→ Evidence
```

### 7.2 page·chunk traceability

PDF Assistant RAG에서 유용한 field:

- document ID
- chunk index
- page
- bbox
- chunk type
- table index
- OCR flag
- extraction method

SEC Insights에서 유용한 field:

- document ID
- page
- score
- citation text
- filing metadata

### 7.3 금융 source metadata

generic PDF assistant의 filename·page만으로는 부족하다.

- security
- source type
- title
- publisher
- published date
- nullable `source_url`
- source별 비어 있지 않은 locator
- fiscal period
- correction
- parser version

을 adapter에서 추가한다.

### 7.4 source-specific parser

- SEC Item parser: 미국 SEC source extension
- DART HTML/XBRL parser: 국내 공시 extension
- research PDF table/OCR parser: report ingestion extension

source-specific parser를 공통 금융 core에 넣지 않는다.

## 8. retrieval 공통 패턴

### 8.1 hard filter가 먼저다

추천 순서:

1. security
2. source type
3. period
4. document type
5. retrieval
6. score·coverage
7. evidence sufficiency

### 8.2 retrieval 후보

레퍼런스에서 확인한 방식:

- FAISS dense
- Chroma dense
- PostgreSQL/pgvector
- Weaviate BM25+dense hybrid
- Qdrant dense+sparse
- RRF
- cross-encoder reranking
- query rewrite
- document-specific retriever

### 8.3 기술 선택 전 비교

초기 corpus에서 평가할 최소 실험:

- lexical only
- dense only
- hybrid
- hybrid+rerank

평가 subset:

- 정확한 회사명·공시명
- 한국어 금융 용어
- 표 수치
- 긴 리포트의 section
- 비슷한 기업 문서
- low relevance
- multi-document comparison

### 8.4 반면교사

- global top-k without metadata
- top-k를 항상 answer context로 사용
- retrieval score를 answer confidence로 표시
- filtering 후 generation에서 재검색
- query rewrite가 intent를 변경
- document별 agent tool을 entity resolver처럼 사용
- 여러 retrieval score scale을 그대로 비교

## 9. evidence·citation 공통 패턴

### 9.1 최소 Evidence

- evidence ID
- document ID
- source type
- title
- `source_url: str | None`
- published date
- snippet
- 비어 있지 않은 locator
- retrieval score

URL이 없어도 citation locator는 반드시 존재해야 한다. news는 보통 URL, DART는 receipt number와 URL, 수동 research report는 manifest ID와 page, glossary는 corpus ID와 section을 사용한다. 로컬 절대 경로는 최종 사용자에게 노출하지 않는다.

### 9.2 code-built citation

가장 좋은 pattern은 citation locator를 LLM이 자유 생성하지 않고 retrieval object에서 code로 만드는 것이다. `source_url`이 nullable이더라도 retrieval object의 source별 locator로 원문을 다시 찾을 수 있어야 한다.

SEC Insights:

- document ID
- page
- text
- score

PDF Assistant:

- filename
- page
- bbox
- score

Korean DART MCP:

- receipt number
- report title
- received date
- source document

### 9.3 citation과 support의 차이

citation이 존재해도 다음을 확인해야 한다.

- 같은 기업인가
- 같은 기간인가
- snippet이 claim을 지지하는가
- source가 오래되지 않았는가
- 정정 전 공시가 아닌가
- LLM이 숫자를 변경하지 않았는가

### 9.4 core와 extension

core:

- answer가 반환한 evidence ID 존재 여부
- 존재하는 `source_url`과 비어 있지 않은 locator 검증
- wrong-company 차단

extension:

- 문장별 claim-evidence
- entailment validator
- 사실·해석·추론 분리

## 10. evidence sufficiency와 abstention

### 10.1 필요한 상태

- `complete`
- `partial`
- `low_relevance`
- `provider_failed`
- `no_evidence`
- `blocked`

### 10.2 tool completeness와 구분

price·news·disclosure tool을 모두 호출했더라도:

- 뉴스가 무관할 수 있음
- 공시가 없을 수 있음
- 가격 기준일이 다를 수 있음
- provider가 실패했을 수 있음

따라서 required tool call과 required evidence 충족은 다른 test다.

### 10.3 답변 policy

- complete: 근거 기반 설명
- partial: 확인된 부분과 missing source
- low relevance: 근거 부족 보류
- provider failed: 장애 명시와 부분 답변
- no evidence: 답변하지 않음
- blocked: 투자 조언·예측 거절

## 11. 답변 구조와 report extension

### 11.1 기본 chat response

- 종목
- 기준 날짜
- 핵심 설명
- 확인된 사실
- 가능한 배경
- 위험·불확실성
- evidence card
- missing source
- warning

### 11.2 관점 mode extension

동일 Evidence 뒤에서 composer만 분리한다.

- 사실 요약
- 근거 기반 관점
- 긍정 요인
- 위험 요인
- 확인 조건

provider와 retriever를 mode별로 복제하지 않는다.

### 11.3 장문 report extension

FinRobot의 참고 pattern:

- section
- data source
- chart
- AI-generated marker
- report completeness validation

제외:

- investment recommendation
- target price
- 모든 질문에 장문 report
- section마다 별도 agent 호출

## 12. reliability·오류·cache

### 12.1 상태 계층

Resolution:

- `resolved`
- `ambiguous`
- `not_found`
- `unsupported`

Provider:

- `ok`
- `no_data`
- `invalid_query`
- `unauthorized`
- `rate_limited`
- `timeout`
- `provider_unavailable`
- `parse_error`

Retrieval:

- `ok`
- `empty`
- `low_relevance`

Evidence Decision:

- `complete`
- `partial`
- `provider_failed`
- `no_evidence`
- `blocked`

entity ambiguity는 provider 상태가 아니다. `SecurityResolver`가 resolution 결과를 확정한 뒤 canonical security를 provider에 전달한다. low relevance는 provider 장애가 아니며, required tool call 성공과 evidence sufficiency도 서로 다른 판정이다. `no_data`, `provider_failed`, `low_relevance`는 같은 상태로 합치지 않는다.

### 12.2 확인된 좋은 pattern

- Naver 429 retry·semaphore·cache
- DART timeout·corp code cache
- Korean DART MCP의 JSON/ZIP error 구분
- lawHelp의 LLM retry 상한과 mid-stream no-retry
- PDF Assistant의 ingest status·retry count·traceback
- SEC Insights의 failed message history 제외

### 12.3 반복된 실패

- requests timeout 없음
- all exception → empty list/None
- no-data와 provider error 혼합
- infinite or unbounded retry
- startup/import 시 external API 호출
- LLM fallback이 data 부족을 해결한다고 가정
- stale cache 표시 없음
- rate-limit을 document 없음으로 처리

## 13. multi-turn과 session

### core에 필요한 context

- current security
- current period
- previous intent
- previous source types
- reset

### 참고 pattern

- StockPilot thread 분리
- SEC Insights successful message history
- PDF Assistant persistent session
- lawHelp thread ID 전달

### 제외

- 모든 과거 대화 무제한 prompt
- 사용자 투자 성향
- 장기 profile
- filesystem research memory
- 관심 종목·소셜 기능

structured context를 먼저 만들고, raw history는 제한적으로 사용한다.

## 14. evaluation 종합

### 14.1 핵심 taxonomy

- entity resolution
- ambiguous security
- intent routing
- source selection
- price move reason
- conflicting sources
- multi-hop
- financial metric
- numeric accuracy
- citation support
- evidence sufficiency
- abstention
- prohibited advice
- multi-turn
- timeout
- rate limit
- stale data
- correction disclosure
- pattern analysis limit

### 14.2 저장소별 가장 유용한 평가 참고

| 평가 | 주요 reference |
|---|---|
| entity·correction | Korean DART MCP |
| provider behavior | OpenDartReader, StockPilot |
| citation schema | SEC Insights, PDF Assistant |
| low result | FinanceRAG |
| routing completeness | StockPilot |
| LLM retry·stream failure | lawHelp |
| PDF table/page | PDF Assistant |
| report structure | FinRobot |
| multi-agent budget | Deep RAG |
| sentiment·duplicate negative cases | News Sentiment repo |
| README/code mismatch | Fin-Rag, RAG Financial Chatbot |

### 14.3 평가 결과를 신뢰하는 조건

- test code 존재
- dataset 또는 fixture 존재
- expected result 존재
- 실행 가능한 dependency
- raw result 보존
- README 수치와 실행 결과 분리
- 실제 product path와 evaluation path 일치

## 15. `core_now` 구현에 참고할 패턴

다음은 저장소 구현을 직접 채택한다는 뜻이 아니다.

### domain·interface

- canonical security resolver
- provider protocol
- `FinancialDocument`
- `Evidence`
- `ProviderResult`
- query plan
- evidence policy
- answer validator

### data

- DART receipt and corp metadata
- page/section/chunk identity
- source-specific metadata
- correction/final version
- published/fetched time

### retrieval

- hard filter
- score와 raw evidence 반환
- empty/low relevance
- optional hybrid benchmark

### answer

- code-built source locator
- missing source
- basis date
- input/output policy

### reliability

- timeout
- retry cap
- cache status
- typed error
- test fake
- health
- CI

## 16. extension 선택 시 참고할 패턴

### research report ingestion

- manual manifest
- PDF page/table extraction
- OCR
- multi-column
- parser version
- numeric fixture

### conflicting source

- content hash
- duplicate group
- original source
- event tag
- independent perspective

### financial metrics

- deterministic normalize/calculate
- period·unit·scope
- source locator
- numeric validator

### multi-hop/report

- sub-question decomposition
- tool call budget
- section report
- AI disclosure
- source list

### historical analysis

- historical OHLCV provider
- separate analysis service
- sample count
- leakage prevention
- walk-forward evaluation

extension을 선택하기 전 빈 class·graph node·DB table을 만들지 않는다.

## 17. 반면교사 및 평가 사례

1. README의 기능 목록을 code로 간주
2. 라이선스 badge만 보고 재사용
3. 여러 기업 문서를 넣으면 entity resolution이 된다고 판단
4. metadata를 prose text 안에 넣음
5. raw chunk display를 citation으로 표현
6. tool 호출 성공을 evidence 충분으로 표현
7. similarity를 factual confidence로 표현
8. filtering 후 다시 검색
9. 동일 뉴스 재배포를 독립 근거로 계산
10. 기사 sentiment를 price cause로 사용
11. 가격 변화 뒤 공개된 자료를 선행 원인으로 사용
12. LLM으로 금융 숫자를 직접 계산
13. 직접 투자 전략·추천 prompt
14. startup 시 모든 외부 provider load
15. multi-agent 수를 고도화로 표현
16. generic QA sample을 금융 평가로 사용
17. 수동 입력 chart를 자동 금융 분석으로 표현
18. full-stack deploy를 core quality로 오해

## 18. lawHelp-agent 재사용 종합

재사용 권한은 확인된 전제다.

우선 후보:

- FastAPI app factory
- health
- CI
- LLM retry policy
- tracing sanitizer
- SSE serialization
- test fake

구조 참고:

- sync/SSE
- workflow
- lazy repository
- Docker ingest profile
- health-gated CD

전면 교체:

- 법률 state
- prompt
- metadata
- threshold
- route
- document schema
- ingest

금융 core 계약을 먼저 작성한 뒤 utility를 추출한다.

## 19. StockPilot 경쟁 기준 종합

StockPilot과 공통으로 필요한 최소 수준:

- ticker resolution
- news/disclosure/price/RAG role
- multi-turn ticker
- investment policy
- provider timeout/error
- required evidence
- regression test

따라 하지 않을 요소:

- positive-news screener
- multi-model UI
- multiple agent modes
- full ReAct default
- auth·interest portfolio 전체
- StockPilot structure에 맞춘 architecture

차별화 후보:

- temporal causal boundary
- independent news source grouping
- evidence sufficiency status
- citation support
- fact/interpretation/inference separation
- numeric validation
- research report corpus

## 20. 차트 패턴 분석 gap

전체 금융 RAG 레퍼런스 분석만으로는 다음에 대한 충분한 근거를 확보하지 못했다.

- historical OHLCV window normalization
- similarity metric comparison
- candidate period selection
- adjusted price
- market calendar
- leakage prevention
- walk-forward evaluation
- post-pattern return distribution
- transaction cost·slippage
- backtest reproducibility

FinRobot에는 quantitative·trading 기능이 있고 일부 저장소는 sentiment와 price를 연결한다고 주장하지만, 이를 “과거 유사 차트 구간 분석”의 검증 가능한 구현으로 사용할 수 없다.

따라서:

- 금융 RAG 레퍼런스만으로는 차트 패턴 분석 근거가 부족함
- 해당 기능이 최종 채택될 경우에만 별도 quant·time-series 레퍼런스 조사 필요
- feature가 선택되기 전에는 `PatternMatchResult`, 기술지표, backtest model을 core에 만들지 않음
- pattern 결과를 미래 방향·BUY/SELL로 표현하지 않음

## 21. 단계별 참고 map

### P0 — 요구사항·domain

- `FINANCIAL_CAPABILITY_BASELINE.md`
- StockPilot의 질문 role
- Korean DART entity
- SEC Insights metadata

### P1 — data·ingest

- OpenDartReader
- Korean DART MCP
- PDF Assistant
- FinanceRAG schema
- manual report manifest

### P2 — retrieval

- StockPilot metadata filter
- PDF Assistant hybrid
- SEC Insights document filter
- FinanceRAG low-result anti-pattern

### P3 — answer·evidence

- SEC Insights Citation
- PDF Assistant SourceChunk
- lawHelp output policy
- StockPilot evidence completeness

### P4 — session·API

- lawHelp FastAPI/SSE
- PDF Assistant session
- StockPilot ticker context

### P5 — evaluation

- taxonomy draft
- StockPilot endpoint evaluation
- lawHelp retry test
- Korean DART field tests
- PDF table/citation fixture

### P6 — infrastructure

- lawHelp CI/Docker/CD utility
- 필요한 최소 health·smoke
- data storage 선택 후 적용

### P7 — 선택 extension

- PDF report parser
- financial metric validator
- conflicting source grouping
- multi-hop report
- historical pattern analysis

## 22. 최종 구현 전 결정 목록

1. 지원 종목 3~5개
2. 뉴스 provider
3. 공시 API·적재 방식
4. 수동 research report corpus 목록
5. 자료 이용 조건
6. 첫 질문 taxonomy
7. “왜 올랐어?” MVP 포함 여부
8. financial metric extension 포함 여부
9. conflicting source extension 포함 여부
10. response mode
11. multi-turn persistence 수준
12. retrieval baseline
13. LLM과 embedding
14. DB·vector store
15. LangGraph 필요 여부
16. 배포 대상
17. 평가 문항 수와 pass 기준
18. chart pattern 기능 채택 여부

## 23. 로컬 구현 에이전트용 최종 체크리스트

- [ ] 저장소 전체를 복제하지 않는다.
- [ ] domain model과 protocol을 먼저 만든다.
- [ ] 2종 source로 core flow를 검증한다.
- [ ] 최종적으로 news·disclosure·research_report를 지원한다.
- [ ] report는 수동 corpus로 시작할 수 있다.
- [ ] security·period·source hard filter를 적용한다.
- [ ] price cause에 시간 선후관계를 검사한다.
- [ ] news duplicate와 independent source를 구분한다.
- [ ] citation을 code-built Evidence로 반환한다.
- [ ] tool completeness와 evidence sufficiency를 구분한다.
- [ ] data 없음과 provider 장애를 구분한다.
- [ ] LLM에 금융 수치 계산을 맡기지 않는다.
- [ ] 직접 투자 조언과 미래 예측을 차단한다.
- [ ] extension을 core에 미리 구현하지 않는다.
- [ ] multi-agent는 장문·병렬 research 요구가 있을 때만 검토한다.
- [ ] README 수치를 재현 전 확정하지 않는다.
- [ ] chart pattern을 선택하면 별도 quant reference를 조사한다.
