# TMRDS Continuous Authoritative Ingestion and Spatial Data Plane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement durable authoritative-source ingestion, immutable evidence capture, source-specific freshness, spatial synchronization, storage abstractions, operational APIs, and governance safeguards.

**Architecture:** Bounded source adapters feed validation/quarantine, immutable raw artifacts, and the Evidence Ledger before normalized operational products. PostGIS is the queryable spatial state; object storage is the immutable payload/artifact layer; the Evidence Ledger is the immutable provenance layer. All determination authority remains outside ingestion and derived-data components.

**Tech Stack:** Python 3.11, FastAPI, Pydantic 2, httpx, PostgreSQL/asyncpg, PostGIS, existing Evidence Ledger, pytest/pytest-asyncio, Docker Compose, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-07-authoritative-ingestion-spatial-data-plane-design.md`

## Global Constraints

- Every accepted observation has source/version/URI/retrieval time/upstream time/request ID/hash/schema/provenance metadata.
- Invalid or ambiguous payloads enter quarantine and never silently enter operational state.
- Evidence Ledger history is append-only; corrections create superseding events.
- Freshness is source/product specific and uses EXPECTED, FRESH, AGING, STALE, UNAVAILABLE.
- STALE data is never represented as live.
- Spatial CRS and vertical datum transformations are explicit and recorded.
- PostGIS is operational spatial state; object storage is immutable payload/artifact storage; the Evidence Ledger is immutable provenance.
- Ingestion failure never fabricates continuity.
- AUTHORITATIVE_SOURCE, REGULATORY_AUTHORITY, TSM_DERIVED_PRODUCT, and ENGINEERING_DETERMINATION remain distinct capabilities.
- No TSM component may emit a governmental or professional regulatory determination.
- Secrets remain outside source code, fixtures, logs, and provenance payloads.
- Public-source ingestion must not ingest patient-level PHI.
- Core CI remains deterministic and independent of optional scientific dependencies.

---

### Task 1: Source and provenance contracts

**Files:**
- Create: `engines/authoritative_ingestion_models.py`
- Create: `engines/source_registry.py`
- Test: `tests/test_authoritative_ingestion_models.py`
- Test: `tests/test_source_registry.py`

- [ ] Write failing tests for source IDs, product classes, provenance envelopes, hashes, timestamps, and authority classifications.
- [ ] Implement immutable Pydantic models with strict identifiers and explicit source/product authority fields.
- [ ] Register USGS NWIS, NOAA/NWS, FEMA NFHL, Indiana DNR BAFL/floodplain resources, Indiana GIS/3DEP, and USACE NLD as typed sources without claiming TSM regulatory authority.
- [ ] Run focused tests and commit `feat: add authoritative ingestion contracts`.

### Task 2: Freshness policy engine

**Files:**
- Create: `engines/source_freshness.py`
- Test: `tests/test_source_freshness.py`

- [ ] Write tests for cadence-aware EXPECTED/FRESH/AGING/STALE/UNAVAILABLE transitions.
- [ ] Implement immutable `FreshnessPolicy` keyed by source and product type.
- [ ] Implement deterministic transition evaluation using upstream observation/publication time and retrieval time.
- [ ] Add last-known-good semantics without presenting stale values as current.
- [ ] Run focused tests and commit `feat: add source-specific freshness engine`.

### Task 3: Quarantine, idempotency, and evidence ingestion

**Files:**
- Create: `engines/authoritative_ingestion.py`
- Modify: `engines/evidence_ledger.py`
- Create: `tests/test_authoritative_ingestion.py`

- [ ] Write tests for duplicate payloads, duplicate observation identity, malformed payloads, ambiguous timestamps, failed validation, and supersession.
- [ ] Implement canonical JSON hashing and idempotency keys.
- [ ] Route invalid/ambiguous records to quarantine with machine-readable reasons.
- [ ] Append accepted provenance to the Evidence Ledger and create superseding events rather than overwriting prior history.
- [ ] Run focused tests and commit `feat: add durable governed ingestion pipeline`.

### Task 4: Durable checkpoints and replay

**Files:**
- Create: `migrations/003_authoritative_ingestion.sql`
- Create: `engines/ingestion_repository.py`
- Test: `tests/test_ingestion_repository.py`

- [ ] Add tables for source products, ingestion runs, checkpoints, observations, quarantine records, dead-letter records, and source health.
- [ ] Add uniqueness constraints for idempotency and observation identity plus indexes for replay/status queries.
- [ ] Implement parameterized asyncpg repository operations for checkpoints, accepted observations, quarantine, dead-letter, and replay state.
- [ ] Add tests for transaction rollback, replay, duplicate prevention, and last-known-good lookup.
- [ ] Run repository tests and commit `feat: persist ingestion checkpoints and quarantine`.

### Task 5: Immutable object-storage abstraction

**Files:**
- Create: `engines/object_storage.py`
- Test: `tests/test_object_storage.py`
- Modify: `docker-compose.yml` only if an object-storage service already fits the repository deployment model

- [ ] Define a small object-store interface for immutable `put`, metadata lookup, and retrieval by content address.
- [ ] Reject overwrite of an existing content address with different bytes.
- [ ] Keep object keys derived from validated content hashes rather than user-controlled paths.
- [ ] Add an in-process test backend only for deterministic unit tests; production backends remain configuration-driven.
- [ ] Run focused tests and commit `feat: add immutable object storage boundary`.

### Task 6: Spatial synchronization contracts and PostGIS repository

**Files:**
- Create: `engines/spatial_sync.py`
- Create: `engines/postgis_repository.py`
- Create: `tests/test_spatial_sync.py`
- Create: `tests/integration/test_postgis_spatial_sync.py`

- [ ] Write tests requiring CRS, vertical datum when applicable, source version, acquisition/publication time, retrieval time, geometry hash, and transformation history.
- [ ] Reject missing or conflicting CRS/datum metadata and prohibit implicit reprojection.
- [ ] Implement explicit transformation records and deterministic geometry hashing.
- [ ] Add PostGIS tables/indexes for synchronized spatial products and versions using the next migration after `003_authoritative_ingestion.sql`.
- [ ] Implement parameterized spatial upsert/query/intersection methods.
- [ ] Run unit tests and PostGIS integration tests when PostGIS is available; record unavailable-service failures explicitly.
- [ ] Commit `feat: add governed PostGIS spatial synchronization`.

### Task 7: Live source adapters

**Files:**
- Create: `engines/authoritative_source_adapters.py`
- Test: `tests/integration/test_authoritative_source_adapters.py`

- [ ] Define a bounded adapter protocol with timeout, pagination/limit, request ID, and provenance output.
- [ ] Implement live USGS NWIS and NOAA/NWS adapters first, preserving raw source identifiers and timestamps.
- [ ] Add FEMA NFHL, Indiana DNR/Indiana GIS/3DEP, and USACE NLD adapters behind the same contract where their current public interfaces are available.
- [ ] Validate payloads before normalization; no mocks may be used to conceal upstream schema failures.
- [ ] Add rate limiting, retry/backoff, and circuit-breaker state at the adapter boundary.
- [ ] Run live integration tests where network access is available and document upstream outages/schema drift without fabricating PASS.
- [ ] Commit `feat: add authoritative hydrology and spatial source adapters`.

### Task 8: Normalized products and API

**Files:**
- Create: `engines/normalized_data_products.py`
- Create: `api/authoritative_ingestion_routes.py`
- Create: `tests/test_authoritative_ingestion_api.py`
- Modify: `api/main.py`

- [ ] Define observation, source-health, freshness, spatial-product, and provenance response schemas.
- [ ] Implement bounded read endpoints for source status, observations, freshness, provenance, quarantine summaries, and spatial products.
- [ ] Ensure every response distinguishes observed/source-backed, derived, forecast, and static products and exposes freshness metadata.
- [ ] Ensure responses expose advisory/governance metadata and cannot emit regulatory determinations.
- [ ] Register the router without eager optional dependency imports.
- [ ] Run focused API tests and commit `feat: expose governed authoritative data products`.

### Task 9: Reliability and observability

**Files:**
- Create: `engines/ingestion_scheduler.py`
- Create: `engines/ingestion_observability.py`
- Test: `tests/test_ingestion_reliability.py`

- [ ] Test bounded concurrency, retries, backoff, circuit breaking, idempotency, checkpoint recovery, and dead-letter behavior.
- [ ] Implement structured source-health metrics without recording secrets or patient identifiers.
- [ ] Implement scheduler leases/checkpoints so a crashed worker resumes without duplicate operational publication.
- [ ] Expose source latency, success/failure, deduplication, quarantine, freshness, and projection lag metrics.
- [ ] Run focused reliability tests and commit `feat: add ingestion reliability and observability`.

### Task 10: Regulatory firewall and security hardening

**Files:**
- Create: `engines/authority_firewall.py`
- Create: `tests/test_authority_firewall.py`
- Create: `tests/test_authoritative_ingestion_security.py`
- Create: `docs/AUTHORITATIVE_INGESTION_SECURITY.md`

- [ ] Write tests proving ingestion/storage APIs cannot emit permit, LOMA, CLOMR/LOMR, No-Rise, or equivalent determination objects.
- [ ] Implement explicit capability checks separating source authority from regulatory and engineering determination authority.
- [ ] Reject secrets and patient identifiers from public-source provenance envelopes.
- [ ] Enforce request/payload size bounds, external timeouts, and environment-driven credentials.
- [ ] Run security tests and commit `security: enforce authoritative ingestion boundaries`.

### Task 11: Operational documentation and UI

**Files:**
- Create: `docs/AUTHORITATIVE_INGESTION_OPERATIONS.md`
- Create: `docs/AUTHORITATIVE_DATA_DICTIONARY.md`
- Modify: `README.md`
- Modify: existing React source-health UI identified during implementation

- [ ] Document source registry, freshness policies, quarantine/replay, storage layers, CRS/datum rules, and failure modes.
- [ ] Document the distinction between source authority and regulatory authority prominently.
- [ ] Add source-health/freshness visualization showing age, cadence, last success, last-known-good, source health, and product class.
- [ ] Add explicit stale/unavailable states and uncertainty labels; never show stale records as live.
- [ ] Run frontend tests/build and commit `docs: document authoritative ingestion operations`.

### Task 12: Full verification and CI

**Files:**
- Modify: `.github/workflows/*` only when required to add deterministic ingestion gates
- Create: `tests/integration/test_authoritative_ingestion_e2e.py`
- Modify: `README.md`

- [ ] Run Python syntax/static validation over changed modules.
- [ ] Run deterministic core tests with external integration tests excluded.
- [ ] Start PostgreSQL/PostGIS and apply migrations when Docker is available.
- [ ] Run ingestion repository, spatial, and replay integration tests.
- [ ] Run live source integration tests and record actual upstream results.
- [ ] Start FastAPI and exercise health/source/freshness/observation/spatial/provenance endpoints.
- [ ] Verify duplicate payloads do not duplicate evidence, corrections supersede rather than overwrite, stale data is labeled correctly, CRS/datum transformations are explicit, and authority firewall tests pass.
- [ ] Update verification documentation with actual results; never report unexecuted checks as passing.
- [ ] Commit `test: finalize authoritative ingestion and spatial data plane`.

## Final acceptance

The implementation is complete only when accepted observations are provenance-bearing and idempotent, invalid records are quarantined, freshness is source-specific, spatial metadata and transformations are explicit, PostGIS/object storage/Evidence Ledger boundaries are enforced, replay and last-known-good behavior work, APIs expose uncertainty and freshness, and no ingestion or derived-data component can claim regulatory authority.