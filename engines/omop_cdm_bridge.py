"""
OMOP CDM v5.4 Bridge for TMRDS.
Maps clinical facts into OMOP clinical event tables and documents
FHIR ↔ OMOP domain alignment (OHDSI / HL7 FHIR-OMOP collaborative patterns).

Core tables: PERSON, CONDITION_OCCURRENCE, DRUG_EXPOSURE, MEASUREMENT,
PROCEDURE_OCCURRENCE, OBSERVATION, VISIT_OCCURRENCE.

Standard vocabs: SNOMED (conditions), RxNorm (drugs), LOINC (measurements).
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional


# High-level FHIR resource → OMOP table (FHIR-OMOP collaborative consensus)
FHIR_TO_OMOP = {
    "Patient": "PERSON",
    "Encounter": "VISIT_OCCURRENCE",
    "Condition": "CONDITION_OCCURRENCE",
    "MedicationRequest": "DRUG_EXPOSURE",
    "MedicationStatement": "DRUG_EXPOSURE",
    "MedicationAdministration": "DRUG_EXPOSURE",
    "Observation": "MEASUREMENT",  # labs/vitals; qualitative → OBSERVATION
    "DiagnosticReport": "MEASUREMENT",  # panel context; results as MEASUREMENT rows
    "Procedure": "PROCEDURE_OCCURRENCE",
    "Immunization": "PROCEDURE_OCCURRENCE",  # or DRUG_EXPOSURE for vaccine product
    "AllergyIntolerance": "OBSERVATION",
    "Practitioner": "PROVIDER",
    "Location": "CARE_SITE",
}

OMOP_TO_FHIR = {v: k for k, v in FHIR_TO_OMOP.items() if v not in ("MEASUREMENT", "DRUG_EXPOSURE")}
OMOP_TO_FHIR["MEASUREMENT"] = "Observation"
OMOP_TO_FHIR["DRUG_EXPOSURE"] = "MedicationRequest"
OMOP_TO_FHIR["PERSON"] = "Patient"
OMOP_TO_FHIR["CONDITION_OCCURRENCE"] = "Condition"
OMOP_TO_FHIR["PROCEDURE_OCCURRENCE"] = "Procedure"
OMOP_TO_FHIR["VISIT_OCCURRENCE"] = "Encounter"


class OMOPCDMBridge:
    """Lightweight OMOP row builder + bidirectional domain map."""

    def __init__(self) -> None:
        self._rows: Dict[str, List[Dict[str, Any]]] = {
            "PERSON": [],
            "CONDITION_OCCURRENCE": [],
            "DRUG_EXPOSURE": [],
            "MEASUREMENT": [],
            "PROCEDURE_OCCURRENCE": [],
            "OBSERVATION": [],
            "VISIT_OCCURRENCE": [],
        }

    def person(self, person_id: int, year_of_birth: Optional[int] = None, gender_concept_id: int = 0) -> Dict[str, Any]:
        row = {
            "person_id": person_id,
            "gender_concept_id": gender_concept_id,
            "year_of_birth": year_of_birth,
            "race_concept_id": 0,
            "ethnicity_concept_id": 0,
        }
        self._rows["PERSON"].append(row)
        return row

    def condition_occurrence(
        self,
        person_id: int,
        condition_concept_id: int,
        condition_start_date: str,
        condition_source_value: str = "",
        condition_source_concept_id: int = 0,
    ) -> Dict[str, Any]:
        row = {
            "condition_occurrence_id": len(self._rows["CONDITION_OCCURRENCE"]) + 1,
            "person_id": person_id,
            "condition_concept_id": condition_concept_id,
            "condition_start_date": condition_start_date,
            "condition_type_concept_id": 32880,  # standard algorithm (FHIR-OMOP cookbook)
            "condition_source_value": condition_source_value,
            "condition_source_concept_id": condition_source_concept_id,
        }
        self._rows["CONDITION_OCCURRENCE"].append(row)
        return row

    def drug_exposure(
        self,
        person_id: int,
        drug_concept_id: int,
        drug_exposure_start_date: str,
        drug_source_value: str = "",
        quantity: Optional[float] = None,
    ) -> Dict[str, Any]:
        row = {
            "drug_exposure_id": len(self._rows["DRUG_EXPOSURE"]) + 1,
            "person_id": person_id,
            "drug_concept_id": drug_concept_id,
            "drug_exposure_start_date": drug_exposure_start_date,
            "drug_type_concept_id": 32880,
            "drug_source_value": drug_source_value,
            "quantity": quantity,
        }
        self._rows["DRUG_EXPOSURE"].append(row)
        return row

    def measurement(
        self,
        person_id: int,
        measurement_concept_id: int,
        measurement_date: str,
        value_as_number: Optional[float] = None,
        unit_source_value: Optional[str] = None,
        measurement_source_value: str = "",
    ) -> Dict[str, Any]:
        row = {
            "measurement_id": len(self._rows["MEASUREMENT"]) + 1,
            "person_id": person_id,
            "measurement_concept_id": measurement_concept_id,
            "measurement_date": measurement_date,
            "measurement_type_concept_id": 32880,
            "value_as_number": value_as_number,
            "unit_source_value": unit_source_value,
            "measurement_source_value": measurement_source_value,
        }
        self._rows["MEASUREMENT"].append(row)
        return row

    def map_fhir_resource_type(self, resource_type: str) -> Optional[str]:
        return FHIR_TO_OMOP.get(resource_type)

    def map_omop_table(self, table: str) -> Optional[str]:
        return OMOP_TO_FHIR.get(table)

    def from_fhir_bundle(self, bundle: Dict[str, Any], person_id: int = 1) -> Dict[str, Any]:
        """Best-effort FHIR Bundle → OMOP row sets (concept IDs left 0 without Athena vocab)."""
        today = time.strftime("%Y-%m-%d")
        mapped = 0
        for entry in bundle.get("entry", []):
            r = entry.get("resource") or entry
            rt = r.get("resourceType")
            table = self.map_fhir_resource_type(rt or "")
            if not table:
                continue
            if table == "CONDITION_OCCURRENCE":
                code = (r.get("code") or {}).get("text") or ""
                self.condition_occurrence(person_id, 0, today, condition_source_value=code)
                mapped += 1
            elif table == "MEASUREMENT":
                code = (r.get("code") or {}).get("text") or ""
                val = None
                if "valueQuantity" in r:
                    val = r["valueQuantity"].get("value")
                self.measurement(person_id, 0, today, value_as_number=val, measurement_source_value=code)
                mapped += 1
            elif table == "DRUG_EXPOSURE":
                med = r.get("medicationCodeableConcept") or {}
                text = med.get("text") or ""
                self.drug_exposure(person_id, 0, today, drug_source_value=text)
                mapped += 1
        return {"mapped_resources": mapped, "tables": {k: len(v) for k, v in self._rows.items() if v}}

    def export_tables(self) -> Dict[str, List[Dict[str, Any]]]:
        return {k: list(v) for k, v in self._rows.items() if v}

    def status(self) -> Dict[str, Any]:
        return {
            "node": "OMOPCDMBridge",
            "cdm_version": "5.4",
            "fhir_to_omop": FHIR_TO_OMOP,
            "row_counts": {k: len(v) for k, v in self._rows.items()},
            "vocab_targets": {"condition": "SNOMED", "drug": "RxNorm", "measurement": "LOINC"},
            "status": "READY",
        }
