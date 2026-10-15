# TMRDS Biomedical Evidence Graph Operations

## Startup

Set database credentials in an untracked `.env` file using `.env.example` as a template. Build the image and start the databases first:

```bash
docker compose build tmrds-api
docker compose up -d tmrds-postgres tmrds-neo4j
docker compose run --rm --no-deps -e TMRDS_ENV=development tmrds-api python -m engines.migration_runner status
docker compose run --rm --no-deps -e TMRDS_ENV=development tmrds-api python -m engines.migration_runner upgrade
docker compose up -d tmrds-api
```

Migrations are explicit; the application does not run schema changes at startup. The runner serializes upgrades with a PostgreSQL advisory lock and records checksums. For an existing volume without migration history, inspect the full schema and follow the baseline/backup procedure in `docs/operations/tmrds-operations-runbook.md`; do not assume table existence proves the entire migration was applied.

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
