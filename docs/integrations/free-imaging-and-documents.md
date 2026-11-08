# Free imaging and public-document tools

Implemented capabilities use local open-source packages, no paid API and no
model/checkpoint download. Normal hardware, bandwidth and CI quotas still apply.
No EHR or scanner is connected and no medical model was run.

## Offline MONAI evaluation

MONAI 1.6.1 (Apache-2.0) and CPU-only PyTorch 2.15.0 are optional dependencies.
They are separate from the API image and do not activate the inactive
`MONAIVisionNode` diagnostic placeholder.

```bash
python -m pip install torch==2.15.0+cpu --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r deploy/monai/requirements.txt
python scripts/evaluate_research_masks.py reference.npy candidate.npy --output overlap.json
```

Inputs must be matching 3D binary arrays; NumPy pickle loading is disabled.
Evaluation uses actual MONAI DiceMetric on CPU, returns package versions and
input-file SHA-256 checksums, and abstains when both masks are empty. No lesion
finding, inference result, confidence score or efficacy claim is generated.
Shape equality cannot establish spatial alignment: the researcher must verify
spacing, orientation and registration before evaluating overlap. No image is
uploaded, and no new API accepts raw masks or patient scans.

## Offline public-PDF extraction

pypdf 6.21.4 (BSD-3-Clause) provides a local alternative to metered conversion:

```bash
python -m pip install -r deploy/documents/requirements.txt
python scripts/extract_public_pdf.py public-paper.pdf --public-document --output paper-text.json
```

Requires explicit public-document attestation; it is not PHI detection or a
copyright license. It preserves page numbers, source checksum and truncation
state. Empty text is reported as `no_text_layer`, not fabricated OCR. The input
limit is 10 MiB and at most 100 pages may be processed; compressed content can
still consume significant resources. Run untrusted PDFs in an isolated process
with memory/time limits. No external conversion service or OCR is invoked.
Existing output files are not overwritten.

## Orthanc/OHIF runtime acceptance

The imaging workflow now starts the existing digest-pinned archive and tests:
HTTP authentication, upload of the generated synthetic fixture, QIDO study UID
matching, WADO frame retrieval and serving OHIF HTML. It tears down containers
when the job ends. These are transport tests; serving OHIF HTML is not a browser
render, GPU/MPR test, segmentation validation or clinical deployment.

Docker is unavailable in the authoring environment; runtime results must be
read from the new GitHub Actions job before claiming success. Reproduce locally
using the imaging sandbox guide and then:

```bash
python scripts/imaging_runtime_smoke.py --live
```

## Discovery and licensing review

The reviewed resource catalog is available at
`GET /api/v1/medical/open-source-resources` and in
`engines/open_medical_resources.json`.

Searches covered GitHub `topic:medical`, `topic:healthcare`,
`topic:medical-imaging`, the requested curated lists, and primary project pages.
Repeated entries in the request were deduplicated.

- [Awesome Healthcare](https://github.com/kakoni/awesome-healthcare) and
  [Awesome Medical Imaging](https://github.com/fepegar/awesome-medical-imaging)
  are discovery lists, not permission to redistribute every linked dataset.
- The [medical VLM list](https://github.com/yangzhou12/awesome-medical-vision-language-models)
  and [MONAI VLM framework](https://github.com/Project-MONAI/VLM-Radiology-Agent-Framework)
  require separate code, checkpoint and training-data review. No medical VLM is
  installed or advertised as diagnostic functionality.
- [OpenEMR](https://github.com/openemr/openemr/blob/master/LICENSE) is GPL-3.0.
  Certification is version/configuration-specific and does not transfer to TMRDS.
  Its existing FHIR integration target remains disconnected.
- [3D Slicer](https://github.com/Slicer/Slicer/blob/main/License.txt) uses a
  BSD-style custom license. Desktop deployment and extensions are separate work;
  this change does not claim Slicer is installed.
- [MONAI](https://github.com/Project-MONAI/MONAI/blob/dev/LICENSE) is Apache-2.0;
  [metrics docs](https://docs.monai.io/en/stable/metrics.html) describe overlap
  evaluation. Framework licensing does not determine model-bundle licensing.
- [AMID](https://github.com/neuro-ml/amid) offers dataset interfaces; some raw
  datasets require manual download and separate usage agreements.
- [TCIA usage policy](https://www.cancerimagingarchive.net/data-usage-policies-and-restrictions/)
  includes attribution and restrictions on re-identification; individual
  collections have separate licenses. No bulk dataset was downloaded.
- AWS documentation identifies IDC as a public imaging resource. Public data
  does not imply free cloud compute or storage; no AWS resources were created.

Further gates: actual browser rendering and keyboard/accessibility review,
Slicer interchange with verified physical coordinates, dataset-specific review,
model evaluation on independent datasets and institutional review before patient
use. Proprietary plugin API access remains subject to its provider's terms.

### Internal-network port correction

Runtime testing found that publishing a port from an exclusively internal Docker
network did not make the running archive reachable. The recipe now publishes
`127.0.0.1:8042` from a digest-pinned nginx proxy attached to the internal archive
network and a frontend bridge. Orthanc remains internal-only; its HTTP
 authentication remains required and DIMSE remains disabled. The proxy enforces a
10 MiB request limit for this small synthetic sandbox. See
https://github.com/moby/moby/discussions/53256 and
https://docs.docker.com/engine/network/port-publishing/ .
