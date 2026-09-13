from __future__ import annotations

import ipaddress

import pytest

from engines.secure_http import OutboundRequestPolicy


def test_rejects_non_https_and_embedded_credentials() -> None:
    policy = OutboundRequestPolicy()
    with pytest.raises(ValueError):
        policy.validate_url("http://example.org/data")
    with pytest.raises(ValueError):
        policy.validate_url("https://user:password@example.org/data")


def test_rejects_private_and_loopback_addresses() -> None:
    policy = OutboundRequestPolicy(resolve_host=lambda host: [ipaddress.ip_address("127.0.0.1")])
    with pytest.raises(ValueError, match="private"):
        policy.validate_url("https://example.org/data")


def test_allowlisted_local_infrastructure_is_explicit() -> None:
    policy = OutboundRequestPolicy(allowed_private_hosts={"tmrds-postgres"}, resolve_host=lambda host: [ipaddress.ip_address("10.0.0.2")])
    assert policy.validate_url("https://tmrds-postgres:5432/") == "https://tmrds-postgres:5432/"
