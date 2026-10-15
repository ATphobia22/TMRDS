from __future__ import annotations

import pytest

from fastapi import HTTPException

from api.error_responses import safe_upstream_error


def test_safe_upstream_error_uses_stable_public_contract() -> None:
    secret_detail = "Authorization: Bearer extremely-sensitive-token"
    error = safe_upstream_error("CDC", secret_detail)

    assert isinstance(error, HTTPException)
    assert error.status_code == 502
    assert error.detail == {
        "code": "UPSTREAM_FAILURE",
        "message": "CDC upstream request failed.",
    }
    assert secret_detail not in str(error.detail)


def test_safe_upstream_error_rejects_untrusted_service_label() -> None:
    error = safe_upstream_error("CDC\nAuthorization", "secret")

    assert error.detail == {
        "code": "UPSTREAM_FAILURE",
        "message": "Upstream request failed.",
    }


@pytest.mark.asyncio
async def test_request_correlation_middleware_replaces_unsafe_request_id() -> None:
    from api.error_responses import RequestCorrelationMiddleware

    messages = []

    async def downstream(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    middleware = RequestCorrelationMiddleware(downstream)
    await middleware(
        {"type": "http", "headers": [(b"x-request-id", b"bad\\r\\nid")]},
        receive,
        send,
    )

    headers = dict(messages[0]["headers"])
    request_id = headers[b"x-request-id"].decode("ascii")
    assert len(request_id) == 36
    assert request_id.count("-") == 4


@pytest.mark.asyncio
async def test_request_correlation_middleware_preserves_safe_request_id() -> None:
    from api.error_responses import RequestCorrelationMiddleware

    messages = []

    async def downstream(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    middleware = RequestCorrelationMiddleware(downstream)
    await middleware(
        {"type": "http", "headers": [(b"x-request-id", b"trace_123") ]},
        receive,
        send,
    )

    assert dict(messages[0]["headers"])[b"x-request-id"] == b"trace_123"
