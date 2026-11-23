"""Checksum/manifest integrity regression tests, including deliberate tampering."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.qrce_wheelhouse import MANIFEST, prepare, seal, verify


def test_wheelhouse_hashes_are_offline_and_mismatch_rejected(tmp_path: Path):
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    wheel = wheelhouse / "fixture-1.0.0-py3-none-any.whl"
    wheel.write_bytes(b"not-an-executable-fixture")
    manifest = seal(wheelhouse)
    assert manifest["manifest_is_signature"] is False
    assert manifest["all_dependency_licenses_independently_reviewed"] is False
    assert verify(wheelhouse)["wheel_count"] == 1
    wheel.write_bytes(b"tampered-with-new-binary")
    with pytest.raises(ValueError, match="mismatch"):
        verify(wheelhouse)


def test_wheelhouse_refuses_extra_file_tampered_manifest_and_reseal(tmp_path: Path):
    d = tmp_path / "wheels"
    d.mkdir()
    (d / "fixture-1.0.0-py3-none-any.whl").write_bytes(b"fixture")
    seal(d)
    with pytest.raises(ValueError, match="Existing manifest"):
        seal(d)
    (d / "untracked.whl").write_bytes(b"unreviewed")
    with pytest.raises(ValueError, match="inventory"):
        verify(d)
    (d / "untracked.whl").unlink()
    payload = json.loads((d / MANIFEST).read_text())
    payload["requirements_sha256"] = "0" * 64
    (d / MANIFEST).write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="requirements"):
        verify(d)


def test_prepare_cannot_overwrite_an_existing_bundle(tmp_path: Path):
    d = tmp_path / "wheelhouse"
    d.mkdir()
    (d / "some.file").write_bytes(b"old")
    with pytest.raises(ValueError, match="new/empty"):
        prepare(d)
