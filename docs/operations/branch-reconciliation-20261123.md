# TMRDS GitHub branch reconciliation and release proof — 2026-11-23

## Exact audited baseline

- Repository: [ATphobia22/TMRDS](https://github.com/ATphobia22/TMRDS), default branch `main`.
- Audited `main` commit: **`6d295e307b137e7c019b88bdfe0d54f487d3604f`**, squash merge of [PR #81](https://github.com/ATphobia22/TMRDS/pull/81).
- **Zero open pull requests**, cross-checked using GitHub PR search and the repository open-PR endpoint.
- **50 non-main branches inspected individually**, using GitHub's compare API against this exact commit. All 50 were accounted for: **33 `behind`, zero commits ahead; 17 `diverged` with historical squash/superseded histories**.
- **No unmerged current PR or safe missing feature commit was established**. Do not merge all 50 branch refs as a single operation. A squash merge integrates changes into a different new commit, so the old source branch still appears ahead/diverged even when its feature has been integrated. A wholesale merge can reintroduce outdated configs, dependencies or biomedical evidence policies.
- **Main is not branch-protected** in the visible GitHub repository branch status (`protected=false`). The repository owner must enable required checks and PR review requirements; neither workflow YAML nor an assistant can honestly claim this control is enabled.

## Full branch comparison

### 33 branches strictly behind main (ahead = 0)

These are exact ancestors of main with no commits left to incorporate at the audited snapshot. There is **nothing to merge** from them.

- `codex/tmrds-actions-current-pins-20261017`
- `codex/tmrds-alphafold-input-hardening-2026-10-17`
- `codex/tmrds-audit-followup-20261017`
- `codex/tmrds-live-population-annotations-2026-10-17`
- `codex/tmrds-post-merge-audit-2026-10-15`
- `codex/tmrds-release-gates-2026-10-17`
- `codex/tmrds-release-gates-audit-20261017`
- `codex/tmrds-remediation-rebased-2026-10-15`
- `codex/tmrds-repository-remediation-2026-10-15`
- `codex/tmrds-scientific-backend-truth-2026-10-17`
- `dependabot/pip/fastapi-0.162.0`
- `dependabot/pip/pytest-asyncio-1.4.1`
- `dependabot/pip/starlette-1.10.0`
- `dependabot/pip/websockets-17.3`
- `deps/fastapi-coordinated-20261025`
- `docs/clinician-patient-safety-roadmap-20261025`
- `feat/biomedical-provider-registry-20261026`
- `feat/free-imaging-validation`
- `feat/free-research-integrations`
- `feat/imaging-research-sandbox`
- `feat/imaging-research-workflow`
- `feat/research-evidence-display-contract-20261025`
- `feat/research-evidence-dossier`
- `feat/research-medical-workbench-20261026`
- `feat/source-telemetry`
- `fix/api-key-auth-fail-closed-20261025`
- `fix/api-key-header-and-log-safety-20261025`
- `fix/coordinated-dependency-pins-20261025`
- `fix/medical-connectors-truthful-synthetic-fhir-20261026`
- `fix/research-stub-scientific-integrity-20261025`
- `fix/smart-discovery-truthful-20261025`
- `quantum-integration`
- `test/fastapi-request-compatibility-20261025`

### 17 divergent historical branches

The table distinguishes a historical merge commit from an unmerged working change; a Git compare `ahead` count alone is not a backlog.

| Source branch | Historical resolution | Decision |
|---|---|---|
| `dependabot/github_actions/actions/dependency-review-action-5.0.1` | #63 closed; superseded by #71 | No wholesale replay; retain branch for audit |
| `dependabot/pip/python-multipart-0.0.34` | #67 closed; superseded by #71 | No wholesale replay; retain branch for audit |
| `deps/consolidated-main-green-20261122` | #60 squash-merged | No wholesale replay; retain branch for audit |
| `deps/pages-actions-python-audit-20261123` | #71 squash-merged | No wholesale replay; retain branch for audit |
| `docs/readme-governed-cube-20261123` | #73 squash-merged | No wholesale replay; retain branch for audit |
| `feat/governed-pathway-cube-20261123` | #72 squash-merged | No wholesale replay; retain branch for audit |
| `feat/gwas-v2-evidence-fabric-20261123` | #61 squash-merged | No wholesale replay; retain branch for audit |
| `feat/live-research-api-entry-monitor-20261123` | #77 squash-merged | No wholesale replay; retain branch for audit |
| `feat/medical-open-source-gateway-20261123` | #74 squash-merged | No wholesale replay; retain branch for audit |
| `feat/offline-fieldlab-real-open-source-adapters-20261123` | #81 squash-merged | No wholesale replay; retain branch for audit |
| `feat/offline-swarm-laptop-workstation-20261123` | #80 squash-merged | No wholesale replay; retain branch for audit |
| `feat/public-evidence-atlas-pages-20261122` | #58 squash-merged | No wholesale replay; retain branch for audit |
| `feat/qrce-crosscheck-openmi-patent-evidence-20261123` | #75 squash-merged | No wholesale replay; retain branch for audit |
| `feat/qrce-grover-six-plane-benchmark-20261123` | #78 squash-merged | No wholesale replay; retain branch for audit |
| `feat/qrce-offline-workstation-real-adapters-20261123` | #79 squash-merged | No wholesale replay; retain branch for audit |
| `feat/qrce-omnicrosscheck-source-fabric-20261123` | #76 squash-merged | No wholesale replay; retain branch for audit |
| `fix/pages-europepmc-lite-timeout-20261122` | #59 squash-merged | No wholesale replay; retain branch for audit |

For the listed feature PRs, the code was squash-merged and remains present under the current architecture, as confirmed by main's actual modules and recent workflow gates. The two Dependabot refs were closed as superseded in the pinned dependency consolidation. **Do not claim their original PRs were individually merged.** If a particular historical feature is suspected to be missing, compare its *specific file contents and contracts* against current main and open a targeted, regression-tested PR—not a 2026-10/2026-11 branch-wide replay.

## Current integrated deliverables — code versus deployment

| Surface | Audited implementation | Independent verification |
|---|---|---|
| Public research site | Animated 26-cubie Rubik display, Europe PMC / ClinicalTrials.gov / Crossref direct searches, read-only Python research backend | GitHub Pages workflow passed on `6d295e30`; separate Render research service previously independently verified at `23aeca451` |
| QRCE science | 22-adapter bounded metadata cross-check, PMID/PMCID/DOI/NCT identity joins, original PMC and PubChem reference queries, six-plane Grover statevector benchmark | Python governance, scientific and end-to-end CI gates green; not evidence of a cure or hardware quantum advantage |
| Offline scientific readers | Real pinned pydicom, NiBabel, Biopython, RDKit, NumPy, pypdf in **separate** controlled profiles | [PR #79](https://github.com/ATphobia22/TMRDS/pull/79) and [PR #81](https://github.com/ATphobia22/TMRDS/pull/81) merged; Windows 11 x64 actual library tests and no-index wheel installation passed |
| Offline specialist UI | Seven-page JSON-RPC research micro-app profile and a distinct nine-page stdlib/loopback synthetic fallback | [PR #79](https://github.com/ATphobia22/TMRDS/pull/79), [PR #80](https://github.com/ATphobia22/TMRDS/pull/80) merged; separate operation modes, not a single interoperable clinical system |
| Windows deliverable | Hash-inventoried, tested offline wheelhouse ZIP with PowerShell installation; local Tkinter FieldLab | `TMRDS Offline FieldLab Libraries and Win11 Wheel Bundle` job **45173817549** passed Windows real-reader and artifact-upload steps on `6d295e30`; still **requires separately installed Python 3.11 x64**; not a native installer or independent on-device medical validation |
| Medical imaging | Isolated synthetic Orthanc DICOMweb, OHIF research-mode build, MONAI bundle gates | `Synthetic Imaging Tools` workflow green; **does not** make imaging diagnosis, segmentation AI clinical-grade, or public patient ingestion live |
| Clinical/rights | No AlphaFold 3 trained weights bundled, no licensed human cohort/PHI in public website, no actual hospital/EHR authorization | Research and license-policy contracts checked in CI only; organizational approvals and independent performance/security studies remain prerequisites |

### Exact merged-baseline workflow gates

All of the following **completed successfully** on `6d295e30`:

- TMRDS Public Evidence Atlas (GitHub Pages).
- TMRDS Security and Interoperability.
- TMRDS Supply Chain Security.
- TMRDS Governed Pathway and Source Audit.
- QRCE Offline Workstation Real Integrations.
- TMRDS CodeQL.
- TMRDS CI.
- TMRDS Offline FieldLab Libraries and Win11 Wheel Bundle — Linux parser/egress tests and Win11 x64 reader/bundle tests **both successful**.
- Synthetic Imaging Tools.
- Dependabot pip graph updater (separate dependency graph job, not a code release gate).

Official workflow runs: [GitHub Actions for TMRDS](https://github.com/ATphobia22/TMRDS/actions). Exact commit [`6d295e30`](https://github.com/ATphobia22/TMRDS/commit/6d295e307b137e7c019b88bdfe0d54f487d3604f).

### Install/test the current offline workstation

Review the full [FieldLab offline operator instructions](../integrations/fieldlab-offline-workstation-20261123.md) and [portable wheelhouse instructions](portable-offline-workstation.md). Use the latest successful Windows workflow artifact, verify its ZIP/wheel hashes, transfer it before disconnecting, and install **Python 3.11 x64** first. A trustable offline installation is *not* a released clinical diagnostic or regulatory-certified device.

**Do not** claim a free public research website can ingest real patient studies, run GPU model weights (AlphaFold 3, Boltz, MONAI) or decode every imaging variant. New clinical tasks need a separate encrypted, authenticated local stack, source licensing, registered medical-device risk assessment, actual validated models and independent local performance data.

## Process for future branches

1. Search *open* PRs first and verify each exact head SHA and required workflow gate; merge only after success.
2. Compare each non-main branch against current main and check associated merged PRs before proposing a merge.
3. For `behind` branches, no merge is needed; for squash-diverged branches, perform **specific file/behavior reconciliation**, not wholesale branch merging.
4. Open one focused PR, preserve security and scientific provenance contracts, and verify **new main** CI after merge. Do not report a skipped deployment as a passing deployment.
5. Enable branch protection/rulesets in owner settings; retain old branches as audit records unless explicitly approved for deletion.
