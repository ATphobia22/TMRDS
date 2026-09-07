# TMRDS: Transparent Medical Research Decision Support

**Research-Advisory Clinical Information Gateway**

| Field | Value |
|-------|--------|
| **Version** | 1.0.0-research |
| **Steward** | Anthony John Tucker, Mount Vernon, Indiana 47620 |
| **Regulatory posture** | Research-advisory only. **Not** FDA-cleared Software as a Medical Device (SaMD). Human clinical authority is final. |
| **Governance** | [GodFirst LLM/ML Protocol (G1P)](https://github.com/ATphobia22/godfirst-llm-ml-protocol) — child protection, anti-deception, audit transparency, human dignity |
| **Primary standards** | FHIR R4 US Core (default); OMOP CDM v5.4; HIPAA Security Rule technical controls (45 CFR 164.312) |

---

## 1. Abstract

TMRDS is a dual-track software system that (1) provides clinicians and biomedical researchers with **read-only access** to public medical terminologies, OMOP vocabulary concepts, literature-oriented research workflows, and **bounded** quantum-algorithm simulations; and (2) maintains empty regulatory scaffolds aligned with current FDA guidance for a possible future SaMD pathway. The system does **not** generate diagnoses, prescriptions, or treatment recommendations. Every public API response carries explicit research-advisory flags.

The design prioritizes **equity of access**: rural and low- and middle-income country (LMIC) practitioners are treated as first-class users of the research surface. Integration points reference open science and global-health drug-discovery resources (dd4gh, DNDi open initiatives, REWARD, OHDSI/DARWIN EU) so that computational assistance is not gated by institutional wealth or geography.

---

## 2. Dual-Track Architecture

| Track | Purpose | Status |
|-------|---------|--------|
| **Research prototype** | Terminology lookup, OMOP concept resolution, quantum research simulations with mandatory error bounds, workflow orchestration | Implemented |
| **Future SaMD pathway** | Predetermined Change Control Plan (PCCP) templates; SaMD checklist mapped to QMSR, IEC 62304, ISO 14971, FDA cybersecurity and AI lifecycle guidance | Scaffold only — no marketing submission |

No component on the research track may assert clinical decision support. No component on the SaMD track may claim clearance.

---

## 3. Implemented Components

### 3.1 API Gateway (`api/main.py`)

FastAPI application wiring engines to a clinician-facing frontend. Session control, audit logging, and integrity seals follow HIPAA Security Rule technical safeguards (45 CFR 164.312). FHIR interoperability defaults to **R4 US Core**; R5 is available as an optional research layer.

### 3.2 Terminology & Data Model Bridges

| Module | Role | Source authority |
|--------|------|------------------|
| `engines/nlm_clinical_tables.py` | Thin client for NLM Clinical Table Search Service (ICD-11, ICD-10-CM, HCPCS, HPO) | [clinicaltables.nlm.nih.gov](https://clinicaltables.nlm.nih.gov/) |
| `engines/omop_cdm_bridge.py` | OMOP concept search / ID lookup (no record fabrication) | OHDSI; DARWIN EU and FDA Sentinel standardize on OMOP |
| `engines/omop_cdm_v54_schema.py` | Structural reference for OMOP CDM **v5.4** clinical tables (PERSON, VISIT_OCCURRENCE, CONDITION_OCCURRENCE, DRUG_EXPOSURE, MEASUREMENT, etc.) | [ohdsi.github.io/CommonDataModel/cdm54.html](https://ohdsi.github.io/CommonDataModel/cdm54.html) |

**Note on Athena:** OHDSI Athena does not expose an official public REST API. Production research deployments should load the vocabulary zip locally or use community SDKs (athena-client, OMOPHub) under appropriate licenses.

### 3.3 Quantum Research Layer

| Module | Role |
|--------|------|
| `engines/quantum_research_prototype.py` | Classical state-vector / matrix simulation by default; optional PennyLane device. **Every public method returns an explicit `error_bound` and research-advisory envelope.** |
| `engines/quantum_medical_research_catalog.py` | Literature-backed catalog of quantum medical technology domains (VQE, CVaR-VQE, QML classifiers, quantum sensing, quantum-safe cryptography) |

**VQE error mitigation (documented, not claimed as clinical):**

- Zero-Noise Extrapolation (ZNE)
- Probabilistic Error Cancellation (PEC)
- Randomized Compiling (RC) combined with ZNE
- Readout error mitigation (e.g., T-REx)
- Characterization-based frameworks aiming for lower-overhead unbiased estimates

These techniques improve expectation-value accuracy on NISQ hardware but do **not** guarantee chemical accuracy or clinical utility. Systematic reviews of quantum machine learning in digital health report no consistent empirical advantage over strong classical baselines at present scale.

**Quantum sensing (catalogued for awareness only; out of software runtime scope):**

- Optically pumped magnetometer MEG (OPM-MEG) — wearable, room-temperature; channel counts scaling; regulatory approvals reported in some jurisdictions
- Nitrogen-vacancy (NV) center / quantum diamond microscopy — nanoscale magnetic imaging
- Research concepts for quantum-sensing MRI using intrinsic nuclear spins
- Photon-counting CT, quantum optical coherence tomography, quantum-dot probes

Near-term translational value is generally assessed as higher for sensing hardware than for quantum computing algorithms.

### 3.4 Regulatory Scaffolds

| Artifact | Content |
|----------|---------|
| `regulatory/pccp_scaffold.md` | Empty three-section PCCP (Description of Modifications, Modification Protocol, Impact Assessment) per FDA final guidance on AI-enabled device software functions |
| `regulatory/samd_checklist.py` | Programmatic emission of PCCP template + readiness checklist referencing QMSR (effective 2026), IEC 62304 (Ed. 2 expected), ISO 14971, FDA cybersecurity final guidance (2026), and AI lifecycle draft guidance |

### 3.5 Research Workflows (`engines/research_workflows.py`)

Named, auditable action sequences:

1. `omop_concept_research`
2. `nlm_terminology_research`
3. `quantum_research_simulation`
4. `regulatory_scaffold`
5. `system_research_health`

### 3.6 Supporting Engines

- `hipaa_security_controls.py` — sessions, audit JSONL, HMAC integrity
- `fhir_r5_interop.py` — version preference and interop helpers
- `evidence_ledger.py` — append-only research event log
- `realtime_analytics.py` — latency and operational metrics

---

## 4. Key Public Routes (Research)

```
GET  /api/v1/research/omop/search
GET  /api/v1/research/omop/concept/{concept_id}
GET  /api/v1/research/omop/schema
GET  /api/v1/research/nlm/icd11
GET  /api/v1/research/nlm/icd10cm
GET  /api/v1/research/quantum/health
GET  /api/v1/research/quantum/vqe-toy
GET  /api/v1/research/quantum/catalog
GET  /api/v1/research/workflows
GET  /api/v1/research/workflows/{workflow_id}
GET  /api/v1/regulatory/pccp-template
GET  /api/v1/research/health
```

All responses include:

```json
{
  "status": "research-advisory",
  "human_authority_final": true,
  "not_samd": true
}
```

---

## 5. Equity and Global-Health Alignment

TMRDS does not gate research tooling by geography or institutional resources. Referenced open resources include:

| Resource | Contribution |
|----------|--------------|
| **dd4gh** (Medicines for Malaria Venture + deepmirror; Gates Foundation support) | Free AI-assisted molecule design for malaria, tuberculosis, and neglected tropical diseases, prioritized for LMIC researchers |
| **DNDi Open Science** / COVID Moonshot / ASAP | Open structural data and licensing models intended to support affordable access |
| **REWARD** | Open-source framework for drug-repurposing signals on OMOP-mapped real-world data |
| **OHDSI / Athena / DARWIN EU** | Standardized vocabularies and federated real-world evidence without shipping patient-level data across borders |
| **NLM Clinical Tables / PubMed / UniProt / AlphaFold DB** | Public terminology, literature, sequence, and structure resources |

Rural open-source stack components planned for real REST/DICOM integration (not quantum-dependent): OpenEMR, Orthanc PACS, OpenELIS, Kiwix WikiMed.

---

## 6. Hard Constraints (Non-Negotiable)

1. **No fabricated clinical databases** — no invented disease prevalence, pathway, or molecular seed files presented as medical fact.
2. **No diagnostic or therapeutic recommendations** from quantum, ML, or retrieval modules.
3. **Read-only public sources** for terminology and literature ingestion.
4. **G1P compliance** — anti-deception, transparent audit trails, child protection, right to exit/delete.
5. **Explicit error bounds** on every quantum research response.
6. **Human authority final** — software never overrides licensed clinician judgment.

---

## 7. References (Selected)

### Regulatory

1. FDA. *Marketing Submission Recommendations for a Predetermined Change Control Plan for Artificial Intelligence-Enabled Device Software Functions.* Final guidance, Dec 2024 (updated Aug 2025).
2. FDA. *Artificial Intelligence-Enabled Device Software Functions: Lifecycle Management and Marketing Submission Recommendations.* Draft, Jan 2025.
3. FDA. *Cybersecurity in Medical Devices: Quality Management System Considerations and Content of Premarket Submissions.* Final, Feb 2026.
4. FDA Quality Management System Regulation (QMSR), 21 CFR Part 820 as amended (effective Feb 2026); harmonization with ISO 13485:2016.
5. IEC 62304 (medical device software lifecycle); Edition 2 expected to address AI/ML lifecycle phases.
6. ISO 14971 (application of risk management to medical devices).
7. 45 CFR 164.312 (HIPAA Security Rule technical safeguards).

### Data Models & Terminologies

8. OHDSI. *OMOP Common Data Model v5.4 Specification.* https://ohdsi.github.io/CommonDataModel/cdm54.html
9. U.S. National Library of Medicine. Clinical Table Search Service. https://clinicaltables.nlm.nih.gov/
10. WHO. International Classification of Diseases, 11th Revision (ICD-11); accessed via NLM ICD-11 Codes API.
11. EMA / DARWIN EU. Data Analysis and Real World Interrogation Network — OMOP CDM standardization for European RWE partners.

### Quantum Computing & Sensing (Illustrative)

12. Systematic and institutional reports on VQE / CVaR-VQE for molecular simulation and mRNA structure (Cleveland Clinic–RIKEN–IBM; IBM–Moderna collaborations, 2024–2026).
13. Error mitigation literature: zero-noise extrapolation, probabilistic error cancellation, randomized compiling + ZNE, readout mitigation, characterization-based methods (Phys. Rev. A; arXiv utility-scale mitigation studies, 2024–2026).
14. Quantum sensing reviews: OPM-MEG, NV-center imaging, photon-counting CT, quantum OCT (Frontiers in Physics and related 2025–2026 reviews); first-in-jurisdiction OPM-MEG authorizations reported.
15. npj Digital Medicine systematic review of quantum machine learning for digital health (2025) — limited evidence of consistent empirical advantage at current scale.

### Global Health & Open Science

16. Medicines for Malaria Venture & deepmirror. *Drug Design for Global Health (dd4gh).* https://dd4gh.ai/
17. Drugs for Neglected Diseases initiative (DNDi). Open science policy and portfolio (including Moonshot / ASAP lineage).
18. REWARD open-source framework for identifying medication benefits on OMOP CDM data (JAMIA, 2026).

### Governance

19. Tucker AJ. *GodFirst LLM/ML Protocol (G1P).* https://github.com/ATphobia22/godfirst-llm-ml-protocol

---

## 8. Deployment

```bash
pip install -r requirements.txt
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

See `docs/DEPLOY_DOCTOR_CONSOLE.md` and `docker-compose.yml`. Default clinician credentials must be rotated before any networked deployment.

---

## 9. Disclaimer

TMRDS outputs are for **research and educational exploration only**. They are not medical advice, not a diagnosis, not a prescription, and not a substitute for the judgment of a licensed clinician. The steward and contributors accept no liability for clinical decisions made in reliance on this software. Human authority is final.

---

*End of document.*
