from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import math
import os
import re
from dataclasses import dataclass
from email.message import Message
from typing import Any, Callable, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import SplitResult, urlsplit
from urllib.request import (
    HTTPRedirectHandler,
    OpenerDirector,
    Request,
    build_opener,
)

from pydantic import ValidationError

from app.api.schemas import ChatRequest, ChatResponse
from app.services.request_protection import CLIENT_KEY_HEADER

DEFAULT_CHAT_ENDPOINT = "http://127.0.0.1:8000/api/chat"
DEFAULT_UI_TIMEOUT_SECONDS = 35.0
MAX_CHAT_RESPONSE_BYTES = 1_048_576
_CLIENT_KEY = re.compile(r"^[0-9a-f]{64}$")

_CONFIGURATION_FAILURE = "UI 연결 설정을 확인할 수 없습니다."
_REQUEST_FAILURE = "요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요."
_RESPONSE_FAILURE = "서버 응답을 확인할 수 없습니다."


class ChatTransportError(RuntimeError):
    """Sanitized UI transport failure."""


class ChatTransport(Protocol):
    def send(
        self,
        request: ChatRequest,
        timeout_seconds: float,
    ) -> ChatResponse: ...


@dataclass(frozen=True)
class UIConfig:
    endpoint: str = DEFAULT_CHAT_ENDPOINT
    timeout_seconds: float = DEFAULT_UI_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        _validate_endpoint(self.endpoint)
        _validate_timeout(self.timeout_seconds)


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Message,
        newurl: str,
    ) -> None:
        return None


class HttpChatTransport:
    def __init__(
        self,
        endpoint: str = DEFAULT_CHAT_ENDPOINT,
        *,
        opener: OpenerDirector | Any | None = None,
        client_key: str | None = None,
    ) -> None:
        try:
            self._endpoint = _validate_endpoint(endpoint).geturl()
        except (TypeError, ValueError):
            raise ChatTransportError(_CONFIGURATION_FAILURE) from None
        self._opener = opener or build_opener(_NoRedirectHandler())
        if client_key is not None and not _CLIENT_KEY.fullmatch(client_key):
            raise ChatTransportError(_CONFIGURATION_FAILURE)
        self._client_key = client_key

    def send(
        self,
        request: ChatRequest,
        timeout_seconds: float,
    ) -> ChatResponse:
        try:
            timeout = _validate_timeout(timeout_seconds)
        except (TypeError, ValueError):
            raise ChatTransportError(_CONFIGURATION_FAILURE) from None
        payload = json.dumps(
            request.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
        }
        if self._client_key is not None:
            headers[CLIENT_KEY_HEADER] = self._client_key
        http_request = Request(
            self._endpoint,
            data=payload,
            headers=headers,
            method="POST",
        )

        try:
            with self._opener.open(http_request, timeout=timeout) as response:
                status = _response_status(response)
                if status is not None and not 200 <= status < 300:
                    raise ChatTransportError(_REQUEST_FAILURE)
                _validate_json_content_type(response.headers)
                body = _read_capped_body(response)
        except ChatTransportError:
            raise
        except (HTTPError, URLError, TimeoutError, OSError, ValueError):
            raise ChatTransportError(_REQUEST_FAILURE) from None

        try:
            decoded = body.decode("utf-8")
            raw_payload = json.loads(decoded)
            return ChatResponse.model_validate(raw_payload)
        except (UnicodeDecodeError, json.JSONDecodeError, ValidationError, TypeError):
            raise ChatTransportError(_RESPONSE_FAILURE) from None


def load_ui_config(
    getenv: Callable[[str], str | None] = os.getenv,
) -> UIConfig:
    endpoint = getenv("QUESTOCK_API_URL") or DEFAULT_CHAT_ENDPOINT
    raw_timeout = getenv("QUESTOCK_UI_TIMEOUT_SECONDS")
    if raw_timeout is None or not raw_timeout.strip():
        timeout = DEFAULT_UI_TIMEOUT_SECONDS
    else:
        try:
            timeout = float(raw_timeout)
        except (TypeError, ValueError):
            raise ChatTransportError(_CONFIGURATION_FAILURE) from None

    try:
        return UIConfig(endpoint=endpoint, timeout_seconds=timeout)
    except (TypeError, ValueError):
        raise ChatTransportError(_CONFIGURATION_FAILURE) from None


def build_opaque_client_key(
    *,
    ip_address_value: object,
    session_id: str,
    secret: bytes,
) -> str:
    if (
        not isinstance(session_id, str)
        or not session_id
        or len(session_id) > 128
        or not isinstance(secret, bytes)
        or len(secret) < 32
    ):
        raise ChatTransportError(_CONFIGURATION_FAILURE)
    identity = f"session:{session_id}"
    if isinstance(ip_address_value, str) and ip_address_value.strip():
        try:
            canonical_ip = ipaddress.ip_address(
                ip_address_value.strip()
            ).compressed
        except ValueError:
            canonical_ip = None
        if canonical_ip is not None:
            identity = f"ip:{canonical_ip}"
    return hmac.new(
        secret,
        identity.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _validate_endpoint(endpoint: str) -> SplitResult:
    if not isinstance(endpoint, str) or not endpoint.strip():
        raise ValueError("invalid endpoint")
    parsed = urlsplit(endpoint.strip())
    try:
        port = parsed.port
    except ValueError:
        raise ValueError("invalid endpoint") from None
    if (
        parsed.scheme.casefold() not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or (port is not None and not 1 <= port <= 65535)
    ):
        raise ValueError("invalid endpoint")
    return parsed


def _validate_timeout(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("invalid timeout")
    timeout = float(value)
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("invalid timeout")
    return timeout


def _response_status(response: Any) -> int | None:
    status = getattr(response, "status", None)
    if status is None and hasattr(response, "getcode"):
        status = response.getcode()
    return status if isinstance(status, int) else None


def _header_values(headers: Mapping[str, str] | Message, name: str) -> list[str]:
    get_all = getattr(headers, "get_all", None)
    if callable(get_all):
        values = get_all(name)
        if values is not None:
            return [str(value) for value in values]
    value = headers.get(name)
    return [] if value is None else [str(value)]


def _validate_json_content_type(
    headers: Mapping[str, str] | Message,
) -> None:
    values = _header_values(headers, "Content-Type")
    if len(values) != 1:
        raise ChatTransportError(_RESPONSE_FAILURE)
    parts = [part.strip() for part in values[0].split(";")]
    if not parts or parts[0].casefold() != "application/json":
        raise ChatTransportError(_RESPONSE_FAILURE)
    parameters = parts[1:]
    if len(parameters) > 1:
        raise ChatTransportError(_RESPONSE_FAILURE)
    if parameters:
        if "=" not in parameters[0]:
            raise ChatTransportError(_RESPONSE_FAILURE)
        key, value = (item.strip().casefold() for item in parameters[0].split("=", 1))
        if key != "charset" or value != "utf-8":
            raise ChatTransportError(_RESPONSE_FAILURE)


def _read_capped_body(response: Any) -> bytes:
    content_lengths = _header_values(response.headers, "Content-Length")
    if len(content_lengths) > 1:
        raise ChatTransportError(_RESPONSE_FAILURE)
    if content_lengths:
        try:
            declared_length = int(content_lengths[0])
        except ValueError:
            raise ChatTransportError(_RESPONSE_FAILURE) from None
        if declared_length < 0:
            raise ChatTransportError(_RESPONSE_FAILURE)
        if declared_length > MAX_CHAT_RESPONSE_BYTES:
            raise ChatTransportError(_RESPONSE_FAILURE)

    body = response.read(MAX_CHAT_RESPONSE_BYTES + 1)
    if not isinstance(body, bytes) or len(body) > MAX_CHAT_RESPONSE_BYTES:
        raise ChatTransportError(_RESPONSE_FAILURE)
    return body


__all__ = [
    "ChatTransport",
    "ChatTransportError",
    "DEFAULT_CHAT_ENDPOINT",
    "DEFAULT_UI_TIMEOUT_SECONDS",
    "HttpChatTransport",
    "MAX_CHAT_RESPONSE_BYTES",
    "UIConfig",
    "build_opaque_client_key",
    "load_ui_config",
]
