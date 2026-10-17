"""Fail-closed Qiskit Nature bridge for optional molecular research computation."""
from __future__ import annotations

import logging
import re
from typing import Any, Dict

import numpy as np

logger = logging.getLogger("TMRDS.QiskitNature")

try:
    from qiskit_nature.second_q.drivers import PySCFDriver
    from qiskit_nature.second_q.mappers import JordanWignerMapper, ParityMapper
    QISKIT_NATURE_AVAILABLE = True
except ImportError:
    QISKIT_NATURE_AVAILABLE = False

try:
    import pyscf  # noqa: F401
    PYSCF_AVAILABLE = True
except ImportError:
    PYSCF_AVAILABLE = False


class QiskitNatureBridge:
    """Build a genuine molecular Hamiltonian when all optional runtime dependencies exist.

    The adapter does not return a generic hard-coded H2 Hamiltonian for another
    molecule. Package availability is not evidence that VQE or quantum hardware
    execution occurred.
    """

    SUPPORTED_MAPPERS = {"jordan_wigner", "parity"}

    def __init__(self, mapper: str = "jordan_wigner") -> None:
        if mapper not in self.SUPPORTED_MAPPERS:
            raise ValueError(f"mapper must be one of {sorted(self.SUPPORTED_MAPPERS)}")
        self.mapper_name = mapper
        self.available = QISKIT_NATURE_AVAILABLE and PYSCF_AVAILABLE

    def build_hamiltonian_from_xyz(
        self,
        atom_string: str,
        basis: str = "sto3g",
        charge: int = 0,
        spin: int = 0,
    ) -> Dict[str, Any]:
        """Build an electronic-structure Hamiltonian from semicolon-delimited XYZ atoms."""
        if not isinstance(atom_string, str) or not atom_string.strip():
            raise ValueError("atom_string must be a non-empty molecular geometry")
        if len(atom_string) > 4096 or any(ord(character) < 32 and character not in "\t\r\n" for character in atom_string):
            raise ValueError("atom_string contains unsupported control characters or exceeds the size limit")
        if not isinstance(basis, str) or not re.fullmatch(r"[A-Za-z0-9*+()_-]{1,64}", basis):
            raise ValueError("basis contains unsupported characters or has an invalid length")
        if isinstance(charge, bool) or not isinstance(charge, int) or not -100 <= charge <= 100:
            raise ValueError("charge must be an integer from -100 through 100")
        if isinstance(spin, bool) or not isinstance(spin, int) or not 0 <= spin <= 100:
            raise ValueError("spin must be an integer from 0 through 100")

        if not QISKIT_NATURE_AVAILABLE or not PYSCF_AVAILABLE:
            return {
                "status": "NOT_CONFIGURED",
                "error_code": "OPTIONAL_BACKEND_UNAVAILABLE",
                "message": (
                    "No Hamiltonian was built because qiskit-nature and PySCF are both required. "
                    "No fallback or placeholder coefficients were returned."
                ),
                "num_qubits": None,
                "num_terms": None,
                "coefficients": None,
                "basis": basis,
                "mapper": self.mapper_name,
                "source": None,
                "computation_executed": False,
            }

        try:
            driver = PySCFDriver(atom=atom_string.strip(), basis=basis, charge=charge, spin=spin)
            problem = driver.run()
            if self.mapper_name == "parity":
                mapper = ParityMapper(num_particles=problem.num_particles)
            else:
                mapper = JordanWignerMapper()
            qubit_op = mapper.map(problem.hamiltonian.second_q_op())
            raw_coefficients = np.asarray(qubit_op.coeffs)
            if raw_coefficients.dtype == object or not np.isfinite(raw_coefficients).all():
                raise ValueError("operator coefficients are parameterized or non-finite")
            if np.any(np.abs(np.imag(raw_coefficients)) > 1e-8):
                raise ValueError("molecular Hamiltonian contains non-real Pauli coefficients")
            coefficients = [float(value) for value in np.real(raw_coefficients).tolist()]
            return {
                "status": "HAMILTONIAN_BUILT",
                "num_qubits": int(qubit_op.num_qubits),
                "num_terms": len(coefficients),
                "coefficients": coefficients[:64],
                "coefficients_truncated": len(coefficients) > 64,
                "basis": basis,
                "mapper": self.mapper_name,
                "source": "qiskit-nature + PySCF",
                "computation_executed": True,
                "note": "Hamiltonian construction only; this result is not a VQE optimization or hardware run.",
            }
        except Exception as exc:  # noqa: BLE001 - do not leak library paths or user input
            logger.error("Hamiltonian build failed (%s)", type(exc).__name__)
            return {
                "status": "ERROR",
                "error_code": "HAMILTONIAN_BUILD_FAILED",
                "error_type": type(exc).__name__,
                "message": "Hamiltonian construction failed; inspect restricted service diagnostics.",
                "num_qubits": None,
                "num_terms": None,
                "coefficients": None,
                "basis": basis,
                "mapper": self.mapper_name,
                "source": "qiskit-nature + PySCF",
                "computation_executed": False,
            }

    def status(self) -> Dict[str, Any]:
        available = QISKIT_NATURE_AVAILABLE and PYSCF_AVAILABLE
        return {
            "node": "QiskitNatureBridge",
            "qiskit_nature_available": QISKIT_NATURE_AVAILABLE,
            "pyscf_available": PYSCF_AVAILABLE,
            "mapper": self.mapper_name,
            "status": "AVAILABLE" if available else "NOT_CONFIGURED",
            "vqe_solver_implemented": False,
            "hardware_execution_claimed": False,
        }
