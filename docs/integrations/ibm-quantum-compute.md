# IBM Quantum Compute Service integration

## Scope and API choice

TMRDS integrates with the **IBM Quantum Compute Service REST API**, not the separate Quantum System REST API intended for eligible on-premises / Direct Access deployments.

- API reference: https://quantum.cloud.ibm.com/docs/en/api/qiskit-runtime-rest
- REST API setup: https://quantum.cloud.ibm.com/docs/en/guides/cloud-setup-rest-api
- Pinned API version: `2026-04-15`
- Base URL: `https://quantum.cloud.ibm.com/api/v1/` (US) or `https://eu-de.quantum.cloud.ibm.com/api/v1/` (EU-DE)
- Auth: IBM IAM bearer token, `Service-CRN`, and `IBM-API-Version` headers.

A regular IBM Quantum account is not by itself proof that a workload can run. You must have access to a **Quantum Compute instance** and its CRN, with IAM roles that permit the requested operations. The adapter does not create an instance, grant permissions, or bypass plan limits. Backend visibility and execution eligibility are determined by the instance, account roles, and current plan.

## Configuration

Set `IBM_QUANTUM_API_KEY` and `IBM_QUANTUM_INSTANCE_CRN`, and optionally
`IBM_QUANTUM_REGION`, `IBM_QUANTUM_API_VERSION`, and
`IBM_QUANTUM_TIMEOUT_SECONDS` in a secret manager or local untracked environment.
Never commit real credentials. `IBM_QUANTUM_REGION` supports `us` and `eu-de`
in the current adapter; select the region where the instance exists.

## Safe use

The adapter in `engines/ibm_quantum_compute.py` is optional and performs no
network request until a client method is called. It does not silently fall back
to synthetic or simulated output. It supports instance details, backend
discovery, backend status, Sampler V2 job submission, job listing, status
retrieval, and result retrieval.

**Never blindly retry job creation.** A transport failure after a POST leaves the
remote outcome uncertain and can create duplicate billable jobs. Persist an
application-side submission record before sending, record any returned IBM job
ID, and reconcile uncertain outcomes against the remote job list before deciding
whether a new submission is safe. IBM documents a limit of five job submissions
per minute per user; apply a lower or equal TMRDS-side rate limit.

Job tags are validated against the current API contract: at most 8 tags, each
no longer than 86 characters. The client uses bounded request timeouts and
refreshes IAM tokens before their expiry; it only retries a read-only GET once
after a 401 response.

## TMRDS research safeguards

- Quantum results are experimental research evidence, not clinical advice,
  diagnosis, treatment selection, or validated biomedical conclusions.
- Preserve the original input hash, circuit text or its immutable artifact hash,
  backend, API version, job ID, shot count, timestamps, and result artifact hash.
- Label simulated, synthetic, and hardware execution distinctly. Never label a
  synthetic fallback as a hardware or quantum-chemistry result.
- Apply instance quotas and require explicit authorization before hardware jobs.
- Validate IBM response schemas against the pinned OpenAPI contract and run
  automated tests before enabling production workloads.

## Read-only smoke test

With credentials and the instance CRN configured in the environment, first
check instance access and backend visibility. The script requires an explicit
opt-in flag, prints only response structure (not payload values), and never
submits a job:

```bash
IBM_QUANTUM_LIVE_SMOKE=1 python scripts/ibm_quantum_readonly_smoke.py
```

The smoke test is intentionally not run automatically in CI because CI should
not require production IBM credentials. Run it manually in a trusted environment
with a least-privilege API key and an authorized instance.

If either request returns HTTP 401, verify the API key and IAM token access. For
HTTP 403, verify the instance CRN, IAM role assignments, and plan entitlements.
Do not paste API keys, bearer tokens, or full credential-bearing environment
output into logs or issue reports.


## Submission durability and reconciliation

The REST adapter is a transport client, not a durable scheduler. Before wiring
it into an automated TMRDS pipeline, implement a persistent job ledger in the
application's existing database (do not keep authoritative job state only in
memory). Each record should include an application-generated submission ID,
idempotency/correlation key, canonical input hash, immutable circuit/artifact
reference, backend, shots, API version, creation timestamp, submission state,
IBM job ID (when known), and terminal status/result artifact hash.

Recommended state machine:

1. Persist `PREPARED` and the immutable input metadata transactionally before
   making a network request.
2. Transition to `SUBMITTING`, then call `submit_sampler` exactly once.
3. On a confirmed response, persist the IBM job ID and transition to
   `SUBMITTED`.
4. On a timeout or transport failure during POST, transition to
   `SUBMISSION_UNKNOWN`; **do not automatically submit again**.
5. Reconcile uncertain submissions with bounded, rate-limited job-list queries
   and available tags/time/backend metadata. If a match cannot be established,
   keep the record unresolved and require an explicit operator decision rather
   than risking duplicate billable execution.
6. Poll job status with bounded exponential backoff and jitter; persist every
   state transition. Fetch results only after the API reports a result-ready
   state, then store immutable results and a content hash.
7. Make the reconciler restart-safe and safe for concurrent workers using
   database uniqueness constraints, leases/row locks, and compare-and-set state
   transitions. Redact credentials and avoid storing raw sensitive payloads in
   routine logs.

Do not assume the IBM service supports idempotency keys unless the current API
contract explicitly documents that behavior. A local correlation key helps
reconciliation but does not make remote job creation idempotent.


## Durable ledger implementation

The initial PostgreSQL ledger migration is
`migrations/004_quantum_job_ledger.sql`; the implementation is
`engines/ibm_quantum_job_ledger.py`. It uses the existing
`TMRDS_DATABASE_URL` PostgreSQL configuration rather than creating a second
persistence system.

Hardware submission is fail-closed. Both conditions are required:
- `TMRDS_IBM_QUANTUM_SUBMISSION_ENABLED=true` in the trusted runtime.
- The caller passes `explicitly_authorized=True` after application-level
  authorization and budget/consent policy checks.

The service persists a `PREPARED` record and atomically claims
`SUBMITTING` before issuing a single submission request. Ambiguous network
failures become `SUBMISSION_UNKNOWN`, not an automatic retry. Reusing an
idempotency key for a different workload is rejected. Local idempotency does
not imply remote IBM idempotency.

The ledger records an input SHA-256 and immutable artifact URI; callers are
responsible for placing the circuit artifact in an approved immutable store.
Never put patient identifiers or protected health information in the idempotency
key, artifact URI, backend tag, or metadata. Do not persist API keys, bearer
tokens, or raw circuit source in this ledger. Apply your retention and access
controls to the ledger because backend, timing, and workload metadata can still
be sensitive.

The ledger's reconciliation query surfaces `SUBMISSION_UNKNOWN`,
`SUBMITTING`, `SUBMITTED`, and `RUNNING` records. An operator/reconciler must
match uncertain records to IBM job history before resolving them; the query
does not guess a match or resubmit automatically. Terminal job polling, result
retrieval, cancellation, automated quota enforcement, and a background worker
are intentionally not claimed as implemented by this submission-only layer.

Run local tests with:

```bash
python -m pytest -q tests/test_ibm_quantum_compute.py tests/test_ibm_quantum_job_ledger.py
```

For an existing PostgreSQL volume, apply `migrations/004_quantum_job_ledger.sql`
through the repository's controlled migration process. Docker's
`/docker-entrypoint-initdb.d` scripts only initialize a fresh database volume;
restarting an already initialized container will not apply this migration.
