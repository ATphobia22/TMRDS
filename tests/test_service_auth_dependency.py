from __future__ import annotations

import os

import pytest
from fastapi import HTTPException

from api.security_dependencies import _validator, require_service_identity


@pytest.mark.asyncio
async def test_service_auth_is_optional_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TMRDS_SERVICE_AUTH_REQUIRED", raising=False)
    assert await require_service_identity(None) is None


@pytest.mark.asyncio
async def test_required_service_auth_rejects_missing_bearer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TMRDS_SERVICE_AUTH_REQUIRED", "true")
    with pytest.raises(HTTPException) as exc_info:
        await require_service_identity(None)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_required_service_auth_fails_closed_without_validator(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TMRDS_SERVICE_AUTH_REQUIRED", "true")
    monkeypatch.setenv("TMRDS_SERVICE_JWKS_JSON", "")
    monkeypatch.setenv("TMRDS_SERVICE_ISSUER", "")
    monkeypatch.setenv("TMRDS_SERVICE_AUDIENCE", "")
    _validator.cache_clear()
    with pytest.raises(HTTPException) as exc_info:
        await require_service_identity("Bearer malformed")
    assert exc_info.value.status_code == 503
