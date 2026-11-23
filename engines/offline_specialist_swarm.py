"""Deterministic, air-gapped research-swarm demo using REAL local TMRDS parsers.

Only built-in synthetic fixtures are accepted. Production patient records,
clinical LLMs, DICOM diagnosis, and actual treatment decisions are NOT here.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from engines.offline_evidence_pack import EvidencePackError, load_pack, search_pack, _query

from engines.cube_grover_research import simulate_grover_research_plan
from engines.qrce_research_formats import inspect_synthetic_fixture

LOCAL_EVIDENCE_PACK_PATH = Path(__file__).resolve().parents[1] / "data" / "offline" / "citations.json"

SCENARIOS = ("synthetic_all", "synthetic_lab", "synthetic_genomics")
NODES = (
    "labs", "imaging", "genomics", "evidence",
    "drug_discovery", "quantum", "knowledge", "supervisor",
)

LAB_FIXTURE = b"code,value,unit\n718-7,13.4,g/dL\n777-3,250,10*9/L\n"
VCF_FIXTURE = (
    b"##fileformat=VCFv4.3\n"
    b"#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
    b"1\t1234\trs777\tA\tG\t.\tPASS\t.\n"
)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def validate_scenario(value: Any) -> str:
    if not isinstance(value, str) or value not in SCENARIOS:
        raise ValueError("Only enumerated built-in synthetic review scenarios are permitted")
    return value


def capability_manifest() -> dict[str, Any]:
    return {
        "schema_version": "1.0", "mode": "loopback_only", "offline": True,
        "patient_data_accepted": False, "public_patient_upload_enabled": False,
        "human_authority_final": True, "openmi_2_conformance": False,
        "quantum_hardware_enabled": False, "clinical_model_weights_bundled": False,
        "research_advisory_only": True, "automated_diagnosis": False,
        "nodes": list(NODES), "scenarios": list(SCENARIOS),
        "installed_builtin_capabilities": [
            "synthetic_csv_lab_inspection",
            "synthetic_8_column_vcf_inspection",
            "six_qubit_grover_research_coverage_simulation",
            "deterministic_local_evidence_receipt",
            "multi_node_local_read_only_workflow",
            "optional_verified_public_citation_metadata_search",
        ],
        "optional_integrations": {
            "orthanc": "separate_synthetic_sandbox_not_bundled",
            "monai": "optional_weights_license_and_human_review_required",
            "kiwix": "external_zim_archive_not_bundled",
            "local_public_citation_pack": "available_only_if_hash_and_rights_verified",
            "alphafold3": "restricted_weights_not_bundled",
            "openelis": "institutional_connector_not_configured",
            "pydicom": "optional_imaging_dependency_not_in_core",
            "openmi": "not_a_conformant_model_host",
            "ruflo": "not_installed_or_authorized",
            "ehr_fhir": "no_patient_connection",
        },
        "notes": [
            "This is an executable, synthetic-only offline swarm prototype.",
            "No external URLs, models, EHRs, personal clinical data, or treatment advice are loaded.",
            "Optional viewers and archives need separately reviewed local installations.",
        ],
    }


def _laboratory_node(scenario: str) -> dict[str, Any]:
    if scenario not in ("synthetic_lab", "synthetic_all"):
        return {"status": "not_requested"}
    r = inspect_synthetic_fixture(suffix=".csv", data=LAB_FIXTURE, explicitly_synthetic=True)
    return {
        "status": r["status"], "format": "CSV",
        "record_count": r["record_count"], "source_sha256": r["artifact_sha256"],
        "observations": r["records"],
        "clinical_interpretation_allowed": False, "loinc_mapping_verified": False,
    }


def _genomics_node(scenario: str) -> dict[str, Any]:
    if scenario not in ("synthetic_genomics", "synthetic_all"):
        return {"status": "not_requested"}
    r = inspect_synthetic_fixture(suffix=".vcf", data=VCF_FIXTURE, explicitly_synthetic=True)
    return {
        "status": r["status"], "format": "VCF8",
        "record_count": r["record_count"], "source_sha256": r["artifact_sha256"],
        "variants": r["records"], "reference_assembly": "UNSPECIFIED",
        "patient_allele_interpretation_allowed": False,
    }


def _quantum_node(scenario: str) -> dict[str, Any]:
    if scenario not in ("synthetic_all", "synthetic_genomics"):
        return {"status": "not_requested"}
    data = simulate_grover_research_plan()
    return {
        "status": "simulated_research_plan", "algorithm": data["algorithm"],
        "backend": data["backend"], "marked_states": data["oracle"]["marked_states"],
        "iterations": data["iterations"], "oracle_sha256": data["oracle_sha256"],
        "probability_of_synthetic_plan": data["simulated_probability_of_valid_plan"],
        "classical_uniform_baseline": data["uniform_random_baseline_probability"],
        "quantum_hardware_used": False, "probability_is_clinical": False,
    }


def _offline_evidence_node() -> dict[str, Any]:
    """Only surface a verified LOCAL public-citation snapshot, never raw input."""
    if not LOCAL_EVIDENCE_PACK_PATH.exists():
        return {
            "status": "offline_snapshot_not_bundled", "indexed_publications": 0,
            "literature_inferred": False,
            "source": "No independently licensed PubMed/PMC snapshot installed",
        }
    try:
        pack = load_pack(LOCAL_EVIDENCE_PACK_PATH)
    except (EvidencePackError, OSError, ValueError):
        return {
            "status": "offline_snapshot_unverified", "indexed_publications": 0,
            "literature_inferred": False, "clinical_guidance_inferred": False,
            "warning": "Local metadata pack failed rights or integrity review; contents not used",
        }
    return {
        "status": "offline_metadata_pack_verified",
        "indexed_publications": pack["record_count"],
        "sources": dict(pack["source_status"]),
        "retrieved_at": pack["retrieved_at"],
        "pack_sha256": pack["pack_sha256"],
        "source_freshness_currently_verified": False,
        "metadata_only": True, "full_text_redistribution": False,
        "clinical_guidance_inferred": False,
        "research_use_requires_human_review": True,
    }


def search_local_public_evidence(term: str) -> dict[str, Any]:
    """Search only installed, integrity-verified, citation-only metadata; no HTTP."""
    _query(term)
    if not LOCAL_EVIDENCE_PACK_PATH.exists():
        return {
            "schema_version": "1.0", "status": "offline_source_not_installed",
            "matches": [], "match_count": 0, "search_executed_online": False,
            "clinical_interpretation": None, "patient_data_used": False,
            "warning": "No local public citation metadata pack installed; no evidence conclusion possible",
        }
    try:
        pack = load_pack(LOCAL_EVIDENCE_PACK_PATH)
    except (EvidencePackError, ValueError, OSError):
        return {
            "schema_version": "1.0", "status": "offline_source_unverified",
            "matches": [], "match_count": 0, "search_executed_online": False,
            "clinical_interpretation": None, "patient_data_used": False,
            "warning": "Pack integrity, source rights or schema failed validation",
        }
    return {"schema_version": "1.0", **search_pack(pack, term)}


def _execute_node(node: str, scenario: str) -> dict[str, Any]:
    if node == "labs":
        return _laboratory_node(scenario)
    if node == "genomics":
        return _genomics_node(scenario)
    if node == "quantum":
        return _quantum_node(scenario)
    if node == "imaging":
        return {
            "status": "requires_approved_local_reader",
            "source": "DICOM study not supplied; no scan analysis performed",
            "external_tools": ["pydicom", "Orthanc", "OHIF", "3D Slicer"],
            "patient_images_examined": False, "image_interpretation": False,
        }
    if node == "evidence":
        return _offline_evidence_node()
    if node == "drug_discovery":
        return {
            "status": "not_executed", "external_tools": ["RDKit", "OpenMM", "DeepChem"],
            "target_docking_performed": False, "admet_predicted": False,
            "binding_affinity_verified": False,
        }
    if node == "knowledge":
        return {
            "status": "external_archive_not_bundled", "source": "Kiwix WikiMed",
            "zim_archive_available": False, "offline_guidance_inferred": False,
        }
    if node == "supervisor":
        return {
            "status": "human_review_required", "auto_approved": False,
            "diagnosis_generated": False, "treatment_generated": False,
            "review_scope": "synthetic pipeline technical inspection only",
        }
    raise ValueError("Unregistered specialist node")


def run_offline_case(scenario: str) -> dict[str, Any]:
    scenario = validate_scenario(scenario)
    results: dict[str, dict[str, Any]] = {}
    events = []
    for i, name in enumerate(NODES, start=1):
        result = _execute_node(name, scenario)
        results[name] = result
        events.append({
            "schema_version": "1.0", "event_id": f"synthetic-{i:03d}",
            "channel": "tmrds.offline.node.v1", "node": name,
            "data_class": ("public_citation_metadata" if name == "evidence" and
                           result["status"] == "offline_metadata_pack_verified" else
                           "synthetic_nonidentifying"), "status": result["status"],
            "result_sha256": _digest(result), "clinical_promotion_allowed": False,
        })
    receipt = {
        "schema_version": "1.0", "scenario": scenario,
        "nodes": results, "events": events,
        "offline": True, "input_class": (
            "built_in_synthetic_fixture_plus_verified_public_citation_metadata"
            if results["evidence"]["status"] == "offline_metadata_pack_verified" else
            "built_in_synthetic_fixture_only"),
        "patient_data_accepted": False, "network_access_used": False,
        "clinical_inference_performed": False, "treatment_recommended": False,
        "human_authority_final": True,
    }
    receipt["receipt_sha256"] = _digest(receipt)
    receipt["receipt_scope"] = (
        "canonical_synthetic_results_and_verified_public_citation_metadata_no_patient_data"
        if results["evidence"]["status"] == "offline_metadata_pack_verified" else
        "canonical_synthetic_results_and_events_no_patient_data")
    return receipt
