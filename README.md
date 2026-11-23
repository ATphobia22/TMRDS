# TMRDS — Transparent Medical Research Decision Support

> **Research software — not a medical device.** TMRDS helps doctors and researchers find and cross-check public biomedical evidence faster. It does not diagnose, prescribe, treat, or replace clinical judgment. It is not FDA-cleared, clinically validated, HIPAA-compliant, ONC-certified, or connected to any live hospital system.

## Try it now

**[Open the fully connected TMRDS research workspace](https://tmrds-public-evidence-api.onrender.com/)** — a free, anonymous, same-origin Docker-backed research interface. **[GitHub Pages static atlas](https://atphobia22.github.io/TMRDS/)** remains the independently deployed static version with a rotating, interactive **3D Rubik's Cube**. The 26 visible cubies rotate continuously and their layers turn while searches run. You can select **Rotate a layer** to turn a face manually; reduced-motion preferences are respected. Search the live **Europe PMC**, **ClinicalTrials.gov v2** and **Crossref** services, inspect source identifiers and retrieval dates, and follow records to their origin.

**[TMRDS 2 — earlier public workspace preview](https://muse.ai/s/tmrds-2-xxd6j1fn9xyxwxf/DtP0Ir8DQV7MepeJdlvuTQBszwBcsygUi_QoYBYFruw)** documents the October 2026 research concept and is not the current production evidence atlas.

**Important hosting boundary:** GitHub Pages serves static HTML/CSS/JavaScript; it **does not run the Python research adapters**. The independent [free-plan Render HTTPS deployment](https://tmrds-public-evidence-api.onrender.com/) serves the same frontend and the read-only Python research API. Render free-plan availability and latency are not guaranteed, and its service readiness does **not** establish upstream data availability. The Rubik's Cube is a visual search indicator, **not** quantum computation.

### Deployment and verification status

| Capability | Verified status (November 23, 2026) |
|---|---|
| Animated 3D cube and manual layer turns | Live on GitHub Pages; browser smoke-tested |
| Public literature and trial searches | Live browser queries to Europe PMC and ClinicalTrials.gov returned real linked results |
| Public read-only research backend | **Public HTTPS deployed on Render free plan**; readiness/config/source metadata routes returned HTTP 200; original PMC, PubChem and bounded 22-source research queries independently tested |
| Federated research adapters | ~25 repository adapters; **22 metadata-only adapters wired into governed concurrent cross-check**. CFTR one-record-per-source live check: **18 responded, four source-unavailable**; does not prove complete coverage |
| Disease → target → compound link | Open Targets source-reported mechanism, exact MONDO / Ensembl / ChEMBL identifiers; bounded research lookup |
| Freshness, source rights, and provenance | Dated source receipts, release observations, conservative license-review gate, limited SHA-256 record hashes |
| Independent efficacy / clinical validation | **Not established**; one FDA-anchored technical reference case and a synthetic negative control are not a blinded clinical benchmark |

The [November 23 source audit](https://github.com/ATphobia22/TMRDS/actions/workflows/source-governance.yml) reported responses from **five** official APIs (Open Targets, ChEMBL, Europe PMC, ClinicalTrials.gov, GWAS Catalog v2), and its one-case CFTR/ivacaftor **technical identifier-consistency check passed**. That does not certify license permission, data currency, comprehensive coverage, or treatment effectiveness.

### New: Six-plane Grover search demonstration (no clinical inference)

The connected Rubik's Cube now has a **reproducible, bounded six-qubit Grover simulator**: `GET /api/v1/research/cube-search?required=disease_phenotype,target_pathway,trials_labels&max_planes=4`. An actual phase oracle and Grover diffuser amplify **synthetic research-coverage configurations** across 64 bitstrings and show a classical 64-evaluation baseline, exact success probability, deterministic SHA-256 oracle digest, and a no-quantum-hardware execution receipt. The static GitHub Pages version links to the separately deployed Python simulator; it cannot run that Python backend. **The reported probability is only a probability of selecting a source-coverage plan—not likelihood a treatment is effective or a cure exists.**

**Sparse Blossom/PyMatching is a quantum error-correction decoder, not a medical search algorithm.** The molecular graph-transformer named GROVER is unrelated to Grover's quantum algorithm. Seven verified, optional open-source software candidates (PyMatching, Stim, DeepChem, Boltz-2, scispaCy, medspaCy, Presidio) were added to the public registry as `optional_not_installed`, bringing the catalog to **122** entries, with zero new patient-data routes or unreviewed model installations. Mathematical tests and [implementation/validation notes](docs/integrations/qrce-grover-molecular-roadmap-20261123.md) accompany the code.

### Public research API deployment, independent verification and monitoring

- **HTTPS research runtime:** [https://tmrds-public-evidence-api.onrender.com/](https://tmrds-public-evidence-api.onrender.com/) — Docker `api.public_gateway`, read-only public methods, no PHI upload; Render free plan, Ohio region, auto-deploys from `main`.
- **Verified release:** `0ec2669c16ddca030ed3fc1dec9cd6b246cb13c9`, Render deployed **2026-11-23**. Live `/health/ready` HTTP 200 (`external_sources_verified:false`), `/backend-config.json` HTTP 200 (`same-origin`), public project and synthetic format endpoints HTTP 200.
- **Original-source checks:** live `/pmc-identifiers?identifier=PMC3531190` returned PMID `23193287`, PMCID `PMC3531190`, DOI `10.1093/nar/gks1195`; live `/periodic-element?symbol=Fe` returned the PubChem original **118-row table** with iron atomic number 26, without clinical inference.
- **Twenty-two-source fan-out:** live `/cross-check?query=CFTR&limit=1` HTTP 200, **18 of 22 sources responded**, 14 returned records, and four source requests failed. One-record bounds and a provider outage are not evidence-quality judgments or full-data discovery.
- **Operations:** scheduled [HTTPS contract smoke workflow](.github/workflows/public-api-smoke.yml), [operator documentation](docs/integrations/live-public-backend-20261123.md), plus the separate weekly upstream source audit. Public service uptime, upstream freshness, privacy compliance, clinical effect and model efficacy require independent assessment.

## Current: 22-source QRCE cross-check, PMC identifier bridge and live FDA/PubChem research

The [public evidence atlas](https://atphobia22.github.io/TMRDS/) searches
**Europe PMC, ClinicalTrials.gov and Crossref DOI metadata** directly from
the browser, with a separate ingredient-only **FDA Orange Book** search
for patent/exclusivity metadata. It also links to 20 official biomedical
research portals for human-triggered original-source searches.

The read-only research-only Python gateway now exposes
`GET /api/v1/research/cross-check`: **22 existing source adapters** queried
concurrently, with original-source bibliographic cross-reference by exact
DOI / PMID / PMCID / NCT, molecular context links that never merge independent
experiments, source failure isolation,
source provenance, metadata disagreements, hash-scoped receipt, and a
typed **OpenMI-inspired, nonclinical model exchange** (not OGC OpenMI
conformance). Each database's copyright and terms remain applicable.
Duplicate bibliographic indexing does NOT count as independent
experimental confirmation.

`GET /api/v1/research/patent-landscape?ingredient=METFORMIN&limit=2`
queries original **FDA Orange Book** records without asserting patent
expiration or freedom to operate. The FDA's reported dates (including
pediatric extension markers), US patent claims, regulatory exclusivity,
jurisdiction and current USPTO status require **separate legal review**.
Nothing here identifies a drug as an established new indication or cure.

The public catalog now lists **115 research databases, tools and scientific projects**, clearly distinguishing existing adapters from software not installed, catalog references and approval-gated resources. The **local-only synthetic research fixture inspector** handles CSV/TSV, selected FHIR JSON, sample-free VCF, FASTA and FASTQ within strict bounds; it never grants patient-level clinical ingestion.

`GET /api/v1/research/pmc-identifiers` maps official NIH PMC identifiers; `GET /api/v1/research/periodic-element?symbol=Fe` returns original PubChem periodic-table metadata. `GET /api/v1/research/file-format-capabilities` reports honest local-only parser support. These routes are present in the separately deployable research-only Python gateway.

The **static GitHub Pages site does not host a Python backend**, and no
EHR/PACS, medical device, quantum hardware or patient-record system
is deployed by this change.

[22-source data fabric, PMC, laboratory formats, controlled datasets and verification](docs/integrations/qrce-source-fabric-20261123.md).

[Source-to-QRCE architecture, official documents, uploaded-code safety
audit and reproducible gates](docs/integrations/qrce-crosscheck-openmi-patents-20261123.md).

## New: open-source medical project integration registry

The [public evidence atlas](https://atphobia22.github.io/TMRDS/) now includes a
**122-resource, category-filterable medical software and research catalog** with official
repository/documentation links and explicit integration/licensing states.
It covers EHRs (OpenEMR, OpenMRS, Bahmni, GNU Health), imaging (Orthanc,
OHIF, Cornerstone3D, Weasis, 3D Slicer), interoperability (HAPI FHIR,
Medplum, Open Integration Engine), imaging AI (MONAI, TotalSegmentator),
labs, genomics, mobile/offline platforms, PubMed and AlphaFold.

The **separately deployable public research API** adds read-only,
bounded `/api/v1/research/pubmed-citations`,
`/api/v1/research/alphafold-db/{accession}` and
`/api/v1/research/alphafold3-status` endpoints. The same gateway also provides `/cross-check`, `/pmc-identifiers`, `/periodic-element` and `/file-format-capabilities` under the research prefix. The AlphaFold DB
endpoint returns **real source-reported prediction metadata**,
not AlphaFold 3 predictions. AlphaFold 3 source is Apache-2.0,
but the weights/output have restrictive noncommercial terms;
**AlphaFold 3 inference is not deployed or bundled**. The GitHub Pages
copy remains static and cannot execute Python. Institutional EHR/PACS
connectors are not connected to patient records.

[Architecture, official upstream references, commands, license gates and tests](docs/integrations/open-source-medical-gateway.md).

## For doctors

TMRDS is a research workspace for answering "what does the evidence say?" — with every answer traceable to its source.

- **Research federation with 25 cataloged public metadata adapters, plus a separate AlphaFold DB structure lookup.** The repository's full research federation supports discovery across the biomedical literature (PubMed, Europe PMC, OpenAlex, Semantic Scholar, Crossref, arXiv, bioRxiv/medRxiv), trials and drug labels (ClinicalTrials.gov, openFDA, DailyMed), chemistry (PubChem, ChEMBL, RxNorm), genomics and variants (Ensembl — including variant-consequence predictions — ClinVar with review stars, UniProtKB, gnomAD population frequencies, GTEx tissue eQTLs, GWAS Catalog v2 genetic associations), and knowledge graphs and pathways (Open Targets, STRING, Reactome, Monarch, NCATS, MeSH). Each result keeps its source, its date, and its limits. Per-source failures are disclosed rather than silently converted to negative findings. **Only eight reviewed-policy metadata adapters are queried by the isolated public API; the static Pages site queries two services.** The other adapters are not automatically represented as public/live integrations.
- **Original-source GWAS Catalog v2 associations.** `GET /api/v1/research/gwas-associations?trait=asthma&limit=2` exposes a bounded, read-only genetic association facet with GWAS IDs, PMIDs, source provenance, per-source error status, and no causal or clinical interpretation. This is a backend endpoint, not part of the static public Pages site.
- **A research dossier with citations.** `GET /api/v1/research/dossier` turns a search into a structured export: exact DOI/PMID matches, each record's provenance, retraction flags, and what is still unreviewed. Discovery material, not proof of a treatment or cure.
- **A synthetic lab-trends workbench.** A FHIR R4 research workbench for reviewing laboratory trends (values, units, dates, statuses, reference ranges) and imaging metadata — **synthetic test data only**. No real patient records, no real images, no diagnosis, no reference-range interpretation. It exists so workflows can be tested safely before any real data is ever involved.
- **Imaging research, kept separate from interpretation.** A local Orthanc/OHIF recipe lets researchers view test DICOM studies, and offline MONAI tools can evaluate segmentation masks. AI output is always labeled as AI output — never mixed with the original image or a radiologist's reading. Nothing here is validated for patient-care use.
- **Uncertainty is shown, not hidden.** Preliminary vs. final results, missing data, conflicting sources, and low-confidence predictions are flagged for clinician review. The system never auto-diagnoses.

## For hospitals and health systems

TMRDS is built to be evaluated as a research platform first, with clear boundaries for anything clinical.

- **No live EHR connection out of the box.** The repository enables no institutional exchange (EHR, HIE, or otherwise) by itself. A production connection would require target-system registration, authorization, BAA/DUA/IRB and privacy review, TLS/certificate management, and exact FHIR/US Core conformance testing — none of which this repository performs for you.
- **Interoperability boundaries, not promises.** FHIR R4 with US Core 9.0.0 as the documented profile target, SMART discovery metadata, PKCE S256, structural resource validation, and Provenance/AuditEvent builders. Full profile and terminology conformance requires a real validator pinned to the exact target release.
- **OMOP CDM v5.4** as the research normalization boundary for longitudinal records.
- **Data stays where you put it.** PostgreSQL is the authoritative evidence store (with pgvector as a derived retrieval projection, never a source of truth); Neo4j is a governed graph projection. The API binds to loopback by default and database ports are not published.
- **Credentials are never in the repository.** Deployment secrets come from a secret manager or environment variables. If a credential was ever exposed, revoke/rotate it at the issuing provider — removing it from source control does not revoke it.
- **What a deployment needs:** PostgreSQL/pgvector, Neo4j, the environment variables listed under [Required production configuration](#required-production-configuration), and an operator-reviewed migration run. Production requires `TMRDS_ALLOW_PRODUCTION_MIGRATIONS=true` as an explicit opt-in.

## What TMRDS is not

- Not FDA-cleared Software as a Medical Device (SaMD), and not a diagnostic, prescribing, or treatment system.
- Not clinically validated and not HIPAA-compliant as deployed — compliance is a property of a governed deployment, not of this code.
- Not connected to any live patient data, hospital system, or registry. The workbench and imaging sandbox use synthetic data only.
- Not a guarantee of exhaustive coverage: federated search covers the sources listed below, each with its own limits, and a source that fails reports a warning rather than pretending to be complete.
- Not quantum hardware: classical simulations are never described as quantum execution, and the IBM Quantum adapter is opt-in, disabled by default, and submits nothing unless explicitly enabled.

## Evidence sources

**25 federated public metadata sources**, each queried in isolation so one failure never blocks the rest; an additional AlphaFold DB structure endpoint is separate. Two more are credential-gated and reported as unavailable, never mocked: Lens Patents and IBM Quantum.

| Group | Sources |
|---|---|
| Literature | PubMed, Europe PMC, OpenAlex, Semantic Scholar, Crossref, arXiv, bioRxiv/medRxiv |
| Trials, labels, safety | ClinicalTrials.gov, openFDA, DailyMed |
| Chemistry and drugs | PubChem, ChEMBL, RxNorm |
| Genomics and variants | Ensembl, ClinVar (review status shown with every classification), UniProtKB, gnomAD, GTEx, GWAS Catalog v2 (trait-associated variants; not causality) |
| Knowledge and pathways | Open Targets Platform, STRING, Reactome, Monarch, NCATS Node Normalization, MeSH |

Per-source limits are stated in the code (`engines/federated_evidence_search.py`) — for example, Semantic Scholar runs on the shared request pool without a free API key, and Ensembl VEP predictions are computational, not clinical assertions.

## How it works

**Evidence → Provenance → Interoperability → Graph → AI governance.**

Public sources are queried by isolated adapters, normalized into a common evidence shape, and stored with provenance in PostgreSQL. Derived views (vectors, graphs) are projections that always trace back to source records. AI governance records model, prompt, and dataset provenance for every generated output and keeps research outputs from becoming clinical authority. The core API starts without heavy scientific dependencies; optional research engines (MONAI, quantum) are isolated from the core import path.

## What's new

**November 23, 2026 — [PR #72](https://github.com/ATphobia22/TMRDS/pull/72), merged to main.** Replaced the original static cube art with a working, accessible 3D Rubik's Cube (26 visible cubies, quarter-turn moves, continuous/search animation, manual control and reduced-motion support). Introduced **`api/public_gateway.py`** and **`Dockerfile.public`**: a separate, nonclinical read-only API that serves the same site and permits only eight policy-registered, bounded metadata adapters from the larger federation. Added a source-governance registry, explicit retrieval freshness vs. upstream version states, a 90-day license-review checkpoint, scheduled official-source receipts and exact-ID Open Targets disease → target → compound links. A single FDA-anchored cystic fibrosis (`MONDO_0009061`) → CFTR (`ENSG00000001626`) → ivacaftor (`CHEMBL2010601`) reference case passed the live technical check, but **independent clinical validation remains outstanding**. All seven PR workflows and the corresponding merged-`main` workflows completed successfully; the public Pages deployment was also browser-tested. The Python service is **deployable but not yet publicly hosted**.

**November 23, 2026 — GWAS Catalog v2.** Added an original-source GWAS Catalog REST API v2 genetic-association metadata adapter to the federated search. The adapter uses one bounded source page, preserves association IDs, study accession, ontology traits and p-values, and explicitly refuses causal or clinical interpretation. Source rights and study population applicability need independent review. The public GitHub Pages site remains a separate, limited two-source browser experience; it does not execute the Python backend.

**November 2026** — gnomAD and GTEx adapters wired into federated search (population frequencies, tissue eQTLs; 25 live sources); Ensembl VEP variant-consequence annotation (HGVS and region queries, same Ensembl source); HAPI FHIR public test-server probe with a documented synthetic-only opt-in, guards intact; degraded-open API-key posture restored per the standing directive; synthetic FHIR R4 research workbench (lab trends, imaging metadata, terminology; synthetic data only); local Orthanc/OHIF imaging research sandbox; research evidence dossiers with retraction flags; a 30-surface research-plugin capability registry with a read-only RCSB PDB metadata route; source telemetry; opt-in IBM Quantum adapter with a bounded reconciliation worker and job ledger.

**October 2026** — 15 new evidence pipelines (Tier 1: Semantic Scholar, Crossref, PubChem, ChEMBL, DailyMed, RxNorm; Tier 2: Open Targets, STRING, Reactome, ClinVar, Ensembl, bioRxiv/medRxiv, NCATS, Monarch, MeSH), each verified live against its official service before coding. Operations hardening: Prometheus metrics, rate limiting, sanitized errors, optional API-key gate, and a deploy stack (Caddy + TLS, Prometheus/Alertmanager/Grafana, Keycloak). Research-only intended use (`docs/INTENDED_USE.md`, mapping the four Cures Act §520(o)(1)(E) criteria). Verified open-source medical software catalog (`docs/reference/open-source-medical-software.md`).

## Run it yourself

### Public research-only gateway (no patient ingestion or database)

The isolated public service serves the animated website and same-origin governed lookup endpoints. It binds to **127.0.0.1:18080** by default. This is a local deployment, not a public production cloud endpoint:

```bash
docker compose -f compose.public.yml config
docker compose -f compose.public.yml up --build -d

# API and same-origin configuration
curl -fsS http://127.0.0.1:18080/health/ready
curl -fsS http://127.0.0.1:18080/backend-config.json
curl -fsS http://127.0.0.1:18080/api/v1/research/source-governance

# Exact identifier test case; evidence discovery only
curl -fsS 'http://127.0.0.1:18080/api/v1/research/evidence-pathway?disease=MONDO_0009061&limit=8'
```

Open **http://127.0.0.1:18080/** for the same interactive Rubik's Cube site with research API lookup enabled. Internet publication requires an operator-controlled HTTPS reverse proxy, rate and concurrency controls, source-license review, and production monitoring. Do **not** expose the separate all-purpose medical API just to serve this public research website.

The public gateway has no clinical write or patient-ingestion routes. Its `/health/ready` checks the service process, **not** whether external evidence providers are live. Source failures return `source_unavailable` rather than invented evidence. The Pages copy of `backend-config.json` explicitly disables the Python backend.

### Full development and integration stack

Core development/CI targets **Python 3.11**. From the repository root:

```bash
python scripts/check_dependency_lock.py
python -m compileall -q api engines scripts tests
python -m pytest -q -m "not integration"
```

For a local development stack:

```bash
cp .env.example .env
# Replace every placeholder with unique local-only values. Do not use these values in production.
docker compose --env-file .env config --quiet
docker compose --env-file .env build
docker compose --env-file .env run --rm tmrds-api python -m engines.migration_runner status
docker compose --env-file .env run --rm tmrds-api python -m engines.migration_runner upgrade
docker compose --env-file .env up -d
```

The migration runner is explicit and never runs at API startup. For an existing database without a migration ledger, inspect the schema and backup/restore path first; use the documented operator-reviewed `baseline --through N` command only if the existing schema truly matches every migration through that version. Never drop or recreate a persistent volume to force migration initialization.

Run the new research governance and frontend checks with:

```bash
python -m pytest -q tests/test_governed_pathway.py tests/test_public_gateway.py
python scripts/check_public_site.py
node --check public/site.js
docker build --pull -f Dockerfile.public -t tmrds-public:test .
```

The `source-governance.yml` GitHub Actions workflow also runs a **weekly** bounded audit of five upstream services and uploads a dated, hashed receipt (30-day artifact retention). It reports actual response state and source version observations; it does not certify independent source currency or data-use rights.

Live-source and database tests are marked `integration` and require their external services. CI does not require live PHI, institutional EHR access, or IBM Quantum hardware. A read-only [Postman smoke collection](postman/TMRDS-API-smoke.postman_collection.json) covers liveness, readiness, and research-advisory metadata.

### Required production configuration

Supply these through a deployment secret manager. Do not commit values:

```text
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
NEO4J_URI
NEO4J_USER
NEO4J_PASSWORD
TMRDS_DATABASE_URL
TMRDS_HMAC_SECRET
TMRDS_CLINICIAN_PASSWORD
TMRDS_EMERGENCY_PIN
TMRDS_BASE_URL
TMRDS_US_CORE_VERSION
TMRDS_SERVICE_ISSUER
TMRDS_SERVICE_AUDIENCE
TMRDS_SERVICE_JWKS_JSON
```

`TMRDS_HMAC_SECRET` must be at least 32 characters. Production Compose requires database, Neo4j, interoperability, and service-auth configuration to be present. `TMRDS_SERVICE_AUTH_REQUIRED=true` is the production default; ingestion and synchronization endpoints then require a valid asymmetric service token with the configured scope. The optional API-key gate (`TMRDS_API_KEYS_FILE`) degrades to loud open if a configured key file cannot be loaded (CRITICAL log + `"auth": "degraded-open"` in the ops posture) — the API keeps serving and never denies traffic over a bad key file — while intentionally public routes stay open when no key file is set. Ops posture is visible at `GET /api/v1/ops/posture`.

## Safety and provenance

1. **No fabricated medical evidence.**
2. **No unsupported clinical claims.**
3. **No autonomous diagnosis or prescribing authority.**
4. **Source provenance must remain inspectable.**
5. **Derived vectors/graphs must not silently replace authoritative evidence.**
6. **Research predictions must be distinguishable from observed/source-backed evidence.**
7. **Human clinical authority remains outside the software's authority boundary.**

AI governance records model identity and version, prompt/policy provenance, dataset and evaluation metadata, and evidence envelopes for every output, with uncertainty and human-review requirements explicit. The route audit (`python scripts/audit_api_routes.py`) inventories FastAPI routes and flags write routes without a recognized declared authentication dependency; it is a heuristic, not proof of authorization correctness.

## Optional IBM Quantum integration

An opt-in adapter for the **IBM Quantum Compute Service REST API**, for research workloads only — not required to run the core API, PostgreSQL store, or Neo4j projection. A regular IBM Quantum account does not by itself guarantee access to a Quantum Compute instance, backend, or job submission; configure an eligible instance CRN and IAM permissions first. Supply `IBM_QUANTUM_API_KEY` and `IBM_QUANTUM_INSTANCE_CRN` through a secret manager or untracked local environment; never commit real credentials. Remote job submission stays disabled unless explicitly enabled with `TMRDS_IBM_QUANTUM_SUBMISSION_ENABLED=true`. The database-backed local limiter defaults to four submissions per rolling minute (ceiling one through five). Uncertain submissions are recorded as `SUBMISSION_UNKNOWN` and are never automatically resubmitted. The optional one-pass reconciliation worker only polls jobs with known IBM job IDs and never creates or cancels remote jobs. See [IBM Quantum integration](docs/integrations/ibm-quantum-compute.md) and the [operations runbook](docs/operations/tmrds-operations-runbook.md). Repository CI submits no jobs to live IBM hardware and incurs no quantum execution charges.

## Repository layout

```text
TMRDS/
├── api/                 # Full medical API + isolated read-only public_gateway.py
├── engines/             # Research, evidence, interoperability, and security engines
├── docs/                # Architecture, security, interoperability, and operations docs
├── migrations/          # Ordered PostgreSQL schema changes and audit tables
├── scripts/             # Security scans, route audit, and bounded operator commands
├── postman/             # Read-only API smoke-test collection
├── tests/               # Unit, API-contract, and integration tests
├── frontend/            # Existing frontend/application surface
├── public/              # Live GitHub Pages atlas, 3D cube JS/CSS, disabled Pages API config
├── workers/             # Continuous real-world data synchronization workers
├── .github/workflows/   # CI and security scanning
├── docker-compose.yml   # PostgreSQL/pgvector + Neo4j + API stack
├── compose.public.yml   # Isolated loopback-bound public research-only service
├── Dockerfile.public     # Unprivileged same-origin website + read-only research API
├── deploy.sh            # Deployment helper
├── requirements.txt     # Python runtime/test dependencies
└── pytest.ini           # Pytest configuration
```

## Further reading

- [Intended use](docs/INTENDED_USE.md) — research-only scope and the Cures Act criteria.
- [SaMD classification checklist](docs/SAMD_CLASSIFICATION_CHECKLIST.md) — per-feature classification.
- [Interoperability compliance matrix](docs/INTEROPERABILITY_COMPLIANCE_MATRIX.md) — FHIR/US Core controls and limitations.
- [Imaging research sandbox](docs/operations/imaging-research-sandbox.md) — local Orthanc/OHIF recipe and synthetic MR-to-FHIR tooling.
- [Imaging research workflow](docs/integrations/imaging-research-workflow.md) — bounded DICOMweb reads, OHIF provenance panel, reviewed MONAI weight loading, human label submission; research only, no clinical approval.
- [Research dossier](docs/operations/research-dossier.md) — dossier contract and remaining gates.
- [GWAS Catalog v2 integration](docs/integrations/gwas-catalog-v2.md) — bounded real-source genetic association metadata, rate limits, identity preservation, and clinical limitations.
- [Open-source medical gateway and 41-project catalog](docs/integrations/open-source-medical-gateway.md) — PubMed and AlphaFold DB metadata, integration status, source rights, and clinical-system isolation.
- [Governed evidence pathway and Rubik's Cube deployment](docs/integrations/governed-evidence-pathway.md) — same-origin Docker service, source-license/freshness checks, exact identifier joins, release audit, and independent-validation limits.
- [Source-governance workflow](.github/workflows/source-governance.yml) — CI tests, public container smoke tests, and weekly upstream audits.
- [Biomedical source gap review](docs/reference/biomedical-source-gap-review-2026-11-07.md) — status baseline for GWAS v2, DepMap/PRISM, LINCS, CELLxGENE, ClinPGx priorities.
- [Verified open-source medical software catalog](docs/reference/open-source-medical-software.md) — 32 projects checked against primary sources.
- [CI and release gates](docs/operations/ci-release-gates.md) — workflows, pinning, and release evidence.
- [Operations runbook](docs/operations/tmrds-operations-runbook.md)

## Disclaimer

TMRDS is research software for biomedical evidence exploration and engineering development. It is not medical advice, a diagnosis, a prescription, or a substitute for qualified clinical judgment. No repository documentation should be interpreted as evidence that TMRDS is FDA-cleared, clinically validated, HIPAA-compliant, ONC-certified, TEFCA-connected, or authorized for a particular regulated use.

**Owner action still required:** branch protection is currently disabled on `main`. Configure required checks and pull-request protections in GitHub repository settings after the new workflow check names have appeared. Workflow YAML alone cannot enforce branch protection.
