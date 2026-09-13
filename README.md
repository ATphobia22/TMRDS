# TMRDS — Transparent Medical Research Decision Support

**Research-advisory biomedical evidence gateway with governed provenance, interoperability, and AI governance.**

> **Status:** Research software. TMRDS is not FDA-cleared Software as a Medical Device (SaMD), does not replace clinical judgment, and is not a diagnostic or prescribing system.

## Security baseline

TMRDS does not commit production passwords, API keys, tokens, private keys, or local runtime data. Deployment credentials are supplied through an external secret manager or environment variables. Production password/PIN authentication has no built-in fallback, and local password material is protected with memory-hard scrypt. Machine-to-machine trust uses asymmetric JWT validation against explicit issuer/audience/JWKS configuration when enabled. The repository also runs deterministic automated secret scanning in `.github/workflows/security.yml`.

**If a credential was ever exposed outside the repository, revoke/rotate it at the issuing provider. Removing a secret from source control does not revoke a previously issued credential.**

## What TMRDS is

TMRDS is a Python/FastAPI research platform for connecting public biomedical evidence to a governed evidence model. The current implementation combines:

- **Public biomedical source adapters** for CDC, OpenNeuro, ClinicalTrials.gov, openFDA, NLM Clinical Tables, Europe PMC, and PubMed.
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

The Compose stack provisions PostgreSQL/pgvector, Neo4j, and the API. The API source mount is read-only while runtime/audit data is stored in a dedicated volume. Supply credentials and service identity material through CI/CD or an external secret manager before startup.

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

## Data and evidence model

TMRDS treats the evidence ledger as authoritative. Derived representations must not silently become sources of truth.

### PostgreSQL

The PostgreSQL layer stores governed evidence, provenance records, and real-time data-fabric observations. Migrations live in `migrations/` and are mounted by the development Docker Compose stack.

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

## Testing and CI

Core development/CI targets **Python 3.11**.

```bash
python -m pytest -q -m "not integration"
python scripts/security_scan.py .
python -m compileall -q api engines scripts tests
```

Live-source and PostgreSQL/Neo4j tests are explicitly marked `integration` and require their external services/configuration. The CI security workflow intentionally runs deterministic unit/security checks without requiring live PHI or institutional systems.

## Repository layout

```text
TMRDS/
├── api/                 # FastAPI application and route modules
├── engines/             # Research, evidence, interoperability, and security engines
├── migrations/          # PostgreSQL / evidence schema migrations
├── docs/                # Architecture, security, interoperability, and operations docs
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
