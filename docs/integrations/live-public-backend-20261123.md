# TMRDS public research HTTPS service — first deployment

**Independently verified 2026-11-23 (UTC).** This is the public, read-only, nonclinical metadata-gateway variant of TMRDS; it is **not** the all-purpose clinical application and does not ingest patient records.

## Links and deployment facts

| Surface | Actual deployment state |
|---|---|
| [Connected research workspace](https://tmrds-public-evidence-api.onrender.com/) | Public HTTPS, same-origin Docker/Python research API and rotating Rubik's Cube |
| [Static public atlas](https://atphobia22.github.io/TMRDS/) | GitHub Pages HTML/CSS/JS, direct browser lookups; Python API disabled, direct link to the hosted research workspace |
| [Render service dashboard](https://dashboard.render.com/web/srv-dc208b59fdbs73c24isg) | Operator control, deployment logs and environment |
| Source repository | `ATphobia22/TMRDS`, branch `main` |
| First verified deploy | `0ec2669c16ddca030ed3fc1dec9cd6b246cb13c9`, free runtime tier, region Ohio, Dockerfile.public, auto-deploy on commit |
| Public application process | Uvicorn `api.public_gateway:app`, port 8000, non-root UID 10001, container file system read-only where Compose is used |

**Note:** the Render web service is configured from Dockerfile.public; the local `compose.public.yml` hardening settings (including a read-only filesystem) do **not** automatically carry over to every Render container setting. Validate the actual cloud configuration independently. Free-plan instances may spin down, cold-start, enforce quotas, and have no uptime/SLA guarantee.

## Independent successful probes

On 2026-11-23 the following externally requested endpoints returned HTTP 200 over HTTPS:

```text
GET /health/ready
  {"status":"ready","external_sources_verified":false}

GET /backend-config.json
  {"schema_version":"1.0","api_mode":"same-origin"}

GET /api/v1/research/medical-projects?category=genomics
  status 200; source catalog, explicit nonclinical flags and source licenses

GET /api/v1/research/file-format-capabilities
  status 200; local_synthetic_only, no patient upload or clinical ingestion

GET /api/v1/research/alphafold3-status
  status 200; not_configured, inference_submitted=false, weights_bundled=false

GET /api/v1/research/pmc-identifiers?identifier=PMC3531190
  status 200; original NIH linked PMCID PMC3531190,
  PMID 23193287 and DOI 10.1093/nar/gks1195

GET /api/v1/research/periodic-element?symbol=Fe
  status 200; original NCBI PubChem periodic table, 118 rows;
  iron, atomic number 26; no safety or efficacy inferences

GET /api/v1/research/cross-check?query=CFTR&limit=1
  status 200; 22 source requests attempted, 18 responded,
  14 records returned, no exact-ID overlap detected within this bounded slice.
```

### Real-world upstream issues from the CFTR check

The four nonresponding adapters were **ChEMBL**, **GWAS Catalog v2**, **PubChem compound search**, and **bioRxiv**. Their per-source error statuses were retained as `source_unavailable`, not converted into no-evidence conclusions. A generic CFTR text query is not valid for all data types (some sources require exact variant/compound identifiers, a trait, or recent date-window filtering). This status does not mean those databases are down globally. Further investigation requires reviewing the adapter-specific error class, live schema, official querying semantics and data-use restrictions.

## Continuous release verification

A separate [public-api-smoke workflow](../../.github/workflows/public-api-smoke.yml) performs a **daily** UTC 12:17 (07:17 EST) HTTPS contract check using only Python standard-library networking. It verifies:

- API readiness is a process-only state, not evidence-provider health.
- Same-origin backend configuration is enabled.
- Genomics catalog and nonclinical/rights-restricted status flags are present.
- Laboratory formats remain synthetic-only; no public patient upload/ingestion advertised.
- AlphaFold 3 weights and inference stay unconfigured.

The workflow writes a dated JSON receipt with a SHA-256 digest, retained as a GitHub Actions artifact for 30 days. It checks the contract, not every upstream provider. **Weekly source-governance tests remain separate**; neither workflow proves clinical accuracy or legal rights.

The monitor runs on manual dispatch or schedule after merge; a green offline pull-request unit test does not mean the scheduled live monitor has run.

## Limits and next operational checks

1. Restrict outgoing HTTP to reviewed source endpoints, monitor per-source errors/rate limits, and keep license/source-release dates current. This first deployment is suitable for bounded *public research metadata*, not storing institution records.
2. Monitor free-plan response times/cold starts and upstream API timeouts. Large 22-source fan-outs are bounded by the public rate limiter and per-source timeouts, but latency and incomplete coverage remain possible.
3. Independently test deployment security: TLS termination, request log retention, abuse/DoS controls, privacy notice, session tracking, CSP, contact disclosure and cloud operator configuration. Container and unit tests alone are insufficient.
4. Run authoritative scientific benchmarks and source-specific reference comparisons before claiming calibrated predictions, clinical outcomes or independent replication; the one-case CFTR/ivacaftor identifier check is not a clinical validation study.
5. AlphaFold 3 parameter terms require independent license/organization eligibility review; no weights, restricted data or proprietary patient input are bundled here.
6. No result establishes a cure, patent freedom-to-operate, approved medical use, validated biometric inference or actual quantum hardware advantage.

The public dashboard has no clinical write or patient upload routes. Source- and license-specific restrictions still govern downstream scientific reproduction.
