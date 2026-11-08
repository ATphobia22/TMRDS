# Research plugin integration boundaries

TMRDS now inventories all 30 requested plugin surfaces at
`GET /api/v1/medical/plugin-capabilities`. This is capability discovery and
integration planning, not 30 connected backend APIs. A ChatGPT connector cannot
be copied into a server or used as a deployable credential. No proprietary plugin
source code has been copied. Unknown free-tier or redistribution rights remain
`not_verified`; account access is not a zero-cost entitlement.

## Requested surfaces

| Plugin | Intended function | Local or public alternative |
| --- | --- | --- |
| Search | Exa / Firecrawl | Existing public-source adapters |
| Firecrawl | Website and paper retrieval | requests / public source APIs |
| Exa | Web search and page retrieval | public source APIs |
| Consensus | Paper discovery | Europe PMC / PubMed |
| Tamarind Bio | Managed molecular computation | local optional scientific engines |
| alphaXiv | Computational paper discovery | arXiv API |
| Amass | Harmonized biomedical records | UniProt / PubMed / ClinicalTrials.gov |
| GitLab (Beta) | Repository workflows | git |
| Stack Overflow for Agents | Engineering references | official project documentation |
| Redis | Derived retrieval cache | PostgreSQL authoritative store; Redis optional |
| Postman | API contract testing | committed Postman smoke collection / pytest |
| ConvertAPI | Document conversion | local optional pypdf / Tesseract |
| Data | Research data quality and analysis | Python / PostgreSQL |
| Life Sciences Databases | Source-specific research requests | direct verified biomedical adapters |
| qBraid | Quantum workspace and simulator discovery | local simulation with classical baselines |
| Life Sciences Literature | Literature requests | PubMed / Europe PMC |
| Scholar Sidekick | Citation and retraction review | Europe PMC integrity metadata |
| Synoptic Panel SVG Map Maker | SVG mapping | local static SVG; capability not verified |
| Arca FDA, Trials & PubMed | Regulatory and trial discovery | openFDA / ClinicalTrials.gov / Europe PMC |
| Genomic Intelligence | Sequence-based hypotheses | Ensembl reference data; local validated models later |
| Adaptyv Bio | Experimental assay workflows | no free wet-lab equivalent assumed |
| Prognyx oncology intelligence | Source-linked oncology landscapes | ClinicalTrials.gov |
| Biohub ESM | Protein annotation and model access | UniProt / RCSB PDB |
| Litmaps | Citation relationships | OpenAlex / Crossref |
| Elicit | Evidence discovery and screening | Europe PMC; reviewer-led screening |
| PDF | PDF extraction / review | local optional PDF tooling |
| AWS Core | AWS documentation and optional services | local Compose stack |
| GitHub | Source and CI workflows | git / existing GitHub Actions |
| Health | User-authorized personal health context | disabled in public research ingestion |
| Google Drive | User-selected research documents | local public-document export |

## Implemented exchange

`POST /api/v1/medical/research-records/preview` accepts 1–100 normalized public
metadata records with explicit public-data attestation. It validates source
identity, HTTPS provenance, retrieval time and research-only flags, computes a
submitted-record SHA-256 and returns an unreviewed preview. It performs no network
fetch, persistence, model execution or clinical approval. Existing service identity
and API-key policy apply. The attestation and field restrictions do not constitute
an automated PHI detector; never submit patient information. Health records are
explicitly rejected from this public-research path.

Fields per record: `provider_id`, `source_id`, `source_url`, `retrieved_at`,
`summary`, `human_authority_final=true`, `clinical_promotion_allowed=false`, plus
optional identifiers/version/limitations already supported by the provider
registry. Query strings/fragments are rejected to avoid carrying access tokens.
Each provider/source identity must be unique. A hash verifies submitted bytes'
normalized identity, not source truth or authorship. Provider-raw formats still
require explicit mapping to this contract; native plugin invocation is not added.

## New verified public source

`GET /api/v1/research/structures/pdb/4HHB` uses the RCSB core-entry API. It retains
experimental method, accession metadata, retrieval time, source link and a
parsed-upstream-JSON checksum. It supports four-character PDB IDs only, does not
download atomic coordinates, and does not infer therapeutic effectiveness.
Computed structure identifiers are intentionally outside this first adapter.

Primary references:
- https://data.rcsb.org/
- https://www.rcsb.org/docs/programmatic-access/web-apis-overview
- https://www.rcsb.org/pages/usage-policy

RCSB core archive data are openly available under CC0; check external annotations'
applicable terms and cite original structure authors. The live check's exact
retrieval time and result are in `docs/audits/2026-11-07-rcsb-live-check.json`.

## Observed connector access and deferred work

Amass returned a public gene record, Prognyx returned a source-linked trial
landscape and Litmaps returned a public paper result. Those checks do not establish
free standalone API entitlement. ConvertAPI exposed converter descriptions; no
conversion or document upload was performed. Elicit reported API access denied by
the account's plan. Earlier Tamarind discovery rejected its credential; paid
computation, wet-lab orders, quantum hardware and cloud provisioning remain off.

Health and Google Drive personal records were not read. No private clinical data
were uploaded to conversion, literature, model or research providers. GitHub is
the actual repository/CI integration; no unrequested GitLab mirror was created.
Redis remains an optional derived cache; the evidence ledger remains PostgreSQL.

Remaining work is provider-specific authentication, current pricing/quotas/license
review, consent-scoped private-document handling, native result mappers, durable
review events, and independently validated scientific use. Catalog entries and
import previews must not be reported as fully functioning provider integrations.
