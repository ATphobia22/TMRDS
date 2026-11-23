"""Exact bounded statevector simulation of Grover search over six *research* planes.

Bits select abstract research-coverage plans, not patients, molecules or cures.
This is classical simulation of a quantum algorithm, not QPU execution.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any

PLANES = (
    "disease_phenotype",
    "target_pathway",
    "structure",
    "molecule",
    "trials_labels",
    "population_equity",
)
N_STATES = 1 << len(PLANES)
MAX_ITERATIONS = 12


def _plan(index: int) -> tuple[str, ...]:
    return tuple(plane for i, plane in enumerate(PLANES) if index & (1 << (5 - i)))


def simulate_grover_research_plan(
    *, required: tuple[str, ...] = ("disease_phenotype", "target_pathway", "trials_labels"),
    max_planes: int = 4,
) -> dict[str, Any]:
    """Phase oracle + diffuser; explicit classical baseline, never clinical inference.

    The marked set is enumerated classically, so this simulator cannot establish
    quantum speedup, even if its ideal oracle-call count is smaller than N.
    """
    if (not isinstance(required, tuple) or not 1 <= len(required) <= len(PLANES)
            or any(not isinstance(x, str) or x not in PLANES for x in required)
            or len(set(required)) != len(required)):
        raise ValueError("required must be a unique, nonempty tuple of canonical evidence planes")
    if type(max_planes) is not int or not len(required) <= max_planes <= len(PLANES):
        raise ValueError("max_planes must include every required plane and be at most six")

    required_set = set(required)
    marked = frozenset(
        i for i in range(N_STATES)
        if required_set.issubset(_plan(i)) and len(_plan(i)) <= max_planes
    )
    count = len(marked)
    if not 0 < count < N_STATES:
        raise ValueError("oracle must select a proper nonempty subset")
    angle = math.asin(math.sqrt(count / N_STATES))
    iterations = min(MAX_ITERATIONS, max(0, int(round(math.pi / (4 * angle) - 0.5))))
    amplitudes = [1.0 / math.sqrt(N_STATES)] * N_STATES
    for _ in range(iterations):
        for i in marked:
            amplitudes[i] = -amplitudes[i]  # S_f phase oracle
        mean = sum(amplitudes) / N_STATES
        amplitudes = [2 * mean - a for a in amplitudes]  # Grover diffuser
    probs = [a * a for a in amplitudes]
    norm = math.fsum(probs)
    if not math.isclose(norm, 1.0, rel_tol=1e-11, abs_tol=1e-11):
        raise ArithmeticError("Quantum statevector norm was not preserved")
    ranked = sorted(marked, key=lambda i: (-probs[i], i))
    oracle = {"required": list(required), "max_planes": max_planes,
              "size": N_STATES, "marked_states": count}
    digest = hashlib.sha256(json.dumps(
        oracle, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": "1.0",
        "task": "synthetic_research_coverage_planning",
        "backend": "classical_exact_statevector_simulator",
        "algorithm": "grover_phase_oracle_and_diffusion",
        "planes": list(PLANES), "oracle": oracle, "oracle_sha256": digest,
        "iterations": iterations,
        "simulated_probability_of_valid_plan": round(math.fsum(probs[i] for i in marked), 12),
        "uniform_random_baseline_probability": round(count / N_STATES, 12),
        "classical_enumeration_oracle_evaluations": N_STATES,
        "idealized_quantum_oracle_calls": iterations,
        "measured_speedup": None,
        "simulated_quantum_advantage_claimed": False,
        "normalization_error": round(abs(1.0 - norm), 14),
        "example_marked_plans": [
            {"bitstring": format(i, "06b"), "planes": list(_plan(i)),
             "simulated_probability": round(probs[i], 12),
             "satisfies_oracle": True}
            for i in ranked[:8]
        ],
        "execution": {
            "quantum_hardware_used": False, "qiskit_used": False,
            "sparse_blossom_used": False,
            "sparse_blossom_applicability": "quantum_error_correction_only_not_medical_search",
            "source_data_queried": False, "patient_data_ingested": False,
            "evidence_verification_executed": False,
        },
        "governance": {
            "research_advisory_only": True, "clinical_promotion_allowed": False,
            "treatment_recommendation": False, "cure_claim": False,
            "human_authority_final": True,
        },
        "limitations": [
            "Each qubit selects an abstract research source plane, not a disease state.",
            "The classical enumeration builds the oracle; query-count comparisons do not imply speedup.",
            "Probability refers to satisfying coverage constraints, not treatment success.",
            "A satisfying plan is not a therapy, cure, clinical recommendation, or scientific finding.",
            "Sparse Blossom is a quantum error-correction decoder, not a medical search algorithm.",
        ],
    }
