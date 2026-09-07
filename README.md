# TMRDS — Tucker Medical Research and Development System

**Research-advisory platform** for Tri-State (Indiana / Illinois / Kentucky) clinics and precision research.

> Technology informs people; it does not silently govern people. **Human authority remains final.**

**Steward:** Anthony John Tucker · Mount Vernon, Indiana 47620  
**Regulatory posture:** Not FDA-cleared SaMD. All clinical outputs are advisory only.

---

## For medical professionals (start here)

**→ [docs/MEDICAL_PROFESSIONAL_INSPECTION.md](docs/MEDICAL_PROFESSIONAL_INSPECTION.md)**  
Scope, safety checklist, standards table, government evidence sources, and inspection steps for physicians, CMIOs, and clinical informaticists.

| Question | Answer |
|----------|--------|
| Does this diagnose or prescribe? | **No** |
| Can it replace specialist judgment? | **No** |
| What does it do? | Standards-based ingest, literature/trial search, OMOP/FHIR mapping, ranked *starting points* for human review |
| Evidence sources? | PubMed, ClinicalTrials.gov, NLM Clinical Tables, RxNorm, MedlinePlus, OpenAlex/S2/arXiv (APIs only) |

---

## Standards stack

| Standard | Module |
|----------|--------|
| FHIR R4 US Core + specialty IGs (mCODE, Genomics, CardX) | `fhir_us_core_mapper`, `specialty_fhir_profiles` |
| **US Core → OMOP concept map** | `us_core_omop_concept_map` |
| OMOP CDM v5.4 | `omop_cdm_bridge` |
| OHDSI Atlas / Circe cohorts | `ohdsi_atlas_cohort`, `omop_phenotype_engine` |
| NLM.gov tables (ICD-10-CM, HPO, RxTerms) + RxNorm + MedlinePlus | `nlm_gov_clinical_tables` |

### US Core → OMOP (inspector summary)

Patient→PERSON · Condition→CONDITION_OCCURRENCE (SNOMED) · Observation lab→MEASUREMENT (LOINC) · MedicationRequest→DRUG_EXPOSURE (RxNorm) · Procedure→PROCEDURE_OCCURRENCE · Encounter→VISIT_OCCURRENCE · type_concept_id **32880** (algorithmic)

---

## Core clinical path

```
SpecialtyCareRouter → UniversalClinicalIngest
  → FHIRUSCoreMapper ⇄ OMOPCDMBridge / USCoreOMOPConceptMap
  → DriveThruIngestion (PubMed, CT.gov, …) + NLMGovClinicalTables
  → KRAGEN / QRCECureOrchestrator
  → EvidenceLedger  →  human clinician review
```

---

## Documentation index

| Doc | Audience |
|-----|----------|
| [MEDICAL_PROFESSIONAL_INSPECTION.md](docs/MEDICAL_PROFESSIONAL_INSPECTION.md) | **Clinicians / CMIO** |
| [FHIR_OMOP_SPECIALTIES.md](docs/FHIR_OMOP_SPECIALTIES.md) | Informatics |
| [DRIVE_THRU_EVIDENCE.md](docs/DRIVE_THRU_EVIDENCE.md) | Evidence network |
| [NEO4J_REGENSTRIEF.md](docs/NEO4J_REGENSTRIEF.md) | Graph + Indiana HIE |
| [ARCHITECTURE_SOVEREIGNTY.md](docs/ARCHITECTURE_SOVEREIGNTY.md) | Governance |

---

## Safety (non-negotiable)

- Research-advisory only — not diagnosis, prescription, or cure claims  
- Not legal advice (patent / FTO modules)  
- HIE data requires BAA/DUA + IRB as applicable  
- Evidence before inference · Human authority final  

**Repository:** https://github.com/ATphobia22/TMRDS
