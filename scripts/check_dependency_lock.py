#!/usr/bin/env python3
"""Validate direct runtime and test requirements against exact-version lock files."""
from __future__ import annotations

import re
import sys
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

ROOT = Path(__file__).resolve().parents[1]
LOCK_PAIRS = (
    (ROOT / "requirements.txt", ROOT / "requirements.lock"),
    (ROOT / "requirements-runtime.txt", ROOT / "requirements-runtime.lock"),
)


def read_lock(path: Path) -> dict[str, Version]:
    """Read a lock file containing one exact == pin per non-comment line."""
    locked: dict[str, Version] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+-]+)", line)
        if not match:
            raise ValueError(f"{path.name}:{line_number}: lock entry must use exact == pins")
        name, version = match.groups()
        key = canonicalize_name(name)
        if key in locked:
            raise ValueError(f"{path.name}:{line_number}: duplicate lock entry for {name}")
        locked[key] = Version(version)
    return locked


def validate_pair(requirements_path: Path, lock_path: Path) -> list[str]:
    """Return all direct-requirement/lock mismatches for one dependency set."""
    failures: list[str] = []
    if not requirements_path.is_file():
        return [f"missing dependency declaration file: {requirements_path.relative_to(ROOT)}"]
    if not lock_path.is_file():
        return [f"missing dependency lock file: {lock_path.relative_to(ROOT)}"]

    try:
        locked = read_lock(lock_path)
    except (OSError, ValueError) as exc:
        return [str(exc)]

    for line_number, raw_line in enumerate(
        requirements_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            requirement = Requirement(line)
        except Exception:
            failures.append(f"{requirements_path.name}:{line_number}: invalid requirement syntax")
            continue

        # Environment markers can make a declaration inactive on the current platform.
        if requirement.marker and not requirement.marker.evaluate():
            continue

        name = canonicalize_name(requirement.name)
        version = locked.get(name)
        if version is None:
            failures.append(
                f"{requirements_path.name}:{line_number}: {requirement.name} "
                f"is missing from {lock_path.name}"
            )
        elif requirement.specifier and version not in requirement.specifier:
            failures.append(
                f"{requirements_path.name}:{line_number}: locked {requirement.name}=={version} "
                f"does not satisfy {requirement.specifier}"
            )
    return failures


def main() -> int:
    failures: list[str] = []
    summaries: list[str] = []
    for requirements_path, lock_path in LOCK_PAIRS:
        pair_failures = validate_pair(requirements_path, lock_path)
        failures.extend(pair_failures)
        if not pair_failures and lock_path.is_file():
            summaries.append(f"{requirements_path.name} -> {lock_path.name}: valid")

    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1

    print("Dependency lock validation passed:")
    print("\n".join(f"  - {summary}" for summary in summaries))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
