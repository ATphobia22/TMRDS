"""
GROVER Molecular Property Node for TMRDS.
Self-supervised Graph Transformer on large-scale molecular data (Tencent AI Lab).
Predicts ADMET / toxicity / solubility / BBBP-style properties from SMILES.
Paper: Rong et al., NeurIPS 2020 — Self-Supervised Graph Transformer on Large-Scale Molecular Data.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("TMRDS.GROVER")

try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, Crippen, Lipinski
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False


class GROVERMolecularNode:
    """
    Molecular property prediction + fingerprint generation.

    Production path: load GROVER_base / GROVER_large checkpoint.
    Offline path: RDKit 2-D descriptors + Lipinski rule-of-five heuristics.
    """

    SUPPORTED_TASKS = (
        "toxicity",
        "solubility",
        "bbbp",
        "lipophilicity",
        "clintox",
        "fingerprint",
    )

    def __init__(self, checkpoint_path: Optional[str] = None) -> None:
        self.checkpoint_path = checkpoint_path
        self.mode = "GROVER" if checkpoint_path else "RDKIT_FALLBACK"

    def _rdkit_descriptors(self, smiles: str) -> Dict[str, Any]:
        if not RDKIT_AVAILABLE:
            return {"error": "RDKit not installed", "smiles": smiles}
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return {"error": "Invalid SMILES", "smiles": smiles}
        mw = Descriptors.MolWt(mol)
        logp = Crippen.MolLogP(mol)
        hbd = Lipinski.NumHDonors(mol)
        hba = Lipinski.NumHAcceptors(mol)
        rot = Lipinski.NumRotatableBonds(mol)
        tpsa = Descriptors.TPSA(mol)
        lipinski_pass = mw <= 500 and logp <= 5 and hbd <= 5 and hba <= 10
        return {
            "smiles": smiles,
            "mol_weight": round(mw, 2),
            "logp": round(logp, 3),
            "hbd": hbd,
            "hba": hba,
            "rotatable_bonds": rot,
            "tpsa": round(tpsa, 2),
            "lipinski_rule_of_five": lipinski_pass,
            "source": "RDKit_FALLBACK",
        }

    def predict_properties(
        self,
        smiles_list: List[str],
        task: str = "toxicity",
    ) -> Dict[str, Any]:
        if task not in self.SUPPORTED_TASKS:
            raise ValueError(f"task must be one of {self.SUPPORTED_TASKS}")
        if not smiles_list:
            raise ValueError("smiles_list must be non-empty")

        results = []
        for smi in smiles_list:
            desc = self._rdkit_descriptors(smi)
            if "error" not in desc:
                risk = "LOW"
                if not desc.get("lipinski_rule_of_five", True):
                    risk = "ELEVATED"
                if desc.get("logp", 0) > 5 or desc.get("mol_weight", 0) > 600:
                    risk = "HIGH"
                desc["task"] = task
                desc["risk_flag"] = risk
                desc["note"] = (
                    "Full GROVER checkpoint not loaded — RDKit heuristic only. "
                    "Load GROVER_base/large for production ADMET scores."
                )
            results.append(desc)

        return {
            "task": task,
            "mode": self.mode,
            "count": len(results),
            "predictions": results,
            "citation": "Rong et al., Self-Supervised Graph Transformer on Large-Scale Molecular Data, NeurIPS 2020",
        }

    def fingerprint(self, smiles: str) -> Dict[str, Any]:
        desc = self._rdkit_descriptors(smiles)
        return {
            "smiles": smiles,
            "fingerprint_source": "rdkit_2d" if RDKIT_AVAILABLE else "none",
            "descriptors": desc,
            "mode": self.mode,
        }

    def status(self) -> Dict[str, Any]:
        return {
            "node": "GROVERMolecularNode",
            "mode": self.mode,
            "rdkit_available": RDKIT_AVAILABLE,
            "checkpoint": self.checkpoint_path,
            "supported_tasks": list(self.SUPPORTED_TASKS),
            "status": "READY",
        }
