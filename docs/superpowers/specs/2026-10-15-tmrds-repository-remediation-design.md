# TMRDS Repository Remediation and Release Readiness — Design Specification

**Date:** 2026-10-15  
**Repository:** ATphobia22/TMRDS  
**Target branch:** main  
**Status:** Core remediation merged; 2026-10-17 release-gate follow-up is under review. Production release remains conditional on current CI/security evidence and environment-specific verification.

## 1. Goals

Improve security, data integrity, operational reliability, reproducible deployment, and verifiability while preserving existing platform boundaries and data.

- Inventory source, configuration, migrations, tests, workflows, dependencies, and documentation.
- Sanitize API errors and add safe structured diagnostics with request IDs.
- Make database migrations ordered, checksummed, concurrency-safe, and compatible with existing persistent volumes.
- Build a reproducible application image with pinned dependencies and reduced privileges.
- Restrict host/network exposure and separate liveness, readiness, and dependency health.
- Audit async adapters for blocking I/O, explicit timeouts, bounded retries, cancellation, and concurrency.
- Preserve evidence provenance and computation artifact integrity.
- Complete IBM Quantum reconciliation, restart recovery, bounded polling, operator handling of ambiguous submissions, and result verification.
- Add test-backed CI gates, security checks, operational docs, and evidence-based release criteria.

## 2. Non-goals and safety boundaries

- No autonomous diagnosis or treatment decisions; no unsupported medical-device or regulatory-compliance claims.
- No paid cloud provisioning, production deployment, destructive database operations, or live quantum hardware submissions.
- No migration to AWS by default. Keep FastAPI/Python, PostgreSQL/pgvector, Neo4j, and Docker Compose unless evidence justifies a separately reviewed change.
- No real secrets in source, images, test fixtures, or logs.
- Do not automatically retry an ambiguous quantum submission.
- Preserve existing persistent data. Do not drop or truncate tables as part of routine remediation.
- Do not claim a test passed unless it was actually executed and its result inspected.

## 3. Initial source-review findings

Initial inspection of the live GitHub tree and selected files identified these risks for confirmation and correction:
1. Some API handlers include raw exception text in client-facing errors.
2. Compose mounts migrations into PostgreSQL's initialization directory; this does not apply new scripts to an already initialized volume.
3. The API installs dependencies during container startup from broad minimum-version requirements.
4. PostgreSQL and Neo4j host-port exposure should be restricted to intended consumers.
5. A configured-state health response does not prove dependencies are operational.
6. Async route handlers call adapters whose blocking behavior, timeout bounds, and cancellation need file-by-file verification.
7. The quantum ledger needs verified reconciliation, restart recovery, bounded result retrieval, and operator-safe ambiguity handling.
8. Identity, provenance, interoperability, and security controls need route coverage mapping and negative-case tests.

These are source-review findings, not a claim that every issue has been reproduced or that a complete security assessment has already passed.

## 4. Architecture and requirements

### API errors and observability
Return stable, sanitized error codes and a correlation ID. Never return raw exception strings, SQL, credentials, upstream response bodies, or filesystem details. Keep diagnostic stack traces server-side and redact secrets and sensitive payloads. Test both expected response contracts and absence of exception contents.

### Identity and security
Classify every route as public, authenticated, or privileged. Sensitive mutation routes fail closed when service identity is required. Verify issuer, audience, signature/algorithm, expiry, and key configuration against the existing implementation. Review input validation, request-size limits, outbound URL/SSRF boundaries, rate limiting, CORS, audit integrity, and secret handling. Do not introduce permissive production defaults.

### Database migrations
Add a versioned migration runner and schema-version/checksum ledger. Serialize execution with a PostgreSQL advisory lock. Apply each migration transactionally where supported; fail on checksum drift or unknown schema state. Preserve existing SQL migrations and data. Test fresh databases, initialized volumes missing later migrations, concurrent startup, failed migration rollback, and checksum mismatch. Document backups, restore, forward-fix, and tested rollback limitations.

### Build and deployment
Build an application image; do not install dependencies at container startup. Resolve and pin compatible dependency versions in an auditable lock/constraints file. Run as non-root where compatible; use a Docker build context exclusion file, health checks, and graceful shutdown. Keep databases on the internal Compose network. Publish only the API port required by the deployment; database/admin host exposure requires explicit opt-in. Never bake secrets into images or commits.

### Health and async reliability
Separate process liveness, readiness to serve, and dependency health. Liveness must not depend on optional public APIs. Set explicit connect/read/total timeouts; bound retries and concurrency; do not retry non-idempotent writes without idempotency guarantees. Use async clients or bounded thread offload for unavoidable synchronous I/O. Test timeouts, upstream failures, cancellation, concurrency, and degraded readiness.

### Evidence and biomedical interoperability
Keep research output advisory and provenance-bearing. Test idempotent ingestion, validation failures, duplicates, transaction boundaries, partial failure, replay, and graph/database consistency. Treat FHIR R4/US Core and OMOP as scoped implementation claims; run validators/conformance tests before asserting compatibility. Never use real patient data in public CI fixtures.

### IBM Quantum lifecycle
Keep hardware submission opt-in and disabled by default. Never blindly resubmit ambiguous submissions. Add bounded reconciliation for known remote job IDs, durable state transitions, restart recovery, operator-controlled ambiguity resolution, immutable result metadata/content hashes, and limits for polling frequency, runtime, job count, and result size. Keep read-only smoke tests separate from hardware submission; runtime secrets only. CI must not submit hardware jobs.

### CI and release evidence
Add or strengthen unit, integration, security, dependency, configuration, migration, and artifact checks. External-service tests must be explicitly marked and require configuration rather than silently relying on live services or secrets. Document environment variables, local build, deployment, migration, health endpoints, backup/restore, and incident response. Use small reviewable commits and inspect final diffs and workflow runs.

## 5. Environment contract

- Local/test environments work without production credentials and never submit quantum jobs by default.
- Production startup fails closed when required security configuration is missing or invalid.
- Example environment files contain names and safe dummy values only.
- Existing persistent volumes are never deleted or reinitialized as a routine deployment step.
- Schema changes require a backup or documented recovery point.
- A repository commit is not equivalent to a production deployment.

## 6. Acceptance criteria

1. Client-facing errors contain no raw exception, database, token, or upstream-body details.
2. Sensitive routes have tests for missing, invalid, expired, and wrong-audience credentials.
3. Migration tests cover fresh/existing volumes, concurrent startup, failure, and checksum drift without destructive side effects.
4. The application image builds from pinned dependencies, runs with reduced privileges, and does not install packages at startup.
5. Database/admin ports are not unintentionally published.
6. Health endpoints behave as documented under healthy and degraded dependencies.
7. Outbound work has bounded timeouts/concurrency; blocking adapters do not stall unrelated requests.
8. Quantum submission remains disabled by default; ambiguous jobs are not automatically retried; recovery paths are tested with mocked remote behavior.
9. Evidence provenance and ingestion replay/partial-failure behavior are tested.
10. CI passes all checks that can run in this environment; unavailable external checks are identified explicitly.
11. Critical/high security findings are fixed or recorded as release blockers with mitigation.
12. Deployment, environment, migration, backup/restore, and operations docs match tested behavior.
13. Final reporting links actual commits and workflow runs and separates verified facts, skips, and external prerequisites.

## 7. Workstream boundaries

Create a test-first task plan with independent workstreams: (1) baseline and coverage map, (2) API/security, (3) migrations/persistence, (4) build/deployment, (5) async reliability/health, (6) evidence/interoperability, (7) quantum lifecycle, and (8) CI/release documentation. Each workstream ends with focused verification and reviewable commits before dependent work proceeds.

The repository currently reports push access, but branch protections and CI outcomes must be respected. If safe direct delivery to main is blocked, use a branch/PR or report the exact blocker.

## 8. Owner review

This specification defines intended outcomes and architectural constraints. It does not authorize destructive data operations, paid infrastructure, production credential access, or live quantum submissions. Review this document before the detailed implementation plan is created.
