import asyncio
import json
from datetime import UTC, date
from pathlib import Path

import pytest

from app.core.models import DateRange, SecurityIdentifier
from app.core.status import ProviderStatus
from app.providers.news import (
    NEWS_INGESTION_VERSION,
    RECORDED_NEWS_PROVIDER_KEY,
    RecordedNewsProvider,
    build_news_query,
    load_news_mention_lexicon,
)

FIXTURE_PATH = Path("tests/fixtures/news/naver_api_hub_synthetic.json")
SAMSUNG = "KRX:005930"
SK_HYNIX = "KRX:000660"
HYUNDAI = "KRX:005380"


def run(coro):
    return asyncio.run(coro)


def security(ticker="005930", name="삼성전자"):
    return SecurityIdentifier(
        market="KRX",
        ticker=ticker,
        security_name=name,
        security_type="common_stock",
        corp_code=None,
        corp_name=name,
    )


def sk_hynix_security():
    return security(ticker="000660", name="SK하이닉스")


def hyundai_security():
    return security(ticker="005380", name="현대자동차")


def response_with(items):
    return {"body": {"items": items}}


def item(
    title,
    description="",
    pub_date="Tue, 21 Jul 2026 09:00:00 +0900",
    originallink="https://news.example.com/article",
    link="https://mirror.example.com/article",
):
    return {
        "title": title,
        "description": description,
        "pubDate": pub_date,
        "originallink": originallink,
        "link": link,
    }


def fetch_docs(provider, selected_security=None, query=None, date_range=None):
    selected_security = selected_security or security()
    result = run(provider.fetch(selected_security, query=query, date_range=date_range))
    assert result.status == ProviderStatus.OK
    assert result.data is not None
    return result.data


def test_recorded_fixture_resolves_three_supported_securities():
    provider = RecordedNewsProvider(fixture_path=FIXTURE_PATH)

    samsung_docs = fetch_docs(provider, security())
    sk_docs = fetch_docs(provider, sk_hynix_security())
    hyundai_docs = fetch_docs(provider, hyundai_security())

    assert samsung_docs[0].provider == RECORDED_NEWS_PROVIDER_KEY
    assert samsung_docs[0].source_type == "news"
    assert samsung_docs[0].ingestion_version == NEWS_INGESTION_VERSION
    assert samsung_docs[0].published_at is not None
    assert samsung_docs[0].published_at.tzinfo == UTC
    assert samsung_docs[0].locator
    assert any(SK_HYNIX in doc.primary_security_ids for doc in sk_docs)
    assert hyundai_docs[0].source_url == "https://news.example.com/articles/hyundai-ev"


def test_query_seed_rules_prevent_duplicate_seed_and_reject_blank():
    lexicon = load_news_mention_lexicon()

    assert build_news_query(security(), None, lexicon) == "삼성전자"
    assert build_news_query(security(), "삼성전자 최근 실적", lexicon) == "삼성전자 최근 실적"
    assert build_news_query(security(), "삼전 최근 실적", lexicon) == "삼전 최근 실적"
    assert build_news_query(security(), "최근 실적", lexicon) == "삼성전자 최근 실적"

    provider = RecordedNewsProvider(recorded_response=response_with([]))
    result = run(provider.fetch(security(), query="   "))

    assert result.status == ProviderStatus.INVALID_QUERY
    assert result.error_code == "invalid_query"


def test_mismatched_security_identifier_is_invalid_query():
    provider = RecordedNewsProvider(recorded_response=response_with([]))
    mismatched = security(ticker="005930", name="SK하이닉스")

    result = run(provider.fetch(mismatched))

    assert result.status == ProviderStatus.INVALID_QUERY
    assert result.error_code == "invalid_query"


def test_document_id_is_deterministic_and_url_fragment_is_removed():
    recorded = response_with(
        [
            item(
                "삼성전자 실적 synthetic",
                originallink="https://news.example.com/path?a=1#fragment",
                link="https://mirror.example.com/path",
            )
        ]
    )
    provider = RecordedNewsProvider(recorded_response=recorded)

    first = fetch_docs(provider)[0]
    second = fetch_docs(provider)[0]

    assert first.document_id == second.document_id
    assert first.source_url == "https://news.example.com/path?a=1"


def test_document_id_is_deterministic_without_url():
    recorded = response_with(
        [
            item(
                "삼성전자 URL 없는 synthetic",
                originallink="",
                link="",
            )
        ]
    )
    provider = RecordedNewsProvider(recorded_response=recorded)

    first = fetch_docs(provider)[0]
    second = fetch_docs(provider)[0]

    assert first.document_id == second.document_id
    assert first.document_id.startswith("news:")
    assert first.source_url is None


def test_originallink_priority_and_link_fallback():
    recorded = response_with(
        [
            item(
                "삼성전자 originallink 우선",
                originallink="https://origin.example.com/a?x=1#frag",
                link="https://link.example.com/a",
            ),
            item(
                "삼성전자 link fallback",
                originallink="not-a-url",
                link="https://link.example.com/b?x=1#frag",
            ),
        ]
    )
    provider = RecordedNewsProvider(recorded_response=recorded)

    docs = fetch_docs(provider)

    assert docs[0].source_url == "https://origin.example.com/a?x=1"
    assert docs[1].source_url == "https://link.example.com/b?x=1"


def test_html_tag_entity_and_whitespace_cleanup():
    recorded = response_with(
        [
            item(
                "<b>삼성전자</b> &amp; SK하이닉스   협력",
                description="  <i>삼성전자</i> &gt; synthetic&nbsp;text  ",
            )
        ]
    )
    provider = RecordedNewsProvider(recorded_response=recorded)

    doc = fetch_docs(provider)[0]

    assert doc.title == "삼성전자 & SK하이닉스 협력"
    assert "삼성전자 > synthetic text" in doc.text
    assert "<" not in doc.text
    assert "&amp;" not in doc.text


def test_malformed_items_are_excluded_but_valid_items_remain_ok():
    recorded = response_with(
        [
            item("", pub_date="Tue, 21 Jul 2026 09:00:00 +0900"),
            item("삼성전자 malformed date", pub_date="not-a-date"),
            item("삼성전자 valid synthetic", pub_date="Tue, 21 Jul 2026 10:00:00 +0900"),
        ]
    )
    provider = RecordedNewsProvider(recorded_response=recorded)

    docs = fetch_docs(provider)

    assert len(docs) == 1
    assert docs[0].title == "삼성전자 valid synthetic"


@pytest.mark.parametrize(
    "recorded",
    [
        {"body": {"items": [item("", pub_date="bad")]}},
        {"body": {"items": "not-list"}},
        {"body": {}},
        {},
    ],
)
def test_all_malformed_or_schema_error_is_parse_error(recorded):
    provider = RecordedNewsProvider(recorded_response=recorded)

    result = run(provider.fetch(security()))

    assert result.status == ProviderStatus.PARSE_ERROR
    assert result.error_code == "parse_error"


def test_empty_items_is_no_data():
    provider = RecordedNewsProvider(recorded_response=response_with([]))

    result = run(provider.fetch(security()))

    assert result.status == ProviderStatus.NO_DATA
    assert result.data is None


def test_date_range_filters_by_asia_seoul_date_inclusively():
    recorded = response_with(
        [
            item("삼성전자 before range", pub_date="Mon, 20 Jul 2026 23:59:00 +0900", originallink="https://n.example.com/before"),
            item("삼성전자 start boundary", pub_date="Tue, 21 Jul 2026 00:00:00 +0900", originallink="https://n.example.com/start"),
            item("삼성전자 end boundary", pub_date="Tue, 21 Jul 2026 23:59:00 +0900", originallink="https://n.example.com/end"),
            item("삼성전자 after range", pub_date="Wed, 22 Jul 2026 00:00:00 +0900", originallink="https://n.example.com/after"),
        ]
    )
    provider = RecordedNewsProvider(recorded_response=recorded)

    docs = fetch_docs(provider, date_range=DateRange(start=date(2026, 7, 21), end=date(2026, 7, 21)))

    assert [doc.title for doc in docs] == ["삼성전자 start boundary", "삼성전자 end boundary"]


def test_date_range_filter_with_no_remaining_documents_is_no_data():
    recorded = response_with([item("삼성전자 outside", pub_date="Mon, 20 Jul 2026 23:59:00 +0900")])
    provider = RecordedNewsProvider(recorded_response=recorded)

    result = run(provider.fetch(security(), date_range=DateRange(start=date(2026, 7, 21), end=date(2026, 7, 21))))

    assert result.status == ProviderStatus.NO_DATA


def test_joint_title_makes_both_supported_companies_primary():
    recorded = response_with([item("삼성전자 SK하이닉스 공동 synthetic", description="삼성전자와 SK하이닉스 설명")])
    provider = RecordedNewsProvider(recorded_response=recorded)

    doc = fetch_docs(provider)[0]

    assert doc.primary_security_ids == [SK_HYNIX, SAMSUNG]
    assert doc.mentioned_security_ids == []


def test_description_only_mentions_are_mentioned_not_primary():
    recorded = response_with([item("반도체 synthetic 업황", description="삼성전자 관련 설명")])
    provider = RecordedNewsProvider(recorded_response=recorded)

    doc = fetch_docs(provider)[0]

    assert doc.primary_security_ids == []
    assert doc.mentioned_security_ids == [SAMSUNG]


def test_wrong_company_title_is_excluded_when_query_security_only_in_description():
    recorded = response_with([item("SK하이닉스 투자 synthetic", description="삼성전자도 설명에만 언급")])
    provider = RecordedNewsProvider(recorded_response=recorded)

    result = run(provider.fetch(security()))

    assert result.status == ProviderStatus.NO_DATA


def test_ambiguous_group_name_only_article_is_excluded():
    recorded = response_with([item("삼성 synthetic 그룹 이슈", description="그룹명만 있는 기사")])
    provider = RecordedNewsProvider(recorded_response=recorded)

    result = run(provider.fetch(security()))

    assert result.status == ProviderStatus.NO_DATA


def test_deduplicates_by_canonical_url_and_keeps_first_api_item():
    recorded = response_with(
        [
            item("삼성전자 first duplicate", originallink="https://dup.example.com/a#one"),
            item("삼성전자 second duplicate", originallink="https://dup.example.com/a#two"),
        ]
    )
    provider = RecordedNewsProvider(recorded_response=recorded)

    docs = fetch_docs(provider)

    assert len(docs) == 1
    assert docs[0].title == "삼성전자 first duplicate"


@pytest.mark.parametrize(
    ("fixture_status", "expected_error_code"),
    [
        (ProviderStatus.TIMEOUT, "attempt_timeout"),
        (ProviderStatus.RATE_LIMITED, "rate_limited"),
        (ProviderStatus.UNAUTHORIZED, "unauthorized"),
        (ProviderStatus.PROVIDER_UNAVAILABLE, "provider_unavailable"),
    ],
)
def test_recorded_status_mapping_for_failures(fixture_status, expected_error_code):
    provider = RecordedNewsProvider(recorded_response=response_with([]), fixture_status=fixture_status)

    result = run(provider.fetch(security()))

    assert result.status == fixture_status
    assert result.error_code == expected_error_code
    assert result.data is None


def test_identical_fixture_reruns_produce_identical_document_payloads():
    recorded = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    provider = RecordedNewsProvider(recorded_response=recorded)

    first = [doc.model_dump() for doc in fetch_docs(provider)]
    second = [doc.model_dump() for doc in fetch_docs(provider)]

    assert first == second
