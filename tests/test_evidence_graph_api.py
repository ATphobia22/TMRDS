from fastapi.testclient import TestClient

from api.main import app


def test_evidence_source_registry_endpoint_is_research_advisory():
    client = TestClient(app)
    response = client.get("/api/v1/evidence/sources")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "research-advisory"
    assert body["human_authority_final"] is True
    assert body["not_samd"] is True
    assert isinstance(body["data"], list)


def test_unknown_evidence_source_returns_404():
    client = TestClient(app)
    response = client.get("/api/v1/evidence/sources/not-registered")
    assert response.status_code == 404
