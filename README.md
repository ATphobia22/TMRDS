# TMRDS — Transparent Medical Research Decision Support

**Research-advisory biomedical evidence gateway with governed provenance, interoperability, and AI governance.**

> **Status:** Research software. TMRDS is not FDA-cleared Software as a Medical Device (SaMD), does not replace clinical judgment, and is not a diagnostic or prescribing system.

## Security baseline

TMRDS does not commit production passwords, API keys, tokens, private keys, or local runtime data. Deployment credentials are supplied through an external secret manager or environment variables. Production authentication requires `TMRDS_CLINICIAN_PASSWORD`, `TMRDS_EMERGENCY_PIN`, and `TMRDS_HMAC_SECRET`; there are no built-in credential fallbacks. Passwords are salted and protected with PBKDF2-HMAC-SHA256. The repository also runs automated secret scanning in `.github/workflows/security.yml`.

**If a credential was ever exposed outside the repository, revoke/rotate it at the issuing provider. Removing a secret from source control does not revoke a previously issued credential.**

## What TMRDS is

TMRDS is a Python/FastAPI research platform for connecting public biomedical evidence to a governed evidence model. The current implementation combines:

- **Public biomedical source adapters** for CDC, OpenNeuro, ClinicalTrials.gov, openFDA, NLM Clinical Tables, Europe PMC, and PubMed.
- **Real-world real-time data fabric** for bounded, provenance-first synchronization of authoritative public feeds, including USGS, NOAA/NWS, FEMA, and CDC sources.
- **Evidence governance** with registered sources, provenance-bearing entities/assertions, conflict handling, ingestion state, and audit-oriented evidence records.
- **FHIR / OMOP interoperability** for separating clinical interoperability concerns from research normalization.
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
        OMOP CDM v5.4      ←→  research normalization boundary
```

## Security and deployment

### Required production secrets

Set these through a deployment secret manager; do not commit them to the repository:

```text
POSTGRES_PASSWORD
NEO4J_PASSWORD
TMRDS_HMAC_SECRET
TMRDS_CLINICIAN_PASSWORD
TMRDS_EMERGENCY_PIN
```

`TMRDS_HMAC_SECRET` must be at least 32 characters. The production Docker Compose profile fails closed when required secrets are absent.

### Docker Compose

The Compose stack provisions PostgreSQL/pgvector, Neo4j, and the API. Supply secrets through the shell environment, CI/CD secret store, or an external secret manager before startup. Never use example/default passwords in production.

### Repository secret hygiene

`.gitignore` excludes `.env` files, private-key/certificate material, credentials directories, and runtime data. Secret scanning runs on pushes, pull requests, scheduled scans, and manual dispatch.

If a real credential has been exposed, **rotate/revoke it first** and then remove the material from the repository/history as appropriate. A source-code cleanup alone does not invalidate an issued credential.

## Data and evidence model

TMRDS treats the evidence ledger as authoritative. Derived representations must not silently become sources of truth.

### PostgreSQL

The PostgreSQL layer stores governed evidence, provenance records, and real-time data-fabric observations. Migrations live in `migrations/` and are mounted by the development Docker Compose stack.

### pgvector

Vector embeddings are a **derived retrieval projection**. They are not authoritative evidence and must remain traceable to the source/evidence records from which they were generated.

### Neo4j

Neo4j is a governed graph projection used for relationship traversal and graph-oriented computation. It is not an independent authority that can override the evidence ledger.

### Evidence semantics

TMRDS distinguishes observed/source-backed assertions from model-derived or hypothesized relationships. Research outputs should retain source identity, retrieval/provenance metadata, and uncertainty rather than presenting predictions as established medical facts.

## Real-world real-time data fabric

The data fabric provides bounded, provenance-first synchronization for authoritative public feeds. It records source identity, retrieval/observation timestamps, ETag/Last-Modified metadata when available, SHA-256 payload identity, provenance state, and durable observation records.

Current catalog includes:

- USGS Water Services
- USGS Earthquake Hazards feeds
- NOAA/NWS weather API
- NWS active alerts
- FEMA disaster declarations
- CDC public data

Continuous synchronization is provided by `workers/realtime_data_fabric_worker.py`. See `docs/REALTIME_DATA_FABRIC.md` for operational details.

## Interoperability

- **FHIR R4 / US Core:** clinical interoperability boundary and resource mapping.
- **OMOP CDM v5.4:** research normalization boundary.
- The architecture keeps clinical exchange, research normalization, evidence provenance, semantic retrieval, and graph projection as separable concerns.

## AI governance

The AI governance layer is intentionally restrictive:

1. Model identity/version is recorded.
2. Prompt/policy provenance is recorded where applicable.
3. Dataset/evaluation metadata can be attached to generations.
4. Evidence envelopes identify the evidence available to an output.
5. Uncertainty and human-review requirements are explicit.
6. Research outputs cannot be promoted implicitly into autonomous clinical authority.

TMRDS therefore implements a **research-advisory architecture**, not an autonomous clinical decision-maker.

## Optional scientific engines

The repository contains additional scientific, imaging, simulation, and research engines. Heavy or optional engines are lazy-loaded from `engines/__init__.py` so that an unavailable optional dependency does not break unrelated API or evidence tests.

Do not install heavyweight scientific stacks merely to run the core API unless a specific engine requires them.

## Repository layout

```text
TMRDS/
├── api/                 # FastAPI application and route modules
├── engines/             # Research, evidence, interoperability, and optional engines
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

## Requirements

Core development/CI targets **Python 3.11**. The repository's `requirements.txt` provides the FastAPI, HTTP, database, Neo4j, numerical, and test dependencies required by the current test suite.

## Testing and CI

The deterministic CI gate runs:

```bash
python -m pytest -q -m "not integration"
```

Live-source and PostgreSQL/Neo4j tests are explicitly marked `integration`. Security scanning is maintained separately in `.github/workflows/security.yml`.

## Non-negotiable research constraints

1. **No fabricated medical evidence.**
2. **No unsupported clinical claims.**
3. **No autonomous diagnosis or prescribing authority.**
4. **Source provenance must remain inspectable.**
5. **Derived vectors/graphs must not silently replace authoritative evidence.**
6. **Research predictions must be distinguishable from observed/source-backed evidence.**
7. **Human clinical authority remains outside the software's authority boundary.**

## Disclaimer

TMRDS is research software for biomedical evidence exploration and engineering development. It is not medical advice, a diagnosis, a prescription, or a substitute for qualified clinical judgment. No repository documentation should be interpreted as evidence that TMRDS is FDA-cleared, clinically validated, HIPAA-certified, or authorized for a particular regulated use.
