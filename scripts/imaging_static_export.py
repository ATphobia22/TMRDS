"""Evaluate offline OHIF DICOM JSON exports using generated synthetic data only."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.imaging_synthetic_demo import generate


def export_synthetic(directory: Path, *, base_url="http://127.0.0.1:8080"):
    if base_url != "http://127.0.0.1:8080":
        raise ValueError("evaluation exports target the fixed offline loopback origin")
    generate(directory)  # refuses existing directories; accepts no arbitrary scans
    import pydicom
    path = directory / "synthetic-mr.dcm"
    ds = pydicom.dcmread(path)
    keys = ('StudyInstanceUID', 'SeriesInstanceUID', 'SOPInstanceUID', 'SOPClassUID',
            'Modality', 'Rows', 'Columns', 'BitsAllocated', 'BitsStored', 'HighBit',
            'PixelRepresentation', 'SamplesPerPixel', 'PhotometricInterpretation',
            'PixelSpacing', 'ImagePositionPatient', 'ImageOrientationPatient',
            'FrameOfReferenceUID', 'SliceThickness', 'InstanceNumber')
    # Convert pydicom numeric/string wrappers using the encoded DICOM JSON values.
    metadata = {}
    for key in keys:
        elem = ds.data_element(key)
        values = elem.to_json_dict(None, 1024)['Value']
        metadata[key] = values if elem.VM > 1 else values[0]
    document = {'studies': [{'StudyInstanceUID': str(ds.StudyInstanceUID),
        'PatientID': 'synthetic-tmrds', 'StudyDate': '20000101', 'NumInstances': 1, 'Modalities': 'MR',
        'series': [{'SeriesInstanceUID': str(ds.SeriesInstanceUID), 'SeriesNumber': 1, 'Modality': 'MR',
            'instances': [{'metadata': metadata, 'url': f'dicomweb:{base_url}/synthetic-mr.dcm'}]}]}]}
    evidence = {str(ds.SOPInstanceUID): {'study': str(ds.StudyInstanceUID), 'series': str(ds.SeriesInstanceUID),
        'instance': str(ds.SOPInstanceUID), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'source': 'TMRDS generated synthetic fixture', 'review': 'pending'}}
    (directory / 'ohif-dicom.json').write_text(json.dumps(document, indent=2))
    (directory / 'provenance.json').write_text(json.dumps(evidence, indent=2))
    # Archive password/configuration is never part of an offline shareable export.
    (directory / 'orthanc.json').unlink()
    manifest_path = directory / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['artifacts'].update({name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
        for name in ('ohif-dicom.json', 'provenance.json')})
    manifest['evaluation'] = {'format': 'OHIF DICOM JSON + Part 10', 'qido': False, 'stow': False,
        'browser_render_verified': False, 'viewer_assets_included': False,
        'offline_condition': 'self-host OHIF assets and codecs; block external network',
        'decision': 'synthetic pilot; retain archive for clinical access controls and querying'}
    manifest_path.write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('data/imaging-static'))
    args = parser.parse_args()
    print(json.dumps(export_synthetic(args.output)['evaluation'], indent=2))
