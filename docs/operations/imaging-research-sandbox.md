# Local imaging research sandbox

Implemented here: synthetic MR fixture generation with pydicom, an explicit
FHIR R4 Patient/ImagingStudy mapping, SHA-256 artifact manifest, and a digest-pinned
Orthanc + official OHIF-plugin Compose recipe. No input scan is accepted by the
fixture generator. No hospital, scanner, PACS, cloud account or patient is connected.

## Run locally

From the repository root, on a host with Python and Docker Compose:

```bash
python -m pip install -r deploy/imaging/requirements.txt
python scripts/imaging_synthetic_demo.py
python -m pytest -q tests/test_imaging_synthetic_demo.py
docker compose -f deploy/imaging/compose.yml config --quiet
docker compose -f deploy/imaging/compose.yml up -d
```

The generator creates `data/imaging-demo` only if it does not already exist, and
protects its local credential file with mode 0600. The randomly generated password
for username `research` is in `data/imaging-demo/orthanc.json`; keep it private.
The runtime directory is ignored by git. Visit `http://127.0.0.1:8042/` and sign
in. Upload **only** the generated `synthetic-mr.dcm` using Orthanc Explorer, then
use its OHIF button. The HTTP upload API is `POST /instances`; DICOMweb is under
`/dicom-web/`. The fixture is a tiny single-slice gradient, not an anatomical scan
or a test of multi-slice MPR performance. The recipe uses OHIF's DICOMweb data
source to avoid JSON-source preloading requirements.

```bash
docker compose -f deploy/imaging/compose.yml down
```

`down` retains the named archive volume. Do not delete or reuse an existing archive
volume without inspecting its contents. This sandbox must never receive real
patient data. It is loopback-only, uses an internal container network, requires
HTTP authentication and disables the DIMSE listener. It does not configure TLS,
DICOM TLS, SSO, institutional authorization or production access control.

## Project decisions from official sources

| Project | Decision | Reason / boundary |
| --- | --- | --- |
| [Orthanc + OHIF plugin](https://orthanc.uclouvain.be/book/plugins/ohif.html) | Compose recipe | Official plugin packages OHIF and can use DICOMweb without a separate reverse proxy |
| [pydicom](https://pydicom.github.io/pydicom/stable/auto_examples/metadata_processing/plot_anonymize.html) | Optional dependency installed and fixture tested | Its anonymization example is explicitly a starting point; not certified de-identification |
| [HAPI FHIR](https://github.com/hapifhir/hapi-fhir) | Next validation target | Apache-2.0; a server/framework does not automatically establish profile or terminology conformance |
| [Cornerstone3D](https://cornerstonejs.org/) | Prefer via OHIF initially | Defer custom React Three Fiber volume rendering until the native DICOMweb path is validated |
| [dcm4chee Archive 5](https://github.com/dcm4che/dcm4chee-arc-light/) | Later enterprise archive candidate | README identifies MPL 1.1; inspect component licenses and institutional integration requirements |
| [BlueHalo FHIR](https://github.com/bluehalo/node-fhir-server-core) | Alternative, not installed | Former Asymmetrik project; verify version-specific support before adding a second FHIR server |
| [AMI](https://github.com/FNNDSC/ami) | Evaluate only if custom Three.js rendering is needed | Do not assume compatibility with current Three.js or deployment readiness from a feature list |
| [AWS HealthImaging](https://docs.aws.amazon.com/healthimaging/latest/devguide/reference-dicom.html) | Optional later cloud archive | AWS docs require supported SOP/transfer syntax and metadata constraints; no cloud resource created |

The full Orthanc image tag `26.11.0-full` was resolved from the Docker Hub API on
November 7, 2026, to the digest committed in the recipe. Pinning is reproducibility,
not an image vulnerability assessment or endorsement of every bundled plugin.
Review the core, plugin and container dependency licenses before redistribution.

## Corrections to the proposed architecture

- Tag replacement alone cannot guarantee removal of identifying pixels, private
  fields, structured reports, dates, overlays or identifying facial anatomy.
  A real ingestion service needs a validated DICOM confidentiality profile,
  pixel/sequence review and documented institutional controls.
- SHA-256 is a checksum. A manifest provides change detection when retained
  securely; it is not a digital signature, immutable ledger or proof of origin.
- The generated FHIR resource is a research mapping with synthetic subject
  reference and DICOM UIDs. Full R4/profile/terminology validation is pending;
  no US Core or federal compliance claim follows from serializing JSON.
- Keep diagnostic voxel values, spatial orientation, spacing and modality
  semantics. H.265 video or derived surface meshes must not silently replace
  source DICOM data used for measurements. Derived meshes need explicit
  algorithm/version, LPS/RAS coordinates, millimeter units and source references.
- No verified GE SIGNA Sprint Elite scanner connection or model-specific DICOM
  compatibility was established. Validate the actual scanner conformance statement.

## Verification scope

The fixture round-trip, UID mapping, synthetic subject reference, checksums,
credential-file permissions and overwrite refusal are covered by an optional test.
The core API never imports pydicom. A separate imaging CI job installs and runs
that test so core CI cannot silently skip this optional capability.

Docker is unavailable in the authoring environment: the Compose YAML and security
settings were checked statically, but container startup, QIDO/WADO, OHIF rendering,
mobile memory, MPR, segmentation and GPU performance remain unverified. These
are explicit next gates before claiming a functioning imaging viewer deployment.

### Internal-network port correction

Runtime testing found that publishing a port from an exclusively internal Docker
network did not make the running archive reachable. The recipe now publishes
`127.0.0.1:8042` from a digest-pinned nginx proxy attached to the internal archive
network and a frontend bridge. Orthanc remains internal-only; its HTTP
 authentication remains required and DIMSE remains disabled. The proxy enforces a
10 MiB request limit for this small synthetic sandbox. See
https://github.com/moby/moby/discussions/53256 and
https://docs.docker.com/engine/network/port-publishing/ .
