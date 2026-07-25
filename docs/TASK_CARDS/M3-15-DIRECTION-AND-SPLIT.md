# M3-15 DIRECTION AND SPLIT ADDENDUM

> canonical Task Card: `docs/TASK_CARDS/M3-15-process-visibility-ui.md`
> Pre-B6 code baseline: `d937d625e26495a3ee8c5a5b2c327dfbd2512ea9`
> Docs update/review base: `f5b3c646ec8696ac5c70d0d700e6fd729fd83bc4`
> M3-01 schema blob: `c10da0270e00105a4f375ba79a2aac5451730a4a`
> trace version: `m3-01-v1`

## 1. 상태

```text
M3-01 prerequisite:
PASS / complete

M3-15 planning base:
f5b3c646ec8696ac5c70d0d700e6fd729fd83bc4

M3-15 plan:
B6-REMAINDER initial plan review CONDITIONAL PASS
corrected plan closure review pending

M3-15 implementation:
BLOCKED pending B6 plan approval, Streamlit dependency approval, and preflight

Streamlit:
NOT_APPROVED until B6 plan review

M3-15 final completion:
split between B6 and B7
```

## 2. M3-15A — B6

소유:

- Streamlit entry point
- UI shell
- transport boundary
- supported-security selector shell
- question submit
- answer/source component interface
- collapsed process expander
- data-mode/live verification badge
- provider/retrieval/EvidenceDecision/LLMStatus 구분
- AppTest와 startup smoke

B6에서 다음과 함께 연결한다.

- M3-04 answer cards
- M3-07 source detail
- M3-05 glossary answer

## 3. M3-15B — B7

소유:

- M3-06 session/reset의 실제 연결
- M3-10·11 결과의 UI 표시
- final multi-turn UI smoke
- M3 Gate UI closure

## 4. B6 종료 상태

```text
M3-15A:
complete

M3-04:
complete

M3-07:
complete

M3-15B:
pending B7

M3-15 overall:
not complete
```

## 5. frozen contract

B6에서 다음을 변경하지 않는다.

- `ChatRequest`
- `ChatResponse`
- `PublicProcessSummary`
- nested public summary fields
- `trace_version="m3-01-v1"`
- `Evidence`
- `AnswerSections` field names

## 6. UI ownership

```text
M3-15A:
shell / transport / component interfaces / process panel

M3-04:
AnswerSections → answer card projection

M3-07:
Evidence → safe source detail / error / stale projection
```

## 7. dependency

Streamlit exact pin과 `uv.lock` 변경은 B6 통합 계획에서 별도 검수한다.
승인 전 설치·lock 변경·UI 구현을 시작하지 않는다.
