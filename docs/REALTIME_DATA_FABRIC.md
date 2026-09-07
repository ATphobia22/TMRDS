# TMRDS Real-World Real-Time Data Fabric

## Purpose

TMRDS now has a provenance-first real-world data fabric for authoritative public feeds. The fabric is an ingestion and synchronization plane; it is not a clinical decision engine and does not convert upstream observations into biomedical assertions automatically.

## Flow

```text
Authoritative source
      |
      v
Bounded HTTPS adapter
      |
      v
Payload-size + schema boundary
      |
      +---- invalid ---> quarantine
      |
      v
Canonical observation + SHA-256 identity
      |
      v
PostgreSQL append-only observation ledger
      |
      v
TMRDS downstream research/data products
```

## Current authoritative public catalog

| Source | Provider | Data | Mode |
|---|---|---|---|
| `usgs_water` | USGS | Water Services instantaneous values | real-time/source-defined |
| `usgs_earthquakes` | USGS | Earthquake GeoJSON | hourly feed |
| `noaa_weather` | NOAA/NWS | Weather point metadata | source-defined |
| `nws_alerts` | NOAA/NWS | Active public alerts | near-real-time |
| `fema_disasters` | FEMA | Disaster declarations | source-defined |
| `cdc_cdi` | CDC | Chronic Disease Indicators | source-defined |
| `clinicaltrials_gov` | NIH/NLM | ClinicalTrials.gov API v2 | daily/source-defined |
| `openfda` | FDA | Drug labels | source-defined |
| `pubmed` | NCBI/NLM | PubMed E-utilities | source-defined |
| `europe_pmc` | EMBL-EBI | Europe PMC search | source-defined |
| `nlm_clinical_tables` | NLM | Clinical Tables conditions | source-defined |

The catalog is deliberately bounded. API-key or licensed feeds must be explicitly registered and credentialed rather than silently enabled.

## Provenance and integrity

Every accepted observation carries:

- source identifier
- source endpoint
- retrieval timestamp
- observation timestamp
- upstream version metadata when available
- ETag / Last-Modified when supplied
- canonical SHA-256 payload hash
- fabric version
- provenance status

ETag and Last-Modified validators avoid unnecessary transfers when upstream servers support conditional requests. Duplicate `(source_id, record_id, payload_hash)` observations are rejected by both the in-process fabric and PostgreSQL uniqueness constraints.

## Operational API

The existing ingestion router mounts the data-fabric operations under `/api/v1/evidence/ingest/api/v1/data-fabric` to preserve compatibility with the existing application bootstrap.

Endpoints:

- `GET /sources` — catalog
- `GET /sources/{source_id}` — source state
- `GET /health` — per-source health
- `POST /sync/{source_id}` — bounded live upstream synchronization

All responses are marked research-advisory/read-only at the data-product boundary.

## Continuous synchronization

Run:

```bash
python -m workers.realtime_data_fabric_worker
```

Configure `TMRDS_DATA_FABRIC_INTERVAL_SECONDS` with a minimum effective interval of 10 seconds. Durable operation requires `DATABASE_URL` and migration `003_realtime_data_fabric.sql`.

## Safety boundaries

- HTTPS-only source endpoints.
- No arbitrary URL fetch endpoint is exposed.
- Maximum upstream response size is 5 MiB.
- Redirects are disabled to reduce SSRF risk.
- Upstream errors are not returned verbatim through the API.
- Raw observations remain distinct from governed biomedical evidence.
- No patient-specific inference or autonomous clinical action is introduced.
