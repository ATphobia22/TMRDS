"""
FHIR Interoperability & Data Portability Layer.
Extracts clinical data from strict HL7 FHIR R4/R5 schema payloads.
Production module for TMRDS.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List


class IntegratedEHRBridge:
    """FHIR Bundle parser → flattened analytical structure."""

    @staticmethod
    def parse_fhir_bundle(fhir_payload: str) -> Dict[str, Any]:
        """
        Converts deeply nested FHIR JSON into a flattened analytical structure.

        Parameters
        ----------
        fhir_payload : str
            Raw JSON string of a FHIR Bundle.

        Returns
        -------
        dict
            Parsed patient, observations, conditions, and status.
        """
        try:
            data = json.loads(fhir_payload)
            bundle_type = data.get("type", "unknown")
            entries: List[Dict[str, Any]] = data.get("entry", [])

            patient_info: Dict[str, Any] = {}
            observations: Dict[str, Any] = {}
            conditions: List[str] = []

            for entry in entries:
                resource = entry.get("resource", {})
                rtype = resource.get("resourceType")

                if rtype == "Patient":
                    patient_info["id"] = resource.get("id")
                    patient_info["gender"] = resource.get("gender")
                elif rtype == "Observation":
                    code = resource.get("code", {}).get("text", "Unknown")
                    val = resource.get("valueQuantity", {}).get("value")
                    observations[code] = val
                elif rtype == "Condition":
                    conditions.append(
                        resource.get("code", {}).get("text", "Unknown")
                    )

            return {
                "status": "FHIR_PARSED_SUCCESS",
                "bundle_type": bundle_type,
                "patient": patient_info,
                "observations": observations,
                "conditions": conditions,
            }
        except Exception as exc:  # noqa: BLE001
            return {"status": "FHIR_PARSE_ERROR", "error": str(exc)}
