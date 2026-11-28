# Synthetic FHIR R4 ↔ OMOP CDM 5.4 research projection

**Status:** bounded local research implementation; not a certified ETL or clinical interface.

## Implemented subset

The in-memory `OMOPCDMBridge` accepts only FHIR R4 collection Bundles and projects these resource types:

| FHIR resource | OMOP target | Required semantics |
|---|---|---|
| Patient | PERSON | Caller supplies an explicit, unique OMOP `person_id` for each FHIR Patient ID |
| Condition | CONDITION_OCCURRENCE | `onsetDateTime` or `onsetPeriod.start` is required; `recordedDate` is not substituted for onset |
| Observation | MEASUREMENT | Only `status=final`, numeric finite `valueQuantity`, a code/text, and an effective date are projected |
| MedicationStatement | DRUG_EXPOSURE | Only active/completed statements with `effectiveDateTime` or `effectivePeriod.start`; this is a reported effective date, not proof of dispensing or administration |

A single-patient Bundle may use `person_id`. A multi-patient Bundle must use `person_id_map={fhir_patient_id: omop_person_id}`. IDs must be valid, positive, and one-to-one. Every clinical resource must reference a Patient resource in the same Bundle. The bridge rejects ambiguous or orphaned identities and does not silently assign all resources to person 1.

## Deliberately not projected

- `MedicationRequest` is reported as unsupported by this exposure projection. Its `authoredOn` value is an order-authored date, not an actual drug exposure start date.
- `DiagnosticReport` is not turned into a synthetic measurement. Its result references must be resolved to the child Observation resources.
- Non-final Observations and non-active/non-completed MedicationStatements are reported as skipped.
- Encounter, Procedure, AllergyIntolerance, ImagingStudy, and other resource types remain unsupported by this executable subset, even where the high-level domain catalog lists a possible OMOP target.

Unsupported records are returned in `skipped_resources` with a reason. Malformed supported records fail the import. Validation is completed before in-memory rows are committed, so a failed import leaves bridge state unchanged.

## Vocabulary and provenance limits

The bridge preserves source coding system/code and source text. It sets standard concept IDs to `0` because this implementation does not perform an Athena vocabulary lookup or prove a standard-concept mapping. A code string is not a standard OMOP concept ID. The algorithm-derived type concept ID is not evidence that the resource passed terminology validation.

The bridge keeps a small in-memory sidecar for the identifiers and source fields needed to reconstruct this subset. `to_fhir_bundle()` and `export_fhir_bundle()` reconstruct the supported fields from the projected rows and that sidecar. This is a bounded research round-trip, not a complete lossless FHIR-to-OMOP transformation: unsupported FHIR elements and domains are not represented.

## Execution and privacy boundary

- Pure in-memory Python transformation; no network access, database writes, file writes, external synchronization, or logging of resource payloads.
- Synthetic fixtures are used in automated tests.
- The caller is responsible for keeping any real records on an appropriately secured local system. Do not submit PHI to external biomedical, AI, IBM Quantum, or Amazon Braket providers.
- A caller-supplied synthetic label is not proof of de-identification.
- This implementation is not a live FHIR server, OMOP database loader, US Core profile validator, certified conformance result, clinical decision support feature, or medical device.

## Verification

Focused test:

```bash
python -m pytest -q tests/test_omop_cdm_bridge_roundtrip.py
```

Repository non-integration suite:

```bash
python -m pytest -q -m "not integration"
```

GitHub Actions results must be associated with the exact PR head SHA. A successful test run demonstrates the tested software contract only; it does not establish clinical validity, vocabulary correctness, institutional authorization, regulatory status, or production suitability.
