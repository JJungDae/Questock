# MENTORING_SCOPE_DECISION_2026-07-24.md

## 1. Decision Status

- Decision date: `2026-07-24`
- Decision owner: `Human Owner`
- Input: mentoring feedback after M2 Gate completion and M3-00 implementation
- Status: `APPROVED DIRECTION - implementation still follows individual Task approval`
- Scope affected:
  - M3-01 public response contract
  - M3-15 UI
  - M3-12 activation
  - M4 demo preparation
  - M5-01 priority
  - later P1 entry

This document records product and presentation priorities. It does not itself
authorize code, dependency, Git, live API, or deployment work.

---

## 2. Mentoring Feedback

### Feedback A - Existing implementation must be visible

The project has substantial M1/M2 logic and tests. A UI that shows only a
question and final answer hides the strongest technical work.

The final UI should therefore expose a safe, understandable view of:

- security resolution
- intent and source routing
- provider/source status
- hard filtering
- freshness
- retrieval
- Evidence sufficiency
- context budget
- citation validation
- LLM or fixed fallback

This must be observable stage data, not LLM chain-of-thought.

### Feedback B - Extension time is limited

M3 and M4 completion remain higher priority than adding many P1 features.

The first optional extension after a stable MVP should be the domestic
price-move background feature when its data/time prerequisites are ready.

---

## 3. Approved Direction

## 3.1 M3-01

M3-01 adds a stable `PublicProcessSummary` to the API response.

It does not implement the UI.

## 3.2 M3-15

M3-15 consumes the stable API response and adds a collapsed
`분석 과정 보기` panel.

The default user experience remains concise.

## 3.3 M3-12

```text
M3-12: NOT_ACTIVATED in the current M3 implementation
```

No price-move model, response field, UI, or provider work is added during M3.

## 3.4 M5-01

After M4 Gate PASS, M5-01 is the mentor-selected first extension candidate.

Activation order:

```text
M4 Gate PASS
→ A15-M activation check
→ Stretch M2-09 when market-session filtering is still absent
→ M5-01
```

## 3.5 P1

P1 work begins only after:

- M5-01 is completed or explicitly skipped by the Human Owner
- Critical set remains 100%
- full golden set remains at least 90%
- deployment smoke passes
- anonymous public MVP remains stable
- at least three full implementation sessions remain after reserving one final
  regression/documentation/presentation buffer

When that time is unavailable, use the remaining work for:

- demo stability
- regression
- documentation
- presentation materials
- video recording
- defect correction

---

## 4. M5-01 Activation Requirements

- M1-09 MarketSnapshot implementation and status reviewed
- price, previous close, change, change percent, observed_at
- timezone and market status
- rise, fall, no-data, timeout fixtures
- news/disclosure published_at available
- market-session temporal filter available
- Critical set 100%
- full golden set 90% or higher
- deployment smoke PASS
- at least one post-feature regression/presentation session remains

When the temporal filter is missing, implement Stretch M2-09 first.

---

## 5. M5-01 Output Boundary

Allowed:

- actual observed price direction
- basis and observed time
- preceding documents
- intraday documents
- subsequent background
- domestic-source coverage warning
- uncertainty
- “cause candidate” wording

Forbidden:

- treating subsequent news as a preceding cause
- claiming one definitive cause
- future price prediction
- buy/sell/hold recommendation
- target price
- guaranteed return
- unsupported overseas/macro explanation

---

## 6. Document Updates

- `M3-01-answer-schema-chat-service-final-revised.md`
  - PublicProcessSummary
  - explicit unconfigured source gateway
  - two checkpoints
- `M3-15-process-visibility-ui.md`
  - process expander and demo scenarios
- `PROJECT_PLAN_FINAL_PASS.md`
  - M3-01/M3-15 contract
  - M3-12 not activated
  - M5-01 first extension priority
  - UI traceability
- `AGENT_WORKFLOW.md`
  - API schema before UI
  - M3-12 ownership moved to M5-01
  - post-M4 extension order
- `LLM_STACK_DECISION.md`
  - no mentoring-driven architecture change required

---

## 7. Non-Changes

This decision does not change:

- supported securities
- M1/M2 financial contracts
- selected LangChain/LiteLLM architecture
- Gemini model choice
- permission gate
- direct-investment-advice block
- M4 quality/deployment gates
- Git approval boundaries
