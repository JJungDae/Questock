from __future__ import annotations

import asyncio
import json
import os
import socket
import tomllib
from copy import deepcopy
from importlib.metadata import version
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from pydantic import BaseModel, ConfigDict

os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
os.environ["LITELLM_LOG"] = "ERROR"

import litellm
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnableSequence
from litellm.llms.custom_httpx.http_handler import AsyncHTTPHandler

litellm.suppress_debug_info = True
litellm.turn_off_message_logging = True


ROOT = Path(__file__).resolve().parents[2]
MODEL = "gemini/gemini-2.5-flash"
SAFE_TIMEOUT_MESSAGE = "Model operation timed out."
HOSTILE_TRACING_ENV = {
    "LANGSMITH_TRACING": "true",
    "LANGSMITH_API_KEY": "dummy",
    "LANGSMITH_ENDPOINT": "http://127.0.0.1:9",
    "LANGSMITH_PROJECT": "questock-m3-00-test",
    "LANGCHAIN_TRACING_V2": "true",
}
DISABLED_TRACING_ENV = {
    "LANGSMITH_TRACING": "false",
    "LANGCHAIN_TRACING_V2": "false",
}


class SpikeOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str
    evidence_ids: list[str]


class FakeProjectModelBoundary:
    def __init__(self, response: str, *, delay: float = 0) -> None:
        self.response = response
        self.delay = delay
        self.call_count = 0
        self.cancel_count = 0
        self.prompts: list[str] = []

    async def __call__(self, prompt_value: Any) -> str:
        self.call_count += 1
        self.prompts.append(prompt_value.to_string())
        try:
            if self.delay:
                await asyncio.sleep(self.delay)
        except asyncio.CancelledError:
            self.cancel_count += 1
            raise
        return self.response


def _build_chain(boundary: FakeProjectModelBoundary) -> RunnableSequence:
    parser = PydanticOutputParser(pydantic_object=SpikeOutput)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Return only the requested JSON.\n{format_instructions}",
            ),
            (
                "human",
                "Question: {question}\n"
                "Evidence ID: {evidence_id}\n"
                "Evidence snippet: {snippet}",
            ),
        ]
    ).partial(format_instructions=parser.get_format_instructions())
    chain = prompt | RunnableLambda(boundary) | parser
    assert isinstance(chain, RunnableSequence)
    return chain


def _input() -> dict[str, str]:
    return {
        "question": "What is the synthetic fact?",
        "evidence_id": "evidence:synthetic",
        "snippet": "Synthetic fact.",
    }


def _valid_output() -> str:
    return json.dumps(
        {
            "answer": "Synthetic fact.",
            "evidence_ids": ["evidence:synthetic"],
        }
    )


async def _invoke_with_timeout(
    chain: RunnableSequence,
    payload: dict[str, str],
    timeout: float,
) -> SpikeOutput:
    try:
        return await asyncio.wait_for(
            chain.ainvoke(payload, config={"callbacks": []}),
            timeout=timeout,
        )
    except TimeoutError:
        raise RuntimeError(SAFE_TIMEOUT_MESSAGE) from None


def _gemini_response() -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": _valid_output()}],
                        "role": "model",
                    },
                    "finishReason": "STOP",
                    "index": 0,
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 11,
                "candidatesTokenCount": 7,
                "totalTokenCount": 18,
            },
        },
        request=httpx.Request("POST", "https://example.invalid"),
    )


def _gemini_error_response(status_code: int) -> httpx.Response:
    return httpx.Response(
        status_code,
        json={
            "error": {
                "code": status_code,
                "message": "sentinel-secret-raw-provider-message",
                "status": "SYNTHETIC_ERROR",
            }
        },
        request=httpx.Request("POST", "https://example.invalid"),
    )


def _schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "answer": {"type": "string"},
            "evidence_ids": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": ["answer", "evidence_ids"],
        "additionalProperties": False,
    }


async def _invoke_mocked_gemini(post: AsyncMock) -> Any:
    client = AsyncHTTPHandler()
    with patch.object(client, "post", post):
        return await litellm.acompletion(
            model=MODEL,
            messages=[{"role": "user", "content": "Synthetic prompt."}],
            timeout=1.5,
            max_tokens=256,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "questock_spike",
                    "schema": _schema(),
                    "strict": True,
                },
            },
            thinking={"type": "enabled", "budget_tokens": 1024},
            num_retries=0,
            api_key="dummy",
            client=client,
        )


def _normalize_litellm_error(exc: Exception) -> tuple[str, str]:
    if isinstance(exc, litellm.AuthenticationError):
        return ("authentication_error", "Model authentication failed.")
    if isinstance(exc, litellm.RateLimitError):
        return ("rate_limited", "Model rate limit reached.")
    if isinstance(exc, litellm.Timeout):
        return ("timeout", "Model request timed out.")
    if isinstance(exc, litellm.ServiceUnavailableError):
        return ("provider_unavailable", "Model provider is unavailable.")
    return ("provider_unavailable", "Model provider is unavailable.")


def test_selected_dependencies_and_lock_are_exact() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    direct = set(project["project"]["dependencies"])
    assert "langchain-core==1.5.1" in direct
    assert "litellm==1.83.7" in direct
    assert all(not item.startswith("langchain-litellm") for item in direct)
    assert all(item != "langchain" for item in direct)
    assert version("langchain-core") == "1.5.1"
    assert version("litellm") == "1.83.7"

    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    locked_versions: dict[str, set[str]] = {}
    for package in lock["package"]:
        locked_versions.setdefault(package["name"], set()).add(package["version"])
    assert "1.5.1" in locked_versions["langchain-core"]
    assert "1.83.7" in locked_versions["litellm"]
    assert "0.10.10" in locked_versions["langsmith"]


def test_real_runnable_sequence_is_async_typed_and_deterministic() -> None:
    boundary = FakeProjectModelBoundary(_valid_output())
    chain = _build_chain(boundary)
    payload = _input()
    snapshot = deepcopy(payload)

    async def invoke_twice() -> tuple[SpikeOutput, SpikeOutput]:
        first = await chain.ainvoke(payload, config={"callbacks": []})
        second = await chain.ainvoke(payload, config={"callbacks": []})
        return first, second

    first, second = asyncio.run(invoke_twice())

    assert [type(step).__name__ for step in chain.steps] == [
        "ChatPromptTemplate",
        "RunnableLambda",
        "PydanticOutputParser",
    ]
    assert first == second == SpikeOutput(
        answer="Synthetic fact.",
        evidence_ids=["evidence:synthetic"],
    )
    assert payload == snapshot
    assert boundary.call_count == 2


def test_prompt_boundary_and_disabled_tracing_make_no_network_call() -> None:
    boundary = FakeProjectModelBoundary(_valid_output())
    chain = _build_chain(boundary)
    network_attempts = 0

    def reject_network(*args: Any, **kwargs: Any) -> None:
        nonlocal network_attempts
        network_attempts += 1
        raise AssertionError("unexpected network call")

    async def invoke_without_network() -> SpikeOutput:
        with patch.object(socket.socket, "connect", reject_network):
            return await chain.ainvoke(_input(), config={"callbacks": []})

    with patch.dict(os.environ, HOSTILE_TRACING_ENV, clear=False):
        with patch.dict(os.environ, DISABLED_TRACING_ENV, clear=False):
            result = asyncio.run(invoke_without_network())

    assert result.answer == "Synthetic fact."
    assert boundary.call_count == 1
    assert network_attempts == 0
    prompt = boundary.prompts[0]
    for expected in (
        "What is the synthetic fact?",
        "evidence:synthetic",
        "Synthetic fact.",
    ):
        assert expected in prompt
    for forbidden in (
        "https://",
        "source_url",
        "locator",
        "provider",
        "permission",
        "local path",
        "sentinel-secret",
        "session history",
    ):
        assert forbidden not in prompt


@pytest.mark.parametrize(
    "response",
    [
        '{"answer":',
        json.dumps(
            {
                "answer": "Synthetic fact.",
                "evidence_ids": "not-a-list",
            }
        ),
        json.dumps(
            {
                "answer": "Synthetic fact.",
                "evidence_ids": ["evidence:synthetic"],
                "extra": "rejected",
            }
        ),
        "Synthetic fact without JSON.",
    ],
)
def test_structured_output_failures_do_not_retry(response: str) -> None:
    boundary = FakeProjectModelBoundary(response)

    with pytest.raises(Exception):
        asyncio.run(
            _build_chain(boundary).ainvoke(
                _input(),
                config={"callbacks": []},
            )
        )

    assert boundary.call_count == 1


def test_outer_timeout_cancels_once_and_returns_sanitized_error() -> None:
    boundary = FakeProjectModelBoundary(_valid_output(), delay=1)

    with pytest.raises(RuntimeError) as exc_info:
        asyncio.run(
            _invoke_with_timeout(
                _build_chain(boundary),
                _input(),
                timeout=0.01,
            )
        )

    assert str(exc_info.value) == SAFE_TIMEOUT_MESSAGE
    assert "Synthetic fact." not in str(exc_info.value)
    assert "sentinel-secret" not in str(exc_info.value)
    assert boundary.call_count == 1
    assert boundary.cancel_count == 1


def test_litellm_gemini_transport_maps_exact_options_and_usage() -> None:
    post = AsyncMock(return_value=_gemini_response())

    async def invoke_without_network() -> Any:
        with patch.object(
            socket.socket,
            "connect",
            side_effect=AssertionError("unexpected network call"),
        ):
            return await _invoke_mocked_gemini(post)

    response = asyncio.run(invoke_without_network())

    assert post.await_count == 1
    request_json = post.await_args.kwargs["json"]
    generation_config = request_json["generationConfig"]
    assert generation_config["max_output_tokens"] == 256
    assert generation_config["thinkingConfig"] == {
        "thinkingBudget": 1024,
        "includeThoughts": True,
    }
    assert generation_config["response_mime_type"] == "application/json"
    assert generation_config["response_json_schema"] == _schema()
    assert response.choices[0].message.content == _valid_output()
    assert response.choices[0].finish_reason == "stop"
    assert response.usage.prompt_tokens == 11
    assert response.usage.completion_tokens == 7
    assert response.usage.total_tokens == 18


@pytest.mark.parametrize(
    ("transport_result", "expected_code"),
    [
        (_gemini_error_response(401), "authentication_error"),
        (_gemini_error_response(429), "rate_limited"),
        (_gemini_error_response(503), "provider_unavailable"),
    ],
)
def test_litellm_http_failures_map_once_without_raw_message(
    transport_result: httpx.Response,
    expected_code: str,
) -> None:
    post = AsyncMock(return_value=transport_result)

    with pytest.raises(Exception) as exc_info:
        asyncio.run(_invoke_mocked_gemini(post))

    code, message = _normalize_litellm_error(exc_info.value)
    assert code == expected_code
    assert post.await_count == 1
    assert "sentinel-secret" not in message
    assert "Synthetic prompt." not in message


def test_litellm_timeout_maps_once_without_raw_message() -> None:
    post = AsyncMock(
        side_effect=httpx.ReadTimeout(
            "sentinel-secret-raw-provider-message",
            request=httpx.Request("POST", "https://example.invalid"),
        )
    )

    with pytest.raises(Exception) as exc_info:
        asyncio.run(_invoke_mocked_gemini(post))

    code, message = _normalize_litellm_error(exc_info.value)
    assert code == "timeout"
    assert post.await_count == 1
    assert "sentinel-secret" not in message
    assert "Synthetic prompt." not in message
