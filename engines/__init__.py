"""TMRDS engine package with lazy loading for optional/heavy dependencies.

Importing ``engines`` remains safe in the minimal CI/runtime environment.
Individual engines are loaded only when their exported symbol is requested.
"""
from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS: dict[str, tuple[str, str]] = {
    "SimulationComputeMesh": ("simulation_compute_mesh", "SimulationComputeMesh"),
    "MONAIVisionNode": ("monai_vision_node", "MONAIVisionNode"),
    "PrecisionMedicineEngine": ("precision_medicine_engine", "PrecisionMedicineEngine"),
    "IntegratedEHRBridge": ("integrated_ehr_bridge", "IntegratedEHRBridge"),
    "MedicalNetBackbone": ("medicalnet_backbone", "MedicalNetBackbone"),
    "ComprehendFHIRBridge": ("comprehend_fhir_bridge", "ComprehendFHIRBridge"),
    "ClinicalLLMRouter": ("clinical_llm_router", "ClinicalLLMRouter"),
    "AlphaFold3Node": ("alphafold3_node", "AlphaFold3Node"),
    "GROVERMolecularNode": ("grover_molecular_node", "GROVERMolecularNode"),
    "QiskitNatureBridge": ("qiskit_nature_bridge", "QiskitNatureBridge"),
    "RDKitChemistryNode": ("rdkit_chemistry_node", "RDKitChemistryNode"),
    "BioCoderAssistant": ("biocoder_assistant", "BioCoderAssistant"),
    "DoctorDignityEthics": ("doctor_dignity_ethics", "DoctorDignityEthics"),
    "OpenMedEngine": ("openmed_nlp", "OpenMedEngine"),
    "TurboVecIndex": ("turbovec_index", "TurboVecIndex"),
    "EvidenceLedger": ("evidence_ledger", "EvidenceLedger"),
    "SovereignEdge": ("sovereign_edge", "SovereignEdge"),
    "KRAGENGraphEngine": ("kragen_graph_engine", "KRAGENGraphEngine"),
    "IHIEBridge": ("ihie_bridge", "IHIEBridge"),
    "UniversalClinicalIngest": ("universal_clinical_ingest", "UniversalClinicalIngest"),
    "PubMedLiteratureBridge": ("pubmed_literature_bridge", "PubMedLiteratureBridge"),
    "Neo4jKRAGENConnector": ("neo4j_kragen_connector", "Neo4jKRAGENConnector"),
    "QRCECureOrchestrator": ("qrce_cure_orchestrator", "QRCECureOrchestrator"),
    "FHIRUSCoreMapper": ("fhir_us_core_mapper", "FHIRUSCoreMapper"),
    "OMOPCDMBridge": ("omop_cdm_bridge", "OMOPCDMBridge"),
    "SpecialtyCareRouter": ("specialty_care_router", "SpecialtyCareRouter"),
    "SpecialtyFHIRProfileRegistry": ("specialty_fhir_profiles", "SpecialtyFHIRProfileRegistry"),
    "OMOPPhenotypeEngine": ("omop_phenotype_engine", "OMOPPhenotypeEngine"),
    "DriveThruIngestion": ("drive_thru_ingestion", "DriveThruIngestion"),
    "OverlookedBlessings": ("overlooked_blessings", "OverlookedBlessings"),
    "OpenSourceMedicalCore": ("open_source_medical_core", "OpenSourceMedicalCore"),
    "USCoreOMOPConceptMap": ("us_core_omop_concept_map", "USCoreOMOPConceptMap"),
    "OHDSIAtlasCohortAdapter": ("ohdsi_atlas_cohort", "OHDSIAtlasCohortAdapter"),
    "NLMGovClinicalTables": ("nlm_gov_clinical_tables", "NLMGovClinicalTables"),
    "ClinicalSwarmOrchestrator": ("clinical_swarm_orchestrator", "ClinicalSwarmOrchestrator"),
    "IEEE11073PHDBridge": ("ieee11073_phd_bridge", "IEEE11073PHDBridge"),
    "DualTierMemory": ("dual_tier_memory", "DualTierMemory"),
    "ESMFoldStructureNode": ("esmfold_structure_node", "ESMFoldStructureNode"),
    "EpistemicParallelRouter": ("epistemic_parallel_router", "EpistemicParallelRouter"),
    "CDCDataPipeline": ("cdc_data_pipeline", "CDCDataPipeline"),
    "OpenNeuroPipeline": ("openneuro_pipeline", "OpenNeuroPipeline"),
    "ClinicalTrialsPipeline": ("clinical_trials_pipeline", "ClinicalTrialsPipeline"),
    "OpenFDAPipeline": ("openfda_pipeline", "OpenFDAPipeline"),
    "NLMResearchPipeline": ("nlm_research_pipeline", "NLMResearchPipeline"),
    "EuropePMCPipeline": ("europe_pmc_pipeline", "EuropePMCPipeline"),
    "CanonicalEntity": ("biomedical_evidence_models", "CanonicalEntity"),
    "EvidenceAssertion": ("biomedical_evidence_models", "EvidenceAssertion"),
    "ConflictGroup": ("biomedical_evidence_models", "ConflictGroup"),
    "SourceRecord": ("biomedical_evidence_models", "SourceRecord"),
    "EvidenceSourceRegistry": ("evidence_source_registry", "EvidenceSourceRegistry"),
    "EvidenceGraphRepository": ("evidence_graph_repository", "EvidenceGraphRepository"),
    "EvidenceGraphService": ("evidence_graph_service", "EvidenceGraphService"),
    "EvidenceConflictEngine": ("evidence_conflict_engine", "EvidenceConflictEngine"),
    "GovernedEvidenceIngestion": ("governed_evidence_ingestion", "GovernedEvidenceIngestion"),
    "Neo4jEvidenceProjection": ("neo4j_evidence_projection", "Neo4jEvidenceProjection"),
    "AIGovernanceRegistry": ("ai_governance", "AIGovernanceRegistry"),
    "EvidenceEnvelope": ("ai_governance", "EvidenceEnvelope"),
    "GovernanceStatus": ("ai_governance", "GovernanceStatus"),
    "ResearchGenerationDecision": ("ai_governance", "ResearchGenerationDecision"),
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> Any:
    """Load an exported engine only when it is actually requested."""
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = target
    module = import_module(f"{__name__}.{module_name}")
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
