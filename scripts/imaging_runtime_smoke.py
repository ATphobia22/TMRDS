"""Explicit localhost-only Orthanc/DICOMweb/OHIF transport check using generated data."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import time
import requests


def run() -> dict:
    import pydicom
    root = Path('data/imaging-demo')
    config = json.loads((root / 'orthanc.json').read_text())
    dicom = root / 'synthetic-mr.dcm'
    ds = pydicom.dcmread(dicom)
    if str(ds.PatientID) != 'synthetic-tmrds':
        raise ValueError('expected generated synthetic fixture')
    base = 'http://127.0.0.1:8042'
    with requests.Session() as session:
        session.trust_env = False
        session.auth = ('research', config['RegisteredUsers']['research'])
        deadline = time.monotonic() + 45
        while True:
            try:
                ready = session.get(base + '/system', timeout=3, allow_redirects=False)
                if ready.status_code == 200:
                    break
            except requests.RequestException:
                pass
            if time.monotonic() >= deadline:
                import subprocess
                logs = subprocess.run(['docker', 'compose', '-f', 'deploy/imaging/compose.yml', 'logs', '--no-color', '--tail', '80'], capture_output=True, text=True)
                password = config['RegisteredUsers']['research']
                print((logs.stdout + logs.stderr).replace(password, '[REDACTED]'))
                raise RuntimeError('Orthanc startup check failed')
            time.sleep(1)
        anonymous = session.get(base + '/system', auth=('', ''), timeout=5, allow_redirects=False)
        if anonymous.status_code != 401:
            raise RuntimeError('archive authentication check failed')
        upload = session.post(base + '/instances', data=dicom.read_bytes(), headers={'Content-Type':'application/dicom'}, timeout=15, allow_redirects=False)
        if upload.status_code != 200:
            raise RuntimeError('synthetic upload failed')
        qido = session.get(base + '/dicom-web/studies', params={'StudyInstanceUID':str(ds.StudyInstanceUID)}, timeout=15)
        qido.raise_for_status()
        records = qido.json()
        if not isinstance(records, list) or not any(r.get('0020000D', {}).get('Value') == [str(ds.StudyInstanceUID)] for r in records):
            raise RuntimeError('QIDO study identity mismatch')
        frame_url = f'{base}/dicom-web/studies/{ds.StudyInstanceUID}/series/{ds.SeriesInstanceUID}/instances/{ds.SOPInstanceUID}/frames/1'
        frame = session.get(frame_url, headers={'Accept':'multipart/related; type="application/octet-stream"'}, timeout=15)
        frame.raise_for_status()
        if len(frame.content) < len(ds.PixelData):
            raise RuntimeError('WADO frame incomplete')
        viewer = session.get(base + '/ohif/', timeout=15)
        viewer.raise_for_status()
        if 'text/html' not in viewer.headers.get('Content-Type', ''):
            raise RuntimeError('OHIF HTML unavailable')
    return {'synthetic_upload':True, 'authentication_enforced':True, 'qido_identity_verified':True,
            'wado_frame_retrieved':True, 'ohif_html_served':True, 'browser_render_verified':False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    if not args.live:
        parser.error('--live is required')
    print(json.dumps(run(), indent=2))
