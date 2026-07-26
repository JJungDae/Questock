from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import cache
from typing import Literal

from app.services.chat_service import ChatService
from app.services.demo_source_gateway import (
    DemoCorpus,
    DemoCorpusValidationError,
    RecordedDemoSourceGateway,
    load_demo_corpus,
)
from app.services.glossary_service import GlossaryService
from app.services.session_store import InMemorySessionStore
from app.services.source_gateway import ExplicitUnconfiguredSourceGateway

SourceMode = Literal["unconfigured", "recorded"]
_SOURCE_MODE_ENV = "QUESTOCK_SOURCE_MODE"
_RUNTIME_VERSION = "b9-recorded-v1"


class RuntimeConfigurationError(ValueError):
    """Raised when the process runtime cannot be configured safely."""


@dataclass(frozen=True)
class RuntimeConfig:
    source_mode: SourceMode


@dataclass(frozen=True)
class RuntimeState:
    config: RuntimeConfig
    chat_service: ChatService
    corpus: DemoCorpus | None


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
    return RuntimeConfig(source_mode=mode)  # type: ignore[arg-type]


def build_runtime(
    *,
    config: RuntimeConfig | None = None,
    corpus_loader: Callable[[], DemoCorpus] | None = None,
) -> RuntimeState:
    canonical_config = config or load_runtime_config()
    if not isinstance(canonical_config, RuntimeConfig):
        raise RuntimeConfigurationError("runtime config is invalid")
    if canonical_config.source_mode == "unconfigured":
        return RuntimeState(
            config=canonical_config,
            chat_service=ChatService(
                source_gateway=ExplicitUnconfiguredSourceGateway(),
                glossary_service=GlossaryService(),
                session_store=InMemorySessionStore(),
            ),
            corpus=None,
        )
    if canonical_config.source_mode != "recorded":
        raise RuntimeConfigurationError("runtime config is invalid")
    try:
        loader = corpus_loader or load_demo_corpus
        corpus = loader()
        gateway = RecordedDemoSourceGateway(corpus)
    except (DemoCorpusValidationError, OSError, TypeError, ValueError):
        raise RuntimeConfigurationError(
            "recorded runtime data is invalid"
        ) from None
    basis_at = corpus.basis_at
    service = ChatService(
        source_gateway=gateway,
        glossary_service=GlossaryService(),
        session_store=InMemorySessionStore(),
        utc_now=lambda: basis_at,
    )
    return RuntimeState(
        config=canonical_config,
        chat_service=service,
        corpus=corpus,
    )


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
    return {
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
