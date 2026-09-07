"""
Specialty Care Router for TMRDS.
Routes problems into specialized medical domains and attaches domain-specific
evidence channels (literature filters, genomic anchors, imaging modalities,
guideline keywords) so clinicians can access care pathways across specialties.

Advisory only — expands search surface; does not replace specialist judgment.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


# Specialty → search / pathway metadata
SPECIALTIES: Dict[str, Dict[str, Any]] = {
    "cardiology": {
        "keywords": ["heart failure", "MI", "arrhythmia", "CAD", "hypertension", "valve"],
        "pubmed_filter": "cardiology OR cardiovascular OR heart failure OR myocardial",
        "common_genes": ["LDLR", "PCSK9", "MYH7", "TNNT2", "KCNQ1", "SCN5A"],
        "modalities": ["ECG", "echo", "cardiac MRI", "coronary CT"],
        "omop_focus": ["CONDITION_OCCURRENCE", "MEASUREMENT", "PROCEDURE_OCCURRENCE"],
    },
    "oncology": {
        "keywords": ["cancer", "tumor", "carcinoma", "lymphoma", "leukemia", "metastasis"],
        "pubmed_filter": "oncology OR neoplasm OR chemotherapy OR immunotherapy",
        "common_genes": ["TP53", "BRCA1", "BRCA2", "EGFR", "KRAS", "ALK", "HER2"],
        "modalities": ["CT", "PET", "biopsy", "pathology"],
        "omop_focus": ["CONDITION_OCCURRENCE", "DRUG_EXPOSURE", "PROCEDURE_OCCURRENCE"],
        "extensions": ["mCODE", "OMOP Oncology Extension"],
    },
    "neurology": {
        "keywords": ["stroke", "seizure", "MS", "Parkinson", "Alzheimer", "neuropathy", "migraine"],
        "pubmed_filter": "neurology OR stroke OR epilepsy OR neurodegenerative",
        "common_genes": ["APP", "PSEN1", "LRRK2", "SOD1", "HTT"],
        "modalities": ["MRI brain", "EEG", "lumbar puncture"],
        "omop_focus": ["CONDITION_OCCURRENCE", "MEASUREMENT", "PROCEDURE_OCCURRENCE"],
    },
    "infectious_disease": {
        "keywords": ["sepsis", "pneumonia", "HIV", "hepatitis", "TB", "COVID", "antibiotic"],
        "pubmed_filter": "infectious disease OR antimicrobial OR sepsis OR pathogen",
        "common_genes": [],
        "modalities": ["culture", "PCR", "chest X-ray"],
        "omop_focus": ["CONDITION_OCCURRENCE", "DRUG_EXPOSURE", "MEASUREMENT"],
    },
    "endocrinology": {
        "keywords": ["diabetes", "thyroid", "adrenal", "osteoporosis", "obesity", "HbA1c"],
        "pubmed_filter": "endocrinology OR diabetes OR thyroid OR metabolic",
        "common_genes": ["HNF1A", "GCK", "INS", "PPARG"],
        "modalities": ["labs", "thyroid ultrasound", "DEXA"],
        "omop_focus": ["CONDITION_OCCURRENCE", "MEASUREMENT", "DRUG_EXPOSURE"],
    },
    "pulmonology": {
        "keywords": ["COPD", "asthma", "ILD", "pulmonary embolism", "respiratory failure"],
        "pubmed_filter": "pulmonology OR COPD OR asthma OR respiratory",
        "common_genes": ["SERPINA1", "CFTR"],
        "modalities": ["PFTs", "chest CT", "bronchoscopy"],
        "omop_focus": ["CONDITION_OCCURRENCE", "MEASUREMENT", "PROCEDURE_OCCURRENCE"],
    },
    "nephrology": {
        "keywords": ["CKD", "AKI", "dialysis", "proteinuria", "electrolyte"],
        "pubmed_filter": "nephrology OR chronic kidney disease OR dialysis",
        "common_genes": ["PKD1", "PKD2", "COL4A5"],
        "modalities": ["renal ultrasound", "biopsy", "labs"],
        "omop_focus": ["CONDITION_OCCURRENCE", "MEASUREMENT", "PROCEDURE_OCCURRENCE"],
    },
    "gastroenterology": {
        "keywords": ["IBD", "cirrhosis", "hepatitis", "pancreatitis", "GERD", "colon"],
        "pubmed_filter": "gastroenterology OR hepatology OR IBD OR cirrhosis",
        "common_genes": ["NOD2", "ATP7B", "HFE"],
        "modalities": ["endoscopy", "colonoscopy", "abdominal ultrasound", "MRCP"],
        "omop_focus": ["CONDITION_OCCURRENCE", "PROCEDURE_OCCURRENCE", "MEASUREMENT"],
    },
    "hematology": {
        "keywords": ["anemia", "thrombosis", "hemophilia", "sickle", "cytopenia"],
        "pubmed_filter": "hematology OR anemia OR thrombosis OR coagulation",
        "common_genes": ["F5", "F2", "HBB", "JAK2"],
        "modalities": ["CBC", "coagulation panel", "bone marrow"],
        "omop_focus": ["CONDITION_OCCURRENCE", "MEASUREMENT", "DRUG_EXPOSURE"],
    },
    "rheumatology": {
        "keywords": ["RA", "lupus", "SLE", "vasculitis", "gout", "autoimmune"],
        "pubmed_filter": "rheumatology OR autoimmune OR rheumatoid OR lupus",
        "common_genes": ["HLA-B27", "HLA-DRB1"],
        "modalities": ["autoantibody panel", "joint imaging"],
        "omop_focus": ["CONDITION_OCCURRENCE", "MEASUREMENT", "DRUG_EXPOSURE"],
    },
    "psychiatry": {
        "keywords": ["depression", "anxiety", "bipolar", "schizophrenia", "PTSD", "substance"],
        "pubmed_filter": "psychiatry OR depression OR bipolar OR schizophrenia",
        "common_genes": ["CYP2D6", "CYP2C19", "HLA-B*1502"],
        "modalities": ["screening scales", "PGx panel"],
        "omop_focus": ["CONDITION_OCCURRENCE", "DRUG_EXPOSURE", "OBSERVATION"],
    },
    "pediatrics": {
        "keywords": ["neonatal", "congenital", "developmental", "pediatric fever", "vaccination"],
        "pubmed_filter": "pediatrics OR neonatal OR congenital OR childhood",
        "common_genes": [],
        "modalities": ["growth charts", "developmental screen", "immunization record"],
        "omop_focus": ["CONDITION_OCCURRENCE", "MEASUREMENT", "DRUG_EXPOSURE"],
    },
    "obstetrics_gynecology": {
        "keywords": ["pregnancy", "preeclampsia", "endometriosis", "infertility", "cervical"],
        "pubmed_filter": "obstetrics OR gynecology OR pregnancy OR prenatal",
        "common_genes": ["BRCA1", "BRCA2", "FMR1"],
        "modalities": ["ultrasound OB", "NST", "Pap", "HPV"],
        "omop_focus": ["CONDITION_OCCURRENCE", "OBSERVATION", "PROCEDURE_OCCURRENCE"],
    },
    "emergency_medicine": {
        "keywords": ["trauma", "acute abdomen", "chest pain", "shortness of breath", "overdose"],
        "pubmed_filter": "emergency medicine OR acute care OR trauma",
        "common_genes": [],
        "modalities": ["FAST exam", "ECG", "portable X-ray", "CT trauma"],
        "omop_focus": ["VISIT_OCCURRENCE", "CONDITION_OCCURRENCE", "PROCEDURE_OCCURRENCE"],
    },
    "rare_disease": {
        "keywords": ["rare", "orphan", "undiagnosed", "syndromic", "Mendelian"],
        "pubmed_filter": "rare disease OR Orphanet OR undiagnosed disease OR Mendelian",
        "common_genes": [],
        "modalities": ["WES", "WGS", "chromosomal microarray", "HPO phenotyping"],
        "omop_focus": ["CONDITION_OCCURRENCE", "MEASUREMENT", "OBSERVATION"],
        "ontologies": ["ORDO", "HPO", "OMIM", "GARD"],
    },
    "clinical_genetics": {
        "keywords": ["variant", "carrier", "inheritance", "karyotype", "CNV"],
        "pubmed_filter": "clinical genetics OR genomic medicine OR variant interpretation",
        "common_genes": [],
        "modalities": ["VCF", "gene panel", "WES", "WGS"],
        "omop_focus": ["OBSERVATION", "MEASUREMENT", "CONDITION_OCCURRENCE"],
    },
    "primary_care": {
        "keywords": ["wellness", "prevention", "screening", "chronic care", "comorbidity"],
        "pubmed_filter": "primary care OR family medicine OR preventive",
        "common_genes": [],
        "modalities": ["vitals", "screening labs", "preventive imaging"],
        "omop_focus": ["CONDITION_OCCURRENCE", "MEASUREMENT", "DRUG_EXPOSURE", "OBSERVATION"],
    },
}


class SpecialtyCareRouter:
    """Classify clinical problems into specialties and emit domain search plans."""

    def classify(self, problem_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        text = (problem_text or "").lower()
        scored: List[Dict[str, Any]] = []
        for name, meta in SPECIALTIES.items():
            hits = sum(1 for kw in meta["keywords"] if kw.lower() in text)
            if hits:
                scored.append({"specialty": name, "score": hits, **meta})
        scored.sort(key=lambda x: x["score"], reverse=True)
        if not scored:
            # default to primary care + rare_disease safety net
            return [
                {"specialty": "primary_care", "score": 0, **SPECIALTIES["primary_care"]},
                {"specialty": "rare_disease", "score": 0, **SPECIALTIES["rare_disease"]},
            ]
        return scored[:top_k]

    def build_search_plan(
        self,
        problem_text: str,
        gene: Optional[str] = None,
    ) -> Dict[str, Any]:
        matches = self.classify(problem_text)
        primary = matches[0]
        pubmed_terms = [primary["pubmed_filter"], f"({problem_text})"]
        if gene:
            pubmed_terms.append(f"({gene})")
        return {
            "problem": problem_text,
            "primary_specialty": primary["specialty"],
            "all_matches": [{"specialty": m["specialty"], "score": m["score"]} for m in matches],
            "pubmed_query": " AND ".join(pubmed_terms),
            "suggested_genes": primary.get("common_genes", []),
            "suggested_modalities": primary.get("modalities", []),
            "omop_tables": primary.get("omop_focus", []),
            "ontologies": primary.get("ontologies", []),
            "extensions": primary.get("extensions", []),
            "advisory_only": True,
        }

    def list_specialties(self) -> List[str]:
        return sorted(SPECIALTIES.keys())

    def status(self) -> Dict[str, Any]:
        return {
            "node": "SpecialtyCareRouter",
            "specialty_count": len(SPECIALTIES),
            "specialties": self.list_specialties(),
            "status": "READY",
        }
