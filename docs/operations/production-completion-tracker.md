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


## Latest engineering run — 2026-11-28 16:42 UTC

- Main remains at `47739aa5f66c78b5f8a857aa365bebcf6c29bcad`; combined commit status returned no status entries and no PR-triggered workflow runs were returned for this merge commit. This is not evidence that all post-merge checks ran or passed.
- PR #87 remains open on `security/service-read-scope-20261128`, latest head `70c28014ddb07c5838480a4c078d59faf2446bbb`. Earlier head `e2f9b48f5869e12fe0c33764f09d45e079a5e690` had six successful workflows. Six new workflows were created for the latest head (TMRDS CI, Security and Interoperability, CodeQL, Supply Chain Security, QRCE Offline Workstation Real Integrations, Synthetic Imaging Tools); at last inspection they were queued/pending, so current-head validation remains open.
- PR #87 was extended with a route-audit correction: `scripts/audit_api_routes.py` now recognizes `require_service_read_identity` and emits `service_auth_scopes` metadata. Regression tests assert that the synthetic FHIR GET is classified as read-scoped and synthetic lab trend POST remains write-scoped. Commits: test `b3c0d8b2082c2e992f637f4cb6dfad15cad62adc`; implementation `70c28014ddb07c5838480a4c078d59faf2446bbb`.
- PR #87 has no submitted reviews as of this run. No merge was attempted. Its PR body now records the latest SHA and distinguishes earlier green workflow results from pending latest-head checks.
- PR #86 tracker branch had six successful workflows on head `b7ec55dd45c55d06a31d01135994693b2aad38e1`; no submitted reviews were returned. PR #86 remains open.

## Next bounded actions

1. Recheck all six workflows for PR #87 at exact head `70c28014ddb07c5838480a4c078d59faf2446bbb`; inspect and repair any failing job before requesting review.
2. Obtain independent review and establish required branch protection before merging PR #87 or documentation PR #86. The connected integration still cannot read/write repository rulesets; owner action in issue #28 remains outstanding.
3. Expand route-level authorization tests to cover all protected mutation/read routes, including synthetic imaging, public-record preview, evidence ingestion, and data-fabric sync. Preserve intentional public research routes.
4. Continue synthetic FHIR/OMOP/DICOM contract tests and disposable database migration/restore tests; keep results separate from standards certification.
5. Verify offline installation and signed artifact verification on clean supported hosts before considering distribution ready.


## Latest engineering run — 2026-11-28 16:46 UTC

- Repository default branch is `main`; the latest commit remains `47739aa5f66c78b5f8a857aa365bebcf6c29bcad`. No main-branch write or merge was performed.
- Open PR #86 (this tracker) and PR #87 (least-privilege service read scope) were confirmed by direct issue/PR fetches. Both have no submitted review records; no merge was attempted.
- PR #87 head advanced from `70c28014ddb07c5838480a4c078d59faf2446bbb` to `048eef7b1775b2af191da9810d49cd18d8e4f8d8`.
- CI at the previous PR #87 head `70c2801`: four of six workflows passed; TMRDS CI and Security/Interoperability failed. Full non-integration suite: 590 passed, 2 failed, 28 skipped, 16 deselected, 58 subtests passed. Both failures were the newly added route-audit tests not finding included medical workbench routes.
- Root cause: dependency lock resolves FastAPI 0.162.0, where `include_router()` stores lazy included-router tree nodes rather than flattening all APIRoutes into `app.routes`. The static route audit's flat `isinstance(route, APIRoute)` loop silently omitted nested endpoints.
- Corrective commit `048eef7b1775b2af191da9810d49cd18d8e4f8d8` updates `scripts/audit_api_routes.py` to use FastAPI's public `iter_route_contexts()` API and effective route contexts, with a fallback for older versions. PR #87 body records the failure evidence and correction.
- Six workflows were observed running on the exact new head `048eef7b1775b2af191da9810d49cd18d8e4f8d8`: TMRDS CI, Security and Interoperability, CodeQL, Supply Chain Security, QRCE Offline Workstation Real Integrations, and Synthetic Imaging Tools. At the time of this tracker update they were still in progress. No local test run is claimed.
- The failed prior CI run uploaded artifact `tmrds-ci-test-results` (artifact ID `15271782122`, SHA-256 `65a662e9caa4d9e7b38ed8eaa27c8fe61ea66feae3d07c64d0da72c9675e76bd`); it documents the failing head only, not a passing result.
- PR #86 and #87 both still require independent review and confirmation of applicable branch-protection gates. Issue #28 remains the owner action for enabling required branch rules. Issue #27 remains the independent clinical/privacy/safety promotion gate.

## Next bounded actions

1. Recheck all six workflows on PR #87 exact head `048eef7b1775b2af191da9810d49cd18d8e4f8d8`; inspect logs if any fail.
2. If CI is green, request independent review; do not merge without current-head passing required checks and confirmed approval requirements.
3. Continue endpoint-by-endpoint runtime authorization tests after the declared-route inventory is corrected; specifically verify `evidence.read` cannot mutate and `evidence.write` remains required for protected mutations.
4. Audit synthetic imaging, public-record preview, evidence ingestion and synchronization endpoints without changing intended public research routes.
5. Continue synthetic FHIR/OMOP/DICOM contracts, migration/restore tests, offline installation and signed artifact verification. Keep clinical and release approvals distinct.
