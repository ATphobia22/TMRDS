# Local EvidenceLedger format and integrity contract

## Purpose

`engines/evidence_ledger.py` provides a local JSONL execution/provenance log for bounded research workflows. It is not the authoritative biomedical evidence database, a clinical record, a digital signature system, or a trusted timestamp service.

## Record format

New entries use schema version 2:

- `schema_version`: integer `2`
- `ts`: UTC ISO-8601 write time
- `previous_hash`: SHA-256 of the immediately preceding entry, or 64 zeroes for the first entry
- caller-supplied operational metadata
- `content_hash`: SHA-256 of canonical JSON for all preceding fields, excluding `content_hash`

Canonical JSON sorts object keys, uses compact separators, UTF-8, and rejects NaN/Infinity and non-JSON values. The writer serializes same-process and cross-process appends with a sidecar OS lock, appends one JSONL record, flushes it, and calls `fsync`.

## Verification and compatibility

- `verify()` reads the complete file and checks every record before reporting success.
- V2 entries must link to the preceding record hash; edits, reordering, and interior deletion break verification.
- Existing v1 entries are verified using the original v1 serialization. A new v2 record anchors to the last valid v1 hash. The report labels this as `PARTIAL_LEGACY_PREFIX`; it does not pretend the legacy prefix had a hash chain.
- Malformed JSON, invalid UTF-8, blank lines, incomplete final lines, unsupported versions, mismatched hashes, and broken links fail closed.
- `append()` verifies the complete existing ledger before writing. It refuses to extend a corrupt file.
- `recent()` also verifies the full ledger; it never silently skips corrupt entries.
- `status()` reports `INTEGRITY_ERROR` rather than `READY` if verification fails.

## Security and privacy limitations

A SHA-256 chain detects accidental or unsophisticated modification of records when the current head is trusted. It does **not** prevent an attacker with write access from rewriting the whole file and recomputing every hash. It also cannot detect deletion of the final records unless the latest head hash is anchored independently.

For stronger audit evidence, export and sign the ledger head in a separately controlled system, protect the signing key outside this host, and retain immutable backups. Do not describe the local JSONL file as WORM storage, non-repudiation, or cryptographic proof of who created a record.

Never put PHI, patient identifiers, free-text clinical notes, genomic values, raw FHIR resources, credentials, or patient-linked packet hashes into this generic ledger. Keep private clinical context in an explicitly authorized, access-controlled local data store with encryption, retention, and deletion controls. The QRCE research orchestrator writes operational counts only; its patient reference, problem description, and packet hash are excluded from the ledger.

Newly created ledger files use restrictive owner-only permissions where supported. Existing file permissions, host encryption, backups, access controls, retention, and deletion remain operator responsibilities. The ledger is local by default and performs no network transmission.
