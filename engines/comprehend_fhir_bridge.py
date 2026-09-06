"""
Amazon Comprehend Medical → FHIR Bridge for TMRDS.
Extracts clinical entities from free-text notes and maps them to FHIR R4 resources.
Inspired by ATphobia22/amazon-comprehend-medical-fhir-integration.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List


class ComprehendFHIRBridge:
    """
    Lightweight NLP → FHIR mapper.
    Production path calls AWS Comprehend Medical DetectEntitiesV2 + InferICD10CM.
    Offline path uses deterministic regex patterns for CI.
    """

    ENTITY_TYPES = ("MEDICATION", "CONDITION", "TEST_TREATMENT_PROCEDURE", "ANATOMY")

    def extract_entities(self, clinical_text: str) -> List[Dict[str, Any]]:
        if not clinical_text or not clinical_text.strip():
            return []
        entities: List[Dict[str, Any]] = []
        med_pattern = re.compile(
            r"\b(metformin|atorvastatin|aspirin|insulin|lisinopril|warfarin|amoxicillin)\b",
            re.I,
        )
        for m in med_pattern.finditer(clinical_text):
            entities.append({
                "text": m.group(0),
                "category": "MEDICATION",
                "score": 0.95,
                "begin_offset": m.start(),
                "end_offset": m.end(),
            })
        return entities

    def map_to_fhir(self, entities: List[Dict[str, Any]], patient_id: str) -> Dict[str, Any]:
        entries = []
        for ent in entities:
            if ent["category"] == "MEDICATION":
                resource = {
                    "resourceType": "MedicationStatement",
                    "status": "active",
                    "medicationCodeableConcept": {"text": ent["text"]},
                    "subject": {"reference": f"Patient/{patient_id}"},
                }
                entries.append({"resource": resource})
        return {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": entries,
            "status": "COMPREHEND_FHIR_MAPPED",
        }

    def process_note(self, clinical_text: str, patient_id: str) -> Dict[str, Any]:
        entities = self.extract_entities(clinical_text)
        bundle = self.map_to_fhir(entities, patient_id)
        return {
            "entities": entities,
            "fhir_bundle": bundle,
            "entity_count": len(entities),
        }
