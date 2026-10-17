from __future__ import annotations

import hashlib
import json
from typing import Any

import pytest
import requests

from engines.disease_graph_model import EnsemblLookupError, EnsemblRESTAdapter


class FakeResponse:
    def __init__(self, payload: Any, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code
        self.headers = {"Content-Type": "application/json"}
        self.content = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.text = self.content.decode("utf-8")

    def json(self) -> Any:
        return self.payload


def _gene_payload() -> dict[str, Any]:
    return {
        "id": "ENSG00000012048",
        "object_type": "Gene",
        "display_name": "BRCA1",
        "version": 19,
        "assembly_name": "GRCh38",
        "start": 43044295,
        "end": 43170245,
        "strand": -1,
    }


def test_lookup_gene_uses_live_source_response_and_hashes_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = {
        "https://rest.ensembl.org/info/data": FakeResponse({"releases": [116]}),
        "https://rest.ensembl.org/lookup/symbol/homo_sapiens/BRCA1": FakeResponse(_gene_payload()),
    }
    calls: list[tuple[str, dict[str, Any]]] = []

    def fake_get(url: str, **kwargs: Any) -> FakeResponse:
        calls.append((url, kwargs))
        return responses[url]

    monkeypatch.setattr(requests, "get", fake_get)
    identifier, provenance, payload = EnsemblRESTAdapter().lookup_gene(" BRCA1 ")

    assert identifier.namespace == "ENSEMBL"
    assert identifier.id == "ENSG00000012048"
    assert identifier.version == "19"
    assert payload["display_name"] == "BRCA1"
    assert provenance.source_version == "116"
    assert provenance.raw_record_hash == hashlib.sha256(responses[
        "https://rest.ensembl.org/lookup/symbol/homo_sapiens/BRCA1"
    ].content).hexdigest()
    assert provenance.query_params["symbol"] == "BRCA1"
    assert len(calls) == 2
    assert all(call_kwargs["allow_redirects"] is False for _, call_kwargs in calls)


def test_lookup_gene_rejects_path_like_symbols_without_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_if_called(*args: Any, **kwargs: Any) -> FakeResponse:
        raise AssertionError("network call should not happen")

    monkeypatch.setattr(requests, "get", fail_if_called)
    with pytest.raises(ValueError, match="unsupported characters"):
        EnsemblRESTAdapter().lookup_gene("../BRCA1")


def test_lookup_gene_does_not_fabricate_identifiers_on_404(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [
        FakeResponse({"releases": [116]}),
        FakeResponse({"error": "No symbol found"}, status_code=404),
    ]

    def fake_get(url: str, **kwargs: Any) -> FakeResponse:
        return responses.pop(0)

    monkeypatch.setattr(requests, "get", fake_get)
    with pytest.raises(EnsemblLookupError, match="HTTP 404"):
        EnsemblRESTAdapter().lookup_gene("UNKNOWN_GENE")


def test_release_pin_fails_closed_when_server_serves_a_different_release(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_get(url: str, **kwargs: Any) -> FakeResponse:
        calls.append(url)
        return FakeResponse({"releases": [116]})

    monkeypatch.setattr(requests, "get", fake_get)
    with pytest.raises(EnsemblLookupError, match="could not be verified"):
        EnsemblRESTAdapter(release="112").lookup_gene("BRCA1")
    assert calls == ["https://rest.ensembl.org/info/data"]


def test_transcript_lookup_maps_real_metadata_and_source_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gene_payload = {
        "id": "ENSG00000012048",
        "object_type": "Gene",
        "version": 19,
        "assembly_name": "GRCh38",
        "Transcript": [
            {
                "id": "ENST00000357654",
                "object_type": "Transcript",
                "version": 3,
                "biotype": "protein_coding",
                "is_canonical": 1,
                "tags": ["MANE_Select"],
                "Exon": [{"id": "ENSE00003884693", "start": 1, "end": 20}],
            }
        ],
    }
    responses = {
        "https://rest.ensembl.org/info/data": FakeResponse({"releases": [116]}),
        "https://rest.ensembl.org/lookup/id/ENSG00000012048?expand=1": FakeResponse(gene_payload),
    }

    monkeypatch.setattr(requests, "get", lambda url, **kwargs: responses[url])
    transcripts, provenance = EnsemblRESTAdapter().get_transcripts("ENSG00000012048")

    assert len(transcripts) == 1
    assert transcripts[0].ensembl_transcript_id.id == "ENST00000357654"
    assert transcripts[0].ensembl_transcript_id.version == "3"
    assert transcripts[0].is_mane_select is True
    assert transcripts[0].is_canonical is True
    assert transcripts[0].exons[0]["id"] == "ENSE00003884693"
    assert transcripts[0].ensembl_release == "116"
    assert transcripts[0].evidence[0].provenance.raw_record_hash == provenance.raw_record_hash


def test_vep_hgvs_query_returns_real_annotations_and_rejects_spdi(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = {
        "https://rest.ensembl.org/info/data": FakeResponse({"releases": [116]}),
        "https://rest.ensembl.org/vep/human/hgvs/17:g.41196312G%3ET": FakeResponse(
            [{"input": "17:g.41196312G>T", "most_severe_consequence": "missense_variant"}]
        ),
    }
    monkeypatch.setattr(requests, "get", lambda url, **kwargs: responses[url])
    annotations, provenance = EnsemblRESTAdapter().get_variant_consequences("17:g.41196312G>T")

    assert annotations[0]["most_severe_consequence"] == "missense_variant"
    assert provenance.source_name == "Ensembl"
    assert provenance.query_params["variant_hgvs"] == "17:g.41196312G>T"

    with pytest.raises(EnsemblLookupError, match="SPDI-to-HGVS normalization is not implemented"):
        EnsemblRESTAdapter().get_variant_consequences("NC_000017.11:41196311:G:T")
