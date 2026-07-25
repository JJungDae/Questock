# TASK CARD - M3-15 Process-Visible Streamlit UI

## 1. Status and Approval

- Task bundle: `B6`
- Step: `M3-15 Actual UI Integration and Process Visibility`
- Priority: `P0 presentation and usability`
- Planning date: `2026-07-24`
- Planning base: `cc9ff7e5951330ae34973d48abf0f065ac515576`
- M3-01 prerequisite:
  `PASS / complete`
- Required API contract:
  `ChatResponse + PublicProcessSummary`
- M3-07 source-detail contract:
  `must be available or scaffolded before final M3-15 closure`
- M3-15 planning:
  `APPROVED through B6-REMAINDER plan`
- M3-15 implementation:
  `M3-15A complete and pushed; M3-15B implemented and locally verified in B7`
- Streamlit dependency:
  `streamlit==1.60.0 AUTHORIZED in Gate 1`
- Commit, push, PR, merge, deploy:
  `B6 M3-15A and B7 M3-15B implementation main pushes complete; further PR/merge/deploy NOT_APPROVED`
- M3-15 final closure:
  `implementation complete; independent B7 closure review pending`

This Task Card implements the mentoring direction that the existing M1/M2
capabilities must be visible in the demonstration instead of appearing as an
opaque question-and-answer box.

It does not expose LLM chain-of-thought. It visualizes only sanitized,
observable application stages returned through `PublicProcessSummary`.

---

## 2. Goal

Build the actual user UI around one stable backend contract:

```text
ChatResponse
+ PublicProcessSummary
+ source details
```

The default screen remains beginner-friendly:

```text
question
→ concise answer
→ risks/uncertainty
→ supporting sources
```

A collapsed `분석 과정 보기` panel makes the technical pipeline visible for
mentoring, evaluation, and debugging:

```text
종목 식별
→ 질문 의도·자료 선택
→ 자료 상태
→ 종목·기간 필터
→ 최신성
→ 관련도 검색
→ 근거 충분성
→ 중복 제거·문맥 제한
→ 인용 검증
→ LLM 또는 고정 응답
```

The UI does not recreate backend decisions.

---

## 3. Prerequisites

Before implementation:

- M3-01 is independently `PASS`
- `/api/chat` returns stable `ChatResponse`
- `PublicProcessSummary` is fixed
- all required summary cases pass backend tests
- source-detail fields are fixed
- API and UI are not modified simultaneously
- repository UI structure and dependency state are inspected
- Streamlit version and lock change receive separate approval

If the API schema is still changing, do not start UI implementation.

---

## 4. UI Layout

## 4.1 Sidebar

- supported security selector:
  - 삼성전자
  - SK하이닉스
  - 현대자동차
- current session ID
- reset
- data-mode badge:
  - recorded
  - live
  - mixed
  - unconfigured
- live verification badge

The selector assists users but does not override an explicitly named different
security without backend clarification.

## 4.2 Main question area

- question input
- submit
- disabled/loading state
- one non-streaming result
- sanitized validation message

No raw request payload or exception is shown.

## 4.3 Answer area

- status
- security and basis date
- summary
- facts
- interpretation
- inference
- positive factors
- risk factors
- uncertainty
- warnings
- missing sources

Empty unsupported sections are hidden rather than filled with model guesses.

## 4.4 Source detail

For each final cited Evidence:

- title
- source type
- published date
- snippet
- locator summary:
  - news coordinates
  - disclosure receipt
  - report page/section
  - glossary section
- original link only when an approved HTTP(S) URL exists
- no local path
- no full raw locator
- no permission note

## 4.5 `분석 과정 보기` expander

The expander is collapsed by default.

### Stage 1 - 종목 식별

Display:

- resolution status
- canonical security ID

Do not display resolver private candidates or alias index.

### Stage 2 - 질문 계획

Display:

- intent
- required sources
- requested date range

Do not echo the complete raw question.

### Stage 3 - 자료 상태

One row per required source:

- source type
- ProviderStatus
- document count
- cache indicator

### Stage 4 - 필터·최신성

Display counts:

- normalized
- hard-filter retained
- freshness retained

Display stable freshness warning codes in beginner-friendly wording.

### Stage 5 - 검색

- RetrievalStatus
- selected Evidence count
- low-relevance indicator

### Stage 6 - 근거 충분성

- EvidenceDecisionStatus
- satisfied sources
- missing sources
- no-data sources
- failed sources

### Stage 7 - 문맥 예산

- input count
- unique count
- selected count
- duplicate drops
- source-cap drops
- count-cap drops
- context drops
- estimated tokens and characters

### Stage 8 - 인용

- claim count
- citation count
- rejection count

Do not show rejected claim text or internal ID detail.

### Stage 9 - 생성 경로

- generation mode
- separate LLMStatus
- model only when called
- live verified badge

The UI must distinguish:

```text
Evidence/provider result
!= retrieval result
!= EvidenceDecision
!= LLMStatus
```

---

## 5. Safety and Non-Goals

Never display:

- chain-of-thought
- hidden reasoning
- prompt
- format instructions
- raw user question duplication in diagnostics
- full source documents
- raw provider payload
- raw exception
- credential
- local path
- permission note
- unrestricted locator
- LangChain/LiteLLM/Gemini object

Do not:

- recompute filter or decision status
- infer why a model “thought” something
- claim live data when recorded or unconfigured
- add price prediction
- add M3-12/M5-01
- add login or persistence
- add streaming
- redesign backend schemas from UI code

---

## 6. Demo Scenarios

The UI must support at least these deterministic scenarios.

### D-01 Normal complete

Show:

- one target security
- source success
- wrong-company removal
- fresh relevant Evidence
- complete decision
- citation
- generation mode

### D-02 Wrong-company candidate removed

The process panel must make the before/after count visible without exposing the
other company's private raw content.

### D-03 Stale candidate removed

Show freshness count reduction and stale warning.

### D-04 Low relevance

Show:

- RetrievalStatus `low_relevance`
- no-evidence decision
- fixed response
- zero LLM calls

### D-05 Provider failure

Show provider failure separately from no-data and LLM failure.

### D-06 Context budget

Show dedupe/source/context drops and final citation count.

### D-07 LLM failure fallback

Show:

- valid Evidence remains
- LLMStatus failure
- generation mode fixed template
- provider and EvidenceDecision unchanged

### D-08 Unconfigured runtime

Show:

- `data_mode=unconfigured`
- no hidden test fixture
- typed provider-unavailable status
- stable safe response

---

## 7. Expected Files

Exact paths are confirmed at implementation-base preflight.

Expected new or modified areas:

- one Streamlit entry point under `app/ui/`
- UI component/render helpers
- application-owned demo configuration only when separately approved
- UI unit tests for pure rendering projections
- Streamlit/AppTest or equivalent UI smoke
- M3-15 Task Card

Potential dependency changes:

- exact Streamlit pin
- existing `uv.lock`

Do not modify M1/M2 modules.

If a recorded demo corpus is approved, it must live under `data/demo/**`, not
`tests/fixtures/**`.

---

## 8. Test Plan

### Contract consumption

- UI consumes ChatResponse without field inference
- UI consumes PublicProcessSummary without recomputing counts
- unknown schema version fails safely
- missing optional sections hidden

### Process panel

- fixed stage order
- all five major status families represented
- recorded/live/mixed/unconfigured labels
- provider, retrieval, EvidenceDecision, LLMStatus visually distinct
- counts and warning wording exact
- no chain-of-thought wording

### Source details

- safe URL only
- no local path
- correct disclosure receipt/page/section
- missing URL handled
- no raw locator dump

### Safety

- sentinel secret absent
- raw exception absent
- prompt absent
- full document absent
- local path absent
- malicious markdown/HTML escaped
- user text cannot inject process state

### UI smoke

- app starts
- selector works
- question submit
- one stable result
- expander renders
- reset works
- complete/failure/unconfigured fixtures
- no infinite external wait

### Regression

- M3-01 API tests unchanged
- M2 full phase slice unchanged
- full suite
- secret scan
- compile
- clean Streamlit start

---

## 9. Completion Criteria

- [x] M3-01 PASS and schema frozen
- [x] exact Streamlit dependency and lock approved
- [x] support selector
- [x] question input
- [x] session display and reset
- [x] answer cards
- [x] source details
- [x] collapsed process expander
- [x] every process stage rendered
- [x] data-mode and live-verification badges
- [x] provider/retrieval/decision/LLM statuses separated
- [x] no chain-of-thought/prompt/secret/path/raw exception
- [x] representative scenarios pass
- [x] UI smoke passes
- [x] M2/M3 regression passes
- [ ] demo screenshots and presentation flow recorded
- [x] B7 implementation commit/main push separately approved and complete

---

## 10. Stop Conditions

Stop if:

- M3-01 schema changes are required
- UI needs raw internal objects
- process counts are unavailable from PublicProcessSummary
- M1/M2 code changes appear necessary
- test fixtures must be imported by app code
- Streamlit requires an unapproved dependency shift
- the UI would expose prompt, reasoning, secrets, or paths
- M5-01 or price data is requested in this Task
- API and UI must be redesigned simultaneously

---

## 11. Result Log

- Implementation base: `cc9ff7e5951330ae34973d48abf0f065ac515576`
- M3-01 prerequisite: `PASS / complete`
- Final approved B6 plan:
  `cc9ff7e5951330ae34973d48abf0f065ac515576`
- Frozen API schema blob:
  `c10da0270e00105a4f375ba79a2aac5451730a4a`
- Frozen Evidence model blob:
  `54397337c3b3e152de247e585494ef4a6c92ef1a`
- Frozen AnswerSections model blob:
  `660563e4859c6301f709c1e2574828eb143781e0`
- Frozen trace version: `m3-01-v1`
- Gate 0 focused regression: `89 passed`
- Gate 0 full regression: `1573 passed, 2 warnings`
- Golden/Critical inventory:
  `24-question draft only; executable assets absent; B7-C REQUIRED`
- Streamlit dependency review:
  `PASS - streamlit==1.60.0 exact pin; existing package movement none`
- Clean Python 3.14 sync: `PASS`
- Streamlit import: `PASS - 1.60.0`
- AppTest import: `PASS - streamlit-apptest-ok`
- Gate 1 focused regression: `89 passed`
- Gate 1 full regression: `1573 passed, 2 warnings`
- UI implementation:
  `M3-15A complete - shell, answer cards, source details, and process panel`
- B6-A targeted: `57 passed`
- B6-A full regression: `1615 passed, 2 warnings`
- B6-C2 targeted: `54 passed, 1 warning`
- B6 focused integration: `358 passed, 2 warnings`
- Final full regression: `1641 passed, 2 warnings`
- Process panel: `PASS - nine public-summary stages in fixed order`
- UI smoke:
  `PASS - complete/glossary/failure/fallback AppTest and headless health HTTP 200`
- Local API smoke:
  `PASS - glossary status complete, 4 Evidence, recorded mode, retrieval ok`
- Pixel screenshot:
  `NOT_VERIFIED - Chrome headless captured the Streamlit shell before websocket content rendering`
- M2/M3 regression: `PASS within full suite`
- Recorded demo corpus: `NOT_APPROVED`
- Live source: `NOT_VERIFIED`
- B6 completion SHA/main push:
  `60e6203b265a967a8b6ba45da2ba3128e1e1bcfe / complete`
- B7 implementation SHA/main push:
  `833336a002b1e02070b35cd4afe9aff279752d61 / complete`
- Further PR/merge/deploy: `NOT_RUN / NOT_APPROVED`
- M3-15A: `COMPLETE`
- M3-15B: `IMPLEMENTED / local verification PASS / independent B7 closure pending`
