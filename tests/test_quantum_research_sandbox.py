from __future__ import annotations

import pytest

from engines.quantum_cure_engine import (
    BackendType,
    ComputationStatus,
    QuantumResearchSandboxFixed,
)


def test_package_presence_does_not_claim_simulation_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    sandbox = QuantumResearchSandboxFixed()
    monkeypatch.setattr(sandbox, "has_qiskit", True)
    monkeypatch.setattr(sandbox, "has_pennylane", True)

    hypotheses = sandbox.generate_hypotheses("breast cancer", "BRCA1", ["olaparib"])

    assert len(hypotheses) == 1
    hypothesis = hypotheses[0]
    assert hypothesis.computation_status is ComputationStatus.NOT_CONFIGURED
    assert hypothesis.reproducibility.status is ComputationStatus.NOT_CONFIGURED
    assert hypothesis.reproducibility.backend is BackendType.NONE
    assert hypothesis.reproducibility.device == "not_configured"
    assert hypothesis.reproducibility.qubits is None
    assert hypothesis.reproducibility.shots is None
    assert hypothesis.reproducibility.seed is None
    assert hypothesis.reproducibility.cost_usd is None
    assert hypothesis.quantum_score is None
    assert hypothesis.classical_baseline_score is None
    evidence = hypothesis.to_evidence_record()
    assert evidence["computation_executed"] is False
    assert evidence["score_available"] is False


def test_empty_compound_list_returns_no_hypotheses() -> None:
    assert QuantumResearchSandboxFixed().generate_hypotheses("disease", "GENE", []) == []


def test_compound_count_above_budget_is_rejected_instead_of_silently_truncated() -> None:
    with pytest.raises(ValueError, match="at most 10"):
        QuantumResearchSandboxFixed().generate_hypotheses("disease", "GENE", [str(i) for i in range(11)])


def test_hypothesis_source_links_are_encoded_and_marked_uncomputed() -> None:
    result = QuantumResearchSandboxFixed().generate_hypotheses(
        "breast cancer", "BRCA1 / TP53", ["compound name #1"]
    )[0]

    assert "%20" in result.evidence_links[0]
    assert "%23" in result.evidence_links[0]
    assert "term=BRCA1+%2F+TP53" in result.evidence_links[1]
    assert any("No molecular Hamiltonian" in item for item in result.limitations)


def test_invalid_hypothesis_inputs_are_rejected() -> None:
    sandbox = QuantumResearchSandboxFixed()
    with pytest.raises(ValueError, match="gene"):
        sandbox.generate_hypotheses("disease", " ", ["compound"])
    with pytest.raises(ValueError, match=r"compounds\[0\]"):
        sandbox.generate_hypotheses("disease", "GENE", [""])
