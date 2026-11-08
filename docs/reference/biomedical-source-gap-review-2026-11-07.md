# Biomedical source gap review — November 7, 2026

This review compares source capabilities with the current TMRDS adapters and
research dossier. A discovered database is not an implemented adapter, a
provider connection, a license grant, or evidence of therapeutic benefit.
The machine-readable counterpart is available at
`GET /api/v1/research/source-catalog`.

## Source priorities and implementation state

| Source | Gap it addresses | State in this change | Integration requirement |
| --- | --- | --- | --- |
| [Europe PMC](https://europepmc.org/RestfulWebService) | Retractions, publication types, correction links were discarded during normalization | Metadata preserved in federated envelopes and dossier groups | Preserve source record and retrieval timestamp; absent flags never mean cleared or reliable |
| [UniProtKB](https://github.com/ebi-uniprot/uniprot-manual/blob/main/notebooks/uniprot_rest_tutorial.ipynb) | Direct protein identity, review status, taxonomy, record/release versions | New bounded read-only adapter, federated search wiring and governance registration | Query uses UniProt syntax, one page only, reviewed/unreviewed status retained; no efficacy inference |
| [GWAS Catalog v2](https://www.ebi.ac.uk/gwas/docs/programmatic-access/rest-api/) | Direct variant-trait and ancestry context rather than only target aggregates | Candidate; no adapter claimed | v1 retired August 2026; use v2; separate full summary-statistics downloads; retain ancestry, genome build and effect units |
| [DepMap / PRISM](https://depmap.org/repurposing/) | Experimental cell-line drug-response and dependency evidence | Access review required | Pin release DOI, assay and cell identifiers and terms; do not scrape or bypass CAPTCHA |
| [LINCS L1000 / GEO GSE70138](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE70138) | Perturbational gene-expression evidence for hypothesis generation | Candidate; no dataset downloaded | Retain cell line, concentration, exposure duration, processing level and measured/inferred distinctions |
| [CZ CELLxGENE Census](https://chanzuckerberg.github.io/cellxgene-census/) | Target expression by tissue and cell type | Candidate; optional scientific environment needed | Pin LTS release; use `is_primary_data` to address duplicated cells; preserve dataset citations/licenses |
| [ClinPGx](https://api.clinpgx.org/) | Pharmacogenomic gene-drug evidence and guideline provenance | Access review required | Respect documented 2 requests/second; schema may change; research use and dataset-specific terms |
| Arca regulatory corpus | Regulatory review/approval/safety context beyond labels | Connector corpus inspected; no backend adapter claimed | Verify original FDA record and freshness; the connector reports the clinical-guideline lane is not yet mirrored |
| Genomic Intelligence | Optional sequence-based splice hypothesis generation | Model catalog inspected; no inference run | Model catalog reported `g0-splice-bigbird`, 15,000-bp context, 500,000-bp request maximum; predictions remain computational evidence |
| qBraid / IBM | Later controlled computational experiments | qBraid community project discovery succeeded; no execution | A demo is not a biomedical solver; require reproducible classical baseline, input provenance, authorization and execution budget |

## Access and licensing findings

- UniProt's [operator-maintained license text](https://github.com/ebi-uniprot/uniprot-manual/blob/main/help/license.md)
  applies CC BY 4.0 to copyrightable database content and cautions that third-party
  rights may apply. Attribution is required; annotations are research information.
- DepMap's current terms page presented a bot-verification screen. A
  [DepMap staff response](https://forum.depmap.org/t/provide-an-open-endpoint-for-latest-version-retrieval/4652)
  reports a metadata-only endpoint at
  `https://depmap.org/portal/api/no-captcha/download/files` and changed terms for
  newer releases, including commercial AI uses. This is not blanket permission
  to redistribute or train on every release. Verify actual release terms first.
- [ClinPGx data usage policy](https://www.clinpgx.org/page/dataUsagePolicy)
  distinguishes ClinPGx/PharmGKB CC BY-SA 4.0 data and research-use conditions
  from CPIC content's separate CC0 terms. Do not apply one license to all records.
- Europe PMC metadata access does not permit indiscriminate full-text mirroring;
  retain each article's access/license scope.
- LINCS/Census bulk ingestion remains staged pending release-specific license,
  citation, checksum and storage review. No large matrix download was performed.

## Operational gaps fixed

Federated per-source tasks now honor the configured timeout, preventing a slow
provider from indefinitely holding the overall response. Failure warnings retain
source and exception type while omitting exception text that may embed queries
or credentials. This bounds awaiting a synchronous adapter's worker thread; it
does not forcibly stop Python threads or replace their underlying HTTP timeout.

Envelope `record_hash` now covers the normalized source record, including
publication-integrity and protein metadata, with explicit
`record_hash_scope=normalized_source_record`. It is not a raw upstream-payload
hash, signature, scientific verification or freshness guarantee. Existing hashes
from the older selected-bibliography-field scheme should not be compared as if
both schemes had the same scope.

## Other requested discovery tools and remaining boundaries

- Exa and Firecrawl were used to locate and read operator documentation.
- Life Sciences Databases returned a live UniProt record; Life Sciences Literature
  returned PubMed identifiers. These are bounded lookups, not exhaustive coverage.
- alphaXiv returned computational benchmark candidates. For example,
  [cross-dataset drug-response benchmarking](https://www.alphaxiv.org/abs/2503.14356)
  is a candidate for a later evaluation review; search excerpts alone are not a
  validated experimental protocol or permission to use its datasets.
- Stack Overflow for Agents supplied engineering search results only; no
  biomedical finding depends on community posts and no contribution was posted.
- Tamarind catalog access failed with an invalid-credential error. No available
  model, entitlement, docking run or backend connection is claimed.
- Patsnap literature search failed with insufficient balance. No patent search,
  freedom-to-operate conclusion or literature coverage is claimed from that call.
- Redis is optional infrastructure, not an authoritative medical dataset. A later
  exact-query cache may use versioned, colon-separated hashed keys, bounded TTL,
  original retrieval times and explicit stale/miss states. Avoid caching patient
  data or treating cache hits as new retrievals; retain PostgreSQL as the ledger.
  Redis was not deployed and no new dependency is required for this change.

## Release and scientific acceptance

Local Python 3.12 validation: 389 tests passed, 6 skipped, 16 integration tests
deselected, and 19 subtests passed. The test environment uses requirements.txt,
not the exact Python 3.11 CI lock; GitHub CI remains a separate gate. Existing
Tier 1/2 orchestration unit tests now stub unrelated adapters so new sources
cannot accidentally turn those checks into live network tests.

Unit tests use synthetic responses, including malformed payloads, upstream 429s,
slow tasks, duplicate source records and retraction notices versus retracted
publications. Live check scope and outcomes are recorded separately in
`docs/audits/2026-11-07-source-adapter-smoke.json`. Both recorded checks passed. Reproduce with
`python scripts/research_source_smoke.py --live --output smoke.json`.
They do not validate every source, deployment readiness or therapeutic utility.

Remaining: implement and independently validate the candidate adapters, screening
and quality appraisal, cohort applicability, reviewer audit/sign-off, accessible
research workspace, and retrospective/held-out scientific evaluations before
any effectiveness claim. No autonomous diagnosis, dosing, prescribing, cure
claim, live patient exchange or clinical deployment is added.
