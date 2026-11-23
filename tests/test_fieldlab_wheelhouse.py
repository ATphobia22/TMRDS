"""Offline wheelhouse integrity and no-unsafe-rollback tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.fieldlab_wheelhouse import (
    WheelhouseError, build_receipt, verify_receipt, main,
)


def wheel(directory: Path, name: str, content: bytes = b"w" * 4096):
    directory.mkdir(exist_ok=True)
    path = directory / name
    path.write_bytes(content)
    return path


def test_real_sha256_manifest_and_local_verification(tmp_path):
    source = tmp_path / "wheelhouse"
    wheel(source, "pydicom-3.0.2-py3-none-any.whl")
    receipt = build_receipt(source, platform_tag="win_amd64", python_abi="cp311")
    assert receipt["wheel_count"] == 1
    assert receipt["clinical_approval_claim"] is False
    assert receipt["publisher_signature_verified"] is False
    assert len(receipt["wheels"]["pydicom-3.0.2-py3-none-any.whl"]["sha256"]) == 64
    assert verify_receipt(source, receipt) == 1
    (source / "pydicom-3.0.2-py3-none-any.whl").write_bytes(b"x" * 4096)
    with pytest.raises(WheelhouseError, match="SHA-256"):
        verify_receipt(source, receipt)


def test_reject_unlisted_redirects_and_empty_bundle(tmp_path):
    source = tmp_path / "wheelhouse"
    with pytest.raises(WheelhouseError):
        build_receipt(source, platform_tag="win_amd64", python_abi="cp311")
    path = wheel(source, "numpy-2.4.6-cp311-win_amd64.whl")
    receipt = build_receipt(source, platform_tag="win_amd64", python_abi="cp311")
    with pytest.raises(WheelhouseError):
        build_receipt(source, platform_tag="../../etc", python_abi="cp311")
    with pytest.raises(WheelhouseError):
        build_receipt(source, platform_tag="win_amd64", python_abi="py38")
    wheel(source, "extra-1.0-py3-none-any.whl")
    with pytest.raises(WheelhouseError, match="changed"):
        verify_receipt(source, receipt)
    (source / "extra-1.0-py3-none-any.whl").unlink()
    path.unlink()
    path.symlink_to(tmp_path / "other")
    with pytest.raises(WheelhouseError):
        verify_receipt(source, receipt)


def test_manifest_cli_refuses_overwriting_existing_receipt(tmp_path):
    source = tmp_path / "wheelhouse"
    wheel(source, "biopython-1.88-cp311-win_amd64.whl")
    manifest = tmp_path / "manifest.json"
    assert main(["create", str(source), "--manifest", str(manifest)]) == 0
    assert main(["verify", str(source), "--manifest", str(manifest)]) == 0
    assert main(["create", str(source), "--manifest", str(manifest)]) == 2
    receipt = json.loads(manifest.read_text())
    receipt["platform"] = "linux_x64"
    manifest.write_text(json.dumps(receipt))
    assert main(["verify", str(source), "--manifest", str(manifest)]) == 2
