from __future__ import annotations

from datetime import date

import pytest

from app.core.resolver import SecurityResolver
from app.services.planning_observation import build_observed_query_plan

BASIS_DATE = date(2026, 7, 25)


@pytest.mark.parametrize(
    ("query", "expected_status", "expected_security_id"),
    [
        (
            "\uc0bc\uc131\uc804\uc790 \ucd5c\uadfc \ub274\uc2a4",
            "resolved",
            "KRX:005930",
        ),
        ("005930 \ucd5c\uadfc \ub274\uc2a4", "resolved", "KRX:005930"),
        ("\uc0bc\uc131 \ucd5c\uadfc \ub274\uc2a4", "ambiguous", None),
        ("005935 \ucd5c\uadfc \ub274\uc2a4", "unsupported", None),
        (
            "\uce74\uce74\uc624 \ucd5c\uadfc \ub274\uc2a4",
            "not_found",
            None,
        ),
        (
            "\uc0bc\uc131\uc804\uc790\uc640 SK\ud558\uc774\ub2c9\uc2a4 "
            "\ucd5c\uadfc \ub274\uc2a4",
            "ambiguous",
            None,
        ),
        (
            "\uc0bc\uc131\uc804\uc790 005935 \ucd5c\uadfc \ub274\uc2a4",
            "unsupported",
            None,
        ),
    ],
)
def test_resolution_observation_is_truthful(
    query: str,
    expected_status: str,
    expected_security_id: str | None,
) -> None:
    observed = build_observed_query_plan(
        query,
        basis_date=BASIS_DATE,
        resolver=SecurityResolver(),
    )

    assert observed.resolution_status == expected_status
    actual_security_id = (
        f"{observed.plan.security.market}:{observed.plan.security.ticker}"
        if observed.plan.security
        else None
    )
    assert actual_security_id == expected_security_id


def test_early_blocked_plan_preserves_resolved_observation() -> None:
    observed = build_observed_query_plan(
        "\uc0bc\uc131\uc804\uc790 \ub9e4\uc218\ud574\uc57c \ud574",
        basis_date=BASIS_DATE,
        resolver=SecurityResolver(),
    )

    assert observed.plan.intent == "prohibited_advice"
    assert observed.plan.requires_clarification is True
    assert observed.resolution_status == "resolved"
    assert observed.security_id == "KRX:005930"


def test_price_move_out_of_scope_preserves_resolved_observation() -> None:
    observed = build_observed_query_plan(
        "\uc0bc\uc131\uc804\uc790 \uc65c \uc62c\ub790\uc5b4",
        basis_date=BASIS_DATE,
        resolver=SecurityResolver(),
    )

    assert observed.plan.intent == "out_of_scope"
    assert observed.resolution_status == "resolved"
    assert observed.security_id == "KRX:005930"


def test_financial_term_without_security_is_deterministic_not_found() -> None:
    first = build_observed_query_plan(
        "\uc21c\uc774\uc775\uc774 \ubb50\uc57c?",
        basis_date=BASIS_DATE,
        resolver=SecurityResolver(),
    )
    second = build_observed_query_plan(
        "\uc21c\uc774\uc775\uc774 \ubb50\uc57c?",
        basis_date=BASIS_DATE,
        resolver=SecurityResolver(),
    )

    assert first.plan.intent == "financial_term"
    assert first.resolution_status == "not_found"
    assert first == second
