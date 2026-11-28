"""Deterministic CPU statevector VQE benchmark for a two-qubit toy Hamiltonian.

This module performs a real local statevector simulation. It is a software
verification benchmark only: it is not a molecular model, clinical model,
treatment optimizer, or evidence of quantum advantage.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any

import numpy as np


_SIMULATOR_VERSION = "tmrds-statevector-v1"


def _statevector(theta: float) -> np.ndarray:
    """Prepare RY(theta) on q0 followed by CNOT(q0 -> q1)."""
    cosine = math.cos(theta / 2.0)
    sine = math.sin(theta / 2.0)
    # Computational basis order: |00>, |01>, |10>, |11>.
    # CNOT maps the |10> amplitude to |11>.
    return np.asarray([cosine, 0.0, 0.0, sine], dtype=np.complex128)


def _hamiltonian() -> np.ndarray:
    """Return H = -Z0 Z1 - X0 X1 in computational basis order."""
    x = np.asarray([[0.0, 1.0], [1.0, 0.0]], dtype=np.float64)
    z = np.asarray([[1.0, 0.0], [0.0, -1.0]], dtype=np.float64)
    return -(np.kron(z, z) + np.kron(x, x))


def run_bell_hamiltonian_vqe(*, grid_points: int = 721) -> dict[str, Any]:
    """Run a deterministic grid-based VQE and exact-diagonalization baseline.

    The variational circuit prepares cos(theta/2)|00> + sin(theta/2)|11>.
    The toy Hamiltonian H = -Z0Z1 - X0X1 has exact ground energy -2. The
    optimizer searches [0, 2*pi] and evaluates the energy using the local
    statevector; no network, hardware, paid service, or patient data is used.
    """
    if (
        isinstance(grid_points, bool)
        or not isinstance(grid_points, int)
        or grid_points < 21
        or grid_points > 1001
        or grid_points % 2 == 0
    ):
        raise ValueError("grid_points must be an odd integer between 21 and 1001")

    hamiltonian = _hamiltonian()
    angles = np.linspace(0.0, 2.0 * math.pi, grid_points, dtype=np.float64)
    energies = np.empty(grid_points, dtype=np.float64)

    for index, angle in enumerate(angles):
        state = _statevector(float(angle))
        energies[index] = float(np.real(np.vdot(state, hamiltonian @ state)))

    best_index = int(np.argmin(energies))
    theta = float(angles[best_index])
    state = _statevector(theta)
    vqe_energy = float(energies[best_index])
    exact_ground_energy = float(np.linalg.eigvalsh(hamiltonian)[0])
    norm = float(np.linalg.norm(state))
    absolute_error = abs(vqe_energy - exact_ground_energy)

    payload: dict[str, Any] = {
        "simulator": _SIMULATOR_VERSION,
        "execution_status": "real_quantum_simulator",
        "backend": "numpy_statevector_cpu",
        "algorithm": "grid_search_variational_quantum_eigensolver",
        "model": "two_qubit_bell_hamiltonian",
        "hamiltonian": "-Z0*Z1 - X0*X1",
        "circuit": ["RY(theta) q0", "CNOT q0->q1"],
        "qubits": 2,
        "grid_points": grid_points,
        "theta_radians": theta,
        "statevector": [[float(value.real), float(value.imag)] for value in state],
        "statevector_norm": norm,
        "vqe_energy": vqe_energy,
        "exact_ground_energy": exact_ground_energy,
        "absolute_error": float(absolute_error),
        "shots": None,
        "seed": None,
        "hardware_executed": False,
        "clinical_claim": False,
        "quantum_advantage_claim": False,
        "data_classification": "synthetic_mathematical_benchmark",
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    payload["result_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return payload
