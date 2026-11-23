# TMRDS FieldLab — Actual Offline Scientific Library Integrations

**Implemented scope:** a separate offline Python workstation and Windows 11 x64 wheel bundle for research and file inspection. **Not** a validated diagnostic device, medical practice system, automated treatment planner, hospital database, imaging interpretation model, or a substitute for clinician review.

The user can run actual libraries locally, without the internet, using a terminal or desktop window. A new optional **private FieldLab → Quantum Rubik review-plan adapter** passes only the file type to the already-tested six-plane Grover simulator; it never transmits source files, patient measurements or identifiers. A queued review plane is **not verified phenotype, molecular target, or treatment evidence**. No browser, login, local HTTP server, Wi-Fi access, internet API or remote account is required by the FieldLab program itself.

## Installed packages and executed functions

| Package / version pinned | Executed operation | Accepted offline input | What is *not* implied |
|---|---|---|---|
| [pydicom 3.0.2](https://pypi.org/project/pydicom/3.0.2/) | Parse DICOM Part 10 headers; optional decoded image pixel min/max after DICOM modality LUT | Local `.dcm` / `.dicom` | No radiology interpretation, tumor detection, segmentation or validated CT windowing; compressed pixel data can require separate decoders |
| [NiBabel 5.5.0](https://pypi.org/project/nibabel/5.5.0/) | Read NIfTI header and image geometry, shape, reported voxel spacing; **does not load voxels** | `.nii`, `.nii.gz` | No NIfTI registration, inference, atlas mapping or MR diagnosis |
| [Biopython 1.88](https://pypi.org/project/biopython/1.88/) | Parse FASTA and FASTQ using actual `Bio.SeqIO`, report length, GC fraction and bounded quality summaries | DNA-only FASTA / FASTQ, max 128 records and 4 MiB | No variant calling, assembly, gene editing recommendations or patient-level interpretation |
| [RDKit 2026.9.2](https://pypi.org/project/rdkit/2026.9.2/) | Parse and sanitize public SMILES; compute molecular weight, RDKit fragment-logP, HBD/HBA, rotatable bonds and TPSA | One public non-patient SMILES (max 500 characters / 256 atoms) | No docking, cryptic-pocket structure finding, binding prediction, toxicology, efficacy or chemical synthesis |

These direct dependencies are pinned in `deploy/fieldlab/requirements.txt`. Python 3.11 / 64-bit wheels are used; indirect dependencies in the **built artifact** are hashed along with the direct packages. The SHA-256 wheelhouse inventory is **not** a publisher signature, independent binary security audit, or blanket license approval.

## Start the offline desktop on Windows 11 x64

**Prerequisites while connected to the internet:** Download and install *Python 3.11 x64*, including the Python Launcher, from its official distribution; ensure the ordinary installer includes Tkinter. Download the `TMRDS-FieldLab-Win11-x64-research` artifact from the successful `TMRDS Offline FieldLab Libraries and Win11 Wheel Bundle` GitHub Actions run, extract its ZIP to a writable folder, and independently compare its published SHA-256 with `TMRDS-FieldLab-win11-x64.sha256`. Downloading this one verified pack needs an internet connection **before** travel; operation afterward does not.

Once the ZIP is on the laptop or a removable drive:

```powershell
# After extraction; this installation uses NO package index/downloads.
powershell.exe -NoProfile -File .\scripts\install_fieldlab_windows.ps1 -BundleDir .

# The local GUI runs without an HTTP service.
.\.fieldlab-venv\Scripts\python.exe .\scripts\fieldlab_desktop.py

# Check actual installed imports/versions.
.\.fieldlab-venv\Scripts\python.exe .\scripts\fieldlab_cli.py status
```

Use Windows PowerShell 5.1 or PowerShell 7+ as installed; the installer itself is PowerShell code using Windows Python Launcher. The ZIP includes the source code, dependency wheelhouse, hashes and installer, but **does not contain Python itself** or a standalone signed Windows `.exe` installer. Current Windows release-gate evidence is a tested ZIP + manual prerequisite, not a hardware-validated single-click installer.

### Local research CLI

```powershell
# Explicit local authorization flag is mandatory; no upload is implemented.
.\.fieldlab-venv\Scripts\python.exe .\scripts\fieldlab_cli.py inspect --private-local C:\my_local_data\study.dcm

# Opt in to pixel decode/summary (supported codecs only, memory/size bound).
.\.fieldlab-venv\Scripts\python.exe .\scripts\fieldlab_cli.py inspect --private-local --pixel-summary C:\my_local_data\study.dcm

# NIfTI spatial metadata only.
.\.fieldlab-venv\Scripts\python.exe .\scripts\fieldlab_cli.py inspect --private-local C:\my_local_data\brain.nii.gz

# Offline Rubik review-plan simulation: local molecule output -> abstract evidence plane.
.\.fieldlab-venv\Scripts\python.exe .\scripts\fieldlab_cli.py molecule --smiles "CCO" --cube-plan

# Public chemistry reference; no binding or efficacy prediction.
.\.fieldlab-venv\Scripts\python.exe .\scripts\fieldlab_cli.py molecule --smiles "CCO"
```

Supported local numeric lab CSV: header `code,value,unit`; values must be finite and codes/units constrained. LOINC syntax may appear, but code identity, calibration, reference intervals, units, measurement uncertainty and clinical interpretation are **not** independently checked. The software does not assign high/low flags or suggest patient treatment.

A clinician's local scan can contain protected information even when an adapter omits patient names, UIDs and source paths from the printed output. **Use an organization-approved encrypted Windows laptop and approved local storage**. Local output can contain biomedical measurement values; do not upload to the public site, store unencrypted logs, or use USB drives without organizational approval. The CLI cannot assert HIPAA compliance; keeping network calls out of this code is necessary but not sufficient.

## Linux disconnected-container alternative

The separate `Dockerfile.fieldlab` installs actual packages during image build. Move the built image securely to the destination before disconnecting. Then run with all network access removed:

```bash
docker build -f Dockerfile.fieldlab -t tmrds-fieldlab:offline .
docker run --rm --network none --read-only --cap-drop ALL --security-opt=no-new-privileges tmrds-fieldlab:offline status
docker run --rm --network none --read-only --cap-drop ALL --security-opt=no-new-privileges tmrds-fieldlab:offline molecule --smiles CCO
docker run --rm --network none --read-only --cap-drop ALL --security-opt=no-new-privileges -v "$PWD/synthetic-fixtures:/input:ro" tmrds-fieldlab:offline inspect --private-local /input/example.dcm
```

Do not assume the Docker image can be built when offline: the **build** downloads Python base images and wheels. Only the previously downloaded and built **runtime** is designed for operation without a network.

## Automated real-library release gates

`.github/workflows/fieldlab-offline.yml` runs Linux and **Windows 11 x64**. Each runner downloads binary wheels, performs an **offline install from downloaded wheels** (`pip --no-index`), imports actual libraries, executes synthetic DICOM pixel decoding, actual NIfTI geometry decoding, Biopython FASTA/FASTQ, and RDKit descriptor calculations; verifies bad-file, symlink, corrupted wheel and patient-tag export negative cases. The Windows job generates a ZIP, a SHA-256 of the ZIP, and wheel-by-wheel integrity receipt. Linux additionally builds and runs a FieldLab image with Docker `--network none`.

Tests validate parser behavior on synthetic fixtures; they **do not** prove regulatory approval, clinical performance, no data leakage in unrelated Windows processes, system-level filesystem encryption, laboratory measurement accuracy or compatibility with every DICOM transfer syntax.

## What remains separate

The existing online Quantum Rubik's Cube uses public source adapters, and the six-qubit Grover simulation is an abstract plan-coverage demonstration, not a cure-finding quantum computation. FieldLab operates privately and **does not transmit patient data to that API**.

Other open-source components can be independently installed in isolated work packages: Weasis / 3D Slicer for complete local image visualization; GDCM/PylibJPEG for selected compressed transfer syntaxes; MONAI and nnU-Net for validated model-specific segmentation; nf-core/Nextflow and pysam/DeepVariant for reference-genome-aware variant analysis; RDKit/OpenMM/Boltz-2 for protein/ligand research; Medplum/OpenEMR/HAPI FHIR for institutional clinical records; approved offline literature snapshots for low-connectivity evidence access. They are **not bundled** in this FieldLab release. AlphaFold 3 model parameters have restrictive terms; software code and weight rights differ. Medical images and patient records require appropriate institutional approval, model scope review, informed consent/legal basis where applicable, and clinical safety evaluations.

**Admission criterion for any future "offline doctor results in minutes" feature:** measure time on an actual representative rural laptop with network disconnected, validate case/reference inputs against qualified clinical interpretation, quantify false positives/false negatives, data leakage, biases and uncertainty, and show exact model/package licenses and SHA-256. No unverified diagnostic outcome should be represented as a medical result.

References:
- [pydicom pixel data and modality LUT](https://pydicom.github.io/pydicom/stable/guides/user/working_with_pixel_data.html)
- [pydicom compressed transfer syntax dependencies](https://pydicom.github.io/pydicom/stable/guides/plugin_table.html)
- [NiBabel documentation](https://nipy.org/nibabel/)
- [Biopython SeqIO documentation](https://biopython.org/wiki/SeqIO)
- [RDKit descriptor reference](https://www.rdkit.org/docs/GettingStartedInPython.html)
- [Weasis desktop viewer](https://weasis.org/en/)
