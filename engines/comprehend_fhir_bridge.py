"""
Amazon Comprehend Medical → FHIR Bridge for TMRDS.
Production path: AWS DetectEntitiesV2 + InferICD10CM.
Fallback: deterministic offline extractor for CI / offline environments.
Inspired by ATphobia22/amazon-comprehend-medical-fhir-integration.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("TMRDS.ComprehendFHIR")

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False


class ComprehendFHIRBridge:
    """
    NLP → FHIR mapper.

    Production (AWS credentials present):
        - DetectEntitiesV2  → medications, conditions, procedures, anatomy
        - InferICD10CM      → ICD-10-CM codes

    Offline fallback uses curated regex patterns.
    """

    ENTITY_TYPES = ("MEDICATION", "CONDITION", "TEST_TREATMENT_PROCEDURE", "ANATOMY")

    def __init__(self, region: Optional[str] = None) -> None:
        self.region = region or os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        self.client = None
        if BOTO3_AVAILABLE:
            try:
                self.client = boto3.client("comprehendmedical", region_name=self.region)
                logger.info("AWS Comprehend Medical client initialized (%s)", self.region)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Comprehend client init failed, using offline mode: %s", exc)

    def _aws_detect_entities(self, text: str) -> List[Dict[str, Any]]:
        if self.client is None:
            return []
        try:
            response = self.client.detect_entities_v2(Text=text)
            entities = []
            for ent in response.get("Entities", []):
                entities.append({
                    "text": ent.get("Text"),
                    "category": ent.get("Category"),
                    "type": ent.get("Type"),
                    "score": ent.get("Score"),
                    "begin_offset": ent.get("BeginOffset"),
                    "end_offset": ent.get("EndOffset"),
                    "traits": [t.get("Name") for t in ent.get("Traits", [])],
                    "source": "AWS_DetectEntitiesV2",
                })
            return entities
        except (BotoCoreError, ClientError) as exc:
            logger.error("DetectEntitiesV2 failed: %s", exc)
            return []

    def _aws_infer_icd10(self, text: str) -> List[Dict[str, Any]]:
        if self.client is None:
            return []
        try:
            response = self.client.infer_icd10_cm(Text=text)
            codes = []
            for ent in response.get("Entities", []):
                for concept in ent.get("ICD10CMConcepts", []):
                    codes.append({
                        "code": concept.get("Code"),
                        "description": concept.get("Description"),
                        "score": concept.get("Score"),
                        "text": ent.get("Text"),
                        "source": "AWS_InferICD10CM",
                    })
            return codes
        except (BotoCoreError, ClientError) as exc:
            logger.error("InferICD10CM failed: %s", exc)
            return []

    def _offline_extract(self, clinical_text: str) -> List[Dict[str, Any]]:
        entities: List[Dict[str, Any]] = []
        patterns = {
            "MEDICATION": r"\b(metformin|atorvastatin|aspirin|insulin|lisinopril|warfarin|amoxicillin|losartan|omeprazole)\b",
            "CONDITION": r"\b(hypertension|diabetes|pneumonia|COPD|asthma|heart failure|sepsis)\b",
        }
        for category, pattern in patterns.items():
            for m in re.finditer(pattern, clinical_text, re.I):
                entities.append({
                    "text": m.group(0),
                    "category": category,
                    "score": 0.90,
                    "begin_offset": m.start(),
                    "end_offset": m.end(),
                    "source": "OFFLINE_REGEX",
                })
        return entities

    def extract_entities(self, clinical_text: str) -> List[Dict[str, Any]]:
        if not clinical_text or not clinical_text.strip():
            return []
        if self.client is not None:
            entities = self._aws_detect_entities(clinical_text)
            if entities:
                return entities
        return self._offline_extract(clinical_text)

    def infer_icd10(self, clinical_text: str) -> List[Dict[str, Any]]:
        if self.client is not None:
            return self._aws_infer_icd10(clinical_text)
        return []

    def map_to_fhir(
        self,
        entities: List[Dict[str, Any]],
        patient_id: str,
        icd10_codes: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        entries: List[Dict[str, Any]] = []
        for ent in entities:
            cat = (ent.get("category") or "").upper()
            if cat == "MEDICATION":
                resource = {
                    "resourceType": "MedicationStatement",
                    "status": "active",
                    "medicationCodeableConcept": {"text": ent.get("text")},
                    "subject": {"reference": f"Patient/{patient_id}"},
                }
                entries.append({"resource": resource})
            elif cat in ("CONDITION", "MEDICAL_CONDITION"):
                resource = {
                    "resourceType": "Condition",
                    "clinicalStatus": {"coding": [{"code": "active"}]},
                    "code": {"text": ent.get("text")},
                    "subject": {"reference": f"Patient/{patient_id}"},
                }
                entries.append({"resource": resource})

        if icd10_codes:
            for code in icd10_codes:
                resource = {
                    "resourceType": "Condition",
                    "clinicalStatus": {"coding": [{"code": "active"}]},
                    "code": {
                        "coding": [{
                            "system": "http://hl7.org/fhir/sid/icd-10-cm",
                            "code": code.get("code"),
                            "display": code.get("description"),
                        }],
                        "text": code.get("text"),
                    },
                    "subject": {"reference": f"Patient/{patient_id}"},
                }
                entries.append({"resource": resource})

        return {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": entries,
            "status": "COMPREHEND_FHIR_MAPPED",
            "mode": "AWS" if self.client else "OFFLINE",
        }

    def process_note(self, clinical_text: str, patient_id: str) -> Dict[str, Any]:
        entities = self.extract_entities(clinical_text)
        icd10 = self.infer_icd10(clinical_text)
        bundle = self.map_to_fhir(entities, patient_id, icd10)
        return {
            "entities": entities,
            "icd10_codes": icd10,
            "fhir_bundle": bundle,
            "entity_count": len(entities),
            "icd10_count": len(icd10),
            "mode": "AWS" if self.client else "OFFLINE",
        }
