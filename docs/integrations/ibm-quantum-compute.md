# IBM Quantum Compute Service integration

## Scope and API choice

TMRDS integrates with the **IBM Quantum Compute Service REST API**, not the separate Quantum System REST API intended for eligible on-premises / Direct Access deployments.

- API reference: https://quantum.cloud.ibm.com/docs/en/api/qiskit-runtime-rest
- REST API setup: https://quantum.cloud.ibm.com/docs/en/guides/cloud-setup-rest-api
- Pinned API version: `2026-04-15`
- Base URL: `https://quantum.cloud.ibm.com/api/v1/` (US) or `https://eu-de.quantum.cloud.ibm.com/api/v1/` (EU-DE)
- Auth: IBM IAM bearer token, `Service-CRN`, and `IBM-API-Version` headers.

## Configuration

Set `IBM_QUANTUM_API_KEY`, `IBM_QUANTUM_INSTANCE_CRN`, and optionally
`IBM_QUANTUM_REGION`, `IBM_QUANTUM_API_VERSION`, and
`IBM_QUANTUM_TIMEOUT_SECONDS` in a secret manager or local untracked environment.
Never commit real credentials.

## Safe use

The adapter in `engines/ibm_quantum_compute.py` is optional and performs no
network request until a client method is called. It does not silently fall back
to synthetic or simulated output. It supports backend discovery, backend status,
Sampler V2 job submission, job listing, status retrieval, and result retrieval.

**Never blindly retry job creation.** A transport failure after a POST leaves the
remote outcome uncertain and can create duplicate billable jobs. Persist an
application-side submission record before sending, record any returned IBM job
ID, and reconcile uncertain outcomes against the remote job list before deciding
whether a new submission is safe.

## TMRDS research safeguards

- Quantum results are experimental research evidence, not clinical advice,
  diagnosis, treatment selection, or validated biomedical conclusions.
- Preserve the original input hash, circuit text or its immutable artifact hash,
  backend, API version, job ID, shot count, timestamps, and result artifact hash.
- Label simulated, synthetic, and hardware execution distinctly. Never label a
  synthetic fallback as a hardware or quantum-chemistry result.
- Apply instance quotas and require explicit authorization before hardware jobs.
- Validate IBM response schemas against the pinned OpenAPI contract before
  promoting the adapter from integration branch to production.

## Smoke test

With credentials set in the environment:

```python
from engines.ibm_quantum_compute import IBMQuantumComputeClient

with IBMQuantumComputeClient.from_environment() as client:
    print(client.list_backends())
```

This read-only call validates authentication and backend visibility; it does not
submit a quantum workload.
