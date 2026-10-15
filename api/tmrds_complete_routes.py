"""TMRDS Quantum Rubik's Cube — complete facet routes (cleaned integration).

Phases:
- Structure facet: live AlphaFold DB via engines.alphafold3_node (fail-closed).
- Quantum facet: live IBM Quantum backends via engines.ibm_quantum_compute
  (fail-closed without IBM_QUANTUM_API_KEY + IBM_QUANTUM_INSTANCE_CRN);
  VQE execution is honest about what ran — simulators only when their
  libraries are installed, hardware only through the governed submission
  flow. Nothing is ever labeled as hardware execution unless IBM ran it.

Research discovery only. Not SaMD. Human clinical authority remains final.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(tags=["TMRDS Quantum Rubik's Cube"])

IBM_API_VERSION_ENV = "IBM_QUANTUM_API_VERSION"
IBM_API_VERSION_DEFAULT = "2025-08-15"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobStatus(str, Enum):
    RUNNING = "Running"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"
    FAILED = "Failed"
    DRY_RUN = "dry_run"
    MOCK_ONLY = "mock_only"
    NOT_EXECUTED = "not_executed"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class StructureRequest(BaseModel):
    uniprot_id: Optional[str] = Field(None, examples=["P04637"])
    gene_symbol: Optional[str] = None
    disease_context: Optional[str] = None


class QuantumVQE_Request(BaseModel):
    molecule: str = Field("H2", description="H2 only for the local simulator path")
    provider: str = Field("qiskit-aer", description="qiskit-aer (simulator) or ibm_quantum (hardware, governed)")
    backend_name: Optional[str] = Field(None, description="e.g. ibm_kingston; hardware only")
    shots: int = Field(1024, ge=1, le=100000)
    dry_run: bool = Field(True, description="True = cost preview only, never billed")


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@router.get("/health", summary="TMRDS facet health")
def health(
    ibm_api_version: Optional[str] = Header(None, alias="IBM-API-Version"),
):
    return {
        "service": "TMRDS Quantum Rubik's Cube facets",
        "facets": {
            "structure": "live AlphaFold DB via engines.alphafold3_node.fetch_live_alphafold_db",
            "quantum_backends": "live IBM Quantum via engines.ibm_quantum_compute (credentials required)",
            "quantum_vqe": "simulator only when qiskit-aer installed; hardware via governed flow only",
            "federated_search": "live via engines.federated_evidence_search (Europe PMC, PubMed, trials, openFDA, arXiv, OpenAlex)",
        },
        "ibm_api_version": ibm_api_version or IBM_API_VERSION_DEFAULT,
        "governance": {
            "research_advisory": True,
            "human_authority_final": True,
            "not_samd": True,
            "no_mock_records": True,
        },
    }


# ---------------------------------------------------------------------------
# Structure facet — live AlphaFold DB
# ---------------------------------------------------------------------------

@router.post("/structure/predict", summary="Structure facet — live AlphaFold DB")
def predict_structure(req: StructureRequest):
    """Fetch real AlphaFold DB metadata. Unknown IDs and network failures
    return explicit unavailable states with null metrics — never fabricated."""
    if not req.uniprot_id:
        raise HTTPException(status_code=400, detail="uniprot_id is required (e.g. P04637)")
    from engines.alphafold3_node import AlphaFold3Node
    node = AlphaFold3Node()
    result = node.fetch_live_alphafold_db(req.uniprot_id)
    return {
        **result,
        "gene_symbol": req.gene_symbol,
        "disease_context": req.disease_context,
        "retrieved_at": _utcnow(),
        "evidence_class": "predicted" if result["status"] == "REAL_PREDICTED" else result["status"].lower(),
    }


# ---------------------------------------------------------------------------
# Quantum facet — live IBM backends (fail-closed)
# ---------------------------------------------------------------------------

def _ibm_client():
    from engines.ibm_quantum_compute import IBMQuantumComputeClient, IBMQuantumError
    try:
        return IBMQuantumComputeClient.from_environment()
    except ValueError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"IBM Quantum not configured: {exc}. Set IBM_QUANTUM_API_KEY and IBM_QUANTUM_INSTANCE_CRN.",
        )


@router.get("/quantum/backends", summary="List IBM Quantum backends (live, credentials required)")
def list_backends(ibm_api_version: Optional[str] = Header(None, alias="IBM-API-Version")):
    """Live backend list via the IBM Quantum REST client. No mock fallback:
    without credentials this returns 503, never invented backends."""
    from engines.ibm_quantum_compute import IBMQuantumError
    client = _ibm_client()
    try:
        payload = client.list_backends()
    except IBMQuantumError as exc:
        raise HTTPException(status_code=502, detail=f"IBM Quantum request failed: {exc}")
    finally:
        client.close()
    backends = payload.get("backends") if isinstance(payload, dict) else payload
    return {
        "backends": backends or [],
        "ibm_api_version": ibm_api_version or IBM_API_VERSION_DEFAULT,
        "total_count": len(backends or []),
        "timestamp": _utcnow(),
        "source": "live IBM Quantum REST",
    }


@router.post("/quantum/vqe", summary="Quantum VQE — honest execution states")
def quantum_vqe(req: QuantumVQE_Request):
    """VQE with honest execution labeling.

    - dry_run=True (default): cost/preview only, nothing billed, nothing executed.
    - provider=qiskit-aer: runs only if qiskit-aer is installed; labeled simulator.
    - provider=ibm_quantum: hardware execution is NOT performed inline; returns
      501 pointing at the governed submission flow (ledger + reconciler).
    A classical computation is never labeled as quantum hardware execution.
    """
    if req.molecule != "H2":
        raise HTTPException(status_code=400, detail="Local simulator path supports H2 only; hardware via governed flow.")
    if req.dry_run:
        return {
            "job_id": None,
            "program_id": "vqe",
            "backend": req.backend_name or req.provider,
            "status": JobStatus.DRY_RUN.value,
            "is_simulator": req.provider != "ibm_quantum",
            "is_hardware": False,
            "shots": req.shots,
            "cost_usd": None,
            "result": None,
            "provenance": {
                "molecule": req.molecule,
                "dry_run": True,
                "message": "Preview only. Nothing was executed or billed.",
            },
            "warning": "DRY RUN: set dry_run=false to request execution.",
            "timestamp": _utcnow(),
        }

    if req.provider == "ibm_quantum" or (req.backend_name or "").startswith("ibm_"):
        raise HTTPException(
            status_code=501,
            detail=(
                "Hardware execution is not performed inline. Use the governed flow: "
                "engines/ibm_quantum_job_ledger.py (authorized submission) + "
                "engines/ibm_quantum_reconciler.py (bounded reconciliation). "
                "Requires IBM_QUANTUM_API_KEY, IBM_QUANTUM_INSTANCE_CRN, and explicit authorization."
            ),
        )

    # Local simulator path — only with a real simulator library present.
    try:
        from qiskit_aer import AerSimulator  # noqa: F401
        from qiskit import QuantumCircuit  # noqa: F401
        has_aer = True
    except ImportError:
        has_aer = False
    if not has_aer:
        return {
            "job_id": None,
            "program_id": "vqe",
            "backend": req.provider,
            "status": JobStatus.MOCK_ONLY.value,
            "is_simulator": True,
            "is_hardware": False,
            "shots": req.shots,
            "cost_usd": 0.0,
            "result": None,
            "provenance": {"mock_only": True, "reason": "qiskit-aer not installed"},
            "warning": "MOCK_ONLY: qiskit-aer not installed. No energy fabricated. pip install qiskit-aer",
            "timestamp": _utcnow(),
        }
    # A real Aer VQE would be implemented here; until then, do not invent energies.
    return {
        "job_id": None,
        "program_id": "vqe",
        "backend": "qiskit-aer",
        "status": JobStatus.NOT_EXECUTED.value,
        "is_simulator": True,
        "is_hardware": False,
        "shots": req.shots,
        "cost_usd": 0.0,
        "result": None,
        "provenance": {"simulator_available": True, "note": "qiskit-aer present; VQE driver not yet implemented — no result fabricated"},
        "warning": "NOT_EXECUTED: simulator present but the VQE driver is not implemented. No energy invented.",
        "timestamp": _utcnow(),
    }


# ---------------------------------------------------------------------------
# Structure facet — live AlphaFold DB (GET convenience)
# ---------------------------------------------------------------------------

@router.get("/structure/live", summary="Live AlphaFold DB lookup (GET)")
def structure_live(uniprot_id: str = Query(..., examples=["P04637"])):
    from engines.alphafold3_node import AlphaFold3Node
    node = AlphaFold3Node()
    result = node.fetch_live_alphafold_db(uniprot_id)
    return {**result, "retrieved_at": _utcnow()}
