from __future__ import annotations

import math

import pytest

from engines.quantum_statevector_vqe import run_bell_hamiltonian_vqe


def test_two_qubit_vqe_executes_statevector_and_matches_exact_ground_state() -> None:
    result = run_bell_hamiltonian_vqe(grid_points=721)

    assert result["execution_status"] == "real_quantum_simulator"
    assert result["backend"] == "numpy_statevector_cpu"
    assert result["model"] == "two_qubit_bell_hamiltonian"
    assert result["qubits"] == 2
    assert result["hardware_executed"] is False
    assert result["clinical_claim"] is False
    assert result["statevector_norm"] == pytest.approx(1.0, abs=1e-12)
    assert result["vqe_energy"] == pytest.approx(-2.0, abs=1e-6)
    assert result["exact_ground_energy"] == pytest.approx(-2.0, abs=1e-12)
    assert result["absolute_error"] <= 1e-6
    assert result["theta_radians"] == pytest.approx(math.pi / 2, abs=1e-3)
    assert len(result["result_sha256"]) == 64


def test_vqe_result_is_reproducible_for_identical_configuration() -> None:
    first = run_bell_hamiltonian_vqe(grid_points=181)
    second = run_bell_hamiltonian_vqe(grid_points=181)

    assert first["result_sha256"] == second["result_sha256"]
    assert first["vqe_energy"] == second["vqe_energy"]
    assert first["theta_radians"] == second["theta_radians"]


@pytest.mark.parametrize("grid_points", [True, 2, 20, 1002, 3.5])
def test_vqe_rejects_invalid_grid_sizes(grid_points: object) -> None:
    with pytest.raises(ValueError, match="odd integer"):
        run_bell_hamiltonian_vqe(grid_points=grid_points)  # type: ignore[arg-type]
