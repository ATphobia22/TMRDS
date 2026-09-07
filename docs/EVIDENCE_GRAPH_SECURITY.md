# TMRDS Evidence Graph Security Boundary

## Data classes

1. **Public biomedical evidence** — live public APIs and repositories such as CDC public data, ClinicalTrials.gov, openFDA, NLM Clinical Tables, PubMed, Europe PMC, and public OpenNeuro metadata.
2. **Credentialed/controlled evidence** — institutional, IRB/DUA/BAA-gated, or otherwise access-controlled sources. These are not bypassed or scraped.
3. **Patient data** — FHIR/HIE/EHR data. Patient-level identifiers are segregated from public research endpoints and are not emitted by the public evidence API.

## Controls

- PostgreSQL and Neo4j credentials are supplied through environment variables.
- No production password is committed to source control.
- Upstream API calls use bounded timeouts and schema validation.
- External source payloads are untrusted input.
- Assertions without provenance are rejected.
- Evidence history is append-oriented; updates create new observations/assertions.
- Graph projection is rebuildable and is not the authoritative evidence store.
- Research endpoints remain read-only and expose `research-advisory`, `human_authority_final`, and `not_samd` metadata.
- The graph does not autonomously diagnose, prescribe, or claim cures.

## Operational requirement

Set `POSTGRES_PASSWORD` and `NEO4J_PASSWORD` before starting Docker Compose. Never use a development password in a production deployment.
