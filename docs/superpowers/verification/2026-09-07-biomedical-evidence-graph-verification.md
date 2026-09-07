# Biomedical Evidence Graph Verification Record

## Implementation state

The approved evidence-graph architecture has been implemented on `main` with:

- typed biomedical evidence models
- governed source registry
- PostgreSQL schema and repository
- immutable source observations/content hashes
- deterministic entity canonicalization
- evidence assertions and assessments
- conservative conflict detection
- live ClinicalTrials.gov and OpenNeuro ingestion adapters
- ClinicalTrials condition/intervention/publication relationships
- Neo4j rebuildable projection
- provenance-aware graph query API
- live ingestion API routes
- operational observability primitives
- security/operations/data-dictionary documentation
- live integration-test suites with no upstream mocks

## Verification limitations

The current agent runtime cannot resolve `github.com` from the container, so the repository could not be cloned and the Python/Docker test suite could not be executed locally in this turn. The GitHub connector successfully committed the implementation files, but that is not equivalent to a passing runtime test.

Live upstream documentation was independently checked for current contracts. ClinicalTrials.gov documents the modern `/api/v2/studies` API, `protocolSection.conditionsModule.conditions`, `protocolSection.referencesModule.references`, and `/api/v2/version` `dataTimestamp`; OpenFDA documents `/drug/shortages.json`; OpenNeuro documents its public GraphQL API. These checks support the implemented source contract, but they do not replace execution of the live tests.

## Required execution environment

Run with network access and Docker:

```bash
export POSTGRES_PASSWORD='<strong-password>'
export NEO4J_PASSWORD='<strong-password>'
docker compose up -d
pytest -m integration -v
pytest -v
```

Then exercise:

```text
GET /api/v1/research/health
GET /api/v1/evidence/sources
GET /api/v1/evidence/ingestion/status
POST /api/v1/evidence/ingest/clinical-trials?query=cancer&limit=5
POST /api/v1/evidence/ingest/openneuro?query=MRI&limit=5
```

The final acceptance claim must be made only after those commands execute successfully in the target environment.
