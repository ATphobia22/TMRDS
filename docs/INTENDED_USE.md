# TMRDS Intended Use Statement — Research Only

**Version:** 1.0.0
**Effective:** 2026-10-18
**Steward:** Anthony John Tucker · Mount Vernon, Indiana 47620
**Status:** Research-advisory software. **Not a medical device. Not FDA-cleared.**

---

## 1. What TMRDS is

The Tucker Medical Research and Development System (TMRDS) is a
**research-navigation workspace** for biomedical evidence. It helps
researchers and clinicians *find* potentially relevant published research —
journal articles, clinical-trial registry entries, public structure records,
and preprints — faster than manual searching. It presents that evidence with
provenance (source, identifiers, retrieval date) and honest coverage limits.

TMRDS outputs are **computational hypotheses and literature pointers**, never
clinical conclusions.

## 2. What TMRDS is not

- Not a diagnostic device. It does not diagnose disease or interpret a
  patient's test results.
- Not a treatment device. It does not recommend, prescribe, dose, or direct
  any therapy.
- Not a cure-state solver. Disease has no single provable "solved" state;
  TMRDS never claims one.
- Not FDA-cleared, CE-marked, HIPAA-attested, or ONC-certified. No clinical
  validation claim is made.
- Structure-confidence values (e.g., AlphaFold pLDDT) describe *prediction
  confidence of a protein shape*, never treatment efficacy.

## 3. Why this stays outside the SaMD definition

Under 21st Century Cures Act §3060 / FD&C §520(o)(1)(E), clinical decision
support software is excluded from the device definition only when **all four**
criteria hold. TMRDS is designed to hold all four:

1. **No medical-image or IVD-signal processing.** TMRDS does not process
   radiology images, pathology slides, waveforms, or in-vitro diagnostic
   signals. Structure records are public prediction metadata, not patient
   measurements.
2. **Displays medical information.** Outputs are published literature,
   registry entries, and public database records — medical information, not
   patient-specific analysis.
3. **Supports a healthcare professional's recommendation.** The tool informs;
   the clinician decides. Human clinical authority is final.
4. **The clinician can independently review the basis.** Every record carries
   its source, identifiers, and retrieval date with outbound links to the
   primary source, so the basis of any pointer is independently reviewable.
   Opaque, black-box recommendations are out of scope for this intended use.

## 4. Boundaries that keep this true

- **Research advisory only.** Every API envelope and page carries
  `research-advisory`, `human_authority_final: true`, `not_samd: true`.
- **No per-patient recommendations.** No patient-identifiable data and no
  sensitive genomic data enter the public pipelines.
- **No autonomous action.** No diagnosis, prescribing, treatment direction,
  or cure claims — in code, copy, or UI.
- **Honest coverage.** Search cannot guarantee exhaustive coverage; sources
  that are unavailable (credential-gated or unreachable) are reported as
  unavailable, never mocked.
- **Quantum output is hypothesis.** Classical simulation is never described
  as quantum-hardware execution.

## 5. Change control

This statement is version-controlled. Any change to the intended use —
including adding per-patient features, image/signal processing, or
diagnostic or therapeutic claims — requires a new version of this document,
a fresh review against §520(o)(1)(E), and updated risk analysis before the
change ships. **This document is not legal advice**; product decisions with
regulatory implications must be checked against the primary FDA guidance
documents with qualified counsel.

## 6. History

| Version | Date       | Change                                  |
|---------|------------|-----------------------------------------|
| 1.0.0   | 2026-10-18 | Initial research-only intended use      |
