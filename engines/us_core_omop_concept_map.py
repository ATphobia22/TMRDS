"""
US Core FHIR Profile → OMOP CDM Concept Map for TMRDS.

Aligns with HL7/OHDSI FHIR–OMOP collaborative guidance and the FHIR to OMOP
Cookbook patterns:
  - Map resource/profile → OMOP domain table
  - Map terminology systems → OHDSI vocabularies
  - type_concept_id = 32880 (standard algorithm) for algorithmically derived rows
  - Only final/completed FHIR statuses map into OMOP clinical tables

Standard vocabularies:
  Conditions → SNOMED CT | Drugs → RxNorm | Labs → LOINC | Procedures → SNOMED/CPT
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


# US Core profile id (short) → OMOP mapping metadata
US_CORE_TO_OMOP: Dict[str, Dict[str, Any]] = {
    "us-core-patient": {
        "omop_table": "PERSON",
        "key_fields": {
            "id": "person_id / person_source_value",
            "birthDate": "year_of_birth / birth_datetime",
            "gender": "gender_concept_id (8507 male / 8532 female)",
        },
        "vocab": None,
    },
    "us-core-condition-problems-health-concerns": {
        "omop_table": "CONDITION_OCCURRENCE",
        "key_fields": {
            "code": "condition_concept_id (SNOMED standard) / condition_source_value",
            "onsetDateTime": "condition_start_date",
            "clinicalStatus": "condition_status_concept_id",
            "subject": "person_id",
        },
        "vocab": "SNOMED",
        "source_systems": ["http://snomed.info/sct", "http://hl7.org/fhir/sid/icd-10-cm"],
    },
    "us-core-condition-encounter-diagnosis": {
        "omop_table": "CONDITION_OCCURRENCE",
        "key_fields": {
            "code": "condition_concept_id",
            "encounter": "visit_occurrence_id",
        },
        "vocab": "SNOMED",
    },
    "us-core-observation-lab": {
        "omop_table": "MEASUREMENT",
        "key_fields": {
            "code": "measurement_concept_id (LOINC)",
            "valueQuantity": "value_as_number + unit_concept_id",
            "effectiveDateTime": "measurement_date",
            "interpretation": "value_as_concept_id / measurement_source_value",
        },
        "vocab": "LOINC",
        "source_systems": ["http://loinc.org"],
    },
    "us-core-diagnosticreport-lab": {
        "omop_table": "MEASUREMENT",  # panel context; each result → MEASUREMENT row
        "key_fields": {
            "code": "measurement_source_value (panel)",
            "result": "child Observation → MEASUREMENT rows",
            "issued": "measurement_date",
        },
        "vocab": "LOINC",
    },
    "us-core-medicationrequest": {
        "omop_table": "DRUG_EXPOSURE",
        "key_fields": {
            "medicationCodeableConcept": "drug_concept_id (RxNorm)",
            "authoredOn": "drug_exposure_start_date",
            "dosageInstruction": "quantity / sig / days_supply",
            "status": "only active/completed typically retained",
        },
        "vocab": "RxNorm",
        "source_systems": ["http://www.nlm.nih.gov/research/umls/rxnorm"],
    },
    "us-core-procedure": {
        "omop_table": "PROCEDURE_OCCURRENCE",
        "key_fields": {
            "code": "procedure_concept_id",
            "performedDateTime": "procedure_date",
        },
        "vocab": "SNOMED",
        "source_systems": ["http://snomed.info/sct", "http://www.ama-assn.org/go/cpt"],
    },
    "us-core-encounter": {
        "omop_table": "VISIT_OCCURRENCE",
        "key_fields": {
            "type": "visit_concept_id",
            "period.start": "visit_start_date",
            "period.end": "visit_end_date",
            "class": "visit type (inpatient/outpatient/ER)",
        },
        "vocab": "Visit",
    },
    "us-core-allergyintolerance": {
        "omop_table": "OBSERVATION",
        "key_fields": {
            "code": "observation_concept_id",
            "reaction": "value_as_concept_id / qualifier",
        },
        "vocab": "SNOMED",
    },
    "us-core-immunization": {
        "omop_table": "DRUG_EXPOSURE",  # vaccine as drug; alt PROCEDURE_OCCURRENCE for act
        "key_fields": {
            "vaccineCode": "drug_concept_id",
            "occurrenceDateTime": "drug_exposure_start_date",
        },
        "vocab": "CVX / RxNorm",
    },
}

GENDER_FHIR_TO_OMOP = {
    "male": 8507,
    "female": 8532,
    "other": 0,
    "unknown": 0,
}

TYPE_CONCEPT_ALGORITHM = 32880  # FHIR-OMOP Cookbook recommendation


class USCoreOMOPConceptMap:
    """Resolve US Core profiles to OMOP tables and terminology targets."""

    def map_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        key = profile_id.lower().replace("_", "-")
        if not key.startswith("us-core") and "us-core" not in key:
            # allow short names like "observation-lab"
            for k, v in US_CORE_TO_OMOP.items():
                if key in k or k.endswith(key):
                    return {"profile": k, **v, "type_concept_id": TYPE_CONCEPT_ALGORITHM}
            return None
        meta = US_CORE_TO_OMOP.get(key)
        if meta:
            return {"profile": key, **meta, "type_concept_id": TYPE_CONCEPT_ALGORITHM}
        return None

    def map_resource_type(self, resource_type: str) -> List[Dict[str, Any]]:
        rt = resource_type.lower()
        out = []
        for k, v in US_CORE_TO_OMOP.items():
            # heuristic: profile contains resource name fragment
            fragment = k.replace("us-core-", "").split("-")[0]
            if fragment in rt or rt in k:
                out.append({"profile": k, **v})
        return out

    def gender_concept_id(self, fhir_gender: str) -> int:
        return GENDER_FHIR_TO_OMOP.get((fhir_gender or "").lower(), 0)

    def catalog(self) -> Dict[str, Any]:
        return {
            "profiles_mapped": list(US_CORE_TO_OMOP.keys()),
            "type_concept_id_default": TYPE_CONCEPT_ALGORITHM,
            "vocab_summary": {
                "CONDITION_OCCURRENCE": "SNOMED (+ ICD-10-CM source)",
                "MEASUREMENT": "LOINC",
                "DRUG_EXPOSURE": "RxNorm",
                "PROCEDURE_OCCURRENCE": "SNOMED / CPT",
                "PERSON": "OMOP gender concepts 8507/8532",
            },
            "references": [
                "HL7 FHIR and OMOP Mappings IG (uv/fhir-omop)",
                "FHIR to OMOP Cookbook (HL7/OHDSI)",
                "OHDSI Athena vocabulary Maps to",
            ],
        }

    def status(self) -> Dict[str, Any]:
        return {
            "node": "USCoreOMOPConceptMap",
            "profile_count": len(US_CORE_TO_OMOP),
            "status": "READY",
        }
