from enum import StrEnum


class ResolutionStatus(StrEnum):
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    NOT_FOUND = "not_found"
    UNSUPPORTED = "unsupported"


class ProviderStatus(StrEnum):
    OK = "ok"
    NO_DATA = "no_data"
    INVALID_QUERY = "invalid_query"
    UNAUTHORIZED = "unauthorized"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    PARSE_ERROR = "parse_error"


class RetrievalStatus(StrEnum):
    OK = "ok"
    EMPTY = "empty"
    LOW_RELEVANCE = "low_relevance"


class EvidenceDecisionStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    PROVIDER_FAILED = "provider_failed"
    NO_EVIDENCE = "no_evidence"
    BLOCKED = "blocked"

