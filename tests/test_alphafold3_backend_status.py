from __future__ import annotations

from engines.alphafold3_node import AlphaFold3Node


def test_unimplemented_backend_is_not_reported_as_queued() -> None:
    node = AlphaFold3Node(backend="alphafold_server")

    result = node.predict_structure("ACDEFGHIKLMNPQRSTVWY")

    assert result["status"] == "NOT_CONFIGURED"
    assert result["job_id"] is None
    assert result["metrics"] is None
    assert result["structure_uri"] is None
    assert "No prediction was submitted" in result["message"]
    assert node.status()["status"] == "NOT_CONFIGURED"


def test_mock_backend_status_is_not_ready() -> None:
    assert AlphaFold3Node().status()["status"] == "MOCK_ONLY"
