# FIRST SERVICE COMPLETION EXECUTION DECISION

> 결정일: `2026-07-27`
> 기준 branch: `main`
> 계획 기준 SHA: `da03a6fb3be5c985cef7d5d1f0523827340fe088`
> 상태: `COMPLETE - FSC-0~FSC-3 PASS / complete; Service Completion Gate PASS / complete; A15-M activation check READY`

## 1. 문서 효력

이 문서는 M4 이후 FSC 삽입 범위에서
PROJECT_PLAN_FINAL_PASS의 실행 순서 addendum과
AGENT_WORKFLOW의 bundle 운영 addendum 역할을 함께 수행한다.

해당 범위에서 기존 문서와 충돌하면 이 결정 문서와
최신 SOURCE_OF_TRUTH_INDEX를 우선한다.

동일 결정을 반복하는 별도 Project Plan 또는 Workflow addendum은 만들지
않는다.

## 2. 삽입 목적

B9와 M4 Gate는 완료됐지만 현재 공개 서비스는 recorded data와 fixed fallback
중심이다. A15-M이나 다른 확장 기능보다 먼저 다음 범위를 완료한다.

```text
3개 지원 종목의 고정시점 snapshot
검증된 뉴스·공시·리서치 자료
Gemini 3.5 Flash 실제 생성과 안전 fallback
요청 보호·제한된 session memory·응답 cache
공개 UI와 exact-SHA release
```

FSC는 새 금융 분석 기능이나 live source provider 구현이 아니다. 기존
Evidence, freshness, policy, citation, validator, safety, public response
shape를 유지한 채 1차 서비스를 완성하는 post-M4 bundle이다.

## 3. 공식 실행 순서

```text
M4 Gate PASS
-> FSC-0 / SC-00 official flow and preflight
-> FSC-1 / SC-01~04 data snapshot
-> data and provenance review
-> FSC-2 / SC-05 live generation and request protection
-> LLM and security review
-> FSC-3 / SC-06~07 UI and release
-> exact-SHA GCE deploy
-> Service Completion review and Gate
-> A15-M activation check
-> optional Stretch M2-09
-> M5-01
-> later P1 eligibility check
```

각 bundle은 이전 bundle의 승인된 결과와 자체 preflight가 통과한 뒤에만
시작한다. commit, push, PR, merge, deploy는 계속 각각 별도 승인을 받는다.

## 4. 공식 상태

```text
M4 Gate:
PASS

current official bundle:
First Service Completion - complete

current checkpoint:
A15-M activation check - READY / NOT_STARTED

Service Completion Gate:
PASS / complete

A15-M:
activation and entry READY / implementation NOT_STARTED
```

M1-09는 `mandatory supplement implemented - final independent review pending`
상태를 유지한다.

## 5. FSC-0 Preflight 결과

### 5.1 Git과 기존 회귀

- branch: `fsc/fsc-0-preflight`
- HEAD와 `origin/main`:
  `da03a6fb3be5c985cef7d5d1f0523827340fe088`
- 기존 사용자 소유 untracked `.tmp/`는 수정·삭제하지 않았다.
- 전체 pytest: `PASS - 1852 passed, 2 warnings`
- M3 Gate: `PASS - 34/34`
- Critical: `PASS - 17/17`
- public exposure: `0`
- secret scan: `PASS - []`
- compile: `PASS - exit 0`
- GitHub CI: `NOT_RUN`

### 5.2 Credential 경계

값을 출력하지 않고 다음 상태만 확인했다.

- local `.env`:
  - `NAVER_CLIENT_ID`: configured
  - `NAVER_CLIENT_SECRET`: configured
  - `GEMINI_API_KEY`: configured
- GitHub Secret `GEMINI_API_KEY`: configured
- local `.env`: Git untracked/ignored
- `.dockerignore`: `.env`와 `.env.*` 제외
- GCE `.env.runtime`: `NOT_CHECKED`

local `.env`, GitHub Secret, GCE runtime secret은 서로 다른 상태다. 하나의
존재 여부로 다른 환경의 설정 완료를 판정하지 않는다.

### 5.3 Gemini

- official model metadata:
  `models/gemini-3.5-flash` present
- official method metadata:
  `generateContent` supported
- LiteLLM `1.83.7` static routing:
  `gemini/gemini-3.5-flash -> gemini`
- sanitized generation smoke:
  `FAIL - rate_limited`
- normalized provider status:
  `rate_limited`
- credential 원문, provider raw message, response content:
  `NOT_EXPOSED`
- structured response, usage, finish reason, `thinking_level=minimal`의 실제
  generation 결과:
  `NOT_CONFIRMED - provider rejected the request before a response`
- Human Owner free quota and billing confirmation:
  `NOT_RUN`

Stop decision:

- 모델을 자동 변경하지 않는다.
- dependency 또는 LiteLLM pin을 변경하지 않는다.
- `thinking_budget`와 `thinking_level`을 함께 보내지 않는다.
- FSC-2 전 Human Owner가 quota/billing 상태를 확인하고 승인한 sanitized
  generation smoke 1회로 실제 structured output과 thinking 전달을 확인한다.

위 항목은 FSC-0 당시의 관측·중단 결정을 보존한다. 이후 Human Owner가
Gemini 3.5 계약 전체 교체와 필요한 최소 호환 dependency 갱신을 승인했다.
현재 효력이 있는 계약은 다음과 같다.

- `gemini/gemini-3.5-flash`
- `litellm==1.84.1`
- `LLM_THINKING_LEVEL=minimal`
- `LLM_MAX_OUTPUT_TOKENS=4096`
- `LLM_TIMEOUT_SECONDS=15`
- retry `0`
- FSC-4 answer path uses concise JSON instructions plus project-side strict
  parsing and safety validation; provider-side JSON-schema-constrained
  decoding is disabled after live repeated-output reproduction
- adapter 전달값 `reasoning_effort=minimal`
- `LLM_THINKING_BUDGET`, level/budget 동시 전송, `drop_params`,
  undocumented `extra_body`, thinking 생략, 2.5 fallback 금지

Human Owner가 제공한 로컬 evidence에 따르면 기존 `litellm==1.83.7`은
해당 3.5 minimal-thinking 요청에서 `UnsupportedParamsError`를 냈다. 이번
교체에서는 그 실패 요청을 재실행하지 않았다. `1.84.0`에는 3.5 모델 등록이
없고 `1.84.1`에는 exact model metadata와 minimal thinking-level mapping이
함께 있음을 확인했다. local mock transport 검증 뒤 Human Owner가 승인한
sanitized Gemini live smoke를 정확히 1회 실행했고 결과는 `PASS`였다.

### 5.4 NAVER API HUB

- endpoint:
  `GET https://naverapihub.apigw.ntruss.com/search/v1/news`
- credential header mapping:
  approved contract와 일치
- initial PowerShell here-string pipeline probes:
  `ENVIRONMENT_INVALID - 한글 query가 ?로 치환됨`
- UTF-8 official example과 generic query 재검증:
  `PASS - HTTP 200`, `total > 0`, items 반환
- UTF-8 company query 재검증:
  `PASS - 삼성전자·SK하이닉스·현대차 모두 items 반환`
- 실제 item의 `pubDate`와 `originallink`:
  `PASS - UTF-8 재검증 결과에서 존재 확인`
- `2026-07-24` cutoff 기준 15건 coverage:
  `NOT_CONFIRMED`
- official documentation:
  query, bounded `display/start`, `sort=date`, response field 계약 확인
- metadata 저장·가공 permission:
  `초기 REVIEW_REQUIRED; SC-01에서 기존 승인 정책 적용으로 해소`

판정:

NAVER API HUB와 credential은 automatic collection에 `COMPATIBLE`하다.
최초 `0 items`는 API 결과가 아니라 Windows PowerShell pipeline encoding
오류이므로 coverage 판단 근거에서 제외한다. FSC-0 시점에는 cutoff·회사
귀속·중복 제거를 통과한 15건 확보와 저장·가공 permission을 확인하지
않았다. 이후 SC-01에서는 기존 승인 정책에 따라 기사 metadata와 Questock
자체 짧은 요약만 사용하고 기사 본문을 runtime/Git에서 제외했다.

### 5.5 DART

다음 official viewer가 모두 `HTTP 200`이며 해당 receipt를 반환 경계에서
확인했다.

- 삼성전자:
  `https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260515002181`
- SK하이닉스:
  `https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260515002287`
- 현대자동차:
  `https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260515002418`

로컬 source inventory에는 삼성전자 PDF 1건만 확인됐다. SK하이닉스와
현대자동차 PDF는 official viewer 다운로드 또는 Human Owner 제공 경로로
확보한다. 세 PDF의 fact extraction·locator·coverage는 `NOT_RUN`이다.

### 5.6 미래에셋 리서치 리포트

Human Owner가 `2026-07-27`에 세 리포트의 입력 package 준비와 다음 범위의
내부 corpus 사용을 승인했다.

- `usage_review_status=approved`
- `corpus_ingest_allowed=true`
- `external_llm_processing_allowed=false`
- PDF 검증 metadata, 구조화 fact, locator, Questock 자체 짧은 요약만 허용
- PDF, report body, evidence excerpt, raw text는 runtime, Git, Gemini에서 제외

- 삼성전자:
  `https://securities.miraeasset.com/bbs/board/message/view.do?categoryId=1800&messageId=2341060`
  - title: `과격한 주가 반응에 뇌동하지 말자`
  - publication date: `2026-07-07`
- SK하이닉스:
  `https://securities.miraeasset.com/bbs/board/message/view.do?categoryId=1533&messageId=2341215`
  - title: `시선을 약간만 아래로`
  - publication date: `2026-07-14`
- 현대차:
  `https://securities.miraeasset.com/bbs/board/message/view.do?categoryId=1800&messageId=2341441`
  - title: `2Q26 리뷰: 우려 대비 양호, 로봇 모멘텀 주목`
  - publication date: `2026-07-24`

세 공식 PDF의 hash, page count, 수치와 locator를 Git ignored working
영역에서 검증했다. 삼성전자 NAND 수치는 PDF 기준 `+3%`, SK하이닉스는
PDF 기준 일반 `HBM` 표기, 현대차 발행일은 PDF 표지와 page mark 기준
`2026-07-24`로 확정했다. 세 종목 모두 M1-06 corpus mode로 12개 section을
정규화했고 당시 결과는 `IMPLEMENTED / Human Owner review pending`이었다.
정규화 결과는 이후 Human Owner 확인을 받아 `PASS / complete`로 마감됐다.

### 5.7 Database

```text
DB:
NOT_USED
```

## 6. FSC-0 판정과 후속 Gate

FSC-0:
`PASS / complete - Human Owner confirmed 2026-07-27`

완료된 항목:

- 공식 FSC 삽입 위치와 bundle 순서 확정
- credential 존재 여부와 secret 제외 경계 확인
- Gemini model/routing 및 rate-limit stop decision 확정
- NAVER automatic collection compatibility 확인과 PDF/URL fallback 유지
- DART 3건 확보 경로 확정
- 리포트 3건 후보와 Human Owner PDF fallback 경로 확정
- 기존 regression과 safety gate 유지 확인

필수 후속:

1. FSC-2 전 Gemini free quota/billing 확인과 승인된 generation smoke

FSC-1 계획 검토:
`ALLOWED`

FSC-1 구현:
`PASS / complete - SC-01~04 complete; Human Owner requested closure 2026-07-27`

SC-01 automatic collection result:

- UTF-8 saved Python collector:
  `IMPLEMENTED`
- PowerShell here-string to Python stdin:
  `NOT_USED`
- initial broad canonical query:
  `1,000 items per security; cutoff-window 0`
- initial zero-candidate cause:
  `broad canonical query exhausted 1,000-result ceiling`
- query/date parsing/timezone/attribution defect:
  `NOT_OBSERVED`
- final query/sort config:
  `삼성전자 2026년 7월 24일/date`,
  `SK하이닉스 7월24일/sim`,
  `현대차 7월24일/date`
- final normalized candidates:
  `16 / 48 / 14`
- final pre-market/intraday:
  `7/9, 16/32, 4/10`
- final result:
  `PASS - exit 0`
- raw/candidate/rejection output:
  `Git ignored`
- Human Owner metadata permission decision:
  `APPROVED - existing metadata and Questock-summary policy`

The API and credentials succeeded in both collection runs. The first broad query result is
retained as a 1,000-result ceiling observation, not an API failure. The final
date-narrowed run satisfies candidate-count and time-distribution readiness.

Initial SC-01 deterministic curation result, superseded by the quality
revision below:

- selected:
  `5 per security`
- pre-market/intraday:
  `1/4 per security`
- unique source hosts:
  `5 per security`
- selected item fields:
  `document_id, time_band, source_locator, Questock short summary`
- article title/text/description in curated output:
  `NONE`
- two consecutive builds:
  `exit 0 / exit 0; byte-identical`
- existing news metadata policy:
  `APPLIED - no new copyright-wide review`
- SC-01 review:
  `initial selection superseded by the quality revision below`

SC-01 quality revision:

- directness and price-causality information now precede event diversity, time,
  and source diversity
- quality supplements: maximum 3 queries and 2 calls per query/security
- revised candidate pools: `24 / 48 / 14`
- selected time bands: `2/3, 1/4, 2/3` pre-market/intraday
- simple price, broad market, leverage regulation, affiliate-only, promotion,
  peripheral, and accidental date-query items are excluded
- title/link review crosswalks remain Git ignored and separate from runtime
- status: `PASS / complete - Human Owner confirmed 2026-07-27`

SC-02 disclosure result:

- fixed receipts: `20260515002181 / 20260515002287 / 20260515002418`
- one `FinancialDocument` per receipt/security
- actual verified fact counts: `18 / 21 / 20`
- required V4 categories: `10/10` for all three
- observed PDF page counts: `323 / 236 / 286`
- official viewer exact receipt/corp/company/report checks: `PASS`
- official viewer remark: `유 / 유 / 유`
- correction/subsequent correction/withdrawal: `false / false / false`
- local OpenDART API key value: `NOT_CONFIGURED`; list API `NOT_RUN`
- corp code source/status: `project_security_mapping / candidate`
- Hyundai definition conflicts: retained with section/basis/conflict note
- raw input, PDF, excerpt, and local path in canonical output: `NONE`
- status: `PASS / complete - Human Owner confirmed 2026-07-27`

SC-03 report result:

- Human Owner source and permission decision: `APPROVED`
- official PDF page counts: `8 / 9 / 12`
- normalized M1-06 corpus documents: `12 / 12 / 12`
- external LLM source processing: `false`
- source PDF/body/excerpt/raw text in runtime or Git: `NONE`
- actual curation and repeated deterministic build: `PASS`
- targeted: `21 passed`
- SC-01~03 and M1-04~M1-06 regression: `382 passed`
- status: `PASS / complete - Human Owner confirmed 2026-07-27`

SC-04 snapshot result:

- snapshot ID/basis:
  `svc-20260724-1402 / 2026-07-24T05:02:00Z`
- canonical data:
  `manifest.json, documents.json, coverage_matrix.json, permission_register.json`
- generated evidence:
  `snapshot_checksum.txt, validation_report.json`
- document counts:
  `54 total; news 15; disclosure 3; report 3 manifests / 36 sections`
- disclosure facts:
  `18 / 21 / 20`
- cutoff-after documents:
  `0`
- global document IDs:
  `54 / 54 unique`
- documents checksum:
  `54a57430f228d0b6305fff979beefeed8da0ebcdfdcbcd92544cc17575bdcf83`
- repeated builds:
  `6 files byte-identical`
- targeted:
  `41 passed`
- full regression:
  `1946 passed`
- Ruff / compile / secret scan / diff check:
  `PASS / PASS / [] / PASS`
- independent pytest rerun:
  `NOT_RUN`
- GitHub CI:
  `NOT_RUN`
- status:
  `PASS / complete`

FSC-1:
`PASS / complete - SC-01~04 complete`

FSC-2/FSC-3 구현:
`PASS / complete - FSC-2 Human Owner confirmed 2026-07-27; FSC-3 local and remote closure complete`

## 7. 변경 제한

FSC-0에서는 다음을 변경하지 않는다.

- application code, tests, fixtures
- dependency, `pyproject.toml`, `uv.lock`
- public schema shape 또는 `trace_version`
- core model/status, M1/M2 계약
- live provider adapter
- snapshot data
- API/UI/LLM runtime

work log는 Human Owner가 FSC-0 결과를 확인한 뒤 실제 작업일 파일에만
기록한다.

## 8. FSC-2 / SC-05 실행 결과

- Human Owner billing confirmation:
  `CONFIRMED - approved smoke authorized after billing and runtime preparation`
- sanitized Gemini smoke:
  `PASS - exactly one live call`
- safe result:
  `status=ok`, `model=gemini/gemini-3.5-flash`,
  `structured_parse_ok=true`, `usage_present=true`, `finish_reason=stop`,
  `latency_ms=1854.106`
- request contract:
  strict JSON schema, `reasoning_effort=minimal`,
  provider `thinkingLevel=minimal`, max output `1024`, timeout `10`, retry `0`
- prohibited payloads:
  no news, disclosure, research-report, session, credential, or local-path data
- raw prompt/provider response/error:
  `NOT_OUTPUT / NOT_RECORDED`
- additional live calls:
  `0`

FSC-2 implements disabled/gemini runtime selection, bounded request
protection, bounded recent anonymous exchanges, a 90-second session response
cache, a browser-local current-session transcript bounded to 4 entries, opaque
client identity, and API-only atomic secret deployment with environment-first
rollback. Report content without exact external processing permission remains
fixed-only.

Local verification:

- targeted: `227 passed, 2 warnings`
- affected integration: `73 passed, 2 warnings`
- full regression: `1999 passed, 2 warnings`
- M3 Gate: `34/34`; Critical `17/17`; public exposure `0`
- Ruff: `PASS`
- compile: `PASS`
- secret/local-path scan: `PASS - []`
- diff check: `PASS`
- GitHub CI: `NOT_RUN`
- independent pytest rerun: `NOT_RUN`
- deploy: `NOT_RUN`

FSC-2 closure boundary (historical snapshot):

- FSC-2: `PASS / complete - Human Owner confirmed 2026-07-27`
- FSC-2 Git: commit/push
  `25cac10030800f08d4167b9f7739d06b3d1492ca` / `complete`
- FSC-2 PR: `#10`, `MERGED`,
  `https://github.com/JJungDae/Questock/pull/10`, merge SHA
  `92561e34b4839d32a9bdac979c6c471da8e56923`
- FSC-3:
  `SC-06 PASS / complete; SC-07 local gate PASS; remote release closure
  pending`
- SC-06 onward commit/push/PR update/merge/deploy:
  `NOT_RUN / NOT_RUN / NOT_RUN / NOT_RUN / NOT_RUN`

## 9. FSC-3 / SC-06 local implementation result

- fixed snapshot UI:
  selector removed; snapshot ID, `2026-07-24 14:02 KST` basis, recorded mode,
  news range, generation/fallback, report permission, disclosure coverage,
  quota fallback, and personal-financial-data warning displayed
- session/UI behavior:
  recent transcript 4, new-session isolation, rerun/F5 automatic POST 0
- acceptance asset:
  exact versioned 15-case fixture plus strict schema/validator/static tests
- representative local API/UI:
  three supported securities PASS in recorded/fixed mode
- targeted:
  `32 passed, 2 warnings`
- affected regression:
  `266 passed, 2 warnings`
- full regression:
  `2020 passed, 2 warnings`
- M3 Gate:
  `34/34`; Critical `17/17`; public exposure `0`
- Ruff / compile / secret scans / JSON / diff check:
  `PASS / PASS / [] / PASS / PASS`
- additional live Gemini calls:
  `0`
- 15-case live acceptance:
  `NOT_RUN - separate Human Owner approval required`

The approved focused supplement resolved those local preconditions with general
contracts rather than acceptance-question or snapshot-label exceptions:

- symmetric Hangul suffix normalization is applied to query and document tokens
  while the BM25 threshold, hard filter, score formula, and wrong-company rules
  remain unchanged
- strict `YYYY년 M월` and `YYYY년 M월 D일` parsing now composes with the
  existing ISO and session-period contracts
- threshold-passing Evidence is source-aware when multiple required sources are
  requested; missing or low-scoring sources are not fabricated
- retrieval, context budget, and fixed composition use the same source-diverse
  projection helper
- acceptance required sources are checked against policy
  `satisfied_sources`, while the public response remains citation-bound
- reports without external LLM permission remain fixed-only; mixed requests
  transmit no report Evidence and no mixed composition was introduced

The exact 15 questions and canonical snapshot content were unchanged. Two
snapshot builds were byte-identical and matched the tracked canonical output.
Focused targeted tests passed `347`; M3 Gate tests passed `9`; full regression
passed `2048`; M3 Gate passed `34/34`, Critical `17/17`, public exposure `0`.
No additional live Gemini or provider call was made. The 15-case live
acceptance remains `NOT_RUN` pending separate Human Owner approval.

SC-06 closure boundary (historical snapshot):

- SC-06:
  `PASS / complete - live acceptance passed 2026-07-27`
- live acceptance:
  `PASS - cumulative LLM success 10/12; Critical 3/3 with 0 calls; actual
  provider attempts 26/30; all public validations PASS`
- SC-07:
  `local release checkpoint PASS; remote CI/GCE/exact-SHA release NOT_RUN`
- GitHub CI / GCE remote smoke / exact-SHA deploy:
  `NOT_RUN / NOT_RUN / NOT_RUN`
- commit / push / PR update / merge:
  `NOT_RUN / NOT_RUN / NOT_RUN / NOT_RUN`

## 10. FSC-3 / SC-07 Docker checkpoint result

- Docker engine:
  `PASS - server 29.6.2`
- clean locked build:
  `PASS - questock:fsc-sc07-local-25cac100`,
  image `sha256:ad8d753d78a0b84fa3321f225188d567fc1940df5e5dac38c6b075ff50384bf4`
- container boundary:
  `PASS - non-root, read-only rootfs, capabilities dropped,
  no-new-privileges`
- API:
  `PASS - HTTP 200; recorded snapshot svc-20260724-1402; 54 documents`
- UI:
  `PASS - health HTTP 200; root HTTP 200`
- recorded release smoke:
  `PASS - 7/7; recent issue complete, disclosure partial, report complete,
  glossary complete, wrong-company no_evidence, blocked blocked, multi-turn
  partial`
- focused release-smoke regression:
  `PASS - 28 passed, 1 warning`
- additional Gemini/provider attempts:
  `0 - cumulative total remains 26/30`

The initial smoke found a B9-only basis-date and unsupported-company
expectation in the release script. The focused correction aligns that
deployment check with the FSC snapshot and versioned wrong-company case, while
retaining exact receipt, official URL, required disclosure value/unit/page/
section, body-answer, and no-evidence checks.

Current boundary:

- SC-07 local gate:
  `PASS`
- SC-07 remote gate:
  `PASS`
- FSC-3:
  `PASS / complete`
- Service Completion Gate:
  `PASS / complete`
- GitHub CI / GCE remote smoke / exact-SHA deploy / external UI:
  `PASS / PASS / PASS / PASS`
- A15-M:
  `activation and entry READY / implementation NOT_STARTED`
- commit / push / PR / merge / deploy:
  `complete / complete / complete / complete / complete for the release`

## 11. FSC-3 / SC-07 remote closure result

### 11.1 CI and merge

- PR #11:
  head `8d1b9521fdbef003cb84708b6aa7b47d01d8dc8a`; first CI
  `30273039760` failed because Python 3.11 could not resolve an extracted
  Streamlit helper annotation; fix commit `8d1b952`; CI `30273607080` passed;
  merge `6affd27f4f95aae438268acd2bc4fa7733346b5d`
- PR #12:
  commits `499bf03`, `bed5684`; first CI `30274239625` failed because a legacy
  B9 static expectation retained the old Gemini-key regex; the synchronized
  focused contract passed `139`; CI `30274469379` passed; merge
  `2adcc787a803996d4a181a6cd3faa3158602660a`

### 11.2 Deployment

- first deploy `30273898079`:
  failed before runtime write or deploy because the anchored key allowlist
  excluded one dot in the already-live-verified 53-character Gemini key;
  existing service and image were unchanged; rollback execution `NOT_RUN`
- exact-SHA deploy `30274651799`:
  `PASS - 3m32s`
- deployed release SHA:
  `2adcc787a803996d4a181a6cd3faa3158602660a`
- deployed image:
  `sha256:53628bacc40f2329bc3f7dfcb6771aeee2e5fd83a1a44592ee08bbc950daf138`
- previous rollback target:
  SHA `67fa43dd5a7ec74e7785713eb1adcfa402baab85`; image
  `sha256:56df8f16ed3ed58de659e9ec46c9e24b7d3ddc896dc8a022102f68f351d7b928`
- rollback execution:
  `NOT_RUN - deployment passed`

### 11.3 Remote verification and final boundary

- runtime health:
  `PASS - status ok; recorded snapshot svc-20260724-1402; 54 documents`;
  news `15`, disclosure `3`, research report `36`;
  `live_connectivity_checked=false`
- recorded smoke:
  `PASS - 7/7`; recent issue `complete`, disclosure `partial`, research report
  `complete`, glossary `complete`, wrong-company `no_evidence`, blocked
  `blocked`, multi-turn `partial`
- workflow external UI health:
  `PASS`
- independent visual check:
  `LIMITED / non-gate`; a separate reviewer browser attempt to the registered
  host on port 8501 timed out, so interactive visual rendering is not claimed
- Gemini provider attempts:
  cumulative `26/30`; fixed/disabled recorded deployment smoke added `0`

FSC-3 and the Service Completion Gate are `PASS / complete`; remote release
closure is complete. A15-M activation and entry are `READY / ALLOWED`, but
implementation has not started. Stretch M2-09, M5-01, and later P1 ordering
remains unchanged.
