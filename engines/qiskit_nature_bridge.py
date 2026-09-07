"""
Qiskit Nature Bridge for TMRDS.
Constructs molecular electronic-structure Hamiltonians and feeds them
into the existing QuantumRubiksCureEngine VQE path.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import numpy as np

logger = logging.getLogger("TMRDS.QiskitNature")

try:
    from qiskit_nature.second_q.drivers import PySCFDriver
    from qiskit_nature.second_q.mappers import JordanWignerMapper, ParityMapper
    QISKIT_NATURE_AVAILABLE = True
except ImportError:
    QISKIT_NATURE_AVAILABLE = False


class QiskitNatureBridge:
    """
    Quantum chemistry → qubit Hamiltonian adapter.

    Flow:
      1. Build molecule (atom coords) via PySCF
      2. Driver → ElectronicStructureProblem
      3. Mapper → qubit Hamiltonian
      4. Hand off coefficients to QuantumRubiksCureEngine.optimize_vqe
    """

    def __init__(self, mapper: str = "jordan_wigner") -> None:
        self.mapper_name = mapper
        self.available = QISKIT_NATURE_AVAILABLE

    def build_hamiltonian_from_xyz(
        self,
        atom_string: str,
        basis: str = "sto3g",
        charge: int = 0,
        spin: int = 0,
    ) -> Dict[str, Any]:
        """atom_string example: 'H 0 0 0; H 0 0 0.74'"""
        if not QISKIT_NATURE_AVAILABLE:
            return self._mock_h2_hamiltonian()

        try:
            driver = PySCFDriver(
                atom=atom_string,
                basis=basis,
                charge=charge,
                spin=spin,
            )
            problem = driver.run()
            if self.mapper_name == "parity":
                mapper = ParityMapper(num_particles=problem.num_particles)
            else:
                mapper = JordanWignerMapper()
            qubit_op = mapper.map(problem.hamiltonian.second_q_op())
            coeffs = [float(np.real(t.coeff)) for t in qubit_op]
            return {
                "status": "HAMILTONIAN_BUILT",
                "num_qubits": qubit_op.num_qubits,
                "num_terms": len(coeffs),
                "coefficients": coeffs[:64],
                "basis": basis,
                "mapper": self.mapper_name,
                "source": "qiskit-nature + PySCF",
            }
        except Exception as exc:  # noqa: BLE001
            logger.error("Hamiltonian build failed: %s", exc)
            return {"status": "ERROR", "error": str(exc)}

    def _mock_h2_hamiltonian(self) -> Dict[str, Any]:
        coeffs = [-1.0523732, 0.39793742, -0.39793742, -0.01128010, 0.18093120]
        return {
            "status": "HAMILTONIAN_BUILT_MOCK",
            "num_qubits": 4,
            "num_terms": len(coeffs),
            "coefficients": coeffs,
            "basis": "sto3g",
            "mapper": "jordan_wigner",
            "source": "mock_H2",
            "note": "Install qiskit-nature + pyscf for real electronic-structure Hamiltonians",
        }

    def status(self) -> Dict[str, Any]:
        return {
            "node": "QiskitNatureBridge",
            "qiskit_nature_available": QISKIT_NATURE_AVAILABLE,
            "mapper": self.mapper_name,
            "status": "READY",
        }
