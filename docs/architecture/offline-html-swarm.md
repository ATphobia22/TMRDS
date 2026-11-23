# Sovereign HTML Specialist Swarm — TMRDS Local Research Protocol

## Two different trust zones

**GitHub** is the audited *source-code and release registry*, not a live patient-record server. All repositories, Actions logs, public Pages, cloud API routes and third-party LLMs must remain free of patient information. The public research service continues to query external biomedical citations, trial metadata and chemical records only.

**Offline laptop** is the only zone for authorized local records. A Python 3.11 process binds **127.0.0.1** only and serves seven linked HTML panels using no CDNs, analytics, fonts, remote scripts or WebSockets. A bounded JSON-RPC 2.0 route, `POST /rpc`, lets panels call allowlisted local science modules. The loopback interface supports synthetic demonstrations only; real locally authorized file reading occurs through a separate CLI command and is never exposed to the browser RPC bridge.

## Actual nodes

| HTML entrypoint | JSON-RPC method | Executed capability |
|---|---|---|
| `index.html` | `swarm.run` | Concurrent fan-out to five independent synthetic research nodes; each per-node failure is explicit |
| `lab.html` | `lab.synthetic_demo` | Real numeric parsing of built-in synthetic lab CSV, source hash and data-use restrictions |
| `imaging.html` | `imaging.synthetic_demo` | pydicom+NumPy in-memory DICOM creation and actual MR image pixel decoding; no patient image |
| `molecular.html` | `molecular.descriptors` | Actual RDKit molecular parsing and standard descriptors of bounded research SMILES |
| `quantum.html` | `quantum.grover` | Exact six-qubit Grover research-coverage statevector and classical 64-state baseline |
| `evidence.html` | `evidence.offline_status` | Truthful `not_installed` status of local WikiMed/Kiwix/ZIM and licensed knowledge corpus |
| `review.html` | `governance.review` | Required clinician review, explicit **no clinical decision** receipt |

The common `swarm.js` makes requests through same-origin `fetch("/rpc")`. It uses a 16-second browser deadline, no cookies, no external URL loading and text-only JSON rendering (`textContent`), not executable HTML. Security headers prohibit remote scripts, remote fetching, embedding and unsafe form submissions. The HTTP host is restricted to `localhost`/127.0.0.1, Origin must equal the service origin, JSON body is limited to **4096 bytes**, methods and parameter keys are allowlisted, and no request body is logged.

### JSON-RPC request contract (static example; not patient content)

```json
{"jsonrpc":"2.0","id":3,"method":"quantum.grover","params":{"scenario":"disease"}}
```

Response outline:

```json
{
  "jsonrpc":"2.0",
  "id":3,
  "result":{
    "schema_version":"1.0",
    "task":"synthetic_research_coverage_planning",
    "backend":"classical_exact_statevector_simulator",
    "execution":{"quantum_hardware_used":false,"patient_data_ingested":false},
    "governance":{"clinical_promotion_allowed":false,"human_authority_final":true}
  }
}
```

The actual result includes normalized oracle probability, deterministic digest and bounded marked review plans. An invalid method or patient identifier request receives a **non-executing error**, never a clinical answer.

### Swarm fan-out and provenance

`swarm.run` executes at most four workers simultaneously and reports each node's state as `completed` or `unavailable` with a per-node result. It does **not** summarize multiple synthetic observations into a disease diagnosis or confidence score. A SHA-256 receipt covers **execution states only**, not scientific results, patient identity or immutable ledger proof. The supervisor review output always says human clinician authorization is required.

### What this protocol is *not*

- It is not the official OGC **OpenMI 2.0** runtime. OpenMI specifies runtime exchange of values between model components; OpenMI conformance is not established by a JSON-RPC wrapper.
- It is not an HL7 v2, SMART on FHIR, DICOMweb, WebSocket, Redis, Kafka, OpenAPI or AsyncAPI implementation. Each requires its own conformant protocol, authentication and testing. Future standards can be bridged **only within an authorized clinical perimeter**.
- It does not install a local language model, execute Ruflo, simulate a patient-physiology model or produce verified differential diagnoses. Claims of flawless HIPAA de-identification or a 'BibleGuard' fairness guarantee cannot be accepted based on regex rules.
- It does not integrate an unrestricted EHR or medical PACS into an anonymous server. Orthanc, Weasis, MONAI, OpenEMR, HAPI FHIR, GNU Health, Synthea and OpenELIS remain separately deployable products needing access/rights and local verification.
- It does not reproduce Microsoft's proprietary MAI-DxO or prove multi-agent clinical accuracy. Microsoft's reported complex-case benchmark accuracy is specific to a controlled evaluation; it does not establish accuracy or safety of this implementation on rural patients.

## Performance and tests

The offline workflow executes actual package parsers against synthetic artifacts on a **Windows Python 3.11 x64 runner**, after `--no-index` installation from a hashed wheelhouse. Cross-platform tests exercise origin and Host enforcement, invalid patient/URL requests, standard JSON-RPC envelopes, seven HTML pages, in-memory synthetic lab and MR parsing, RDKit chemistry and six-qubit math.

The only guaranteed time bounds are declared request-size constraints and per-module wait time; no 'minutes rather than days' medical accuracy or processing time has yet been measured on a physical rural laptop. Validation and benchmark data remain necessary before clinical deployment.
