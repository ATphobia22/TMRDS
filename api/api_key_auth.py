"""Optional API-key gate for the TMRDS research API.

v1 scope, per the October 2026 auth research:
- Keys are prefixed (``tmrds_<key_id>_<secret>``), hashed at rest (SHA-256 of
  the secret only), and revocable (delete the line).
- Keys live in a file (``TMRDS_API_KEYS_FILE``), never as secret values in the
  environment — environment values are visible via ``docker inspect``.
- If ``TMRDS_API_KEYS_FILE`` is configured but cannot be loaded, API paths
  fail closed with HTTP 503. Liveness and monitoring paths remain accessible
  so operators can repair the configuration without exposing protected routes.
  Leaving the variable unset intentionally permits public research access.
- Denials are logged with the key_id only. Raw keys/secrets are never logged.
- 401 vs 403: missing/invalid key -> 401. (Per-key scopes are future work;
  v1 grants the single research scope or nothing.)

Research-advisory only. Not SaMD.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import re
from typing import Any, Callable

logger = logging.getLogger("tmrds.auth")

KEY_ID_RE = re.compile(r"[a-z0-9]{4,32}\Z")
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
PRESENTED_RE = re.compile(r"tmrds_([a-z0-9]{4,32})_([A-Za-z0-9._-]{16,128})\Z")


def load_api_keys(path: str) -> dict[str, str]:
    """Load ``key_id -> sha256(secret)`` from a key file. Fail closed on any problem."""
    keys: dict[str, str] = {}
    try:
        raw = open(path, encoding="utf-8").read()
    except OSError as exc:
        raise RuntimeError(f"fail-closed: cannot read TMRDS_API_KEYS_FILE at {path}: {exc}") from exc
    for line_number, raw_line in enumerate(raw.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(":", 1)
        if len(parts) != 2 or not KEY_ID_RE.fullmatch(parts[0]) or not SHA256_RE.fullmatch(parts[1].lower()):
            raise RuntimeError(
                f"fail-closed: malformed key entry at {path}:{line_number} "
                "(expected 'key_id:sha256_hex', key_id [a-z0-9]{4,32})"
            )
        key_id = parts[0]
        if key_id in keys:
            raise RuntimeError(f"fail-closed: duplicate key_id '{key_id}' at {path}:{line_number}")
        keys[key_id] = parts[1].lower()
    if not keys:
        raise RuntimeError(f"fail-closed: no usable keys in TMRDS_API_KEYS_FILE at {path}")
    return keys


def check_startup_posture() -> dict[str, Any]:
    """Validate auth configuration at startup.

    The public research API is deliberately open when no key file is set.
    A configured but invalid key file is a deployment error: report the
    problem without exposing sensitive filesystem details to API clients,
    and make API routes unavailable rather than silently disabling auth.
    """
    keys_file = os.environ.get("TMRDS_API_KEYS_FILE", "").strip()
    if not keys_file:
        logger.info("auth posture: open (TMRDS_API_KEYS_FILE unset; public research data)")
        return {"auth": "open", "keys": None}
    try:
        keys = load_api_keys(keys_file)
    except RuntimeError as exc:
        logger.critical(
            "auth posture: UNAVAILABLE — configured API-key file invalid; "
            "all /api/* requests will return 503 until repaired: %s",
            exc,
        )
        return {
            "auth": "unavailable",
            "keys": None,
            "warning": "Configured API-key authentication is unavailable; API requests are denied.",
        }
    logger.info("auth posture: key-gated (%d key(s) loaded; file=%s)", len(keys), keys_file)
    return {"auth": "key-gated", "keys": keys}


def _unauthorized() -> dict[str, Any]:
    return {
        "type": "http.response.start",
        "status": 401,
        "headers": [(b"content-type", b"application/json"), (b"www-authenticate", b"APIKey")],
    }


_UNAUTHORIZED_BODY = b'{"detail":{"code":"UNAUTHORIZED","message":"Valid API key required."}}'


class ApiKeyConfigurationUnavailableMiddleware:
    """Deny API requests when an explicitly configured key file cannot load."""

    def __init__(self, app: Callable[..., Any]) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Callable[..., Any], send: Callable[..., Any]) -> None:
        if scope.get("type") != "http" or not str(scope.get("path", "")).startswith("/api/"):
            await self.app(scope, receive, send)
            return
        await send({
            "type": "http.response.start",
            "status": 503,
            "headers": [(b"content-type", b"application/json"), (b"cache-control", b"no-store")],
        })
        await send({
            "type": "http.response.body",
            "body": b'{"detail":{"code":"AUTH_UNAVAILABLE","message":"API authentication is temporarily unavailable."}}',
        })


class ApiKeyGateMiddleware:
    """Require a valid X-API-Key for /api/* paths. Health and /metrics stay open."""

    def __init__(self, app: Callable[..., Any], keys: dict[str, str]) -> None:
        self.app = app
        self.keys = keys

    async def __call__(self, scope: dict[str, Any], receive: Callable[..., Any], send: Callable[..., Any]) -> None:
        if scope.get("type") != "http" or not str(scope.get("path", "")).startswith("/api/"):
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        presented = headers.get(b"x-api-key", b"").decode("ascii", errors="ignore").strip()
        match = PRESENTED_RE.fullmatch(presented)
        key_id = match.group(1) if match else None

        authorized = False
        if match:
            secret = match.group(2)
            expected = self.keys.get(key_id or "")
            if expected is not None:
                candidate = hashlib.sha256(secret.encode("utf-8")).hexdigest()
                authorized = hmac.compare_digest(candidate, expected)

        if not authorized:
            # Log the key_id (never the secret) so abuse can be traced and revoked.
            logger.warning("auth denial for /api path key_id=%s", key_id or "unknown")
            await send(_unauthorized())
            await send({"type": "http.response.body", "body": _UNAUTHORIZED_BODY})
            return

        scope.setdefault("state", {})["api_key_id"] = key_id
        # Append-only audit of the auth decision (allow). key_id only — never the secret.
        logger.info("auth allow key_id=%s path=%s", key_id, scope.get("path", ""))
        await self.app(scope, receive, send)
