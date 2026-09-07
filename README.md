# TMRDS — Tucker Medical Research and Development System

**Research-advisory** platform for Tri-State (IN / IL / KY) clinics and precision research.

> Technology informs people; it does not silently govern people. **Human authority remains final.**

**Steward:** Anthony John Tucker · Mount Vernon, Indiana 47620  
**Regulatory posture:** Not FDA-cleared SaMD. Advisory outputs only.

---

## Medical professionals — start here

1. **[docs/MEDICAL_PROFESSIONAL_INSPECTION.md](docs/MEDICAL_PROFESSIONAL_INSPECTION.md)** — safety checklist & standards  
2. **[docs/ARCHITECTURE_VERIFICATION.md](docs/ARCHITECTURE_VERIFICATION.md)** — what was verified, incorporated, or rejected  
3. **[docs/SAMD_IEC62304_ISO14971.md](docs/SAMD_IEC62304_ISO14971.md)** — process scaffold (not certification)

---

## Verified layers (2026-09)

| Layer | Module |
|-------|--------|
| Multi-agent advisory swarm | `ClinicalSwarmOrchestrator` |
| Epistemic parallel branches | `EpistemicParallelRouter` |
| Dual-tier memory (Redis-ready + long context) | `DualTierMemory` |
| IEEE 11073 PHD → FHIR | `IEEE11073PHDBridge` |
| Structure (AF3 + ESMFold interfaces) | `AlphaFold3Node`, `ESMFoldStructureNode` |
| FHIR / OMOP / Atlas / NLM.gov | existing interop stack |
| Drive-Thru evidence APIs | `DriveThruIngestion` |
| Ethics / ledger / sovereign edge | `DoctorDignityEthics`, `EvidenceLedger`, `SovereignEdge` |

**Not claimed:** clinical 6G product network, disease “cures,” 8512 TPS, street-address SSoT, CRISPR care automation, religious seals as clinical validation.

---

## Path

```
Device (IEEE 11073) / labs / genome
  → UniversalClinicalIngest + FHIR/OMOP maps
  → DriveThru + NLM.gov evidence
  → Swarm / Epistemic routers (advisory)
  → QRCE + KRAGEN  → EvidenceLedger → clinician
```

**Repo:** https://github.com/ATphobia22/TMRDS
