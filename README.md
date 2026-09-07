# TMRDS — Transparent Medical Research Decision Support

**Research-advisory biomedical evidence gateway with governed provenance, interoperability, and AI governance.**

> **Status:** Research software. TMRDS is not FDA-cleared Software as a Medical Device (SaMD), does not replace clinical judgment, and is not a diagnostic or prescribing system.

## What TMRDS is

TMRDS is a Python/FastAPI research platform for connecting public biomedical evidence to a governed evidence model. The current implementation combines:

- **Public biomedical source adapters** for CDC, OpenNeuro, ClinicalTrials.gov, openFDA, NLM Clinical Tables, Europe PMC, and PubMed.
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
     OpenNeuro
              │                       │                        │
              └───────────────────────┼────────────────────────┘
                                      ▼
                         ┌─────────────────────────┐
                         │      PostgreSQL          │
                         │  authoritative evidence  │
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

## Implemented API surface

The FastAPI application currently exposes research-advisory routes including:

### Public biomedical research

```text
GET /api/v1/research/health
GET /api/v1/research/datasets/cdc
GET /api/v1/research/datasets/openneuro
GET /api/v1/research/trials
GET /api/v1/research/drugs/labels
GET /api/v1/research/drugs/adverse-events
GET /api/v1/research/drugs/shortages
GET /api/v1/research/nlm/conditions
GET /api/v1/research/nlm/hpo
GET /api/v1/research/nlm/genes
GET /api/v1/research/nlm/rxterms
GET /api/v1/research/literature/europe-pmc
GET /api/v1/research/literature/pubmed
GET /api/v1/research/federated-search
```

### Governed evidence graph

```text
GET /api/v1/evidence/entities/{entity_id}
GET /api/v1/evidence/entities/{entity_id}/assertions
GET /api/v1/evidence/assertions/{assertion_id}
GET /api/v1/evidence/path
GET /api/v1/evidence/graph
GET /api/v1/evidence/conflicts
GET /api/v1/evidence/sources
GET /api/v1/evidence/sources/{source_id}
GET /api/v1/evidence/ingestion/status
```

Additional ingestion, retrieval, and AI-governance routes are registered through the dedicated API routers in `api/`.

Research responses are wrapped with explicit governance metadata, including:

```json
{
  "status": "research-advisory",
  "human_authority_final": true,
  "not_samd": true,
  "read_only": true
}
```

## Data and evidence model

TMRDS treats the evidence ledger as authoritative. Derived representations must not silently become sources of truth.

### PostgreSQL

The PostgreSQL layer stores governed evidence and provenance records. Migrations live in `migrations/` and are mounted by the development Docker Compose stack.

### pgvector

Vector embeddings are a **derived retrieval projection**. They are not authoritative evidence and must remain traceable to the source/evidence records from which they were generated.

### Neo4j

Neo4j is a governed graph projection used for relationship traversal and graph-oriented computation. It is not an independent authority that can override the evidence ledger.

### Evidence semantics

TMRDS distinguishes observed/source-backed assertions from model-derived or hypothesized relationships. Research outputs should retain source identity, retrieval/provenance metadata, and uncertainty rather than presenting predictions as established medical facts.

## Interoperability

- **FHIR R4 / US Core:** clinical interoperability boundary and resource mapping.
- **OMOP CDM v5.4:** research normalization boundary.
- The architecture keeps clinical exchange, research normalization, evidence provenance, semantic retrieval, and graph projection as separable concerns.

FHIR/OMOP adapters and supporting specifications are documented in `docs/`.

## AI governance

The AI governance layer is intentionally restrictive:

1. Model identity/version is recorded.
2. Prompt/policy provenance is recorded where applicable.
3. Dataset/evaluation metadata can be attached to generations.
4. Evidence envelopes identify the evidence available to an output.
5. Uncertainty and human-review requirements are explicit.
6. Research outputs cannot be promoted implicitly into autonomous clinical authority.

TMRDS therefore implements a **research-advisory architecture**, not an autonomous clinical decision-maker.

## Source registry

The repository contains a governed source registry for biomedical sources such as:

- CDC
- OpenNeuro
- ClinicalTrials.gov
- openFDA
- NLM
- PubMed
- Europe PMC
- LOINC
- MONDO
- HGNC
- ChEMBL

A source being registered does **not** mean its data are automatically clinical-grade or validated for clinical decision-making. Upstream source limitations remain part of the governance boundary.

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
├── .github/workflows/   # CI
├── docker-compose.yml   # PostgreSQL/pgvector + Neo4j + API development stack
├── deploy.sh            # Deployment helper
├── requirements.txt     # Python runtime/test dependencies
└── pytest.ini           # Pytest configuration
```

## Requirements

Core development/CI currently targets **Python 3.11**. The repository's `requirements.txt` provides the FastAPI, HTTP, database, Neo4j, numerical, and test dependencies required by the current test suite.

Some optional scientific engines have dependencies that are intentionally not part of the core installation.

## Run locally

### Python environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m pytest -q -m "not integration"
```

The normal test command intentionally excludes live integration tests because those tests require external upstream availability and/or running PostgreSQL/Neo4j services. To run the live integration suite explicitly:

```bash
python -m pytest -q -m integration
```

The integration suite is therefore a separate operational check, not a prerequisite for the deterministic unit/API CI gate.

Start the API with:

```bash
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Then inspect the FastAPI OpenAPI document at `/docs` or `/openapi.json`.

### Docker Compose

The Compose stack provisions:

- `tmrds-postgres` using `pgvector/pgvector:pg16`
- `tmrds-neo4j` using Neo4j Community Edition
- `tmrds-api` using Python 3.11

Set the required database and Neo4j passwords before starting the stack:

```bash
export POSTGRES_PASSWORD='change-me'
export NEO4J_PASSWORD='change-me-too'
docker compose up --build
```

The API is exposed on port `8000`; Neo4j exposes ports `7474` and `7687`.

**Do not use placeholder passwords or the development Compose configuration as a production security boundary.** Production deployments require secret management, network controls, least privilege, TLS, backups, monitoring, and a documented threat/risk model.

## Testing and CI

GitHub Actions runs the deterministic Python test gate with Python 3.11:

```bash
python -m pytest -q -m "not integration"
```

Live-source and PostgreSQL/Neo4j tests are explicitly marked `integration` and are not included in the default CI gate. The dependency set includes `requests` because the integration suite uses it, while optional scientific dependencies remain outside the core requirements unless required by a specific test or deployment profile.

## Security and regulated-boundary posture

TMRDS is designed with security and regulatory boundaries in mind, but repository alignment is **not** equivalent to certification, compliance attestation, FDA clearance, or authorization to process regulated clinical workloads.

Important controls and design documents include:

- `docs/EVIDENCE_GRAPH_SECURITY.md`
- `docs/EVIDENCE_GRAPH_OPERATIONS.md`
- `docs/ARCHITECTURE_VERIFICATION.md`
- `docs/FHIR_OMOP_SPECIALTIES.md`
- `docs/FHIR_R5_HIPAA.md`
- `docs/SAMD_IEC62304_ISO14971.md`
- `engines/hipaa_security_controls.py`

For real PHI/clinical deployment, conduct an independent security assessment, HIPAA risk analysis where applicable, access-control review, privacy analysis, threat modeling, validation, and regulatory determination before use.

## Non-negotiable research constraints

1. **No fabricated medical evidence.**
2. **No unsupported clinical claims.**
3. **No autonomous diagnosis or prescribing authority.**
4. **Source provenance must remain inspectable.**
5. **Derived vectors/graphs must not silently replace authoritative evidence.**
6. **Research predictions must be distinguishable from observed/source-backed evidence.**
7. **Human clinical authority remains outside the software's authority boundary.**

## Documentation

Start with:

- `docs/ARCHITECTURE_SOVEREIGNTY.md`
- `docs/ARCHITECTURE_VERIFICATION.md`
- `docs/EVIDENCE_GRAPH_DATA_DICTIONARY.md`
- `docs/EVIDENCE_GRAPH_OPERATIONS.md`
- `docs/EVIDENCE_GRAPH_SECURITY.md`
- `docs/FHIR_OMOP_SPECIALTIES.md`
- `docs/MEDICAL_PROFESSIONAL_INSPECTION.md`
- `docs/NEO4J_REGENSTRIEF.md`

## Disclaimer

TMRDS is research software for biomedical evidence exploration and engineering development. It is not medical advice, a diagnosis, a prescription, or a substitute for qualified clinical judgment. No repository documentation should be interpreted as evidence that TMRDS is FDA-cleared, clinically validated, HIPAA-certified, or authorized for a particular regulated use.
