"""
IEEE 11073 Personal Health Device bridge for TMRDS.

Maps PHD-style observations into FHIR R4 Observation skeletons per
HL7 Personal Health Device Implementation Guide (Devices on FHIR).

Standards:
  - IEEE 11073-10206 Abstract Content Model
  - IEEE 11073-10101 nomenclature (MDC codes)
  - HL7 FHIR PHD IG (build.fhir.org/ig/HL7/phd)

Ingest path: Device → Personal Health Gateway → FHIR Observation →
UniversalClinicalIngest / OMOP MEASUREMENT.
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional


# Common MDC codes (IEEE 11073-10101) — illustrative subset
MDC_CODES = {
    "blood_pressure_systolic": {"code": "150017", "display": "MDC_PRESS_BLD_SYS"},
    "blood_pressure_diastolic": {"code": "150018", "display": "MDC_PRESS_BLD_DIA"},
    "heart_rate": {"code": "147842", "display": "MDC_ECG_HEART_RATE"},
    "body_weight": {"code": "188736", "display": "MDC_MASS_BODY_ACTUAL"},
    "body_temperature": {"code": "150364", "display": "MDC_TEMP_BODY"},
    "spo2": {"code": "150456", "display": "MDC_PULS_OXIM_SAT_O2"},
    "glucose": {"code": "160184", "display": "MDC_CONC_GLU_GEN"},
}


class IEEE11073PHDBridge:
    """Convert PHD measurements to FHIR Observations with MDC coding."""

    def observation(
        self,
        patient_id: str,
        metric: str,
        value: float,
        unit: str,
        device_id: Optional[str] = None,
        loinc: Optional[str] = None,
    ) -> Dict[str, Any]:
        mdc = MDC_CODES.get(metric, {"code": "0", "display": metric})
        coding = [
            {
                "system": "urn:iso:std:iso:11073:10101",
                "code": mdc["code"],
                "display": mdc["display"],
            }
        ]
        if loinc:
            coding.append({"system": "http://loinc.org", "code": loinc})
        res: Dict[str, Any] = {
            "resourceType": "Observation",
            "id": f"phd-{uuid.uuid4().hex[:10]}",
            "meta": {
                "profile": [
                    "http://hl7.org/fhir/uv/phd/StructureDefinition/PhdNumericObservation"
                ]
            },
            "status": "final",
            "code": {"coding": coding, "text": metric},
            "subject": {"reference": f"Patient/{patient_id}"},
            "effectiveDateTime": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "valueQuantity": {
                "value": value,
                "unit": unit,
                "system": "http://unitsofmeasure.org",
            },
        }
        if device_id:
            res["device"] = {"reference": f"Device/{device_id}"}
        return res

    def from_telemetry_batch(
        self,
        patient_id: str,
        readings: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        obs = []
        for r in readings:
            obs.append(
                self.observation(
                    patient_id,
                    metric=str(r.get("metric", "unknown")),
                    value=float(r.get("value", 0)),
                    unit=str(r.get("unit", "")),
                    device_id=r.get("device_id"),
                    loinc=r.get("loinc"),
                )
            )
        return {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [{"resource": o} for o in obs],
            "count": len(obs),
            "standard": "IEEE_11073_PHD_FHIR",
        }

    def status(self) -> Dict[str, Any]:
        return {
            "node": "IEEE11073PHDBridge",
            "metrics": list(MDC_CODES.keys()),
            "ig": "HL7 Personal Health Device IG",
            "status": "READY",
        }
