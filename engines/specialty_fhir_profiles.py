"""
Specialty-Specific FHIR Profile Registry for TMRDS.
Maps clinical specialties to HL7 FHIR Implementation Guide profiles beyond US Core.

Verified IGs:
  - mCODE (Minimal Common Oncology Data Elements)
  - HL7 Clinical Genomics / Genomics Reporting
  - CardX Hypertension / CIED
  - US Core (foundation for all US Realm)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


SPECIALTY_FHIR_PROFILES: Dict[str, Dict[str, Any]] = {
    "oncology": {
        "ig": "hl7.fhir.us.mcode",
        "ig_title": "mCODE — Minimal Common Oncology Data Elements",
        "canonical_base": "http://hl7.org/fhir/us/mcode/StructureDefinition",
        "profiles": [
            "mcode-cancer-patient",
            "mcode-primary-cancer-condition",
            "mcode-secondary-cancer-condition",
            "mcode-tumor",
            "mcode-genomic-variant",
            "mcode-genomics-report",
            "mcode-cancer-stage",
            "mcode-tnm-stage-group",
            "mcode-human-specimen",
            "mcode-radiotherapy-course-summary",
        ],
        "key_resources": ["Condition", "Observation", "DiagnosticReport", "Specimen", "Procedure"],
    },
    "clinical_genetics": {
        "ig": "hl7.fhir.uv.genomics-reporting",
        "ig_title": "HL7 Genomics Reporting",
        "canonical_base": "http://hl7.org/fhir/uv/genomics-reporting/StructureDefinition",
        "profiles": [
            "genomics-report",
            "variant",
            "sequence-phase-relationship",
            "haplotype",
            "genotype",
            "inherited-disease-pathogenicity",
            "therapeutic-implication",
            "medication-efficacy",
            "medication-metabolism",
        ],
        "key_resources": ["DiagnosticReport", "Observation", "MolecularSequence"],
        "related": ["GA4GH Phenopackets"],
    },
    "cardiology": {
        "ig": "hl7.fhir.uv.cardx-htn / CardX CIED",
        "ig_title": "CardX Hypertension Management / Cardiac Implantable Electronic Devices",
        "canonical_base": "http://hl7.org/fhir/uv/cardx",
        "profiles": [
            "cardx-blood-pressure-panel",
            "cardx-hypertension-condition",
            "cied-device",
            "cied-observation",
        ],
        "key_resources": ["Observation", "Condition", "Device", "Procedure"],
    },
    "primary_care": {
        "ig": "hl7.fhir.us.core",
        "ig_title": "US Core",
        "canonical_base": "http://hl7.org/fhir/us/core/StructureDefinition",
        "profiles": [
            "us-core-patient",
            "us-core-condition-problems-health-concerns",
            "us-core-observation-lab",
            "us-core-medicationrequest",
            "us-core-encounter",
            "us-core-diagnosticreport-lab",
        ],
        "key_resources": ["Patient", "Condition", "Observation", "MedicationRequest", "Encounter"],
    },
    "rare_disease": {
        "ig": "US Core + Genomics Reporting + Phenopackets",
        "ig_title": "Rare disease — HPO-linked phenotype + genomic profiles",
        "canonical_base": "http://hl7.org/fhir/uv/genomics-reporting/StructureDefinition",
        "profiles": [
            "genomics-report",
            "variant",
            "inherited-disease-pathogenicity",
            "us-core-condition-problems-health-concerns",
        ],
        "ontologies": ["HPO", "ORDO", "OMIM", "GARD"],
        "key_resources": ["Condition", "Observation", "DiagnosticReport"],
    },
    "radiation_oncology": {
        "ig": "hl7.fhir.us.codex-radiation-therapy",
        "ig_title": "CodeX Radiation Therapy",
        "canonical_base": "http://hl7.org/fhir/us/codex-radiation-therapy/StructureDefinition",
        "profiles": ["radiotherapy-course-summary", "radiotherapy-treated-phase", "radiotherapy-volume"],
        "key_resources": ["Procedure", "Observation", "BodyStructure"],
    },
}

# Fallback: all other SpecialtyCareRouter domains use US Core as floor
_US_CORE_FLOOR = SPECIALTY_FHIR_PROFILES["primary_care"]


class SpecialtyFHIRProfileRegistry:
    """Resolve specialty → FHIR IG profiles for resource construction."""

    def resolve(self, specialty: str) -> Dict[str, Any]:
        key = (specialty or "").lower().replace(" ", "_").replace("/", "_")
        if key in SPECIALTY_FHIR_PROFILES:
            return {"specialty": key, **SPECIALTY_FHIR_PROFILES[key]}
        # aliases
        aliases = {
            "cancer": "oncology",
            "genomics": "clinical_genetics",
            "genetics": "clinical_genetics",
            "cardio": "cardiology",
            "heart": "cardiology",
            "radiation": "radiation_oncology",
        }
        mapped = aliases.get(key)
        if mapped and mapped in SPECIALTY_FHIR_PROFILES:
            return {"specialty": mapped, **SPECIALTY_FHIR_PROFILES[mapped]}
        return {"specialty": key or "primary_care", **_US_CORE_FLOOR, "note": "US Core floor applied"}

    def profile_url(self, specialty: str, profile_name: str) -> str:
        meta = self.resolve(specialty)
        base = meta.get("canonical_base", "").rstrip("/")
        return f"{base}/{profile_name}"

    def list_igs(self) -> List[Dict[str, str]]:
        return [
            {"specialty": k, "ig": v["ig"], "title": v["ig_title"]}
            for k, v in SPECIALTY_FHIR_PROFILES.items()
        ]

    def status(self) -> Dict[str, Any]:
        return {
            "node": "SpecialtyFHIRProfileRegistry",
            "specialty_igs": list(SPECIALTY_FHIR_PROFILES.keys()),
            "status": "READY",
        }
