from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.api.schemas import ChatRequest
from app.core.models import Evidence, FinancialDocument, RetrievalRequest
from app.retrieval import filter_evidence, filter_financial_documents
from app.runtime import RuntimeConfig, build_runtime
from app.services.chat_service import ChatService
from app.services.market_snapshot_schema import (
    SECURITIES,
    checkpoint_matrix,
)
from app.services.market_snapshot_store import RecordedMarketSnapshotStore
from app.services.session_store import InMemorySessionStore

KST = ZoneInfo("Asia/Seoul")


def test_all_sixty_recorded_price_cases_resolve_without_future_observation() -> None:
    store = RecordedMarketSnapshotStore()

    for security_id, _ticker, _name in SECURITIES:
        for as_of in checkpoint_matrix():
            snapshot = store.get(
                security_id=security_id,
                as_of=as_of,
            )
            assert snapshot is not None
            assert snapshot.requested_as_of == as_of
            assert snapshot.observed_at <= as_of
            assert snapshot.checkpoint_id == as_of.strftime(
                "%Y%m%dT%H%MKST"
            )


def test_weekend_checkpoint_keeps_last_real_friday_observation() -> None:
    store = RecordedMarketSnapshotStore()

    snapshot = store.get(
        security_id="KRX:005930",
        as_of=datetime(2026, 7, 25, 8, 30, tzinfo=KST),
    )

    assert snapshot is not None
    assert snapshot.market_status == "closed"
    assert snapshot.market_session == "closed"
    assert snapshot.observed_at == datetime(
        2026,
        7,
        24,
        19,
        59,
        tzinfo=KST,
    )


def test_price_answer_exposes_selected_and_actual_observation_times() -> None:
    service = ChatService(
        market_snapshot_store=RecordedMarketSnapshotStore(),
    )

    response = asyncio.run(
        service.chat(
            ChatRequest(
                message="삼성전자 현재 주가 얼마야?",
                session_id="m5-price-answer",
                as_of=datetime(2026, 7, 24, 21, 0, tzinfo=KST),
            )
        )
    )

    assert response.status == "complete"
    assert response.diagnostics_public.query_plan.intent == "price"
    assert response.basis_at == datetime(
        2026,
        7,
        24,
        12,
        0,
        tzinfo=ZoneInfo("UTC"),
    )
    assert response.market_snapshot is not None
    assert response.market_snapshot.checkpoint_id == "20260724T2100KST"
    assert response.market_snapshot.observed_at == datetime(
        2026,
        7,
        24,
        19,
        59,
        tzinfo=KST,
    )
    assert response.market_snapshot.price == 252_500
    assert "252,500원" in response.answer_sections.summary[0]


def test_as_of_hard_filter_includes_boundary_and_excludes_one_second_after() -> None:
    as_of = datetime(2026, 7, 24, 14, 0, tzinfo=KST)
    boundary = as_of
    future = as_of + timedelta(seconds=1)
    request = RetrievalRequest(
        query="삼성전자",
        security_id="KRX:005930",
        source_types=["news"],
        as_of=as_of,
    )
    documents = [
        _document("boundary", boundary),
        _document("future", future),
        _document("missing", None),
    ]
    evidence = [
        _evidence("boundary", boundary),
        _evidence("future", future),
        _evidence("missing", None),
    ]
    documents_by_id = {
        item.document_id: item for item in documents
    }

    filtered_documents = filter_financial_documents(documents, request)
    filtered_evidence = filter_evidence(
        evidence,
        request,
        documents_by_id=documents_by_id,
    )

    assert [item.document_id for item in filtered_documents] == [
        "doc:boundary"
    ]
    assert [item.evidence_id for item in filtered_evidence] == [
        "ev:boundary"
    ]


def test_changing_checkpoint_partitions_anonymous_session_state() -> None:
    sessions = InMemorySessionStore()
    service = ChatService(
        market_snapshot_store=RecordedMarketSnapshotStore(),
        session_store=sessions,
    )

    for hour in (10, 14):
        asyncio.run(
            service.chat(
                ChatRequest(
                    message="삼성전자 주가 알려줘",
                    session_id="same-public-session",
                    as_of=datetime(
                        2026,
                        7,
                        24,
                        hour,
                        0,
                        tzinfo=KST,
                    ),
                )
            )
        )

    assert sessions.size == 2


def test_runtime_price_move_uses_only_news_available_by_checkpoint() -> None:
    service = build_runtime(
        config=RuntimeConfig(
            source_mode="recorded",
            snapshot_id="svc-20260724-1402",
        )
    ).chat_service
    as_of = datetime(2026, 7, 27, 14, 0, tzinfo=KST)

    response = asyncio.run(
        service.chat(
            ChatRequest(
                message="삼성전자 오늘 왜 올랐어?",
                session_id="m5-price-move-news",
                as_of=as_of,
            )
        )
    )

    assert response.diagnostics_public.query_plan.intent == "price_move"
    assert response.market_snapshot is not None
    assert response.evidence
    assert all(
        item.published_at is not None
        and item.published_at <= response.basis_at
        for item in response.evidence
    )
    assert all(
        "292조 브로드컴 동맹" not in item.title
        for item in response.evidence
    )


def _document(
    suffix: str,
    published_at: datetime | None,
) -> FinancialDocument:
    return FinancialDocument(
        document_id=f"doc:{suffix}",
        source_type="news",
        provider="test",
        primary_security_ids=["KRX:005930"],
        mentioned_security_ids=[],
        title=f"title {suffix}",
        published_at=published_at,
        source_url=f"https://example.test/{suffix}",
        text="삼성전자 관련 근거",
        locator={"provider": "test", "source": suffix},
        metadata={},
        ingestion_version="test-v1",
    )


def _evidence(
    suffix: str,
    published_at: datetime | None,
) -> Evidence:
    return Evidence(
        evidence_id=f"ev:{suffix}",
        document_id=f"doc:{suffix}",
        source_type="news",
        title=f"title {suffix}",
        published_at=published_at,
        source_url=f"https://example.test/{suffix}",
        subject_security_ids=["KRX:005930"],
        mentioned_security_ids=[],
        scope="company_specific",
        snippet="삼성전자 관련 근거",
        locator={"provider": "test", "source": suffix},
    )
