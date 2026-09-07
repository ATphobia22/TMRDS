"""
OHDSI Atlas Cohort Definition Adapter for TMRDS.

Atlas cohort anatomy (Book of OHDSI / Circe):
  ConceptSets → PrimaryCriteria (entry events) → InclusionRules →
  EndStrategy / CensoringCriteria → CollapseSettings

Export path: Atlas UI → EXPORT/JSON or ROhdsiWebApi::exportCohortDefinitionSet
Library: https://ohdsi.github.io/PhenotypeLibrary/
Atlas phenotype instance: https://atlas-phenotype.ohdsi.org

This module validates structure and wraps definitions for TMRDS phenotype engine.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional


REQUIRED_ATLAS_KEYS = (
    "ConceptSets",
    "PrimaryCriteria",
    "InclusionRules",
)


class OHDSIAtlasCohortAdapter:
    """Inspect and register Atlas/Circe cohort definition JSON."""

    def __init__(self) -> None:
        self._registry: Dict[str, Dict[str, Any]] = {}

    def validate(self, cohort_json: Dict[str, Any]) -> Dict[str, Any]:
        missing = [k for k in REQUIRED_ATLAS_KEYS if k not in cohort_json]
        concept_sets = cohort_json.get("ConceptSets") or []
        inclusion = cohort_json.get("InclusionRules") or []
        primary = cohort_json.get("PrimaryCriteria") or {}
        return {
            "valid_structure": len(missing) == 0,
            "missing_keys": missing,
            "concept_set_count": len(concept_sets) if isinstance(concept_sets, list) else 0,
            "inclusion_rule_count": len(inclusion) if isinstance(inclusion, list) else 0,
            "has_primary_criteria": bool(primary),
            "cdm_version_range": cohort_json.get("cdmVersionRange"),
            "note": "Full Circe validation requires OHDSI CirceR / Atlas WebAPI",
        }

    def register(
        self,
        cohort_id: str,
        cohort_name: str,
        cohort_json: Dict[str, Any],
        clinical_description: str = "",
    ) -> Dict[str, Any]:
        report = self.validate(cohort_json)
        entry = {
            "cohort_id": cohort_id,
            "cohort_name": cohort_name,
            "clinical_description": clinical_description,
            "validation": report,
            "json": cohort_json,
            "registered_at": time.time(),
            "source_format": "Atlas_Circe_JSON",
        }
        self._registry[str(cohort_id)] = entry
        return {
            "cohort_id": cohort_id,
            "cohort_name": cohort_name,
            "validation": report,
            "status": "REGISTERED" if report["valid_structure"] else "REGISTERED_WITH_WARNINGS",
        }

    def skeleton(self, name: str = "New cohort") -> Dict[str, Any]:
        """Minimal Circe-like skeleton for educational / inspection use."""
        return {
            "ConceptSets": [],
            "PrimaryCriteria": {
                "CriteriaList": [],
                "ObservationWindow": {"PriorDays": 0, "PostDays": 0},
                "PrimaryCriteriaLimit": {"Type": "First"},
            },
            "QualifiedLimit": {"Type": "First"},
            "ExpressionLimit": {"Type": "First"},
            "InclusionRules": [],
            "CensoringCriteria": [],
            "CollapseSettings": {"CollapseType": "ERA", "EraPad": 0},
            "CensorWindow": {},
            "EndStrategy": {},
            "cdmVersionRange": ">=5.0.0",
            "_tmrds_note": f"Skeleton for '{name}' — populate ConceptSets in Atlas",
        }

    def list_registered(self) -> List[Dict[str, str]]:
        return [
            {"cohort_id": e["cohort_id"], "cohort_name": e["cohort_name"]}
            for e in self._registry.values()
        ]

    def status(self) -> Dict[str, Any]:
        return {
            "node": "OHDSIAtlasCohortAdapter",
            "registered": len(self._registry),
            "required_keys": list(REQUIRED_ATLAS_KEYS),
            "refs": [
                "https://ohdsi.github.io/PhenotypeLibrary/",
                "https://atlas-phenotype.ohdsi.org",
                "Book of OHDSI — Cohorts",
            ],
            "status": "READY",
        }
