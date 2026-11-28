"""Regression coverage for fail-closed service authentication."""
import asyncio

import pytest
from fastapi import HTTPException

from api import security_dependencies as auth


@pytest.fixture(autouse=True)
def production(monkeypatch):
    monkeypatch.setenv("TMRDS_ENV", "production")
    for name in ("TMRDS_SERVICE_JWKS_JSON", "TMRDS_SERVICE_ISSUER", "TMRDS_SERVICE_AUDIENCE"):
        monkeypatch.delenv(name, raising=False)
    auth._validator.cache_clear()
    yield
    auth._validator.cache_clear()


@pytest.mark.parametrize("document", ["{", "{}", '{"keys":[]}', '{"keys":[null]}', '{"keys":[{"kid":"test"}]}'])
def test_invalid_configuration_returns_503(monkeypatch, document):
    monkeypatch.setenv("TMRDS_SERVICE_JWKS_JSON", document)
    monkeypatch.setenv("TMRDS_SERVICE_ISSUER", "test")
    monkeypatch.setenv("TMRDS_SERVICE_AUDIENCE", "test")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(auth.require_service_identity("Bearer a.b.c"))
    assert exc.value.status_code == 503


@pytest.mark.parametrize("header", [None, "", "Bearer ", "Basic a.b.c"])
def test_missing_bearer_returns_401(header):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(auth.require_service_identity(header))
    assert exc.value.status_code == 401


def test_partial_configuration_returns_503(monkeypatch):
    monkeypatch.setenv("TMRDS_SERVICE_ISSUER", "test")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(auth.require_service_identity("bearer a.b.c"))
    assert exc.value.status_code == 503


def test_missing_configuration_returns_503():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(auth.require_service_identity("Bearer a.b.c"))
    assert exc.value.status_code == 503
