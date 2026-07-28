# TASK CARD — M5-01-HR1 Hybrid Intent Router

> Planning date: `2026-07-28`
> Status: `INDEPENDENT REVIEW PASS / DEPLOYMENT AUTHORIZED`
> Human Owner approval: `APPROVED`
> Git and deployment: `NOT_AUTHORIZED`

## 1. Purpose

Improve ordinary-language intent classification without replacing the proven
deterministic router or expanding the supported product scope.

The router is hybrid:

1. deterministic rules produce the first result
2. high-confidence, non-conflicting results return without an LLM call
3. only ambiguous or conflicting supported-stock questions may call the
   approved Gemini model
4. invalid output, timeout, quota, provider failure, or unsupported intent
   returns to the deterministic result

## 2. In scope

- ambiguity detection around price, price move, risk, recent issue, disclosure,
  report, multi-source summary, and financial-term questions
- a small structured classifier result with supported intent only
- existing security and selected-date resolution remain deterministic
- bounded classifier timeout and zero retry
- sanitized diagnostics for route, fallback, and call count
- deterministic fake-client tests and a minimal approved live smoke

## 3. Out of scope

- investment recommendation or prediction
- direct company comparison
- new data providers or dependencies
- replacing evidence policy, retrieval, answer generation, or citation checks
- using the classifier to create facts or answer content
- more than one classifier call per user request
- commit, push, PR, merge, or deployment

## 4. Decision contract

The classifier may return only an intent already present in the QueryPlanner
source/evidence matrix. It must not create or change:

- security
- selected checkpoint
- date range
- required source/evidence lists independently of the canonical planner
- prohibited-advice or out-of-scope safety decisions

Safety and deterministic precedence:

- prohibited-advice and out-of-scope results never call the classifier
- explicit unambiguous intent cues never call the classifier
- an LLM result is accepted only when it is schema-valid, supported, and
  compatible with the deterministic security/date contract
- every failure returns the deterministic plan

## 5. Initial ambiguity targets

- a prior stock context followed by a conceptual risk question containing
  `주가`
- colloquial company-state questions with price words but no explicit request
  for a quote
- short `왜` questions where price-move and risk cues conflict
- ordinary issue/positive-factor wording with multiple supported intent cues

## 6. Configuration

Use the existing approved Gemini stack and credentials.

Required defaults:

- hybrid router disabled unless explicitly enabled
- classifier model defaults to the configured LLM model
- timeout must be lower than the answer-generation timeout
- retry `0`
- maximum one classifier call per request
- CI and deterministic tests keep the classifier disabled or use a fake client

## 7. Acceptance

- unambiguous existing golden cases preserve their intent and use zero
  classifier calls
- ambiguous target cases resolve to the expected supported intent
- malformed, unsafe, unsupported, timed-out, quota-limited, and provider-failed
  classifier results preserve the deterministic plan
- security, checkpoint, temporal filtering, evidence policy, citation safety,
  and answer-generation contracts remain unchanged
- focused tests, full regression, Ruff, and diff check pass
- a minimal sanitized live classification smoke passes without exposing prompt,
  credentials, provider payload, or user/session data

## 8. Execution record

- implementation branch: `fix/m5-answer-quality-closure`
- implementation base:
  `9bf9b1a6992e172417f68c734f0dcd460a6af5d2`
- implementation:
  `INDEPENDENT REVIEW PASS / DEPLOYMENT AUTHORIZED`
- implementation details:
  - deterministic rules remain the first route
  - only ambiguous or conflicting supported-stock questions may call the
    classifier
  - prohibited-advice, out-of-scope, clarification, and explicit
    unambiguous-intent questions use zero classifier calls
  - accepted classifier output is restricted to the existing eight supported
    intent values
  - security, selected checkpoint, basis date, and temporal boundary remain
    deterministic
  - timeout, quota, authentication, provider, blocked-content, malformed JSON,
    extra-key, and unsupported-output failures return to the deterministic plan
  - classifier timeout is `3` seconds with retry `0`
  - maximum classifier calls per request: `1`
  - maximum total LLM calls per ambiguous generated answer:
    `2` (`1` classifier + `1` answer composer)
  - runtime default and CI default:
    `QUESTOCK_HYBRID_ROUTER_ENABLED=false`
  - GCE runtime contract:
    `QUESTOCK_HYBRID_ROUTER_ENABLED=true`
- validation:
  - focused hybrid-router boundary:
    `115 passed, 1 warning`
  - affected unit, integration, and UI regression:
    `435 passed, 1 warning`
  - deployment-contract regression:
    `61 passed, 1 warning`
  - full regression:
    `2148 passed, 2 warnings`
  - Ruff over `app`, `tests`, `scripts`, and `streamlit_app.py`:
    `PASS`
  - M3 Gate:
    `34/34`; Critical `17/17`; public exposure `0`
  - tracked and new-file secret scans:
    `PASS`, findings `[]`
  - diff check:
    `PASS`
- bounded live classifier smoke:
  - actual provider calls: `2`
  - answer-generation calls: `0`
  - model: `gemini/gemini-3.5-flash`
  - recent-risk ambiguity:
    `risk_factors -> risk_factors`, `PASS`
  - price-situation ambiguity:
    `multi_source_summary -> multi_source_summary`, `PASS`
  - strict structured parse:
    `2/2 PASS`
  - prompt, credential, provider payload, question text, and session data were
    not printed
- independent implementation review:
  `PASS WITH REQUIRED FIX / FIX CLOSED`
- review finding and closure:
  - a classifier-reclassified direct-price response could return before
    emitting its LLM call observation
  - price-only responses now emit a sanitized market-snapshot observation
  - `intent_classifier_status` distinguishes accepted, timeout, rate-limited,
    authentication, provider, blocked-content, and invalid-response outcomes
  - observation contracts reject inconsistent route/status combinations
- post-review validation:
  - affected unit, integration, and UI regression:
    `164 passed, 1 warning`
  - full regression:
    `2158 passed, 2 warnings`
  - M3 Gate:
    `34/34`; Critical `17/17`; public exposure `0`
  - Ruff, compile, tracked/new-file secret scans, and diff check:
    `PASS`
- deployment authorization:
  `APPROVED by Human Owner on 2026-07-28`
- commit, push, PR, merge, deployment:
  `IN PROGRESS`
