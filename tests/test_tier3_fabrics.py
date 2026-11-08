"""Tests for the Tier 3 data-fabric pipelines (mocked HTTP) + live smoke (gated).

gnomAD (GraphQL, gnomad_r4) and GTEx Portal v2 (single-tissue eQTL) were
verified live 2026-11-07 before coding; mocked payloads below reuse the
verified live response shapes (TP53 P72R rs1042522 for gnomAD; TP53
single-tissue eQTL rows for GTEx). Live smoke tests are gated by
TMRDS_LIVE_SMOKE=1 and fail honestly if a source is unreachable — they
assert on honest reporting (ok or warning), never on invented records.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

import httpx

from engines.federated_evidence_search import FederatedEvidenceSearch
from engines.gnomad_pipeline import GnomADLookupError, GnomADPipeline
from engines.gtex_pipeline import GTExLookupError, GTExPipeline
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


# ---- gnomAD ----

# Shape verified live 2026-11-07 (TP53 P72R, rs1042522; populations trimmed).
GNOMAD_VARIANT = {
    "variant_id": "17-7676154-G-C",
    "chrom": "17",
    "pos": 7676154,
    "ref": "G",
    "alt": "C",
    "rsids": ["rs1042522"],
    "exome": {
        "ac": 1046941,
        "an": 1461558,
        "af": 0.7163184765845761,
        "populations": [
            {"id": "nfe", "ac": 831482, "an": 1111994},
            {"id": "afr", "ac": 12577, "an": 33470},
        ],
    },
    "genome": {
        "ac": 95285,
        "an": 152024,
        "af": 0.6267760353628374,
        "populations": [{"id": "nfe", "ac": 70000, "an": 110000}],
    },
}
GNOMAD_PAYLOAD = {"data": {"variant": GNOMAD_VARIANT}}


def test_gnomad_normalize():
    rec = GnomADPipeline.normalize(GNOMAD_VARIANT, "17-7676154-G-C")
    assert rec["variant_id"] == "17-7676154-G-C"
    assert rec["title"] == "17-7676154-G-C (rs1042522)"
    assert rec["rsids"] == ["rs1042522"]
    assert rec["exome"]["af"] == pytest.approx(0.7163184765845761)
    assert rec["genome"]["af"] == pytest.approx(0.6267760353628374)
    assert rec["allele_frequency"] is None  # Do not collapse exome and genome into one number.
    nfe = [p for p in rec["populations"] if p["id"] == "nfe" and p["callset"] == "exome"][0]
    assert nfe["af"] == pytest.approx(831482 / 1111994)
    assert rec["dataset"] == "gnomad_r4"
    assert rec["assembly"] == "GRCh38"
    assert "gnomad.broadinstitute.org/variant/17-7676154-G-C" in rec["source_url"]


def test_gnomad_fetch_mocked(monkeypatch):
    holder = _fake_client(monkeypatch, GNOMAD_PAYLOAD)
    rec = asyncio.run(GnomADPipeline(min_interval=0).fetch_variant("17-7676154-G-C"))
    assert rec["variant_id"] == "17-7676154-G-C"
    assert holder["client"].seen["url"] == GnomADPipeline.BASE
    assert holder["client"].seen["json"]["variables"]["variantId"] == "17-7676154-G-C"


def test_gnomad_search_variant_id_mocked(monkeypatch):
    _fake_client(monkeypatch, GNOMAD_PAYLOAD)
    out = asyncio.run(GnomADPipeline(min_interval=0).search("17-7676154-G-C"))
    assert len(out) == 1
    assert out[0]["exome"]["ac"] == 1046941


def test_gnomad_search_non_variant_returns_empty(monkeypatch):
    # Gene symbols and rsIDs are not variant IDs; an empty result is honest.
    _fake_client(monkeypatch, GNOMAD_PAYLOAD)
    assert asyncio.run(GnomADPipeline(min_interval=0).search("TP53")) == []
    assert asyncio.run(GnomADPipeline(min_interval=0).search("rs1042522")) == []


def test_gnomad_search_empty_query_rejected():
    with pytest.raises(ValueError):
        asyncio.run(GnomADPipeline(min_interval=0).search("  "))


def test_gnomad_invalid_variant_ids_rejected():
    pipe = GnomADPipeline(min_interval=0)
    for bad in ("17-7676154", "chr17-7676154-G-C", "17-7676154-G", "17:7676154-G-C", "99-1-A-G"):
        with pytest.raises(ValueError):
            asyncio.run(pipe.fetch_variant(bad))


def test_gnomad_ac_exceeds_an_raises(monkeypatch):
    bad = {"data": {"variant": {**GNOMAD_VARIANT, "exome": {"ac": 10, "an": 5, "af": 2.0, "populations": []}}}}
    _fake_client(monkeypatch, bad)
    with pytest.raises(GnomADLookupError):
        asyncio.run(GnomADPipeline(min_interval=0).fetch_variant("17-7676154-G-C"))


def test_gnomad_graphql_errors_raise(monkeypatch):
    _fake_client(monkeypatch, {"errors": [{"message": "Variant not found"}], "data": {"variant": None}})
    with pytest.raises(GnomADLookupError):
        asyncio.run(GnomADPipeline(min_interval=0).fetch_variant("1-55516888-G-A"))


def test_gnomad_mismatched_variant_raises(monkeypatch):
    wrong = {"data": {"variant": {**GNOMAD_VARIANT, "variant_id": "17-7676154-G-T"}}}
    _fake_client(monkeypatch, wrong)
    with pytest.raises(GnomADLookupError):
        asyncio.run(GnomADPipeline(min_interval=0).fetch_variant("17-7676154-G-C"))


# ---- GTEx ----

# Rows verified live 2026-11-07 (TP53 single-tissue eQTLs, gtex_v10).
GTEX_EQTL_ROWS = [
    {
        "snpId": "rs112895815", "pos": 7037114, "snpIdUpper": "RS112895815",
        "variantId": "chr17_7037114_A_G_b38", "geneSymbol": "TP53",
        "pValue": 5.98694240872263e-6, "geneSymbolUpper": "TP53",
        "datasetId": "gtex_v10", "tissueSiteDetailId": "Esophagus_Muscularis",
        "ontologyId": "UBERON:0004648", "chromosome": "chr17",
        "gencodeId": "ENSG00000141510.18", "nes": -0.20134204626083374,
    },
    {
        "snpId": "rs113422253", "pos": 7056936, "snpIdUpper": "RS113422253",
        "variantId": "chr17_7056936_G_A_b38", "geneSymbol": "TP53",
        "pValue": 2.2176481601808264e-5, "geneSymbolUpper": "TP53",
        "datasetId": "gtex_v10", "tissueSiteDetailId": "Esophagus_Muscularis",
        "ontologyId": "UBERON:0004648", "chromosome": "chr17",
        "gencodeId": "ENSG00000141510.18", "nes": -0.13934287428855896,
    },
]
GTEX_EQTL_PAYLOAD = {
    "data": GTEX_EQTL_ROWS,
    "paging_info": {"numberOfPages": 26, "page": 0, "maxItemsPerPage": 2, "totalNumberOfItems": 51},
}
GTEX_GENESEARCH_PAYLOAD = {
    "data": [
        {"geneSymbol": "TP53BP2", "gencodeId": "ENSG00000143514.16"},
        {"geneSymbol": "TP53", "gencodeId": "ENSG00000141510.18"},
    ],
    "paging_info": {"numberOfPages": 1, "page": 0, "maxItemsPerPage": 10, "totalNumberOfItems": 2},
}


def test_gtex_normalize():
    rec = GTExPipeline.normalize(GTEX_EQTL_ROWS[0], "gtex_v10")
    assert rec["snp_id"] == "rs112895815"
    assert rec["title"] == "TP53 eQTL rs112895815 (Esophagus_Muscularis)"
    assert rec["p_value"] == pytest.approx(5.98694240872263e-6)
    assert rec["nes"] == pytest.approx(-0.20134204626083374)
    assert rec["tissue"] == "Esophagus_Muscularis"
    assert rec["gencode_id"] == "ENSG00000141510.18"
    assert rec["dataset_id"] == "gtex_v10"
    assert "gtexportal.org/home/gene/ENSG00000141510.18" in rec["source_url"]


def test_gtex_resolve_gene_symbol_exact_match(monkeypatch):
    holder = _fake_client(monkeypatch, GTEX_GENESEARCH_PAYLOAD)
    gene_id = asyncio.run(GTExPipeline(min_interval=0).resolve_gene_symbol("TP53"))
    assert gene_id == "ENSG00000141510.18"
    assert "reference/geneSearch" in holder["client"].seen["url"]
    # The dataset-matched GENCODE version must be requested (v39 for v10),
    # otherwise the returned ID does not match the eQTL data.
    assert holder["client"].seen["params"]["gencodeVersion"] == "v39"


def test_gtex_resolve_gene_symbol_no_exact_match(monkeypatch):
    _fake_client(monkeypatch, {"data": [{"geneSymbol": "TP53BP2", "gencodeId": "ENSG00000143514.16"}]})
    assert asyncio.run(GTExPipeline(min_interval=0).resolve_gene_symbol("TP53")) is None


def test_gtex_search_symbol_mocked(monkeypatch):
    calls = []

    class SeqClient(FakeClient):
        async def get(self, url, params=None):
            calls.append(url)
            payload = GTEX_GENESEARCH_PAYLOAD if "geneSearch" in url else GTEX_EQTL_PAYLOAD
            return FakeResponse(payload)

    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: SeqClient(FakeResponse({})))
    out = asyncio.run(GTExPipeline(min_interval=0).search("TP53", 2))
    assert len(out) == 2
    assert out[0]["snp_id"] == "rs112895815"
    assert out[0]["has_more"] is True  # 26 pages reported; only the first page is fetched.
    assert any("geneSearch" in u for u in calls)
    assert any("singleTissueEqtl" in u for u in calls)


def test_gtex_search_versioned_id_direct(monkeypatch):
    calls = []

    class SeqClient(FakeClient):
        async def get(self, url, params=None):
            calls.append(url)
            return FakeResponse(GTEX_EQTL_PAYLOAD)

    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: SeqClient(FakeResponse({})))
    out = asyncio.run(GTExPipeline(min_interval=0).search("ENSG00000141510.18", 2))
    assert len(out) == 2
    assert not any("geneSearch" in u for u in calls)


def test_gtex_search_unresolved_symbol_returns_empty(monkeypatch):
    _fake_client(monkeypatch, {"data": []})
    assert asyncio.run(GTExPipeline(min_interval=0).search("NOTAGENE")) == []


def test_gtex_search_empty_query_rejected():
    with pytest.raises(ValueError):
        asyncio.run(GTExPipeline(min_interval=0).search("  "))


def test_gtex_invalid_gencode_ids_rejected():
    pipe = GTExPipeline(min_interval=0)
    for bad in ("ENSG00000141510", "ENSG0000014151.18", "TP53", "ENSG00000141510."):
        with pytest.raises(ValueError):
            asyncio.run(pipe.fetch_eqtls(bad))


def test_gtex_invalid_dataset_rejected():
    with pytest.raises(ValueError):
        asyncio.run(GTExPipeline(min_interval=0).fetch_eqtls("ENSG00000141510.18", dataset_id="gtex_v9"))


def test_gtex_mismatched_dataset_raises(monkeypatch):
    wrong = {
        "data": [{**GTEX_EQTL_ROWS[0], "datasetId": "gtex_v8"}],
        "paging_info": {"numberOfPages": 1, "page": 0, "maxItemsPerPage": 1, "totalNumberOfItems": 1},
    }
    _fake_client(monkeypatch, wrong)
    with pytest.raises(GTExLookupError):
        asyncio.run(GTExPipeline(min_interval=0).fetch_eqtls("ENSG00000141510.18"))


def test_gtex_empty_result_is_honest(monkeypatch):
    # A gene/tissue with no eQTL (e.g. TP53 in Whole_Blood) returns zero records.
    _fake_client(monkeypatch, {"data": [], "paging_info": {"numberOfPages": 0, "page": 0, "maxItemsPerPage": 10, "totalNumberOfItems": 0}})
    out = asyncio.run(GTExPipeline(min_interval=0).fetch_eqtls("ENSG00000141510.18"))
    assert out["records"] == []
    assert out["is_partial"] is False


# ---- Registry ----

def test_tier3_registry_entries():
    reg = build_default_registry()
    for key in ("gnomad", "gtex"):
        assert key in reg, f"missing registry entry: {key}"
        entry = reg[key]
        assert entry.api_endpoint.startswith("https://"), key
        assert entry.adapter_owner.startswith("engines/"), key
        # The adapter_owner must point at a real file, not a stale path.
        assert Path(entry.adapter_owner).exists(), f"adapter file missing: {entry.adapter_owner}"
    assert reg["gnomad"].adapter_owner == "engines/gnomad_pipeline.py"
    assert reg["gtex"].adapter_owner == "engines/gtex_pipeline.py"
    assert reg["gnomad"].upstream_version_pinned == "gnomad_r4"
    assert reg["gtex"].upstream_version_pinned == "GTEx v10"


# ---- Orchestrator wiring ----

def test_orchestrator_has_tier3_adapters():
    search = FederatedEvidenceSearch()
    for name in ("gnomad", "gtex"):
        assert getattr(search, name) is not None, f"missing pipeline attr: {name}"
        assert callable(getattr(search, f"_search_{name}")), f"missing adapter: _search_{name}"


def test_orchestrator_tier3_failure_isolation():
    async def runner():
        search = FederatedEvidenceSearch()

        async def boom(query, n=10):
            raise ConnectionError("simulated outage")

        async def empty(*args):
            return []

        for name in dir(search):
            if name.startswith("_search_") and name != "_search_gnomad":
                setattr(search, name, empty)
        search.gnomad.search = boom
        result = await search.search_all("17-7676154-G-C", per_source=2)
        status = result["source_status"]["gnomad"]
        assert status["ok"] is False
        assert "unavailable" in status["warning"]
        assert "gtex" in result["source_status"]
        assert result["source_status"]["gtex"]["ok"] is True

    asyncio.run(runner())


def test_orchestrator_gnomad_envelope_warnings():
    async def runner():
        search = FederatedEvidenceSearch()

        async def empty(*args):
            return []

        async def gnomad_records(query, n=10):
            return [GnomADPipeline.normalize(GNOMAD_VARIANT, "17-7676154-G-C")]

        for name in dir(search):
            if name.startswith("_search_") and name != "_search_gnomad":
                setattr(search, name, empty)
        search.gnomad.search = gnomad_records
        result = await search.search_all("17-7676154-G-C", per_source=2)
        envs = [e for e in result["envelopes"] if e["source"] == "gnomad"]
        assert len(envs) == 1
        assert envs[0]["variant_id"] == "17-7676154-G-C"
        assert envs[0]["exome_af"] == pytest.approx(0.7163184765845761)
        assert any("not clinical evidence" in w for w in envs[0]["warnings"])

    asyncio.run(runner())


# ---- Live smoke (gated) ----

@needs_live
def test_live_tier3_smoke():
    async def runner():
        search = FederatedEvidenceSearch()
        variant = await search.search_all("17-7676154-G-C", per_source=2)
        gnomad = variant["source_status"]["gnomad"]
        assert gnomad["ok"] or gnomad["warning"], "dishonest gnomad status"
        if gnomad["ok"]:
            assert gnomad["count"] == 1
            env = [e for e in variant["envelopes"] if e["source"] == "gnomad"][0]
            assert env["exome_af"] is not None and 0.0 <= env["exome_af"] <= 1.0
        gene = await search.search_all("TP53", per_source=2)
        gtex = gene["source_status"]["gtex"]
        assert gtex["ok"] or gtex["warning"], "dishonest gtex status"
        if gtex["ok"]:
            assert gtex["count"] >= 1

    asyncio.run(runner())
