from __future__ import annotations

from typing import Any

import pytest

import engines.qiskit_nature_bridge as bridge_module
from engines.qiskit_nature_bridge import QiskitNatureBridge


def test_missing_optional_dependencies_never_returns_hard_coded_h2_coefficients(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bridge_module, "QISKIT_NATURE_AVAILABLE", False)
    monkeypatch.setattr(bridge_module, "PYSCF_AVAILABLE", False)
    bridge = QiskitNatureBridge()

    result = bridge.build_hamiltonian_from_xyz("Li 0 0 0; H 0 0 2.5")

    assert result["status"] == "NOT_CONFIGURED"
    assert result["coefficients"] is None
    assert result["num_qubits"] is None
    assert result["computation_executed"] is False
    assert bridge.status()["status"] == "NOT_CONFIGURED"
    assert bridge.status()["vqe_solver_implemented"] is False


@pytest.mark.parametrize("mapper", ["bogus", "", "../jordan_wigner"])
def test_unknown_mapper_is_rejected(mapper: str) -> None:
    with pytest.raises(ValueError, match="mapper"):
        QiskitNatureBridge(mapper=mapper)


def test_invalid_molecular_input_is_rejected_before_optional_dependency_check() -> None:
    with pytest.raises(ValueError, match="atom_string"):
        QiskitNatureBridge().build_hamiltonian_from_xyz("")


def test_runtime_failure_does_not_expose_raw_exception_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BrokenDriver:
        def __init__(self, **kwargs: Any) -> None:
            raise RuntimeError("sensitive filesystem or user input detail")

    monkeypatch.setattr(bridge_module, "QISKIT_NATURE_AVAILABLE", True)
    monkeypatch.setattr(bridge_module, "PYSCF_AVAILABLE", True)
    monkeypatch.setattr(bridge_module, "PySCFDriver", BrokenDriver, raising=False)

    result = QiskitNatureBridge().build_hamiltonian_from_xyz("H 0 0 0; H 0 0 0.74")

    assert result["status"] == "ERROR"
    assert "sensitive filesystem" not in str(result)
    assert result["computation_executed"] is False


def test_real_hamiltonian_coefficients_are_read_from_sparse_pauli_op(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import numpy as np

    class FakeProblem:
        num_particles = (1, 1)

        class Hamiltonian:
            @staticmethod
            def second_q_op() -> str:
                return "fermionic-operator"

        hamiltonian = Hamiltonian()

    class FakeDriver:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

        def run(self) -> FakeProblem:
            return FakeProblem()

    class FakeSparsePauliOp:
        coeffs = np.asarray([-1.25 + 0j, 0.5 + 0j], dtype=np.complex128)
        num_qubits = 2

    class FakeMapper:
        def map(self, _operator: str) -> FakeSparsePauliOp:
            return FakeSparsePauliOp()

    monkeypatch.setattr(bridge_module, "QISKIT_NATURE_AVAILABLE", True)
    monkeypatch.setattr(bridge_module, "PYSCF_AVAILABLE", True)
    monkeypatch.setattr(bridge_module, "PySCFDriver", FakeDriver, raising=False)
    monkeypatch.setattr(bridge_module, "JordanWignerMapper", FakeMapper, raising=False)

    result = QiskitNatureBridge().build_hamiltonian_from_xyz("H 0 0 0; H 0 0 0.74")

    assert result["status"] == "HAMILTONIAN_BUILT"
    assert result["coefficients"] == [-1.25, 0.5]
    assert result["num_qubits"] == 2
    assert result["computation_executed"] is True
    assert "not a VQE optimization" in result["note"]


def test_non_real_coefficients_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import numpy as np

    class FakeProblem:
        num_particles = (1, 1)

        class Hamiltonian:
            @staticmethod
            def second_q_op() -> str:
                return "fermionic-operator"

        hamiltonian = Hamiltonian()

    class FakeDriver:
        def __init__(self, **kwargs: Any) -> None:
            pass

        def run(self) -> FakeProblem:
            return FakeProblem()

    class FakeSparsePauliOp:
        coeffs = np.asarray([-1.25 + 0.1j], dtype=np.complex128)
        num_qubits = 2

    class FakeMapper:
        def map(self, _operator: str) -> FakeSparsePauliOp:
            return FakeSparsePauliOp()

    monkeypatch.setattr(bridge_module, "QISKIT_NATURE_AVAILABLE", True)
    monkeypatch.setattr(bridge_module, "PYSCF_AVAILABLE", True)
    monkeypatch.setattr(bridge_module, "PySCFDriver", FakeDriver, raising=False)
    monkeypatch.setattr(bridge_module, "JordanWignerMapper", FakeMapper, raising=False)

    result = QiskitNatureBridge().build_hamiltonian_from_xyz("H 0 0 0; H 0 0 0.74")

    assert result["status"] == "ERROR"
    assert result["coefficients"] is None
    assert result["computation_executed"] is False
