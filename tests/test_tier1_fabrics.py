"""Tests for the Tier 1 data-fabric pipelines (mocked HTTP) + live smoke (gated).

Unit tests use canned payloads (no network). Live smoke tests are gated by
TMRDS_LIVE_SMOKE=1 and fail honestly if a source is unreachable — they assert
on honest reporting (ok or warning), never on invented records.
"""
from __future__ import annotations

import asyncio
import os

import pytest

import httpx

from engines.chembl_pipeline import ChEMBLPipeline
from engines.crossref_pipeline import CrossrefPipeline
from engines.dailymed_pipeline import DailyMedPipeline
from engines.federated_evidence_search import FederatedEvidenceSearch
from engines.pubchem_pipeline import PubChemPipeline
from engines.rxnorm_pipeline import RxNormPipeline
from engines.semantic_scholar_pipeline import SemanticScholarPipeline
from engines.source_registry import build_default_registry

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


def _fake_client(monkeypatch, payload, status=200):
    holder = {}

    def factory(*args, **kwargs):
        client = FakeClient(FakeResponse(payload, status))
        holder["client"] = client
        return client

    monkeypatch.setattr(httpx, "AsyncClient", factory)
    return holder


# ---- Semantic Scholar ----

S2_PAPER = {
    "title": "TP53 and cancer",
    "abstract": "An abstract.",
    "authors": [{"name": "Jane Doe"}, {"name": "John Smith"}],
    "year": 2023,
    "doi": "10.1/example",
    "externalIds": {"PubMed": "12345", "ArXiv": "2301.00001"},
    "url": "https://www.semanticscholar.org/paper/abc",
    "openAccessPdf": {"url": "https://example.org/paper.pdf"},
    "citationCount": 42,
    "venue": "Nature",
}


def test_s2_normalize():
    rec = SemanticScholarPipeline.normalize(S2_PAPER)
    assert rec["title"] == "TP53 and cancer"
    assert rec["authors"] == ["Jane Doe", "John Smith"]
    assert rec["doi"] == "10.1/example"
    assert rec["pmid"] == "12345"
    assert rec["open_access_url"] == "https://example.org/paper.pdf"
    assert rec["cited_by_count"] == 42
    assert rec["is_preprint"] is False


def test_s2_search_mocked(monkeypatch):
    holder = _fake_client(monkeypatch, {"data": [S2_PAPER]})
    out = asyncio.run(SemanticScholarPipeline(min_interval=0).search("tp53", 5))
    assert len(out) == 1
    assert out[0]["title"] == "TP53 and cancer"
    assert "semanticscholar.org" in holder["client"].seen["url"]


def test_s2_empty_query_rejected():
    with pytest.raises(ValueError):
        asyncio.run(SemanticScholarPipeline(min_interval=0).search("  "))


def test_s2_http_error_propagates(monkeypatch):
    _fake_client(monkeypatch, {}, status=500)
    with pytest.raises(Exception):
        asyncio.run(SemanticScholarPipeline(min_interval=0).search("tp53"))


# ---- PubChem ----

PUBCHEM_PROP = {
    "CID": 2244,
    "IUPACName": "2-acetyloxybenzoic acid",
    "MolecularFormula": "C9H8O4",
    "MolecularWeight": "180.16",
    "CanonicalSMILES": "CC(=O)OC1=CC=CC=C1C(=O)O",
    "InChIKey": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
    "XLogP": 1.2,
}


def test_pubchem_normalize():
    rec = PubChemPipeline.normalize(PUBCHEM_PROP)
    assert rec["cid"] == 2244
    assert rec["title"] == "2-acetyloxybenzoic acid"
    assert rec["source_url"] == "https://pubchem.ncbi.nlm.nih.gov/compound/2244"
    assert rec["properties"]["MolecularFormula"] == "C9H8O4"


def test_pubchem_search_mocked(monkeypatch):
    holder = _fake_client(monkeypatch, {"PropertyTable": {"Properties": [PUBCHEM_PROP]}})
    out = asyncio.run(PubChemPipeline(min_interval=0).search_by_name("aspirin"))
    assert len(out) == 1
    assert out[0]["cid"] == 2244
    assert "pubchem.ncbi.nlm.nih.gov" in holder["client"].seen["url"]


def test_pubchem_empty_name_rejected():
    with pytest.raises(ValueError):
        asyncio.run(PubChemPipeline(min_interval=0).search_by_name(""))


# ---- ChEMBL ----

CHEMBL_MOL = {
    "molecule_chembl_id": "CHEMBL25",
    "pref_name": "ASPIRIN",
    "molecule_type": "Small molecule",
    "max_phase": 4,
    "molecule_structures": {"canonical_smiles": "CC(=O)Oc1ccccc1C(=O)O"},
}


def test_chembl_normalize():
    rec = ChEMBLPipeline.normalize(CHEMBL_MOL)
    assert rec["chembl_id"] == "CHEMBL25"
    assert rec["title"] == "ASPIRIN"
    assert rec["source_url"] == "https://www.ebi.ac.uk/chembl/compound_report_card/CHEMBL25/"
    assert rec["license"] == "CC BY-SA 3.0"


def test_chembl_search_mocked(monkeypatch):
    holder = _fake_client(monkeypatch, {"molecules": [CHEMBL_MOL]})
    out = asyncio.run(ChEMBLPipeline(min_interval=0).search_molecule("aspirin"))
    assert len(out) == 1
    assert out[0]["chembl_id"] == "CHEMBL25"
    assert holder["client"].seen["url"].endswith("/molecule/search.json")


def test_chembl_bad_shape_raises(monkeypatch):
    _fake_client(monkeypatch, {"molecules": "not-a-list"})
    with pytest.raises(ValueError):
        asyncio.run(ChEMBLPipeline(min_interval=0).search_molecule("aspirin"))


# ---- DailyMed ----

DAILYMED_REC = {
    "setid": "123e4567-e89b-12d3-a456-426614174000",
    "title": "ASPIRIN TABLET [ACME]",
    "published_date": "Oct 16, 2026",
    "spl_version": 3,
}


def test_dailymed_normalize():
    rec = DailyMedPipeline.normalize(DAILYMED_REC)
    assert rec["spl_set_id"] == "123e4567-e89b-12d3-a456-426614174000"
    assert "drugInfo.cfm?setid=" in rec["source_url"]
    assert rec["published"] == "Oct 16, 2026"


def test_dailymed_search_mocked(monkeypatch):
    holder = _fake_client(monkeypatch, {"data": [DAILYMED_REC]})
    out = asyncio.run(DailyMedPipeline().search_by_drug_name("aspirin"))
    assert len(out) == 1
    assert out[0]["title"] == "ASPIRIN TABLET [ACME]"
    assert holder["client"].seen["params"]["drug_name"] == "aspirin"


# ---- RxNorm ----

RXNORM_CAND = {"rxcui": "1191", "name": "Aspirin", "score": "10.37", "source": "USP"}


def test_rxnorm_normalize():
    rec = RxNormPipeline.normalize(RXNORM_CAND)
    assert rec["rxcui"] == "1191"
    assert rec["title"] == "Aspirin"
    assert "searchTerm=1191" in rec["source_url"]


def test_rxnorm_search_mocked(monkeypatch):
    holder = _fake_client(
        monkeypatch, {"approximateGroup": {"candidate": [RXNORM_CAND]}}
    )
    out = asyncio.run(RxNormPipeline(min_interval=0).approximate_term("aspirin"))
    assert len(out) == 1
    assert out[0]["rxcui"] == "1191"
    assert "approximateTerm.json" in holder["client"].seen["url"]


# ---- Crossref ----

CROSSREF_WORK = {
    "DOI": "10.1/example",
    "title": ["A study"],
    "author": [{"given": "Jane", "family": "Doe"}],
    "published": {"date-parts": [[2023, 5, 1]]},
    "URL": "https://doi.org/10.1/example",
    "is-referenced-by-count": 7,
    "container-title": ["J Test"],
}


def test_crossref_normalize():
    rec = CrossrefPipeline.normalize(CROSSREF_WORK)
    assert rec["doi"] == "10.1/example"
    assert rec["authors"] == ["Jane Doe"]
    assert rec["published"] == "2023-5-1"
    assert rec["cited_by_count"] == 7
    assert rec["journal"] == "J Test"


def test_crossref_search_mocked(monkeypatch):
    holder = _fake_client(monkeypatch, {"message": {"items": [CROSSREF_WORK]}})
    out = asyncio.run(CrossrefPipeline(min_interval=0).search("tp53"))
    assert len(out) == 1
    assert out[0]["doi"] == "10.1/example"
    assert holder["client"].seen["params"]["mailto"] == "tmrds@example.org"


# ---- Registry ----

def test_registry_contains_tier1_fabrics_without_api_keys():
    reg = build_default_registry()
    for key in ("semantic_scholar", "pubchem", "chembl", "dailymed", "rxnorm", "crossref"):
        assert key in reg, f"missing registry entry: {key}"
    for key in ("semantic_scholar", "pubchem", "chembl", "dailymed", "rxnorm"):
        assert reg[key].requires_api_key is False


# ---- Orchestrator wiring ----

class _Stub:
    def __init__(self, payload):
        self._payload = payload

    async def search(self, *a, **k):
        return self._payload

    async def drug_labels(self, *a, **k):
        return self._payload

    # pipeline-specific entry points used by the Tier 1 adapters
    async def search_by_name(self, *a, **k):
        return self._payload

    async def search_molecule(self, *a, **k):
        return self._payload

    async def search_by_drug_name(self, *a, **k):
        return self._payload

    async def approximate_term(self, *a, **k):
        return self._payload


def _stubbed_searcher():
    f = FederatedEvidenceSearch()
    f.europepmc = _Stub({"resultList": {"result": []}})
    f.pubmed = _Stub({"status": "OK", "pmids": []})
    f.trials = _Stub({"studies": []})
    f.openfda = _Stub({"results": []})
    f.openalex = _Stub({"results": []})
    f.arxiv = _Stub([])
    f.semantic_scholar = _Stub([SemanticScholarPipeline.normalize(S2_PAPER)])
    f.crossref = _Stub([CrossrefPipeline.normalize(CROSSREF_WORK)])
    f.pubchem = _Stub([PubChemPipeline.normalize(PUBCHEM_PROP)])
    f.chembl = _Stub([ChEMBLPipeline.normalize(CHEMBL_MOL)])
    f.dailymed = _Stub([DailyMedPipeline.normalize(DAILYMED_REC)])
    f.rxnorm = _Stub([RxNormPipeline.normalize(RXNORM_CAND)])
    # pubmed bridge uses .search/.summaries sync methods; stub them too
    f.pubmed.search = lambda q, n: {"status": "OK", "pmids": []}
    f.pubmed.summaries = lambda pmids: {"articles": []}
    return f


def test_orchestrator_wires_tier1_sources_with_isolation():
    f = _stubbed_searcher()
    res = asyncio.run(f.search_all("aspirin", per_source=2))
    for key in ("semantic_scholar", "crossref", "pubchem", "chembl", "dailymed", "rxnorm"):
        assert key in res["source_status"], f"missing source_status: {key}"
        assert res["source_status"][key]["ok"] is True
        assert res["source_status"][key]["coverage"]
    for env in res["envelopes"]:
        assert env["is_mock"] is False
        assert env["record_hash"]
    by_source = {}
    for env in res["envelopes"]:
        by_source.setdefault(env["source"], []).append(env)
    assert by_source["pubchem"][0]["cid"] == 2244
    assert by_source["chembl"][0]["chembl_id"] == "CHEMBL25"
    assert by_source["dailymed"][0]["spl_set_id"].startswith("123e4567")
    assert by_source["rxnorm"][0]["rxcui"] == "1191"


def test_orchestrator_isolates_tier1_failure():
    f = _stubbed_searcher()

    async def boom(*a, **k):
        raise RuntimeError("upstream down")

    f.pubchem.search_by_name = boom
    res = asyncio.run(f.search_all("aspirin", per_source=2))
    assert res["source_status"]["pubchem"]["ok"] is False
    assert "unavailable" in res["source_status"]["pubchem"]["warning"]
    # other sources unaffected
    assert res["source_status"]["rxnorm"]["ok"] is True
    assert res["total_envelopes"] > 0


@needs_live
def test_live_tier1_sources_report_honestly():
    f = FederatedEvidenceSearch()
    res = f.search_all_sync("aspirin", per_source=2)
    for key in ("semantic_scholar", "crossref", "pubchem", "chembl", "dailymed", "rxnorm"):
        assert key in res["source_status"]
        st = res["source_status"][key]
        assert st["coverage"]
        # Either live records or an honest warning — never a crash, never mocks.
        assert st["ok"] or st["warning"]
        assert res["governance"]["no_mock_records"] is True
