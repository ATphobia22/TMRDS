"""Local immutable artifact sink for bounded IBM Quantum result payloads."""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path


class QuantumArtifactStoreError(RuntimeError):
    """Safe error for result artifact persistence failures."""


class LocalQuantumArtifactStore:
    """Persist canonical JSON with exclusive creation and content verification."""

    _SAFE_JOB_ID = re.compile(r"[A-Za-z0-9_-]{1,200}\Z")

    def __init__(self, root: Path | str | None = None, *, max_bytes: int = 10 * 1024 * 1024) -> None:
        if not 1024 <= max_bytes <= 100 * 1024 * 1024:
            raise ValueError("max_bytes must be between 1 KiB and 100 MiB")
        self.root = Path(root or os.getenv("TMRDS_QUANTUM_ARTIFACT_DIR", "/app/data/quantum-results"))
        self.max_bytes = max_bytes

    async def store(self, job_id: str, payload: object) -> str:
        """Store results without allowing job IDs to influence filesystem paths."""
        import asyncio

        return await asyncio.to_thread(self._store_sync, job_id, payload)

    def _store_sync(self, job_id: str, payload: object) -> str:
        if not isinstance(job_id, str) or not self._SAFE_JOB_ID.fullmatch(job_id):
            raise QuantumArtifactStoreError("Invalid remote job identifier.")
        try:
            serialized = json.dumps(
                payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
            ).encode("utf-8")
        except (TypeError, ValueError, UnicodeError) as exc:
            raise QuantumArtifactStoreError("Result payload is not canonical JSON.") from exc
        if len(serialized) > self.max_bytes:
            raise QuantumArtifactStoreError("Result payload exceeds configured artifact size limit.")

        job_key = hashlib.sha256(job_id.encode("utf-8")).hexdigest()
        content_hash = hashlib.sha256(serialized).hexdigest()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        root = self.root.resolve(strict=True)
        target = root / f"{job_key}-{content_hash}.json"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(target, flags, 0o600)
        except FileExistsError:
            try:
                existing = target.read_bytes()
            except OSError as exc:
                raise QuantumArtifactStoreError("Existing result artifact cannot be verified.") from exc
            if existing != serialized:
                raise QuantumArtifactStoreError("Existing result artifact failed integrity verification.")
        except OSError as exc:
            raise QuantumArtifactStoreError("Result artifact could not be created.") from exc
        else:
            try:
                with os.fdopen(descriptor, "wb") as output:
                    output.write(serialized)
                    output.flush()
                    os.fsync(output.fileno())
            except OSError as exc:
                try:
                    target.unlink(missing_ok=True)
                except OSError:
                    pass
                raise QuantumArtifactStoreError("Result artifact could not be durably written.") from exc
        return f"artifact://quantum-results/{job_key}-{content_hash}.json"
