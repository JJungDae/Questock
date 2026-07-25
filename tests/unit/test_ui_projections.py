from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from app.answer.models import AnswerSections
from app.api.schemas import ChatRequest
from app.core.models import Evidence
from app.services.chat_service import ChatService
from app.ui.projections import (
    ProjectionError,
    project_baseline_answer,
    project_baseline_sources,
    project_process_stages,
)

NOW = datetime(2026, 7, 25, 3, tzinfo=UTC)


def _response():
    return asyncio.run(
        ChatService(utc_now=lambda: NOW).chat(
            ChatRequest(
                message="삼성전자 최근 뉴스",
                session_id="ui-projection-unit",
            )
        )
    )


def test_baseline_answer_consumes_only_frozen_public_fields() -> None:
    response = _response()

    view = project_baseline_answer(response)

    assert view.status == response.status
    assert view.status_label == "자료 제공 실패"
    assert view.security_name == response.security.security_name
    assert view.basis_date == response.basis_date.isoformat()
    assert view.summary == tuple(response.answer_sections.summary)
    assert view.warnings == tuple(response.warnings)
    assert view.missing_sources == ("뉴스",)


def test_answer_cards_have_exact_order_labels_and_hide_empty_sections() -> None:
    response = _response().model_copy(
        deep=True,
        update={
            "status": "complete",
            "answer_sections": AnswerSections(
                summary=["결론"],
                facts=["사실"],
                interpretation=["중요성"],
                positive_factors=["긍정"],
                risk_factors=["위험"],
                inference=["추론"],
                uncertainty=["추가 확인"],
            ),
        },
    )

    cards = project_baseline_answer(response).cards

    assert [(item.key, item.title) for item in cards] == [
        ("summary", "한 줄 결론"),
        ("facts", "확인된 사실"),
        ("interpretation", "왜 중요한가"),
        ("positive_factors", "긍정 요인"),
        ("risk_factors", "확인된 위험"),
        ("inference", "AI 정리·추론"),
        ("uncertainty", "더 확인할 것"),
    ]
    assert all(item.emphasis == "normal" for item in cards)

    empty_hidden = response.model_copy(
        deep=True,
        update={
            "answer_sections": AnswerSections(summary=["결론"]),
        },
    )
    assert [
        item.key for item in project_baseline_answer(empty_hidden).cards
    ] == ["summary"]


def test_failure_answer_uses_fixed_wording_and_red_fallback() -> None:
    response = _response().model_copy(
        deep=True,
        update={
            "warnings": [
                "request_deadline_exceeded",
                "llm_generation_degraded",
                "unknown-warning",
            ],
        },
    )

    view = project_baseline_answer(response)

    assert view.status_label == "자료 제공 실패"
    assert view.cards[0].key == "summary"
    assert view.cards[0].emphasis == "error"
    assert view.warnings == (
        "전체 요청 시간 제한에 도달함",
        "AI 정리 대신 근거 기반 고정 응답 사용",
        "추가 확인이 필요함",
    )
    assert "request_deadline_exceeded" not in repr(view)


def test_baseline_source_projection_does_not_expose_locator_or_ids() -> None:
    response = _response()

    views = project_baseline_sources(response)
    serialized = repr(views).casefold()

    assert "locator" not in serialized
    assert "evidence_id" not in serialized
    assert "document_id" not in serialized


def test_source_projection_shows_only_type_specific_safe_details() -> None:
    response = _response().model_copy(
        deep=True,
        update={
            "evidence": [
                _evidence(
                    "news",
                    locator={
                        "provider": "recorded_news",
                        "query": "private query",
                        "raw_index": 3,
                    },
                    source_url="https://news.example.test/article",
                ),
                _evidence(
                    "disclosure",
                    locator={
                        "receipt_no": "20260725000001",
                        "report_name": "분기보고서",
                        "section": "재무사항",
                        "corp_code": "00126380",
                    },
                    source_url=(
                        "https://dart.fss.or.kr/dsaf001/main.do"
                        "?rcpNo=20260725000001"
                    ),
                ),
                _evidence(
                    "research_report",
                    locator={
                        "publisher": "승인 리서치",
                        "manifest_id": "report-samsung-001",
                        "document_id": "report:samsung:001:page-2",
                        "page": 2,
                        "section": "실적 전망",
                        "access_note": "private note",
                    },
                    source_url=None,
                ),
                _evidence(
                    "glossary",
                    locator={
                        "entry_id": "glossary:per",
                        "version": 1,
                        "section": "definition",
                        "permission_note": "private permission",
                    },
                    source_url=None,
                ),
            ],
        },
    )

    views = project_baseline_sources(response)

    assert [item.source_label for item in views] == [
        "뉴스",
        "공시",
        "리서치 리포트",
        "금융 용어",
    ]
    assert views[0].details == (
        type(views[0].details[0])("제공자", "recorded_news"),
    )
    assert views[0].link_url == "https://news.example.test/article"
    assert [item.label for item in views[1].details] == [
        "접수번호",
        "보고서",
        "구간",
    ]
    assert [item.label for item in views[2].details] == [
        "발행기관",
        "매니페스트",
        "문서 ID",
        "페이지",
        "구간",
    ]
    assert [item.label for item in views[3].details] == [
        "항목 ID",
        "버전",
        "구간",
    ]
    serialized = repr(views)
    for forbidden in (
        "private query",
        "raw_index",
        "corp_code",
        "access_note",
        "permission_note",
        "private permission",
    ):
        assert forbidden not in serialized


@pytest.mark.parametrize(
    "source_url",
    [
        "https://user:password@example.test/article",
        "https://example.test/article?api-key=credential-sentinel",
        "https://example.test/article?%58-Amz-Signature=credential-sentinel",
        "https://example.test/article#fragment",
        "file:///C:/private/article",
    ],
)
def test_unsafe_source_url_is_hidden(source_url: str) -> None:
    item = _evidence(
        "news",
        locator={"provider": "recorded_news"},
        source_url="https://news.example.test/safe",
    ).model_copy(update={"source_url": source_url})
    response = _response().model_copy(update={"evidence": [item]})

    view = project_baseline_sources(response)[0]

    assert view.link_url is None
    assert "credential-sentinel" not in repr(view)


def test_unsafe_dynamic_text_is_replaced_without_raw_path_or_secret() -> None:
    item = _evidence(
        "research_report",
        locator={
            "publisher": "Approved Research",
            "manifest_id": "report-001",
            "document_id": "report:001:page-1",
            "page": 1,
            "section": "Overview",
        },
        source_url=None,
    ).model_copy(
        update={
            "title": "/mnt/data/private/report",
            "snippet": "<script>alert('safe text rendering')</script>",
            "locator": {
                "publisher": "C:\\Users\\private\\report",
                "manifest_id": "report-001",
                "document_id": "report:001:page-1",
                "page": 1,
                "section": "api_key=credential-sentinel",
            },
        }
    )
    response = _response().model_copy(update={"evidence": [item]})

    view = project_baseline_sources(response)[0]

    assert view.title == "안전하게 표시할 수 없는 내용입니다."
    assert view.snippet == "<script>alert('safe text rendering')</script>"
    assert [item.label for item in view.details] == [
        "매니페스트",
        "문서 ID",
        "페이지",
    ]
    assert "credential-sentinel" not in repr(view)
    assert "C:\\Users" not in repr(view)
    assert "/mnt/data" not in repr(view)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("title", "/tmp"),
        ("snippet", "/etc"),
        ("publisher", "/home"),
        ("section", "file:///private"),
        ("title", "C:\\private\\report"),
        ("snippet", "\\\\server\\share\\report"),
        ("publisher", "//server/share/report"),
    ],
)
def test_local_path_variants_are_hidden_from_source_projection(
    field: str,
    value: str,
) -> None:
    item = _evidence(
        "research_report",
        locator={
            "publisher": "Approved Research",
            "manifest_id": "report-001",
            "document_id": "report:001:page-1",
            "page": 1,
            "section": "Overview",
        },
        source_url=None,
    )
    if field in {"title", "snippet"}:
        item = item.model_copy(update={field: value})
    else:
        locator = dict(item.locator)
        locator[field] = value
        item = item.model_copy(update={"locator": locator})
    response = _response().model_copy(update={"evidence": [item]})

    view = project_baseline_sources(response)[0]

    assert value not in repr(view)
    if field in {"title", "snippet"}:
        assert getattr(view, field) == "안전하게 표시할 수 없는 내용입니다."
    else:
        assert all(detail.label != {
            "publisher": "발행기관",
            "section": "구간",
        }[field] for detail in view.details)


def test_safe_slash_prose_and_markdown_metadata_remain_literal_text() -> None:
    item = _evidence(
        "research_report",
        locator={
            "publisher": "[공식 문서](https://unapproved.example)",
            "manifest_id": "report-001",
            "document_id": "report:001:page-1",
            "page": 1,
            "section": "![이미지](https://unapproved.example)",
        },
        source_url=None,
    ).model_copy(update={"snippet": "profit / loss"})
    response = _response().model_copy(update={"evidence": [item]})

    view = project_baseline_sources(response)[0]

    assert view.snippet == "profit / loss"
    assert [item.value for item in view.details if item.label in {
        "발행기관",
        "구간",
    }] == [
        "[공식 문서](https://unapproved.example)",
        "![이미지](https://unapproved.example)",
    ]


def test_markdown_directives_in_metadata_are_preserved_only_as_plain_values() -> None:
    item = _evidence(
        "research_report",
        locator={
            "publisher": ":red[경고]",
            "manifest_id": "report-001",
            "document_id": "report:001:page-1",
            "page": 1,
            "section": ":material/open_in_new:",
        },
        source_url=None,
    )
    response = _response().model_copy(update={"evidence": [item]})

    view = project_baseline_sources(response)[0]

    assert [item.value for item in view.details if item.label in {
        "발행기관",
        "구간",
    }] == [":red[경고]", ":material/open_in_new:"]


def test_unknown_source_type_fails_with_sanitized_projection_error() -> None:
    item = _evidence(
        "news",
        locator={"provider": "recorded_news"},
        source_url=None,
    ).model_copy(update={"source_type": "credential-sentinel"})
    response = _response().model_copy(update={"evidence": [item]})

    with pytest.raises(ProjectionError) as error:
        project_baseline_sources(response)

    assert str(error.value) == "근거를 화면에 표시할 수 없습니다."
    assert "credential-sentinel" not in str(error.value)


def test_unknown_missing_source_uses_fixed_safe_label() -> None:
    response = _response().model_copy(
        update={"missing_sources": ["credential-sentinel"]}
    )

    view = project_baseline_answer(response)

    assert view.missing_sources == ("기타 자료",)
    assert "credential-sentinel" not in repr(view)


def test_process_stage_order_and_status_families_are_exact() -> None:
    summary = _response().diagnostics_public

    stages = project_process_stages(summary)

    assert [stage.key for stage in stages] == [
        "security",
        "query_plan",
        "sources",
        "filtering",
        "retrieval",
        "decision",
        "context_budget",
        "citation",
        "generation",
    ]
    serialized = repr(stages)
    assert "종목 확인 완료" in serialized
    assert "자료 제공 경로가 구성되지 않았거나 이용 불가" in serialized
    assert "관련 근거 없음" in serialized
    assert "자료 제공 실패" in serialized
    assert "AI 호출 없음" in serialized
    assert "provider_unavailable" not in serialized
    assert "not_called" not in serialized


def test_process_projection_excludes_private_content() -> None:
    serialized = repr(
        project_process_stages(_response().diagnostics_public)
    ).casefold()

    for forbidden in (
        "삼성전자 최근 뉴스",
        "prompt",
        "reasoning",
        "locator",
        "snippet",
        "api_key",
        "permission",
        "exception",
    ):
        assert forbidden.casefold() not in serialized


def test_unknown_trace_version_fails_safely() -> None:
    summary = _response().diagnostics_public.model_copy(
        update={"trace_version": "m3-unknown"}
    )

    with pytest.raises(ProjectionError) as error:
        project_process_stages(summary)

    assert "m3-unknown" not in str(error.value)


def _evidence(
    source_type: str,
    *,
    locator: dict[str, object],
    source_url: str | None,
) -> Evidence:
    return Evidence(
        evidence_id=f"evidence:{source_type}:ui",
        document_id=f"document:{source_type}:ui",
        source_type=source_type,
        title=f"{source_type} title",
        source_url=source_url,
        published_at=NOW,
        subject_security_ids=(
            [] if source_type == "glossary" else ["KRX:005930"]
        ),
        mentioned_security_ids=[],
        scope=(
            "industry_common"
            if source_type == "glossary"
            else "company_specific"
        ),
        snippet=f"{source_type} snippet",
        locator=locator,
        retrieval_score=1.0,
    )
