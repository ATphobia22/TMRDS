# TMRDS animated Rubik cube and governed public biomedical evidence gateway

Status: implemented source code and test contracts; public cloud backend deployment
requires an operator-owned host and TLS configuration. **GitHub Pages is static
and DOES NOT execute the Python adapters.**

## What runs where

| Surface | What is connected | What is deliberately absent |
|---|---|---|
| GitHub Pages `public/` | Direct, bounded Europe PMC and ClinicalTrials.gov v2 lookups; real 3D rotating 26-cubie display | Python API, database, clinical records, quantum hardware |
| Docker `api.public_gateway:app` | Same site, exact-ID disease-to-target-to-compound route, 25-source federated discovery dossier, GWAS v2, source-policy inventory | Patient ingestion, DICOM, FHIR writes, Neo4j/PostgreSQL access, admin routes, clinical endpoints |
| Existing `api.main:app` | Original full TMRDS backend plus new read-only pathway routes | Not recommended as internet-facing public viewer |

The cube is physically reindexed as quarter-turn layers (26 visible cubies,
six colored external sticker orientations), rotates between searches, and
turns layers when searching. It does not model quantum computation. A user can
manually trigger a turn; `prefers-reduced-motion` avoids animated movement.

## Deploy locally; publish only behind TLS

```bash
docker compose -f compose.public.yml config
docker compose -f compose.public.yml up --build -d
curl -fsS http://127.0.0.1:18080/health/ready
curl -fsS http://127.0.0.1:18080/backend-config.json
curl -fsS http://127.0.0.1:18080/api/v1/research/source-governance
```

Visit `http://127.0.0.1:18080/`. The public-only Docker image is built
from `Dockerfile.public`, runs as UID 10001, listens on container 8000,
and is loopback-bound in Compose. Deploy it behind a properly configured
HTTPS reverse proxy with sensible concurrency limits, request logging that
does not persist disease-query text, egress restrictions and observability.
The readiness endpoint tests *process* readiness, not provider liveness.
No proxy, DNS, TLS certificate or production cloud service is provisioned here.

The deployed backend overrides `/backend-config.json` to
`{"api_mode":"same-origin"}`. The **GitHub Pages** copy of that file is
`{"api_mode":"disabled"}` and does not attempt to call a fabricated backend.
CSP permits only the same origin, Europe PMC and ClinicalTrials.gov.
Do not add cross-origin arbitrary API URLs, universal CORS wildcards or
browser API keys.

## Read-only API routes

- `GET /api/v1/research/evidence-pathway?disease=MONDO_0009061&limit=8`
  queries Open Targets fixed HTTPS GraphQL; one exact disease identifier,
  the top 8 direct target-association rows and source-reported candidate
  mechanisms. It creates a triple only when the molecule's source-reported
  mechanism names a target's exact Ensembl ID. Matching names, search
  co-occurrence and broad disease descendants do **not** create joins.
  A query for text must resolve to a unique exact preferred name;
  ambiguous names return candidates without fabricated links.
- `GET /api/v1/research/dossier?query=cystic%20fibrosis&limit=3`
  invokes the existing 25-source federated research adapters with isolated
  provider failures, normalized source metadata, evidence hashes and
  unpublished/retraction warnings. A source failure is not a negative result.
  Queries may be forwarded to third-party sources. Never enter patient data.
- `GET /api/v1/research/gwas-associations?trait=asthma&limit=8`
  uses the existing bounded GWAS Catalog v2 adapter.
- `GET /api/v1/research/source-governance` lists **all 25** federated
  sources and conservative license/permission states; unreviewed sources
  have `metadata_display_allowed=false`.
- `GET /api/v1/research/reference-pathway-contract` returns the
  method and review boundary for the embedded reference cases.
- `GET /health/live`, `GET /health/ready`, and
  `GET /backend-config.json` are operational endpoint metadata.

Source-origin allowlisting is in adapter code; the new pathway client
uses fixed HTTPS origin, rejects redirects, sets 18 s timeouts and a
2 MB response ceiling, validates identifiers, records SHA-256 over
**selected** source fields, and rejects GraphQL `errors` even on HTTP 200.
The API is research-only and has per-route rate limits. A source request
that fails returns `status=source_unavailable` and empty links, never
a false evidence-negative finding.

## Freshness and licensing

`engines/governed_pathway.py` separates:

1. **Retrieval age:** `fresh`, `stale`, `unknown` or
   `invalid_future_timestamp`, calculated from an actual timestamp.
   Fresh retrieval **does not** certify that the upstream scientific
   release is current.
2. **Upstream release identity:** preserved from Open Targets `meta.dataVersion`
   when present. It is `observed_not_independently_verified`;
   an absent version is not silently invented.
3. **License class and terms-review age:** core provider policies record
   attribution, public metadata-display scope, a terms URL and a dated
   review checkpoint; all forbid automatic bulk redistribution and
   request human approval. Unregistered source policies are withheld,
   not marked open. A 90-day checkpoint flags `review_overdue`.
   Open Targets integrates ChEMBL, for which CC BY-SA 3.0 obligations
   can remain relevant even when aggregated platform data are available.
4. **Monitoring:** `scripts/audit_research_sources.py` makes a
   bounded, dated read of 5 official sources (Open Targets, ChEMBL,
   Europe PMC, ClinicalTrials.gov, GWAS Catalog v2), captures the
   exact unsigned response byte hash, and runs a small live pathway
   regression case when available. GitHub Actions
   `.github/workflows/source-governance.yml` runs the receipt weekly
   and uploads the JSON as a 30-day artifact. Provider downtime is
   recorded as unavailable; it is not a successful freshness check.
   The remaining ~20 adapters have policy visibility but are **not**
   continuously probed by this workflow.

The policy is a *technical reuse gate*, **not a legal opinion**. Actual
provider terms, redistribution, commercial use, dataset lineage, retraction
and share-alike obligations still require named human review.

## FDA-anchored pathway reference and independent validation boundary

File: `engines/pathway_reference_cases.json`.

The positive reference is **cystic fibrosis**
(`MONDO_0009061`) → **CFTR** (`ENSG00000001626`) →
**ivacaftor** (`CHEMBL2010601`). It is anchored in a current
FDA KALYDECO label, NCBI Gene identifiers and the Open Targets drug page.
This is **genotype-specific** treatment evidence: the source label does not
generalize eligibility across all cystic fibrosis cases.

The negative test `MONDO_0009061` + TP53 (`ENSG00000141510`)
+ aspirin (`CHEMBL25`) is an explicitly **synthetic** false-join control.
Failure to emit it is an algorithmic precision check, **not** a clinical
conclusion that the combination has no biological relevance.

`validate_reference_pathways` checks the expected exact identifier
triples, negative controls and source result hash scope. The unit
fixture is **synthetic** and the script's optional live receipt is
one-case technical consistency only. The reference case file explicitly
sets `independent_human_review_completed=false`; the API returns
`clinical_validation=false`.

To establish independent scientific validation later, a domain reviewer
must approve source versions and label terms, prospectively lock a
multi-disease benchmark from independently curated reference datasets,
include clinically adjudicated negatives and blinded holdouts, report
precision/recall with confidence intervals and error analysis, and
verify population/genotype applicability. None of this has been silently
claimed complete.

Official anchor documents:

- [FDA 2026 KALYDECO label](https://www.accessdata.fda.gov/drugsatfda_docs/label/2026/207925s021lbl.pdf)
- [NCBI Gene CFTR](https://www.ncbi.nlm.nih.gov/gene/1080)
- [Open Targets ivacaftor](https://platform.opentargets.org/drug/CHEMBL2010601)
- [MONDO 0009061 at ClinGen](https://search.clinicalgenome.org/kb/conditions/MONDO%3A0009061)
- [Open Targets API](https://platform-docs.opentargets.org/data-access/graphql-api)
- [ChEMBL API docs](https://chembl.gitbook.io/chembl-interface-documentation/web-services/chembl-data-web-services)
- [Open Targets source licensing](https://platform-docs.opentargets.org/licence)

## CI/release gates

```bash
python -m pytest -q tests/test_governed_pathway.py tests/test_public_gateway.py
python -m pytest -q -m 'not integration'
python scripts/check_public_site.py
node --check public/site.js
docker build --pull -f Dockerfile.public -t tmrds-public:test .
```

Separate PR workflow checks the gateway, 3D UI contract and isolated Docker
smoke tests. A green CI run does not prove that a public backend is hosted
or that reference cases have been independently clinically validated.
