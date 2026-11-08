import hashlib
import json
from pathlib import Path

import pytest

pydicom = pytest.importorskip("pydicom", reason="optional imaging tools not installed")
from scripts.imaging_synthetic_demo import generate


def test_fixture_bundle_and_checksums(tmp_path):
    folder = tmp_path / "demo"
    manifest = generate(folder)
    ds = pydicom.dcmread(folder / "synthetic-mr.dcm")
    assert ds.PatientID == "synthetic-tmrds"
    assert ds.Rows == ds.Columns == 16
    assert len(ds.PixelData) == 512
    bundle = json.loads((folder / "research-bundle.json").read_text())
    study = bundle["entry"][1]["resource"]
    assert study["subject"]["reference"] == "Patient/synthetic-patient"
    assert study["series"][0]["uid"] == ds.SeriesInstanceUID
    assert study["series"][0]["instance"][0]["uid"] == ds.SOPInstanceUID
    assert "PatientName" not in json.dumps(bundle)
    for name, expected in manifest["artifacts"].items():
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == expected
    assert manifest["hash_is_signature"] is False
    config = json.loads((folder / "orthanc.json").read_text())
    assert config["AuthenticationEnabled"] and not config["DicomServerEnabled"]
    assert len(config["RegisteredUsers"]["research"]) >= 32
    assert (folder / "orthanc.json").stat().st_mode & 0o077 == 0
    with pytest.raises(FileExistsError):
        generate(folder)
