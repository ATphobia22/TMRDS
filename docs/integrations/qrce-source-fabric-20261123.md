# QRCE Research Source Fabric — 2026-11-23

**Research discovery only.** The TMRDS "Quantum Rubik's Cube" is a transparent evidence-navigation interface, not a validated automated medical system, not a cure discovery engine and not a confirmed physical quantum computation.

## Implemented functionality

- 22 *existing* bounded public/metadata source adapters queried concurrently by \`GET /api/v1/research/cross-check?query=CFTR&limit=2\`, subject to per-source 16-second timeouts and total 42-second budget. Each returns explicit "responding", "unavailable" or "not queried" state. A rate limiter caps this public route at 3 requests/minute/IP.
- Eight source planes: literature (Europe PMC, PubMed, bioRxiv, OpenAlex, arXiv, Crossref); experimental and regulatory (ClinicalTrials.gov, openFDA, DailyMed); targets and pathways (Open Targets, Reactome, STRING); drugs/chemistry (ChEMBL, PubChem); variation/genome (ClinVar, Ensembl, GWAS Catalog v2, gnomAD, GTEx); terminology (MeSH, NCATS); proteins (UniProtKB); and independent patents via FDA Orange Book.
- Exact source-reported **DOI, PMID, PMCID or NCT** can group *bibliographically identical articles/registrations*; same title or shared gene does NOT suffice. Validated gene/compound/variant IDs are emitted separately as \`molecular_context_links\` for navigation only, without combining experiments, evidence strength or clinical results.
- New \`GET /api/v1/research/pmc-identifiers?identifier=PMC3531190\`: bounded (262144-byte max) official NIH PMC converter lookup, fixed HTTPS host with redirects disallowed, single PMID/PMCID/DOI input, source field match check; returns no body text and does not imply article OA licensing.
- The public project/tool catalog is now **115 names**. Entries distinguish *existing adapters*, *static official destinations*, *software not installed* and *controlled access requiring authorization*. A catalog entry does not run, download or license software.
- A local-only synthetic fixture inspector implements numeric **CSV**, **TSV**, selected **FHIR Observation/Bundle JSON**, sample-free **8-column VCF**, **FASTA** and **FASTQ**. It requires \`--synthetic-only\`, rejects basic identity keys, constrains files to 256 KiB and at most 100 records, returns scoped SHA-256, no raw sequence, no patient identifier and NO medical interpretation. Other formats are explicitly optional, never falsely parsed.

## Exact execution commands

\`\`\`sh
# Local, synthetic-only specimen: NOT for real patient data
python -m scripts.inspect_synthetic_research_fixture --synthetic-only ./examples/synthetic_lab.csv

# Offline unit and static contract gates
python -m pytest -q tests/test_public_crosscheck_routes.py tests/test_qrce_research_formats.py
python scripts/check_public_site.py
node --check public/site.js

# Separate backend research surface, from an independently operated HTTPS host.
# (Local Docker is NOT independently deployed to the Internet.)
docker compose -f compose.public.yml up --build -d
curl -fsS "http://127.0.0.1:18080/api/v1/research/cross-check?query=CFTR&limit=1"
curl -fsS "http://127.0.0.1:18080/api/v1/research/pmc-identifiers?identifier=PMC3531190"
curl -fsS "http://127.0.0.1:18080/api/v1/research/file-format-capabilities"
\`\`\`

### Capability and legal boundaries

**Literature**: PubMed indexing is not PMC full-text inclusion. Cochrane often has subscription content, Google Scholar lacks an unrestricted public bulk-search API; neither is in QRCE's live API fan-out. DOAJ is a public directory, not a license for every manuscript. bioRxiv and medRxiv are **preprints**, not clinical guidance. Preprints and journal versions can share DOI references or have distinct DOIs; don't infer equivalence from titles.

**Clinical trial records**: WHO ICTRP portal is public, but partner XML and bulk services have separate access agreements; EU CTIS and ISRCTN are linked as original registries, not misrepresented as public installed adapters. Trial status, publication and outcome data require reconciliation. ClinicalTrials.gov registration is not demonstrated efficacy.

**Public health/data catalogs**: NLM Dataset Catalog, HealthData.gov, CDC WONDER/Open Data, WHO Global Health Observatory and World Bank are linked as data discovery and population indicators. The WHO's prior GHO OData API has legacy/deprecation guidance; do not assume an old endpoint is evergreen or integrate it without a fresh documented contract.

**Controlled-access data**: PhysioNet has both open and credentialed collections. MIMIC-IV, eICU, dbGaP, UK Biobank and NIH All of Us require approval and/or data-use terms; their patient/participant records **must never** be pulled into GitHub Pages or into the public API. No automatic reidentification, genotype-to-patient matching, or PHI persistence.

**Molecular/structural tools**: Original-source NCBI Gene/ClinVar/GEO/SRA, Ensembl, UniProt, PDB, AlphaFold DB and ChEMBL are distinct evidence sources with separate version/build/organism/ligand semantics. The existing AlphaFold DB adapter retrieves **predicted public structures**; it does not run AlphaFold 3. AlphaFold 3 **code** is Apache 2.0; **weights and outputs** are separately restricted. The terms require particular noncommercial eligibility and disallow publishing model parameters. No unapproved AF3 weights, inference or third-party model training are installed or executed by this release. Local file format support is NOT equivalent to computational gene editing or splicing/CRISPR protocols.

**Lab/biometric files**: FHIR is a schema, not a grant of patient-data access; LOINC/UCUM require terminology validation; lab "normal ranges" vary with method and patient context. DICOM/DICOMweb, HL7v2, BAM/CRAM, BCF, AnnData and mmCIF need separately authorized and validated packages. No "read any formats" claim: unsupported extensions are explicitly reported as requiring an external reader. Biometric inference from patient measurements must remain in authorized, separate environments.

**Scientific software**: RDKit, Biopython, pysam/htslib, scverse/Scanpy, PySCF, OpenFermion, Qiskit, PennyLane, OpenMM, Snakemake and Nextflow are cataloged for optional, versioned workflows; merely listing them does NOT install dependencies, create model jobs or prove an algorithm's validity. For structure/docking/QSAR/quantum approaches use reproducible benchmarks, negative controls, uncertainty, conformer/protonation handling, assay provenance and measured-vs-predicted flags. No claims of quantum advantage or drug efficacy are made.

**Chemistry/periodic table**: IUPAC and NIST original references are linked. Chemical composition, molecular structural similarity, assay activity, atomic data and human drug response are different questions; no scalar "cure" score can combine them without independent scientific validation. The existing RDKit chemistry module is a separate optional compute path, not part of a live public patient application.

**OpenMI**: The research result includes a source-count value exchange *inspired by* OGC OpenMI (typed values and temporal context). It is NOT a conformance-tested OpenMI 2 runtime. Healthcare messaging requires separate FHIR/HL7/DICOMweb profiles, identity/access controls, consent governance and institutional approval.

**Patents**: The FDA Orange Book provides reported numbers/expiration/exclusivity fields, but neither its reported dates nor a public-domain old research paper prove legal freedom to operate. USPTO claim, term/maintenance, jurisdiction, family, blocking patents and FDA exclusivity review remain required. No "expired = reusable" inference or cure claims.

## Original references

- NIH [PMC ID Converter API](https://pmc.ncbi.nlm.nih.gov/tools/id-converter-api/) (single-ID original-source mappings)
- NIH [PMC API tools](https://pmc.ncbi.nlm.nih.gov/tools/developers/)
- NIH [MIMIC controlled-access instructions](https://mimic.mit.edu/docs/faq/how-to-get-access.html)
- WHO [ICTRP partner access and portal](https://www.who.int/tools/clinical-trials-registry-platform/data)
- WHO [GHO OData legacy migration notice](https://www.who.int/data/gho/legacy?target=DATASOURCE)
- DeepMind [AlphaFold 3 model parameters and output terms](https://github.com/google-deepmind/alphafold3/blob/main/WEIGHTS_TERMS_OF_USE.md)
- OGC [OpenMI 2.0 standard](https://docs.ogc.org/is/11-014r3/11-014r3.html)
- IUPAC [Periodic Table](https://iupac.org/what-we-do/periodic-table-of-elements/)
- [TMRDS research catalog](../../public/medical-projects.json) and [source adapter definitions](../../engines/federated_evidence_search.py)

## Evidence gate

The source catalog does **not** imply verified availability, authentication, effective licenses, usable patient data, scientific or medical validation, approval of gene editing or pharmaceutical reuse, hardware-backed QPU execution or a deployed internet-facing Python backend. All source links, health and terms require dated rechecking. Individual pipeline CI must pass before merge; end-to-end production connectivity requires independent runtime checks and cannot be inferred from local or Docker tests.
