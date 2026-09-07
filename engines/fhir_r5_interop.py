"""
FHIR R5 interoperability awareness layer for TMRDS.
Production US exchange remains FHIR R4 + US Core (ONC / USCDI path).
US Core skips R5 and plans R6; R5 is optional research surface.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

R5_NEW_OR_NOTABLE = [
    "SubscriptionTopic", "SubscriptionStatus", "InventoryItem", "InventoryReport",
    "Transport", "GenomicStudy", "FormularyItem",
]
R4_TO_R5_NOTES = {
    "Subscription": "R5 splits topic definition into SubscriptionTopic + channel binding",
    "Encounter": "R5 expands journey modeling; map carefully from R4 Encounter",
    "Appointment": "R5 adds subject and RecurrenceTemplate patterns",
    "Device": "Align with PHD IG; MDC codes remain valid across versions",
}

class FHIRR5Interop:
    def __init__(self, preferred: str = "R4") -> None:
        self.preferred = preferred if preferred in ("R4", "R5") else "R4"

    def capability_statement(self) -> Dict[str, Any]:
        return {
            "resourceType": "CapabilityStatement",
            "status": "active",
            "date": "2026-09-07",
            "kind": "instance",
            "fhirVersion": "4.0.1" if self.preferred == "R4" else "5.0.0",
            "format": ["json"],
            "rest": [{
                "mode": "server",
                "resource": [
                    {"type": "Patient", "interaction": [{"code": "read"}, {"code": "search-type"}]},
                    {"type": "Condition", "interaction": [{"code": "read"}, {"code": "search-type"}]},
                    {"type": "Observation", "interaction": [{"code": "read"}, {"code": "search-type"}]},
                    {"type": "DiagnosticReport", "interaction": [{"code": "read"}]},
                    {"type": "MedicationRequest", "interaction": [{"code": "read"}]},
                    {"type": "Encounter", "interaction": [{"code": "read"}]},
                ],
            }],
            "tmrds": {
                "production_default": "R4_US_Core",
                "r5_support": "research_optional",
                "us_core_note": "US Core v9 remains on R4; no US Core R5 — R6 planned",
                "r5_notable_resources": R5_NEW_OR_NOTABLE,
                "migration_notes": R4_TO_R5_NOTES,
            },
        }

    def normalize_version(self, resource: Dict[str, Any], target: Optional[str] = None) -> Dict[str, Any]:
        tgt = target or self.preferred
        out = dict(resource)
        meta = dict(out.get("meta") or {})
        meta["tmrdsFhirTarget"] = tgt
        out["meta"] = meta
        return out

    def status(self) -> Dict[str, Any]:
        return {
            "node": "FHIRR5Interop",
            "preferred": self.preferred,
            "production": "R4_US_Core",
            "r5": "optional_research",
            "status": "READY",
        }
