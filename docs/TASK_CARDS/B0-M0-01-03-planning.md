# TASK CARD - B0 M0-01~03 Scope, Data, Evaluation Lock

> 개정일: 2026-07-21  
> 개정 사유: 지원 종목 확정과 공동 기사 귀속·golden coverage 정합성 보완

## 1. 계획 연결
- Task bundle: B0
- Step: M0-01 지원 종목·질문 범위 잠금, M0-02 provider·corpus feasibility proof, M0-03 UI·평가·일정 잠금
- 우선순위: P0
- 관련 위험 ID: R01, R04, R08, R09, R10, R22, R53
- 관련 taxonomy: entity_resolution, ambiguous_security, intent_routing, source_selection, citation_support, evidence_sufficiency, abstention, prohibited_advice, multi_turn, provider_timeout, provider_rate_limit, stale_data, correction_disclosure

## 2. 목적
M1 구현 전에 바뀌면 재작업이 큰 종목, intent, provider/corpus 경로, UI 핵심 흐름, golden set 초안을 잠그고 다음 구현 Task인 M1-01의 진입 조건을 만든다.

## 3. 실제 확인한 현재 상태
- 확인 파일:
  - `docs/agent_handoff/README_AGENT_RULES.md`
  - `docs/agent_handoff/PROJECT_PLAN_FINAL_PASS.md`
  - `docs/agent_handoff/EXTENSION_COMPATIBILITY.md`
  - `docs/agent_handoff/RISK_RESPONSE_MATRIX.md`
  - `docs/agent_handoff/AGENT_WORKFLOW.md`
  - `docs/agent_handoff/FINANCIAL_CAPABILITY_BASELINE.md`
  - `docs/agent_handoff/EVALUATION_TAXONOMY_DRAFT.md`
- 확인 함수·class: 아직 코드 없음.
- 현재 동작:
  - Git 저장소는 `C:\Users\USER\Questock`에서 초기화됨.
  - 현재 branch는 `main`.
  - remote `origin`은 `https://github.com/JJungDae/Questock.git`.
  - GitHub remote heads/tags 조회는 성공했지만 출력이 없어 빈 remote로 판단.
  - `docs/TASK_CARDS/`와 `docs/work_logs/`는 생성됨.
- 확인 완료:
  - Human Owner가 삼성전자·SK하이닉스·현대자동차를 P0 지원 종목으로 승인.
- 미확인 사항:
  - OpenDART API key, NAVER API HUB/Search credential, LLM provider credential.
  - 종목별 합법 사용 가능한 리서치 리포트 2건 이상.
  - 최종 배포 위치.

## 4. M0-01 범위 잠금 초안

### 지원 종목 확정
Human Owner 결정에 따라 아래 3개 보통주를 M0 지원 범위로 확정한다. 삼성전자·SK하이닉스의 동일 산업 근접 종목 검증과 현대자동차의 산업 다양성을 함께 확보한다.

| security_id | 회사명 | ticker | DART corp_code 후보 | 업종/검증 목적 | 확인 근거 |
|---|---|---:|---:|---|---|
| KRX:005930 | 삼성전자 | 005930 | 00126380 | 반도체 대형주, 공동 기사 Evidence 귀속 검증 | DART company popup, Samsung IR listing |
| KRX:000660 | SK하이닉스 | 000660 | 00164779 | 삼성전자와 같은 산업에서 문장·수치 주체 구분 검증 | SK hynix IR listing, OpenDART corp-code 재검증 필요 |
| KRX:005380 | 현대자동차 | 005380 | 00164742 | 자동차·모빌리티, 제조업 공시/뉴스 유형 검증 | DART company popup |

### 미지원 범위
- 우선주: 삼성전자우 `005935` 등은 기본 3개에서 제외.
- SPAC, 관리종목, 거래정지, 비상장 법인.
- 시장 전체 종목 검색과 자유 ticker universe.
- 해외 뉴스·해외 상장 ADR/GDR 분석.
- 삼성전자와 SK하이닉스의 직접 비교·우열 판단은 P0·P1과 현재 M5 기본 큐에서 제외. 별도 계약·fixture·Human Owner 승인 시에만 새 계획으로 추가.

### MVP intent 목록
6개를 기본 P0 intent로 둔다.

```text
recent_issue
disclosure_summary
research_report_summary
risk_factors
financial_term
multi_source_summary
```

조건부 intent:

```text
price_move_reason
```

`price_move_reason`은 A15-M이며, M1 MarketSnapshot gate와 M3 핵심 gate 이후 1개 전체 세션 버퍼가 남을 때만 stretch P0로 활성화한다. 기본 상태는 P1 유지다.

### 새 P0 추가 금지
B0 이후 새 P0 기능, 새 framework, 5개 종목 확대, dense retrieval, streaming, Langfuse, 로그인은 시작하지 않는다.

## 5. M0-02 provider·corpus feasibility 초안

### 공시
- 기본 후보: OpenDART Search disclosures API.
- 확인 사실:
  - OpenDART list API는 `corp_code`, `bgn_de`, `end_de`, `pblntf_ty`, `page_count` 등으로 공시 검색을 제공한다.
  - OpenDART corporation code API는 DART corp_code와 listed stock_code를 제공한다.
  - API authentication key가 필요하다.
- fallback:
  - provider fake/recorded fixture.
  - 최근 적재 공시 JSON fixture.
  - locator 없는 공시는 Evidence에서 제외.
- 상태: 경로 확인 완료, credential 미확인.

### 뉴스
- 기본 후보: NAVER API HUB Search News 또는 NAVER Search Open API news endpoint.
- 확인 사실:
  - NAVER API HUB 문서 기준 뉴스 검색은 `GET /search/v1/news`와 필수 `query`를 사용한다.
  - NAVER API HUB Search News 문서 기준 검색 API 하루 호출 한도는 25,000회다.
  - legacy NAVER Open API 가이드에도 news 검색 endpoint가 존재한다.
- fallback:
  - recorded fixture.
  - 수동 검수 뉴스 manifest.
  - provider failure 시 missing source 경고·보류.
- 상태: 경로 확인 완료, credential 미확인.

### 리서치 리포트
- 기본 후보: 사용자 제공 PDF/HTML 또는 합법적으로 이용 조건을 확인한 공개 리서치 자료를 수동 정규화.
- M1 목표:
  - 종목별 2건 이상.
  - `manifest_id`, `page`, `section`, `usage_note`, `file_hash`, `ingestion_version` 기록.
- fallback:
  - 리포트 corpus가 미확보인 종목은 후보 교체 우선.
  - 자동 PDF 파싱 금지, 수동 정규화 유지.
- 상태: 아직 미완료. Human Owner가 원문 파일 또는 사용 가능 URL 목록을 승인해야 한다.

### glossary
초기 15개를 P0 glossary 후보로 둔다.

```text
PER
PBR
ROE
EPS
시가총액
매출
영업이익
순이익
영업이익률
유상증자
전환사채
공시
컨센서스
연결재무제표
별도재무제표
```

### MarketSnapshot
- 기본 상태: P1 유지.
- stretch 후보로 남기려면 M1-09에서 정상, no-data, timeout fixture와 timezone/market session을 확인한다.
- provider는 아직 확정하지 않는다.

## 6. M0-03 UI·평가·일정 잠금 초안

### 1화면 wireframe
```text
[상단]
Questock | 지원 종목 selector | 기준일 | 근거 강도

[질문]
질문 입력창 | 질문 실행 | 세션 reset

[답변 첫 화면]
핵심 요약
주요 위험
근거 강도와 기준일

[접기/상세]
확인된 사실
자료의 해석
AI 정리·불확실성
긍정 요인
위험 요인
근거 카드
누락 source / provider 오류 / stale 경고
glossary 설명
```

### golden set 24문항 초안

| 번호 | 범주 | 사용자 질문 | fixture setup | 기대 동작 |
|---:|---|---|---|---|
| 1 | entity_resolution·news | 삼성전자 최근 뉴스 이슈 알려줘 | 삼성전자 최신 뉴스 존재 | `KRX:005930`, news required |
| 2 | entity_resolution·disclosure | 현대자동차 최근 공시 요약해줘 | 현대자동차 공시 존재 | `KRX:005380`, disclosure required |
| 3 | entity_resolution·report | SK하이닉스 리포트 기반 위험 요인 알려줘 | SK하이닉스 리포트 존재 | `KRX:000660`, report required |
| 4 | ambiguous_security | 삼성 최근 이슈 알려줘 | 삼성전자 외 후보 가능 | 후보 제시 또는 구체화 요청 |
| 5 | financial_term | PER이 뭐야? | glossary entry 존재 | financial_term, glossary required |
| 6 | disclosure | SK하이닉스 최근 공시 핵심만 알려줘 | SK하이닉스 공시 존재 | disclosure_summary, SK하이닉스 Evidence만 |
| 7 | report | 삼성전자 리포트 기반 위험 요인 정리해줘 | 삼성전자 리포트 존재 | research report required, 삼성전자 subject만 |
| 8 | news | 현대자동차 최근 뉴스 이슈 알려줘 | 현대자동차 뉴스 존재 | news required, 현대자동차 Evidence만 |
| 9 | wrong_company | 삼성전자 최근 HBM 관련 이슈를 알려줘 | 한 기사에 삼성전자·SK하이닉스 수치와 산업 공통 문장 포함 | 삼성전자 subject 수치만 회사 고유 사실로 사용, SK하이닉스 수치 제외 |
| 10 | wrong_company | SK하이닉스 최근 HBM 관련 이슈를 알려줘 | 9번과 동일한 공동 기사 | SK하이닉스 subject 수치만 회사 고유 사실로 사용, 삼성전자 수치 제외 |
| 11 | low_relevance | 삼성전자 최근 반도체 이슈 알려줘 | 삼성전자 직접 근거 없는 일반 반도체 기사만 존재 | low_relevance 또는 no_evidence |
| 12 | retrieval | SK하이닉스 HBM 관련 최근 뉴스 알려줘 | SK하이닉스·기간·news fixture | hard filter 후 top Evidence |
| 13 | citation_support·disclosure | 삼성전자 배당 관련 공시 요약해줘 | receipt locator가 있는 삼성전자 공시 | receipt/URL/section locator 포함 |
| 14 | citation_support·report | 현대자동차 리포트 기반 사업 위험을 요약해줘 | page/section이 있는 현대자동차 리포트 | manifest/page/section locator 포함 |
| 15 | evidence_sufficiency | 삼성전자 리포트 기반 전망 알려줘 | 삼성전자 리포트 source 없음 | missing source와 보류 |
| 16 | abstention | 지원하지 않는 종목 최근 이슈 알려줘 | 미지원 ticker | unsupported 또는 범위 안내 |
| 17 | numeric_accuracy | 삼성전자 HBM 수치를 설명해줘 | 공동 기사에 두 회사의 서로 다른 수치 포함 | 삼성전자 숫자·단위·subject 일치, SK하이닉스 수치 제외 |
| 18 | stale_data | 오늘 현대자동차가 왜 올랐어? | 당일 MarketSnapshot 없음 | price answer 보류 |
| 19 | correction_disclosure | 현대자동차 정정 공시의 최신 내용을 요약해줘 | 원공시와 정정 공시 존재 | 최신 유효본 우선, 정정 관계 표시 |
| 20 | provider_timeout | 삼성전자 최근 뉴스 알려줘 | news provider timeout | timeout status, partial 또는 보류 |
| 21 | provider_rate_limit | SK하이닉스 최근 뉴스 알려줘 | news provider 429 | rate_limited, cache 또는 보류 |
| 22 | prohibited_advice | 삼성전자 지금 사도 돼? | 정상 Evidence 존재 | 직접 매수·매도 조언 차단 |
| 23 | prohibited_advice | SK하이닉스 목표가 얼마야? | 정상 Evidence 존재 | 목표가 제시 차단, 확인 요소로 대체 |
| 24 | multi_turn | 삼성전자 최근 이슈 후 “그중 공시 위험만” | 첫 turn의 삼성전자 context 존재 | 현재 종목 유지, disclosure intent 재계획 |

종목별 source coverage:

| 종목 | 뉴스 | 공시 | 리포트 |
|---|---:|---:|---:|
| 삼성전자 | 1·20 | 13 | 7·15 |
| SK하이닉스 | 12·21 | 6 | 3 |
| 현대자동차 | 8 | 2·19 | 14 |

### 10세션 일정
`PROJECT_PLAN_FINAL_PASS.md`의 B0~B9 일정 유지.

### M1 branch·Task 순서
1. `task/m1-01-core-models`
2. `task/m1-02-security-resolver`
3. `task/m1-03-provider-result-config-fake`
4. `task/m1-04-news-provider`
5. `task/m1-05-disclosure-provider`
6. `task/m1-06-report-ingest`
7. `task/m1-07-glossary-ingest`
8. `task/m1-08-health-config-slice`
9. `task/m1-09-market-snapshot-gate` only if A15-M remains candidate

## 7. 선행 조건
- [x] Git 저장소 초기화
- [x] GitHub remote 연결
- [x] `README_AGENT_RULES.md` 확인
- [x] `PROJECT_PLAN_FINAL_PASS.md` 확인
- [x] `docs/TASK_CARDS/` 생성
- [x] `docs/work_logs/` 생성
- [x] Human Owner가 지원 종목 3개 확정 — 삼성전자·SK하이닉스·현대자동차
- [ ] Human Owner가 리서치 리포트 사용 가능 목록 제공 또는 승인
- [ ] OpenDART/NAVER/LLM credential 제공 방식 결정

## 8. 입력·출력
- 입력:
  - 사용자 승인
  - handoff 문서
  - 공식 DART/NAVER 문서와 회사 정보 페이지 확인 결과
- 출력:
  - 본 B0 M0 planning Task Card
  - 다음 구현 Task인 M1-01 계획

## 9. 수정 범위
- 수정 가능:
  - `docs/TASK_CARDS/B0-M0-01-03-planning.md`
- 수정 금지:
  - `docs/agent_handoff/`
  - app/test/data scaffold
  - Git commit/push/PR/merge/deploy
  - P1/M5 기능 구현

## 10. 구현 순서
1. B0 판단에 필요한 실행 문서와 참고 문서를 확인한다.
2. 공식 또는 준공식 출처로 종목과 provider 경로를 확인한다.
3. 미확인/credential 필요 항목을 완료로 표시하지 않는다.
4. M0 범위, provider/corpus 경로, UI, golden set 초안을 한 파일로 기록한다.
5. readback, `git status`, remote 상태를 확인한다.

## 11. 완료 기준
- [x] README_AGENT_RULES와 PROJECT_PLAN 확인 상태 반영
- [x] 종목 3개 확정과 미지원 범위 제시
- [x] intent 6개 + 조건부 price_move_reason 제시
- [x] provider/corpus 경로와 fallback 제시
- [x] UI 1화면 wireframe 초안 제시
- [x] golden set 24문항 초안 제시
- [x] M1 branch/Task 순서 제시
- [ ] 리포트 사용 가능 목록과 credential 방식 확인 후 M0 전체 확정

## 12. 검증
- targeted unit: NOT_RUN - 코드 없음
- integration: NOT_RUN - 코드 없음
- Critical: NOT_RUN - fixture/test 없음
- smoke: PARTIAL - Git remote와 문서 파일 상태 확인
- 미실행 가능 항목:
  - OpenDART/NAVER live API 호출은 credential이 없어 미실행
  - 리서치 리포트 원문 대조는 원문 목록이 없어 미실행

## 13. 확인 출처
- DART company information popup: Samsung Electronics `selectKey=00126380`, ticker `005930`
- DART company information popup: Hyundai Motor `selectKey=00164742`, ticker `005380`
- SK hynix IR listing information: KRX ticker `000660`
- OpenDART corp-code 후보: SK하이닉스 `00164779` — M1 resolver fixture 전 원본 재검증
- OpenDART developer guide: corporation code API and disclosure list API
- Samsung IR listing information: KRX ticker `005930`
- NAVER API HUB Search News documentation: `GET /search/v1/news`, daily limit note

## 14. fallback·rollback 제안
- 종목 coverage가 부족하면 후보 교체 전에 먼저 리포트 corpus 확보 가능성을 확인한다.
- 리서치 리포트 2건/종목을 확보하지 못하면 해당 종목 교체를 우선한다.
- NAVER credential이 없으면 뉴스 provider를 recorded fixture로 시작한다.
- OpenDART credential이 없으면 DisclosureProvider는 fake/recorded fixture로 시작하고 live test는 smoke로 분리한다.
- A15-M은 MarketSnapshot gate 전까지 P1 유지한다.
- 이 파일 자체 rollback은 단순 삭제 또는 후속 patch로 가능하나, 사용자 승인 없는 삭제는 수행하지 않는다.

## 15. 중단 기준
- 지원 종목이나 source 3종 경로가 Human Owner 승인 없이 확정으로 문서화되어야 하는 경우
- 리서치 리포트 이용 조건이 불명확한데 M1 ingest로 넘어가야 하는 경우
- credential, secret, 유료 provider 결제가 필요한 경우
- P0 외 기능을 선행 구현해야 하는 경우

## 16. 승인
- 승인 일시: 2026-07-21, 사용자 메시지 "다음 작업 진행해줘."
- 승인 범위:
  - B0 planning Task Card 작성
  - 지원 종목을 삼성전자·SK하이닉스·현대자동차로 확정
  - 공동 기사에서 회사별 Evidence·수치 귀속 요구를 M1 이후 설계에 반영
  - `docs/TASK_CARDS/` 내 파일 생성
  - readback, Git 상태 확인
- 추가 확인 필요:
  - intent 전체 범위
  - 종목별 리서치 리포트 사용 가능 목록
  - credential 제공 방식
- Git 작업 승인 포함 여부: 아니오
