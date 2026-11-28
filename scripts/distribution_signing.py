#!/usr/bin/env python3
"""Create and verify reproducible Ed25519-signed TMRDS distribution manifests.

The private signing key is supplied by an operator and must never enter the
repository, CI, the package directory, or a patient-data workflow. Verification
requires an independently pinned SHA-256 fingerprint for the trusted public key.
The inventory manifest is not a signature until the separate sign operation.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

MANIFEST_NAME = "DISTRIBUTION-MANIFEST.json"
SIGNATURE_NAME = "DISTRIBUTION-MANIFEST.sig.json"
MANIFEST_SCHEMA = "tmrds.distribution-manifest.v1"
SIGNATURE_SCHEMA = "tmrds.ed25519-signature.v1"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SOURCE_COMMIT = re.compile(r"[0-9a-f]{40}\Z")
_LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9.+_-]{0,63}\Z")
MAX_FILES = 10_000
MAX_FILE_BYTES = 2 * 1024 * 1024 * 1024
MAX_TOTAL_BYTES = 8 * 1024 * 1024 * 1024
MAX_MANIFEST_BYTES = 16 * 1024 * 1024
MAX_KEY_BYTES = 16 * 1024


class DistributionError(ValueError):
    """Raised when a package, manifest, key or signature is unsafe or invalid."""


def _safe_root(value: Path) -> Path:
    root = Path(value)
    if root.is_symlink() or not root.is_dir():
        raise DistributionError("package root must be an existing, non-symlink directory")
    try:
        return root.resolve(strict=True)
    except OSError as exc:
        raise DistributionError("package root cannot be resolved") from exc


def _safe_relative(value: Any) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value or ":" in value:
        raise DistributionError("manifest contains an unsafe relative path")
    if value.startswith("/") or PurePosixPath(value).is_absolute():
        raise DistributionError("manifest contains an absolute path")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise DistributionError("manifest contains a path traversal segment")
    if PurePosixPath(value).as_posix() != value:
        raise DistributionError("manifest path is not canonical")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_json(value: dict[str, Any]) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise DistributionError("manifest is not canonical JSON data") from exc


def _inventory(root: Path) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    total = 0
    paths = sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix())
    for path in paths:
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise DistributionError("package contains a symlink")
        if path.is_dir():
            continue
        if not path.is_file():
            raise DistributionError("package contains a non-regular filesystem entry")
        if relative in {MANIFEST_NAME, SIGNATURE_NAME}:
            continue
        _safe_relative(relative)
        size = path.stat(follow_symlinks=False).st_size
        if size < 0 or size > MAX_FILE_BYTES:
            raise DistributionError("package file exceeds the supported size limit")
        total += size
        if total > MAX_TOTAL_BYTES:
            raise DistributionError("package exceeds the supported total size limit")
        files.append({"path": relative, "size_bytes": size, "sha256": _sha256(path)})
        if len(files) > MAX_FILES:
            raise DistributionError("package contains too many files")
    if not files:
        raise DistributionError("package contains no regular files")
    return files


def _write_new(path: Path, payload: bytes, *, mode: int = 0o644) -> None:
    try:
        with path.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if os.name == "posix":
            path.chmod(mode)
    except FileExistsError as exc:
        raise DistributionError("output already exists; refusing to overwrite") from exc
    except OSError as exc:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        raise DistributionError("unable to write distribution metadata") from exc


def _load_json_file(path: Path, *, maximum: int = MAX_MANIFEST_BYTES) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise DistributionError("required metadata file is missing or unsafe")
    if path.stat(follow_symlinks=False).st_size > maximum:
        raise DistributionError("metadata file exceeds the supported size limit")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise DistributionError("metadata file is missing or invalid JSON") from None
    if not isinstance(value, dict):
        raise DistributionError("metadata root must be a JSON object")
    return value


def _validate_manifest_shape(manifest: dict[str, Any]) -> None:
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise DistributionError("unsupported distribution manifest schema")
    package = manifest.get("package")
    if not isinstance(package, dict) or not all(
        isinstance(package.get(field), str) and _LABEL.fullmatch(package[field])
        for field in ("name", "version", "target")
    ):
        raise DistributionError("manifest package metadata is invalid")
    commit = manifest.get("source_commit")
    if commit is not None and (not isinstance(commit, str) or not _SOURCE_COMMIT.fullmatch(commit)):
        raise DistributionError("manifest source commit must be a full lowercase Git SHA")
    claims = manifest.get("claims")
    if not isinstance(claims, dict) or claims.get("research_only") is not True:
        raise DistributionError("manifest must retain the research-only claim")
    if claims.get("clinical_validation_completed") is not False:
        raise DistributionError("manifest cannot claim clinical validation")


def create_manifest(
    root: Path,
    package_name: str,
    version: str,
    target: str,
    source_commit: str | None = None,
) -> dict[str, Any]:
    """Create a deterministic inventory manifest inside a package directory."""
    package_root = _safe_root(root)
    if not all(isinstance(value, str) and _LABEL.fullmatch(value)
               for value in (package_name, version, target)):
        raise DistributionError("package name, version and target must be safe labels")
    if source_commit is not None and (
        not isinstance(source_commit, str) or not _SOURCE_COMMIT.fullmatch(source_commit)
    ):
        raise DistributionError("source commit must be a full lowercase Git SHA")
    manifest_path = package_root / MANIFEST_NAME
    signature_path = package_root / SIGNATURE_NAME
    if manifest_path.exists() or manifest_path.is_symlink() or signature_path.exists() or signature_path.is_symlink():
        raise DistributionError("distribution metadata already exists; refusing to replace it")
    files = _inventory(package_root)
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "package": {"name": package_name, "version": version, "target": target},
        "source_commit": source_commit,
        "files": files,
        "file_count": len(files),
        "total_size_bytes": sum(row["size_bytes"] for row in files),
        "claims": {
            "research_only": True,
            "clinical_validation_completed": False,
            "clinical_efficacy_claimed": False,
            "quantum_advantage_claimed": False,
        },
    }
    payload = json.dumps(
        manifest, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False
    ).encode("utf-8") + b"\n"
    _write_new(manifest_path, payload)
    return manifest


def verify_manifest(root: Path) -> dict[str, Any]:
    """Verify every package file against its unsigned inventory manifest."""
    package_root = _safe_root(root)
    manifest = _load_json_file(package_root / MANIFEST_NAME)
    _validate_manifest_shape(manifest)
    rows = manifest.get("files")
    if not isinstance(rows, list) or not rows or len(rows) > MAX_FILES:
        raise DistributionError("manifest file inventory is empty or oversized")
    expected: dict[str, tuple[int, str]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise DistributionError("manifest file record is invalid")
        relative = _safe_relative(row.get("path"))
        size = row.get("size_bytes")
        digest = row.get("sha256")
        if type(size) is not int or size < 0 or not isinstance(digest, str) or not _SHA256.fullmatch(digest):
            raise DistributionError("manifest file record has invalid size or SHA-256")
        if relative in expected:
            raise DistributionError("manifest contains duplicate file paths")
        expected[relative] = (size, digest)
    if type(manifest.get("file_count")) is not int or manifest["file_count"] != len(expected):
        raise DistributionError("manifest file count does not match its inventory")
    if type(manifest.get("total_size_bytes")) is not int or manifest["total_size_bytes"] != sum(
        size for size, _ in expected.values()
    ):
        raise DistributionError("manifest total size does not match its inventory")

    actual_rows = _inventory(package_root)
    actual = {row["path"]: row for row in actual_rows}
    if set(actual) != set(expected):
        raise DistributionError("package inventory differs from the manifest")
    for relative, (size, digest) in expected.items():
        record = actual[relative]
        if record["size_bytes"] != size or not hmac.compare_digest(record["sha256"], digest):
            raise DistributionError("package file size or hash mismatch")
    return {
        "status": "inventory_verified_not_signed",
        "file_count": len(actual_rows),
        "total_size_bytes": sum(row["size_bytes"] for row in actual_rows),
        "clinical_validation_completed": False,
    }


def _read_key(path: Path, *, private: bool) -> bytes:
    key_path = Path(path)
    if key_path.is_symlink() or not key_path.is_file():
        raise DistributionError("key file is missing or unsafe")
    info = key_path.stat(follow_symlinks=False)
    if info.st_size <= 0 or info.st_size > MAX_KEY_BYTES:
        raise DistributionError("key file has an invalid size")
    if private and os.name == "posix" and stat.S_IMODE(info.st_mode) & 0o077:
        raise DistributionError("private key file permissions must be owner-only (0600)")
    try:
        return key_path.read_bytes()
    except OSError as exc:
        raise DistributionError("key file cannot be read") from exc


def _load_private_key(path: Path, package_root: Path) -> Ed25519PrivateKey:
    key_path = Path(path)
    try:
        resolved = key_path.resolve(strict=True)
        resolved.relative_to(package_root)
    except ValueError:
        pass
    except OSError as exc:
        raise DistributionError("private key file is missing") from exc
    else:
        raise DistributionError("private signing key must remain outside the package directory")
    try:
        key = serialization.load_pem_private_key(_read_key(key_path, private=True), password=None)
    except (TypeError, ValueError):
        raise DistributionError("private key must be an unencrypted PEM Ed25519 key") from None
    if not isinstance(key, Ed25519PrivateKey):
        raise DistributionError("only Ed25519 private keys are supported")
    return key


def _load_public_key(path: Path) -> Ed25519PublicKey:
    try:
        key = serialization.load_pem_public_key(_read_key(path, private=False))
    except (TypeError, ValueError):
        raise DistributionError("public key must be a valid PEM Ed25519 key") from None
    if not isinstance(key, Ed25519PublicKey):
        raise DistributionError("only Ed25519 public keys are supported")
    return key


def _public_fingerprint(key: Ed25519PublicKey) -> str:
    raw = key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return hashlib.sha256(raw).hexdigest()


def sign_manifest(root: Path, private_key_path: Path) -> dict[str, str]:
    """Sign a verified manifest; never generate, store or export a private key."""
    package_root = _safe_root(root)
    verify_manifest(package_root)
    private_key = _load_private_key(Path(private_key_path), package_root)
    manifest = _load_json_file(package_root / MANIFEST_NAME)
    message = _canonical_json(manifest)
    public_fingerprint = _public_fingerprint(private_key.public_key())
    envelope = {
        "schema": SIGNATURE_SCHEMA,
        "algorithm": "Ed25519",
        "manifest_sha256": hashlib.sha256(message).hexdigest(),
        "public_key_sha256": public_fingerprint,
        "signature_base64": base64.b64encode(private_key.sign(message)).decode("ascii"),
    }
    payload = json.dumps(
        envelope, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False
    ).encode("ascii") + b"\n"
    _write_new(package_root / SIGNATURE_NAME, payload)
    return {
        "status": "signed",
        "algorithm": "Ed25519",
        "public_key_sha256": public_fingerprint,
        "manifest_sha256": envelope["manifest_sha256"],
    }


def verify_distribution(
    root: Path,
    public_key_path: Path,
    expected_public_key_sha256: str,
) -> dict[str, Any]:
    """Verify package inventory and signature against an out-of-band key pin."""
    package_root = _safe_root(root)
    inventory = verify_manifest(package_root)
    if not isinstance(expected_public_key_sha256, str) or not _SHA256.fullmatch(
        expected_public_key_sha256.casefold()
    ):
        raise DistributionError("a 64-character trusted public-key SHA-256 fingerprint is required")
    public_key = _load_public_key(Path(public_key_path))
    fingerprint = _public_fingerprint(public_key)
    if not hmac.compare_digest(fingerprint, expected_public_key_sha256.casefold()):
        raise DistributionError("trusted public-key fingerprint mismatch")
    envelope = _load_json_file(package_root / SIGNATURE_NAME, maximum=MAX_KEY_BYTES)
    if envelope.get("schema") != SIGNATURE_SCHEMA or envelope.get("algorithm") != "Ed25519":
        raise DistributionError("unsupported distribution signature envelope")
    manifest = _load_json_file(package_root / MANIFEST_NAME)
    message = _canonical_json(manifest)
    manifest_digest = hashlib.sha256(message).hexdigest()
    if not isinstance(envelope.get("manifest_sha256"), str) or not hmac.compare_digest(
        envelope["manifest_sha256"], manifest_digest
    ):
        raise DistributionError("signature manifest digest mismatch")
    if not isinstance(envelope.get("public_key_sha256"), str) or not hmac.compare_digest(
        envelope["public_key_sha256"], fingerprint
    ):
        raise DistributionError("signature public-key fingerprint mismatch")
    encoded = envelope.get("signature_base64")
    if not isinstance(encoded, str):
        raise DistributionError("signature value is missing")
    try:
        signature = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError):
        raise DistributionError("signature value is not valid base64") from None
    if len(signature) != 64:
        raise DistributionError("Ed25519 signature must contain exactly 64 bytes")
    try:
        public_key.verify(signature, message)
    except InvalidSignature:
        raise DistributionError("Ed25519 signature verification failed") from None
    return {
        "status": "signature_verified",
        "algorithm": "Ed25519",
        "public_key_sha256": fingerprint,
        "file_count": inventory["file_count"],
        "total_size_bytes": inventory["total_size_bytes"],
        "research_only": True,
        "clinical_validation_completed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)

    create = commands.add_parser("manifest", help="create an unsigned deterministic package inventory")
    create.add_argument("root", type=Path)
    create.add_argument("--package-name", required=True)
    create.add_argument("--version", required=True)
    create.add_argument("--target", required=True)
    create.add_argument("--source-commit")

    check = commands.add_parser("verify-manifest", help="verify package hashes without claiming a signature")
    check.add_argument("root", type=Path)

    sign = commands.add_parser("sign", help="sign an existing manifest with an operator-managed key")
    sign.add_argument("root", type=Path)
    sign.add_argument("--private-key", required=True, type=Path)

    verify = commands.add_parser("verify", help="verify inventory and Ed25519 signature against a pinned key")
    verify.add_argument("root", type=Path)
    verify.add_argument("--public-key", required=True, type=Path)
    verify.add_argument("--expected-public-key-sha256", required=True)

    args = parser.parse_args(argv)
    try:
        if args.action == "manifest":
            result = create_manifest(
                args.root, args.package_name, args.version, args.target, args.source_commit
            )
            output: dict[str, Any] = {
                "status": "manifest_created_not_signed",
                "package": result["package"],
                "file_count": result["file_count"],
                "total_size_bytes": result["total_size_bytes"],
            }
        elif args.action == "verify-manifest":
            output = verify_manifest(args.root)
        elif args.action == "sign":
            output = sign_manifest(args.root, args.private_key)
        else:
            output = verify_distribution(
                args.root, args.public_key, args.expected_public_key_sha256
            )
        print(json.dumps(output, sort_keys=True, indent=2))
        return 0
    except (DistributionError, OSError, ValueError) as exc:
        print(f"Distribution operation refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
