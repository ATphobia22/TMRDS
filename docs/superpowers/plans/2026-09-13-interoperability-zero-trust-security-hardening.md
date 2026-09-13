# TMRDS Interoperability & Zero-Trust Security Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove insecure defaults and establish a production-oriented security/interoperability foundation for TMRDS FHIR/SMART and machine-to-machine communication.

**Architecture:** Add focused security modules rather than embedding authentication policy throughout the API. Keep human sessions separate from service identities, pin interoperability metadata, validate FHIR-shaped resources, generate audit/provenance records, and enforce outbound transport policy at one reusable boundary.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic 2, httpx, standard-library cryptography primitives where practical, pytest/pytest-asyncio, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-13-interoperability-zero-trust-security-design.md`

## Global Constraints

- Target branch is `main` because the user explicitly approved direct implementation on `main`.
- No live PHI or institutional EHR connectivity is enabled by default.
- No credentials, API keys, bearer tokens, private keys, or deterministic secrets may be committed.
- Production configuration fails closed when required secrets are absent.
- FHIR baseline is R4 and interoperability metadata is explicitly versioned/configurable.
- SMART user authorization uses PKCE with S256; backend service authentication uses signed JWT assertions/JWKS.
- Code implements technical controls only; it does not assert legal/regulatory compliance.

---

### Task 1: Credential and security configuration hardening

**Files:**
- Modify: `engines/hipaa_security_controls.py`
- Modify: `engines/evidence_graph_repository.py`
- Modify: `engines/neo4j_evidence_projection.py`
- Modify: `docker-compose.yml`
- Modify: `requirements.txt`
- Create: `tests/test_security_hardening.py`

**Interfaces:**
- `SecurityConfiguration.from_environment()` returns a validated immutable configuration.
- `PasswordHasher.hash()` and `PasswordHasher.verify()` implement the selected KDF format.
- Existing `HIPAASecurityControls.authenticate()` continues to return its established response shape while using the stronger KDF.

- [ ] **Step 1: Write failing tests** for required production secrets, absence of database fallback credentials, modern password hashing, and configured emergency credentials.
- [ ] **Step 2: Run the focused tests** and confirm failure on the missing new interfaces/behavior.
- [ ] **Step 3: Implement configuration validation and password KDF migration support.** Production requires explicit secrets; development may generate an ephemeral HMAC secret but never a password/PIN. Use a memory-hard KDF if available in the dependency set; otherwise use PBKDF2-HMAC-SHA256 with a high iteration count as a standards-based fallback and expose the format for future migration.
- [ ] **Step 4: Remove any DB/Neo4j password fallbacks and make deployment variables explicit.** Docker Compose must require passwords instead of defaulting them.
- [ ] **Step 5: Run focused tests and confirm pass.
- [ ] **Step 6: Commit** with `security: harden credentials and deployment secrets`.

---

### Task 2: Zero-trust service identity and JWT validation

**Files:**
- Create: `engines/service_identity.py`
- Create: `tests/test_service_identity.py`
- Modify: `requirements.txt`

**Interfaces:**
- `ServiceTokenClaims` is a typed claim model.
- `ServiceTokenValidator.validate(token)` validates signature, issuer, audience, expiry, not-before, key ID, and required scopes.
- `JWKSKeySet` loads public JWK material from an explicit configuration source.

- [ ] **Step 1: Write failing tests** for issuer/audience rejection, expired-token rejection, missing-scope rejection, unknown-key rejection, and successful asymmetric verification.
- [ ] **Step 2: Run focused tests and verify expected failures.
- [ ] **Step 3: Implement JWT/JWKS validation using an audited maintained dependency and explicit algorithms (RS256/ES256 as configured; no algorithm confusion).
- [ ] **Step 4: Add correlation/service identity fields to audit output without logging tokens.
- [ ] **Step 5: Run focused tests and verify pass.
- [ ] **Step 6: Commit** with `security: add zero-trust service identity validation`.

---

### Task 3: SMART configuration and PKCE primitives

**Files:**
- Create: `engines/smart_security.py`
- Create: `tests/test_smart_security.py`
- Modify: `api/main.py`

**Interfaces:**
- `SmartConfiguration` exposes authorization, token, JWKS, issuer, scopes, and capability metadata.
- `create_pkce_pair()` returns a verifier and S256 challenge.
- `validate_pkce(verifier, challenge)` performs constant-time comparison.

- [ ] **Step 1: Write failing tests** for S256 generation, challenge verification, tampered verifier rejection, and SMART discovery serialization.
- [ ] **Step 2: Run focused tests and verify expected failures.
- [ ] **Step 3: Implement SMART metadata and PKCE S256.
- [ ] **Step 4: Add a discovery endpoint at `/.well-known/smart-configuration` that is configuration-driven and does not expose secrets.
- [ ] **Step 5: Run focused tests and verify pass.
- [ ] **Step 6: Commit** with `feat: add SMART discovery and PKCE security primitives`.

---

### Task 4: FHIR version/profile validation boundary

**Files:**
- Create: `engines/fhir_interoperability.py`
- Create: `tests/test_fhir_interoperability.py`
- Modify: `api/main.py`
- Modify: `requirements.txt`

**Interfaces:**
- `FHIRInteroperabilityConfig` contains `fhir_version`, `us_core_version`, and terminology package identifiers.
- `FHIRResourceValidator.validate(resource)` returns structured validation errors.
- `build_provenance()` and `build_audit_event()` produce FHIR R4 resources with explicit references.

- [ ] **Step 1: Write failing tests** for R4 resource type/version checks, required resource identifiers, profile metadata, and invalid resource rejection.
- [ ] **Step 2: Run focused tests and verify failures.
- [ ] **Step 3: Implement deterministic structural validation and version/profile metadata. Do not claim full profile conformance unless a real validator/package is available at runtime.
- [ ] **Step 4: Add Provenance/AuditEvent/security-label builders.
- [ ] **Step 5: Expose read-only interoperability metadata/validation endpoints without enabling PHI exchange.
- [ ] **Step 6: Run focused tests and verify pass.
- [ ] **Step 7: Commit** with `feat: add governed FHIR interoperability boundary`.

---

### Task 5: Secure outbound HTTP/SSRF policy

**Files:**
- Create: `engines/secure_http.py`
- Create: `tests/test_secure_http.py`
- Modify: selected upstream pipeline modules to use the policy where practical.

**Interfaces:**
- `OutboundRequestPolicy.validate_url(url, allow_private=False)` rejects unsafe schemes, malformed hosts, credentials in URLs, and private/link-local/loopback destinations unless explicitly allowlisted.
- `SecureHTTPClient` applies bounded connect/read/write/pool timeouts and redirects policy.

- [ ] **Step 1: Write failing tests** for HTTP rejection, private IP rejection, credential-bearing URL rejection, timeout bounds, and explicitly allowlisted local infrastructure.
- [ ] **Step 2: Run focused tests and verify failures.
- [ ] **Step 3: Implement policy and bounded HTTP client.
- [ ] **Step 4: Integrate the highest-risk outbound connectors without changing their public method signatures.
- [ ] **Step 5: Run focused tests and verify pass.
- [ ] **Step 6: Commit** with `security: enforce outbound transport and SSRF policy`.

---

### Task 6: Secret scanning and compliance evidence

**Files:**
- Create: `scripts/security_scan.py`
- Create: `tests/test_security_scan.py`
- Create: `.github/workflows/security.yml`
- Create: `docs/INTEROPERABILITY_COMPLIANCE_MATRIX.md`
- Modify: `.gitignore`
- Modify: `.dockerignore`

- [ ] **Step 1: Write failing tests** for detection of known credential/token/private-key patterns and safe handling of placeholders.
- [ ] **Step 2: Run focused tests and verify failures.
- [ ] **Step 3: Implement a deterministic scanner with allowlisted documentation placeholders and nonzero exit on findings.
- [ ] **Step 4: Add CI workflow that runs the scanner and Python tests.
- [ ] **Step 5: Expand ignore rules for environment files, credentials, private keys, database dumps, logs, and generated PHI-like data.
- [ ] **Step 6: Write the compliance matrix mapping technical controls to HIPAA Security Rule sections, FHIR security guidance, SMART 2.2, US Core, and FDA CDS governance boundaries, with official-source URLs recorded as references.
- [ ] **Step 7: Run focused tests and scanner; verify pass and zero findings.
- [ ] **Step 8: Commit** with `security: add secret scanning and interoperability compliance evidence`.

---

### Task 7: Final integration verification

**Files:**
- Modify: `README.md` if deployment/security instructions require correction.
- Create: `docs/superpowers/verification/2026-09-13-zero-trust-interoperability-verification.md`

- [ ] **Step 1:** Run the full available test suite.
- [ ] **Step 2:** Run the repository security scanner.
- [ ] **Step 3:** Run syntax compilation/import checks.
- [ ] **Step 4:** Review changed files for secrets, insecure defaults, accidental PHI, and unsupported compliance claims.
- [ ] **Step 5:** Record exact commands/results and known external limitations in the verification report.
- [ ] **Step 6:** Commit verification documentation.
