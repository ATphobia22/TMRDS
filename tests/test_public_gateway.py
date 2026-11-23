"""Public research-only app must never expose clinical or ingestion write APIs."""
from __future__ import annotations

from fastapi.testclient import TestClient

from api.public_gateway import app, pathway_router
from engines.governed_pathway import PathwaySourceError


def test_public_gateway_has_only_read_only_research_routes_and_static_site():
    # FastAPI can defer router flattening; inspect the registered APIRouter
    # separately and also assert the network-facing URLs resolve.
    paths = {getattr(route, "path", ""): route for route in [*app.routes, *pathway_router.routes]}
    expected = {
        "/health/live", "/health/ready", "/backend-config.json",
        "/api/v1/research/dossier", "/api/v1/research/gwas-associations",
        "/api/v1/research/source-governance",
        "/api/v1/research/evidence-pathway",
        "/api/v1/research/reference-pathway-contract",
    }
    assert expected <= paths.keys(), sorted(paths.keys())
    client = TestClient(app)
    for path in expected:
        response = client.get(path)
        assert response.status_code in {200, 422}, (path, response.status_code)
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


def test_public_dossier_blocks_unreviewed_source_adapters_and_abstract_redistribution(monkeypatch):
    from engines.federated_evidence_search import SourceResult

    called = []

    async def isolated_guard(self, source, coro):
        coro.close()
        called.append(source)
        if source == "europe_pmc":
            return SourceResult(source=source, ok=True, count=1, envelopes=[{
                "stable_id": "europe_pmc:test", "source": "europe_pmc",
                "title": "Nonclinical source reference", "doi": "10.5555/demo",
                "abstract": "Publisher-restricted abstract must not leave this gateway",
                "record_hash": "a" * 64, "retrieved_at": "2026-11-23T05:50:00+00:00",
            }])
        return SourceResult(source=source, ok=True, count=0, envelopes=[])

    monkeypatch.setattr(
        "api.public_gateway.FederatedEvidenceSearch._guard", isolated_guard
    )
    client = TestClient(app)
    response = client.get("/api/v1/research/dossier", params={"query": "cystic fibrosis"})
    assert response.status_code == 200
    data = response.json()
    assert set(called) == {
        "opentargets", "chembl", "europe_pmc", "pubmed",
        "clinicaltrials_gov", "openfda", "dailymed", "gwas_catalog_v2",
    }
    assert data["source_status"]["monarch"]["governance"] == "license_review_required_not_queried"
    assert data["items"][0]["source_records"][0].get("abstract") is None
    assert data["clinical_promotion_allowed"] is False
