"""Contract regression tests for FastAPI request parsing across dependency upgrades.

These use only synthetic public metadata and never ingest patient records.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


def test_fhir_validation_requires_json_body() -> None:
    client = TestClient(app)
    response = client.post("/api/v1/interoperability/fhir/validate")
    assert response.status_code == 422


def test_fhir_validation_rejects_explicit_null_body() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/interoperability/fhir/validate",
        content="null",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 422


def test_fhir_validation_rejects_null_required_resource() -> None:
    client = TestClient(app)
    response = client.post("/api/v1/interoperability/fhir/validate", json={"resource": None})
    assert response.status_code == 422


def test_fhir_validation_accepts_synthetic_resource() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/interoperability/fhir/validate",
        json={"resource": {"resourceType": "Patient", "id": "synthetic-test-only"}},
    )
    assert response.status_code == 200
    assert response.json()["fhir_version"] == "R4"


def test_fhir_validation_rejects_wrong_profile_type() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/interoperability/fhir/validate",
        json={"resource": {"resourceType": "Patient"}, "required_profile": 123},
    )
    assert response.status_code == 422


def test_governance_status_is_research_only() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/governance/ai/status")
    assert response.status_code == 200
    assert response.json()["clinical_promotion_allowed"] is False
    assert response.json()["human_authority_final"] is True


def test_openapi_includes_fhir_json_request_schema() -> None:
    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200
    operation = response.json()["paths"]["/api/v1/interoperability/fhir/validate"]["post"]
    assert "application/json" in operation["requestBody"]["content"]
