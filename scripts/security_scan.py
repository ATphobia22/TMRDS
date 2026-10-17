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
    ("github_fine_grained_token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("gitlab_token", re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("api_token", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("bearer_token", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{24,}\b", re.IGNORECASE)),
    ("database_password_url", re.compile(r"(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?)://[^\s:/]+:[^\s@]+@", re.IGNORECASE)),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    (
        "secret_assignment",
        re.compile(
            r"\b(?:SECRET_KEY|API_KEY|ACCESS_TOKEN|CLIENT_SECRET|PRIVATE_KEY|"
            r"AWS_SECRET_ACCESS_KEY|TMRDS_HMAC_SECRET|IBM_QUANTUM_API_KEY)\s*=\s*[\"'][^\"']{12,}[\"']",
            re.IGNORECASE,
        ),
    ),
)
# Only these explicit placeholder values may suppress the specific regex match that
# contains them. They never suppress scanning of other text on the same line.
SAFE_PLACEHOLDERS = {
    "<strong-random-secret>",
    "<strong-password>",
    "<set-in-deployment-secret>",
    "<redacted>",
    "replace-with-local-only-password",
    "replace-with-local-only-pin",
    "replace-with-random-secret",
}
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache"}
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".zip", ".pdf", ".sqlite", ".db"}


def scan_text(text: str, path: str = "<text>") -> list[SecretFinding]:
    """Return likely secret-pattern matches without line-level allowlist bypasses."""
    findings: list[SecretFinding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for pattern_name, pattern in PATTERNS:
            for match in pattern.finditer(line):
                matched_text = match.group(0).casefold()
                if any(placeholder.casefold() in matched_text for placeholder in SAFE_PLACEHOLDERS):
                    continue
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
