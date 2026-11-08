# TMRDS — Transparent Medical Research Decision Support

> **Research software — not a medical device.** TMRDS helps doctors and researchers find and cross-check public biomedical evidence faster. It does not diagnose, prescribe, treat, or replace clinical judgment. It is not FDA-cleared, clinically validated, HIPAA-compliant, ONC-certified, or connected to any live hospital system.

## Try it now

**[TMRDS 2 — public research workspace](https://muse.ai/s/tmrds-2-xxd6j1fn9xyxwxf/DtP0Ir8DQV7MepeJdlvuTQBszwBcsygUi_QoYBYFruw)** — a static, public preview of the workspace: federated evidence search, the Quantum Research Navigation Cube, the Care Evidence Brief, and the development roadmap. Research-advisory only; human clinical authority final. (Public preview reflects the October 2026 build; the repository below is current.)

## For doctors

TMRDS is a research workspace for answering "what does the evidence say?" — with every answer traceable to its source.

- **One search across 25 public sources.** Ask about a drug, gene, variant, trial, or condition and get results from the biomedical literature (PubMed, Europe PMC, OpenAlex, Semantic Scholar, Crossref, arXiv, bioRxiv/medRxiv), trials and drug labels (ClinicalTrials.gov, openFDA, DailyMed), chemistry (PubChem, ChEMBL, RxNorm), genomics and variants (Ensembl — including variant-consequence predictions — ClinVar with review stars, UniProtKB, AlphaFold DB, gnomAD population frequencies, GTEx tissue eQTLs), and knowledge graphs and pathways (Open Targets, STRING, Reactome, Monarch, NCATS, MeSH). Each result keeps its source, its date, and its limits. If a source is down or throttled, you see a warning for that source — never a silent gap.
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

**25 live public sources**, each queried in isolation so one failure never blocks the rest. Two more are credential-gated and reported as unavailable, never mocked: Lens Patents and IBM Quantum.

| Group | Sources |
|---|---|
| Literature | PubMed, Europe PMC, OpenAlex, Semantic Scholar, Crossref, arXiv, bioRxiv/medRxiv |
| Trials, labels, safety | ClinicalTrials.gov, openFDA, DailyMed |
| Chemistry and drugs | PubChem, ChEMBL, RxNorm |
| Genomics and variants | Ensembl, ClinVar (review status shown with every classification), UniProtKB, AlphaFold DB, gnomAD, GTEx |
| Knowledge and pathways | Open Targets Platform, STRING, Reactome, Monarch, NCATS Node Normalization, MeSH |

Per-source limits are stated in the code (`engines/federated_evidence_search.py`) — for example, Semantic Scholar runs on the shared request pool without a free API key, and Ensembl VEP predictions are computational, not clinical assertions.

## How it works

**Evidence → Provenance → Interoperability → Graph → AI governance.**

Public sources are queried by isolated adapters, normalized into a common evidence shape, and stored with provenance in PostgreSQL. Derived views (vectors, graphs) are projections that always trace back to source records. AI governance records model, prompt, and dataset provenance for every generated output and keeps research outputs from becoming clinical authority. The core API starts without heavy scientific dependencies; optional research engines (MONAI, quantum) are isolated from the core import path.

## What's new

**November 2026** — gnomAD and GTEx adapters wired into federated search (population frequencies, tissue eQTLs; 25 live sources); degraded-open API-key posture restored per the standing directive; synthetic FHIR R4 research workbench (lab trends, imaging metadata, terminology; synthetic data only); local Orthanc/OHIF imaging research sandbox; research evidence dossiers with retraction flags; a 30-surface research-plugin capability registry with a read-only RCSB PDB metadata route; source telemetry; opt-in IBM Quantum adapter with a bounded reconciliation worker and job ledger.

**October 2026** — 15 new evidence pipelines (Tier 1: Semantic Scholar, Crossref, PubChem, ChEMBL, DailyMed, RxNorm; Tier 2: Open Targets, STRING, Reactome, ClinVar, Ensembl, bioRxiv/medRxiv, NCATS, Monarch, MeSH), each verified live against its official service before coding. Operations hardening: Prometheus metrics, rate limiting, sanitized errors, optional API-key gate, and a deploy stack (Caddy + TLS, Prometheus/Alertmanager/Grafana, Keycloak). Research-only intended use (`docs/INTENDED_USE.md`, mapping the four Cures Act §520(o)(1)(E) criteria). Verified open-source medical software catalog (`docs/reference/open-source-medical-software.md`).

## Run it yourself

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
├── api/                 # FastAPI application and route modules
├── engines/             # Research, evidence, interoperability, and security engines
├── docs/                # Architecture, security, interoperability, and operations docs
├── migrations/          # Ordered PostgreSQL schema changes and audit tables
├── scripts/             # Security scans, route audit, and bounded operator commands
├── postman/             # Read-only API smoke-test collection
├── tests/               # Unit, API-contract, and integration tests
├── frontend/            # Frontend assets/application surface
├── workers/             # Continuous real-world data synchronization workers
├── .github/workflows/   # CI and security scanning
├── docker-compose.yml   # PostgreSQL/pgvector + Neo4j + API stack
├── deploy.sh            # Deployment helper
├── requirements.txt     # Python runtime/test dependencies
└── pytest.ini           # Pytest configuration
```

## Further reading

- [Intended use](docs/INTENDED_USE.md) — research-only scope and the Cures Act criteria.
- [SaMD classification checklist](docs/SAMD_CLASSIFICATION_CHECKLIST.md) — per-feature classification.
- [Interoperability compliance matrix](docs/INTEROPERABILITY_COMPLIANCE_MATRIX.md) — FHIR/US Core controls and limitations.
- [Imaging research sandbox](docs/operations/imaging-research-sandbox.md) — local Orthanc/OHIF recipe and synthetic MR-to-FHIR tooling.
- [Research dossier](docs/operations/research-dossier.md) — dossier contract and remaining gates.
- [Biomedical source gap review](docs/reference/biomedical-source-gap-review-2026-11-07.md) — GWAS v2, DepMap/PRISM, LINCS, CELLxGENE, ClinPGx priorities.
- [Verified open-source medical software catalog](docs/reference/open-source-medical-software.md) — 32 projects checked against primary sources.
- [CI and release gates](docs/operations/ci-release-gates.md) — workflows, pinning, and release evidence.
- [Operations runbook](docs/operations/tmrds-operations-runbook.md)

## Disclaimer

TMRDS is research software for biomedical evidence exploration and engineering development. It is not medical advice, a diagnosis, a prescription, or a substitute for qualified clinical judgment. No repository documentation should be interpreted as evidence that TMRDS is FDA-cleared, clinically validated, HIPAA-compliant, ONC-certified, TEFCA-connected, or authorized for a particular regulated use.

**Owner action still required:** branch protection is currently disabled on `main`. Configure required checks and pull-request protections in GitHub repository settings after the new workflow check names have appeared. Workflow YAML alone cannot enforce branch protection.
