# Dependency Management and Lockfile Release Gate

**Scope:** TMRDS Python runtime and test dependencies. Runtime: Python 3.11.

## Source of truth

- `requirements.txt` declares app and test ranges; `requirements.lock` is the exact pin set used by CI.
- `requirements-runtime.txt` declares runtime-only dependencies; `requirements-runtime.lock` is used for the application image.
- `requirements-lock.txt` and `requirements-runtime-lock.txt` remain compatibility aliases and must be byte-identical to their corresponding canonical lock.
- Direct runtime dependencies shared by both manifests must use the same version in both locks.
- Dependabot changes are proposals. A PR that edits a manifest or alias without synchronizing canonical lock files is incomplete and must not be merged.

The lock checker validates direct declaration coverage, version specifier compatibility, strict exact-pin syntax, duplicate pins, alias equality, and consistent shared direct pins. Exact version pins alone are not a cryptographic artifact-integrity guarantee; hash-locked artifacts remain a separate supply-chain improvement.

## Controlled dependency update

Use a clean Python 3.11 virtual environment. Review upstream changelogs, supported Python versions, dates, and known advisories before changing packages.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "pip-tools==7.5.2"
pip-compile --resolver=backtracking --output-file=requirements.lock requirements.txt
pip-compile --resolver=backtracking --output-file=requirements-runtime.lock requirements-runtime.txt
cp requirements.lock requirements-lock.txt
cp requirements-runtime.lock requirements-runtime-lock.txt
python scripts/check_dependency_lock.py
python -m pip install -r requirements.lock
python -m pip check
python scripts/security_scan.py .
python -m pytest -q -m "not integration"
docker build --pull -t tmrds-api:dependency-review .
```

For a targeted upgrade, use `pip-compile --upgrade-package package-name` rather than broadly upgrading everything. Regenerate both locks, review transitive changes, run the dependency advisory workflow, and keep the upgrade in a reviewable PR. Do not automatically apply suggested versions to production.

## CI and release workflows

- **TMRDS CI** validates both lock pairs and aliases, checks workflow action pins, scans for likely committed secrets, inventories API routes/auth dependencies, compiles Python, validates Compose, builds the image, smoke-tests liveness, and runs unit/mock tests.
- **TMRDS Security and Interoperability** runs static security checks and the non-integration test suite.
- **TMRDS Dependency Audit** uses [pip-audit](https://github.com/pypa/pip-audit) against both canonical locks and fails on vulnerabilities or incomplete dependency collection. Reports are uploaded even if the audit fails.
- **TMRDS CodeQL** analyzes Python and GitHub Actions. Review results in the repository's Security tab.
- **TMRDS Release Verification** runs checks/tests, builds a local release candidate image, creates runtime CycloneDX SBOM evidence, and uploads results. It deliberately does not push images, deploy services, run database migrations, or submit IBM Quantum jobs.

GitHub recommends pinning third-party actions to a full commit SHA because it is immutable; see [GitHub Actions secure use](https://docs.github.com/en/actions/reference/security/secure-use). SHA pins must still be deliberately updated to receive upstream fixes.

## Deferred integration

Redis is absent from runtime dependencies until a real external Redis adapter is implemented and tested. The current `DualTierMemory` is process-local and non-durable across restarts; it does not provide distributed caching. Reintroducing Redis requires an adapter, configuration validation, timeout/failure policy, concurrency and persistence tests, operational metrics, and reviewed deployment configuration.
