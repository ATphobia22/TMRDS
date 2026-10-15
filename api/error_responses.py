"""Stable, sanitized API errors and request correlation.

Never include exception text or upstream response bodies in public errors.
Detailed diagnostics should be logged only by a redacting logging boundary.
"""
from __future__ import annotations

import re
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import HTTPException

_SAFE_LABEL = re.compile(r"[A-Za-z0-9 ._-]{1,64}\Z")
_SAFE_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,64}\Z")


def safe_upstream_error(
    service_label: str,
    _internal_detail: object | None = None,
    *,
    status_code: int = 502,
) -> HTTPException:
    """Create a stable public error without exposing internal details."""
    label = service_label.strip() if _SAFE_LABEL.fullmatch(service_label) else ""
    if status_code == 502:
        code = "UPSTREAM_FAILURE"
        message = f"{label} upstream request failed." if label else "Upstream request failed."
    else:
        code = "DEPENDENCY_UNAVAILABLE"
        message = f"{label} dependency is unavailable." if label else "Required dependency is unavailable."
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


class RequestCorrelationMiddleware:
    """ASGI middleware that sets a safe request ID response header."""

    def __init__(self, app: Callable[..., Awaitable[None]]) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Callable[..., Awaitable[Any]], send: Callable[..., Awaitable[Any]]) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        supplied = headers.get(b"x-request-id", b"").decode("ascii", errors="ignore")
        request_id = supplied if _SAFE_REQUEST_ID.fullmatch(supplied) else str(uuid.uuid4())

        async def send_with_request_id(message: dict[str, Any]) -> None:
            if message.get("type") == "http.response.start":
                response_headers = list(message.get("headers", []))
                response_headers.append((b"x-request-id", request_id.encode("ascii")))
                message = {**message, "headers": response_headers}
            await send(message)

        await self.app(scope, receive, send_with_request_id)
