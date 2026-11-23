# TMRDS sovereign offline specialist swarm — initial executable workstation

**Date:** 2026-11-23. **Stage:** synthetic-data research engineering prototype only. Not a medical device, hospital information system, diagnostic assistant, approved therapy recommender, personal-record storage system, or independently validated clinical workstation.

## Why a swarm, and why GitHub is not the live patient brain

`ATphobia22/TMRDS` is the **version-controlled code and governance authority**: source adapters, tests, human-review rules, evidence schemas, source licenses, and signed releases. It is **not** a database of patients and cannot orchestrate offline tasks when the laptop has no Internet connection. The **local Python process** is the runtime coordinator; its HTML specialists communicate over loopback HTTP and browser `CustomEvent` messages. The first prototype accepts only built-in, nonidentifying synthetic research cases.

```text
GitHub TMRDS (source and tests, only when updating)
                |
       reviewed local package
                v
  Windows / Linux / macOS laptop, Internet DISCONNECTED
                |
       127.0.0.1 loopback-only process
                |
    /api/local/capabilities   /api/local/run
                |
        TMRDS OfflineSwarm
                |
   +------------+-----------+------------+
   | lab parser | VCF parser| Grover math|
   +------------+-----------+------------+
         |             |           |
    Source hash     Source hash   Oracle hash
                |
         research events (in memory)
                |
     supervisor / human-review-required
                |
        deterministic receipt
   No cloud, PHI, diagnosis, eRx, or real DICOM interpretation
```

## Run the standalone offline workstation

On a laptop with **Python 3.11+**, obtain a checked-out and inspected repository release. The demo engine, HTML, JS, CSS and HTTP coordinator require only Python and JavaScript standard-library capabilities, not Docker or a cloud service. For first setup, install the runtime while connected; then **disconnect the network** and confirm all pages and synthetic local processing still work.

```sh
python -m scripts.run_offline_swarm --port 8765
```

Open `http://127.0.0.1:8765/` using a locally installed browser. Use `--port 0` to bind a free loopback port (the exact address is printed). You can visit the nine real HTML entries: dashboard, labs, imaging, genomics, evidence, drug discovery, quantum, knowledge and supervisor. A button runs the selected built-in synthetic scenario; the coordinator returns real parser results and an evidence receipt.

The instance is **not exposed to the LAN** and does not write patient records or create an upload endpoint. Host-header checks, origin checks, a required custom synthetic-only request header, a 256-byte request cap, no cookies/CORS, no cache, restrictive CSP and a short allowlist protect the demo. No persistent audit ledger or clinical access-control system is included. Don't expose it behind a reverse proxy or tunnel. This is not a HIPAA compliance assessment.

### Actual capabilities versus missing prerequisites

| Specialist HTML application | What executes now | What remains absent |
|---|---|---|
| Laboratory | TMRDS's existing bounded synthetic CSV/LOINC-like numeric inspector; no clinical reference-range interpretation | Authenticated OpenELIS connector, approved LOINC/UCUM map, reference intervals, clinical lab validation |
| Genomics | Existing synthetic 8-column, sample-free VCF parser, with source-byte SHA-256 | Reference-genome build, clinical BAM/CRAM/VCF genotype parsing, variant interpretation validation |
| Quantum research | Actual 6-qubit mathematical Grover plan simulator and classical baseline | QPU, fault-tolerant algorithms, chemical oracle, proven quantum speedup |
| Imaging | Explicit DICOM prerequisite status | Authorized DICOM reader, pixel decode/CT rescale, workstation viewer, calibrated clinical validation |
| Research evidence | Reports no bundled offline literature snapshot | Licensable metadata cache, dated offline snapshot and source freshness review |
| Drug discovery | Reports model not executed | RDKit/OpenMM/DeepChem validated molecule pipeline, model weights/license, biological assays |
| Knowledge | Reports external Kiwix WikiMed archive not bundled | Independently downloaded legal ZIM and local reader plus dated snapshot/index |
| Supervisor | Explicit human-review-required policy and deterministic receipt | Account authentication, professional approval record, prospective clinical validation |

The **Kiwix** open-source reader and **WikiMed ZIM** are separately downloadable. Archive size varies by release; do not hardcode the supplied 2–5 GB estimate or mirror licensed ZIM archives into this repository without review. Direct ZIM integration is not yet implemented; offline knowledge is truthfully marked unavailable until separately provisioned.

## Inter-app contracts and event rules

- `offline/swarm/contracts/openapi.yaml` describes the implemented **loopback REST** endpoints `GET /api/local/health`, `GET /api/local/capabilities` and `POST /api/local/run`.
- `offline/swarm/contracts/event.schema.json` validates the actual in-page event envelope: `event_id`, `channel`, `node`, `data_class=synthetic_nonidentifying`, `status`, `result_sha256` and `clinical_promotion_allowed=false`.
- `offline/swarm/contracts/asyncapi.yaml` documents the current event *semantics* for future interoperability. **There is no WebSocket server or JSON-RPC runtime yet.** Do not claim a JSON-RPC/AsyncAPI message bus is deployed.
- Each local specialist is an HTML app that calls the same process, not a separate unauthenticated listening network port. The model computes source-scoped receipts for the built-in fixtures, not a Daubert certification or regulator-signed immutable ledger.
- **OpenMI 2.0** is a model-exchange standard for time/space simulation components. It is not the current message bus and does not implement HL7, DICOM, SMART authentication or regulatory review. `openmi_2_conformance=false` until independently tested.

## Future implementation gates — real clinical deployment

Clinical records, diagnoses, medicines, genetic variants and DICOM images cannot safely enter this public/synthetic demo. The next separate local-clinical environment would need an authenticated per-clinic identity/role service; encryption at rest; purpose-specific retention and consent; consent-aware local FHIR R4/LOINC/UCUM/HL7v2 and DICOMweb boundaries; verified offline reference snapshots; validated image codecs; audit-record tamper resistance; an emergency-offline failure model; jurisdiction-specific privacy compliance; and a formal risk and clinical performance evaluation. These are nontrivial infrastructure and regulatory requirements.

No automatic clinical diagnosis, diagnosis confidence score, prescription, insulin dosing, gene-editing action or medical-device actuation is allowed without the full clinical safety/approval path. Model-generated differentials must undergo independent validation, not only an expert-looking multi-agent conversation. Claims that one medical-agent benchmark reached 80–85.5% on selected challenging cases do **not** validate this system or guarantee comparable rural-world performance.

For drug-discovery and protein-structure research, expensive or restricted AlphaFold 3/Boltz/OpenMM weights and reference databases belong in a versioned, separately licensed computational node; cheap offline laptops may not be able to run them, and the results are hypotheses rather than treatment orders.

## Verification

```sh
# Real local HTTP, security-policy, synthetic parser and Grover tests:
python -m unittest discover -s tests -p 'test_offline_specialist_swarm.py' -v
python -m unittest discover -s tests -p 'test_offline_swarm_http.py' -v
node --check offline/swarm/swarm.js
python -m compileall -q engines/offline_specialist_swarm.py scripts/run_offline_swarm.py

# Check the offline server without the internet:
python -m scripts.run_offline_swarm --port 8765
# From a separate local terminal:
curl -fsS http://127.0.0.1:8765/api/local/capabilities
curl -fsS -H 'Content-Type: application/json' -H 'X-TMRDS-Local-Only: synthetic-demo' \
  -d '{"scenario":"synthetic_all"}' http://127.0.0.1:8765/api/local/run
```

GitHub Actions workflow `.github/workflows/offline-swarm.yml` runs offline contract tests on changes. Passing these tests proves the prototype's **synthetic software behavior** in CI, not medical efficacy, privacy certification, a ready-to-install Windows installer, or that all 122 cataloged projects are installed.

## Primary references

- [HL7 FHIR R4 Observation](https://hl7.org/fhir/R4/observation.html) — clinical data semantics, not permission to exchange records
- [AsyncAPI 3.0](https://www.asyncapi.com/docs/reference/specification/v3.0.0) — message-contract vocabulary
- [OGC OpenMI 2.0](https://www.ogc.org/standards/openmi/) — model runtime data exchange
- [Kiwix official offline medical archives](https://get.kiwix.org/en/solutions/hotspots/content-bundles/medical/) — ZIM license and release review
- [Microsoft MAI-DxO Sequential Diagnosis benchmark](https://arxiv.org/abs/2506.22405) — selected research benchmark, not TMRDS clinical validation
