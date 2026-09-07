# TMRDS Architecture — Zero-Latency Sovereignty

Aligned with the **Tri-State Medical Healthcare System** and **Tri-State Systems Manager** doctrine.

> Technology informs people; it does not silently govern people. Human authority remains final.

**Steward:** Anthony John Tucker · Mount Vernon, Indiana 47620

## 1. Operating Model

| Plane | Responsibility | Boundary |
|-------|-----------------|----------|
| **Sovereign Edge** | Offline EHR / imaging / lab queues | Clinics operate without internet |
| **Identity / Consent** | RBAC + ABAC + MFA multi-tenant gates | Least privilege |
| **Evidence Ledger** | Immutable `content_hash` provenance | Evidence before inference |
| **KRAGEN Graph** | Pathology + molecular + quantum knowledge layers | Graph-of-Thoughts RAG |
| **Clinical Engines** | OpenMed, MONAI, DeepXDE, AlphaFold3, QRCE, GROVER | Advisory unless human-accepted |
| **Ethics Gate** | Doctor-Dignity bias matrix | Fail-closed on critical bias |
| **IHIE Bridge** | Indiana Network for Patient Care interoperability | FHIR R4 / Bulk FHIR / DUA-gated |

## 2. Indiana / Tri-State Data Plane

- Indiana Department of Health (IDOH)
- Indiana Medicaid provider directory
- **Indiana Health Information Exchange (IHIE)** / Indiana Network for Patient Care (INPC)
- Regenstrief Institute Data Services (Bulk FHIR research access pattern)
- Geographic scope: **Indiana, Kentucky, Illinois**

## 3. KRAGEN Graph Storage

Based on EpistasisLab/KRAGEN (Matsumoto et al., *Bioinformatics* 2024):

1. Multi-layer KG (pathology / molecular / quantum / clinical)
2. Edge → natural-language statements for vectorization
3. Vector retrieval (TurboVec / Weaviate)
4. Graph-of-Thoughts (GoT) reasoning for explainable biomedical answers

Production path: Neo4j dump → Weaviate → KRAGEN Docker + React GoT viewer.

## 4. SaMD & Compliance Posture

- SaMD Class II–III aspirational target
- IEC 62304 lifecycle / ISO 14971 risk management
- IHIE/INPC access requires BAA / DUA + applicable IRB

## 5. Autonomy Ladder

- **S1:** no agency — default
- **S2:** prescribed tools with explicit human gate
- **S3:** deferred (not approved for autonomous governance)

AI and quantum outputs remain **advisory** until human promotion in the Evidence Ledger.
