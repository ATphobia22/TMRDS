"""
QRNC open-source integration registry — structure, chemistry, trials, KG adapters.

Maps cube faces to public/open medical systems doctors can use for research arrows.
AlphaFold 3 weights are academic-restricted; prefer AFDB metadata + Boltz/OpenFold
for open pipelines. Research-advisory only. Not SaMD.
"""
from __future__ import annotations
from typing import Any, Dict, List

RESEARCH_ADVISORY = {
    "status": "research-advisory",
    "human_authority_final": True,
    "not_samd": True,
}

INTEGRATIONS: List[Dict[str, Any]] = [
    {
        "id": "alphafold_db",
        "name": "AlphaFold Database (EMBL-EBI)",
        "cube_faces": ["structure", "target"],
        "access": "public_api",
        "license_note": "Predicted structures; commercial use of AF3 weights restricted — use AFDB API for metadata",
        "url": "https://alphafold.ebi.ac.uk/",
        "api": "https://alphafold.ebi.ac.uk/api/prediction/{accession}",
        "tmrds": "engines/alphafold_research.py client_implemented",
        "doctor_value": "pLDDT/pAE metadata for known UniProt accessions; not efficacy",
    },
    {
        "id": "alphafold3",
        "name": "AlphaFold 3 (DeepMind)",
        "cube_faces": ["structure", "molecule"],
        "access": "academic_weights_request",
        "license_note": "Source public; weights terms + prohibited-use policy — not unrestricted commercial",
        "url": "https://github.com/google-deepmind/alphafold3",
        "tmrds": "optional_heavy_extra_only; mock must return MOCK_ONLY with no invented metrics",
        "doctor_value": "Complex/ligand structure hypothesis when legally runnable",
    },
    {
        "id": "boltz2",
        "name": "Boltz-2 / Boltz API",
        "cube_faces": ["structure", "molecule"],
        "access": "open_source_mit_plus_api",
        "license_note": "MIT open models; commercial API available",
        "url": "https://github.com/jwohlwend/boltz",
        "tmrds": "preferred_open_alternative_to_af3_for_complexes",
        "doctor_value": "Structure + affinity research hypotheses; validate experimentally",
    },
    {
        "id": "esmfold",
        "name": "ESMFold / ESM protein LMs",
        "cube_faces": ["structure", "target"],
        "access": "open_source_mit",
        "license_note": "MIT",
        "url": "https://github.com/facebookresearch/ESM",
        "tmrds": "fast_single_sequence_structure_optional",
        "doctor_value": "Rapid single-chain fold when MSA unavailable",
    },
    {
        "id": "open_targets",
        "name": "Open Targets Platform",
        "cube_faces": ["target", "disease", "trials"],
        "access": "public_api",
        "url": "https://platform.opentargets.org/",
        "tmrds": "catalog_target_validation_evidence",
        "doctor_value": "Genetic and literature evidence for target–disease links",
    },
    {
        "id": "chembl",
        "name": "ChEMBL",
        "cube_faces": ["molecule", "target", "trials"],
        "access": "public_api",
        "url": "https://www.ebi.ac.uk/chembl/",
        "tmrds": "bioactivity_and_mechanism_lookup",
        "doctor_value": "Bioactivity, targets, clinical candidate status",
    },
    {
        "id": "string_db",
        "name": "STRING PPI",
        "cube_faces": ["target"],
        "access": "public_api",
        "url": "https://string-db.org/",
        "tmrds": "ppi_adjacency_source_for_quantum_walk",
        "doctor_value": "Interactome edges for gene prioritization graphs",
    },
    {
        "id": "reactome",
        "name": "Reactome pathways",
        "cube_faces": ["target", "disease"],
        "access": "public_api",
        "url": "https://reactome.org/",
        "tmrds": "pathway_context_for_arrows",
        "doctor_value": "Pathway context around prioritized genes",
    },
    {
        "id": "clinicaltrials_gov",
        "name": "ClinicalTrials.gov API",
        "cube_faces": ["trials", "disease"],
        "access": "public_api",
        "url": "https://clinicaltrials.gov/",
        "tmrds": "registry_status_arrows",
        "doctor_value": "Live trial status — not efficacy proof",
    },
    {
        "id": "openfda",
        "name": "openFDA",
        "cube_faces": ["trials", "molecule"],
        "access": "public_api",
        "url": "https://open.fda.gov/",
        "tmrds": "label_and_safety_metadata",
        "doctor_value": "Label and adverse-event research context",
    },
    {
        "id": "omop_ohdsi",
        "name": "OMOP CDM / OHDSI",
        "cube_faces": ["disease", "equity"],
        "access": "vocabulary_and_tools",
        "url": "https://www.ohdsi.org/",
        "tmrds": "engines/omop_cdm_bridge.py",
        "doctor_value": "Standardized concepts for multi-site research",
    },
    {
        "id": "monarch",
        "name": "Monarch Initiative",
        "cube_faces": ["disease", "target"],
        "access": "public_api",
        "url": "https://monarchinitiative.org/",
        "tmrds": "phenotype_gene_disease_graph",
        "doctor_value": "Phenotype–gene–disease associations",
    },
    {
        "id": "uniprot",
        "name": "UniProt",
        "cube_faces": ["structure", "target"],
        "access": "public_api",
        "url": "https://www.uniprot.org/",
        "tmrds": "accession_resolution_for_afdb",
        "doctor_value": "Canonical protein accessions and function",
    },
    {
        "id": "translator",
        "name": "NIH Biomedical Data Translator",
        "cube_faces": ["disease", "target", "molecule"],
        "access": "open_source_federated_kg",
        "url": "https://ncats.nih.gov/translator",
        "tmrds": "federated_hypothesis_paths",
        "doctor_value": "Multi-source reasoning paths with provenance",
    },
]


def catalog() -> Dict[str, Any]:
    return {
        **RESEARCH_ADVISORY,
        "count": len(INTEGRATIONS),
        "integrations": INTEGRATIONS,
        "qrnc_wiring_priority": [
            "alphafold_db (live metadata)",
            "string_db (PPI for CTQW)",
            "open_targets + chembl (target/molecule arrows)",
            "clinicaltrials_gov + openfda (registry arrows)",
            "boltz2 optional structure extra",
            "alphafold3 only behind academic license gate",
        ],
        "disclaimer": (
            "Integrations support research arrows only. Structure scores and graph ranks "
            "are not clinical endpoints. Human authority final."
        ),
    }


def for_face(face_id: str) -> Dict[str, Any]:
    items = [i for i in INTEGRATIONS if face_id in i.get("cube_faces", [])]
    return {**RESEARCH_ADVISORY, "face": face_id, "count": len(items), "integrations": items}
