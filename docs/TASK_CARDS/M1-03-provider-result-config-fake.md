# TASK CARD - M1-03 ProviderResult Config Fake

## 1. 계획 연결
- Task bundle: B2
- Step: M1-03 ProviderResult·config·fake
- 우선순위: P0
- 구현 기준 commit: `a727fccbf8175c53d5e62198ba47b1f7486df80f`
- 관련 위험 ID: R02, R15, R16, R17, R18, R19, R54
- 관련 taxonomy: provider_timeout, provider_rate_limit, source_selection, stale_data

## 2. 목적
M1-04 뉴스 provider와 M1-05 공시 provider가 같은 오류·timeout·cache·secret 계약을 쓰도록, live API 호출 전 공통 provider 경계와 deterministic fake provider를 고정한다.

M1-03은 실제 NAVER/OpenDART adapter를 만들지 않는다. 외부 credential이 없어도 unit test로 `ok`, `no_data`, `invalid_query`, `timeout`, `rate_limited`, `parse_error`, `provider_unavailable`, `unauthorized`와 timeout wrapper·deadline·cache·secret 비노출 계약을 검증할 수 있어야 한다.

## 3. 실제 확인한 현재 상태
- 확인 파일:
  - `docs/agent_handoff/PROJECT_PLAN_FINAL_PASS.md`
  - `docs/agent_handoff/FINANCIAL_CAPABILITY_BASELINE.md`
  - `docs/agent_handoff/RISK_RESPONSE_MATRIX.md`
  - `docs/agent_handoff/TASK_CARD_TEMPLATE.md`
  - `docs/TASK_CARDS/M1-01-core-models.md`
  - `docs/TASK_CARDS/M1-02-security-resolver.md`
  - `.env.example`
  - `app/core/models.py`
  - `app/core/status.py`
  - `app/core/resolver.py`
- 확인 class·enum:
  - `app.core.models.ProviderResult`
  - `app.core.models.SecurityIdentifier`
  - `app.core.status.ProviderStatus`
  - `app.core.resolver.SecurityResolver`
- 현재 동작:
  - M1-01 PASS, 기준 SHA `0358fd88e65b11082369d35cf37c8d3c3a3163ab`
  - M1-02 PASS, 보완 SHA `a727fccbf8175c53d5e62198ba47b1f7486df80f`
  - `.env.example`에는 `OPENDART_API_KEY`, `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`, `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL` 이름이 존재한다.
  - provider base protocol, config loader, fake provider, timeout wrapper, cache interface 구현은 아직 없음.
- 미확인 사항:
  - 실제 OpenDART/NAVER credential 값
  - live OpenDART/NAVER API 응답
  - GitHub CI 실행 결과

## 4. 선행 조건
- [x] M1-01 core model과 `ProviderStatus` 계약 존재
- [x] M1-02 `SecurityResolver` PASS
- [x] 지원 종목 3개 canonical fixture 존재
- [x] M1-03 계획 CONDITIONAL PASS
- [ ] commit/push 별도 승인

## 5. 입력·출력
- production provider protocol 입력:
  - canonical `SecurityIdentifier`
  - optional query
  - optional `DateRange`
  - attempt timeout
- fake provider 입력:
  - production protocol 입력과 동일
  - scenario id는 production protocol에 넣지 않고 `FakeProvider` 생성 시 별도 주입
- 출력:
  - 기존 `ProviderResult[T]`
  - normalized payload 또는 `None`
  - `ProviderStatus`
  - `error_code`, `message`, `fetched_at`, `from_cache`

## 6. 파일 위치
- 수정 가능:
  - `app/providers/base.py`
  - `app/providers/fake.py`
  - `app/config.py`
  - `tests/unit/test_provider_base.py`
  - `tests/unit/test_config.py`
  - 필요 시 `app/providers/__init__.py`
  - `.env.example`
  - `docs/TASK_CARDS/M1-03-provider-result-config-fake.md`
- 생성 금지:
  - `app/core/provider.py`
  - `app/core/providers.py`
  - `app/core/config.py`

## 7. ProviderResult 불변조건
기존 `ProviderResult` model과 `ProviderStatus` enum은 변경하지 않는다. `app/providers/base.py`의 중앙 factory 또는 동등한 validator에서 아래 불변조건을 강제한다.

- `ok`: `data` 필수, `error_code is None`
- `no_data`: `data is None`, `error_code is None`
- 모든 실패 상태: `data is None`, 상태별 고정 `error_code`, sanitized `message`
- `invalid_query`: `error_code=invalid_query`
- `unauthorized`: `error_code=unauthorized`
- `rate_limited`: `error_code=rate_limited`
- `parse_error`: `error_code=parse_error`
- `provider_unavailable`: `error_code=provider_unavailable`
- attempt timeout: `status=timeout`, `error_code=attempt_timeout`
- total deadline: `status=timeout`, `error_code=total_deadline_exceeded`
- 모든 `fetched_at`은 timezone-aware UTC
- `Retry-After`는 M1-03 결과 schema에 구조화하지 않고 `rate_limited` status와 safe message로만 정규화
- `ProviderResult`에 metadata나 diagnostics field를 추가하지 않는다.
- `FakeProvider`, cache, orchestration 결과는 모두 이 factory 경계를 통과한다.

## 8. Provider 계약
- provider는 이미 resolve된 canonical `SecurityIdentifier`만 받는다.
- provider는 종목 ambiguity를 다시 판정하지 않는다.
- provider는 최종 사용자 답변을 생성하지 않는다.
- raw exception, raw provider 객체, credential 값은 반환·로그·문서 fixture에 남기지 않는다.
- `no_data`는 정상 조회 결과 없음이고, `timeout`, `rate_limited`, `parse_error`, `provider_unavailable`, `unauthorized`, `invalid_query`와 분리한다.
- `low_relevance`는 retrieval 상태이므로 provider 상태로 사용하지 않는다.

## 9. Retry·deadline 계약
- `retry_count=1`은 최초 1회와 재시도 최대 1회, 총 2 attempts를 의미한다.
- retry 대상:
  - `timeout`
  - `provider_unavailable`
- retry 금지:
  - `ok`
  - `no_data`
  - `invalid_query`
  - `unauthorized`
  - `rate_limited`
  - `parse_error`
- 전체 deadline 초과 결과는 `status=timeout`, `error_code=total_deadline_exceeded`
- 요청된 모든 provider key를 결과 dict에 남긴다.
- 한 provider 실패가 orchestration helper 전체를 raise하지 않는다.
- timeout wrapper 자체를 deterministic test로 검증한다.
- 실제 8초 sleep은 사용하지 않는다.
- deadline 이후 남은 작업을 더 기다리지 않고, 취소 가능한 pending task는 취소한다.

## 10. Cache 계약
- injectable monotonic clock 기반 in-memory TTL cache를 구현한다.
- 기본 TTL: 300초
- TTL 0: cache 비활성화
- `ok` 결과만 cache한다.
- cache key:
  - provider_key
  - canonical security_id
  - normalized query
  - date range start/end
- hit은 원본을 수정하지 않고 복사본에만 `from_cache=True`를 설정하며 원래 `fetched_at`을 유지한다.
- expired entry는 stale 반환 없이 miss 처리한다.

## 11. Config 계약
- `os.getenv`와 기존 Pydantic만 사용한다. 새 dependency를 추가하지 않는다.
- 기본값:
  - `timeout_seconds=8`
  - `retry_count=1`
  - `total_deadline_seconds=20`
  - `cache_ttl_seconds=300`
- 숫자 범위:
  - `timeout_seconds > 0`
  - `retry_count >= 0`
  - `total_deadline_seconds > 0`
  - `cache_ttl_seconds >= 0`
  - `cache_ttl_seconds == 0`은 cache 비활성화
  - NaN과 Infinity 금지
- secret은 repr, str, JSON dump, safe summary, exception, log에 노출하지 않는다.
- safe summary에는 credential 값이 아니라 configured 여부만 포함한다.
- fake/unit 환경에서는 credential 없이 load 가능하다.
- 잘못된 숫자·음수 설정은 sanitized validation error로 처리하고 invalid env 원문은 validation error에 노출하지 않는다.
- `.env.example`에는 이름만 추가하고 실제 값은 비워 둔다.

## 12. Fake Provider 기준
- fixture scenario는 deterministic해야 한다.
- 최소 scenario:
  - `ok`
  - `no_data`
  - `invalid_query`
  - `timeout`
  - `rate_limited`
  - `parse_error`
  - `provider_unavailable`
  - `unauthorized`
- fake provider는 production protocol에 scenario id를 받지 않고 생성 시 주입된 scenario로 동작한다.
- wrapper timeout 검증용으로 pending/cancel 가능한 fake 동작을 제공할 수 있다.

## 13. 수정 금지 범위
- 기존 M1-01 model field와 status enum 변경
- `SecurityResolver` 구조 재작성
- NAVER live NewsProvider 구현
- OpenDART live DisclosureProvider 구현
- retrieval 구현
- API route
- UI
- LLMStatus, LiteLLM, Gemini, provider LLM code
- secret 값 기록

## 14. 구현 순서
1. `.env.example`에 M1-03 provider config 변수 이름만 추가한다.
2. `app/config.py`에 secret-safe `ProviderConfig`를 구현한다.
3. `app/providers/base.py`에 provider protocol, 중앙 result factory, TTL cache, orchestration helper를 구현한다.
4. `app/providers/fake.py`에 scenario 주입형 `FakeProvider`를 구현한다.
5. `tests/unit/test_config.py`를 작성한다.
6. `tests/unit/test_provider_base.py`를 작성한다.
7. targeted unit, regression, smoke를 실행한다.
8. Task Card에 실제 실행 결과를 기록한다.

## 15. 테스트 계획
- provider status:
  - `ok` -> `ProviderResult.status == ok`, data 존재, `error_code is None`
  - `no_data` -> `data is None`, `error_code is None`
  - `invalid_query` -> `data is None`, `error_code=invalid_query`
  - `timeout` -> `data is None`, `error_code=attempt_timeout`
  - `rate_limited` -> `data is None`, `error_code=rate_limited`, safe message
  - `parse_error` -> `data is None`, `error_code=parse_error`
  - `provider_unavailable` -> `data is None`, `error_code=provider_unavailable`
  - `unauthorized` -> `data is None`, `error_code=unauthorized`, secret 비노출
- timeout/retry:
  - 기본 timeout 8초 config
  - retry 1회 config는 총 2 attempts
  - retry 대상과 금지 대상 분리
  - wrapper가 attempt timeout과 total deadline을 집행
- deadline:
  - retry 포함 전체 20초 deadline config
  - deadline 부족 시 남은 작업 대기 없음
  - pending task cancel 확인
- parallel:
  - requested provider key가 모두 결과 dict에 남음
  - 한 provider timeout이 다른 provider ok 결과를 막지 않음
- cache:
  - TTL 300 기본값
  - TTL 0 cache 비활성화
  - ok만 cache
  - cache key 구성 검증
  - hit은 원래 fetched_at 유지와 복사본 `from_cache=True`
  - expired는 miss
- secret:
  - repr, str, JSON dump, safe summary, exception, log에 secret 실제 값 미노출
- regression:
  - M1-01 core model/status tests
  - M1-02 security resolver tests

## 16. 완료 기준
- [x] 지정 파일 위치만 사용
- [x] base provider protocol 존재
- [x] 중앙 ProviderResult factory 불변조건 테스트 통과
- [x] fake provider deterministic 동작
- [x] `ok`, `no_data`, `invalid_query`, `timeout`, `rate_limited`, `parse_error` fixture 테스트 통과
- [x] `provider_unavailable`, `unauthorized` fixture 테스트 통과
- [x] timeout 8초 기본값과 1회 retry config 존재
- [x] retry 포함 전체 20초 deadline config 존재
- [x] retry 대상과 retry 금지 대상 테스트 통과
- [x] required provider orchestration helper 존재
- [x] 한 provider 실패가 다른 provider 결과를 막지 않음
- [x] 요청된 모든 provider key가 결과 dict에 남음
- [x] injectable clock 기반 TTL cache 테스트 통과
- [x] key 로그·repr·summary·JSON dump 미노출 테스트 통과
- [x] live API 호출 없이 unit test 통과
- [x] M1-01/M1-02 회귀 없음

## 17. 검증
- targeted unit:
```powershell
$env:PYTHONPATH = ".test_deps;."; python -m pytest tests/unit/test_provider_base.py tests/unit/test_config.py -q
```
- regression:
```powershell
$env:PYTHONPATH = ".test_deps;."; python -m pytest tests/unit/test_core_models.py tests/unit/test_status_contracts.py tests/unit/test_security_resolver.py tests/unit/test_provider_base.py tests/unit/test_config.py -q
```
- smoke:
```powershell
$env:PYTHONPATH = ".test_deps;."; python -c "from app.config import ProviderConfig; from app.providers.fake import FakeProvider; print('ok')"
```
- live OpenDART 검증: `NOT_RUN — 승인 범위 제외`
- live NAVER 검증: `NOT_RUN — 승인 범위 제외`
- GitHub CI: 별도 확인 전 `NOT_RUN`

## 18. fallback·rollback 제안
- async orchestration이 과해지면 `asyncio` 기반 최소 helper만 남긴다.
- cache 구현이 커지면 in-memory TTL cache만 유지하고 외부 cache interface는 다음 단계로 넘긴다.
- timeout wrapper가 테스트를 느리게 만들면 fake provider의 cancel 가능한 pending task와 짧은 timeout config로 검증한다.
- config loader가 복잡해지면 `os.getenv` 기반 Pydantic model만 유지한다.

## 19. 중단 기준
- 기존 `ProviderResult` field 또는 `ProviderStatus` enum 변경이 필요해지는 경우
- 실제 NAVER/OpenDART adapter 구현이 필요해지는 경우
- live API 호출 또는 credential 값 기록이 필요해지는 경우
- LLMStatus, LiteLLM, Gemini 코드가 필요해지는 경우
- retrieval/API/UI 구현이 필요해지는 경우
- 테스트가 외부 네트워크 또는 실제 시간 8초 대기에 의존하는 경우
- `app/core/provider.py`, `app/core/providers.py`, `app/core/config.py` 생성이 필요해지는 경우

## 20. 승인
- 승인 일시: 2026-07-21
- 승인 범위: M1-03 Task Card 보완 후 구현 승인
- Git 작업 승인 포함 여부: 기본 `아니오`

## 21. 구현 결과 기록
- 기록 일시: 2026-07-21
- 구현 기준 commit: `a727fccbf8175c53d5e62198ba47b1f7486df80f`
- 구현 SHA: 미생성, 사용자 별도 승인 전 commit/push 미수행
- 수정 파일:
  - `.env.example`
  - `app/config.py`
  - `app/providers/__init__.py`
  - `app/providers/base.py`
  - `app/providers/fake.py`
  - `tests/unit/test_config.py`
  - `tests/unit/test_provider_base.py`
  - `docs/TASK_CARDS/M1-03-provider-result-config-fake.md`
- 실제 테스트 결과:
  - PYTHONPATH: `.test_deps;.`
  - targeted unit 명령: `python -m pytest tests/unit/test_provider_base.py tests/unit/test_config.py -q`
  - targeted unit exit code: `0`
  - targeted unit 출력: `34 passed in 0.17s`
  - regression 명령: `python -m pytest tests/unit/test_core_models.py tests/unit/test_status_contracts.py tests/unit/test_security_resolver.py tests/unit/test_provider_base.py tests/unit/test_config.py -q`
  - regression exit code: `0`
  - regression 출력: `107 passed in 0.20s`
  - smoke 명령: `python -c "from app.config import ProviderConfig; from app.providers.fake import FakeProvider; print('ok')"`
  - smoke exit code: `0`
  - smoke 출력: `ok`
- live OpenDART 검증: `NOT_RUN — 승인 범위 제외`
- live NAVER 검증: `NOT_RUN — 승인 범위 제외`
- GitHub CI: `NOT_RUN`
- 독립 검수 환경 재실행: `NOT_RUN`
- 미실행:
  - commit/push: NOT_RUN, 별도 승인 전 수행 금지
  - Provider live adapter/retrieval/API/UI/LiteLLM/Gemini: NOT_RUN, 범위 제외
- 최종 판정: 사용자 검수 전
