#!/usr/bin/env python3
"""Build and verify a local, SHA-256 sealed wheelhouse. Hashes are not signatures.

'prepare' is ONLINE BUILD-TIME ONLY. 'verify' is OFFLINE and does no requests.
No patient files are accepted. Install packages with pip --no-index afterwards.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import platform
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / "deploy" / "offline" / "requirements.txt"
MANIFEST = "wheelhouse-manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def prepare(directory: Path) -> dict:
    """Build-only network fetch into a NEW empty directory; never auto-update."""
    if directory.exists() and any(directory.iterdir()):
        raise ValueError("Wheelhouse must be new/empty to prevent unsigned dependencies")
    directory.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        sys.executable, "-m", "pip", "--isolated", "download",
        "--index-url", "https://pypi.org/simple", "--only-binary=:all:",
        "--dest", str(directory), "-r", str(REQUIREMENTS),
    ], check=True)
    return seal(directory)


def seal(directory: Path) -> dict:
    """Receipt for explicit approved runner output, not independent authenticity."""
    if (directory / MANIFEST).exists():
        raise ValueError("Existing manifest cannot be silently replaced")
    wheels = sorted(directory.iterdir())
    if not wheels or any(not p.is_file() or p.is_symlink() or p.suffix != ".whl" for p in wheels):
        raise ValueError("Wheelhouse contains no wheels or unexpected files")
    manifest = {
        "schema_version": "1.0", "scope": "pinned_optional_offline_python_readers",
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        "platform": sys.platform, "machine": platform.machine(),
        "requirements_sha256": sha256(REQUIREMENTS),
        "wheels": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha256(p)}
                   for p in wheels],
        "manifest_is_signature": False, "requires_trusted_artifact_delivery": True,
        "all_dependency_licenses_independently_reviewed": False,
        "clinical_validation_completed": False,
        "network_runtime": "not_required",
    }
    (directory / MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def verify(directory: Path) -> dict:
    """Offline SHA validation before a local pip --no-index install."""
    try:
        data = json.loads((directory / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ValueError("Missing or invalid wheelhouse manifest") from None
    if data.get("schema_version") != "1.0" or data.get("requirements_sha256") != sha256(REQUIREMENTS):
        raise ValueError("Pinned requirements do not match the manifest")
    if data.get("python") != f"{sys.version_info.major}.{sys.version_info.minor}" or (
        data.get("platform") != sys.platform or data.get("machine") != platform.machine()
    ):
        raise ValueError("Wheelhouse built for a different Python or operating system")
    entries = data.get("wheels")
    if not isinstance(entries, list) or not entries:
        raise ValueError("No audited wheel entries")
    expected = {x.get("name") for x in entries if isinstance(x, dict)}
    actual = {x.name for x in directory.iterdir() if x.name != MANIFEST}
    if len(expected) != len(entries) or expected != actual:
        raise ValueError("Wheelhouse file inventory mismatch")
    for row in entries:
        filename = row["name"]
        if not isinstance(filename, str) or Path(filename).name != filename or not filename.endswith(".whl"):
            raise ValueError("Wheelhouse name invalid")
        wheel = directory / filename
        if not wheel.is_file() or wheel.is_symlink() or wheel.stat().st_size != row["bytes"]:
            raise ValueError("Wheel missing, unsafe or size mismatch")
        if not isinstance(row.get("sha256"), str) or sha256(wheel) != row["sha256"]:
            raise ValueError("Wheel integrity mismatch")
    return {"status": "sha256_inventory_verified_not_signed",
            "wheel_count": len(entries), "platform": sys.platform,
            "clinical_validation_completed": False,
            "license_review_completed": False}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "seal", "verify"))
    parser.add_argument("wheelhouse", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.action == "prepare":
            result = prepare(args.wheelhouse)
        elif args.action == "seal":
            result = seal(args.wheelhouse)
        else:
            result = verify(args.wheelhouse)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print("Wheelhouse operation refused: " + type(exc).__name__, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
