# TASK CARD - M1-01 Core Models and Status Contracts

> 개정일: 2026-07-21  
> 개정 사유: 다중 기업 문서·Evidence 귀속 validation 불변조건 보완

## 1. 계획 연결
- Task bundle: B1
- Step: M1-01 core models와 상태 계약
- 우선순위: P0
- 관련 위험 ID: R02, R05, R06, R25, R29, R30, R32, R38
- 관련 taxonomy: entity_resolution, intent_routing, source_selection, citation_support, evidence_sufficiency, abstention, prohibited_advice, provider_timeout, provider_rate_limit, stale_data

## 2. 목적
FastAPI/RAG 구현 전에 금융 RAG의 최소 데이터 계약과 상태 계층을 Pydantic 모델로 고정하고, provider 장애·검색 관련도·근거 충분성·안전 차단 상태가 섞이지 않도록 한다.

## 3. 실제 확인한 현재 상태
- 확인 파일:
  - `docs/agent_handoff/PROJECT_PLAN_FINAL_PASS.md`
  - `docs/agent_handoff/FINANCIAL_CAPABILITY_BASELINE.md`
  - `docs/agent_handoff/RISK_RESPONSE_MATRIX.md`
  - `docs/TASK_CARDS/B0-M0-01-03-planning.md`
- 확인 함수·class: 아직 없음.
- 현재 동작:
  - `app/`, `tests/`, `pyproject.toml` 없음.
  - dependency와 테스트 러너가 아직 없음.
- 미확인 사항:
  - Python 버전 실제 설치 상태.
  - 사용할 Pydantic major version.
  - lint/type checker 선택.

## 4. 선행 조건
- [x] Human Owner가 B0 종목 3개를 승인한다 — 삼성전자·SK하이닉스·현대자동차
- [ ] Human Owner가 B0 intent 전체 범위를 승인한다.
- [ ] Human Owner가 M1-01 구현을 별도 승인한다.
- [ ] Python dependency 방식 결정: `pyproject.toml` 신규 생성 또는 기존 dependency 파일 발견 시 기존 방식 준수.
- [ ] app/test scaffold 생성 승인.

## 5. 입력·출력
- 입력:
  - B0에서 승인된 지원 종목/intent 범위
  - Financial Capability Baseline의 core_now 최소 계약
- 출력:
  - core models
  - status enums 또는 literal contracts
  - serialization/schema tests

## 6. 수정 범위
- 수정 가능:
  - `pyproject.toml` only if no dependency file exists and user approves scaffold
  - `app/core/models.py`
  - `app/core/status.py`
  - `tests/unit/test_core_models.py`
  - `tests/unit/test_status_contracts.py`
- 수정 금지:
  - `docs/agent_handoff/`
  - provider implementation
  - resolver behavior
  - retrieval implementation
  - API route/UI
  - LLM prompt/composer/validator
  - P1/M5 model, DB schema, migration

## 7. 구현 요구사항
1. 다음 core model만 만든다.
   - `SecurityIdentifier`
   - `DateRange`
   - `QueryPlan`
   - `MarketSnapshot`
   - `FinancialDocument`
   - `Evidence`
   - `ProviderResult`
   - `RetrievalRequest`
   - `RetrievalResult`
   - `SessionContext`
   - `FinancialAnswer`
2. 다음 상태 계층을 분리한다.
   - Resolution: `resolved`, `ambiguous`, `not_found`, `unsupported`
   - Provider: `ok`, `no_data`, `invalid_query`, `unauthorized`, `rate_limited`, `timeout`, `provider_unavailable`, `parse_error`
   - Retrieval: `ok`, `empty`, `low_relevance`
   - Evidence Decision: `complete`, `partial`, `provider_failed`, `no_evidence`, `blocked`
3. `FinancialDocument`는 단일 `security_id` 대신 다음 field를 둔다.
   - `primary_security_ids: list[str]`
   - `mentioned_security_ids: list[str]`
4. `Evidence`는 다음 귀속 field를 둔다.
   - `subject_security_ids: list[str]`
   - `mentioned_security_ids: list[str]`
   - `scope: company_specific | industry_common | multi_company`
5. 다음 validation 불변조건을 구현한다.
   - FinancialDocument의 primary/mentioned 합집합은 non-empty
   - primary와 mentioned에 동일 security ID 중복 금지
   - Evidence subject는 연결 Document의 primary/mentioned 범위 안에 있어야 함
   - company_specific은 숫자 유무와 무관하게 subject 정확히 1개
   - industry_common은 subject 빈 목록
   - multi_company는 subject 2개 이상
   - Evidence subject와 mentioned 중복 금지
6. `source_url`은 nullable로 둔다.
7. `locator`는 빈 dict 또는 null이 되지 않도록 validation한다.
8. 사용자 응답에 로컬 절대 경로가 들어가지 않도록 모델 또는 test에서 금지 기준을 둔다.
9. 주체가 불명확한 수치를 허용하는 별도 자동 추론 model은 만들지 않는다.
10. extension-only model은 만들지 않는다.
   - `FinancialMetric`
   - `Claim`
   - `ContradictionGroup`
   - `PatternMatchResult`
   - 범용 `Event`
   - user/auth/watchlist models

## 8. 완료 기준
- [ ] core model import 가능
- [ ] JSON serialization round-trip test 통과
- [ ] 삼성전자·SK하이닉스 공동 기사 `FinancialDocument` fixture 통과
- [ ] 삼성전자 전용·SK하이닉스 전용·industry_common Evidence fixture 통과
- [ ] `subject_security_ids`가 없거나 2개 이상인 company-specific Evidence가 숫자 유무와 무관하게 validation 실패
- [ ] industry_common subject non-empty validation 실패
- [ ] multi_company subject 1개 이하 validation 실패
- [ ] Document primary/mentioned 빈 합집합·중복 validation 실패
- [ ] Evidence subject가 Document 종목 범위 밖이면 validation 실패
- [ ] nullable `source_url` test 통과
- [ ] 필수 locator validation test 통과
- [ ] Provider/Retrieval/EvidenceDecision 상태가 섞이지 않는 test 통과
- [ ] extension-only class가 생성되지 않음
- [ ] secret/local absolute path 미노출 test 또는 validation 기준 존재

## 9. 검증
- targeted unit:
  - `pytest tests/unit/test_core_models.py`
  - `pytest tests/unit/test_status_contracts.py`
- integration:
  - NOT_RUN for M1-01 unless minimal import smoke is added
- Critical:
  - fake locator/local path blocking unit
  - provider timeout vs no_data status separation unit
  - 삼성전자·SK하이닉스 공동 기사 subject/scope schema unit
  - company-specific 사실·수치 Evidence의 subject 정확히 1개 unit
  - industry_common·multi_company scope invariant unit
  - Document/Evidence 종목 집합 관계 unit
- smoke:
  - `python -c "from app.core.models import SecurityIdentifier, Evidence; print('ok')"`
- 미실행 가능 항목:
  - API smoke, provider live test, UI smoke, Docker smoke

## 10. fallback·rollback 제안
- Pydantic version 충돌이 있으면 Python `dataclasses` + explicit validators로 축소한다.
- dependency 추가가 막히면 dependency 파일 생성 없이 pure Python model skeleton과 tests만 작성한다.
- status enum이 과하게 복잡하면 `Literal[...]`로 시작한다.
- extension field가 필요해 보이면 이번 Task에서는 `metadata: dict`에 보관하고 별도 승인 전 새 class를 만들지 않는다.
- rollback은 생성 파일 제거 또는 후속 patch로 가능하나, 사용자 승인 없는 삭제는 수행하지 않는다.

## 11. 중단 기준
- app scaffold 생성이 승인되지 않은 경우
- dependency 추가가 필요한데 승인이 없는 경우
- B0 intent가 확정되지 않아 QueryPlan field가 흔들리는 경우
- provider 구현이나 API route까지 동시에 필요해지는 경우
- P1 auth/user DB 또는 M5 기능이 model에 들어가야 하는 경우

## 12. 승인
- 승인 일시: 2026-07-21, 사용자 메시지 "현재 계획에서 승인이 필요한 요소는 모두 허가할게."
- 승인 범위:
  - M1-01 core models와 상태 계약 구현
  - `app/`, `tests/` scaffold 생성
  - `pyproject.toml` 생성
  - Pydantic/pytest dependency를 workspace 내부 test target에 설치
  - `.gitignore`, `.env.example` 생성
  - SK하이닉스 DART/회사 정보 재확인
  - targeted unit test와 import smoke 실행
  - live API 호출은 credential이 없으면 실행하지 않음
- Git 작업 승인 포함 여부: 기본 `아니오`
