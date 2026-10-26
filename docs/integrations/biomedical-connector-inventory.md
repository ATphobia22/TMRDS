# Biomedical provider expansion: governed research integration

Implemented metadata-only integration in `engines/biomedical_provider_registry.py` and tests in `tests/test_biomedical_provider_registry.py`.

**Connector access is separate from TMRDS deployment.** ChatGPT plugin connections do not grant backend API keys, entitlement, patient-data agreements or permission to perform compute. This module deliberately makes **no external calls** and cannot launch paid jobs, analyze patient records or recommend treatment.

| Providers | Research surface | Next live integration gate |
| --- | --- | --- |
| Arca | FDA/public health, PubMed, ClinicalTrials.gov | Public source identifiers, retrieval timestamps, licensing |
| Litmaps, Scite, Consensus, Elicit | Literature and citation evaluation | DOI/PMID, retraction checking, cited source snapshots |
| Prognyx | Oncology trial landscape | NCT ID, sponsor, status, registry version |
| Biohub ESM | Protein Atlas and managed ESM predictions | Exact sequence, version, cost approval, provenance |
| Tamarind Bio | Protein/chemical research computation | Working account credentials, job schema, limits, explicit cost approval |
| Adaptyv Bio via Tamarind | Wet-lab assays | Target and assay selection, written approval before order |
| Proto | Bioinformatics tool runner | Schema validation, provenance and execution permission |
| Genomic Intelligence | Sequence prediction | Reference assembly, consent, model version, inference limitations |
| Tabulous | Managed research workspace | Authorized dataset scope, row-level access, privacy contract |

All incoming external records must contain a provider ID, source ID, HTTPS URL without credentials, timezone-aware retrieval time, source summary, `clinical_promotion_allowed=false`, and `human_authority_final=true`. The contract rejects unexpected fields, including patient identifiers. Passing this validator **does not** establish evidence quality, scientific accuracy, safety, HIPAA status or medical effectiveness.

**Discovery observations (2026-10-26):** Arca exposed public research dataset lanes; Proto exposed runnable AlphaFold DB, Ensembl, variant and sequence tools. Tamarind returned unauthorized/invalid connection credentials; no compute or assay was submitted.

## Remaining gates

- [x] Non-executing catalog and synthetic safety tests.
- [ ] Implement authenticated provider-native clients independently and document terms/licensing.
- [ ] Add secure credential provisioning, per-provider quotas, timeouts, SSRF protections, source snapshots, artifact hashes and resilient retries.
- [ ] Prove reproducible retrieval, revocation/retraction handling, audit logs and precise provenance.
- [ ] Obtain privacy, scientific and clinical review before any patient-specific or consequential use.
