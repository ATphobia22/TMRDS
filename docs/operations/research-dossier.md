# Evidence discovery dossier

Implemented: `GET /api/v1/research/dossier?query=synthetic%20research&limit=5`.
Use public research topics only. The query is transmitted to the existing
federated biomedical providers; do not enter patient information or secrets.
The endpoint uses the existing federated-search rate limit and optional API-key
middleware. `limit` is per provider (1–25), not a total-result limit.

The JSON export includes the question, search timestamp, source coverage and
failure warnings, grouped records, missing metadata and explicit review gaps.
DOI normalization groups resolver URLs and case variants. PMID is the fallback;
otherwise source stable IDs are retained. Matching titles do not merge studies.
Each group retains every source envelope rather than counting duplicate source
appearances as independent studies. Original record hashes and retrieval times
remain attached to their respective records. These hashes are not a signature
or independent verification of source accuracy.

`records_retrieved`, `no_records` and `unavailable` describe retrieval only.
No efficacy, quality score, clinical conflict, retraction determination, patient
eligibility or cure is inferred. Metadata discrepancies are exposed for review.
Retrieved abstracts remain untrusted data; this endpoint runs no LLM and obeys
no instructions in source text. JSON exports are not rendered HTML.

## Verification and remaining delivery gates

Synthetic tests cover DOI duplicates, retention of disagreeing metadata,
no title-only merging, upstream availability, untrusted text and API wiring.
They do not establish live-provider reliability or medical validity.

The clinician/patient roadmap remains partially implemented. Further work:

- Add a browser workspace with source links, accessible tables and keyboard review;
  complete independent screen-reader and WCAG review.
- Add authenticated reviewer annotations and immutable, database-backed review
  events with ownership and cross-user authorization tests.
- Validate study-design, population, effect-size and retraction extraction against
  independently reviewed evidence sets before displaying extracted conclusions.
- Add protocol-defined screening and evidence-quality evaluation with biomedical
  reviewers; do not treat relative provider scores as calibrated probabilities.
- Separately validate live integrations, production deployment, FHIR conformance,
  privacy controls and any computational hypotheses. No clinical effectiveness
  or cure-discovery success is claimed by this implementation.
