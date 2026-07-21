from app.core.status import (
    EvidenceDecisionStatus,
    ProviderStatus,
    ResolutionStatus,
    RetrievalStatus,
)


def test_resolution_status_contract():
    assert {status.value for status in ResolutionStatus} == {
        "resolved",
        "ambiguous",
        "not_found",
        "unsupported",
    }


def test_provider_status_contract_keeps_errors_separate_from_no_data():
    assert {status.value for status in ProviderStatus} == {
        "ok",
        "no_data",
        "invalid_query",
        "unauthorized",
        "rate_limited",
        "timeout",
        "provider_unavailable",
        "parse_error",
    }
    assert ProviderStatus.TIMEOUT != ProviderStatus.NO_DATA
    assert ProviderStatus.RATE_LIMITED != ProviderStatus.NO_DATA


def test_retrieval_status_contract_keeps_low_relevance_out_of_provider_status():
    assert {status.value for status in RetrievalStatus} == {
        "ok",
        "empty",
        "low_relevance",
    }
    assert "low_relevance" not in {status.value for status in ProviderStatus}


def test_evidence_decision_status_contract():
    assert {status.value for status in EvidenceDecisionStatus} == {
        "complete",
        "partial",
        "provider_failed",
        "no_evidence",
        "blocked",
    }
    assert "low_relevance" not in {status.value for status in EvidenceDecisionStatus}
