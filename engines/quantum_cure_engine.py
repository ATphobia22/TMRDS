"""Research-computation metadata scaffold; no model or quantum job is executed here."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import List, Optional
from urllib.parse import quote, urlencode
import os


class ComputationStatus(str, Enum):
    REAL_CLASSICAL = "real_classical_simulation"
    REAL_QUANTUM_HARDWARE = "real_quantum_hardware"
    REAL_QUANTUM_SIMULATOR = "real_quantum_simulator"
    MOCK_ONLY = "mock_only"
    NOT_CONFIGURED = "not_configured"
    FAILED = "failed"


class BackendType(str, Enum):
    CLASSICAL_RDKit = "rdkit_docking_mock_removed"
    CLASSICAL_OPENMM = "openmm"
    QISKIT_AER = "qiskit_aer_simulator"
    QISKIT_IBM = "ibm_quantum_hardware"
    PENNYLANE = "pennylane"
    NONE = "none"


@dataclass
class ReproducibilityEnvelope:
    backend: BackendType
    status: ComputationStatus
    device: str
    provider: str
    qubits: Optional[int]
    shots: Optional[int]
    noise_model: Optional[str]
    seed: Optional[int]
    elapsed_seconds: Optional[float]
    cost_usd: Optional[float]
    commit_hash: str
    environment: str
    raw_result_hash: Optional[str]


@dataclass
class ResearchHypothesis:
    """A source-link scaffold, not a cure, score, ranking, or computed result."""
    compound_id: str
    target_gene: str
    disease_context: str
    computation_status: ComputationStatus
    reproducibility: ReproducibilityEnvelope
    evidence_links: List[str]
    limitations: List[str]
    classical_baseline_score: Optional[float] = None
    quantum_score: Optional[float] = None
    improvement_over_baseline: Optional[float] = None
    warning: str = (
        "Research hypothesis scaffold only. No computation was executed. "
        "Not a treatment recommendation or diagnosis; human review required."
    )

    def to_evidence_record(self) -> dict[str, object]:
        computation_executed = self.computation_status in {
            ComputationStatus.REAL_CLASSICAL,
            ComputationStatus.REAL_QUANTUM_HARDWARE,
            ComputationStatus.REAL_QUANTUM_SIMULATOR,
        }
        return {
            "entity_type": "research_hypothesis",
            "compound": self.compound_id,
            "target": self.target_gene,
            "disease_context": self.disease_context,
            "status": self.computation_status.value,
            "computation_executed": computation_executed,
            "score_available": any(
                score is not None
                for score in (
                    self.classical_baseline_score,
                    self.quantum_score,
                    self.improvement_over_baseline,
                )
            ),
            "is_cure_claim": False,
            "is_ranking": False,
            "reproducibility": asdict(self.reproducibility),
            "requires_human_review": True,
        }


class QuantumResearchSandboxFixed:
    """Generate bounded research links without claiming to run a solver.

    Qiskit/PennyLane package presence alone is not sufficient to claim a simulation.
    A genuine solver, explicit molecular problem construction, and evaluation against
    a classical baseline must be implemented before computation statuses can change.
    """

    MAX_COMPOUNDS = 10

    def __init__(self) -> None:
        self.has_qiskit = self._check_qiskit()
        self.has_pennylane = self._check_pennylane()

    @staticmethod
    def _check_qiskit() -> bool:
        try:
            import qiskit  # noqa: F401
            return True
        except ImportError:
            return False

    @staticmethod
    def _check_pennylane() -> bool:
        try:
            import pennylane  # noqa: F401
            return True
        except ImportError:
            return False

    @staticmethod
    def _required_label(name: str, value: str, max_length: int) -> str:
        if not isinstance(value, str):
            raise ValueError(f"{name} must be a string")
        normalized = value.strip()
        if not normalized or len(normalized) > max_length:
            raise ValueError(f"{name} must be non-empty and at most {max_length} characters")
        return normalized

    def generate_hypotheses(
        self,
        disease: str,
        gene: str,
        compounds: List[str],
        classical_baseline: bool = True,
    ) -> List[ResearchHypothesis]:
        """Return source links only; no VQE, docking, ranking or hardware calls occur."""
        disease_label = self._required_label("disease", disease, 256)
        gene_label = self._required_label("gene", gene, 128)
        if not isinstance(compounds, list):
            raise ValueError("compounds must be a list of compound names or identifiers")
        if len(compounds) > self.MAX_COMPOUNDS:
            raise ValueError(f"at most {self.MAX_COMPOUNDS} compounds may be requested per call")
        if not isinstance(classical_baseline, bool):
            raise ValueError("classical_baseline must be a boolean")
        normalized_compounds = [
            self._required_label(f"compounds[{index}]", compound, 128)
            for index, compound in enumerate(compounds)
        ]
        if not normalized_compounds:
            return []

        commit = (os.getenv("GIT_COMMIT") or "unknown").strip() or "unknown"
        environment = (
            f"qiskit_installed={self.has_qiskit}; "
            f"pennylane_installed={self.has_pennylane}; "
            "execution_adapter=not_implemented"
        )
        results: List[ResearchHypothesis] = []
        for compound in normalized_compounds:
            reproducibility = ReproducibilityEnvelope(
                backend=BackendType.NONE,
                status=ComputationStatus.NOT_CONFIGURED,
                device="not_configured",
                provider="none",
                qubits=None,
                shots=None,
                noise_model=None,
                seed=None,
                elapsed_seconds=None,
                cost_usd=None,
                commit_hash=commit,
                environment=environment,
                raw_result_hash=None,
            )
            limitations = [
                "No molecular Hamiltonian, VQE solver, quantum simulation, docking run, or hardware job was executed.",
                "No classical baseline was computed; this module emits no scientific scores or rankings.",
                "Quantum advantage is not demonstrated and experimental validation has not been performed.",
                "Research discovery only; human review required.",
            ]
            if not classical_baseline:
                limitations.append("The caller explicitly disabled a classical baseline request.")
            results.append(
                ResearchHypothesis(
                    compound_id=compound,
                    target_gene=gene_label,
                    disease_context=disease_label,
                    computation_status=ComputationStatus.NOT_CONFIGURED,
                    reproducibility=reproducibility,
                    evidence_links=[
                        f"https://pubchem.ncbi.nlm.nih.gov/#query={quote(compound, safe='')}",
                        f"https://www.ncbi.nlm.nih.gov/gene/?{urlencode({'term': gene_label})}",
                    ],
                    limitations=limitations,
                )
            )
        return results


# Backward compatibility: these aliases are research scaffolds, not cure engines.
QuantumCureEngine = QuantumResearchSandboxFixed
QuantumRubiksCureEngine = QuantumResearchSandboxFixed
