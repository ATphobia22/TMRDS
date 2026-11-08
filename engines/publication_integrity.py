"""Preserve Europe PMC publication-type and correction metadata without clearance claims."""
from __future__ import annotations

from copy import deepcopy


def europe_pmc_integrity(record: dict) -> dict:
    types = (record.get("pubTypeList") or {}).get("pubType") or []
    if not isinstance(types, list) or any(not isinstance(t, str) for t in types):
        raise ValueError("invalid Europe PMC publication types")
    corrections = (record.get("commentCorrectionList") or {}).get("commentCorrection") or []
    if not isinstance(corrections, list) or any(not isinstance(c, dict) for c in corrections):
        raise ValueError("invalid Europe PMC correction metadata")
    normalized = {t.casefold() for t in types}
    retracted = ("retracted publication" in normalized
                 or str(record.get("isRetracted", "")).upper() == "Y"
                 or any(str(c.get("type", "")).casefold() == "retraction in" for c in corrections))
    return {
        "provider": "europe_pmc", "publication_types": deepcopy(types),
        "correction_links": deepcopy(corrections),
        "retraction_status": "retraction_reported" if retracted else "not_reported_in_retrieved_metadata",
        "is_retraction_notice": "retraction of publication" in normalized,
        "is_expression_of_concern": "expression of concern" in normalized,
        "assessment_scope": "source_metadata_only",
        "limitation": "Absence of a flag is not proof that a publication is unretracted or reliable.",
    }


def summarize_integrity(records: list[dict]) -> dict:
    metadata = [r["publication_integrity"] for r in records if r.get("publication_integrity")]
    if any(m.get("retraction_status") == "retraction_reported" for m in metadata):
        status = "retraction_reported"
    elif metadata:
        status = "not_reported_in_retrieved_metadata"
    else:
        status = "not_checked"
    return {"retraction_status": status,
            "integrity_sources": sorted({m["provider"] for m in metadata}),
            "integrity_review_required": True}
