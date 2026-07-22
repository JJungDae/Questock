# TASK CARD - M1-05 DisclosureProvider

## 1. 계획 연결
- Task bundle: B2
- Step: M1-05 DisclosureProvider
- 우선순위: P0
- 구현 기준 commit: `192207e35c902aded50d43facc3c67393f2eb3b7`
- 선행 완료:
  - M1-01 core models/status contract: PASS
  - M1-02 SecurityResolver: PASS
  - M1-03 provider base/config/fake: PASS
  - M1-04 RecordedNewsProvider: PASS
- 관련 위험 ID: R02, R10, R11, R12, R15, R16, R17, R18, R23, R25, R54
- 관련 taxonomy: entity_resolution, source_selection, citation_support, stale_data, correction_disclosure, provider_timeout, provider_rate_limit

## 2. 목적
지원 종목 3개의 공시 데이터를 기존 `ProviderResult[list[FinancialDocument]]` 계약으로 정규화한다.

M1-05에서는 recorded OpenDART list API 형식 fixture를 사용하는 `RecordedDisclosureProvider`만 구현한다. 실제 HTTP 요청, OpenDART credential 사용, corporation-code live 재검증, live OpenDART adapter, NAVER live adapter, retrieval, API, UI, LLM 코드는 구현하지 않는다.

## 3. 실제 확인한 현재 상태
- 확인 문서:
  - `docs/agent_handoff/PROJECT_PLAN_FINAL_PASS.md`
  - `docs/agent_handoff/RISK_RESPONSE_MATRIX.md`
  - `docs/TASK_CARDS/B0-M0-01-03-planning.md`
  - `docs/TASK_CARDS/M1-02-security-resolver.md`
  - `docs/TASK_CARDS/M1-03-provider-result-config-fake.md`
  - `docs/TASK_CARDS/M1-04-news-provider.md`
- 확인 파일:
  - `app/core/models.py`
  - `app/core/status.py`
  - `app/core/resolver.py`
  - `app/providers/base.py`
  - `app/providers/news.py`
  - `app/config.py`
  - `data/securities.json`
  - `.env.example`
- 확인한 기존 계약:
  - `FinancialDocument`
  - `ProviderResult`
  - `SecurityIdentifier`
  - `DateRange`
  - `ProviderStatus`
  - `Provider` protocol
  - `create_provider_result`
  - `fetch_with_policy`
  - `security_id_for`
  - `normalize_query`
- 현재 미확정:
  - OpenDART API key 실제 값
  - OpenDART corporation-code 원본 ZIP/API 재검증 결과
  - 세 종목 `corp_code`의 `verified` 전환 여부
  - live OpenDART 응답 최신 schema
  - 실제 공시 coverage

## 4. 범위
### 구현 가능
- `RecordedDisclosureProvider`
- OpenDART list API 형식 recorded fixture
- transport-independent 순수 normalizer
- raw response -> `FinancialDocument` 정규화
- 공시 receipt locator 보존
- 정정 공시 식별 정보 보존
- 최신 유효본 미확정 계약과 receipt 기반 안정 정렬 검증
- M1-03 `create_provider_result` 기반 상태 mapping
- deterministic unit/regression/smoke test

### 구현 제외
- 실제 OpenDART HTTP 호출
- OpenDART credential 사용
- corporation-code live/API 재검증
- `data/securities.json`의 verification_status 변경
- live OpenDART adapter
- Live NAVER adapter
- legacy NAVER 기능
- 리서치 리포트 ingest
- retrieval/index/vector store
- API route
- UI
- LLMStatus, LiteLLM, Gemini 코드
- 기존 M1-01 model field 또는 `ProviderStatus` enum 변경
- M1-02 resolver 구조 변경
- M1-03 provider base/config/fake 구조 재작성
- M1-04 news provider 구조 재작성

## 5. 파일 위치
수정 예상 파일:
- `app/providers/disclosure.py`
- `app/providers/__init__.py`
- `tests/unit/test_disclosure_provider.py`
- `tests/fixtures/disclosures/opendart_list_synthetic.json`
- `docs/TASK_CARDS/M1-05-disclosure-provider.md`

수정하지 않을 파일:
- `app/core/models.py`
- `app/core/status.py`
- `app/core/resolver.py`
- `app/providers/base.py`
- `app/providers/news.py`
- `app/config.py`
- `.env.example`

`.env.example`에는 이미 `OPENDART_API_KEY`가 있으므로 M1-05 recorded implementation에서는 변경하지 않는다.

## 6. 고정 이름
- class: `RecordedDisclosureProvider`
- key: `recorded_disclosure`
- `FinancialDocument.provider`: `recorded_disclosure`
- `FinancialDocument.source_type`: `disclosure`
- ingestion_version: `disclosure-provider-m1-05-v1`
- shared normalizer function: `normalize_opendart_disclosure_response`

향후 live adapter 이름은 `OpenDartDisclosureProvider` 후보로만 둔다. M1-05 승인 범위에서는 `PLANNED/NOT_IMPLEMENTED` 상태로 유지한다.

## 7. 입력과 provider protocol
`RecordedDisclosureProvider.fetch()`는 M1-03 `Provider` protocol을 그대로 따른다.

- `security: SecurityIdentifier`
- `query: str | None = None`
- `date_range: DateRange | None = None`
- `attempt_timeout_seconds: float = 8`

`ProviderConfig`는 provider `fetch()` 입력에 넣지 않는다. retry, timeout, total deadline, cache는 M1-03 `fetch_with_policy()`가 담당하며 M1-05에서 재구현하지 않는다.

## 8. 지원 종목과 corp_code 경계
지원 종목은 M1-02와 동일한 3개 보통주로 제한한다.

| security_id | ticker | security_name | security_type | corp_code 후보 | 현재 검증 상태 |
|---|---:|---|---|---:|---|
| `KRX:005930` | `005930` | 삼성전자 | `common_stock` | `00126380` | `candidate` |
| `KRX:000660` | `000660` | SK하이닉스 | `common_stock` | `00164779` | `candidate` |
| `KRX:005380` | `005380` | 현대자동차 | `common_stock` | `00164742` | `candidate` |

- provider는 사용자 입력을 다시 resolve하지 않는다.
- provider는 M1-02에서 확정된 canonical `SecurityIdentifier`만 받는다.
- market, ticker, security_name, security_type이 `data/securities.json`과 모두 일치해야 한다.
- P0에서는 `common_stock`만 허용한다.
- preferred_stock, unsupported ticker, mismatched security는 `invalid_query`.
- `SecurityIdentifier.corp_code`가 `None`일 수 있으므로 recorded fixture 정규화는 `security_id`와 ticker/corp fixture matching을 함께 사용한다.
- `corp_code` 원본 재검증은 live OpenDART credential 또는 원본 corp-code 파일 제공 전까지 완료로 표시하지 않는다.
- live OpenDART adapter는 verified corp_code 없이는 시작하지 않는다.

## 9. recorded fixture schema
Recorded fixture는 OpenDART disclosure list 응답과 유사한 top-level object를 사용한다. 실제 live schema 최신성은 M1-05 recorded 범위에서 확정하지 않는다.

필수 top-level:
- `status`
- `message`
- `list`

공시 item 필수:
- `corp_code`
- `corp_name`
- `stock_code`
- `report_nm`
- `rcept_no`
- `rcept_dt`

공시 item 선택:
- `corp_cls`
- `flr_nm`
- `rm`

정정 관계는 OpenDART raw item에 섞지 않고 fixture wrapper의 `extensions.correction_links`에만 둔다.

`extensions.correction_links` 형식:
```json
{
  "정정공시접수번호": "원공시접수번호"
}
```

## 10. query 규칙
- `query is None`: 해당 종목의 recorded disclosure 전체를 반환한다.
- explicit blank query: `invalid_query`.
- nonblank query: `report_nm`과 정규화 text에 대해 NFKC/공백/casefold 정규화 후 포함 여부로 필터링한다.
- query는 회사명 seed에 사용하지 않는다. 공시 provider는 이미 canonical security로 제한된다.
- query 필터 결과가 없으면 `no_data`.

## 11. DateRange
- `rcept_dt`는 `YYYYMMDD` 형식만 허용한다.
- `published_at`은 `rcept_dt`의 Asia/Seoul 날짜 00:00:00을 UTC로 변환해 저장한다.
- `DateRange.start`와 `DateRange.end`는 Asia/Seoul 날짜 기준 inclusive로 적용한다.
- date filter 결과가 없으면 `no_data`.

## 12. FinancialDocument 정규화
- `document_id`: `disclosure:{rcept_no}` receipt-only deterministic id
- `source_type`: `disclosure`
- `provider`: `recorded_disclosure`
- `primary_security_ids`: target `security_id` 1개
- `mentioned_security_ids`: 기본 빈 목록
- `title`: cleaned `report_nm`
- `published_at`: timezone-aware UTC
- `source_url`: receipt 기반 공식 DART viewer URL
- `text`: title과 제출자/회사명/정정 표시 등 안전한 요약 text
- `locator`:
  - `provider`
  - `receipt_no`
  - `corp_code`
  - `stock_code`
  - `corp_name`
  - `report_name`
  - `received_date`
  - `viewer_url`
- `metadata`:
  - `corp_cls`
  - `submitter`
  - `remark`
  - `is_correction`
  - `correction_of`
  - `corp_code_verification_status`
- `ingestion_version`: `disclosure-provider-m1-05-v1`

`locator`, `metadata`, `source_url`에는 fixture 경로, 로컬 절대경로, credential 값을 넣지 않는다.

## 13. 공시 귀속과 정정 공시
- item의 `stock_code`와 `corp_code`가 target security fixture와 일치하면 target security를 primary로 둔다.
- 다른 지원 종목의 ticker/corp_code item은 wrong-company로 제외한다.
- item의 `report_nm`에 정정 제출 marker가 있거나 `extensions.correction_links`에 현재 receipt가 key로 있으면 `metadata.is_correction=True`로 보존한다.
- `extensions.correction_links`에 명시 관계가 있으면 원공시 receipt와 정정공시 receipt 관계를 metadata에 보존한다.
- report family는 추론하지 않는다.
- 서로 다른 receipt는 모두 보존한다.
- 전체 유효 문서는 `rcept_dt` 내림차순, 같은 날짜면 `rcept_no` 내림차순으로 안정 정렬한다.
- 정정 관계가 fixture로 명시되지 않은 경우 수치 변경을 추론하지 않는다.
- 정정 chain이 불확실하면 최신 유효본이라고 단정하지 않고 보존 정보만 반환한다.

`rm` 의미:
- `유`: 유가증권시장 소관. 후속 정정으로 처리하지 않는다.
- `정`: 해당 보고서 제출 후 정정신고 존재. `has_subsequent_correction=True`.
- `철`: 철회 또는 철회 간주. `is_withdrawn=True`.
- `rm`의 `정` 또는 `철`은 현재 item의 `is_correction`을 강제로 true로 만들지 않는다.

## 14. parse 정책
- raw response가 dict가 아니면 `parse_error`.
- top-level `list`가 없거나 list가 아니면 `parse_error`.
- `list`가 원래 비어 있으면 `no_data`.
- item이 dict가 아니면 malformed item으로 제외한다.
- 필수 item field가 없거나 string이 아니면 malformed item으로 제외한다.
- `rcept_dt`가 `YYYYMMDD` 날짜로 파싱되지 않으면 malformed item으로 제외한다.
- `rcept_no`가 비어 있으면 malformed item으로 제외한다.
- 일부 malformed와 valid item이 섞이면 valid item은 유지한다.
- 모든 item이 malformed이면 `parse_error`.
- valid item이 security/date/query filter에서 모두 제외되면 `no_data`.

## 15. status mapping
모든 결과는 M1-03 `create_provider_result`를 통과한다.

- `ok`: normalized `FinancialDocument` 1개 이상
- `no_data`: 정상 fixture이나 해당 security/date/query 공시 없음
- `invalid_query`: canonical security 불일치 또는 blank query
- `timeout`: provider timeout fixture 또는 M1-03 wrapper timeout
- `rate_limited`: rate limit fixture
- `unauthorized`: credential 관련 failure fixture
- `provider_unavailable`: 서비스 장애 fixture 또는 알 수 없는 provider failure fixture
- `parse_error`: schema 또는 all-malformed fixture

OpenDART status code의 전체 live mapping은 M1-05 recorded 범위에서 확정하지 않는다. recorded fixture에서 명시한 status만 테스트하고, live adapter 작업에서 공식 문서 재확인 후 별도 고정한다.

## 16. 테스트 계획
Targeted tests:
- 3개 지원 종목 recorded disclosure 정상 반환
- provider key/source_type/ingestion_version 확인
- receipt locator 필수 확인
- deterministic document_id
- DateRange start/end inclusive
- blank query invalid_query
- report title query filter
- query filter no_data
- unsupported ticker invalid_query
- preferred_stock invalid_query
- mismatched canonical security invalid_query
- target과 다른 supported corp_code/ticker item wrong-company 제외
- raw response non-dict parse_error
- top-level list schema error parse_error
- empty list no_data
- 일부 malformed 제외와 valid item 유지
- 모두 malformed parse_error
- non-string required field malformed
- invalid `rcept_dt` malformed
- receipt 기반 공식 viewer URL 사용, raw fixture URL 무시, local absolute path 비노출
- correction disclosure metadata 보존
- correction_of 관계 보존
- rcept_dt/rcept_no 기반 안정 정렬
- 동일 receipt dedupe, API 순서상 첫 항목 유지
- 동일 fixture 재실행 동일 결과
- timeout/rate_limited/unauthorized/provider_unavailable fixture status mapping

Regression tests:
- M1-01 core model/status contracts
- M1-02 security resolver
- M1-03 provider base/config/fake
- M1-04 news provider
- M1-05 disclosure provider

Smoke:
- `RecordedDisclosureProvider`
- `normalize_opendart_disclosure_response`

## 17. 검증 명령
targeted:
```powershell
$env:PYTHONPATH = ".test_deps;."; python -m pytest tests/unit/test_disclosure_provider.py -q
```

regression:
```powershell
$env:PYTHONPATH = ".test_deps;."; python -m pytest tests/unit/test_core_models.py tests/unit/test_status_contracts.py tests/unit/test_security_resolver.py tests/unit/test_provider_base.py tests/unit/test_config.py tests/unit/test_news_provider.py tests/unit/test_disclosure_provider.py -q
```

smoke:
```powershell
$env:PYTHONPATH = ".test_deps;."; python -c "from app.providers.disclosure import RecordedDisclosureProvider, map_opendart_status, normalize_opendart_disclosure_response; print('ok')"
```

Live OpenDART 검증: `NOT_RUN — 승인 범위 제외`

GitHub CI: `NOT_RUN — 별도 확인 전 성공 주장 금지`

## 18. 완료 기준
- [x] `RecordedDisclosureProvider` 구현
- [x] OpenDART list API 형식 synthetic fixture 추가
- [x] 3개 지원 종목 정상 fixture 통과
- [x] canonical security validation 통과
- [x] unsupported ticker/preferred_stock invalid_query 테스트 통과
- [x] receipt locator 보존 테스트 통과
- [x] 정정 공시 식별 정보 보존 테스트 통과
- [x] `rm` 유/정/철 의미 테스트 통과
- [x] receipt-only dedupe와 rcept_dt/rcept_no 안정 정렬 테스트 통과
- [x] deterministic document_id 테스트 통과
- [x] DateRange inclusive 테스트 통과
- [x] no_data와 parse_error 분리 테스트 통과
- [x] timeout/rate_limited/unauthorized/provider_unavailable fixture 통과
- [x] wrong-company 공시 제외 테스트 통과
- [x] 로컬 절대경로와 secret 비노출 테스트 통과
- [x] targeted unit 통과
- [x] M1-01~M1-04 포함 regression 통과
- [x] import smoke 통과
- [x] live OpenDART 검증은 `NOT_RUN` 또는 별도 승인 결과로 기록
- [x] 실제 공시 coverage는 synthetic fixture와 분리해 기록

## 19. fallback / rollback 제안
- OpenDART credential이 없으면 recorded fixture만 사용하고 live 검증은 `NOT_RUN` 또는 `BLOCKED`로 기록한다.
- corp_code 원본 재검증이 막히면 `verification_status: candidate`를 유지하고 live adapter를 시작하지 않는다.
- correction chain이 불확실하면 최신 유효본 단정 없이 receipt 관계와 정정 표시만 보존한다.
- 공시 본문 원문 확보가 어렵다면 M1-05는 list-level title/receipt locator까지로 축소하고 본문 ingest는 후속 작업으로 분리한다.
- schema가 흔들리면 raw item 저장을 늘리지 않고 normalized fixture 계약을 우선한다.

## 20. 중단 기준
- `FinancialDocument`, `ProviderResult`, `ProviderStatus`, `SecurityIdentifier` 변경이 필요해지는 경우
- M1-03 provider base/config/fake 구조 변경이 필요해지는 경우
- M1-04 news provider 구조 변경이 필요해지는 경우
- live OpenDART HTTP 호출 또는 credential 사용이 필요해지는 경우
- OpenDART API key 값을 코드/문서/로그에 기록해야 하는 경우
- corp_code를 verified로 전환해야 하지만 원본 재검증 자료가 없는 경우
- 정정 공시를 최신 유효본으로 단정하려면 원문 또는 relation 정보가 필요한 경우
- retrieval/API/UI/LLM 구현이 필요해지는 경우
- 지원 종목 3개 밖으로 범위를 넓혀야 하는 경우

## 21. 승인 상태
- Task Card 작성 일시: 2026-07-22
- 계획 상태: 구현 완료, 사용자 검수 대기
- 구현 승인: 승인됨, 첨부 지시 기준
- commit/push 승인: 미승인
- Live OpenDART adapter: `PLANNED/NOT_IMPLEMENTED`
- Live NAVER adapter: `PLANNED/NOT_IMPLEMENTED`
- M1-06 리서치 리포트 ingest: `NOT_RUN`

## 22. 구현 결과 기록
- 기록 일시: 2026-07-22
- 구현 기준 commit: `192207e35c902aded50d43facc3c67393f2eb3b7`
- 최초 구현 SHA: `f20b33d7f77edc04f2c7b4599b2464c5f553d8be`
- 최초 main push: 완료
- 사용자 검수: `CONDITIONAL PASS`
- 보완 SHA: 미생성, 사용자 별도 승인 전 commit/push 미수행
- 수정 파일:
  - `app/providers/disclosure.py`
  - `app/providers/__init__.py`
  - `tests/unit/test_disclosure_provider.py`
  - `tests/fixtures/disclosures/opendart_list_synthetic.json`
  - `docs/TASK_CARDS/M1-04-news-provider.md`
  - `docs/TASK_CARDS/M1-05-disclosure-provider.md`
- 구현 범위:
  - `RecordedDisclosureProvider`
  - OpenDART disclosure list API 형식 synthetic fixture wrapper
  - status-first `map_opendart_status`
  - transport-independent `normalize_opendart_disclosure_response`
  - canonical security registry loader와 validation
  - query filter, DateRange filter
  - receipt 기반 DART viewer URL 생성
  - receipt-only deterministic document_id와 dedupe
  - correction/update/withdrawal listing metadata parsing
  - listing metadata content level 제한
  - M1-03 `create_provider_result` 기반 status mapping
- 제외 범위:
  - actual OpenDART HTTP request: `NOT_RUN`
  - OpenDART credential 사용: `NOT_RUN`
  - corporation-code 원본 ZIP/API 검증: `NOT_RUN`
  - `verification_status` verified 전환: `NOT_RUN`
  - live OpenDART adapter: `PLANNED/NOT_IMPLEMENTED`
  - Live NAVER adapter: `PLANNED/NOT_IMPLEMENTED`
  - disclosure body document API/HTML/XML/PDF ingest: `NOT_RUN`
  - retrieval/index/vector store/API/UI/LLM: `NOT_RUN`
  - M1-06 research report ingest: `NOT_RUN`
- status mapping:
  - `000`: success response parsing
  - `013`: `no_data`
  - `010`, `011`, `012`, `101`, `901`: `unauthorized`
  - `020`: `rate_limited`
  - `021`, `100`: `invalid_query`
  - `014`, `800`, `900`, unknown non-000: `provider_unavailable`
  - missing/non-string status: `parse_error`
  - fixture `case=timeout`: `timeout`
  - fixture `case=network_error`: `provider_unavailable`
- content level 제한:
  - `metadata.content_level = "listing_metadata"`
  - 공시 목록 metadata, receipt, official viewer URL만 제공
  - 공시 본문 상세 요약, 재무 수치, 계약 금액, 배당금, 사업 조건 분석에는 supporting evidence로 사용 금지
- corp-code candidate 상태:
  - `data/securities.json`의 `verification_status`는 `candidate` 유지
  - input `SecurityIdentifier.corp_code is None`이면 registry candidate corp_code로 item matching
  - verified 전환 및 원본 재검증은 `NOT_RUN`
- synthetic fixture:
  - `tests/fixtures/disclosures/opendart_list_synthetic.json`
  - provider contract unit 증거로만 사용
  - real disclosure coverage로 계산하지 않음
- 실제 검증 결과:
  - PYTHONPATH: `.test_deps;.`
  - targeted 최초 명령: `python -m pytest tests/unit/test_disclosure_provider.py -q`
  - targeted 최초 exit code: `1`
  - targeted 최초 출력: `.test_deps` 접근 `PermissionError`
  - targeted 재실행 명령: `python -m pytest tests/unit/test_disclosure_provider.py -q`
  - targeted 재실행 exit code: `0`
  - targeted 재실행 출력: `70 passed in 0.24s`
  - regression 명령: `python -m pytest tests/unit/test_core_models.py tests/unit/test_status_contracts.py tests/unit/test_security_resolver.py tests/unit/test_provider_base.py tests/unit/test_config.py tests/unit/test_news_provider.py tests/unit/test_disclosure_provider.py -q`
  - regression exit code: `0`
  - regression 출력: `221 passed in 0.35s`
  - smoke 명령: `python -c "from app.providers.disclosure import RecordedDisclosureProvider, map_opendart_status, normalize_opendart_disclosure_response; print('ok')"`
  - smoke exit code: `0`
  - smoke 출력: `ok`
- provider contract unit: `PASS`
- real disclosure coverage: `NOT_RUN`
- corp-code source verification: `NOT_RUN`
- live OpenDART: `NOT_RUN`
- live adapter: `PLANNED/NOT_IMPLEMENTED`
- GitHub CI: `NOT_RUN`
- commit/push: `NOT_RUN`
- 최종 상태: 보완 구현 후 사용자 재검수 대기

## 23. CONDITIONAL PASS 보완 결과 기록
- 기록 일시: 2026-07-22
- 최초 구현 SHA: `f20b33d7f77edc04f2c7b4599b2464c5f553d8be`
- 최초 main push: 완료
- 사용자 검수: `CONDITIONAL PASS`
- 보완 SHA: 미생성, 사용자 별도 승인 전 commit/push 미수행
- 보완 범위:
  - OpenDART `rm` 의미 수정
  - `rm="유"`는 유가증권시장 소관으로만 처리하고 후속 정정으로 보지 않음
  - `rm`에 `정`이 포함될 때만 `has_subsequent_correction=True`
  - `rm`에 `철`이 포함될 때 `is_withdrawn=True`
  - `rm` 정정/철회 표시는 현재 item의 `is_correction`을 강제로 true로 만들지 않음
  - Task Card의 raw `source_url`/`correction_of` 계약 제거 및 `extensions.correction_links` 계약 명시
  - receipt viewer URL, receipt-only document_id/dedupe, report family 추론 금지, 최신 유효본 미확정, listing_metadata 제한 재기록
- 실제 검증 결과:
  - PYTHONPATH: `.test_deps;.`
  - targeted 최초 명령: `python -m pytest tests/unit/test_disclosure_provider.py -q`
  - targeted 최초 exit code: `1`
  - targeted 최초 출력: `.test_deps` 접근 `PermissionError`
  - targeted 재실행 명령: `python -m pytest tests/unit/test_disclosure_provider.py -q`
  - targeted 재실행 exit code: `0`
  - targeted 재실행 출력: `70 passed in 0.24s`
  - regression 명령: `python -m pytest tests/unit/test_core_models.py tests/unit/test_status_contracts.py tests/unit/test_security_resolver.py tests/unit/test_provider_base.py tests/unit/test_config.py tests/unit/test_news_provider.py tests/unit/test_disclosure_provider.py -q`
  - regression exit code: `0`
  - regression 출력: `221 passed in 0.34s`
  - smoke 명령: `python -c "from app.providers.disclosure import RecordedDisclosureProvider, map_opendart_status, normalize_opendart_disclosure_response; print('ok')"`
  - smoke exit code: `0`
  - smoke 출력: `ok`
- live OpenDART: `NOT_RUN`
- corp-code source verification: `NOT_RUN`
- real disclosure coverage: `NOT_RUN`
- live adapter: `PLANNED/NOT_IMPLEMENTED`
- M1-06 구현: `NOT_RUN`
- GitHub CI: `NOT_RUN`
- commit/push: `NOT_RUN`
- 최종 상태: 보완 구현 후 사용자 재검수 대기
