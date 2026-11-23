"""Public research-only app must never expose clinical or ingestion write APIs."""
from __future__ import annotations

from fastapi.testclient import TestClient

from api.public_gateway import app
from engines.governed_pathway import PathwaySourceError


def test_public_gateway_has_only_read_only_research_routes_and_static_site():
    paths = {getattr(route, "path", ""): route for route in app.routes}
    expected = {
        "/health/live", "/health/ready", "/backend-config.json",
        "/api/v1/research/dossier", "/api/v1/research/gwas-associations",
        "/api/v1/research/source-governance",
        "/api/v1/research/evidence-pathway",
        "/api/v1/research/reference-pathway-contract",
    }
    assert expected <= paths.keys()
    assert not any("/api/v1/medical" in path or "/api/v1/evidence/ingest" in path for path in paths)
    assert not any("/api/v1/ops" in path for path in paths)
    for path in expected:
        route = paths[path]
        assert "POST" not in getattr(route, "methods", []), path


def test_public_gateway_static_csp_and_same_origin_mode():
    client = TestClient(app)
    assert client.get("/health/live").json()["status"] == "alive"
    assert client.get("/health/ready").json()["external_sources_verified"] is False
    assert client.get("/backend-config.json").json()["api_mode"] == "same-origin"
    html = client.get("/")
    assert html.status_code == 200
    assert "rubiksCube" in html.text
    assert "connect-src 'self'" in html.text
    assert client.get("/site.js").status_code == 200


def test_public_gateway_discloses_missing_source_without_fabricating_links(monkeypatch):
    async def unavailable(self, disease_query, *, limit=10):
        raise PathwaySourceError("test fixture network failure")
    monkeypatch.setattr("api.governed_pathway_routes.PathwaySourceClient.search", unavailable)
    client = TestClient(app)
    result = client.get("/api/v1/research/evidence-pathway", params={"disease": "cystic fibrosis"})
    assert result.status_code == 200
    payload = result.json()
    assert payload["status"] == "source_unavailable"
    assert payload["links"] == []
    assert payload["governance"]["clinical_promotion_allowed"] is False


def test_source_inventory_discloses_unreviewed_licenses():
    client = TestClient(app)
    r = client.get("/api/v1/research/source-governance")
    assert r.status_code == 200
    data = r.json()
    assert data["health_scope"] == "not_probed"
    assert data["source_policies"]["chembl"]["policy"]["bulk_redistribution_allowed"] is False
    assert data["source_policies"]["monarch"]["policy"]["review_state"] == "unregistered"
    assert data["clinical_promotion_allowed"] is False
