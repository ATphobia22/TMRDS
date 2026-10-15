"""Tests for the live federated evidence search.

Unit tests use canned payloads (no network). Live smoke tests are gated by
TMRDS_LIVE_SMOKE=1 and fail honestly if a source is unreachable — they never
assert on invented records.
"""
from __future__ import annotations

import os

import pytest

from engines.arxiv_pipeline import ArxivPipeline
from engines.federated_evidence_search import FederatedEvidenceSearch, _make_envelope
from engines.openalex_pipeline import OpenAlexPipeline

LIVE = os.getenv("TMRDS_LIVE_SMOKE") == "1"
needs_live = pytest.mark.skipif(not LIVE, reason="Live smoke test opt-in only (TMRDS_LIVE_SMOKE=1)")


def test_envelope_has_provenance_and_no_mock_flag():
    env = _make_envelope(
        "europe_pmc", "Europe PMC",
        {"title": "TP53 and cancer", "doi": "10.1234/example", "source_url": "https://example.org/x"},
        "citation",
    )
    assert env["is_mock"] is False
    assert env["is_authoritative"] is False
    assert env["stable_id"].startswith("europe_pmc:")
    assert env["record_hash"] and len(env["record_hash"]) == 64
    assert env["retrieved_at"]
    assert env["coverage"]


def test_dedupe_keeps_first_and_merges_urls():
    f = FederatedEvidenceSearch()
    a = _make_envelope("europe_pmc", "Europe PMC", {"title": "T", "doi": "10.1/x", "source_url": "https://a.org"}, "citation")
    b = _make_envelope("pubmed", "PubMed", {"title": "T", "doi": "10.1/x", "source_url": "https://b.org"}, "citation")
    out = f._dedupe([a, b])
    assert len(out) == 1
    assert "https://a.org" in out[0]["related_ids"]
    assert "https://b.org" in out[0]["related_ids"]


def test_openalex_normalize_handles_minimal_work():
    rec = OpenAlexPipeline.normalize({"id": "https://openalex.org/W1", "display_name": "A study"})
    assert rec["title"] == "A study"
    assert rec["authors"] == []
    assert rec["doi"] is None


def test_arxiv_normalize_parses_atom():
    xml = """<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
    <entry><id>http://arxiv.org/abs/2401.00001v1</id>
    <title>Quantum test</title><summary>An abstract.</summary>
    <published>2024-01-01T00:00:00Z</published>
    <author><name>Jane Doe</name></author>
    <arxiv:primary_category term="q-bio.QM"/></entry></feed>"""
    entries = ArxivPipeline._parse(xml)
    rec = ArxivPipeline.normalize(entries[0])
    assert rec["arxiv_id"] == "2401.00001v1"
    assert rec["authors"] == ["Jane Doe"]
    assert rec["is_preprint"] is True


def test_empty_query_rejected():
    f = FederatedEvidenceSearch()
    with pytest.raises(ValueError):
        f.search_all_sync("  ")


@needs_live
def test_live_search_returns_real_envelopes():
    f = FederatedEvidenceSearch()
    res = f.search_all_sync("TP53", per_source=3)
    assert res["total_envelopes"] > 0
    assert res["governance"]["no_mock_records"] is True
    for env in res["envelopes"]:
        assert env["is_mock"] is False
        assert env["source_url"]
        assert env["record_hash"]


@needs_live
def test_live_structure_fetch_tp53():
    import asyncio
    f = FederatedEvidenceSearch()
    s = asyncio.run(f.fetch_structure("P04637"))
    assert s["status"] == "real_predicted"
    assert s["is_mock"] is False
    assert isinstance(s["mean_plddt"], (int, float))
    assert s["pdb_url"]


@needs_live
def test_live_structure_unknown_accession_is_not_found():
    import asyncio
    f = FederatedEvidenceSearch()
    s = asyncio.run(f.fetch_structure("NOTANACCESSION123"))
    assert s["status"] in ("not_found", "unavailable")
    assert s.get("mean_plddt") is None
