from __future__ import annotations

import pytest

from engines.alphafold3_node import AlphaFold3Node


def test_mock_structure_request_is_explicitly_not_a_prediction() -> None:
    result = AlphaFold3Node().predict_structure("ACDEFGHIKLMNPQRSTVWY")

    assert result["backend"] == "mock"
    assert result["status"] == "MOCK_ONLY"
    assert result["metrics"] is None
    assert result["structure_uri"] is None
    assert "does not run AlphaFold" in result["message"]


def test_mock_target_validation_does_not_fabricate_rankings() -> None:
    result = AlphaFold3Node().validate_target(
        "ACDEFGHIKLMNPQRSTVWY", ["CCO", "CCN"]
    )

    assert result["status"] == "NO_RANKING_PERFORMED"
    assert result["top_k"] == []
    assert result["method"] == "mock_unavailable"
    assert "does not score" in result["message"]


def test_mock_target_validation_rejects_nonpositive_top_k() -> None:
    with pytest.raises(ValueError, match="top_k must be at least 1"):
        AlphaFold3Node().validate_target("ACDEFGHIKLMNPQRSTVWY", ["CCO"], top_k=0)
