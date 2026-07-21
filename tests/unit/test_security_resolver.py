import copy
import json

import pytest
from pydantic import ValidationError

from app.core.models import SecurityIdentifier
from app.core.resolver import (
    DEFAULT_FIXTURE_PATH,
    FixtureValidationError,
    ResolutionResult,
    SecurityResolver,
    security_id_for,
)
from app.core.status import ResolutionStatus

SAMSUNG = "KRX:005930"
SK_HYNIX = "KRX:000660"
HYUNDAI = "KRX:005380"


def load_fixture():
    return json.loads(DEFAULT_FIXTURE_PATH.read_text(encoding="utf-8"))


def security(**overrides):
    payload = {
        "market": "KRX",
        "ticker": "005930",
        "security_name": "삼성전자",
        "security_type": "common_stock",
        "corp_code": None,
        "corp_name": "삼성전자",
    }
    payload.update(overrides)
    return SecurityIdentifier(**payload)


def assert_resolved(result, expected_security_id, matched_by):
    assert result.status == ResolutionStatus.RESOLVED
    assert result.security is not None
    assert security_id_for(result.security) == expected_security_id
    assert result.candidates == []
    assert result.matched_by == matched_by


@pytest.mark.parametrize(
    ("query", "expected_security_id"),
    [
        ("삼성전자", SAMSUNG),
        ("SK하이닉스", SK_HYNIX),
        ("현대자동차", HYUNDAI),
    ],
)
def test_resolves_exact_security_names(query, expected_security_id):
    result = SecurityResolver().resolve(query)

    assert_resolved(result, expected_security_id, "name")


@pytest.mark.parametrize(
    ("query", "expected_security_id"),
    [
        ("005930", SAMSUNG),
        ("000660", SK_HYNIX),
        ("005380", HYUNDAI),
    ],
)
def test_resolves_exact_tickers(query, expected_security_id):
    result = SecurityResolver().resolve(query)

    assert_resolved(result, expected_security_id, "ticker")


@pytest.mark.parametrize(
    ("query", "expected_security_id"),
    [
        ("KRX:005930", SAMSUNG),
        ("krx:000660", SK_HYNIX),
    ],
)
def test_resolves_exact_security_ids(query, expected_security_id):
    result = SecurityResolver().resolve(query)

    assert_resolved(result, expected_security_id, "security_id")


@pytest.mark.parametrize(
    ("query", "expected_security_id"),
    [
        ("삼전", SAMSUNG),
        ("하이닉스", SK_HYNIX),
        ("SK  하이닉스", SK_HYNIX),
        ("SK hynix", SK_HYNIX),
        ("현대차", HYUNDAI),
    ],
)
def test_resolves_explicit_aliases(query, expected_security_id):
    result = SecurityResolver().resolve(query)

    assert_resolved(result, expected_security_id, "alias")


@pytest.mark.parametrize(
    ("query", "expected_security_id", "matched_by"),
    [
        ("  삼성전자  ", SAMSUNG, "name"),
        ("００５９３０", SAMSUNG, "ticker"),
        ("ＫＲＸ:０００６６０", SK_HYNIX, "security_id"),
    ],
)
def test_normalizes_whitespace_and_nfkc(query, expected_security_id, matched_by):
    result = SecurityResolver().resolve(query)

    assert_resolved(result, expected_security_id, matched_by)


@pytest.mark.parametrize("query", ["", "   "])
def test_empty_input_is_not_found(query):
    result = SecurityResolver().resolve(query)

    assert result.status == ResolutionStatus.NOT_FOUND
    assert result.security is None
    assert result.candidates == []
    assert result.matched_by == "none"


@pytest.mark.parametrize(
    ("query", "expected_security_id"),
    [
        ("삼성", SAMSUNG),
        ("SK", SK_HYNIX),
        ("현대", HYUNDAI),
    ],
)
def test_curated_ambiguous_terms_return_supported_candidates(query, expected_security_id):
    resolver = SecurityResolver()

    result = resolver.resolve(query)

    assert result.status == ResolutionStatus.AMBIGUOUS
    assert result.security is None
    assert len(result.candidates) >= 1
    assert result.message
    assert result.matched_by == "none"
    candidate_ids = {security_id_for(candidate) for candidate in result.candidates}
    assert expected_security_id in candidate_ids
    assert candidate_ids <= resolver.supported_security_ids


@pytest.mark.parametrize("query", ["삼성전자우", "005935", "AAPL"])
def test_explicitly_unsupported_inputs_are_unsupported(query):
    result = SecurityResolver().resolve(query)

    assert result.status == ResolutionStatus.UNSUPPORTED
    assert result.security is None
    assert result.candidates == []
    assert result.matched_by == "unsupported_rule"


@pytest.mark.parametrize("query", ["999999", "000001"])
def test_unknown_inputs_are_not_found(query):
    result = SecurityResolver().resolve(query)

    assert result.status == ResolutionStatus.NOT_FOUND
    assert result.security is None
    assert result.candidates == []
    assert result.matched_by == "none"


def test_candidate_corp_codes_are_not_returned_before_source_revalidation():
    result = SecurityResolver().resolve("삼성전자")

    assert result.security is not None
    assert result.security.corp_code is None


def test_blocked_corp_codes_are_not_returned():
    fixture = load_fixture()
    fixture["securities"][0]["verification_status"] = "blocked"

    result = SecurityResolver(fixture_data=fixture).resolve("삼성전자")

    assert result.security is not None
    assert result.security.corp_code is None


def test_verified_corp_codes_are_returned():
    fixture = load_fixture()
    fixture["securities"][0]["verification_status"] = "verified"

    result = SecurityResolver(fixture_data=fixture).resolve("삼성전자")

    assert result.security is not None
    assert result.security.corp_code == "00126380"


def test_fixture_rejects_duplicate_security_id():
    fixture = load_fixture()
    fixture["securities"].append(copy.deepcopy(fixture["securities"][0]))

    with pytest.raises(FixtureValidationError):
        SecurityResolver(fixture_data=fixture)


def test_fixture_rejects_duplicate_ticker():
    fixture = load_fixture()
    fixture["securities"][1]["market"] = "ALT"
    fixture["securities"][1]["ticker"] = "005930"
    fixture["securities"][1]["security_id"] = "ALT:005930"

    with pytest.raises(FixtureValidationError):
        SecurityResolver(fixture_data=fixture)


def test_fixture_rejects_alias_collision_across_securities():
    fixture = load_fixture()
    fixture["securities"][1]["aliases"].append("삼전")

    with pytest.raises(FixtureValidationError):
        SecurityResolver(fixture_data=fixture)


def test_fixture_rejects_empty_alias():
    fixture = load_fixture()
    fixture["securities"][0]["aliases"].append("   ")

    with pytest.raises(FixtureValidationError):
        SecurityResolver(fixture_data=fixture)


def test_resolution_result_rejects_invalid_matched_by_literal():
    with pytest.raises(ValidationError):
        ResolutionResult(
            status=ResolutionStatus.NOT_FOUND,
            normalized_query="삼성전자",
            matched_by="fuzzy",
        )


def test_resolution_result_requires_resolved_security_and_empty_candidates():
    valid_security = security()

    with pytest.raises(ValidationError):
        ResolutionResult(
            status=ResolutionStatus.RESOLVED,
            normalized_query="삼성전자",
            matched_by="name",
        )

    with pytest.raises(ValidationError):
        ResolutionResult(
            status=ResolutionStatus.RESOLVED,
            security=valid_security,
            candidates=[valid_security],
            normalized_query="삼성전자",
            matched_by="name",
        )


def test_resolution_result_enforces_ambiguous_contract():
    with pytest.raises(ValidationError):
        ResolutionResult(
            status=ResolutionStatus.AMBIGUOUS,
            normalized_query="삼성",
            message="확인이 필요합니다.",
            matched_by="none",
        )

    with pytest.raises(ValidationError):
        ResolutionResult(
            status=ResolutionStatus.AMBIGUOUS,
            candidates=[security()],
            normalized_query="삼성",
            message="확인이 필요합니다.",
            matched_by="alias",
        )


def test_resolution_result_enforces_not_found_and_unsupported_contracts():
    valid_security = security()

    with pytest.raises(ValidationError):
        ResolutionResult(
            status=ResolutionStatus.NOT_FOUND,
            candidates=[valid_security],
            normalized_query="999999",
            matched_by="none",
        )

    with pytest.raises(ValidationError):
        ResolutionResult(
            status=ResolutionStatus.UNSUPPORTED,
            normalized_query="AAPL",
            matched_by="none",
        )


def test_resolution_priority_checks_exact_and_alias_before_later_rules():
    fixture = load_fixture()
    fixture["ambiguous_terms"].append(
        {
            "term": "삼성전자",
            "candidate_security_ids": [SAMSUNG],
            "message": "exact name should win",
        }
    )
    fixture["ambiguous_terms"].append(
        {
            "term": "삼전",
            "candidate_security_ids": [SAMSUNG],
            "message": "alias should win",
        }
    )
    resolver = SecurityResolver(fixture_data=fixture)

    exact_result = resolver.resolve("삼성전자")
    alias_result = resolver.resolve("삼전")
    ambiguous_result = resolver.resolve("SK")
    empty_result = resolver.resolve("")

    assert_resolved(exact_result, SAMSUNG, "name")
    assert_resolved(alias_result, SAMSUNG, "alias")
    assert ambiguous_result.status == ResolutionStatus.AMBIGUOUS
    assert empty_result.status == ResolutionStatus.NOT_FOUND
