# M5-E1 Gemini Pro Batch Evaluation

> 실행일: 2026-07-29
> 상태: `EVALUATION COMPLETE / QUALITY GATE FAIL`
> 평가 대상 release: `373ea00d4e06526a98898e9c38f4d4a7871b1a8f`
> 제품 generator: `gemini/gemini-3.5-flash`
> Batch judge: `gemini-3.1-pro-preview`

## 1. 전환 이유

기존 DeepEval held-out 실행은 Gemini 3.1 Pro의 일반 API 일일 한도
`250 RPD`를 초과해 HTTP 429로 중단됐다.

Gemini 2.5 Pro는 model-list와 AI Studio 한도에는 표시됐지만 이 프로젝트의
실제 generation 호출에서 신규 사용자 사용 불가 HTTP 404를 반환했다.

밤 사이 비동기 실행이 가능하다는 Human Owner 판단에 따라 일반 API와 별도
한도를 사용하는 Gemini Batch API로 별도 평가 run을 만들었다.

## 2. 평가 계약

- 기존 held-out 제품 답변 24건과 setup 답변 4건을 재생성하지 않았다.
- 기존 금융 hard gate 결과 `24/24 PASS`를 그대로 사용했다.
- pilot 6건과 held-out 24건에 네 지표를 각각 적용해 Batch 요청 120건을
  제출했다.
- judge 입력은 사용자 질문, 공개 답변, runtime이 실제 사용한 commit-safe
  근거 요약으로 제한했다.
- 리포트 PDF 원문, 원문 excerpt, credential, 내부 경로는 전송하지 않았다.
- 기존 DeepEval built-in partial 점수와 Batch 점수를 같은 aggregate에
  혼합하지 않았다.
- rubric은 `m5-e1-batch-rubric-v1`, temperature 요청값은 `0`,
  thinking level은 `low`로 고정했다.

Batch는 2026-07-29 01:42 KST 제출 후 약 4분 만에
`JOB_STATE_SUCCEEDED`로 끝났고, 120건 모두 구조화 응답으로 수집됐다.

## 3. Pilot 교정

| 지표 | threshold | human agreement | false pass | 상태 |
|---|---:|---:|---:|---|
| Answer Relevancy | 0.3 | 5/6 | 0 | REQUIRED |
| Faithfulness | 0.5 | 6/6 | 0 | REQUIRED |
| Contextual Relevancy | 0.0 | 5/6 | 1 | REPORT_ONLY |
| Beginner Usefulness | 0.9 | 6/6 | 0 | REQUIRED |

Contextual Relevancy는 noisy-context 음성 대조군을 구분하지 못했으므로
release gate로 사용하지 않는다.

held-out 결과를 본 뒤 threshold를 낮추지 않았다.

## 4. Held-out 결과

| 지표 | 통과 | 평균 | 상태 |
|---|---:|---:|---|
| Answer Relevancy | 22/24 | 0.8917 | PASS |
| Faithfulness | 24/24 | 1.0000 | PASS |
| Contextual Relevancy | 24/24 | 0.9167 | REPORT_ONLY |
| Beginner Usefulness | 12/24 | 0.7375 | FAIL |

결정론적 금융 hard gate는 `24/24 PASS`지만 필수 지표인
Beginner Usefulness가 80% 통과 기준을 충족하지 못해 전체 상태는
`FAIL`이다.

## 5. 핵심 실패 유형

### 질문에 직접 답하지 못함

- `crosscheck-samsung-hbm5`
- `conversation-disclosure-followup`

사건 반복 여부를 묻는 질문에 관련 자료를 나열했고, “핵심만 다시”라는
후속 질문에는 이전 답변을 그대로 반복했다.

### 초보자 친화성이 부족함

- 공시·리포트 답변에서 전문용어와 큰 수치를 쉬운 말로 바꾸지 못함
- 위험 요인 질문에서 근거 문장을 연결하지 못하고 나열함
- 가격 변동 원인 근거가 부족할 때 안전한 제한 답변은 했지만 사용자가
  기대한 설명을 제공하지 못함
- 일부 0.8점 답변도 pilot에서 고정된 0.9 threshold에는 미달함

## 6. 해석 경계

- Faithfulness 24/24는 이 Batch rubric과 제공 문맥 안에서의 judge
  결과이며, 사실 정확성 전체를 독립적으로 증명하지 않는다.
- judge와 generator가 모두 Gemini 계열이므로 계열 편향 가능성이 있다.
- Contextual Relevancy는 pilot 교정 실패로 참고값일 뿐이다.
- 이번 결과는 제품 개선 우선순위를 정하는 평가이며 배포 근거가 아니다.

## 7. 산출물

- sanitised summary:
  `data/evaluation/m5_e1_batch_summary.json`
- Batch adapter:
  `scripts/evaluate_m5_e1_gemini_batch.py`
- raw local-only artifact:
  `var/evaluation/m5_e1_pro_batch_20260729/`

commit, push, PR, deployment는 수행하지 않았다.

## 8. 다음 결정

현재 M5-E1 품질 gate는 통과하지 못했다. Gemini 생성 모델 비교는
`NOT_RUN`으로 유지한다.

다음 단계는 위 실패 유형을 범위로 한 보완 작업과 동일 frozen 질문의
회귀 평가다. Human Owner가 발표 목적의 탐색적 모델 비교를 별도로
승인하면 품질 gate와 구분해 실행해야 한다.
