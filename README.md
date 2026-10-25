# TMRDS — Transparent Medical Research Decision Support

**Research-advisory biomedical evidence gateway with governed provenance, interoperability, and AI governance.**

> **Status:** Research software. TMRDS is not FDA-cleared Software as a Medical Device (SaMD), does not replace clinical judgment, and is not a diagnostic or prescribing system.

## Explore TMRDS

**[TMRDS 2 — public research workspace](https://muse.ai/s/tmrds-2-xxd6j1fn9xyxwxf/DtP0Ir8DQV7MepeJdlvuTQBszwBcsygUi_QoYBYFruw)** — the public, static companion to this repository: federated evidence search across 22 live sources, the Quantum Research Navigation Cube, the Care Evidence Brief, and the development roadmap. Research-advisory only; human clinical authority final.

## Security baseline

TMRDS does not commit production passwords, API keys, tokens, private keys, or local runtime data. Deployment credentials are supplied through an external secret manager or environment variables. Production password/PIN authentication has no built-in fallback, and local password material is protected with memory-hard scrypt. Machine-to-machine trust uses asymmetric JWT validation against explicit issuer/audience/JWKS configuration when enabled. The repository also runs deterministic automated secret scanning in `.github/workflows/security.yml`.

**If a credential was ever exposed outside the repository, revoke/rotate it at the issuing provider. Removing a secret from source control does not revoke a previously issued credential.**

## What TMRDS is

TMRDS is a Python/FastAPI research platform for connecting public biomedical evidence to a governed evidence model. The current implementation combines:

- **Federated evidence search across 22 live public sources** — literature (Europe PMC, PubMed, OpenAlex, Semantic Scholar, Crossref, arXiv, bioRxiv/medRxiv), trials and labels (ClinicalTrials.gov, openFDA, DailyMed), chemistry and drugs (PubChem, ChEMBL, RxNorm terminology), genomics and variants (Ensembl, ClinVar with review stars, AlphaFold DB), knowledge graphs and pathways (Open Targets Platform, STRING, Reactome, Monarch, NCATS Node Normalization, MeSH). Every source runs isolated with per-source failure warnings and honest coverage statements; Lens Patents and IBM Quantum are credential-gated and reported as unavailable, never mocked.
- **Real-world real-time data fabric** for bounded, provenance-first synchronization of authoritative public feeds, including USGS, NOAA/NWS, FEMA, and CDC sources.
- **Evidence governance** with registered sources, provenance-bearing entities/assertions, conflict handling, ingestion state, and audit-oriented evidence records.
- **FHIR R4 / US Core interoperability boundary** with SMART discovery, PKCE S256 primitives, structural resource validation, Provenance/AuditEvent builders, and configurable service-to-service identity.
- **OMOP CDM v5.4** for the research normalization boundary.
- **PostgreSQL** as the authoritative evidence store, with **pgvector** support for derived semantic retrieval.
- **Neo4j** as a governed graph projection for relationship-oriented research and graph analytics.
- **AI governance** that records model/prompt/dataset provenance and evidence envelopes and keeps generated outputs research-advisory.
- **Optional research engines** that are isolated from the core import path so heavy scientific dependencies do not prevent the API and evidence stack from starting.

The design principle is:

**Evidence → Provenance → Interoperability → Graph → AI Governance**

## What's new (October 2026)

- **15 new evidence pipelines** (Tier 1 + Tier 2), each verified live against its official service before coding: Semantic Scholar, Crossref, PubChem, ChEMBL, DailyMed, RxNorm, Open Targets Platform, STRING, Reactome, ClinVar, Ensembl, bioRxiv/medRxiv, NCATS, Monarch, MeSH. See `engines/federated_evidence_search.py`.
- **Operations hardening** — Prometheus RED metrics at `/metrics`, slowapi rate limiting (120/min default, 20/min on federated search), sanitized 429s with `Retry-After`, baseline security headers, and an optional API-key gate (`TMRDS_API_KEYS_FILE`) that denies API traffic if a configured key file cannot be loaded (503), while keeping intentionally public routes open when no key file is set. Ops posture is visible at `GET /api/v1/ops/posture`.
- **Deploy stack** — `docker-compose.obs.yml` overlay: Caddy with automatic TLS, Prometheus + Alertmanager + Grafana, and Keycloak as the OIDC identity provider for the existing service-JWT validator. Secrets via Compose file secrets (`*_FILE`), never environment values.
- **Research-only intended use** — `docs/INTENDED_USE.md` v1.0.0 maps the four Cures Act §520(o)(1)(E) criteria, plus a per-feature SaMD classification checklist (`docs/SAMD_CLASSIFICATION_CHECKLIST.md`).
- **Verified open-source medical software catalog** — 32 projects checked against primary sources (`docs/reference/open-source-medical-software.md`).

## Current architecture

```text
                         ┌─────────────────────────┐
                         │     FastAPI Gateway      │
                         │       api/main.py       │
                         └────────────┬────────────┘
                                      │
              ┌───────────────────────┼────────────────────────┐
              │                       │                        │
              ▼                       ▼                        ▼
     Public Source Adapters   Evidence Governance       AI Governance
     CDC / NLM / PubMed       entities / assertions     model + prompt +
     Europe PMC / FDA         provenance / conflicts    dataset + evidence
     ClinicalTrials.gov       ingestion state           envelopes
     OpenNeuro                │
              │               │
              └───────────────┼────────────────────────────┐
                              ▼                            │
                    Real-Time Data Fabric                 │
                    USGS / NOAA / FEMA / CDC              │
                              │                            │
                              ▼                            ▼
                         ┌─────────────────────────┐
                         │      PostgreSQL          │
                         │  authoritative evidence  │
                         │  + data-fabric ledger    │
                         │  + pgvector projection   │
                         └────────────┬────────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │        Neo4j             │
                         │ governed graph projection│
                         └─────────────────────────┘

        FHIR R4 / US Core  ←→  clinical interoperability boundary
        SMART / OAuth       ←→  authentication and authorization boundary
        OMOP CDM v5.4      ←→  research normalization boundary
```

## Security and deployment

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

`TMRDS_HMAC_SECRET` must be at least 32 characters. Production Compose fails closed when required database, Neo4j, interoperability, or service-auth configuration is absent. `TMRDS_SERVICE_AUTH_REQUIRED=true` is the production Compose default; ingestion and real-time synchronization endpoints then require a valid asymmetric service token with the configured scope.

### Docker Compose

The hardened Compose stack provisions PostgreSQL/pgvector, Neo4j, and a non-root API image. Database ports are not published by default; the API binds to loopback by default, the database network is internal, and the API's runtime/audit/artifact data lives in a dedicated volume. Optional local database ports are available only through `docker-compose.dev.yml`.

For a local development stack:

```bash
cp .env.example .env
# Replace every placeholder with unique local-only values. Do not use these values in production.
docker compose --env-file .env config --quiet
docker compose --env-file .env build
docker compose --env-file .env run --rm tmrds-api python -m engines.migration_runner status
docker compose --env-file .env run --rm tmrds-api python -m engines.migration_runner upgrade
docker compose --env-file .env up -d
docker compose --env-file .env ps
```

The migration runner is explicit and does not run on API startup. For an existing database without a migration ledger, stop before `upgrade`: inspect the complete schema and backup/restore path, then use the documented operator-reviewed `baseline --through N` command only if the existing schema truly matches every migration through that version. Do not reinitialize or delete an existing database volume to work around migration errors.

Production migrations require a separately reviewed release procedure and an explicit `TMRDS_ALLOW_PRODUCTION_MIGRATIONS=true` opt-in. The local example values are not production secrets or a production identity configuration.

### Repository secret hygiene

`.gitignore` and `.dockerignore` exclude environment files, private-key/certificate material, credential stores, database dumps, and runtime data. Secret scanning runs on pushes, pull requests, scheduled scans, and manual dispatch.

If a real credential has been exposed, **rotate/revoke it first** and then remove the material from the repository/history as appropriate. A source-code cleanup alone does not invalidate an issued credential.

## Interoperability

### FHIR / US Core

- Baseline: **FHIR R4**.
- Current documented US Core release: **9.0.0**, which is R4-based.
- `TMRDS_US_CORE_VERSION` is explicit configuration rather than a hidden hard-coded profile contract.
- Structural validation is implemented in `engines/fhir_interoperability.py`; full profile/terminology conformance requires a real validator/package pinned to the exact target release.
- Provenance and AuditEvent helpers are available for governed exchange metadata.

### SMART / OAuth

- `/.well-known/smart-configuration` exposes non-secret SMART metadata.
- PKCE is S256-only; `plain` is not advertised.
- Service-to-service validation supports asymmetric JWTs with explicit issuer, audience, expiry, `nbf`, `kid`, algorithm, and scope checks.
- Production ingestion/synchronization can fail closed on missing service identity configuration.

### PHI and institutional exchange boundary

No live institutional EHR/INPC/IHIE exchange is enabled by this repository configuration alone. Production exchange still requires target-system registration, appropriate authorization, BAA/DUA/IRB/privacy review where applicable, TLS/certificate management, identity proofing, terminology validation, and exact FHIR/US Core conformance testing.

See `docs/INTEROPERABILITY_COMPLIANCE_MATRIX.md` for the technical-control matrix and regulatory limitations.

## Optional IBM Quantum integration

TMRDS includes an opt-in adapter for the **IBM Quantum Compute Service REST API**. This integration is for research workloads only and is not required to run the core API, PostgreSQL evidence store, or Neo4j projection.

- **Account access:** a regular IBM Quantum account does not by itself guarantee access to a Quantum Compute instance, backend, or job submission. Configure an eligible instance CRN and the appropriate IAM permissions first.
- **Credentials:** supply `IBM_QUANTUM_API_KEY` and `IBM_QUANTUM_INSTANCE_CRN` through a secret manager or an untracked local environment. Optional settings include `IBM_QUANTUM_REGION`, `IBM_QUANTUM_API_VERSION`, and `IBM_QUANTUM_TIMEOUT_SECONDS`. Never commit real credentials.
- **Default safety:** remote job submission remains disabled unless explicitly enabled with `TMRDS_IBM_QUANTUM_SUBMISSION_ENABLED=true`, and the calling code must also provide explicit authorization. Do not enable it merely to test connectivity.
- **Rate limits:** the database-backed local limiter defaults to four submissions per rolling minute and accepts only a configured ceiling from one through five per minute.
- **Ambiguous requests:** an uncertain submission is recorded as `SUBMISSION_UNKNOWN`. TMRDS does not automatically resubmit it or infer a matching remote job from timestamps or backend metadata.
- **Reconciliation:** the optional one-pass worker only polls jobs with known IBM job IDs, is bounded by batch/runtime limits, and can persist completed results to the configured private artifact directory. It does not create or cancel remote jobs. Run only one worker instance at a time.
- **Operator resolution:** resolving an ambiguous submission requires the explicit `TMRDS_QUANTUM_OPERATOR_RESOLUTION_ENABLED=true` opt-in plus a confirmed IBM job ID, operator identifier, and evidence reference. Resolution attempts are recorded in the operator audit ledger.
- **Not performed:** repository CI does not submit jobs to live IBM hardware, create IBM resources, or incur quantum execution charges.

For configuration, state transitions, recovery steps, and limitations, see [IBM Quantum integration](docs/integrations/ibm-quantum-compute.md) and the [operations runbook](docs/operations/tmrds-operations-runbook.md).

A bounded reconciliation pass can be run only after the IBM credentials, instance, database migrations, and operator policy have been configured:

```bash
TMRDS_IBM_QUANTUM_RECONCILER_ENABLED=true python scripts/ibm_quantum_reconcile_once.py --limit 25
```

Keep the reconciliation opt-in disabled until the deployment has been reviewed. Store result artifacts in a private, access-controlled location and include that location in backup/retention controls.

## Data and evidence model

TMRDS treats the evidence ledger as authoritative. Derived representations must not silently become sources of truth.

### PostgreSQL

The PostgreSQL layer stores governed evidence, provenance records, and real-time data-fabric observations. SQL migrations live in `migrations/`; apply them with the explicit checksummed runner (`python -m engines.migration_runner status|upgrade`). The runner records migration versions and SHA-256 checksums, uses a PostgreSQL advisory lock, rejects checksum drift, and never runs automatically at API startup. Existing untracked schemas require an operator-reviewed baseline; never drop or recreate a persistent volume to force migration initialization.

### pgvector

Vector embeddings are a **derived retrieval projection**. They are not authoritative evidence and must remain traceable to the source/evidence records from which they were generated.

### Neo4j

Neo4j is a governed graph projection used for relationship traversal and graph-oriented computation. It is not an independent authority that can override the evidence ledger.

## Real-world real-time data fabric

The data fabric provides bounded, provenance-first synchronization for authoritative public feeds. It records source identity, retrieval/observation timestamps, ETag/Last-Modified metadata when available, SHA-256 payload identity, provenance state, and durable observation records.

Current catalog includes USGS Water Services, USGS Earthquake feeds, NOAA/NWS weather and alerts, FEMA disaster declarations, CDC public data, ClinicalTrials.gov, openFDA, PubMed, Europe PMC, and NLM Clinical Tables. Outbound synchronization is HTTPS-only and passes through an SSRF-resistant host/IP policy with bounded timeouts and redirects disabled.

Continuous synchronization is provided by `workers/realtime_data_fabric_worker.py`. See `docs/REALTIME_DATA_FABRIC.md` for operational details.

## AI governance

The AI governance layer is intentionally restrictive:

1. Model identity/version is recorded.
2. Prompt/policy provenance is recorded where applicable.
3. Dataset/evaluation metadata can be attached to generations.
4. Evidence envelopes identify the evidence available to an output.
5. Uncertainty and human-review requirements are explicit.
6. Research outputs cannot be promoted implicitly into autonomous clinical authority.

TMRDS therefore implements a **research-advisory architecture**, not an autonomous clinical decision-maker.

## Testing, CI, and API audit

Core development/CI targets **Python 3.11**. From the repository root, run:

```bash
python scripts/check_dependency_lock.py
python scripts/check_workflow_security.py
python scripts/security_scan.py .
python -m compileall -q api engines scripts tests
python scripts/audit_api_routes.py --output api-route-inventory.json
python -m pytest -q -m "not integration"
```

The route audit emits a JSON inventory of FastAPI routes, source locations, declared dependencies, and write routes without a recognized declared authentication dependency. Duplicate method/path definitions and write routes without a recognized declared auth dependency fail the static gate. This is still a heuristic, not proof of authorization correctness; review endpoint behavior and runtime policy.

Live-source and PostgreSQL/Neo4j tests are explicitly marked `integration` and require their external services/configuration. CI does not require live PHI, institutional EHR access, or IBM Quantum hardware. A read-only [Postman smoke collection](postman/TMRDS-API-smoke.postman_collection.json) covers liveness, readiness, and research-advisory metadata; import it into Postman and set `baseUrl` to the local API address.

The current remediation work adds checksummed explicit migrations, request-correlation/error handling, hardened container defaults, dependency locks, health probes, route inventory output, and bounded IBM Quantum recovery controls. These controls still require environment-specific operational validation before a production release.

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

## Non-negotiable research constraints

1. **No fabricated medical evidence.**
2. **No unsupported clinical claims.**
3. **No autonomous diagnosis or prescribing authority.**
4. **Source provenance must remain inspectable.**
5. **Derived vectors/graphs must not silently replace authoritative evidence.**
6. **Research predictions must be distinguishable from observed/source-backed evidence.**
7. **Human clinical authority remains outside the software's authority boundary.**

## Disclaimer

TMRDS is research software for biomedical evidence exploration and engineering development. It is not medical advice, a diagnosis, a prescription, or a substitute for qualified clinical judgment. No repository documentation should be interpreted as evidence that TMRDS is FDA-cleared, clinically validated, HIPAA-compliant, ONC-certified, TEFCA-connected, or authorized for a particular regulated use.


## Release gates and dependency security

The repository now defines CI, secret/security/interoperability, supply-chain, CodeQL (Python and GitHub Actions), and release-verification workflows. Third-party workflow actions are pinned to verified full commit SHAs, with version comments for review and Dependabot update proposals. The supply-chain gate validates both `requirements.txt`/`requirements.lock` and `requirements-runtime.txt`/`requirements-runtime.lock`, then audits each exact-pin lock for known Python dependency advisories. Pull requests also receive dependency review. See [CI and release gates](docs/operations/ci-release-gates.md), the [dependency-management procedure](docs/operations/dependency-management.md), and the [release-readiness audit](docs/audits/2026-10-17-tmrds-release-readiness.md) for update steps, limitations, and release evidence requirements. The release workflow builds locally and uploads test/SBOM evidence; it does not publish or deploy.

**Owner action still required:** branch protection is currently disabled on `main`. Configure required checks and pull-request protections in GitHub repository settings after the new workflow check names have appeared. Workflow YAML alone cannot enforce branch protection.


## Scientific adapter readiness

The genetics and molecular-computation boundary is explicitly fail-closed: Ensembl gene/transcript data must originate from a live source response; missing Qiskit Nature/PySCF dependencies no longer return hard-coded Hamiltonian coefficients; and optional quantum-research scaffolding does not claim simulations, scores, or hardware jobs that did not run. See [Research Compute and Genetics Readiness](docs/operations/research-compute-readiness.md). HGVS-based VEP lookup is supported; SPDI-to-HGVS normalization and an actual VQE/classical-baseline solver remain staged work.
