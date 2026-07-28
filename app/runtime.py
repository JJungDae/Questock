from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import cache
from typing import Literal

from app.answer.composer import AnswerComposer
from app.config import ConfigValidationError, LLMConfig
from app.llm.litellm_client import LiteLLMClient
from app.services.chat_service import ChatService
from app.services.demo_source_gateway import (
    DemoCorpus,
    DemoCorpusValidationError,
    RecordedDemoSourceGateway,
    load_demo_corpus,
)
from app.services.glossary_service import GlossaryService
from app.services.m5_news_snapshot import M5NewsSnapshotError
from app.services.m5_source_gateway import M5RecordedSourceGateway
from app.services.market_snapshot_store import (
    MarketSnapshotStoreError,
    RecordedMarketSnapshotStore,
)
from app.services.service_snapshot import (
    SERVICE_SNAPSHOT_ID,
    ServiceSnapshot,
    ServiceSnapshotValidationError,
    load_service_snapshot,
)
from app.services.service_snapshot_gateway import (
    RecordedServiceSnapshotGateway,
)
from app.services.session_store import InMemorySessionStore
from app.services.request_protection import RequestProtector
from app.services.response_cache import ResponseCache
from app.services.source_gateway import ExplicitUnconfiguredSourceGateway

SourceMode = Literal["unconfigured", "recorded"]
LLMMode = Literal["disabled", "gemini"]
_SOURCE_MODE_ENV = "QUESTOCK_SOURCE_MODE"
_SNAPSHOT_ID_ENV = "QUESTOCK_SNAPSHOT_ID"
_LLM_MODE_ENV = "QUESTOCK_LLM_MODE"
_REQUEST_PROTECTION_ENV = "QUESTOCK_REQUEST_PROTECTION_ENABLED"
_RESPONSE_CACHE_ENV = "QUESTOCK_RESPONSE_CACHE_ENABLED"
_RUNTIME_VERSION = "b9-recorded-v1"
_M5_RUNTIME_DATA_VERSION = "m5-01-v1-c963ba0d-438138c4"


class RuntimeConfigurationError(ValueError):
    """Raised when the process runtime cannot be configured safely."""


@dataclass(frozen=True)
class RuntimeConfig:
    source_mode: SourceMode
    snapshot_id: str | None = None
    llm_mode: LLMMode = "disabled"
    request_protection_enabled: bool = False
    response_cache_enabled: bool = False


@dataclass(frozen=True)
class RuntimeState:
    config: RuntimeConfig
    chat_service: ChatService
    corpus: DemoCorpus | ServiceSnapshot | None


def load_runtime_config(
    environment: Mapping[str, str] | None = None,
) -> RuntimeConfig:
    values = os.environ if environment is None else environment
    raw_mode = values.get(_SOURCE_MODE_ENV)
    mode = "unconfigured" if raw_mode is None else raw_mode.strip().casefold()
    if not mode:
        mode = "unconfigured"
    if mode not in {"unconfigured", "recorded"}:
        raise RuntimeConfigurationError("source mode is invalid")
    raw_snapshot_id = values.get(_SNAPSHOT_ID_ENV)
    snapshot_id = (
        None
        if raw_snapshot_id is None or not raw_snapshot_id.strip()
        else raw_snapshot_id.strip()
    )
    if snapshot_id is not None and (
        mode != "recorded" or snapshot_id != SERVICE_SNAPSHOT_ID
    ):
        raise RuntimeConfigurationError("snapshot selection is invalid")
    raw_llm_mode = values.get(_LLM_MODE_ENV)
    llm_mode = (
        "disabled"
        if raw_llm_mode is None or not raw_llm_mode.strip()
        else raw_llm_mode.strip().casefold()
    )
    if llm_mode not in {"disabled", "gemini"}:
        raise RuntimeConfigurationError("LLM mode is invalid")
    request_protection_enabled = _read_switch(
        values,
        _REQUEST_PROTECTION_ENV,
    )
    response_cache_enabled = _read_switch(
        values,
        _RESPONSE_CACHE_ENV,
    )
    return RuntimeConfig(  # type: ignore[arg-type]
        source_mode=mode,
        snapshot_id=snapshot_id,
        llm_mode=llm_mode,
        request_protection_enabled=request_protection_enabled,
        response_cache_enabled=response_cache_enabled,
    )


def build_runtime(
    *,
    config: RuntimeConfig | None = None,
    corpus_loader: Callable[[], DemoCorpus] | None = None,
    snapshot_loader: Callable[[], ServiceSnapshot] | None = None,
) -> RuntimeState:
    canonical_config = config or load_runtime_config()
    if not isinstance(canonical_config, RuntimeConfig):
        raise RuntimeConfigurationError("runtime config is invalid")
    _validate_runtime_config(canonical_config)
    if canonical_config.source_mode == "unconfigured":
        if canonical_config.snapshot_id is not None:
            raise RuntimeConfigurationError("snapshot selection is invalid")
        return RuntimeState(
            config=canonical_config,
            chat_service=_build_chat_service(
                config=canonical_config,
                source_gateway=ExplicitUnconfiguredSourceGateway(),
                snapshot_id="runtime-unconfigured",
            ),
            corpus=None,
        )
    if canonical_config.source_mode != "recorded":
        raise RuntimeConfigurationError("runtime config is invalid")
    try:
        if canonical_config.snapshot_id is None:
            loader = corpus_loader or load_demo_corpus
            corpus: DemoCorpus | ServiceSnapshot = loader()
            gateway = RecordedDemoSourceGateway(corpus)
        else:
            if corpus_loader is not None:
                raise RuntimeConfigurationError(
                    "runtime loader selection is invalid"
                )
            loader = snapshot_loader or load_service_snapshot
            corpus = loader()
            if corpus.snapshot_id != canonical_config.snapshot_id:
                raise ServiceSnapshotValidationError(
                    "snapshot selection is invalid"
                )
            gateway = RecordedServiceSnapshotGateway(corpus)
    except RuntimeConfigurationError:
        raise
    except (
        DemoCorpusValidationError,
        ServiceSnapshotValidationError,
        OSError,
        TypeError,
        ValueError,
    ):
        raise RuntimeConfigurationError(
            "recorded runtime data is invalid"
        ) from None
    basis_at = corpus.basis_at
    try:
        gateway = M5RecordedSourceGateway(gateway)
    except M5NewsSnapshotError:
        raise RuntimeConfigurationError(
            "recorded M5 news data is invalid"
        ) from None
    try:
        market_snapshot_store = RecordedMarketSnapshotStore()
    except MarketSnapshotStoreError:
        raise RuntimeConfigurationError(
            "recorded market data is invalid"
        ) from None
    service = _build_chat_service(
        config=canonical_config,
        source_gateway=gateway,
        snapshot_id=(
            f"{canonical_config.snapshot_id or 'b9-recorded-demo'}."
            f"{_M5_RUNTIME_DATA_VERSION}"
        ),
        utc_now=lambda: basis_at,
        market_snapshot_store=market_snapshot_store,
    )
    return RuntimeState(
        config=canonical_config,
        chat_service=service,
        corpus=corpus,
    )


def _build_chat_service(
    *,
    config: RuntimeConfig,
    source_gateway: object,
    snapshot_id: str,
    utc_now: Callable[[], object] | None = None,
    market_snapshot_store: RecordedMarketSnapshotStore | None = None,
) -> ChatService:
    composer = None
    model_fingerprint = "disabled"
    live_llm_enabled = False
    if config.llm_mode == "gemini":
        try:
            llm_config = LLMConfig.from_env(require_credential=True)
            composer = AnswerComposer(LiteLLMClient(llm_config))
        except (ConfigValidationError, TypeError, ValueError):
            raise RuntimeConfigurationError(
                "LLM runtime configuration is invalid"
            ) from None
        model_fingerprint = hashlib.sha256(
            json.dumps(
                llm_config.safe_summary(),
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        live_llm_enabled = True
    try:
        return ChatService(
            source_gateway=source_gateway,  # type: ignore[arg-type]
            composer=composer,
            glossary_service=GlossaryService(),
            session_store=InMemorySessionStore(),
            request_protector=RequestProtector(
                enabled=config.request_protection_enabled,
            ),
            response_cache=ResponseCache(
                enabled=config.response_cache_enabled,
            ),
            utc_now=utc_now,  # type: ignore[arg-type]
            snapshot_id=snapshot_id,
            model_fingerprint=model_fingerprint,
            live_llm_enabled=live_llm_enabled,
            market_snapshot_store=market_snapshot_store,
        )
    except (MarketSnapshotStoreError, TypeError, ValueError):
        raise RuntimeConfigurationError(
            "runtime service configuration is invalid"
        ) from None


def _validate_runtime_config(config: RuntimeConfig) -> None:
    if (
        config.source_mode not in {"unconfigured", "recorded"}
        or config.llm_mode not in {"disabled", "gemini"}
        or type(config.request_protection_enabled) is not bool
        or type(config.response_cache_enabled) is not bool
        or (
            config.snapshot_id is not None
            and (
                config.source_mode != "recorded"
                or config.snapshot_id != SERVICE_SNAPSHOT_ID
            )
        )
    ):
        raise RuntimeConfigurationError("runtime config is invalid")


def _read_switch(
    values: Mapping[str, str],
    name: str,
) -> bool:
    raw = values.get(name)
    if raw is None or not raw.strip():
        return False
    canonical = raw.strip().casefold()
    if canonical == "true":
        return True
    if canonical == "false":
        return False
    raise RuntimeConfigurationError("runtime switch is invalid")


@cache
def get_runtime_state() -> RuntimeState:
    return build_runtime()


def get_chat_service() -> ChatService:
    return get_runtime_state().chat_service


def get_runtime_health_payload() -> dict[str, object]:
    state = get_runtime_state()
    if state.config.source_mode == "unconfigured":
        return {
            "status": "ok",
            "version": _RUNTIME_VERSION,
            "mode": "unconfigured",
            "data_mode": "unconfigured",
            "live_connectivity_checked": False,
            "sources": {},
            "phase_slice": {
                "status": "unconfigured",
                "scope": "recorded_mvp",
            },
        }
    corpus = state.corpus
    if corpus is None:
        raise RuntimeConfigurationError("recorded runtime data is invalid")
    source_counts = {
        source: sum(
            1 for item in corpus.documents if item.source_type == source
        )
        for source in ("news", "disclosure", "research_report")
    }
    payload: dict[str, object] = {
        "status": "ok",
        "version": corpus.schema_version,
        "mode": "recorded",
        "data_mode": "recorded",
        "live_connectivity_checked": False,
        "basis_at": corpus.basis_at.isoformat().replace("+00:00", "Z"),
        "sources": source_counts,
        "phase_slice": {
            "status": "recorded",
            "scope": "recorded_mvp",
            "document_count": len(corpus.documents),
        },
    }
    if isinstance(corpus, ServiceSnapshot):
        payload["snapshot_id"] = corpus.snapshot_id
        payload["phase_slice"] = {
            "status": "recorded",
            "scope": "service_snapshot",
            "document_count": len(corpus.documents),
            "report_count": corpus.coverage["research_report"][
                "report_count"
            ],
        }
    return payload


__all__ = [
    "RuntimeConfig",
    "RuntimeConfigurationError",
    "RuntimeState",
    "SourceMode",
    "build_runtime",
    "get_chat_service",
    "get_runtime_health_payload",
    "get_runtime_state",
    "load_runtime_config",
]
