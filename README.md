# TMRDS
## Tucker Medical Research and Development System

**A portable, evidence-grounded biomedical research workspace—designed to make trustworthy medical knowledge and scientific tools more accessible, especially where infrastructure and specialist resources are limited.**

[Explore the public research workspace](https://tmrds-public-evidence-api.onrender.com/) · [Static evidence atlas](https://atphobia22.github.io/TMRDS/) · [Offline FieldLab guide](docs/integrations/fieldlab-offline-workstation-20261123.md) · [Intended use and safety boundaries](docs/INTENDED_USE.md)

> **Current status: research and engineering platform—not a clinical diagnostic product.** TMRDS can retrieve and organize public biomedical evidence, inspect certain local scientific files, and run bounded research demonstrations. It does **not** currently provide validated patient diagnoses, treatment recommendations, autonomous clinical decisions, MRI/CT interpretation, gene-editing instructions, or drug-efficacy predictions. It is not FDA-cleared, ONC-certified, or independently validated for patient care. Do not upload patient records to the public website.

---

## Why TMRDS exists

A physician working in a rural clinic, a researcher at a small institution, or a healthcare team serving a remote community should not have to choose between access to scientific knowledge and the ability to work without reliable Internet, expensive enterprise software, or a large laboratory infrastructure.

Modern biomedical knowledge is scattered across publications, clinical-trial registries, drug labels, molecular databases, genomic resources, imaging formats, and local records. Finding a paper is relatively easy; establishing **where the information came from, how recent it is, what it actually supports, and what remains uncertain** is harder. Internet outages and limited hardware make that problem worse.

**TMRDS was created to narrow that gap.** Its long-term goal is a portable, affordable, multidisciplinary research assistant that gives qualified professionals a coherent workspace for literature, laboratory data, imaging research, genomics, pharmacology, and scientific computation—with a practical offline path for under-resourced settings.

The intended result is **faster access to reviewable information**, not a machine that replaces a physician. The aspiration to move useful research workflows from days toward minutes is a design goal, **not a demonstrated clinical turnaround-time guarantee**.

### Principles behind the design

1. **Access:** public research should be usable without a subscription or personal account where feasible.
2. **Offline resilience:** essential local tools should continue operating on a prepared laptop without cloud access.
3. **Evidence before answers:** every sourced finding should retain an origin, identifier, retrieval date, and limitations.
4. **Real integration:** executable software and tested interfaces take priority over a long catalog of links.
5. **One workspace, many disciplines:** literature, imaging, chemistry, genomics, lab formats, and model governance should connect through explicit contracts.
6. **Human authority is final:** research outputs and AI predictions are never silently promoted to clinical facts.
7. **Honest failure states:** stale, partial, inaccessible, conflicting, or unverified evidence stays visibly marked.

## What you can use today

TMRDS has **multiple distinct execution environments**. A feature implemented in one is not automatically installed or available in the others.

| Capability | What is implemented | Where it works | Important limit |
|---|---|---|---|
| **Public evidence atlas** | Source-linked biomedical search and interactive 3D research navigation | Web browser, connected | Public metadata only; network and upstream availability required |
| **Cross-source evidence review** | Governed, bounded federation across **22 source adapters**, with identifiers, statuses, timestamps, and source receipts | Connected Python research API | Not exhaustive; correlated database records are not independent experimental validation |
| **Research dossiers and disease pathways** | Cited evidence exports; exact-ID disease → target → compound research links | Backend research endpoints | Associations and registry records do not prove treatment efficacy |
| **Offline citation pack** | Prepare, hash-check, transfer, and search a bounded cache of public citation metadata | Connected preparation, then offline laptop | Not a complete medical library or full-text archive |
| **FieldLab scientific readers** | Execute actual pydicom, NiBabel, Biopython, RDKit, and bounded lab-file inspection | Offline Windows 11 x64 with Python 3.11 | File inspection, not validated clinical interpretation |
| **Offline specialist swarm** | Local-only research interface, deterministic demonstrations, synthetic data and reviewed citation search | Offline Python/browser on loopback | HTML demonstration does not accept patient uploads |
| **Imaging research workflow** | Bounded DICOMweb reads, an OHIF provenance/review mode, MONAI bundle review, human annotation and static exports | Separately configured research sandbox | Not a hospital PACS deployment or clinically validated AI |
| **Genomics and molecular research** | Public variant/target/pathway metadata; local sequence parsing and chemical descriptors | Connected API and selected offline tools | No patient-level variant interpretation, docking efficacy, or gene-editing recommendations |
| **Interoperability prototypes** | Synthetic FHIR R4 workflows, selected resource validation, audit/provenance contracts and OMOP-oriented design | Development and research environments | No live EHR/HIE connection or certified FHIR/US Core conformance |
| **Quantum-inspired research planning** | Rotating Rubik's Cube visualization and a real **classically simulated six-qubit Grover search** over abstract evidence-coverage configurations | Web/API and selected offline research workflows | No quantum speedup, clinical likelihood calculation, or connected quantum hardware by default |

**Software catalog versus installed capability:** the repository also documents a larger medical software and source registry (currently **122 entries**). Entries may be integrated, optional, not installed, or reference-only. Inclusion in the catalog **does not** mean a tool, trained model, dataset, or its license has been installed, approved, or clinically validated. See [the source/software inventory](docs/reference/open-source-medical-software.md).

## The TMRDS workspace

### 1. Research across biomedical knowledge

TMRDS provides one research entry point to several kinds of evidence:

- **Publications and citations:** PubMed, Europe PMC, Crossref, OpenAlex, Semantic Scholar, arXiv, and bioRxiv/medRxiv.
- **Trials, regulatory information, and drug labels:** ClinicalTrials.gov, openFDA, DailyMed, and FDA Orange Book patent/exclusivity metadata.
- **Molecules, compounds, and proteins:** PubChem, ChEMBL, RxNorm, UniProtKB, and separate AlphaFold Database structure metadata lookups.
- **Genetics and disease biology:** Ensembl, ClinVar, gnomAD, GTEx, GWAS Catalog v2, Open Targets, STRING, Reactome, Monarch, NCATS Node Normalization, and MeSH.

The repository contains approximately **25 federated public metadata adapters**, with **22** wired into the governed multi-source cross-check. Individual frontends expose smaller subsets: the static GitHub Pages atlas performs direct browser lookups, while the separate Python gateway provides the bounded federated routes. A source may fail, impose rate limits, or return no matches; TMRDS preserves that distinction.

Reviewers can inspect DOI, PMID, PMCID, NCT, genomic identifiers, provider attribution, retrieval timestamps, source errors, and bibliographic overlap. The [research dossier](docs/operations/research-dossier.md) and [governed evidence pathway](docs/integrations/governed-evidence-pathway.md) are designed to make the underlying evidence inspectable rather than delivering an unexplained conclusion.

### 2. The Quantum Rubik's Cube engine

The interactive **3D Rubik's Cube** represents the challenge of bringing multiple independent research disciplines into alignment. Its visible cubies animate and support manual layer turns, while the backend includes an actual **six-qubit classical statevector implementation of Grover's algorithm** for a bounded research-coverage planning experiment.

The six evidence-coverage planes are an organizing model, **not medical measurements**. The simulator evaluates abstract combinations, reports its oracle configuration and reproducible calculation receipt, and distinguishes its results from source-backed medical evidence.

**A rotating cube is not a quantum computer.** The demo does not use a QPU, solve disease, infer treatment effectiveness, predict drug binding, or turn probability amplitudes into diagnostic confidence. IBM Quantum integration is optional and disabled for remote submission unless deliberately configured and authorized. See [the QRCE technical roadmap](docs/integrations/qrce-grover-molecular-roadmap-20261123.md) and [IBM Quantum operations](docs/integrations/ibm-quantum-compute.md).

### 3. A scientific FieldLab on a disconnected laptop

The **FieldLab** research preview executes scientific libraries locally rather than simply listing them. The supported bounded operations include:

| Actual local library | Supported research function |
|---|---|
| **pydicom** | Read DICOM Part-10 headers and optional bounded pixel statistics, including modality-LUT handling where supported |
| **NiBabel** | Inspect NIfTI headers, image dimensions, geometry and voxel spacing |
| **Biopython** | Parse FASTA/FASTQ and compute limited sequence and quality summaries |
| **RDKit** | Parse public SMILES and calculate basic molecular descriptors |
| **Python/standard-library helpers** | Inspect selected numeric lab CSV/TSV and structured synthetic FHIR resources |
| **pypdf** (separate workstation profile) | Inspect PDF page/text-extraction capability without returning document contents |

This is a **real offline execution path**, not a validated MRI reader, genetics diagnosis engine, automated laboratory instrument, or molecular docking service. The standalone FieldLab Tkinter GUI requires **no browser or local HTTP server**. A separate offline HTML specialist interface uses a loopback-only Python coordinator for synthetic demonstrations and approved local research metadata.

**Current distribution:** a hashed Windows wheelhouse/ZIP research artifact, **not** a self-contained or signed one-click installer. Python **3.11 x64 must be installed before disconnecting**. See [FieldLab installation](docs/integrations/fieldlab-offline-workstation-20261123.md), [offline workstation](docs/operations/portable-offline-workstation.md), and [specialist swarm architecture](docs/architecture/offline-html-swarm.md).

### 4. Imaging, laboratory, genomic, and molecular research

TMRDS is being engineered to join disciplines that normally sit in separate programs:

- **Imaging:** bounded QIDO-RS DICOMweb query support; OHIF research mode displaying Study/Series/SOP UIDs, provenance and review state; optional local Orthanc sandbox; checksum and license review before MONAI research weights are loaded; human annotation workflows and static research exports.
- **Laboratory and interoperability:** synthetic FHIR Observation/Bundle workbench, lab metadata and trends for test data, explicit source/units/status semantics, and versioned evidence records.
- **Genomics:** public variant-frequency, consequence, association, gene-expression and pathway references, with separate local FASTA/FASTQ parsing.
- **Pharmacology and chemistry:** source-linked compound and assay metadata, FDA labels and Orange Book research records, plus RDKit descriptors.

These are **research components at different maturity levels**. The imaging sandbox has not demonstrated a clinically validated model reading patient CT/MRI studies. Genomic associations do not establish causation; molecular descriptors do not predict efficacy; patent listings do not constitute a freedom-to-operate opinion. The [imaging implementation notes](docs/integrations/imaging-research-workflow.md) specify the executable boundaries and human-review gates.

### 5. Traceable evidence, safety, and governance

TMRDS favors a source-first architecture:

```text
Public biomedical sources                  Authorized local research files
          |                                            |
Bounded source-specific adapters                 Offline scientific readers
          |                                            |
Source identity + timestamps + status          Local bounded inspection
          |                                            |
Governed evidence review                      Human review and local outputs
          |
Research dossier / approved metadata snapshot
          |
Verified offline citation cache
```

The connected API and offline tools are intentionally separate from clinical systems. Records are normalized into evidence envelopes with provenance. Data-store options include PostgreSQL/pgvector for governed research records and Neo4j for derived relationships; neither a vector result nor a graph edge replaces an original source.

Controls and conventions include bounded requests, explicit source unavailability, checksums, model-weight review, synthetic test fixtures, audit metadata, human-review states, and separation between observed data and predictions.

**Do not treat a passing test, a checksum, or a source citation as proof of clinical safety, authenticity, regulatory clearance, de-identification, or data-use permission.**

## How to get started

### Option A — Explore public research online

Visit the [connected research workspace](https://tmrds-public-evidence-api.onrender.com/) or [GitHub Pages atlas](https://atphobia22.github.io/TMRDS/). Use **public research terms only**. The static Pages site does not run the Python backend; the connected workspace provides a separate same-origin research gateway. Public hosting and upstream provider availability can change.

**Never submit patient names, scans, genomic records, laboratory results, clinical identifiers, or confidential institutional information to the public endpoints.**

To run the isolated public gateway locally, with Docker installed:

```bash
docker compose -f compose.public.yml config
docker compose -f compose.public.yml up --build -d
curl -fsS http://127.0.0.1:18080/health/ready
curl -fsS http://127.0.0.1:18080/api/v1/research/source-governance
```

Open `http://127.0.0.1:18080/` for the same-origin public research frontend. Readiness checks the gateway process; it does not certify the availability or currency of external sources.

### Option B — Prepare a research metadata pack for offline use

From a trusted connected preparation computer with Python 3.11+ and the reviewed source checkout:

```bash
python scripts/offline_evidence_pack.py prepare --query CFTR --out citations.json
python scripts/offline_evidence_pack.py verify --path citations.json
```

Transfer the file to the field laptop using an authorized method. With the laptop disconnected:

```bash
python scripts/offline_evidence_pack.py verify --path data/offline/citations.json
python scripts/offline_evidence_pack.py search --path data/offline/citations.json --term CFTR
python -m scripts.run_offline_swarm --port 8765
```

The last command serves the local research demo at `http://127.0.0.1:8765/`; citation search is available at `/evidence.html`. The pack contains **bounded citation metadata**, not full papers or a complete offline medical knowledge base. Copy the verified pack to `data/offline/citations.json` for automatic discovery by this interface. See [offline citation pack documentation](docs/integrations/offline-citation-metadata-pack-20261123.md).

### Option C — Use Windows 11 FieldLab without Internet

On a trusted connected computer, obtain the successful **TMRDS Offline FieldLab Libraries and Win11 Wheel Bundle** workflow artifact, verify its published SHA-256, and transfer the ZIP. Install Python **3.11 x64** on the Windows laptop before travel, then extract the bundle.

In PowerShell, from the extracted bundle directory:

```powershell
powershell.exe -NoProfile -File .\scripts\install_fieldlab_windows.ps1 -BundleDir .
.\.fieldlab-venv\Scripts\python.exe .\scripts\fieldlab_cli.py status
.\.fieldlab-venv\Scripts\python.exe .\scripts\fieldlab_desktop.py
```

The installer uses the included local wheels with no package index. For separately authorized local files, consult the [documented CLI flags and file limits](docs/integrations/fieldlab-offline-workstation-20261123.md). Device encryption, access control, file retention, and applicable patient-data rules remain the responsibility of the operator or institution.

### Option D — Development and validation

Core development targets Python 3.11:

```bash
python scripts/check_dependency_lock.py
python -m compileall -q api engines scripts tests
python -m pytest -q -m "not integration"
python scripts/check_public_site.py
```

For the complete optional data/graph stack and safe migrations, consult the [operations runbook](docs/operations/tmrds-operations-runbook.md). It requires operator-provided secrets, explicit migration control, and deployment review. Do not expose the full development API or data stores as a substitute for the isolated public gateway.

## The longer-term vision

The architectural goal is a **portable, multidisciplinary physician-and-researcher workstation** that can assist in remote and resource-constrained locations. Important next-stage work includes:

| Direction | What must happen before it is a trustworthy clinical feature |
|---|---|
| **AI-assisted MRI/CT and pathology analysis** | Appropriately licensed models and datasets; patient-level security; independent case-level validation, calibration, radiologist review, and applicable regulatory review |
| **Laboratory result interpretation and clinical decision support** | Analytical and clinical validation, unit/reference governance, real workflow evaluation, explainable evidence, and appropriate regulatory review |
| **Precision genomics, splicing, and gene-editing research** | Rigorous variant interpretation, biological verification, ethical oversight, and specialist-led validation; no autonomous therapeutic recommendations |
| **Protein structures, cryptic pockets, docking, and drug discovery** | Reproducible structural methods, appropriate benchmarks, experimental confirmation, model/dataset licenses, and clear separation of prediction from effect |
| **Rich offline medical knowledge** | Authorized content redistribution, dated snapshots, staleness controls, local indexing, source reconciliation, and sustainable updates |
| **Practical low-resource deployment** | Signed self-contained installer, clean Windows 11 offline tests, hardware/performance characterization, resilience, accessibility, and operator training |
| **Authorized institutional interoperability** | Consent, access controls, audit/retention, real FHIR/US Core and DICOMweb conformance testing, contracts, and privacy/security assessment |

**These are engineering goals, not descriptions of completed or approved features.** An open-source library alone does not establish that TMRDS has integrated it, licensed its weights or data, tested its performance, or made it safe for clinical use.

## Responsible use

TMRDS is currently **research-advisory software**. Its intended use is public biomedical discovery and bounded scientific experimentation. It is **not** a medical device cleared or approved for diagnosis or treatment, a replacement for radiologists or clinicians, a prescription engine, or an emergency decision system. The repository is not connected to a live hospital or patient database, and the hosted public service must never receive protected or identifiable patient information.

Any future feature processing patient images, diagnostic signals, or patient-specific clinical decisions requires an explicit **reassessment of intended use and regulatory classification**, as well as independent clinical validation and privacy/security controls. Current prototypes should not be assumed to qualify for any regulatory exemption. See [intended use](docs/INTENDED_USE.md), [SaMD checklist](docs/SAMD_CLASSIFICATION_CHECKLIST.md), and [interoperability compliance matrix](docs/INTEROPERABILITY_COMPLIANCE_MATRIX.md).

## Project structure

```text
TMRDS/
├── api/                 Public research gateway and separate development APIs
├── engines/             Evidence, scientific readers, interoperability and governance
├── public/              Public atlas and interactive 3D Cube
├── frontend/            Additional application surface
├── deploy/              Offline wheel profiles and deployment assets
├── scripts/             FieldLab CLI/GUI, offline packs, checks and operators
├── extensions/, modes/  OHIF research extensions and modes
├── offline/             Additional local research utilities
├── migrations/          Versioned research database migrations
├── workers/             Research source synchronization workers
├── tests/               Unit, contract, synthetic and integration tests
├── docs/                Intended use, architecture, source and operations records
└── .github/workflows/   Build, audit, security and release workflows
```

## Documentation and release evidence

- [Medical software inventory](docs/reference/open-source-medical-software.md) — integrations versus optional, cataloged, and not-installed projects.
- [22-source research cross-check](docs/integrations/qrce-source-fabric-20261123.md) — source adapter contracts, identifiers, and failure behavior.
- [Offline FieldLab and library execution](docs/integrations/fieldlab-offline-workstation-20261123.md) — supported formats, versions, setup and limits.
- [Offline citation packs](docs/integrations/offline-citation-metadata-pack-20261123.md) — preparation, hashing, permitted fields, and staleness.
- [Imaging research workflow](docs/integrations/imaging-research-workflow.md) — DICOMweb, OHIF provenance, MONAI review, annotation, and exports.
- [Release verification](docs/operations/branch-reconciliation-20261123.md) — historical branch reconciliation and November 23, 2026 CI evidence. A green workflow is technical evidence, **not clinical validation**.
- [Architecture and operations](docs/operations/tmrds-operations-runbook.md) — deployment, secrets, migrations, monitoring, and constraints.

---

### The guiding idea

**Make the world's available medical research easier to find, inspect, connect, and carry—without pretending that software can replace the judgment, accountability, or compassion of the people delivering care.**

*TMRDS is being built toward that goal in verifiable stages: source-backed evidence first, real local tools second, and clinical capabilities only when the necessary validation and governance exist.*
