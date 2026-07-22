import copy
import json
import re
import traceback
from dataclasses import replace
from pathlib import Path

import pytest

import app.ingest.glossary as glossary_module
from app.ingest.glossary import (
    GLOSSARY_INGESTION_VERSION,
    GLOSSARY_SOURCE_TYPE,
    MANUAL_GLOSSARY_PROVIDER,
    GlossaryCorpusBundle,
    GlossaryCorpusValidationError,
    GlossaryEntryValidationError,
    GlossaryIndex,
    GlossaryIngestValidationError,
    GlossaryLookupValidationError,
    build_glossary_index,
    build_glossary_locator,
    calculate_glossary_coverage,
    evaluate_actual_glossary_coverage,
    load_glossary_entries,
    lookup_glossary_entry,
    validate_glossary_corpus,
    validate_glossary_entry,
)

FIXTURE_PATH = Path("tests/fixtures/glossary/glossary_synthetic.json")
DATA_PATH = Path("data/glossary.json")
COMMON_SOURCE_NOTE = (
    "Questock 프로젝트가 M1-07B Task Card의 항목별 fact-check matrix에 기록된 공식 자료로 "
    "사실·용어·주의점을 확인한 뒤 외부 문장을 복사·번역·근접 변형하지 않고 독립적으로 작성한 설명입니다."
)
COMMON_PERMISSION_NOTE = "Human Owner가 Questock 작성 문구의 glossary corpus 적재와 외부 LLM을 통한 설명 재구성 처리를 승인했습니다."
EXPECTED_ACTUAL_ENTRY_IDS = {
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
EXPECTED_ACTUAL_ENTRY_CONTENT = {
    "glossary:per": {
        "canonical_term": "주가수익비율",
        "aliases": ("PER", "주가 수익 비율", "주가이익비율", "주가 이익 비율"),
        "category": "valuation",
        "definition": "주가수익비율은 현재 주가가 주당순이익의 몇 배 수준인지 나타내는 주가평가 지표입니다.",
        "why_it_matters": "기업의 주가 수준을 이익과 비교하고 비슷한 업종이나 기업 사이의 상대적인 평가 수준을 살펴볼 때 사용합니다.",
        "caution": "사용한 이익의 기간과 예상치 여부에 따라 값이 달라질 수 있으며, PER이 낮거나 높다는 사실만으로 저평가나 고평가를 단정할 수 없습니다. 적자 기업에서는 해석이 어렵습니다.",
        "formula": "주가 ÷ 주당순이익(EPS)",
        "example": None,
        "related_entry_ids": ("glossary:eps",),
    },
    "glossary:pbr": {
        "canonical_term": "주가순자산비율",
        "aliases": ("PBR", "주가 순자산 비율"),
        "category": "valuation",
        "definition": "주가순자산비율은 현재 주가가 주당순자산의 몇 배 수준인지 나타내는 주가평가 지표입니다.",
        "why_it_matters": "시장에서 평가받는 주가와 회계상 순자산을 비교해 기업의 상대적인 평가 수준을 살펴볼 때 사용합니다.",
        "caution": "장부에 반영되지 않은 경쟁력이나 무형자산이 있을 수 있고 업종별 자산 구조도 다르므로, PBR만으로 기업가치를 판단하면 안 됩니다.",
        "formula": "주가 ÷ 주당순자산(BPS)",
        "example": None,
        "related_entry_ids": ("glossary:roe",),
    },
    "glossary:roe": {
        "canonical_term": "자기자본이익률",
        "aliases": ("ROE", "자기자본 이익률", "자기자본수익률", "자기자본 수익률"),
        "category": "profitability",
        "definition": "자기자본이익률은 기업이 자기자본을 이용해 어느 정도의 이익을 냈는지 비율로 나타낸 지표입니다.",
        "why_it_matters": "주주가 제공한 자본을 기업이 얼마나 효율적으로 활용했는지 살펴보는 데 도움이 됩니다.",
        "caution": "평균 자기자본과 기말 자기자본 중 무엇을 사용했는지에 따라 값이 달라질 수 있습니다. 일회성 이익이나 자기자본 감소, 높은 부채로 ROE가 일시적으로 높아질 수도 있습니다.",
        "formula": "당기순이익 ÷ 평균 자기자본 × 100",
        "example": None,
        "related_entry_ids": ("glossary:net_income",),
    },
    "glossary:eps": {
        "canonical_term": "주당순이익",
        "aliases": ("EPS", "주당 순이익"),
        "category": "profitability",
        "definition": "주당순이익은 일정 기간의 보통주 귀속 이익을 가중평균 유통보통주식수로 나누어 주식 한 주당 이익을 나타낸 값입니다.",
        "why_it_matters": "기업의 이익을 주식 수 기준으로 비교하며 PER 계산과 주당 수익성 확인에 활용합니다.",
        "caution": "기본 EPS와 희석 EPS는 계산 범위가 다릅니다. 유상증자, 전환사채 전환, 주식분할처럼 주식 수에 영향을 주는 사건이 발생하면 EPS도 달라질 수 있습니다.",
        "formula": "보통주 귀속 당기순이익 ÷ 가중평균 유통보통주식수",
        "example": None,
        "related_entry_ids": ("glossary:net_income", "glossary:rights_offering", "glossary:convertible_bond"),
    },
    "glossary:market_cap": {
        "canonical_term": "시가총액",
        "aliases": ("시총",),
        "category": "market_value",
        "definition": "시가총액은 현재 주가에 상장주식수를 곱해 계산한 주식시장에서의 회사 규모 지표입니다.",
        "why_it_matters": "상장기업의 시장 규모를 비교하거나 지수에서 차지하는 비중을 이해할 때 활용합니다.",
        "caution": "주가가 움직이면 시가총액도 변합니다. 시가총액은 현금과 부채까지 반영한 기업가치와 같은 개념이 아닙니다.",
        "formula": "현재 주가 × 상장주식수",
        "example": None,
        "related_entry_ids": ("glossary:rights_offering",),
    },
    "glossary:revenue": {
        "canonical_term": "매출액",
        "aliases": ("매출",),
        "category": "performance",
        "definition": "매출액은 기업이 주된 영업활동에서 상품이나 서비스를 제공해 얻은 대가를 일정 기간 동안 합산한 금액입니다.",
        "why_it_matters": "기업의 사업 규모와 성장 흐름을 파악하고 영업이익이나 영업이익률을 계산하는 출발점으로 사용합니다.",
        "caution": "업종과 거래 구조에 따라 매출을 인식하는 시점과 총액·순액 표시 방식이 다를 수 있으므로 회계정책을 함께 확인해야 합니다.",
        "formula": None,
        "example": None,
        "related_entry_ids": ("glossary:operating_profit", "glossary:operating_margin"),
    },
    "glossary:operating_profit": {
        "canonical_term": "영업이익",
        "aliases": ("영업 이익",),
        "category": "performance",
        "definition": "영업이익은 매출액에서 매출원가와 판매비와관리비 등 주된 영업활동에 관련된 비용을 반영한 뒤 남은 이익입니다.",
        "why_it_matters": "금융손익이나 법인세 등 영업 외 요인의 영향을 분리해 본업의 수익성을 살펴볼 때 사용합니다.",
        "caution": "비용 분류와 회계정책에 따라 기업 간 비교가 달라질 수 있으며, 일시적인 비용 절감이나 비용 인식 시점도 함께 확인해야 합니다.",
        "formula": None,
        "example": None,
        "related_entry_ids": ("glossary:revenue", "glossary:operating_margin"),
    },
    "glossary:net_income": {
        "canonical_term": "당기순이익",
        "aliases": ("순이익", "당기 순이익"),
        "category": "performance",
        "definition": "당기순이익은 일정 기간의 모든 수익과 비용, 금융손익, 영업외손익, 법인세 등을 반영한 뒤 남은 최종적인 회계상 이익입니다.",
        "why_it_matters": "기업이 해당 기간에 전체적으로 얼마의 이익을 남겼는지 확인하고 EPS나 ROE 같은 지표를 계산할 때 활용합니다.",
        "caution": "연결재무제표와 별도재무제표의 당기순이익은 범위가 다릅니다. 연결 기준에서는 전체 당기순이익과 지배기업 소유주에게 귀속되는 순이익도 구분해야 합니다.",
        "formula": None,
        "example": None,
        "related_entry_ids": (
            "glossary:eps",
            "glossary:roe",
            "glossary:consolidated_financial_statements",
            "glossary:separate_financial_statements",
        ),
    },
    "glossary:operating_margin": {
        "canonical_term": "영업이익률",
        "aliases": ("영업 이익률", "영업마진", "영업 마진"),
        "category": "profitability",
        "definition": "영업이익률은 매출액 가운데 영업이익이 차지하는 비율을 나타내는 수익성 지표입니다.",
        "why_it_matters": "기업이 매출을 본업의 이익으로 전환하는 정도를 파악하고 기간별 또는 유사업체 간 수익성을 비교할 때 사용합니다.",
        "caution": "업종별 원가 구조가 다르고 일회성 비용이나 회계 분류가 영향을 줄 수 있으므로, 절대 수치만으로 기업의 우열을 판단하면 안 됩니다.",
        "formula": "영업이익 ÷ 매출액 × 100",
        "example": None,
        "related_entry_ids": ("glossary:revenue", "glossary:operating_profit"),
    },
    "glossary:rights_offering": {
        "canonical_term": "유상증자",
        "aliases": ("유상 증자", "유증"),
        "category": "financing",
        "definition": "유상증자는 기업이 자금을 조달하기 위해 새 주식을 발행하고 투자자로부터 그 대가를 받는 방식입니다.",
        "why_it_matters": "조달 목적과 발행 방식, 발행 규모는 기업의 재무구조와 기존 주주의 지분에 영향을 줄 수 있습니다.",
        "caution": "기존 주주가 새 주식 배정에 참여하지 않으면 지분율이나 주당 가치가 희석될 수 있습니다. 자금 사용 목적, 발행가액, 배정 방식과 일정도 함께 확인해야 합니다.",
        "formula": None,
        "example": "기존 주식이 100주인 회사가 새 주식 20주를 발행하면 총 주식 수가 늘어납니다. 기존 주주가 추가 취득하지 않으면 같은 보유 주식 수의 지분율은 낮아질 수 있습니다.",
        "related_entry_ids": ("glossary:eps", "glossary:market_cap"),
    },
    "glossary:convertible_bond": {
        "canonical_term": "전환사채",
        "aliases": ("CB", "전환 사채"),
        "category": "financing",
        "definition": "전환사채는 정해진 조건에 따라 채권을 발행회사의 주식으로 전환할 수 있는 권리가 붙은 회사채입니다.",
        "why_it_matters": "기업에는 자금조달 수단이 되고, 투자자에게는 이자 조건과 주식 전환 가능성을 함께 제공할 수 있습니다.",
        "caution": "전환이 이루어지면 발행주식수가 늘어 기존 주주의 지분과 주당 지표가 희석될 수 있습니다. 전환가액, 조정 조건, 만기, 이자, 조기상환권과 매도청구권 조건을 확인해야 합니다.",
        "formula": None,
        "example": "전환가액이 10,000원인 전환사채의 전환권을 행사하면 전환 대상 금액을 기준으로 주식 수가 계산되어 채권이 주식으로 바뀔 수 있습니다.",
        "related_entry_ids": ("glossary:eps", "glossary:corporate_disclosure"),
    },
    "glossary:corporate_disclosure": {
        "canonical_term": "기업공시",
        "aliases": ("공시", "기업 공시"),
        "category": "disclosure",
        "definition": "기업공시는 투자 판단에 중요한 회사 정보를 정해진 절차와 시스템을 통해 시장에 공개하는 것입니다.",
        "why_it_matters": "정기보고서, 주요 경영사항, 자금조달과 같은 사실을 확인해 기업 상황을 근거 중심으로 파악하는 데 사용합니다.",
        "caution": "최초 공시 뒤 정정이나 철회가 이어질 수 있으므로 접수일, 보고 기간, 정정 여부와 최신 유효 문서를 확인해야 합니다. 공시됐다는 사실이 투자 결과를 보장하지는 않습니다.",
        "formula": None,
        "example": "회사가 대규모 계약, 유상증자 결정 또는 분기보고서를 제출하면 투자자는 공시시스템에서 해당 문서와 정정 이력을 확인할 수 있습니다.",
        "related_entry_ids": ("glossary:rights_offering", "glossary:convertible_bond"),
    },
    "glossary:consensus": {
        "canonical_term": "시장 컨센서스",
        "aliases": ("컨센서스", "증권사 컨센서스", "시장예상치", "시장 예상치"),
        "category": "forecast",
        "definition": "시장 컨센서스는 여러 분석기관이나 애널리스트가 제시한 실적 전망치를 모아 산출한 대표적인 예상 수준입니다.",
        "why_it_matters": "실제 실적이 시장의 사전 기대와 비교해 어느 정도 차이가 있는지 살펴보는 기준으로 활용합니다.",
        "caution": "조사기관, 참여자 수, 집계 방식과 기준일에 따라 값이 달라지며 실제 실적을 보장하지 않습니다. 오래된 전망치와 최신 전망치를 섞어 비교하면 해석이 왜곡될 수 있습니다.",
        "formula": None,
        "example": "여러 증권사가 한 기업의 다음 분기 영업이익을 각각 전망했다면, 그 전망치의 평균이나 중앙값이 시장 컨센서스로 제시될 수 있습니다.",
        "related_entry_ids": ("glossary:revenue", "glossary:operating_profit", "glossary:net_income"),
    },
    "glossary:consolidated_financial_statements": {
        "canonical_term": "연결재무제표",
        "aliases": ("연결 재무제표", "연결재무"),
        "category": "financial_statements",
        "definition": "연결재무제표는 지배기업과 종속기업을 하나의 경제적 실체로 보아 작성한 재무제표입니다.",
        "why_it_matters": "모회사뿐 아니라 지배하는 자회사까지 포함한 그룹 전체의 재무상태와 경영성과를 파악하는 데 사용합니다.",
        "caution": "그룹 내부 거래와 채권·채무는 연결 과정에서 제거될 수 있습니다. 별도재무제표 수치와 범위가 다르므로 두 기준의 수치를 직접 섞어 비교하면 안 됩니다.",
        "formula": None,
        "example": "모회사가 자회사를 지배한다면 연결재무제표에는 두 회사의 자산과 실적이 포함되고, 두 회사 사이의 내부 거래는 연결 조정 과정에서 제거될 수 있습니다.",
        "related_entry_ids": ("glossary:separate_financial_statements", "glossary:net_income"),
    },
    "glossary:separate_financial_statements": {
        "canonical_term": "별도재무제표",
        "aliases": ("별도 재무제표", "별도재무"),
        "category": "financial_statements",
        "definition": "별도재무제표는 지배기업이 종속기업의 자산과 실적을 항목별로 합치지 않고 자기 회사 자체를 중심으로 작성한 재무제표입니다.",
        "why_it_matters": "모회사 자체의 재무상태와 배당 재원, 자회사 투자 관계 등을 별도로 살펴보는 데 도움이 됩니다.",
        "caution": "자회사의 매출과 이익이 모회사 실적에 직접 합산되지 않으므로 그룹 전체 상황을 보려면 연결재무제표도 함께 확인해야 합니다.",
        "formula": None,
        "example": "모회사의 별도재무제표에서는 자회사 자체의 매출과 비용 대신 자회사에 대한 투자자산과 배당수익 등이 모회사 기준으로 표시될 수 있습니다.",
        "related_entry_ids": ("glossary:consolidated_financial_statements", "glossary:net_income"),
    },
}


def corpus_data(**updates):
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    data.update(updates)
    return data


def entry_data(index=0, **updates):
    raw = json.loads(json.dumps(corpus_data()["entries"][index]))
    raw.update(updates)
    return raw


def approved_entry(number=1, **updates):
    raw = entry_data(
        0,
        entry_id=f"glossary:approved_{number}",
        canonical_term=f"승인용어{number}",
        aliases=[f"approved alias {number}"],
        usage_review_status="approved",
        corpus_ingest_allowed=True,
        external_llm_processing_allowed=False,
        content_origin="user_authored",
        source_note="User authored reviewed glossary text.",
        permission_note="User approved this glossary entry for corpus ingest.",
        source_url=None,
        source_asset_id=None,
        related_entry_ids=[],
    )
    raw.update(updates)
    return raw


def approved_ascii_entry(number=1, **updates):
    raw = approved_entry(
        number,
        canonical_term=f"approved term {number}",
        aliases=[f"approved alias {number}", f"approved alt {number}"],
    )
    raw.update(updates)
    return raw


def review_entry(status, number=1, **updates):
    raw = approved_entry(number, usage_review_status=status, corpus_ingest_allowed=status == "approved")
    raw.update(updates)
    return raw


def approved_corpus(entries=None, **updates):
    data = {
        "schema_version": 1,
        "corpus_type": "approved_corpus",
        "corpus_id": "glossary-approved-memory-v1",
        "language": "ko",
        "entries": entries or [approved_entry(1)],
    }
    data.update(updates)
    return data


def review_corpus(entries=None, **updates):
    data = {
        "schema_version": 1,
        "corpus_type": "review_corpus",
        "corpus_id": "glossary-review-memory-v1",
        "language": "ko",
        "entries": entries
        or [
            review_entry("pending", 1, corpus_ingest_allowed=False),
            review_entry("approved", 2),
            review_entry("rejected", 3, corpus_ingest_allowed=False),
        ],
    }
    data.update(updates)
    return data


def test_load_synthetic_fixture_index_lookup_locator_and_coverage():
    bundle = load_glossary_entries(FIXTURE_PATH)
    entries = validate_glossary_corpus(bundle, mode="synthetic_unit")
    index = build_glossary_index(bundle, mode="synthetic_unit")

    canonical = lookup_glossary_entry(index, "알파비율")
    alias = lookup_glossary_entry(index, " alpha   ratio ")
    locator = build_glossary_locator(bundle, entries[0], "definition")
    coverage = calculate_glossary_coverage(bundle)

    assert bundle.schema_version == 1
    assert bundle.corpus_type == "synthetic_unit"
    assert len(entries) == 3
    assert canonical.status == "found"
    assert canonical.matched_by == "canonical"
    assert canonical.matched_term == "알파비율"
    assert alias.status == "found"
    assert alias.matched_by == "alias"
    assert alias.matched_term == "ALPHA Ratio"
    assert locator.corpus_id == "glossary-synthetic-v1"
    assert locator.source_type == GLOSSARY_SOURCE_TYPE
    assert locator.provider == MANUAL_GLOSSARY_PROVIDER
    assert coverage.total_entries == 3
    assert coverage.synthetic_entries == 3
    assert coverage.approved_actual_entries == 0
    assert coverage.minimum_required == 15
    assert coverage.meets_minimum is False
    assert coverage.actual_coverage_evaluated is False


@pytest.mark.parametrize("field", ["schema_version", "corpus_type", "corpus_id", "language", "entries"])
def test_wrapper_missing_required_field(field):
    raw = corpus_data()
    raw.pop(field)

    with pytest.raises(GlossaryCorpusValidationError):
        validate_glossary_corpus(raw, mode="load")


@pytest.mark.parametrize("schema_version", [True, "1", 0, 2])
def test_wrapper_schema_version_boundaries(schema_version):
    with pytest.raises(GlossaryCorpusValidationError):
        validate_glossary_corpus(corpus_data(schema_version=schema_version), mode="load")


@pytest.mark.parametrize(
    "updates",
    [
        {"extra": "nope"},
        {"corpus_type": "fixture_type"},
        {"language": "en"},
        {"entries": []},
    ],
)
def test_wrapper_extra_unsupported_and_empty_boundaries(updates):
    with pytest.raises(GlossaryCorpusValidationError):
        validate_glossary_corpus(corpus_data(**updates), mode="load")


def test_wrapper_and_entry_language_mismatch_fails():
    raw = corpus_data()
    raw["entries"][0]["language"] = "en"

    with pytest.raises(GlossaryEntryValidationError):
        validate_glossary_corpus(raw, mode="load")


def test_synthetic_wrapper_rejects_approved_entry_mix():
    raw = corpus_data()
    raw["entries"][0] = approved_entry(1)

    with pytest.raises(GlossaryCorpusValidationError):
        validate_glossary_corpus(raw, mode="synthetic_unit")


def test_review_corpus_loads_but_production_index_fails():
    raw = review_corpus()

    entries = validate_glossary_corpus(raw, mode="load")

    assert [entry.usage_review_status for entry in entries] == ["pending", "approved", "rejected"]
    with pytest.raises(GlossaryCorpusValidationError):
        build_glossary_index(raw, mode="corpus")


def test_approved_corpus_contract_builds_index_but_is_not_actual_coverage_completion():
    raw = approved_corpus(entries=[approved_entry(number) for number in range(1, 16)])

    entries = validate_glossary_corpus(raw, mode="corpus")
    index = build_glossary_index(raw, mode="corpus")
    coverage = calculate_glossary_coverage(raw)

    assert len(entries) == 15
    assert lookup_glossary_entry(index, "승인용어1").status == "found"
    assert coverage.approved_actual_entries == 15
    assert coverage.actual_coverage_evaluated is False
    assert coverage.meets_minimum is False


def test_actual_glossary_corpus_identity_and_coverage():
    bundle = load_glossary_entries(DATA_PATH)
    entries = validate_glossary_corpus(bundle, mode="corpus")
    entries_by_id = {entry.entry_id: entry for entry in entries}
    candidate_coverage = calculate_glossary_coverage(bundle)
    actual_coverage = evaluate_actual_glossary_coverage(DATA_PATH)

    assert bundle.schema_version == 1
    assert bundle.corpus_type == "approved_corpus"
    assert bundle.corpus_id == "glossary-approved-v1"
    assert bundle.language == "ko"
    assert len(entries) == 15
    assert {entry.entry_id for entry in entries} == EXPECTED_ACTUAL_ENTRY_IDS
    assert all(entry.usage_review_status == "approved" for entry in entries)
    assert all(entry.corpus_ingest_allowed for entry in entries)
    assert all(entry.external_llm_processing_allowed for entry in entries)
    assert all(entry.content_origin == "user_authored" for entry in entries)
    assert all(entry.source_note == COMMON_SOURCE_NOTE for entry in entries)
    assert all(entry.permission_note == COMMON_PERMISSION_NOTE for entry in entries)
    assert all(entry.source_url is None and entry.source_asset_id is None for entry in entries)
    for entry_id, expected in EXPECTED_ACTUAL_ENTRY_CONTENT.items():
        entry = entries_by_id[entry_id]
        for field, expected_value in expected.items():
            assert getattr(entry, field) == expected_value
    assert (
        entries_by_id["glossary:convertible_bond"].why_it_matters
        == "기업에는 자금조달 수단이 되고, 투자자에게는 이자 조건과 주식 전환 가능성을 함께 제공할 수 있습니다."
    )
    assert (
        entries_by_id["glossary:eps"].definition
        == "주당순이익은 일정 기간의 보통주 귀속 이익을 가중평균 유통보통주식수로 나누어 주식 한 주당 이익을 나타낸 값입니다."
    )
    assert candidate_coverage.approved_actual_entries == 15
    assert candidate_coverage.actual_coverage_evaluated is False
    assert candidate_coverage.meets_minimum is False
    assert actual_coverage.total_entries == 15
    assert actual_coverage.approved_actual_entries == 15
    assert actual_coverage.synthetic_entries == 0
    assert actual_coverage.pending_entries == 0
    assert actual_coverage.rejected_entries == 0
    assert actual_coverage.minimum_required == 15
    assert actual_coverage.actual_coverage_evaluated is True
    assert actual_coverage.meets_minimum is True


def test_actual_glossary_snapshot_fingerprint_matches_approved_digest():
    bundle = load_glossary_entries(DATA_PATH)
    calculated = glossary_module._calculate_approved_glossary_snapshot_sha256(bundle.entries)

    assert re.fullmatch(r"[0-9a-f]{64}", glossary_module._APPROVED_ACTUAL_GLOSSARY_SNAPSHOT_SHA256)
    assert calculated == glossary_module._APPROVED_ACTUAL_GLOSSARY_SNAPSHOT_SHA256


def test_actual_glossary_full_lookup_and_required_locators():
    bundle = load_glossary_entries(DATA_PATH)
    index = build_glossary_index(bundle, mode="corpus")

    for entry in bundle.entries:
        canonical = lookup_glossary_entry(index, entry.canonical_term)
        assert canonical.status == "found"
        assert canonical.matched_by == "canonical"
        assert canonical.entry == entry
        for alias in entry.aliases:
            alias_result = lookup_glossary_entry(index, alias)
            assert alias_result.status == "found"
            assert alias_result.matched_by == "alias"
            assert alias_result.entry == entry
        for section in ("definition", "why_it_matters", "caution"):
            locator = build_glossary_locator(bundle, entry, section)
            assert locator.corpus_id == "glossary-approved-v1"
            assert locator.entry_id == entry.entry_id
            assert locator.source_type == GLOSSARY_SOURCE_TYPE
            assert locator.provider == MANUAL_GLOSSARY_PROVIDER
            assert locator.source_url is None
            assert locator.source_asset_id is None
        for section in ("formula", "example"):
            if getattr(entry, section) is None:
                with pytest.raises(GlossaryCorpusValidationError):
                    build_glossary_locator(bundle, entry, section)
            else:
                assert build_glossary_locator(bundle, entry, section).section == section


def test_actual_glossary_repeated_loads_are_deterministic():
    first_bundle = load_glossary_entries(DATA_PATH)
    second_bundle = load_glossary_entries(DATA_PATH)
    first_index = build_glossary_index(first_bundle, mode="corpus")
    second_index = build_glossary_index(second_bundle, mode="corpus")

    assert first_bundle == second_bundle
    assert evaluate_actual_glossary_coverage(DATA_PATH) == evaluate_actual_glossary_coverage(DATA_PATH)
    for query in ("PER", "영업 이익률", "별도재무"):
        first = lookup_glossary_entry(first_index, query)
        second = lookup_glossary_entry(second_index, query)
        assert first.status == second.status == "found"
        assert first.entry == second.entry
        assert first.matched_term == second.matched_term


def test_actual_glossary_coverage_rejects_synthetic_fixture_and_temp_approved_copy(tmp_path):
    temp_copy = tmp_path / "glossary.json"
    temp_copy.write_text(DATA_PATH.read_text(encoding="utf-8"), encoding="utf-8")

    with pytest.raises(GlossaryCorpusValidationError):
        evaluate_actual_glossary_coverage(FIXTURE_PATH)
    with pytest.raises(GlossaryCorpusValidationError):
        evaluate_actual_glossary_coverage(temp_copy)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda bundle: replace(bundle, corpus_id="glossary-approved-v2"),
        lambda bundle: replace(bundle, corpus_type="review_corpus"),
        lambda bundle: replace(bundle, language="en"),
        lambda bundle: replace(bundle, entries=bundle.entries[:-1]),
        lambda bundle: replace(
            bundle,
            entries=bundle.entries
            + (
                replace(
                    bundle.entries[0],
                    entry_id="glossary:extra",
                    canonical_term="추가 용어",
                    aliases=("extra actual alias",),
                    related_entry_ids=(),
                ),
            ),
        ),
        lambda bundle: replace(
            bundle,
            entries=(
                replace(
                    bundle.entries[0],
                    corpus_ingest_allowed=False,
                    external_llm_processing_allowed=False,
                ),
            )
            + bundle.entries[1:],
        ),
        lambda bundle: replace(
            bundle,
            entries=(replace(bundle.entries[0], external_llm_processing_allowed=False),) + bundle.entries[1:],
        ),
    ],
)
def test_actual_glossary_coverage_rejects_identity_or_entry_drift(monkeypatch, mutate):
    drifted = mutate(load_glossary_entries(DATA_PATH))
    monkeypatch.setattr(glossary_module, "load_glossary_entries", lambda path: drifted)

    with pytest.raises(GlossaryCorpusValidationError):
        evaluate_actual_glossary_coverage(DATA_PATH)


def drift_actual_entry(entry_id, **updates):
    bundle = load_glossary_entries(DATA_PATH)
    entries = tuple(replace(entry, **updates) if entry.entry_id == entry_id else entry for entry in bundle.entries)
    return replace(bundle, entries=entries)


@pytest.mark.parametrize(
    "drifted_bundle",
    [
        lambda: drift_actual_entry("glossary:per", canonical_term="주가이익비율"),
        lambda: drift_actual_entry("glossary:per", aliases=("PER", "주가 수익 비율", "주가이익비율", "주가 이익 비율", "피이알")),
        lambda: drift_actual_entry("glossary:per", aliases=("PER", "주가 수익 비율", "주가이익비율")),
        lambda: drift_actual_entry("glossary:per", aliases=("PER", "주가 수익 비율", "주가이익비율", "주가 이익비율")),
        lambda: drift_actual_entry("glossary:per", category="profitability"),
        lambda: drift_actual_entry("glossary:per", definition="주가수익비율 정의가 변경되었습니다."),
        lambda: drift_actual_entry("glossary:per", why_it_matters="주가수익비율 활용 문구가 변경되었습니다."),
        lambda: drift_actual_entry("glossary:per", caution="주가수익비율 주의 문구가 변경되었습니다."),
        lambda: drift_actual_entry("glossary:per", formula="주가 / 주당순이익(EPS)"),
        lambda: drift_actual_entry("glossary:rights_offering", example="유상증자 예시가 변경되었습니다."),
        lambda: drift_actual_entry("glossary:per", related_entry_ids=("glossary:eps", "glossary:pbr")),
        lambda: drift_actual_entry("glossary:per", related_entry_ids=()),
        lambda: drift_actual_entry("glossary:per", related_entry_ids=("glossary:pbr",)),
        lambda: drift_actual_entry("glossary:per", source_note="Source note drift."),
        lambda: drift_actual_entry("glossary:per", permission_note="Human Owner가 corpus 적재만 승인했습니다."),
        lambda: drift_actual_entry("glossary:per", external_llm_processing_allowed=False),
        lambda: drift_actual_entry("glossary:per", ingestion_version="glossary-ingest-m1-07-v2"),
        lambda: drift_actual_entry("glossary:per", source_url="https://example.com/glossary"),
        lambda: drift_actual_entry("glossary:per", source_asset_id="asset001"),
    ],
)
def test_actual_glossary_coverage_rejects_approved_field_drift(monkeypatch, drifted_bundle):
    monkeypatch.setattr(glossary_module, "load_glossary_entries", lambda path: drifted_bundle())

    with pytest.raises(GlossaryCorpusValidationError):
        evaluate_actual_glossary_coverage(DATA_PATH)


def test_approved_snapshot_fingerprint_is_order_and_format_independent(tmp_path):
    bundle = load_glossary_entries(DATA_PATH)
    base = glossary_module._calculate_approved_glossary_snapshot_sha256(bundle.entries)
    per = next(entry for entry in bundle.entries if entry.entry_id == "glossary:per")
    net_income = next(entry for entry in bundle.entries if entry.entry_id == "glossary:net_income")
    reordered_entries = tuple(reversed(bundle.entries))
    alias_reordered_entries = tuple(
        replace(entry, aliases=tuple(reversed(entry.aliases))) if entry.entry_id == per.entry_id else entry
        for entry in bundle.entries
    )
    related_reordered_entries = tuple(
        replace(entry, related_entry_ids=tuple(reversed(entry.related_entry_ids)))
        if entry.entry_id == net_income.entry_id
        else entry
        for entry in bundle.entries
    )
    raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    compact_path = tmp_path / "compact.json"
    pretty_path = tmp_path / "pretty.json"
    compact_path.write_text(json.dumps(raw, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    pretty_path.write_text(
        json.dumps(
            {
                "entries": raw["entries"],
                "language": raw["language"],
                "corpus_id": raw["corpus_id"],
                "corpus_type": raw["corpus_type"],
                "schema_version": raw["schema_version"],
            },
            ensure_ascii=False,
            indent=4,
        ),
        encoding="utf-8",
    )

    assert glossary_module._calculate_approved_glossary_snapshot_sha256(reordered_entries) == base
    assert glossary_module._calculate_approved_glossary_snapshot_sha256(alias_reordered_entries) == base
    assert glossary_module._calculate_approved_glossary_snapshot_sha256(related_reordered_entries) == base
    assert glossary_module._calculate_approved_glossary_snapshot_sha256(load_glossary_entries(compact_path).entries) == base
    assert glossary_module._calculate_approved_glossary_snapshot_sha256(load_glossary_entries(pretty_path).entries) == base


@pytest.mark.parametrize(
    "entries",
    [
        [approved_entry(1), review_entry("pending", 2, corpus_ingest_allowed=False)],
        [approved_entry(1, corpus_ingest_allowed=False)],
    ],
)
def test_approved_corpus_rejects_pending_rejected_or_permission_false(entries):
    with pytest.raises(GlossaryCorpusValidationError):
        validate_glossary_corpus(approved_corpus(entries=entries), mode="corpus")


@pytest.mark.parametrize(
    "updates",
    [
        {"usage_review_status": "synthetic", "corpus_ingest_allowed": True},
        {"usage_review_status": "synthetic", "external_llm_processing_allowed": True},
        {
            "usage_review_status": "pending",
            "content_origin": "user_authored",
            "corpus_ingest_allowed": True,
        },
        {
            "usage_review_status": "pending",
            "content_origin": "user_authored",
            "external_llm_processing_allowed": True,
        },
        {
            "usage_review_status": "rejected",
            "content_origin": "user_authored",
            "corpus_ingest_allowed": True,
        },
        {
            "usage_review_status": "rejected",
            "content_origin": "user_authored",
            "external_llm_processing_allowed": True,
        },
        {"corpus_ingest_allowed": False, "external_llm_processing_allowed": True},
    ],
)
def test_permission_gate_rejects_unapproved_or_llm_without_corpus(updates):
    with pytest.raises(GlossaryEntryValidationError):
        validate_glossary_entry(approved_entry(1, **updates))


@pytest.mark.parametrize(
    "updates",
    [
        {"usage_review_status": "pending", "content_origin": "user_authored", "corpus_ingest_allowed": False},
        {"usage_review_status": "rejected", "content_origin": "user_authored", "corpus_ingest_allowed": False},
        {"corpus_ingest_allowed": False, "external_llm_processing_allowed": False},
        {"corpus_ingest_allowed": True, "external_llm_processing_allowed": False},
        {"corpus_ingest_allowed": True, "external_llm_processing_allowed": True},
    ],
)
def test_permission_gate_allows_supported_review_and_approved_combinations(updates):
    entry = validate_glossary_entry(approved_entry(1, **updates))

    assert entry.external_llm_processing_allowed is updates.get("external_llm_processing_allowed", False)


@pytest.mark.parametrize(
    "field",
    [
        "entry_id",
        "version",
        "canonical_term",
        "aliases",
        "definition",
        "why_it_matters",
        "caution",
        "language",
        "usage_review_status",
        "corpus_ingest_allowed",
        "external_llm_processing_allowed",
        "content_origin",
        "source_note",
        "permission_note",
        "ingestion_version",
    ],
)
def test_entry_missing_required_field(field):
    raw = entry_data()
    raw.pop(field)

    with pytest.raises(GlossaryEntryValidationError):
        validate_glossary_entry(raw)


@pytest.mark.parametrize(
    "updates",
    [
        {"extra": "nope"},
        {"entry_id": "bad:id"},
        {"version": True},
        {"version": "1"},
        {"version": 2},
        {"canonical_term": "   "},
        {"aliases": ["   "]},
        {"aliases": ["알파비율"]},
        {"aliases": ["dup", " DUP "]},
        {"formula": ""},
        {"example": ""},
        {"ingestion_version": "future"},
        {"content_origin": "scraped"},
        {"content_origin": "external_source", "source_url": None, "source_asset_id": None},
        {"definition": "무조건 저평가 상태를 뜻한다."},
        {"source_note": "C:\\secret\\source.txt"},
    ],
)
def test_entry_validation_boundaries(updates):
    with pytest.raises(GlossaryEntryValidationError):
        validate_glossary_entry(entry_data(**updates))


@pytest.mark.parametrize(
    "updates",
    [
        {"source_url": "HTTPS://Example.COM:443/path?q=1"},
        {"source_asset_id": "asset.glossary-001"},
    ],
)
def test_entry_source_url_and_asset_success_boundaries(updates):
    raw = approved_entry(1, content_origin="user_authored", **updates)

    entry = validate_glossary_entry(raw)

    if updates.get("source_url"):
        assert entry.source_url == "https://example.com/path?q=1"
    if updates.get("source_asset_id"):
        assert entry.source_asset_id == "asset.glossary-001"


@pytest.mark.parametrize("source_url", ["https://example.com/path", "HTTPS://Example.COM:443/path?q=1"])
def test_entry_source_url_userinfo_success_baseline(source_url):
    entry = validate_glossary_entry(approved_entry(1, source_url=source_url))

    assert entry.source_url in {"https://example.com/path", "https://example.com/path?q=1"}


@pytest.mark.parametrize(
    "source_url",
    [
        "https://example.com/path?api-key=secret",
        "https://example.com/path?ACCESS_TOKEN=secret",
        "https://example.com/path?client%2Esecret=secret",
        "https://example.com/path?X-Amz-Signature=secret",
        "https://@example.com/path",
        "https://:@example.com/path",
        "https://user:@example.com/path",
        "https://:pass@example.com/path",
        "https://user:pass@example.com/path",
        "https://example.com/path#fragment",
        "https://example.com:bad/path",
        "file:///C:/secret/glossary.json",
        "C:\\secret\\glossary.json",
    ],
)
def test_entry_source_url_rejects_unsafe_values(source_url):
    with pytest.raises(GlossaryEntryValidationError):
        validate_glossary_entry(approved_entry(1, source_url=source_url))


@pytest.mark.parametrize("source_asset_id", [".", "..", "bad/id", "bad\\id", "C:\\asset\\id", "file://asset", "   "])
def test_entry_source_asset_id_rejects_unsafe_values(source_asset_id):
    with pytest.raises(GlossaryEntryValidationError):
        validate_glossary_entry(approved_entry(1, source_asset_id=source_asset_id))


@pytest.mark.parametrize(
    "mutate",
    [
        lambda raw: raw["entries"].append(copy.deepcopy(raw["entries"][0])),
        lambda raw: raw["entries"].__setitem__(1, {**raw["entries"][1], "canonical_term": "알파비율"}),
        lambda raw: raw["entries"].__setitem__(1, {**raw["entries"][1], "aliases": ["알파비율"]}),
        lambda raw: raw["entries"].__setitem__(1, {**raw["entries"][1], "aliases": ["ALPHA Ratio"]}),
        lambda raw: raw["entries"].__setitem__(0, {**raw["entries"][0], "related_entry_ids": ["glossary:alpha_ratio"]}),
        lambda raw: raw["entries"].__setitem__(
            0, {**raw["entries"][0], "related_entry_ids": ["glossary:beta_base", "glossary:beta_base"]}
        ),
        lambda raw: raw["entries"].__setitem__(
            0, {**raw["entries"][0], "related_entry_ids": ["glossary:missing"]}
        ),
    ],
)
def test_global_integrity_failures(mutate):
    raw = corpus_data()
    mutate(raw)

    with pytest.raises(GlossaryIngestValidationError):
        validate_glossary_corpus(raw, mode="load")


def test_direct_dataclass_malformed_entry_and_bundle_are_deep_validated():
    entry = validate_glossary_entry(entry_data())
    bundle = load_glossary_entries(FIXTURE_PATH)

    malformed_entry = replace(entry, aliases=(["bad"],))
    malformed_bundle = replace(bundle, entries=({"bad": "value"},))

    with pytest.raises(GlossaryEntryValidationError):
        validate_glossary_entry(malformed_entry)
    with pytest.raises(GlossaryIngestValidationError):
        validate_glossary_corpus(malformed_bundle, mode="load")


@pytest.mark.parametrize("raw", ["bad", b"bad", ["bad"], object()])
def test_public_corpus_boundary_rejects_raw_objects_with_typed_error(raw):
    with pytest.raises(GlossaryCorpusValidationError):
        validate_glossary_corpus(raw, mode="load")


def test_lookup_normalization_not_found_and_type_boundaries():
    index = build_glossary_index(load_glossary_entries(FIXTURE_PATH), mode="synthetic_unit")

    nfkc = lookup_glossary_entry(index, "ＡＬＰＨＡ　Ratio")
    whitespace = lookup_glossary_entry(index, "  알파   비율  ")
    blank = lookup_glossary_entry(index, "   ")
    unknown = lookup_glossary_entry(index, "없는 용어")

    assert nfkc.status == "found"
    assert nfkc.matched_by == "alias"
    assert whitespace.status == "found"
    assert whitespace.matched_term == "알파 비율"
    assert blank.status == "not_found"
    assert unknown.status == "not_found"
    with pytest.raises(GlossaryLookupValidationError):
        lookup_glossary_entry(index, 123)  # type: ignore[arg-type]


def test_index_is_copy_safe_and_mapping_is_read_only():
    raw = corpus_data()
    index = build_glossary_index(raw, mode="synthetic_unit")
    raw["entries"][0]["canonical_term"] = "변경된용어"
    raw["entries"][0]["aliases"].append("새별칭")

    assert lookup_glossary_entry(index, "알파비율").status == "found"
    assert lookup_glossary_entry(index, "변경된용어").status == "not_found"
    with pytest.raises(TypeError):
        index.lookup_map["new"] = index.lookup_map["알파비율"]  # type: ignore[index]


def direct_index(entries, *, corpus_id="glossary-direct-v1", corpus_type="synthetic_unit", language="ko", mutate=None):
    lookup = {}
    for entry in entries:
        lookup[glossary_module._normalize_lookup(entry.canonical_term)] = (entry, "canonical", entry.canonical_term)
        for alias in entry.aliases:
            lookup[glossary_module._normalize_lookup(alias)] = (entry, "alias", alias)
    if mutate is not None:
        mutate(lookup, entries)
    return GlossaryIndex(corpus_id=corpus_id, corpus_type=corpus_type, language=language, _lookup=lookup)


def synthetic_entries():
    return load_glossary_entries(FIXTURE_PATH).entries


def approved_entries(count=1):
    return tuple(validate_glossary_entry(approved_ascii_entry(number)) for number in range(1, count + 1))


@pytest.mark.parametrize(
    "index",
    [
        GlossaryIndex("glossary-direct-v1", "synthetic_unit", "ko", {}),
        GlossaryIndex("bad/id", "synthetic_unit", "ko", {"key": "bad"}),
        GlossaryIndex(123, "synthetic_unit", "ko", {"key": "bad"}),  # type: ignore[arg-type]
        GlossaryIndex("glossary-direct-v1", "unsupported", "ko", {"key": "bad"}),
        GlossaryIndex("glossary-direct-v1", "review_corpus", "ko", {"key": "bad"}),
        GlossaryIndex("glossary-direct-v1", "synthetic_unit", "en", {"key": "bad"}),
        GlossaryIndex("glossary-direct-v1", "synthetic_unit", "ko", "bad"),  # type: ignore[arg-type]
        GlossaryIndex("glossary-direct-v1", "synthetic_unit", "ko", {"": "bad"}),
        GlossaryIndex("glossary-direct-v1", "synthetic_unit", "ko", {123: "bad"}),  # type: ignore[dict-item]
        GlossaryIndex("glossary-direct-v1", "synthetic_unit", "ko", {"key": ("bad",)}),
    ],
)
def test_direct_index_basic_boundaries_fail_with_lookup_error(index):
    with pytest.raises(GlossaryLookupValidationError):
        lookup_glossary_entry(index, "anything")


def test_direct_index_malformed_entry_fails_with_lookup_error():
    entry = replace(synthetic_entries()[0], aliases=(["bad"],))
    index = GlossaryIndex(
        "glossary-direct-v1",
        "synthetic_unit",
        "ko",
        {glossary_module._normalize_lookup(entry.canonical_term): (entry, "canonical", entry.canonical_term)},
    )

    with pytest.raises(GlossaryLookupValidationError):
        lookup_glossary_entry(index, entry.canonical_term)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda lookup, entries: lookup.__setitem__("forged", (entries[0], "canonical", entries[0].canonical_term)),
        lambda lookup, entries: lookup.__setitem__("forgedalias", (entries[0], "alias", entries[0].aliases[0])),
        lambda lookup, entries: lookup.__setitem__(
            glossary_module._normalize_lookup(entries[0].canonical_term), (entries[0], "canonical", entries[0].aliases[0])
        ),
        lambda lookup, entries: lookup.__setitem__(
            glossary_module._normalize_lookup(entries[0].aliases[0]), (entries[0], "alias", entries[0].canonical_term)
        ),
        lambda lookup, entries: lookup.__setitem__(
            glossary_module._normalize_lookup("missing alias"), (entries[0], "alias", "missing alias")
        ),
        lambda lookup, entries: lookup.__setitem__("ALPHA Ratio", (entries[0], "alias", entries[0].aliases[0])),
        lambda lookup, entries: lookup.__setitem__(
            glossary_module._normalize_lookup(entries[0].aliases[0]), (entries[1], "alias", entries[0].aliases[0])
        ),
    ],
)
def test_direct_index_semantic_tuple_failures(mutate):
    index = direct_index(synthetic_entries(), mutate=mutate)

    with pytest.raises(GlossaryLookupValidationError):
        lookup_glossary_entry(index, "anything")


def test_direct_index_same_entry_id_with_different_content_fails():
    first = synthetic_entries()[0]
    second = replace(first, canonical_term="different direct term", aliases=())
    index = GlossaryIndex(
        "glossary-direct-v1",
        "synthetic_unit",
        "ko",
        {
            glossary_module._normalize_lookup(first.canonical_term): (first, "canonical", first.canonical_term),
            glossary_module._normalize_lookup(first.aliases[0]): (first, "alias", first.aliases[0]),
            glossary_module._normalize_lookup(first.aliases[1]): (first, "alias", first.aliases[1]),
            glossary_module._normalize_lookup(second.canonical_term): (second, "canonical", second.canonical_term),
        },
    )

    with pytest.raises(GlossaryLookupValidationError):
        lookup_glossary_entry(index, first.canonical_term)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda lookup, entries: lookup.pop(glossary_module._normalize_lookup(entries[0].canonical_term)),
        lambda lookup, entries: lookup.pop(glossary_module._normalize_lookup(entries[0].aliases[0])),
        lambda lookup, entries: lookup.pop(glossary_module._normalize_lookup(entries[0].aliases[1])),
        lambda lookup, entries: lookup.__setitem__("extra", (entries[0], "canonical", entries[0].canonical_term)),
    ],
)
def test_direct_index_key_completeness_failures(mutate):
    index = direct_index(synthetic_entries(), mutate=mutate)

    with pytest.raises(GlossaryLookupValidationError):
        lookup_glossary_entry(index, "anything")


@pytest.mark.parametrize(
    "index",
    [
        direct_index(approved_entries(), corpus_type="synthetic_unit"),
        direct_index(synthetic_entries(), corpus_type="approved_corpus"),
        direct_index(
            (validate_glossary_entry(approved_ascii_entry(1, corpus_ingest_allowed=False)),),
            corpus_type="approved_corpus",
        ),
        direct_index((replace(synthetic_entries()[0], language="en"),), language="ko"),
        direct_index(
            (validate_glossary_entry(approved_ascii_entry(1, related_entry_ids=["glossary:missing"])),),
            corpus_type="approved_corpus",
        ),
    ],
)
def test_direct_index_corpus_entry_mismatch_failures(index):
    with pytest.raises(GlossaryLookupValidationError):
        lookup_glossary_entry(index, "anything")


def test_direct_index_global_collision_failure():
    first, second = approved_entries(2)
    second = replace(second, aliases=(first.canonical_term,))
    index = direct_index((first, second), corpus_type="approved_corpus")

    with pytest.raises(GlossaryLookupValidationError):
        lookup_glossary_entry(index, first.canonical_term)


def test_direct_index_valid_synthetic_success():
    entry = synthetic_entries()[0]
    index = direct_index(synthetic_entries(), corpus_type="synthetic_unit")

    result = lookup_glossary_entry(index, entry.canonical_term)

    assert result.status == "found"


def test_direct_index_valid_approved_success():
    entry = approved_entries()[0]
    index = direct_index((entry,), corpus_type="approved_corpus")

    result = lookup_glossary_entry(index, entry.canonical_term)

    assert result.status == "found"


def test_validate_index_returns_sanitized_immutable_copy():
    raw_lookup = {}
    entries = synthetic_entries()
    entry = entries[0]
    for indexed_entry in entries:
        raw_lookup[glossary_module._normalize_lookup(indexed_entry.canonical_term)] = (
            indexed_entry,
            "canonical",
            indexed_entry.canonical_term,
        )
        for alias in indexed_entry.aliases:
            raw_lookup[glossary_module._normalize_lookup(alias)] = (indexed_entry, "alias", alias)
    direct = GlossaryIndex("glossary-direct-v1", "synthetic_unit", "ko", raw_lookup)

    sanitized = glossary_module._validate_index(direct)
    raw_lookup.clear()

    assert sanitized is not direct
    assert lookup_glossary_entry(sanitized, entry.canonical_term).status == "found"
    with pytest.raises(TypeError):
        sanitized.lookup_map["new"] = sanitized.lookup_map[glossary_module._normalize_lookup(entry.canonical_term)]  # type: ignore[index]


@pytest.mark.parametrize("section", ["definition", "why_it_matters", "caution", "formula", "example"])
def test_locator_success_sections(section):
    bundle = load_glossary_entries(FIXTURE_PATH)
    entry = bundle.entries[0]

    locator = build_glossary_locator(bundle, entry, section)

    assert locator.corpus_id == bundle.corpus_id
    assert locator.entry_id == entry.entry_id
    assert locator.version == 1
    assert locator.section == section
    assert locator.source_type == GLOSSARY_SOURCE_TYPE
    assert locator.provider == MANUAL_GLOSSARY_PROVIDER
    assert locator.ingestion_version == GLOSSARY_INGESTION_VERSION
    assert "C:\\" not in str(locator)
    assert "secret" not in str(locator).casefold()


@pytest.mark.parametrize("section", ["formula", "example"])
def test_locator_missing_optional_section_fails(section):
    bundle = load_glossary_entries(FIXTURE_PATH)
    entry_without_optional_sections = bundle.entries[1]

    with pytest.raises(GlossaryCorpusValidationError):
        build_glossary_locator(bundle, entry_without_optional_sections, section)


def test_locator_unsupported_or_foreign_entry_fails():
    bundle = load_glossary_entries(FIXTURE_PATH)
    foreign_entry = validate_glossary_entry(entry_data(entry_id="glossary:foreign", canonical_term="외부항목"))

    with pytest.raises(GlossaryCorpusValidationError):
        build_glossary_locator(bundle, bundle.entries[0], "summary")
    with pytest.raises(GlossaryCorpusValidationError):
        build_glossary_locator(bundle, foreign_entry, "definition")


def test_coverage_counts_review_statuses_and_keeps_actual_coverage_not_run():
    raw = review_corpus()

    coverage = calculate_glossary_coverage(raw)

    assert coverage.total_entries == 3
    assert coverage.pending_entries == 1
    assert coverage.approved_actual_entries == 0
    assert coverage.rejected_entries == 1
    assert coverage.synthetic_entries == 0
    assert coverage.minimum_required == 15
    assert coverage.actual_coverage_evaluated is False
    assert coverage.meets_minimum is False


@pytest.mark.parametrize(
    "writer",
    [
        lambda path: path.write_text("{not json", encoding="utf-8"),
        lambda path: path.write_bytes(b"\xff\xfe\x00"),
        lambda path: path.write_text('["not-object"]', encoding="utf-8"),
    ],
)
def test_loader_errors_are_typed_and_sanitized(tmp_path, writer):
    path = tmp_path / "sentinel_secret_fixture.json"
    writer(path)

    with pytest.raises(GlossaryIngestValidationError) as exc_info:
        load_glossary_entries(path)

    rendered = "".join(traceback.format_exception_only(type(exc_info.value), exc_info.value)).casefold()
    assert "sentinel" not in rendered
    assert "secret" not in rendered
    assert str(path).casefold() not in rendered
    assert "not json" not in rendered


def test_loader_missing_file_is_typed_and_sanitized(tmp_path):
    path = tmp_path / "sentinel_secret_missing.json"

    with pytest.raises(GlossaryCorpusValidationError) as exc_info:
        load_glossary_entries(path)

    rendered = "".join(traceback.format_exception_only(type(exc_info.value), exc_info.value)).casefold()
    assert "sentinel" not in rendered
    assert "secret" not in rendered
    assert str(path).casefold() not in rendered


@pytest.mark.parametrize(
    "phrase",
    ["무조건 저평가", "반드시 상승", "확실한 수익", "always undervalued", "guaranteed return"],
)
def test_fixed_overclaim_blocklist_rejects_configured_phrases(phrase):
    with pytest.raises(GlossaryEntryValidationError):
        validate_glossary_entry(entry_data(definition=f"이 문장은 {phrase} 표현을 포함합니다."))


def test_smoke_public_import_surface_is_available():
    bundle = load_glossary_entries(FIXTURE_PATH)
    index = build_glossary_index(bundle, mode="synthetic_unit")
    result = lookup_glossary_entry(index, "감마노트")
    locator = build_glossary_locator(bundle, result.entry, "example")

    assert result.status == "found"
    assert locator.section == "example"
