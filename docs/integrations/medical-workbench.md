# TMRDS open-source medical workbench: synthetic interoperability slice

**Date:** 2026-10-26  
**Intended use:** public-source biomedical research navigation plus opt-in, synthetic-only technical demonstrations. **No real patient records, image pixels, diagnosis, clinical treatment suggestions, or clinical sign-offs.**

This implementation does **not** constitute a clinical deployment, validated medical device, operational EHR, PACS, LIS, terminology license, HIPAA certification or FDA clearance.

## Implemented and routed in this change

- GET /api/v1/medical/stack — structured, 30+ project inventory with truthful deployment states, interfaces and cautions. No silent install or connection claims.
- GET /api/v1/medical/research-providers — previously merged, governed 12-provider research catalog. Connecting a ChatGPT plugin never supplies an API credential to TMRDS.
- GET /api/v1/medical/integration-status — explicit status of the actual integration layer.
- POST /api/v1/medical/synthetic/labs/trends — test-only FHIR R4 Observation subset. Enforces synthetic classification, synthetic IDs, LOINC code, UTC-normalized timestamps, UCUM identifiers, matching reference-range unit, finite bounded readings, resource count, uniqueness and an explicit prohibited-field allowlist. Groups tests by LOINC and UCUM without clinical normalization. Only computes arithmetic differences. Provides code-only public LOINC and topical PubMed links, *never* transmits submitted values.
- POST /api/v1/medical/synthetic/imaging/index — test-only FHIR R4 ImagingStudy metadata subset (DX, CR, CT, MR, etc.). Never ingests pixels, scans, patient IDs, diagnosis, image URLs or DICOM files.

The existing interoperability route, PubMed/Europe PMC/ClinicalTrials.gov/openFDA data pipelines, OHDSI/OMOP research code and FHIR R4 structural checks remain in place. This is additive, not a reimplementation.

## How to run the sandbox

By default, both POST endpoints return HTTP 403. Only a **nonproduction** test deployment with explicit opt-in enables them.

Set:

    TMRDS_ENV=development
    TMRDS_SYNTHETIC_WORKBENCH_ENABLED=true
    TMRDS_SERVICE_AUTH_REQUIRED=false

For local smoke testing only, with a trusted loopback API. Do not disable authentication on a shared or externally reachable network. The API-key gate, if configured, still applies.

Example:

    curl http://127.0.0.1:8000/api/v1/medical/integration-status
    curl http://127.0.0.1:8000/api/v1/medical/stack?category=imaging

Sample synthetic Observation POST:

    curl -X POST http://127.0.0.1:8000/api/v1/medical/synthetic/labs/trends \
      -H 'content-type: application/json' \
      -d '{"resources":[{"resourceType":"Observation","id":"synthetic-hemoglobin-a1c-1","meta":{"tag":[{"system":"urn:tmrds:data-classification","code":"synthetic"}]},"status":"final","code":{"coding":[{"system":"http://loinc.org","code":"4548-4"}]},"effectiveDateTime":"2026-01-01T12:00:00Z","valueQuantity":{"value":5.1,"system":"http://unitsofmeasure.org","code":"%","unit":"%"}}]}'

**Security:** Labels and IDs alone cannot prove de-identification. Never submit real or pseudonymized patient information, scan metadata, accession numbers, clinical notes or variant-level personal genomic data. A schema guard is not a HIPAA protection program.

## Integration status / rollout map

| Project group | Integrated here | Future clinical requirements |
|---|---|---|
| HAPI FHIR / OpenEMR / OpenELIS | R4 Observation contract for synthetic test input; metadata catalog only | Site-specific FHIR endpoints, SMART/OAuth or service JWT, patient consent, provenanced read/audit and separation of duties |
| Orthanc / OHIF / Cornerstone3D / DCMTK | Synthetic ImagingStudy metadata contract and project discovery; no DICOMweb transport | Authenticated DICOMweb QIDO/WADO/STOW, image-safe PACS network, viewer deployment, privacy controls, study/series provenance |
| LOINC / UCUM / Snowstorm / RxNorm | LOINC/UCUM structural checks and public identifiers; RxNorm pipeline already exists | Terminology licensing, vocabulary release pinning, FHIR $lookup/$translate validation, local code mappings |
| PubMed / Europe PMC / openFDA / ClinicalTrials.gov | Existing public research routes; new lab topic pointers contain **no** result values | Citation grading, systematic-review ranking, guideline provenance, cache/freshness, licensed clinical sources |
| OMOP / OHDSI ATLAS / Usagi / WhiteRabbit / DataQualityDashboard | Existing OMOP-related modules and catalog | Institutional ETL, CDM version lock, data-quality gates, cohort permissions and de-identification assessments |
| MONAI / 3D Slicer / nnU-Net / TorchIO / PyRadiomics / TIAToolbox | Project discovery only | Separate segregated imaging research compute, external validation, model card, intended-use classification, safety analysis |
| HL7 CQF / cTAKES / patient prediction | Catalog only | Privacy-preserving NLP, validated guideline representations, bias and calibration studies, clinician oversight |
| Synthea | Synthetic fixture target documented; no automatic generator installed | Pin toolchain, test data quality and keep fixtures segregated from authentic medical evidence |

## Release gates that remain **not satisfied**

1. Data-handling agreement, healthcare organization ownership, HIPAA privacy and security risk assessment, consent and institutional role-based access controls.
2. Updated intended-use statement and medical-device/CDS regulatory assessment **before** introducing real patient data or image processing.
3. Connector-specific secret storage, audited institutional endpoint onboarding, verified TLS, disabled public accessibility and data retention/deletion policies.
4. Provenance through FHIR DiagnosticReport → Observation → ImagingStudy → source accession, corrected/preliminary/final statuses, code-system versions and clinical annotation attribution.
5. OHIF / Orthanc / HAPI / OpenELIS image and data services actually deployed, security-scanned and tested with a purely synthetic dataset; no default admin credentials.
6. Clinical performance validation, protocol conformance testing (FHIR packages, DICOMweb, terminology), specialist evaluation, usability and accessibility testing.

**Do not set an operational-ready or clinical-ready badge based on GitHub CI.** The unit tests establish a test-only interoperability boundary, not evidence of diagnostic accuracy.

## Governance conventions

Research observations may display arithmetic trends but must not infer diagnoses, severity, triage, medication adjustment, imaging findings, or whether a test result is "normal". Reference intervals in synthetic inputs are **unverified examples** and cannot drive clinical status. Public literature links are topic-based and must never contain patient values or identifiers. Integrations must explicitly show NOT_CONNECTED until a real endpoint is separately verified.

See also: docs/INTENDED_USE.md, docs/reference/open-source-medical-software.md, docs/integrations/biomedical-connector-inventory.md.
