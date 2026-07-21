from __future__ import annotations

import asyncio
from typing import Any, Literal

from app.core.models import DateRange, ProviderResult, SecurityIdentifier
from app.core.status import ProviderStatus
from app.providers.base import create_provider_result, security_id_for

FakeScenario = Literal[
    "ok",
    "no_data",
    "invalid_query",
    "timeout",
    "rate_limited",
    "parse_error",
    "provider_unavailable",
    "unauthorized",
    "pending",
    "raise",
]


class FakeProvider:
    def __init__(
        self,
        key: str = "fake",
        scenario: FakeScenario | list[FakeScenario] = "ok",
        data: Any | None = None,
        delay_seconds: float = 0,
    ) -> None:
        self.key = key
        self._scenarios = scenario if isinstance(scenario, list) else [scenario]
        self._data = data
        self._delay_seconds = delay_seconds
        self.attempt_count = 0
        self.cancel_count = 0

    async def fetch(
        self,
        security: SecurityIdentifier,
        query: str | None = None,
        date_range: DateRange | None = None,
        attempt_timeout_seconds: float = 8,
    ) -> ProviderResult[Any]:
        self.attempt_count += 1
        scenario = self._scenario_for_attempt()
        if self._delay_seconds:
            await asyncio.sleep(self._delay_seconds)

        if scenario == "pending":
            try:
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                self.cancel_count += 1
                raise

        if scenario == "raise":
            raise RuntimeError("fake provider failure")

        if scenario == "ok":
            data = self._data
            if data is None:
                data = {"provider": self.key, "security_id": security_id_for(security), "query": query}
            return create_provider_result(status=ProviderStatus.OK, data=data)
        if scenario == "no_data":
            return create_provider_result(status=ProviderStatus.NO_DATA, message="no data")
        if scenario == "invalid_query":
            return create_provider_result(status=ProviderStatus.INVALID_QUERY, message="invalid query")
        if scenario == "timeout":
            return create_provider_result(
                status=ProviderStatus.TIMEOUT,
                error_code="attempt_timeout",
                message="provider attempt timed out",
            )
        if scenario == "rate_limited":
            return create_provider_result(status=ProviderStatus.RATE_LIMITED, message="provider rate limited")
        if scenario == "parse_error":
            return create_provider_result(status=ProviderStatus.PARSE_ERROR, message="provider parse error")
        if scenario == "provider_unavailable":
            return create_provider_result(status=ProviderStatus.PROVIDER_UNAVAILABLE, message="provider unavailable")
        if scenario == "unauthorized":
            return create_provider_result(status=ProviderStatus.UNAUTHORIZED, message="provider unauthorized")

        raise ValueError(f"unsupported fake scenario: {scenario}")

    def _scenario_for_attempt(self) -> FakeScenario:
        index = min(self.attempt_count - 1, len(self._scenarios) - 1)
        return self._scenarios[index]


__all__ = ["FakeProvider", "FakeScenario"]
