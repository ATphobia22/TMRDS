# Drive-Thru Evidence Network · Specialty FHIR · OMOP Phenotypes

**Steward:** Anthony John Tucker · Mount Vernon, Indiana 47620

## 1. Specialty FHIR Profiles

Module: `engines/specialty_fhir_profiles.py`

| Specialty | IG | Example profiles |
|-----------|-----|------------------|
| Oncology | mCODE | primary-cancer-condition, genomic-variant, genomics-report, TNM stage |
| Clinical Genetics | Genomics Reporting | variant, genotype, therapeutic-implication |
| Cardiology | CardX HTN / CIED | blood-pressure-panel, CIED device/observation |
| Radiation Oncology | CodeX RT | radiotherapy-course-summary |
| Rare Disease | Genomics + US Core | HPO-linked phenotype + variant |
| Primary Care (floor) | US Core | patient, condition, observation-lab, medicationrequest |

## 2. OMOP Phenotype Definitions

Module: `engines/omop_phenotype_engine.py`

OHDSI model: **phenotype** = clinical idea; **cohort definition** = computable chapter (entry + inclusion + exit) against OMOP CDM.

Seed phenotypes: type_2_diabetes, heart_failure, ischemic_stroke, ckd_stage_3_plus.

Production: export concept sets from [OHDSI Phenotype Library / Atlas](https://ohdsi.github.io/PhenotypeLibrary/).

## 3. Drive-Thru Ingestion (API-only)

Module: `engines/drive_thru_ingestion.py`

| Source | Endpoint family |
|--------|-----------------|
| PubMed | NCBI E-utilities |
| arXiv | export.arxiv.org/api |
| OpenAlex | api.openalex.org/works |
| Semantic Scholar | api.semanticscholar.org/graph/v1 |
| ClinicalTrials.gov | /api/v2/studies |

**Evidence Altar:** local document metadata index (Chroma/FTS5-ready).
**No scraping** — official APIs only.

## 4. Overlooked Blessings

Module: `engines/overlooked_blessings.py`

USPTO PatentsView queries with date < 2006-03-01 for expired-pathway research.
**Not legal advice** — FTO requires counsel.

## 5. Open-Source Medical Core

Module: `engines/open_source_medical_core.py`

| Component | Role |
|-----------|------|
| OpenEMR | Local EHR + FHIR |
| Orthanc | DICOM PACS |
| OHIF | Zero-footprint viewer |
| OpenELIS | Lab LIS |
| Kiwix + WikiMed | Offline clinical reference |

## 6. Tri-State Knowledge Graph doctrine

Reject frozen giant directories. Prefer:
- dynamic source adapters
- canonical entity resolution
- geospatial indexing for IN / IL / KY health infrastructure
- KRAGEN layers + EvidenceLedger hashes

**Advisory only. Human authority remains final.**
