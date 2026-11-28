"""Synthetic tests for reproducible, pinned Ed25519 distribution verification."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key

from scripts.distribution_signing import (
    DistributionError,
    create_manifest,
    sign_manifest,
    verify_distribution,
    verify_manifest,
)


def _package(tmp_path: Path) -> Path:
    root = tmp_path / "offline-release"
    (root / "scripts").mkdir(parents=True)
    (root / "README.md").write_text("Synthetic research-only package\n", encoding="utf-8")
    (root / "scripts" / "runner.py").write_text("print('synthetic')\n", encoding="utf-8")
    return root


def _keypair(tmp_path: Path, *, ed25519: bool = True):
    tmp_path.mkdir(parents=True, exist_ok=True)
    private = Ed25519PrivateKey.generate() if ed25519 else generate_private_key(
        public_exponent=65537, key_size=2048
    )
    private_path = tmp_path / "release-private.pem"
    private_path.write_bytes(private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ))
    if os.name == "posix":
        private_path.chmod(0o600)
    public = private.public_key()
    public_path = tmp_path / "release-public.pem"
    public_path.write_bytes(public.public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ))
    if ed25519:
        raw = public.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        fingerprint = hashlib.sha256(raw).hexdigest()
    else:
        fingerprint = ""
    return private_path, public_path, fingerprint


def _create(root: Path):
    return create_manifest(
        root,
        package_name="TMRDS-QRCE-Offline-Workstation",
        version="research-preview",
        target="win-x64",
        source_commit="47739aa5f66c78b5f8a857aa365bebcf6c29bcad",
    )


def test_manifest_is_deterministic_and_inventory_only(tmp_path: Path):
    first = _package(tmp_path / "one")
    second = _package(tmp_path / "two")
    first_manifest = create_manifest(first, "TMRDS-QRCE", "research-preview", "win-x64")
    second_manifest = create_manifest(second, "TMRDS-QRCE", "research-preview", "win-x64")
    assert first_manifest == second_manifest
    assert "patient" not in json.dumps(first_manifest).casefold()
    assert first_manifest["claims"]["research_only"] is True
    assert first_manifest["claims"]["clinical_validation_completed"] is False
    assert verify_manifest(first)["status"] == "inventory_verified_not_signed"


def test_inventory_rejects_modified_missing_and_unlisted_files(tmp_path: Path):
    root = _package(tmp_path)
    _create(root)
    (root / "README.md").write_text("modified\n", encoding="utf-8")
    with pytest.raises(DistributionError, match="hash|size|inventory"):
        verify_manifest(root)
    (root / "README.md").write_text("Synthetic research-only package\n", encoding="utf-8")
    (root / "unlisted.bin").write_bytes(b"unexpected")
    with pytest.raises(DistributionError, match="inventory"):
        verify_manifest(root)


def test_ed25519_signature_verifies_only_with_pinned_trusted_key(tmp_path: Path):
    root = _package(tmp_path)
    _create(root)
    private_path, public_path, fingerprint = _keypair(tmp_path)
    signed = sign_manifest(root, private_path)
    assert signed["algorithm"] == "Ed25519"
    assert signed["public_key_sha256"] == fingerprint
    verified = verify_distribution(root, public_path, fingerprint)
    assert verified["status"] == "signature_verified"
    assert verified["clinical_validation_completed"] is False
    with pytest.raises(DistributionError, match="fingerprint"):
        verify_distribution(root, public_path, "0" * 64)


def test_manifest_tampering_invalidates_signature(tmp_path: Path):
    root = _package(tmp_path)
    _create(root)
    private_path, public_path, fingerprint = _keypair(tmp_path)
    sign_manifest(root, private_path)
    path = root / "DISTRIBUTION-MANIFEST.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["package"]["version"] = "tampered"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(DistributionError, match="signature|manifest"):
        verify_distribution(root, public_path, fingerprint)


def test_signing_refuses_private_key_inside_package_and_weak_posix_permissions(tmp_path: Path):
    root = _package(tmp_path)
    _create(root)
    inside = root / "private.pem"
    inside.write_text("not a key", encoding="utf-8")
    with pytest.raises(DistributionError, match="outside"):
        sign_manifest(root, inside)

    private_path, _, _ = _keypair(tmp_path / "keys")
    if os.name == "posix":
        private_path.chmod(0o644)
        with pytest.raises(DistributionError, match="permissions"):
            sign_manifest(root, private_path)


def test_signing_rejects_non_ed25519_keys_and_refuses_overwrite(tmp_path: Path):
    root = _package(tmp_path)
    _create(root)
    rsa_path, _, _ = _keypair(tmp_path / "rsa", ed25519=False)
    with pytest.raises(DistributionError, match="Ed25519"):
        sign_manifest(root, rsa_path)

    private_path, _, _ = _keypair(tmp_path / "ed")
    sign_manifest(root, private_path)
    with pytest.raises(DistributionError, match="already exists"):
        sign_manifest(root, private_path)


def test_symlinks_and_path_traversal_are_rejected(tmp_path: Path):
    root = _package(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    link = root / "escape.txt"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("Symlinks unavailable on this platform")
    with pytest.raises(DistributionError, match="symlink"):
        create_manifest(root, "TMRDS-QRCE", "research-preview", "win-x64")

    link.unlink()
    _create(root)
    manifest_path = root / "DISTRIBUTION-MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][0]["path"] = "../outside.txt"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(DistributionError, match="path"):
        verify_manifest(root)
