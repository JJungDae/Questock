# FSC-4 — Beginner Grounded Chat Stabilization

> Status: `PASS / DEPLOYED / COMPLETE`
>
> Baseline: `main` at `8c861a7664de001442b892a4f8d811d5d2655a14`
>
> Working branch: `fix/fsc4-beginner-grounded-chat`
>
> Human Owner direction: restore the product goal before entering M5. Questock
> must answer ordinary Korean questions about the three supported securities
> with useful evidence-grounded explanations, not merely copy source snippets.

## 1. Purpose

The completed FSC release proved snapshot integrity, attribution, citation
safety, request protection, deployment, and a bounded Gemini path. It did not
prove that answers were useful to a beginner. The current query planner accepts
only a narrow lexical taxonomy and the generation contract treats Gemini as an
extractive selector of one to three snippets.

FSC-4 changes that product contract while retaining the safety and release
boundaries that remain valid.

Target flow:

```text
ordinary Korean stock question
-> supported-security and safety boundary
-> question focus and source needs
-> relevant recorded evidence
-> question-adaptive grounded explanation
-> compact source references
-> chat-style UI
```

## 2. Scope

### 2.1 Included

- Samsung Electronics, SK hynix, and Hyundai Motor
- everyday Korean phrasings for:
  - current situation and general analysis
  - recent issues
  - positive factors and catalysts
  - risks and negative factors
  - financial performance
  - business, products, and technology
  - outlook
  - dividends and shareholder return
  - disclosures
  - research-report views and valuation
  - balanced strengths and weaknesses
  - financial terms
  - follow-up questions
- question-adaptive answer structure and length
- source-aware grounding and attribution
- deterministic fallback that remains useful
- compact source presentation
- bottom chat input and cleared submitted text
- product-quality acceptance in addition to existing regression gates

### 2.2 Excluded

- prices, returns, charts, and price-move reasons reserved for M5-01
- additional securities
- new live-source or database infrastructure
- authentication or durable conversation history
- vector or dense retrieval
- transmission of research-report text or summaries to an external LLM
- broad reopening of already approved source-rights decisions

## 3. Decision rule when existing contracts conflict

Minimal change is preferred only when it resolves the root cause and passes the
product-quality acceptance defined here.

```text
identify the root cause
-> test whether a minimal change satisfies the product contract
-> use the minimal change when it does
-> otherwise revise the blocking upstream contract
-> synchronize dependent code, tests, runtime configuration, and documents
```

The following are not acceptable fixes:

- adding exceptions only for demonstrated questions
- adding a few keywords while keeping unknown supported-company questions out
  of scope
- keeping the extractive contract and changing only prompt wording
- forcing a fixed number of answer items or source documents
- using weakly related news to satisfy a source-count requirement
- making a one-line answer appear longer by splitting it into UI cards

### 3.1 Invariants to preserve

- fixed three-security scope and recorded snapshot basis
- M5 price-data boundary
- no direct investment action or guaranteed return
- no unsupported number, wrong-company attribution, or invented link
- `external_llm_processing_allowed=false` for research reports
- bounded session memory and non-evidence conversation context
- request protection and cause-specific fallback
- exact-SHA release, rollback, and credential contracts

### 3.2 Contracts that may be revised

- intent taxonomy and literal substring matching
- intent-to-source matrix
- lexical relevance threshold and context selection
- one-document/one-Evidence disclosure normalization
- internal news titles and short summaries
- exact-copy generation and one-to-three-claim limit
- output-token and request-deadline settings
- fixed fallback composition
- verbose public source cards
- the assumption that the existing 15-case fixture proves answer quality

## 4. Trust and attribution boundary

The model input has four explicitly separated zones:

1. system rules
2. current user question
3. prior conversation context
4. external evidence

External evidence is untrusted third-party data, never a user statement or an
instruction. Instructions contained in evidence are ignored. A person,
investor, company, analyst, position, holding, or preference mentioned in
evidence must never be connected to the current user.

Unless explicitly provided in the current conversation, the answer must not
infer:

- ownership, purchase price, quantity, profit or loss
- investment horizon, risk appetite, portfolio, assets, or objectives
- any personal or financial identity

Conversation context is used only to resolve follow-up intent and security. It
is not Evidence. Even explicitly stated user context must not be converted into
an evidence claim or direct investment instruction.

Attribution must distinguish:

- filing facts: `공시에 따르면`
- reported events: `해당 뉴스는 ...라고 보도했습니다`
- analyst views: `증권사 리포트는 ...라고 전망했습니다`
- bounded synthesis: `현재 근거를 종합하면 ...로 볼 수 있습니다`
- uncertainty: `현재 자료만으로는 확인하기 어렵습니다`

## 5. Question planning contract

Security, prohibited-advice, price-data, and unsupported-scope checks remain
deterministic. Literal substring matches must use phrase/token boundaries so
that text such as `회사야` is not interpreted as `사야`.

Once one of the three securities is resolved, a non-price, non-advice question
must not become `out_of_scope` solely because its wording is unfamiliar.
Existing public intents remain compatible, while an internal answer focus
drives retrieval and composition.

Supported focuses:

- `general`
- `recent_events`
- `positive`
- `risk`
- `performance`
- `business`
- `technology`
- `outlook`
- `shareholder_return`
- `disclosure`
- `research_view`
- `balanced`
- `term`

Unknown but valid supported-company questions use `general` retrieval. If the
snapshot genuinely lacks the requested fact, the service returns a scoped
partial answer or a concrete limitation instead of a lexical no-evidence
response.

## 6. Evidence and retrieval contract

### 6.1 News

- restore the selected source title already present in the Git-ignored local
  candidate material
- keep the verified URL and publication time
- enrich only the existing 15 Questock-authored summaries
- do not ingest article bodies or raw API responses into runtime or Git
- select only news relevant to the question
- do not require a minimum number of news articles
- deduplicate articles describing the same event

### 6.2 Disclosures

Expose verified disclosure facts as retrieval Evidence units keyed by
`fact_id`, retaining receipt, section, period, unit, and page locators. Public
source display groups facts back to one DART document.

### 6.3 Research reports

Research-report section summaries remain internal and fixed-only. They are not
transmitted to Gemini. A mixed composer may merge validated fixed report facts
with Gemini output generated only from externally eligible evidence.

### 6.4 Selection

- expand everyday focus terms into evidence-domain terms
- use strict security, time, and source filters before relevance ranking
- permit source-diverse representative selection for a broad supported-company
  question even when literal overlap is low
- do not fill a numeric quota with irrelevant evidence
- use all explicitly requested source types when available; otherwise return
  partial with missing-source disclosure

## 7. Answer composition contract

Gemini may paraphrase, explain, and combine eligible evidence. It must return
structured answer units with Evidence IDs. It must not add unsupported facts,
numbers, companies, dates, links, causal certainty, or user attributes.

Gemini receives short request-local aliases such as `E1` instead of internal
hashed Evidence IDs. Aliases are expanded back to canonical IDs before any
validation. Provider-side JSON-schema-constrained decoding is not used for
Gemini 3.5 Flash because live FSC-4 probes reproduced nondeterministic repeated
quote output until the token limit. The model receives a concise JSON contract;
the existing Pydantic parser and deterministic project validators remain the
acceptance boundary.

Runtime generation contract:

- `gemini/gemini-3.5-flash`
- `LLM_THINKING_LEVEL=minimal`
- `LLM_MAX_OUTPUT_TOKENS=4096`
- `LLM_TIMEOUT_SECONDS=15`
- provider retry `0`
- project-side parse, citation, number, company, URL, advice, and user-property
  validation

The answer has one direct summary followed only by sections useful for the
question. Empty or irrelevant sections are omitted.

### 7.1 Type-specific sufficiency

| Type | Sufficiency rule |
|---|---|
| financial term | direct definition; example or caution only when useful |
| single fact | direct fact, period/basis, and source |
| recent issue | only relevant distinct events; one article is valid when one is relevant |
| positive/risk | all supported factors that materially answer the question; no fixed count |
| performance | relevant values, period/unit, and beginner-readable meaning |
| outlook | attribute the forecaster and distinguish fact, view, and uncertainty |
| general situation | select the material dimensions supported by the snapshot; do not force every section |
| filing/report | prioritize the requested source and use other sources only when helpful |
| follow-up | answer the new focus without repeating the entire prior answer |
| price-required | state the M5 boundary and offer supported alternatives |
| prohibited advice | brief restriction plus a safe analytical alternative |
| fallback | cause-specific notice plus the useful validated facts available |

Length and item count are diagnostics, not universal pass gates. Quality is
judged by directness, relevance, sufficiency, grounding, attribution,
beginner-readable clarity, and honest limitation.

## 8. Validation contract

Deterministic validation retains:

- valid cited Evidence IDs
- security and source scope
- all public numeric tokens grounded in cited Evidence
- no invented public URL
- no direct investment action or guaranteed outcome
- no user-property inference
- no cross-boundary use of conversation as Evidence
- explicit attribution for analyst or news views

Unsupported detail claims are removed without discarding a supported summary.
If the summary or remaining answer contract is invalid, the request uses the
deterministic fallback rather than publishing an unsafe draft. FSC-4 does not
add an automatic provider retry.

## 9. UI contract

- use a bottom chat input
- submitted text clears immediately
- show user and assistant messages in normal conversation order
- keep the latest response visible
- retain the bounded four-exchange transcript
- show the direct answer before technical status
- move process details behind the existing expander
- show sources as one compact line per underlying source:
  `자료 유형 · 실제 제목 · 원문`
- group multiple facts/sections from one disclosure or report
- hide snippet, provider, manifest ID, and internal document ID from the
  default answer view

## 10. Acceptance

The original 15 cases remain regression coverage. A new beginner-QA fixture
contains:

- 90 questions: 3 securities x 10 focuses x 3 everyday phrasings
- 15 follow-up questions
- 15 advice, price-data, unsupported, and attribution-boundary questions

### 10.1 Deterministic gates

- supported non-price everyday wording is not rejected only for lexical form
- wrong-company facts, unsupported numbers, invented links, and direct advice:
  zero
- inferred user holdings, preferences, losses, or goals: zero
- evidence text treated as user speech or instruction: zero
- citation IDs and numeric support valid
- requested source types used when available
- source scarcity represented as partial/limitation, not padded output
- bottom input, clearing, transcript order, and compact sources pass

### 10.2 Type-specific quality gates

- terms: accuracy and concision
- facts: directness and basis
- recent issues: event relevance and deduplication
- performance: value/period/unit accuracy and meaning
- positive/risk: fact-versus-assessment distinction
- outlook: speaker attribution and uncertainty
- general: balanced material coverage without forced sections
- follow-up: continuity without unnecessary repetition

No universal minimum answer-item count, article count, or answer length is a
release gate.

## 11. Live-call budget

The Human Owner permits a hard ceiling below 10,000 Gemini test calls. This is
an authorization ceiling, not a target.

- deterministic and mock work: zero live calls
- first live beginner-QA pass: approximately one call per eligible case
- no automatic correction call in the FSC-4 runtime
- initial operational target: at most 500 total calls including focused reruns
- diagnose before expanding beyond 500
- never exceed 10,000 without a new explicit decision

Production request-protection limits remain separate and unchanged. The
acceptance runner owns its explicit provider-attempt ceiling.

## 12. Implementation order

1. freeze this Task Card and add failing product-quality tests
2. fix deterministic safety boundaries and everyday question focuses
3. expose richer news metadata and fact-level disclosure Evidence
4. revise retrieval and context selection
5. replace extractive generation, validation, and fixed fallback
6. implement compact sources and bottom chat input
7. run focused and full regressions
8. run bounded live acceptance only after deterministic gates pass
9. update Source of Truth, work log, and release evidence

## 13. Stop conditions

FSC-4 does not pass if any of the following remains:

- demonstrated ordinary supported-company questions still fail lexically
- answers remain snippet copies rather than useful explanations
- irrelevant news is added to satisfy a count
- report content is transmitted externally
- user attributes are inferred from evidence
- wrong-company, unsupported number, fake locator, or direct advice regresses
- UI retains submitted text or obscures the latest answer
- product-quality tests pass only through question-specific exceptions

## 14. Implementation and validation record

- everyday focus routing, source-aware retrieval, fact-level disclosures,
  enriched internal news summaries, question-adaptive composition, compact
  sources, and bottom chat input: implemented
- beginner-QA fixture: 120 cases
- deterministic beginner-QA result: PASS
- focused answer/citation safety result after final composition change:
  `361 passed`
- Ruff: `PASS`
- final full regression: `2086 passed, 2 warnings`
- M3 Gate: `34/34`; Critical `17/17`; public exposure `0`
- service snapshot validation: `PASS`, 54 documents
- secret scan and diff check: `PASS`
- final live service acceptance:
  - result: `PASS`
  - Gemini success: `10/12`
  - public response validation: `15/15`
  - Critical provider attempts: `0`
  - unsupported number, wrong company, uncited core number, direct advice:
    `0`
  - remaining two eligible cases: validated fixed fallback
- Human Owner approved deployment on 2026-07-28
- implementation PR:
  - PR `#14`: `MERGED`
  - head SHA: `7e66cb58dca6434886f797d914109d73adb6926e`
  - merge SHA: `b5fde16c69d03fadcb57cff5c0f26e72dbc9d69f`
  - quality-gate run `30299315471`: `PASS`
- initial deployment run `30299536951`:
  - result: `FAILED` at the release smoke
  - cause: the smoke still required the pre-FSC-4 single-disclosure-evidence
    shape while the public response correctly used fact-level and
    multi-source Evidence
  - automatic rollback: `PASS`
  - restored release SHA:
    `2adcc787a803996d4a181a6cd3faa3158602660a`
- deployment smoke hotfix:
  - PR `#15`: `MERGED`
  - merge SHA: `136271ea80802a39f1981e539f183d544d95e23a`
  - quality-gate run `30300234890`: `PASS`
- final deployment run `30300383109`: `PASS`
  - deployed release SHA:
    `136271ea80802a39f1981e539f183d544d95e23a`
  - deployed image ID:
    `sha256:bda18d4456742b59f2ac0e44877fe5544ccac7d54d4438b83d64e2c6768ce3b9`
  - API and Streamlit health: `PASS`
  - recorded snapshot: 54 documents; news 15, disclosure 3,
    research-report sections 36
  - release smoke: `PASS`, 7 scenarios and 8 requests
  - rollback on the successful deployment: `NOT_RUN`

## 15. Post-deployment answer-presentation closure

Human Owner feedback after the deployed FSC-4 demo identified two remaining
presentation defects:

- the loading message could remain visible beside an already rendered answer
- separate bordered section cards made a valid structured answer read like a
  technical report rather than one conversational explanation

The local follow-up branch `fix/fsc4-answer-presentation-polish` applies the
following bounded closure:

- explicitly clear the loading placeholder before the post-submit rerun
- keep the existing answer-section schema but render its non-empty sections
  inside one assistant message without separate bordered cards
- use beginner-facing section names, compact status wording, one combined
  notice, and `참고한 자료` links
- strengthen the Gemini instruction toward a connected explanation, without
  adding a universal item count or forcing unsupported length
- keep research-report text outside Gemini and add local attribution so
  report estimates do not appear as unexplained service facts
- enforce LF for immutable service-snapshot JSON and checksum files through
  `.gitattributes`

Local validation:

- focused answer/UI regression: `82 passed, 2 warnings`
- full regression: `2087 passed, 2 warnings`
- Ruff: `PASS`
- service snapshot validation: `PASS`, 54 documents
- approved-snapshot browser probe, `삼성전자 호재 있어?`: `PASS`
  - submitted input cleared
  - loading message absent after answer completion
  - one continuous assistant answer
  - report estimates explicitly attributed
  - compact source links retained

Publication status:

- implementation and plan commit:
  `edb46ae` (`Polish FSC-4 answers and plan M5`)
- remote branch:
  `fix/fsc4-answer-presentation-polish` — pushed
- PR:
  `#18` — `MERGED` — <https://github.com/JJungDae/Questock/pull/18>
- merge SHA:
  `6f50ee922c2a1c74278ead2f679472ba3e19bc8b`
- focused publish-preflight regression:
  `85 passed, 2 warnings`
- quality-gate run `30323480083`: `PASS`
- deployment: `NOT_STARTED`
