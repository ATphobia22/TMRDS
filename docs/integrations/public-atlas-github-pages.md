# Public TMRDS evidence atlas — GitHub Pages

## Intended use

Anonymous, read-only, static biomedical research interface in the public directory. On explicit form submission, public-topic text is sent to Europe PMC and ClinicalTrials.gov API v2. No patient information, medical records, logins, cookies, tokens, institution integrations or clinical predictions are exposed.

The separate 25-source Python federated engine, its evidence ledger, and optional quantum research runtimes remain server-side in the TMRDS repository. The site is NOT a live proxy for those services. Molecule, structure, gene, and population facets provide links to original source sites; their data is not requested here. The Muse preview and personnel uploads are not copied to Pages.

## Data provenance and boundaries

| Source | Page status | Usage boundary |
|---|---|---|
| Europe PMC REST Search | Live read-only browser fetch on search | Metadata discovery. Copyright and open-access article license are distinct. |
| ClinicalTrials.gov API v2 | Live read-only browser fetch on search | Trial registry discovery. Registry status is not efficacy. |
| Open Targets, RCSB PDB, ChEMBL, ClinVar | Source reference links only | No live connection or clinical proof claimed. |
| IBM Quantum, Qiskit and internal models | Not executed | No quantum hardware or clinical validation claimed. |

Every successful response gets a retrieval timestamp, the date supplied by the origin, a stable source identifier, its original URL, and a local SHA-256 digest over normalized display fields. The digest is not an upstream signature or independent authentication. Errors and browser CORS failures are displayed without fake fallback data. No patient-specific advice or clinical grading is performed.

## Deploy

1. Merge this PR into main after passing static validation and repository CI.
2. In GitHub repository Settings > Pages > Build and deployment > Source choose GitHub Actions. The connector used to create code cannot itself verify or change that administrative setting.
3. Trigger or inspect the TMRDS Public Evidence Atlas (GitHub Pages) workflow.
4. Independently open https://atphobia22.github.io/TMRDS/ and verify the loaded site and each source status. Do not claim a live deployment before successful publish and HTTP verification.

## Checks

- python3 scripts/check_public_site.py
- node --check public/site.js
- python3 scripts/check_workflow_security.py

The Pages action pins are immutable 40-character commit SHAs. Browser behavior should also be tested on iPhone and desktop with live, empty, malformed, timed-out, and blocked upstream responses. The site has no backend secrets. Only two official API hosts are in its CSP connect-src.

## Security limitations

GitHub Pages is public hosting and cannot safely keep secrets or protected medical data. The current public search uses source data subject to provider terms, not a blanket permission for copying full text or training datasets. No auto-refresh loop, API polling interval, dynamic compute submission, or public mutation route is enabled.