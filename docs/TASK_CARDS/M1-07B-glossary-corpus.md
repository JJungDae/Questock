# TASK CARD - M1-07B Glossary Corpus

## 1. Plan Linkage
- Task bundle: B3
- Step: M1-07 glossary ingest
- Substep: M1-07B actual glossary corpus
- Priority: P0
- Planning base commit: `2aa991c6674d9947548432aa520b6c03f9b6065d`
- Preconditions:
  - M1-07A schema/index/lookup/locator/candidate-coverage boundary: PASS
  - M1-07A completion SHA: `2aa991c6674d9947548432aa520b6c03f9b6065d`
  - M1-07A main push: complete
  - M1-07A final review: PASS
- Related risk IDs: R13, R14, R17, R24, R37, R43, R45, R54
- Related taxonomy: financial_term, source_selection, citation_support, evidence_sufficiency, abstention

## 2. Human Owner Decision Record
Decision date: `2026-07-22`

The Human Owner approved the following.

1. Use the existing 15-term P0 set.
2. Use formal Korean terms as `canonical_term` and add English abbreviations, spacing variants, and safe short expressions as aliases.
3. Use `content_origin="user_authored"` for all entries.
4. Official explanations, accounting/disclosure materials, and established dictionaries may be used only to verify facts, terminology, formulas, and caution points.
5. Do not copy, translate, sentence-match, or closely paraphrase source wording. “Slightly modifying an official sentence” is not the approved method; verify facts first and then write a new Questock sentence independently.
6. Set `corpus_ingest_allowed=true` and `external_llm_processing_allowed=true` for all 15 independently authored entries.
7. Include formulas and examples only where they materially improve beginner understanding.
8. Use concise beginner-oriented prose: normally one or two sentences each for `definition`, `why_it_matters`, and `caution`.
9. Adoption of this revised Task Card records approval of the term identities, content policy, content drafts, corpus ingest, and external LLM processing. Commit and push still require separate approval.

## 3. Objective
Create `data/glossary.json`, an approved Korean glossary corpus containing exactly the 15 reviewed P0 financial terms fixed in this Task Card.

M1-07B includes actual content/data creation, explicit actual-corpus coverage evaluation, complete lookup/locator verification, and Task Card result logging. Retrieval and answer generation remain out of scope.

## 4. Scope
### Implemented in M1-07B
- Add `data/glossary.json`.
- Add exactly the 15 approved entries in Section 8.
- Use `corpus_type="approved_corpus"` and `corpus_id="glossary-approved-v1"`.
- Add reviewed `definition`, `why_it_matters`, `caution`, and selected formula/example fields.
- Record project-authored origin and permission metadata.
- Permit external LLM processing for all 15 Questock-authored entries.
- Add an explicit actual-corpus coverage evaluation helper.
- Verify every canonical term, alias, required locator, optional locator, related ID, and coverage result.
- Record actual targeted/regression/smoke results.

### Excluded
- Retrieval, EvidencePolicy, router, API, UI, LLM invocation, prompt implementation
- Provider protocol and `FinancialDocument` conversion
- Fuzzy matching
- Semantic overclaim detection beyond the existing fixed blocklist
- Automated web scraping
- Copying, translating, or closely paraphrasing external definitions
- Core model, status, provider, resolver, or config changes
- M2 implementation

## 5. Approved Files
### Modify or create
- `data/glossary.json`
- `app/ingest/glossary.py`
- `tests/unit/test_glossary_ingest.py`
- `docs/TASK_CARDS/M1-07B-glossary-corpus.md`

`app/ingest/glossary.py` modification is approved only for the actual-corpus coverage boundary in Section 11.

### Do not modify
- `app/core/**`
- `app/providers/**`
- `app/config.py`
- `app/ingest/reports.py`
- `tests/fixtures/glossary/glossary_synthetic.json`
- retrieval, API, UI, LLM, and M2 files

Do not refactor M1-07A utilities into unrelated shared modules.

## 6. Corpus Contract
```json
{
  "schema_version": 1,
  "corpus_type": "approved_corpus",
  "corpus_id": "glossary-approved-v1",
  "language": "ko",
  "entries": []
}
```

Rules:
- `schema_version` is real integer `1`.
- `corpus_type` is exactly `approved_corpus`.
- `corpus_id` is exactly `glossary-approved-v1`.
- `language` is exactly `ko`.
- Entry ID set exactly matches Section 8.
- Exactly 15 entries are present.
- Every entry has `version=1`, `language="ko"`, `usage_review_status="approved"`, `corpus_ingest_allowed=true`, `external_llm_processing_allowed=true`, `content_origin="user_authored"`, and `ingestion_version="glossary-ingest-m1-07-v1"`.
- No synthetic, pending, or rejected entry is allowed.
- No duplicate or normalized canonical/alias collision is allowed.
- No unresolved, duplicate, or self-referencing related ID is allowed.

## 7. Common Authorship, Source, and Permission Metadata
All 15 entries use the following.

### `content_origin`
```text
user_authored
```

### `source_note`
```text
Questock 프로젝트가 금융감독·거래소·회계기준 등 공식 자료와 확립된 사전의 개념을 사실 확인에 참고한 뒤 독립적으로 작성한 설명입니다. 외부 원문의 문장을 복사·번역하거나 근접 변형하지 않았습니다.
```

### `permission_note`
```text
Human Owner가 이 Questock 작성 문구의 glossary corpus 적재와 외부 LLM을 통한 설명 재구성 처리를 승인했습니다.
```

### Source locator fields
```json
{
  "source_url": null,
  "source_asset_id": null
}
```

Official reference URLs used for factual review must be recorded in the M1-07B implementation log or content-review table. They must not be represented as if external wording were the corpus text.

### Manual fact-check order
1. Korean financial supervisory, disclosure, and exchange authorities
2. Korean accounting standards and official accounting guidance
3. Government or public-institution glossaries
4. Established Korean dictionaries for terminology only
5. Multiple secondary references only as a cross-check

If official and secondary sources differ, prefer the official source and record the conflict. If independent wording cannot be produced confidently, stop that entry instead of copying.

## 8. Approved Entry Identity Set
```python
EXPECTED_ENTRY_IDS = {
    "glossary:per",
    "glossary:pbr",
    "glossary:roe",
    "glossary:eps",
    "glossary:market_cap",
    "glossary:revenue",
    "glossary:operating_profit",
    "glossary:net_income",
    "glossary:operating_margin",
    "glossary:rights_offering",
    "glossary:convertible_bond",
    "glossary:corporate_disclosure",
    "glossary:consensus",
    "glossary:consolidated_financial_statements",
    "glossary:separate_financial_statements",
}
```

| Entry ID | Canonical term | Approved aliases | Category |
|---|---|---|---|
| `glossary:per` | 주가수익비율 | `PER`, `주가 수익 비율`, `주가이익비율`, `주가 이익 비율` | valuation |
| `glossary:pbr` | 주가순자산비율 | `PBR`, `주가 순자산 비율` | valuation |
| `glossary:roe` | 자기자본이익률 | `ROE`, `자기자본 이익률`, `자기자본수익률`, `자기자본 수익률` | profitability |
| `glossary:eps` | 주당순이익 | `EPS`, `주당 순이익` | profitability |
| `glossary:market_cap` | 시가총액 | `시총` | market_value |
| `glossary:revenue` | 매출액 | `매출` | performance |
| `glossary:operating_profit` | 영업이익 | `영업 이익` | performance |
| `glossary:net_income` | 당기순이익 | `순이익`, `당기 순이익` | performance |
| `glossary:operating_margin` | 영업이익률 | `영업 이익률`, `영업마진`, `영업 마진` | profitability |
| `glossary:rights_offering` | 유상증자 | `유상 증자`, `유증` | financing |
| `glossary:convertible_bond` | 전환사채 | `CB`, `전환 사채` | financing |
| `glossary:corporate_disclosure` | 기업공시 | `공시`, `기업 공시` | disclosure |
| `glossary:consensus` | 시장 컨센서스 | `컨센서스`, `증권사 컨센서스`, `시장예상치`, `시장 예상치` | forecast |
| `glossary:consolidated_financial_statements` | 연결재무제표 | `연결 재무제표`, `연결재무` | financial_statements |
| `glossary:separate_financial_statements` | 별도재무제표 | `별도 재무제표`, `별도재무` | financial_statements |

Do not add broad aliases such as `수익`, `기업가치`, or `신주발행`, because they can refer to concepts outside the approved canonical term.

## 9. Approved Content Drafts
Implementation may make only grammar or JSON-escaping corrections. A financial-meaning change requires Human Owner review.

### 9.1 `glossary:per` — 주가수익비율
- `definition`: 주가수익비율은 현재 주가가 주당순이익의 몇 배 수준인지 나타내는 주가평가 지표입니다.
- `why_it_matters`: 기업의 주가 수준을 이익과 비교하고 비슷한 업종이나 기업 사이의 상대적인 평가 수준을 살펴볼 때 사용합니다.
- `caution`: 사용한 이익의 기간과 예상치 여부에 따라 값이 달라질 수 있으며, PER이 낮거나 높다는 사실만으로 저평가나 고평가를 단정할 수 없습니다. 적자 기업에서는 해석이 어렵습니다.
- `formula`: `주가 ÷ 주당순이익(EPS)`
- `example`: `null`
- `related_entry_ids`: `glossary:eps`

### 9.2 `glossary:pbr` — 주가순자산비율
- `definition`: 주가순자산비율은 현재 주가가 주당순자산의 몇 배 수준인지 나타내는 주가평가 지표입니다.
- `why_it_matters`: 시장에서 평가받는 주가와 회계상 순자산을 비교해 기업의 상대적인 평가 수준을 살펴볼 때 사용합니다.
- `caution`: 장부에 반영되지 않은 경쟁력이나 무형자산이 있을 수 있고 업종별 자산 구조도 다르므로, PBR만으로 기업가치를 판단하면 안 됩니다.
- `formula`: `주가 ÷ 주당순자산(BPS)`
- `example`: `null`
- `related_entry_ids`: `glossary:roe`

### 9.3 `glossary:roe` — 자기자본이익률
- `definition`: 자기자본이익률은 기업이 자기자본을 이용해 어느 정도의 이익을 냈는지 비율로 나타낸 지표입니다.
- `why_it_matters`: 주주가 제공한 자본을 기업이 얼마나 효율적으로 활용했는지 살펴보는 데 도움이 됩니다.
- `caution`: 평균 자기자본과 기말 자기자본 중 무엇을 사용했는지에 따라 값이 달라질 수 있습니다. 일회성 이익이나 자기자본 감소, 높은 부채로 ROE가 일시적으로 높아질 수도 있습니다.
- `formula`: `당기순이익 ÷ 평균 자기자본 × 100`
- `example`: `null`
- `related_entry_ids`: `glossary:net_income`

### 9.4 `glossary:eps` — 주당순이익
- `definition`: 주당순이익은 일정 기간의 보통주 귀속 이익을 가중평균 유통보통주식수로 나누어 주식 한 주당 이익을 나타낸 값입니다.
- `why_it_matters`: 기업의 이익을 주식 수 기준으로 비교하며 PER 계산과 주당 수익성 확인에 활용합니다.
- `caution`: 기본 EPS와 희석 EPS는 계산 범위가 다릅니다. 유상증자, 전환사채 전환, 주식분할처럼 주식 수에 영향을 주는 사건이 발생하면 EPS도 달라질 수 있습니다.
- `formula`: `보통주 귀속 당기순이익 ÷ 가중평균 유통보통주식수`
- `example`: `null`
- `related_entry_ids`: `glossary:net_income`, `glossary:rights_offering`, `glossary:convertible_bond`

### 9.5 `glossary:market_cap` — 시가총액
- `definition`: 시가총액은 현재 주가에 상장주식수를 곱해 계산한 주식시장에서의 회사 규모 지표입니다.
- `why_it_matters`: 상장기업의 시장 규모를 비교하거나 지수에서 차지하는 비중을 이해할 때 활용합니다.
- `caution`: 주가가 움직이면 시가총액도 변합니다. 시가총액은 현금과 부채까지 반영한 기업가치와 같은 개념이 아닙니다.
- `formula`: `현재 주가 × 상장주식수`
- `example`: `null`
- `related_entry_ids`: `glossary:rights_offering`

### 9.6 `glossary:revenue` — 매출액
- `definition`: 매출액은 기업이 주된 영업활동에서 상품이나 서비스를 제공해 얻은 대가를 일정 기간 동안 합산한 금액입니다.
- `why_it_matters`: 기업의 사업 규모와 성장 흐름을 파악하고 영업이익이나 영업이익률을 계산하는 출발점으로 사용합니다.
- `caution`: 업종과 거래 구조에 따라 매출을 인식하는 시점과 총액·순액 표시 방식이 다를 수 있으므로 회계정책을 함께 확인해야 합니다.
- `formula`: `null`
- `example`: `null`
- `related_entry_ids`: `glossary:operating_profit`, `glossary:operating_margin`

### 9.7 `glossary:operating_profit` — 영업이익
- `definition`: 영업이익은 매출액에서 매출원가와 판매비와관리비 등 주된 영업활동에 관련된 비용을 반영한 뒤 남은 이익입니다.
- `why_it_matters`: 금융손익이나 법인세 등 영업 외 요인의 영향을 분리해 본업의 수익성을 살펴볼 때 사용합니다.
- `caution`: 비용 분류와 회계정책에 따라 기업 간 비교가 달라질 수 있으며, 일시적인 비용 절감이나 비용 인식 시점도 함께 확인해야 합니다.
- `formula`: `null`
- `example`: `null`
- `related_entry_ids`: `glossary:revenue`, `glossary:operating_margin`

### 9.8 `glossary:net_income` — 당기순이익
- `definition`: 당기순이익은 일정 기간의 모든 수익과 비용, 금융손익, 영업외손익, 법인세 등을 반영한 뒤 남은 최종적인 회계상 이익입니다.
- `why_it_matters`: 기업이 해당 기간에 전체적으로 얼마의 이익을 남겼는지 확인하고 EPS나 ROE 같은 지표를 계산할 때 활용합니다.
- `caution`: 연결재무제표와 별도재무제표의 당기순이익은 범위가 다릅니다. 연결 기준에서는 전체 당기순이익과 지배기업 소유주에게 귀속되는 순이익도 구분해야 합니다.
- `formula`: `null`
- `example`: `null`
- `related_entry_ids`: `glossary:eps`, `glossary:roe`, `glossary:consolidated_financial_statements`, `glossary:separate_financial_statements`

### 9.9 `glossary:operating_margin` — 영업이익률
- `definition`: 영업이익률은 매출액 가운데 영업이익이 차지하는 비율을 나타내는 수익성 지표입니다.
- `why_it_matters`: 기업이 매출을 본업의 이익으로 전환하는 정도를 파악하고 기간별 또는 유사업체 간 수익성을 비교할 때 사용합니다.
- `caution`: 업종별 원가 구조가 다르고 일회성 비용이나 회계 분류가 영향을 줄 수 있으므로, 절대 수치만으로 기업의 우열을 판단하면 안 됩니다.
- `formula`: `영업이익 ÷ 매출액 × 100`
- `example`: `null`
- `related_entry_ids`: `glossary:revenue`, `glossary:operating_profit`

### 9.10 `glossary:rights_offering` — 유상증자
- `definition`: 유상증자는 기업이 자금을 조달하기 위해 새 주식을 발행하고 투자자로부터 그 대가를 받는 방식입니다.
- `why_it_matters`: 조달 목적과 발행 방식, 발행 규모는 기업의 재무구조와 기존 주주의 지분에 영향을 줄 수 있습니다.
- `caution`: 기존 주주가 새 주식 배정에 참여하지 않으면 지분율이나 주당 가치가 희석될 수 있습니다. 자금 사용 목적, 발행가액, 배정 방식과 일정도 함께 확인해야 합니다.
- `formula`: `null`
- `example`: 기존 주식이 100주인 회사가 새 주식 20주를 발행하면 총 주식 수가 늘어납니다. 기존 주주가 추가 취득하지 않으면 같은 보유 주식 수의 지분율은 낮아질 수 있습니다.
- `related_entry_ids`: `glossary:eps`, `glossary:market_cap`

### 9.11 `glossary:convertible_bond` — 전환사채
- `definition`: 전환사채는 정해진 조건에 따라 채권을 발행회사의 주식으로 전환할 수 있는 권리가 붙은 회사채입니다.
- `why_it_matters`: 기업에는 자금조달 수단이고 투자자에게는 이자와 주식 전환 가능성을 함께 제공할 수 있습니다.
- `caution`: 전환이 이루어지면 발행주식수가 늘어 기존 주주의 지분과 주당 지표가 희석될 수 있습니다. 전환가액, 조정 조건, 만기, 이자, 조기상환권과 매도청구권 조건을 확인해야 합니다.
- `formula`: `null`
- `example`: 전환가액이 10,000원인 전환사채의 전환권을 행사하면 전환 대상 금액을 기준으로 주식 수가 계산되어 채권이 주식으로 바뀔 수 있습니다.
- `related_entry_ids`: `glossary:eps`, `glossary:corporate_disclosure`

### 9.12 `glossary:corporate_disclosure` — 기업공시
- `definition`: 기업공시는 투자 판단에 중요한 회사 정보를 정해진 절차와 시스템을 통해 시장에 공개하는 것입니다.
- `why_it_matters`: 정기보고서, 주요 경영사항, 자금조달과 같은 사실을 확인해 기업 상황을 근거 중심으로 파악하는 데 사용합니다.
- `caution`: 최초 공시 뒤 정정이나 철회가 이어질 수 있으므로 접수일, 보고 기간, 정정 여부와 최신 유효 문서를 확인해야 합니다. 공시됐다는 사실이 투자 결과를 보장하지는 않습니다.
- `formula`: `null`
- `example`: 회사가 대규모 계약, 유상증자 결정 또는 분기보고서를 제출하면 투자자는 공시시스템에서 해당 문서와 정정 이력을 확인할 수 있습니다.
- `related_entry_ids`: `glossary:rights_offering`, `glossary:convertible_bond`

### 9.13 `glossary:consensus` — 시장 컨센서스
- `definition`: 시장 컨센서스는 여러 분석기관이나 애널리스트가 제시한 실적 전망치를 모아 산출한 대표적인 예상 수준입니다.
- `why_it_matters`: 실제 실적이 시장의 사전 기대와 비교해 어느 정도 차이가 있는지 살펴보는 기준으로 활용합니다.
- `caution`: 조사기관, 참여자 수, 집계 방식과 기준일에 따라 값이 달라지며 실제 실적을 보장하지 않습니다. 오래된 전망치와 최신 전망치를 섞어 비교하면 해석이 왜곡될 수 있습니다.
- `formula`: `null`
- `example`: 여러 증권사가 한 기업의 다음 분기 영업이익을 각각 전망했다면, 그 전망치의 평균이나 중앙값이 시장 컨센서스로 제시될 수 있습니다.
- `related_entry_ids`: `glossary:revenue`, `glossary:operating_profit`, `glossary:net_income`

### 9.14 `glossary:consolidated_financial_statements` — 연결재무제표
- `definition`: 연결재무제표는 지배기업과 종속기업을 하나의 경제적 실체로 보아 작성한 재무제표입니다.
- `why_it_matters`: 모회사뿐 아니라 지배하는 자회사까지 포함한 그룹 전체의 재무상태와 경영성과를 파악하는 데 사용합니다.
- `caution`: 그룹 내부 거래와 채권·채무는 연결 과정에서 제거될 수 있습니다. 별도재무제표 수치와 범위가 다르므로 두 기준의 수치를 직접 섞어 비교하면 안 됩니다.
- `formula`: `null`
- `example`: 모회사가 자회사를 지배한다면 연결재무제표에는 두 회사의 자산과 실적이 포함되고, 두 회사 사이의 내부 거래는 연결 조정 과정에서 제거될 수 있습니다.
- `related_entry_ids`: `glossary:separate_financial_statements`, `glossary:net_income`

### 9.15 `glossary:separate_financial_statements` — 별도재무제표
- `definition`: 별도재무제표는 지배기업이 종속기업의 자산과 실적을 항목별로 합치지 않고 자기 회사 자체를 중심으로 작성한 재무제표입니다.
- `why_it_matters`: 모회사 자체의 재무상태와 배당 재원, 자회사 투자 관계 등을 별도로 살펴보는 데 도움이 됩니다.
- `caution`: 자회사의 매출과 이익이 모회사 실적에 직접 합산되지 않으므로 그룹 전체 상황을 보려면 연결재무제표도 함께 확인해야 합니다.
- `formula`: `null`
- `example`: 모회사의 별도재무제표에서는 자회사 자체의 매출과 비용 대신 자회사에 대한 투자자산과 배당수익 등이 모회사 기준으로 표시될 수 있습니다.
- `related_entry_ids`: `glossary:consolidated_financial_statements`, `glossary:net_income`

## 10. Per-Entry Approval State
All entries in Section 9 are approved with these values.

| Field | Approved value |
|---|---|
| `version` | `1` |
| `language` | `ko` |
| `usage_review_status` | `approved` |
| `corpus_ingest_allowed` | `true` |
| `external_llm_processing_allowed` | `true` |
| `content_origin` | `user_authored` |
| `ingestion_version` | `glossary-ingest-m1-07-v1` |
| Content review | approved by adoption of this Task Card |
| Corpus creation | approved |
| External LLM processing | approved for Questock-authored text |

The implementation agent must not silently change an entry to `external_source` or `public_domain`.

## 11. Actual Coverage Evaluation Contract
M1-07B explicitly approves a narrow extension to `app.ingest.glossary`.

### Existing candidate helper remains unchanged
```python
calculate_glossary_coverage(raw_or_bundle) -> GlossaryCoverage
```
- Candidate and structural coverage only
- `actual_coverage_evaluated` remains `False`
- In-memory approved-like data is not the actual project corpus

### New helper
```python
evaluate_actual_glossary_coverage(path: str | Path) -> GlossaryCoverage
```

Required behavior:
1. Accept only project-relative `data/glossary.json`.
2. Do not expose absolute local paths in errors.
3. Load through `load_glossary_entries(path)`.
4. Validate through `validate_glossary_corpus(bundle, mode="corpus")`.
5. Require exact wrapper identity and exact Section 8 entry ID equality.
6. Require exactly 15 entries.
7. Return:
   - `total_entries == 15`
   - `approved_actual_entries == 15`
   - `synthetic_entries == 0`
   - `pending_entries == 0`
   - `rejected_entries == 0`
   - `minimum_required == 15`
   - `actual_coverage_evaluated is True`
   - `meets_minimum is True`

The helper must not mark a temporary file, synthetic fixture, review corpus, arbitrary approved in-memory object, differently identified corpus, missing-entry corpus, or extra-entry corpus as actual coverage.

The expected entry IDs may be stored as a private immutable constant. Do not expose them as user-editable runtime configuration in M1-07B.

## 12. Full Validation Plan
### Corpus identity
- Path is `data/glossary.json`.
- Wrapper identity exactly matches Section 6.
- Exactly 15 entries.
- Exact `EXPECTED_ENTRY_IDS` equality.
- No extra or missing entry.

### Every-entry contract
For every entry verify:
- approved, corpus enabled, external LLM enabled, user authored
- nonblank source and permission notes
- external LLM permission explicitly covered
- source URL and asset ID are null
- fixed ingestion version
- nonblank definition/why/caution
- fixed overclaim blocklist phrases absent

### Full lookup
For every canonical term:
- `found`
- `matched_by == "canonical"`
- correct entry ID

For every alias:
- `found`
- `matched_by == "alias"`
- stored alias returned as `matched_term`
- correct entry ID

Representative-only lookup tests are insufficient.

### Full locator
For every entry:
- definition, why_it_matters, and caution locators succeed
- corpus ID, entry ID, version, source type, provider, and ingestion version are preserved

For formula/example:
- present field locator succeeds
- absent field locator raises typed validation error

### Collision and related IDs
- no normalized canonical/canonical, canonical/alias, or alias/alias collision
- no self, duplicate, or unresolved related ID

### Actual versus candidate coverage
```python
candidate = calculate_glossary_coverage(bundle)
assert candidate.actual_coverage_evaluated is False
assert candidate.meets_minimum is False

actual = evaluate_actual_glossary_coverage(Path("data/glossary.json"))
assert actual.approved_actual_entries == 15
assert actual.actual_coverage_evaluated is True
assert actual.meets_minimum is True
```

Negative actual-evaluation tests:
- synthetic fixture path
- temporary approved-corpus file
- wrong corpus ID/type/language
- missing entry
- extra entry
- fewer than 15 entries
- wrong permission state

### Determinism and immutability
- repeated JSON loads produce identical lookup results
- entry ID and corpus ID remain fixed
- unrelated input ordering does not change term identity or lookup mapping
- caller mutation cannot change a built index
- actual evaluator result is deterministic for unchanged file

## 13. Content Review Checklist
- PER/PBR: denominator and date basis; low/high does not prove under/overvaluation; sector context matters.
- ROE: average versus closing equity; one-time profit, equity reduction, and leverage can distort.
- EPS: basic versus diluted; financing and share-count changes matter.
- Revenue: recognition timing and gross/net presentation can differ.
- Operating profit: expense classification and accounting policy can affect comparison.
- Net income: consolidated versus separate; total versus owners-of-parent attribution.
- Operating margin: industry cost structure and temporary items matter.
- Rights offering: issue method, price, use of funds, schedule, and dilution.
- Convertible bond: conversion price, reset, interest, maturity, put/call, and dilution.
- Disclosure: correction/withdrawal, receipt/reporting period, latest valid document; no performance guarantee.
- Consensus: participant set, method, reference date; not actual performance.
- Consolidated statements: subsidiaries included, intragroup items eliminated, scope differs from separate statements.
- Separate statements: parent basis, subsidiaries not directly combined, do not mix with consolidated values without labels.

### Implementation Fact-Check References
- KRX KIND value-up investment indicator screen: `https://kind.krx.co.kr/valueup/invstindicsectors.do?method=valueupInvstIndicRankIndMain`
- KRX KIND value-up index screen: `https://kind.krx.co.kr/valueup/idx.do?method=valueupIdxMain`
- DART disclosure guide, major report / rights offering / convertible-bond submission guidance: `https://dart.fss.or.kr/info/main.do?menu=220`
- DART disclosure guide, periodic disclosure purpose and reporting scope: `https://dart.fss.or.kr/info/main.do?menu=210`
- KASB accounting standards list / K-IFRS access: `https://www.kasb.or.kr/fe/accstd/NR_list.do?divCd=01&sortCd=K-IFRS`
- KASB enactment and amendment status: `https://www.kasb.or.kr/front/board/List2006.do`

These references were used only for factual review of terms, formulas, and cautions. `data/glossary.json` remains Questock user-authored content and does not copy, translate, or closely paraphrase external wording.

## 14. Verification Commands
### Targeted
```powershell
$env:PYTHONPATH = ".test_deps;."; python -m pytest tests/unit/test_glossary_ingest.py -q
```

### Regression
```powershell
$env:PYTHONPATH = ".test_deps;."; python -m pytest tests/unit/test_core_models.py tests/unit/test_status_contracts.py tests/unit/test_security_resolver.py tests/unit/test_provider_base.py tests/unit/test_config.py tests/unit/test_news_provider.py tests/unit/test_disclosure_provider.py tests/unit/test_report_ingest.py tests/unit/test_glossary_ingest.py -q
```

### Smoke
```powershell
$env:PYTHONPATH = ".test_deps;."; python -c "from pathlib import Path; from app.ingest.glossary import load_glossary_entries, build_glossary_index, lookup_glossary_entry, evaluate_actual_glossary_coverage; bundle=load_glossary_entries(Path('data/glossary.json')); index=build_glossary_index(bundle, mode='corpus'); result=lookup_glossary_entry(index, 'PER'); coverage=evaluate_actual_glossary_coverage(Path('data/glossary.json')); print(result.status, coverage.meets_minimum)"
```

Expected smoke output:
```text
found True
```

Record exact commands, exit codes, passed counts, and smoke output. If an environment error occurs first, record both the first failure and successful rerun.

## 15. Completion Criteria
- [x] `data/glossary.json` exists.
- [x] Wrapper identity matches Section 6.
- [x] Exact 15-entry ID set matches Section 8.
- [x] Canonical terms and aliases match Section 8.
- [x] Content meaning matches Section 9.
- [x] Every entry is approved, corpus-enabled, external-LLM-enabled, and user-authored.
- [x] Source and permission notes are nonblank.
- [x] No copied, translated, or closely paraphrased external wording is present.
- [x] Full canonical and alias lookup passes.
- [x] Required and optional locator tests pass.
- [x] Related-entry integrity passes.
- [x] Candidate coverage remains unevaluated.
- [x] Actual coverage is evaluated and meets the 15-entry minimum.
- [x] Targeted and regression tests pass.
- [x] Actual-corpus smoke passes.
- [x] Actual results are written back to this Task Card.
- [x] GitHub CI and commit/push states remain accurate.

## 16. Stop Conditions
Stop and report instead of guessing when:
- official factual bases cannot be reconciled
- an entry would require copied or closely paraphrased wording
- meaning, formula, caution, or permission would materially differ from Section 9
- an approved alias causes a normalized collision
- an entry or corpus ID must change
- actual coverage would need a path other than `data/glossary.json`
- implementation requires core, Provider, resolver, retrieval, API, UI, or LLM changes
- existing M1-07A regression fails for an unrelated reason
- terms beyond the approved 15 become necessary
- external LLM permission cannot remain true for an approved Questock-authored entry

Do not silently omit a failed entry to keep the count at 15.

## 17. Git Boundary
This Task Card approves:
- plan replacement
- independent content drafting according to Section 9
- `data/glossary.json` creation
- M1-07B-only actual coverage helper
- test additions and test execution
- Task Card result logging

This Task Card does not approve:
- commit, push, PR, merge, deployment
- live API invocation
- retrieval or LLM invocation
- M2 work

Commit and push require separate explicit Human Owner approval after review of the working tree and test results.

## 18. Status
- Task Card created: `2026-07-22`
- Decision sync: `2026-07-22`
- Planning base commit: `2aa991c6674d9947548432aa520b6c03f9b6065d`
- Human Owner term-set approval: `APPROVED`
- Human Owner canonical/alias approval: `APPROVED`
- Human Owner content policy approval: `APPROVED`
- Human Owner corpus ingest approval: `APPROVED`
- Human Owner external LLM processing approval: `APPROVED`
- Human Owner formula/example strategy approval: `APPROVED`
- Entry content approval: effective when this exact revised Task Card is adopted into the project
- M1-07B implementation approval: `APPROVED`
- M1-07B status: `IMPLEMENTED - USER REVIEW PENDING`
- Actual glossary corpus: `PASS`
- Actual coverage 15+: `PASS`
- Targeted tests: `PASS - 163 passed`
- Regression tests: `PASS - 594 passed`
- Import/actual-corpus smoke: `PASS - found True`
- GitHub CI: `NOT_RUN`
- Independent pytest rerun: `NOT_RUN`
- Commit/push: `NOT_RUN`

### 18.1 Implementation Result Log
- Initial targeted command: `python -m pytest tests/unit/test_glossary_ingest.py -q`
  - exit code: `1`
  - output: `No module named pytest`
- `.test_deps` targeted command: `$env:PYTHONPATH = ".test_deps;."; python -m pytest tests/unit/test_glossary_ingest.py -q`
  - exit code: `1`
  - output: `No module named pytest.__main__; 'pytest' is a package and cannot be directly executed`
- `.venv` targeted command: `.venv\Scripts\python.exe -m pytest tests/unit/test_glossary_ingest.py -q`
  - exit code: `1`
  - output: `No module named pytest`
- `.deps` targeted first command: `$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_glossary_ingest.py -q`
  - exit code: `1`
  - output: `PermissionError: [Errno 13] Permission denied: 'C:\\Users\\USER\\Questock\\.deps\\pytest\\__init__.py'`
- `.deps` targeted rerun command: `$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_glossary_ingest.py -q`
  - exit code: `0`
  - passed count: `163 passed`
  - output: `163 passed in 0.29s`
- Regression command: `$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_core_models.py tests/unit/test_status_contracts.py tests/unit/test_security_resolver.py tests/unit/test_provider_base.py tests/unit/test_config.py tests/unit/test_news_provider.py tests/unit/test_disclosure_provider.py tests/unit/test_report_ingest.py tests/unit/test_glossary_ingest.py -q`
  - exit code: `0`
  - passed count: `594 passed`
  - output: `594 passed in 0.76s`
- Smoke command: `$env:PYTHONPATH = ".deps;."; python -c "from pathlib import Path; from app.ingest.glossary import load_glossary_entries, build_glossary_index, lookup_glossary_entry, evaluate_actual_glossary_coverage; bundle=load_glossary_entries(Path('data/glossary.json')); index=build_glossary_index(bundle, mode='corpus'); result=lookup_glossary_entry(index, 'PER'); coverage=evaluate_actual_glossary_coverage(Path('data/glossary.json')); print(result.status, coverage.meets_minimum)"`
  - exit code: `0`
  - output: `found True`
- Compile check: `python -m compileall app tests -q`
  - exit code: `0`
- GitHub CI: `NOT_RUN`
- Independent pytest rerun: `NOT_RUN`
- Commit/push: `NOT_RUN`
