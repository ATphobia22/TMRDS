# TMRDS — Guide for Medical Professional Inspection

**Steward:** Anthony John Tucker · Mount Vernon, Indiana 47620  
**Repository:** https://github.com/ATphobia22/TMRDS  
**Status:** Research software under active development — **not FDA-cleared SaMD**

---

## 1. What this system is (and is not)

| Is | Is not |
|----|--------|
| Research-advisory software platform | Licensed medical device (no 510(k)/De Novo claim) |
| Standards-based data plumbing (FHIR, OMOP, LOINC, SNOMED, RxNorm) | Autonomous diagnosis or prescribing system |
| Literature / trial / patent *search* assist | Authoritative clinical guideline engine |
| Local-first / sovereign-clinic oriented | Replacement for clinician judgment |

**Doctrine:** Evidence before inference. Human authority remains final.

---

## 2. Clinical safety posture

- All LLM, graph, quantum, structure, and ranking outputs are **advisory only**.
- `DoctorDignityEthics` applies bias gates on free text.
- `EvidenceLedger` stores content hashes for provenance audit.
- No module issues prescriptions, dosing orders, or cure claims.
- Patent search (`OverlookedBlessings`) is **not legal advice** and not FTO opinion.
- Live HIE/INPC data requires institutional BAA/DUA and IRB where applicable.

**Recommended inspection checklist for clinicians / CMIO / informatics**

1. Read this document and `docs/ARCHITECTURE_SOVEREIGNTY.md`
2. Review `engines/qrce_cure_orchestrator.py` disclaimer strings
3. Confirm no production path bypasses human review for clinical decisions
4. Verify terminology sources are NLM/HL7/OHDSI-backed (below)
5. Treat all ranked “starting points” as hypothesis generation only

---

## 3. Standards & mappings (for informatics review)

| Layer | Implementation | Authority |
|-------|----------------|-----------|
| FHIR R4 US Core | `fhir_us_core_mapper.py`, `specialty_fhir_profiles.py` | HL7 US Core, mCODE, Genomics Reporting, CardX |
| US Core → OMOP | `us_core_omop_concept_map.py` | HL7/OHDSI FHIR–OMOP guidance; type_concept_id 32880 |
| OMOP CDM v5.4 | `omop_cdm_bridge.py` | OHDSI CDM |
| Phenotypes / cohorts | `omop_phenotype_engine.py`, `ohdsi_atlas_cohort.py` | OHDSI Phenotype Library, Atlas/Circe |
| Labs | LOINC via NLM Clinical Tables | Regenstrief / NLM |
| Drugs | RxNorm API | NLM |
| Literature | PubMed E-utilities | NCBI/NLM |
| Trials | ClinicalTrials.gov API v2 | NLM/NIH |

### US Core → OMOP (summary)

| US Core profile | OMOP table | Vocab |
|-----------------|------------|-------|
| Patient | PERSON | gender 8507/8532 |
| Condition | CONDITION_OCCURRENCE | SNOMED |
| Observation lab | MEASUREMENT | LOINC |
| MedicationRequest | DRUG_EXPOSURE | RxNorm |
| Procedure | PROCEDURE_OCCURRENCE | SNOMED/CPT |
| Encounter | VISIT_OCCURRENCE | Visit |
| AllergyIntolerance | OBSERVATION | SNOMED |

---

## 4. Government & academic evidence sources (no scrape)

| Source | Module / use |
|--------|----------------|
| PubMed / MEDLINE | `pubmed_literature_bridge.py`, Drive-Thru |
| ClinicalTrials.gov | `drive_thru_ingestion.py` |
| NLM Clinical Table Search (ICD-10-CM, HPO, RxTerms, HCPCS, NPI) | `nlm_gov_clinical_tables.py` |
| MedlinePlus | patient education bridge |
| RxNorm | drug normalization |
| OpenAlex / Semantic Scholar / arXiv | secondary literature graph (API) |
| USPTO PatentsView | expired-pathway *research* only |

---

## 5. Specialty coverage

`SpecialtyCareRouter` + specialty FHIR IGs cover major domains including oncology (mCODE), cardiology (CardX), genomics, rare disease (HPO/ORDO-oriented), and primary care (US Core floor). Routing expands **search surface**; it does not assign specialty care responsibility.

---

## 6. Local open-source clinical stack (optional)

OpenEMR · Orthanc PACS · OHIF Viewer · OpenELIS · Kiwix/WikiMed — see `open_source_medical_core.py`.

---

## 7. Intended professional audience for inspection

- Physicians / APP clinical leads evaluating research tooling
- CMIO / CNIO / clinical informaticists
- Pharmacy / precision medicine / oncology analytics teams
- Compliance / privacy reviewing advisory-only scope
- Academic collaborators (OMOP/Atlas phenotype reuse)

**Contact steward for formal review sessions:** Anthony John Tucker, Mount Vernon, Indiana 47620

---

*This document is part of the TMRDS repository and should be updated when clinical claims or regulatory posture change.*
