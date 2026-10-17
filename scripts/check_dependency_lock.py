#!/usr/bin/env python3
"""Validate direct requirements against canonical locks and legacy aliases."""
from __future__ import annotations

import re
import sys
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version, InvalidVersion

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENT_PAIRS = (
    ("requirements.txt", "requirements.lock"),
    ("requirements-runtime.txt", "requirements-runtime.lock"),
)
LOCK_ALIASES = (
    ("requirements.lock", "requirements-lock.txt"),
    ("requirements-runtime.lock", "requirements-runtime-lock.txt"),
)


def read_lock(path: Path) -> dict[str, Version]:
    """Read strict exact pins and reject ambiguous lock syntax."""
    locked: dict[str, Version] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+-]+)", line)
        if not match:
            raise ValueError(f"{path.name}:{line_number}: lock entry must use exact == pins")
        name, version_text = match.groups()
        key = canonicalize_name(name)
        if key in locked:
            raise ValueError(f"{path.name}:{line_number}: duplicate lock entry for {name}")
        try:
            locked[key] = Version(version_text)
        except InvalidVersion as exc:
            raise ValueError(f"{path.name}:{line_number}: invalid version for {name}") from exc
    return locked


def validate_pair(root: Path, requirements_name: str, lock_name: str) -> tuple[list[str], dict[str, Version]]:
    """Validate one declaration/lock pair and return issues plus its parsed lock."""
    requirements_path = root / requirements_name
    lock_path = root / lock_name
    failures: list[str] = []
    try:
        locked = read_lock(lock_path)
    except (OSError, ValueError) as exc:
        return [str(exc)], {}

    for line_number, raw_line in enumerate(requirements_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            requirement = Requirement(line)
        except Exception:
            failures.append(f"{requirements_name}:{line_number}: invalid requirement syntax")
            continue
        # Environment markers must still be syntactically valid. Locks intentionally cover
        # the supported Python 3.11 runtime, regardless of the host running this check.
        name = canonicalize_name(requirement.name)
        version = locked.get(name)
        if version is None:
            failures.append(f"{requirements_name}:{line_number}: {requirement.name} is missing from {lock_name}")
        elif requirement.specifier and version not in requirement.specifier:
            failures.append(
                f"{requirements_name}:{line_number}: locked {requirement.name}=={version} "
                f"does not satisfy {requirement.specifier}"
            )
    return failures, locked


def validate_dependency_locks(root: Path = ROOT) -> list[str]:
    """Validate requirements/locks, shared direct pins, and compatibility aliases."""
    failures: list[str] = []
    parsed_locks: dict[str, dict[str, Version]] = {}
    for requirements_name, lock_name in REQUIREMENT_PAIRS:
        pair_failures, locked = validate_pair(root, requirements_name, lock_name)
        failures.extend(pair_failures)
        parsed_locks[lock_name] = locked

    for canonical_name, alias_name in LOCK_ALIASES:
        canonical_path = root / canonical_name
        alias_path = root / alias_name
        try:
            if canonical_path.read_bytes() != alias_path.read_bytes():
                failures.append(f"{alias_name} must be byte-identical to {canonical_name}")
        except OSError as exc:
            failures.append(f"{alias_name}: unable to verify alias ({type(exc).__name__})")

    # Runtime and test locks can have different transitive extras, but every shared direct
    # runtime dependency must resolve to the same exact version in both environments.
    try:
        test_reqs = [
            Requirement(line.strip())
            for line in (root / "requirements.txt").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        runtime_reqs = [
            Requirement(line.strip())
            for line in (root / "requirements-runtime.txt").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        test_names = {canonicalize_name(req.name) for req in test_reqs}
        runtime_names = {canonicalize_name(req.name) for req in runtime_reqs}
        shared_direct = test_names & runtime_names
        test_lock = parsed_locks.get("requirements.lock", {})
        runtime_lock = parsed_locks.get("requirements-runtime.lock", {})
        for name in sorted(shared_direct):
            left, right = test_lock.get(name), runtime_lock.get(name)
            if left is not None and right is not None and left != right:
                failures.append(
                    f"shared direct dependency {name} differs between locks: "
                    f"requirements.lock=={left}, requirements-runtime.lock=={right}"
                )
    except (OSError, ValueError) as exc:
        failures.append(f"unable to compare direct dependencies ({type(exc).__name__})")

    return failures


def main() -> int:
    try:
        failures = validate_dependency_locks()
    except OSError as exc:
        print(f"dependency lock validation failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    if failures:
        print("\n".join(failures), file=sys.stderr)
        print(f"dependency lock validation failed: {len(failures)} issue(s)", file=sys.stderr)
        return 1
    total = len(read_lock(ROOT / "requirements.lock"))
    runtime = len(read_lock(ROOT / "requirements-runtime.lock"))
    print(
        "dependency locks valid: "
        f"{total} test/development pins and {runtime} runtime pins; aliases and shared pins consistent"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
