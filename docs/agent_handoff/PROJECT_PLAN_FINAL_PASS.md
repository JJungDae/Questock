# PROJECT_PLAN.md

> 작성일: 2026-07-20  
> 개정일: 2026-07-21  
> 개정 사유: P0 지원 종목 확정과 공동 기사 Evidence 귀속 계약 정합성 보완  
> 프로젝트: 증권 AI 투자 어시스턴트 프로토타입 개발  
> MVP 기준: **10개 작업 세션 × 세션당 약 5시간 = 약 50시간**  
> 목표 기간: **2주**  
> 확장 운영: 10개 MVP 세션을 조기에 완료하면 남은 기간 동안 `M5 확장 세션`을 순차 수행하며, 추가 세션 수에는 고정 상한을 두지 않는다.  
> 운영 원칙: 먼저 10개 세션 안에서 핵심 RAG를 안정화하고, 이후 P1-RAG 품질 → P1-User 기능 → 선택적 고도화 순서로 구현 수준을 높인다.  
> 기준 문서: `EXTENSION_COMPATIBILITY.md`, `RISK_RESPONSE_MATRIX.md`, `AGENT_WORKFLOW.md`, `FINANCIAL_CAPABILITY_BASELINE.md`, `EVALUATION_TAXONOMY_DRAFT.md`
> 범위 효력: 본 문서의 2주 활성 P0 결정은 이번 구현 회차의 공식 범위 기준으로 사용한다.

---

# 1. 프로젝트 목표

## 1.1 한 문장 목표

사용자가 선택한 주요 종목에 대해 최신 뉴스·공시·리서치 리포트를 검색하고, 근거와 한계를 명확하게 연결한 초보자 친화적 AI 답변을 제공하는 RAG 기반 프로토타입을 완성한다.

## 1.2 최종 시연 흐름

```text
지원 종목 선택 또는 질문 입력
→ 종목·법인 식별
→ 질문 의도와 필요한 자료 유형 결정
→ 뉴스·공시·리서치 리포트 조회·검색
→ 종목·기간·source hard filter
→ Evidence 생성과 근거 충분성 판단
→ 구조화 답변 생성
→ 숫자·출처·투자 조언 정책 검증
→ 핵심 요약·위험·불확실성·근거 UI 표시
```

## 1.3 필수 체크포인트 연결

### 체크포인트 1 — 최신 자료 기반 RAG API

완료 증거:

- 지원 종목의 canonical 식별
- 뉴스·공시·리서치 리포트 3종
- 질문별 source routing
- Evidence snippet과 원문 locator
- 자료 기준일과 최신성 경고
- provider 오류·자료 없음·검색 관련도 부족 구분
- 근거가 부족할 때 답변 보류
- 안정적인 단일 응답 API
- golden set과 회귀 테스트

### 체크포인트 2 — 명확하고 직관적인 UI

완료 증거:

- 핵심 요약을 첫 화면에 표시
- 사실·자료 해석·AI 추론 구분
- 긍정 요인·위험 요인·불확실성 표시
- 어려운 금융 용어 설명
- 기준일·누락 자료·provider 오류 표시
- 근거 상세 보기와 원문 연결
- 익명 세션의 멀티턴 종목 문맥 유지

### 체크포인트 3 — 핵심 가치 집중

완료 증거:

- 로그인 없이 질문→답변→근거 전체 시연 가능
- 시장 전체 종목·소셜·알림·차트 예측 미구현
- P0 완료 전 P1 시작 금지
- 범위 초과 시 기능 수보다 근거·정확성 보존
- 3개 종목의 안정적 MVP를 5개 종목의 불안정 MVP보다 우선

---

# 2. 최종 범위

## 2.1 기본 지원 범위

| 항목 | 기본 목표 | 확장 조건 |
|---|---|---|
| 지원 종목 | **3개 고정** | 5개 확대는 P1 이후 별도 검증 |
| 자료 유형 | 뉴스·공시·리서치 리포트 | 변경 없음 |
| 금융 용어 | 검수 glossary 15개 이상 | 시간 여유 시 30개 |
| 응답 방식 | 안정적인 sync 단일 응답 | streaming은 P2 또는 충분한 버퍼가 있을 때 |
| 세션 | 익명 현재 세션 멀티턴 | 로그인·영구 세션은 P1 |
| 배포 | 한 가지 재현 가능한 실행·배포 경로 | 다중 cloud·고가용성 제외 |
| 시장 범위 | 국내 상장 종목 3개 | 시장 전체 탐색 제외 |
| 언어 | 한국어 답변 | 해외 뉴스·다국어 분석 P3 |

## 2.2 확정 지원 종목과 선정 기준

M0의 지원 종목은 다음 3개 보통주로 확정한다.

| security_id | 회사명 | ticker | DART corp_code 후보 | P0 검증 목적 |
|---|---|---:|---:|---|
| `KRX:005930` | 삼성전자 | `005930` | `00126380` | 반도체 대형주와 다중 기업 기사 처리 |
| `KRX:000660` | SK하이닉스 | `000660` | `00164779` | 삼성전자와 같은 산업에서 Evidence·수치 귀속 검증 |
| `KRX:005380` | 현대자동차 | `005380` | `00164742` | 자동차·제조업 자료로 산업 다양성 검증 |

`corp_code`는 M1 resolver fixture 작성 전에 OpenDART corporation-code 원본으로 다시 검증한다.

선정 의도:

- 삼성전자와 SK하이닉스를 함께 지원해 동일 기사에 두 회사가 등장할 때 문장·수치 귀속을 검증한다.
- 현대자동차를 포함해 반도체 산업에만 편중되지 않도록 한다.
- P0 질문은 한 번에 하나의 종목을 대상으로 한다.
- 삼성전자와 SK하이닉스의 직접 비교·우열 판단은 P0·P1과 현재 M5 기본 큐에서 제외한다. 별도 데이터 계약·평가 fixture·Human Owner 승인이 있을 때만 새 계획으로 추가한다.
- 우선주와 해외 DR은 P0에서 지원하지 않는다.

선정 조건:

- ticker와 법인 식별이 명확함
- DART 공시가 충분함
- 최근 뉴스가 충분함
- 최근 리서치 리포트를 합법적으로 확보·정규화할 수 있음
- 서로 다른 산업 특성을 일부 포함하여 질문 유형을 검증할 수 있음
- 우선주·SPAC·관리종목처럼 resolver·데이터 해석이 복잡한 종목은 기본 3개에서 제외

2주 실행 기간에는 지원 종목을 3개로 고정한다.  
5개 확대는 새 종목마다 M1의 corpus·resolver와 M2의 retrieval·wrong-company 검증을 다시 수행해야 하므로 P1 이후 별도 작업으로 둔다.

## 2.3 P0 범위

### P0 코어

- `CORE01` 종목·법인 resolver
- `CORE02` 뉴스·공시·리서치 리포트 3종
- `CORE03` ProviderResult와 상태 계약
- `CORE04` 종목·기간·source hard filter
- `CORE05` retrieval baseline
- `CORE06` Evidence와 locator
- `CORE07` EvidencePolicy와 abstention
- `CORE08` 안정적인 단일 응답 API
- `CORE09` 외부 API fallback
- `CORE10` 실행·배포 경로

### P0 답변·UI·운영

- `A01` 초보자 쉬운 설명
- `A02` 사실·자료 해석·AI 추론 분리
- `A03` 핵심·긍정·위험·불확실성 카드
- `A04` 근거 강도와 보류
- `A05-M` 상충 자료 제한형
- `A06-M` 여러 자료 연결 제한형
- `A07-M` 기본 숫자·날짜·단위 검증
- `A08-M` 익명 세션 멀티턴
- `A10` glossary 기반 금융 용어 설명
- `A11` 질문 intent와 source routing
- `A12` 최신성·stale 경고
- `A13` 근거 요약과 원문 연결
- `A17-M` 문서 기반 사업 전망 제한형
- `A18` API 오류·한도·fallback
- `A19` token·context budget
- `A20-M` 최소 평가·회귀·관측
- `A23-M` 단일 안전 구조화 답변
- `SAFE01` 직접 투자 조언 차단
- `UI01` 핵심 흐름 중심 UI

## 2.4 2주 실행본의 후반 기능 범위

이 절은 2주 실행을 위한 공식 활성 P0 결정이다.

- `A15-M`: 기본은 P1. M1 데이터 gate를 통과하고 **M3 핵심 gate 이후 1개 전체 세션의 버퍼가 남을 때만** stretch P0로 활성화
- `A23-M`: P0 단일 안전 구조화 답변. 별도 mode toggle과 두 답변 모드는 `A23-H`로 분리하여 M5-06에서 구현
- `A17-M`: 독립 사업 전망 카드로 구현하지 않고 리서치 리포트 요약의 `확인된 계획·성장 조건·위험 조건·예정 이벤트` 항목으로 통합
- `A05-M`·`A06-M`: 별도 분석 시스템이나 graph node를 만들지 않고 AnswerComposer의 구조화 규칙과 validator acceptance criterion으로 최소 구현
- dense retrieval·Langfuse·streaming·5개 종목 확대: 2주 P0에서 제외

## 2.5 Stretch P0 후보

### `A15-M` 국내 자료 기반 상승·하락 배경

M1 종료 시까지 아래 데이터 조건을 통과하면 stretch 후보 자격을 얻는다. 실제 P0 활성화는 M3 핵심 gate 이후 1개 전체 세션의 버퍼가 남을 때만 확정한다.

- `MarketSnapshot` adapter 존재
- 가격·전일 종가·변동률·observed_at 반환
- timezone과 market session 확인
- 정상·no-data·timeout fixture 통과
- 뉴스·공시 `published_at`과 가격 시점 비교 가능

데이터 조건 또는 일정 버퍼 조건 중 하나라도 충족하지 못하면 P1으로 유지한다.

## 2.6 P1

### P1-RAG 품질

- 분기별 매출·영업이익·순이익 추세
- 수치 검증 고도화
- 상충 자료 자동 grouping
- 뉴스 중복 제거

### P1-User 기능

- 회원가입·로그인
- 사용자별 영구 대화 세션
- 이전 대화 목록·재열기
- 관심 종목 저장

M4 완료 후 어느 묶음을 먼저 시작할지 결정한다.

## 2.7 P2·P3·X

### P2

- 실시간에 가까운 갱신
- 관심 분야 정보 강조
- 제한된 산업 수혜 구조
- 시나리오 조건 카드

### P3

- 해외 뉴스
- 장기 거시 인과
- 자동 PDF 표·그래프 파싱
- 과거 유사 차트
- 시장 전체 스크리닝
- 정교한 투자 성향 개인화
- 알림·소셜 기능

### X

- 매수·매도·보유 추천
- 목표가·손절·익절 지시
- 오늘·내일 가격 방향 확정 예측
- 근거 없는 확률·순위·수익 보장

---

# 3. 기술 구조

## 3.1 기본 기술 선택

| 영역 | 기본 선택 | 이유 |
|---|---|---|
| 언어 | Python 3.11 이상 | 금융 데이터·RAG·FastAPI 생태계 |
| Backend | FastAPI + Pydantic | 명시적 API·schema·테스트 |
| Workflow | 일반 async Python service | LangGraph 없이 먼저 완성 |
| Retrieval | metadata hard filter + TF-IDF/BM25 계열 baseline | 작은 corpus에서 빠르고 설명 가능 |
| Dense retrieval | 2주 P0에서 제외 | lexical baseline 완료 후 P1 실험 |
| Metadata DB | SQLite | 3~5개 종목 프로토타입에 충분 |
| 문서 원본 | versioned JSON/Markdown + manifest | 리포트 수동 정규화와 locator 관리 |
| UI | Streamlit 기본 권장 | 2~3주 내 빠른 단일 화면 구현 |
| LLM | 단일 provider adapter | multi-provider routing 제외 |
| 관측 | 구조화 JSON log | 2주 P0에서는 Langfuse 미도입 |
| 테스트 | pytest + provider fake/fixture | 외부 API와 분리된 결정적 테스트 |
| 배포 | Docker Compose 또는 단일 Docker 이미지 1안 | 한 가지 실행 경로에 집중 |
| CI | GitHub Actions 최소 구성 | test·lint·secret scan 자동화 |

React/Vite 등 별도 프론트엔드는 기존 scaffold가 이미 있고 M0에서 추가 부담이 없다고 판단될 때만 선택한다. UI 선택 때문에 M1 시작이 지연되면 Streamlit으로 고정한다.

## 3.2 초기에는 도입하지 않는 기술

- 다중 agent orchestration
- LangGraph 필수화
- 복수 vector DB
- Kafka·Celery 등 분산 처리
- Kubernetes
- 자동 PDF OCR·표 추출
- 실시간 websocket 시세
- 다중 LLM provider routing
- 시장 전체 종목 검색 DB

## 3.3 권장 저장소 구조

```text
project/
├─ app/
│  ├─ api/
│  │  ├─ routes_chat.py
│  │  ├─ routes_health.py
│  │  └─ schemas.py
│  ├─ core/
│  │  ├─ models.py
│  │  ├─ status.py
│  │  ├─ resolver.py
│  │  ├─ planner.py
│  │  ├─ evidence_policy.py
│  │  ├─ composer.py
│  │  └─ validator.py
│  ├─ providers/
│  │  ├─ news.py
│  │  ├─ disclosure.py
│  │  ├─ market.py
│  │  └─ base.py
│  ├─ retrieval/
│  │  ├─ index.py
│  │  ├─ retriever.py
│  │  └─ filters.py
│  ├─ repositories/
│  │  ├─ documents.py
│  │  ├─ securities.py
│  │  └─ sessions.py
│  ├─ services/
│  │  └─ chat_service.py
│  └─ config.py
├─ ui/
│  └─ streamlit_app.py
├─ data/
│  ├─ securities.json
│  ├─ glossary.json
│  ├─ manifests/
│  ├─ reports/
│  └─ fixtures/
├─ scripts/
│  ├─ ingest_reports.py
│  ├─ build_index.py
│  └─ smoke_test.py
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  ├─ golden/
│  └─ fixtures/
├─ docs/
│  ├─ TASK_CARDS/
│  ├─ HANDOFFS/
│  └─ DECISIONS.md
├─ Dockerfile
├─ compose.yaml
├─ pyproject.toml
└─ README.md
```

---

# 4. 핵심 데이터 계약

## 4.1 반드시 먼저 고정할 모델

- `SecurityIdentifier`
- `QueryPlan`
- `MarketSnapshot`
- `FinancialDocument`
- `Evidence`
- `ProviderResult`
- `RetrievalRequest`
- `RetrievalResult`
- `SessionContext`
- `FinancialAnswer`

## 4.2 상태 계층

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

매핑 원칙:

- provider 장애를 `no_data`로 표현하지 않음
- `low_relevance`는 Retrieval 상태
- `low_relevance`는 EvidencePolicy에서 `partial` 또는 `no_evidence`로 변환
- 안전 정책 위반은 `blocked`
- required source 일부 실패는 `partial` 또는 `provider_failed`

## 4.3 다중 기업 문서의 최소 귀속 계약

삼성전자와 SK하이닉스가 같은 뉴스·리포트에 함께 등장할 수 있으므로 문서 관련성과 Evidence 주체를 분리한다.

`FinancialDocument` 최소 필드:

```text
primary_security_ids: list[str]
mentioned_security_ids: list[str]
```

`Evidence` 최소 필드:

```text
subject_security_ids: list[str]
mentioned_security_ids: list[str]
scope: company_specific | industry_common | multi_company
```

귀속 원칙과 validation 불변조건:

### FinancialDocument

- `primary_security_ids`와 `mentioned_security_ids`의 합집합은 비어 있지 않아야 한다.
- 동일 `security_id`를 두 필드에 중복 저장하지 않는다.
- 두 회사를 직접 분석하면 두 종목 모두 `primary_security_ids`에 둔다.
- 한 회사가 중심이고 다른 회사가 단순 언급이면 중심 회사는 `primary`, 다른 회사는 `mentioned`에 둔다.

### Evidence

- `subject_security_ids`는 연결된 FinancialDocument의 primary/mentioned 종목 범위 안에 있어야 한다.
- `company_specific`이면 `subject_security_ids`는 P0에서 정확히 1개여야 한다.
- `industry_common`이면 `subject_security_ids`는 비워 둔다.
- `multi_company`이면 `subject_security_ids`는 2개 이상이어야 한다.
- `mentioned_security_ids`와 `subject_security_ids`를 중복 저장하지 않는다.
- company-specific Evidence의 사실과 수치는 모두 동일한 대상 종목에 귀속되어야 한다.

### P0 필터

- `company_specific`: target `security_id`가 `subject_security_ids`에 있을 때만 허용한다.
- `industry_common`: target 종목과 관련된 배경으로만 허용하고 회사 고유 실적·점유율로 재서술하지 않는다.
- `multi_company`: target 종목이 `subject_security_ids`에 포함될 때만 허용한다.
- 주체가 불명확한 사실·수치는 P0 답변에 사용하지 않는다.
- P0에서 종목 간 우열·추천 결론을 생성하지 않는다.

## 4.4 locator 원칙

모든 Evidence는 다음 중 하나를 가져야 한다.

- 유효한 웹 URL
- DART receipt/document locator
- 리포트 manifest ID + page/section
- glossary entry ID + version

사용자 응답에 로컬 절대 경로를 노출하지 않는다.

---

# 5. 데이터 계획

## 5.1 종목별 최소 corpus coverage

M0에서 선택한 각 종목에 대해 M1 종료 시 다음을 목표로 한다.

| 자료 | 종목별 최소 목표 | 기준 |
|---|---:|---|
| 뉴스 | 중복 제거 후 10건 이상 | 최근 30일 우선 |
| 공시 | 5건 이상 | 최근 180일 + 최신 정기보고서 우선 |
| 리서치 리포트 | 2건 이상 | 최근 180일 우선, 수동 정규화 가능 |
| glossary | 전체 15개 이상 | 종목 공통 |
| MarketSnapshot | A15-M 승격 시 정상 fixture 2건 이상 | 상승·하락 각각 포함 |

최소 coverage를 만족하지 못하는 종목은 다른 후보로 교체하는 것을 우선한다.

삼성전자·SK하이닉스 공동 등장 문서 처리:

1. 문서 metadata에는 두 회사의 관련 여부를 기록한다.
2. chunk 또는 Evidence 단위에서 사실·수치의 실제 주체를 기록한다.
3. 회사명이 같은 문장에 명시된 숫자만 우선 귀속한다.
4. 인접 문맥으로만 추정되는 수치는 주체가 명확하지 않으면 제외한다.
5. 산업 공통 문장은 회사 고유 실적이나 점유율로 바꾸어 쓰지 않는다.
6. 동일 문서를 두 종목에서 재사용할 수 있지만, 질문 종목별 허용 Evidence는 별도로 필터링한다.

실제 시장 상황상 최근 공시가 5건 미만인 경우:

- 검색 기간을 최대 365일까지 확대
- UI에 기준 기간을 명시
- 자료가 부족하다는 경고 표시
- 없는 자료를 채우기 위해 무관 공시를 포함하지 않음

## 5.2 freshness 기본값

| 질문·자료 | 기본 조회 기간 | stale 또는 제한 표시 |
|---|---|---|
| 최근 이슈·뉴스 | 최근 30일 | 가장 최신 supporting news가 14일 초과면 경고 |
| 오늘 상승·하락 배경 | 당일 + 직전 거래일 이후 | 당일 가격 snapshot이 없으면 답변 보류 |
| 공시 요약 | 최근 180일 | 최신 유효 공시 날짜 표시 |
| 사업 전망·리포트 | 최근 180일 | supporting report가 180일 초과면 경고 |
| 금융 용어 | versioned glossary | 날짜보다 glossary version 표시 |
| 실적 추세 P1 | 최근 4개 분기 | 기간·연결/별도·actual/estimate 표시 |

사용자가 기간을 명시하면 사용자 기간을 우선한다.

## 5.3 리서치 리포트 정규화 schema

```json
{
  "document_id": "report-...",
  "primary_security_ids": ["KRX:005930"],
  "mentioned_security_ids": [],
  "source_type": "research_report",
  "provider": "manual_manifest",
  "title": "...",
  "published_at": "...",
  "source_url": null,
  "locator": {
    "manifest_id": "...",
    "page": 3,
    "section": "투자포인트"
  },
  "text": "...",
  "metadata": {
    "publisher": "...",
    "analyst": "...",
    "usage_note": "...",
    "file_hash": "..."
  },
  "ingestion_version": "v1"
}
```

## 5.4 provider fallback

| provider | 정상 경로 | 1차 fallback | 최종 fallback |
|---|---|---|---|
| 뉴스 | live search | cache 또는 recorded fixture | missing source 경고·보류 |
| 공시 | DART adapter | 최근 적재 공시 | missing source 경고·보류 |
| 리포트 | 수동 corpus | 이전 ingestion version | stale 경고 |
| 시세 | MarketSnapshot provider | 짧은 TTL cache | A15-M 보류 또는 P1 이동 |

---

# 6. API·성능·예산 기준

## 6.1 API endpoint

### 필수

```text
GET  /health
GET  /api/securities
POST /api/chat
POST /api/session/reset
```

### 선택

```text
GET /api/evidence/{evidence_id}
```

리포트 ingest와 index build는 사용자 API가 아니라 CLI script로 실행한다.

## 6.2 `/api/chat` 입력

```json
{
  "message": "삼성전자 최근 위험 요인 알려줘",
  "session_id": "anonymous-uuid"
}
```

## 6.3 `/api/chat` 핵심 출력

```json
{
  "status": "complete",
  "security": {},
  "basis_date": "...",
  "answer_sections": {
    "summary": "...",
    "facts": [],
    "interpretation": [],
    "inference": [],
    "positive_factors": [],
    "risk_factors": [],
    "uncertainty": []
  },
  "evidence": [],
  "warnings": [],
  "missing_sources": [],
  "diagnostics_public": {
    "freshness": "...",
    "evidence_strength": "..."
  }
}
```

## 6.4 timeout·retry·cache 기본값

| 항목 | 초기값 |
|---|---:|
| provider 개별 timeout | 8초 |
| provider retry | 최대 1회 |
| 전체 chat request 상한 | 20초 |
| retry 대상 | timeout·일시적 5xx·Retry-After가 짧은 429 |
| 뉴스 cache TTL | 15분 |
| 공시 cache TTL | 60분 |
| MarketSnapshot cache TTL | 1분 |
| 수동 리포트 | ingestion version이 바뀔 때까지 |
| 무한 재시도 | 금지 |

429에서 `Retry-After`가 전체 요청 상한을 넘으면 재시도하지 않고 cache 또는 partial response로 전환한다.

### 6.4.1 병렬 호출과 전체 deadline

- required provider는 서로 의존하지 않는 경우 `asyncio.gather` 등으로 병렬 호출한다.
- 각 provider timeout은 전체 20초 request deadline의 남은 시간을 넘을 수 없다.
- retry도 전체 deadline 안에서만 허용한다.
- 남은 시간이 retry timeout보다 짧으면 재시도하지 않고 cache·partial·provider_failed로 전환한다.
- 하나의 provider 실패가 다른 provider 결과 반환을 막지 않는다.
- 수동 리포트 corpus와 glossary는 외부 API 대기 없이 즉시 조회한다.

## 6.5 retrieval·LLM 예산

| 항목 | 초기값 |
|---|---:|
| retrieval top-k | 6 |
| source별 최대 Evidence | 3 |
| 답변에 전달할 Evidence | 최대 6 |
| Evidence snippet | 항목당 약 500~800자 |
| 총 context 기본 제한 | `max_context_tokens = 3000` |
| tokenizer 미사용 fallback | `max_context_chars = 4500` |
| 한 요청의 LLM 호출 | 최대 2회 |
| router | 규칙 기반 우선, LLM 호출 없음 |
| composer | 1회 |
| validator | 규칙 기반 우선, 필요한 경우에만 LLM 1회 |

top-k·threshold는 M2 golden fixture 결과에 따라 config로 조정한다. 모델별 score를 다른 모델의 threshold와 공유하지 않는다.

## 6.6 성능 목표

| 조건 | 목표 |
|---|---|
| cache·수동 corpus 중심 요청 | p95 10초 이내 |
| live provider 포함 요청 | p95 20초 이내 |
| 무한 대기 | 0건 |
| provider 일부 실패 | 전체 500이 아니라 partial·보류 응답 |
| 다른 종목 Evidence | 0건 |
| 가짜 URL·locator | 0건 |

---

# 7. UI 계획

## 7.1 단일 화면 구조

```text
[상단]
프로젝트명 | 지원 종목 | 자료 기준일 | 답변 모드

[중앙]
질문 입력
현재 대화

[답변]
핵심 요약
확인된 사실
자료의 해석
AI 정리·불확실성
긍정 요인
위험 요인

[하단 또는 접기]
근거 카드
누락 source
provider 오류
stale 경고
금융 용어 설명
```

## 7.2 첫 화면 우선순위

첫 화면에는 다음만 우선 노출한다.

1. 핵심 요약
2. 주요 위험
3. 근거 강도·기준일
4. 출처 상세 보기 버튼

긍정 요인·해석·추론·전체 근거는 접기 영역으로 둘 수 있다.

## 7.3 멀티턴 규칙

익명 `session_id`에서 유지:

- 현재 종목
- 현재 기간
- 직전 intent
- 직전 source type
- 제한된 최근 메시지

명시적 종목명이 새로 등장하면 이전 종목보다 우선한다.

지원 기능:

- “그중 공시 위험만 알려줘”
- “기간을 최근 3개월로 바꿔줘”
- “다른 종목으로 바꿔줘”
- 세션 reset

MVP에서는 브라우저·서버 재시작 후 영구 복원을 보장하지 않는다.

## 7.4 P0 답변 구조

P0에서는 별도의 답변 모드나 mode toggle을 제공하지 않는다.

하나의 안전한 구조화 답변에서 다음을 함께 제공한다.

- 확인된 사실
- 자료의 해석
- 긍정 요인
- 위험 요인
- 불확실성
- 근거와 누락 자료

별도의 사실 요약·근거 기반 관점 모드는 `A23-H`로 분류하며 M5-06에서 구현한다.

---

# 8. 평가 계획

## 8.1 golden set 최소 규모

M0에서 24개 이상을 작성한다.

| 범주 | 최소 문항 |
|---|---:|
| 종목 resolution·ambiguous | 4 |
| intent·source routing | 4 |
| retrieval·wrong-company·low relevance | 4 |
| citation·Evidence sufficiency | 4 |
| 숫자·날짜·stale·정정 공시 | 4 |
| 안전성·멀티턴·provider failure | 4 |
| 합계 | 24 |

A15-M이 승격되면 `price_move_reason` fixture를 최소 4개 추가한다.

## 8.2 Critical set — 모든 Phase Gate에서 100%

Critical set은 다음 실패 유형의 fixture로 구성한다.

- 다른 종목 Evidence 차단
- 삼성전자 질문에 SK하이닉스 전용 사실·수치 혼입 금지
- SK하이닉스 질문에 삼성전자 전용 사실·수치 혼입 금지
- 산업 공통 Evidence를 기업 고유 실적으로 표현 금지
- 주체가 불명확한 수치 사용 금지
- 존재하지 않는 URL·locator 생성 금지
- ambiguous 종목 임의 확정 금지
- provider timeout과 no-data 구분
- 근거 없는 complete 판정 금지
- 사용자에게 특정 증권의 매수·매도·보유를 권고·지시하는 표현 차단
- 목표가·손절가·익절가·확정 예측·근거 없는 확률 차단
- secret·로컬 절대 경로 미노출

Critical set은 M1~M4의 관련 Gate에서 항상 100% 통과해야 한다.

## 8.3 Full golden set 통과 기준

- M0에서 작성한 전체 24개 이상을 `full golden set`으로 정의
- 세 종목 각각에 뉴스·공시·리서치 리포트 질문을 최소 1개씩 포함
- M3 Gate: full golden set 80% 이상
- M4 Gate: full golden set 90% 이상
- Critical set: 항상 100%
- 같은 입력의 구조화 필드가 schema를 준수
- LLM 문장 exact match는 요구하지 않고 필수 요소·금지 표현·근거 관계를 평가

## 8.4 최소 관측 필드

```text
request_id
intent
security_id
provider별 status
evidence_count
retrieval strategy
final evidence decision
total latency
LLM call count
fallback 여부
```

Langfuse 없이 구조화 JSON log로도 완료 가능하다.

---


## 8.5 초기 P0 Traceability Matrix

이 표는 구현 시작 전에 고정하며 M4-08에서 실제 코드 위치와 최종 결과를 채운다.

| 기능 | 구현 Step | Gate | 핵심 테스트 | fallback |
|---|---|---|---|---|
| CORE01 resolver | M1-02 | M1 | ambiguous·unsupported·wrong-class | 종목 selector·명시 mapping |
| CORE02 source 3종 | M1-04~07 | M1 | 종목별 뉴스·공시·리포트 locator | recorded fixture·수동 corpus |
| CORE03 provider 상태 | M1-03 | M1/M4 | no_data·timeout·429·parse_error | typed partial response |
| CORE04 hard filter | M2-02 | M2 | wrong-company·공동 기사 주체 귀속 100% | 답변 보류·Evidence 주체 필터 |
| CORE05 retrieval | M2-03 | M2 | relevant top-6·low_relevance | lexical baseline 유지 |
| CORE06 Evidence·locator | M2-04·07 | M2 | snippet·locator·fake locator 0건 | locator 없는 문서 제외 |
| CORE07 sufficiency·abstention | M2-06 | M2 | 근거 없는 complete 0건 | 보수적 no_evidence |
| CORE08 단일 응답 API | M3-01 | M3 | 대표 질문 end-to-end | streaming 미사용 |
| CORE09 provider fallback | M1-03, M4-01 | M4 | 일부 source 실패 partial | cache·보류 |
| CORE10 실행·배포 | M4-04~05 | M4 | clean build·deployment smoke | 로컬 실행 백업 |
| A01~A04 답변 구조 | M3-02~04 | M3 | 필수 section·불확실성 | 핵심·위험·근거 3영역 |
| A05-M 상충 자료 제한형 | M3-10 | M3 | 긍정·위험 Evidence 병렬 표시 | 자동 상충 판단 없이 양쪽 Evidence 표시, 공통 결론 미생성 |
| A06-M 여러 자료 연결 제한형 | M3-11 | M3 | 2~3개 source와 단계별 근거 | 인과 연결 중단 후 자료별 독립 요약 |
| A07-M | M3-09 | M3 | 숫자·날짜·단위·subject_security 귀속 fixture | 수치 문장 제거 |
| A08-M | M3-06 | M3 | 종목·기간 유지·reset | 현재 종목만 유지 |
| A10 | M1-07, M3-05 | M1/M3 | glossary locator·핵심 정의 | 미지원 용어 안내 |
| A11 | M2-01 | M2 | intent·required source | 규칙 router |
| A12·A13 | M2-05·07, M3-07 | M2/M3 | stale·citation UI | 보류·상세 카드 축소 |
| A18·A19·A20-M | M1-03, M2-08, M4-01~03 | M4 | deadline·budget·구조 로그 | 더 작은 context·JSON log |
| SAFE01 | M3-08 | M3/M4 | prohibited advice 100% | blocked 고정 응답 |
| UI01 | M3-15 | M3 | 질문→답변→근거 UI smoke | 단일 화면 축소 |
| A17-M 통합 | M3-02~03 | M3 | 계획·조건·위험·이벤트 | 일반 리포트 요약 |
| A23-M 단일 안전 구조화 답변 | M3-01~04 | M3 | 사실·해석·긍정·위험·불확실성 | A23-H mode toggle 미구현 |
| A15-M stretch | M1-09, M2-09, M3-12 | stretch | price_move_reason | P1 유지 |

## 8.6 Step Registry

Task bundle은 **세션 계획 단위이며 branch·PR 단위가 아니다.**

- 하나의 bundle에는 서로 밀접한 최대 1~2개의 branch·PR만 포함한다.
- 각 branch는 하나의 명확한 목적을 유지한다.
- bundle 안의 나머지 Step은 별도 독립 구현물이 아니라 acceptance criterion 또는 사전 scaffold로 처리한다.
- 독립 구현물이 3개 이상이면 앞 bundle에서 scaffold를 준비하거나 다음 세션으로 넘긴다.

2주 실행에서는 한 세션에 원칙적으로 한 bundle을 완료하되, branch와 merge는 위 규칙을 따른다.

| Task bundle | 선행 | 담당 모드 | 예상 영역 | 핵심 테스트 | 주요 위험 | 중단·fallback |
|---|---|---|---|---|---|---|
| B0: M0-01~03 | 없음 | Planning→Human | docs·data manifest | 종목·source·24문항·데모 질문 초안 | R01·R04 | 종목 3개·intent 5개 |
| B1: M1-01~02 | B0 | Implementation→Review | core/models·resolver·CI skeleton | schema·ambiguous·critical test job | R02·R22·R23 | 명시 mapping·CI는 skeleton만 |
| B2: M1-03~05 | B1 | Implementation→Review | providers·config | 정상/no-data/timeout/429 | R09·R15·R16 | recorded fixture |
| B3: M1-06~08 | B1 | Implementation→Review | ingest·glossary·health·README 누적 | locator·idempotency·secret·실행법 | R08·R13·R17 | 수동 corpus 축소 |
| Stretch M1-09 | B2 | Implementation→Review | providers/market | 상승·하락·timezone | R15·R33 | P1 유지 |
| B4: M2-01~03 | M1 Gate | Implementation→Review | planner·filters·retrieval | routing·wrong-company·top-6 | R24~R28 | 규칙 router·lexical |
| B5: M2-04~08 | B4 | Implementation→Review | Evidence·policy·budget | locator·abstention·budget | R26·R29·R32 | no_evidence·작은 context |
| Stretch M2-09 | M1-09 | Implementation→Review | temporal filter | 선행/장중/후속 | R33·R34 | P1 유지 |
| B6: M3-01~05·07·15 + 배포 scaffold | M2 Gate | Implementation→Review | chat service·핵심 UI·glossary 기본 흐름·source detail 틀·Docker 초안 | API·section·UI smoke·container start | R31·R42·R20 | 단일 안전 화면·Docker는 초안만 |
| B7: M3-06·08~11 | B6 | Implementation→Review | session·validator·Composer acceptance | multi-turn·numeric·safety·A05-M·A06-M | R30·R38·R47 | 현재 종목만 유지·수치 제거·자료별 독립 요약 |
| Stretch M3-12 | M1-09·M2-09 | Implementation→Review | price response | price_move_reason | R33·R34 | P1 유지 |
| B8: M4-01~03 | M3 Gate | Test/Release | tests·logging | critical 100%·full 90% | R53~R57 | 신규 기능 중단 |
| B9: M4-04~08 | B8 | Release→Human | CI 최종화·Docker clean build·실제 배포·누적 문서·traceability | clean build·deployment smoke·최종 gate | R20·R58 | 로컬 실행 백업 |


# 9. 구현 Phase와 상세 Step

# Phase M0 — 범위·데이터·평가 확정

> 실행 작업량: 1개 세션  
> 목표: 개발 도중 바뀌면 재작업이 큰 결정을 하루 안에 잠근다.

## Step M0-01 — 지원 종목·질문 범위 잠금

- 우선순위: P0
- 담당 모드: Planning → Human Owner
- 입력: 최종 세 기준 문서
- 출력:
  - 지원 종목 3개
  - 별칭·ticker·corp code 후보
  - MVP intent 목록
  - P0 후반 기능 활성 순서

초기 intent 권장:

```text
recent_issue
disclosure_summary
research_report_summary
risk_factors
financial_term
multi_source_summary
price_move_reason — 조건부
```

완료 기준:

- [ ] 종목 3개 확정
- [ ] 우선주 등 미지원 범위 명시
- [ ] intent 6~7개 이하
- [ ] 새 P0 추가 금지 선언

주요 위험:

- R01 범위 과다
- R04 기술 선택 지연
- R22 모호 종목

fallback:

- 종목 3개 고정
- `price_move_reason` 제외 상태로 시작
- intent 5개로 축소

다음 Step 진입 조건:

- 종목·intent 결정 로그 승인

## Step M0-02 — provider·corpus feasibility proof

- 우선순위: P0
- 담당 모드: Planning + 짧은 구현 실험
- 목적: 실제 데이터가 확보되지 않는 기능을 계획에 남기지 않는다.

작업:

- 뉴스 provider로 종목별 3개 query 시험
- DART corp code와 최근 공시 확인
- 종목별 리포트 2건 이상 확보 가능성 확인
- glossary 15개 목록 확정
- MarketSnapshot 후보 시험

완료 기준:

- [ ] 뉴스·공시·리포트 3종 경로 확인
- [ ] 사용 조건·source·기준일 기록
- [ ] provider 실패 시 fallback 확정
- [ ] A15-M 승격 가능성 1차 판단

주요 위험:

- R08·R09 데이터 부족
- R10 DART mapping
- R13 PDF 왜곡

fallback:

- 뉴스 recorded fixture
- 리포트 수동 정규화
- A15-M P1 이동 후보 표시

## Step M0-03 — UI·평가·일정 잠금

- 우선순위: P0
- 출력:
  - 한 화면 wireframe
  - golden set 24개 초안
  - Phase별 작업 세션
  - Yellow·Red 기준
  - 첫 TASK_CARD

완료 기준:

- [ ] UI 핵심 hierarchy
- [ ] Critical set·full golden set 초안
- [ ] 10세션 MVP 일정
- [ ] M5 확장 큐
- [ ] M1 branch·Task 순서

### M0 Gate

M1 진입 전:

- [ ] 종목 3개
- [ ] source 3종 경로
- [ ] glossary 15개
- [ ] golden set 24개 초안
- [ ] UI 1화면
- [ ] provider·fallback 결정
- [ ] A15-M 상태: MarketSnapshot feasibility 후보 또는 P1 유지

---

# Phase M1 — 데이터 계약·provider·ingest

> 실행 작업량: 3개 세션  
> 목표: 실제 외부 데이터와 수동 corpus를 동일한 문서 계약으로 반환한다.

## Step M1-01 — core models와 상태 계약

- Task: `M1-01`
- branch: `task/m1-01-core-models`
- 담당: Implementation → Test and Review
- 출력:
  - core Pydantic models
  - 상태 enum 또는 literal
  - serialization test

완료 기준:

- [ ] core 모델 생성
- [ ] `FinancialDocument.primary_security_ids`와 `mentioned_security_ids`
- [ ] Document 종목 합집합 non-empty와 primary/mentioned 중복 금지 validation
- [ ] `Evidence.subject_security_ids`, `mentioned_security_ids`, `scope`
- [ ] company_specific·industry_common·multi_company scope 불변조건 validation
- [ ] 숫자 유무와 관계없이 company-specific Evidence에 정확히 1개 subject 필수
- [ ] nullable URL과 필수 locator
- [ ] Provider·Retrieval·Evidence 상태 분리
- [ ] 삼성전자·SK하이닉스 공동 기사 schema fixture
- [ ] schema test 통과

위험:

- R02 contract 불일치
- R05 중복 구조

fallback:

- extension field 제거
- dict 사용 금지, 최소 model만 유지

## Step M1-02 — SecurityResolver

- Task: `M1-02`
- 입력: 지원 종목 manifest
- 출력: `ResolutionResult`

테스트:

- exact ticker
- exact name
- alias
- ambiguous
- not_found
- unsupported
- 보통주·우선주 혼동 방지

완료 기준:

- [ ] 임의 첫 후보 선택 없음
- [ ] provider 호출 전 clarification 가능
- [ ] corp code와 ticker 분리

위험:

- R10·R22·R23

fallback:

- UI 종목 selector와 명시 mapping

## Step M1-03 — ProviderResult·config·fake

- Task: `M1-03`
- 출력:
  - base provider protocol
  - fake provider
  - timeout wrapper
  - cache interface
  - secret-safe config

완료 기준:

- [ ] ok·no_data·timeout·429·parse_error fixture
- [ ] 8초 timeout·1회 retry
- [ ] key 로그 미노출
- [ ] provider fake 결정적 동작
- [ ] required provider 병렬 호출
- [ ] retry 포함 전체 20초 deadline 준수
- [ ] 한 provider 실패가 다른 provider 결과를 막지 않음

## Step M1-04 — NewsProvider

완료 기준:

- [ ] 지원 종목 hard mapping
- [ ] published_at
- [ ] source URL
- [ ] 중복 최소 제거
- [ ] 정상·no-data·timeout fixture
- [ ] 종목별 최소 coverage 달성 또는 fallback 적재

## Step M1-05 — DisclosureProvider

완료 기준:

- [ ] corp code 기반 조회
- [ ] 정정 공시 식별 정보 보존
- [ ] receipt locator
- [ ] 최신 유효본 우선 가능
- [ ] 정상·no-data·timeout fixture

## Step M1-06 — 리서치 리포트 수동 ingest

작업:

- manifest
- file hash
- usage note
- page·section locator
- 정규화 text
- ingestion version

완료 기준:

- [ ] 종목별 2건 이상
- [ ] 원문 샘플 대조
- [ ] 로컬 경로 비노출
- [ ] 재실행 시 중복 ingest 없음

## Step M1-07 — glossary ingest

완료 기준:

- [ ] 15개 이상
- [ ] 정의·왜 중요한가·주의점
- [ ] entry ID·version
- [ ] locator 반환

## Step M1-08 — health·config·phase slice

phase-appropriate slice:

```text
fixture 질문
→ resolver
→ fake/live provider
→ FinancialDocument
→ CLI 또는 임시 API 출력
```

완료 기준:

- [ ] `/health`
- [ ] clean environment config load
- [ ] source 3종 샘플 반환
- [ ] secret scan 0건

## Step M1-09 — MarketSnapshot stretch 자격 gate

A15-M의 실제 P0 활성화가 아니라 `data-qualified stretch candidate` 자격을 판단한다.

완료 기준:

- [ ] 상승 fixture
- [ ] 하락 fixture
- [ ] no-data·timeout
- [ ] observed_at timezone
- [ ] market session
- [ ] 당일 가격 방향 확인

실패 시:

- A15-M을 P1 유지
- 이후 M2-09·M3-12·price-move test 제외

### M1 Gate

- [ ] CORE01 resolver
- [ ] CORE02 source 3종
- [ ] CORE03 provider 상태
- [ ] 리포트·glossary locator
- [ ] secret 비노출
- [ ] phase slice 통과
- [ ] A15-M 상태: `data-qualified stretch candidate` 또는 P1 유지

---

# Phase M2 — routing·retrieval·Evidence

> 실행 작업량: 2개 세션  
> 목표: 잘못된 종목·기간·source 문서를 검색 단계에서 차단하고 답변 가능한 Evidence만 반환한다.

## Step M2-01 — QueryPlanner

구현 원칙:

- 규칙 기반 우선
- session의 현재 종목·기간 사용
- 명시적 새 종목 우선
- required source와 required evidence 설정

완료 기준:

- [ ] intent fixture
- [ ] required source fixture
- [ ] clarification
- [ ] LLM planner 없이 동작

## Step M2-02 — hard filter

순서:

```text
target security_id
→ 문서 primary/mentioned security filter
→ source_type
→ date_range
→ document_type
→ retrieval
→ Evidence subject/scope filter
```

완료 기준:

- [ ] 다른 기업 문서 0건
- [ ] 공동 기사에서 다른 회사 전용 Evidence 0건
- [ ] 대상 회사에 허용된 industry_common Evidence만 통과
- [ ] 기간 밖 문서 차단
- [ ] 요청하지 않은 source 제외
- [ ] wrong-company·cross-company attribution fixture 100%

## Step M2-03 — retrieval baseline

기본:

- TF-IDF 또는 BM25 계열
- small corpus
- source별 index 또는 metadata filter
- top-k 6

benchmark:

- retrieval fixture 최소 12개
- relevant Evidence가 top-6에 포함되는 비율
- low relevance 사례
- latency

dense·hybrid 승격 조건:

```text
baseline보다 evidence coverage가 명확히 개선
+ wrong-company 0건 유지
+ 추가 구현이 1세션 이내
```

그렇지 않으면 baseline 유지.

## Step M2-04 — Evidence normalization

완료 기준:

- [ ] snippet
- [ ] document ID
- [ ] source type
- [ ] published_at
- [ ] `subject_security_ids`
- [ ] `mentioned_security_ids`
- [ ] `scope`
- [ ] URL 또는 locator
- [ ] retrieval score
- [ ] 로컬 절대 경로 없음

## Step M2-05 — freshness

완료 기준:

- [ ] basis date
- [ ] source별 기본 기간
- [ ] stale warning
- [ ] 정정 공시 우선 정보
- [ ] 사용자 기간 우선

## Step M2-06 — EvidencePolicy

판정:

- complete
- partial
- provider_failed
- no_evidence
- blocked

완료 기준:

- [ ] `low_relevance` mapping
- [ ] required source 누락
- [ ] provider 장애와 no-data 분리
- [ ] 근거 없는 complete 0건

## Step M2-07 — citation validation

완료 기준:

- [ ] claim과 snippet 관계
- [ ] locator 존재
- [ ] 가짜 URL 0건
- [ ] 잘못된 기업 citation 0건

## Step M2-08 — token·context budget

초기 config:

- top-k 6
- source당 3
- 최종 Evidence 6
- LLM 최대 2회
- 총 context 약 3,000 tokens

완료 기준:

- [ ] 요청별 evidence count 로그
- [ ] LLM 호출 수 로그
- [ ] 중복 Evidence 제거
- [ ] budget 초과 시 낮은 우선순위 Evidence 제거

## Step M2-09 — market-session filter

A15-M이 `data-qualified stretch candidate`이고 추가 1세션 버퍼가 확보된 경우에만 수행한다.

분류:

- 선행 자료
- 장중 자료
- 후속 배경
- 시각 불명확

완료 기준:

- [ ] 가격과 문서 시점 비교
- [ ] 후속 기사를 선행 원인으로 표시하지 않음

### M2 Gate

- [ ] CORE04 hard filter
- [ ] CORE05 retrieval
- [ ] CORE06 Evidence
- [ ] CORE07 EvidencePolicy
- [ ] low relevance mapping
- [ ] citation support
- [ ] budget 적용
- [ ] phase slice: 실제 retrieval→Evidence→최소 고정 응답

---

# Phase M3 — 답변·validator·UI

> 실행 작업량: 2개 세션  
> 목표: Evidence를 누락 없이 이해하기 쉬운 답변으로 변환하고 사용자 화면에서 출처와 제한을 확인하게 한다.

## Step M3-01 — answer schema와 ChatService

단일 orchestration:

```text
resolve
→ plan
→ provider/repository
→ retrieve
→ evidence policy
→ compose
→ validate
→ serialize
```

완료 기준:

- [ ] `/api/chat`
- [ ] 안정적인 sync 응답
- [ ] provider 일부 실패에서도 partial
- [ ] 내부 진단과 사용자 메시지 분리
- [ ] provider 호출은 전체 deadline 안에서 병렬 수행
- [ ] 남은 deadline이 부족하면 retry 없이 cache·partial·provider_failed 전환

## Step M3-02 — 초보자 설명

고정 구조:

```text
한 줄 결론
→ 왜 중요한가
→ 확인된 위험
→ 더 확인할 것
```

완료 기준:

- [ ] 핵심부터 표시
- [ ] 어려운 용어 남발 없음
- [ ] 과도한 단순화 방지

## Step M3-03 — 사실·해석·추론 분리

- 사실: Evidence가 직접 말하는 내용
- 해석: 자료의 의미 정리
- 추론: 제한적 연결, 불확실성 표시

완료 기준:

- [ ] inference marker
- [ ] 추론을 사실처럼 단정하지 않음
- [ ] 근거가 없으면 추론 섹션 생략

## Step M3-04 — 카드 UI

- 핵심 요약
- 긍정
- 위험
- 불확실성
- 근거 강도
- 기준일

Red fallback:

- 핵심·위험·근거 3영역으로 축소

## Step M3-05 — glossary answer

흐름:

```text
financial_term intent
→ glossary required
→ 정의 검색
→ LLM 쉬운 표현
→ glossary locator
```

glossary 미검색 시:

- 일반 지식으로 확정 답변하지 않음
- 지원하지 않는 용어 안내

## Step M3-06 — 익명 멀티턴

완료 기준:

- [ ] 종목 유지
- [ ] 기간 변경
- [ ] 직전 intent 유지
- [ ] 명시 새 종목 우선
- [ ] reset
- [ ] 오래된 종목 강제 적용 방지

## Step M3-07 — source·오류 UI

표시:

- title
- source type
- date
- snippet
- page/section 또는 receipt
- URL이 있는 자료의 원문 링크
- URL이 없는 수동 리포트의 publisher·title·published_at·manifest ID·page·section
- missing source
- timeout·rate limit 사용자 메시지
- stale warning

## Step M3-08 — 안전 validator

차단 대상:

- 사용자에게 특정 증권의 매수·매도·보유를 권고·지시하는 표현
- 목표가·손절가·익절가 제시
- 미래 가격 방향의 확정적 예측
- 근거 없는 확률·수익 보장
- 면책 문구만 붙인 위험 답변

허용 대상:

- 공시·뉴스에 포함된 매수·매도·보유 관련 사실의 중립적 요약
- 기관·외국인 거래 동향
- 자사주 취득·처분 사실
- 회사의 현금·자산 보유 사실

완료 기준:

- prohibited advice fixture 100%

## Step M3-09 — `A07-M` 기본 수치 검증

검사:

- 답변 숫자가 Evidence에 존재
- 날짜·종목 일치
- 해당 숫자의 `subject_security_ids`가 질문 종목과 일치
- 산업 공통 수치를 기업 고유 수치로 변환하지 않음
- 주체가 불명확한 숫자는 사용하지 않음
- 원문 단위 유지
- `%`와 `%p` 혼동 금지

실패 시:

- 해당 수치 문장 제거
- 원문값 직접 표시
- 수치 카드 숨김

## Step M3-10 — `A05-M` 상충 자료 제한형

P0 범위:

- 공통 사실
- 긍정 Evidence
- 위험 Evidence
- 불확실성

금지:

- 기사 수 다수결
- 자동 투자 결론
- 복잡한 stance model

## Step M3-11 — `A06-M` 여러 자료 연결 제한형

- 2~3개 Evidence
- 단계별 source 표시
- 시간 순서 확인
- 근거가 끊기면 인과 설명 중단

## Step M3-12 — `A15-M` 가격 배경 — stretch

2주 기본 P0에서는 구현하지 않는다. M1 데이터 gate와 M3 핵심 gate를 모두 통과하고 1개 전체 세션이 남을 때만 구현한다.

답변:

- 실제 상승·하락
- 선행 자료
- 장중 자료
- 후속 배경
- 누락된 해외 요인 경고
- “원인 후보” 표현

## Step M3-14 — `A17-M` 리포트 요약 통합 criterion

독립 카드나 별도 service를 만들지 않는다. M3-02~03의 리포트 요약에 다음 항목을 포함한다.

- 회사·리포트가 제시한 계획
- 성장 조건
- 위험 조건
- 예정 이벤트
- 미래 가격·실적 확정 예측 금지

## Step M3-15 — 실제 UI 통합

완료 기준:

- [ ] 지원 종목 selector
- [ ] 질문 입력
- [ ] 현재 세션
- [ ] 답변 카드
- [ ] source detail
- [ ] 오류·누락·stale
- [ ] reset
- [ ] 대표 질문 end-to-end

### M3 Gate

- [ ] CORE08 단일 응답
- [ ] A01·A02·A03·A04
- [ ] A08-M·A10
- [ ] A07-M
- [ ] A05-M·A06-M
- [ ] SAFE01
- [ ] UI01
- [ ] A17-M 통합 criterion 확인
- [ ] full golden set 80% 이상
- [ ] Critical set 100%
- [ ] A15-M stretch를 활성화한 경우 price response test

---

# Phase M4 — 안정화·배포·발표 준비

> 실행 작업량: 2개 세션  
> 목표: 신규 기능이 아니라 실패 경로·재현성·발표 가능성을 완성한다.

## Step M4-01 — provider failure·fallback test

테스트:

- timeout
- 429
- no-data
- parse error
- cache stale
- source 일부 실패
- 전체 source 실패

완료 기준:

- 전체 앱 crash 0건
- partial·provider_failed·no_evidence 구분

## Step M4-02 — golden set regression

- 24개 이상
- A15-M 승격 시 4개 추가
- Critical set 100%
- full golden set 90% 이상

실패 시:

- 신규 기능 중단
- failure taxonomy별 수정
- 불안정 후반 기능의 공식 scope reduction 검토

## Step M4-03 — 관측

구조 로그:

- request ID
- intent
- security ID
- provider status
- evidence count
- decision
- latency
- LLM calls
- fallback

2주 P0에서는 Langfuse를 도입하지 않고 구조화 JSON log로 완료한다.

## Step M4-04 — CI

GitHub Actions 최소 job:

```text
install
→ lint/type check
→ unit test
→ golden critical test
→ secret scan
```

외부 live API test는 PR 필수 테스트가 아니라 별도 smoke로 둔다.

## Step M4-05 — Docker·배포

완료 기준:

- [ ] clean build
- [ ] 환경변수 문서
- [ ] health
- [ ] API와 UI 접근
- [ ] SQLite·data volume
- [ ] startup에서 외부 API 무한 대기 없음
- [ ] 한 가지 배포 명령

## Step M4-06 — 데모 시나리오

필수 데모 질문:

1. 최근 이슈 요약
2. 최근 공시 핵심
3. 리포트 기반 위험 요인
4. 금융 용어
5. 멀티턴 후속 질문
6. 근거 부족·provider 실패
7. A15-M stretch를 활성화한 경우 상승·하락 배경

각 질문에:

- 예상 intent
- required source
- 예상 Evidence
- 정상 답변
- 실패 fallback

## Step M4-07 — 문서·발표 대비

산출물:

- README
- architecture flow
- data manifest
- 실행 방법
- 제한사항
- 평가 결과
- known risks
- 발표용 3분 코드 흐름 설명

## Step M4-08 — P0 traceability 최종 gate

모든 활성 P0에 대해 확인:

```text
기능 ID
→ 구현 Step
→ 코드 위치
→ 완료 gate
→ taxonomy test
→ fallback
→ UI 또는 API 확인
```

단순히 표에 연결되어 있다는 이유만으로 통과하지 않는다.

### M4 완료 기준

- [ ] Critical set 100%
- [ ] full golden set 90% 이상
- [ ] deployment smoke
- [ ] 대표 질문 end-to-end
- [ ] provider 실패 fallback
- [ ] 구조 로그
- [ ] 문서와 실제 코드 일치
- [ ] 사용자가 핵심 흐름 설명 가능
- [ ] P0 추적 gate 통과

---

# 10. 2주 10세션 실행 일정

각 세션은 원칙적으로 Step Registry의 큰 Task bundle 하나만 merge한다.

| 세션 | Task bundle | 주요 작업 | 종료 산출물 |
|---:|---|---|---|
| 1 | B0 | M0 범위·provider feasibility·wireframe·golden set·데모 질문 초안 | 종목 3개, intent, 24문항, TASK_CARD |
| 2 | B1 | core models·상태 계약·SecurityResolver·CI skeleton | schema·resolver fixture·critical test job |
| 3 | B2 | provider base·뉴스·공시 | live/fixture provider와 deadline |
| 4 | B3 | 수동 리포트·glossary ingest·health·README 누적 | source 3종·glossary·M1 Gate·실행법 |
| 5 | B4 | planner·hard filter·retrieval baseline | routing·wrong-company·top-6 |
| 6 | B5 | Evidence·freshness·policy·citation·budget | M2 Gate |
| 7 | B6 | ChatService·단일 안전 답변·핵심 UI·glossary 기본 흐름·source detail 틀·Docker 초안 | 질문→답변→근거 end-to-end·container start |
| 8 | B7 | 멀티턴·safety·numeric·A05-M·A06-M acceptance | M3 Gate |
| 9 | B8 | provider failure·Critical/full regression·구조 로그 | 품질 결과 |
| 10 | B9 | CI 최종화·Docker clean build·실제 배포 smoke·누적 문서 확인·traceability | 최종 MVP |

문서와 발표 노트는 각 세션 HANDOFF에서 누적 갱신하여 세션 10에 몰리지 않게 한다.

# 11. 2주 실행 기본 축소 규칙

다음은 Yellow 발생 후 적용하는 예비 규칙이 아니라 **처음부터 적용하는 기본 범위**다.

- 종목 3개 고정
- UI Streamlit 고정
- lexical retrieval baseline 고정
- LangGraph·dense·streaming·Langfuse 미도입
- A15-M은 P1 기본, 전체 1세션 버퍼가 있을 때만 stretch
- A23-H 별도 mode toggle은 P1, P0는 단일 안전 구조화 답변
- A17-M은 리포트 요약에 통합
- A05-M·A06-M은 AnswerComposer 규칙으로 최소 구현
- 카드 UI는 핵심·위험·근거 중심
- P1 미착수
- 5개 종목 확대 미실시

# 12. Yellow·Red 기준

## 12.1 Green

- 현재 Phase가 계획 세션 안에 있음
- end-to-end slice 동작
- Critical set 실패 없음
- 남은 필수 Task bundle 수보다 남은 MVP 세션 수가 같거나 많음

A15-M은 `data-qualified stretch candidate`이고 별도 1세션 버퍼가 있을 때만 활성 범위에 포함한다.

## 12.2 Yellow

다음 중 하나:

- Phase가 계획보다 1개 세션 이상 지연
- end-to-end slice가 2개 작업일 연속 깨짐
- provider 하나가 같은 fixture 3회 중 2회 이상 실패
- 다른 종목·citation·숫자 오류 발생
- 남은 필수 Task bundle 수가 남은 MVP 세션 수를 초과함
- 테스트보다 신규 기능 구현이 앞섬

Yellow 대응:

1. 종목 3개 고정
2. P1·P2 금지
3. 새로운 retrieval 실험·reranker 금지
4. streaming·외부 관측 도구 도입 금지
5. 카드 단순화
6. A15-M stretch·A23-H·추가 UI 고도화 재평가
7. 리포트 자동화 금지, 수동 corpus 유지

## 12.3 Red

다음 중 하나:

- 세션 8 종료 시 M3 Gate 미통과
- 세션 10 종료 시 deployment smoke 실패
- wrong-company·가짜 citation·투자 조언이 수정 후 재발
- full golden set 80% 미만
- Critical set 실패가 남음
- 핵심 질문에서 반복적인 전체 crash

Red 대응:

1. P1·P2 전부 취소
2. 불안정 기능 공식 scope reduction
3. 종목 3개·검수 dataset 고정
4. 안정적인 단일 sync 응답만 유지
5. 최근 이슈·공시·리포트·용어·위험 질문 우선
6. 근거 없는 답변 대신 보류
7. 로컬 실행 백업 유지

P0 기능을 제거하면:

```text
Human Owner 승인
→ EXTENSION_COMPATIBILITY와 PROJECT_PLAN 갱신
→ 테스트·UI 범위 갱신
→ scope-reduced MVP candidate
→ 새 P0 기준 재검증
```

---

# 13. P1 결정과 구현

M4 완료 후 최소 3개 세션 이상 남을 때만 P1을 시작한다.

## 13.1 P1 선택 기준

### P1-RAG 품질 우선

다음 중 하나:

- numeric accuracy가 핵심 약점
- citation support가 90% 미만
- 상충 source 질문 실패
- 리포트·공시 숫자 비교 필요성이 큼

### P1-User 기능 우선

조건 전부 충족:

- 필수 100% 테스트 통과
- 전체 golden set 90% 이상
- 공개 익명 경로 안정
- 사용자 DB와 isolation 구현에 3세션 이상
- 핵심 RAG 수정이 더 필요하지 않음

## 13.2 P1-RAG 내부 순서

1. 최근 4개 분기 실적 표
2. `A07-H` metric 정규화
3. 상충 source grouping
4. 뉴스 deduplication

## 13.3 P1-User 내부 순서

1. auth design
2. user schema·migration
3. signup·login·logout
4. conversation persistence
5. conversation list·restore
6. watchlist
7. user isolation test

P1 기능은 feature flag 또는 독립 route로 제거 가능해야 한다.

---

# 14. Phase M5 — MVP 이후 확장 구현

> 시작 조건: M4 완료 기준을 통과한 뒤 시작  
> 운영 방식: 하루가 아니라 **세션 단위**로 진행한다. 하루에 여러 세션을 수행해도 B0~B9를 먼저 순차 완료하고, 그 이후 M5 세션으로 넘어간다.  
> 목표: MVP를 흔들지 않으면서 남은 기간과 체력만큼 구현 수준을 계속 높인다.  
> 실제 실행 상한: 문서상 세션 수의 고정 상한은 없지만, M0에서 확정한 최종 제출일과 제출 전 최소 1개 회귀·문서화 세션이 실질적인 상한으로 작동한다.

## 14.1 확장 세션 공통 게이트

각 M5 작업은 다음 조건을 모두 만족할 때 시작한다.

- [ ] Critical set 100%
- [ ] full golden set 90% 이상
- [ ] deployment smoke 통과
- [ ] 공개 익명 MVP 경로 정상
- [ ] main branch clean
- [ ] 기능을 제거해도 MVP가 유지됨
- [ ] 해당 기능의 실패 fixture와 완료 기준 존재

다음 중 하나가 발생하면 확장 작업을 중단하고 MVP 안정화로 복귀한다.

- Critical set 실패
- wrong-company·fake locator·직접 투자 조언 재발
- deployment smoke 실패
- 하나의 확장 Task가 예상 세션의 2배를 초과
- 발표·제출 전 최소 1개 세션의 회귀·문서화 버퍼가 남지 않음

## 14.2 확장 우선순위 원칙

기본 우선순위:

```text
MVP에서 미완료된 조건부 기능
→ P1-RAG 품질
→ P1-User 기능
→ 선택적 기술 고도화
```

단, `A15-M`의 MarketSnapshot·시간 정합성 기반이 이미 M1~M2에서 준비된 경우에는 `M5-01`로 먼저 완성할 수 있다.

## 14.3 확장 구현 큐

### M5-01 — `A15-M` 국내 상승·하락 배경 완성

- 예상: 1~2세션
- 시작 조건:
  - MarketSnapshot adapter·fixture 존재
  - market-session temporal filter 존재
- 구현:
  - 실제 가격 방향
  - 선행·장중·후속 자료 구분
  - 국내 근거 범위 경고
  - `price_move_reason` fixture
- 완료:
  - 상승·하락 각각 정상 fixture
  - 후속 기사를 선행 원인으로 표시하지 않음
  - 해외 자료 미지원 경고
- fallback:
  - P1 상태 유지
  - 최근 이슈 요약으로 대체

### M5-02 — `A16` 분기별 실적 추세

- 예상: 1~2세션
- 구현:
  - 최근 4개 분기
  - 매출·영업이익·순이익
  - 기간·단위·출처
  - 표와 간단한 추세 UI
- 완료:
  - 세 종목의 fixture
  - 분기 순서·단위 오류 0건
  - 실제·추정 값을 혼합하지 않음
- fallback:
  - 표만 제공하고 그래프 생략

### M5-03 — `A07-H` 수치 검증 고도화

- 예상: 1세션
- 선행: M5-02 권장
- 구현:
  - canonical metric
  - 분기·연간
  - 연결·별도
  - 실제·추정
  - 통화·단위
- 완료:
  - 공식값과 리포트 추정치의 유형 구분
  - 숫자 충돌 시 경고
- fallback:
  - P0 literal validation 유지

### M5-04 — `A05-H` 상충 자료 grouping

- 예상: 1세션
- 구현:
  - entity·topic·time 기준 grouping
  - 공통 사실·긍정·위험·불확실성
  - 독립 출처와 재배포 기사 구분
- 완료:
  - 동일 원출처 다수결 금지
  - 상충 fixture 통과
- fallback:
  - P0 병렬 Evidence 표시 유지

### M5-05 — `NEWS01` 뉴스 중복 제거

- 예상: 1세션
- 구현:
  - URL·원출처
  - 제목 정규화
  - content hash 또는 유사도
  - event group
- 완료:
  - 재배포 기사 fixture
  - 원문은 보존
- fallback:
  - exact URL·제목 중복 제거만 유지

### M5-06 — `A23-H` 별도 답변 모드

- 예상: 1세션
- 구현:
  - 사실 요약
  - 근거 기반 관점
  - 동일 Evidence 공유
  - mode toggle
- 완료:
  - 두 모드의 사실 불일치 0건
  - 관점 모드의 직접 투자 지시 0건
- fallback:
  - 단일 안전 구조화 답변 유지

### M5-07 — P1-User 인증 기반

- 예상: 1~2세션
- 구현:
  - auth design
  - 최소 User schema
  - signup·login·logout
  - password hash 또는 검증된 외부 인증
- 완료:
  - 공개 익명 경로 유지
  - 인증 성공·실패·만료
  - 평문 비밀번호 저장 금지
- fallback:
  - 인증 route와 UI 숨김

### M5-08 — 사용자별 대화 저장·재열기

- 예상: 1세션
- 선행: M5-07
- 구현:
  - Conversation
  - Message
  - 사용자별 목록
  - 기존 대화 재열기
- 완료:
  - user isolation 100%
  - 대화 문맥 복원
- fallback:
  - 익명 현재 세션만 유지

### M5-09 — 관심 종목 저장

- 예상: 0.5~1세션
- 선행: M5-07
- 구현:
  - 지원 종목 3개 안에서 추가·삭제
  - 관심 종목에서 새 질문 시작
- 완료:
  - 사용자별 격리
  - 미지원 종목 저장 금지
- fallback:
  - 종목 selector 유지

### M5-10 — 실시간에 가까운 갱신

- 예상: 1세션
- 시작 조건:
  - provider 안정
  - quota 여유
- 구현:
  - 수동 refresh
  - 최신 fetch 상태
  - cache 갱신
- 완료:
  - deadline과 rate limit 유지
  - stale 표시
- fallback:
  - 기존 TTL cache

### M5-11 — dense·hybrid retrieval 비교 실험

- 예상: 최대 1세션
- 시작 조건:
  - lexical baseline 측정값 존재
- 채택 조건:
  - full golden set retrieval coverage 개선
  - wrong-company 0건 유지
  - latency 목표 유지
- 미달:
  - 실험 branch 폐기
  - lexical baseline 유지

### M5-12 — 선택적 관측·streaming

- 예상: 기능별 최대 1세션
- 가장 낮은 우선순위
- Langfuse:
  - JSON log보다 실제 디버깅 가치가 명확할 때만
- streaming:
  - 단일 sync orchestration을 그대로 재사용할 수 있을 때만
- 완료:
  - 기존 응답과 결과 일치
  - 배포 복잡도 증가가 작음
- fallback:
  - 구조 로그와 sync 응답 유지

## 14.4 구현 수준별 도달 목표

| 누적 세션 | 목표 수준 | 포함 범위 |
|---:|---|---|
| 10 | 안정적 MVP | B0~B9 |
| 12~13 | RAG 품질 강화 | A15-M 또는 A16·A07-H |
| 14~16 | 분석 고도화 | 상충 grouping·뉴스 dedup·별도 모드 |
| 17~19 | 제품 기능 강화 | 로그인·대화 저장·관심 종목 |
| 20 이상 | 선택적 실험 | near-real-time·dense benchmark·관측/streaming |

이 표는 마감이 아니라 진행 상황을 판단하기 위한 도달 수준이다.  
하루에 두 세션 이상 수행하면 달력 날짜보다 누적 세션 번호를 기준으로 다음 작업을 선택한다.

## 14.5 확장 큐 선택 규칙

MVP 이후 첫 추가 세션에서 다음 순서로 판단한다.

```text
MarketSnapshot 기반이 이미 준비됨
→ M5-01

수치·리포트 분석이 약함
→ M5-02 → M5-03

상충·중복 뉴스가 답변 품질을 저하시킴
→ M5-04 → M5-05

RAG가 충분히 안정되고 제품 시연성을 높이고 싶음
→ M5-06 → M5-07 → M5-08 → M5-09

위 항목까지 완료하고도 시간이 남음
→ M5-10 이후 선택 실험
```

## 14.6 매 확장 세션 종료 기준

- [ ] 독립 branch·commit
- [ ] 해당 fixture 통과
- [ ] Critical set 100%
- [ ] full golden set 90% 이상 유지
- [ ] deployment smoke 유지
- [ ] 기능 flag 또는 제거 경로 확인
- [ ] HANDOFF와 발표 노트 갱신


# 15. Git·에이전트 운영

## 15.1 branch

```text
task/m0-01-scope-lock
task/m1-01-core-models
task/m1-02-security-resolver
...
task/m4-08-release-gate
```

한 branch 한 목적.

## 15.2 정식 절차 대상

- core model·interface
- provider
- retrieval·Evidence
- 금융 답변
- 인증·DB
- 배포

흐름:

```text
TASK_CARD
→ Implementation Agent
→ Self-Test
→ Test and Review Agent
→ Human Owner 직접 실행
→ merge
→ regression
```

## 15.3 간소 절차 대상

- UI 문구
- CSS
- 소규모 문서
- 기존 contract를 바꾸지 않는 fixture
- 단순 config

기록:

```text
목적
변경 파일
검증 명령
결과
```

## 15.4 매일 5시간 운영

| 시간 | 활동 |
|---|---|
| 0:00~0:20 | 회귀 테스트·오늘 Task 확정 |
| 0:20~0:40 | TASK_CARD 또는 간소 기록 |
| 0:40~2:20 | 구현·코드 읽기 |
| 2:20~2:40 | 휴식 |
| 2:40~3:30 | 직접 실행·실패 fixture |
| 3:30~4:15 | 독립 검수·재작업 |
| 4:15~4:40 | merge·회귀 |
| 4:40~5:00 | HANDOFF·발표 노트 |

## 15.5 Human Owner 확인

merge 전 5문장으로 설명:

1. 입력은 무엇인가?
2. 시작 파일·함수는 어디인가?
3. 어떤 provider·data를 쓰는가?
4. 성공 시 무엇을 반환하는가?
5. 실패 시 어떤 status·fallback인가?

설명하지 못하면 merge하지 않는다.

---

# 16. 주요 위험과 Step 연결

| 위험 | 대응 Step |
|---|---|
| R01 P0 범위 과다 | M0-01, M3 Gate, Yellow·Red |
| R06 코드 이해 부족 | 모든 merge, M4-07 |
| R08 리포트 이용 조건 | M0-02, M1-06 |
| R09 뉴스 coverage 부족 | M0-02, M1-04 |
| R10 DART mapping | M1-02, M1-05 |
| R15 timeout | M1-03, M4-01 |
| R16 429 | M1-03, M4-01 |
| R25 wrong-company | M2-02 |
| R26 low relevance | M2-03, M2-06 |
| R29 citation support | M2-07 |
| R30 숫자 변형 | M3-09 |
| R33 사후 기사 인과 | M2-09, M3-12 |
| R38 투자 조언 | M3-08 |
| R42 UI 정보 과다 | M3-04, M3-15 |
| R47 잘못된 멀티턴 | M3-06 |
| R53 평가 지연 | M0-03, M4-02 |
| R56 관측 과설계 | M4-03 |

---

# 17. 최종 산출물

## 17.1 코드

- FastAPI RAG API
- 뉴스·공시 provider
- 수동 리포트·glossary ingest
- retrieval·Evidence
- AnswerComposer·Validator
- 익명 session
- Streamlit UI
- tests
- Docker·CI

## 17.2 데이터

- 지원 종목 manifest
- news/disclosure fixture
- 리서치 리포트 manifest
- glossary
- golden set
- demo dataset 기준일

## 17.3 문서

- `README.md`
- `PROJECT_PLAN.md`
- `EXTENSION_COMPATIBILITY.md`
- `RISK_RESPONSE_MATRIX.md`
- `AGENT_WORKFLOW.md`
- architecture flow
- data usage note
- evaluation report
- known limitations
- demo script
- MVP 이후 실제 구현한 M5 기능 목록
- 기능별 baseline·개선 결과
- 미완료 확장 기능과 제외 이유

---

# 18. 최종 Definition of Done

프로젝트는 다음을 모두 만족해야 완료다.

## 체크포인트 1

- [ ] 지원 종목 3개
- [ ] 뉴스·공시·리포트 3종
- [ ] resolver·routing·hard filter
- [ ] Evidence·locator
- [ ] freshness
- [ ] provider 오류 구분
- [ ] abstention
- [ ] 단일 응답 API
- [ ] golden set

## 체크포인트 2

- [ ] 핵심 요약
- [ ] 사실·해석·추론
- [ ] 위험·불확실성
- [ ] glossary
- [ ] 근거 상세
- [ ] 오류·누락·stale
- [ ] 익명 멀티턴

## 체크포인트 3

- [ ] 로그인 없이 전체 시연
- [ ] 부가 기능 때문에 핵심 흐름 지연 없음
- [ ] P1 미완성 기능이 P0를 막지 않음
- [ ] 배포·실행 1안
- [ ] 사용자가 코드 흐름 설명

## 품질

- [ ] Critical set 100%
- [ ] full golden set 90% 이상
- [ ] wrong-company 0건
- [ ] 가짜 locator 0건
- [ ] 무한 대기 0건
- [ ] 문서·코드 일치
- [ ] P0 추적 gate 통과

---

# 19. M0에서 확정할 결정 목록

아래 항목만 M0 종료 시 실제 값으로 잠근다.

1. 지원 종목 3개 — 삼성전자·SK하이닉스·현대자동차
2. 뉴스 provider
3. MarketSnapshot provider의 feasibility와 A15-M stretch 후보 유지 여부
4. Streamlit 실행 구조
5. 단일 LLM provider
6. 배포 위치
7. 리포트 사용 가능 목록
8. lexical retrieval baseline 구현체
9. critical/full golden set 실제 질문
10. Phase별 실제 달력 날짜

M0 이후 새로운 기술·기능을 추가하려면 기존 P0 완료 일정에 영향이 없는지 먼저 확인한다.

---

# 20. 최종 실행 원칙

```text
3개 종목의 안정적 근거 기반 답변을 먼저 완성한다.
모든 Phase에서 작은 전체 흐름을 유지한다.
외부 API가 실패해도 전체 앱을 실패시키지 않는다.
검색 결과가 있다고 무조건 답하지 않는다.
근거 없는 숫자·URL·투자 조언을 차단한다.
P0 완료 전 로그인과 고도화 기능을 시작하지 않는다.
MVP를 조기에 완료하면 남은 세션을 M5 확장 큐에 순차 투자한다.
확장 기능 때문에 Critical set·배포 안정성이 깨지면 즉시 MVP로 복귀한다.
일정이 부족하면 기능보다 정확성·근거·재현성을 보존한다.
```
