"""Tests for the Tier 2 data-fabric pipelines (mocked HTTP) + live smoke (gated).

Unit tests use canned payloads (no network). Live smoke tests are gated by
TMRDS_LIVE_SMOKE=1 and fail honestly if a source is unreachable — they assert
on honest reporting (ok or warning), never on invented records.
"""
from __future__ import annotations

import asyncio
import os

import pytest

import httpx

from engines.biorxiv_pipeline import BiorxivPipeline
from engines.clinvar_pipeline import ClinVarPipeline
from engines.ensembl_pipeline import EnsemblPipeline
from engines.federated_evidence_search import FederatedEvidenceSearch
from engines.mesh_pipeline import MeshPipeline
from engines.monarch_pipeline import MonarchPipeline
from engines.ncats_pipeline import NcatsPipeline
from engines.opentargets_pipeline import OpenTargetsPipeline
from engines.reactome_pipeline import ReactomePipeline
from engines.source_registry import build_default_registry
from engines.string_pipeline import StringPipeline

LIVE = os.getenv("TMRDS_LIVE_SMOKE") == "1"
needs_live = pytest.mark.skipif(not LIVE, reason="Live smoke test opt-in only (TMRDS_LIVE_SMOKE=1)")


class FakeResponse:
    def __init__(self, payload=None, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class FakeClient:
    """Stands in for httpx.AsyncClient in pipeline search() calls."""

    def __init__(self, response):
        self._response = response
        self.seen = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, params=None):
        self.seen["url"] = url
        self.seen["params"] = params
        return self._response

    async def post(self, url, json=None):
        self.seen["url"] = url
        self.seen["json"] = json
        return self._response


def _fake_client(monkeypatch, payload, status=200):
    holder = {}

    def factory(*args, **kwargs):
        client = FakeClient(FakeResponse(payload, status))
        holder["client"] = client
        return client

    monkeypatch.setattr(httpx, "AsyncClient", factory)
    return holder


# ---- Open Targets ----

OT_SEARCH = {"data": {"search": {"hits": [{"id": "ENSG00000141510", "name": "TP53", "entity": "target"}]}}}
OT_DISEASES = {
    "data": {
        "target": {
            "approvedSymbol": "TP53",
            "id": "ENSG00000141510",
            "associatedDiseases": {
                "rows": [{"score": 0.87, "disease": {"id": "MONDO_0018875", "name": "Li-Fraumeni syndrome"}}]
            },
        }
    }
}


def test_ot_normalize():
    rec = OpenTargetsPipeline.normalize("TP53", "ENSG00000141510", "MONDO_0018875", "Li-Fraumeni syndrome", 0.87)
    assert rec["disease_name"] == "Li-Fraumeni syndrome"
    assert rec["association_score"] == 0.87
    assert rec["target_id"] == "ENSG00000141510"
    assert "platform.opentargets.org" in rec["source_url"]


def test_ot_associated_diseases_mocked(monkeypatch):
    calls = []

    class SeqClient(FakeClient):
        async def post(self, url, json=None):
            calls.append(json["query"][:20])
            payload = OT_SEARCH if "searchTarget" in json["query"] else OT_DISEASES
            return FakeResponse(payload)

    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: SeqClient(FakeResponse({})))
    out = asyncio.run(OpenTargetsPipeline(min_interval=0).associated_diseases("TP53", 5))
    assert len(out) == 1
    assert out[0]["disease_id"] == "MONDO_0018875"
    assert len(calls) == 2


def test_ot_empty_query_rejected():
    with pytest.raises(ValueError):
        asyncio.run(OpenTargetsPipeline(min_interval=0).associated_diseases("  "))


def test_ot_graphql_error_raises(monkeypatch):
    _fake_client(monkeypatch, {"errors": [{"message": "bad"}]})
    with pytest.raises(ValueError):
        asyncio.run(OpenTargetsPipeline(min_interval=0).associated_diseases("TP53"))


# ---- STRING ----

STRING_IDS = [{"stringId": "9606.ENSP00000269305", "preferredName": "TP53", "ncbiTaxonId": 9606}]
STRING_NET = [{
    "stringId_A": "9606.ENSP00000212015", "stringId_B": "9606.ENSP00000269305",
    "preferredName_A": "SIRT1", "preferredName_B": "TP53", "score": 0.999,
}]


def test_string_normalize():
    rec = StringPipeline.normalize(STRING_NET[0])
    assert rec["protein_a"] == "SIRT1"
    assert rec["protein_b"] == "TP53"
    assert rec["association_score"] == 0.999


def test_string_interactions_mocked(monkeypatch):
    calls = []

    class SeqClient(FakeClient):
        async def get(self, url, params=None):
            calls.append(url)
            payload = STRING_IDS if url.endswith("get_string_ids") else STRING_NET
            return FakeResponse(payload)

    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: SeqClient(FakeResponse({})))
    out = asyncio.run(StringPipeline(min_interval=0).interactions("TP53", 5))
    assert len(out) == 1
    assert out[0]["protein_a"] == "SIRT1"
    assert any("get_string_ids" in u for u in calls) and any("network" in u for u in calls)


def test_string_empty_name_rejected():
    with pytest.raises(ValueError):
        asyncio.run(StringPipeline(min_interval=0).interactions("  "))


# ---- Reactome ----

REACTOME_SEARCH = {
    "results": [{
        "entries": [{
            "stId": "R-HSA-109581", "name": "Apoptosis", "exactType": "Pathway",
            "summation": "A distinct form of cell death.", "species": ["Homo sapiens"],
        }]
    }]
}


def test_reactome_normalize():
    rec = ReactomePipeline.normalize(REACTOME_SEARCH["results"][0]["entries"][0])
    assert rec["title"] == "Apoptosis"
    assert rec["stable_id"] == "R-HSA-109581"
    assert "reactome.org" in rec["source_url"]
    assert rec["abstract"] == "A distinct form of cell death."


def test_reactome_search_mocked(monkeypatch):
    holder = _fake_client(monkeypatch, REACTOME_SEARCH)
    out = asyncio.run(ReactomePipeline(min_interval=0).search_pathways("apoptosis", page_size=5))
    assert len(out) == 1
    assert out[0]["stable_id"] == "R-HSA-109581"
    assert "reactome.org" in holder["client"].seen["url"]


def test_reactome_empty_query_rejected():
    with pytest.raises(ValueError):
        asyncio.run(ReactomePipeline(min_interval=0).search_pathways("  "))


# ---- ClinVar ----

CLINVAR_SEARCH = {"header": {}, "esearchresult": {"idlist": ["5019950"]}}
CLINVAR_SUMMARY = {
    "result": {
        "uids": ["5019950"],
        "5019950": {
            "uid": "5019950",
            "title": "NM_000465.4(BARD1):c.1527del (p.Ile509fs)",
            "germline_classification": {
                "description": "Likely pathogenic",
                "last_evaluated": "Jan 01, 2020",
                "review_status": "criteria provided, single submitter",
                "trait_set": [{"trait_name": "Familial cancer of breast"}],
            },
        },
    }
}


def test_clinvar_normalize_surfaces_review_status():
    rec = ClinVarPipeline.normalize(CLINVAR_SUMMARY["result"]["5019950"])
    assert rec["classification"] == "Likely pathogenic"
    # The report's explicit requirement: stars must surface with the label.
    assert rec["review_status"] == "criteria provided, single submitter"
    assert "Familial cancer of breast" in rec["conditions"]
    assert rec["variation_id"] == "5019950"


def test_clinvar_search_mocked(monkeypatch):
    calls = []

    class SeqClient(FakeClient):
        async def get(self, url, params=None):
            calls.append(url)
            payload = CLINVAR_SEARCH if "esearch" in url else CLINVAR_SUMMARY
            return FakeResponse(payload)

    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: SeqClient(FakeResponse({})))
    out = asyncio.run(ClinVarPipeline(min_interval=0).search_variants("BARD1", 5))
    assert len(out) == 1
    assert out[0]["review_status"] == "criteria provided, single submitter"
    assert any("esearch" in u for u in calls) and any("esummary" in u for u in calls)


def test_clinvar_empty_term_rejected():
    with pytest.raises(ValueError):
        asyncio.run(ClinVarPipeline(min_interval=0).search_variants("  "))


# ---- Ensembl ----

ENSEMBL_GENE = {
    "id": "ENSG00000139618", "display_name": "BRCA2", "biotype": "protein_coding",
    "assembly_name": "GRCh38", "seq_region_name": "13", "start": 32315086, "end": 32400266,
    "description": "BRCA2 DNA repair associated",
}


def test_ensembl_normalize():
    rec = EnsemblPipeline.normalize(ENSEMBL_GENE)
    assert rec["ensembl_id"] == "ENSG00000139618"
    assert rec["assembly"] == "GRCh38"
    assert rec["location"] == "13:32315086-32400266"
    assert "ensembl.org" in rec["source_url"]


def test_ensembl_lookup_mocked(monkeypatch):
    holder = _fake_client(monkeypatch, ENSEMBL_GENE)
    out = asyncio.run(EnsemblPipeline(min_interval=0).lookup_gene("BRCA2"))
    assert out is not None
    assert out["ensembl_id"] == "ENSG00000139618"
    assert "rest.ensembl.org" in holder["client"].seen["url"]


def test_ensembl_404_returns_none(monkeypatch):
    class NotFoundResponse(FakeResponse):
        def raise_for_status(self):
            request = httpx.Request("GET", "https://rest.ensembl.org/x")
            response = httpx.Response(404, request=request)
            raise httpx.HTTPStatusError("not found", request=request, response=response)

    class NFClient(FakeClient):
        def __init__(self):
            super().__init__(NotFoundResponse())

    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: NFClient())
    out = asyncio.run(EnsemblPipeline(min_interval=0).lookup_gene("NOTAGENE"))
    assert out is None


def test_ensembl_empty_symbol_rejected():
    with pytest.raises(ValueError):
        asyncio.run(EnsemblPipeline(min_interval=0).lookup_gene("  "))


# ---- bioRxiv ----

BIORXIV_PAGE = {
    "collection": [
        {
            "title": "TP53 regulation in cancer cells", "abstract": "We study tp53 pathways.",
            "authors": "Doe, J.; Smith, J.", "date": "2026-10-01", "doi": "10.1101/2026.10.01.123456",
            "version": "1", "license": "cc_by", "category": "cancer biology", "published": "NA",
        },
        {
            "title": "Unrelated plant study", "abstract": "Photosynthesis details.",
            "authors": "Green, A.", "date": "2026-10-01", "doi": "10.1101/2026.10.01.999999",
            "version": "1", "license": "cc_by", "category": "plant biology", "published": "NA",
        },
    ]
}


def test_biorxiv_normalize_marks_unpeerreviewed():
    rec = BiorxivPipeline.normalize(BIORXIV_PAGE["collection"][0])
    assert rec["is_preprint"] is True
    assert "NOT peer-reviewed" in rec["journal"]
    assert rec["version"] == "1"


def test_biorxiv_search_filters_locally(monkeypatch):
    _fake_client(monkeypatch, BIORXIV_PAGE)
    out = asyncio.run(BiorxivPipeline(min_interval=0).search_recent("tp53", days_back=1, max_pages=1))
    assert len(out) == 1
    assert "TP53" in out[0]["title"]
    assert all(r["is_preprint"] for r in out)


def test_biorxiv_invalid_server_rejected():
    with pytest.raises(ValueError):
        asyncio.run(BiorxivPipeline(min_interval=0).search_recent("tp53", server="arxiv"))


# ---- NCATS ----

NODENORM = {
    "MONDO:0008903": {
        "id": {"identifier": "MONDO:0008903", "label": "lung cancer"},
        "equivalent_identifiers": [
            {"identifier": "MONDO:0008903", "label": "lung cancer"},
            {"identifier": "DOID:1324", "label": "lung cancer"},
        ],
        "type": ["biolink:Disease"],
    }
}
NAMERES = [{"curie": "NCBIGene:7157", "label": "TP53", "synonyms": ["P53"], "types": ["biolink:Gene"]}]


def test_ncats_normalize_node():
    rec = NcatsPipeline.normalize_node("MONDO:0008903", NODENORM["MONDO:0008903"])
    assert rec["curie"] == "MONDO:0008903"
    assert "DOID:1324" in rec["equivalent_identifiers"]
    assert rec["biolink_types"] == ["biolink:Disease"]


def test_ncats_normalize_resolution():
    rec = NcatsPipeline.normalize_resolution(NAMERES[0])
    assert rec["curie"] == "NCBIGene:7157"
    assert "P53" in rec["synonyms"]


def test_ncats_normalize_nodes_mocked(monkeypatch):
    holder = _fake_client(monkeypatch, NODENORM)
    out = asyncio.run(NcatsPipeline(min_interval=0).normalize_nodes(["MONDO:0008903"]))
    assert len(out) == 1
    assert out[0]["curie"] == "MONDO:0008903"
    assert "nodenormalization-sri.renci.org" in holder["client"].seen["url"]


def test_ncats_resolve_name_mocked(monkeypatch):
    holder = _fake_client(monkeypatch, NAMERES)
    out = asyncio.run(NcatsPipeline(min_interval=0).resolve_name("tp53", 3))
    assert len(out) == 1
    assert out[0]["label"] == "TP53"
    assert "name-resolution-sri.renci.org" in holder["client"].seen["url"]


def test_ncats_empty_inputs_rejected():
    with pytest.raises(ValueError):
        asyncio.run(NcatsPipeline(min_interval=0).normalize_nodes([]))
    with pytest.raises(ValueError):
        asyncio.run(NcatsPipeline(min_interval=0).resolve_name("  "))


# ---- Monarch ----

MONARCH_SEARCH = {
    "items": [{
        "id": "MONDO:0018875", "name": "Li-Fraumeni syndrome", "category": "biolink:Disease",
        "description": "Autosomal dominant cancer predisposition.",
        "synonym": ["LFS"], "xref": ["OMIM:151623"],
    }]
}


def test_monarch_normalize():
    rec = MonarchPipeline.normalize(MONARCH_SEARCH["items"][0])
    assert rec["curie"] == "MONDO:0018875"
    assert rec["category"] == "biolink:Disease"
    assert "monarchinitiative.org" in rec["source_url"]


def test_monarch_search_mocked(monkeypatch):
    holder = _fake_client(monkeypatch, MONARCH_SEARCH)
    out = asyncio.run(MonarchPipeline(min_interval=0).search("Li-Fraumeni", page_size=5))
    assert len(out) == 1
    assert out[0]["curie"] == "MONDO:0018875"
    assert "api.monarchinitiative.org/v3/api/search" in holder["client"].seen["url"]


def test_monarch_empty_query_rejected():
    with pytest.raises(ValueError):
        asyncio.run(MonarchPipeline(min_interval=0).search("  "))


# ---- MeSH ----

MESH_LOOKUP = [{"resource": "http://id.nlm.nih.gov/mesh/D003920", "label": "Diabetes Mellitus"}]
MESH_DESCRIPTOR = {"scopeNote": "A heterogeneous group of disorders.", "treeNumber": ["C18.452.394.750"]}


def test_mesh_normalize():
    rec = MeshPipeline.normalize("Diabetes Mellitus", "D003920", MESH_DESCRIPTOR)
    assert rec["descriptor_id"] == "D003920"
    assert rec["tree_numbers"] == ["C18.452.394.750"]
    assert "meshb.nlm.nih.gov" in rec["source_url"]


def test_mesh_lookup_mocked(monkeypatch):
    calls = []

    class SeqClient(FakeClient):
        async def get(self, url, params=None):
            calls.append(url)
            payload = MESH_LOOKUP if url.endswith("lookup/descriptor") else MESH_DESCRIPTOR
            return FakeResponse(payload)

    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: SeqClient(FakeResponse({})))
    out = asyncio.run(MeshPipeline(min_interval=0).lookup("Diabetes Mellitus"))
    assert len(out) == 1
    assert out[0]["descriptor_id"] == "D003920"
    assert any("lookup/descriptor" in u for u in calls)


def test_mesh_empty_label_rejected():
    with pytest.raises(ValueError):
        asyncio.run(MeshPipeline(min_interval=0).lookup("  "))


# ---- Registry ----

def test_tier2_registry_entries():
    reg = build_default_registry()
    for key in ("opentargets", "string", "reactome", "clinvar", "ensembl", "biorxiv", "ncats", "monarch", "mesh"):
        assert key in reg, f"missing registry entry: {key}"
        entry = reg[key]
        assert entry.adapter_owner.startswith("engines/"), key
        assert entry.api_endpoint.startswith("https://"), key


# ---- Orchestrator wiring ----

def test_orchestrator_has_tier2_adapters():
    search = FederatedEvidenceSearch()
    for name in ("opentargets", "string", "reactome", "clinvar", "ensembl",
                 "biorxiv", "ncats", "monarch", "mesh"):
        assert getattr(search, name) is not None, f"missing pipeline attr: {name}"
        assert callable(getattr(search, f"_search_{name}")), f"missing adapter: _search_{name}"


def test_orchestrator_failure_isolation():
    async def runner():
        search = FederatedEvidenceSearch()

        async def boom(query, n=10):
            raise ConnectionError("simulated outage")

        search.opentargets.associated_diseases = boom
        result = await search.search_all("TP53", per_source=2)
        status = result["source_status"]["opentargets"]
        assert status["ok"] is False
        assert "unavailable" in status["warning"]
        # Other sources unaffected in structure.
        assert "ensembl" in result["source_status"]

    asyncio.run(runner())


# ---- Live smoke (gated) ----

@needs_live
def test_live_tier2_smoke():
    async def runner():
        search = FederatedEvidenceSearch()
        result = await search.search_all("TP53", per_source=2)
        for key in ("opentargets", "string", "reactome", "clinvar", "ensembl", "ncats", "monarch", "mesh"):
            assert key in result["source_status"], f"missing status: {key}"
            st = result["source_status"][key]
            assert st["ok"] or st["warning"], f"dishonest status for {key}"
        # bioRxiv host was unreachable from the build network on 2026-10-23;
        # it must report honestly either way.
        assert "biorxiv" in result["source_status"]

    asyncio.run(runner())
