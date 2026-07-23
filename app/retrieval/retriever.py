from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from math import log
import re
import unicodedata

from app.core.models import Evidence, FinancialDocument, RetrievalRequest, RetrievalResult
from app.core.status import RetrievalStatus
from app.retrieval.filters import filter_evidence

STRATEGY = "lexical-bm25-m2-03-v1"
MAX_TOP_K = 6
LOW_RELEVANCE_THRESHOLD = 0.5
BM25_K1 = 1.2
BM25_B = 0.75
SCORE_ROUND_DIGITS = 6

_TOKEN_PATTERN = re.compile(r"[가-힣]+|[a-z0-9]+")
_GENERIC_QUERY_TOKENS = frozenset(
    {
        "최근",
        "요약",
        "설명",
        "알려",
        "알려줘",
        "자료",
        "정보",
        "관련",
        "어때",
        "대해",
    }
)
_DIAGNOSTIC_KEYS = (
    "input_count",
    "filtered_count",
    "scored_count",
    "eligible_count",
    "returned_count",
    "query_token_count",
    "requested_top_k",
    "effective_top_k",
    "max_top_k",
    "low_relevance_threshold",
)


def retrieve_evidence(
    evidence: Sequence[Evidence],
    request: RetrievalRequest,
    *,
    documents_by_id: Mapping[str, FinancialDocument] | None = None,
) -> RetrievalResult:
    filtered_evidence = filter_evidence(evidence, request, documents_by_id=documents_by_id)
    input_count = len(evidence)
    filtered_count = len(filtered_evidence)
    effective_top_k = min(request.top_k, MAX_TOP_K)

    if not filtered_evidence:
        return _result(
            evidence=[],
            status=RetrievalStatus.EMPTY,
            low_relevance=False,
            diagnostics=_diagnostics(
                input_count=input_count,
                filtered_count=filtered_count,
                scored_count=0,
                eligible_count=0,
                returned_count=0,
                query_token_count=0,
                requested_top_k=request.top_k,
                effective_top_k=effective_top_k,
            ),
        )

    query_tokens = _tokenize_query(request.query)
    if not query_tokens:
        return _result(
            evidence=[],
            status=RetrievalStatus.LOW_RELEVANCE,
            low_relevance=True,
            diagnostics=_diagnostics(
                input_count=input_count,
                filtered_count=filtered_count,
                scored_count=0,
                eligible_count=0,
                returned_count=0,
                query_token_count=0,
                requested_top_k=request.top_k,
                effective_top_k=effective_top_k,
            ),
        )

    scores = _score_candidates(filtered_evidence, query_tokens)
    eligible = [
        (score, index, item)
        for index, (item, score) in enumerate(zip(filtered_evidence, scores, strict=True))
        if score >= LOW_RELEVANCE_THRESHOLD
    ]
    if not eligible:
        return _result(
            evidence=[],
            status=RetrievalStatus.LOW_RELEVANCE,
            low_relevance=True,
            diagnostics=_diagnostics(
                input_count=input_count,
                filtered_count=filtered_count,
                scored_count=filtered_count,
                eligible_count=0,
                returned_count=0,
                query_token_count=len(query_tokens),
                requested_top_k=request.top_k,
                effective_top_k=effective_top_k,
            ),
        )

    eligible.sort(key=lambda entry: (-entry[0], entry[1]))
    selected = [
        item.model_copy(deep=True, update={"retrieval_score": score})
        for score, _, item in eligible[:effective_top_k]
    ]
    return _result(
        evidence=selected,
        status=RetrievalStatus.OK,
        low_relevance=False,
        diagnostics=_diagnostics(
            input_count=input_count,
            filtered_count=filtered_count,
            scored_count=filtered_count,
            eligible_count=len(eligible),
            returned_count=len(selected),
            query_token_count=len(query_tokens),
            requested_top_k=request.top_k,
            effective_top_k=effective_top_k,
        ),
    )


def _tokenize_query(query: str) -> list[str]:
    return [token for token in _tokenize_text(query) if token not in _GENERIC_QUERY_TOKENS]


def _tokenize_text(value: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return _TOKEN_PATTERN.findall(normalized)


def _score_candidates(evidence: Sequence[Evidence], query_tokens: Sequence[str]) -> list[float]:
    documents = [_candidate_tokens(item) for item in evidence]
    average_document_length = sum(len(document) for document in documents) / len(documents)
    if average_document_length == 0:
        return [0.0 for _ in documents]

    document_frequency = Counter(token for document in documents for token in set(document))
    query_frequency = Counter(query_tokens)
    scores: list[float] = []
    for document in documents:
        term_frequency = Counter(document)
        document_length = len(document)
        score = 0.0
        for token, query_term_frequency in query_frequency.items():
            token_frequency = term_frequency[token]
            if token_frequency == 0:
                continue
            frequency = document_frequency[token]
            inverse_document_frequency = log(
                1 + (len(documents) - frequency + 0.5) / (frequency + 0.5)
            )
            denominator = token_frequency + BM25_K1 * (
                1 - BM25_B + BM25_B * document_length / average_document_length
            )
            score += (
                inverse_document_frequency
                * (token_frequency * (BM25_K1 + 1))
                / denominator
                * query_term_frequency
            )
        scores.append(round(score, SCORE_ROUND_DIGITS))
    return scores


def _candidate_tokens(item: Evidence) -> list[str]:
    return _tokenize_text(item.title) * 2 + _tokenize_text(item.snippet)


def _diagnostics(
    *,
    input_count: int,
    filtered_count: int,
    scored_count: int,
    eligible_count: int,
    returned_count: int,
    query_token_count: int,
    requested_top_k: int,
    effective_top_k: int,
) -> dict[str, int | float]:
    diagnostics: dict[str, int | float] = {
        "input_count": input_count,
        "filtered_count": filtered_count,
        "scored_count": scored_count,
        "eligible_count": eligible_count,
        "returned_count": returned_count,
        "query_token_count": query_token_count,
        "requested_top_k": requested_top_k,
        "effective_top_k": effective_top_k,
        "max_top_k": MAX_TOP_K,
        "low_relevance_threshold": LOW_RELEVANCE_THRESHOLD,
    }
    return {key: diagnostics[key] for key in _DIAGNOSTIC_KEYS}


def _result(
    *,
    evidence: list[Evidence],
    status: RetrievalStatus,
    low_relevance: bool,
    diagnostics: dict[str, int | float],
) -> RetrievalResult:
    return RetrievalResult(
        evidence=evidence,
        status=status,
        strategy=STRATEGY,
        low_relevance=low_relevance,
        diagnostics=diagnostics,
    )


__all__ = ["retrieve_evidence"]
