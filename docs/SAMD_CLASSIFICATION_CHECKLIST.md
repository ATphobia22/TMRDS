# SaMD Classification Review Checklist (per feature/change)

**Purpose:** Guardrail from the October 2026 SaMD research. Run this checklist for every feature or change before it ships, and file the completed copy with the change. If any answer is YES, stop: the change needs a new `docs/INTENDED_USE.md` version, fresh review against 21st Century Cures Act §3060 / FD&C §520(o)(1)(E), and updated risk analysis before release.

**Feature/change:** ____________________ **Date:** __________ **Reviewer:** __________

## The four Cures Act criteria (ALL must remain true)

| # | Criterion | Still true? |
|---|-----------|-------------|
| 1 | No medical-image or IVD-signal processing is added (no radiology/pathology images, waveforms, or diagnostic signals as inputs) | ☐ Yes ☐ No |
| 2 | The change only displays medical information (published literature, registry entries, public database records) | ☐ Yes ☐ No |
| 3 | The change supports — never replaces — a healthcare professional's recommendation; human clinical authority stays final | ☐ Yes ☐ No |
| 4 | A clinician can independently review the basis of every output (source, identifiers, retrieval date, outbound primary-source link) | ☐ Yes ☐ No |

## Boundary questions (ALL must be NO)

- [ ] Does it give per-patient recommendations, diagnoses, or treatment direction?
- [ ] Does it ingest patient-identifiable data or sensitive genomic data?
- [ ] Does it claim FDA clearance, clinical validation, HIPAA compliance, ONC certification, or TEFCA connectivity?
- [ ] Does it present a "solved"/cure state, efficacy claim, or confidence score a clinician cannot independently verify?
- [ ] Does it describe classical simulation as quantum-hardware execution?
- [ ] Does it silently mock an unavailable source instead of reporting it unavailable?

## Disposition

- [ ] PASS — research-advisory posture intact; no intended-use change.
- [ ] HOLD — one or more boxes failed; change blocked pending intended-use review.

**Notes:** ____________________

*This checklist is a process guardrail, not legal advice. Product decisions with regulatory implications must be checked against the primary FDA guidance documents with qualified counsel.*
