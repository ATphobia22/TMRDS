#!/usr/bin/env python3
"""Deterministic repository secret scanner for CI and local verification."""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SecretFinding:
    path: str
    line: int
    pattern_name: str


PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("api_token", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("bearer_token", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{24,}\b", re.IGNORECASE)),
    ("database_password_url", re.compile(r"(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?)://[^\s:/]+:[^\s@]+@", re.IGNORECASE)),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("secret_assignment", re.compile(r"\b(?:SECRET_KEY|API_KEY|ACCESS_TOKEN)\s*=\s*[\"'][^\"']{12,}[\"']")),
)

ALLOWED_MARKERS = {
    "<strong-random-secret>",
    "<strong-password>",
    "<set-in-deployment-secret>",
    "<redacted>",
    "example.invalid",
}
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache"}
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".zip", ".pdf", ".sqlite", ".db"}


def scan_text(text: str, path: str = "<text>") -> list[SecretFinding]:
    findings: list[SecretFinding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if any(marker in line for marker in ALLOWED_MARKERS):
            continue
        for pattern_name, pattern in PATTERNS:
            if pattern.search(line):
                findings.append(SecretFinding(path, line_number, pattern_name))
    return findings


def iter_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.parts) or path.suffix.casefold() in SKIP_SUFFIXES:
            continue
        try:
            path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        yield path


def scan_repository(root: Path) -> list[SecretFinding]:
    findings: list[SecretFinding] = []
    for path in iter_files(root):
        findings.extend(scan_text(path.read_text(encoding="utf-8"), str(path.relative_to(root))))
    return findings


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    findings = scan_repository(root)
    for finding in findings:
        print(f"{finding.path}:{finding.line}: {finding.pattern_name}")
    if findings:
        print(f"security scan failed: {len(findings)} finding(s)", file=sys.stderr)
        return 1
    print("security scan passed: no committed secret patterns found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
