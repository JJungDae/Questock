from __future__ import annotations

import copy
import json
import math
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Literal
from urllib.parse import parse_qsl, unquote_plus, urlsplit

from pydantic import ValidationError

from app.core.models import DateRange, Evidence, QueryPlan, SecurityIdentifier
from app.retrieval.retriever import LOW_RELEVANCE_THRESHOLD

CitationRejectionCode = Literal[
    "unknown_evidence",
    "wrong_company",
    "invalid_locator",
    "unsafe_source_url",
    "unsupported_claim",
]

_SUPPORTED_INTENTS = frozenset(
    {
        "financial_term",
        "recent_issue",
        "disclosure_summary",
        "research_report_summary",
        "risk_factors",
        "multi_source_summary",
    }
)
_CLARIFICATION_INTENTS = frozenset({*_SUPPORTED_INTENTS, "prohibited_advice", "out_of_scope"})
_SUPPORTED_SOURCES = frozenset({"news", "disclosure", "research_report", "glossary"})
_SUPPORTED_SECURITY_IDS = frozenset({"KRX:005930", "KRX:000660", "KRX:005380"})
_PAGE_BASES = frozenset({"pdf_1_based", "printed_page", "source_section_only"})
_WINDOWS_DRIVE_PATH = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z]:[\\/]")
_BACKSLASH_UNC_PATH = re.compile(r"\\\\[^\\/\s]+[\\/][^\\/\s]+")
_FORWARD_UNC_PATH = re.compile(r"(?<![A-Za-z0-9_:])//[^/\s]+/[^/\s]+")
_POSIX_ABSOLUTE_PATH = re.compile(r"(?:^|[\s\"'()=\[\]{},;])/(?![/\s])")
_CONTROL_CHARACTER = re.compile(r"[\x00-\x1f\x7f]")
_QUERY_KEY_NORMALIZER = re.compile(r"[^a-z0-9]")
_WHITESPACE = re.compile(r"\s+")
_OPAQUE_SOURCE_ASSET_ID = re.compile(r"^[A-Za-z0-9._-]+$")
_CREDENTIAL_KEYS = frozenset(
    {
        "accesstoken",
        "apikey",
        "authorization",
        "authtoken",
        "bearertoken",
        "clientsecret",
        "credential",
        "opendartapikey",
        "secret",
        "signature",
        "token",
        "xamzsignature",
        "xapikey",
    }
)


class CitationValidationError(ValueError):
    """Raised when public citation-validation input is malformed."""


@dataclass(frozen=True)
class CitationClaim:
    claim_id: str
    text: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class Citation:
    claim_id: str
    evidence_id: str
    document_id: str
    source_type: str
    title: str
    source_url: str | None
    snippet: str
    locator: Mapping[str, object]


@dataclass(frozen=True)
class CitationRejection:
    claim_id: str
    code: CitationRejectionCode


@dataclass(frozen=True)
class CitationValidationResult:
    citations: tuple[Citation, ...]
    rejections: tuple[CitationRejection, ...]


def validate_citations(
    claims: Sequence[CitationClaim],
    plan: QueryPlan,
    selected_evidence: Sequence[Evidence],
) -> CitationValidationResult:
    canonical_claims = _canonical_claims(claims)
    canonical_plan = _canonical_plan(plan)
    canonical_evidence = _canonical_selected_evidence(selected_evidence, canonical_plan)

    if canonical_plan.requires_clarification and canonical_claims:
        raise CitationValidationError("claims are incompatible with the plan")

    occurrences_by_id = _index_occurrences(canonical_evidence)
    citations: list[Citation] = []
    rejections: list[CitationRejection] = []

    for claim in canonical_claims:
        unknown = next(
            (evidence_id for evidence_id in claim.evidence_ids if evidence_id not in occurrences_by_id),
            None,
        )
        if unknown is not None:
            rejections.append(CitationRejection(claim.claim_id, "unknown_evidence"))
            continue

        referenced_ids = set(claim.evidence_ids)
        occurrences = [
            item for item in canonical_evidence if item.evidence_id in referenced_ids
        ]
        if any(not _target_matches(canonical_plan, item) for item in occurrences):
            rejections.append(CitationRejection(claim.claim_id, "wrong_company"))
            continue

        locator_issues = [_locator_issue(item) for item in occurrences]
        if "invalid_locator" in locator_issues:
            rejections.append(CitationRejection(claim.claim_id, "invalid_locator"))
            continue
        if "unsafe_source_url" in locator_issues:
            rejections.append(CitationRejection(claim.claim_id, "unsafe_source_url"))
            continue

        normalized_claim = _normalize_text(claim.text)
        if any(normalized_claim not in _normalize_text(item.snippet) for item in occurrences):
            rejections.append(CitationRejection(claim.claim_id, "unsupported_claim"))
            continue

        citations.extend(_build_citation(claim.claim_id, item) for item in occurrences)

    result = CitationValidationResult(tuple(citations), tuple(rejections))
    _audit_result(result)
    return result


def _canonical_claims(value: object) -> tuple[CitationClaim, ...]:
    if not _is_sequence(value):
        raise CitationValidationError("claims must be a sequence")

    claims: list[CitationClaim] = []
    claim_ids: set[str] = set()
    for item in value:
        if not isinstance(item, CitationClaim):
            raise CitationValidationError("claims are invalid")
        claim_id = item.claim_id
        text = item.text
        evidence_ids = item.evidence_ids
        if (
            not _nonblank_string(claim_id)
            or _unsafe_public_string(claim_id)
            or not _nonblank_string(text)
            or not any(character.isalnum() for character in _normalize_text(text))
            or not isinstance(evidence_ids, tuple)
            or not evidence_ids
            or any(not _nonblank_string(evidence_id) for evidence_id in evidence_ids)
            or len(set(evidence_ids)) != len(evidence_ids)
            or claim_id in claim_ids
        ):
            raise CitationValidationError("claims are invalid")
        claim_ids.add(claim_id)
        claims.append(CitationClaim(claim_id, text, tuple(evidence_ids)))
    return tuple(claims)


def _canonical_plan(value: object) -> QueryPlan:
    if not isinstance(value, QueryPlan):
        raise CitationValidationError("plan must be a QueryPlan")
    try:
        values = _model_values(value, QueryPlan)
        security = values.get("security")
        date_range = values.get("date_range")
        if security is not None:
            security = _canonical_security(security)
        if date_range is not None:
            date_range = _canonical_date_range(date_range)
        values["security"] = security
        values["date_range"] = date_range
        canonical = QueryPlan.model_validate(values, strict=True)
    except (AttributeError, TypeError, ValueError, ValidationError):
        raise CitationValidationError("plan must be a QueryPlan") from None

    intent = canonical.intent
    clarification = canonical.requires_clarification
    sources = canonical.required_sources
    if (
        not _nonblank_string(intent)
        or type(clarification) is not bool
        or not isinstance(sources, list)
        or any(not _nonblank_string(source) or source not in _SUPPORTED_SOURCES for source in sources)
        or len(set(sources)) != len(sources)
    ):
        raise CitationValidationError("plan must be a QueryPlan")
    if clarification:
        if intent not in _CLARIFICATION_INTENTS:
            raise CitationValidationError("plan must be a QueryPlan")
    elif intent not in _SUPPORTED_INTENTS:
        raise CitationValidationError("plan must be a QueryPlan")

    if intent != "financial_term" and not clarification and canonical.security is None:
        raise CitationValidationError("plan must be a QueryPlan")
    return canonical.model_copy(deep=True)


def _canonical_security(value: object) -> SecurityIdentifier:
    if not isinstance(value, SecurityIdentifier):
        raise CitationValidationError("plan must be a QueryPlan")
    values = _model_values(value, SecurityIdentifier)
    canonical = SecurityIdentifier.model_validate(values, strict=True)
    scalar_fields = (
        canonical.market,
        canonical.ticker,
        canonical.security_name,
        canonical.security_type,
        canonical.corp_name,
    )
    security_id = f"{canonical.market}:{canonical.ticker}"
    if (
        any(not _nonblank_string(item) for item in scalar_fields)
        or canonical.security_type != "common_stock"
        or security_id not in _SUPPORTED_SECURITY_IDS
        or (
            canonical.corp_code is not None
            and not _nonblank_string(canonical.corp_code)
        )
    ):
        raise CitationValidationError("plan must be a QueryPlan")
    return canonical.model_copy(deep=True)


def _canonical_date_range(value: object) -> DateRange:
    if not isinstance(value, DateRange):
        raise CitationValidationError("plan must be a QueryPlan")
    canonical = DateRange.model_validate(_model_values(value, DateRange), strict=True)
    if (
        canonical.start is not None
        and type(canonical.start) is not date
    ) or (
        canonical.end is not None
        and type(canonical.end) is not date
    ):
        raise CitationValidationError("plan must be a QueryPlan")
    return canonical.model_copy(deep=True)


def _canonical_selected_evidence(
    value: object,
    plan: QueryPlan,
) -> tuple[Evidence, ...]:
    if not _is_sequence(value):
        raise CitationValidationError("selected evidence must be a sequence")

    items: list[Evidence] = []
    payload_by_id: dict[str, dict[str, Any]] = {}
    for raw_item in value:
        if not isinstance(raw_item, Evidence):
            raise CitationValidationError("selected evidence is invalid")
        try:
            canonical = Evidence.model_validate(
                _model_values(raw_item, Evidence),
                strict=True,
            )
        except (AttributeError, RecursionError, TypeError, ValueError, ValidationError):
            raise CitationValidationError("selected evidence is invalid") from None

        if (
            not _nonblank_string(canonical.evidence_id)
            or not _nonblank_string(canonical.document_id)
            or not _nonblank_string(canonical.source_type)
            or canonical.source_type not in _SUPPORTED_SOURCES
            or canonical.source_type not in plan.required_sources
            or not _nonblank_string(canonical.title)
            or not _nonblank_string(canonical.snippet)
            or not _valid_score(canonical.retrieval_score)
            or (
                plan.intent == "financial_term"
                and canonical.source_type != "glossary"
            )
        ):
            raise CitationValidationError("selected evidence is invalid")

        payload = canonical.model_dump(mode="python")
        previous = payload_by_id.get(canonical.evidence_id)
        if previous is not None and not _payloads_equal(previous, payload):
            raise CitationValidationError("selected evidence IDs are inconsistent")
        payload_by_id.setdefault(canonical.evidence_id, payload)
        items.append(canonical)
    return tuple(items)


def _index_occurrences(evidence: Sequence[Evidence]) -> dict[str, tuple[Evidence, ...]]:
    indexed: dict[str, list[Evidence]] = {}
    for item in evidence:
        indexed.setdefault(item.evidence_id, []).append(item)
    return {key: tuple(value) for key, value in indexed.items()}


def _target_matches(plan: QueryPlan, item: Evidence) -> bool:
    if plan.intent == "financial_term":
        return item.source_type == "glossary"
    security = plan.security
    if security is None:
        return False
    target = f"{security.market}:{security.ticker}"
    if item.scope == "company_specific":
        return item.subject_security_ids == [target]
    if item.scope == "multi_company":
        return target in item.subject_security_ids
    if item.scope == "industry_common":
        return not item.subject_security_ids and target in item.mentioned_security_ids
    return False


def _locator_issue(item: Evidence) -> CitationRejectionCode | None:
    locator = item.locator
    if not _locator_structure_valid(locator):
        return "invalid_locator"

    if item.source_type == "news":
        issue = _news_locator_issue(item, locator)
    elif item.source_type == "disclosure":
        issue = _disclosure_locator_issue(item, locator)
    elif item.source_type == "research_report":
        issue = _report_locator_issue(item, locator)
    elif item.source_type == "glossary":
        issue = _glossary_locator_issue(item, locator)
    else:
        return "invalid_locator"

    if issue is not None:
        return issue
    if not _all_locator_urls_safe(locator):
        return "unsafe_source_url"
    return None


def _news_locator_issue(
    item: Evidence,
    locator: Mapping[str, Any],
) -> CitationRejectionCode | None:
    if not _nonblank_string(locator.get("provider")):
        return "invalid_locator"
    if locator.get("source_url") != item.source_url:
        return "unsafe_source_url"
    if item.source_url is not None:
        return None if _safe_url(item.source_url) else "unsafe_source_url"

    published_at = locator.get("published_at")
    raw_index = locator.get("raw_index")
    if not _aware_timestamp_string(published_at):
        return "invalid_locator"
    if type(raw_index) is not int or raw_index < 0:
        return "invalid_locator"
    return None


def _disclosure_locator_issue(
    item: Evidence,
    locator: Mapping[str, Any],
) -> CitationRejectionCode | None:
    provider = locator.get("provider")
    receipt_no = locator.get("receipt_no")
    viewer_url = locator.get("viewer_url")
    if (
        not _nonblank_string(provider)
        or not isinstance(receipt_no, str)
        or re.fullmatch(r"\d{14}", receipt_no) is None
    ):
        return "invalid_locator"
    expected = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={receipt_no}"
    if viewer_url != item.source_url or viewer_url != expected:
        return "unsafe_source_url"
    return None if _safe_url(viewer_url) else "unsafe_source_url"


def _report_locator_issue(
    item: Evidence,
    locator: Mapping[str, Any],
) -> CitationRejectionCode | None:
    manifest_id = locator.get("manifest_id")
    document_id = locator.get("document_id")
    page_basis = locator.get("page_basis")
    section = locator.get("section")
    page = locator.get("page")
    if (
        not _nonblank_string(manifest_id)
        or document_id != item.document_id
        or page_basis not in _PAGE_BASES
        or not _nonblank_string(section)
    ):
        return "invalid_locator"
    if page_basis in {"pdf_1_based", "printed_page"}:
        if type(page) is not int or page <= 0:
            return "invalid_locator"
    elif page is not None:
        return "invalid_locator"

    locator_url = locator.get("source_url")
    source_asset_id = locator.get("source_asset_id")
    if source_asset_id is not None and not _stable_source_asset_id(source_asset_id):
        return "invalid_locator"
    if item.source_url is not None:
        if locator_url != item.source_url:
            return "unsafe_source_url"
        return None if _safe_url(item.source_url) else "unsafe_source_url"
    if locator_url is not None:
        return "unsafe_source_url"
    if not _stable_source_asset_id(source_asset_id):
        return "invalid_locator"
    return None


def _glossary_locator_issue(
    item: Evidence,
    locator: Mapping[str, Any],
) -> CitationRejectionCode | None:
    version = locator.get("version")
    if (
        not _nonblank_string(locator.get("corpus_id"))
        or not _nonblank_string(locator.get("entry_id"))
        or type(version) is not int
        or not _nonblank_string(locator.get("section"))
        or locator.get("source_type") != "glossary"
    ):
        return "invalid_locator"
    locator_url = locator.get("source_url")
    if item.source_url is None:
        return None if locator_url is None else "unsafe_source_url"
    if locator_url != item.source_url:
        return "unsafe_source_url"
    return None if _safe_url(item.source_url) else "unsafe_source_url"


def _locator_structure_valid(value: object) -> bool:
    if not isinstance(value, Mapping) or not value:
        return False
    return _safe_locator_value(value)


def _safe_locator_value(value: object) -> bool:
    if value is None or type(value) is bool or type(value) is int:
        return True
    if type(value) is float:
        return math.isfinite(value)
    if isinstance(value, str):
        return (
            not _CONTROL_CHARACTER.search(value)
            and not _contains_local_path(value)
        )
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if (
                not _safe_locator_key(key)
                or not _safe_locator_value(nested)
            ):
                return False
        return True
    if isinstance(value, (list, tuple)):
        return all(_safe_locator_value(nested) for nested in value)
    return False


def _all_locator_urls_safe(value: object) -> bool:
    if isinstance(value, str):
        if value.casefold().startswith(("http://", "https://")):
            return _safe_url(value)
        return True
    if isinstance(value, Mapping):
        return all(_all_locator_urls_safe(nested) for nested in value.values())
    if isinstance(value, (list, tuple)):
        return all(_all_locator_urls_safe(nested) for nested in value)
    return True


def _safe_url(value: object) -> bool:
    if (
        not isinstance(value, str)
        or _CONTROL_CHARACTER.search(value)
        or any(character.isspace() for character in value)
    ):
        return False
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return False
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or port is not None and not 0 < port <= 65535
    ):
        return False
    for key, nested_value in parse_qsl(parsed.query, keep_blank_values=True):
        if (
            _normalized_key(key) in _CREDENTIAL_KEYS
            or _CONTROL_CHARACTER.search(nested_value)
            or _contains_local_path(unquote_plus(nested_value))
        ):
            return False
    return True


def _aware_timestamp_string(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _build_citation(claim_id: str, item: Evidence) -> Citation:
    return Citation(
        claim_id=claim_id,
        evidence_id=item.evidence_id,
        document_id=item.document_id,
        source_type=item.source_type,
        title=item.title,
        source_url=item.source_url,
        snippet=item.snippet,
        locator=copy.deepcopy(item.locator),
    )


def _audit_result(result: CitationValidationResult) -> None:
    serialized = {
        "citations": [
            {
                "claim_id": item.claim_id,
                "evidence_id": item.evidence_id,
                "document_id": item.document_id,
                "source_type": item.source_type,
                "title": item.title,
                "source_url": item.source_url,
                "snippet": item.snippet,
                "locator": _json_equivalent(item.locator),
            }
            for item in result.citations
        ],
        "rejections": [
            {"claim_id": item.claim_id, "code": item.code}
            for item in result.rejections
        ],
    }
    try:
        for citation in result.citations:
            if any(
                _unsafe_public_string(value)
                for value in (
                    citation.claim_id,
                    citation.evidence_id,
                    citation.document_id,
                    citation.source_type,
                    citation.title,
                    citation.snippet,
                )
            ):
                raise ValueError
            if (
                not _locator_structure_valid(citation.locator)
                or not _all_locator_urls_safe(citation.locator)
            ):
                raise ValueError
            if citation.source_url is not None and not _safe_url(citation.source_url):
                raise ValueError
        json.dumps(serialized, allow_nan=False)
    except (TypeError, ValueError):
        raise CitationValidationError("citation output is invalid") from None


def _json_equivalent(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _json_equivalent(nested) for key, nested in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_equivalent(nested) for nested in value]
    return value


def _payloads_equal(left: object, right: object) -> bool:
    try:
        result = left == right
    except (TypeError, ValueError):
        return False
    return type(result) is bool and result


def _model_values(value: object, model_type: type[Any]) -> dict[str, Any]:
    return {
        field_name: getattr(value, field_name)
        for field_name in model_type.model_fields
    }


def _valid_score(value: object) -> bool:
    return (
        type(value) in {int, float}
        and math.isfinite(value)
        and value >= LOW_RELEVANCE_THRESHOLD
    )


def _is_sequence(value: object) -> bool:
    return (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes, bytearray, Mapping))
    )


def _nonblank_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _normalize_text(value: str) -> str:
    return _WHITESPACE.sub(" ", unicodedata.normalize("NFKC", value).casefold()).strip()


def _normalized_key(value: str) -> str:
    return _QUERY_KEY_NORMALIZER.sub("", unquote_plus(value).casefold())


def _safe_locator_key(value: object) -> bool:
    return (
        type(value) is str
        and not _CONTROL_CHARACTER.search(value)
        and not _contains_local_path(value)
        and _normalized_key(value) not in _CREDENTIAL_KEYS
    )


def _stable_source_asset_id(value: object) -> bool:
    return (
        type(value) is str
        and value not in {".", ".."}
        and _OPAQUE_SOURCE_ASSET_ID.fullmatch(value) is not None
        and any(character.isalnum() for character in value)
    )


def _unsafe_public_string(value: str) -> bool:
    return bool(_CONTROL_CHARACTER.search(value) or _contains_local_path(value))


def _contains_local_path(value: str) -> bool:
    if value.casefold().startswith(("http://", "https://")):
        return False
    return bool(
        value.casefold().startswith("file://")
        or _WINDOWS_DRIVE_PATH.search(value)
        or _BACKSLASH_UNC_PATH.search(value)
        or _FORWARD_UNC_PATH.search(value)
        or _POSIX_ABSOLUTE_PATH.search(value)
    )


__all__ = [
    "Citation",
    "CitationClaim",
    "CitationRejection",
    "CitationValidationError",
    "CitationValidationResult",
    "validate_citations",
]
