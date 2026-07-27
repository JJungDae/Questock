from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import litellm

from app.api.schemas import ChatRequest
from app.config import APPROVED_LLM_MODEL, LLMConfig
from app.runtime import RuntimeConfig, build_runtime
from app.services.service_acceptance import (
    ServiceAcceptanceCase,
    load_service_acceptance_fixture,
    validate_service_acceptance_response,
)
from app.services.service_snapshot import SERVICE_SNAPSHOT_ID

MAX_PROVIDER_ATTEMPTS = 30
PRIMARY_BATCH_ATTEMPTS = 12
MIN_LLM_SUCCESSES = 10
_ENV_KEYS = frozenset(
    {
        "GEMINI_API_KEY",
        "LLM_MAX_OUTPUT_TOKENS",
        "LLM_MODEL",
        "LLM_THINKING_LEVEL",
        "LLM_TIMEOUT_SECONDS",
    }
)
_SAFE_FAILURE_CATEGORIES = frozenset(
    {
        "authentication_error",
        "claim_validation",
        "content_blocked",
        "invalid_response",
        "not_attempted",
        "provider_unavailable",
        "rate_limited",
        "runtime_error",
        "timeout",
        "validation_failed",
    }
)
Completion = Callable[..., Awaitable[Any]]


class ServiceAcceptanceRunError(RuntimeError):
    """Raised when the live acceptance runner cannot continue safely."""


@dataclass(frozen=True)
class LiveCaseResult:
    case_id: str
    public_status: str | None
    expected_security_id: str | None
    expected_intent: str
    policy_satisfied_sources: tuple[str, ...]
    final_cited_sources: tuple[str, ...]
    llm_attempted: bool
    llm_succeeded: bool
    validation_result: str
    safe_failure_category: str | None


@dataclass(frozen=True)
class LiveAcceptanceReport:
    result: str
    provider_attempts_before: int
    provider_attempts_this_run: int
    provider_attempts_total: int
    provider_attempt_limit: int
    llm_eligible_cases: int
    llm_attempted_cases: int
    llm_succeeded_cases: int
    critical_cases: int
    critical_provider_attempts: int
    critical_safe_failures: int
    unsupported_number_failures: int
    wrong_company_failures: int
    uncited_core_number_failures: int
    direct_advice_failures: int
    cases: tuple[LiveCaseResult, ...]


@dataclass(frozen=True)
class LiveFollowupReport:
    result: str
    provider_attempts_before: int
    provider_attempts_this_run: int
    provider_attempts_total: int
    provider_attempt_limit: int
    selected_cases: int
    required_llm_successes: int
    llm_succeeded_cases: int
    cases: tuple[LiveCaseResult, ...]


class ProviderAttemptCounter:
    def __init__(self, state_path: Path) -> None:
        if not isinstance(state_path, Path):
            raise ServiceAcceptanceRunError(
                "provider attempt state is invalid"
            )
        self._path = state_path
        self._attempts = self._load()

    @property
    def attempts(self) -> int:
        return self._attempts

    def wrap(self, completion: Completion) -> Completion:
        if not callable(completion):
            raise ServiceAcceptanceRunError(
                "provider completion is invalid"
            )

        async def counted_completion(**kwargs: Any) -> Any:
            _validate_provider_options(kwargs)
            self._reserve()
            return await completion(**kwargs)

        return counted_completion

    def _load(self) -> int:
        if not self._path.exists():
            return 0
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            raise ServiceAcceptanceRunError(
                "provider attempt state is invalid"
            ) from None
        attempts = (
            payload.get("provider_attempts")
            if isinstance(payload, dict)
            else None
        )
        limit = (
            payload.get("provider_attempt_limit")
            if isinstance(payload, dict)
            else None
        )
        if (
            type(attempts) is not int
            or not 0 <= attempts <= MAX_PROVIDER_ATTEMPTS
            or limit != MAX_PROVIDER_ATTEMPTS
        ):
            raise ServiceAcceptanceRunError(
                "provider attempt state is invalid"
            )
        return attempts

    def _reserve(self) -> None:
        if self._attempts >= MAX_PROVIDER_ATTEMPTS:
            raise ServiceAcceptanceRunError(
                "provider attempt limit exceeded"
            )
        self._attempts += 1
        payload = {
            "provider_attempt_limit": MAX_PROVIDER_ATTEMPTS,
            "provider_attempts": self._attempts,
        }
        temporary = self._path.with_name(f"{self._path.name}.next")
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_text(
                json.dumps(
                    payload,
                    ensure_ascii=True,
                    separators=(",", ":"),
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            temporary.replace(self._path)
        except OSError:
            raise ServiceAcceptanceRunError(
                "provider attempt state could not be saved"
            ) from None


def load_local_llm_environment(path: Path) -> None:
    if not isinstance(path, Path):
        raise ServiceAcceptanceRunError("LLM environment is invalid")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        raise ServiceAcceptanceRunError("LLM environment is invalid") from None
    observed: set[str] = set()
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, separator, raw_value = stripped.partition("=")
        if not separator or key not in _ENV_KEYS or key in observed:
            continue
        value = _unquote_env_value(raw_value.strip())
        os.environ[key] = value
        observed.add(key)
    if observed != _ENV_KEYS:
        raise ServiceAcceptanceRunError("LLM environment is incomplete")
    if not os.environ["GEMINI_API_KEY"]:
        raise ServiceAcceptanceRunError("LLM credential is not configured")
    config = LLMConfig.from_env(require_credential=True)
    if config.safe_summary() != {
        "model": APPROVED_LLM_MODEL,
        "thinking_level": "minimal",
        "max_output_tokens": 1024,
        "timeout_seconds": 10.0,
        "gemini_api_key_configured": True,
    }:
        raise ServiceAcceptanceRunError("LLM environment is invalid")


async def run_primary_acceptance(
    *,
    completion: Completion,
    state_path: Path,
    fixture_path: Path,
) -> LiveAcceptanceReport:
    counter = ProviderAttemptCounter(state_path)
    attempts_before = counter.attempts
    fixture = load_service_acceptance_fixture(fixture_path)
    state = _build_counted_runtime(
        completion=completion,
        counter=counter,
    )

    results: list[LiveCaseResult] = []
    for case in fixture.cases:
        results.append(
            await _run_case(
                case,
                chat_service=state.chat_service,
                counter=counter,
            )
        )
    attempts_this_run = counter.attempts - attempts_before
    if attempts_this_run > PRIMARY_BATCH_ATTEMPTS:
        raise ServiceAcceptanceRunError(
            "primary provider attempt limit exceeded"
        )
    return _build_report(
        cases=fixture.cases,
        results=tuple(results),
        attempts_before=attempts_before,
        attempts_this_run=attempts_this_run,
        attempts_total=counter.attempts,
    )


async def run_followup_acceptance(
    *,
    completion: Completion,
    state_path: Path,
    fixture_path: Path,
    case_ids: tuple[str, ...],
    required_llm_successes: int,
) -> LiveFollowupReport:
    fixture = load_service_acceptance_fixture(fixture_path)
    if (
        not case_ids
        or len(case_ids) != len(set(case_ids))
        or type(required_llm_successes) is not int
        or not 1 <= required_llm_successes <= len(case_ids)
    ):
        raise ServiceAcceptanceRunError(
            "follow-up acceptance selection is invalid"
        )
    cases_by_id = {case.case_id: case for case in fixture.cases}
    try:
        selected = tuple(cases_by_id[case_id] for case_id in case_ids)
    except KeyError:
        raise ServiceAcceptanceRunError(
            "follow-up acceptance selection is invalid"
        ) from None
    if any(case.critical or not case.llm_eligible for case in selected):
        raise ServiceAcceptanceRunError(
            "follow-up acceptance selection is invalid"
        )

    counter = ProviderAttemptCounter(state_path)
    attempts_before = counter.attempts
    if attempts_before + len(selected) > MAX_PROVIDER_ATTEMPTS:
        raise ServiceAcceptanceRunError(
            "provider attempt limit exceeded"
        )
    state = _build_counted_runtime(
        completion=completion,
        counter=counter,
    )
    collected: list[LiveCaseResult] = []
    for case in selected:
        collected.append(
            await _run_case(
                case,
                chat_service=state.chat_service,
                counter=counter,
            )
        )
        if (
            sum(item.llm_succeeded for item in collected)
            >= required_llm_successes
        ):
            break
    results = tuple(collected)
    attempts_this_run = counter.attempts - attempts_before
    if attempts_this_run != len(results):
        raise ServiceAcceptanceRunError(
            "follow-up provider attempt count is invalid"
        )
    successes = sum(item.llm_succeeded for item in results)
    passed = (
        all(item.validation_result == "PASS" for item in results)
        and successes >= required_llm_successes
    )
    return LiveFollowupReport(
        result="PASS" if passed else "FAIL",
        provider_attempts_before=attempts_before,
        provider_attempts_this_run=attempts_this_run,
        provider_attempts_total=counter.attempts,
        provider_attempt_limit=MAX_PROVIDER_ATTEMPTS,
        selected_cases=len(results),
        required_llm_successes=required_llm_successes,
        llm_succeeded_cases=successes,
        cases=results,
    )


async def _run_case(
    case: ServiceAcceptanceCase,
    *,
    chat_service: object,
    counter: ProviderAttemptCounter,
) -> LiveCaseResult:
    before = counter.attempts
    try:
        response = await chat_service.chat(  # type: ignore[attr-defined]
            ChatRequest(
                message=case.question,
                session_id=case.session_id,
            )
        )
        after = counter.attempts
        if after - before not in {0, 1}:
            raise ServiceAcceptanceRunError(
                "case provider attempt count is invalid"
            )
        generation = response.diagnostics_public.generation
        attempted = after > before
        succeeded = (
            attempted
            and generation.mode == "llm"
            and generation.llm_status == "ok"
            and generation.live_verified
        )
        validate_service_acceptance_response(case, response)
        failure = _safe_failure_category(
            attempted=attempted,
            succeeded=succeeded,
            llm_status=generation.llm_status,
            citation_rejection_count=(
                response.diagnostics_public.citation.rejection_count
            ),
        )
        return LiveCaseResult(
            case_id=case.case_id,
            public_status=response.status,
            expected_security_id=case.expected_security_id,
            expected_intent=case.expected_intent,
            policy_satisfied_sources=tuple(
                response.diagnostics_public.decision.satisfied_sources
            ),
            final_cited_sources=tuple(
                item.source_type for item in response.evidence
            ),
            llm_attempted=attempted,
            llm_succeeded=succeeded,
            validation_result="PASS",
            safe_failure_category=failure,
        )
    except ServiceAcceptanceRunError:
        raise
    except Exception:
        return LiveCaseResult(
            case_id=case.case_id,
            public_status=None,
            expected_security_id=case.expected_security_id,
            expected_intent=case.expected_intent,
            policy_satisfied_sources=(),
            final_cited_sources=(),
            llm_attempted=counter.attempts > before,
            llm_succeeded=False,
            validation_result="FAIL",
            safe_failure_category="runtime_error",
        )


def _build_report(
    *,
    cases: tuple[ServiceAcceptanceCase, ...],
    results: tuple[LiveCaseResult, ...],
    attempts_before: int,
    attempts_this_run: int,
    attempts_total: int,
) -> LiveAcceptanceReport:
    llm_eligible = sum(case.llm_eligible for case in cases)
    llm_attempted = sum(item.llm_attempted for item in results)
    llm_succeeded = sum(item.llm_succeeded for item in results)
    critical_ids = {case.case_id for case in cases if case.critical}
    critical_attempts = sum(
        item.llm_attempted
        for item in results
        if item.case_id in critical_ids
    )
    critical_failures = sum(
        item.validation_result != "PASS"
        for item in results
        if item.case_id in critical_ids
    )
    all_valid = all(item.validation_result == "PASS" for item in results)
    safe_fallback = all(
        item.llm_succeeded
        or item.safe_failure_category in _SAFE_FAILURE_CATEGORIES
        for item in results
        if item.llm_attempted
    )
    passed = (
        len(results) == 15
        and all_valid
        and llm_eligible == PRIMARY_BATCH_ATTEMPTS
        and llm_attempted == PRIMARY_BATCH_ATTEMPTS
        and llm_succeeded >= MIN_LLM_SUCCESSES
        and critical_attempts == 0
        and critical_failures == 0
        and safe_fallback
    )
    safety_failures = 0 if all_valid else 1
    return LiveAcceptanceReport(
        result="PASS" if passed else "FAIL",
        provider_attempts_before=attempts_before,
        provider_attempts_this_run=attempts_this_run,
        provider_attempts_total=attempts_total,
        provider_attempt_limit=MAX_PROVIDER_ATTEMPTS,
        llm_eligible_cases=llm_eligible,
        llm_attempted_cases=llm_attempted,
        llm_succeeded_cases=llm_succeeded,
        critical_cases=len(critical_ids),
        critical_provider_attempts=critical_attempts,
        critical_safe_failures=critical_failures,
        unsupported_number_failures=safety_failures,
        wrong_company_failures=safety_failures,
        uncited_core_number_failures=safety_failures,
        direct_advice_failures=safety_failures,
        cases=results,
    )


def _validate_provider_options(kwargs: Mapping[str, Any]) -> None:
    response_format = kwargs.get("response_format")
    schema = (
        response_format.get("json_schema")
        if isinstance(response_format, Mapping)
        else None
    )
    if (
        kwargs.get("model") != APPROVED_LLM_MODEL
        or kwargs.get("reasoning_effort") != "minimal"
        or kwargs.get("max_tokens") != 1024
        or kwargs.get("num_retries") != 0
        or type(kwargs.get("timeout")) not in {int, float}
        or not 0 < float(kwargs["timeout"]) <= 10
        or not isinstance(schema, Mapping)
        or schema.get("strict") is not True
        or not kwargs.get("api_key")
        or any(
            key in kwargs
            for key in (
                "drop_params",
                "extra_body",
                "thinking",
                "thinking_budget",
            )
        )
    ):
        raise ServiceAcceptanceRunError(
            "provider request contract is invalid"
        )


def _safe_failure_category(
    *,
    attempted: bool,
    succeeded: bool,
    llm_status: str | None,
    citation_rejection_count: int,
) -> str | None:
    if succeeded or not attempted:
        return None
    if (
        llm_status == "invalid_response"
        and citation_rejection_count > 0
    ):
        return "claim_validation"
    if llm_status in _SAFE_FAILURE_CATEGORIES:
        return llm_status
    return "invalid_response"


def _unquote_env_value(value: str) -> str:
    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in {'"', "'"}
    ):
        return value[1:-1]
    return value


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument(
        "--fixture",
        type=Path,
        default=Path("tests/fixtures/service_acceptance/fsc_v1.json"),
    )
    parser.add_argument(
        "--state-file",
        type=Path,
        default=Path(".tmp/fsc-live-attempts-20260727-sc06.json"),
    )
    parser.add_argument(
        "--case-id",
        action="append",
        default=[],
    )
    parser.add_argument(
        "--required-llm-successes",
        type=int,
    )
    return parser.parse_args()


def _build_counted_runtime(
    *,
    completion: Completion,
    counter: ProviderAttemptCounter,
) -> Any:
    wrapped = counter.wrap(completion)
    original_completion = litellm.acompletion
    logging.getLogger("questock.observability").disabled = True
    litellm.acompletion = wrapped
    try:
        return build_runtime(
            config=RuntimeConfig(
                source_mode="recorded",
                snapshot_id=SERVICE_SNAPSHOT_ID,
                llm_mode="gemini",
                request_protection_enabled=False,
                response_cache_enabled=False,
            )
        )
    finally:
        litellm.acompletion = original_completion


def main() -> int:
    args = _parse_args()
    try:
        load_local_llm_environment(args.env_file)
        if args.case_id:
            if args.required_llm_successes is None:
                raise ServiceAcceptanceRunError(
                    "follow-up success threshold is required"
                )
            report = asyncio.run(
                run_followup_acceptance(
                    completion=litellm.acompletion,
                    state_path=args.state_file,
                    fixture_path=args.fixture,
                    case_ids=tuple(args.case_id),
                    required_llm_successes=args.required_llm_successes,
                )
            )
        else:
            if args.required_llm_successes is not None:
                raise ServiceAcceptanceRunError(
                    "follow-up acceptance selection is invalid"
                )
            report = asyncio.run(
                run_primary_acceptance(
                    completion=litellm.acompletion,
                    state_path=args.state_file,
                    fixture_path=args.fixture,
                )
            )
    except Exception:
        print(
            json.dumps(
                {
                    "result": "BLOCKED",
                    "safe_failure_category": "runtime_error",
                },
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return 2
    print(
        json.dumps(
            asdict(report),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0 if report.result == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
