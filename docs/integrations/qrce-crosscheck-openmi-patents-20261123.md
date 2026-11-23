# TMRDS Quantum Rubik's Cross-Source Evidence and Patent Metadata

**Audit date: 2026-11-23.** Public research only; no clinical ingestion, patient identifiers, treatment choices, QPU connection or legal freedom-to-operate claim.

## 1. Original-source discovery and verification

The public site preserves **direct requests** to Europe PMC and ClinicalTrials.gov and adds Crossref deposited DOI metadata, plus a separate **FDA Orange Book drug-ingredient lookup**. Each request displays upstream availability, record IDs, access disclaimers and a query timestamp. Crossref is broad scholarly metadata; a DOI is **not** independent validation.

12 existing Python backend source adapters participate in a new bounded route, `GET /api/v1/research/cross-check?query=CFTR&limit=2`:

| Source | Evidence function | Rights and caveats |
|---|---|---|
| PubMed/NCBI | Original PMID citations | Citations only; per-publisher rights |
| Europe PMC | Bibliographic metadata and indexed PMIDs/DOIs | No full-text redistribution |
| ClinicalTrials.gov | NCT registrations | Registration is not measured clinical efficacy |
| Open Targets | Gene/target association context | Relative association scores, not causal proof |
| ChEMBL | Assay/drug context | CC BY-SA 3.0, heterogeneous assay conditions |
| openFDA | FDA label context | Safety/regulatory data, not treatment advice |
| DailyMed | Structured product labels | Label and provider terms |
| GWAS Catalog v2 | Curated top trait-variant associations | Association does not establish causation |
| Reactome | Human pathway/functional context | Pathway annotations CC0; figures/software separately licensed |
| PubChem | Public molecular properties and identifiers | Contributors retain upstream rights |
| UniProtKB | Reviewed/unreviewed protein metadata | CC BY 4.0 with attribution |
| Crossref | DOI-deposited metadata | Factual metadata generally CC0; manuscripts separate |

The **cross-checker** only unifies records with exact matching source-supplied **DOI, PMID or NCT** identifiers. Identically titled records are *not* linked without an ID. One work appearing in multiple databases is recorded as **cross-index overlap**, never as independent scientific replication. Metadata disagreements, retraction-review flags, source errors and unqueried sources remain visible, along with a SHA-256 fingerprint of the normalized source-count/status snapshot (not a signature or a hash of raw upstream records). When a provider cannot respond, results are partial rather than automatically negative.

The 3D rotating Rubik's Cube is a **user interface for these evidence planes**. It does not run a physical QPU, discover cures or assign clinical efficacy scores.

### Deployed surfaces

| Route or frontend | Purpose | Deployment status |
|---|---|---|
| Browser Europe PMC, ClinicalTrials.gov, Crossref | Direct live read-only source searches | GitHub Pages when remote CORS permits |
| Browser FDA Orange Book | On-demand active ingredient search | GitHub Pages when remote CORS permits |
| `GET /api/v1/research/cross-check` | 12-adapter exact-ID crosscheck | In separately deployable Python public gateway |
| `GET /api/v1/research/patent-landscape` | FDA Orange Book normalized patent metadata | In separately deployable Python public gateway |
| `GET /api/v1/research/pubmed-citations` | NCBI citations only | Existing Python gateway |
| `GET /api/v1/research/alphafold-db/{accession}` | EMBL-EBI prediction metadata | Existing Python gateway |

**GitHub Pages cannot host Python**. The Pages `backend-config.json` explicitly disables backend functions. The isolated `Dockerfile.public` and `compose.public.yml` are packaging contracts, not proof of an externally reachable HTTPS backend. The health endpoints are *process readiness*, not evidence of clinical validation.

### OpenMI: where it really fits

[OGC OpenMI 2.0 (11-014r3)](https://docs.ogc.org/is/11-014r3/11-014r3.html) is a standard for **runtime exchange of model component values**. The crosschecker exports an `openmi_inspired_exchange` object containing a typed `source_public_record_count`, units `1`, timestamp, producer/consumer IDs and source-status context. This is a **nonclinical, OpenMI-inspired model exchange contract**, not an OpenMI-compliant component or a live OpenMI .NET host.

Clinical EHR messaging requires separate **FHIR/HL7v2** contracts; imaging requires **DICOMweb**. OGC OpenMI does not provide patient consent, HL7 semantics, identity management, BAA coverage or medical-terminology interoperability. Any eventual compliant OpenMI runtime would require a model-component host, time/space quantity/adaptor exchange, executable conformance tests and versioned model schema. Do not use the unrelated `OpenMI/openmi` machine-learning library as if it implemented the OGC standard.

### FDA Orange Book research and freedom-to-operate control

The live **openFDA `drug/orangebook.json`** endpoint contains FDA-supplied application/product metadata and may contain listed patent numbers, reported dates and pediatric extension flags, alongside drug-specific regulatory exclusivity. It is a **monthly** database. The new backend route is fixed to that endpoint: allowlisted ingredient syntax, no redirects, 12-second deadline, a 1 MiB cap, maximum five source records and per-request timestamps. The browser makes the same bounded ingredient query with at most three records.

The route intentionally emits `patent_freedom_to_operate: NOT_DETERMINED`, `expired_public_domain_claim: false`, `federal_patent_database_checked: false` and `legal_status: UNVERIFIED` for every reported patent. It reports whether a date is **before, on or after** the lookup date without translating it into expiration/legal effect. Child data may carry `*PED` pediatric extension markers, which are preserved without assuming their legal effect.

The FDA source metadata sample checked 2026-11-23 for `METFORMIN` included a 2012-02-02 approved JANUMET XR record with listed US patent `7326708`, a reported date `2026-11-24`, and a second `7326708*PED` entry reporting `2027-05-24`. **This does not establish current legal status**, freedom to practice or drug repurposing efficacy. In fact it illustrates why mapping a drug name or gene variant directly to `EXPIRED_PUBLIC_DOMAIN` is unsound.

Before reusing a historic technique, conduct patent *claim* and *family* search at the USPTO; verify jurisdiction, filing and grant dates, priority, adjustment and extension, maintenance, terminal disclaimers, litigation, pediatric exceptions, later blocking claims and any FDA exclusivity. Review the method, formulation and manufacturing patents independently. Obtain professional legal review before deployment/production. FDA clearance and clinical effectiveness are separate requirements.

Official upstream documents:
- [FDA Orange Book API examples](https://open.fda.gov/apis/drug/orangebook/example-api-queries/)
- [FDA original data files and patent-field definitions](https://www.fda.gov/drugs/drug-approvals-and-databases/orange-book-data-files)
- [USPTO maintenance fees and expiry notices](https://www.uspto.gov/patents/maintain)
- [USPTO patent-term calculator and limitations](https://www.uspto.gov/patents/laws/patent-term-calculator)
- [USPTO searchable Patent Public Search](https://www.uspto.gov/patents/search)
- [USPTO Patent/Open Data Portal](https://data.uspto.gov/) — account/API key may be required after 2026-06-18
- [USPTO/FDA warning on patent and exclusivity](https://www.fda.gov/drugs/development-approval-process-drugs/frequently-asked-questions-patents-and-exclusivity)

No user-uploaded prescription/genomic table, real patient record or PHI enters this public website.

## 2. Uploaded material applicability audit

The user's local source materials were inspected as **proposed code/designs**, not as verified runtime observations. They are **not directly imported or autoexecuted** in production.

| Provided material | Potential reusable piece | Blocker / status |
|---|---|---|
| `TMRDS_Quantum_Engine.txt` | Three.js rotating cube and UI interaction patterns | WebSocket/QPU "connected" state is assigned by a timer; random QPU temperature, coherence and latency are mock telemetry. **Do not claim a live QPU.** |
| `quantum_cure_engine.py` | Basic local vector cosine search, input shapes, reproducible Hamiltonian toy calculations, offline queue ideas | Simulated quantum error decoding assigns fixed fidelity, hashes nucleotide strings into toy energies, pattern scrubber does not reliably meet HIPAA Safe Harbor, and simple file hashes are not cryptographic signatures or immutable ledgers. No clinical/chemical validations |
| `Quantum Medical.pdf` and `QRCE.pdf` | Q-FSRU FFT, quantum-state fidelity and simulated VQE patterns for *independently tested* research benchmarks | PDF-extracted code contains inconsistent indentation/malformed lines and unrealistic hardware-guard claims; no clinical cure inference |
| `Quantum Rubiks Cure Engines Code.pdf` | Decomposable pipeline outlines and module boundaries | Unverified module names, hardcoded throughput/timing claims and unvalidated system-level override commands; do not execute bootstrap or force-push steps |
| `Quantum React.pdf` | Mobile Web Worker / local storage / accessible UI sketch | Architectural concepts only, no supported simulation speedup or compliance proof |
| `Deep Xde med.pdf` | Fisher-KPP reaction–diffusion PINN demo setup | `model.compile` and `model.train` are commented out while output claims `SOLVER_CONVERGED`; simulated radius is a literal. **Must be treated as untrained demo, not real scientific result** |
| `3D moonray med.pdf` | Scene export/render adapter idea | Fixed return values (`4K`, `VALIDATED`, `RESOLVED_TO_HEALTHY_CONFIGURATION`) without OpenMoonray execution. No scientific effect |
| `Multi OMnics engine med.pdf` | Basic VCF column parsing / repurposing hypothesis discovery | A three-row hardcoded drug/variant dictionary falsely claims `EXPIRED_PUBLIC_DOMAIN` and freedom-to-operate. Never adopt those legal or clinical conclusions |
| `Tri-State Medical.pdf` | Public-source provider ontology, facilities and Indiana healthcare intelligence model | Database/jurisdiction mapping proposal, not proof of source API integration, authorization, up-to-date provider records or patient-consent approval |
| `TMRDS Personnel.html` | Existing UI assets/design ideas only | Contains manually authored data/UI; **not published** without specific privacy/source audit |
| `tmrds-dependency-audit.zip` | Historical 2026-11-16 dependency-security signal | Snapshot no longer defines installed main locks; verify current pinned runtime and CI before claiming any prior alert remains vulnerable |

**Important engineering conclusion:** For QRCE, retain useful mathematical primitives only as research algorithms subject to unit/invariant checks, reproducible baselines and independent scientific tests. Eliminate hardcoded `VALIDATED`, `SOLVER_CONVERGED`, `HEALED`, `EXPIRED_PUBLIC_DOMAIN`, fake QPU status, and unsupported medical regulatory claims from any promoted output. The actual repository already offers stronger source-aware PubMed, trial, ChEMBL and Open Targets adapters than the uploaded toy dictionaries.

## 3. Verification and acceptance

```bash
python -m pytest -q tests/test_public_crosscheck_routes.py
python -m pytest -q tests/test_public_gateway.py tests/test_open_medical_routes.py
python scripts/check_public_site.py
node --check public/site.js
docker compose -f compose.public.yml up --build -d
curl -fsS 'http://127.0.0.1:18080/api/v1/research/cross-check?query=CFTR&limit=1'
curl -fsS 'http://127.0.0.1:18080/api/v1/research/patent-landscape?ingredient=METFORMIN&limit=1'
```

The provided tests use mocked upstream responses and check fixed origins, size caps, source outages, invalid identifiers, exact-ID transitive joins, non-inference of legal clearance, and **no patient data writes**. GitHub CI exercises the Python API and frontend contract, while a successful production deployment and research validity require separate evidence. No clinical human-subject studies, outcome trials, patent counsel reviews, FDA clearance, or actual QPU benchmarks are performed by this integration.
