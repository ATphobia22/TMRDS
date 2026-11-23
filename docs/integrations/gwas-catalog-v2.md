# NHGRI–EBI GWAS Catalog v2 integration (TMRDS)

Research-advisory association discovery only; not a clinical interpretation, causal inference, individualized treatment, or cure prediction.

## Official upstream source

- Provider: NHGRI–EBI GWAS Catalog (EMBL–EBI).
- Documentation: https://www.ebi.ac.uk/gwas/docs/programmatic-access/rest-api/
- API: https://www.ebi.ac.uk/gwas/rest/api/v2/associations
- Independently inspected 2026-11-23: GET /gwas/rest/api/v2/associations?efo_trait=asthma&page=0&size=2 returned HTTP 200 with association IDs, EFO traits, study accessions, PMID, p-values and pagination.
- API v1 retired August 2026. There is no current API for full GWAS summary statistics; the v2 API offers literature-curated top associations only.
- Provider cap: 100 requests per minute AND 15 per second per IP; bulk use requires a separate official flat-file workflow.

## Implementation

- engines/gwas_catalog_v2_pipeline.py contains a one-page, bounded read-only request against fixed HTTPS origin; no redirects or arbitrary URLs.
- At most 25 records; query length 2–120 characters without control bytes; show_child_traits=false prevents silent ontology expansion.
- Source errors, bad schemas, malformed numeric identifiers and invalid p-values fail visibly through the existing per-source isolation.
- Each normalized record carries association_id, study accession (GCST), EFO traits, reported traits, PubMed ID, p-value plus mantissa/exponent, effect text, effect alleles and the original source record.
- Distinct association IDs must survive a shared publication PMID. Record hash scope is normalized source record, not an upstream signed payload.
- Cohort ancestry, genome assembly, confounding and clinical applicability are not supplied or inferred by the initial adapter.
- Source lane is genetic_association; no automatic diagnosis, dosing, efficacy grade or clinical promotion.
- The GitHub Pages public site does not run this backend adapter or claim connectivity to it.

## Tests and operations

- Focused: python -m pytest -q tests/test_gwas_catalog_v2.py
- Full suite: python -m pytest -q -m 'not integration'
- Live gateway requires separately deployed TMRDS Python backend; check source_status.gwas_catalog_v2 and upstream rate-limit errors.
- Source code is open, but public API access does not imply unrestricted reuse of individual studies, licensed source text, or bulk datasets. Review permissions before replication/training.

## Quantum cube boundary

GWAS contributes disease/phenotype-to-variant research arrows, not causal target validation or a cure score. Pairing with ClinVar, Ensembl, gnomAD, GTEx or Open Targets requires matching ontology identifiers, genome assembly, population coverage and peer-reviewed study context. No molecular or quantum computation was triggered by this adapter.

Human authority final. TMRDS is not FDA-cleared or clinically validated.
