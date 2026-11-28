# TMRDS portable offline workstation — actual optional biomedical readers

**Status:** Windows/Python 3.11 x64 **technical research preview**, with an unsigned CI artifact and operator-managed Ed25519 package-signing support. It is NOT a ready-to-use clinical diagnostic product, FDA-cleared device, or complete standalone Windows installer. No current release demonstrates accurate automated MRI/CT interpretation, drug efficacy, gene-editing recommendations, or differential diagnosis.

## Locally executed open-source components

| Component | Fixed installation | Actual bounded operation |
|---|---|---|
| pydicom | 3.0.2 | Local DICOM Part-10 metadata, optionally uncompressed MR/CT pixel min/max/mean and CT modality LUT |
| Biopython | 1.88 | Local FASTA/FASTQ sequence count, bases, GC fraction, FASTQ Q20 flags |
| RDKit | 2026.9.2 | Local SMILES and SDF parsing, molecular weight, logP, H-bond and polar surface descriptors |
| pypdf | 7.1.0 | Local PDF page/text-extraction counts (no OCR, no returned full text) |
| Python standard library | Python 3.11 | FHIR Observation/Bundle structure, CSV/TSV lab row/units counts |
| Grover statevector module | repository code | Reproducible six-plane synthetic research coverage experiment, not quantum hardware |

These are actual conditional imports and callable readers in `engines/offline_workstation_adapters.py`, not simply catalog listings. `scripts/qrce_offline_workstation.py doctor` reports installed and enabled packages honestly. No server process, data download, or remote API is required for local file inspection.

**Limits:** Only authorized local files can be inspected. Input is bounded to 64 MiB and 1000 records (except the PDF page cap of 32). The output does not expose patient names/IDs, DICOM UIDs, raw genetic sequences, extracted PDF text, individual laboratory values or FHIR subject references. The authorized operator is still responsible for encryption, source rights, retention, clinical privacy, safe file storage, operating-system access control and deletion. A SHA-256 hash alone is not a signature or HIPAA compliance proof.

## Windows 11 x64 offline build and use

A successful `QRCE Offline Workstation Real Integrations` GitHub Actions job produces `tmrds-offline-python311-win-x64-research-preview` as a **Windows Python wheelhouse artifact**, not a native `.exe`. Prepare and transfer it on a trusted device. Requires separately installed Python 3.11 x64 on the offline laptop. Exact wheel SHA-256s and matching Python/OS profile are checked offline, but artifact authenticity and licensing still require trusted download and human review.

```powershell
# All operations below on the offline laptop after trusted file transfer.
py -3.11 scripts/qrce_wheelhouse.py verify wheelhouse
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --isolated --no-index --find-links wheelhouse -r deploy/offline/requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/qrce_offline_workstation.py doctor
.\.venv\Scripts\python.exe scripts/qrce_offline_workstation.py inspect "D:\authorized\CT.dcm" --authorized-local --pixel-qc --html-report "local-review.html"
.\.venv\Scripts\python.exe scripts/qrce_offline_workstation.py molecule --smiles "CCO"
.\.venv\Scripts\python.exe scripts/qrce_offline_workstation.py cube
```

**Linked specialist HTML apps / loopback swarm:**

```powershell
.\.venv\Scripts\python.exe scripts/qrce_swarm_local.py --port 8765
# Open http://127.0.0.1:8765/ in the laptop browser
```

The HTML pages run locally and invoke narrowly allowlisted JSON-RPC 2.0 operations to test **built-in synthetic** lab/MR fixtures, RDKit descriptors and six-qubit mathematics. The swarm has no patient-file upload path or external-network transport and does not depend on internet access. The separate CLI can inspect individually authorized local files. View the [swarm architecture and JSON-RPC contract](../architecture/offline-html-swarm.md).

The existing public https://tmrds-public-evidence-api.onrender.com/ is an anonymous **public-source research** service. Never send patient records or laboratory files to that website.

## Distribution integrity and operator signing

The wheelhouse SHA-256 manifest protects against accidental file changes but is **not a publisher signature**. CI now creates `DISTRIBUTION-MANIFEST.json` over every file in the assembled Windows package and verifies that inventory. The CI artifact remains **unsigned**: no private signing key is stored in GitHub, no signature is created by CI, and no public release is published by this workflow.

A release operator may sign the completed package on a separately controlled machine with an existing unencrypted Ed25519 PEM private key. Do not put the private key in the repository, CI, package directory, or a patient-data workflow. On POSIX, the signing utility requires owner-only `0600` permissions; on Windows, the operator must enforce an equivalent restrictive NTFS ACL.

```powershell
# Run from a trusted Python environment with cryptography installed.
py -3.11 scripts/distribution_signing.py sign .\offline-release --private-key C:\secure\keys\tmrds-release-ed25519.pem
# Record the returned public_key_sha256 fingerprint in a trusted channel.

# On the receiving workstation, verify BEFORE installing package wheels.
py -3.11 scripts/distribution_signing.py verify .\offline-release --public-key .\trusted-tmrds-release.pem --expected-public-key-sha256 <64-character-out-of-band-fingerprint>
```

The verifier requires a trusted Python environment that already has `cryptography` installed from a separately trusted source; do not bootstrap trust by installing an unverified wheel from the package being checked. The expected public-key fingerprint must be obtained independently of the package. The signature authenticates package bytes against that key; it does not establish dependency-license review, clinical validation, efficacy, or regulatory status. If the package changes after manifest creation, rebuild the manifest and sign again.

## Offline medical knowledge and deployment boundaries

Kiwix/WikiMed offers separately downloadable ZIM files and an offline reader, but no WHO, FDA, clinical guideline or PubMed full-text archive is bundled in this research preview. Licensed corpora need source versions, terms, citation integrity, snapshot hashes, editorial update dates, incremental/whole-file update strategy, and explicit staleness warnings before use. The `evidence` specialist panel reports `not_installed` until a real offline content pack is verified.

Weasis and 3D Slicer can be launched as **independent installed software** on a secure offline laptop, but they are **not** included or executed in this artifact. Existing OHIF/Orthanc and MONAI integrations remain separate controlled research services. Clinical software cannot become safe simply because it is open source or because two apps can exchange JSON.

## Clinical deployment prerequisites

Before using real patient cases for care: define clinical intended use, secure authentication/role control and encryption, local audit/retention, consent, independent security assessment, validated DICOM rendering and orientation, medical terminology/reference ranges, benchmarks against independently reviewed local cases (with sensitivity/specificity/false negatives), clinician acceptance tests, device/regulatory assessment and facility training. A fast parser is not a laboratory analyzer, a valid reference range, or evidence of a treatment. Current software shall not autonomously prescribe, diagnose, or suggest gene-editing procedures.

## Relevant original documentation

- https://pydicom.github.io/pydicom/stable/guides/user/working_with_pixel_data.html
- https://biopython.org/
- https://www.rdkit.org/docs/
- https://pypdf.readthedocs.io/
- https://kiwix.org/
- https://weasis.org/
