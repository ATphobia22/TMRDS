import pytest

from engines.evidence_graph_repository import vector_literal


def test_vector_literal_serializes_finite_fixed_dimension_vector():
    assert vector_literal([0.0, 0.25, -1.0]) == "[0.0,0.25,-1.0]"


def test_vector_literal_rejects_non_finite_values():
    with pytest.raises(ValueError, match="finite"):
        vector_literal([float("nan")])
