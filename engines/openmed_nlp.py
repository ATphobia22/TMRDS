"""
OpenMedEngine — HIPAA PII scrubbing + Medical NER for TMRDS.
Offline-first NLP plane for rural clinical environments.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


_PII_PATTERNS: List[Tuple[str, str]] = [
    (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN_REDACTED]"),
    (r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", "[PHONE_REDACTED]"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL_REDACTED]"),
    (r"\b\d{1,5}\s+\w+\s+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr)\b", "[ADDRESS_REDACTED]"),
    (r"\b(?:MRN|Medical Record)[#:\s]*\d{5,}\b", "[MRN_REDACTED]"),
    (r"\b\d{2}/\d{2}/\d{4}\b", "[DATE_REDACTED]"),
]

_MEDICAL_ENTITY_PATTERNS: List[Tuple[str, str]] = [
    (r"\b(hypertension|diabetes|pneumonia|COPD|asthma|sepsis|CHF|CKD|CAD)\b", "CONDITION"),
    (r"\b(metformin|atorvastatin|lisinopril|aspirin|insulin|warfarin|amoxicillin)\b", "MEDICATION"),
    (r"\b(CBC|CMP|BNP|Troponin|HbA1c|PT/INR|D-dimer)\b", "LAB"),
    (r"\b(CT|MRI|X-ray|ultrasound|echocardiogram|EKG|ECG)\b", "PROCEDURE"),
]


class OpenMedEngine:
    """Offline NLP for HIPAA PII scrubbing and Medical NER."""

    def __init__(self) -> None:
        self.pii_compiled = [(re.compile(p, re.I), repl) for p, repl in _PII_PATTERNS]
        self.entity_compiled = [(re.compile(p, re.I), label) for p, label in _MEDICAL_ENTITY_PATTERNS]

    def scrub_pii(self, text: str) -> Dict[str, Any]:
        if not text:
            return {"original_length": 0, "scrubbed": "", "redactions": 0}
        scrubbed = text
        redactions = 0
        for regex, repl in self.pii_compiled:
            matches = list(regex.finditer(scrubbed))
            redactions += len(matches)
            scrubbed = regex.sub(repl, scrubbed)
        return {
            "original_length": len(text),
            "scrubbed": scrubbed,
            "redactions": redactions,
            "status": "SCRUBBED",
        }

    def extract_entities(self, text: str) -> Dict[str, Any]:
        entities: List[Dict[str, Any]] = []
        for regex, label in self.entity_compiled:
            for m in regex.finditer(text or ""):
                entities.append({
                    "text": m.group(0),
                    "label": label,
                    "start": m.start(),
                    "end": m.end(),
                })
        return {
            "entity_count": len(entities),
            "entities": entities,
            "status": "NER_COMPLETE",
        }

    def process(self, text: str) -> Dict[str, Any]:
        scrub = self.scrub_pii(text)
        ner = self.extract_entities(scrub["scrubbed"])
        return {
            "pii": scrub,
            "ner": ner,
            "mode": "OFFLINE_SOVEREIGN",
            "status": "OPENMED_COMPLETE",
        }

    def status(self) -> Dict[str, Any]:
        return {
            "node": "OpenMedEngine",
            "pii_patterns": len(self.pii_compiled),
            "entity_patterns": len(self.entity_compiled),
            "mode": "offline_first",
            "status": "READY",
        }
