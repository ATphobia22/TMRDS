#!/usr/bin/env python3
"""Fail CI when GitHub workflow actions are not pinned to immutable commit SHAs."""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USES_PATTERN = re.compile(r"^\s*(?:-\s*)?uses:\s*([^\s#]+)", re.MULTILINE)
FULL_SHA_REF = re.compile(r"^[^@\s]+@[0-9a-fA-F]{40}$")


@dataclass(frozen=True, slots=True)
class WorkflowFinding:
    path: str
    line: int
    message: str


def scan_workflow_text(text: str, path: str = "<workflow>") -> list[WorkflowFinding]:
    findings: list[WorkflowFinding] = []
    if not re.search(r"^permissions\s*:", text, re.MULTILINE):
        findings.append(WorkflowFinding(path, 1, "workflow must declare least-privilege top-level permissions"))
    for match in USES_PATTERN.finditer(text):
        reference = match.group(1)
        if reference.startswith("./"):
            continue
        if not FULL_SHA_REF.fullmatch(reference):
            line = text.count("\n", 0, match.start()) + 1
            findings.append(
                WorkflowFinding(
                    path,
                    line,
                    f"action reference must be pinned to a full 40-character commit SHA: {reference}",
                )
            )
    return findings


def scan_workflows(root: Path = ROOT) -> list[WorkflowFinding]:
    workflow_dir = root / ".github" / "workflows"
    if not workflow_dir.is_dir():
        return [WorkflowFinding(".github/workflows", 1, "workflow directory is missing")]
    findings: list[WorkflowFinding] = []
    files = sorted(
        path for path in workflow_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".yml", ".yaml"}
    )
    if not files:
        return [WorkflowFinding(".github/workflows", 1, "no workflow files found")]
    for path in files:
        findings.extend(scan_workflow_text(path.read_text(encoding="utf-8"), str(path.relative_to(root))))
    return findings


def main() -> int:
    findings = scan_workflows()
    for finding in findings:
        print(f"{finding.path}:{finding.line}: {finding.message}", file=sys.stderr)
    if findings:
        print(f"workflow security check failed: {len(findings)} issue(s)", file=sys.stderr)
        return 1
    print("workflow security check passed: action refs are immutable SHAs and permissions are explicit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
