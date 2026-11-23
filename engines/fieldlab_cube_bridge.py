"""Local scientific reader -> bounded Quantum Rubik's *review plan* bridge.

An imaging file is not itself phenotypic evidence; a sequence is not itself
a verified target. This queues a human review plane based only on file type,
then runs the already-tested six-qubit mathematical plan simulation. Nothing
is transmitted and no patient measurements are passed to that simulator.
"""
from __future__ import annotations

from typing import Any

from engines.cube_grover_research import simulate_grover_research_plan

_LOCAL_ROUTES = {
    ("pydicom", "DICOM Part 10"): "disease_phenotype",
    ("nibabel", "NIfTI"): "disease_phenotype",
    ("Python CSV", "lab_csv"): "disease_phenotype",
    ("Bio.SeqIO", "fasta"): "target_pathway",
    ("Bio.SeqIO", "fastq"): "target_pathway",
    ("RDKit", "SMILES"): "molecule",
}


def create_offline_review_plan(report: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(report, dict):
        raise ValueError("Expected a bounded local research metadata contract")
    if (
        report.get("schema_version") != "1.0"
        or report.get("execution_scope") != "local_process_only"
        or report.get("network_required") is not False
        or report.get("patient_data_uploaded") is not False
        or report.get("clinical_promotion_allowed") is not False
    ):
        raise ValueError("Untrusted or clinical data cannot be routed into a public research cube")
    reader = report.get("reader")
    fmt = report.get("format")
    try:
        plane = _LOCAL_ROUTES[(reader, fmt)]
    except (TypeError, KeyError):
        raise ValueError("Unrecognized private research file type") from None

    mathematical_plan = simulate_grover_research_plan(
        required=(plane,), max_planes=3
    )
    return {
        "schema_version": "1.0",
        "engine": "TMRDS-FieldLab-Local-QRCE-Bridge",
        "queued_review_plane": plane,
        "review_status": "unreviewed_local_file_type_routing_only",
        "clinical_evidence_computed": False,
        "file_type_does_not_prove_phenotype_or_target": True,
        "raw_patient_records_exported": False,
        "external_research_queried": False,
        "source_freshness_checked": False,
        "clinical_promotion_allowed": False,
        "human_authority_final": True,
        "grover": mathematical_plan,
        "limitations": [
            "The file format alone cannot establish a disease, phenotype, causal target or therapy.",
            "A Grover marked state is a synthetic review-plan mask, never a drug or diagnosis.",
            "No original patient data or source identifiers are passed to the mathematical simulator.",
            "No quantum processor or clinical evidence database is queried in this offline operation.",
        ],
    }
