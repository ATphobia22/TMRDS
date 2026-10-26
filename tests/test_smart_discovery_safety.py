"""Synthetic interoperability assertions: unimplemented SMART discovery stays unavailable."""
from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


def test_smart_discovery_does_not_claim_nonexistent_oauth_endpoints() -> None:
    response = TestClient(app).get("/.well-known/smart-configuration")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "SMART_NOT_CONFIGURED"
    assert "authorization_endpoint" not in response.text
    assert "client_secret" not in response.text


def test_interoperability_status_distinguishes_helper_from_live_smart_launch() -> None:
    response = TestClient(app).get("/api/v1/interoperability/status")
    assert response.status_code == 200
    body = response.json()
    assert body["smart_app_launch"] == "NOT_CONFIGURED"
    assert body["pkce_helper"] == "S256_ONLY"
    assert body["live_phi_exchange"] is False
