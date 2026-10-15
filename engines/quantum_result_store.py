"""Opt-in private local artifact store for quantum job results."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any


class QuantumResultStoreError(RuntimeError):
    """Safe failure for immutable quantum result artifact storage."""


class LocalQuantumResultStore:
    """Write immutable JSON results into an explicitly configured private directory."""

    def __init__(self, root: str | Path, *, max_bytes: int = 10 * 1024 * 1024) -> None:
        if not 1024 <= max_bytes <= 100 * 1024 * 1024:
            raise ValueError("max_bytes must be between 1 KiB and 100 MiB")
        self.root = Path(root)
        self.max_bytes = max_bytes

    async def __call__(self, job_id: str, payload: object) -> str:
        return await asyncio.to_thread(self._store, job_id, payload)

    def _store(self, job_id: str, payload: object) -> str:
        if not isinstance(job_id, str) or not job_id or len(job_id) > 256:
            raise ValueError("job_id is invalid")
        try:
            content = json.dumps(
                payload, sort_keys=True, separators=(",", ":"),
                ensure_ascii=False, allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ValueError("result payload must be finite JSON") from exc
        if len(content) > self.max_bytes:
            raise QuantumResultStoreError("result payload exceeds configured size limit")

        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        root = self.root.resolve(strict=True)
        if not root.is_dir():
            raise QuantumResultStoreError("result storage path is not a directory")
        try:
            os.chmod(root, 0o700)
        except OSError as exc:
            raise QuantumResultStoreError("result storage permissions could not be secured") from exc

        job_hash = hashlib.sha256(job_id.encode("utf-8")).hexdigest()
        payload_hash = hashlib.sha256(content).hexdigest()
        destination = root / f"result-{job_hash}.json"
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", prefix=".tmp-", dir=root, delete=False
            ) as temporary:
                temp_path = Path(temporary.name)
                os.chmod(temp_path, 0o600)
                temporary.write(content)
                temporary.flush()
                os.fsync(temporary.fileno())
            try:
                os.link(temp_path, destination)
            except FileExistsError:
                file_stat = destination.lstat()
                if not stat.S_ISREG(file_stat.st_mode):
                    raise QuantumResultStoreError("existing result artifact is not a regular file")
                existing = destination.read_bytes()
                if existing != content:
                    raise QuantumResultStoreError("immutable result artifact conflicts with existing content")
            directory_fd = os.open(root, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError as exc:
            raise QuantumResultStoreError("result artifact could not be stored safely") from exc
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass
        return f"artifact://quantum-results/{destination.name}"
