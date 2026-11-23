"""GWAS Catalog v2: genuine association metadata, isolated source failures, no cure claims."""
from __future__ import annotations

import httpx
import pytest

from engines.federated_evidence_search import FederatedEvidenceSearch
from engines.gwas_catalog_v2_pipeline import GWASCatalogV2Error, GWASCatalogV2Pipeline

ASSOCIATION = {
    "association_id": 228393513,
    "accession_id": "GCST90476372",
    "p_value": 1.0e-24,
    "pvalue_mantissa": 1,
    "pvalue_exponent": -24,
    "beta": "0.1112 unit decrease",
    "risk_frequency": "0.5002",
    "pubmed_id": "39024449",
    "efo_traits": [{"efo_id": "MONDO_0004979", "efo_trait": "asthma"}],
    "reported_trait": ["Biological Sibling: Asthma"],
    "mapped_genes": [],
    "snp_effect_allele": ["chr17:37921742-C"],
    "_links": {"self": {"href": "https://www.ebi.ac.uk/gwas/rest/api/v2/associations/228393513"}},
}

@pytest.mark.asyncio
async def test_official_gwas_v2_bounded_metadata_fetch(monkeypatch):
    original = httpx.AsyncClient
    def respond(request):
        assert request.method == "GET"
        assert request.url.scheme == "https"
        assert request.url.host == "www.ebi.ac.uk"
        assert request.url.path == "/gwas/rest/api/v2/associations"
        assert request.url.params["efo_trait"] == "asthma"
        assert request.url.params["size"] == "25"
        assert request.url.params["page"] == "0"
        assert request.url.params["show_child_traits"] == "false"
        return httpx.Response(200, json={"_embedded": {"associations": [ASSOCIATION]},
                "_links": {"next": {"href": "https://www.ebi.ac.uk/gwas/rest/api/v2/associations?page=1"}},
                "page": {"size": 25, "number": 0, "totalElements": 3236}})
    def client(**kwargs):
        assert kwargs["follow_redirects"] is False
        return original(transport=httpx.MockTransport(respond), **kwargs)
    monkeypatch.setattr("engines.gwas_catalog_v2_pipeline.httpx.AsyncClient", client)
    result = await GWASCatalogV2Pipeline().search_trait("asthma", 99)
    assert len(result) == 1
    item = result[0]
    assert item["source_url"] == "https://www.ebi.ac.uk/gwas/rest/api/v2/associations/228393513"
    assert item["association_id"] == 228393513
    assert item["study_accession"] == "GCST90476372"
    assert item["pmid"] == "39024449"
    assert item["p_value"] == 1e-24
    assert item["efo_traits"][0]["efo_id"] == "MONDO_0004979"
    assert item["reported_traits"][0] == "Biological Sibling: Asthma"
    assert item["has_more"] is True
    assert item["effect_description"] == "0.1112 unit decrease"
    assert item["raw"]["snp_effect_allele"] == ["chr17:37921742-C"]
    assert item["clinical_interpretation"] == "not_assessed"

@pytest.mark.asyncio
async def test_gwas_rejects_malformed_payload_and_does_not_fabricate_data(monkeypatch):
    original = httpx.AsyncClient
    for payload in ({}, {"_embedded": {"associations": [None]}},
                    {"_embedded": {"associations": [{**ASSOCIATION, "association_id": "../../bad"}]}},
                    {"_embedded": {"associations": [{**ASSOCIATION, "p_value": -3}]}},
                    {"_embedded": {"associations": [{**ASSOCIATION, "p_value": "NaN"}]}},
                    {"_embedded": {"associations": "not-a-list"}}):
        monkeypatch.setattr("engines.gwas_catalog_v2_pipeline.httpx.AsyncClient",
            lambda **kwargs: original(transport=httpx.MockTransport(
                lambda _: httpx.Response(200, json=payload)), **kwargs))
        with pytest.raises(GWASCatalogV2Error):
            await GWASCatalogV2Pipeline().search_trait("asthma", 2)

@pytest.mark.asyncio
async def test_gwas_upstream_429_is_isolated_and_not_a_negative_result(monkeypatch):
    original = httpx.AsyncClient
    monkeypatch.setattr("engines.gwas_catalog_v2_pipeline.httpx.AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(
            lambda _: httpx.Response(429, json={"error": "rate limited"})), **kwargs))
    f = FederatedEvidenceSearch()
    result = await f._guard("gwas_catalog_v2", f._search_gwas_catalog_v2("asthma", 2))
    assert not result.ok
    assert result.count == 0
    assert result.envelopes == []
    assert "unavailable" in result.warning

@pytest.mark.asyncio
async def test_gwas_is_wired_into_federation_without_clinical_promotion(monkeypatch):
    f = FederatedEvidenceSearch()
    async def empty(*_args): return []
    for name in dir(f):
        if name.startswith("_search_"):
            monkeypatch.setattr(f, name, empty)
    async def associations(*_args):
        from engines.federated_evidence_search import _make_envelope
        env = _make_envelope("gwas_catalog_v2", "GWAS Catalog v2",
                GWASCatalogV2Pipeline.normalize(ASSOCIATION, "asthma", has_more=False),
                "genetic_association")
        env["warnings"].append("Association is not causal or clinical evidence.")
        return [env]
    monkeypatch.setattr(f, "_search_gwas_catalog_v2", associations)
    result = await f.search_all("asthma", 2, preserve_source_records=True)
    assert result["source_status"]["gwas_catalog_v2"]["ok"] is True
    assert result["source_status"]["gwas_catalog_v2"]["count"] == 1
    assert result["envelopes"][0]["evidence_class"] == "genetic_association"
    assert result["envelopes"][0]["is_authoritative"] is False
    assert result["envelopes"][0]["record_hash_scope"] == "normalized_source_record"
    assert result["envelopes"][0]["warnings"]

def test_gwas_rejects_unsafe_or_empty_queries():
    for bad in ("", " ", "a" * 121, 123, "a\nb"):
        with pytest.raises(ValueError):
            GWASCatalogV2Pipeline._validate_trait(bad)

def test_multiple_gwas_associations_from_one_publication_remain_distinct():
    """The study PMID must never collapse distinct variant-trait associations."""
    from engines.federated_evidence_search import _make_envelope
    a = GWASCatalogV2Pipeline.normalize(ASSOCIATION, "asthma", has_more=False)
    b = GWASCatalogV2Pipeline.normalize(
        {**ASSOCIATION, "association_id": 228393509}, "asthma", has_more=False)
    entries = [_make_envelope("gwas_catalog_v2", "GWAS Catalog v2", item, "genetic_association")
               for item in (a, b)]
    assert entries[0]["pmid"] == entries[1]["pmid"] == "39024449"
    assert entries[0]["stable_id"] != entries[1]["stable_id"]
    assert len(FederatedEvidenceSearch._dedupe(entries)) == 2
