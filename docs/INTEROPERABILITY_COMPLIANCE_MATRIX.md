# TMRDS Interoperability & Security Compliance Evidence Matrix

**Verification date:** 2026-09-13  
**Status:** Technical alignment controls implemented; this document is **not** a certification or legal-compliance determination.

## 1. FHIR / SMART

| Area | Current external baseline | TMRDS control | Evidence |
|---|---|---|---|
| FHIR | FHIR R4 baseline | `FHIRInteroperabilityConfig` pins R4 and rejects unsupported baseline versions | `engines/fhir_interoperability.py` |
| US Core | Explicit release/version required | `TMRDS_US_CORE_VERSION` is deployment-configurable; default documentation value is 9.0.0 and must be validated against the deployment package before claiming profile conformance | `engines/fhir_interoperability.py`, `api/interoperability_routes.py` |
| SMART App Launch | OAuth 2.0 authorization code + PKCE; S256 required for PKCE | `create_pkce_pair()` and discovery metadata advertise S256 only | `engines/smart_security.py` |
| SMART Backend Services | Signed backend client assertions/JWKS | `ServiceTokenValidator` validates asymmetric JWTs with issuer, audience, expiry, nbf, kid and scopes | `engines/service_identity.py` |
| Provenance | FHIR Provenance | Minimal R4 Provenance builder records target, agent and correlation source | `engines/fhir_interoperability.py` |
| Audit | FHIR AuditEvent | Minimal R4 AuditEvent builder records operation identity and target without credentials | `engines/fhir_interoperability.py` |

Official references:
- SMART App Launch: https://hl7.org/fhir/smart-app-launch/
- FHIR R4: https://hl7.org/fhir/R4/
- US Core: https://hl7.org/fhir/us/core/

## 2. HIPAA Security Rule technical alignment

NIST SP 800-66 Rev. 2 is the current NIST cybersecurity resource guide for implementing the HIPAA Security Rule. It describes safeguards for ePHI and maps HIPAA Security Rule standards to security controls. TMRDS implements selected technical safeguards but cannot establish organizational compliance by code alone.

| HIPAA technical area | TMRDS implementation |
|---|---|
| Unique user identification / person or entity authentication | Deployment-configured human identities; no built-in password/PIN; session tokens are generated at authentication |
| Automatic logoff | Configurable session timeout |
| Audit controls | Append-only local audit records with identity/action/resource/timestamp |
| Integrity | HMAC integrity seals with deployment-managed secret |
| Transmission security | HTTPS-only public feed catalog and outbound SSRF/transport policy |
| Access control | Service-to-service bearer validation with issuer/audience/scope controls; additional application RBAC/ABAC remains deployment/application responsibility |
| Emergency access | Emergency identity is deployment-configured; no default emergency PIN is shipped |

Official reference:
- NIST SP 800-66 Rev. 2: https://csrc.nist.gov/pubs/sp/800/66/r2/final

## 3. ONC / USCDI / information blocking

HTI-1 established USCDI v3 as the baseline standard in the ONC Health IT Certification Program beginning January 1, 2026 and revised information-blocking provisions. TMRDS should not be represented as ONC-certified merely because it implements FHIR/SMART primitives.

TMRDS technical posture:
- FHIR R4 and US Core version are explicit configuration values.
- FHIR validation is deliberately structural unless a complete profile/terminology validator is installed and invoked.
- No ONC certification claim is made.
- Information-blocking obligations, organizational policies, certified-module scope, and exception analysis remain external governance requirements.

Official reference:
- ONC HTI-1 Final Rule: https://healthit.gov/regulations/hti-rules/hti-1-final-rule/

## 4. FDA clinical decision support boundary

FDA's January 2026 Clinical Decision Support Software final guidance distinguishes certain non-device CDS functions from software functions that remain medical devices. TMRDS therefore keeps research/advisory output and human-authority metadata explicit and does not infer regulatory status from an API route.

Required governance metadata for future clinical/AI functions:
- intended use
- intended user
- intended patient population
- input medical information
- output type and actionability
- human-review requirement
- validation/evidence basis
- regulatory classification decision and rationale

Official references:
- FDA Clinical Decision Support Software: https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software
- FDA CDS FAQ: https://www.fda.gov/medical-devices/software-medical-device-samd/clinical-decision-support-software-frequently-asked-questions-faqs

## 5. Machine-to-machine trust model

TMRDS services must not trust one another solely because they share a Docker network. When `TMRDS_SERVICE_AUTH_REQUIRED=true`, protected ingestion/synchronization operations require a bearer token validated as an asymmetric JWT against configured JWKS with:

- explicit issuer
- explicit audience
- `kid` key selection
- fixed approved algorithms
- `iat`, `nbf`, and `exp` validation
- required scopes
- no token logging

This is a technical control. Production key management, client registration, identity proofing, certificate/key rotation, and incident response remain deployment responsibilities.

## 6. Known external prerequisites

Before enabling live PHI or institutional exchange, TMRDS still requires:

1. Institutional endpoint registration and authorization.
2. Appropriate BAA/DUA and any required IRB/privacy review.
3. Production identity provider and key-management infrastructure.
4. TLS certificate management and network segmentation.
5. Formal FHIR/US Core conformance validation against the exact package version used by the target exchange.
6. Terminology validation and code-system governance.
7. Data-retention, minimum-necessary, disclosure, and access-review policies.
8. Penetration testing and operational incident-response controls.
9. Regulatory/product classification review for any clinical decision-support function.

## 7. Important limitation

Passing TMRDS automated tests or this matrix does **not** mean TMRDS is HIPAA compliant, ONC certified, TEFCA-connected, FDA-cleared/authorized, or authorized to exchange institutional PHI. Those determinations depend on the deployed system, contracts, organizational controls, exact interoperability packages, target endpoint requirements, and applicable law/regulation.
