"""FastAPI dependency for optional fail-closed service-to-service authentication."""
from __future__ import annotations

import json
import os
from functools import lru_cache

from fastapi import Header, HTTPException
from jwt.exceptions import PyJWTError

from engines.service_identity import ServiceTokenValidator


@lru_cache(maxsize=1)
def _validator() -> ServiceTokenValidator | None:
    jwks_text = os.getenv("TMRDS_SERVICE_JWKS_JSON", "").strip()
    issuer = os.getenv("TMRDS_SERVICE_ISSUER", "").strip()
    audience = os.getenv("TMRDS_SERVICE_AUDIENCE", "").strip()
    if not any((jwks_text, issuer, audience)):
        return None
    if not all((jwks_text, issuer, audience)):
        raise RuntimeError("service authentication configuration is incomplete")
    try:
        document = json.loads(jwks_text)
        keys = document.get("keys", document) if isinstance(document, dict) else document
        if not isinstance(keys, list) or not keys or not all(isinstance(key, dict) for key in keys):
            raise ValueError("JWKS must contain a keys array")
        return ServiceTokenValidator.from_jwks(keys, issuer=issuer, audience=audience)
    except (ValueError, TypeError, KeyError, PyJWTError) as exc:
        raise RuntimeError("TMRDS_SERVICE_JWKS_JSON is invalid") from exc


async def require_service_identity(
    authorization: str | None = Header(default=None),
) -> dict[str, object] | None:
    """Validate a bearer service token when service authentication is required."""
    production = os.getenv("TMRDS_ENV", "development").strip().casefold() in {"production", "prod"}
    configured_required = os.getenv("TMRDS_SERVICE_AUTH_REQUIRED", "false").casefold() == "true"
    required = production or configured_required
    if not required:
        return None
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.casefold() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="service bearer token required")
    try:
        validator = _validator()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="service authentication is unavailable") from exc
    if validator is None:
        raise HTTPException(status_code=503, detail="service authentication is not configured")
    try:
        claims = validator.validate(token.strip(), required_scopes={"evidence.write"})
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="invalid service identity") from exc
    return {"sub": claims.subject, "scopes": sorted(claims.scopes), "kid": claims.key_id}
