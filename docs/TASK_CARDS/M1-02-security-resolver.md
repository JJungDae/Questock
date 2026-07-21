# TASK CARD - M1-02 SecurityResolver

## 1. 계획 연결
- Task bundle: B1
- Step: M1-02 SecurityResolver
- 우선순위: P0
- 관련 위험 ID: R02, R10, R22, R23, R25
- 관련 taxonomy: entity_resolution, ambiguous_security

## 2. 목적
사용자 입력의 회사명, ticker, security_id, 별칭을 지원 종목 3개의 canonical `SecurityIdentifier`로 안정적으로 정규화하고, 모호하거나 지원하지 않는 입력을 provider 호출 전에 차단한다.

## 3. 실제 확인한 현재 상태
- 확인 파일:
  - `docs/TASK_CARDS/M1-01-core-models.md`
  - `docs/TASK_CARDS/B0-M0-01-03-planning.md`
  - `docs/agent_handoff/PROJECT_PLAN_FINAL_PASS.md`
  - `docs/agent_handoff/FINANCIAL_CAPABILITY_BASELINE.md`
  - `docs/agent_handoff/RISK_RESPONSE_MATRIX.md`
- 확인 class:
  - `app.core.models.SecurityIdentifier`
  - `app.core.status.ResolutionStatus`
- 현재 동작:
  - M1-01 완료 승인: PASS
  - 기준 커밋: `0358fd88e65b11082369d35cf37c8d3c3a3163ab`
  - main push 완료
  - resolver 구현 파일과 data fixture는 아직 없음.
- 미확인 사항:
  - OpenDART corporation-code 원본 파일 또는 API credential.
  - SK하이닉스 corp_code `00164779` 원본 재검증.

## 4. 지원 종목 canonical fixture
M1-02에서 아래 3개 보통주만 resolver fixture로 고정한다.

| security_id | market | ticker | security_name | security_type | corp_code 후보 | corp_name |
|---|---|---:|---|---|---:|---|
| `KRX:005930` | `KRX` | `005930` | 삼성전자 | `common_stock` | `00126380` | 삼성전자 |
| `KRX:000660` | `KRX` | `000660` | SK하이닉스 | `common_stock` | `00164779` | 에스케이하이닉스 |
| `KRX:005380` | `KRX` | `005380` | 현대자동차 | `common_stock` | `00164742` | 현대자동차 |

corp_code는 M1-02 구현 중 OpenDART corporation-code 원본으로 재검증한 뒤 fixture에 반영한다. credential이 없으면 live 검증은 `BLOCKED` 또는 `NOT_RUN`으로 기록하고, fixture에는 `corp_code 후보`임을 분리 기록한다.

## 5. 입력 정규화 기준
resolver는 provider 호출 전에 다음 입력을 정규화한다.

- 이름:
  - Unicode NFKC 정규화
  - 앞뒤 공백 제거
  - 내부 연속 공백 축소
  - 대소문자 무시가 필요한 영문 alias는 casefold 처리
- ticker:
  - 앞뒤 공백 제거
  - 6자리 숫자만 ticker로 인정
  - `005930`, `000660`, `005380` exact match만 resolved
- security_id:
  - `KRX:005930`, `KRX:000660`, `KRX:005380` exact match
  - market prefix는 대소문자 정규화 가능
- alias:
  - 지원 종목 안에서만 명시 alias를 둔다.
  - alias가 여러 종목 후보를 만들면 resolved 처리하지 않고 ambiguous 처리한다.
  - 빈 alias는 fixture validation 실패로 처리한다.
  - canonical ID, ticker, exact name, alias가 서로 다른 종목에 충돌하면 fixture validation 실패로 처리한다.

## 6. ResolutionResult 계약
M1-01의 기존 model field와 status enum은 변경하지 않고, resolver module 안에 최소 `ResolutionResult`를 추가한다.

권장 field:

```text
status: ResolutionStatus
security: SecurityIdentifier | None
candidates: list[SecurityIdentifier]
normalized_query: str
message: str | None
matched_by: name | ticker | security_id | alias | unsupported_rule | none
```

`matched_by`는 구현에서 `Literal` 계약으로 고정하고 상태별 허용값을 테스트한다.

상태별 불변조건:

### `resolved`
- `security`는 반드시 존재한다.
- `candidates`는 항상 빈 목록이다.
- `matched_by`는 `name`, `ticker`, `security_id`, `alias` 중 하나다.
- provider 호출 가능.

### `ambiguous`
- `security`는 `None`.
- `candidates`는 1개 이상이다.
- `candidates`에는 현재 지원 universe의 후보만 포함한다.
- `message`는 구체화 요청이어야 한다.
- `matched_by`는 `none`이다.
- provider 호출 금지.
- `삼성`, `SK`, `현대`는 각각 지원 후보 1개와 clarification message를 반환한다.

### `not_found`
- `security`는 `None`.
- `candidates`는 빈 목록이다.
- 어떤 fixture, alias, exact name, ticker, security_id, unsupported 규칙에도 매칭되지 않은 입력이다.
- 빈 입력 또는 정규화 후 빈 문자열은 `not_found`.
- `matched_by`는 `none`이다.
- provider 호출 금지.

### `unsupported`
- `security`는 `None`.
- `candidates`는 빈 목록이다.
- 미지원으로 명시 식별 가능한 입력에만 사용한다.
- 예: 우선주 ticker/name, 해외 ticker 패턴, SPAC/ETF 등 명시 규칙에 걸린 입력.
- `matched_by`는 `unsupported_rule`이다.
- provider 호출 금지.

## 7. 판정 우선순위
resolver는 다음 순서를 고정한다.

1. 정규화
2. 빈 입력
3. exact security_id
4. exact ticker
5. exact name
6. resolved alias
7. curated ambiguous term
8. explicit unsupported rule
9. not_found

## 8. Resolution 기준

### `resolved`
- 하나의 지원 종목으로만 확정되는 exact ticker, exact security_id, exact name, 명시 alias.
- 반환값은 `SecurityIdentifier`여야 한다.
- `candidates`는 항상 빈 목록이다.

### `ambiguous`
- 입력이 현재 지원 universe 안의 후보를 만들 수 있지만 단일 종목으로 자동 확정하면 위험한 경우.
- 예: `삼성`, `SK`, `현대`.
- provider 호출 금지.
- 지원 후보 1개 이상과 clarification message를 반환한다.

### `not_found`
- 어떤 fixture, alias, exact name, ticker, security_id, unsupported 규칙에도 매칭되지 않은 경우.
- 예: `999999`, `000001`, 빈 입력.
- `카카오`는 known unsupported fixture에 명시하지 않는 한 테스트에서 제외한다.

### `unsupported`
- 명시적으로 식별 가능한 범위 밖 입력.
- 예: `삼성전자우`, `005935`, 해외 ticker, SPAC/우선주로 명시된 입력.

## 9. corp_code 원본 재검증 방식
우선순위:

1. OpenDART corporation-code 원본 XML 또는 API 응답에서 `stock_code`와 `corp_code`를 대조한다.
2. credential이 제공되지 않은 경우 live/API 검증은 실행하지 않고 `BLOCKED`로 기록한다.
3. offline fixture에는 출처와 검증 상태를 나눈다.
   - `corp_code`
   - `stock_code`
   - `corp_name`
   - `verification_status: verified | candidate | blocked`
   - `verified_at`
4. M1-02에서 원본 재검증 없이 corp_code를 확정 완료로 표시하지 않는다.
5. `verification_status`가 `candidate` 또는 `blocked`이면 반환 `SecurityIdentifier.corp_code`는 `None`이어야 한다.
6. `verification_status`가 `verified`일 때만 반환 `SecurityIdentifier.corp_code`에 값을 넣는다.

## 10. 수정 범위
- 수정 가능:
  - `app/core/resolver.py`
  - `data/securities.json`
  - `tests/unit/test_security_resolver.py`
  - 필요 시 `app/core/__init__.py`
  - 필요 시 `docs/TASK_CARDS/M1-02-security-resolver.md`
- 수정 금지:
  - 기존 M1-01 model field와 status enum 변경
  - LLMStatus, LiteLLM, Gemini 관련 코드
  - provider 구현
  - retrieval 구현
  - API route
  - UI
  - DB/auth/watchlist/P1/M5 기능

## 11. 구현 순서
1. 지원 종목 3개를 `data/securities.json`에 fixture로 둔다.
2. fixture validation으로 canonical ID, ticker, exact name, alias 충돌과 빈 alias를 차단한다.
3. `SecurityResolver`와 `ResolutionResult`를 최소 구현한다.
4. NFKC, 공백, casefold 정규화 함수를 resolver 내부 또는 작은 private helper로 둔다.
5. exact ticker/name/security_id resolved 테스트를 작성한다.
6. alias resolved 테스트를 작성한다.
7. 공백/NFKC/대소문자 정규화 테스트를 작성한다.
8. ambiguous/not_found/unsupported 테스트를 작성한다.
9. corp_code 재검증 상태와 `corp_code` 반환 null 규칙을 테스트한다.
10. 판정 우선순위와 `matched_by` 상태별 허용값을 테스트한다.

## 12. 테스트 계획
- 정상:
  - `삼성전자` -> `resolved`, `KRX:005930`
  - `SK하이닉스` -> `resolved`, `KRX:000660`
  - `현대자동차` -> `resolved`, `KRX:005380`
- ticker:
  - `005930`, `000660`, `005380` resolved
  - `999999` not_found
  - `005935` unsupported
- security_id:
  - `KRX:005930`, `krx:000660` resolved
- 별칭:
  - `삼전` -> 삼성전자
  - `하이닉스` -> SK하이닉스
  - `SK  하이닉스` -> SK하이닉스, 명시 alias를 통해 resolved
  - `현대차` -> 현대자동차
- 공백:
  - `  삼성전자  ` resolved
- NFKC:
  - full-width ticker 또는 호환 문자 입력은 NFKC 후 매칭
- 빈 입력:
  - `""`, `"   "` -> not_found
- ambiguous:
  - `삼성` -> candidates 1개 이상, 지원 universe 후보만 포함, clarification message 존재
  - `SK` -> candidates 1개 이상, 지원 universe 후보만 포함, clarification message 존재
  - `현대` -> candidates 1개 이상, 지원 universe 후보만 포함, clarification message 존재
- unsupported:
  - `삼성전자우`
  - `005935`
  - `AAPL`
- not_found:
  - `999999`
  - `000001`
  - 빈 입력
  - `카카오`는 known unsupported fixture에 넣지 않는 한 제외
- fixture validation:
  - canonical security_id 중복 실패
  - ticker 중복 실패
  - alias가 서로 다른 종목에 충돌하면 실패
  - 빈 alias 실패
- corp_code:
  - `verification_status: candidate` 또는 `blocked`이면 반환 `SecurityIdentifier.corp_code is None`
  - `verification_status: verified`이면 반환 `SecurityIdentifier.corp_code` 값 존재
- ResolutionResult:
  - `resolved`는 `security` 필수, `candidates == []`, `matched_by in {"name", "ticker", "security_id", "alias"}`
  - `ambiguous`는 `security is None`, `len(candidates) >= 1`, `matched_by == "none"`
  - `not_found`는 `security is None`, `candidates == []`, `matched_by == "none"`
  - `unsupported`는 `security is None`, `candidates == []`, `matched_by == "unsupported_rule"`
- 판정 우선순위:
  - exact match가 ambiguous/unsupported보다 먼저 적용됨
  - 빈 입력은 unsupported rule에 도달하지 않고 `not_found`
- regression:
  - `pytest tests/unit/test_core_models.py tests/unit/test_status_contracts.py tests/unit/test_security_resolver.py -q`

## 13. 완료 기준
- [ ] 지원 종목 3개 canonical fixture 존재
- [ ] exact name/ticker/security_id resolved
- [ ] alias resolved
- [ ] NFKC 정규화와 빈 입력 not_found 테스트 통과
- [ ] ambiguous 입력을 임의 첫 후보로 확정하지 않음
- [ ] wrong ticker not_found
- [ ] 우선주/해외 ticker unsupported
- [ ] unsupported와 not_found 의미가 테스트로 분리됨
- [ ] corp_code 검증 상태가 fixture에 명시됨
- [ ] candidate/blocked corp_code는 반환 `SecurityIdentifier.corp_code`가 `None`
- [ ] canonical ID·ticker·alias 충돌과 빈 alias validation 실패
- [ ] ResolutionResult 상태별 불변조건 테스트 통과
- [ ] `matched_by` Literal 계약과 상태별 허용값 테스트 통과
- [ ] 판정 우선순위 테스트 통과
- [ ] provider 호출 없이 unit test만으로 동작 검증
- [ ] M1-01 테스트 회귀 없음

## 14. 검증 명령
```powershell
$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_core_models.py tests/unit/test_status_contracts.py tests/unit/test_security_resolver.py -q
$env:PYTHONPATH = ".deps;."; python -c "from app.core.resolver import SecurityResolver; print('ok')"
```

live OpenDART 검증은 credential과 별도 승인 전까지 실행하지 않는다.

## 15. fallback·rollback 제안
- corp_code 원본 검증이 막히면 `verification_status: blocked` 또는 `candidate`로 두고 M1-05 전 재검증 항목으로 넘긴다.
- alias가 모호하면 alias를 제거하거나 ambiguous로 보수 처리한다.
- resolver가 복잡해지면 fuzzy matching을 제외하고 exact mapping과 명시 alias만 유지한다.
- unsupported 판정이 흔들리면 지원 종목 selector fallback을 유지한다.

## 16. 중단 기준
- 기존 `SecurityIdentifier` field 변경이 필요해지는 경우
- status enum 변경이 필요해지는 경우
- provider/API/retrieval/UI 구현이 필요해지는 경우
- LLMStatus, LiteLLM, Gemini 등 M3 범위 코드가 필요해지는 경우
- OpenDART credential 또는 secret 값을 코드/문서에 기록해야 하는 경우
- 지원 종목을 3개 밖으로 확대해야 하는 경우

## 17. 승인
- 승인 일시: 2026-07-21
- 승인 범위: M1-02 Task Card 보완 후 구현 승인
- Git 작업 승인 포함 여부: 기본 `아니오`
