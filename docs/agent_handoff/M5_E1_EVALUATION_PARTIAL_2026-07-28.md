# M5-E1 EVALUATION PARTIAL — 2026-07-28

> 상태: `PARTIAL / JUDGE_QUOTA_STOP`
> 제품 generator: `gemini/gemini-3.5-flash`
> 평가 judge: `gemini-3.1-pro-preview`
> DeepEval: `4.1.4`
> google-genai: `2.14.0`
> 평가 대상 release: `373ea00d4e06526a98898e9c38f4d4a7871b1a8f`

## 1. 결론

M5-E1 평가 구현과 실제 실행을 시작했고, 다음 범위는 유효하게 완료됐다.

- Python 3.11 격리 평가 환경 설치
- DeepEval과 Gemini judge smoke PASS
- pilot 6건 전체 실행과 threshold 교정 완료
- held-out 24건의 Questock 답변을 case당 1회 생성해 고정
- 다중 턴 setup 답변 4건 고정
- 결정론적 hard gate `24/24 PASS`
- M5-D1 사건 묶기 precision `1.0`, recall `1.0`,
  false positive `0`

Gemini judge quota가 held-out 중간에 소진되어 범용 지표 전체 평가는
완료되지 않았다. 따라서 현재 상태는 `PASS`나 제품 품질 `FAIL`이 아니라
`PARTIAL / JUDGE_QUOTA_STOP`이다.

## 2. Judge 계약

### 모델 선택

- model-list에는 `gemini-2.5-pro`가 표시됐지만 실제 호출은
  신규 사용자에게 종료된 모델이라는 HTTP 404를 반환했다.
- `gemini-3.1-pro-preview`는 structured judge smoke를 통과해 고정했다.
- temperature: `0`
- max output tokens: `4096`
- DeepEval retry max attempts: `1`
- telemetry: opt-out
- Confident AI hosted upload: 사용하지 않음

### API 종료 원인

held-out 13번째 case의 일부 지표부터 `ClientError`가 발생했다.
실행 후 민감정보 없는 최소 진단 호출 1회로 다음을 확인했다.

```text
HTTP 429
quota exceeded
```

평가 오류를 제품 품질 0점으로 합산하지 않았다.

## 3. 제품 응답 고정 결과

- target response: `24`
- multi-turn setup response: `4`
- generation mode:
  - `llm`: `11`
  - `fixed_template`: `13`
- response status:
  - `complete`: `17`
  - `partial`: `5`
  - `no_evidence`: `2`

raw 답변·retrieval context·judge reason은 다음 Git ignored 로컬 경로에만 있다.

```text
var/evaluation/m5_e1_20260728/
```

Git에는 원문 답변이 없는 sanitised 결과만 남긴다.

```text
data/evaluation/m5_e1_summary.json
```

## 4. 결정론적 hard gate

| 항목 | 결과 |
|---|---:|
| held-out case | `24/24 PASS` |
| future information leakage | `0` |
| wrong company evidence | `0` |
| price/time/percent mismatch | `0` |
| direct investment advice | `0` |
| public claim citation coverage failure | `0` |
| invalid public citation URL structure | `0` |
| false independent lineage | `0` |
| M5-D1 grouping precision | `1.0` |
| M5-D1 grouping recall | `1.0` |
| M5-D1 false positive | `0` |

URL 검사는 HTTP 가용성이 아니라 공개 URL의 구조만 확인했다.

## 5. Pilot 교정

| 지표 | 사람 판정 일치 | threshold | 상태 |
|---|---:|---:|---|
| Answer Relevancy | `6/6` | `1.0` | `REQUIRED` |
| Contextual Relevancy | `6/6` | `1.0` | `REQUIRED` |
| Beginner Usefulness | `6/6` | `0.5` | `REQUIRED` |
| Faithfulness | `4/6` | `1.0` | `REPORT_ONLY` |

Faithfulness는 wrong-company와 unsupported-claim known-bad 두 건을
1.0으로 통과시켰다. 따라서 범용 Faithfulness를 release gate로 사용하지
않고, Questock hard gate를 유지한 결정이 타당했다.

Pilot 사용량:

- logical judge requests: `63`
- input tokens: `21,822`
- output tokens: `3,307`
- DeepEval reported cost: `$0.083328`

## 6. Held-out 부분 결과

Held-out 사용량:

- logical judge requests: `231`
- input tokens: `96,481`
- output tokens: `22,933`
- DeepEval reported cost: `$0.468158`

다음 수치는 evaluator error가 발생하기 전 성공한 일부 case만의 진단값이다.
24건 전체 결과나 최종 모델 점수로 인용하면 안 된다.

| 지표 | 채점 성공 | mean | 명시적 score fail | evaluator error |
|---|---:|---:|---:|---:|
| Answer Relevancy | `13/24` | `0.9538` | `3` | `11` |
| Contextual Relevancy | `12/24` | `0.7994` | `7` | `12` |
| Beginner Usefulness | `13/24` | `0.8308` | `3` | `11` |
| Faithfulness | `12/24` | `0.9583` | `1` | `12` |

Faithfulness는 `REPORT_ONLY`이며 위 mean은 안전성 근거로 사용할 수 없다.

## 7. quota 이전에 확인된 품질 이슈

### 주가 변동 원인

- SK하이닉스 2026-07-27 19:00 원인 질문:
  `no_evidence`; Answer Relevancy `0.667`,
  Contextual Relevancy `0.0`
- 현대차 2026-07-24 14:00 하락 원인:
  Answer Relevancy `0.833`, Contextual Relevancy `0.667`
- 삼성전자 2026-07-27 21:00 상승 배경:
  Answer Relevancy `0.9`, Contextual Relevancy `0.833`
- 변동 원인 4건 모두 Beginner Usefulness는 threshold를 통과

가격 수치 안전성은 통과했지만 원인 근거의 직접성과 질문 집중도가 약점이다.

### 일반 이슈·위험

- 삼성전자 호재 질문:
  Contextual Relevancy `0.875`, Beginner Usefulness `0.4`
- 삼성전자 위험 질문:
  Contextual Relevancy `0.818`, Beginner Usefulness `0.2`
- SK하이닉스 최근 이슈 질문:
  네 지표 모두 `1.0`

fallback과 다중 근거 답변에서 불필요한 문맥과 정보 구성 문제가 남아 있다.

## 8. 재개 계약

quota가 회복되면 다음 순서로만 재개한다.

1. 현재 frozen response hash와 pilot result hash 확인
2. 제품 답변과 setup 답변 재생성 금지
3. pilot threshold 변경 금지
4. evaluator error가 난 metric-case cell만 동일 judge로 실행
5. 기존 성공 cell과 합쳐 24건 전체 집계
6. required metric error `0` 확인
7. 전체 결과가 확정된 뒤에만 Pro 비교 준비 여부 결정

judge 모델을 바꾸려면 pilot부터 별도 evaluation run으로 다시 시작해야 한다.
서로 다른 judge 결과를 같은 aggregate에 혼합하지 않는다.

## 9. 현재 경계

- M5-E1 implementation: `PASS`
- hard gate: `PASS`
- pilot calibration: `PASS`
- held-out generic evaluation: `PARTIAL / JUDGE_QUOTA_STOP`
- overall M5-E1: `PARTIAL`
- Pro comparison: `BLOCKED`
- commit/push/PR/deploy: `NOT_RUN`
