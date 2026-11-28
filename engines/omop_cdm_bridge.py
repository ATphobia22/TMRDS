"""Bounded local FHIR R4 to OMOP CDM 5.4 research projection.

Only Patient, Condition, numeric final Observation, and MedicationRequest are
projected. The bridge performs no network access or persistence. Vocabulary
concept IDs remain zero until an independently governed vocabulary mapping is
available; source codes are retained and must not be mistaken for standard IDs.
"""
from __future__ import annotations

import copy
import math
import re
from datetime import date, datetime
from typing import Any, Dict, List, Mapping, Optional


FHIR_TO_OMOP = {
    "Patient": "PERSON",
    "Encounter": "VISIT_OCCURRENCE",
    "Condition": "CONDITION_OCCURRENCE",
    "MedicationRequest": "DRUG_EXPOSURE",
    "MedicationStatement": "DRUG_EXPOSURE",
    "MedicationAdministration": "DRUG_EXPOSURE",
    "Observation": "MEASUREMENT",
    "DiagnosticReport": "MEASUREMENT",
    "Procedure": "PROCEDURE_OCCURRENCE",
    "Immunization": "PROCEDURE_OCCURRENCE",
    "AllergyIntolerance": "OBSERVATION",
    "Practitioner": "PROVIDER",
    "Location": "CARE_SITE",
}

OMOP_TO_FHIR = {
    value: key for key, value in FHIR_TO_OMOP.items()
    if value not in {"MEASUREMENT", "DRUG_EXPOSURE"}
}
OMOP_TO_FHIR.update({
    "MEASUREMENT": "Observation",
    "DRUG_EXPOSURE": "MedicationRequest",
    "PERSON": "Patient",
    "CONDITION_OCCURRENCE": "Condition",
    "PROCEDURE_OCCURRENCE": "Procedure",
    "VISIT_OCCURRENCE": "Encounter",
})

SUPPORTED_FHIR_TYPES = frozenset({
    "Patient", "Condition", "Observation", "MedicationRequest",
})
FHIR_ID_PATTERN = re.compile(r"[A-Za-z0-9.-]{1,64}\\Z")
PATIENT_REFERENCE_PATTERN = re.compile(r"Patient/([A-Za-z0-9.-]{1,64})\\Z")
GENDER_CONCEPT_IDS = {
    "male": 8507,
    "female": 8532,
    "other": 0,
    "unknown": 0,
}
ALGORITHM_TYPE_CONCEPT_ID = 32880


def _fhir_date(value: Any, field_name: str) -> str:
    """Convert a complete FHIR date/dateTime to an OMOP ISO calendar date."""
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} is required")
    try:
        if len(value) == 10:
            return date.fromisoformat(value).isoformat()
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        return datetime.fromisoformat(normalized).date().isoformat()
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a complete ISO date or dateTime") from exc


def _codeable_concept(value: Any, field_name: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a CodeableConcept")
    codings = value.get("coding", [])
    if not isinstance(codings, list) or any(not isinstance(item, dict) for item in codings):
        raise ValueError(f"{field_name}.coding must be an array of objects")
    normalized_codings = []
    for coding in codings:
        system = coding.get("system")
        code = coding.get("code")
        if system is not None and not isinstance(system, str):
            raise ValueError(f"{field_name}.coding.system must be a string")
        if code is not None and not isinstance(code, str):
            raise ValueError(f"{field_name}.coding.code must be a string")
        if system and code:
            normalized_codings.append(copy.deepcopy(coding))
    text = value.get("text")
    if text is not None and not isinstance(text, str):
        raise ValueError(f"{field_name}.text must be a string")
    if not normalized_codings and not text:
        raise ValueError(f"{field_name} needs a coded value or text")
    primary = normalized_codings[0] if normalized_codings else {}
    source_value = (
        f"{primary.get('system')}|{primary.get('code')}"
        if primary else text
    )
    return {
        "coding": normalized_codings,
        "text": text,
        "source_value": source_value,
    }


def _patient_reference(resource: Mapping[str, Any]) -> tuple[str, str]:
    subject = resource.get("subject")
    reference = subject.get("reference") if isinstance(subject, dict) else None
    match = PATIENT_REFERENCE_PATTERN.fullmatch(reference or "") if isinstance(reference, str) else None
    if match is None:
        raise ValueError(
            f"{resource.get('resourceType')} resource must reference exactly one Patient/id"
        )
    return match.group(1), reference


class OMOPCDMBridge:
    """In-memory OMOP row builder with an explicit, bounded FHIR round-trip."""

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
        # Sidecar metadata is limited to fields needed to reconstruct the
        # supported FHIR subset; it is not an OMOP CDM table or audit store.
        self._fhir_index: List[Dict[str, Any]] = []
        self._fhir_resource_keys: set[tuple[str, str]] = set()

    def person(
        self,
        person_id: int,
        year_of_birth: Optional[int] = None,
        gender_concept_id: int = 0,
        *,
        birth_datetime: Optional[str] = None,
        person_source_value: Optional[str] = None,
    ) -> Dict[str, Any]:
        row = {
            "person_id": person_id,
            "gender_concept_id": gender_concept_id,
            "year_of_birth": year_of_birth,
            "birth_datetime": birth_datetime,
            "race_concept_id": 0,
            "ethnicity_concept_id": 0,
            "person_source_value": person_source_value,
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
            "condition_type_concept_id": ALGORITHM_TYPE_CONCEPT_ID,
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
            "drug_type_concept_id": ALGORITHM_TYPE_CONCEPT_ID,
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
        if value_as_number is not None and (
            isinstance(value_as_number, bool)
            or not isinstance(value_as_number, (int, float))
            or not math.isfinite(float(value_as_number))
        ):
            raise ValueError("measurement value must be finite and numeric")
        row = {
            "measurement_id": len(self._rows["MEASUREMENT"]) + 1,
            "person_id": person_id,
            "measurement_concept_id": measurement_concept_id,
            "measurement_date": measurement_date,
            "measurement_type_concept_id": ALGORITHM_TYPE_CONCEPT_ID,
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

    def from_fhir_bundle(
        self,
        bundle: Dict[str, Any],
        person_id: Optional[int] = None,
        *,
        person_id_map: Optional[Mapping[str, int]] = None,
    ) -> Dict[str, Any]:
        """Project a FHIR collection Bundle using explicit, one-to-one identity mapping.

        A single Patient may use person_id. Multi-patient bundles require
        person_id_map. Patient references must resolve to Patient resources
        in the same Bundle. Unsupported resources and non-final requests are
        reported rather than silently coerced into OMOP rows.
        """
        if (
            not isinstance(bundle, dict)
            or bundle.get("resourceType") != "Bundle"
            or bundle.get("type") != "collection"
            or not isinstance(bundle.get("entry"), list)
        ):
            raise ValueError("FHIR Bundle must be a collection with an entry array")

        resources: List[Dict[str, Any]] = []
        patient_resources: List[Dict[str, Any]] = []
        subject_patient_ids: set[str] = set()
        seen_keys: set[tuple[str, str]] = set()
        skipped: List[Dict[str, Any]] = []

        for entry in bundle["entry"]:
            if not isinstance(entry, dict) or not isinstance(entry.get("resource"), dict):
                raise ValueError("FHIR Bundle entry must contain a resource object")
            resource = entry["resource"]
            resource_type = resource.get("resourceType")
            if not isinstance(resource_type, str) or not resource_type:
                raise ValueError("FHIR resourceType is required")
            resource_id = resource.get("id")
            if resource_type in SUPPORTED_FHIR_TYPES:
                if not isinstance(resource_id, str) or not FHIR_ID_PATTERN.fullmatch(resource_id):
                    raise ValueError(f"{resource_type} resource id is invalid")
                key = (resource_type, resource_id)
                if key in seen_keys or key in self._fhir_resource_keys:
                    raise ValueError(f"duplicate FHIR resource identity: {resource_type}/{resource_id}")
                seen_keys.add(key)
                resources.append(resource)
                if resource_type == "Patient":
                    patient_resources.append(resource)
                else:
                    patient_id, _ = _patient_reference(resource)
                    subject_patient_ids.add(patient_id)
            else:
                reason = "unsupported_mapping" if resource_type in FHIR_TO_OMOP else "unsupported_resource_type"
                skipped.append({
                    "resource_type": resource_type,
                    "resource_id": resource_id if isinstance(resource_id, str) else None,
                    "reason": reason,
                })

        patient_ids = [resource["id"] for resource in patient_resources]
        if len(patient_ids) != len(set(patient_ids)):
            raise ValueError("duplicate Patient resource id")
        patient_id_set = set(patient_ids)
        missing_patient_resources = sorted(subject_patient_ids - patient_id_set)
        if missing_patient_resources:
            raise ValueError(f"Patient resource missing for references: {missing_patient_resources}")

        if person_id is not None and person_id_map is not None:
            raise ValueError("provide person_id or person_id_map, not both")
        if person_id_map is not None:
            identity_map = dict(person_id_map)
            if any(
                not isinstance(key, str) or not FHIR_ID_PATTERN.fullmatch(key)
                or isinstance(value, bool) or not isinstance(value, int) or value <= 0
                for key, value in identity_map.items()
            ):
                raise ValueError("person_id_map must map valid FHIR Patient ids to positive integers")
            if set(identity_map) != patient_id_set:
                raise ValueError("person_id_map must contain exactly the Patient resources in the Bundle")
            if len(set(identity_map.values())) != len(identity_map):
                raise ValueError("person_id_map values must be unique")
        elif person_id is not None:
            if isinstance(person_id, bool) or not isinstance(person_id, int) or person_id <= 0:
                raise ValueError("person_id must be a positive integer")
            if len(patient_ids) != 1:
                raise ValueError("multiple or missing Patient resources require person_id_map")
            identity_map = {patient_ids[0]: person_id}
        elif patient_ids:
            raise ValueError("an explicit person_id or person_id_map is required")
        else:
            identity_map = {}

        existing_person_ids = {row["person_id"] for row in self._rows["PERSON"]}
        if existing_person_ids.intersection(identity_map.values()):
            raise ValueError("person_id assignment conflicts with existing bridge state")

        pending_rows: Dict[str, List[Dict[str, Any]]] = {name: [] for name in self._rows}
        pending_index: List[Dict[str, Any]] = []
        mapped = 0

        def next_row_id(table: str) -> int:
            return len(self._rows[table]) + len(pending_rows[table]) + 1

        for resource in resources:
            resource_type = resource["resourceType"]
            resource_id = resource["id"]
            if resource_type == "Patient":
                gender = resource.get("gender", "unknown")
                if gender not in GENDER_CONCEPT_IDS:
                    raise ValueError(f"Patient/{resource_id} has an unsupported FHIR gender")
                birth_date = resource.get("birthDate")
                birth_day = _fhir_date(birth_date, "Patient.birthDate") if birth_date else None
                person_key = identity_map[resource_id]
                pending_rows["PERSON"].append({
                    "person_id": person_key,
                    "gender_concept_id": GENDER_CONCEPT_IDS[gender],
                    "year_of_birth": int(birth_day[:4]) if birth_day else None,
                    "birth_datetime": birth_day,
                    "race_concept_id": 0,
                    "ethnicity_concept_id": 0,
                    "person_source_value": resource_id,
                })
                pending_index.append({
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "table": "PERSON",
                    "row_key": "person_id",
                    "row_id": person_key,
                    "person_id": person_key,
                    "gender": gender,
                    "birth_date": birth_day,
                })
                mapped += 1
                continue

            patient_id, subject_reference = _patient_reference(resource)
            mapped_person_id = identity_map[patient_id]

            if resource_type == "Condition":
                onset = resource.get("onsetDateTime")
                if onset is None and isinstance(resource.get("onsetPeriod"), dict):
                    onset = resource["onsetPeriod"].get("start")
                if onset is None:
                    onset = resource.get("recordedDate")
                start_date = _fhir_date(onset, "Condition onset/recorded date")
                code = _codeable_concept(resource.get("code"), "Condition.code")
                row_id = next_row_id("CONDITION_OCCURRENCE")
                pending_rows["CONDITION_OCCURRENCE"].append({
                    "condition_occurrence_id": row_id,
                    "person_id": mapped_person_id,
                    "condition_concept_id": 0,
                    "condition_start_date": start_date,
                    "condition_type_concept_id": ALGORITHM_TYPE_CONCEPT_ID,
                    "condition_source_value": code["source_value"],
                    "condition_source_concept_id": 0,
                })
                pending_index.append({
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "table": "CONDITION_OCCURRENCE",
                    "row_key": "condition_occurrence_id",
                    "row_id": row_id,
                    "person_id": mapped_person_id,
                    "subject_reference": subject_reference,
                    "code": code,
                    "clinical_status": copy.deepcopy(resource.get("clinicalStatus")),
                })
                mapped += 1
                continue

            if resource_type == "Observation":
                if resource.get("status") != "final":
                    skipped.append({
                        "resource_type": resource_type,
                        "resource_id": resource_id,
                        "reason": "non_final_status",
                    })
                    continue
                effective = resource.get("effectiveDateTime")
                if effective is None and isinstance(resource.get("effectivePeriod"), dict):
                    effective = resource["effectivePeriod"].get("start")
                measurement_date = _fhir_date(effective, "Observation effective date")
                code = _codeable_concept(resource.get("code"), "Observation.code")
                quantity = resource.get("valueQuantity")
                if not isinstance(quantity, dict):
                    raise ValueError("only numeric Observation.valueQuantity is supported")
                value = quantity.get("value")
                if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(float(value))
                ):
                    raise ValueError("Observation.valueQuantity.value must be finite and numeric")
                row_id = next_row_id("MEASUREMENT")
                pending_rows["MEASUREMENT"].append({
                    "measurement_id": row_id,
                    "person_id": mapped_person_id,
                    "measurement_concept_id": 0,
                    "measurement_date": measurement_date,
                    "measurement_type_concept_id": ALGORITHM_TYPE_CONCEPT_ID,
                    "value_as_number": value,
                    "unit_source_value": quantity.get("unit") or quantity.get("code"),
                    "measurement_source_value": code["source_value"],
                })
                pending_index.append({
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "table": "MEASUREMENT",
                    "row_key": "measurement_id",
                    "row_id": row_id,
                    "person_id": mapped_person_id,
                    "subject_reference": subject_reference,
                    "code": code,
                    "status": "final",
                    "value_quantity": copy.deepcopy(quantity),
                })
                mapped += 1
                continue

            if resource_type == "MedicationRequest":
                status = resource.get("status")
                if status not in {"active", "completed"}:
                    skipped.append({
                        "resource_type": resource_type,
                        "resource_id": resource_id,
                        "reason": "non_active_status",
                    })
                    continue
                start_date = _fhir_date(resource.get("authoredOn"), "MedicationRequest.authoredOn")
                medication = _codeable_concept(
                    resource.get("medicationCodeableConcept"),
                    "MedicationRequest.medicationCodeableConcept",
                )
                quantity = None
                dispense = resource.get("dispenseRequest")
                quantity_payload = dispense.get("quantity") if isinstance(dispense, dict) else None
                if isinstance(quantity_payload, dict) and quantity_payload.get("value") is not None:
                    raw_quantity = quantity_payload["value"]
                    if (
                        isinstance(raw_quantity, bool)
                        or not isinstance(raw_quantity, (int, float))
                        or not math.isfinite(float(raw_quantity))
                    ):
                        raise ValueError("MedicationRequest quantity must be finite and numeric")
                    quantity = raw_quantity
                row_id = next_row_id("DRUG_EXPOSURE")
                pending_rows["DRUG_EXPOSURE"].append({
                    "drug_exposure_id": row_id,
                    "person_id": mapped_person_id,
                    "drug_concept_id": 0,
                    "drug_exposure_start_date": start_date,
                    "drug_type_concept_id": ALGORITHM_TYPE_CONCEPT_ID,
                    "drug_source_value": medication["source_value"],
                    "quantity": quantity,
                })
                pending_index.append({
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "table": "DRUG_EXPOSURE",
                    "row_key": "drug_exposure_id",
                    "row_id": row_id,
                    "person_id": mapped_person_id,
                    "subject_reference": subject_reference,
                    "medication": medication,
                    "status": status,
                    "intent": resource.get("intent"),
                })
                mapped += 1

        # Commit in-memory state only after every supported resource validates.
        for table, rows in pending_rows.items():
            self._rows[table].extend(rows)
        self._fhir_index.extend(pending_index)
        self._fhir_resource_keys.update(
            (item["resource_type"], item["resource_id"]) for item in pending_index
        )
        return {
            "mapped_resources": mapped,
            "tables": {table: len(rows) for table, rows in pending_rows.items() if rows},
            "skipped_resources": skipped,
            "concept_ids_resolved": False,
            "persistence": "none",
            "external_transmission": False,
        }

    def to_fhir_bundle(self) -> Dict[str, Any]:
        """Reconstruct the supported subset from OMOP rows and local sidecar metadata."""
        resources: List[Dict[str, Any]] = []
        for metadata in self._fhir_index:
            table = metadata["table"]
            row_key = metadata["row_key"]
            row_id = metadata["row_id"]
            row = next(
                (item for item in self._rows[table] if item.get(row_key) == row_id),
                None,
            )
            if row is None:
                raise RuntimeError(
                    f"OMOP projection row missing for {metadata['resource_type']}/{metadata['resource_id']}"
                )

            resource_type = metadata["resource_type"]
            resource: Dict[str, Any] = {"resourceType": resource_type, "id": metadata["resource_id"]}
            if resource_type == "Patient":
                resource["gender"] = metadata["gender"]
                if metadata["birth_date"]:
                    resource["birthDate"] = row["birth_datetime"]
            elif resource_type == "Condition":
                resource.update({
                    "subject": {"reference": metadata["subject_reference"]},
                    "code": {
                        "coding": copy.deepcopy(metadata["code"]["coding"]),
                        "text": metadata["code"]["text"],
                    },
                    "onsetDateTime": row["condition_start_date"],
                })
                if metadata["clinical_status"] is not None:
                    resource["clinicalStatus"] = copy.deepcopy(metadata["clinical_status"])
            elif resource_type == "Observation":
                quantity = copy.deepcopy(metadata["value_quantity"])
                quantity["value"] = row["value_as_number"]
                if row["unit_source_value"] is not None:
                    quantity["unit"] = row["unit_source_value"]
                resource.update({
                    "status": metadata["status"],
                    "subject": {"reference": metadata["subject_reference"]},
                    "code": {
                        "coding": copy.deepcopy(metadata["code"]["coding"]),
                        "text": metadata["code"]["text"],
                    },
                    "effectiveDateTime": row["measurement_date"],
                    "valueQuantity": quantity,
                })
            elif resource_type == "MedicationRequest":
                resource.update({
                    "status": metadata["status"],
                    "subject": {"reference": metadata["subject_reference"]},
                    "authoredOn": row["drug_exposure_start_date"],
                    "medicationCodeableConcept": {
                        "coding": copy.deepcopy(metadata["medication"]["coding"]),
                        "text": metadata["medication"]["text"],
                    },
                })
                if metadata["intent"] is not None:
                    resource["intent"] = metadata["intent"]
            resources.append(resource)

        return {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [{"resource": resource} for resource in resources],
        }

    def export_fhir_bundle(self) -> Dict[str, Any]:
        """Alias for to_fhir_bundle."""
        return self.to_fhir_bundle()

    def export_tables(self) -> Dict[str, List[Dict[str, Any]]]:
        return {table: copy.deepcopy(rows) for table, rows in self._rows.items() if rows}

    def status(self) -> Dict[str, Any]:
        return {
            "node": "OMOPCDMBridge",
            "cdm_version": "5.4",
            "fhir_to_omop": FHIR_TO_OMOP,
            "supported_fhir_resource_types": sorted(SUPPORTED_FHIR_TYPES),
            "row_counts": {table: len(rows) for table, rows in self._rows.items()},
            "vocab_targets": {"condition": "SNOMED", "drug": "RxNorm", "measurement": "LOINC"},
            "concept_id_policy": "zero_until_governed_vocabulary_mapping_is_loaded",
            "status": "RESEARCH_SUBSET",
            "persistence": "none",
            "external_transmission": False,
        }
