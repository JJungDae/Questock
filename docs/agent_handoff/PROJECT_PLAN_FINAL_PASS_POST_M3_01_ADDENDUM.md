# PROJECT_PLAN_FINAL_PASS — POST-M3-01 ADDENDUM

> 기준일: 2026-07-25
> 적용 범위: M3-01 완료 이후 B6·B7·M3 Gate·B8·B9·M4 Gate·M5/P1
> 기준 SHA: `d937d625e26495a3ee8c5a5b2c327dfbd2512ea9`
> 우선 참조: `POST_M3_01_EXECUTION_FLOW_DECISION_2026-07-25.md`

## 1. Addendum 효력

본 Addendum은 기존 `PROJECT_PLAN_FINAL_PASS.md`를 삭제하거나 전면 대체하지 않는다.

다만 M3-01 이후 실행 순서·bundle 내부 checkpoint·M3-15 분리·검수 경계에
대해서는 본 Addendum이 기존의 더 일반적인 B6·B7 설명보다 우선한다.

## 2. 현재 Phase 상태

| 항목 | 상태 |
|---|---|
| M2 Gate | PASS |
| M3-00 | PASS / complete |
| M3-01 | PASS / complete |
| M3-01 코드 BLOCKER | CLOSED |
| M3-01 남은 작업 | B6-0 factual sync |
| M3-15 | direction locked / B6 plan pending |
| M3-12 | NOT_ACTIVATED |
| 다음 bundle | B6-REMAINDER |

## 3. 수정된 Step Registry

| Bundle | 선행 | 로컬 checkpoint | 핵심 출력 | 외부 판정 |
|---|---|---|---|---|
| B6-REMAINDER | M3-01 PASS | B6-0, A, B, C1, C2 | Streamlit scaffold, beginner answer, glossary, cards, source detail | B6 implementation review |
| B7 | B6 PASS | A, B1, B2, 필요 시 C | session, validators, conflicting/multi-source, M3-15B | B7 review + M3 Gate |
| B8 | M3 Gate PASS | M4-01~03 | failure regression, golden 90%, observability | B8 review |
| B9 | B8 PASS | A, B | CI, Docker, deploy, demo, docs, traceability | B9 review + M4 Gate |
| M5-01 | M4 Gate PASS + activation | 필요 시 Stretch M2-09 후 1~2세션 | price-move background | M5 review |
| P1 | M5-01 완료/생략 + 시간 gate | 독립 Task | RAG 품질 또는 User 기능 | 별도 review |

## 4. B6 상세

### B6-0

- M3-01 Task Card 사실 동기화
- M3-01 `PASS / complete`
- `ChatResponse + PublicProcessSummary` freeze
- golden/Critical inventory
- Streamlit dependency audit

### B6-A — M3-15A

- Streamlit shell
- transport boundary
- selector·질문 입력
- 기본 답변/source frame
- 분석 과정 expander
- AppTest·startup smoke

### B6-B — M3-02·03·14

- 초보자형 순서
- 사실·해석·추론 구분
- 리포트의 계획·조건·위험·예정 이벤트 criterion

### B6-C1 — M3-05

- approved glossary corpus
- financial-term recorded path
- glossary locator
- unsupported term fallback

### B6-C2 — M3-04·07

- answer cards
- source-specific safe detail
- provider/no-data/timeout/stale wording
- B6 UI integration

### B6 완료 상태

```text
M3-15A complete
M3-04 complete
M3-05 complete
M3-07 complete
M3-15B pending B7
M3 Gate not claimed
```

## 5. B7 상세

### B7-A — M3-06

- 익명 현재 세션
- 종목·기간·intent context
- 명시적 새 종목 우선
- reset
- 오래된 종목 강제 적용 방지

### B7-B1 — M3-08·09

- 직접 투자 조언 차단
- 목표가·확정 예측 차단
- 숫자·날짜·단위·회사 귀속
- 실패 문장 제거

### B7-B2 — M3-10·11·M3-15B

- 상충 Evidence 병렬 표시
- 제한적 multi-source 연결
- 근거 단절 시 인과 중단
- session/reset UI 연결
- final M3-15 closure

### B7-C — 조건부

다음 중 하나면 추가한다.

- golden set 24개 미만
- Critical subset 미식별
- runner 없음
- taxonomy 집계 불가
- M3 Gate 점수 재현 불가

## 6. M3 Gate

B7 구현 검수와 같은 요청에서 수행할 수 있으나 별도 판정을 남긴다.

필수:

- CORE08
- A01~A04
- A05-M·A06-M
- A07-M
- A08-M
- A10
- SAFE01
- UI01
- PublicProcessSummary UI smoke
- full golden 80% 이상
- Critical 100%
- secret·prompt·raw exception 노출 0
- M3-12 NOT_ACTIVATED

## 7. B8와 B9

### B8

- M4-01 provider failure/fallback
- M4-02 full golden 90%·Critical 100%
- M4-03 structured observability

### B9-A

- M4-04 CI
- M4-05 clean local Docker/container
- API·UI health/startup smoke

### B9-B

- M4-05 remote deployment
- M4-06 demo
- M4-07 docs/presentation
- M4-08 P0 traceability
- M4 Gate

## 8. M4 이후

```text
M4 Gate PASS
→ A15-M activation check
→ temporal filter 없으면 Stretch M2-09
→ M5-01
→ 최종 버퍼와 3개 세션 조건 확인
→ P1
```

## 9. 계획·검수 횟수

| Bundle | 계획 검수 | 구현 검수 |
|---|---:|---:|
| B6 | 1 | 1 |
| B7 | 1 | 1 + M3 Gate |
| B8 | 1 | 1 |
| B9 | 1 | 1 + M4 Gate |

로컬 checkpoint는 외부 검수를 반복하지 않고 자체 검수·HANDOFF로 연결한다.

## 10. 범위 변경 trigger

다음은 Addendum 범위를 넘어선다.

- frozen public schema 변경
- M1/M2 변경
- 새 provider/live source
- DB/migration/persistence
- 승인되지 않은 dependency
- M3-12 선행
- 가격 기능
- Critical 실패 무시
- 투자 조언 정책 완화
