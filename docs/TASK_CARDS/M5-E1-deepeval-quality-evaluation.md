# TASK CARD — M5-E1 DeepEval + Questock Golden Evaluation

> 작성일: 2026-07-28
> 상태: `BATCH EVALUATION COMPLETE / QUALITY GATE FAIL`
> 기준 branch: canonical `main`
> 기준 코드 HEAD: `6b4d78e035c2aa9076a88f6c5f8777b31baf812a`
> 평가 대상 배포 release: `373ea00d4e06526a98898e9c38f4d4a7871b1a8f`
> 선행 상태: `M5-D1 PASS / DEPLOYED / COMPLETE`

## 1. 목적

현재 Questock의 답변 품질을 프로젝트 자체 점검만으로 주장하지 않고,
범용 LLM/RAG 평가 프레임워크로 반복 측정한다.

다만 범용 LLM 판정기가 금융 서비스의 숫자·종목·시점 안전성을 대신 검증하게
하지 않는다. 다음 두 층을 결합한다.

1. **DeepEval 범용 평가**
   - 질문에 답했는가
   - 제공된 근거에 충실한가
   - 검색된 근거가 질문에 적합한가
   - 초보자에게 필요한 수준으로 설명했는가
2. **Questock 결정론적 골든셋**
   - 미래정보 누출, 잘못된 종목, 근거 없는 가격·등락률·비교 주장,
     인용 불일치, 직접 투자 권유를 절대 실패 조건으로 검증

이 Task Card는 **평가 계획과 평가 구현만** 다룬다.
Gemini Flash와 Pro의 생성 품질 비교는 M5-E1 결과가 확정된 뒤
별도 Task Card에서 진행한다.

## 2. 조사 결론

### 2.1 선택: DeepEval

DeepEval을 Questock의 범용 평가 프레임워크로 선택한다.

선정 이유:

- pytest와 유사한 로컬 평가 흐름을 제공해 현재 프로젝트의 pytest 중심
  검증 구조에 별도 평가 플랫폼 없이 결합할 수 있다.
- RAG에 필요한 Answer Relevancy, Faithfulness,
  Contextual Relevancy 계열 지표를 제공한다.
- 단일 질문뿐 아니라 다중 턴 대화 평가 자산을 지원한다.
- Gemini 및 사용자 정의 LLM 연결을 지원하므로 기존 provider 환경과
  분리된 **평가 전용 judge**를 구성할 수 있다.
- G-Eval의 고정 평가 절차를 이용해 Questock의
  `초보자 유용성`을 강제 항목 수나 답변 길이가 아닌 품질 기준으로 평가할
  수 있다.

DeepEval을 “유일한 표준” 또는 “업계 표준”이라고 표현하지 않는다.
이 문서에서의 의미는 **Questock 구조와 일정에 가장 잘 맞는 범용
오픈소스 평가 도구**다.

### 2.2 비교 후보

| 후보 | 공식 기능상 장점 | 이번 단계에서 선택하지 않은 이유 |
|---|---|---|
| Ragas | Context Precision/Recall, Faithfulness, Response Relevancy 등 RAG 지표가 넓다. | Questock은 현재 pytest 결합, 다중 턴, 사용자 정의 평가 기준을 한 흐름에서 운영하는 편이 더 중요하다. |
| TruLens | RAG Triad로 문맥 관련성·근거성·답변 관련성을 관찰하기 좋다. | 이번 범위는 운영 추적 시스템보다 고정 데이터셋 기반 release 평가가 우선이다. |
| LangSmith | 데이터셋·실험·추적을 한 플랫폼에서 운영할 수 있다. | 촉박한 일정에 별도 hosted 평가 플랫폼과 데이터 전송 경계를 추가할 필요가 없다. |
| DeepEval | 로컬·pytest형 실행, RAG 지표, 다중 턴, G-Eval, Gemini/custom judge를 한 도구에서 제공한다. | 선택 |

### 2.3 공식 조사 자료

- DeepEval 소개와 pytest형 평가:
  <https://deepeval.com/docs/introduction>
- DeepEval 지표와 권장 구성:
  <https://deepeval.com/docs/metrics-introduction>
- DeepEval Gemini 연결:
  <https://deepeval.com/integrations/models/gemini>
- DeepEval G-Eval:
  <https://deepeval.com/docs/metrics-llm-evals>
- DeepEval 다중 턴 평가:
  <https://deepeval.com/docs/evaluation-multiturn-test-cases>
- Ragas 지표 목록:
  <https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/>
- TruLens RAG Triad:
  <https://www.trulens.org/getting_started/core_concepts/rag_triad/>
- LangSmith RAG 평가:
  <https://docs.langchain.com/langsmith/evaluate-rag-tutorial>
- LLM judge의 위치·장황성·자기 선호 편향에 대한 연구:
  <https://arxiv.org/abs/2306.05685>

## 3. 평가 원칙

### 3.1 범용 점수와 안전 게이트를 합산하지 않는다

DeepEval 평균 점수가 높더라도 Questock hard gate가 한 건이라도 실패하면
전체 결과는 `FAIL`이다. 범용 지표 평균으로 금융 안전 오류를 상쇄하지 않는다.

### 3.2 답변 생성과 평가를 분리한다

평가 대상 답변은 case당 한 번 생성하고 응답·검색 문맥·인용·설정의 hash를
고정한다. DeepEval judge는 고정된 결과만 평가한다.

이렇게 해야 judge 재실행 때 제품 답변이 다시 생성되어 결과 원인이 섞이지
않는다.

### 3.3 judge 점수는 먼저 교정한다

LLM-as-a-judge는 비결정적이며 위치·길이·모델 계열에 따른 편향이 있을 수 있다.
따라서 임의의 `0.5` 또는 `0.8`을 바로 release 기준으로 사용하지 않는다.

- pilot case에 Human Owner/검수자가 먼저 기대 판정을 기록한다.
- known-good, borderline, known-bad 대조군으로 judge를 교정한다.
- 지표별로 사람 판정과 `5/6` 이상 일치할 때만 해당 지표를 품질 판정에 쓴다.
- 미달 지표는 삭제하지 않고 `REPORT_ONLY`로 남긴다.
- held-out 평가를 본 뒤 threshold를 유리하게 다시 조정하지 않는다.

### 3.4 길이를 품질로 오인하지 않는다

초보자 유용성은 다음 기준으로 평가한다.

- 질문에 먼저 직접 답한다.
- 필요한 용어만 쉬운 표현으로 설명한다.
- 질문 난이도에 비례한 충분한 상세도를 제공한다.
- 불확실성과 추가 확인 사항을 구분한다.
- 정해진 section 수나 긴 답변 자체에 가점을 주지 않는다.
- 근거에 없는 배경지식을 사실처럼 추가하지 않는다.

## 4. 평가 데이터셋

### 4.1 구성

초기 범위는 **pilot 6건 + held-out 24건**으로 제한한다.

#### Pilot 6건

- known-good 2건
- borderline 2건
- known-bad 2건
  - 관련 없는 답변
  - 잘못된 종목 또는 미래 근거가 섞인 답변

Pilot은 threshold와 rubric 검증에만 사용하며 최종 품질 점수에서 제외한다.

#### Held-out 24건

| 유형 | 건수 | 확인 대상 |
|---|---:|---|
| 기준시점 가격·등락 | 4 | 가격, 방향, 등락률, checkpoint |
| 주가 변동 원인 | 4 | 가격 결과와 당시까지의 뉴스 원인 연결 |
| 최근 이슈·호재·악재·위험 | 4 | 질문 의도, 사건 요약, 불확실성 |
| 공시·리포트 활용 | 3 | 공식 사실과 관점의 역할 구분 |
| 주식 초보 용어·설명 | 2 | 쉬운 설명, 과잉 구조화 방지 |
| 근거 대조형 답변 | 3 | 중복 원출처, 합의·충돌·미확인 |
| 다중 턴 대화 | 4 | 후속 질문, 종목 전환, 시점 전환, 대화 오염 방지 |
| 합계 | 24 | 삼성전자·SK하이닉스·현대차와 여러 기준시점에 분산 |

### 4.2 기존 자산 재사용 경계

다음 기존 자산은 schema와 hard gate의 seed로 사용한다.

- `tests/fixtures/evaluation/m3_golden_cases.json`
- `tests/fixtures/evaluation/m5_time_grounding_cases.json`
- `tests/fixtures/m5_d1_event_pairs.json`
- `scripts/evaluate_m5_d1_event_grouping.py`
- `scripts/m3_gate.py`
- `tests/integration/test_m5_golden.py`

기존 구현·threshold 조정에 이미 사용된 질문을 그대로 held-out이라고 부르지
않는다. 중복 case는 회귀 테스트에 남기고, 최종 보고용 held-out 질문은
표현·시점·종목 조합을 새로 구성한다.

### 4.3 평가 입력의 보안·저작권 경계

외부 judge에 전달할 수 있는 항목:

- 사용자 질문
- Questock public response
- runtime이 실제 사용한 commit-safe evidence context
- 공개 citation metadata

외부 judge에 전달하면 안 되는 항목:

- 증권사 리포트 PDF 원문
- 원문 evidence excerpt
- Git ignored 원문 작업 파일
- credential 또는 내부 경로
- 공개 답변 생성에 쓰이지 않은 자료

리포트는 Questock이 작성하고 승인한 짧은 관점 요약만 사용할 수 있다.
평가 raw artifact는 Git ignored 로컬 경로에 보관하고, Git에는 case ID,
설정, hash, 수치, 판정, 원문을 재현하지 않는 짧은 사유만 남긴다.

## 5. 평가 지표

### 5.1 DeepEval 범용 지표

초기 core metric은 네 개로 제한한다.

1. **Answer Relevancy**
   - 사용자의 실제 질문에 직접 답했는가
2. **Faithfulness**
   - 답변의 사실 주장이 제공된 evidence context로 뒷받침되는가
3. **Contextual Relevancy**
   - 검색 문맥이 질문 해결에 실제로 필요한 자료인가
4. **G-Eval: Beginner Usefulness**
   - 쉬운 설명, 적정 상세도, 불확실성 표현, 불필요한 반복을 종합 판정

Contextual Precision/Recall은 trusted gold context 라벨이 필요한 만큼
M5-E1 초기 필수 지표로 두지 않는다. 이후 gold context가 충분히 라벨링된
경우에만 탐색 지표로 추가한다.

### 5.2 Questock hard gates

다음은 LLM judge가 아닌 결정론적 검사와 사람이 확인 가능한 locator로
검증한다.

| Hard gate | 통과 기준 |
|---|---:|
| future information leakage | `0` |
| wrong company evidence | `0` |
| unsupported price/time/percent | `0` |
| unsupported comparison claim | `0` |
| direct investment advice | `0` |
| 공개 claim-citation 불일치 | `0` |
| 가격·방향·등락률 정확도 | `100%` |
| 중요 인용 링크 유효성 | `100%` |
| false independent lineage | `0` |
| M5-D1 grouping precision | `>= 0.90` |

자료가 부족한 상황에서 제한 문구를 올바르게 제시한 답변은
“상세 답변이 짧다”는 이유만으로 실패시키지 않는다.

### 5.3 결과 집계

지표별로 다음을 기록한다.

- mean
- median
- minimum
- calibrated threshold 통과율
- 실패 case ID와 짧은 judge reason
- provider 호출 수, token, 비용, latency

Held-out 실행 전 다음 통과 기준을 고정한다.

- required metric별 threshold 통과율: `>= 0.80`
- required metric별 mean: 교정된 threshold 이상
- required metric evaluator error: `0`
- `REPORT_ONLY` 지표는 전체 PASS/FAIL 계산에서 제외

단일 총점은 만들지 않는다. 최종 상태는 다음처럼 표시한다.

```text
Hard gates: PASS | FAIL
Generic metrics: PASS | REPORT_ONLY | FAIL
Overall: PASS only when hard gates PASS and required calibrated metrics PASS
```

## 6. Judge 계약과 호출 예산

### 6.1 Judge 모델

- 제품 답변 생성 모델과 judge 모델 설정을 분리한다.
- `EVALUATION_JUDGE_MODEL`은 model-list와 실제 generation smoke를 모두
  통과한 **Pro 계열 고정 모델 ID**를 기록한다.
- temperature는 `0`으로 고정한다.
- exact model ID, provider 설정, rubric version, DeepEval version을
  결과에 남긴다.
- 평가 이후의 Flash/Pro 생성 모델 비교에서는 같은 Pro judge의 점수만으로
  승자를 정하지 않는다. 자기 계열 선호 가능성을 한계로 기록하고,
  blind output, 순서 교대, 결정론적 gate, 필요 시 Human Owner tie-break를
  별도 계획에 포함한다.

### 6.2 호출 예산

DeepEval 지표 하나가 내부적으로 복수 judge 호출을 사용할 수 있으므로
`case 수 × metric 수`를 실제 API 요청 수라고 가정하지 않는다.

- pilot: evaluator provider 요청 최대 `80`
- held-out: evaluator provider 요청 최대 `300`
- 동시성: 최대 `2`
- retry: 원칙 `0`; 도구 내부 retry가 불가피하면 호출 수에 포함하고 기록
- budget 도달 시: 즉시 중단하고 `PARTIAL / BUDGET_STOP` 기록
- provider 오류 답변을 0점 품질 답변으로 섞지 않고 `EVAL_ERROR`로 분리

실제 답변 생성 호출은 held-out case당 1회만 허용하고 hash로 고정한다.

## 7. 구현 계획

### M5-E1-0 — 계약 고정

- 이 Task Card Human Owner 승인
- 평가 대상 release와 코드 SHA 고정
- 평가 범위와 금지 데이터 확인
- DeepEval exact version 후보 확인
- 실행 전 API 비용 상한 승인

완료 기준:

- 실행 중 지표·threshold·데이터셋을 임의 변경하지 않을 기준이 문서화됨

### M5-E1-1 — 격리된 dependency/provider preflight

- DeepEval을 runtime dependency가 아닌 별도 `eval` optional/dev group에 고정
- Python 3.11, Pydantic, LiteLLM 기존 버전과 충돌 여부 확인
- 로컬-only 실행을 기본으로 하고 Confident AI hosted upload는 사용하지 않음
- Gemini judge model-list 확인
- commit-safe 짧은 샘플 1건으로 smoke

완료 기준:

- runtime image와 production dependency에 영향 없음
- judge 응답, token/cost/latency 계측 가능
- 원문 리포트·credential 전송 없음

### M5-E1-2 — 데이터셋과 deterministic gate

예상 파일:

- `tests/fixtures/evaluation/m5_e1_pilot_cases.json`
- `tests/fixtures/evaluation/m5_e1_held_out_cases.json`
- `tests/unit/test_m5_e1_fixture_contract.py`
- 기존 gate 확장 또는 `scripts/m5_e1_hard_gate.py`

작업:

- pilot 6건과 held-out 24건 작성
- 종목·날짜·checkpoint·질문 유형 분포 검사
- 미래정보, 종목, 가격, 인용, lineage locator 고정
- 기존 회귀 질문과 held-out 중복 검사

### M5-E1-3 — DeepEval adapter와 pilot 교정

예상 파일:

- `scripts/evaluate_m5_e1_deepeval.py`
- `tests/unit/test_m5_e1_eval_adapter.py`

작업:

- 고정 응답과 context를 DeepEval test case로 변환
- core metric 4개 구성
- G-Eval 평가 절차와 rubric version 고정
- pilot 사람 판정과 judge 판정 비교
- 지표별 threshold 또는 `REPORT_ONLY` 상태 고정

완료 기준:

- required metric은 사람 판정과 `5/6` 이상 일치
- known-bad가 통과하는 rubric은 held-out 전에 수정
- 교정 결과와 변경 이력이 기록됨

### M5-E1-4 — Held-out 실행

실행 순서:

1. 평가 대상 release와 환경 확인
2. 24개 응답을 case당 1회 생성하고 hash 고정
3. hard gate 실행
4. hard gate PASS일 때 DeepEval 실행
5. 오류와 품질 실패 분리
6. 결과 요약과 case별 실패 분석 생성

hard gate가 실패해도 진단 목적의 DeepEval 실행은 가능하지만,
전체 상태를 `PASS`로 표시할 수 없다.

### M5-E1-5 — 검수와 종료

필수 산출물:

- sanitised 평가 결과 JSON
- 지표별 요약 표
- hard gate 결과
- failure taxonomy
- API 호출·token·비용·latency 기록
- `PASS`, `PARTIAL`, `FAIL` 중 하나의 closure
- Pro 비교 진행 가능 여부

완료 후에만 별도 M5-E2 모델 비교 계획을 작성한다.

## 8. 검수 항목

### 코드·데이터

- 평가 dependency가 production runtime에 들어가지 않았는가
- fixture가 schema 검사를 통과하는가
- pilot과 held-out이 분리되었는가
- 답변 재생성 없이 동일 hash로 judge를 재실행할 수 있는가
- raw artifact가 Git에 포함되지 않는가
- secret scan이 PASS인가

### 평가 타당성

- known-bad가 낮게 평가되는가
- 질문에 맞는 짧은 답변이 길이 때문에 실패하지 않는가
- 장황하지만 근거 없는 답변이 상세하다는 이유로 통과하지 않는가
- future leakage와 wrong-company가 DeepEval 점수와 무관하게 실패하는가
- no-evidence 제한 답변이 올바르게 평가되는가
- judge reason이 실제 입력과 metric 기준을 설명하는가

### 재현성

- release SHA, dataset version, judge model, framework version이 고정됐는가
- temperature, concurrency, retry가 기록됐는가
- 평가 시각과 기준시점이 혼동되지 않는가
- 동일 frozen output 재평가의 판정 변동이 기록됐는가

## 9. 중단 조건

다음 중 하나면 결과를 과장하지 않고 중단한다.

- DeepEval 설치가 기존 runtime dependency를 변경해야만 가능함
- judge 입력에 금지된 리포트 원문·excerpt·credential이 포함됨
- pilot에서 사람 판정과 `5/6` 미만으로 일치하는 지표를 필수 gate로 써야 함
- API budget을 초과함
- 평가 오류와 제품 품질 실패를 구분할 수 없음
- held-out 확인 후 threshold 또는 rubric을 유리하게 변경하려 함
- 평가 대상 release가 실행 중 변경됨

중단 시 상태는 `PARTIAL` 또는 `BLOCKED`로 기록하고,
성공한 일부 지표만으로 전체 `PASS`를 선언하지 않는다.

## 10. 완료 기준

M5-E1은 다음을 모두 만족해야 완료다.

- DeepEval exact version과 고정 judge 계약이 기록됨
- pilot 6건 교정 완료
- held-out 24건이 고정 출력으로 평가됨
- Questock hard gate 전체 PASS
- required DeepEval metric이 교정 기준과 최종 threshold를 통과함
- report-only metric과 평가 한계가 숨김없이 기록됨
- raw evidence/credential/Git ignored 원문이 외부 judge나 Git에 노출되지 않음
- 평가 결과가 Source of Truth와 work log에 동기화됨
- 이후 Pro 비교가 가능한지 명확한 결론이 남음

## 11. 비범위

- Gemini Flash와 Pro의 생성 품질 비교
- 더 나은 모델을 production 기본값으로 변경
- runtime 답변 로직 또는 UI 수정
- 실시간 데이터 기능 추가
- LangSmith/Confident AI hosted 계정 또는 dashboard 도입
- 평가 결과만을 근거로 배포
- 골든셋 실패를 DeepEval 평균으로 상쇄

## 12. 현재 승인 경계

승인 후 실제 수행한 작업:

- DeepEval `4.1.4`와 google-genai `2.14.0` 평가 dependency 고정
- Python `3.11.15` 격리 평가 환경 설치
- pilot 6건과 held-out 24건 fixture 및 평가 adapter 구현
- Gemini 3.5 Flash held-out 답변 24건과 setup 답변 4건 고정
- 결정론적 hard gate와 pilot 교정 실행
- Gemini 3.1 Pro Preview held-out 평가 시도

현재 결과:

- DeepEval 설치: `PASS`
- hard gate: `24/24 PASS`
- M5-D1 grouping: precision `1.0`, recall `1.0`, false positive `0`
- pilot: `6/6` 실행 완료
- held-out: quota 429로 중간 이후 evaluator error 발생, `PARTIAL`
- judge: `gemini-3.1-pro-preview`
- judge logical requests: pilot `63`, held-out `231`
- framework reported cost: pilot `$0.083328`, held-out `$0.468158`
- Pro 비교: `NOT_RUN`
- commit/push/PR/deploy: `NOT_RUN`

closure와 재개 기준:

- `docs/agent_handoff/M5_E1_EVALUATION_PARTIAL_2026-07-28.md`
- quota 회복 후 frozen response와 pilot threshold를 그대로 사용한다.
- 제품 답변을 재생성하지 않고 evaluator error cell만 재평가한다.
- required metric 전체가 채워지기 전 Pro 비교를 시작하지 않는다.

## 13. 2026-07-29 Gemini Pro Batch 대체 실행

### 전환

Gemini 3.1 Pro 일반 API의 `250 RPD`를 초과한 상태에서 Human Owner가
밤 사이 비동기 실행을 선택했다. 기존 frozen response와 hard gate를
유지하고, 일반 API와 별도 한도를 사용하는 Batch API로 별도 run을
수행했다.

기존 DeepEval built-in partial 결과와 Batch 결과는 혼합하지 않았다.
Batch run은 네 평가 차원을 고정 rubric으로 각각 평가한
G-Eval형 교차평가다.

### 실행

- judge: `gemini-3.1-pro-preview`
- rubric: `m5-e1-batch-rubric-v1`
- pilot: `6`
- held-out: `24`
- metric: `4`
- Batch request: `120`
- Batch response: `120/120`
- terminal state: `JOB_STATE_SUCCEEDED`
- frozen 제품 답변 재생성: `NOT_RUN`

### 결과

- hard gate: `24/24 PASS`
- Answer Relevancy: `22/24`, `PASS`
- Faithfulness: `24/24`, `PASS`
- Contextual Relevancy: `REPORT_ONLY`
- Beginner Usefulness: `12/24`, `FAIL`
- overall: `EVALUATION COMPLETE / QUALITY GATE FAIL`
- held-out 확인 후 threshold 변경: `NOT_RUN`
- Gemini 생성 모델 비교: `NOT_RUN`

세부 closure:

- `docs/agent_handoff/M5_E1_BATCH_EVALUATION_2026-07-29.md`
- `data/evaluation/m5_e1_batch_summary.json`
