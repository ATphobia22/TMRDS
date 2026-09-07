# TMRDS Biomedical Evidence Graph Operations

## Startup

Set database credentials in the deployment environment, then run:

```bash
docker compose up -d
```

The PostgreSQL initialization directory applies `migrations/001_biomedical_evidence_graph.sql` to a new database. Existing volumes require an explicit migration process before applying later schema changes.

## Research API

The governed graph exposes:

- `/api/v1/evidence/entities/{entity_id}`
- `/api/v1/evidence/entities/{entity_id}/assertions`
- `/api/v1/evidence/assertions/{assertion_id}`
- `/api/v1/evidence/path`
- `/api/v1/evidence/graph`
- `/api/v1/evidence/conflicts`
- `/api/v1/evidence/sources`
- `/api/v1/evidence/sources/{source_id}`
- `/api/v1/evidence/ingestion/status`

Every response is research-advisory and read-only.

## Evidence lineage

```text
live source
  -> source observation + content hash
  -> canonical entity
  -> immutable assertion
  -> evidence assessment
  -> conflict detection
  -> Neo4j projection
  -> provenance-aware query
```

## Conflict handling

Conflicts remain visible. A detected conflict is not automatically converted into a clinical conclusion. Human review or an authoritative source may change the conflict state, with provenance retained.

## Graph rebuild

Neo4j is a projection. It can be rebuilt from PostgreSQL governed records without depending on vector embeddings or an LLM.

## Upstream verification

Live integration tests intentionally make real requests to supported public sources. They must be run in an environment with network access and should be interpreted alongside upstream rate limits, maintenance windows, and schema changes.
