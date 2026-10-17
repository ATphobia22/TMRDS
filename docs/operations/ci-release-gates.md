# TMRDS CI and release gates

## Automated gates

| Gate | Workflow | Purpose | What it does not prove |
|---|---|---|---|
| Unit/API tests, compilation, Compose validation, container build and liveness smoke test | `.github/workflows/ci.yml` | Catch code, packaging, container and basic startup regressions | Production database readiness, live external integrations, or deployment health |
| Secret scan, route/auth inventory, unit tests | `.github/workflows/security.yml` | Detect known secret patterns and surface routes needing auth review | Correct authorization semantics for every route |
| Direct requirement-to-lock validation and vulnerability audit | `.github/workflows/supply-chain.yml` | Check both dependency sets and fail on known advisories | Absence of undisclosed vulnerabilities or risks in non-Python assets |
| Pull-request dependency review | `.github/workflows/supply-chain.yml` | Fail a PR when dependency review identifies high/critical severity changes | Full transitive runtime behavior |
| CodeQL Python analysis | `.github/workflows/codeql.yml` | Static analysis for supported Python security patterns | Runtime exploitability or regulatory compliance |

All workflows use read-only repository permissions by default. The CodeQL job adds only the permissions required to publish code-scanning results. No workflow should use production credentials, run production migrations, submit IBM Quantum jobs, or provision cloud resources.

## Dependency update procedure

1. Update the declaration in `requirements.txt` and/or `requirements-runtime.txt`.
2. Regenerate the matching lock file(s) using the project's reviewed dependency-lock process; lock files must contain exact `==` pins, including transitive dependencies.
3. Run `python scripts/check_dependency_lock.py`.
4. Run `pip-audit --strict --no-deps -r requirements.lock` and `pip-audit --strict --no-deps -r requirements-runtime.lock`.
5. Review the resulting diff for unrelated upgrades, license/source concerns, Python 3.11 compatibility, and upstream release notes.
6. Let CI complete before merging. Do not resolve a failed lock check by adding a package to a lock without confirming it is intentionally required.

Redis is not declared in the runtime dependency set because the current dual-tier memory implementation is an in-process store and does not instantiate a Redis client. Do not merge an automated Redis version bump unless a Redis-backed implementation and integration tests are added together.

## Required repository settings (manual owner action)

The repository's default branch currently has branch protection disabled. The workflow files cannot enforce required status checks on `main` by themselves. In GitHub repository settings, configure a ruleset or branch protection rule for `main` that:

- requires pull requests before merging;
- requires the CI, Security and Interoperability, Supply Chain Security, and CodeQL checks to pass (use the exact check names reported by GitHub);
- dismisses stale approvals when new commits are pushed, and requires approval of the most recent reviewable push where supported;
- blocks force pushes and branch deletion;
- requires conversation resolution;
- restricts bypass access to explicitly authorized maintainers.

Do not configure required-check names until the first runs have completed and the exact status-check names are visible. Keep a documented recovery path for repository owners.

## Release evidence checklist

- [ ] Main CI passed on the exact release commit.
- [ ] Secret/security and CodeQL workflows completed; findings were triaged.
- [ ] Both dependency lock sets validate and both vulnerability audits passed or have explicitly accepted, time-bounded exceptions.
- [ ] Container image built and liveness smoke test passed.
- [ ] Required integrations were tested in a non-production environment with synthetic data.
- [ ] Migration status, backup and restore evidence reviewed by the database owner.
- [ ] Production configuration and secrets reviewed independently.
- [ ] Remaining risks and unsupported features disclosed in release notes.

Green CI is necessary but not sufficient for a production release. It does not establish clinical validity, HIPAA compliance, FDA clearance, external service entitlement, or deployment readiness.
