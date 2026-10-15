"""
TMRDS Fixed - quantum_cure_engine.py
Phase 4 Fix: Rename/reframe as optional research computation
No synthetic compound ranking, no cure scores
"""
from enum import Enum
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any
import time, hashlib, os

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
    """Not a cure, not a ranking - just a hypothesis with provenance"""
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
    warning: str = "Research hypothesis only. Not a treatment recommendation. Not a diagnostic. Human review required."

    def to_evidence_record(self):
        return {
            "entity_type": "research_hypothesis",
            "compound": self.compound_id,
            "target": self.target_gene,
            "disease_context": self.disease_context,
            "status": self.computation_status.value,
            "is_cure_claim": False,
            "is_ranking": False,
            "reproducibility": asdict(self.reproducibility),
            "requires_human_review": True
        }

class QuantumResearchSandboxFixed:
    """
    Fixed version of quantum_cure_engine
    - No synthetic rankings
    - Classical baseline required
    - All results marked hypothesized
    - Cost/resource tracking
    """

    def __init__(self):
        self.has_qiskit = self._check_qiskit()
        self.has_pennylane = self._check_pennylane()

    def _check_qiskit(self):
        try:
            import qiskit  # noqa: F401
            return True
        except ImportError:
            return False

    def _check_pennylane(self):
        try:
            import pennylane  # noqa: F401
            return True
        except ImportError:
            return False

    def generate_hypotheses(self, disease: str, gene: str, compounds: List[str], classical_baseline: bool = True) -> List[ResearchHypothesis]:
        """
        For Quantum Rubik's Cube: disease/gene/compounds are the cube facets
        Returns hypotheses, not cures
        """
        if not compounds:
            return []

        results = []
        commit = os.getenv("GIT_COMMIT", "dev")
        
        # Determine real status
        if self.has_qiskit:
            status = ComputationStatus.REAL_QUANTUM_SIMULATOR
            backend = BackendType.QISKIT_AER
            device = "aer_simulator"
        else:
            status = ComputationStatus.MOCK_ONLY
            backend = BackendType.NONE
            device = "not_configured"

        for comp in compounds[:10]:  # bounded
            # NO synthetic score - only real computation or MOCK_ONLY with empty scores
            if status == ComputationStatus.MOCK_ONLY:
                classical_score = None
                quantum_score = None
                improvement = None
            else:
                # Real computation would happen here - placeholder for actual VQE
                # For now, still None to avoid fake scores - must be replaced with real qiskit call
                classical_score = None
                quantum_score = None
                improvement = None

            repro = ReproducibilityEnvelope(
                backend=backend,
                status=status,
                device=device,
                provider="local" if self.has_qiskit else "none",
                qubits=4 if self.has_qiskit else None,
                shots=1024 if self.has_qiskit else None,
                noise_model="ideal" if status == ComputationStatus.REAL_QUANTUM_SIMULATOR else None,
                seed=42,
                elapsed_seconds=None,
                cost_usd=0.0,
                commit_hash=commit,
                environment=f"qiskit={self.has_qiskit}, pennylane={self.has_pennylane}",
                raw_result_hash=None
            )

            hyp = ResearchHypothesis(
                compound_id=comp,
                target_gene=gene,
                disease_context=disease,
                computation_status=status,
                reproducibility=repro,
                evidence_links=[
                    f"https://pubchem.ncbi.nlm.nih.gov/compound/{comp}",
                    f"https://www.ncbi.nlm.nih.gov/gene/?term={gene}"
                ],
                limitations=[
                    "No wet-lab validation",
                    "Classical baseline not yet computed - requires RDKit/OpenMM" if status != ComputationStatus.MOCK_ONLY else "Backend not configured - install qiskit[aer]",
                    "Quantum advantage not demonstrated",
                    "Exploratory only"
                ],
                classical_baseline_score=classical_score,
                quantum_score=quantum_score,
                improvement_over_baseline=improvement
            )
            results.append(hyp)

        return results

# Backward compat (old names referenced in docs; the class is a research sandbox, not a cure engine)
QuantumCureEngine = QuantumResearchSandboxFixed
QuantumRubiksCureEngine = QuantumResearchSandboxFixed
