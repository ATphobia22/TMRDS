"""Local append-only evidence ledger with a verifiable SHA-256 hash chain.

The ledger is an integrity aid, not a digital signature, trusted timestamp, or
protection against an attacker who can rewrite the entire file and its anchors.
Sensitive/patient-level content must not be written here.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import threading
from typing import Any, Dict, Iterator, List


GENESIS_HASH = "0" * 64
CURRENT_SCHEMA_VERSION = 2
_RESERVED_FIELDS = frozenset({"schema_version", "ts", "previous_hash", "content_hash"})


class LedgerIntegrityError(ValueError):
    """Raised when an existing ledger cannot be verified without ambiguity."""


class EvidenceLedger:
    """Single-file JSONL ledger; writers serialize through a sidecar OS lock."""

    def __init__(self, path: str = "data/research/evidence_ledger.jsonl") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._thread_lock = threading.RLock()

    def content_hash(self, payload: Dict[str, Any]) -> str:
        """Hash canonical JSON, rejecting NaN/Infinity and non-JSON objects."""
        if not isinstance(payload, dict):
            raise ValueError("ledger record must be a JSON object")
        try:
            body = json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ValueError("ledger record must contain finite JSON-compatible values") from exc
        return hashlib.sha256(body).hexdigest()

    @staticmethod
    def _legacy_content_hash(payload: Dict[str, Any]) -> str:
        """Match the original v1 serializer exactly for backward verification."""
        try:
            body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        except (TypeError, ValueError) as exc:
            raise LedgerIntegrityError("legacy ledger record cannot be serialized") from exc
        return hashlib.sha256(body).hexdigest()

    @contextmanager
    def _process_lock(self) -> Iterator[None]:
        lock_path = self.path.with_name(self.path.name + ".lock")
        with lock_path.open("a+b") as lock_file:
            if os.name == "nt":
                import msvcrt

                lock_file.seek(0, os.SEEK_END)
                if lock_file.tell() == 0:
                    lock_file.write(b"\0")
                    lock_file.flush()
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
                try:
                    yield
                finally:
                    lock_file.seek(0)
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    @contextmanager
    def _locked(self) -> Iterator[None]:
        with self._thread_lock:
            with self._process_lock():
                yield

    def _read_verified(self) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        if not self.path.exists():
            entries: list[dict[str, Any]] = []
        else:
            raw = self.path.read_bytes()
            if raw and not raw.endswith(b"\n"):
                raise LedgerIntegrityError("ledger has an incomplete final line")
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise LedgerIntegrityError("ledger is not valid UTF-8") from exc

            entries = []
            legacy_count = 0
            chain_count = 0
            for line_number, line in enumerate(text.splitlines(), start=1):
                if not line.strip():
                    raise LedgerIntegrityError(f"ledger contains an empty line at {line_number}")
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise LedgerIntegrityError(f"ledger JSON is invalid at line {line_number}") from exc
                if not isinstance(entry, dict):
                    raise LedgerIntegrityError(f"ledger entry is not an object at line {line_number}")

                stored_hash = entry.get("content_hash")
                if not isinstance(stored_hash, str) or len(stored_hash) != 64:
                    raise LedgerIntegrityError(f"ledger hash is missing or malformed at line {line_number}")
                try:
                    int(stored_hash, 16)
                except ValueError as exc:
                    raise LedgerIntegrityError(f"ledger hash is not hexadecimal at line {line_number}") from exc

                schema_version = entry.get("schema_version", 1)
                unhashed = {key: value for key, value in entry.items() if key != "content_hash"}
                if schema_version == 1 and type(schema_version) is int:
                    if chain_count:
                        raise LedgerIntegrityError(
                            f"legacy v1 entry appears after v2 chain at line {line_number}"
                        )
                    expected_hash = self._legacy_content_hash(unhashed)
                    legacy_count += 1
                elif schema_version == CURRENT_SCHEMA_VERSION and type(schema_version) is int:
                    previous_hash = entry.get("previous_hash")
                    expected_previous = entries[-1]["content_hash"] if entries else GENESIS_HASH
                    if previous_hash != expected_previous:
                        raise LedgerIntegrityError(
                            f"previous_hash mismatch at line {line_number}"
                        )
                    expected_hash = self.content_hash(unhashed)
                    chain_count += 1
                else:
                    raise LedgerIntegrityError(
                        f"unsupported ledger schema version at line {line_number}"
                    )

                if stored_hash.casefold() != expected_hash:
                    raise LedgerIntegrityError(f"content hash mismatch at line {line_number}")
                entries.append(entry)

        legacy_count = sum(1 for entry in entries if "schema_version" not in entry or entry.get("schema_version") == 1)
        chain_count = len(entries) - legacy_count
        report = {
            "valid": True,
            "entry_count": len(entries),
            "legacy_entry_count": legacy_count,
            "chain_entry_count": chain_count,
            "chain_status": "PARTIAL_LEGACY_PREFIX" if legacy_count else "VERIFIED",
            "last_hash": entries[-1]["content_hash"] if entries else None,
            "external_head_anchor_required": bool(entries),
        }
        return entries, report

    def append(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Append a v2 entry only after the existing file verifies successfully."""
        if not isinstance(record, dict):
            raise ValueError("ledger record must be a JSON object")
        reserved = sorted(_RESERVED_FIELDS.intersection(record))
        if reserved:
            raise ValueError(f"ledger record contains reserved fields: {', '.join(reserved)}")

        with self._locked():
            entries, _ = self._read_verified()
            entry = dict(record)
            entry["schema_version"] = CURRENT_SCHEMA_VERSION
            entry["ts"] = datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
            entry["previous_hash"] = entries[-1]["content_hash"] if entries else GENESIS_HASH
            entry["content_hash"] = self.content_hash(entry)
            try:
                encoded = (
                    json.dumps(entry, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"
                )
            except (TypeError, ValueError) as exc:
                raise ValueError("ledger record must contain finite JSON-compatible values") from exc

            descriptor = os.open(
                self.path,
                os.O_WRONLY | os.O_CREAT | os.O_APPEND,
                0o600,
            )
            try:
                remaining = memoryview(encoded)
                while remaining:
                    written = os.write(descriptor, remaining)
                    if written <= 0:
                        raise OSError("ledger append made no forward progress")
                    remaining = remaining[written:]
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            return entry

    def verify(self) -> Dict[str, Any]:
        """Verify all records; v1 prefixes are hash-checked but not retroactively chained."""
        with self._locked():
            _, report = self._read_verified()
            return report

    def recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        with self._locked():
            entries, _ = self._read_verified()
            return entries[-limit:]

    def status(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "node": "EvidenceLedger",
            "path": str(self.path),
            "exists": self.path.exists(),
        }
        try:
            report = self.verify()
        except (LedgerIntegrityError, OSError) as exc:
            result.update({
                "status": "INTEGRITY_ERROR",
                "integrity_valid": False,
                "integrity_error": str(exc),
            })
            return result
        result.update(report)
        result.update({"status": "READY", "integrity_valid": True})
        return result
