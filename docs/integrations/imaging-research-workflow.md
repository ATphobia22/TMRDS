# Imaging research workflow

This workflow adds five optional capabilities without patient data, paid APIs or remote model execution. It is for research. A checksum identifies bytes, not origin authenticity, de-identification or clinical validity.

## Bounded Python DICOMweb

Install `python -m pip install -r deploy/imaging/requirements.txt`. `ResearchDICOMweb` uses dicomweb-client 0.61.0 with library retries disabled and `ImagingSession`, which reuses `OutboundRequestPolicy`. Each request has 5-second connect/10-second read timeouts, a 30-second streaming deadline, a 10 MiB decompressed response cap, redirects disabled, environment proxies disabled, and a fixed origin/path. Study queries permit 1–100 records. The wrapper exposes QIDO studies and instance metadata, with UID validation; it does not expose STOW or arbitrary pixel-volume retrieval. These are synchronous research operations, not async API handlers. DNS validation shares the existing transport's DNS rebinding limitations; use network egress controls in production.

After starting the existing synthetic Orthanc stack:

```bash
python scripts/imaging_research.py studies
```

The exact loopback URL is a separate explicit sandbox exception; public sources still require HTTPS and public addresses. Credentials come from the generated private local configuration. CI runs the actual client against the synthetic archive and checks study identity and instance metadata.

## OHIF research mode

The original packages in `extensions/ohif-tmrds-research` and `modes/ohif-tmrds-research` target **OHIF 3.11.0**, source commit `522531cc5c97ed05470f55a7a8f6571d9a512bd4`. The mode wraps OHIF's longitudinal mode, preserving its viewport and tool lifecycle. It adds a visible provenance panel showing study, series and SOP instance UIDs, SHA-256, source, reviewer and review state. Missing evidence stays `not evidenced` / `pending`. Evidence must match all three UIDs; a sidecar is a declaration, not independently authenticated evidence. The panel does not change review state or approve treatment.

Create a fresh upstream checkout and install the packages before its normal build:

```bash
git clone https://github.com/OHIF/Viewers.git /tmp/tmrds-ohif
git -C /tmp/tmrds-ohif checkout 522531cc5c97ed05470f55a7a8f6571d9a512bd4
python scripts/imaging_static_export.py
python scripts/install_ohif_research.py /tmp/tmrds-ohif --evidence data/imaging-static/provenance.json
cd /tmp/tmrds-ohif
yarn install --frozen-lockfile --non-interactive
APP_CONFIG=config/tmrds.js PUBLIC_URL=/ QUICK_BUILD=true yarn build
```

The installer refuses other OHIF versions and existing TMRDS package directories. It registers the packages in `platform/app/pluginConfig.json` and creates a localhost-only app configuration. Build output is in `platform/app/dist`. This is a separate OHIF build; Orthanc's prebuilt bundled viewer does not automatically contain these packages. Authentication/proxy and CORS must be configured for a separately hosted live viewer; no credentials are embedded in app config. CI builds the pinned upstream viewer and checks emitted assets. This proves compilation, not browser viewport rendering.

## MONAI bundle gate

`review_bundle` verifies local weights, license text and model card checksums, safe relative file paths, file size, a reviewed license identifier and explicit named human review attestations. Unknown licenses stop for review. Allowlisted identifiers are a local policy, not legal advice or confirmation of a model's declared license. A reviewer must compare the declaration to the actual license and intended use. Model weights and training datasets can have different terms.

Example local manifest (replace every checksum with the actual artifact hash):

```json
{
  "license": "Apache-2.0",
  "license_file": "LICENSE",
  "model_card": "docs/model-card.md",
  "weights": "models/model.pt",
  "intended_use": "research",
  "reviewer": "reviewer-identifier",
  "license_reviewed": true,
  "model_card_reviewed": true,
  "files": {
    "LICENSE": "actual-sha256",
    "docs/model-card.md": "actual-sha256",
    "models/model.pt": "actual-sha256"
  }
}
```

```bash
python scripts/imaging_research.py review-bundle /path/to/bundle /path/to/review.json
```

`load_reviewed_weights` rechecks the exact weight bytes before CPU-only `torch.load(weights_only=True)` and accepts only a string-to-tensor state dictionary. It never evaluates MONAI bundle config expressions, imports bundle code, downloads weights or constructs a model architecture. Use this entry point for any future TMRDS weight loading. The existing MedicalNet adapter now constructs with `pretrained=False` and routes manual/pretrained loading through this gate; it refuses pretrained requests without a reviewed local bundle and labels random initialization `UNTRAINED_RESEARCH`. Automatic MONAI/Hugging Face downloads and the substitute feature-extractor stub were removed. Existing MONAI mask metrics do not load models. No pretrained model has been downloaded or approved by this change. Large/malformed tensor checkpoints still require OS memory/CPU isolation.

## Human annotation through MONAILabel

`HumanAnnotationClient` implements the MONAILabel 0.8.5 `save_label` wire contract: `PUT /datastore/label`, image/tag query parameters, multipart label and JSON params. It sends a reviewer identifier, source UID triple, label checksum and `human_submitted` state. Research submission never means clinical approval. File bytes are limited to 10 MiB and response bytes to 1 MiB; there are no write retries. The server remains responsible for format/geometry validation, access control and persistent storage. A failed/timed-out response may follow a successful write: reconcile the server before resubmitting.

Run a MONAILabel server/app separately on `127.0.0.1:8000`, using its officially supported environment and license terms. Configure its datastore image IDs and disable automatic training/inference hooks if human-only behavior is required: MONAILabel calls the application's `on_save_label` hook after saving. This adapter does not call infer/train, but cannot override server hooks. The default client only permits this exact local origin; Python callers can configure a protected HTTPS server and authentication explicitly. No internet-facing annotation server is provisioned.

```bash
python scripts/imaging_research.py annotation-info
python scripts/imaging_research.py submit-label --image datastore-image-id \
  --label /private/path/annotation.nrrd --reviewer reviewer-id \
  --study 1.2.3 --series 1.2.4 --instance 1.2.5 --confirm-human-review
```

Use the actual UIDs and image ID from the reviewed study. The tool outputs a JSON submission receipt to the caller; save it only in a private research workspace. No patient data should be placed in repository files, Actions logs or public static assets. Contract tests exercise the exact multipart request without claiming a running MONAILabel server or actual human labeling session.

## Static/offline evaluation

```bash
python scripts/imaging_static_export.py
python -m http.server 8080 --bind 127.0.0.1 --directory data/imaging-static
```

Only newly generated synthetic data can be exported. The exporter writes OHIF's DICOM JSON launch file, the Part 10 DICOM, provenance sidecar and checksummed manifest. It removes archive credentials/config. Serve the built OHIF assets locally as well; place these synthetic export files in the same served directory for a same-origin setup. The corresponding research route is `/tmrds-research/dicomjson?url=http%3A%2F%2F127.0.0.1%3A8080%2Fohif-dicom.json` when the viewer is served at port 8080. To retain that origin, serve the combined directory there instead of the export-only command above.

Decision: adopt this small synthetic pilot for reproducible offline evaluation. It needs no cloud costs. Do not replace the archive with static hosting: this format supplies no QIDO querying, STOW, authentication or revocation; copying real DICOM can expose identifiers in both headers and pixels. Full offline readiness still requires local OHIF assets, codecs, a browser viewport check with external network disabled, and a licensing/privacy review of any nonsynthetic export. The manifest explicitly leaves browser rendering unverified.

RadicalImaging Static-DICOMWeb remains an alternative for precomputed WADO/frame stores and larger collections. It introduces a separate conversion/toolchain and is not installed or represented as a standard-compliant service by this small exporter.

## Primary references

- https://dicomweb-client.readthedocs.io/en/latest/package.html
- https://docs.ohif.org/platform/extensions/modules/panel/
- https://docs.ohif.org/platform/modes/
- https://docs.ohif.org/configuration/dataSources/dicom-json/
- https://github.com/OHIF/Viewers/tree/v3.11.0
- https://docs.monai.io/en/stable/bundle.html
- https://pytorch.org/docs/stable/generated/torch.load.html
- https://docs.monai.io/projects/label/en/latest/apis.html
- https://github.com/Project-MONAI/MONAILabel/blob/0.8.5/monailabel/client/client.py
- https://github.com/RadicalImaging/Static-DICOMWeb
