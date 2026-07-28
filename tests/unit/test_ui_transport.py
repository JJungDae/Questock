from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from email.message import Message
from typing import Any

import pytest

from app.api.schemas import ChatRequest
from app.services.chat_service import ChatService
from app.ui.transport import (
    DEFAULT_CHAT_ENDPOINT,
    MAX_CHAT_RESPONSE_BYTES,
    ChatTransportError,
    HttpChatTransport,
    build_opaque_client_key,
    load_ui_config,
)

NOW = datetime(2026, 7, 25, 3, tzinfo=UTC)


class FakeResponse:
    def __init__(
        self,
        body: bytes,
        *,
        status: int = 200,
        content_type: str = "application/json",
        content_length: str | None = None,
    ) -> None:
        self.body = body
        self.status = status
        self.read_count = 0
        self.read_size: int | None = None
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        if content_length is not None:
            self.headers["Content-Length"] = content_length

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self, size: int) -> bytes:
        self.read_count += 1
        self.read_size = size
        return self.body[:size]

    def getcode(self) -> int:
        return self.status


class FakeOpener:
    def __init__(
        self,
        response: FakeResponse | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self.response = response
        self.error = error
        self.request: Any | None = None
        self.timeout: float | None = None

    def open(self, request: Any, timeout: float) -> FakeResponse:
        self.request = request
        self.timeout = timeout
        if self.error is not None:
            raise self.error
        assert self.response is not None
        return self.response


def _chat_request() -> ChatRequest:
    return ChatRequest(message="삼성전자 최근 뉴스", session_id="ui-unit")


def _valid_body() -> bytes:
    response = asyncio.run(
        ChatService(utc_now=lambda: NOW).chat(_chat_request())
    )
    return response.model_dump_json().encode("utf-8")


def _send(
    response: FakeResponse,
    *,
    timeout: float = 1.5,
) -> tuple[Any, FakeOpener]:
    opener = FakeOpener(response)
    result = HttpChatTransport(opener=opener).send(_chat_request(), timeout)
    return result, opener


def test_transport_success_and_exact_request_contract() -> None:
    result, opener = _send(FakeResponse(_valid_body()))

    assert result.diagnostics_public.trace_version == "m3-01-v1"
    assert opener.timeout == 1.5
    assert opener.request.full_url == DEFAULT_CHAT_ENDPOINT
    assert opener.request.get_method() == "POST"
    assert json.loads(opener.request.data.decode("utf-8")) == {
        "message": "삼성전자 최근 뉴스",
        "session_id": "ui-unit",
    }


def test_transport_sends_only_opaque_client_key_in_internal_header() -> None:
    secret = b"s" * 32
    client_key = build_opaque_client_key(
        ip_address_value="2001:0db8:0:0:0:0:0:1",
        session_id="ui-unit",
        secret=secret,
    )
    opener = FakeOpener(FakeResponse(_valid_body()))

    result = HttpChatTransport(
        opener=opener,
        client_key=client_key,
    ).send(_chat_request(), 1.5)

    assert result.status in {
        "complete",
        "partial",
        "provider_failed",
        "no_evidence",
        "blocked",
    }
    assert opener.request.get_header("X-questock-client-key") == client_key
    assert json.loads(opener.request.data.decode("utf-8")) == (
        _chat_request().model_dump(mode="json", exclude_none=True)
    )
    assert "2001:db8::1" not in client_key
    assert "ui-unit" not in client_key
    assert secret.decode("ascii") not in client_key


def test_client_key_canonicalizes_ip_and_falls_back_to_session() -> None:
    secret = b"k" * 32

    expanded = build_opaque_client_key(
        ip_address_value="2001:0db8:0:0:0:0:0:1",
        session_id="session-a",
        secret=secret,
    )
    compressed = build_opaque_client_key(
        ip_address_value="2001:db8::1",
        session_id="session-b",
        secret=secret,
    )
    invalid_ip = build_opaque_client_key(
        ip_address_value="not-an-ip",
        session_id="session-a",
        secret=secret,
    )
    missing_ip = build_opaque_client_key(
        ip_address_value=None,
        session_id="session-a",
        secret=secret,
    )

    assert expanded == compressed
    assert invalid_ip == missing_ip
    assert len(expanded) == 64
    assert set(expanded) <= set("0123456789abcdef")


@pytest.mark.parametrize("client_key", ["raw-ip", "A" * 64, "0" * 63])
def test_invalid_transport_client_key_is_sanitized(client_key: str) -> None:
    with pytest.raises(ChatTransportError) as error:
        HttpChatTransport(client_key=client_key)

    assert client_key not in str(error.value)


def test_response_exactly_at_cap_is_not_rejected_as_oversized() -> None:
    payload = _valid_body()
    body = payload + (b" " * (MAX_CHAT_RESPONSE_BYTES - len(payload)))

    result, opener = _send(
        FakeResponse(body, content_length=str(MAX_CHAT_RESPONSE_BYTES))
    )

    assert result.diagnostics_public.trace_version == "m3-01-v1"
    assert opener.response.read_size == MAX_CHAT_RESPONSE_BYTES + 1


def test_response_at_cap_plus_one_is_rejected_without_raw_body() -> None:
    sentinel = b"sentinel-private-body"
    body = b" " * (MAX_CHAT_RESPONSE_BYTES + 1) + sentinel

    with pytest.raises(ChatTransportError) as error:
        _send(FakeResponse(body))

    assert "sentinel" not in str(error.value)


def test_oversized_content_length_is_rejected_before_read() -> None:
    response = FakeResponse(
        b"sentinel-private-body",
        content_length=str(MAX_CHAT_RESPONSE_BYTES + 1),
    )

    with pytest.raises(ChatTransportError):
        _send(response)

    assert response.read_count == 0


def test_no_content_length_streamed_overflow_stops_at_cap_plus_one() -> None:
    response = FakeResponse(b"x" * (MAX_CHAT_RESPONSE_BYTES + 50))

    with pytest.raises(ChatTransportError):
        _send(response)

    assert response.read_size == MAX_CHAT_RESPONSE_BYTES + 1


@pytest.mark.parametrize("status", [301, 302, 307, 308])
def test_redirect_status_is_rejected(status: int) -> None:
    response = FakeResponse(_valid_body(), status=status)

    with pytest.raises(ChatTransportError):
        _send(response)

    assert response.read_count == 0


@pytest.mark.parametrize(
    "endpoint",
    [
        "ftp://example.com/api/chat",
        "https:///api/chat",
        "https://user@example.com/api/chat",
        "https://user:password@example.com/api/chat",
        "https://example.com/api/chat?mode=test",
        "https://example.com/api/chat#fragment",
        "https://example.com:99999/api/chat",
    ],
)
def test_invalid_endpoint_is_rejected_with_sanitized_message(
    endpoint: str,
) -> None:
    with pytest.raises(ChatTransportError) as error:
        HttpChatTransport(endpoint)

    assert endpoint not in str(error.value)
    assert "user" not in str(error.value).casefold()
    assert "password" not in str(error.value).casefold()


@pytest.mark.parametrize(
    "content_type",
    [
        "text/plain",
        "application/problem+json",
        "application/json; charset=euc-kr",
        "application/json; charset=utf-8; version=1",
        "application/json; charset=utf-8; charset=utf-8",
    ],
)
def test_invalid_content_type_is_rejected(content_type: str) -> None:
    with pytest.raises(ChatTransportError):
        _send(FakeResponse(_valid_body(), content_type=content_type))


@pytest.mark.parametrize(
    "content_type",
    [
        "application/json",
        "APPLICATION/JSON",
        "application/json; charset=utf-8",
        "application/json; CHARSET=UTF-8",
    ],
)
def test_exact_json_content_type_policy_accepts_valid_values(
    content_type: str,
) -> None:
    result, _ = _send(FakeResponse(_valid_body(), content_type=content_type))

    assert result.status in {
        "complete",
        "partial",
        "provider_failed",
        "no_evidence",
        "blocked",
    }


@pytest.mark.parametrize(
    "body",
    [
        b"not-json sentinel-private-body",
        b"{}",
        b'{"status":"complete","private":"sentinel-private-body"}',
    ],
)
def test_invalid_json_or_schema_is_sanitized(body: bytes) -> None:
    with pytest.raises(ChatTransportError) as error:
        _send(FakeResponse(body))

    message = str(error.value)
    assert "sentinel" not in message
    assert DEFAULT_CHAT_ENDPOINT not in message


def test_socket_or_timeout_error_is_sanitized() -> None:
    sentinel = "sentinel-private-exception"
    opener = FakeOpener(error=TimeoutError(sentinel))

    with pytest.raises(ChatTransportError) as error:
        HttpChatTransport(opener=opener).send(_chat_request(), 1)

    assert sentinel not in str(error.value)
    assert DEFAULT_CHAT_ENDPOINT not in str(error.value)


@pytest.mark.parametrize("timeout", [0, -1, True, float("nan"), float("inf")])
def test_timeout_must_be_finite_and_positive(timeout: float) -> None:
    with pytest.raises(ChatTransportError) as error:
        HttpChatTransport(opener=FakeOpener()).send(_chat_request(), timeout)

    assert str(timeout) not in str(error.value)


def test_ui_config_defaults_and_sanitized_invalid_values() -> None:
    def empty(_: str) -> None:
        return None

    config = load_ui_config(empty)

    assert config.endpoint == DEFAULT_CHAT_ENDPOINT
    assert config.timeout_seconds == 35

    values = {
        "QUESTOCK_API_URL": "https://user:sentinel@example.com/api/chat",
        "QUESTOCK_UI_TIMEOUT_SECONDS": "sentinel-timeout",
    }
    with pytest.raises(ChatTransportError) as error:
        load_ui_config(values.get)

    assert "sentinel" not in str(error.value)
