# TASK CARD - M1-04 NewsProvider

## 1. 계획 연결
- Task bundle: B2
- Step: M1-04 NewsProvider
- 우선순위: P0
- 구현 기준 commit: `f9bf35bde1d7929eb96d9a897c244ad906e1255a`
- 관련 위험 ID: R02, R09, R15, R16, R17, R18, R19, R25, R54
- 관련 taxonomy: source_selection, provider_timeout, provider_rate_limit, stale_data, wrong_company, entity_resolution

## 2. 목적
지원 종목 3개에 대해 뉴스 provider 결과를 기존 `ProviderResult`와 `FinancialDocument` 계약으로 정규화한다. M1-04는 뉴스 원천만 다루며, provider가 반환한 기사 제목·날짜·URL·locator·snippet을 안전한 문서 형태로 보존한다.

M1-04에서는 `RecordedNewsProvider`만 구현한다. NAVER API HUB News 형식의 recorded fixture를 `FinancialDocument`로 정규화하고 상태 mapping을 검증한다. 실제 HTTP 요청, credential 사용, legacy NAVER Developers endpoint, live NAVER API HUB adapter는 구현하지 않는다.

## 3. 실제 확인한 현재 상태
- 확인 파일:
  - `docs/agent_handoff/PROJECT_PLAN_FINAL_PASS.md`
  - `docs/TASK_CARDS/B0-M0-01-03-planning.md`
  - `docs/agent_handoff/FINANCIAL_CAPABILITY_BASELINE.md`
  - `docs/agent_handoff/RISK_RESPONSE_MATRIX.md`
  - `docs/agent_handoff/STOCK_SCOPE_CHANGE_NOTICE.md`
  - `docs/TASK_CARDS/M1-02-security-resolver.md`
  - `docs/TASK_CARDS/M1-03-provider-result-config-fake.md`
  - `.env.example`
  - `app/core/models.py`
  - `app/providers/base.py`
- 확인 class·function:
  - `app.core.models.FinancialDocument`
  - `app.core.models.ProviderResult`
  - `app.core.models.SecurityIdentifier`
  - `app.core.models.DateRange`
  - `app.core.status.ProviderStatus`
  - `app.providers.base.create_provider_result`
  - `app.providers.base.fetch_with_policy`
  - `app.config.ProviderConfig`
- 현재 동작:
  - M1-01 PASS
  - M1-02 PASS
  - M1-03 PASS, 보완 SHA `f9bf35bde1d7929eb96d9a897c244ad906e1255a`
  - provider 공통 factory·retry·deadline·cache·config·fake provider 존재
  - `RecordedNewsProvider` 구현 완료, 사용자 검수 전
- 미확인 사항:
  - 실제 NAVER credential 값
  - 현재 NAVER 뉴스 API endpoint·응답 schema·quota의 공식 최신 상태
  - live API 호출 결과
  - 종목별 실제 뉴스 coverage

## 4. 선행 조건
- [x] M1-02 `SecurityResolver` PASS
- [x] M1-03 provider base/config/fake PASS
- [x] 지원 종목 3개 scope 확정
- [x] M1-04 구현 승인
- [ ] live NAVER 호출 별도 승인, M1-04에서는 사용하지 않음
- [ ] commit/push 별도 승인

## 5. 입력·출력
- 입력:
  - canonical `SecurityIdentifier`
  - optional query
  - optional `DateRange`
  - attempt timeout
- 출력:
  - `ProviderResult[list[FinancialDocument]]`
  - `status=ok`이면 `FinancialDocument` 목록 필수
  - `status=no_data`이면 data `None`
  - 실패 상태는 M1-03 중앙 factory 불변조건을 따른다.

`ProviderConfig`는 `RecordedNewsProvider.fetch()` 입력에 넣지 않는다. retry, deadline, cache는 M1-03 `fetch_with_policy()`가 담당하며 M1-04에서 재구현하지 않는다.

## 5.1 고정 이름
- class: `RecordedNewsProvider`
- provider key: `recorded_news`
- `FinancialDocument.provider`: `recorded_news`
- `ingestion_version`: `news-provider-m1-04-v1`

## 6. 지원 종목 hard mapping
NewsProvider는 provider 호출 전 종목을 다시 추론하지 않는다. 입력은 M1-02에서 확정된 canonical security만 받는다.

| security_id | ticker | security_name | query seed |
|---|---:|---|---|
| `KRX:005930` | `005930` | 삼성전자 | `삼성전자` |
| `KRX:000660` | `000660` | SK하이닉스 | `SK하이닉스` |
| `KRX:005380` | `005380` | 현대자동차 | `현대자동차` |

- unsupported/ambiguous/not_found 입력은 M1-02 책임이며 NewsProvider에서 처리하지 않는다.
- query가 `None`이면 canonical 종목명을 사용한다.
- explicit blank query는 `invalid_query`.
- explicit query에 canonical 이름이나 허용 alias가 이미 있으면 seed를 중복 추가하지 않는다.
- ambiguous group name인 `삼성`, `SK`, `현대`는 entity 판정이나 mention attribution에 사용하지 않는다.
- 사용자 query가 종목명·허용 alias를 포함하지 않으면 canonical 종목 seed를 앞에 붙인다.

## 7. 문서 정규화 계약
뉴스 결과는 `FinancialDocument`로 정규화한다.

- `source_type`: `news`
- `provider`: `recorded_news`
- `primary_security_ids`:
  - title에 명시된 지원 종목
  - title에 두 종목 이상이 나오면 해당 종목들을 모두 primary
  - title에 지원 종목이 없고 description에 질문 종목이 있으면 질문 종목
- `mentioned_security_ids`:
  - description에만 나온 지원 종목 중 질문 종목 primary와 중복되지 않는 종목
  - description에 질문 종목과 다른 지원 종목이 함께 나오면 질문 종목은 primary, 다른 지원 종목은 mentioned
  - primary와 중복 금지
- `title`: HTML tag 제거 후 비어 있지 않아야 함
- `description`: 선택 필드이며 HTML tag 제거 후 text에 결합
- `published_at`: `pubDate`를 timezone-aware로 파싱해 UTC 저장
- `source_url` 우선순위:
  - valid `originallink`
  - valid `link`
  - 둘 다 없으면 `None`
  - URL fragment만 제거하고 path/query는 보존
  - scheme과 hostname은 소문자로 정규화
  - HTTP 80, HTTPS 443 기본 port는 제거
  - username/password가 포함된 URL과 invalid port는 거부
- `text`: title + snippet 기반 제한 text
- `locator`: 비어 있지 않은 dict
  - 예: `provider`, `source_url`, `published_at`, `raw_index`, `query`
- `ingestion_version`: `news-provider-m1-04-v1`
- local absolute path는 노출하지 않는다.
- `document_id`:
  - canonical URL 우선
  - URL이 없으면 normalized title + UTC `published_at`
  - SHA-256 기반 deterministic id
  - Python hash, raw index 단독, 실행 시각, 로컬 경로 금지
- title과 description 모두 HTML entity 해제, tag 제거, 공백 정규화.

## 8. Provider status 기준
- `ok`: normalized `FinancialDocument` 1개 이상
- `no_data`: provider가 정상 응답했지만 관련 기사 없음
- `timeout`: M1-03 timeout wrapper 또는 provider timeout fixture
- `rate_limited`: 429 또는 quota 관련 fixture
- `unauthorized`: credential 누락/invalid live response fixture
- `parse_error`: 필수 필드 파싱 실패 또는 응답 schema 불일치 fixture
- `provider_unavailable`: 네트워크/서비스 장애 fixture
- `invalid_query`: 비어 있거나 provider에 전달할 수 없는 query fixture

모든 결과는 M1-03 `create_provider_result` 경계를 통과한다.

Parse 정책:
- raw response가 dict가 아니면 `parse_error`.
- top-level `body.items` schema 오류는 `parse_error`.
- `items`가 원래 비어 있으면 `no_data`.
- 개별 item이 dict가 아니면 malformed item으로 제외.
- title은 실제 `str`일 때만 허용하며 `None`이나 숫자를 `str()`로 변환하지 않는다.
- description이 없거나 `None`/non-string이면 빈 문자열로 처리한다.
- title/pubDate가 잘못된 개별 item은 제외.
- 모든 item이 malformed이면 `parse_error`.
- 유효 item이 관련성 또는 date filter에서 모두 제외되면 `no_data`.

## 9. 중복·관련성 기준
- 중복 최소 제거 key:
  - canonicalized `source_url` 우선
  - 없으면 normalized title + published_at
- 같은 기사 중복은 1개만 유지한다.
- 중복 시 API 순서상 첫 항목 유지.
- title에 지원 종목이 없고 description에 질문 종목이 있으면 질문 종목을 primary로 둔다.
- description에 질문 종목과 다른 지원 종목이 함께 있으면 질문 종목은 primary, 다른 종목은 mentioned로 둔다.
- title에 질문 종목이 없고 description에만 질문 종목이 나오며 title 중심 종목이 다른 지원 종목이면 wrong-company로 제외한다.
- ambiguous group name만 있는 기사는 지원 종목 mention으로 보지 않고 제외한다.
- 삼성전자·SK하이닉스 공동 제목에서는 둘 다 primary로 둔다.
- primary/mentioned 중복 금지.
- mention lexicon은 `data/securities.json`의 canonical name·aliases에서 파생하고, `ambiguous_terms`는 기사 귀속에 사용하지 않는다.

## 9.1 DateRange
- `DateRange`를 무시하지 않는다.
- `published_at`을 Asia/Seoul 날짜로 변환해 비교한다.
- `start`/`end` inclusive.
- date filter 결과가 없으면 `no_data`.

## 9.2 synthetic fixture와 실제 coverage
- synthetic fixture는 unit test 증거다.
- 실제 coverage는 종목별 중복 제거 후 10건 이상, 최근 30일 우선, 실제 URL 필요.
- 실제 자료가 없으면 coverage를 `NOT_RUN` 또는 `BLOCKED`로 기록한다.
- synthetic fixture를 real coverage로 표시하지 않는다.

## 9.3 확장성 계약
- NAVER API HUB 응답 정규화 로직은 `RecordedNewsProvider`에 종속시키지 않고 transport-independent 순수 함수로 구현한다.
- `RecordedNewsProvider`와 향후 `NaverApiHubNewsProvider`는 동일한 M1-03 Provider protocol을 구현한다.
- 두 provider는 동일한 query builder, response parser, attribution, dedupe 함수를 사용한다.
- shared normalizer는 `provider_key`와 `ingestion_version`을 인자로 받으며 `recorded_news`를 내부에 hard-code하지 않는다.
- 향후 live adapter는 constructor/factory로 credential과 HTTP transport를 주입받는다.
- `Provider.fetch` signature와 `fetch_with_policy` 계약은 변경하지 않는다.

## 10. 수정 범위
- 수정 가능:
  - `app/providers/news.py`
  - `tests/unit/test_news_provider.py`
  - `tests/fixtures/news/*.json`
  - 필요 시 `app/providers/__init__.py`
  - 필요 시 `.env.example`
  - 필요 시 `docs/TASK_CARDS/M1-04-news-provider.md`
- 수정 금지:
  - M1-01 core model field와 status enum 변경
  - M1-02 `SecurityResolver` 구조 변경
  - M1-03 provider base/config/fake 구조 재작성
  - OpenDART DisclosureProvider 구현
  - retrieval 구현
  - API route
  - UI
  - LLMStatus, LiteLLM, Gemini code
  - actual HTTP request
  - credential 사용
  - legacy NAVER Developers endpoint 구현
  - live NAVER API HUB adapter 구현
  - live API 호출을 unit test 완료 조건으로 사용
  - secret 값 기록

## 11. 구현 순서
1. NAVER API HUB News 형식의 recorded fixture schema를 정한다.
2. 삼성전자/SK하이닉스/현대자동차 정상 fixture를 추가한다.
3. no-data, timeout, rate_limited, unauthorized, parse_error, provider_unavailable fixture를 추가한다.
4. `app/providers/news.py`에 `RecordedNewsProvider`를 구현한다.
5. raw response를 `FinancialDocument`로 변환하는 transport-independent pure helper를 구현한다.
6. HTML tag 제거, URL 검증, timezone-aware `published_at`, locator 생성, dedup을 테스트한다.
7. wrong-company와 공동 기사 primary/mentioned 분리 테스트를 추가한다.
8. M1-03 provider wrapper와 함께 targeted/regression/smoke를 실행한다.
9. live NAVER 검증은 credential과 별도 승인 없으면 `NOT_RUN — 승인 범위 제외`로 기록한다.

## 12. 테스트 계획
- 정상:
  - 삼성전자 recorded news -> `ok`, `FinancialDocument.source_type == "news"`
  - SK하이닉스 recorded news -> `ok`
  - 현대자동차 recorded news -> `ok`
- 필드:
  - `published_at` timezone-aware
  - `source_url` HTTP(S) 또는 `None`
  - `locator` non-empty
  - `primary_security_ids` 질문 종목 포함
  - `ingestion_version` 존재
- 중복:
  - 동일 URL 중복 제거
  - URL 없을 때 title + published_at 중복 제거
  - 동일 fixture 재실행 결과 동일
- 관련성:
  - 질문 종목 미언급 무관 기사 제외
  - 공동 제목 두 종목 모두 primary
  - 타사 전용 뉴스가 질문 종목 primary로 들어가지 않음
  - ambiguous 그룹명만 있는 기사 제외
- 상태:
  - no-data fixture -> `ProviderStatus.NO_DATA`
  - timeout fixture -> `ProviderStatus.TIMEOUT`
  - rate-limit fixture -> `ProviderStatus.RATE_LIMITED`
  - unauthorized fixture -> `ProviderStatus.UNAUTHORIZED`
  - parse-error fixture -> `ProviderStatus.PARSE_ERROR`
  - provider-unavailable fixture -> `ProviderStatus.PROVIDER_UNAVAILABLE`
- security:
  - provider는 canonical `SecurityIdentifier`만 입력받음
  - mismatched `SecurityIdentifier` invalid_query
  - unsupported/ambiguous query 처리 없음
- 추가 필수:
  - deterministic document_id
  - originallink 우선/link fallback
  - query seed 중복 방지
  - HTML tag/entity 제거
  - malformed 일부 제외와 전부 malformed 구분
  - DateRange 양 끝 포함
- regression:
  - M1-01/M1-02/M1-03 unit tests 유지

## 13. 완료 기준
- [x] 지원 종목 3개 hard mapping 사용
- [x] `published_at` timezone-aware 보존
- [x] `source_url`와 `locator` 보존
- [x] `FinancialDocument` 정규화 테스트 통과
- [x] deterministic document_id 테스트 통과
- [x] originallink 우선/link fallback 테스트 통과
- [x] query seed 중복 방지 테스트 통과
- [x] mismatched `SecurityIdentifier` 테스트 통과
- [x] HTML tag/entity 제거 테스트 통과
- [x] malformed 일부 제외와 전부 malformed 구분 테스트 통과
- [x] DateRange 양 끝 포함 테스트 통과
- [x] 중복 최소 제거 테스트 통과
- [x] 정상·no-data·timeout fixture 통과
- [x] rate_limited·unauthorized·parse_error·provider_unavailable fixture 통과
- [x] synthetic 종목별 recorded fixture 존재
- [ ] 실제 coverage 종목별 10건 이상 검증
- [x] wrong-company fixture 통과
- [x] description-only 질문 종목 primary attribution 테스트 통과
- [x] description-only 질문 종목 primary 및 다른 지원 종목 mentioned 테스트 통과
- [x] `security_type` 포함 canonical security validation 테스트 통과
- [x] unsupported ticker 및 preferred_stock 입력 테스트 통과
- [x] raw response non-dict 및 non-dict item parser 경계 테스트 통과
- [x] title non-string 제외 및 description non-string 빈 문자열 처리 테스트 통과
- [x] URL scheme/host 소문자, default port 제거, userinfo/invalid port 거부 테스트 통과
- [x] host 대소문자와 default port 차이 URL dedupe 테스트 통과
- [x] URL 없는 normalized title + published_at dedupe 테스트 통과
- [x] shared normalizer provider_key/ingestion_version 주입 테스트 통과
- [x] 공동 제목 두 primary 테스트 통과
- [x] ambiguous 그룹명만 있는 기사 제외 테스트 통과
- [x] 동일 fixture 재실행 동일 결과 테스트 통과
- [x] M1-03 provider factory/cache/timeout 계약 회귀 없음
- [x] live API 없이 unit test 통과

## 14. 검증
- targeted unit:
```powershell
$env:PYTHONPATH = ".test_deps;."; python -m pytest tests/unit/test_news_provider.py -q
```
- regression:
```powershell
$env:PYTHONPATH = ".test_deps;."; python -m pytest tests/unit/test_core_models.py tests/unit/test_status_contracts.py tests/unit/test_security_resolver.py tests/unit/test_provider_base.py tests/unit/test_config.py tests/unit/test_news_provider.py -q
```
- smoke:
```powershell
$env:PYTHONPATH = ".test_deps;."; python -c "from app.providers.news import RecordedNewsProvider; print('ok')"
```
- live NAVER 검증: `NOT_RUN — 승인 범위 제외`
- legacy NAVER Developers endpoint: `NOT_RUN — 승인 범위 제외`
- GitHub CI: 별도 확인 전 `NOT_RUN`

## 15. fallback·rollback 제안
- live NAVER credential이 없으면 recorded fixture만 사용한다.
- NAVER coverage가 부족하면 수동 검수 뉴스 manifest를 fallback으로 둔다.
- snippet만으로 관련성 판정이 흔들리면 title/source_url 중심으로 축소하고 무관 기사는 제외한다.
- provider schema가 흔들리면 raw item 저장을 늘리지 않고 normalized fixture를 우선한다.

## 16. 중단 기준
- live API credential 값이 코드/문서/로그에 필요해지는 경우
- actual HTTP request가 필요해지는 경우
- M1-03 `ProviderResult` field 또는 `ProviderStatus` enum 변경이 필요해지는 경우
- retrieval/API/UI/LLM 구현이 필요해지는 경우
- OpenDART DisclosureProvider를 함께 구현해야 하는 경우
- NAVER API 공식 문서와 기존 전제가 달라 live adapter 설계를 바꿔야 하는 경우
- 뉴스 본문 전문 수집, 크롤링, 저작권 불명 자료 저장이 필요해지는 경우

## 17. 승인
- 승인 일시: 2026-07-21
- 승인 범위: M1-04 Task Card 보완 후 `RecordedNewsProvider` 구현 승인
- Git 작업 승인 포함 여부: 기본 `아니오`

## 18. 구현 결과 기록
- 기록 일시: 2026-07-21
- 구현 기준 commit: `f9bf35bde1d7929eb96d9a897c244ad906e1255a`
- 최초 구현 SHA: `751274529f0948e489655694ab64c0d642f57078`
- 최초 구현 main push: 완료, 사용자 검수 목적
- 사용자 검수 판정: `CONDITIONAL PASS`
- 보완 SHA: 미생성, 사용자 별도 승인 전 commit/push 미수행
- 구현 범위:
  - `RecordedNewsProvider` only
  - NAVER API HUB News 형식 recorded fixture
  - transport-independent query builder·response parser·attribution·dedupe normalizer
  - raw response -> `FinancialDocument` 정규화
  - M1-03 `create_provider_result` 상태 mapping
- 제외 범위:
  - actual HTTP request: NOT_RUN
  - credential 사용: NOT_RUN
  - legacy NAVER Developers endpoint: NOT_RUN
  - live NAVER API HUB adapter: NOT_RUN
  - M1-05 DisclosureProvider: NOT_RUN
  - retrieval/API/UI/LLM: NOT_RUN
- synthetic fixture:
  - `tests/fixtures/news/naver_api_hub_synthetic.json`
  - unit test 증거로만 사용
  - real coverage로 표시하지 않음
- 실제 coverage:
  - 종목별 중복 제거 후 10건 이상, 최근 30일 우선, 실제 URL 기준 검증: `NOT_RUN — 승인 범위 제외`
- 실제 테스트 결과:
  - PYTHONPATH: `.test_deps;.`
  - targeted unit 명령: `python -m pytest tests/unit/test_news_provider.py -q`
  - targeted unit exit code: `0`
  - targeted unit 출력: `25 passed in 0.13s`
  - regression 명령: `python -m pytest tests/unit/test_core_models.py tests/unit/test_status_contracts.py tests/unit/test_security_resolver.py tests/unit/test_provider_base.py tests/unit/test_config.py tests/unit/test_news_provider.py -q`
  - regression exit code: `0`
  - regression 출력: `139 passed in 0.28s`
  - smoke 명령: `python -c "from app.providers.news import RecordedNewsProvider; print('ok')"`
  - smoke exit code: `0`
  - smoke 출력: `ok`
- live NAVER 검증: `NOT_RUN — 승인 범위 제외`
- GitHub CI: `NOT_RUN`
- 독립 검수 환경 재실행: `NOT_RUN`
- 독립 검수 판정: `CONDITIONAL PASS`
- M1-04 상태: 보완 구현 완료, 사용자 재검수 전

## 19. CONDITIONAL PASS 보완 결과 기록
- 기록 일시: 2026-07-22
- 최초 구현 SHA: `751274529f0948e489655694ab64c0d642f57078`
- 최초 구현 main push: 완료, 사용자 검수 목적
- 사용자 검수 판정: `CONDITIONAL PASS`
- 보완 SHA: 미생성, 사용자 별도 승인 전 commit/push 미수행
- 보완 범위:
  - description-only 질문 종목 attribution을 primary로 수정
  - description에 질문 종목과 다른 지원 종목이 함께 있을 때 질문 종목 primary, 다른 종목 mentioned 처리
  - `NewsSecurityRecord.security_type` 추가 및 `data/securities.json` 기반 canonical security validation 강화
  - P0 `common_stock`만 허용
  - raw response non-dict, non-dict item, title non-string, description non-string parser 경계 강화
  - URL scheme/host 소문자 정규화, default port 제거, userinfo/invalid port 거부
  - shared normalizer가 `provider_key`와 `ingestion_version`을 인자로 반영하는 확장성 계약 테스트
  - URL 없는 normalized title + UTC `published_at` dedupe 테스트
- 구현 환경 테스트:
  - PYTHONPATH: `.test_deps;.`
  - targeted unit 명령: `python -m pytest tests/unit/test_news_provider.py -q`
  - targeted unit exit code: `0`
  - targeted unit 출력: `37 passed in 0.17s`
  - regression 명령: `python -m pytest tests/unit/test_core_models.py tests/unit/test_status_contracts.py tests/unit/test_security_resolver.py tests/unit/test_provider_base.py tests/unit/test_config.py tests/unit/test_news_provider.py -q`
  - regression exit code: `0`
  - regression 출력: `151 passed in 0.27s`
  - smoke 명령: `python -c "from app.providers.news import RecordedNewsProvider, normalize_naver_api_hub_news_response; print('ok')"`
  - smoke exit code: `0`
  - smoke 출력: `ok`
- live NAVER 검증: `NOT_RUN — 승인 범위 제외`
- legacy NAVER Developers endpoint: `NOT_RUN — 승인 범위 제외`
- live NAVER API HUB adapter: `NOT_IMPLEMENTED — 승인 범위 제외`
- live adapter 상태: `PLANNED/NOT_IMPLEMENTED`
- 실제 뉴스 coverage 종목별 10건 이상: `NOT_RUN — 승인 범위 제외`
- GitHub CI: `NOT_RUN`
- 독립 검수 환경 재실행: `NOT_RUN`
- M1-05 구현: `NOT_RUN — M1-04 보완 재검수 PASS 전 시작 금지`
