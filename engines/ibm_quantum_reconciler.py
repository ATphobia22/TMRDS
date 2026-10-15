"""Bounded, read-only IBM Quantum job reconciliation.

Remote job creation is never called here. Ambiguous submissions without a known
remote job ID remain unresolved for an operator; results require an injected,
approved artifact sink before the ledger can mark a job complete.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

from engines.ibm_quantum_compute import IBMQuantumComputeClient
from engines.ibm_quantum_job_ledger import QuantumJobLedger

ResultSink = Callable[[str, object], Awaitable[str]]


class IBMQuantumReconciler:
    """Reconcile at most one bounded page of known remote job IDs per call."""

    def __init__(
        self,
        ledger: QuantumJobLedger,
        client: IBMQuantumComputeClient,
        *,
        result_sink: ResultSink | None = None,
        max_result_bytes: int = 10 * 1024 * 1024,
        batch_limit: int = 25,
    ) -> None:
        if not 1 <= batch_limit <= 100:
            raise ValueError("batch_limit must be between 1 and 100")
        if not 1024 <= max_result_bytes <= 100 * 1024 * 1024:
            raise ValueError("max_result_bytes must be between 1 KiB and 100 MiB")
        self.ledger = ledger
        self.client = client
        self.result_sink = result_sink
        self.max_result_bytes = max_result_bytes
        self.batch_limit = batch_limit

    async def reconcile_once(self) -> dict[str, int]:
        """Perform one bounded pass; never create or cancel remote jobs."""
        if os.getenv("TMRDS_IBM_QUANTUM_RECONCILER_ENABLED") != "true":
            raise RuntimeError("IBM Quantum reconciliation is disabled; explicit opt-in is required")
        rows = await self.ledger.list_reconciliation_candidates(self.batch_limit)
        counts = {
            "checked": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0,
            "unresolved": 0,
            "result_storage_unavailable": 0,
            "unrecognized": 0,
            "errors": 0,
        }
        for row in rows:
            job_id = row.get("ibm_job_id")
            if not isinstance(job_id, str) or not job_id:
                # Never guess a match from timestamps, backend, or workload content.
                counts["unresolved"] += 1
                continue
            counts["checked"] += 1
            try:
                remote = await asyncio.to_thread(self.client.get_job, job_id)
                if not isinstance(remote, dict) or remote.get("id") != job_id:
                    counts["errors"] += 1
                    continue
                status = _remote_status(remote)
                current_state = str(row.get("state", ""))
                submission_id = row.get("submission_id")
                if not isinstance(submission_id, UUID):
                    counts["errors"] += 1
                    continue
                if status in {"queued", "pending", "validating", "running", "in progress", "completed", "done", "failed", "cancelled", "canceled"}:
                    current_state = await self._ensure_submitted(submission_id, current_state, job_id)
                    if not current_state:
                        counts["errors"] += 1
                        continue
                if status in {"queued", "pending", "validating"}:
                    continue
                if status in {"running", "in progress"}:
                    if current_state == "SUBMITTED":
                        saved = await self.ledger.transition(
                            submission_id, "SUBMITTED", "RUNNING", ibm_job_id=job_id
                        )
                        if saved:
                            counts["running"] += 1
                        else:
                            counts["errors"] += 1
                    continue
                if status in {"completed", "done"}:
                    if self.result_sink is None:
                        counts["result_storage_unavailable"] += 1
                        continue
                    payload = await asyncio.to_thread(self.client.get_job_results, job_id)
                    serialized = json.dumps(
                        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                        allow_nan=False,
                    ).encode("utf-8")
                    if len(serialized) > self.max_result_bytes:
                        counts["errors"] += 1
                        continue
                    artifact_uri = await self.result_sink(job_id, payload)
                    if not _is_safe_artifact_uri(artifact_uri):
                        counts["errors"] += 1
                        continue
                    result_hash = hashlib.sha256(serialized).hexdigest()
                    saved = await self.ledger.transition(
                        submission_id, current_state, "COMPLETED",
                        ibm_job_id=job_id,
                        result_sha256=result_hash,
                        result_artifact_uri=artifact_uri,
                    )
                    if saved:
                        counts["completed"] += 1
                    else:
                        counts["errors"] += 1
                    continue
                if status in {"failed", "cancelled", "canceled"}:
                    terminal = "FAILED" if status == "failed" else "CANCELLED"
                    saved = await self.ledger.transition(
                        submission_id, current_state, terminal,
                        ibm_job_id=job_id,
                        error_code="IBM_REMOTE_FAILED" if terminal == "FAILED" else "IBM_REMOTE_CANCELLED",
                    )
                    if saved:
                        counts["failed" if terminal == "FAILED" else "cancelled"] += 1
                    else:
                        counts["errors"] += 1
                    continue
                counts["unrecognized"] += 1
            except Exception:
                # Do not log upstream bodies or exception strings from the SDK.
                counts["errors"] += 1
        return counts

    async def _ensure_submitted(
        self, submission_id: UUID, current_state: str, job_id: str
    ) -> str:
        if current_state in {"SUBMISSION_UNKNOWN", "SUBMITTING"}:
            saved = await self.ledger.transition(
                submission_id, current_state, "SUBMITTED", ibm_job_id=job_id
            )
            return "SUBMITTED" if saved else ""
        return current_state


def _remote_status(remote: dict[str, Any]) -> str:
    state = remote.get("state")
    status = state.get("status") if isinstance(state, dict) else None
    if not isinstance(status, str):
        status = remote.get("status")
    return status.strip().casefold() if isinstance(status, str) else ""



def _is_safe_artifact_uri(value: object) -> bool:
    if not isinstance(value, str) or not value or len(value) > 2048:
        return False
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    return (
        parsed.scheme in {"artifact", "s3"}
        and bool(parsed.netloc)
        and parsed.username is None
        and parsed.password is None
        and not parsed.query
        and not parsed.fragment
        and all(part not in {".", ".."} for part in parsed.path.split("/"))
    )



async def _run_once() -> dict[str, int]:
    from engines.ibm_quantum_compute import IBMQuantumComputeClient
    from engines.ibm_quantum_job_ledger import QuantumJobLedger
    from engines.quantum_result_store import LocalQuantumResultStore

    result_dir = os.getenv("TMRDS_QUANTUM_RESULT_DIR", "").strip()
    if not result_dir:
        raise RuntimeError("TMRDS_QUANTUM_RESULT_DIR is required for result integrity")
    client = IBMQuantumComputeClient.from_environment()
    ledger = QuantumJobLedger()
    try:
        batch_limit = int(os.getenv("TMRDS_IBM_QUANTUM_RECONCILER_BATCH_LIMIT", "25"))
        reconciler = IBMQuantumReconciler(
            ledger,
            client,
            result_sink=LocalQuantumResultStore(result_dir),
            batch_limit=batch_limit,
        )
        return await reconciler.reconcile_once()
    finally:
        client.close()
        await ledger.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="perform one bounded reconciliation pass")
    args = parser.parse_args(argv)
    if not args.once:
        parser.error("only --once is supported; schedule repeated runs externally with bounded intervals")
    try:
        counts = asyncio.run(_run_once())
    except Exception:
        print("IBM Quantum reconciliation failed; check safe configuration and database status.", file=sys.stderr)
        return 2
    print(json.dumps(counts, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
