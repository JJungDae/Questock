# Financial Capability Baseline

> 개정 기준일: 2026-07-21  
> 개정 사유: P0 지원 종목 확정과 공동 기사 Evidence 귀속 계약 정합성 보완  ; LiteLLM Python SDK + Gemini 단일 모델 경계 확정; 무료 등급 전송 정책과 M3 LLMStatus 계약 추가
> 근거 범위: 프로젝트 목표, 멘토링 방향, `REFERENCE_INDEX.md`, 1차 금융 레퍼런스, 최신 `IDEA_BACKLOG.md`  
> 목적: 모든 아이디어를 수용하는 거대한 구조를 만드는 것이 아니라, **선택된 기능을 추가하거나 포기해도 기본 금융 RAG 흐름이 흔들리지 않는 최소 계약**을 정의한다.  
> 기술 채택 상태: P0 LLM stack은 LiteLLM Python SDK + Gemini 단일 모델로 확정한다. LangGraph, vector DB, cloud, UI framework는 아직 확정하지 않는다.

## 1. 구조 설계 원칙

### 1.1 금융 요구사항을 먼저 정의한다

저장소나 프레임워크 구조를 기준으로 프로젝트를 설계하지 않는다.

먼저 다음을 정한다.

- 사용자가 어떤 종목을 묻는가
- 어떤 질문 의도인가
- 어떤 자료가 필요하고 실제로 확보되었는가
- 어떤 근거까지 답변에 사용할 수 있는가
- 근거가 부족할 때 어떻게 보류할 것인가
- 투자 조언으로 넘어가지 않도록 어떤 정책을 적용할 것인가

### 1.2 capability를 세 수준으로 구분한다

| 수준 | 의미 | 코드 반영 원칙 |
|---|---|---|
| `core_now` | 최종 차별화 아이디어와 무관하게 기본 금융 RAG에 반드시 필요한 기능 | 실제 코어 모델·인터페이스·테스트에 반영 |
| `extension_point` | 선택 가능성이 높은 기능을 별도 모듈로 붙이는 경계 | 연결 지점과 필요한 데이터 계약만 문서화. 미사용 class·빈 구현은 만들지 않음 |
| `idea_only` | 채택 가능성이 낮거나 데이터·평가가 준비되지 않은 기능 | 아이디어 문서에서만 관리. 코어 model·graph·DB schema에 반영하지 않음 |

### 1.3 코어 구조의 목표

코어의 목표는 다음이 아니다.

- 최신 IDEA_BACKLOG의 모든 아이디어 지원
- 모든 데이터 provider 지원
- 모든 질문을 하나의 agent가 처리
- 향후 가능성을 이유로 빈 class와 table을 미리 생성
- 기술지표·패턴 분석·백테스트를 금융 RAG 코어에 포함

코어의 목표는 다음이다.

```text
종목 식별
→ 질문 계획
→ 필요한 자료 조회 또는 검색
→ 근거 정규화
→ 근거 충분성 판단
→ 제한된 답변 생성
→ 정책·출처 검증
→ 응답
```

## 2. `core_now` — 현재 반드시 구현할 capability

### C01. 종목·법인 식별

회사명, 별칭, ticker를 canonical security로 변환한다.

필수 동작:

- 정식 종목명 exact match
- 6자리 ticker
- 자주 쓰는 별칭
- 보통주·우선주 구분
- 상장 security와 법인 `corp_code` 분리
- 후보가 여러 개면 확정하지 않고 재질문
- 지원 범위 밖 종목 안내
- 후속 질문에서 현재 종목 유지

### C02. 질문 의도와 자료 요구 계획

질문을 완전한 자연어 agent 계획으로 만들 필요는 없다. MVP에서는 다음 정보만 안정적으로 결정하면 된다.

- 대상 종목
- 질문 의도
- 기준 기간
- 필요한 자료 유형
- 추가 확인이 필요한지
- 답변을 생성하려면 필요한 최소 근거

초기 intent:

- `company_overview`
- `price_move_reason`
- `recent_issue`
- `disclosure_summary`
- `document_explanation`
- `financial_term`
- `risk_summary`
- `out_of_scope`
- `prohibited_advice`

### C03. 데이터 provider 경계

뉴스·공시·시세·사전 적재 문서를 서로 다른 provider 또는 repository 경계로 둔다.

코어가 요구하는 provider 공통 동작:

- canonical 종목 입력
- 기간 입력
- 정규화된 결과 반환
- 원문 ID·제목·날짜·`source_url`(있는 경우)과 재탐색 가능한 `locator` 보존
- 조회 기준 시각 반환
- cache 사용 여부 반환
- 오류 상태를 공통 코드로 변환

provider가 하지 않을 일:

- 최종 사용자 답변 생성
- 매수·매도 판단
- 근거 충분성 최종 판정
- 자유로운 추가 tool 호출

### C04. 공통 금융 문서 정규화

`FinancialDocument.source_type`은 최소한 다음 유형을 수용해야 한다.

- `news`
- `disclosure`
- `research_report`
- `glossary`

자료 수집 방식은 source type마다 달라도 된다.

- 뉴스와 공시는 API 또는 정기 수집기로 자동 수집할 수 있다.
- 리서치 리포트는 초기부터 복잡한 실시간 `ReportProvider`를 요구하지 않는다.
- 초기 리서치 리포트는 이용 조건을 확인한 자료를 수동 정규화하여 corpus에 적재하고, 일반 `Retriever`를 통해 검색할 수 있다.
- glossary도 검수된 수동 corpus로 시작할 수 있다.
- 자동 리포트 수집, PDF 표·그래프 파싱, OCR·layout 분석은 `extension_point`로 유지한다.

모든 원문을 하나의 거대한 schema로 만들 필요는 없다. 기본 검색과 출처 표시에 필요한 공통 필드만 코어로 둔다.

공통 필드:

- `document_id`
- `source_type`
- `provider`
- canonical security ID
- `title`
- `published_at`
- nullable `source_url`
- 비어 있지 않은 원문 `locator`
- text 또는 snippet
- ingestion/version 정보
- source별 추가 metadata

문서 정규화 규칙:

- `source_url`은 필수 필드가 아니라 `str | None`인 nullable 필드다.
- URL이 없더라도 `locator`는 비어 있으면 안 된다.
- `locator`만으로 원문 또는 내부 corpus에서 근거를 다시 찾을 수 있어야 한다.
- 로컬 절대 경로는 사용자 응답에 노출하지 않는다.
- 내부 파일은 `manifest_id`, `document_id`, `page` 등 안전한 locator를 사용한다.

locator 예시:

```text
news:
- source_url
- publisher
- published_at

disclosure:
- receipt_no
- source_url
- document_type
- section

research_report:
- manifest_id
- page
- publisher
- source_url 또는 access_note

glossary:
- corpus_id
- section
- version
```

공시·재무 문서에는 필요한 경우 metadata로 다음을 유지한다.

- `corp_code`
- `receipt_no`
- `document_type`
- `fiscal_year`
- `report_code`
- `consolidated_or_separate`
- `currency`
- `unit`
- `section`
- `page`
- `correction_status`
- `event_at` — source가 명시한 사건 발생 시각이 있을 때만
- `effective_at` — 공시·정책·계약 등의 효력 발생 시각이 있을 때만
- `market_session` — `pre_market`, `regular`, `after_hours`, `unknown` 등 source-specific 값

위 세 필드는 `FinancialDocument` core class의 필수 field나 범용 `Event` class로 만들지 않는다. 가격 원인 분석을 수행하는 source adapter가 제공할 수 있는 optional metadata 후보로만 관리한다.

이 필드를 모두 core class의 필수 property로 만들지는 않는다. source별 metadata validation에서 관리한다.

### C05. 검색과 근거 반환

retriever 종류보다 계약을 먼저 고정한다.

검색 요청:

- query
- canonical security ID
- source type
- 기간
- document type
- top-k

검색 결과:

- 근거 ID
- 문서 ID
- 짧은 snippet
- 제목·날짜·nullable `source_url`
- section·page·receipt number·manifest ID 등 비어 있지 않은 locator
- retrieval score
- 검색 방식
- 낮은 관련도 여부

필수 정책:

- 종목·source type·기간 hard filter를 similarity보다 먼저 적용
- 결과 0건과 낮은 관련도를 구분
- score만으로 답변 가능 여부를 결정하지 않음
- 원문을 확인할 locator를 항상 보존

### C06. 질문 유형별 근거 충분성

질문 유형마다 최소 근거를 정의한다.

| 질문 | 최소 근거 |
|---|---|
| “요즘 어때?” | 기준일이 있는 시세 또는 최근 자료 + 뉴스나 공시 중 하나 |
| “오늘 왜 올랐어?” | 실제 가격 방향·기준 시각 + 같은 기간 뉴스·공시. 인과는 후보로만 표현 |
| “공시 리스크 알려줘” | 대상 법인 확인 + 공시 제목·날짜 + receipt number·URL 등 locator + 관련 snippet |
| “PER이 뭐야?” | 검수된 금융 용어 자료 |
| “최근 위험 요인은?” | 동일 종목·최근 기간의 관련 문서와 직접 근거 문장 |

근거 일부가 실패하면:

- 확인 가능한 부분만 답변
- 누락된 자료 유형 명시
- 확정적 인과 표현 금지
- 핵심 근거가 없으면 답변 보류

### C07. 답변 정책

기본 RAG 응답에 반드시 필요한 정책:

- 직접 매수·매도·보유 지시 금지
- 목표가·미래 가격 예측 금지
- 자료에 없는 숫자·날짜·종목 생성 금지
- 뉴스와 주가 움직임의 인과를 자동 확정하지 않음
- 근거 부족 시 표현 강도 낮춤 또는 보류
- 기준 날짜 표시
- 짧은 근거와 원문 출처 제공
- 투자 자문이 아니라는 고지를 코드에서 일관되게 부착

### C08. 기본 검증

LLM 생성 뒤 최소한 다음을 확인한다.

- 답변에 다른 종목이 섞이지 않았는가
- 답변의 source ID가 실제 근거 목록에 존재하는가
- 금지된 투자 조언 표현이 있는가
- 원문에 없는 URL을 만들지 않았는가
- 근거 부족 상태인데 확정 표현을 사용하지 않았는가

숫자·단위의 정밀한 canonical metric 검증은 실제 실적 추세 기능을 선택할 때 extension으로 추가한다.

### C09. 멀티턴 종목 문맥

최소 session context:

- 현재 종목
- 현재 기준 기간
- 직전 질문 intent
- 직전 사용 source type
- 명시적 context reset

다음은 코어에 넣지 않는다.

- 장기 사용자 프로필
- 투자 성향
- 관심 종목 DB
- 소셜 관계
- 모든 과거 대화 원문

### C10. provider 오류와 fallback

상태는 서로 다른 책임 계층으로 구분한다.

Resolution 상태:

```text
resolved
ambiguous
not_found
unsupported
```

Provider 상태:

```text
ok
no_data
invalid_query
unauthorized
rate_limited
timeout
provider_unavailable
parse_error
```

Retrieval 상태:

```text
ok
empty
low_relevance
```

Evidence Decision 상태:

```text
complete
partial
provider_failed
no_evidence
blocked
```

적용 원칙:

- 종목 모호성은 `SecurityResolver`와 `ResolutionResult`가 처리한다.
- provider는 canonical security를 입력받으므로 종목 모호성을 다시 판정하지 않는다.
- `low_relevance`는 provider 오류가 아니라 retrieval 또는 evidence 판단에 사용되는 상태다.
- `no_data`, `provider_failed`, `low_relevance`는 서로 다른 의미로 유지한다.
- 이 구분은 책임과 응답 의미를 명확히 하기 위한 계약이며, 새로운 enum이나 class를 미리 구현하라는 뜻은 아니다.

fallback 우선순위:

1. 유효한 cache
2. 이미 적재된 자료
3. 정상 provider의 부분 근거
4. 근거·provider 부족 표시
5. 필요한 경우 재질문
6. 고정 template
7. Gemini·LiteLLM 장애 시 고정 오류 또는 보류 응답

P0에서는 다른 LLM으로 자동 전환하지 않는다. 모델 장애는 데이터 부재나 잘못된 종목을 해결하는 fallback이 아니다.

### C11. 기본 평가

초기부터 누적할 평가:

- 종목 resolution
- 질문 intent
- 필요한 provider 선택
- 검색 관련도
- 근거 충분성
- 근거 없는 확정 표현
- 금지된 투자 조언
- 멀티턴 종목 문맥
- provider timeout·no-data
- sync·stream 결과 일관성
- latency와 LLM 호출 수

### C12. LLM 호출 경계

P0 LLM stack:

```text
AnswerComposer
→ LLMClient
→ LiteLLM Python SDK
→ Gemini API
```

확정값:

- 기본 model: `gemini/gemini-2.5-flash`
- 사용 정책: Gemini API 무료 등급 우선
- 가용성: credential·AI Studio quota·live smoke 전까지 미검증
- 자동 billing·유료 fallback 금지
- 유료 모델 후보 검토: MVP end-to-end 완성과 Critical regression 이후
- credential: `GEMINI_API_KEY`
- model은 `LLM_MODEL` config로 주입
- LiteLLM Proxy·Router·자동 fallback·사용자 모델 선택은 사용하지 않음
- MVP 완성 전에는 유료 모델 비교·전환을 수행하지 않음
- Google Search Grounding은 자체 Evidence와 출처 정책을 섞지 않기 위해 사용하지 않음

무료 등급 전송 정책:

- 개인·기밀·민감정보, secret, 로컬 경로와 내부 로그 원문을 전송하지 않는다.
- 사용자 질문과 선택된 Evidence snippet만 최소 전송한다.
- 전체 세션 기록과 원문 파일 전체를 기본 전송하지 않는다.
- 리포트 manifest의 `external_llm_processing_allowed=true`인 자료만 LLM 입력에 포함한다.
- 허용 여부가 없거나 false인 리포트는 fixed template·비LLM 경로만 사용한다.
- 기존 `usage_note`에 외부 처리 허용 근거를 기록하며 별도 `usage_basis`를 만들지 않는다.
- P0에는 redaction pipeline을 만들지 않으므로 redaction이 필요한 자료는 외부 전송 금지로 처리한다.

`LLMClient` 책임:

- provider-neutral request 생성
- LiteLLM 호출
- Gemini 응답을 내부 `LLMResult`로 정규화
- timeout·rate limit·authentication·provider error mapping
- model·usage·latency·finish reason 기록
- raw provider 객체를 composer와 API 응답에 노출하지 않음

`LLMStatus`:

```text
ok
timeout
rate_limited
authentication_error
provider_unavailable
invalid_response
content_blocked
```

- 금융 데이터 `ProviderResult`와 분리한다.
- LLM 실패를 `missing_sources` 또는 `no_data`로 표현하지 않는다.
- Evidence가 유효하면 fixed template를 우선한다.
- content safety block과 parse/schema 실패를 구분한다.
- raw exception과 prompt 원문을 사용자에게 노출하지 않는다.

실행 설정:

```text
LLM_THINKING_BUDGET
LLM_MAX_OUTPUT_TOKENS
LLM_TIMEOUT_SECONDS
```

- 동적 thinking 기본값을 사용하지 않는다.
- 0과 1024를 비교해 Critical·full golden·p95 latency를 통과하는 가장 작은 값을 pin한다.
- sanitized live smoke 전에는 Gemini live 연동 완료로 표시하지 않는다.

환각 통제:

- Evidence 목록 밖 사실·숫자·URL을 허용하지 않음
- structured output은 형식 보조일 뿐 사실성 증거가 아님
- Pydantic schema와 기존 종목·수치·citation·안전 validator를 반드시 통과해야 함
- parse 또는 의미 validation 실패 시 자유형 응답을 채택하지 않고 보류하거나 고정 template로 전환
- 모델 교체 시 Critical regression을 다시 통과해야 함

## 3. `core_now` — 최소 데이터 계약

### 3.1 `SecurityIdentifier`

```python
class SecurityIdentifier:
    market: str
    ticker: str
    security_name: str
    security_type: str
    corp_code: str | None
    corp_name: str
```

alias는 resolver 저장소에서 관리할 수 있으며 응답 모델에 항상 포함할 필요는 없다.

### 3.2 `QueryPlan`

```python
class QueryPlan:
    security: SecurityIdentifier | None
    intent: str
    date_range: DateRange | None
    required_sources: list[str]
    required_evidence: list[str]
    requires_clarification: bool
```

초기에는 규칙 기반으로 만들 수 있다. LLM planner는 필수 조건이 아니다.

### 3.3 `MarketSnapshot`

```python
class MarketSnapshot:
    security_id: str
    trading_date: date
    observed_at: datetime
    price: float
    previous_close: float
    change: float
    change_percent: float
    volume: int | None
    market_session: str
    currency: str
    source: str
```

이 계약은 가격 분석에 필요한 최소 데이터만 고정한다.

- 실제 상승·하락 여부
- 거래일
- 가격 변화량과 변화율
- 조회 기준 시각
- 뉴스·공시 공개 시각과 비교할 시장 세션

historical OHLCV, 기술지표, 과거 유사 차트, 백테스트, BUY/SELL 신호는 기존대로 `extension_point`에 유지한다.

### 3.4 `FinancialDocument`

```python
class FinancialDocument:
    document_id: str
    source_type: str
    provider: str
    primary_security_ids: list[str]
    mentioned_security_ids: list[str]
    title: str
    published_at: datetime | None
    source_url: str | None
    text: str
    locator: dict
    metadata: dict
    ingestion_version: str
```

### 3.5 `Evidence`

```python
class Evidence:
    evidence_id: str
    document_id: str
    source_type: str
    title: str
    source_url: str | None
    published_at: datetime | None
    subject_security_ids: list[str]
    mentioned_security_ids: list[str]
    scope: Literal["company_specific", "industry_common", "multi_company"]
    snippet: str
    locator: dict
    retrieval_score: float | None
```

문서와 Evidence의 종목 field는 다음을 구분한다.

- `primary_security_ids`: 문서가 직접 분석하는 회사
- `mentioned_security_ids`: 문서에서 언급된 지원 회사
- `subject_security_ids`: Evidence의 사실·수치가 직접 귀속되는 회사
- `industry_common`: 특정 회사 수치로 바꾸어 쓰지 않는 산업 공통 배경
- `multi_company`: 둘 이상의 회사 관계를 직접 서술한 Evidence

validation 불변조건:

### FinancialDocument

- primary/mentioned 합집합은 비어 있지 않아야 한다.
- 같은 `security_id`를 primary와 mentioned에 동시에 저장하지 않는다.
- 공동 분석 문서는 직접 분석 대상 모두를 primary에 둔다.
- 중심 회사와 단순 언급 회사를 primary와 mentioned로 분리한다.

### Evidence

- subject는 연결 문서의 primary/mentioned 범위 안에 있어야 한다.
- `company_specific`: subject가 정확히 1개여야 한다.
- `industry_common`: subject는 비어 있어야 한다.
- `multi_company`: subject가 2개 이상이어야 한다.
- subject와 mentioned에 같은 `security_id`를 중복 저장하지 않는다.
- 숫자 유무와 관계없이 company-specific 사실은 동일한 subject 규칙을 따른다.

P0 필터 규칙:

- 단일 종목 질문만 지원한다.
- company-specific은 target 종목이 subject에 있을 때만 허용한다.
- industry-common은 관련 배경으로만 허용하고 기업 고유 실적·점유율로 재서술하지 않는다.
- multi-company는 target 종목이 subject에 있을 때만 허용한다.
- 다른 지원 종목에만 귀속된 사실·수치는 제외한다.
- 주체가 불명확한 사실·수치는 답변에 사용하지 않는다.
- 직접 비교·우열 판단은 P0·P1과 현재 M5 기본 큐에서 제외하며 별도 승인 계획이 있을 때만 추가한다.

### 3.6 `ProviderResult`

```python
class ProviderResult[T]:
    status: str
    data: T | None
    error_code: str | None
    message: str | None
    fetched_at: datetime
    from_cache: bool
```

### 3.7 `RetrievalRequest`와 `RetrievalResult`

```python
class RetrievalRequest:
    query: str
    security_id: str
    source_types: list[str]
    date_range: DateRange | None
    document_types: list[str] | None
    top_k: int
```

```python
class RetrievalResult:
    evidence: list[Evidence]
    strategy: str
    low_relevance: bool
    diagnostics: dict
```

### 3.8 `SessionContext`

```python
class SessionContext:
    current_security_id: str | None
    current_date_range: DateRange | None
    previous_intent: str | None
    previous_source_types: list[str]
```

### 3.9 `FinancialAnswer`

```python
class FinancialAnswer:
    answer: str
    status: str
    security: SecurityIdentifier | None
    basis_date: datetime | None
    evidence: list[Evidence]
    warnings: list[str]
    missing_sources: list[str]
```

코어 응답은 자유 텍스트와 evidence를 안정적으로 연결하는 수준까지만 요구한다. 사실·해석·추론별 별도 claim 모델은 해당 차별화 기능이 선택된 후 extension에서 추가한다.

## 4. `core_now` — 최소 인터페이스

### 4.1 `SecurityResolver`

```python
class SecurityResolver(Protocol):
    async def resolve(
        self,
        query: str,
    ) -> ResolutionResult: ...
```

### 4.2 `QueryPlanner`

```python
class QueryPlanner(Protocol):
    async def plan(
        self,
        message: str,
        session: SessionContext,
    ) -> QueryPlan: ...
```

### 4.3 provider

```python
class MarketDataProvider(Protocol):
    async def snapshot(
        self,
        security: SecurityIdentifier,
        date_range: DateRange | None,
    ) -> ProviderResult[MarketSnapshot]:
        ...
```

```python
class NewsProvider(Protocol):
    async def search(
        self,
        security: SecurityIdentifier,
        date_range: DateRange,
        limit: int,
    ) -> ProviderResult[list[FinancialDocument]]: ...
```

```python
class DisclosureProvider(Protocol):
    async def list_documents(
        self,
        security: SecurityIdentifier,
        date_range: DateRange,
        document_types: list[str] | None,
    ) -> ProviderResult[list[FinancialDocument]]: ...
```

### 4.4 `Retriever`

```python
class Retriever(Protocol):
    async def search(
        self,
        request: RetrievalRequest,
    ) -> RetrievalResult: ...
```

### 4.5 `EvidencePolicy`

```python
class EvidencePolicy(Protocol):
    def evaluate(
        self,
        plan: QueryPlan,
        provider_results: list[ProviderResult],
        evidence: list[Evidence],
    ) -> EvidenceDecision: ...
```

### 4.6 `AnswerComposer`

```python
class AnswerComposer(Protocol):
    async def compose(
        self,
        plan: QueryPlan,
        evidence: list[Evidence],
        decision: EvidenceDecision,
    ) -> FinancialAnswer: ...
```

### 4.7 `AnswerValidator`

```python
class AnswerValidator(Protocol):
    def validate(
        self,
        plan: QueryPlan,
        answer: FinancialAnswer,
    ) -> ValidationResult: ...
```

## 5. `extension_point` — 기능 선택 후 추가할 경계

이 절의 기능은 코어 class, DB table, graph node로 미리 구현하지 않는다. 실제 최종 아이디어로 선택되었을 때 별도 package 또는 service로 붙인다.

### E01. 사실 요약 / 근거 기반 관점 mode

선택 시 연결 지점:

```text
EvidencePolicy
→ AnswerComposer
→ mode별 response formatter
```

필요 데이터:

- 동일한 core `Evidence`
- 근거 충분성
- source type
- 최신성
- 긍정·위험 근거 tag
- 불확실성

추가 계약:

- request의 optional `response_mode`
- mode별 output schema
- 관점 mode의 금지 표현 validator
- 사실 mode와 관점 mode의 사실 일치 test

코어에 미리 `Claim`, `Viewpoint`, `Score` model을 추가하지 않는다.

### E02. 사실·자료 해석·AI 추론 분리

선택 시 연결 지점:

```text
AnswerComposer
→ structured answer formatter
→ evidence reference validator
```

필요 데이터:

- 문장별 evidence reference
- source type
- 추론 표시
- 불확실성 표현

기능 선택 후에만 구조화 claim contract를 추가한다.

### E03. 실적 추세와 수치 검증

이 extension은 DART 정형 수치 또는 수동 정규화된 리서치 리포트 수치를 사용할 수 있다. 자동 PDF 표·그래프 파싱은 이 기능과 별도의 `report_ingestion` extension으로 둔다.

선택 시 별도 `financial_metrics` module을 추가한다.

연결 지점:

```text
DisclosureProvider 또는 FinancialDataProvider
→ metric normalizer
→ number validator
→ AnswerComposer
```

필요 데이터:

- canonical metric name
- value
- unit·currency
- period
- 연결·별도
- actual·estimate
- source locator

코어에 `FinancialMetric` table이나 모든 재무지표 enum을 미리 만들지 않는다.

### E04. 리서치 리포트 자동 수집·PDF 파싱

선택 시 별도 `report_ingestion` module을 추가한다.

연결 지점:

```text
리포트 source
→ downloader 또는 crawler
→ PDF/layout parser
→ 수치·표 검증
→ FinancialDocument(source_type="research_report")
→ corpus repository
→ Retriever
```

필요 조건:

- 이용·저작권·재배포 범위
- 외부 제3자 LLM 처리 허용 여부와 manifest의 `external_llm_processing_allowed`
- 증권사별 문서 형식
- PDF text·표·그래프 parsing 정확도
- parser version
- 원문 page locator
- 수치 검증 dataset
- 실패 문서의 수동 보정 절차

초기 코어에서는 수동 정규화 corpus로 대체한다.

### E05. 상충 뉴스·리포트 비교

선택 시 별도 `evidence_comparison` module을 추가한다.

연결 지점:

```text
Retriever 결과
→ topic/time/entity grouping
→ stance comparison
→ AnswerComposer
```

필요 데이터:

- 동일 종목
- 동일 사건 또는 topic
- 기간
- source
- 긍정·부정·중립 근거
- 공통 사실

기능을 선택했을 때 사용할 수 있는 optional metadata 후보:

- `content_hash`
- `duplicate_group_id`
- `event_tag`
- `original_source`

이 값들은 현재 core `FinancialDocument`의 필수 field나 범용 event model로 만들지 않는다. 뉴스 중복 제거·event grouping extension 내부에서만 검증하고 사용한다.

코어에 `ContradictionGroup` 같은 model을 미리 추가하지 않는다.

### E06. historical OHLCV

선택 시 `MarketDataProvider`의 별도 historical method 또는 별도 historical provider를 추가한다.

연결 지점:

```text
QueryPlan
→ historical market data adapter
→ 선택된 분석 service
→ evidence-compatible summary
→ AnswerComposer
```

필요 데이터:

- adjusted OHLCV
- market calendar
- split·dividend 보정
- interval
- timezone
- missing bar 정책

기본 RAG 검색과 분리한다.

### E07. 과거 유사 구간 분석

선택 시 독립 `pattern_analysis` service로 둔다.

연결 지점:

```text
historical OHLCV provider
→ pattern_analysis service
→ 제한된 분석 summary
→ AnswerComposer의 extension payload
```

필요 데이터와 평가:

- 분석 window
- 정규화 방식
- 유사도 방식
- 과거 후보 구간
- 이후 수익률 분포
- sample count
- 데이터 누수 방지
- walk-forward test
- 거래비용·slippage 조건

코어에 다음을 넣지 않는다.

- `PatternMatchResult`
- 기술지표 전체 모델
- 백테스트 결과 모델
- BUY/SELL signal
- 미래 방향 field

### E08. 관심 종목·개인화

선택 시 별도 user feature module을 추가한다.

연결 지점:

- API authentication layer
- user preference repository
- answer display priority

core RAG 문서·graph와 결합하지 않는다.

### E09. 알림·이벤트 감시

선택 시 별도 scheduler와 notification service를 추가한다.

연결 지점:

- provider ingest log
- watchlist
- alert rule
- notification channel

코어에 범용 `Event` model이나 scheduler state를 미리 추가하지 않는다.

### E10. 관심 분야 종목 탐색

선택 시 별도 universe·industry mapping module을 추가한다.

필요 데이터:

- 산업·테마 taxonomy
- 종목과 사업의 근거 문서
- 종목 universe
- 탐색 결과의 추천 금지 정책

기본 사용자가 선택한 종목 RAG와 분리한다.

## 6. `idea_only` — 아직 구조에 반영하지 않을 기능

다음 기능은 최신 IDEA_BACKLOG에서 관리하되 현재 core model, graph, DB schema, API contract에 반영하지 않는다.

### 6.1 예측·매매 기능

- 오늘 또는 내일 오를 종목 직접 예측
- 목표가
- 매수·매도·보유 추천
- 손절·익절·진입 시점
- 유사 차트 기반 미래 방향 확정
- “아직 안 올랐으니 곧 오른다” 판단

### 6.2 데이터·평가 준비가 부족한 고난도 기능

최종 기능으로 선택되기 전까지 `idea_only`로 유지한다.

- 시장 전체 긍정 이벤트 미반응 종목 탐색
- 요일 효과
- 테마주 상대 미반응
- 장기 거시경제 인과 chain
- 5분봉 pattern 분석
- 전체 증권사 리포트 자동 표·그래프 parsing
- 실시간 시장 전체 ranking
- 기술지표 전체
- 범용 backtest engine

### 6.3 제품 범위를 크게 늘리는 기능

- 친구 관계와 수익률 공유
- 본격적인 소셜 투자 기능
- 복잡한 사용자 투자 성향 기반 개인화
- 여러 알림 channel
- 다중 LLM 사용자 선택 UI
- 자동 portfolio 관리

아이디어가 선택되면 먼저 데이터·평가·안전성 계획을 작성한 뒤 `extension_point`로 승격한다.

## 7. 코어 처리 흐름

```text
User Message
→ Input Policy
→ Security Resolver
→ Query Planner
→ Provider Calls / Document Retrieval
→ Evidence Normalization
→ Evidence Sufficiency Check
→ Answer Composer
→ Answer Validator
→ FinancialAnswer
→ Session Context Update
```

LangGraph가 없어도 이 흐름은 구현 가능해야 한다. 분기와 상태가 실제로 복잡해졌을 때 LangGraph 적용을 검토한다.

## 8. 단계별 데이터 범위와 완료 기준

### 8.1 초기 코어 검증

초기 코어 검증 단계에서는 **source 2종 이상**만으로도 다음 전체 흐름을 검증할 수 있다.

```text
수집 또는 적재
→ 정규화
→ 검색 또는 provider 조회
→ Evidence 생성
→ 근거 충분성 판단
→ 답변 생성
→ 출처·정책 검증
```

초기 코어 검증의 목적은 모든 자료 유형을 한 번에 자동화하는 것이 아니다. 다음을 먼저 확인한다.

- canonical 종목 식별
- source별 metadata
- 종목·기간·source filter
- evidence snippet과 원문 locator
- provider 오류와 low relevance 구분
- 근거 부족 보류
- 투자 조언 차단
- 멀티턴 현재 종목
- 기본 회귀 test

가능한 조합 예:

- 뉴스 + 공시
- 공시 + 수동 리서치 리포트 corpus
- 뉴스 + 수동 리서치 리포트 corpus

### 8.2 최종 프로토타입 목표

최종 프로토타입은 다음 **3종 금융 자료를 모두 지원**하는 것을 목표로 한다.

1. 뉴스
2. 공시
3. 리서치 리포트

세 자료를 모두 자동 수집할 필요는 없다.

- 뉴스: 선택한 API 또는 수집 방식
- 공시: OpenDART 또는 사전 적재
- 리서치 리포트: 수동 정규화 corpus로 시작 가능

리서치 리포트는 core에서 복잡한 실시간 `ReportProvider`를 요구하지 않는다.

```text
수동 확보·이용 조건 확인
→ 정규화 script
→ FinancialDocument(source_type="research_report")
→ corpus repository
→ Retriever
→ Evidence
```

최종 프로토타입 완료 기준:

- 삼성전자·SK하이닉스·현대자동차 3개 보통주
- 뉴스·공시·리서치 리포트 3종 조회 또는 검색
- `source_type`별 metadata와 원문 locator
- 질문 intent별 required source
- 종목·기간·source filter
- “왜 올랐어?”에서 실제 가격 방향과 자료 기반 배경 후보 구분
- 근거 snippet과 원문 출처
- 부분 자료·stale data·provider 오류 표시
- 근거 부족 보류
- 투자 조언 차단
- 멀티턴 현재 종목·기간
- 평가 taxonomy 기반 회귀 test
- 한 가지 명확한 실행·배포 방법

### 8.3 리서치 리포트 관련 `extension_point`

다음은 최종 프로토타입의 필수 코어가 아니다.

- 증권사 사이트 자동 crawler
- 실시간 리포트 API
- 자동 PDF table extraction
- graph·chart 의미 해석
- OCR·layout model
- 증권사별 parser
- 대량 리포트 갱신 scheduler

이 기능을 선택할 때 별도 `report_ingestion` extension으로 추가한다.

## 9. `lawHelp-agent` 역검증 기준

| 기준 | 확인 질문 |
|---|---|
| domain coupling | 법률 state·prompt·route 없이 추출 가능한가? |
| file reuse difficulty | 파일 전체를 재사용할 수 있는가, 작은 utility만 추출해야 하는가? |
| interface fit | core_now interface와 맞는가? |
| sync/SSE consistency | 같은 orchestration 결과를 공유할 수 있는가? |
| testability | 외부 API를 fake로 바꿔 실패 경로를 검증할 수 있는가? |
| observability | security·provider·evidence metadata를 추가할 수 있는가? |
| external licensing | 사용 라이브러리와 데이터 이용 조건을 별도로 확인했는가? |

팀 공동 코드의 재사용 허락은 확인된 전제로 두며 다시 조사하지 않는다.

## 10. 기술 채택 상태

### 확정

- Google Gemini API
- LiteLLM Python SDK
- `LLMClient` provider-neutral boundary
- 기본 model `gemini/gemini-2.5-flash`
- Gemini API 무료 등급 우선 사용, live smoke 전 가용성 미검증
- 유료 모델 전환은 MVP 완성 이후 별도 승인
- `GEMINI_API_KEY`
- 단일 모델, 자동 fallback 없음

### 아직 확정하지 않음 또는 P0 제외

- LangGraph
- ReAct
- Chroma, FAISS, pgvector
- Supabase
- keyword 또는 hybrid retrieval
- reranker
- LiteLLM Proxy·Router
- Langfuse
- React 또는 Streamlit
- GCE
- multi-LLM routing·사용자 모델 선택
- persistent user profile
- pattern analysis

## 11. 로컬 구현 에이전트용 체크리스트

- [ ] `core_now`, `extension_point`, `idea_only`를 혼합하지 않는다.
- [ ] 코어에는 현재 사용되는 class와 field만 만든다.
- [ ] 법인과 상장 security를 분리한다.
- [ ] provider가 최종 사용자 답변을 만들지 않게 한다.
- [ ] 종목·source type·기간 hard filter를 적용한다.
- [ ] 모든 근거에 원문 locator를 둔다.
- [ ] 근거 부족과 provider 장애를 구분한다.
- [ ] 답변의 종목·citation·정책을 검증한다.
- [ ] `FinancialMetric`, structured claim, pattern result는 기능 선택 후 추가한다.
- [ ] `PatternMatchResult`, `ContradictionGroup`, 범용 `Event`, 모든 기술지표·백테스트 model을 코어에 만들지 않는다.
- [ ] extension은 연결 지점과 데이터 요구만 먼저 문서화한다.
- [ ] 선택하지 않은 아이디어를 graph node·DB table·API field로 미리 만들지 않는다.
