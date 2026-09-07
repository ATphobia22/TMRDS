# Biomedical Evidence Graph Verification Record

## Implementation state

The approved TMRDS evidence/provenance/interoperability/graph/AI-governance backbone is implemented on `main` with:

- typed biomedical evidence models
- governed source registry
- PostgreSQL evidence authority and append-oriented observations
- deterministic entity canonicalization
- evidence assertions and assessments
- conservative conflict detection
- live public-source adapters already present in the repository
- Neo4j rebuildable graph projection
- provenance-aware graph query API
- live ingestion API routes
- FHIR R4 / US Core and OMOP CDM v5.4 integration modules already present in the repository
- new PostgreSQL migration for AI governance, vector retrieval, FHIR resource observations, and OMOP research tables
- pgvector-backed evidence embeddings and cosine semantic retrieval
- provider-neutral AI model/prompt/dataset/evaluation/generation governance contracts
- provenance-required AI generation validation with mandatory human authority
- terminology/chemistry source governance entries for LOINC, MONDO, HGNC, and ChEMBL
- LOINC access explicitly modeled as credentialed rather than public
- GitHub Actions CI workflow for Python test execution
- security/operations/data-dictionary documentation

## Verification limitations

The current agent runtime cannot resolve `github.com` from the container, so the repository could not be cloned and the Python/Docker test suite could not be executed locally in this turn. GitHub connector writes succeeded, but repository mutation is not equivalent to a passing runtime test.

The GitHub commit status for the latest `main` commit is currently `pending` with no completed status checks reported yet. Therefore **no claim of passing CI is made here**.

Current implementation should be validated in a network-enabled repository runner with PostgreSQL/pgvector and Neo4j available.

## Required execution environment

```bash
export POSTGRES_PASSWORD='<strong-password>'
export NEO4J_PASSWORD='<strong-password>'
docker compose up -d
python -m pytest -v
```

For the live integration suite, also run:

```bash
python -m pytest -m integration -v
```

Then exercise:

```text
GET /api/v1/research/health
GET /api/v1/evidence/sources
GET /api/v1/evidence/ingestion/status
GET /api/v1/governance/ai/status
POST /api/v1/governance/ai/validate
POST /api/v1/evidence/semantic-search
POST /api/v1/evidence/ingest/clinical-trials?query=cancer&limit=5
POST /api/v1/evidence/ingest/openneuro?query=MRI&limit=5
```

The final acceptance claim must be made only after those commands execute successfully in the target environment.
