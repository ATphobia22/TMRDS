"""Synthetic adapter, integrity and coverage checks; no remote scientific claims."""
from __future__ import annotations

import asyncio
from copy import deepcopy

import httpx
import pytest
from fastapi.testclient import TestClient

from engines.federated_evidence_search import FederatedEvidenceSearch, _make_envelope
from engines.publication_integrity import europe_pmc_integrity
from engines.research_dossier import build_research_dossier
from engines.research_source_catalog import research_source_catalog
from engines.uniprot_pipeline import UniProtPipeline


@pytest.mark.parametrize("types,retracted,notice", [
    (["Journal Article"], False, False),
    (["Retracted Publication"], True, False),
    (["Retraction of Publication"], False, True),
    (["Expression of Concern"], False, False),
    ([], False, False),
])
def test_integrity_is_metadata_not_clearance(types, retracted, notice):
    record = {"pubTypeList": {"pubType": types}}
    before = deepcopy(record)
    result = europe_pmc_integrity(record)
    assert (result["retraction_status"] == "retraction_reported") is retracted
    assert result["is_retraction_notice"] is notice
    assert result["assessment_scope"] == "source_metadata_only"
    assert "not proof" in result["limitation"]
    assert record == before


def test_retraction_survives_federation_hash_and_dossier():
    raw = {"pubTypeList": {"pubType": ["Retracted Publication"]},
           "commentCorrectionList": {"commentCorrection": [{"type": "Retraction in", "id": "synthetic-notice"}]}}
    rec = {"doi": "10.1234/synthetic", "publication_integrity": europe_pmc_integrity(raw)}
    env = _make_envelope("europe_pmc", "Europe PMC", rec, "citation")
    changed = _make_envelope("europe_pmc", "Europe PMC", {**rec, "publication_integrity": europe_pmc_integrity({})}, "citation")
    assert env["record_hash"] != changed["record_hash"]
    assert env["warnings"]
    dossier = build_research_dossier({"query": "synthetic research", "searched_at": env["retrieved_at"],
                                      "envelopes": [env], "source_status": {}})
    group = dossier["items"][0]
    assert group["retraction_status"] == "retraction_reported"
    assert group["source_records"][0]["publication_integrity"]["correction_links"][0]["id"] == "synthetic-notice"
    assert group["review_status"] == "pending"


@pytest.mark.asyncio
async def test_europepmc_normalization_retains_integrity(monkeypatch):
    f = FederatedEvidenceSearch()
    async def fake(query, n):
        return {"resultList": {"result": [{"id": "synthetic", "source": "MED", "pubTypeList": {"pubType": ["Retracted Publication"]}}]}}
    monkeypatch.setattr(f.europepmc, "search", fake)
    result = await f._search_europepmc("synthetic", 1)
    assert result[0]["publication_integrity"]["retraction_status"] == "retraction_reported"


@pytest.mark.asyncio
async def test_guard_bounds_slow_sources_and_sanitizes_failures():
    f = FederatedEvidenceSearch(timeout=0.001)
    async def slow():
        await asyncio.sleep(1)
    result = await f._guard("synthetic", slow())
    assert result.ok is False and result.envelopes == []
    async def fails():
        raise ValueError("private-query-must-not-appear")
    result = await f._guard("synthetic", fails())
    assert "private-query" not in result.warning
    assert "ValueError" in result.warning


@pytest.mark.asyncio
async def test_uniprot_bounded_transport_and_release(monkeypatch):
    original = httpx.AsyncClient
    def respond(request):
        assert request.url.host == "rest.uniprot.org"
        assert request.url.params["size"] == "25"
        assert "version" in request.url.params["fields"]
        return httpx.Response(200, headers={"x-uniprot-release": "synthetic-release", "link": '<next>; rel="next"'},
                              json={"results": [{"primaryAccession": "P04637", "entryType": "UniProtKB reviewed (Swiss-Prot)",
                                   "organism": {"taxonId": 9606}, "entryAudit": {"entryVersion": 1}}]})
    def client(**kwargs):
        assert kwargs["follow_redirects"] is False
        return original(transport=httpx.MockTransport(respond), **kwargs)
    monkeypatch.setattr("engines.uniprot_pipeline.httpx.AsyncClient", client)
    result = await UniProtPipeline().search("synthetic", 200)
    assert result["source_release"] == "synthetic-release"
    assert result["has_more"] is True
    assert UniProtPipeline.normalize(result["results"][0])["protein_metadata"]["clinical_effectiveness"] == "not_assessed"


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [{}, [], {"results": [None]}, {"results": [{"primaryAccession": "../../bad"}]}])
async def test_uniprot_rejects_malformed_payload(monkeypatch, payload):
    original = httpx.AsyncClient
    monkeypatch.setattr("engines.uniprot_pipeline.httpx.AsyncClient", lambda **kw: original(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=payload)), **kw))
    with pytest.raises(ValueError):
        await UniProtPipeline().search("synthetic")


@pytest.mark.asyncio
async def test_uniprot_failure_is_not_invented_evidence(monkeypatch):
    f = FederatedEvidenceSearch()
    async def fails(*args):
        raise httpx.HTTPStatusError("rate limited", request=httpx.Request("GET", UniProtPipeline.BASE_URL), response=httpx.Response(429))
    monkeypatch.setattr(f.uniprot, "search", fails)
    result = await f._guard("uniprot", f._search_uniprot("synthetic", 1))
    assert not result.ok and not result.envelopes and result.count == 0


@pytest.mark.asyncio
async def test_fanout_includes_uniprot_with_source_metadata(monkeypatch):
    f = FederatedEvidenceSearch()
    async def empty(*args):
        return []
    for name in dir(f):
        if name.startswith("_search_"):
            monkeypatch.setattr(f, name, empty)
    async def proteins(*args):
        return [_make_envelope("uniprot", "UniProtKB", {"title": "synthetic protein"}, "protein_annotation")]
    monkeypatch.setattr(f, "_search_uniprot", proteins)
    result = await f.search_all("synthetic", 1, preserve_source_records=True)
    assert result["source_status"]["uniprot"]["ok"] is True
    assert result["envelopes"][0]["evidence_class"] == "protein_annotation"


def test_catalog_does_not_claim_all_sources_connected():
    catalog = research_source_catalog()
    assert catalog["catalog_is_not_live_health"]
    ids = [s["source_id"] for s in catalog["sources"]]
    assert len(ids) == len(set(ids)) == 10
    assert all(not s["background_or_compute_execution_enabled"] for s in catalog["sources"])
    assert all(s["documentation_url"].startswith("https://") for s in catalog["sources"])
    assert any(s["implementation_status"] == "access_review_required" for s in catalog["sources"])


def test_catalog_api_and_governance_registration():
    from api.main import app
    from engines.evidence_source_registry import default_source_registry
    with TestClient(app) as client:
        response = client.get("/api/v1/research/source-catalog")
        assert response.status_code == 200
        assert response.json()["clinical_promotion_allowed"] is False
    assert default_source_registry().get("uniprot").identifier_namespaces == ["uniprot"]
    from engines.source_registry import build_default_registry
    assert build_default_registry()["uniprot"].adapter_owner == "engines/uniprot_pipeline.py"


def test_correction_link_alone_can_report_retraction():
    result = europe_pmc_integrity({"commentCorrectionList": {"commentCorrection": [{"type": "Retraction in"}]}})
    assert result["retraction_status"] == "retraction_reported"
