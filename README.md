# TMRDS — Tucker Medical Research and Development System

**Zero-Latency Sovereignty** for Tri-State clinics and precision research.

> Technology informs people; it does not silently govern people. Human authority remains final.

**Steward:** Anthony John Tucker · Mount Vernon, Indiana 47620

## Whole-of-Medicine Path

```
Any specialty problem
  → SpecialtyCareRouter (17+ domains)
  → UniversalClinicalIngest (labs / genome / scans / notes)
  → FHIRUSCoreMapper ⇄ OMOPCDMBridge
  → PubMed + KRAGEN / Neo4j
  → QRCECureOrchestrator
  → EvidenceLedger (human review)
```

## Interoperability

| Module | Path | Role |
|--------|------|------|
| **FHIRUSCoreMapper** | `engines/fhir_us_core_mapper.py` | FHIR R4 US Core resources + v2 segment map |
| **OMOPCDMBridge** | `engines/omop_cdm_bridge.py` | OMOP CDM v5.4 tables + FHIR↔OMOP |
| **SpecialtyCareRouter** | `engines/specialty_care_router.py` | Cardiology→Rare Disease specialty plans |
| **IHIEBridge** | `engines/ihie_bridge.py` | Indiana HIE / INPC |
| **UniversalClinicalIngest** | `engines/universal_clinical_ingest.py` | On-the-spot multi-modal input |
| **PubMedLiteratureBridge** | `engines/pubmed_literature_bridge.py` | Verifiable journal evidence |
| **QRCECureOrchestrator** | `engines/qrce_cure_orchestrator.py` | Advisory treatment starting points |

## Docs

- [docs/FHIR_OMOP_SPECIALTIES.md](docs/FHIR_OMOP_SPECIALTIES.md) — FHIR mapping, OMOP CDM, specialties
- [docs/NEO4J_REGENSTRIEF.md](docs/NEO4J_REGENSTRIEF.md) — Neo4j GraphRAG, Regenstrief methods
- [docs/ARCHITECTURE_SOVEREIGNTY.md](docs/ARCHITECTURE_SOVEREIGNTY.md)
- [docs/WEIGHTS_DOWNLOAD.md](docs/WEIGHTS_DOWNLOAD.md)

## Specialties Routed

Cardiology · Oncology · Neurology · Infectious Disease · Endocrinology · Pulmonology · Nephrology · Gastroenterology · Hematology · Rheumatology · Psychiatry · Pediatrics · OB/GYN · Emergency · Primary Care · **Rare Disease** · **Clinical Genetics**

## Safety

All automated outputs are **research-advisory only**. Not diagnosis, prescription, or cure claims. Licensed clinicians retain final authority.

---
**Status**: Private | Active development  
**Steward**: Anthony John Tucker · Mount Vernon, Indiana 47620
