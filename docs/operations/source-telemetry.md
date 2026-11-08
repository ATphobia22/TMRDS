# Source telemetry and ingestion review

`GET /api/v1/sources/catalog` reports process-local observations. It does not probe
upstreams on reads or infer operational status from a static source listing.
`POST /api/v1/sources/{provider}/probe` explicitly requests a bounded check, uses
existing service-identity policy and rate limiting, and never submits compute.
Production requires the existing service token. Optional API-key policy also applies.

Tamarind uses only the documented `https://app.tamarind.bio/api/tools` endpoint
with `TAMARIND_API_KEY` in `x-api-key`, redirects disabled and no automatic retries.
Patsnap returns `not_configured`: no verified free balance/health endpoint is
configured. A missing balance field must never become an invented zero balance.
No pasted key is installed, committed or used. If any pasted values were actual
credentials, revoke/rotate them at their provider before using replacements.

The schema is in `config/source_catalog.json` (JSON Schema generated from the
same Pydantic model as the API). The schema is a contract, not a populated config
file or proof of connectivity. Added `not_checked`, `not_configured`, `stale`
and `circuit_open` states preserve unknowns. Observations older than five minutes
are stale. Three failures open a 60-second circuit; the next explicit request
can retry after cooldown. Observations reset on process restart and are not
shared across workers. No durable PostgreSQL telemetry or production readiness
is claimed. Response bodies, exception text and credentials are not returned.

## Why the pasted ingestion script was not installed

- Two incomplete `if status_code in:` statements are syntax errors.
- A website HTTP 200 does not validate an account, API entitlement or credit balance.
  Provider-specific balance fields/error codes need a documented API contract.
- Replacing three Patient-group tags leaves identifiers in other groups,
  sequences, private fields and pixels. It also assigns invalid date content.
  The modified dataset is never saved by the proposed function.
- Pixel-only hashing excludes the DICOM metadata being represented; use an
  artifact checksum with explicit scope. SHA-256 is not a digital signature.
- FHIR R4 Attachment.hash is base64 SHA-1, not hex SHA-256. It is an integrity
  field, not a signature. Keep a separate SHA-256 manifest and use an appropriately
  designed signing service for provenance signatures.
- Generic anonymous patient references, hard-coded report status and unverified
  LOINC labels do not establish FHIR/profile conformance or clinical authority.

The synthetic imaging tool remains the ingestion development boundary until
validated de-identification, institutional authorization, terminology/profile
validation and archive/viewer runtime evidence are supplied.

Primary references:
- https://app.tamarind.bio/api-docs/overview
- https://open.patsnap.com/devportal/api-reference
- https://hl7.org/fhir/R4/datatypes-definitions.html#Attachment.hash
- https://pydicom.github.io/pydicom/stable/auto_examples/metadata_processing/plot_anonymize.html
