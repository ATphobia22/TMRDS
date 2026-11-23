# Offline biomedical citation pack — verifiable local search

**Implementation date:** November 23, 2026. **Scope:** bibliographic discovery and evidence provenance, not clinical decision support or stored patient information.

## End-to-end operation

1. **On a trusted Internet-connected preparation computer**, run the reviewed source checkout with Python 3.11+:

   ```sh
   python scripts/offline_evidence_pack.py prepare --query CFTR --out citations.json
   python scripts/offline_evidence_pack.py verify --path citations.json
   ```

   `prepare` contacts **only** the fixed TMRDS HTTPS research backend `https://tmrds-public-evidence-api.onrender.com/api/v1/research/cross-check` with a public research term, bounded to two records per 22-source adapter. It refuses redirects, non-JSON, oversized responses and mismatched queries. Each adapter retains its original `responding` or `source_unavailable` status. Every contributing source must have an explicit metadata-display permission in the research gateway and **no bulk redistribution permission**. The pack strips abstracts, full text, raw sequences, patient fields and arbitrary URLs. It contains only original source IDs, titles, DOI/PMID/PMCID/NCT codes, source date and status.

2. Review source terms and citations, then **copy** `citations.json` onto the offline laptop. For automatic recognition by the standalone HTML specialist workspace, use the reviewed source checkout and place the file at `data/offline/citations.json`. This path is a local directory, never an external URL, share, GitHub content, or hosted service. Do not commit or redistribute personal case data. A SHA-256 receipt detects accidental or post-build changes but is **not** a publisher signature, content endorsement, or proof of source accuracy.

3. On the **disconnected laptop**, before reading any records:

   ```sh
   python scripts/offline_evidence_pack.py verify --path data/offline/citations.json
   python scripts/offline_evidence_pack.py search --path data/offline/citations.json --term CFTR
   python scripts/offline_evidence_pack.py search --path data/offline/citations.json --term 38718835
   ```

   `verify`, `search` and the offline evidence node use Python's standard library and make **zero network calls**. They verify the full saved metadata digest and source policy before use; a missing, symlinked, malformed, altered or oversized pack is rejected. Exact DOI strings can also be searched.

4. For the **offline HTML interface**, run `python -m scripts.run_offline_swarm --port 8765` and open `http://127.0.0.1:8765/evidence.html`. The `Scientific literature` page searches the verified pack using a separate bounded loopback-only POST contract. It accepts only `{"term":"..."}` and requires `X-TMRDS-Local-Only: public-citation-query`, a same-origin request and the fixed localhost hostname. No arbitrary filesystem path, patient record or remote address can be supplied from the browser.

The new `engines/offline_evidence_pack.py` and `scripts/offline_evidence_pack.py` are also copied into the Windows FieldLab wheelhouse ZIP. That ZIP is a Python 3.11 **research preview**, not a signed, standalone .exe; the HTML swarm still requires the separate checkout/static assets.

## Scientific safeguards

- **No offline full-text corpus is bundled.** A small metadata cache does not equal global PubMed/PMC coverage. Some of the 22 providers may be unavailable or require richer identifiers. A failed cached search is `no_cached_metadata_matches`, **not evidence that no biomedical research exists**.
- The pack reports `source_retrieved_at`, age in days, `freshness: stale` after 90 days, `current_source_freshness_verified: false`, and a list of upstream providers that were unavailable/unqueried. Source changes cannot be checked while offline.
- Bibliographic overlap and titles are **not** independent experimental replication. No gene-editing plan, physician diagnosis, medication advice, molecular-binding simulation, trial efficacy rating or quantum hardware claim is generated from this cache.
- A DOI or PMID is an original-source pointer, not a licensed copy of a paper. Source redistributions, publisher rights, and local patient-data policies require separate human review. This pack is *not* a mechanism for acquiring restricted Cochrane, UK Biobank, MIMIC-IV or other licensed datasets.
- Source snapshots and local source file paths are not written to public HTTP logs. The HTML server remains loopback-only and retains its CSP and host/origin controls. Local device encryption, authorized users, offline backup and incident response remain institutional obligations.

## Technical and test contracts

| Component | Executable functionality |
|---|---|
| `engines/offline_evidence_pack.py` | Deterministic source field allowlist, source rights gate, digest, 512 KiB/256-record limit, 22-source status, no-network local search |
| `scripts/offline_evidence_pack.py` | Prepare over fixed reviewed HTTPS; verify/search from local file; no overwriting existing packs |
| `engines/offline_specialist_swarm.py` | Evidence plane checks fixed `data/offline/citations.json` for integrity and source rights before declaring it available |
| `scripts/run_offline_swarm.py` | Same-origin, loopback-only public-citation POST without arbitrary routes or patient uploads |
| `offline/swarm/evidence.html` and `swarm.js` | Search local citation metadata with escaped text-only rendering; show unavailable/partial states |
| `.github/workflows/offline-swarm.yml` | Offline builder/integrity tests, local node/HTTP tests, JavaScript compilation |
| `.github/workflows/fieldlab-offline.yml` | Copy actual module and CLI into Windows offline bundle for verified local use |

```sh
python -m unittest discover -s tests -p 'test_offline_evidence_pack.py' -v
python -m unittest discover -s tests -p 'test_offline_swarm_http.py' -v
python -m unittest discover -s tests -p 'test_offline_specialist_swarm.py' -v
node --check offline/swarm/swarm.js
```

**Verification remains scoped:** passing a source-contract test, local parser, Windows wheel installation or SHA-256 comparison does not establish medical-device clearance, hospital data authorization, patient safety, clinical predictive performance or licensed full-text access.
