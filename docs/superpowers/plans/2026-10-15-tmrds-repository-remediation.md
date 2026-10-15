# TMRDS Repository Remediation — Implementation Plan

**Date:** 2026-10-15  
**Repository:** ATphobia22/TMRDS  
**Target branch:** `main`  
**Spec:** [2026-10-15-tmrds-repository-remediation-design.md](../specs/2026-10-15-tmrds-repository-remediation-design.md)  
**Status:** Core remediation implemented and merged to `main`; final production readiness remains conditional on environment-specific verification.

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan. Work in small, test-first commits. Do not claim commands, tests, builds, attestations, installs, or deployments succeeded unless they were actually run and inspected.

## Goal

Remediate the verified security, data-integrity, deployment, reliability, provenance, and quantum-workflow risks in TMRDS while preserving existing platform boundaries and persistent data. Deliver reviewable commits, reproducible checks, operator documentation, and a clear list of any blocked acceptance criteria.

## Architecture

Keep FastAPI/Python, PostgreSQL/pgvector, Neo4j, and Docker Compose. Use a single versioned PostgreSQL migration runner with a durable checksum ledger and advisory lock. Use stable sanitized API error envelopes and correlation IDs. Build the API as an immutable non-root image with locked dependencies; keep databases on internal Compose networks. Separate liveness, readiness, and dependency health. Keep IBM Quantum hardware submission disabled by default; reconcile existing remote job IDs only, never auto-resubmit ambiguous submissions. Preserve evidence provenance and advisory-only medical-research boundaries.

## Tech stack

Python 3.11; FastAPI; pytest/pytest-asyncio; PostgreSQL/asyncpg; Neo4j; Docker Compose; GitHub Actions. Do not introduce a new cloud dependency or paid service without separate approval.

## Global constraints

- Never delete/reinitialize persistent volumes or drop/truncate existing data.
- Do not run migrations against a production database; integration tests must use disposable, explicitly named test databases/containers.
- No live IBM Quantum job submissions, no secret-bearing outputs, no patient data in fixtures, and no unapproved cloud provisioning.
- Never automatically retry a potentially accepted quantum POST or another non-idempotent write.
- Do not make medical-device, diagnostic, treatment, FHIR/US Core, OMOP, or regulatory-conformance claims beyond validated evidence.
- Keep compatibility with regular IBM Quantum accounts and current documented Compute Service access; no assumption that an account automatically has instance/job entitlements.
- Keep external-service checks opt-in and skip/fail with a clear reason when their required local service/configuration is absent; never silently replace live outputs with synthetic results.
- Commit in small, independently reviewable increments; inspect diffs and CI results after each workstream.

## Workstream 0 — Baseline inventory and reproducibility

**Files:** `docs/superpowers/specs/2026-10-15-tmrds-repository-remediation-design.md`, `docs/superpowers/plans/2026-10-15-tmrds-repository-remediation.md`, repository inventory/test scripts as justified.

1. Re-fetch the current `main` tree and relevant files before editing; reconcile the plan with the live tree and note any changed SHAs.
2. Record Python version, dependency/test commands, existing migrations, all FastAPI routes and auth dependencies, container ports/volumes, and current workflow jobs.
3. Run existing non-destructive checks available in the environment: compile, test collection, unit tests, deterministic secret scan, and static configuration checks. Capture actual outputs and distinguish baseline failures from introduced failures.
4. Create a baseline report in `docs/audits/` containing date, commit SHA, commands, pass/fail/blocked results, and no secrets or patient data.
5. **Tests/acceptance:** baseline report is reproducible; all route and migration paths are enumerated; no changes to runtime behavior in this workstream.

## Workstream 1 — API error contract, correlation, and identity

**Likely files:** `api/main.py`, `api/evidence_ingestion_routes.py`, shared API error/observability module, `api/security_dependencies.py`, related `tests/test_*.py`.

1. Add failing tests asserting that upstream and ingestion failures return stable public error codes plus a correlation/request ID and never include the original exception string.
2. Implement a shared exception-to-response policy and request correlation middleware/dependency. Return generic details to clients; log structured, redacted diagnostics server-side without authorization headers, tokens, full upstream bodies, SQL parameters, or sensitive query payloads.
3. Preserve HTTP status semantics (upstream failure remains 502; validation/auth statuses remain appropriate); avoid exposing stack traces in production responses.
4. Enumerate all routes and label each public, authenticated, or privileged. Verify service identity fail-closed behavior in production configuration and test missing, malformed, expired, wrong-issuer, wrong-audience, wrong-scope, and invalid-signature tokens where the existing validator supports these claims.
5. Review CORS, request/body limits, outbound URL validation/SSRF surfaces, and rate limiting. Add protections only where supported by actual route and deployment behavior; document limits that require a reverse proxy.
6. **Tests:** API contract tests; secret/error leakage tests; auth negative cases; regression tests for successful responses. Run the focused tests, then the full non-integration suite.

## Workstream 2 — Ordered, checksummed database migrations

**Files:** new `engines/migration_runner.py` (or a module under the established database package after inventory), `migrations/`, `tests/test_migration_runner.py`, `docker-compose.yml`, migration runbook.

1. Add unit tests first for migration discovery/order, checksum computation, unknown/duplicate versions, checksum drift, and malformed migration names.
2. Implement a migration metadata table recording version, name, checksum, and applied timestamp. Serialize runners using a PostgreSQL advisory lock. Execute each SQL migration in a transaction where PostgreSQL and the script permit it; if an existing migration cannot be transactional, document and test the exception rather than pretending rollback is possible.
3. Reuse existing numbered SQL scripts; do not rewrite applied migrations. Make the runner idempotent and fail closed on drift or unknown schema state. Do not run migrations implicitly against an unknown production target.
4. Add an explicit command (e.g. `python -m engines.migration_runner status|upgrade`) requiring `TMRDS_DATABASE_URL`, with clear dry-run/status output and safeguards against an accidental production target. Confirm the command/interface after source inventory.
5. Test against a disposable PostgreSQL instance: empty database, existing schema missing later migrations, concurrent runners, a failing migration, checksum mismatch, and repeat invocation. Verify table/data counts are unchanged on failed migrations where transactional rollback is supported.
6. Update Compose so migrations are not dependent solely on PostgreSQL's first-volume initialization hook. Keep a controlled explicit migration step and document backup/recovery before upgrades.
7. **Acceptance:** fresh and pre-existing test databases converge to the expected schema; parallel runners apply each migration once; drift stops startup/upgrade without destructive repair.

## Workstream 3 — Immutable build and network boundary

**Files:** `Dockerfile`, `.dockerignore`, dependency lock/constraints file, `requirements.txt` as compatibility policy permits, `docker-compose.yml`, `deploy.sh`, `.github/workflows/ci.yml`.

1. Add build/config tests first for required files, pinned dependency resolution, no package install in container startup, non-root runtime, and absence of unintended database/admin host-port publishing.
2. Resolve compatible versions from the current dependency set, create an auditable fully pinned lock or constraints file with hashes if the selected resolver supports them, and verify clean installation. Do not blindly pin arbitrary latest versions; check Python 3.11 compatibility and run tests.
3. Build a multi-stage or minimal Python 3.11 image, install dependencies at build time, copy only required runtime files, run as non-root, define a health check, and use exec-form startup with graceful shutdown support. Keep secrets out of image layers and build args.
4. Add `.dockerignore` for VCS metadata, local env files, caches, virtualenvs, patient/runtime data, logs, artifacts, and credentials while explicitly retaining required runtime assets.
5. Remove Neo4j/PostgreSQL host port publishing by default; support opt-in local development exposure via explicit Compose profiles/overrides or documented environment-controlled bindings. Preserve internal service DNS and volumes.
6. Replace startup-time `pip install` in Compose and `deploy.sh` with image build/run. Make local-only fallback behavior explicit; fail with an actionable error rather than silently claiming deployment when Docker is unavailable.
7. Add Compose config validation and build checks to CI. Use immutable image tags/digests for release evidence where feasible; do not push to a registry without explicit registry configuration and authorization.
8. **Acceptance:** clean image builds from locked dependencies; image runs non-root; startup performs no dependency installation; database ports are not published by default; existing volumes remain untouched.

## Workstream 4 — Health, timeout, and async behavior

**Likely files:** `api/main.py`, adapter modules under `engines/`, health/observability module, tests, Compose health checks.

1. Inventory every `async def` route and every adapter call it awaits; inspect whether network/database work is truly asynchronous or wraps blocking libraries.
2. Add tests with delayed/failing fake adapters to prove explicit timeouts, cancellation behavior, and that a slow blocking adapter does not starve unrelated requests.
3. Add separate liveness, readiness, and dependency-health endpoints. Liveness checks process responsiveness only; readiness verifies mandatory dependencies and reports degraded/unavailable dependencies without leaking DSNs or credentials. Keep optional external research sources from making liveness fail.
4. Use async clients where already supported; otherwise use bounded thread offload for synchronous I/O. Apply connect/read/total timeouts, bounded concurrency, and limited retries only for idempotent reads. Do not add retries to non-idempotent writes without durable idempotency.
5. Add structured logs and metrics only using libraries or mechanisms justified by the current stack; keep labels bounded and omit PHI, tokens, arbitrary queries, and high-cardinality identifiers.
6. **Acceptance:** health semantics match docs; timeout/cancellation/concurrency tests pass; no unbounded fan-out or retry loop is introduced.

## Workstream 5 — Biomedical evidence provenance and interoperability

**Likely files:** evidence ingestion/retrieval services and repositories, `api/interoperability_routes.py`, FHIR/OMOP modules, corresponding tests/docs.

1. Map each ingest/retrieve path and its persistence boundaries; add failing tests for duplicate/replayed input, validation errors, partial source failure, transaction rollback, and graph/database inconsistency.
2. Enforce deterministic source IDs, provenance timestamps/source references, idempotent writes, and explicit failure semantics without overwriting established provenance silently.
3. Verify FHIR R4/US Core and OMOP behavior against existing declared scope; use available validators/conformance tests where practical. Do not label the entire system conformant based solely on field mapping.
4. Add public-CI fixtures with synthetic/non-identifiable data only. Ensure audit logs exclude full records and sensitive clinical fields.
5. **Acceptance:** ingestion replay is deterministic; partial failure is visible and recoverable; provenance survives round trips; docs state exactly which profiles/resources are tested and which are not.

## Workstream 6 — IBM Quantum job lifecycle and result integrity

**Files:** `engines/ibm_quantum_job_ledger.py`, `migrations/004_quantum_job_ledger.sql` (preserve if already applied), IBM client adapter, new reconciler/worker module and tests, `docs/integrations/ibm-quantum-compute.md`, configuration docs.

1. Add mocked tests first for job status transitions, remote status mapping, rate-limited bounded polling, restart recovery, result retrieval only after completion, result content hashing, worker concurrency, and operator resolution of ambiguous submissions.
2. Implement a bounded reconciler for rows with known IBM job IDs and for `SUBMISSION_UNKNOWN`/stale `SUBMITTING` rows. Query remote history only when available; never infer a match without evidence and never auto-resubmit ambiguous jobs. Keep unmatched jobs unresolved for explicit operator action.
3. Add row-lock/lease or compare-and-set claims so concurrent workers cannot process the same row unsafely. Respect legal state transitions; add migrations only when schema changes are required and update migration tests.
4. Add bounded exponential backoff with jitter, overall deadline, request/job/result-size limits, a local rate limit no greater than IBM's documented contract, and safe cancellation/shutdown. Use configuration defaults that do not start the worker unless explicitly enabled.
5. Persist terminal state and result SHA-256; store result payloads only in an approved artifact store and keep PHI/raw circuit content out of routine logs and the ledger. Verify the hash after retrieval.
6. Add an operator-only command/API for resolving an ambiguous submission with a documented evidence record and audit entry. Do not allow a public unauthenticated endpoint to mutate job state.
7. Keep `TMRDS_IBM_QUANTUM_SUBMISSION_ENABLED` off by default; CI uses mocks only. Validate the pinned IBM API contract against official docs and distinguish regular-account/instance entitlement requirements.
8. **Acceptance:** tests prove no duplicate POST after timeout/restart; known remote jobs recover to terminal states; results are stored/hashed only after successful completion; no hardware job is submitted during CI.

## Workstream 7 — CI, security gates, release and operations evidence

**Files:** `.github/workflows/ci.yml`, `.github/workflows/security.yml`, security/config tests, `docs/operations/`, `docs/audits/`.

1. Add workflow tests/linting for YAML/Compose and run deterministic secret scan, compile, focused tests, full non-integration tests, migration tests, and container build. Keep least-privilege GitHub Actions permissions.
2. Pin third-party Actions to verified full commit SHAs where feasible, documenting update cadence. Add dependency vulnerability checks and SBOM/artifact generation only where tool availability and lockfile format support them; don't create misleading attestations without an actual build artifact and identity.
3. Split integration tests from unit tests and make external-service credentials opt-in. Upload sanitized test reports even on failure; never upload env dumps or raw logs with secrets.
4. Write operations docs for environment variables, local setup, migration status/upgrade, backup and restore, deployment/rollback limitations, health checks, IBM Quantum reconciliation/operator runbook, incident response, and evidence provenance.
5. Generate release evidence from actual run outputs: commit SHA, dependency lock hash, test reports, image digest (if built), SBOM (if generated), and unresolved blockers. Do not state that a deployment or regulatory attestation occurred if it did not.
6. **Acceptance:** CI runs all deterministic checks without production credentials; failing checks fail the workflow; unavailable Docker/DB/external-service checks are explicitly marked blocked rather than silently passed.

## Workstream 8 — Final verification and handoff

1. Re-fetch changed files and inspect the complete diff; scan for accidental secrets, unsafe defaults, unrelated churn, and documentation drift.
2. Run focused tests after each task, then the complete non-integration suite, compile checks, secret scan, migration tests, Compose validation, and image build where tools are available.
3. Run disposable PostgreSQL integration tests only if a local container/service is available and verify target DSN is explicitly test-only. Do not point tests at production or shared user data.
4. Inspect CI run conclusions and artifact contents. Fix regressions before declaring acceptance.
5. Publish a final audit matrix: finding, change/commit, test evidence, residual risk, and owner action required. Explicitly identify tests blocked by unavailable local Docker/DB or credentials.
6. Deploy only to a specifically authorized target after the image, config, backup/recovery point, health checks, and rollback path are verified. Current approval does not authorize an unrequested production target or paid infrastructure.

## Commit strategy

Create small commits by workstream in this order: baseline; API/security; migration runner; image/network; health/async; evidence/interoperability; quantum worker; CI/docs; final verification. Keep all changes on a dedicated branch or reviewable PR if branch/PR tooling is available. Do not commit directly to `main` during broad remediation unless the repository's established policy and explicit user approval authorize it; the user has authorized implementation, not an unsafe bypass of required review checks.

## Review focus

- Existing DB volumes and migration history are preserved.
- Error and log redaction covers exception messages, headers, upstream bodies, and clinical payloads.
- Authentication is fail-closed in production and tested negatively.
- Container startup is reproducible and ports are not overexposed.
- Async routes are bounded under slow/failing dependencies.
- Quantum jobs cannot be duplicated by retry/restart, and no live hardware job runs in CI.
- Claims of interoperability, security, build success, attestations, and deployment match actual evidence.


## Execution record and remaining gates

### Implemented and merged

The core workstreams were implemented and merged through pull request #2 (merge commit `d438df0fbf87fa60cbcffe1da96de6229941e2b6`):

- Stable, sanitized API dependency errors and request correlation.
- Explicit PostgreSQL migration runner with numeric ordering, SHA-256 checksums, advisory locking, and operator-reviewed baseline safeguards.
- Non-root API image, locked runtime/test dependencies, hardened Compose networking, local-only optional database ports, and a safer deploy helper.
- Liveness and readiness endpoints with tests.
- Production-default service identity enforcement and fail-closed configuration.
- Bounded IBM Quantum reconciliation, immutable content-addressed result artifacts, operator-controlled ambiguity resolution, append-only operator audit, and rate-limited submission safeguards. Remote quantum submission and reconciliation remain disabled by default.
- Read-only Postman smoke collection, migration and operations documentation, route/auth inventory generator, and CI container smoke test.

### Verified evidence

The latest checked runs for commit `ba00dbbbcb1929eeaf7c3c659e4a8508ffa00e91` completed successfully:

- [TMRDS CI](https://github.com/ATphobia22/TMRDS/actions/runs/38662711265): dependency lock check, Python compilation, Compose configuration validation, Docker image build, API container liveness smoke test, IBM Quantum adapter/ledger tests, and the non-integration suite.
- [TMRDS Security and Interoperability](https://github.com/ATphobia22/TMRDS/actions/runs/38662711229): deterministic secret scan, compilation, and non-integration tests.

### Remaining acceptance gates

- No production or staging deployment was performed: no target environment or deployment credentials were supplied.
- No live PostgreSQL/Neo4j migration was performed. Before an existing database is upgraded, take and verify a backup, inspect its full schema, and use the documented baseline procedure only after confirming the schema matches.
- No live IBM Quantum hardware job was submitted. Reconciliation requires explicit enablement and a configured account; ambiguous submissions remain unresolved until an operator supplies evidence.
- FHIR/US Core and OMOP compatibility are not certified by unit tests alone; validate against the target server/profile versions and representative de-identified fixtures.
- Review the generated route/auth inventory as an audit artifact. It classifies declared FastAPI dependencies only and is not proof of end-to-end authorization or infrastructure controls.
- Before production use, provision valid service-identity JWKS/issuer/audience values, strong unique secrets, TLS/reverse-proxy policy, backups/restore drills, alerting, retention controls, and environment-specific threat-model review.

This plan is an execution record, not a claim that all operational acceptance gates have been met.
