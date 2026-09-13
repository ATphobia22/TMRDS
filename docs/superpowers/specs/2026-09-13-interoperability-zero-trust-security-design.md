# TMRDS Interoperability & Zero-Trust Security Hardening Design

**Date:** 2026-09-13  
**Target branch:** `main`

## Goal

Harden TMRDS against committed/default credentials and insecure machine-to-machine trust while establishing a standards-aligned interoperability boundary for FHIR R4, US Core, SMART App Launch, SMART Backend Services, provenance/audit, and PHI transport.

## Scope

1. Eliminate built-in production credentials, fallback database credentials, and deterministic emergency secrets.
2. Require deployment-managed secrets and fail closed in production.
3. Add password hashing with a modern memory-hard password KDF while preserving a PBKDF2 verification path for controlled migration.
4. Add service-to-service JWT authentication with issuer, audience, expiry, scope, and key-ID validation; support JWKS-backed asymmetric verification.
5. Add SMART configuration discovery and PKCE S256 primitives.
6. Add FHIR version/profile/terminology configuration and structural validation for FHIR-shaped resources before interoperability use.
7. Add FHIR Provenance and AuditEvent envelopes plus security-label helpers.
8. Enforce secure outbound HTTP policy: HTTPS by default for protected/institutional endpoints, bounded timeouts, and SSRF-resistant host/IP validation.
9. Add deterministic repository secret scanning in CI without relying on mutable third-party actions.
10. Add a compliance evidence matrix documenting technical alignment with HIPAA Security Rule controls, FHIR security guidance, SMART, US Core, and FDA CDS governance boundaries. The repository will not claim legal/regulatory compliance solely from code.

## Non-goals

- No live institutional EHR/INPC/IHIE access is enabled by this change.
- No PHI import/export is enabled by default.
- No bypass of BAA, DUA, IRB, organizational authorization, or identity-proofing requirements.
- No claim of ONC certification, TEFCA participation, HIPAA compliance, or FDA device status is made by the software.

## Architecture

TMRDS uses a defense-in-depth boundary:

`client/service -> authenticated API boundary -> authorization -> validated resource -> provenance/audit -> governed persistence`

Machine identities are independent from human sessions. Human authentication remains deployment-configured. Interoperability clients use standards-defined OAuth/SMART primitives rather than shared passwords. FHIR resources are version-pinned and validated before being exposed as interoperable output. Sensitive exchange requires TLS at the deployment edge and secure outbound policies.

## Security defaults

- Production requires `TMRDS_HMAC_SECRET`, `TMRDS_DATABASE_URL`, and configured authentication credentials/identity providers.
- No password, PIN, DB password, API key, private key, or bearer token is committed.
- Production service tokens are asymmetric JWTs with explicit issuer/audience and short expiry.
- HTTPS is required for configured protected upstreams; loopback/private network access is explicitly allowlisted for local infrastructure only.
- Audit records contain identity, action, resource, timestamp, and correlation ID without storing secrets or authentication material.

## Interoperability baseline

- FHIR baseline: R4.
- US Core: configured/pinned independently rather than hard-coded to a historical release.
- SMART App Launch: OAuth 2.0 authorization-code flow with PKCE S256 for user-facing clients.
- SMART Backend Services: client-credentials-style backend authentication using signed JWT client assertions/JWKS.
- Resource security: Provenance, AuditEvent, RBAC/ABAC hooks, and security labels.
- Bulk FHIR: NDJSON remains an integration target and requires separate deployment authorization and data-use controls.

## Verification

The implementation must have automated tests for secret/config validation, KDF behavior, JWT validation, PKCE, SMART discovery, FHIR metadata/validation, provenance/audit generation, SSRF policy, and repository secret scanning. Verification must distinguish unit-test success from external institutional interoperability and legal compliance.
