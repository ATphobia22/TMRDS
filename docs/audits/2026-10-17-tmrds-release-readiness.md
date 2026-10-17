# TMRDS Release-Readiness Audit

**Audit date:** 2026-10-17  
**Repository:** [ATphobia22/TMRDS](https://github.com/ATphobia22/TMRDS)  
**Baseline main SHA:** `27ef61b07359b088b342213d51650fe1210bc222`  
**Scope:** release engineering, dependency governance, workflow security, route inventory, model-execution status, and feature boundaries.

## Current follow-up status

The release-gate follow-up is merged on `main` at `75784c07e19fafa4733613bd481d4a238d5a0c14`. On that exact commit, these workflows completed successfully:

- [TMRDS CI](https://github.com/ATphobia22/TMRDS/actions/runs/39054866443)
- [TMRDS Supply Chain Security](https://github.com/ATphobia22/TMRDS/actions/runs/39054866456)
- [TMRDS CodeQL](https://github.com/ATphobia22/TMRDS/actions/runs/39054866463)
- [TMRDS Security and Interoperability](https://github.com/ATphobia22/TMRDS/actions/runs/39054866471)

The repository's `main` branch protection remains disabled and must be configured manually by the repository owner. Green workflow runs do not enforce review or required checks.

## Baseline evidence

At audit time, GitHub Actions reported the baseline `main` commit as successful for:

- [TMRDS CI](https://github.com/ATphobia22/TMRDS/actions/runs/38801911323)
- [TMRDS Security and Interoperability](https://github.com/ATphobia22/TMRDS/actions/runs/38801911327)

The inspected Security and Interoperability run logged **147 passed, 4 skipped, 16 deselected, 1 warning, and 19 subtests passed**. Its route inventory reported 25 routes, no duplicate method/path definitions, and no write routes lacking a recognized declared authentication dependency. These are baseline results, not results for the changes in this follow-up, and not proof of complete authorization correctness.

## Findings and follow-up changes

| Finding | Evidence / risk | Remediation |
|---|---|---|
| Dependency declaration and lock drift was only partially checked | The existing validator checked the test pair, but not the runtime pair or aliases. Dependabot could update `requirements-lock.txt` while the canonical `requirements.lock` remained stale; an existing NumPy update proposal demonstrated a lock-gate failure. | Validate both declaration/lock pairs, enforce byte-identical aliases, and verify shared direct package pins match. Document controlled dependency updates. |
| Redis was declared but no external adapter existed | `DualTierMemory` stores values in in-process `OrderedDict` objects and contains no Redis client wiring. Calling this deployment Redis-ready overstates current capabilities. | Remove the unused runtime declaration and clarify the architecture matrix and dependency-management docs. Redis remains deferred until an adapter is implemented and tested. |
| Workflow actions used mutable version tags | Existing workflows referred to tags such as `@v4` and `@v5`, which can move to another commit. | Pin actions to reviewed full commit SHAs and add an automated check for immutable references and explicit workflow permissions. |
| Secret scanning could skip an entire line | A configured allowlist marker caused the scanner to ignore all patterns on that line. A benign comment like `example.invalid` could hide another secret-shaped string. Some provider-token formats were absent. | Suppress only a match that contains a specific approved placeholder; remove the domain-wide bypass; add GitHub fine-grained, GitLab, and Slack token-pattern tests. |
| Route audit inventoried auth but did not gate unguarded writes | The route inventory included an unguarded-write finding field but only duplicate routes caused a nonzero exit. | Make duplicate method/path definitions and write routes without a recognized declared auth dependency fail the static gate. This remains a heuristic, not proof of access-control correctness. |
| LLM loading could execute remote model-repository code by default | The optional Hugging Face and vLLM paths supplied `trust_remote_code=True`. | Disable remote code by default and require `TMRDS_LLM_TRUST_REMOTE_CODE=true` as explicit opt-in with a warning. Review and pin model artifacts separately. |
| Mock output could be mislabeled as generated | The router returned `status=GENERATED` from its mock branch and BioCoderAssistant overwrote router status. | Emit explicit `MOCK` and fallback metadata, validate generation bounds, and propagate status through BioCoderAssistant. |
| Dedicated dependency and SAST gates were missing | Existing CI scanned secrets and ran tests but did not run a dependency advisory audit or CodeQL. Release verification did not produce build/SBOM evidence. | Add pip-audit against both locks, CodeQL for Python and GitHub Actions, and a release-verification workflow that builds locally and uploads tests/SBOM evidence without deployment. |

## TODO and stub review

The repository search for TODO produced a case-insensitive match in an AlphaFold 3 docstring ("toDo"), not an executable TODO. No FIXME match was returned. The `NotImplementedError` in `BioCoderAssistant` is intentional mock-only behavior when no LLM router is configured; it is not real code generation. The follow-up makes that state explicit rather than pretending the stub is production-complete.

## Pipeline contract

1. **CI:** dependency lock validation, immutable workflow-action check, secret scan, route/auth inventory gate, compilation, Compose configuration, Docker build/liveness smoke test, IBM Quantum mock-only focused tests, and non-integration tests.
2. **Static security/interoperability:** dependency and action checks, secret scan, compilation, route policy, non-integration tests, diagnostics artifact.
3. **Dependency audit:** checks both lock sets against a public advisory service; fails on vulnerabilities or incomplete package collection and uploads machine-readable reports.
4. **CodeQL:** analyzes Python and GitHub Actions. Review alerts in GitHub's Security tab.
5. **Release verification:** checks and tests the release commit, builds a local image, generates a runtime CycloneDX SBOM via pip-audit, and uploads test/SBOM evidence. It does not publish images or deploy.

## Limitations and release blockers

- The merged release-gate workflow outcomes above are verified for the recorded main commit. Future commits must be checked independently; green workflow results are commit-specific.
- Static route inventory checks only a configured set of dependency names. Authorization still needs endpoint-level review and negative tests.
- Integration-marked tests need disposable PostgreSQL/Neo4j instances or live source access; baseline runs skipped integration-related tests. They are not silently replaced with production tests.
- Runtime configuration, migration/restore rehearsals, upstream timeout verification, external service availability, backups/retention, and disaster recovery remain environment-specific release checks.
- Current lock files pin versions but do not include artifact hashes. They improve deterministic version selection but do not alone establish package archive integrity.
- CodeQL and dependency-audit results depend on GitHub Actions settings/permissions and reachable advisory services. Findings are release gates, not compliance certifications.
- No production deployment, database migration, cloud provisioning, live patient-data access, or IBM Quantum hardware submission was performed.

## Evidence references

- [Baseline TMRDS CI](https://github.com/ATphobia22/TMRDS/actions/runs/38801911323)
- [Baseline Security and Interoperability](https://github.com/ATphobia22/TMRDS/actions/runs/38801911327)
- [Failing NumPy Dependabot CI example](https://github.com/ATphobia22/TMRDS/actions/runs/38664852634)
- [GitHub secure use of Actions](https://docs.github.com/en/actions/reference/security/secure-use)
- [PyPA pip-audit](https://github.com/pypa/pip-audit)


## Latest post-merge verification (2026-10-17)

The current main commit is `03c36caa38ace2c340127393b9b01060df480ea3`. The four push-triggered workflows on that exact commit completed successfully:

- [TMRDS CI](https://github.com/ATphobia22/TMRDS/actions/runs/39057490498)
- [Security and Interoperability](https://github.com/ATphobia22/TMRDS/actions/runs/39057490415)
- [Supply Chain Security](https://github.com/ATphobia22/TMRDS/actions/runs/39057490483)
- [CodeQL](https://github.com/ATphobia22/TMRDS/actions/runs/39057490639)

The scientific-backend remediation was merged as [PR #15](https://github.com/ATphobia22/TMRDS/pull/15). A stale pre-merge branch run failed test collection because it retained the old `ClinVarSubmission` dataclass field order; that run is not the current main commit's status. Current-main workflow results above are green.

### Remaining blockers and staged work

- **Repository policy:** branch protection / rulesets could not be inspected or changed with the available repository integration permissions. The existing owner-action note says protection is disabled; an authorized owner must configure required checks and review rules in repository settings.
- **Scientific execution:** AlphaFold3/OpenFold3 prediction backends, VQE/classical-baseline solving, SPDI-to-HGVS normalization, and production molecular docking remain unimplemented. These must report `MOCK_ONLY` or `NOT_CONFIGURED` rather than fabricate results.
- **Environment verification:** no production deployment, production migration, cloud provisioning, live patient-data access, or IBM Quantum hardware submission was performed. Integration tests requiring external services need a disposable non-production environment.
- **Operational recovery:** backup/restore and disaster-recovery rehearsal, production secrets/configuration review, and upstream quota/timeout checks remain release-environment tasks.
- **Lock integrity:** exact dependency versions are pinned, but the current lock files do not include artifact hashes; pinning is not equivalent to verified package-artifact integrity.

The latest main workflow success is evidence for that commit only; each subsequent release candidate must be checked independently.
