from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from app.core.models import (
    DateRange,
    Evidence,
    FinancialAnswer,
    FinancialDocument,
    MarketSnapshot,
    ProviderResult,
    QueryPlan,
    RetrievalRequest,
    RetrievalResult,
    SecurityIdentifier,
    SessionContext,
    ensure_evidence_matches_document,
)
from app.core.status import EvidenceDecisionStatus, ProviderStatus, RetrievalStatus

SAMSUNG = "KRX:005930"
SK_HYNIX = "KRX:000660"
HYUNDAI = "KRX:005380"


def make_document(**overrides):
    payload = {
        "document_id": "news-joint-hbm-001",
        "source_type": "news",
        "provider": "fixture",
        "primary_security_ids": [SAMSUNG],
        "mentioned_security_ids": [SK_HYNIX],
        "title": "HBM supply update",
        "published_at": datetime(2026, 7, 21, 9, 0, tzinfo=timezone.utc),
        "source_url": "https://example.com/news/hbm",
        "text": "Samsung Electronics and SK hynix were mentioned in the same article.",
        "locator": {"url": "https://example.com/news/hbm"},
        "metadata": {},
        "ingestion_version": "fixture-v1",
    }
    payload.update(overrides)
    return FinancialDocument(**payload)


def make_evidence(**overrides):
    payload = {
        "evidence_id": "ev-samsung-hbm-001",
        "document_id": "news-joint-hbm-001",
        "source_type": "news",
        "title": "HBM supply update",
        "source_url": "https://example.com/news/hbm",
        "published_at": datetime(2026, 7, 21, 9, 0, tzinfo=timezone.utc),
        "subject_security_ids": [SAMSUNG],
        "mentioned_security_ids": [SK_HYNIX],
        "scope": "company_specific",
        "snippet": "Samsung Electronics announced its HBM supply update.",
        "locator": {"url": "https://example.com/news/hbm", "paragraph": 3},
        "retrieval_score": 0.91,
    }
    payload.update(overrides)
    return Evidence(**payload)


def assert_json_round_trip(model):
    restored = type(model).model_validate_json(model.model_dump_json())
    assert restored == model


def test_security_identifier_serializes_stock_identity():
    security = SecurityIdentifier(
        market="KRX",
        ticker="000660",
        security_name="SK하이닉스",
        security_type="common_stock",
        corp_code="00164779",
        corp_name="에스케이하이닉스(주)",
    )

    assert security.model_dump()["ticker"] == "000660"


def test_all_core_models_json_round_trip():
    security = SecurityIdentifier(
        market="KRX",
        ticker="005930",
        security_name="Samsung Electronics",
        security_type="common_stock",
        corp_code="00126380",
        corp_name="Samsung Electronics Co., Ltd.",
    )
    date_range = DateRange(start=date(2026, 7, 1), end=date(2026, 7, 21))
    document = make_document()
    evidence = make_evidence()
    market_snapshot = MarketSnapshot(
        security_id=SAMSUNG,
        trading_date=date(2026, 7, 21),
        observed_at=datetime(2026, 7, 21, 6, 0, tzinfo=timezone.utc),
        price=70000,
        previous_close=69000,
        change=1000,
        change_percent=1.45,
        volume=1234567,
        market_session="regular",
        currency="KRW",
        source="fixture",
    )
    query_plan = QueryPlan(
        security=security,
        intent="recent_issue",
        date_range=date_range,
        required_sources=["news"],
        required_evidence=["company_specific_news"],
        requires_clarification=False,
    )
    provider_result = ProviderResult[dict](
        status=ProviderStatus.OK,
        data={"document_count": 1},
        error_code=None,
        message=None,
        fetched_at=datetime(2026, 7, 21, 6, 1, tzinfo=timezone.utc),
        from_cache=False,
    )
    retrieval_request = RetrievalRequest(
        query="Samsung Electronics recent issue",
        security_id=SAMSUNG,
        source_types=["news"],
        date_range=date_range,
        document_types=None,
        top_k=6,
    )
    retrieval_result = RetrievalResult(
        evidence=[evidence],
        status=RetrievalStatus.OK,
        strategy="fixture",
        low_relevance=False,
        diagnostics={"candidate_count": 1},
    )
    session_context = SessionContext(
        current_security_id=SAMSUNG,
        current_date_range=date_range,
        previous_intent="recent_issue",
        previous_source_types=["news"],
    )
    answer = FinancialAnswer(
        answer="Fixture answer",
        status=EvidenceDecisionStatus.PARTIAL,
        security=security,
        basis_date=datetime(2026, 7, 21, 6, 2, tzinfo=timezone.utc),
        evidence=[evidence],
        warnings=["fixture warning"],
        missing_sources=["disclosure"],
    )

    for model in [
        security,
        date_range,
        query_plan,
        market_snapshot,
        document,
        evidence,
        provider_result,
        retrieval_request,
        retrieval_result,
        session_context,
        answer,
    ]:
        assert_json_round_trip(model)


def test_date_range_rejects_reversed_dates():
    with pytest.raises(ValidationError):
        DateRange(start=date(2026, 7, 22), end=date(2026, 7, 21))


def test_financial_document_allows_nullable_source_url_and_required_locator():
    document = make_document(source_url=None, locator={"manifest_id": "report-samsung-001", "page": 3})

    assert document.source_url is None
    assert document.locator["page"] == 3


def test_financial_document_rejects_empty_security_union():
    with pytest.raises(ValidationError):
        make_document(primary_security_ids=[], mentioned_security_ids=[])


def test_financial_document_rejects_primary_mentioned_overlap():
    with pytest.raises(ValidationError):
        make_document(primary_security_ids=[SAMSUNG], mentioned_security_ids=[SAMSUNG])


def test_financial_document_rejects_internal_duplicate_security_ids():
    with pytest.raises(ValidationError):
        make_document(primary_security_ids=[SAMSUNG, SAMSUNG], mentioned_security_ids=[])

    with pytest.raises(ValidationError):
        make_document(primary_security_ids=[], mentioned_security_ids=[SK_HYNIX, SK_HYNIX])


def test_financial_document_rejects_empty_locator():
    with pytest.raises(ValidationError):
        make_document(locator={})


def test_financial_document_rejects_local_absolute_path_locator():
    with pytest.raises(ValidationError):
        make_document(locator={"path": r"C:\Users\USER\Questock\reports\secret.pdf"})


@pytest.mark.parametrize("path", ["/root/secret.pdf", "/opt/data.json", "/workspace/report.md", "/etc/passwd"])
def test_financial_document_rejects_posix_absolute_path_locator(path):
    with pytest.raises(ValidationError):
        make_document(locator={"path": path})


def test_financial_document_rejects_local_absolute_path_source_url():
    with pytest.raises(ValidationError):
        make_document(source_url=r"C:\Users\USER\Questock\reports\secret.pdf")


def test_company_specific_evidence_requires_exactly_one_subject():
    assert make_evidence(subject_security_ids=[SAMSUNG]).subject_security_ids == [SAMSUNG]

    with pytest.raises(ValidationError):
        make_evidence(subject_security_ids=[])

    with pytest.raises(ValidationError):
        make_evidence(subject_security_ids=[SAMSUNG, SK_HYNIX])


def test_sk_hynix_company_specific_evidence_fixture():
    document = make_document(
        document_id="news-sk-hbm-001",
        primary_security_ids=[SK_HYNIX],
        mentioned_security_ids=[],
        title="SK hynix HBM supply update",
        text="SK hynix announced its HBM supply update.",
        locator={"url": "https://example.com/news/sk-hbm"},
    )
    evidence = make_evidence(
        evidence_id="ev-sk-hbm-001",
        document_id="news-sk-hbm-001",
        title="SK hynix HBM supply update",
        subject_security_ids=[SK_HYNIX],
        mentioned_security_ids=[],
        scope="company_specific",
        snippet="SK hynix announced its HBM supply update.",
        locator={"url": "https://example.com/news/sk-hbm", "paragraph": 2},
    )

    ensure_evidence_matches_document(evidence, document)
    assert evidence.subject_security_ids == [SK_HYNIX]


def test_industry_common_evidence_requires_empty_subjects():
    evidence = make_evidence(
        evidence_id="ev-industry-001",
        subject_security_ids=[],
        mentioned_security_ids=[SAMSUNG, SK_HYNIX],
        scope="industry_common",
        snippet="Demand for HBM increased across the memory industry.",
    )

    assert evidence.subject_security_ids == []

    with pytest.raises(ValidationError):
        make_evidence(subject_security_ids=[SAMSUNG], scope="industry_common")


def test_multi_company_evidence_requires_two_or_more_subjects():
    evidence = make_evidence(
        evidence_id="ev-multi-001",
        subject_security_ids=[SAMSUNG, SK_HYNIX],
        mentioned_security_ids=[],
        scope="multi_company",
        snippet="Samsung Electronics and SK hynix both expanded HBM capacity.",
    )

    assert evidence.subject_security_ids == [SAMSUNG, SK_HYNIX]

    with pytest.raises(ValidationError):
        make_evidence(subject_security_ids=[SAMSUNG], scope="multi_company")


def test_evidence_rejects_subject_mentioned_overlap():
    with pytest.raises(ValidationError):
        make_evidence(subject_security_ids=[SAMSUNG], mentioned_security_ids=[SAMSUNG])


def test_evidence_rejects_internal_duplicate_security_ids():
    with pytest.raises(ValidationError):
        make_evidence(subject_security_ids=[SAMSUNG, SAMSUNG], mentioned_security_ids=[])

    with pytest.raises(ValidationError):
        make_evidence(
            subject_security_ids=[SAMSUNG],
            mentioned_security_ids=[SK_HYNIX, SK_HYNIX],
        )


def test_evidence_rejects_empty_locator_and_local_path():
    with pytest.raises(ValidationError):
        make_evidence(locator={})

    with pytest.raises(ValidationError):
        make_evidence(locator={"path": r"C:\tmp\fixture.json"})


@pytest.mark.parametrize("path", ["/root/fixture.json", "/opt/fixture.json", "/workspace/fixture.json", "/tmp/fixture.json"])
def test_evidence_rejects_posix_absolute_path_locator(path):
    with pytest.raises(ValidationError):
        make_evidence(locator={"path": path})


def test_evidence_must_match_linked_document_security_scope():
    document = make_document()
    evidence = make_evidence()

    ensure_evidence_matches_document(evidence, document)

    invalid_evidence = make_evidence(
        evidence_id="ev-hyundai-001",
        subject_security_ids=[HYUNDAI],
        mentioned_security_ids=[],
    )

    with pytest.raises(ValueError):
        ensure_evidence_matches_document(invalid_evidence, document)


def test_evidence_must_match_linked_document_id():
    document = make_document()
    evidence = make_evidence(document_id="other-doc")

    with pytest.raises(ValueError):
        ensure_evidence_matches_document(evidence, document)


def test_provider_result_serializes_status_value():
    result = ProviderResult[dict](
        status=ProviderStatus.TIMEOUT,
        data=None,
        error_code="timeout",
        message="provider timed out",
        fetched_at=datetime(2026, 7, 21, 9, 0, tzinfo=timezone.utc),
        from_cache=False,
    )

    assert result.model_dump()["status"] == "timeout"
