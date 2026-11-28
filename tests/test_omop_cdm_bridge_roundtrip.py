from __future__ import annotations

import copy

import pytest

from engines.omop_cdm_bridge import OMOPCDMBridge


def _bundle() -> dict:
    patient = {
        "resourceType": "Patient",
        "id": "synthetic-patient-1",
        "gender": "female",
        "birthDate": "1988-06-15",
    }
    condition = {
        "resourceType": "Condition",
        "id": "synthetic-condition-1",
        "subject": {"reference": "Patient/synthetic-patient-1"},
        "clinicalStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                "code": "active",
            }]
        },
        "code": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "44054006",
                "display": "Type 2 diabetes mellitus",
            }],
            "text": "Type 2 diabetes mellitus",
        },
        "onsetDateTime": "2025-01-02T08:00:00Z",
    }
    observation = {
        "resourceType": "Observation",
        "id": "synthetic-observation-1",
        "status": "final",
        "subject": {"reference": "Patient/synthetic-patient-1"},
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "718-7",
                "display": "Hemoglobin",
            }],
            "text": "Hemoglobin",
        },
        "effectiveDateTime": "2025-01-03T08:30:00-05:00",
        "valueQuantity": {
            "value": 13.2,
            "unit": "g/dL",
            "system": "http://unitsofmeasure.org",
            "code": "g/dL",
        },
    }
    medication = {
        "resourceType": "MedicationStatement",
        "id": "synthetic-medication-1",
        "status": "active",
        "subject": {"reference": "Patient/synthetic-patient-1"},
        "effectivePeriod": {"start": "2025-01-04T10:00:00Z", "end": "2025-01-10"},
        "medicationCodeableConcept": {
            "coding": [{
                "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                "code": "1049502",
                "display": "Synthetic example medication",
            }],
            "text": "Synthetic example medication",
        },
    }
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [{"resource": item} for item in (patient, condition, observation, medication)],
    }


def test_fhir_import_requires_explicit_person_identity_assignment() -> None:
    bridge = OMOPCDMBridge()

    with pytest.raises(ValueError, match="explicit person_id"):
        bridge.from_fhir_bundle(_bundle())


def test_supported_synthetic_bundle_maps_to_omop_and_roundtrips() -> None:
    source = _bundle()
    bridge = OMOPCDMBridge()

    result = bridge.from_fhir_bundle(source, person_id=41)

    assert result["mapped_resources"] == 4
    assert result["skipped_resources"] == []
    assert result["tables"] == {
        "PERSON": 1,
        "CONDITION_OCCURRENCE": 1,
        "DRUG_EXPOSURE": 1,
        "MEASUREMENT": 1,
    }
    tables = bridge.export_tables()
    assert tables["PERSON"][0]["person_id"] == 41
    assert tables["PERSON"][0]["year_of_birth"] == 1988
    assert tables["PERSON"][0]["gender_concept_id"] == 8532
    assert tables["CONDITION_OCCURRENCE"][0]["condition_start_date"] == "2025-01-02"
    assert tables["CONDITION_OCCURRENCE"][0]["condition_source_value"] == (
        "http://snomed.info/sct|44054006"
    )
    assert tables["MEASUREMENT"][0]["measurement_date"] == "2025-01-03"
    assert tables["MEASUREMENT"][0]["value_as_number"] == 13.2
    assert tables["MEASUREMENT"][0]["unit_source_value"] == "g/dL"
    assert tables["DRUG_EXPOSURE"][0]["drug_exposure_start_date"] == "2025-01-04"
    assert tables["DRUG_EXPOSURE"][0]["quantity"] is None
    assert tables["DRUG_EXPOSURE"][0]["drug_source_value"] == (
        "http://www.nlm.nih.gov/research/umls/rxnorm|1049502"
    )

    exported = bridge.to_fhir_bundle()
    assert exported["resourceType"] == "Bundle"
    assert exported["type"] == "collection"
    assert [entry["resource"] for entry in exported["entry"]] == [
        entry["resource"] for entry in source["entry"]
    ]


def test_multiple_patients_need_a_distinct_explicit_mapping() -> None:
    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {"resource": {"resourceType": "Patient", "id": "synthetic-patient-a"}},
            {"resource": {"resourceType": "Patient", "id": "synthetic-patient-b"}},
        ],
    }
    bridge = OMOPCDMBridge()

    with pytest.raises(ValueError, match="person_id_map"):
        bridge.from_fhir_bundle(bundle, person_id=10)

    with pytest.raises(ValueError, match="unique"):
        bridge.from_fhir_bundle(
            bundle,
            person_id_map={"synthetic-patient-a": 10, "synthetic-patient-b": 10},
        )

    result = bridge.from_fhir_bundle(
        bundle,
        person_id_map={"synthetic-patient-a": 10, "synthetic-patient-b": 11},
    )
    assert result["mapped_resources"] == 2
    assert [row["person_id"] for row in bridge.export_tables()["PERSON"]] == [10, 11]


def test_missing_patient_resource_is_rejected_instead_of_assigning_person_one() -> None:
    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [{
            "resource": {
                "resourceType": "Observation",
                "id": "synthetic-observation-orphan",
                "status": "final",
                "subject": {"reference": "Patient/synthetic-missing"},
                "code": {"text": "Synthetic lab"},
                "effectiveDateTime": "2025-01-03",
                "valueQuantity": {"value": 1.0, "unit": "unit"},
            }
        }],
    }

    with pytest.raises(ValueError, match="Patient resource"):
        OMOPCDMBridge().from_fhir_bundle(
            bundle,
            person_id_map={"synthetic-missing": 41},
        )


def test_non_finite_observation_values_are_rejected() -> None:
    bundle = _bundle()
    observation = bundle["entry"][2]["resource"]
    observation["valueQuantity"]["value"] = float("nan")

    with pytest.raises(ValueError, match="finite"):
        OMOPCDMBridge().from_fhir_bundle(bundle, person_id=41)


def test_non_final_observations_are_reported_as_skipped() -> None:
    bundle = _bundle()
    observation = bundle["entry"][2]["resource"]
    observation["status"] = "preliminary"

    result = OMOPCDMBridge().from_fhir_bundle(bundle, person_id=41)

    assert result["mapped_resources"] == 3
    assert result["skipped_resources"] == [{
        "resource_type": "Observation",
        "resource_id": "synthetic-observation-1",
        "reason": "non_final_status",
    }]
    assert "MEASUREMENT" not in result["tables"]


def test_declared_but_unimplemented_resource_types_are_not_fabricated() -> None:
    bundle = _bundle()
    bundle["entry"].append({
        "resource": {
            "resourceType": "DiagnosticReport",
            "id": "synthetic-report-1",
            "status": "final",
            "subject": {"reference": "Patient/synthetic-patient-1"},
            "code": {"text": "Synthetic panel"},
        }
    })

    bridge = OMOPCDMBridge()
    result = bridge.from_fhir_bundle(bundle, person_id=41)

    assert result["mapped_resources"] == 4
    assert result["skipped_resources"] == [{
        "resource_type": "DiagnosticReport",
        "resource_id": "synthetic-report-1",
        "reason": "unsupported_mapping",
    }]
    assert len(bridge.export_tables()["MEASUREMENT"]) == 1


def test_invalid_bundle_is_rejected() -> None:
    with pytest.raises(ValueError, match="FHIR Bundle"):
        OMOPCDMBridge().from_fhir_bundle({"resourceType": "Patient", "id": "p1"})


def test_medication_request_is_not_misrepresented_as_actual_drug_exposure() -> None:
    bundle = _bundle()
    bundle["entry"][3]["resource"] = {
        "resourceType": "MedicationRequest",
        "id": "synthetic-medication-order-1",
        "status": "active",
        "subject": {"reference": "Patient/synthetic-patient-1"},
        "authoredOn": "2025-01-04",
        "medicationCodeableConcept": {"text": "Synthetic medication order"},
    }

    bridge = OMOPCDMBridge()
    result = bridge.from_fhir_bundle(bundle, person_id=41)

    assert result["mapped_resources"] == 3
    assert result["skipped_resources"] == [{
        "resource_type": "MedicationRequest",
        "resource_id": "synthetic-medication-order-1",
        "reason": "unsupported_mapping",
    }]
    assert "DRUG_EXPOSURE" not in bridge.export_tables()


def test_recorded_date_is_not_misrepresented_as_condition_onset() -> None:
    bundle = _bundle()
    condition = bundle["entry"][1]["resource"]
    condition.pop("onsetDateTime")
    condition["recordedDate"] = "2025-01-02"

    with pytest.raises(ValueError, match="Condition onset date"):
        OMOPCDMBridge().from_fhir_bundle(bundle, person_id=41)


def test_optional_patient_gender_and_code_text_are_not_fabricated_as_nulls() -> None:
    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {"resource": {"resourceType": "Patient", "id": "synthetic-patient-no-gender"}},
            {"resource": {
                "resourceType": "Observation",
                "id": "synthetic-observation-no-text",
                "status": "final",
                "subject": {"reference": "Patient/synthetic-patient-no-gender"},
                "code": {"coding": [{"system": "http://loinc.org", "code": "718-7"}]},
                "effectiveDateTime": "2025-01-03",
                "valueQuantity": {"value": 13.2, "unit": "g/dL"},
            }},
        ],
    }

    exported = OMOPCDMBridge().from_fhir_bundle(bundle, person_id=7)
    assert exported["mapped_resources"] == 2
    bridge = OMOPCDMBridge()
    bridge.from_fhir_bundle(bundle, person_id=7)
    resources = [entry["resource"] for entry in bridge.to_fhir_bundle()["entry"]]
    assert "gender" not in resources[0]
    assert "text" not in resources[1]["code"]


def test_import_failure_does_not_partially_mutate_bridge_state() -> None:
    bridge = OMOPCDMBridge()
    before = copy.deepcopy(bridge.export_tables())
    bundle = _bundle()
    bundle["entry"][2]["resource"]["valueQuantity"]["value"] = float("inf")

    with pytest.raises(ValueError):
        bridge.from_fhir_bundle(bundle, person_id=41)

    assert bridge.export_tables() == before
