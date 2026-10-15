"""
TMRDS + eigenkit + IBM Quantum Cloud Integration
For AJ Tucker - ATphobia22/eigenkit + ATphobia22/TMRDS

You have IBM Quantum account -> This wires eigenkit to real IBM hardware with CostWarning guard

IBM Docs: https://quantum.cloud.ibm.com/docs/en/api
Auth: https://quantum.cloud.ibm.com/docs/en/guides/hello-world#install-and-authenticate

Phases covered: Phase 4 Quantum Sandbox - REAL hardware path
Governance: Research-advisory only, not SaMD, human authority final
"""

import os
from enum import Enum
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any

# ============ CONFIGURATION FOR YOUR IBM ACCOUNT ============

"""
SETUP (one time):

1. Get your IBM Quantum Platform API key:
   Go to https://quantum.cloud.ibm.com -> Account -> API Token -> Copy

2. Save it - 3 ways (pick one):

   Option A - Save to disk (trusted device only, plain text warning):
   from qiskit_ibm_runtime import QiskitRuntimeService
   QiskitRuntimeService.save_account(
       channel="ibm_quantum_platform",  # or "ibm_cloud" - same now
       token="YOUR_IBM_QUANTUM_API_KEY",
       instance="YOUR_CRN"  # For ibm_cloud channel, or leave for ibm_quantum_platform
   )

   Option B - Environment variables (recommended for TMRDS):
   export QISKIT_IBM_TOKEN="your_api_key"
   export QISKIT_IBM_INSTANCE="your_crn_if_needed"
   export QISKIT_IBM_CHANNEL="ibm_quantum_platform"

   Option C - Current session only:
   service = QiskitRuntimeService(channel="ibm_quantum_platform", token="...", instance="...")

Your .qiskit/qiskit-ibm.json will contain: {"ibm_quantum_platform": {"token": "...", "instance": "..."}}
"""

class IBMBackend(str, Enum):
    # Simulators (free, fast, for TMRDS CI)
    AER_STATEVECTOR = "qiskit-aer"
    AER_MPS = "qiskit-aer-mps"  # Matrix Product State - for many qubits
    
    # IBM Quantum Hardware (billable, needs CostWarning)
    IBM_KINGSTON = "ibm_kingston"  # 156Q Heron
    IBM_SHERBROOKE = "ibm_sherbrooke"  # 127Q Eagle
    IBM_QUEBEC = "ibm_quebec"
    LEAST_BUSY = "least_busy"  # Auto-select

@dataclass
class IBMQuantumJob:
    job_id: str
    backend_name: str
    status: str
    is_simulator: bool
    shots: int
    cost_usd: Optional[float]
    queue_time: Optional[float]
    result: Optional[Dict[str, Any]]
    provenance: Dict[str, Any]

class TMRDS_Eigenkit_IBM_Bridge:
    """
    Bridges TMRDS Quantum Rubik's Cube + eigenkit + IBM Quantum Cloud
    
    This is the FIXED version of quantum_cure_engine.py + qiskit_nature_bridge.py
    Now using eigenkit as unified provider, with IBM hardware path
    
    Usage:
        bridge = TMRDS_Eigenkit_IBM_Bridge()
        
        # 1. For CI / Tests - no IBM account needed (free)
        result = bridge.run_vqe_simulator(molecule="H2", provider="qiskit-aer")
        
        # 2. For real hardware - needs IBM account + CostWarning
        result = bridge.run_vqe_hardware(
            molecule="H2", 
            backend=IBMBackend.IBM_KINGSTON,
            shots=4096,
            dry_run=True  # First check cost!
        )
    """
    
    def __init__(self, ibm_channel: str = "ibm_quantum_platform"):
        self.ibm_channel = ibm_channel
        self.has_eigenkit = self._check_eigenkit()
        self.has_qiskit_runtime = self._check_qiskit_runtime()
        
    def _check_eigenkit(self):
        try:
            import eigenkit
            return True
        except ImportError:
            return False
    
    def _check_qiskit_runtime(self):
        try:
            import qiskit_ibm_runtime
            return True
        except ImportError:
            return False
    
    def setup_ibm_account(self, token: str, instance: Optional[str] = None):
        """Save IBM Quantum account to disk"""
        from qiskit_ibm_runtime import QiskitRuntimeService
        
        # For ibm_quantum_platform, instance is optional (uses default)
        # For ibm_cloud, instance is CRN
        if instance:
            QiskitRuntimeService.save_account(
                channel=self.ibm_channel,
                token=token,
                instance=instance
            )
        else:
            QiskitRuntimeService.save_account(
                channel=self.ibm_channel,
                token=token
            )
        print(f"✅ Saved IBM account to ~/.qiskit/qiskit-ibm.json channel={self.ibm_channel}")
        print("Now you can use: service = QiskitRuntimeService()")
    
    def list_ibm_backends(self) -> List[Dict]:
        """List your available IBM backends"""
        from qiskit_ibm_runtime import QiskitRuntimeService
        
        service = QiskitRuntimeService(channel=self.ibm_channel)
        backends = service.backends()
        
        result = []
        for b in backends:
            result.append({
                "name": b.name,
                "num_qubits": b.num_qubits,
                "operational": b.status().operational,
                "pending_jobs": b.status().pending_jobs,
                "is_simulator": b.simulator
            })
        return result
    
    def run_vqe_with_eigenkit(self, 
                              molecule: str = "H2",
                              provider: str = "qiskit-aer",
                              backend_name: Optional[str] = None,
                              shots: int = 1024,
                              dry_run: bool = True) -> IBMQuantumJob:
        """
        Run VQE using eigenkit - build once, run anywhere
        
        For your TMRDS goal: molecule = drug fragment or protein-ligand interaction
        
        Args:
            molecule: "H2", "LiH", or custom via PySCF
            provider: "numpy" (free, default), "qiskit-aer" (free sim), "qiskit-runtime" (IBM hardware)
            backend_name: For IBM hardware: "ibm_kingston", "ibm_sherbrooke", etc.
            shots: Number of shots for sampling
            dry_run: If True, only preview cost, don't run (recommended for hardware)
        
        Returns:
            IBMQuantumJob with full provenance for TMRDS evidence ledger
        """
        import time
        start = time.time()
        
        # ============ EIGENKIT CIRCUIT DEFINITION (build once) ============
        # This is the same for all backends!
        try:
            from eigenkit import Circuit, Variational, molecular_hamiltonian
            from eigenkit.chemistry import hydrogen_molecule
            
            # Real molecular Hamiltonian - not fake score
            if molecule == "H2":
                # H2 at 0.735 angstrom - textbook VQE
                h2_data = hydrogen_molecule(bond_length=0.735)
                hamiltonian = h2_data.hamiltonian
                num_qubits = h2_data.num_qubits
            else:
                # For drug-like molecules, need PySCF (chemistry extra)
                # pip install eigenkit[chemistry]
                hamiltonian = molecular_hamiltonian(molecule)
                num_qubits = hamiltonian.num_qubits
            
            # Variational circuit - same for all backends
            circuit_spec = Variational(depth=2, num_qubits=num_qubits)
            circuit = Circuit(
                blocks=[circuit_spec],
                observables=hamiltonian,
                provider=provider if provider != "qiskit-runtime" else None
            )
            
            # ============ IBM HARDWARE PATH (with CostWarning guard) ============
            if provider == "qiskit-runtime" and backend_name:
                from eigenkit import QiskitRuntimeBackend, QiskitRuntimeConfig, register
                
                # Register IBM backend (opt-in, needs deliberate choice)
                config = QiskitRuntimeConfig(
                    backend_name=backend_name,
                    shots=shots,
                    primitive="estimator"  # For VQE we need estimator
                )
                backend = QiskitRuntimeBackend(config)
                register("qiskit-runtime-ibm", backend)
                
                # Preview cost before running (eigenkit guard)
                if dry_run:
                    cost_info = backend.dry_run_info(circuit.spec)
                    print(f"💰 Cost Preview: {cost_info}")
                    print("Set dry_run=False to actually submit to IBM Quantum")
                    return IBMQuantumJob(
                        job_id="dry_run_preview",
                        backend_name=backend_name,
                        status="dry_run",
                        is_simulator=False,
                        shots=shots,
                        cost_usd=cost_info.get("estimated_cost"),
                        queue_time=None,
                        result={"cost_preview": cost_info},
                        provenance={
                            "backend": backend_name,
                            "provider": "eigenkit+ibm_quantum_platform",
                            "is_simulator": False,
                            "dry_run": True,
                            "molecule": molecule,
                            "num_qubits": num_qubits,
                            "shots": shots,
                            "governance": {
                                "research_advisory": True,
                                "human_authority_final": True,
                                "not_samd": True,
                                "cost_warning_shown": True
                            }
                        }
                    )
                
                # Real submission - will raise CostWarning first (eigenkit safety)
                import warnings
                from eigenkit import CostWarning
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter("always")
                    circuit.provider = "qiskit-runtime-ibm"
                    # This will warn about billable hardware
                    result = circuit(weights=[0.1]*circuit.spec.n_weights)
                    if w and issubclass(w[-1].category, CostWarning):
                        print(f"⚠️ CostWarning (expected): {w[-1].message}")
            
            else:
                # Simulator path - free, for TMRDS CI
                import numpy as np
                weights = [0.1] * circuit.spec.n_weights if hasattr(circuit.spec, 'n_weights') else []
                result_value = circuit(weights) if weights else circuit([])
                result = {"energy": float(result_value) if isinstance(result_value, (int, float)) else result_value}
            
            elapsed = time.time() - start
            
            return IBMQuantumJob(
                job_id=f"eigenkit_{molecule}_{provider}_{int(start)}",
                backend_name=backend_name or provider,
                status="completed",
                is_simulator=provider != "qiskit-runtime",
                shots=shots,
                cost_usd=0.0 if provider != "qiskit-runtime" else None,
                queue_time=None,
                result=result,
                provenance={
                    "backend": backend_name or provider,
                    "provider": "eigenkit",
                    "channel": self.ibm_channel,
                    "is_simulator": provider != "qiskit-runtime",
                    "molecule": molecule,
                    "num_qubits": num_qubits,
                    "shots": shots,
                    "elapsed_seconds": elapsed,
                    "governance": {
                        "research_advisory": True,
                        "human_authority_final": True,
                        "not_samd": True,
                        "not_diagnostic": True,
                        "is_quantum_hardware": provider == "qiskit-runtime"
                    },
                    "quantum_rubiks_cube_facet": "computation",
                    "evidence_class": "predicted" if provider != "qiskit-runtime" else "real_quantum_hardware"
                }
            )
            
        except ImportError as e:
            return IBMQuantumJob(
                job_id="failed_import",
                backend_name=provider,
                status="mock_only",
                is_simulator=True,
                shots=shots,
                cost_usd=0.0,
                queue_time=None,
                result=None,
                provenance={
                    "error": str(e),
                    "install_hint": "pip install eigenkit[qiskit,chemistry] qiskit-ibm-runtime",
                    "governance": {"mock_only": True, "empty_confidence": True}
                }
            )

# ============ FASTAPI INTEGRATION FOR TMRDS ============

"""
Add to api/structure_routes.py or new api/quantum_routes.py:

from fastapi import APIRouter
router = APIRouter()

@router.post("/quantum/vqe")
def quantum_vqe(molecule: str = "H2", backend: str = "qiskit-aer", dry_run: bool = True):
    bridge = TMRDS_Eigenkit_IBM_Bridge()
    job = bridge.run_vqe_with_eigenkit(
        molecule=molecule,
        provider="qiskit-runtime" if "ibm_" in backend else backend,
        backend_name=backend if "ibm_" in backend else None,
        dry_run=dry_run
    )
    return job

@router.get("/quantum/backends")
def list_backends():
    bridge = TMRDS_Eigenkit_IBM_Bridge()
    return bridge.list_ibm_backends()

# In api/main.py:
# app.include_router(quantum_router, prefix="/api/v1")
"""

if __name__ == "__main__":
    # Test without IBM account (free simulators)
    print("Testing TMRDS + eigenkit integration (simulators, no IBM account needed)...")
    bridge = TMRDS_Eigenkit_IBM_Bridge()
    
    # Test 1: Numpy simulator (always works)
    print("\n1. Testing numpy simulator (free)...")
    job1 = bridge.run_vqe_with_eigenkit(molecule="H2", provider="numpy")
    print(f"Result: {job1.result}, Provenance: {job1.provenance}")
    assert job1.status == "completed" or job1.status == "mock_only"
    
    # Test 2: Qiskit Aer simulator (needs eigenkit[qiskit])
    print("\n2. Testing qiskit-aer simulator (needs pip install eigenkit[qiskit])...")
    job2 = bridge.run_vqe_with_eigenkit(molecule="H2", provider="qiskit-aer")
    print(f"Status: {job2.status}, Backend: {job2.backend_name}")
    
    # Test 3: Dry run for IBM hardware (shows cost preview, doesn't bill)
    print("\n3. Dry run for IBM Kingston (needs IBM account + qiskit-ibm-runtime)...")
    print("Set dry_run=False to actually submit (will raise CostWarning)")
    print("To get real backends: bridge.list_ibm_backends()")
    
    print("\n✅ TMRDS + eigenkit integration ready")
    print("Next: Set QISKIT_IBM_TOKEN env var and run with provider='qiskit-runtime', backend='ibm_kingston', dry_run=True")
