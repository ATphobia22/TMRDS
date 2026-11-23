"""Record and verify every offline FieldLab wheel SHA-256.

This protects downloaded bits against accidental corruption after bundle build.
It is not a publisher signature; compare the manifest/ZIP to the trusted
GitHub Actions artifact and independently audit package versions and licenses.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

MAX_WHEELS = 60
MAX_WHEEL_BYTES = 256 * 1024 * 1024
WHEEL_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.+-]{1,200}\.whl$")


class WheelhouseError(ValueError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _wheels(directory: Path) -> list[Path]:
    if not directory.is_dir() or directory.is_symlink():
        raise WheelhouseError("Wheelhouse folder not found or redirected")
    names = sorted(directory.iterdir())
    if not names or len(names) > MAX_WHEELS:
        raise WheelhouseError("Unexpected wheel count")
    for path in names:
        if (not path.is_file() or path.is_symlink()
                or not WHEEL_NAME.fullmatch(path.name)
                or path.stat().st_size < 200 or path.stat().st_size > MAX_WHEEL_BYTES):
            raise WheelhouseError("Wheelhouse contains an unsupported file")
    return names


def build_receipt(directory: Path, *, platform_tag: str, python_abi: str) -> dict:
    if not (re.fullmatch(r"[A-Za-z0-9_-]{2,40}", platform_tag)
            and re.fullmatch(r"cp3[0-9]{2}", python_abi)):
        raise WheelhouseError("Unsupported platform/ABI")
    wheels = _wheels(directory)
    records = {
        path.name: {"sha256": _sha256(path), "bytes": path.stat().st_size}
        for path in wheels
    }
    return {
        "schema_version": "1.0",
        "platform": platform_tag,
        "python_abi": python_abi,
        "purpose": "TMRDS FieldLab offline Python research adapters",
        "replay_target": "no-index local wheel installation",
        "clinical_approval_claim": False,
        "publisher_signature_verified": False,
        "package_license_reviews_complete": False,
        "wheel_count": len(wheels),
        "wheels": records,
    }


def verify_receipt(directory: Path, data: dict) -> int:
    if not isinstance(data, dict) or data.get("schema_version") != "1.0":
        raise WheelhouseError("Invalid wheelhouse manifest schema")
    candidates = _wheels(directory)
    expected = data.get("wheels")
    if not isinstance(expected, dict) or set(expected) != {path.name for path in candidates}:
        raise WheelhouseError("Wheelhouse files changed or manifest incomplete")
    for file in candidates:
        entry = expected[file.name]
        if (not isinstance(entry, dict) or entry.get("bytes") != file.stat().st_size
                or not isinstance(entry.get("sha256"), str)
                or not re.fullmatch(r"[a-f0-9]{64}", entry["sha256"])
                or _sha256(file) != entry["sha256"]):
            raise WheelhouseError("Wheel SHA-256 mismatch; do not install")
    return len(candidates)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["create", "verify"])
    parser.add_argument("directory", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--platform", default="win_amd64")
    parser.add_argument("--python-abi", default="cp311")
    args = parser.parse_args(argv)
    try:
        if args.action == "create":
            receipt = build_receipt(args.directory, platform_tag=args.platform, python_abi=args.python_abi)
            if args.manifest.exists() or args.manifest.is_symlink():
                raise WheelhouseError("Refusing to replace an existing receipt")
            args.manifest.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf8")
            number = receipt["wheel_count"]
        else:
            receipt = json.loads(args.manifest.read_text(encoding="utf8"))
            if receipt.get("platform") != args.platform or receipt.get("python_abi") != args.python_abi:
                raise WheelhouseError("Wheelhouse platform/Python mismatch")
            number = verify_receipt(args.directory, receipt)
    except (WheelhouseError, ValueError, OSError, json.JSONDecodeError):
        print("FieldLab wheelhouse verification failed; no dependency installation permitted.", file=sys.stderr)
        return 2
    print(json.dumps({"status": "verified_local_wheels" if args.action == "verify" else "manifest_created",
                      "wheel_count": number, "platform": args.platform, "python_abi": args.python_abi}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
