from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_ai_governance_health_is_research_advisory():
    response = client.get("/api/v1/governance/ai/status")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "research-advisory"
    assert body["human_authority_final"] is True
    assert body["clinical_promotion_allowed"] is False


def test_ai_governance_policy_rejects_missing_provenance():
    response = client.post(
        "/api/v1/governance/ai/validate",
        json={
            "generation_id": "gen-1",
            "model_id": "model-1",
            "model_version": "1.0.0",
            "retrieved_at": "2026-09-07T00:00:00Z",
            "evidence_assertion_ids": [],
            "human_authority_final": True,
            "research_advisory": True,
            "governance_status": "review_required",
        },
    )
    assert response.status_code == 422
