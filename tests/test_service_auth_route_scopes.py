"""Route-level authorization matrix for TMRDS service scopes.

Uses generated ephemeral RSA keys and synthetic FHIR fixtures only. No external
identity provider, patient data, or network service is contacted.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from api import security_dependencies
from api.main import app


_SYNTHETIC_META = {
    "tag": [{"system": "urn:tmrds:data-classification", "code": "synthetic"}],
}


def _observation() -> dict[str, object]:
    return {
        "resourceType": "Observation",
        "id": "synthetic-authz-route-test",
        "meta": _SYNTHETIC_META,
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": "4548-4"}]},
        "effectiveDateTime": "2026-01-01T10:00:00Z",
        "valueQuantity": {
            "value": 5.1,
            "system": "http://unitsofmeasure.org",
            "code": "%",
            "unit": "%",
        },
    }


@pytest.fixture
def service_auth_client(monkeypatch: pytest.MonkeyPatch):
    """Configure the real FastAPI dependencies with an ephemeral local JWKS."""
    monkeypatch.setenv("TMRDS_ENV", "development")
    monkeypatch.setenv("TMRDS_SERVICE_AUTH_REQUIRED", "true")
    monkeypatch.setenv("TMRDS_SYNTHETIC_WORKBENCH_ENABLED", "true")
    monkeypatch.setenv("TMRDS_SERVICE_ISSUER", "https://issuer.test.invalid")
    monkeypatch.setenv("TMRDS_SERVICE_AUDIENCE", "tmrds-route-test")

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key()))
    public_jwk.update({"kid": "route-test-key", "use": "sig", "alg": "RS256"})
    monkeypatch.setenv("TMRDS_SERVICE_JWKS_JSON", json.dumps({"keys": [public_jwk]}))
    security_dependencies._validator.cache_clear()

    now = datetime.now(timezone.utc)

    def token(scope: str) -> str:
        claims = {
            "iss": "https://issuer.test.invalid",
            "aud": "tmrds-route-test",
            "sub": "synthetic-route-test-service",
            "iat": int(now.timestamp()),
            "nbf": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=5)).timestamp()),
            "scope": scope,
        }
        return jwt.encode(
            claims,
            private_key,
            algorithm="RS256",
            headers={"kid": "route-test-key"},
        )

    client = TestClient(app)
    yield client, token
    security_dependencies._validator.cache_clear()


def test_read_scope_token_can_call_synthetic_fhir_validation(service_auth_client) -> None:
    client, token = service_auth_client
    response = client.post(
        "/api/v1/interoperability/fhir/validate",
        json={
            "resource": {
                "resourceType": "Patient",
                "id": "synthetic-route-auth-test",
                "meta": _SYNTHETIC_META,
            }
        },
        headers={"Authorization": f"Bearer {token('evidence.read')}"},
    )

    assert response.status_code == 200
    assert response.json()["data_classification"] == "synthetic-attested"
    assert response.json()["external_transmission"] is False


def test_write_only_token_cannot_call_read_scoped_fhir_validation(service_auth_client) -> None:
    client, token = service_auth_client
    response = client.post(
        "/api/v1/interoperability/fhir/validate",
        json={
            "resource": {
                "resourceType": "Patient",
                "id": "synthetic-route-auth-test",
                "meta": _SYNTHETIC_META,
            }
        },
        headers={"Authorization": f"Bearer {token('evidence.write')}"},
    )

    assert response.status_code == 401


def test_write_scope_token_can_call_synthetic_workbench_mutation(service_auth_client) -> None:
    client, token = service_auth_client
    response = client.post(
        "/api/v1/medical/synthetic/labs/trends",
        json={"resources": [_observation()]},
        headers={"Authorization": f"Bearer {token('evidence.write')}"},
    )

    assert response.status_code == 200
    assert response.json()["patient_data_accepted"] is False
    assert response.json()["external_data_transmitted"] is False


def test_read_only_token_cannot_call_write_scoped_synthetic_workbench(service_auth_client) -> None:
    client, token = service_auth_client
    response = client.post(
        "/api/v1/medical/synthetic/labs/trends",
        json={"resources": [_observation()]},
        headers={"Authorization": f"Bearer {token('evidence.read')}"},
    )

    assert response.status_code == 401
