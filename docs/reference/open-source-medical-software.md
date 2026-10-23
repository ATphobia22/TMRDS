# Open-Source Medical Software — Verified Catalog (2026-10-23)

**Purpose:** a verified directory of open-source medical software for TMRDS planning —
deployment references, library building blocks, and wireable integration targets.
Every entry below was checked against primary sources (official docs, repos, project
pages) in two verify-or-flag passes (2026-10-18, 2026-10-23). Anything unverifiable is
marked UNVERIFIED, not asserted.

**Standing posture:** TMRDS is research-advisory only. These are operational systems and
research tools — evidence-navigation context, never clinical decision-making authority.
None is a medical device or clinically validated for diagnosis. Human clinical authority
is final. No AWS-hosted dependency: anything AWS-locked or cloud-mandatory is excluded.

**Scorecard:** 32 entities checked across both passes — 25 verified REAL (several with
corrections), 4 misleading specifics, 3 archived/stagnant, 5 invented or misattributed
names (must never appear in TMRDS materials: "Ambys", "Awesome Medical AI", "SynthHealth",
"CardioRhythm", "OpenCPR").

## Key corrections to the pasted overviews

- **Bahmni's ERP is Odoo, not ERPNext.** Real stack: OpenMRS + OpenELIS + Odoo + PACS.
- **"NextGen Connect" is not the product name.** Still officially "Mirth Connect";
  commercial/proprietary since 4.6 (Mar 2025); 4.5.2 is the last frozen open-source release.
- **FHIR Works on AWS is dead** (EOL 2024-01-31, repo archived) and AWS-serverless — excluded.
- **HospitalRun is archived** (last code Jan 2023) — study only.
- **"SynthHealth" doesn't exist** — the real project is **Synthea** (`synthetichealth/synthea`).
- **"CardioRhythm" doesn't exist** as open source — the real tool is **ECGSyn** (PhysioNet).
- **"OpenCPR" doesn't exist** as an openEHR project — the real legacy tool is **OpenSDE**
  (Delphi, 2003–2005, LGPL).
- **"BioPython" is properly "Biopython"** (one word).
- **MedGemma 1.5 "~91% MedQA" is false** — the open 4B model scores 69.1%; 91.1% belongs to
  proprietary Med-Gemini. (From the 2026-10-18 models investigation.)
- **NVIDIA Clara is a commercial suite, not open source** — use MONAI core instead.

## EHR & hospital systems (deployable references)

| Project | License | 2026 status | TMRDS fit |
|---|---|---|---|
| OpenEMR | GPL-2.0 | v8.4.0; ONC-certified (cert #15.05.05.3115.OPEN.02.01.1.260130, Jan 2026) | Reference EHR; on-premise only (cloud edition is AWS) |
| GNU Health | GPL-3.0-or-later | 5.0.7 (Apr 2026); official GNU package | Strongest ideological match — no telemetry, full data sovereignty |
| OpenMRS | MPL-2.0 + Healthcare Disclaimer | Platform 2.8.x | Reference EHR; REST/FHIR APIs are wireable |
| Bahmni | AGPL-3.0 | Active; 500+ implementations, 50+ countries | Reference stack; wire via APIs (AGPL — do not embed code) |
| HospitalRun | MIT | **Archived** Jan 2023 | Study only |

## Medical imaging: PACS, viewing, I/O (deployable + libraries)

| Project | License | 2026 status | TMRDS fit |
|---|---|---|---|
| Orthanc | Core GPLv3, plugins AGPL | 1.13.0 (Aug 2026) | Best wireable REST/DICOMweb imaging source; mini-PACS |
| OHIF Viewer | MIT | v3.11; NIH/NCI-funded | Embeddable viewer front-end (pairs with Cornerstone3D) |
| Cornerstone3D | MIT | v5 line | In-browser rendering for a future image-evidence viewer |
| pydicom | MIT | 3.0.2 (May 2026; fixed CVE-2026-32711) | DICOM I/O + metadata/provenance extraction |
| ITK | Apache-2.0 | 5.4.7 (Aug 2026) | Offline registration/segmentation/filtering algorithms |
| SimpleITK | Apache-2.0 | 2.5.6 (Jul 2026) | Rapid prototyping over ITK (Python + 7 more languages) |
| 3D Slicer | BSD-style | 5.12.4 (Sep 2026); explicitly research-only, NOT FDA-approved | Reference workbench only |
| dcm4chee | MPL/triple (verify per release) | 5.34.3–5.35.2 active; **critical CVE Oct 2026 on default config** | Reference only unless hardened |

## Imaging deep-learning frameworks (library building blocks)

| Project | License | 2026 status | TMRDS fit |
|---|---|---|---|
| MONAI (core) | Apache-2.0 | monai 1.5.2 (Jan 2026); Aug 2026 pickle CVEs — pin versions, treat deserialization as untrusted | Research training/benchmarking; core only (NVIDIA packaging is paid) |
| nnU-Net | Apache-2.0 | nnunetv2 2.6.4 (Feb 2026) | Self-configuring segmentation baseline |
| TorchIO | Apache-2.0 | Canonical repo `TorchIO-project/torchio` | Preprocessing/augmentation for imaging pipelines |
| TotalSegmentator | Apache-2.0 code; key-gated subtasks (free non-commercial) | 2.18.0; "117" = CT `total` task only (MR = 50) | Offline anatomy labeling on anonymized/published scans; README: not a medical device |

## Interoperability (wireable targets)

| Project | License | 2026 status | TMRDS fit |
|---|---|---|---|
| HAPI FHIR | Apache-2.0 | v8.8.2 (Sep 2026); self-hostable | The wireable FHIR R4 target — deployable server, no AWS conflict |
| Medplum | Apache-2.0 (open-core) | v5.1.42 (Sep 2026); self-hostable, not AWS-locked | Deployable FHIR R4 backend; keep out of patient-data scope |
| NextGen/Mirth Connect | Commercial since 4.6 | 4.5.2 last OSS (frozen) | Reference only |
| FHIR Works on AWS | Apache-2.0 | **EOL 2024-01-31, archived** | Excluded (dead + AWS) |

## Lab, pharmacy, logistics

| Project | License | 2026 status | TMRDS fit |
|---|---|---|---|
| OpenELIS Global | MPL-2.0 | 3.2.3.0; FHIR R4 native; very active 2026 | Wireable lab APIs |
| OpenLMIS | AGPL-3.0 | Ref-distro 3.19.0; 10k+ facilities | Outside evidence-navigation scope; reference only |

## Research, analytics, data models

| Project | License | 2026 status | TMRDS fit |
|---|---|---|---|
| i2b2 | MPL-2.0 (current) | 1.8.3 (Jun 2026) | Cohort-discovery reference architecture |
| OHDSI / OMOP CDM | Community / open standard; ATLAS Apache-2.0 | ATLAS 3.0 preview (Jul 2026) | OMOP CDM as a data *model* for organizing evidence (not a queryable API) |
| Invenio RDM | MIT | v14.0 (Aug 2026); CERN-coordinated | Strongest fit — evidence/dataset repository pattern with DOIs |
| Biopython | Dual BSD-compatible | v1.87 (Mar 2026) | Sequence/dataset parsing for genomics pipelines |

## Synthetic data generators (methods-level only)

| Project | License | Standing rule |
|---|---|---|
| Synthea | Apache-2.0 | Test-fixture generator for pipeline validation. "Realistic, but not real." Label synthetic everywhere; never clinical evidence. |
| ECGSyn | GPL | Synthetic ECG waveforms with recorded limitations (simplified morphology, no pathology-specific shapes). Label synthetic everywhere; never present synthetic benchmarks as clinical performance. |

Copyleft flags: Fasten Health (GPL-3.0), ECGSyn (GPL), old PatientView code (GPL-3.0) — keep out of permissively-licensed cores. Fasten Health and PatientView are reference-only (weak TMRDS fit).

## Standing caveats

- None of these are evidence corpora. TMRDS evidence sources remain the literature / trial /
  registry / label / chemistry pipelines. These are deployment and integration references.
- AGPL-3.0 (Bahmni, OpenLMIS) and GPL copyleft items: wire via REST/FHIR APIs, never embed
  or modify code inside permissively-licensed cores.
- Every integration stays research-advisory: provenance-labeled outputs, human clinical
  authority final, no diagnosis/treatment/cure claims.
- Source investigations: `~/workspace/research_notes/tmrds-open-source-medical-ai-20261018/`
  (models), `~/workspace/research_notes/tmrds-open-source-medical-software-20261023/`
  (systems), `~/workspace/research_notes/tmrds-medical-imaging-repos-20261023/` (imaging).
