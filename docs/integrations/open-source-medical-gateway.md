# Open-source biomedical integrations — research gateway

Reviewed: **2026-11-23**. Source links and contracts are supplied for an
implementation audit, not a claim that all upstream systems were installed.

## Shipped in this change

- `public/medical-projects.json`: **41** official project/homepage
  references categorized by clinical system, imaging, molecular modeling,
  interoperability, LIMS, mobile, genomics and research. Each has
  `integration_state`, `license_notes`, and `verification`; a referenced
  project is **not a deployed connector**.
- `public/index.html`, `site.js` and `site.css`: searchable,
  filterable open-source platform cards plus two real-source research-only
  panels. The site preserves the rotating 3D Rubik's Cube.
- `GET /api/v1/research/medical-projects[?category=imaging]`: serves the
  same static project catalog used by GitHub Pages. No network probes or
  patient records are performed by catalog lookup.
- `GET /api/v1/research/pubmed-citations?query=CFTR&limit=5`: invokes the
  **existing** bounded PubMed/NCBI E-utilities adapter. Reports PMID,
  publication title, journal, publication date and official PMID link.
  Withholds abstracts and third-party article bodies. A failed upstream
  lookup reports `source_unavailable`, not `no scientific evidence`.
- `GET /api/v1/research/alphafold-db/P13569`: retrieves one
  **AlphaFold Protein Structure Database** response through fixed HTTPS,
  no redirects, 1 MiB response ceiling and 12-second timeout. It checks
  the UniProt accession, validates downloadable links to the official host,
  retains source version/pLDDT only when reported, and computes a SHA-256
  over the explicitly selected metadata fields.
- `GET /api/v1/research/alphafold3-status`: explicit
  `not_configured` with license and weights restrictions; never
  submits a job or pretends that AlphaFold DB predictions are AlphaFold 3.
- Synthetic-local Orthanc/DICOMweb and OHIF, MONAI mask-metric tools, and
  bounded research records already in TMRDS remain available through
  their **separate existing workflows**. This change makes no public
  clinical source ingress or PACS connection.

## Frontend-to-backend topology

```text
PUBLIC GITHUB PAGES
  ├── animated 26-cubie Rubik search indicator
  ├── Europe PMC and ClinicalTrials.gov browser-side source lookups
  └── 41-project read-only JSON registry [reference and status, not live health]

ISOLATED SELF-HOSTED RESEARCH API (Dockerfile.public + compose.public.yml)
  ├── same-origin website / backend-config.json=enabled
  ├── /api/v1/research/pubmed-citations
  │     └── bounded NCBI PubMed E-utilities citation metadata
  ├── /api/v1/research/alphafold-db/{UniProt}
  │     └── EMBL-EBI AlphaFold DB structure-prediction metadata
  ├── /api/v1/research/medical-projects
  ├── /api/v1/research/dossier [eight policy-gated metadata providers]
  ├── /api/v1/research/evidence-pathway [source-reported exact-ID links]
  └── /api/v1/research/alphafold3-status [not configured]

SEPARATE, INSTITUTION-CONTROLLED CLINICAL SYSTEMS (NOT DEPLOYED HERE)
  OpenEMR / OpenMRS / Bahmni / GNU Health / Medplum
  HAPI FHIR / Blaze / Open Integration Engine
  Orthanc / dcm4chee / OHIF / OpenELIS / LIMS
  └── FHIR / DICOMweb / HL7v2 boundaries require explicit contracts,
      authorization, deidentification, audit, isolation and organization approval
```

GitHub Pages is **static** and has the backend explicitly disabled.
The backend Docker service listens on loopback by default. The public
UI never requests cookies, accepts patient datasets, or calls arbitrary
URLs typed by a visitor.

Run the research-only Docker variant:

```bash
docker compose -f compose.public.yml up --build -d
curl -fsS http://127.0.0.1:18080/api/v1/research/medical-projects
curl -fsS 'http://127.0.0.1:18080/api/v1/research/pubmed-citations?query=CFTR&limit=3'
curl -fsS http://127.0.0.1:18080/api/v1/research/alphafold-db/P13569
curl -fsS http://127.0.0.1:18080/api/v1/research/alphafold3-status
```

For institutional FHIR/HL7/PACS implementation, stage a distinct *private*
stack with pinned/reviewed container digest and no public host bindings.
Never use literal example passwords or unpinned `latest` EHR/PACS/router
images in production. Connect only preapproved test servers, with test
fixtures or independently verified deidentified data. Do not expose
HL7 MLLP (e.g., 6661), DICOM DIMSE (4242), PACS UI (8042) or FHIR
datastores on public IPs. Use service identity/SMART authorization,
TLS/mTLS, access/audit logs, rate limits, consent and per-record governance
before any real clinical exchange.

### Proposed future synthetic-local FHIR/DICOM workflow (not deployed)

1. Generate patients and ImagingStudy fixtures from Synthea or TMRDS's
   synthetic workbench, including deterministic `urn:uuid` references.
   Never reuse actual patient names, IDs, DICOM tags or images.
2. Load ONLY those synthetic fixtures into a local isolated HAPI FHIR
   instance with OIDC/SMART test client registration and a private network.
3. Load only generated synthetic DICOM instances into an isolated Orthanc
   and turn on a reviewed DICOMweb plugin with auth. **Do not assume** the
   OHIF plugin is enabled by a single undocumented environment variable.
4. A governed translation service can create `ImagingStudy` metadata
   referencing a whitelisted synthetic WADO-RS origin. Validate UID
   referential integrity, matching Patient references, `application/dicom+json`,
   date precision and FHIR R4 conformance.
5. Add a separate approvals gate for OpenEMR/OpenMRS/Bahmni FHIR,
   OpenELIS laboratory observations, and clinical note NLP. A vendor
   being 'open source' is neither patient consent nor API authorization.

## AlphaFold 3 versus AlphaFold DB

The official `google-deepmind/alphafold3` **code is Apache-2.0**,
but its **trained parameters and generated outputs have separate,
restricted noncommercial terms**. Official weights are **not** copied,
downloaded, embedded or served by TMRDS. This implementation performs
**no AlphaFold 3 inference**. AlphaFold DB prediction metadata is a
different service, with per-entry attribution and license terms.

Any eventual local AF3 inference will require eligibility/terms review,
versioned local model/environment manifests, model checksum recording,
approved hardware, input provenance, confidence-field validation,
and independently assessed experimental performance. Predictions alone
do not substantiate treatment efficacy.

Official references:
- [AlphaFold 3 repository](https://github.com/google-deepmind/alphafold3)
- [AlphaFold 3 weights and output restrictions](https://github.com/google-deepmind/alphafold3/blob/main/WEIGHTS_TERMS_OF_USE.md)
- [EMBL-EBI AlphaFold DB](https://alphafold.ebi.ac.uk/)
- [NCBI E-utilities](https://www.ncbi.nlm.nih.gov/home/develop/api/)
- [OpenEMR FHIR API](https://github.com/openemr/openemr/blob/master/FHIR_README.md)
- [OpenMRS FHIR2 module](https://github.com/openmrs/openmrs-module-fhir2)
- [Orthanc DICOMweb plugin](https://orthanc.uclouvain.be/book/plugins/dicomweb.html)
- [HAPI FHIR](https://github.com/hapifhir/hapi-fhir)
- [MONAI](https://github.com/Project-MONAI/MONAI)
- [AlphaFold 3 paper (Nature 2024)](https://pubmed.ncbi.nlm.nih.gov/38718835/)
- [MONAI original framework report](https://arxiv.org/abs/2211.02701)

The two papers above were identifier-checked and screened for known
retractions on 2026-11-23; that does not authenticate their findings
or imply the software provides clinical-grade evidence.

## Gates and acceptance scope

```bash
python -m pytest -q tests/test_open_medical_routes.py tests/test_public_gateway.py
python scripts/check_public_site.py
node --check public/site.js
docker build -f Dockerfile.public -t tmrds-research:test .
```

Tests use a mocked HTTP transport for EBI and an isolated mocked PubMed
source result; **no live EHR/PACS records** are read. Independent live
source checks, clinical conformance, legal data-use approvals and
cloud deployment are not proven by green unit/CI tests.
