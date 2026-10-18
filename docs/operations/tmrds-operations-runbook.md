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

## Observability, rate limiting, and API-key auth

**Metrics.** `GET /metrics` exposes Prometheus RED metrics (rate, errors, duration per route) via `prometheus-fastapi-instrumentator`. Scrape it from Prometheus on a 15s interval. In Compose the API binds to loopback, so scrape via `127.0.0.1:8000`; do not expose `/metrics` to the public internet. If the instrumentator package is missing, the endpoint is absent and startup logs a warning — the API still serves.

**Rate limiting.** `slowapi` enforces a sliding-window default of 120 requests/minute per client IP on all routes, with a stricter 20/minute on the expensive `GET /api/v1/research/federated-search` (it fans out to six upstream sources per call). A 429 response carries a `Retry-After` header and the sanitized body `{"detail": {"code": "RATE_LIMITED", "message": ...}}`. Per-route tiers are applied with `@limiter.limit(...)` in `api/main.py`; the decorated route must accept `request: Request`.

**Security headers.** Every response carries `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, and a minimal `Permissions-Policy`.

**API-key auth (optional, off by default).** Public research routes serve public data and stay open unless the operator opts into key-gating:

1. Create a key file with one `key_id:sha256(secret)` per line (`#` comments and blanks allowed). Generate each secret with `python -c "import secrets; print(secrets.token_urlsafe(32))"` and store only its SHA-256 hex in the file — never the secret itself.
2. Hand the key to the consumer as `tmrds_<key_id>_<secret>`.
3. Set `TMRDS_API_KEYS_FILE=/run/secrets/tmrds_api_keys` (Compose file secret or a root-only file) and restart.

Fail-closed behavior is intentionally NOT used here: the system always starts and serves. If `TMRDS_API_KEYS_FILE` is set but the file is missing, unreadable, malformed, or empty, the API runs OPEN and reports the degraded posture loudly — a CRITICAL startup log line plus `"auth": "degraded-open"` with the reason in `GET /api/v1/ops/posture` — instead of refusing to start. Nothing fails silently, and public research data stays reachable. When the file is valid, every `/api/*` path requires `X-API-Key`; `/health/*` and `/metrics` stay open. Denials return 401 `{"detail": {"code": "UNAUTHORIZED", ...}}` and are logged with the key_id only — raw keys are never logged. Allowed requests are audit-logged with key_id and path. Revoke a key by deleting its line and restarting. Per-key scopes are future work; v1 grants the single research scope or nothing.

## Observability overlay (Caddy, Prometheus, Alertmanager, Grafana, Keycloak)

`docker-compose.obs.yml` layers the public edge and operations stack onto the base file without touching it:

```bash
cp secrets/grafana_admin_password.txt.example secrets/grafana_admin_password.txt
cp secrets/keycloak_db_password.txt.example secrets/keycloak_db_password.txt
cp secrets/keycloak_admin_password.txt.example secrets/keycloak_admin_password.txt
# fill in all three files, then:
docker compose -f docker-compose.yml -f docker-compose.obs.yml up -d
```

What it adds:
- **Caddy** (`https://$TMRDS_PUBLIC_HOST`): automatic Let's Encrypt TLS, certificates persisted in `caddy_data`. `/metrics*` is blocked at the edge (`abort`) — Prometheus scrapes it over the internal backend network only.
- **Prometheus**: scrapes `tmrds-api:8000/metrics` every 15s; evaluates `deploy/prometheus/alerts.yml` (API down, 5xx rate, p95 latency, 429 spike).
- **Alertmanager**: receives alerts; the default receiver is a placeholder — configure a real notifier before relying on pages.
- **Grafana OSS** (AGPL-3.0): serves the provisioned "TMRDS API — RED" dashboard (request rate, 5xx share, p50/p95 latency, 429 rate) with the Prometheus datasource pre-wired. Admin password comes from the `grafana_admin_password` file secret, never the environment.
- **Keycloak** (`https://$TMRDS_AUTH_HOST`, realm `tmrds`): OIDC identity provider for the existing service-JWT validator (`engines/service_identity.py`). The realm import creates the confidential `tmrds-api` client (client-credentials flow only, human login disabled) with `evidence.write` / `evidence.read` client scopes.

Wiring Keycloak to the API (machine-to-machine):
1. Open the Keycloak admin console, retrieve the generated secret for the `tmrds-api` client (Credentials tab).
2. `python scripts/fetch-keycloak-jwks.py --issuer https://$TMRDS_AUTH_HOST/realms/tmrds` and store the output as `TMRDS_SERVICE_JWKS_JSON` (use a secret, not a committed file).
3. Set `TMRDS_SERVICE_ISSUER=https://$TMRDS_AUTH_HOST/realms/tmrds` (must match exactly — the validator checks `iss` strictly) and `TMRDS_SERVICE_AUDIENCE=tmrds-api`.
4. Keep `TMRDS_SERVICE_AUTH_REQUIRED=true` in production. Re-run the fetch script after any Keycloak key rotation.

Secrets rule for the whole stack: secret VALUES never go in `environment:` (visible via `docker inspect`). Use Compose file secrets mounted at `/run/secrets/` with `*_FILE` variables, or `_FILE`-suffixed app variables like `TMRDS_API_KEYS_FILE`. The `./secrets/` directory is gitignored; only `*.example` templates are committed.

## IBM Quantum reconciliation

Hardware job creation remains disabled unless the submitting application explicitly enables it and supplies per-workload authorization. CI never submits hardware jobs.

For a read-only reconciliation pass, configure in a trusted environment:
- `IBM_QUANTUM_API_KEY` and `IBM_QUANTUM_INSTANCE_CRN` for an existing eligible Compute Service instance.
- `TMRDS_DATABASE_URL` pointing to the TMRDS PostgreSQL ledger.
- `TMRDS_IBM_QUANTUM_RECONCILER_ENABLED=true`.
- `TMRDS_QUANTUM_ARTIFACT_DIR` optionally pointing to a private, durable directory; the default is `/app/data/quantum-results` in Compose. Back up this directory under the operator's policy.

Then run a single bounded pass:

```bash
python scripts/ibm_quantum_reconcile_once.py --limit 25
```

The reconciler performs read-only job/status/result requests, processes a bounded page, stores result JSON as private immutable artifacts, and persists a SHA-256 hash and artifact URI. It does not submit or cancel jobs. If an accepted remote job has no known job ID, it remains unresolved; do not infer a match from timestamps, backend, or input content. Resolve such records only through a reviewed operator workflow with evidence and an audit entry.

The optional Compose worker is under the `quantum-reconciler` profile. It is a one-shot task and defaults to disabled. Do not enable it until the IBM account has a valid instance CRN, required IAM read permissions, and a configured durable result store. The regular IBM Quantum account alone does not prove Compute Service job entitlement.

Run one pass only after the profile is explicitly enabled:

```bash
TMRDS_IBM_QUANTUM_RECONCILER_ENABLED=true docker compose --profile quantum-reconciler run --rm tmrds-quantum-reconciler
```

For an ambiguous record, first verify the remote job ID in IBM's authenticated job history and preserve evidence in a durable, access-controlled artifact or incident record. Then run the privileged command from an administrative shell:

```bash
TMRDS_QUANTUM_OPERATOR_RESOLUTION_ENABLED=true python scripts/ibm_quantum_reconcile_once.py \\
  --resolve-unknown <submission-uuid> \\
  --ibm-job-id <confirmed-ibm-job-id> \\
  --operator-id <operator-audit-id> \\
  --evidence-reference artifact://quantum-audit/<evidence-id>
```

This updates only a `SUBMISSION_UNKNOWN` record that has no linked remote job ID and writes a separate append-only audit row through migration 005. The operator identifier is an asserted audit identity supplied by the privileged operator; this CLI does not authenticate the human independently. Protect shell access and audit storage accordingly. The command never creates a remote job.

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


## Optional AWS deployment assessment (not provisioned)

The current deployment remains Docker Compose. No AWS account, IAM role, ECS service, registry, or paid resource was created. If TMRDS is later approved for ECS, use task-level least-privilege IAM, restrict security-group ingress/egress, inject credentials from AWS Secrets Manager or Systems Manager Parameter Store rather than baking them into images, and enable CloudTrail/CloudWatch monitoring. Review the current [AWS ECS secrets-management guidance](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/security-secrets-management.html) and [ECS container-instance hardening guidance](https://repost.aws/knowledge-center/ecs-secure-container-instance-best-practices) before designing that deployment. This is a future deployment checklist, not evidence that AWS controls are configured.
