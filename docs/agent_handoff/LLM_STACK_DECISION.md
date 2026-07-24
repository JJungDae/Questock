# LLM_STACK_DECISION.md

> 결정일: 2026-07-21
> 상태: P0 채택
> 기본 사용 정책: Gemini API 무료 등급 우선 사용
> 가용성 상태: credential 연결·AI Studio quota 확인·sanitized live smoke 전까지 미검증

## 결정

```text
AnswerComposer
→ project-owned Evidence/context adapter
→ ChatPromptTemplate
→ RunnableLambda(project-owned LLMClient)
→ LiteLLM Python SDK
→ Gemini API
→ Pydantic structured parser
→ project-owned validators
```

- 기본 model: `gemini/gemini-2.5-flash`
- 사용 정책: Gemini API 무료 등급 우선 사용
- 가용성: credential·활성 quota·live 호출 미검증
- 자동 billing 연결 또는 유료 호출 전환: 금지
- 유료 모델 전환: MVP end-to-end 완성과 Critical regression 이후 별도 승인
- credential: `GEMINI_API_KEY`
- config: `LLM_MODEL`
- LiteLLM 사용 형태: Python SDK
- P0 제외: Proxy, Router, 자동 fallback, multi-LLM, 사용자 모델 선택, Google Search Grounding, 유료 모델 비교·전환

## 선택 이유

- MVP 핵심은 provider→retrieval→Evidence→답변→검증 전체 흐름 완성이다.
- LiteLLM을 adapter 내부에 한정하면 provider 교체 비용을 낮추면서 코어 구조를 바꾸지 않는다.
- Gemini 2.5 Flash의 stable model ID를 고정해 preview·latest alias 변경 위험을 피한다.
- Gemini 환각은 유료 모델 선행 도입보다 Evidence 제한과 validator로 통제한다.
- 무료 등급의 quota·rate limit은 운영 성능이 아니라 MVP 흐름 검증 조건으로 다룬다.


## 무료 등급 데이터 처리 원칙

- 무료 등급의 입력·출력이 Google 제품 개선에 사용될 수 있음을 전제로 사용한다.
- API key, secret, 로컬 절대 경로, 내부 오류 원문과 원본 로그를 Gemini에 전달하지 않는다.
- 개인 계좌번호, 실제 보유 수량, 자산 규모 등 개인 금융정보를 입력하지 않도록 UI에 안내한다.
- LLM에는 필요한 사용자 질문과 선택된 Evidence snippet만 최소 전송한다.
- 전체 세션 기록이나 원문 파일 전체를 기본 전송하지 않는다.
- 리서치 리포트는 외부 제3자 LLM 처리 허용 여부를 문서별로 확인한다.
- 외부 처리가 허용되지 않았거나 판단이 불명확한 리포트는 Gemini 입력에서 제외하고 fixed template·비LLM 경로만 사용한다.

리포트 manifest에는 다음 필드 하나만 추가한다.

```text
external_llm_processing_allowed: bool
```

- 기존 `usage_note`에 확인 근거와 제한 사항을 기록하므로 별도 `usage_basis` 필드는 추가하지 않는다.
- P0에는 redaction pipeline이 없으므로 별도 `redaction_required` 필드를 추가하지 않는다.
- redaction이 필요한 자료는 `external_llm_processing_allowed=false`로 처리한다.
- 필드가 없거나 `false`이면 LLM 전송을 허용하지 않는다.

## 내부 경계

`AnswerComposer`는 LiteLLM이나 Gemini raw response를 직접 다루지 않는다.

`LLMClient`가 다음을 반환한다.

```text
content
model
provider
usage
finish_reason
latency_ms
status
```

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

- `LLMStatus`는 뉴스·공시·리포트의 `ProviderResult` 상태와 분리한다.
- LLM 실패를 `missing_sources`나 `no_data`로 기록하지 않는다.
- Evidence가 유효하면 fixed template 응답을 우선한다.
- `content_blocked`와 schema·parse 실패인 `invalid_response`를 구분한다.
- raw exception과 prompt 원문을 사용자에게 노출하지 않는다.


## 실행 설정과 live 검증

M3 구현 전 다음 설정을 명시한다.

```text
LLM_THINKING_BUDGET
LLM_MAX_OUTPUT_TOKENS
LLM_TIMEOUT_SECONDS
```

- Gemini의 동적 thinking 기본값을 그대로 사용하지 않는다.
- fixture에서 `thinking_budget=0`과 `1024`를 비교한다.
- Critical set, 구조화 출력 안정성, full golden 기준과 p95 latency를 만족하는 가장 작은 값을 pin한다.
- 승인된 credential로 sanitized live smoke를 최소 1회 수행한다.
- live smoke에서 실제 model ID, structured output 또는 JSON parse, timeout, usage 반환을 확인한다.
- fixture 성공과 live API 성공을 별도로 기록한다.
- live smoke를 수행하지 않았으면 “Gemini live 연동 완료”라고 기록하지 않는다.
- 무료 quota 실패 시 billing을 자동 연결하거나 유료 모델로 전환하지 않는다.

## 정확성 원칙

- structured output은 형식 보조이지 사실성 보장이 아니다.
- Evidence 밖 사실·숫자·URL은 금지한다.
- 종목·수치 귀속·citation·투자 조언은 코드 validator가 검사한다.
- parse 또는 의미 validation 실패 응답을 그대로 사용자에게 반환하지 않는다.
- 모델 ID 변경 후 Critical regression을 다시 실행한다.


## LiteLLM dependency 승인 기록

### M3-00 LangChain composition boundary

- Selected architecture: LangChain Core `RunnableSequence` around the
  project-owned direct LiteLLM adapter boundary.
- Direct runtime pins: `langchain-core==1.5.1`, `litellm==1.83.7`.
- Composition ownership: `ChatPromptTemplate` -> project-owned async
  `LLMClient` boundary through `RunnableLambda` -> Pydantic parser.
- LangChain does not own retrieval, Evidence policy, permission checks,
  context budgeting, citation validation, numeric validation, or public status
  contracts.
- `langsmith` remains a locked transitive dependency. Production code and
  persistent tests do not import it directly.
- Runtime must set `LITELLM_LOCAL_MODEL_COST_MAP=True` before importing
  LiteLLM, explicitly set `LANGSMITH_TRACING=false` and
  `LANGCHAIN_TRACING_V2=false`, and invoke chains with `callbacks=[]`.
- No full `langchain`, `langchain-litellm`, Router, Proxy, model fallback,
  callback logging, remote prompt, or live Gemini call is part of M3-00.
- Deterministic dependency source: repository `uv.lock`.

- package: `litellm`
- 필요한 이유: Gemini 호출을 project-owned `LLMClient` 뒤에서 정규화하고 향후 adapter 교체 범위를 제한
- 기존 dependency로 대체하기 어려운 이유: 현재 저장소에는 provider-neutral LLM 호출·예외 normalization 계층이 없음
- license: 오픈소스 영역 MIT, enterprise 디렉터리는 별도 license이므로 P0에서 사용하지 않음
- exact version: M3 compatibility smoke 후 선택하고 merge 전에 pin
- 배포 영향: transitive dependency, 이미지 크기, import/startup 시간을 M3에서 확인
- 제거 방법: `LLMClient`는 유지하고 `litellm_client.py` adapter만 native SDK adapter로 교체
- lock file: `pyproject.toml`과 lock file 변경을 별도 diff로 검토
- 구현 산출물: dependency diff, 빈 값만 있는 `.env.example`, adapter mock, compatibility fixture, sanitized live smoke 기록

## 구현 시점

M1-01 core model은 수정하지 않는다.
실제 dependency와 adapter 구현은 M3 AnswerComposer 작업 계획에서 별도 승인 후 진행한다.


## 유료 모델 전환 gate

다음 조건을 모두 만족한 뒤에만 유료 Gemini 모델을 검토한다.

- provider→retrieval→Evidence→answer→validator end-to-end 동작
- Critical regression 통과
- 무료 등급 quota가 실제 개발·시연을 방해한다는 증거
- 동일 fixture로 품질·지연·비용 비교 계획 승인

모델 변경은 `LLM_MODEL` 설정과 adapter compatibility test로 제한한다.
