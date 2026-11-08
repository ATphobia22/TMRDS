"""Generate a synthetic MR fixture, FHIR R4 research bundle and local Orthanc config.

No input scan is accepted. This is not a de-identification tool or validator.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets


def generate(directory: Path) -> dict:
    # Optional dependency: core API does not import this tool.
    import pydicom
    from pydicom.dataset import FileDataset, FileMetaDataset
    from pydicom.uid import ExplicitVRLittleEndian, MRImageStorage, generate_uid

    directory.mkdir(parents=True, exist_ok=False)
    directory.chmod(0o700)
    study, series, instance = generate_uid(), generate_uid(), generate_uid()
    meta = FileMetaDataset()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    meta.MediaStorageSOPClassUID = MRImageStorage
    meta.MediaStorageSOPInstanceUID = instance
    ds = FileDataset(None, {}, file_meta=meta, preamble=b"\0" * 128)
    ds.SOPClassUID, ds.SOPInstanceUID = MRImageStorage, instance
    ds.StudyInstanceUID, ds.SeriesInstanceUID = study, series
    ds.PatientID, ds.PatientName = "synthetic-tmrds", "SYNTHETIC^TMRDS"
    ds.PatientBirthDate, ds.PatientSex = "", ""
    ds.StudyDate, ds.StudyTime = "20000101", "120000"
    ds.AccessionNumber, ds.ReferringPhysicianName = "", ""
    ds.StudyID, ds.SeriesNumber, ds.InstanceNumber = "1", 1, 1
    ds.Modality = "MR"
    ds.Rows, ds.Columns = 16, 16
    ds.SamplesPerPixel, ds.PhotometricInterpretation = 1, "MONOCHROME2"
    ds.BitsAllocated, ds.BitsStored, ds.HighBit, ds.PixelRepresentation = 16, 12, 11, 0
    ds.PixelSpacing, ds.SliceThickness = [1, 1], 1
    ds.ImagePositionPatient, ds.ImageOrientationPatient = [0, 0, 0], [1, 0, 0, 0, 1, 0]
    ds.FrameOfReferenceUID = generate_uid()
    ds.PixelData = b"".join((i * 8).to_bytes(2, "little") for i in range(256))
    path = directory / "synthetic-mr.dcm"
    ds.save_as(path, enforce_file_format=True)
    parsed = pydicom.dcmread(path)
    # Explicit mapping from a fixture created here, never copying arbitrary tags.
    imaging = {
        "resourceType": "ImagingStudy", "id": "synthetic-imaging",
        "meta": {"tag": [{"system": "urn:tmrds:data-classification", "code": "synthetic"}]},
        "status": "available", "subject": {"reference": "Patient/synthetic-patient"},
        "identifier": [{"system": "urn:dicom:uid", "value": f"urn:oid:{parsed.StudyInstanceUID}"}],
        "numberOfSeries": 1, "numberOfInstances": 1,
        "series": [{"uid": str(parsed.SeriesInstanceUID), "number": 1,
                    "modality": {"system": "http://dicom.nema.org/resources/ontology/DCM", "code": str(parsed.Modality)},
                    "numberOfInstances": 1, "instance": [{"uid": str(parsed.SOPInstanceUID),
                    "sopClass": {"system": "urn:ietf:rfc:3986", "code": f"urn:oid:{parsed.SOPClassUID}"}}]}],
    }
    bundle = {"resourceType": "Bundle", "type": "collection", "entry": [
        {"fullUrl": "https://synthetic.invalid/Patient/synthetic-patient", "resource": {"resourceType": "Patient", "id": "synthetic-patient", "meta": imaging["meta"]}},
        {"fullUrl": "https://synthetic.invalid/ImagingStudy/synthetic-imaging", "resource": imaging},
    ]}
    bundle_path = directory / "research-bundle.json"
    bundle_path.write_text(json.dumps(bundle, indent=2) + "\n")
    manifest = {"schema_version": "1.0", "created_at": datetime.now(timezone.utc).isoformat(),
                "data_classification": "synthetic", "fhir_validation": "not_profile_validated",
                "clinical_promotion_allowed": False, "hash_is_signature": False,
                "artifacts": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (path, bundle_path)}}
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    config = {"Name": "TMRDS synthetic research only", "RemoteAccessAllowed": True,
              "AuthenticationEnabled": True, "RegisteredUsers": {"research": secrets.token_urlsafe(32)},
              "DicomServerEnabled": False, "DicomWeb": {"Enable": True},
              "OHIF": {"Enable": True, "DataSource": "dicom-web"}}
    config_path = directory / "orthanc.json"
    config_path.touch(mode=0o600)
    config_path.write_text(json.dumps(config, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/imaging-demo"))
    args = parser.parse_args()
    generate(args.output)
    print(f"Created synthetic fixture and local configuration in {args.output}")
