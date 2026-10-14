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
check instance access and backend visibility. These calls do not submit a job:

```python
from engines.ibm_quantum_compute import IBMQuantumComputeClient

with IBMQuantumComputeClient.from_environment() as client:
    print(client.get_instance_details())
    print(client.list_backends())
```

If either request returns HTTP 401, verify the API key and IAM token access. For
HTTP 403, verify the instance CRN, IAM role assignments, and plan entitlements.
Do not paste API keys, bearer tokens, or full credential-bearing environment
output into logs or issue reports.
