#!/usr/bin/env python3
"""Check every declared requirement is represented and satisfied by the lock."""
from __future__ import annotations

import re
import sys
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

ROOT = Path(__file__).resolve().parents[1]


def read_lock(path: Path) -> dict[str, Version]:
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


def main() -> int:
    requirements_path = ROOT / "requirements.txt"
    lock_path = ROOT / "requirements.lock"
    locked = read_lock(lock_path)
    failures: list[str] = []
    for line_number, raw_line in enumerate(requirements_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            requirement = Requirement(line)
        except Exception as exc:
            failures.append(f"requirements.txt:{line_number}: invalid requirement syntax")
            continue
        name = canonicalize_name(requirement.name)
        version = locked.get(name)
        if version is None:
            failures.append(f"requirements.txt:{line_number}: {requirement.name} is missing from requirements.lock")
        elif requirement.specifier and version not in requirement.specifier:
            failures.append(
                f"requirements.txt:{line_number}: locked {requirement.name}=={version} "
                f"does not satisfy {requirement.specifier}"
            )
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print(f"dependency lock valid: {len(locked)} exact pins satisfy declared requirements")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
