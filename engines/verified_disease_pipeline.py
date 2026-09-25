"""
Verified disease pipeline statuses — registry and FDA-grounded research notes only.
Research-advisory. Not SaMD. No cure probabilities. Human authority final.
Steward: Anthony John Tucker.
Sources: ClinicalTrials.gov, FDA labels, peer-reviewed long-term data (as of 2026 scan).
"""
from __future__ import annotations

from typing import Any, Dict, List

RESEARCH_ADVISORY = {
    "status": "research-advisory",
    "human_authority_final": True,
    "not_samd": True,
    "not_clinical_decision_support": True,
}

# Hard bans — never emit as clinical truth
FORBIDDEN_CLAIM_PATTERNS = (
    "99% closure",
    "cure engine",
    "cure synthesized",
    "rubiksml cure",
    "innovation spark",
    "order locked",
    "evidence altar",
)

PIPELINE: List[Dict[str, Any]] = [
    {
        "id": "diabetic_wound_ceria",
        "domain": "Diabetic wound / chronic ulcer",
        "topic": "Ceria (CeO₂) nanoparticles / CeO₂@Exo",
        "clinical_status": "preclinical_only",
        "human_trials_registered": False,
        "notes": (
            "No registered human Phase I/II/III trials identified for ceria nanoparticles "
            "in diabetic foot ulcers as of 2026 scan. Preclinical literature reports ROS "
            "reduction and angiogenic signals; these do not establish clinical closure rates."
        ),
        "rejected_claims": [
            "99% closure probability within 14 days",
            "RubiksML Cure Engine clinical prediction",
        ],
        "related_clinical_activity_not_ceria": [
            "Other DFU agents (e.g., autologous skin constructs, investigational gels) "
            "have Phase 3 activity; do not conflate with ceria."
        ],
        "tmrds_rule": "Label preclinical only. Never output closure probability as fact.",
    },
    {
        "id": "kras_g12d",
        "domain": "KRAS-mutant cancers",
        "topic": "G12D direct inhibitors",
        "clinical_status": "investigational_pipeline_active_mrtx1133_terminated",
        "approved_agent": None,
        "notes": (
            "MRTX1133 Phase 1/2 (NCT05737706) terminated (2025) after Phase 1 only "
            "(formulation / variable PK). No FDA-approved G12D-selective agent. "
            "Other investigational programs include zoldonrasib (RMC-9805), ASP3082 "
            "(degrader), and additional Phase 1 assets — statuses change; verify ClinicalTrials.gov."
        ),
        "mrtx1133": {
            "nct": "NCT05737706",
            "status": "terminated",
            "reason_reported": "formulation challenges / suboptimal PK",
        },
        "rejected_claims": [
            "MRTX1133 actively in Phase I/II as current development path",
            "VQE docking energy as clinical target lock",
            "AlphaFold pLDDT as therapeutic endpoint",
        ],
        "tmrds_rule": "State termination accurately. Structure/VQE metrics are research only.",
    },
    {
        "id": "als_sod1",
        "domain": "ALS / neurodegeneration",
        "topic": "SOD1-directed and related agents",
        "clinical_status": "tofersen_approved_cnm_au8_investigational",
        "approved": [
            {
                "name": "tofersen (Qalsody)",
                "year": 2023,
                "indication": "ALS in adults with SOD1 mutation",
                "notes": "Long-term OLE analyses support slowed progression with earlier start; not a cure.",
            }
        ],
        "investigational": [
            {
                "name": "CNM-Au8",
                "status": "investigational",
                "notes": (
                    "Phase 2 / platform and OLE biomarker and survival analyses reported; "
                    "sponsor has discussed accelerated NDA framing. Not FDA-approved as of scan."
                ),
            }
        ],
        "rejected_claims": [
            "Grover-optimized pegRNA as standard of care",
            "Any engine-declared ALS cure",
        ],
        "tmrds_rule": "Tofersen approved for SOD1-ALS only. CNM-Au8 investigational.",
    },
    {
        "id": "alzheimer",
        "domain": "Alzheimer’s disease",
        "topic": "Anti-amyloid monoclonals",
        "clinical_status": "two_approved_early_disease",
        "approved": [
            {
                "name": "lecanemab (Leqembi)",
                "year": 2023,
                "indication": "Early AD (MCI or mild dementia) with confirmed amyloid",
            },
            {
                "name": "donanemab (Kisunla)",
                "year": 2024,
                "indication": "Early symptomatic AD with confirmed amyloid; label titration updates 2025",
            },
        ],
        "rejected_claims": [
            "Virtual chaperone quantum binder as therapy",
            "Quantum engine as substitute for approved care",
        ],
        "tmrds_rule": "Cite approved agents accurately. Quantum binders are research concepts only.",
    },
]


def catalog() -> Dict[str, Any]:
    return {
        **RESEARCH_ADVISORY,
        "count": len(PIPELINE),
        "entries": PIPELINE,
        "forbidden_claim_patterns": list(FORBIDDEN_CLAIM_PATTERNS),
        "disclaimer": (
            "Statuses are research notes from public registries and labels. "
            "They are not treatment recommendations. Licensed clinicians retain final authority. "
            "No internal score (Innovation Spark, VQE energy, pLDDT) is a clinical endpoint."
        ),
    }


def get_entry(entry_id: str) -> Dict[str, Any]:
    for e in PIPELINE:
        if e["id"] == entry_id:
            return {**RESEARCH_ADVISORY, "entry": e}
    return {
        **RESEARCH_ADVISORY,
        "error": f"Unknown entry_id '{entry_id}'",
        "known": [e["id"] for e in PIPELINE],
    }


def scrub_forbidden_claims(text: str) -> Dict[str, Any]:
    """Flag text that contains banned clinical-hype patterns."""
    lower = (text or "").lower()
    hits = [p for p in FORBIDDEN_CLAIM_PATTERNS if p in lower]
    return {
        **RESEARCH_ADVISORY,
        "clean": len(hits) == 0,
        "hits": hits,
        "action": "reject_or_rewrite" if hits else "ok",
    }
