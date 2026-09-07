# TMRDS — Tucker Medical Research and Development System

**Zero-Latency Sovereignty** medical infrastructure for rural Tri-State clinics (Indiana / Kentucky / Illinois) and high-precision research.

> Technology informs people; it does not silently govern people. Human authority remains final.

**Steward:** Anthony John Tucker · Mount Vernon, Indiana 47620

## On-the-Spot Treatment Starting Points (QRCE)

```
Labs / scans / genome / sequencing / notes
  → UniversalClinicalIngest
  → DoctorDignityEthics
  → PubMedLiteratureBridge (verifiable journals)
  → KRAGENGraphEngine (+ Neo4j GraphRAG when connected)
  → QRCECureOrchestrator
  → EvidenceLedger
  → Ranked advisory starting points for clinician review
```

| Module | Path | Role |
|--------|------|------|
| **UniversalClinicalIngest** | `engines/universal_clinical_ingest.py` | Labs, imaging, VCF/genomic, sequencing, notes |
| **PubMedLiteratureBridge** | `engines/pubmed_literature_bridge.py` | NCBI E-utilities — searchable medical literature |
| **Neo4jKRAGENConnector** | `engines/neo4j_kragen_connector.py` | Production Cypher GraphRAG store |
| **QRCECureOrchestrator** | `engines/qrce_cure_orchestrator.py` | End-to-end advisory treatment search |

**All outputs are research-advisory only** — not diagnoses, prescriptions, or cure claims.

## Sovereignty & Graph

| Module | Path |
|--------|------|
| SovereignEdge | `engines/sovereign_edge.py` |
| EvidenceLedger | `engines/evidence_ledger.py` |
| DoctorDignityEthics | `engines/doctor_dignity_ethics.py` |
| OpenMedEngine | `engines/openmed_nlp.py` |
| TurboVecIndex | `engines/turbovec_index.py` |
| KRAGENGraphEngine | `engines/kragen_graph_engine.py` |
| IHIEBridge | `engines/ihie_bridge.py` |

## Clinical & Research Engines

MONAIVision · MedicalNet · DeepXDE Simulation · PrecisionMedicine · FHIR bridges · ClinicalLLMRouter · AlphaFold3 · GROVER · RDKit · QiskitNature · BioCoder · QuantumRubiksCureEngine

## Docs

- [ARCHITECTURE_SOVEREIGNTY.md](docs/ARCHITECTURE_SOVEREIGNTY.md)
- [NEO4J_REGENSTRIEF.md](docs/NEO4J_REGENSTRIEF.md) — Neo4j GraphRAG + Regenstrief INPC methods
- [WEIGHTS_DOWNLOAD.md](docs/WEIGHTS_DOWNLOAD.md)

## Indiana Ecosystem

IDOH · Indiana Medicaid · **IHIE / INPC** · Regenstrief Data Services (Bulk FHIR, LOINC, OMOP ATLAS)  
Live HIE access requires BAA/DUA + IRB.

---
**Status**: Private | Active development  
**Steward**: Anthony John Tucker · Mount Vernon, Indiana 47620  
**Doctrine**: Evidence before inference · Human authority final
