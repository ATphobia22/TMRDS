"""
AlphaFold3 Structure Node for TMRDS.
Predicts biomolecular structures (proteins, ligands, DNA/RNA complexes)
and supports structure-guided molecular target validation / docking workflows.

Official: google-deepmind/alphafold3 (academic weights via request)
Open alternatives: OpenFold3, Ligo-Biosciences/AlphaFold3
Cloud: Google Cloud Model Garden / AlphaFold Server
"""
from __future__ import annotations

import logging
import math
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("TMRDS.AlphaFold3")


class AlphaFold3Node:
    """
    Molecular structure prediction & target-validation node.

    Capabilities (when backend available):
      - Protein monomer / multimer folding
      - Protein–ligand co-folding (SMILES or CCD)
      - Protein–DNA / RNA complexes
      - Confidence metrics (pLDDT, PAE, ipTM)

    Molecular docking note:
      AF3 co-folding can act as a screening engine or post-docking filter.
      Conventional physics docking (DOCK3, AutoDock Vina) remains complementary.
      AF3 is strongest when used to re-rank or refine poses, not as sole screener.
    """

    SUPPORTED_BACKENDs = ("mock", "alphafold_server", "openfold3", "local_af3")

    def __init__(self, backend: str = "mock") -> None:
        if backend not in self.SUPPORTED_BACKENDs:
            raise ValueError(f"backend must be one of {self.SUPPORTED_BACKENDs}")
        self.backend = backend
        self.safety_note = (
            "Structure predictions are research tools. "
            "Experimental validation is required before clinical or therapeutic use."
        )

    def predict_structure(
        self,
        sequence: str,
        ligand_smiles: Optional[str] = None,
        job_name: str = "tmrds_af3",
    ) -> Dict[str, Any]:
        sequence = self._validate_sequence(sequence)
        if not isinstance(job_name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", job_name):
            raise ValueError("job_name must be 1-128 safe ASCII letters, digits, dots, underscores, or hyphens")
        if ligand_smiles is not None:
            if not isinstance(ligand_smiles, str) or not ligand_smiles.strip() or len(ligand_smiles) > 4096:
                raise ValueError("ligand_smiles must be non-empty and at most 4096 characters")
            if any(ord(character) < 32 for character in ligand_smiles):
                raise ValueError("ligand_smiles must not contain control characters")

        if self.backend == "mock":
            return self._mock_prediction(sequence, ligand_smiles, job_name)

        logger.info(
            "AF3 backend requested but adapter is not implemented: backend=%s len=%d ligand=%s",
            self.backend,
            len(sequence),
            bool(ligand_smiles),
        )
        return {
            "job_name": job_name,
            "backend": self.backend,
            "status": "NOT_CONFIGURED",
            "job_id": None,
            "message": (
                "No prediction was submitted: this backend is a configuration placeholder "
                "until a real adapter is implemented and verified."
            ),
            "sequence_length": len(sequence),
            "ligand_provided": ligand_smiles is not None,
            "metrics": None,
            "structure_uri": None,
            "safety_note": self.safety_note,
        }

    def _mock_prediction(
        self,
        sequence: str,
        ligand_smiles: Optional[str],
        job_name: str,
    ) -> Dict[str, Any]:
        """Return a schema-shaped placeholder without fabricating scientific results."""
        return {
            "job_name": job_name,
            "backend": "mock",
            "status": "MOCK_ONLY",
            "sequence_length": len(sequence),
            "ligand_provided": ligand_smiles is not None,
            "metrics": None,
            "structure_format": None,
            "structure_uri": None,
            "docking_context": None,
            "message": "Mock mode does not run AlphaFold, generate a structure, or calculate confidence metrics.",
            "safety_note": self.safety_note,
        }

    def validate_target(
        self,
        sequence: str,
        candidate_smiles: List[str],
        top_k: int = 5,
    ) -> Dict[str, Any]:
        self._validate_sequence(sequence)
        if not isinstance(candidate_smiles, list) or not candidate_smiles:
            raise ValueError("candidate_smiles must be a non-empty list")
        if len(candidate_smiles) > 1000:
            raise ValueError("candidate_smiles must contain at most 1000 entries")
        for index, smiles in enumerate(candidate_smiles):
            if not isinstance(smiles, str) or not smiles.strip() or len(smiles) > 4096:
                raise ValueError(f"candidate_smiles[{index}] must be non-empty and at most 4096 characters")
            if any(ord(character) < 32 for character in smiles):
                raise ValueError(f"candidate_smiles[{index}] must not contain control characters")
        if isinstance(top_k, bool) or not isinstance(top_k, int) or not 1 <= top_k <= 1000:
            raise ValueError("top_k must be an integer from 1 through 1000")
        return {
            "target_length": len(sequence),
            "candidates_evaluated": len(candidate_smiles),
            "top_k": [],
            "method": "mock_unavailable",
            "status": "NO_RANKING_PERFORMED",
            "message": "Mock mode does not score, rank, or predict properties for compounds.",
            "safety_note": self.safety_note,
        }

    def fetch_live_alphafold_db(self, uniprot_id: str, timeout: float = 20.0) -> Dict[str, Any]:
        """Fetch validated AlphaFold DB metadata for a UniProt accession.

        Only upstream metadata is returned. Invalid accessions, unsafe redirects,
        malformed payloads, and invalid confidence values fail closed.
        """
        import re
        import requests

        if not isinstance(uniprot_id, str):
            raise ValueError("uniprot_id must be a string")
        uid = uniprot_id.strip().upper()
        if not re.fullmatch(r"(?:[A-Z0-9]{6}|[A-Z0-9]{10})(?:-[1-9][0-9]*)?", uid):
            raise ValueError("uniprot_id must be a valid-looking six- or ten-character accession with optional isoform suffix")
        timeout_value = self._validate_timeout(timeout)
        url = f"https://alphafold.ebi.ac.uk/api/prediction/{uid}"
        try:
            response = requests.get(
                url,
                headers={"Accept": "application/json"},
                timeout=timeout_value,
                allow_redirects=False,
            )
            status_code = getattr(response, "status_code", 0)
            if status_code == 404:
                return {
                    "backend": "alphafold_db",
                    "status": "NOT_FOUND",
                    "uniprot_id": uid,
                    "metrics": None,
                    "message": "No AlphaFold DB entry for this accession.",
                }
            if not isinstance(status_code, int) or not 200 <= status_code < 300:
                return {
                    "backend": "alphafold_db",
                    "status": "UNAVAILABLE",
                    "uniprot_id": uid,
                    "metrics": None,
                    "message": f"AlphaFold DB returned HTTP {status_code}.",
                }
            data = response.json()
        except Exception as exc:  # noqa: BLE001 — fail closed, never expose request internals
            logger.warning("AlphaFold DB lookup failed (%s)", type(exc).__name__)
            return {
                "backend": "alphafold_db",
                "status": "UNAVAILABLE",
                "uniprot_id": uid,
                "metrics": None,
                "message": f"AlphaFold DB request failed ({type(exc).__name__}).",
            }

        if isinstance(data, list):
            entry = data[0] if data and isinstance(data[0], dict) else None
        else:
            entry = data if isinstance(data, dict) else None
        if entry is None:
            return {
                "backend": "alphafold_db",
                "status": "INVALID_RESPONSE",
                "uniprot_id": uid,
                "metrics": None,
                "message": "AlphaFold DB returned an unexpected response shape.",
            }

        mean_plddt = entry.get("globalMetricValue")
        valid_plddt = (
            isinstance(mean_plddt, (int, float))
            and not isinstance(mean_plddt, bool)
            and math.isfinite(float(mean_plddt))
            and 0.0 <= float(mean_plddt) <= 100.0
        )
        safe_pdb_url = self._safe_asset_url(entry.get("pdbUrl"))
        safe_cif_url = self._safe_asset_url(entry.get("cifUrl"))
        safe_pae_url = self._safe_asset_url(entry.get("paeDocUrl"))
        return {
            "backend": "alphafold_db",
            "status": "REAL_PREDICTION_CONFIDENCE_AVAILABLE" if valid_plddt else "REAL_PREDICTION_CONFIDENCE_UNAVAILABLE",
            "uniprot_id": uid,
            "gene": entry.get("gene") if isinstance(entry.get("gene"), str) else None,
            "pdb_url": safe_pdb_url,
            "cif_url": safe_cif_url,
            "pae_url": safe_pae_url,
            "metrics": {"mean_plddt": float(mean_plddt)} if valid_plddt else None,
            "model_version": entry.get("latestVersion"),
            "source_url": url,
            "license": "CC-BY-4.0",
            "message": "Predicted-structure confidence only; not a clinical or efficacy measure.",
            "safety_note": self.safety_note,
        }

    def status(self) -> Dict[str, Any]:
        configured = False  # No prediction backend adapter is implemented in this node.
        return {
            "node": "AlphaFold3Node",
            "backend": self.backend,
            "supported_backends": list(self.SUPPORTED_BACKENDs),
            "declared_capabilities": [
                "protein_folding",
                "protein_ligand_cofolding",
                "multimer",
                "structure_guided_ranking",
            ],
            "available_capabilities": [],
            "status": "MOCK_ONLY" if self.backend == "mock" else "NOT_CONFIGURED",
            "prediction_execution_available": configured,
            "confidence_metrics_available": False,
            "structure_artifact_available": False,
        }
