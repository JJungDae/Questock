from __future__ import annotations

import hashlib
import html
import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.services.m5_d1_evidence_comparison import StoredComparisonPayload
from app.services.m5_d1_report_inventory import (
    validate_report_inventory_payload,
)

_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_SOURCE_INVENTORY = (
    _ROOT
    / "var"
    / "service_completion"
    / "m5_d1"
    / "inventory"
    / "m5_d1_source_inventory.json"
)
_DEFAULT_REPORT_INVENTORY = _ROOT / "data" / "m5_d1_report_inventory.json"
_DEFAULT_SERVICE_DOCUMENTS = (
    _ROOT
    / "data"
    / "service_snapshot"
    / "svc-20260724-1402"
    / "documents.json"
)
_DEFAULT_OUTPUT = _ROOT / "data" / "m5_d1_evidence_comparisons.json"
_TAG = re.compile(r"<[^>]+>")
_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9.+-]*|[가-힣]{2,}")
_STOP = frozenset(
    {
        "삼성전자",
        "sk하이닉스",
        "하이닉스",
        "현대차",
        "현대자동차",
        "관련",
        "대한",
        "으로",
        "에서",
        "한다",
        "전망",
        "주가",
        "증시",
        "코스피",
        "기업",
        "시장",
        "올해",
        "내년",
        "한국",
        "국내",
        "글로벌",
        "가능성",
        "강화",
        "본격",
    }
)
_PHRASES = {
    "hbm5": "hbm5",
    "hbm4": "hbm4",
    "2나노": "2나노",
    "2분기": "2분기",
    "3분기": "3분기",
    "실적": "실적",
    "로봇": "로봇",
    "피지컬 ai": "피지컬ai",
    "관세": "관세",
    "생산차질": "생산차질",
    "생산 차질": "생산차질",
    "생산중단": "생산중단",
    "생산 중단": "생산중단",
    "배당": "배당",
    "자사주": "자사주",
    "adr": "adr",
    "구글": "구글",
    "아이폰": "아이폰",
    "파운드리": "파운드리",
    "브로드컴": "브로드컴",
    "반도체": "반도체",
    "fomc": "fomc",
    "엔비디아": "엔비디아",
    "웨이모": "웨이모",
    "보스턴다이내믹스": "보스턴다이내믹스",
    "파업": "파업",
    "목표가": "목표가",
    "etf": "etf",
    "d램": "d램",
    "메모리": "메모리",
}
_DISTINCTIVE = frozenset(
    {
        "hbm5",
        "hbm4",
        "2나노",
        "2분기",
        "로봇",
        "피지컬ai",
        "관세",
        "생산차질",
        "생산중단",
        "배당",
        "자사주",
        "adr",
        "구글",
        "아이폰",
        "파운드리",
        "브로드컴",
        "fomc",
        "엔비디아",
        "웨이모",
        "보스턴다이내믹스",
        "파업",
        "목표가",
        "etf",
        "d램",
    }
)
_CATEGORY_TOPICS = {
    "consolidated_revenue": ["실적", "매출"],
    "consolidated_operating_profit": ["실적", "영업이익"],
    "major_segment_revenue": ["실적", "매출"],
    "major_segment_profit": ["실적", "영업이익"],
    "contract_or_business_plan": ["수주", "계약", "사업"],
    "major_product_or_technology": ["기술", "제품"],
    "production_or_sales": ["생산", "판매"],
    "capex": ["투자", "시설투자", "생산"],
    "risk_or_uncertainty": ["위험", "불확실성"],
    "shareholder_return": ["배당", "자사주", "주주환원"],
}
_FACT_TOPIC_PHRASES = {
    "hbm4": "hbm4",
    "hbm5": "hbm5",
    "d램": "d램",
    "dram": "d램",
    "lpddr": "d램",
    "반도체": "반도체",
    "foundry": "파운드리",
    "파운드리": "파운드리",
    "tesla": "테슬라",
    "전기차": "전기차",
    "전동화": "전기차",
    "로봇": "로봇",
    "관세": "관세",
    "환율": "환율",
    "통화": "환율",
    "배당": "배당",
    "자기주식": "자사주",
    "자사주": "자사주",
    "생산중단": "생산중단",
    "생산 중단": "생산중단",
    "생산차질": "생산차질",
    "생산 차질": "생산차질",
    "시설투자": "시설투자",
    "시설 투자": "시설투자",
    "adr": "adr",
}
_REPORT_PERSPECTIVES = (
    (
        "SK하이닉스 ADR, 7월 나스닥 입성",
        ["adr", "etf", "주식", "수급"],
        (
            "삼성증권은 신주 2.5%를 활용한 ADR 상장이 해외 "
            "투자자의 가격 비교 기준과 수급에 영향을 줄 수 있다고 해석했습니다."
        ),
        "interpretation",
    ),
    (
        "Market Issue-SK하이닉스 급락 코멘트",
        ["adr", "실적", "하락", "반도체", "메모리"],
        (
            "미래에셋증권은 당시 하락 배경을 ADR 프리미엄 확대와 "
            "이벤트 소진, 실적 기대 조정이 함께 작용한 것으로 해석했습니다."
        ),
        "interpretation",
    ),
    (
        "ETP Weekly Insight-SK하이닉스 ADR",
        ["adr", "etf", "수급"],
        (
            "삼성증권은 SK하이닉스 ADR을 기초로 한 미국 단일종목 "
            "레버리지·인버스 ETF 출시 가능성을 점검했습니다."
        ),
        "interpretation",
    ),
    (
        "시선을 약간만 아래로",
        ["hbm4", "d램", "메모리", "실적", "전망"],
        (
            "미래에셋증권은 2026년 추정치는 낮췄지만 일반 메모리와 "
            "HBM 가격 환경을 근거로 2027년 성장 관점은 유지했습니다."
        ),
        "estimate",
    ),
    (
        "MSCI 2026년 8월 정기 리뷰 전망",
        ["adr", "msci", "수급"],
        (
            "삼성증권은 MSCI 정기변경 규칙과 SK하이닉스 ADR 발행이 "
            "지수 수급에 미칠 수 있는 조건을 함께 점검했습니다."
        ),
        "interpretation",
    ),
    (
        "내러티브보다는 펀더멘털 회복 가능성에 주목",
        ["관세", "실적", "생산차질", "환율", "자동차"],
        (
            "키움증권은 계열사 화재와 환율 등 2분기 부담을 반영하면서, "
            "회복 여부는 생산 정상화와 본업 수익성에서 확인해야 한다고 봤습니다."
        ),
        "interpretation",
    ),
    (
        "2Q26 프리뷰",
        ["2분기", "실적", "생산차질", "로봇", "환율"],
        (
            "미래에셋증권은 해외 생산 차질이 2분기 실적에 부담을 "
            "줬지만 3분기에는 로봇 사업 관련 일정이 촉매가 될 수 있다고 봤습니다."
        ),
        "estimate",
    ),
    (
        "2Q26 Review 살아남는 자가 강한 자",
        ["2분기", "실적", "생산차질", "로봇", "관세"],
        (
            "삼성증권은 생산 차질·인센티브·원재료 부담을 2분기 이익 "
            "감소 요인으로 보고, 하반기 공급 정상화와 피지컬 AI를 점검했습니다."
        ),
        "interpretation",
    ),
    (
        "2Q26 리뷰",
        ["2분기", "실적", "생산차질", "로봇", "환율"],
        (
            "미래에셋증권은 2분기 매출 49.2조원과 영업이익 2.85조원을 "
            "확인하고, 환율·인센티브·생산 차질과 로봇 모멘텀을 함께 짚었습니다."
        ),
        "actual",
    ),
    (
        "상반기의 부진을 딛고 수익성 가이던스 유지",
        ["2분기", "실적", "가이던스", "하이브리드", "로봇"],
        (
            "키움증권은 2분기 매출 49.2조원과 영업이익 2.85조원, "
            "연간 영업이익률 가이던스 유지와 하이브리드 신차·로봇 일정을 확인했습니다."
        ),
        "actual",
    ),
    (
        "변동성을 극복하면 사이클이 보인다",
        ["실적", "d램", "메모리", "반도체", "hbm4"],
        (
            "삼성증권은 D램 가격 개선을 근거로 메모리 이익 회복과 "
            "상승 사이클 지속 가능성을 제시했습니다."
        ),
        "estimate",
    ),
    (
        "Market Issue-삼성전자 하락 코멘트",
        ["실적", "하락", "수급", "외국인"],
        (
            "미래에셋증권은 실적 발표 뒤 하락을 펀더멘털 훼손보다 "
            "외국인 차익실현과 리밸런싱 성격의 수급 요인으로 해석했습니다."
        ),
        "interpretation",
    ),
    (
        "과격한 주가 반응에 뇌동하지 말자",
        ["실적", "hbm4", "메모리", "하락", "전망"],
        (
            "미래에셋증권은 잠정실적이 기대를 웃돌았고 HBM4 가격과 "
            "메모리 사이클을 근거로 이익 전망을 높였습니다."
        ),
        "estimate",
    ),
    (
        "과격한 조정, 그러나 사이클은 전반전",
        ["실적", "메모리", "하락", "전망"],
        (
            "삼성증권은 2분기 영업이익과 메모리 이익을 확인하면서 "
            "급격한 주가 조정과 업황 사이클을 구분해 볼 필요가 있다고 해석했습니다."
        ),
        "interpretation",
    ),
    (
        "하반기, EPS 성장률 둔화",
        ["실적", "3분기", "메모리", "전망", "반도체"],
        (
            "키움증권은 2분기 영업이익을 확인한 뒤 3분기 개선을 "
            "예상하면서도 하반기 EPS 성장 속도 둔화 가능성을 제시했습니다."
        ),
        "estimate",
    ),
)


class M5D1ComparisonBuildError(RuntimeError):
    """Raised when the public M5-D1 sidecar cannot be built safely."""


def build_comparison_payload(
    *,
    source_inventory: dict[str, Any],
    report_inventory: dict[str, Any],
    service_documents: dict[str, Any],
    built_at: datetime,
) -> dict[str, Any]:
    validate_report_inventory_payload(report_inventory)
    news_items = source_inventory.get("news_items")
    if not isinstance(news_items, list):
        raise M5D1ComparisonBuildError("news inventory is invalid")
    clusters = _build_clusters(news_items)
    reports = _build_report_perspectives(report_inventory)
    disclosures = _build_disclosure_backgrounds(service_documents)
    disclosures.extend(_build_event_disclosure_metadata(source_inventory))
    payload = {
        "schema_version": "m5-d1-evidence-comparison-v2",
        "built_at": built_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "source_inventory_sha256": source_inventory.get("source_sha256"),
        "report_inventory_sha256": _canonical_sha256(report_inventory),
        "event_clusters": clusters,
        "report_perspectives": reports,
        "disclosure_backgrounds": disclosures,
    }
    return StoredComparisonPayload.model_validate(payload).model_dump(
        mode="json"
    )


def _build_clusters(news_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_security: dict[str, list[dict[str, Any]]] = {}
    for item in news_items:
        security_id = item.get("security_id")
        if (
            security_id not in {"KRX:005930", "KRX:000660", "KRX:005380"}
            or item.get("security_match_basis") != "title_alias"
        ):
            continue
        by_security.setdefault(security_id, []).append(item)
    output: list[dict[str, Any]] = []
    for security_id, items in sorted(by_security.items()):
        ordered = sorted(items, key=lambda item: item["published_at"])
        groups: list[list[dict[str, Any]]] = []
        for candidate in ordered:
            placed = False
            for group in groups:
                if all(_same_event(candidate, member) for member in group):
                    group.append(candidate)
                    placed = True
                    break
            if not placed:
                groups.append([candidate])
        for group in groups:
            publishers = {item["publisher_host"] for item in group}
            if len(group) < 2 or len(publishers) < 2:
                continue
            terms = _cluster_terms(group)
            if not terms:
                continue
            sources = [_news_source(item) for item in group]
            digest = hashlib.sha256(
                "\n".join(item["source_id"] for item in sources).encode("utf-8")
            ).hexdigest()
            output.append(
                {
                    "event_id": f"event:{digest}",
                    "security_id": security_id,
                    "event_label": min(
                        (item["title"] for item in sources),
                        key=len,
                    ),
                    "event_terms": terms,
                    "first_published_at": sources[0]["published_at"],
                    "last_published_at": sources[-1]["published_at"],
                    "article_sources": sources,
                    "security_match_basis": "title_alias_only",
                    "cluster_basis": "deterministic_title_similarity",
                    "review_status": "conservative_automatic",
                }
            )
    return output


def _same_event(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_time = datetime.fromisoformat(left["published_at"].replace("Z", "+00:00"))
    right_time = datetime.fromisoformat(
        right["published_at"].replace("Z", "+00:00")
    )
    if abs((left_time - right_time).total_seconds()) > 36 * 3600:
        return False
    left_terms = _title_terms(left["title"])
    right_terms = _title_terms(right["title"])
    shared = left_terms & right_terms
    shared_distinctive = shared & _DISTINCTIVE
    phrase_shared = shared & set(_PHRASES.values())
    return len(shared_distinctive) >= 2 or (
        len(shared_distinctive) == 1
        and len(shared) >= 3
        and len(phrase_shared) >= 2
    )


def classify_title_pair(
    *,
    left_title: str,
    right_title: str,
    hours_apart: float,
) -> bool:
    if (
        not isinstance(left_title, str)
        or not left_title.strip()
        or not isinstance(right_title, str)
        or not right_title.strip()
        or type(hours_apart) not in {int, float}
        or hours_apart < 0
    ):
        raise M5D1ComparisonBuildError("event pair is invalid")
    if hours_apart > 36:
        return False
    left_terms = _title_terms(left_title)
    right_terms = _title_terms(right_title)
    shared = left_terms & right_terms
    shared_distinctive = shared & _DISTINCTIVE
    phrase_shared = shared & set(_PHRASES.values())
    return len(shared_distinctive) >= 2 or (
        len(shared_distinctive) == 1
        and len(shared) >= 3
        and len(phrase_shared) >= 2
    )


def _cluster_terms(group: list[dict[str, Any]]) -> list[str]:
    counts: Counter[str] = Counter()
    for item in group:
        counts.update(_title_terms(item["title"]))
    repeated = [term for term, count in counts.items() if count >= 2]
    repeated.sort(
        key=lambda term: (
            term in _DISTINCTIVE,
            counts[term],
            len(term),
            term,
        ),
        reverse=True,
    )
    return repeated[:30]


def _title_terms(value: str) -> set[str]:
    normalized = _clean_title(value).casefold()
    terms = {
        token.casefold()
        for token in _TOKEN.findall(normalized)
        if token.casefold() not in _STOP and len(token) >= 2
    }
    for phrase, canonical in _PHRASES.items():
        if phrase in normalized:
            terms.add(canonical)
    return terms


def _news_source(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_id": item["news_id"],
        "source_type": "news",
        "title": _clean_title(item["title"]),
        "publisher": item["publisher_host"],
        "published_at": item["published_at"],
        "source_url": item["canonical_url"],
    }


def _build_report_perspectives(
    report_inventory: dict[str, Any],
) -> list[dict[str, Any]]:
    reports = report_inventory.get("reports")
    if not isinstance(reports, list):
        raise M5D1ComparisonBuildError("report inventory is invalid")
    output = []
    used: set[str] = set()
    for needle, topics, text, actual_or_estimate in _REPORT_PERSPECTIVES:
        matches = [
            report
            for report in reports
            if needle.casefold() in report["title"].casefold()
        ]
        if len(matches) != 1:
            raise M5D1ComparisonBuildError(
                f"report perspective mapping is ambiguous: {needle}"
            )
        report = matches[0]
        if report["report_id"] in used:
            raise M5D1ComparisonBuildError("report mapping is duplicated")
        used.add(report["report_id"])
        output.append(
            {
                "source": {
                    "source_id": report["report_id"],
                    "source_type": "research_report",
                    "title": report["title"],
                    "publisher": report["publisher"],
                    "published_at": report["available_from"],
                    "source_url": report["source_url"],
                },
                "security_id": report["security_id"],
                "topics": topics,
                "text": text,
                "actual_or_estimate": actual_or_estimate,
                "source_locator": "PDF 1쪽",
                "verified_against_source": True,
            }
        )
    if len(used) != len(reports):
        raise M5D1ComparisonBuildError(
            "every selected report needs one verified perspective"
        )
    return output


def _build_disclosure_backgrounds(
    service_documents: dict[str, Any],
) -> list[dict[str, Any]]:
    documents = service_documents.get("documents")
    if not isinstance(documents, list):
        raise M5D1ComparisonBuildError("service documents are invalid")
    output = []
    for document in documents:
        if document.get("source_type") != "disclosure":
            continue
        facts = document.get("locator", {}).get("facts", [])
        if not isinstance(facts, list):
            continue
        selected_categories: set[str] = set()
        for fact in facts:
            category = fact.get("category")
            topics = _fact_topics(fact)
            if (
                not topics
                or category in selected_categories
                or fact.get("verification_status") != "verified_against_source"
            ):
                continue
            selected_categories.add(category)
            page = fact.get("physical_pdf_page")
            section_path = fact.get("section_path")
            if type(page) is not int or not isinstance(section_path, list):
                continue
            output.append(
                {
                    "source": {
                        "source_id": document["document_id"],
                        "source_type": "disclosure",
                        "title": document["title"],
                        "publisher": "금융감독원 DART",
                        "published_at": document["published_at"],
                        "source_url": document["source_url"],
                    },
                    "security_id": document["primary_security_ids"][0],
                    "topics": topics,
                    "text": fact["claim"],
                    "source_locator": (
                        f"PDF {page}쪽 · {' > '.join(section_path)}"
                    ),
                    "link_basis": "verified_body_fact",
                    "verified_against_source": True,
                }
            )
    return output


def _build_event_disclosure_metadata(
    source_inventory: dict[str, Any],
) -> list[dict[str, Any]]:
    items = source_inventory.get("disclosure_items")
    if not isinstance(items, list):
        raise M5D1ComparisonBuildError("disclosure inventory is invalid")
    output = []
    for item in items:
        submitted_date = item.get("submitted_date")
        if (
            not isinstance(submitted_date, str)
            or submitted_date < "2026-07-20"
            or submitted_date > "2026-07-27"
            or item.get("correction_status") == "superseded"
        ):
            continue
        report_name = item.get("report_name")
        if not isinstance(report_name, str):
            continue
        topics = _disclosure_title_topics(report_name)
        if not topics:
            continue
        receipt_no = item.get("receipt_no")
        if not isinstance(receipt_no, str):
            continue
        output.append(
            {
                "source": {
                    "source_id": item["disclosure_id"],
                    "source_type": "disclosure",
                    "title": report_name,
                    "publisher": "금융감독원 DART",
                    "published_at": item["available_from"],
                    "source_url": item["viewer_url"],
                },
                "security_id": item["security_id"],
                "topics": topics,
                "text": (
                    f"{submitted_date} DART에 '{report_name}' 공시가 "
                    "제출됐습니다. 이 연결은 공시 목록 메타데이터를 "
                    "공식 배경으로 사용하며, 세부 본문 사실을 뜻하지 않습니다."
                ),
                "source_locator": (
                    f"DART list metadata · receipt {receipt_no}"
                ),
                "link_basis": "official_list_metadata",
                "verified_against_source": True,
            }
        )
    return output


def _fact_topics(fact: dict[str, Any]) -> list[str]:
    category = fact.get("category")
    base_topics = _CATEGORY_TOPICS.get(category)
    claim = fact.get("claim")
    if not base_topics or not isinstance(claim, str):
        return []
    normalized = claim.casefold()
    topics = set(base_topics)
    quarter_matches = re.findall(r"\d분기", normalized)
    topics.update(quarter_matches)
    for phrase, topic in _FACT_TOPIC_PHRASES.items():
        if phrase in normalized:
            topics.add(topic)
    return sorted(topics)


def _disclosure_title_topics(report_name: str) -> list[str]:
    normalized = report_name.replace(" ", "")
    topics: set[str] = set()
    mappings = (
        ("영업(잠정)실적", {"실적", "2분기", "매출", "영업이익"}),
        ("배당", {"배당", "주주환원"}),
        ("자기주식", {"자사주", "주주환원", "수급"}),
        ("생산중단", {"생산중단", "생산차질", "생산"}),
        ("시설투자", {"시설투자", "투자", "생산", "반도체"}),
        ("풍문또는보도", {"보도", "이슈"}),
        ("최대주주", {"지분", "수급"}),
    )
    for needle, values in mappings:
        if needle in normalized:
            topics.update(values)
    return sorted(topics)


def _clean_title(value: str) -> str:
    return " ".join(
        html.unescape(_TAG.sub("", value)).replace("\u00a0", " ").split()
    )


def _canonical_sha256(value: Any) -> str:
    serialized = json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def main() -> int:
    source_inventory = json.loads(
        _DEFAULT_SOURCE_INVENTORY.read_text(encoding="utf-8")
    )
    report_inventory = json.loads(
        _DEFAULT_REPORT_INVENTORY.read_text(encoding="utf-8")
    )
    service_documents = json.loads(
        _DEFAULT_SERVICE_DOCUMENTS.read_text(encoding="utf-8")
    )
    payload = build_comparison_payload(
        source_inventory=source_inventory,
        report_inventory=report_inventory,
        service_documents=service_documents,
        built_at=datetime.now(UTC),
    )
    _DEFAULT_OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "event_cluster_count": len(payload["event_clusters"]),
                "report_perspective_count": len(
                    payload["report_perspectives"]
                ),
                "disclosure_background_count": len(
                    payload["disclosure_backgrounds"]
                ),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
