# TMRDS Research Discovery Upgrade Roadmap

**Prepared:** 2026-10-09  
**Repository reviewed:** `ATphobia22/TMRDS`  
**Current working branch:** `feature/evidence-discovery-research`  
**Product boundary:** Research discovery and evidence support only; not a diagnostic, prescribing, or autonomous treatment system.

## Executive direction

TMRDS already contains much of the proposed foundation: public-source adapters for PubMed, Europe PMC, ClinicalTrials.gov, FDA, CDC, OpenNeuro, and NLM; an evidence ledger and provenance-aware graph; FHIR/OMOP interoperability boundaries; AI governance; plus early structure-prediction and quantum-related modules. The highest-value upgrade is therefore **not to add every source indiscriminately**, but to turn this growing catalog into a coherent, auditable discovery workflow with explicit coverage, rights, freshness, evidence class, and reproducible computation.

The “disease as a Rubik’s cube” idea can be implemented as a **multidimensional research workspace**: a disease/phenotype view connected to genes and variants, pathways, compounds, trials, outcomes, publications, safety/regulatory records, and datasets. Each connection must retain its source and evidential meaning. Search can help find and organize evidence; it cannot guarantee exhaustive coverage or solve a disease.

## Repository inspection: what exists and what is still a stub

| Area | Repository evidence | Upgrade implication |
|---|---|---|
| Literature and trials | PubMed, Europe PMC, ClinicalTrials.gov, openFDA and other public-source pipeline modules are present. | Extend governed adapters, deduplication, date/update handling, citation export, source freshness, and search UX before adding overlapping scrapers. |
| Evidence handling | Evidence ledger, source registry, conflict handling, graph, and vector retrieval modules/docs exist. | Preserve the ledger as the authority; keep vector/graph indexes derived and link every hit back to source records. |
| Interoperability | FHIR R4/US Core and OMOP modules are documented; external institutional access is explicitly not enabled by repository configuration alone. | Treat HL7 FHIR, OMOP, OpenAPI, and source APIs as distinct boundaries; validate profile/terminology compatibility and institutional authorization. |
| Protein structures | `engines/alphafold3_node.py` has placeholder backends; its default mock path previously returned invented pLDDT/pTM-like values, a mock structure URI, and synthetic compound ranks. | Do not call placeholders predictions. A mock-only behavior fix is implemented on this branch; real adapters need genuine execution, source/model/license provenance, and artifact validation. |
| Quantum chemistry | `engines/quantum_cure_engine.py` and `engines/qiskit_nature_bridge.py` contain prototype/classical-mock paths; QML path in the quantum engine is stubbed. | Rename/reframe as optional research computation; distinguish classical simulation from quantum hardware and report reproducibility, resource cost, and limits. Never imply diagnostic or therapeutic outcomes. |
| Gene editing / splicing | The project architecture verification explicitly excludes automated clinical CRISPR design. | Add read-only, source-grounded research links and variant/transcript context before considering any sequence-design research module; no care-path recommendations. |
| Medical education | No learning-content/course integration is evident in the scanned source catalog. | Start with links and metadata for openly licensed course catalogs; do not scrape restricted LMS/course material or imply course completion/competency. |

Repository documents already define useful guardrails: observed/derived/predicted/hypothesized semantics, immutable provenance, optional heavy dependencies, public-versus-licensed source boundaries, and human review. The roadmap should implement and test those contracts rather than create a second evidence store.

## Target research workflow

1. **Question intake:** normalize disease, phenotype, gene/variant, drug/compound, and population concepts; preserve the original query and show ambiguity for user refinement.
2. **Federated discovery:** query documented, permitted APIs/connectors with bounded requests, source-aware filters, retries/backoff, and clear partial-failure reporting. Avoid a promise to search “all” literature: indexes differ, some content is licensed, delayed, or not indexed.
3. **Evidence normalization:** canonicalize identifiers and terminology; deduplicate by stable source identifiers/DOI/PMID/NCT where available; retain preprint-to-publication relationships without silently merging distinct versions.
4. **Evidence graph:** present disease/phenotype ↔ gene/variant ↔ mechanism/pathway ↔ intervention/compound ↔ trial ↔ outcome ↔ publication/data edges. Each edge carries a source, timestamp, access/license state, evidence class, confidence/limitations, and conflict links.
5. **Research facets (“cube”):** let users rotate/filter across population, evidence type, intervention, disease stage, outcome, time, geography, and translational level (in-vitro, animal, observational, interventional, approved-label). These are navigation facets, not a composite cure score.
6. **Optional computation:** link a reproducible research run to exact input evidence, dataset/model/version, source commit, environment, parameters/seeds, outputs, and evaluation protocol. Computed predictions remain explicitly predicted/hypothesized.
7. **Human review and export:** expose citations, source links, retrieval dates, disagreements, missing coverage, and limitations; export a reviewable evidence packet with provenance.

## Recommended phased implementation

### Phase 0 — Reliability and catalog (next)

- Create a versioned **source registry** with API endpoint, permitted use, license/access class, identifiers, query parameters, update cadence, attribution, retention policy, and adapter owner/version.
- Build a single source health/coverage view: last success, last upstream update observed, rate-limit/errors, records added/updated, and stale/partial-source warnings.
- Add deterministic cross-source deduplication and citation normalization; represent retractions/corrections and preprint/publication links explicitly.
- Add contract tests using fixtures and small opt-in live smoke tests; keep regular CI deterministic and avoid making network scraping a unit-test dependency.

### Phase 1 — Federated evidence search

- Implement a typed search plan across the already integrated bibliographic/trial/regulatory adapters, with query translation shown to the user and bounded concurrency.
- Return an evidence envelope for every result: stable ID, title/citation, source URL, source and retrieval timestamps, access/licensing status, source version/hash where policy allows, evidence class, and parse/quality warnings.
- Add ranking as transparent, configurable **retrieval relevance only**; keep evidence quality appraisal separate, cite its method, and never present ranking as truth or care advice.

### Phase 2 — Disease graph and genetics research data

- Extend the canonical model for genes, transcripts, variants, phenotypes, pathways, compounds, assays, and biospecimen/data artifacts, using established identifiers and versioned crosswalks.
- Integrate approved public/permissioned sources through their documented APIs, with population/ancestry representation warnings and explicit uncertainty. Keep sensitive human genomic data outside public ingestion unless a separate governance/authorization pathway exists.
- Add a splice/variant literature view that reports source-supported annotations and conflicting interpretations; do not generate a clinical interpretation or prescribe an edit.

### Phase 3 — Structure and molecular research adapters

- Make AlphaFold/structure backends real adapters rather than status-only stubs: validated request payloads, job lifecycle, output artifact checks, model/database/release provenance, license/terms checks, and resource limits.
- Record pLDDT/PAE/ipTM only when they are actually present in a genuine backend result and in their proper structural interpretation. They are not efficacy or clinical endpoints.
- Compare structure predictions with orthogonal evidence/experiments; connect candidate docking outputs only as computational hypotheses.

### Phase 4 — Optional quantum research sandbox

- Use mature quantum-chemistry libraries behind an optional dependency extra and a narrow, benchmarked interface; include a classical baseline for every benchmark.
- Initially support small, well-defined molecular Hamiltonian demonstrations or simulation experiments only where the problem formulation and compute budget are explicit.
- Persist backend (`classical_simulator`, `quantum_hardware`, etc.), device/provider, transpilation/configuration, qubit/shot counts, noise model, seed, elapsed cost, and raw results.
- Evaluate whether the quantum workflow improves a named metric over a classical baseline; otherwise label it exploratory. No Grover/VQE score, quantum speedup, or optimizer output may be represented as a disease solution, diagnosis, target validation, or treatment recommendation.

### Phase 5 — Education and research collaboration

- Add an opt-in catalog of openly accessible medical/scientific courses and open educational resources as external links plus descriptive metadata (provider, topic, level, language, access/license, last checked).
- Do not ingest full restricted course materials, bypass login/paywalls, or infer competence from page views. Keep education resources separate from clinical evidence.

## Open-source adoption rules

- Prefer active, documented upstream APIs and maintained repositories with compatible licensing; review releases, security posture, open issues, tests, and deployment footprint before adoption.
- Use adapters and pinned optional dependencies rather than wholesale vendoring. Keep core API startup independent of heavyweight model, GPU, quantum, and genomics packages.
- Store code/release/version and license metadata with integrations; review code provenance and software supply-chain risk before adding dependencies.
- Do not mirror full-text research corpora by default. Store citations and permitted metadata; retrieve full text only when access and reuse rights allow, and honor provider policy, robots rules, rate limits, and takedown/correction notices.

## Acceptance criteria for the next release slice

- Every search result is source-traceable and visibly distinguishes citation metadata, abstract/full text, preprint, registry record, and model-derived output.
- Partial or unavailable sources are disclosed; no “all research searched” assertion is emitted.
- The same search/evidence input can be replayed from persisted parameters and source versions as far as upstream permits.
- Duplicate records and corrections are handled without losing source lineage.
- Mock scientific adapters emit no scientific measurements, artifacts, rankings, or confidence scores.
- Classical simulation, quantum hardware, actual model execution, and unavailable/stub adapters have distinct statuses.
- Core tests run without live-source credentials, proprietary data, or optional scientific dependencies.
- No feature promotes a prediction or hypothesis into observed evidence or clinical authority.

## Work completed in this task

- Corrected AlphaFold mock behavior so it returns `MOCK_ONLY`, no invented metrics or structure URI, and no synthetic compound ranking.
- Added regression tests for the mock structure output, mock compound ranking, and invalid `top_k`.
- Full source/API expansion and live model/provider integrations remain future staged work; no papers or models were bulk-downloaded in this task.

## Selected sources and open-source candidates

The following were checked in the domain review and are starting points for implementation—not blanket permission to use or redistribute source data, weights, or outputs. Recheck terms and API versions during implementation.

### Literature and preprints

- [NCBI Entrez API](https://www.ncbi.nlm.nih.gov/home/develop/api/) and [PubMed E-utilities](https://www.ncbi.nlm.nih.gov/books/NBK25497/): use API adapters rather than HTML scraping. Exact current rate limits should be re-verified before launch.
- [Europe PMC REST API](https://europepmc.org/RestfulWebService) and its [Open Access collection](https://europepmc.org/downloads/openaccess): check per-item license before retaining full text.
- [bioRxiv API](https://api.biorxiv.org/) and [TDM guidance](https://www.biorxiv.org/tdm): API metadata and full-text terms are distinct; access is not redistribution permission.
- [arXiv API manual](https://info.arxiv.org/help/api/user-manual.html), [terms](https://info.arxiv.org/help/api/tou.html), and [open-access guidance](https://info.arxiv.org/help/oa/index.html): follow request pacing; use metadata-first retrieval and honor content rights.
- [Crossref REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/): useful DOI metadata enrichment; abstracts can remain copyrighted.
- Search options: PostgreSQL [full-text search](https://www.postgresql.org/docs/current/textsearch.html) as a low-ops baseline, or [OpenSearch hybrid search](https://docs.opensearch.org/latest/vector-search/ai-search/hybrid-search/) when scale warrants it. [GROBID](https://grobid.readthedocs.io/en/latest/Introduction/) parses only documents the system is authorized to process.

### Trials and regulatory records

- [ClinicalTrials.gov API overview](https://clinicaltrials.gov/data-api/about-api), [migration guide](https://clinicaltrials.gov/data-api/about-api/api-migration), and [study data structure](https://clinicaltrials.gov/data-api/about-api/study-data-structure): preserve registry-native statuses, identifiers, source timestamps, and result semantics.
- [WHO ICTRP portal](https://www.who.int/tools/clinical-trials-registry-platform/the-ictrp-search-portal), [Web Service conditions](https://www.who.int/tools/clinical-trials-registry-platform/the-ictrp-search-portal/ictrp-search-portal-web-service), and [Trial Registration Data Set](https://www.who.int/tools/clinical-trials-registry-platform/network/who-data-set): confirm access conditions before connector work; do not crawl the portal without permission.
- [openFDA APIs](https://open.fda.gov/apis/), [authentication and rate limits](https://open.fda.gov/apis/authentication/), [drug-event caveats](https://open.fda.gov/apis/drug/event/), and [terms](https://open.fda.gov/terms/): openFDA explicitly cautions against use for medical-care decisions.
- Optional code references: [pytrials](https://github.com/jvfe/pytrials) (check current ClinicalTrials.gov v2 compatibility) and [FDA open.fda.gov](https://github.com/FDA/open.fda.gov) (documentation/reference, not a required runtime dependency).

### Genomics, variants, splicing, and standards

- [ClinVar programmatic access](https://www.ncbi.nlm.nih.gov/clinvar/docs/programmatic_access/) and [ClinGen downloads](https://search.clinicalgenome.org/kb/downloads): preserve submitter, review status, dates, conflicts, and condition/context; do not collapse assertions into ground truth.
- [Ensembl REST API](https://rest.ensembl.org/) and [variation documentation](https://www.ensembl.org/info/genome/variation/index.html): pin release, assembly, and transcript versions.
- [gnomAD data](https://gnomad.broadinstitute.org/data) and [help/terms](https://gnomad.broadinstitute.org/help); [GTEx API documentation](https://gtexportal.org/api/v2/redoc); [UCSC API](https://genome.ucsc.edu/goldenpath/help/api.html): respect each service's intended access patterns and coordinate conventions.
- [GA4GH Variation Representation Specification (VRS)](https://vrs.ga4gh.org/en/stable/releases/2.0.html) for computable variant representation; [GA4GH Consent Policy](https://www.ga4gh.org/product/consent-policy/) and [WHO human genome editing governance](https://www.who.int/publications/i/item/9789240030381) for research governance context.

### Structure prediction and quantum chemistry

- [AlphaFold 3 source](https://github.com/google-deepmind/alphafold3), separate [weights terms](https://github.com/google-deepmind/alphafold3/blob/main/WEIGHTS_TERMS_OF_USE.md), [prohibited-use policy](https://github.com/google-deepmind/alphafold3/blob/main/WEIGHTS_PROHIBITED_USE_POLICY.md), and [output/confidence documentation](https://github.com/google-deepmind/alphafold3/blob/main/docs/output.md): source-code license does not grant unrestricted weights or output use. Review the [AlphaFold Server terms](https://alphafoldserver.com/terms) separately.
- Potential alternatives requiring independent license/fit review: [ESM/ESMFold](https://github.com/facebookresearch/ESM), [Boltz](https://github.com/jwohlwend/boltz), and [Chai-1](https://github.com/chaidiscovery/chai-lab). None is presumed a drop-in AlphaFold 3 replacement.
- Chemistry frameworks: [Qiskit Nature](https://qiskit-community.github.io/qiskit-nature/) / [repository](https://github.com/qiskit-community/qiskit-nature), [PennyLane](https://docs.pennylane.ai/en/stable/introduction/chemistry.html) / [repository](https://github.com/PennyLaneAI/pennylane), and [OpenFermion](https://quantumai.google/openfermion) / [repository](https://github.com/quantumlib/OpenFermion). A simulator is classical execution, not a quantum hardware result; benchmark against classical baselines.

The repository’s own baseline design documents are:

- `docs/superpowers/specs/2026-09-07-biomedical-evidence-graph-design.md`
- `docs/superpowers/specs/2026-09-07-research-compute-provenance-design.md`
- `docs/ARCHITECTURE_VERIFICATION.md`
- `docs/VERIFIED_DISEASE_PIPELINE.md`
