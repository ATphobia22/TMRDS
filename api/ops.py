"""TMRDS API operations: observability, rate limiting, security headers, startup posture.

Implements the October 2026 ops research: RED metrics via
prometheus-fastapi-instrumentator at /metrics, sliding-window rate limiting via
slowapi keyed on client IP with Retry-After on 429, baseline security headers,
structured startup logging, and fail-closed startup checks.

Research-advisory only. Not SaMD.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any, Callable

logger = logging.getLogger("tmrds.ops")

DEFAULT_RATE_LIMIT = "120/minute"
FEDERATED_SEARCH_RATE_LIMIT = "20/minute"

_metrics_enabled = False
_rate_limiting_enabled = False

try:
    from prometheus_fastapi_instrumentator import Instrumentator

    _instrumentator_available = True
except ImportError:  # pragma: no cover - depends on installed extras
    Instrumentator = None  # type: ignore[assignment]
    _instrumentator_available = False

try:
    from slowapi import Limiter
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    from slowapi.util import get_remote_address

    _slowapi_available = True
except ImportError:  # pragma: no cover - depends on installed extras
    Limiter = None  # type: ignore[assignment]
    RateLimitExceeded = Exception  # type: ignore[assignment]
    SlowAPIMiddleware = None  # type: ignore[assignment]
    _slowapi_available = False

    def get_remote_address(request: Any) -> str:  # type: ignore[no-redef]
        return "127.0.0.1"


def _rate_limit_key(request: Any) -> str:
    """Key rate limits on API identity when the key gate is active, else client IP.

    The ApiKeyGateMiddleware runs outer (added later) and stores api_key_id in
    scope state before SlowAPIMiddleware evaluates this function.
    """
    try:
        key_id = request.scope.get("state", {}).get("api_key_id")
    except Exception:
        key_id = None
    if key_id:
        return f"apikey:{key_id}"
    return get_remote_address(request)


# Shared limiter so route modules can apply per-route tiers with @limiter.limit(...).
# slowapi decorators require the route to accept `request: Request`.
# When slowapi is not installed, `limiter` is a no-op shim so route modules
# import cleanly and the missing dependency is only a logged warning.
class _NoOpLimiter:
    def limit(self, *args: Any, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return func

        return decorator


limiter: Any = None
if _slowapi_available:
    # NOTE: headers_enabled stays False (slowapi default). Enabling it requires
    # every @limiter.limit route to declare `response: Response`, which is
    # fragile with this codebase's plain-dict routes. Clients still get
    # Retry-After on every 429 from our custom handler below.
    limiter = Limiter(
        key_func=_rate_limit_key,
        default_limits=[DEFAULT_RATE_LIMIT],
    )
else:
    limiter = _NoOpLimiter()


class _RequestIdFilter(logging.Filter):
    """Ensure the request_id field exists on every record (defaults to "-")."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


def configure_logging() -> None:
    """Configure stdlib logging once. Never logs secret values."""
    if logging.getLogger().handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s")
    )
    handler.addFilter(_RequestIdFilter())
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)


def setup_metrics(app: Any) -> bool:
    """Expose Prometheus RED metrics at /metrics. Returns True when enabled."""
    global _metrics_enabled
    if not _instrumentator_available or Instrumentator is None:
        logger.warning("prometheus-fastapi-instrumentator not installed; /metrics disabled")
        _metrics_enabled = False
        return False
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    _metrics_enabled = True
    logger.info("metrics enabled at /metrics")
    return True


def _retry_after_seconds(exc: BaseException) -> int:
    """Best-effort Retry-After from a slowapi limit description; defaults to 60."""
    detail = str(getattr(exc, "detail", ""))
    match = re.search(r"per\s+1\s+(second|minute|hour|day)", detail, re.IGNORECASE)
    if match:
        return {"second": 1, "minute": 60, "hour": 3600, "day": 86400}[match.group(1).lower()]
    return 60


async def _rate_limit_exceeded_handler(request: Any, exc: BaseException) -> Any:
    from fastapi.responses import JSONResponse

    retry_after = _retry_after_seconds(exc)
    request_id = ""
    try:
        request_id = request.scope.get("state", {}).get("request_id", "")
    except Exception:
        pass
    logger.warning("rate limit exceeded for %s request_id=%s", get_remote_address(request), request_id)
    return JSONResponse(
        status_code=429,
        headers={"Retry-After": str(retry_after)},
        content={
            "detail": {
                "code": "RATE_LIMITED",
                "message": f"Rate limit exceeded. Retry after {retry_after} seconds.",
            }
        },
    )


def setup_rate_limiting(app: Any) -> bool:
    """Attach the shared slowapi limiter and a sanitized 429 handler."""
    global _rate_limiting_enabled
    if not _slowapi_available or SlowAPIMiddleware is None:
        logger.warning("slowapi not installed; rate limiting disabled")
        _rate_limiting_enabled = False
        return False
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    app.add_middleware(SlowAPIMiddleware)
    _rate_limiting_enabled = True
    logger.info("rate limiting enabled (default %s)", DEFAULT_RATE_LIMIT)
    return True


class SecurityHeadersMiddleware:
    """Baseline security headers for API responses."""

    def __init__(self, app: Callable[..., Any]) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Callable[..., Any], send: Callable[..., Any]) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: dict[str, Any]) -> None:
            if message.get("type") == "http.response.start":
                headers = [(n, v) for n, v in message.get("headers", []) if n.lower() not in _OVERWRITTEN]
                headers.extend(
                    [
                        (b"x-content-type-options", b"nosniff"),
                        (b"x-frame-options", b"DENY"),
                        (b"referrer-policy", b"no-referrer"),
                        (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
                    ]
                )
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)


_OVERWRITTEN = {b"x-content-type-options", b"x-frame-options", b"referrer-policy", b"permissions-policy"}


def metrics_enabled() -> bool:
    return _metrics_enabled


def rate_limiting_enabled() -> bool:
    return _rate_limiting_enabled
