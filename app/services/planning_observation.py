from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

from app.core.models import QueryPlan, SecurityIdentifier, SessionContext
from app.core.resolver import (
    ResolutionResult,
    SecurityResolver,
    security_id_for,
)
from app.core.status import ResolutionStatus
from app.planning.query_planner import (
    QueryPlanner,
    _Candidate,
    _candidate_spans,
    _is_contained_by_resolved,
    _normalize_security_text,
)

PublicResolutionStatus = Literal[
    "resolved",
    "ambiguous",
    "not_found",
    "unsupported",
]


@dataclass(frozen=True)
class ObservedQueryPlan:
    plan: QueryPlan
    resolution_status: PublicResolutionStatus
    security_id: str | None


class _ObservingSecurityResolver:
    def __init__(self, delegate: SecurityResolver) -> None:
        self._delegate = delegate
        self._statuses: list[str] = []
        self._resolved_security_ids: set[str] = set()

    @property
    def has_observations(self) -> bool:
        return bool(self._statuses)

    def resolve(self, query: str) -> ResolutionResult:
        result = self._delegate.resolve(query)
        status = str(result.status)
        self._statuses.append(status)
        if (
            status == ResolutionStatus.RESOLVED
            and result.security is not None
        ):
            self._resolved_security_ids.add(security_id_for(result.security))
        return result.model_copy(deep=True)

    def observe_query(self, query: str) -> None:
        accepted: list[tuple[_Candidate, SecurityIdentifier]] = []
        normalized = _normalize_security_text(query)
        for candidate in _candidate_spans(normalized):
            if _is_contained_by_resolved(candidate, accepted):
                continue
            result = self.resolve(candidate.text)
            if (
                result.status == ResolutionStatus.RESOLVED
                and result.security is not None
            ):
                accepted.append((candidate, result.security))

    def public_status(
        self,
        plan: QueryPlan,
        *,
        fallback_observation: bool,
    ) -> PublicResolutionStatus:
        if len(self._resolved_security_ids) > 1:
            return "ambiguous"
        if plan.security is not None:
            return "resolved"
        if ResolutionStatus.AMBIGUOUS.value in self._statuses:
            return "ambiguous"
        if ResolutionStatus.UNSUPPORTED.value in self._statuses:
            return "unsupported"
        if fallback_observation and len(self._resolved_security_ids) == 1:
            return "resolved"
        return "not_found"

    def public_security_id(
        self,
        plan: QueryPlan,
        *,
        resolution_status: PublicResolutionStatus,
        fallback_observation: bool,
    ) -> str | None:
        if resolution_status != "resolved":
            return None
        if len(self._resolved_security_ids) > 1:
            return None
        if plan.security is not None:
            return security_id_for(plan.security)
        if fallback_observation and len(self._resolved_security_ids) == 1:
            return next(iter(self._resolved_security_ids))
        return None


def build_observed_query_plan(
    query: str,
    *,
    basis_date: date,
    resolver: SecurityResolver,
    session: SessionContext | None = None,
) -> ObservedQueryPlan:
    observer = _ObservingSecurityResolver(resolver)
    plan = QueryPlanner(
        resolver=observer,  # type: ignore[arg-type]
        basis_date=basis_date,
    ).plan(query, session=session)
    fallback_observation = not observer.has_observations
    if fallback_observation:
        observer.observe_query(query)
    resolution_status = observer.public_status(
        plan,
        fallback_observation=fallback_observation,
    )
    return ObservedQueryPlan(
        plan=plan,
        resolution_status=resolution_status,
        security_id=observer.public_security_id(
            plan,
            resolution_status=resolution_status,
            fallback_observation=fallback_observation,
        ),
    )


__all__ = [
    "ObservedQueryPlan",
    "PublicResolutionStatus",
    "build_observed_query_plan",
]
