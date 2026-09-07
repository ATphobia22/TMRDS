# TMRDS Continuous Authoritative Ingestion, Evidence, and Spatial Data Plane

**Date:** 2026-09-07
**Repository:** `ATphobia22/TMRDS`
**Base:** `main`

## Purpose

Add a durable ingestion and data-product plane for authoritative hydrologic, meteorological, floodplain, elevation, geospatial, and infrastructure sources while preserving immutable provenance and preventing TMRDS from acquiring governmental or professional regulatory authority.

## Authoritative source classes

Initial governed source registry entries may include USGS NWIS, NOAA/NWS, FEMA NFHL, Indiana Department of Natural Resources floodplain/BAFL resources, Indiana GIS/3DEP, and USACE National Levee Database. Future sources require explicit registry approval.

A source can be authoritative for a published observation or dataset without granting TMRDS legal, permitting, engineering, or regulatory authority.

## Ingestion contract

Every adapter emits a provenance envelope containing source identifier/version, canonical source URI, retrieval timestamp, upstream observation/publication timestamp when available, request/correlation ID, payload hash, schema version, CRS and vertical datum when applicable, freshness policy identifier, validation state, and provenance chain.

The pipeline is:

`authoritative source -> bounded adapter -> validation/quarantine -> immutable raw artifact -> evidence ledger -> normalized product -> PostGIS/object storage consumers`.

Malformed, ambiguous, unauthorized, or contract-invalid payloads are quarantined and cannot enter operational state. Reprocessing is deterministic and idempotent.

## Evidence semantics

The Evidence Ledger is append-only. A correction creates a new event referencing the superseded event; history is never overwritten. Evidence existence does not constitute a regulatory determination.

## Freshness

Freshness is source/product specific and uses `EXPECTED`, `FRESH`, `AGING`, `STALE`, and `UNAVAILABLE`. Policies specify expected cadence and transition thresholds. The API exposes observation age, expected cadence, last successful retrieval, last-known-good state, source health, freshness, and product class. `STALE` data must never be labeled live.

## Spatial integrity

Spatial products retain CRS, vertical datum where applicable, acquisition/publication date, retrieval time, source version/product identifier, geometry/payload hash, transformation history, and published accuracy/quality metadata. Reprojection or datum conversion requires an explicit transformation record; silent conversion is prohibited.

## Storage

PostGIS stores current normalized spatial state, indexes, version metadata, and spatial relationships. Object storage stores immutable raw payloads and large artifacts such as GeoTIFF/COG, GeoJSON, Parquet, and evidence envelopes. The Evidence Ledger stores immutable provenance, content hashes, lineage, validation, and supersession metadata.

The application accesses storage through repository/object-store interfaces so deployment backends can change without changing domain contracts.

## Reliability

The ingestion scheduler uses bounded concurrency, retry with backoff, circuit breaking, rate limiting, idempotency keys, content/observation deduplication, last-known-good state, quarantine, dead-letter records, source-health telemetry, checkpoints, and replay. Failures never fabricate continuity.

## Regulatory-authority firewall

The following are distinct capabilities:

`AUTHORITATIVE_SOURCE != REGULATORY_AUTHORITY != TSM_DERIVED_PRODUCT != ENGINEERING_DETERMINATION`.

Ingestion, storage, graph, simulation, visualization, and optimization components cannot emit permits, LOMAs, CLOMR/LOMR determinations, No-Rise determinations, or equivalent governmental/professional decisions. Any future determination workflow must cross an explicit human-governance boundary and record the responsible authority.

## Security

Credentials remain environment-managed. Raw source payloads and provenance records must not contain secrets. Public-source ingestion must not ingest patient-level PHI. Requests and payloads are bounded; external calls use timeouts; SQL and object-store keys are parameterized or generated from validated identifiers.

## Testing and acceptance

Tests cover provenance validation, idempotency, deduplication, quarantine/replay, freshness transitions, source-specific policies, CRS/datum validation, spatial synchronization, storage failure/retry, last-known-good behavior, API uncertainty/freshness metadata, and regulatory-boundary enforcement.

Acceptance requires deterministic core tests to pass, migration/schema checks to pass where services are available, and external upstream failures to be reported as such rather than hidden behind mocks.