# HAPI FHIR Public Test Server — synthetic-only opt-in

The HAPI project runs a public FHIR R4 test server at
`https://hapi.fhir.org/baseR4`. It is a shared, unauthenticated endpoint
holding synthetic/test data only. It offers **no SLA** and must **never**
receive PHI or real patient identifiers.

TMRDS talks to it in exactly two ways, both honest about what they do and
do not do.

## 1. Metadata probe (no PHI, no resource fetch)

`engines/hapi_test_server.py` fetches only the server's CapabilityStatement
(`GET /baseR4/metadata`) and verifies it is the expected HAPI test server
(FHIR 4.0.1, software "HAPI FHIR Server"). It fetches no resources and no
patient data.

Verified live 2026-11-08: HTTP 200, `CapabilityStatement`, `fhirVersion:
4.0.1`, software `HAPI FHIR Server 8.13.10-SNAPSHOT/6bd250944e/2026-09-25`,
`status: active`.

Use it to confirm the test server is what it claims before any fetch is
attempted:

```python
from engines.hapi_test_server import verify_test_server

identity = await verify_test_server()  # raises HapiTestServerUnavailable otherwise
```

## 2. Resource fetch (gated synthetic connector, guards intact)

Resource reads still go through `engines/synthetic_fhir_connector.py`
with **every guard intact** — nothing in this integration relaxes them:

- Opt-in env flags (`TMRDS_SYNTHETIC_WORKBENCH_ENABLED=true` and
  `TMRDS_SYNTHETIC_FHIR_FETCH_ENABLED=true`), disabled in production.
- Explicitly allowlisted HTTPS host (`TMRDS_SYNTHETIC_FHIR_ALLOWED_HOSTS`).
- Bearer token required by the connector config.
- `synthetic-*` IDs only; `Observation`/`ImagingStudy` only; no `Patient`
  resource; 64 KB response cap; no redirects.

Example operator configuration:

```text
TMRDS_ENV=development
TMRDS_SYNTHETIC_WORKBENCH_ENABLED=true
TMRDS_SYNTHETIC_FHIR_FETCH_ENABLED=true
TMRDS_SYNTHETIC_FHIR_BASE_URL=https://hapi.fhir.org/baseR4
TMRDS_SYNTHETIC_FHIR_ALLOWED_HOSTS=hapi.fhir.org
TMRDS_SYNTHETIC_FHIR_TOKEN=placeholder-token
```

**Token warning:** the public test server ignores `Authorization` headers.
The token value above is a placeholder that satisfies the connector's
config requirement. **Never send a real credential to a public server.**

**What works and what does not (verified 2026-11-08):** the server holds
107,211 `Observation` resources — and **zero** resources with a
`synthetic-*` ID. A live fetch against the public server therefore fails
honestly today (`SyntheticFHIRUnavailable`: the source did not return a
resource), because there is nothing synthetic-ID'd to fetch. That is the
correct outcome, not a bug. **Do not create resources on the shared public
server to work around it.** A fetch succeeds only against a FHIR server
where `synthetic-*` resources actually exist (for example, an operator's
own HAPI deployment seeded with synthetic fixtures).

## What this is not

- Not a federated evidence source — a FHIR server is clinical-data
  infrastructure, not literature or genomic evidence, so it is not wired
  into federated search and is not counted among the live sources.
- Not a live EHR connection. `live_patient_exchange: false` and
  `external_clinical_services_connected: false` are unchanged.
- Not a validation of the test server's data: test data is test data, and
  anything fetched is labeled synthetic and must not be treated as
  clinical evidence.
