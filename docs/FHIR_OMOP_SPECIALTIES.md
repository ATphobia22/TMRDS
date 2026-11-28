# FHIR Resource Mapping · OMOP CDM · Specialty Care

**Steward:** Anthony John Tucker · Mount Vernon, Indiana 47620

## 1. FHIR R4 / US Core Mapping (TMRDS)

Module: `engines/fhir_us_core_mapper.py`

| Clinical fact | FHIR R4 resource | US Core profile (representative) |
|---------------|------------------|----------------------------------|
| Demographics | Patient | us-core-patient |
| Diagnosis / problem | Condition | us-core-condition-problems-health-concerns |
| Lab / vital | Observation | us-core-observation-lab |
| Lab panel / note | DiagnosticReport | us-core-diagnosticreport-lab |
| Prescription | MedicationRequest | us-core-medicationrequest |
| Procedure | Procedure | us-core-procedure |
| Allergy | AllergyIntolerance | us-core-allergyintolerance |
| Encounter | Encounter | us-core-encounter |

### HL7 v2 → FHIR (HIE feeds)

| v2 segment | FHIR resource |
|------------|---------------|
| PID | Patient |
| PV1 | Encounter |
| DG1 | Condition |
| OBX | Observation |
| OBR | ServiceRequest + DiagnosticReport |
| AL1 | AllergyIntolerance |
| ORC | ServiceRequest |

Terminology bindings: **LOINC** (labs), **SNOMED CT** (conditions/procedures), **RxNorm** (meds), **ICD-10-CM** (billing diagnoses).

---

## 2. OMOP CDM v5.4 (TMRDS)

Module: `engines/omop_cdm_bridge.py`

| OMOP table | Domain | Standard vocabulary |
|------------|--------|---------------------|
| PERSON | Demographics | Gender/race concepts |
| CONDITION_OCCURRENCE | Diagnoses | SNOMED |
| DRUG_EXPOSURE | Medications | RxNorm |
| MEASUREMENT | Labs / vitals | LOINC |
| PROCEDURE_OCCURRENCE | Procedures | SNOMED / CPT |
| OBSERVATION | Assertions / history | SNOMED / LOINC |
| VISIT_OCCURRENCE | Encounters | Visit concepts |

### Executable FHIR ↔ OMOP research subset

The current local in-memory bridge implements a deliberately smaller projection:

| FHIR | OMOP | Executable rule |
|------|------|-----------------|
| Patient | PERSON | Explicit one-to-one FHIR ID to OMOP person_id mapping required |
| Condition | CONDITION_OCCURRENCE | Requires onset date; recordedDate is not treated as onset |
| Observation | MEASUREMENT | Final numeric valueQuantity and effective date only |
| MedicationStatement | DRUG_EXPOSURE | Active/completed statement with effective date; not proof of dispensing/admin |

MedicationRequest is not converted into an actual exposure because authoredOn is the order-authored date. DiagnosticReport is not converted into a measurement because result references must resolve to child Observations. Other cataloged domain mappings are not yet executable in this bridge.

No OHDSI Athena vocabulary lookup is currently wired into this bridge. Source coding systems/codes are preserved and standard concept IDs remain 0 until a governed vocabulary resolver is implemented and validated. See [the executable subset and limits](integrations/fhir-omop-roundtrip-research.md).

Aligns with Indiana CTSI **INPC-OMOP ATLAS** cohort discovery patterns and Regenstrief research extracts.

---

## 3. Specialty Care Router

Module: `engines/specialty_care_router.py`

Domains covered (non-exhaustive, expandable):

- Cardiology, Oncology (+ mCODE / OMOP Oncology Extension hooks)
- Neurology, Infectious Disease, Endocrinology, Pulmonology
- Nephrology, Gastroenterology, Hematology, Rheumatology
- Psychiatry (incl. PGx), Pediatrics, OB/GYN
- Emergency Medicine, Primary Care
- **Rare Disease** (ORDO, HPO, OMIM, GARD) + **Clinical Genetics**

Each specialty emits:
- PubMed query filters
- Suggested genes / modalities
- OMOP tables to prioritize
- Ontology extensions when relevant

---

## 4. Innovation path (whole-of-medicine)

```
Any specialty problem
  → SpecialtyCareRouter
  → UniversalClinicalIngest (labs/genome/scans)
  → FHIRUSCoreMapper ⇄ OMOPCDMBridge
  → PubMed + KRAGEN/Neo4j
  → QRCEResearchOrchestrator
  → EvidenceLedger (human review)
```

Goal: every clinician—regardless of specialty—gets an immediate, standards-based evidence packet and literature/graph starting points for the patient in front of them.

**Advisory only. Human authority remains final.**
