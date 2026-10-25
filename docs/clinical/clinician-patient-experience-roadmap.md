# TMRDS clinician and patient experience: safety-first delivery plan

Status: **proposal, not implemented clinical functionality**. TMRDS remains research-advisory. No clinical deployment, diagnosis, treatment, medical-device clearance, HIPAA compliance, or EHR certification is claimed.

## Product principles
1. **Patients understand the result.** Plain-language summary, reading-level review, source date, limitations, uncertainty, and accessible alternative formats. Do not imply a research hypothesis is a diagnosis.
2. **Clinicians can verify the evidence.** Every research result displays source identifier/DOI, publication and retrieval dates, method, population applicability, conflicts, provenance chain, confidence limits, and reasons for abstention.
3. **Human review controls consequential action.** No autonomous prescribing, triage disposition, clinical note finalization, or EHR write-back. Research results are explicitly non-actionable until independent validation and authorized clinician review.
4. **Privacy by design.** No PHI in logs, telemetry, URLs, prompts, third-party research queries, or synthetic fixtures. Implement scoped SMART OAuth authorization, consent, minimum-necessary access, short retention, and auditable access *before* real patient data.
5. **Safe failure.** Missing evidence, conflicting studies, stale results, unavailable upstream services, or invalid credentials produce a visible unavailable/insufficient-evidence state rather than a confident generated recommendation.

## Delivery sequence and acceptance gates

### P0: User trust and accessible interface
- Create patient and clinician views sharing the same evidence envelope but with audience-specific language.
- Add persistent research-only banner, 'what this means / does not mean', last-updated timestamp, confidence/uncertainty, source links, and explicit data freshness.
- Keyboard-only navigation, semantic headings, screen-reader announcements, high contrast, scalable text, and WCAG 2.2 AA review.
- **Acceptance:** automated accessibility tests and human keyboard/screen-reader review; no fabricated confidence scores or clinical claims.

### P0: Provenance and safety contracts
- Define versioned output schema: research_question, result_status (supported / conflicting / insufficient / unavailable), evidence_ids, model_version, source_timestamps, limitations, uncertainty_basis, and review_status.
- Render the source citation and method beside each claim; reject uncited generated claims and expose abstention reasons.
- Add synthetic-data adversarial tests for missing/null fields, conflicting sources, stale evidence, prompt injection in retrieved literature, and cross-user data leakage.
- **Acceptance:** negative tests prove unsafe states do not silently become approved clinical recommendations.

### P1: Clinician evidence workspace
- Evidence table: study design, cohort, applicability, effect size and confidence interval *when sourced*, recency, retraction/correction status, and evidence gaps.
- Clinician annotations, reproducible export, explicit review sign-off and immutable audit events.
- Research-only differential hypotheses may be shown as unranked literature topics; do not issue patient-specific diagnostic or treatment advice without separate clinical validation.
- **Acceptance:** reviewer can trace every displayed finding back to immutable source and transformation records.

### P1: Patient communication
- Patient-friendly explanation generated **from approved, cited research facts**, not raw model speculation.
- Provide printable/exportable summary, accessibility and language preferences, questions to ask a clinician, and easy correction/feedback path.
- **Acceptance:** readability/usability testing with patients and clinicians; translations undergo clinical and language review before release.

### P1: Interoperability sandbox
- Test HL7 FHIR R4 / US Core profile conformance with synthetic resources; distinguish implemented profile support from merely returning a status endpoint.
- Add SMART App Launch 2.0 PKCE/EHR-launch authorization tests and token-scope isolation before any live EHR integration.
- Evaluate CDS Hooks only as a future *research-context* workflow, not as live patient-specific decision support.
- **Acceptance:** independent conformance tests, consent/privacy assessment, penetration testing, institutional authorization and documented data-processing agreements before real PHI.

### P2: Quality and operations
- Track abstention rate, evidence coverage, retrieval freshness, broken citations, user correction rate, accessibility regressions, and clinician-review completion. Use synthetic/aggregated telemetry only by default.
- Add rollback, feature flags, dependency/SBOM review, disaster recovery tests, security incident runbooks, and research model drift checks.
- **Acceptance:** CI gates and independent clinical safety review documented; no claim of medical effectiveness without prospective validation.

## Standards references
- HL7 US Core implementation guide: https://hl7.org/fhir/us/core/
- U.S. interoperability standards and SMART/CDS Hooks: https://isp.healthit.gov/shareable-clinical-decision-support
- CMS interoperability and API implementation guides: https://www.cms.gov/initiatives/burden-reduction/overview/interoperability/implementation-guides-standards/application-programming-interfaces-apis-relevant-standards-implementation-guides-igs

## Definition of done
The roadmap is complete only when each capability has code, synthetic tests, security/privacy review, accessibility validation, documented user acceptance, and a green release gate. The presence of this document is **not** implementation or regulatory approval.
