# Neo4j Integration & Regenstrief Institute Methods

**Steward:** Anthony John Tucker · Mount Vernon, Indiana 47620

## 1. Neo4j + KRAGEN GraphRAG

### Role in TMRDS
Neo4j is the **production graph store** behind `KRAGENGraphEngine` and `Neo4jKRAGENConnector`.

| Pattern | Use |
|---------|-----|
| Node labels | `Disease`, `Gene`, `Chemical`, `Paper`, `Entity` |
| Relations | `TREATS`, `ASSOCIATE`, `MENTIONED_IN`, `CAUSES`, `INHIBITS` |
| Query language | Cypher |
| RAG style | GraphRAG / GraphCypherQAChain (LLM → Cypher → context) |

### Setup
```bash
pip install neo4j
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=***
```

### Example Cypher (literature-linked gene)
```cypher
MATCH (g:Gene)-[:MENTIONED_IN]->(p:Paper)
WHERE toUpper(g.mention) = 'BRCA1'
RETURN p.pmid, p.title, p.year
ORDER BY p.year DESC LIMIT 20
```

### Literature graph scale (reference datasets)
- UMLS-derived graphs: ~3.4M concepts, tens of millions of relations (Neo4j)
- PubMed-GraphRAG style sets: papers + genes/diseases/chemicals + 100M+ edges
- Import via `neo4j-admin database import` from CSV node/relationship files

### TMRDS flow
```
KRAGENGraphEngine (in-memory layers)
    → Neo4jKRAGENConnector.push_kragen_nodes
    → Cypher multi-hop retrieval
    → statements / paths → TurboVec or Weaviate
    → ClinicalLLMRouter / QRCECureOrchestrator
```

Offline mode remains fully usable without Neo4j (in-memory KRAGEN only).

---

## 2. Regenstrief Institute Methods (INPC / IHIE)

### What Regenstrief provides
- **Indiana Network for Patient Care (INPC)** — statewide longitudinal clinical data (labs, admits, radiology, pathology, meds, etc.) across 100+ hospital systems
- **Regenstrief Data Services (RDS)** — research broker for INPC / IU Health / Eskenazi warehouses
- **LOINC / UCUM** — Regenstrief-led clinical terminology standards (semantic interoperability)
- **Bulk FHIR** — research export path: relational store → US Core FHIR → NDJSON (high throughput demonstrated)
- **ATLAS (OMOP)** — cohort discovery over INPC-OMOP for CTSI researchers

### Access model (research)
1. Feasibility / aggregate counts (often free for CTSI members)
2. IRB approval (IU / Purdue / Notre Dame or reliance)
3. Data use agreement + analyst effort funding
4. Extraction or Bulk FHIR export — **not** open public API

### Implications for TMRDS `IHIEBridge`
- Production patient-level pulls require institutional BAA/DUA + IRB
- Design target: FHIR R4 / US Core / Bulk FHIR / SMART on FHIR
- LOINC coding on lab ingest aligns with Regenstrief standards
- Health Dart pattern: FHIR app retrieving high-value INPC context into EHR workflow

### Local sovereign path (always available)
```
UniversalClinicalIngest (labs, genome, scans, notes)
  → EvidenceLedger content_hash
  → QRCECureOrchestrator + PubMed (public literature)
  → KRAGEN / Neo4j (when available)
```
No HIE credentials required for on-the-spot personal packet + literature search.

---

## 3. Safety

All automated treatment/literature rankings are **research-advisory only**.
Licensed clinicians retain final authority. No module issues prescriptions or cure claims.
