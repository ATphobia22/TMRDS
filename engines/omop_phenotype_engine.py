"""
OMOP Phenotype Engine for TMRDS.
Implements OHDSI phenotype library patterns: clinical description +
computable cohort entry/inclusion/exit criteria against OMOP CDM domains.

Reference: OHDSI Phenotype Library (atlas-phenotype.ohdsi.org),
Book of OHDSI — Cohorts chapter.

A phenotype ≈ clinical idea; a cohort definition = computable chapter that
identifies persons of that phenotype for a duration of time.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional


# Seed phenotypes with domain concept placeholders (resolve via Athena in production)
SEED_PHENOTYPES: Dict[str, Dict[str, Any]] = {
    "type_2_diabetes": {
        "title": "Type 2 diabetes mellitus",
        "clinical_overview": (
            "Chronic metabolic disorder characterized by hyperglycemia due to "
            "insulin resistance and relative insulin deficiency."
        ),
        "entry_domain": "CONDITION_OCCURRENCE",
        "entry_concepts_source": ["E11", "T2DM", "type 2 diabetes"],
        "inclusion_rules": [
            ">=1 condition_occurrence of T2DM codes",
            "OR >=1 antidiabetic drug_exposure (metformin, SGLT2i, GLP-1, insulin)",
            "OR HbA1c measurement >= 6.5%",
        ],
        "exit_rules": ["end of observation_period"],
        "omop_tables": ["CONDITION_OCCURRENCE", "DRUG_EXPOSURE", "MEASUREMENT"],
        "study_applications": ["outcomes", "drug safety", "comparative effectiveness"],
    },
    "heart_failure": {
        "title": "Heart failure",
        "clinical_overview": (
            "Clinical syndrome of structural or functional cardiac impairment "
            "leading to inadequate cardiac output or elevated filling pressures."
        ),
        "entry_domain": "CONDITION_OCCURRENCE",
        "entry_concepts_source": ["I50", "heart failure", "CHF"],
        "inclusion_rules": [
            ">=1 HF condition code in CONDITION_OCCURRENCE",
            "optional: BNP/NT-proBNP MEASUREMENT elevated",
        ],
        "exit_rules": ["end of observation_period"],
        "omop_tables": ["CONDITION_OCCURRENCE", "MEASUREMENT", "DRUG_EXPOSURE"],
        "study_applications": ["outcomes", "readmission", "device therapy"],
    },
    "ischemic_stroke": {
        "title": "Ischemic stroke",
        "clinical_overview": (
            "Sudden death of brain cells due to oxygen deprivation from reduced "
            "or blocked blood flow to the brain."
        ),
        "entry_domain": "CONDITION_OCCURRENCE",
        "entry_concepts_source": ["I63", "ischemic stroke", "CVA"],
        "inclusion_rules": [
            "acute inpatient visit_occurrence with ischemic stroke condition",
            "exclude traumatic intracranial injury codes same visit",
        ],
        "exit_rules": ["fixed 30-day window from index OR observation end"],
        "omop_tables": ["CONDITION_OCCURRENCE", "VISIT_OCCURRENCE", "PROCEDURE_OCCURRENCE"],
        "study_applications": ["outcomes", "secondary prevention"],
    },
    "ckd_stage_3_plus": {
        "title": "Chronic kidney disease stage 3+",
        "clinical_overview": "Sustained reduction in GFR <60 mL/min/1.73m2 for >=3 months.",
        "entry_domain": "CONDITION_OCCURRENCE",
        "entry_concepts_source": ["N18.3", "N18.4", "N18.5", "CKD stage 3"],
        "inclusion_rules": [
            "CKD stage 3-5 condition codes",
            "OR eGFR MEASUREMENT < 60 on two occasions >=90 days apart",
        ],
        "exit_rules": ["end of observation_period"],
        "omop_tables": ["CONDITION_OCCURRENCE", "MEASUREMENT"],
        "study_applications": ["progression", "drug dosing safety"],
    },
}


class OMOPPhenotypeEngine:
    """Register and resolve OMOP-aligned phenotype / cohort definitions."""

    def __init__(self) -> None:
        self._library: Dict[str, Dict[str, Any]] = dict(SEED_PHENOTYPES)

    def get(self, phenotype_id: str) -> Optional[Dict[str, Any]]:
        return self._library.get(phenotype_id)

    def list_phenotypes(self) -> List[Dict[str, str]]:
        return [
            {"id": k, "title": v["title"]}
            for k, v in self._library.items()
        ]

    def register(
        self,
        phenotype_id: str,
        title: str,
        clinical_overview: str,
        inclusion_rules: List[str],
        omop_tables: List[str],
        entry_concepts_source: Optional[List[str]] = None,
        exit_rules: Optional[List[str]] = None,
        study_applications: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        entry = {
            "title": title,
            "clinical_overview": clinical_overview,
            "entry_domain": "CONDITION_OCCURRENCE",
            "entry_concepts_source": entry_concepts_source or [],
            "inclusion_rules": inclusion_rules,
            "exit_rules": exit_rules or ["end of observation_period"],
            "omop_tables": omop_tables,
            "study_applications": study_applications or ["general"],
            "registered_at": time.time(),
            "format": "OHDSI_phenotype_chapter_stub",
        }
        self._library[phenotype_id] = entry
        return {"id": phenotype_id, **entry}

    def cohort_sql_stub(self, phenotype_id: str) -> Dict[str, Any]:
        """Emit illustrative OHDSI-SQL-shaped stub (not executable without vocab)."""
        p = self.get(phenotype_id)
        if not p:
            return {"error": "NOT_FOUND", "id": phenotype_id}
        sql = (
            f"-- Phenotype: {p['title']}\n"
            f"-- Clinical: {p['clinical_overview'][:120]}...\n"
            "SELECT DISTINCT c.person_id, c.condition_start_date AS cohort_start_date\n"
            "FROM condition_occurrence c\n"
            "WHERE c.condition_concept_id IN (/* standard concept set via Athena */)\n"
            f"-- Inclusion: {'; '.join(p['inclusion_rules'][:2])}\n"
        )
        return {
            "phenotype_id": phenotype_id,
            "title": p["title"],
            "sql_stub": sql,
            "note": "Replace concept sets via OHDSI Athena / Atlas export",
            "library_ref": "https://ohdsi.github.io/PhenotypeLibrary/",
        }

    def status(self) -> Dict[str, Any]:
        return {
            "node": "OMOPPhenotypeEngine",
            "phenotype_count": len(self._library),
            "ids": list(self._library.keys()),
            "status": "READY",
        }
