"""
FHIR R4 / US Core Resource Mapper for TMRDS.
Maps clinical facts into US Core–aligned FHIR resource skeletons and
supports HL7 v2 → FHIR segment patterns used by HIEs (PID, DG1, OBX, OBR).

Reference: HL7 US Core IG, USCDI; HL7 v2→FHIR (PID→Patient, DG1→Condition,
OBX→Observation, OBR→DiagnosticReport/ServiceRequest).
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional


class FHIRUSCoreMapper:
    """Produce minimal US Core–shaped FHIR R4 resources from structured clinical input."""

    US_CORE_RESOURCES = (
        "Patient",
        "Condition",
        "Observation",
        "DiagnosticReport",
        "MedicationRequest",
        "Procedure",
        "AllergyIntolerance",
        "Encounter",
        "Immunization",
        "DocumentReference",
        "ServiceRequest",
        "Specimen",
    )

    def __init__(self) -> None:
        self._created: List[str] = []

    def patient(
        self,
        patient_id: str,
        family: str = "",
        given: str = "",
        birth_date: Optional[str] = None,
        gender: Optional[str] = None,
    ) -> Dict[str, Any]:
        res = {
            "resourceType": "Patient",
            "id": patient_id,
            "meta": {"profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"]},
            "identifier": [{"system": "urn:tmrds:patient", "value": patient_id}],
            "name": [{"family": family, "given": [given] if given else []}],
        }
        if birth_date:
            res["birthDate"] = birth_date
        if gender:
            res["gender"] = gender
        self._created.append("Patient")
        return res

    def condition(
        self,
        patient_id: str,
        code: str,
        display: str,
        system: str = "http://snomed.info/sct",
        clinical_status: str = "active",
    ) -> Dict[str, Any]:
        res = {
            "resourceType": "Condition",
            "id": f"cond-{uuid.uuid4().hex[:10]}",
            "meta": {"profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-condition-problems-health-concerns"]},
            "clinicalStatus": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": clinical_status,
                }]
            },
            "code": {"coding": [{"system": system, "code": code, "display": display}], "text": display},
            "subject": {"reference": f"Patient/{patient_id}"},
            "recordedDate": time.strftime("%Y-%m-%d"),
        }
        self._created.append("Condition")
        return res

    def observation_lab(
        self,
        patient_id: str,
        loinc: str,
        display: str,
        value: Any,
        unit: Optional[str] = None,
        interpretation: Optional[str] = None,
    ) -> Dict[str, Any]:
        res: Dict[str, Any] = {
            "resourceType": "Observation",
            "id": f"obs-{uuid.uuid4().hex[:10]}",
            "meta": {"profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-observation-lab"]},
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "laboratory",
                }]
            }],
            "code": {
                "coding": [{"system": "http://loinc.org", "code": loinc, "display": display}],
                "text": display,
            },
            "subject": {"reference": f"Patient/{patient_id}"},
            "effectiveDateTime": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        if isinstance(value, (int, float)):
            res["valueQuantity"] = {"value": value, "unit": unit or "", "system": "http://unitsofmeasure.org"}
        else:
            res["valueString"] = str(value)
        if interpretation:
            res["interpretation"] = [{"coding": [{"code": interpretation}]}]
        self._created.append("Observation")
        return res

    def diagnostic_report(
        self,
        patient_id: str,
        code: str,
        display: str,
        observation_ids: Optional[List[str]] = None,
        category: str = "LAB",
    ) -> Dict[str, Any]:
        res = {
            "resourceType": "DiagnosticReport",
            "id": f"dr-{uuid.uuid4().hex[:10]}",
            "meta": {"profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-diagnosticreport-lab"]},
            "status": "final",
            "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0074", "code": category}]}],
            "code": {"coding": [{"code": code, "display": display}], "text": display},
            "subject": {"reference": f"Patient/{patient_id}"},
            "issued": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "result": [{"reference": f"Observation/{oid}"} for oid in (observation_ids or [])],
        }
        self._created.append("DiagnosticReport")
        return res

    def medication_request(
        self,
        patient_id: str,
        rxnorm: str,
        display: str,
        status: str = "active",
    ) -> Dict[str, Any]:
        res = {
            "resourceType": "MedicationRequest",
            "id": f"medreq-{uuid.uuid4().hex[:10]}",
            "meta": {"profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-medicationrequest"]},
            "status": status,
            "intent": "order",
            "medicationCodeableConcept": {
                "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": rxnorm, "display": display}],
                "text": display,
            },
            "subject": {"reference": f"Patient/{patient_id}"},
            "authoredOn": time.strftime("%Y-%m-%d"),
        }
        self._created.append("MedicationRequest")
        return res

    def bundle(self, resources: List[Dict[str, Any]], bundle_type: str = "collection") -> Dict[str, Any]:
        return {
            "resourceType": "Bundle",
            "id": f"bun-{uuid.uuid4().hex[:10]}",
            "type": bundle_type,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "entry": [{"resource": r} for r in resources],
        }

    def from_lab_channel(self, patient_id: str, tests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Map UniversalClinicalIngest lab tests → Observation + DiagnosticReport bundle."""
        obs = []
        for t in tests:
            o = self.observation_lab(
                patient_id,
                loinc=str(t.get("loinc") or "unknown"),
                display=str(t.get("name") or "lab"),
                value=t.get("value"),
                unit=t.get("unit"),
                interpretation=t.get("flag"),
            )
            obs.append(o)
        report = self.diagnostic_report(
            patient_id,
            code="panel",
            display="Laboratory panel",
            observation_ids=[o["id"] for o in obs],
        )
        return self.bundle(obs + [report])

    def status(self) -> Dict[str, Any]:
        return {
            "node": "FHIRUSCoreMapper",
            "resources": list(self.US_CORE_RESOURCES),
            "created_counts": {r: self._created.count(r) for r in set(self._created)},
            "status": "READY",
        }
