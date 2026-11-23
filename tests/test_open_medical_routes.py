"""Research-only public medical ecosystem, PubMed and AFDB source contracts."""
from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from api.open_medical_routes import load_afdb_metadata, medical_project_catalog
from api.public_gateway import app
from engines.federated_evidence_search import SourceResult

ROOT = Path(__file__).resolve().parents[1]


def test_catalog_is_shared_with_static_site_and_does_not_infer_installation():
    catalog = medical_project_catalog()
    disk = json.loads((ROOT / "public/medical-projects.json").read_text(encoding="utf-8"))
    assert len(catalog["projects"]) >= 40
    assert catalog["projects"] == disk["projects"]
    assert catalog["all_platforms_installed"] is False
    assert catalog["license_approvals_completed"] is False
    assert catalog["external_clinical_connections_enabled"] is False
    identifiers = [r["id"] for r in catalog["projects"]]
    assert len(set(identifiers)) == len(identifiers)
    assert {"alphafold3", "alphafold_db", "pubmed", "openemr", "openmrs", "orthanc",
            "ohif", "monai", "medplum", "openelis", "hapi_fhir"} <= set(identifiers)
    for project in catalog["projects"]:
        assert project["source_url"].startswith("https://")
        assert "integration_state" in project
        assert project["verification"] in {
            "official_api_checked", "official_docs_checked",
            "official_license_checked", "cataloged_review_pending"}
        assert project["integration_state"] != "clinical_live"


def test_catalog_category_filter_and_invalid_input():
    client = TestClient(app)
    response = client.get("/api/v1/research/medical-projects", params={"category": "imaging"})
    assert response.status_code == 200
    assert response.json()["count"] >= 4
    assert all(x["category"] == "imaging" for x in response.json()["projects"])
    assert client.get("/api/v1/research/medical-projects", params={"category": "not-registered"}).status_code == 422
    assert client.get("/api/v1/research/medical-projects").json()["count"] >= 40
    assert client.post("/api/v1/research/medical-projects").status_code == 405


def test_alphafold_3_never_claims_actual_inference():
    data = TestClient(app).get("/api/v1/research/alphafold3-status").json()
    assert data["status"] == "not_configured"
    assert data["inference_submitted"] is False
    assert data["model_parameters_bundled"] is False
    assert data["public_run_enabled"] is False
    assert data["clinical_promotion_allowed"] is False
    assert "WEIGHTS_TERMS_OF_USE" in data["terms_url"]


def test_bounded_alphafold_db_original_source_metadata_and_identifiers():
    requests = []
    def respond(req: httpx.Request) -> httpx.Response:
        requests.append(req.url)
        return httpx.Response(200, json=[{
            "uniprotAccession": "P13569", "gene": "CFTR", "latestVersion": 4,
            "globalMetricValue": 84.1,
            "cifUrl": "https://alphafold.ebi.ac.uk/files/AF-P13569-F1-model_v4.cif",
            "pdbUrl": "https://alphafold.ebi.ac.uk/files/AF-P13569-F1-model_v4.pdb",
            "paeDocUrl": "http://internal.invalid/patient-file",
        }])
    out = asyncio.run(load_afdb_metadata("P13569", transport=httpx.MockTransport(respond)))
    assert out["status"] == "predicted_structure_metadata"
    assert out["source_url"] == "https://alphafold.ebi.ac.uk/api/prediction/P13569"
    assert out["not_alphafold_3"] is True
    assert out["records"][0]["gene"] == "CFTR"
    assert out["records"][0]["mean_plddt"] == 84.1
    assert out["records"][0]["pae_url"] is None
    assert out["record_sha256_scope"] == "normalized_display_metadata_only"
    assert len(out["record_sha256"]) == 64
    assert len(requests) == 1


def test_afdb_refuses_redirects_wrong_accession_oversized_records_and_failure():
    for status, headers, body in [
        (302, {"location": "http://127.0.0.1/internal"}, b""),
        (200, {}, b'{"uniprotAccession":"Q99999","gene":"wrong"}'),
        (200, {}, b"x" * (1024 * 1024 + 1)),
        (503, {}, b"unavailable"),
    ]:
        def respond(_request, s=status, h=headers, b=body):
            return httpx.Response(s, headers=h, content=b)
        result = asyncio.run(load_afdb_metadata("P13569", transport=httpx.MockTransport(respond)))
        assert result["status"] == "source_unavailable"
        assert result["records"] == []
    for untrusted in ("../../etc", "P13569?token=x", "bad", "", "P13569/"):
        try:
            asyncio.run(load_afdb_metadata(untrusted))
        except ValueError:
            pass
        else:
            raise AssertionError("invalid UniProt path must not trigger an upstream call")


def test_afdb_404_is_distinct_from_source_unavailable():
    result = asyncio.run(load_afdb_metadata(
        "P13569", transport=httpx.MockTransport(lambda _: httpx.Response(404))))
    assert result["status"] == "not_found"
    assert result["records"] == []


def test_pubmed_citations_use_bounded_existing_original_source_pipeline(monkeypatch):
    called = []
    async def bounded_guard(self, source, coro):
        coro.close()
        called.append(source)
        return SourceResult(source=source, ok=True, count=2, envelopes=[
            {"pmid": "38718835", "title": "AlphaFold 3 research", "published": "2024",
             "journal": "Nature", "abstract": "licensed article body must be withheld"},
            {"pmid": "INVALID", "title": "unidentified record"}])
    monkeypatch.setattr(
        "api.open_medical_routes.FederatedEvidenceSearch._guard", bounded_guard)
    client = TestClient(app)
    result = client.get("/api/v1/research/pubmed-citations",
                        params={"query": "AlphaFold 3", "limit": 5})
    assert result.status_code == 200
    data = result.json()
    assert called == ["pubmed"]
    assert data["status"] == "responding"
    assert len(data["records"]) == 1
    assert data["records"][0]["pmid"] == "38718835"
    assert "abstract" not in data["records"][0]
    assert data["abstract_redistribution_enabled"] is False
    assert data["clinical_promotion_allowed"] is False
    assert client.post("/api/v1/research/pubmed-citations", params={"query": "cancer"}).status_code == 405


def test_pubmed_source_errors_cannot_fake_a_negative_result(monkeypatch):
    async def source_down(self, source, coro):
        coro.close()
        return SourceResult(source=source, ok=False, count=0, warning="upstream unreachable")
    monkeypatch.setattr(
        "api.open_medical_routes.FederatedEvidenceSearch._guard", source_down)
    result = TestClient(app).get("/api/v1/research/pubmed-citations", params={"query": "CFTR"})
    assert result.status_code == 200
    data = result.json()
    assert data["status"] == "source_unavailable"
    assert data["records"] == []
    assert "not a negative" not in json.dumps(data).lower() or data["status"] != "not_found"


def test_public_gateway_medical_routes_have_no_patient_data_write_operations():
    paths = [p for p in app.routes if getattr(p, "path", "").startswith("/api/v1/research/")]
    for route in paths:
        assert getattr(route, "methods", set()) <= {"GET", "HEAD"}
    assert not any("patient/" in getattr(p, "path", "") or "/ingest" in getattr(p, "path", "") for p in paths)
