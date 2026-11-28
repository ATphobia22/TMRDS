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


## Latest engineering run — 2026-11-28 16:47 UTC

- PR #87 route-inventory correction exposed an additional security gap after the first scanner fix. The prior flat scan had silently omitted nested FastAPI routes; once the public `iter_route_contexts()` iterator was used, the CI route audit identified five POST endpoints without a declared auth dependency:
  - `POST /api/v1/cube/structure/predict`
  - `POST /api/v1/cube/quantum/vqe`
  - `POST /api/v1/governance/ai/validate`
  - `POST /api/v1/evidence/semantic-search`
  - `POST /api/v1/interoperability/fhir/validate`
- These are research read/compute/validation operations, not evidence writes. To avoid treating POST as permission to accept arbitrary unauthenticated input, the PR now declares `require_service_read_identity` on all five. The FHIR validator can accept resource-shaped payloads, so the route is not left publicly callable merely because it validates rather than persists data.
- Test-first commit `19622a967fe3cd8608621a27304b83d338c559af` asserts all five endpoints are declared `evidence.read` routes. Implementation commits: `914da138a9baf4c7c89bdf674c6cb2a90034649a`, `79e1c719dfe4f3da6c0eda1a5692e4c4fd097645`, `2e92b35e33f4030bc7dca5a330e8f07105757e7f`, `df4571ac0d5cda6026f89a2f08b57fd99c946516`.
- PR #87 current head is `df4571ac0d5cda6026f89a2f08b57fd99c946516`. Six workflows were observed for this exact head: TMRDS CI in progress; Security/Interoperability queued; CodeQL pending; Supply Chain Security pending; QRCE Offline Workstation Real Integrations queued; Synthetic Imaging Tools queued. No result is yet green or failed on this head.
- The route inventory is static declared-dependency evidence only. Runtime service authentication remains conditional on production mode or `TMRDS_SERVICE_AUTH_REQUIRED=true`; validate the actual JWT scope behavior in the follow-on runtime tests.
- PR #87 still has no submitted review. PR #86 tracker PR still has no submitted review. No merge was attempted.

## Next bounded actions

1. Recheck all six workflows on exact PR #87 head `df4571ac0d5cda6026f89a2f08b57fd99c946516`.
2. Inspect route-audit artifact and confirm route count plus no unguarded writes; run full unit suite after audit stage passes.
3. Add/verify runtime negative tests for `evidence.read` vs `evidence.write` on the five routes; ensure no patient payload is sent to external providers.
4. Obtain independent review and owner-confirmed branch protection before any merge.
5. Continue synthetic FHIR/OMOP/DICOM and migration/restore validation, then offline distribution and signed-artifact tests.


## Latest engineering run — 2026-11-28 16:48 UTC

- PR #87 exact head `df4571ac0d5cda6026f89a2f08b57fd99c946516` now has these confirmed workflow results:
  - TMRDS CI: **success**. Route audit: 72 routes, zero duplicate method/path pairs, zero POST/PUT/PATCH/DELETE routes without a recognized declared auth dependency. Python compile, Docker Compose config, Docker image build, container liveness, focused IBM quantum tests, and full non-integration tests passed.
  - Full non-integration suite: **593 passed, 28 skipped, 16 deselected, 58 subtests passed, 1 warning**.
  - Security and Interoperability: **success**.
  - CodeQL: **success** for Python and GitHub Actions.
  - Supply Chain Security: **success** for dependency-change review and locked dependency audit.
  - Synthetic Imaging Tools: MONAI metrics, public documents, and synthetic imaging jobs succeeded; OHIF research build was still running at this snapshot.
  - QRCE Offline Workstation Real Integrations: local-policy contract succeeded; Windows binary packaging was still queued at this snapshot.
- PR #87 body updated with exact-head validation and remaining workflow states. PR #87 still has no submitted review; do not merge while OHIF/Windows jobs remain unfinished or independent review/branch-protection requirements are unconfirmed.
- PR #86 tracker updated to record the lazy-router inventory failure, the five additional unguarded POST routes, their read-scope hardening, and the current CI evidence. Its updated documentation commit is `5b1e405776c76a2775c1f9e5d9cbc33f10b5df0d`; PR checks for this latest tracker commit must be rechecked separately.
- No main-branch merge occurred. Main remains `47739aa5f66c78b5f8a857aa365bebcf6c29bcad`. No branch protection write/read capability is exposed by the connected GitHub toolset; issue #28 remains the owner action.

## Next bounded actions

1. Recheck the OHIF research build and Windows binary packaging workflows for exact PR #87 head `df4571ac0d5cda6026f89a2f08b57fd99c946516`.
2. If both pass, request independent review and confirm branch protection/approval gates before merge.
3. Recheck the latest PR #86 tracker commit workflows and obtain review.
4. Continue runtime scope denial tests and audit any further endpoints revealed by route inventory; preserve public GET research routes intentionally.
5. Move to synthetic FHIR/OMOP/DICOM conformance and database migration/restore testing only after this security PR is resolved.


## Latest engineering run — 2026-11-28 16:51 UTC

- PR #87 advanced to exact head `f9386dc78c14af6d324b141d07a21978deb134c2` (16 commits, 10 changed files). The service read-scope change now covers the synthetic FHIR GET route plus the five research/validation POST routes enumerated in the PR description. The deterministic route audit recognizes read scopes and expands FastAPI >=0.137 lazy included-router contexts through the public `iter_route_contexts()` API.
- FHIR validation now requires a `synthetic-*` fixture ID and exact `meta.tag` classification `urn:tmrds:data-classification=synthetic`. Response metadata explicitly states that the tag is an unverified caller attestation, that no persistence is enabled, and that no external transmission occurs. Regression tests cover accepted synthetic fixture, missing classification, and non-synthetic ID. This is not proof of de-identification; real patient data must not be submitted to this endpoint.
- Six fresh workflows were queued/pending on exact head `f9386dc78c14af6d324b141d07a21978deb134c2`: TMRDS CI, Security and Interoperability, CodeQL, Supply Chain Security, Synthetic Imaging Tools, and QRCE Offline Workstation Real Integrations. Prior-head successes do not validate this latest FHIR boundary change.
- PR #87 has no submitted independent review. No merge attempted.
- PR #86 tracker branch head `5b1e405776c76a2775c1f9e5d9cbc33f10b5df0d` workflow snapshot: Supply Chain Security success; QRCE Offline Workstation Real Integrations success; Synthetic Imaging Tools in progress; TMRDS CI, Security/Interoperability, and CodeQL canceled after subsequent documentation pushes. PR #86 has no submitted review and remains open.
- Main remains `47739aa5f66c78b5f8a857aa365bebcf6c29bcad`. Issue #28 still records `main.protected=false` (last verified 2026-10-25); no ruleset administration is available through the connected GitHub integration. Owner must establish and verify required PR, review, and check enforcement before merge.

## Next bounded actions

1. Recheck all six workflows for exact PR #87 head `f9386dc78c14af6d324b141d07a21978deb134c2`; repair any failure before review.
2. Verify route-audit output contains all expected read/write scopes and zero unguarded state-changing routes.
3. Confirm FHIR synthetic marker tests pass and keep the response wording explicit that a marker is an unverified attestation, not de-identification.
4. Obtain independent review and owner-confirmed branch protection before merging either open PR.
5. After this security gate, continue synthetic FHIR/OMOP/DICOM contract and migration/restore tests, then clean-host offline install and signed-artifact verification.


## Latest engineering run — 2026-11-28 17:43 UTC

- Repository `main` remains at `47739aa5f66c78b5f8a857aa365bebcf6c29bcad`. The open PRs are #86 (this tracker) and #87 (service read/write scope hardening). No main-branch write or merge occurred.
- PR #87 exact head `f9386dc78c14af6d324b141d07a21978deb134c2` completed all six required project workflows successfully: TMRDS CI, Security and Interoperability, CodeQL, Supply Chain Security, Synthetic Imaging Tools, and QRCE Offline Workstation Real Integrations. The six corresponding run IDs were `46167297614`, `46167297649`, `46167297611`, `46167297635`, `46167297669`, and `46167297622`. This validates that exact head only.
- Added route-level authorization integration tests on PR #87 in commit `775a34ba03659500fb2f9b14bfadf104fa5fb5e1` (`tests/test_service_auth_route_scopes.py`). The four cases exercise actual FastAPI requests using ephemeral RSA/JWKS credentials and synthetic fixtures: `evidence.read` `evidence.write` token separation on FHIR validation and synthetic lab transformation. The test commit's six workflows were in progress at the last check; no result for this new head is claimed yet.
- PR #86 exact head `b914074e06889fae1ba7b7f58faf3a061ee05d8f` had all six project workflows complete successfully (run IDs `46167356556`, `46167356534`, `46167356543`, `46167356586`, `46167356479`, and `46167356463`). This is evidence for the prior tracker head; this append-only update will trigger a fresh PR #86 validation cycle.
- PR #87 and PR #86 review endpoints both returned no submitted reviews. GitHub reports `main.protected=false` and required status checks disabled on the branch object. A direct branch-protection API request is forbidden to the connected integration (HTTP 403), so ruleset details cannot be independently read through this connection. Issue #28 remains an owner/admin action; no merge was attempted.
- No patient data, paid services, remote quantum hardware jobs, live EHR writes, credential changes, or public release publication were used.

## Next bounded actions

1. Recheck all six workflows on PR #87 exact head `775a34ba03659500fb2f9b14bfadf104fa5fb5e1`; inspect and repair any route-level JWT scope test failure before requesting review.
2. Recheck PR #86 after this tracker append; retain the exact tracker commit and all six workflow results.
3. Obtain independent PR review and have the repository owner enable/verify required main branch protections before merging either PR.
4. After the authorization PR is reviewed and safely integrated, move to synthetic FHIR/OMOP/DICOM conformance and disposable PostgreSQL/Neo4j migration/restore tests. Do not describe these as certification.
5. Continue clean-host offline installation and signed artifact verification; no distribution publication without explicit authorization.


## Latest engineering run — 2026-11-28 17:55 UTC

- PR #87 current head `775a34ba03659500fb2f9b14bfadf104fa5fb5e1`: all six required workflows passed (TMRDS CI, Security and Interoperability, CodeQL, Supply Chain Security, QRCE Offline Workstation Real Integrations, Synthetic Imaging Tools). The originally requested `f9386dc78c14af6d324b141d07a21978deb134c2` also has all six passing. Additional current-head checks passed, including Windows packaging, dependency audit, route/security analysis, synthetic imaging, MONAI metrics, and OHIF research build.
- PR #87 remains open; no independent review is recorded. Main metadata reports `protected=false`. Branch-protection GET returns HTTP 403 to the connected integration, and no branch-protection/ruleset write action is exposed. Issue #28 remains an administrator action. A status comment was added to PR #87 and issue #28; no self-approval, protection bypass, or merge was attempted.
- PR #88 opened: [deterministic local two-qubit statevector VQE](https://github.com/ATphobia22/TMRDS/pull/88), branch `feat/local-vqe-statevector-20261128`. Adds a NumPy CPU statevector simulation for the synthetic Hamiltonian `H = -Z0 Z1 - X0 X1`, bounded deterministic grid VQE, exact 4x4 eigenspectrum comparison, normalized statevector receipt, canonical SHA-256 digest, tests, offline CLI runner, and documentation. This is a mathematical software benchmark only; no molecular/clinical input, PHI, external service, paid compute, IBM/Braket hardware, or quantum-advantage claim is involved.
- PR #88 head `8cc953b559a669d6a914ad85d443ac7ff504656c`: CI was still queued/in progress at the time of this update; do not mark the new simulator as CI-verified until all six workflows finish on this exact head. No local repository test run is claimed.
- Distribution evidence on PR #87 current head: Windows Python 3.11 offline wheelhouse job passed. Artifact `tmrds-offline-python311-win-x64-research-preview`, ID `15273694304`, 50,419,049 bytes, expires 2026-12-05. The workflow explicitly describes this as a portable Python wheelhouse, **not** a standalone executable. It checksum-verifies wheels, installs in offline no-index mode, and exercises real pydicom MR pixel data, Biopython FASTQ, RDKit SDF, and pypdf.
- Interoperability status remains research-only: FHIR validation is synthetic-only and caller tags are not independent de-identification proof; OMOP/DICOM still require end-to-end conformance and round-trip evidence. Clinical deployment, live EHR write-back, signed public release, and regulatory claims remain blocked.

## Next bounded actions

1. Recheck PR #88's six workflows on exact head `8cc953b559a669d6a914ad85d443ac7ff504656c`; inspect test/build failures and repair with regression tests.
2. Obtain independent maintainer reviews for PRs #86, #87, and #88; an authorized repository administrator must enable and demonstrate main branch protection under issue #28.
3. Integrate the local simulator into a governed QRCE research interface only after the PR is reviewed and merged; keep it separated from biomedical result generation.
4. Continue synthetic FHIR/OMOP/DICOM round-trip testing and disposable-database migration/restore validation; record each exact fixture/version and outcome.
5. Verify Linux/macOS/Windows clean-host installation, artifact checksums, SBOM/provenance, signing and signature verification. The existing Windows artifact is a wheelhouse preview, not a signed standalone release.
