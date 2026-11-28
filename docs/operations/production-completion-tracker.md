# TMRDS Production Completion Tracker

**Project:** Tri-State Medical Research Discovery System (TMRDS) / Quantum Rubik's Cure Engine (QRCE)  
**Snapshot:** 2026-11-28  
**Scope:** This tracker applies only to `ATphobia22/TMRDS`. It does not track TSM or the River Valley game.

## Verified repository baseline

- Main commit at snapshot: `47739aa5f66c78b5f8a857aa365bebcf6c29bcad` (PR #85 squash merge).
- PR #84 service-authentication configuration hardening is merged as `acf1761281285d53dc6b32ea534e9bda2d0911cd`; the PR reported 13 successful checks.
- PR #85 API-key configuration fail-closed hardening is merged as `47739aa5f66c78b5f8a857aa365bebcf6c29bcad`; its exact head `450ca1e89a91c7be546ca3a1c962b6f642d93f09` reported 16/16 successful checks before merge.
- No open pull requests were returned immediately after PR #85 merged.
- Main's post-merge check run had 15 checks; several were still `in_progress` at this snapshot. Recheck the exact main SHA before release or another merge.
- GitHub reported repository admin/push capability for the user, but the connected integration's branch-protection read returned 403 and it exposes no branch-protection/ruleset write action. Do not infer that required protections are enabled.

## Release posture

**Infrastructure/software release:** conditional; only commit-specific passing checks count.  
**Clinical / patient-data deployment:** **NOT APPROVED**. Public and synthetic research only until independent intended-use, privacy/security, interoperability, clinical safety and institutional approvals are recorded. Passing CI is not clinical validation, HIPAA compliance, FDA clearance or deployment authorization.

## Completion workstream

| Workstream | State | Acceptance evidence / next action |
|---|---|---|
| Architecture and repository organization | Existing architecture is present; comprehensive audit incomplete | Inventory implemented modules and remove duplicate/stub paths with tests |
| Versioned data models and migrations | Partial / environment-dependent | Validate schema versions, migration ordering, rollback and disposable PostgreSQL/Neo4j tests |
| Authenticated API | **Recent P0 remediation merged** | Recheck main CI; audit every protected route and negative scope/tenant tests |
| Public biomedical adapters | Implemented in part | Source-by-source license/access review, rate limits, timeouts, freshness and citation tests |
| Evidence ledger and provenance | Implemented in part | Reproducible hash/signature, source lineage, immutable event and export-integrity tests |
| FHIR R4 / US Core / SMART OAuth2 PKCE | Not independently certified | Synthetic HAPI conformance, negative scope and tenant-isolation tests; no live write-back |
| OMOP / DICOM interoperability | Research components exist; integration evidence incomplete | Versioned mappings, de-identified/synthetic fixtures, conformance and round-trip tests |
| Classical CPU/GPU research | Available components; benchmark completeness unverified | Deterministic baselines, hardware/software manifests and reproducible performance reports |
| Quantum simulator / IBM / Braket | Adapter work exists; production validation unverified | Simulator equivalence tests; hardware disabled by default; no paid jobs without authorization |
| Workstation and offline runtime | Partial distribution surfaces exist | Clean install, offline dependency wheelhouse, checksum, startup and rollback tests |
| Security and privacy | P0 API-key/JWT fixes merged | Threat model, secret/log review, key rotation, retention/deletion, incident runbook and SBOM review |
| CI/CD and branch protection | Workflows exist; branch protection is an owner action | Owner configure PR/review/check rules, stale approval dismissal, resolved conversations, no force-push/delete |
| Monitoring and deployment | Runbook/metrics exist; alert receiver is placeholder | Verify staging probes, real alert routing, backup/restore and rollback drills |
| Signed distribution | Release verification workflow exists; signed published packages not verified | Build reproducibly, generate SBOM/provenance, sign and verify artifacts before publication |
| Durable completion reporting | This tracker | Update only with exact SHA, PR, workflow/test evidence, artifacts and blockers |


## Latest engineering run — 2026-11-28

- PR #86 tracker branch commit `533bb958dc28c0221a16c18b1bdec8100691be65`: six PR-triggered workflows were fetched and all six completed successfully (TMRDS CI, security/interoperability, CodeQL, supply-chain security, offline workstation integrations, and synthetic imaging). The review API returned no submitted reviews. PR #86 remains open; do not merge until review/protection requirements are established.
- PR #87: [least-privilege service read scope](https://github.com/ATphobia22/TMRDS/pull/87), branch `security/service-read-scope-20261128`, head `e2f9b48f5869e12fe0c33764f09d45e079a5e690`. It separates read (`evidence.read`) and write (`evidence.write`) service dependencies and applies read scope to the protected synthetic FHIR GET route. Regression tests were added for requested scopes and missing-read-scope denial.
- PR #87 CI was observed queued for all six workflows at this snapshot; combined commit status returned no status entries. No local test execution is claimed. PR #87 review API returned no reviews and the PR was not mergeable at creation.
- Main remains at `47739aa5f66c78b5f8a857aa365bebcf6c29bcad`; no main merge occurred in this run.

## Required owner action — issue #28

Configure main branch ruleset in GitHub settings. The current connector cannot read or write this administrative setting. Require pull requests, the exact stable CI/security/supply-chain/CodeQL checks, appropriate independent reviews, review of the latest push, resolved conversations, and block force-push/deletion. Verify a failing check actually prevents merge. Keep issue #28 open until this is demonstrated.

## Next bounded tasks

1. Recheck PR #87 workflows at exact head `e2f9b48f5869e12fe0c33764f09d45e079a5e690`; inspect failures, then request/obtain required review before merge.
2. Complete endpoint-by-endpoint authorization tests; retain intentional public research routes and verify write/clinical routes remain protected.
3. Recheck PR #86 current-head CI after this tracker update and obtain required review before merge.
4. Execute synthetic interoperability and disposable database migration/restore tests; publish reports, not unsupported compliance claims.
5. Validate offline installation and release artifact signing/verification; close clinical-promotion issue #27 only with independent evidence and qualified sign-offs.

## Safety and evidence rules

- Never upload PHI to external quantum or AI providers.
- No paid hardware jobs, paid infrastructure, credential changes, live EHR writes or public release publication without explicit authorization.
- Keep hardware submission disabled by default; label mocks and simulator output honestly.
- Never claim cure, clinical efficacy, quantum advantage, physical hardware execution, regulatory approval or HIPAA compliance without evidence.
- Record failures and unverified items as blockers; do not convert them to completed checkboxes.
