from __future__ import annotations

from app.services.m5_news_snapshot import (
    DAILY_CAP,
    SECURITY_TERMS,
    curate_m5_news_items,
    load_m5_news_documents,
)


def test_m5_news_curation_rejects_market_product_and_employment_noise() -> None:
    raw = {security_id: [] for security_id in SECURITY_TERMS}
    raw["KRX:005930"] = [
        _item(
            "삼성전자, HBM5에 2나노 공정 적용 기술 개발",
            "https://example.test/direct",
        ),
        _item(
            "삼성전자우 주가 17만원대 회귀",
            "https://example.test/preferred",
        ),
        _item(
            "삼성전자 ETF 레버리지 수익률 급등",
            "https://example.test/etf",
        ),
    ]

    documents = curate_m5_news_items(raw)

    assert [item.title for item in documents] == [
        "삼성전자, HBM5에 2나노 공정 적용 기술 개발"
    ]
    assert documents[0].text.startswith(
        "기사 제목에서 확인되는 내용:"
    )
    assert (
        documents[0].metadata["content_origin"]
        == "source_title_only"
    )


def test_m5_news_daily_cap_is_maximum_not_quota() -> None:
    raw = {security_id: [] for security_id in SECURITY_TERMS}
    raw["KRX:005930"] = [
        _item(
            f"삼성전자 반도체 공급 계약 {index}",
            f"https://example.test/direct-{index}",
            minute=index,
        )
        for index in range(20)
    ]

    documents = curate_m5_news_items(raw)

    assert len(documents) == DAILY_CAP


def test_committed_m5_news_corpus_is_valid_and_directly_scoped() -> None:
    documents = load_m5_news_documents()

    assert documents
    assert all(
        len(item.primary_security_ids) == 1
        and item.primary_security_ids[0] in SECURITY_TERMS
        and item.metadata["content_origin"] == "source_title_only"
        and item.locator["content_level"] == "source_title_only"
        for item in documents
    )


def _item(
    title: str,
    url: str,
    *,
    minute: int = 0,
) -> dict[str, str]:
    return {
        "title": title,
        "originallink": url,
        "link": url,
        "pubDate": (
            f"Fri, 24 Jul 2026 15:{minute:02d}:00 +0900"
        ),
    }
