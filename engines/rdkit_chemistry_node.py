"""
RDKit Chemistry Node for TMRDS.
Molecule construction, descriptors, conformer generation, and Lipinski filtering.
Drawn from quantum-chem-skills / rdkit-chemistry patterns.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger("TMRDS.RDKit")

try:
    from rdkit import Chem
    from rdkit.Chem import AllChem, Descriptors, Crippen, Lipinski, QED
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False


class RDKitChemistryNode:
    """Canonical molecular utilities for the precision-medicine pipeline."""

    def __init__(self) -> None:
        if not RDKIT_AVAILABLE:
            logger.warning("RDKit not installed — node will return structured errors")

    def validate_smiles(self, smiles: str) -> Dict[str, Any]:
        if not RDKIT_AVAILABLE:
            return {"valid": False, "error": "RDKit not installed"}
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return {"valid": False, "smiles": smiles, "error": "Invalid SMILES"}
        canonical = Chem.MolToSmiles(mol, canonical=True)
        return {"valid": True, "smiles": smiles, "canonical": canonical}

    def descriptors(self, smiles: str) -> Dict[str, Any]:
        if not RDKIT_AVAILABLE:
            return {"error": "RDKit not installed"}
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return {"error": "Invalid SMILES", "smiles": smiles}
        return {
            "smiles": smiles,
            "canonical": Chem.MolToSmiles(mol, canonical=True),
            "mol_weight": round(Descriptors.MolWt(mol), 2),
            "logp": round(Crippen.MolLogP(mol), 3),
            "hbd": Lipinski.NumHDonors(mol),
            "hba": Lipinski.NumHAcceptors(mol),
            "rotatable_bonds": Lipinski.NumRotatableBonds(mol),
            "tpsa": round(Descriptors.TPSA(mol), 2),
            "qed": round(QED.qed(mol), 3),
            "lipinski_pass": (
                Descriptors.MolWt(mol) <= 500
                and Crippen.MolLogP(mol) <= 5
                and Lipinski.NumHDonors(mol) <= 5
                and Lipinski.NumHAcceptors(mol) <= 10
            ),
        }

    def generate_conformers(
        self,
        smiles: str,
        num_confs: int = 5,
        seed: int = 42,
    ) -> Dict[str, Any]:
        if not RDKIT_AVAILABLE:
            return {"error": "RDKit not installed"}
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return {"error": "Invalid SMILES"}
        mol = Chem.AddHs(mol)
        conf_ids = AllChem.EmbedMultipleConfs(
            mol, numConfs=num_confs, randomSeed=seed, pruneRmsThresh=0.5
        )
        energies = []
        for cid in conf_ids:
            AllChem.UFFOptimizeMolecule(mol, confId=cid)
            ff = AllChem.UFFGetMoleculeForceField(mol, confId=cid)
            energies.append(round(ff.CalcEnergy(), 4) if ff else None)
        return {
            "smiles": smiles,
            "num_conformers": len(conf_ids),
            "energies_kcal": energies,
            "status": "CONFORMERS_GENERATED",
        }

    def filter_druglike(self, smiles_list: List[str]) -> Dict[str, Any]:
        passed, failed = [], []
        for smi in smiles_list:
            d = self.descriptors(smi)
            if d.get("lipinski_pass"):
                passed.append(d)
            else:
                failed.append(d)
        return {
            "input_count": len(smiles_list),
            "passed": len(passed),
            "failed": len(failed),
            "passed_molecules": passed,
            "failed_molecules": failed,
        }

    def status(self) -> Dict[str, Any]:
        return {
            "node": "RDKitChemistryNode",
            "rdkit_available": RDKIT_AVAILABLE,
            "status": "READY" if RDKIT_AVAILABLE else "DEGRADED",
        }
