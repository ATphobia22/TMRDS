"""Synthetic-only FHIR R4 research workbench: labs, terminology, imaging metadata.

No patient records, image pixels, diagnosis, reference-range interpretation,
remote transmission, or durable clinical review. Inputs must be generated for
testing and still cannot prove that data were genuinely synthetic.
"""
from __future__ import annotations

import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from urllib.parse import quote

from engines.fhir_interoperability import FHIRInteroperabilityConfig, FHIRResourceValidator

_LOINC = re.compile(r"[0-9]{1,7}-[0-9]\Z")
_SYNTHETIC_ID = re.compile(r"synthetic-[A-Za-z0-9.-]{1,64}\Z")
_UCUM = re.compile(r"[A-Za-z0-9%/.*^{}\[\]_-]{1,40}\Z")
_TAG = {"system": "urn:tmrds:data-classification", "code": "synthetic"}
_OBS_KEYS = frozenset({
    "resourceType", "id", "meta", "status", "code", "effectiveDateTime",
    "valueQuantity", "referenceRange",
})
_STUDY_KEYS = frozenset({"resourceType", "id", "meta", "status", "started", "series"})
_LAB_TERMS = {
    "718-7": "hemoglobin",
    "4548-4": "hemoglobin A1c",
    "2345-7": "glucose",
    "2160-0": "creatinine",
    "2951-2": "sodium",
    "2823-3": "potassium",
    "6690-2": "leukocytes",
    "777-3": "platelets",
}
_ALLOWED_STATUS = frozenset({"registered", "preliminary", "final", "amended", "corrected"})
_ALLOWED_MODALITY = frozenset({"CR", "DX", "CT", "MR", "US", "MG", "NM", "PT", "XA"})
_FHIR_VALIDATOR = FHIRResourceValidator(FHIRInteroperabilityConfig())


def _timestamp(value: object, label: str) -> str:
    if not isinstance(value, str) or len(value) > 64:
        raise ValueError(f"{label} requires a bounded ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} requires an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must include a timezone")
    if not 1900 <= parsed.year <= datetime.now(timezone.utc).year + 1:
        raise ValueError(f"{label} year outside expected test range")
    return parsed.astimezone(timezone.utc).isoformat()


def _synthetic(resource: object, kind: str, allowed: frozenset[str]) -> dict:
    if not isinstance(resource, dict) or set(resource) - allowed:
        raise ValueError("unsupported fields: identifiable records and non-test inputs are prohibited")
    if resource.get("resourceType") != kind:
        raise ValueError(f"expected FHIR R4 {kind}")
    identity = resource.get("id")
    if not isinstance(identity, str) or not _SYNTHETIC_ID.fullmatch(identity):
        raise ValueError("test resource id must start with synthetic-")
    if _FHIR_VALIDATOR.validate(resource):
        raise ValueError("invalid FHIR R4 resource structure")
    if resource.get("meta") != {"tag": [_TAG]}:
        raise ValueError("explicit synthetic test classification is required")
    return resource


def _quantity(obj: object, *, label: str) -> dict:
    if not isinstance(obj, dict) or set(obj) != {"value", "system", "code", "unit"}:
        raise ValueError(f"{label} must contain only value, UCUM system, code and unit")
    if obj["system"] != "http://unitsofmeasure.org":
        raise ValueError(f"{label} must carry the UCUM system")
    if not isinstance(obj["code"], str) or not _UCUM.fullmatch(obj["code"]):
        raise ValueError(f"{label} requires bounded UCUM unit code")
    if not isinstance(obj["unit"], str) or not 1 <= len(obj["unit"]) <= 48:
        raise ValueError(f"{label} requires display unit")
    value = obj["value"]
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or abs(value) > 1e12:
        raise ValueError(f"{label} requires finite numeric test result")
    return {"value": value, "code": obj["code"], "unit": obj["unit"]}


def _range(obj: object, code: str) -> dict:
    if not isinstance(obj, dict) or not obj or set(obj) - {"low", "high"}:
        raise ValueError("referenceRange must contain only low/high")
    result: dict = {}
    for limit in ("low", "high"):
        if limit in obj:
            quantity = _quantity(obj[limit], label="reference limit")
            if quantity["code"] != code:
                raise ValueError("reference range unit must match result UCUM code")
            result[limit] = quantity["value"]
    if result.get("high", float("inf")) < result.get("low", float("-inf")):
        raise ValueError("reference low exceeds high")
    return result


def synthetic_lab_trends(resources: list[dict]) -> dict:
    """Summarize test-only lab values; differences are arithmetic, never diagnosis."""
    if not isinstance(resources, list) or not 1 <= len(resources) <= 100:
        raise ValueError("supply 1-100 synthetic FHIR observations")
    seen: set[str] = set()
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for item in resources:
        obs = _synthetic(item, "Observation", _OBS_KEYS)
        if obs["id"] in seen:
            raise ValueError("duplicate synthetic resource id")
        seen.add(obs["id"])
        if obs.get("status") not in _ALLOWED_STATUS:
            raise ValueError("unsupported observation status")
        coding = obs.get("code", {}).get("coding") if isinstance(obs.get("code"), dict) else None
        if not isinstance(coding, list) or len(coding) != 1 or set(coding[0]) != {"system", "code"}:
            raise ValueError("one LOINC code is required")
        coded = coding[0]
        if coded["system"] != "http://loinc.org" or not isinstance(coded["code"], str) or not _LOINC.fullmatch(coded["code"]):
            raise ValueError("only LOINC test identifiers supported")
        at = _timestamp(obs.get("effectiveDateTime"), "effectiveDateTime")
        quantity = _quantity(obs.get("valueQuantity"), label="valueQuantity")
        refs = obs.get("referenceRange", [])
        if not isinstance(refs, list) or len(refs) > 1:
            raise ValueError("at most one synthetic laboratory reference range is supported")
        reported_range = _range(refs[0], quantity["code"]) if refs else None
        grouped[(coded["code"], quantity["code"])].append({
            "synthetic_id": obs["id"], "collected_at": at, "value": quantity["value"],
            "unit": quantity["unit"], "status": obs["status"], "source_reference_range": reported_range,
        })
    trends = []
    for (loinc, unit), values in sorted(grouped.items()):
        values.sort(key=lambda v: (v["collected_at"], v["synthetic_id"]))
        first, last = values[0], values[-1]
        delta = float(last["value"]) - float(first["value"]) if len(values) > 1 else None
        trends.append({
            "loinc": loinc, "label": _LAB_TERMS.get(loinc, f"LOINC {loinc}"),
            "loinc_url": f"https://loinc.org/{loinc}/", "ucum_code": unit,
            "measurements": values, "arithmetic_delta": delta, "delta_interpretation": "NOT_EVALUATED",
            "literature_lookup": (
                f"https://pubmed.ncbi.nlm.nih.gov/?term={quote(_LAB_TERMS[loinc])}"
                if loinc in _LAB_TERMS else None
            ),
            "reference_intervals_are_unverified": True,
        })
    return {
        "status": "synthetic-research-demo", "human_authority_final": True,
        "clinical_promotion_allowed": False, "patient_data_accepted": False,
        "diagnosis_performed": False, "external_data_transmitted": False,
        "review_state": "NOT_CLINICALLY_REVIEWED", "trends": trends,
    }


def synthetic_imaging_index(studies: list[dict]) -> dict:
    """Index FHIR ImagingStudy test metadata; no pixel retrieval or image inference."""
    if not isinstance(studies, list) or not 1 <= len(studies) <= 40:
        raise ValueError("supply 1-40 synthetic FHIR ImagingStudy metadata records")
    entries = []
    seen: set[str] = set()
    for item in studies:
        study = _synthetic(item, "ImagingStudy", _STUDY_KEYS)
        if study["id"] in seen:
            raise ValueError("duplicate synthetic imaging study id")
        seen.add(study["id"])
        if study.get("status") not in {"available", "registered", "cancelled"}:
            raise ValueError("invalid ImagingStudy status")
        started = _timestamp(study.get("started"), "started")
        series = study.get("series", [])
        if not isinstance(series, list) or not 1 <= len(series) <= 40:
            raise ValueError("synthetic imaging study requires 1-40 series")
        entries_series = []
        for value in series:
            if not isinstance(value, dict) or set(value) != {"modality", "numberOfInstances"}:
                raise ValueError("series must contain only modality and numberOfInstances")
            modality = value["modality"]
            if not isinstance(modality, dict) or set(modality) != {"system", "code"}:
                raise ValueError("series modality requires DICOM code and system")
            if modality["system"] != "http://dicom.nema.org/resources/ontology/DCM" or modality["code"] not in _ALLOWED_MODALITY:
                raise ValueError("unsupported DICOM modality")
            count = value["numberOfInstances"]
            if isinstance(count, bool) or not isinstance(count, int) or not 0 <= count <= 100000:
                raise ValueError("numberOfInstances must be bounded")
            entries_series.append({"modality": modality["code"], "number_of_instances": count})
        entries.append({
            "synthetic_id": study["id"], "started_at": started,
            "status": study["status"], "series": entries_series,
            "dicom_pixels_loaded": False, "ai_inference_performed": False,
        })
    return {
        "status": "synthetic-research-demo", "human_authority_final": True,
        "clinical_promotion_allowed": False, "patient_data_accepted": False,
        "studies": entries, "viewer_link": None, "image_transfer_enabled": False,
    }
