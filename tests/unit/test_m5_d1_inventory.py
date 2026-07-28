from __future__ import annotations

from datetime import UTC, datetime
from datetime import timedelta

import pytest

from app.services.m5_d1_inventory import (
    SECURITY_DART_IDENTITIES,
    M5D1InventoryError,
    build_source_inventory_payload,
    normalize_disclosure_inventory,
    normalize_news_inventory,
    validate_corp_code_registry,
    validate_source_inventory_payload,
)
from app.services.m5_news_snapshot import SECURITY_TERMS


def test_same_title_different_publishers_survive_news_normalization() -> None:
    raw = {security_id: [] for security_id in SECURITY_TERMS}
    raw["KRX:005930"] = [
        _news(
            "삼성전자 HBM 공급 확대",
            "https://alpha.example/article/1?utm_source=test",
            "q1",
        ),
        _news(
            "삼성전자 HBM 공급 확대",
            "https://beta.example/article/2",
            "q2",
        ),
        _news(
            "삼성전자 HBM 공급 확대",
            "https://alpha.example/article/1?utm_source=other",
            "q3",
        ),
    ]

    items, rejections = normalize_news_inventory(
        raw,
        collected_at=datetime(2026, 7, 28, tzinfo=UTC),
    )

    assert len(items) == 2
    assert {item.publisher_host for item in items} == {
        "alpha.example",
        "beta.example",
    }
    assert {item.publisher for item in items} == {
        "alpha.example",
        "beta.example",
    }
    assert rejections["exact_url_duplicate"] == 1
    alpha = next(
        item for item in items if item.publisher_host == "alpha.example"
    )
    assert alpha.query_provenance == ("q1", "q3")


def test_news_normalization_rejects_future_and_wrong_company_items() -> None:
    raw = {security_id: [] for security_id in SECURITY_TERMS}
    raw["KRX:005930"] = [
        _news(
            "삼성전자 HBM 공급 확대",
            "https://example.test/late",
            "q1",
            pub_date="Mon, 27 Jul 2026 21:01:00 +0900",
        ),
        _news(
            "SK하이닉스 HBM 공급 확대",
            "https://example.test/wrong",
            "q1",
        ),
    ]

    items, rejections = normalize_news_inventory(
        raw,
        collected_at=datetime(2026, 7, 28, tzinfo=UTC),
    )

    assert items == ()
    assert rejections == {
        "outside_window": 1,
        "retained": 0,
        "security_not_established": 1,
    }


def test_corp_registry_and_disclosures_are_exactly_scoped() -> None:
    registry = [
        {
            "stock_code": stock_code,
            "corp_code": corp_code,
            "corp_name": f"{name} 주식회사",
        }
        for stock_code, corp_code, name in SECURITY_DART_IDENTITIES.values()
    ]
    verified = validate_corp_code_registry(registry)
    raw = {
        security_id: [
            _disclosure(
                stock_code=stock_code,
                corp_code=corp_code,
                company_name=f"{name} 주식회사",
                receipt_no=f"20260724{index:06d}",
                report_name=(
                    "[기재정정]단일판매ㆍ공급계약체결"
                    if index == 1
                    else "분기보고서"
                ),
            )
        ]
        for index, (
            security_id,
            (stock_code, corp_code, name),
        ) in enumerate(SECURITY_DART_IDENTITIES.items(), start=1)
    }

    disclosures = normalize_disclosure_inventory(raw)

    assert set(verified) == set(SECURITY_DART_IDENTITIES)
    assert len(disclosures) == 3
    first = next(
        item for item in disclosures if item.receipt_no.endswith("000001")
    )
    assert first.report_category == "material_event"
    assert first.correction_status == "correction"
    assert first.available_from.isoformat() == "2026-07-24T14:59:59+00:00"


def test_hynix_description_fallback_is_bounded_to_event_titles() -> None:
    raw = {security_id: [] for security_id in SECURITY_TERMS}
    raw["KRX:000660"] = [
        {
            **_news(
                "HBM4 가격 급등에 서버 원가 비중 확대",
                "https://example.test/direct-description",
                "q1",
            ),
            "description": (
                "SK하이닉스는 HBM4 공급을 위한 협력 관계를 설명했다."
            ),
        },
        {
            **_news(
                "정치권 주간 일정 정리",
                "https://example.test/incidental-description",
                "q1",
            ),
            "description": (
                "SK하이닉스 관련 일정도 기사 후반에 함께 언급됐다."
            ),
        },
    ]

    items, rejections = normalize_news_inventory(
        raw,
        collected_at=datetime(2026, 7, 28, tzinfo=UTC),
    )

    assert len(items) == 1
    assert items[0].security_match_basis == (
        "provider_description_alias"
    )
    assert rejections["security_not_established"] == 1


def test_dart_correction_remark_distinguishes_superseded_and_withdrawn() -> None:
    raw = {
        security_id: []
        for security_id in SECURITY_DART_IDENTITIES
    }
    stock_code, corp_code, name = SECURITY_DART_IDENTITIES["KRX:005930"]
    superseded = _disclosure(
        stock_code=stock_code,
        corp_code=corp_code,
        company_name=f"{name} 주식회사",
        receipt_no="20260724000011",
        report_name="단일판매ㆍ공급계약체결",
    )
    superseded["rm"] = "정"
    withdrawn = _disclosure(
        stock_code=stock_code,
        corp_code=corp_code,
        company_name=f"{name} 주식회사",
        receipt_no="20260724000012",
        report_name="단일판매ㆍ공급계약체결",
    )
    withdrawn["rm"] = "철"
    raw["KRX:005930"] = [superseded, withdrawn]

    disclosures = normalize_disclosure_inventory(raw)

    assert [item.correction_status for item in disclosures] == [
        "superseded",
        "withdrawal",
    ]


def test_dart_extension_decision_is_not_misclassified_as_correction() -> None:
    raw = {
        security_id: []
        for security_id in SECURITY_DART_IDENTITIES
    }
    stock_code, corp_code, name = SECURITY_DART_IDENTITIES["KRX:005930"]
    original = _disclosure(
        stock_code=stock_code,
        corp_code=corp_code,
        company_name=f"{name} 주식회사",
        receipt_no="20260724000013",
        report_name="신고서 제출기한 연장신고서",
    )
    extension = _disclosure(
        stock_code=stock_code,
        corp_code=corp_code,
        company_name=f"{name} 주식회사",
        receipt_no="20260724000014",
        report_name="[연장결정]신고서 제출기한 연장신고서",
    )
    raw["KRX:005930"] = [original, extension]

    disclosures = normalize_disclosure_inventory(raw)

    assert [item.correction_status for item in disclosures] == [
        "original",
        "original",
    ]
    assert disclosures[0].lineage_key == disclosures[1].lineage_key


def test_source_inventory_round_trip_and_coverage() -> None:
    raw_news = {security_id: [] for security_id in SECURITY_TERMS}
    raw_news["KRX:005930"] = [
        _news(
            "삼성전자 HBM 공급 확대",
            "https://alpha.example/article/1",
            "q1",
        ),
        _news(
            "삼성전자 HBM 공급 확대",
            "https://beta.example/article/2",
            "q2",
        ),
    ]
    news, rejections = normalize_news_inventory(
        raw_news,
        collected_at=datetime(2026, 7, 28, tzinfo=UTC),
    )
    registry_raw = [
        {
            "stock_code": stock_code,
            "corp_code": corp_code,
            "corp_name": f"{name} 주식회사",
        }
        for stock_code, corp_code, name in SECURITY_DART_IDENTITIES.values()
    ]
    registry = validate_corp_code_registry(registry_raw)
    disclosures = normalize_disclosure_inventory(
        {
            security_id: []
            for security_id in SECURITY_DART_IDENTITIES
        }
    )
    payload = build_source_inventory_payload(
        news_items=news,
        disclosure_items=disclosures,
        corp_registry=registry,
        news_rejections=rejections,
        collected_at=datetime(2026, 7, 28, tzinfo=UTC),
        provider_calls={"naver": 2, "opendart": 4},
    )

    validate_source_inventory_payload(payload)

    samsung = payload["coverage"]["news"]["KRX:005930"]
    assert samsung["total"] == 2
    assert samsung["publisher_host_count"] == 2
    assert samsung["same_title_multi_publisher_groups"] == 1


def test_source_checksum_ignores_collection_execution_time() -> None:
    raw_news = {security_id: [] for security_id in SECURITY_TERMS}
    raw_news["KRX:005930"] = [
        _news(
            "삼성전자 HBM 공급 확대",
            "https://alpha.example/article/1",
            "q1",
        )
    ]
    first_time = datetime(2026, 7, 28, tzinfo=UTC)
    second_time = first_time + timedelta(minutes=5)
    first_news, first_rejections = normalize_news_inventory(
        raw_news,
        collected_at=first_time,
    )
    second_news, second_rejections = normalize_news_inventory(
        raw_news,
        collected_at=second_time,
    )
    registry = validate_corp_code_registry(
        [
            {
                "stock_code": stock_code,
                "corp_code": corp_code,
                "corp_name": f"{name} 주식회사",
            }
            for (
                stock_code,
                corp_code,
                name,
            ) in SECURITY_DART_IDENTITIES.values()
        ]
    )
    disclosures = normalize_disclosure_inventory(
        {
            security_id: []
            for security_id in SECURITY_DART_IDENTITIES
        }
    )

    first = build_source_inventory_payload(
        news_items=first_news,
        disclosure_items=disclosures,
        corp_registry=registry,
        news_rejections=first_rejections,
        collected_at=first_time,
        provider_calls={"naver": 1, "opendart": 1},
    )
    second = build_source_inventory_payload(
        news_items=second_news,
        disclosure_items=disclosures,
        corp_registry=registry,
        news_rejections=second_rejections,
        collected_at=second_time,
        provider_calls={"naver": 1, "opendart": 1},
    )

    assert first["source_sha256"] == second["source_sha256"]
    assert first["collected_at"] != second["collected_at"]


def test_wrong_dart_mapping_is_rejected() -> None:
    registry = [
        {
            "stock_code": stock_code,
            "corp_code": (
                "99999999" if stock_code == "005930" else corp_code
            ),
            "corp_name": f"{name} 주식회사",
        }
        for stock_code, corp_code, name in SECURITY_DART_IDENTITIES.values()
    ]

    with pytest.raises(M5D1InventoryError):
        validate_corp_code_registry(registry)


def _news(
    title: str,
    url: str,
    provenance: str,
    *,
    pub_date: str = "Fri, 24 Jul 2026 15:00:00 +0900",
) -> dict[str, object]:
    return {
        "title": title,
        "originallink": url,
        "link": f"https://n.news.naver.com/{provenance}",
        "pubDate": pub_date,
        "_questock_query_provenance": provenance,
    }


def _disclosure(
    *,
    stock_code: str,
    corp_code: str,
    company_name: str,
    receipt_no: str,
    report_name: str,
) -> dict[str, str]:
    return {
        "corp_code": corp_code,
        "corp_name": company_name,
        "stock_code": stock_code,
        "corp_cls": "Y",
        "report_nm": report_name,
        "rcept_no": receipt_no,
        "flr_nm": company_name,
        "rcept_dt": "20260724",
        "rm": "",
    }
