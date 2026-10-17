from __future__ import annotations

import math
from typing import Any

import pytest
import requests

from engines.alphafold3_node import AlphaFold3Node


class FakeResponse:
    def __init__(self, payload: Any, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def json(self) -> Any:
        return self.payload


def test_mock_mode_never_claims_structure_or_confidence() -> None:
    result = AlphaFold3Node().predict_structure("ACDEFGHIKLMNPQRSTVWY")

    assert result["status"] == "MOCK_ONLY"
    assert result["metrics"] is None
    assert result["structure_uri"] is None
    assert "does not run AlphaFold" in result["message"]


@pytest.mark.parametrize("sequence", ["", "ABCDEFGHI!", "A" * 100001, None])
def test_predict_structure_rejects_invalid_sequences(sequence: Any) -> None:
    with pytest.raises(ValueError, match="sequence"):
        AlphaFold3Node().predict_structure(sequence)


@pytest.mark.parametrize("job_name", ["../secrets", "bad name", "", "x" * 129])
def test_job_name_is_validated(job_name: str) -> None:
    with pytest.raises(ValueError, match="job_name"):
        AlphaFold3Node().predict_structure("ACDEFGHIKLMNPQRSTVWY", job_name=job_name)


def test_validate_target_rejects_invalid_bounds_and_entries() -> None:
    node = AlphaFold3Node()
    with pytest.raises(ValueError, match="top_k"):
        node.validate_target("ACDEFGHIKLMNPQRSTVWY", ["CCO"], top_k=True)
    with pytest.raises(ValueError, match=r"candidate_smiles\[0\]"):
        node.validate_target("ACDEFGHIKLMNPQRSTVWY", [""])


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf"), True, 61])
def test_live_lookup_rejects_invalid_timeout_before_network(timeout: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: pytest.fail("network must not be called"))
    with pytest.raises(ValueError, match="timeout"):
        AlphaFold3Node().fetch_live_alphafold_db("P04637", timeout=timeout)


@pytest.mark.parametrize("accession", ["", "../P04637", "https://example.com", "P04637?x=1", None])
def test_live_lookup_rejects_invalid_accession_before_network(accession: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: pytest.fail("network must not be called"))
    with pytest.raises(ValueError, match="uniprot_id"):
        AlphaFold3Node().fetch_live_alphafold_db(accession)


def test_live_lookup_uses_validated_upstream_metric_and_asset_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []
    payload = [{
        "globalMetricValue": 92.4,
        "gene": "TP53",
        "pdbUrl": "https://alphafold.ebi.ac.uk/files/AF-P04637-F1-model_v4.pdb",
        "cifUrl": "https://alphafold.ebi.ac.uk/files/AF-P04637-F1-model_v4.cif",
        "paeDocUrl": "https://evil.example/pae.json",
        "latestVersion": 4,
    }]

    def fake_get(url: str, **kwargs: Any) -> FakeResponse:
        calls.append((url, kwargs))
        return FakeResponse(payload)

    monkeypatch.setattr(requests, "get", fake_get)
    result = AlphaFold3Node().fetch_live_alphafold_db("p04637")

    assert result["status"] == "REAL_PREDICTION_CONFIDENCE_AVAILABLE"
    assert result["uniprot_id"] == "P04637"
    assert result["metrics"] == {"mean_plddt": 92.4}
    assert result["pdb_url"].startswith("https://alphafold.ebi.ac.uk/")
    assert result["pae_url"] is None
    assert calls[0][1]["allow_redirects"] is False
    assert calls[0][1]["timeout"] == 20.0


def test_live_lookup_does_not_accept_nonfinite_or_out_of_range_confidence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: FakeResponse([{"globalMetricValue": math.inf}]))
    result = AlphaFold3Node().fetch_live_alphafold_db("P04637")

    assert result["status"] == "REAL_PREDICTION_CONFIDENCE_UNAVAILABLE"
    assert result["metrics"] is None


def test_backend_placeholders_never_claim_execution() -> None:
    for backend in ("alphafold_server", "openfold3", "local_af3"):
        result = AlphaFold3Node(backend=backend).predict_structure("ACDEFGHIKLMNPQRSTVWY")
        assert result["status"] == "NOT_CONFIGURED"
        assert result["metrics"] is None
        assert result["structure_uri"] is None


def test_status_does_not_advertise_unimplemented_prediction_capabilities_as_available() -> None:
    for backend in ("mock", "alphafold_server", "openfold3", "local_af3"):
        status = AlphaFold3Node(backend=backend).status()
        assert status["available_capabilities"] == []
        assert status["prediction_execution_available"] is False
        assert status["confidence_metrics_available"] is False
        assert status["structure_artifact_available"] is False
        assert status["declared_capabilities"]
