import asyncio
import json
from datetime import UTC, date
from pathlib import Path

import pytest

from app.core.models import DateRange, SecurityIdentifier
from app.core.status import ProviderStatus
from app.providers.disclosure import (
    DISCLOSURE_INGESTION_VERSION,
    RECORDED_DISCLOSURE_PROVIDER_KEY,
    DisclosureRegistryError,
    RecordedDisclosureProvider,
    load_disclosure_security_registry,
    map_opendart_status,
    normalize_opendart_disclosure_response,
)

FIXTURE_PATH = Path("tests/fixtures/disclosures/opendart_list_synthetic.json")
SECURITIES_PATH = Path("data/securities.json")
SAMSUNG = "KRX:005930"
SK_HYNIX = "KRX:000660"
HYUNDAI = "KRX:005380"


def run(coro):
    return asyncio.run(coro)


def security_record(ticker="005930"):
    data = json.loads(SECURITIES_PATH.read_text(encoding="utf-8"))
    return next(item for item in data["securities"] if item["ticker"] == ticker)


def security(ticker="005930", *, corp_code=None, security_type=None, security_name=None, corp_name=None):
    record = security_record(ticker)
    return SecurityIdentifier(
        market=record["market"],
        ticker=record["ticker"],
        security_name=security_name if security_name is not None else record["security_name"],
        security_type=security_type if security_type is not None else record["security_type"],
        corp_code=corp_code,
        corp_name=corp_name if corp_name is not None else record["corp_name"],
    )


def sk_hynix_security():
    return security("000660")


def hyundai_security():
    return security("005380")


def item(
    *,
    corp_code="00126380",
    corp_name="Samsung Electronics",
    stock_code="005930",
    report_nm="Annual disclosure",
    rcept_no="20260721000001",
    flr_nm="Finance Team",
    rcept_dt="20260721",
    rm="",
    corp_cls="Y",
    **extra,
):
    result = {
        "corp_cls": corp_cls,
        "corp_name": corp_name,
        "corp_code": corp_code,
        "stock_code": stock_code,
        "report_nm": report_nm,
        "rcept_no": rcept_no,
        "flr_nm": flr_nm,
        "rcept_dt": rcept_dt,
        "rm": rm,
    }
    result.update(extra)
    return result


def response_with(items=None, *, status="000", **extra):
    response = {
        "status": status,
        "message": "OK",
        "page_no": 1,
        "page_count": 10,
        "total_count": len(items or []),
        "total_page": 1,
        "list": items or [],
    }
    response.update(extra)
    return response


def fixture_with(items=None, *, status="000", case="response", correction_links=None, response=None, **response_extra):
    if response is None:
        response = response_with(items, status=status, **response_extra)
    return {
        "fixture_version": 1,
        "fixture_type": "synthetic_unit",
        "case": case,
        "response": response,
        "extensions": {"correction_links": correction_links or {}},
    }


def fetch_docs(provider, selected_security=None, query=None, date_range=None):
    result = run(provider.fetch(selected_security or security(), query=query, date_range=date_range))
    assert result.status == ProviderStatus.OK
    assert result.data is not None
    return result.data


def flatten(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def test_recorded_fixture_returns_three_supported_securities():
    provider = RecordedDisclosureProvider(fixture_path=FIXTURE_PATH)

    samsung_docs = fetch_docs(provider, security())
    sk_docs = fetch_docs(provider, sk_hynix_security())
    hyundai_docs = fetch_docs(provider, hyundai_security())

    samsung = samsung_docs[0]
    assert samsung.provider == RECORDED_DISCLOSURE_PROVIDER_KEY
    assert samsung.source_type == "disclosure"
    assert samsung.ingestion_version == DISCLOSURE_INGESTION_VERSION
    assert samsung.primary_security_ids == [SAMSUNG]
    assert samsung.mentioned_security_ids == []
    assert samsung.document_id == "disclosure:20260721000005"
    assert samsung.source_url == "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260721000005"
    assert samsung.locator["receipt_no"] == "20260721000005"
    assert samsung.locator["viewer_url"] == samsung.source_url
    assert samsung.metadata["content_level"] == "listing_metadata"
    assert samsung.metadata["corp_code_verification_status"] == "candidate"
    assert samsung.metadata["correction_of"] == "20260720000004"
    assert samsung.metadata["has_subsequent_correction"] is False
    assert samsung.published_at is not None
    assert samsung.published_at.tzinfo == UTC
    assert sk_docs[0].primary_security_ids == [SK_HYNIX]
    assert hyundai_docs[0].primary_security_ids == [HYUNDAI]


def test_shared_normalizer_uses_injected_provider_key_and_ingestion_version():
    registry = load_disclosure_security_registry()
    docs = normalize_opendart_disclosure_response(
        response_with([item(report_nm="Live compatible disclosure")]),
        security=security(),
        query=None,
        date_range=None,
        provider_key="opendart_disclosure",
        ingestion_version="disclosure-live-v1",
        registry=registry,
        correction_links={},
    )

    assert len(docs) == 1
    assert docs[0].provider == "opendart_disclosure"
    assert docs[0].ingestion_version == "disclosure-live-v1"
    assert docs[0].locator["provider"] == "opendart_disclosure"


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("000", ProviderStatus.OK),
        ("013", ProviderStatus.NO_DATA),
        ("010", ProviderStatus.UNAUTHORIZED),
        ("011", ProviderStatus.UNAUTHORIZED),
        ("012", ProviderStatus.UNAUTHORIZED),
        ("101", ProviderStatus.UNAUTHORIZED),
        ("901", ProviderStatus.UNAUTHORIZED),
        ("020", ProviderStatus.RATE_LIMITED),
        ("021", ProviderStatus.INVALID_QUERY),
        ("100", ProviderStatus.INVALID_QUERY),
        ("014", ProviderStatus.PROVIDER_UNAVAILABLE),
        ("800", ProviderStatus.PROVIDER_UNAVAILABLE),
        ("900", ProviderStatus.PROVIDER_UNAVAILABLE),
        ("999", ProviderStatus.PROVIDER_UNAVAILABLE),
        (None, ProviderStatus.PARSE_ERROR),
        (123, ProviderStatus.PARSE_ERROR),
    ],
)
def test_map_opendart_status(status, expected):
    assert map_opendart_status(status) == expected


@pytest.mark.parametrize(
    ("fixture", "expected_status", "expected_error_code"),
    [
        (fixture_with(status="013", response={"status": "013", "message": "no data"}), ProviderStatus.NO_DATA, None),
        (fixture_with(status="020", response={"status": "020", "message": "rate"}), ProviderStatus.RATE_LIMITED, "rate_limited"),
        (fixture_with(status="010", response={"status": "010", "message": "auth"}), ProviderStatus.UNAUTHORIZED, "unauthorized"),
        (fixture_with(status="021", response={"status": "021", "message": "bad"}), ProviderStatus.INVALID_QUERY, "invalid_query"),
        (
            fixture_with(status="014", response={"status": "014", "message": "down"}),
            ProviderStatus.PROVIDER_UNAVAILABLE,
            "provider_unavailable",
        ),
        (fixture_with(case="timeout", response=None), ProviderStatus.TIMEOUT, "attempt_timeout"),
        (fixture_with(case="network_error", response=None), ProviderStatus.PROVIDER_UNAVAILABLE, "provider_unavailable"),
        (fixture_with(response={"message": "missing"}), ProviderStatus.PARSE_ERROR, "parse_error"),
        (fixture_with(response={"status": 1}), ProviderStatus.PARSE_ERROR, "parse_error"),
    ],
)
def test_recorded_status_mapping_for_failures(fixture, expected_status, expected_error_code):
    provider = RecordedDisclosureProvider(recorded_fixture=fixture)

    result = run(provider.fetch(security()))

    assert result.status == expected_status
    assert result.error_code == expected_error_code
    assert result.data is None


@pytest.mark.parametrize(
    "response",
    [
        ["not-dict"],
        {"status": "000"},
        {"status": "000", "list": "not-list"},
    ],
)
def test_success_schema_errors_are_parse_error(response):
    provider = RecordedDisclosureProvider(recorded_fixture=fixture_with(response=response))

    result = run(provider.fetch(security()))

    assert result.status == ProviderStatus.PARSE_ERROR
    assert result.error_code == "parse_error"


def test_empty_success_list_is_no_data():
    provider = RecordedDisclosureProvider(recorded_fixture=fixture_with([]))

    result = run(provider.fetch(security()))

    assert result.status == ProviderStatus.NO_DATA
    assert result.data is None


def test_canonical_security_accepts_none_or_matching_corp_code():
    provider = RecordedDisclosureProvider(recorded_fixture=fixture_with([item()]))

    none_result = run(provider.fetch(security(corp_code=None)))
    matching_result = run(provider.fetch(security(corp_code="00126380")))

    assert none_result.status == ProviderStatus.OK
    assert none_result.data[0].metadata["corp_code_verification_status"] == "candidate"
    assert matching_result.status == ProviderStatus.OK


@pytest.mark.parametrize(
    "bad_security",
    [
        SecurityIdentifier(
            market="KRX",
            ticker="123456",
            security_name=security().security_name,
            security_type="common_stock",
            corp_code=None,
            corp_name=security().corp_name,
        ),
        security(security_type="preferred_stock"),
        security(security_name=sk_hynix_security().security_name),
        security(corp_name=sk_hynix_security().corp_name),
        security(corp_code="99999999"),
    ],
)
def test_canonical_security_rejects_unsupported_and_mismatched_inputs(bad_security):
    provider = RecordedDisclosureProvider(recorded_fixture=fixture_with([item()]))

    result = run(provider.fetch(bad_security))

    assert result.status == ProviderStatus.INVALID_QUERY
    assert result.error_code == "invalid_query"


@pytest.mark.parametrize(
    "override",
    [
        {"corp_code": "123"},
        {"stock_code": "123"},
        {"rcept_no": "123"},
        {"rcept_dt": "20260231"},
        {"report_nm": "   "},
        {"corp_code": None},
        {"report_nm": 123},
    ],
)
def test_malformed_items_all_bad_is_parse_error(override):
    provider = RecordedDisclosureProvider(recorded_fixture=fixture_with([item(**override)]))

    result = run(provider.fetch(security()))

    assert result.status == ProviderStatus.PARSE_ERROR


def test_malformed_items_are_excluded_but_valid_items_remain_ok():
    recorded = fixture_with(
        [
            "not-an-item",
            item(report_nm=123, rcept_no="20260721000001"),
            item(report_nm="valid disclosure", rcept_no="20260721000002"),
        ]
    )
    provider = RecordedDisclosureProvider(recorded_fixture=recorded)

    docs = fetch_docs(provider)

    assert len(docs) == 1
    assert docs[0].title == "valid disclosure"


def test_optional_fields_none_or_non_string_are_safe_empty_values():
    recorded = fixture_with(
        [
            item(corp_cls=None, flr_nm=None, rm=123, report_nm="Optional fields", rcept_no="20260721000003"),
        ]
    )
    provider = RecordedDisclosureProvider(recorded_fixture=recorded)

    doc = fetch_docs(provider)[0]

    assert doc.metadata["corp_cls"] == ""
    assert doc.metadata["submitter"] == ""
    assert doc.metadata["remark"] == ""


@pytest.mark.parametrize(
    "raw_item",
    [
        item(corp_code="00164779", stock_code="000660", rcept_no="20260721000004"),
        item(corp_code="00126380", stock_code="000660", rcept_no="20260721000005"),
        item(corp_code="00164779", stock_code="005930", rcept_no="20260721000006"),
        item(corp_code="12345678", stock_code="123456", rcept_no="20260721000007"),
    ],
)
def test_wrong_company_items_are_excluded(raw_item):
    provider = RecordedDisclosureProvider(recorded_fixture=fixture_with([raw_item]))

    result = run(provider.fetch(security()))

    assert result.status == ProviderStatus.NO_DATA


def test_viewer_url_ignores_fixture_url_and_document_id_uses_receipt_only():
    recorded = fixture_with(
        [
            item(
                report_nm="URL source ignored",
                rcept_no="20260721000008",
                source_url="https://example.com/not-used",
            )
        ]
    )
    provider = RecordedDisclosureProvider(recorded_fixture=recorded)

    doc = fetch_docs(provider)[0]

    assert doc.source_url == "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260721000008"
    assert doc.locator["viewer_url"] == doc.source_url
    assert doc.document_id == "disclosure:20260721000008"


def test_receipt_dedupe_keeps_first_but_distinct_receipts_are_kept():
    recorded = fixture_with(
        [
            item(report_nm="first duplicate", rcept_no="20260721000009"),
            item(report_nm="second duplicate", rcept_no="20260721000009"),
            item(report_nm="same title different receipt", rcept_no="20260721000010"),
        ]
    )
    provider = RecordedDisclosureProvider(recorded_fixture=recorded)

    docs = fetch_docs(provider)

    assert len(docs) == 2
    assert {doc.document_id for doc in docs} == {"disclosure:20260721000009", "disclosure:20260721000010"}
    duplicate_doc = next(doc for doc in docs if doc.document_id == "disclosure:20260721000009")
    assert duplicate_doc.title == "first duplicate"


def test_url_locator_metadata_and_message_do_not_include_local_paths_or_synthetic_secret():
    sentinel = "SECRET_SENTINEL"
    recorded = fixture_with([item(report_nm="safe disclosure", rcept_no="20260721000011")])
    recorded["fixture_path"] = "C:/Users/USER/Questock/secret.json"
    recorded["extensions"]["secret"] = sentinel
    provider = RecordedDisclosureProvider(recorded_fixture=recorded)

    result = run(provider.fetch(security()))

    assert result.status == ProviderStatus.OK
    doc = result.data[0]
    combined = flatten({"source_url": doc.source_url, "locator": doc.locator, "metadata": doc.metadata, "message": result.message})
    assert sentinel not in combined
    assert "C:/Users" not in combined
    assert "/workspace" not in combined


@pytest.mark.parametrize("marker", ["[\uae30\uc7ac\uc815\uc815]", "[\ucca8\ubd80\uc815\uc815]"])
def test_correction_submission_markers_are_correction(marker):
    provider = RecordedDisclosureProvider(recorded_fixture=fixture_with([item(report_nm=f"{marker} Correction")]))

    doc = fetch_docs(provider)[0]

    assert doc.metadata["is_correction"] is True
    assert doc.metadata["correction_type"] == "report_marker"


def test_explicit_correction_link_sets_correction_of_and_unlinked_receipts_keep_none():
    recorded = fixture_with(
        [
            item(report_nm="linked correction", rcept_no="20260721000012"),
            item(report_nm="original disclosure", rcept_no="20260720000012", rcept_dt="20260720"),
        ],
        correction_links={"20260721000012": "20260720000012"},
    )
    provider = RecordedDisclosureProvider(recorded_fixture=recorded)

    docs = fetch_docs(provider)

    linked = next(doc for doc in docs if doc.document_id == "disclosure:20260721000012")
    original = next(doc for doc in docs if doc.document_id == "disclosure:20260720000012")
    assert linked.metadata["correction_of"] == "20260720000012"
    assert linked.metadata["is_correction"] is True
    assert original.metadata["correction_of"] is None


@pytest.mark.parametrize(
    "marker",
    [
        "[\ucca8\ubd80\ucd94\uac00]",
        "[\ubcc0\uacbd\ub4f1\ub85d]",
        "[\uc5f0\uc7a5\uacb0\uc815]",
        "[\ubc1c\ud589\uc870\uac74\uc815\uc815]",
    ],
)
def test_update_variant_markers_are_not_correction_submissions(marker):
    provider = RecordedDisclosureProvider(recorded_fixture=fixture_with([item(report_nm=f"{marker} Update")]))

    doc = fetch_docs(provider)[0]

    assert doc.metadata["is_update_variant"] is True
    assert doc.metadata["update_variant_type"] == marker.strip("[]")
    assert doc.metadata["is_correction"] is False


@pytest.mark.parametrize(
    ("marker", "expected_field"),
    [
        ("[\uc815\uc815\uba85\ub839\ubd80\uacfc]", "has_correction_order"),
        ("[\uc815\uc815\uc81c\ucd9c\uc694\uad6c]", "has_correction_request"),
    ],
)
def test_correction_order_and_request_are_separate_from_correction_submission(marker, expected_field):
    provider = RecordedDisclosureProvider(recorded_fixture=fixture_with([item(report_nm=f"{marker} Order")]))

    doc = fetch_docs(provider)[0]

    assert doc.metadata[expected_field] is True
    assert doc.metadata["is_correction"] is False


def test_remark_marks_subsequent_correction_and_withdrawn_without_forcing_current_correction():
    recorded = fixture_with(
        [
            item(report_nm="securities market", rm="\uc720", rcept_no="20260721000013"),
            item(report_nm="subsequent exists", rm="\uc815", rcept_no="20260721000014"),
            item(report_nm="market and subsequent", rm="\uc720\uc815", rcept_no="20260721000015"),
            item(report_nm="market and withdrawn", rm="\uc720\ucca0", rcept_no="20260721000016"),
        ]
    )
    provider = RecordedDisclosureProvider(recorded_fixture=recorded)

    docs = fetch_docs(provider)

    market = next(doc for doc in docs if doc.document_id == "disclosure:20260721000013")
    subsequent = next(doc for doc in docs if doc.document_id == "disclosure:20260721000014")
    market_subsequent = next(doc for doc in docs if doc.document_id == "disclosure:20260721000015")
    withdrawn = next(doc for doc in docs if doc.document_id == "disclosure:20260721000016")
    assert market.metadata["has_subsequent_correction"] is False
    assert market.metadata["is_correction"] is False
    assert subsequent.metadata["has_subsequent_correction"] is True
    assert subsequent.metadata["is_correction"] is False
    assert market_subsequent.metadata["has_subsequent_correction"] is True
    assert market_subsequent.metadata["is_correction"] is False
    assert withdrawn.metadata["has_subsequent_correction"] is False
    assert withdrawn.metadata["is_withdrawn"] is True
    assert withdrawn.metadata["is_correction"] is False


def test_sorting_is_received_date_desc_then_receipt_desc_and_not_legal_effective_order():
    recorded = fixture_with(
        [
            item(report_nm="older", rcept_no="20260720000001", rcept_dt="20260720"),
            item(report_nm="same date lower receipt", rcept_no="20260721000001", rcept_dt="20260721"),
            item(report_nm="same date higher receipt", rcept_no="20260721000002", rcept_dt="20260721"),
        ]
    )
    provider = RecordedDisclosureProvider(recorded_fixture=recorded)

    docs = fetch_docs(provider)

    assert [doc.title for doc in docs] == ["same date higher receipt", "same date lower receipt", "older"]


def test_date_range_is_inclusive_and_no_match_is_no_data():
    recorded = fixture_with(
        [
            item(report_nm="before", rcept_no="20260720000001", rcept_dt="20260720"),
            item(report_nm="start", rcept_no="20260721000001", rcept_dt="20260721"),
            item(report_nm="end", rcept_no="20260722000001", rcept_dt="20260722"),
            item(report_nm="after", rcept_no="20260723000001", rcept_dt="20260723"),
        ]
    )
    provider = RecordedDisclosureProvider(recorded_fixture=recorded)

    docs = fetch_docs(provider, date_range=DateRange(start=date(2026, 7, 21), end=date(2026, 7, 22)))
    no_data = run(provider.fetch(security(), date_range=DateRange(start=date(2026, 7, 24), end=date(2026, 7, 24))))

    assert [doc.title for doc in docs] == ["end", "start"]
    assert no_data.status == ProviderStatus.NO_DATA
    assert docs[0].metadata["published_at_precision"] == "date"
    assert docs[0].metadata["timezone_basis"] == "Asia/Seoul"
    assert docs[0].published_at.tzinfo == UTC


def test_query_filters_report_submitter_and_remark_but_not_corp_name():
    recorded = fixture_with(
        [
            item(report_nm="<b>Annual&nbsp;Report</b>", flr_nm="Finance Team", rm="", rcept_no="20260721000015"),
            item(report_nm="Other filing", flr_nm="Special Submitter", rm="", rcept_no="20260721000016"),
            item(report_nm="Remark filing", flr_nm="", rm="Material Change", rcept_no="20260721000017"),
        ]
    )
    provider = RecordedDisclosureProvider(recorded_fixture=recorded)

    by_report = fetch_docs(provider, query=" annual report ")
    by_submitter = fetch_docs(provider, query="special submitter")
    by_remark = fetch_docs(provider, query="material change")
    by_corp_name = run(provider.fetch(security(), query="Samsung Electronics"))
    no_match = run(provider.fetch(security(), query="missing query"))

    assert [doc.title for doc in by_report] == ["Annual Report"]
    assert [doc.title for doc in by_submitter] == ["Other filing"]
    assert [doc.title for doc in by_remark] == ["Remark filing"]
    assert by_corp_name.status == ProviderStatus.NO_DATA
    assert no_match.status == ProviderStatus.NO_DATA


def test_blank_query_is_invalid_query():
    provider = RecordedDisclosureProvider(recorded_fixture=fixture_with([item()]))

    result = run(provider.fetch(security(), query=" \t "))

    assert result.status == ProviderStatus.INVALID_QUERY


def test_pagination_numbers_or_strings_do_not_block_item_parsing():
    numeric = RecordedDisclosureProvider(recorded_fixture=fixture_with([item(rcept_no="20260721000018")], page_no=1, total_count=1))
    stringy = RecordedDisclosureProvider(
        recorded_fixture=fixture_with([item(rcept_no="20260721000019")], page_no="1", total_count="1")
    )
    malformed = RecordedDisclosureProvider(
        recorded_fixture=fixture_with([item(rcept_no="20260721000020")], page_no={"bad": "value"})
    )

    assert fetch_docs(numeric)[0].document_id == "disclosure:20260721000018"
    assert fetch_docs(stringy)[0].document_id == "disclosure:20260721000019"
    assert fetch_docs(malformed)[0].document_id == "disclosure:20260721000020"


def test_registry_rejects_malformed_corp_code_or_ticker(tmp_path):
    data = json.loads(SECURITIES_PATH.read_text(encoding="utf-8"))
    bad_corp = tmp_path / "bad_corp.json"
    bad_ticker = tmp_path / "bad_ticker.json"
    bad_corp_data = json.loads(json.dumps(data))
    bad_ticker_data = json.loads(json.dumps(data))
    bad_corp_data["securities"][0]["corp_code"] = "123"
    bad_ticker_data["securities"][0]["ticker"] = "123"
    bad_corp.write_text(json.dumps(bad_corp_data), encoding="utf-8")
    bad_ticker.write_text(json.dumps(bad_ticker_data), encoding="utf-8")

    with pytest.raises(DisclosureRegistryError):
        load_disclosure_security_registry(bad_corp)
    with pytest.raises(DisclosureRegistryError):
        load_disclosure_security_registry(bad_ticker)


def test_identical_fixture_reruns_produce_identical_document_payloads():
    recorded = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    provider = RecordedDisclosureProvider(recorded_fixture=recorded)

    first = [doc.model_dump() for doc in fetch_docs(provider)]
    second = [doc.model_dump() for doc in fetch_docs(provider)]

    assert first == second
