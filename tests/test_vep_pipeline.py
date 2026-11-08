"""Tests for Ensembl VEP annotation (mocked HTTP) + live smoke (gated).

VEP POST /vep/human/hgvs and GET /vep/human/region were verified live
2026-11-08 before coding (ENST00000269305:c.215C>G, TP53 P72R: missense,
SIFT tolerated, PolyPhen benign, 39 transcript consequences; region
17:7675218: missense, 39 transcript consequences). Mocked payloads below
reuse the verified live response shapes, trimmed. Live smoke tests are
gated by TMRDS_LIVE_SMOKE=1 and fail honestly if a source is unreachable.
"""
from __future__ import annotations

import os

import httpx
import pytest

from engines.ensembl_pipeline import EnsemblLookupError, EnsemblPipeline
from engines.federated_evidence_search import COVERAGE, FederatedEvidenceSearch
from engines.source_registry import build_default_registry

LIVE = os.getenv("TMRDS_LIVE_SMOKE") == "1"
needs_live = pytest.mark.skipif(not LIVE, reason="Live smoke test opt-in only (TMRDS_LIVE_SMOKE=1)")


# ---- verified live payload shapes (trimmed from the 2026-11-08 responses) ----

def _vep_post_payload() -> list[dict]:
    return [{
        "allele_string": "C/G",
        "assembly_name": "GRCh38",
        "colocated_variants": [
            {"allele_string": "HGMD_MUTATION", "clinvar_somatic_classification": None,
             "end": 7676154, "id": "CM961374", "phenotype_or_disease": 1,
             "seq_region_name": "17", "start": 7676154, "strand": -1},
            {"allele_string": "C/G", "clin_sig": ["benign", "likely_benign"],
             "clin_sig_allele": "G", "clin_sig_ref_allele": "C",
             "end": 7676154, "id": "rs1042522", "phenotype_or_disease": 1,
             "pubmed": [12345678], "seq_region_name": "17", "start": 7676154,
             "strand": -1, "var_synonyms": {"ClinVar": ["RCV000123456"]}},
        ],
        "end": 7676154,
        "id": "ENST00000269305:c.215C>G",
        "input": "ENST00000269305:c.215C>G",
        "most_severe_consequence": "missense_variant",
        "seq_region_name": "17",
        "start": 7676154,
        "strand": -1,
        "transcript_consequences": [
            {"amino_acids": "P/R", "biotype": "protein_coding", "cds_end": 215,
             "cds_start": 215, "codons": "Ccc/Gcc", "consequence_terms": ["missense_variant"],
             "gene_id": "ENSG00000141510", "gene_symbol": "TP53",
             "gene_symbol_source": "HGNC", "hgnc_id": "HGNC:11998",
             "impact": "MODERATE", "polyphen_prediction": "benign",
             "polyphen_score": 0.047, "protein_end": 72, "protein_start": 72,
             "sift_prediction": "tolerated", "sift_score": 0.14, "strand": -1,
             "transcript_id": "ENST00000269305", "variant_allele": "G"},
            {"amino_acids": None, "biotype": "protein_coding", "cds_end": None,
             "cds_start": None, "codons": None, "consequence_terms": ["intron_variant"],
             "gene_id": "ENSG00000141510", "gene_symbol": "TP53",
             "gene_symbol_source": "HGNC", "hgnc_id": "HGNC:11998",
             "impact": "MODIFIER", "polyphen_prediction": None,
             "polyphen_score": None, "protein_end": None, "protein_start": None,
             "sift_prediction": None, "sift_score": None, "strand": -1,
             "transcript_id": "ENST00000269305", "variant_allele": "G"},
        ],
    }]


def _vep_region_payload() -> list[dict]:
    payload = _vep_post_payload()
    payload[0]["input"] = "17:7675218-7675218:1/G"
    payload[0]["id"] = "17:7675218-7675218:1/G"
    return payload


def _gene_payload() -> dict:
    return {
        "id": "ENSG00000141510", "display_name": "TP53",
        "description": "tumor protein p53 [Source:HGNC Symbol;Acc:HGNC:11998]",
        "biotype": "protein_coding", "assembly_name": "GRCh38",
        "seq_region_name": "17", "start": 7676154, "end": 7675356,
        "object_type": "Gene", "strand": -1, "version": 11,
    }


class FakeResponse:
    def __init__(self, payload=None, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=httpx.Request("GET", "https://rest.ensembl.org/"),
                response=httpx.Response(self.status_code, request=httpx.Request("GET", "https://rest.ensembl.org/")),
            )

    def json(self):
        return self._payload


class RoutingClient:
    """Fake httpx.AsyncClient routing by URL, recording what was called."""

    def __init__(self):
        self.seen: dict = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, params=None):
        self.seen["get_url"] = url
        self.seen["get_params"] = params
        if "/lookup/symbol/" in url:
            return FakeResponse(_gene_payload())
        if "/vep/human/region/" in url:
            return FakeResponse(_vep_region_payload())
        return FakeResponse(None, status=404)

    async def post(self, url, json=None):
        self.seen["post_url"] = url
        self.seen["post_json"] = json
        if "/vep/human/hgvs" in url:
            return FakeResponse(_vep_post_payload())
        return FakeResponse(None, status=404)


def _fake_client(monkeypatch):
    holder = {}

    def factory(*args, **kwargs):
        client = RoutingClient()
        holder["client"] = client
        return client

    monkeypatch.setattr(httpx, "AsyncClient", factory)
    return holder


# ---- classifiers ----

def test_is_hgvs_notation_accepts_enst_and_genomic() -> None:
    assert EnsemblPipeline.is_hgvs_notation("ENST00000269305:c.215C>G")
    assert EnsemblPipeline.is_hgvs_notation("ENST00000269305.4:c.215C>G")
    assert EnsemblPipeline.is_hgvs_notation("17:g.7676154C>G")
    assert not EnsemblPipeline.is_hgvs_notation("NM_000546.5:c.215C>G")
    assert not EnsemblPipeline.is_hgvs_notation("TP53")
    assert not EnsemblPipeline.is_hgvs_notation("")


def test_is_region_query_parses_and_rejects() -> None:
    assert EnsemblPipeline.is_region_query("17:7675218-7675218:1/G") == ("17", 7675218, 7675218, 1, "G")
    assert EnsemblPipeline.is_region_query("chr17:7675218-7675218:-1/G") == ("17", 7675218, 7675218, -1, "G")
    assert EnsemblPipeline.is_region_query("TP53") is None
    assert EnsemblPipeline.is_region_query("17:7675218-7675218:1/B") is None  # B is not a base
    assert EnsemblPipeline.is_region_query("17:7675218-7675217:1/G") is None  # start > end


# ---- annotate_hgvs ----

@pytest.mark.asyncio
async def test_annotate_hgvs_posts_enst_and_normalizes(monkeypatch) -> None:
    holder = _fake_client(monkeypatch)
    records = await EnsemblPipeline().annotate_hgvs(["ENST00000269305:c.215C>G"])
    assert holder["client"].seen["post_url"].endswith("/vep/human/hgvs")
    assert holder["client"].seen["post_json"] == {"hgvs_notations": ["ENST00000269305:c.215C>G"]}
    assert len(records) == 1
    rec = records[0]
    assert rec["most_severe_consequence"] == "missense_variant"
    assert rec["assembly"] == "GRCh38"
    assert rec["input_notation"] == "ENST00000269305:c.215C>G"
    assert rec["transcript_consequence_count"] == 2
    canonical = rec["transcript_consequences"][0]
    assert canonical["amino_acids"] == "P/R"
    assert canonical["sift_prediction"] == "tolerated"
    assert canonical["polyphen_prediction"] == "benign"
    assert rec["transcript_consequences"][1]["sift_prediction"] is None  # None survives
    assert rec["research_only"] is True
    assert rec["clinician_review_required"] is True
    assert rec["predictions_are_computational"] is True
    assert rec["source_url"] == "https://www.ensembl.org/Homo_sapiens/Variation/Explore?v=rs1042522"
    colocated_ids = [c["id"] for c in rec["colocated_variants"]]
    assert "rs1042522" in colocated_ids and "CM961374" in colocated_ids


@pytest.mark.asyncio
async def test_annotate_hgvs_refuses_refseq_accessions() -> None:
    with pytest.raises(ValueError, match="RefSeq"):
        await EnsemblPipeline().annotate_hgvs(["NM_000546.5:c.215C>G"])


@pytest.mark.asyncio
async def test_annotate_hgvs_rejects_empty_and_bad_shapes() -> None:
    pipe = EnsemblPipeline()
    with pytest.raises(ValueError):
        await pipe.annotate_hgvs([])
    with pytest.raises(ValueError):
        await pipe.annotate_hgvs(["TP53"])
    with pytest.raises(ValueError):
        await pipe.annotate_hgvs(["ENST00000269305:c.215C>G"] * 201)


@pytest.mark.asyncio
async def test_annotate_hgvs_server_error_entry_raises(monkeypatch) -> None:
    class ErrorClient(RoutingClient):
        async def post(self, url, json=None):
            return FakeResponse([{"input": "ENST00000269305:c.215C>G", "error": "Could not get a Transcript object"}])

    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: ErrorClient())
    with pytest.raises(EnsemblLookupError, match="could not annotate"):
        await EnsemblPipeline().annotate_hgvs(["ENST00000269305:c.215C>G"])


# ---- annotate_region ----

@pytest.mark.asyncio
async def test_annotate_region_gets_and_normalizes(monkeypatch) -> None:
    holder = _fake_client(monkeypatch)
    records = await EnsemblPipeline().annotate_region("17", 7675218, 7675218, 1, "G")
    assert "/vep/human/region/17:7675218-7675218:1/G" in holder["client"].seen["get_url"]
    assert records[0]["most_severe_consequence"] == "missense_variant"
    assert records[0]["assembly"] == "GRCh38"


@pytest.mark.asyncio
async def test_annotate_region_rejects_bad_inputs() -> None:
    pipe = EnsemblPipeline()
    with pytest.raises(ValueError):
        await pipe.annotate_region("17", 7675218, 7675218, 0, "G")
    with pytest.raises(ValueError):
        await pipe.annotate_region("17", 7675219, 7675218, 1, "G")
    with pytest.raises(ValueError):
        await pipe.annotate_region("17", 7675218, 7675218, 1, "B")


# ---- normalize validation ----

def test_normalize_vep_rejects_wrong_assembly() -> None:
    payload = _vep_post_payload()[0]
    payload["assembly_name"] = "GRCh37"
    with pytest.raises(EnsemblLookupError, match="assembly"):
        EnsemblPipeline.normalize_vep(payload)


def test_normalize_vep_rejects_missing_consequences() -> None:
    payload = _vep_post_payload()[0]
    del payload["transcript_consequences"]
    with pytest.raises(EnsemblLookupError):
        EnsemblPipeline.normalize_vep(payload)


def test_normalize_vep_source_url_without_rsid() -> None:
    payload = _vep_post_payload()[0]
    payload["colocated_variants"] = [c for c in payload["colocated_variants"] if c["id"] != "rs1042522"]
    rec = EnsemblPipeline.normalize_vep(payload)
    assert rec["source_url"] == "https://rest.ensembl.org/"


# ---- federated dispatch (one ensembl source, two evidence classes) ----

@pytest.mark.asyncio
async def test_search_dispatches_hgvs_to_vep(monkeypatch) -> None:
    _fake_client(monkeypatch)
    f = FederatedEvidenceSearch()
    envs = await f._search_ensembl("ENST00000269305:c.215C>G", 5)
    assert len(envs) == 1
    env = envs[0]
    assert env["source"] == "ensembl"
    assert env["evidence_class"] == "variant_consequence"
    assert env["most_severe_consequence"] == "missense_variant"
    assert any("Computational consequence prediction" in w for w in env["warnings"])
    assert env["coverage"] == COVERAGE["ensembl"]


@pytest.mark.asyncio
async def test_search_dispatches_region_to_vep(monkeypatch) -> None:
    _fake_client(monkeypatch)
    f = FederatedEvidenceSearch()
    envs = await f._search_ensembl("17:7675218-7675218:1/G", 5)
    assert len(envs) == 1
    assert envs[0]["evidence_class"] == "variant_consequence"


@pytest.mark.asyncio
async def test_search_dispatches_gene_symbol_to_lookup(monkeypatch) -> None:
    _fake_client(monkeypatch)
    f = FederatedEvidenceSearch()
    envs = await f._search_ensembl("TP53", 5)
    assert len(envs) == 1
    assert envs[0]["evidence_class"] == "reference"
    assert envs[0]["ensembl_id"] == "ENSG00000141510"


def test_ensembl_is_one_federated_source_not_two() -> None:
    f = FederatedEvidenceSearch()
    assert "ensembl" in COVERAGE
    assert "vep" not in COVERAGE  # VEP is a capability of the ensembl source
    assert len([k for k in COVERAGE if k in ("lens_patents", "ibm_quantum")]) == 2


def test_registry_ensembl_points_at_real_pipeline() -> None:
    from pathlib import Path

    reg = build_default_registry()
    assert "ensembl" in reg
    entry = reg["ensembl"]
    # The adapter_owner must point at a real file, not a stale path.
    assert entry.adapter_owner == "engines/ensembl_pipeline.py"
    assert Path(entry.adapter_owner).exists()
    assert "VEP" in (entry.notes or "")


# ---- live smoke (gated) ----

@needs_live
@pytest.mark.asyncio
async def test_live_vep_post_tp53_p72r() -> None:
    records = await EnsemblPipeline().annotate_hgvs(["ENST00000269305:c.215C>G"])
    assert len(records) == 1
    rec = records[0]
    assert rec["most_severe_consequence"] == "missense_variant"
    assert rec["assembly"] == "GRCh38"
    canonical = next(
        t for t in rec["transcript_consequences"]
        if t["transcript_id"] == "ENST00000269305"
    )
    assert canonical["amino_acids"] == "P/R"
    assert canonical["sift_prediction"] == "tolerated"
    assert canonical["polyphen_prediction"] == "benign"


@needs_live
@pytest.mark.asyncio
async def test_live_vep_region_tp53() -> None:
    records = await EnsemblPipeline().annotate_region("17", 7675218, 7675218, 1, "G")
    assert records
    assert records[0]["most_severe_consequence"] == "missense_variant"
    assert records[0]["assembly"] == "GRCh38"
