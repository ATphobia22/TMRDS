# TMRDS Operations and Recovery Runbook

## Deployment model

TMRDS runs a Python 3.11 API image with PostgreSQL/pgvector and Neo4j under Docker Compose. The API image installs exact versions from `requirements-runtime.lock`; CI installs the complete `requirements.lock`. The runtime container is non-root, has a read-only root filesystem, drops Linux capabilities, and writes mutable runtime data only to the named `tmrds-runtime-data` volume.

The default Compose configuration publishes the API only to loopback (`127.0.0.1:8000`) and does not publish database ports. Use `docker-compose.dev.yml` only for local debugging; it binds database ports to loopback and must not be used as a production exposure policy.

## Safe local setup

1. Copy `.env.example` to an untracked `.env` file and replace every placeholder with local values. Generate strong random secrets; do not reuse these example values.
2. Confirm `TMRDS_DATABASE_URL` points to the Compose PostgreSQL service (`tmrds-postgres`) and uses a URL-encoded password.
3. Build and start the database services:

   ```bash
   docker compose build tmrds-api
   docker compose up -d tmrds-postgres tmrds-neo4j
   ```

4. Check migration status before changing schema:

   ```bash
   docker compose run --rm --no-deps tmrds-api python -m engines.migration_runner status
   ```

5. For a fresh, empty local database, apply migrations explicitly:

   ```bash
   docker compose run --rm --no-deps -e TMRDS_ENV=development tmrds-api python -m engines.migration_runner upgrade
   ```

6. Start the API and check service health:

   ```bash
   docker compose up -d tmrds-api
   docker compose ps
   curl --fail http://127.0.0.1:8000/health/live
   curl --fail http://127.0.0.1:8000/health/ready
   ```

The application does not auto-apply migrations at startup. Readiness remains unavailable until the required PostgreSQL schema is present.

## Existing PostgreSQL volumes

**Never delete a volume or rerun initialization by destroying an existing database.** PostgreSQL's initialization directory is only run when the data directory is first initialized; the current Compose configuration deliberately does not mount migration scripts into that init directory.

Before an upgrade:
- Take and verify a database backup or snapshot using the operator's established procedure.
- Confirm the target DSN and database identity using a read-only connection.
- Run `status` and inspect the full schema and migration files.
- If the database predates the migration ledger, determine the exact migrations already applied. The runner intentionally refuses to infer history from table names alone.
- Only after reviewing schema equivalence and backup recovery, record the verified baseline. For example, `baseline --through 2` asserts that versions 001 and 002 are fully applied; it does not validate every column/index/constraint. Do not use this example without a schema review.
- Apply remaining migrations explicitly, then rerun `status`.

The runner serializes migrations with a PostgreSQL advisory lock, records SHA-256 checksums, and stops on checksum/name drift. Current migration files are transaction-compatible. Any future migration using non-transactional DDL (for example, `CREATE INDEX CONCURRENTLY`) must be isolated and explicitly supported before being added to the runner.

For a production database, the runner requires the explicit environment flag `TMRDS_ALLOW_PRODUCTION_MIGRATIONS=true`. Use it only from the approved release process after backup/recovery validation. Do not run production migration commands from CI.

## Health semantics

- `GET /health/live`: process is running; does not depend on PostgreSQL or upstream research sources.
- `GET /health/ready`: PostgreSQL is reachable and the core evidence schema exists.
- `GET /api/v1/research/health`: informational inventory of configured research adapters; this is not proof that every external source is reachable.

API errors use stable public error codes and the `X-Request-ID` response header. Do not log tokens, authorization headers, full upstream bodies, raw circuits, or clinical payloads. The request ID is for correlation, not authentication.

## IBM Quantum reconciliation

Hardware job creation remains disabled unless the submitting application explicitly enables it and supplies per-workload authorization. CI never submits hardware jobs.

For a read-only reconciliation pass, configure in a trusted environment:
- `IBM_QUANTUM_API_KEY` and `IBM_QUANTUM_INSTANCE_CRN` for an existing eligible Compute Service instance.
- `TMRDS_DATABASE_URL` pointing to the TMRDS PostgreSQL ledger.
- `TMRDS_IBM_QUANTUM_RECONCILER_ENABLED=true`.
- `TMRDS_QUANTUM_RESULT_DIR` pointing to a private, durable directory backed up under the operator's policy.

Then run a single bounded pass:

```bash
python -m engines.ibm_quantum_reconciler --once
```

The reconciler performs read-only job/status/result requests, processes a bounded page, stores result JSON as private immutable artifacts, and persists a SHA-256 hash and artifact URI. It does not submit or cancel jobs. If an accepted remote job has no known job ID, it remains unresolved; do not infer a match from timestamps, backend, or input content. Resolve such records only through a reviewed operator workflow with evidence and an audit entry.

The optional Compose worker is under the `quantum-reconciler` profile. It is a one-shot task and defaults to disabled. Do not enable it until the IBM account has a valid instance CRN, required IAM read permissions, and a configured durable result store. The regular IBM Quantum account alone does not prove Compute Service job entitlement.

## Backup and rollback

- Back up PostgreSQL using the established operator backup mechanism and verify restoration in an isolated test environment.
- Back up the named `tmrds-runtime-data` volume if it contains audit logs or quantum result artifacts that must be retained.
- Treat Neo4j as a rebuildable evidence projection only where repository documentation and current data state confirm it; do not discard it without verifying that the projection can be rebuilt.
- Prefer forward corrective migrations. Do not delete the migration ledger or edit an applied SQL file to make a checksum error disappear.
- A failed transactional migration should roll back its schema/data changes; confirm the actual migration's transactional behavior before relying on rollback.

## Release evidence

For each release, retain:
- source commit SHA and pull-request review outcome;
- dependency-lock verification and container build results;
- unit and integration test results, including explicit blocked checks;
- Compose configuration validation;
- image digest if a release image is built and published;
- backup/recovery verification and migration status;
- unresolved security, interoperability, and deployment risks.

A successful CI run does not prove production health, regulatory conformance, external-source availability, or IBM hardware access. Never claim those outcomes without separate evidence.
