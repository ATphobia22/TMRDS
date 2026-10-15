"""Durable, fail-closed IBM Quantum job ledger and submission orchestration.

The ledger uses the same PostgreSQL DSN as the evidence graph. It intentionally
never persists credentials or raw circuit text. Callers must store immutable
circuit artifacts in an approved artifact store and pass its reference.
"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Sequence

import asyncpg

from engines.ibm_quantum_compute import IBMQuantumComputeClient, IBMQuantumError


class QuantumJobLedgerError(RuntimeError):
    """Safe error for durable quantum job orchestration."""


@dataclass(frozen=True, slots=True)
class QuantumSubmission:
    submission_id: uuid.UUID
    idempotency_key: str
    input_sha256: str
    artifact_uri: str
    backend: str
    shots: int | None
    api_version: str
    region: str


class QuantumJobLedger:
    """PostgreSQL-backed ledger; database state is authoritative locally."""

    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or os.getenv("TMRDS_DATABASE_URL") or None
        self.pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        if self.pool is None:
            if not self.dsn:
                raise QuantumJobLedgerError(
                    "TMRDS_DATABASE_URL is required; no built-in database credential is permitted"
                )
            self.pool = await asyncpg.create_pool(
                self.dsn, min_size=1, max_size=10, command_timeout=30
            )

    async def close(self) -> None:
        if self.pool is not None:
            await self.pool.close()
            self.pool = None

    async def _pool(self) -> asyncpg.Pool:
        await self.connect()
        assert self.pool is not None
        return self.pool

    async def prepare(self, submission: QuantumSubmission) -> None:
        pool = await self._pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO quantum_job_submissions
                   (submission_id, idempotency_key, input_sha256, artifact_uri,
                    backend, shots, api_version, region, state)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,'PREPARED')
                   ON CONFLICT (idempotency_key) DO NOTHING""",
                submission.submission_id, submission.idempotency_key,
                submission.input_sha256, submission.artifact_uri,
                submission.backend, submission.shots, submission.api_version,
                submission.region,
            )
            row = await conn.fetchrow(
                """SELECT submission_id, input_sha256, artifact_uri, backend, shots,
                          api_version, region, state
                   FROM quantum_job_submissions WHERE idempotency_key=$1""",
                submission.idempotency_key,
            )
        if row is None:
            raise QuantumJobLedgerError("Unable to confirm durable submission record.")
        if (
            row["input_sha256"] != submission.input_sha256
            or row["artifact_uri"] != submission.artifact_uri
            or row["backend"] != submission.backend
            or row["shots"] != submission.shots
        ):
            raise QuantumJobLedgerError(
                "Idempotency key already belongs to a different workload."
            )
        if row["state"] != "PREPARED":
            raise QuantumJobLedgerError(
                f"Submission already exists in state {row['state']}; refusing duplicate remote submission."
            )

    async def transition(
        self,
        submission_id: uuid.UUID,
        expected_state: str,
        new_state: str,
        *,
        ibm_job_id: str | None = None,
        error_code: str | None = None,
        result_sha256: str | None = None,
        result_artifact_uri: str | None = None,
    ) -> bool:
        allowed = {
            "PREPARED": {"SUBMITTING"},
            "SUBMITTING": {"SUBMITTED", "SUBMISSION_UNKNOWN"},
            "SUBMITTED": {"RUNNING", "COMPLETED", "FAILED", "CANCELLED"},
            "RUNNING": {"COMPLETED", "FAILED", "CANCELLED"},
            "SUBMISSION_UNKNOWN": {"SUBMITTED", "FAILED"},
        }
        if new_state not in allowed.get(expected_state, set()):
            raise ValueError(f"Invalid quantum job state transition: {expected_state} -> {new_state}")
        pool = await self._pool()
        row = await pool.fetchrow(
            """UPDATE quantum_job_submissions
               SET state=$3,
                   ibm_job_id=COALESCE($4, ibm_job_id),
                   error_code=$5,
                   result_sha256=COALESCE($6, result_sha256),
                   updated_at=now(),
                   submitted_at=CASE WHEN $3='SUBMITTED' THEN now() ELSE submitted_at END,
                   completed_at=CASE WHEN $3 IN ('COMPLETED','FAILED','CANCELLED') THEN now() ELSE completed_at END,
                   metadata=CASE WHEN $7 IS NULL THEN metadata
                                 ELSE metadata || jsonb_build_object('result_artifact_uri', $7) END
               WHERE submission_id=$1 AND state=$2
               RETURNING submission_id""",
            submission_id, expected_state, new_state, ibm_job_id, error_code, result_sha256,
            result_artifact_uri,
        )
        return row is not None

    async def get(self, submission_id: uuid.UUID) -> dict[str, Any] | None:
        pool = await self._pool()
        row = await pool.fetchrow(
            """SELECT submission_id, idempotency_key, input_sha256, artifact_uri,
                      backend, shots, api_version, region, state, ibm_job_id,
                      result_sha256, error_code, created_at, updated_at,
                      submitted_at, completed_at, metadata
               FROM quantum_job_submissions WHERE submission_id=$1""",
            submission_id,
        )
        return dict(row) if row else None

    async def list_reconciliation_candidates(self, limit: int = 100) -> list[dict[str, Any]]:
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        pool = await self._pool()
        rows = await pool.fetch(
            """SELECT submission_id, idempotency_key, input_sha256, artifact_uri,
                      backend, shots, api_version, region, state, ibm_job_id,
                      created_at, updated_at
               FROM quantum_job_submissions
               WHERE state IN ('SUBMISSION_UNKNOWN','SUBMITTING','SUBMITTED','RUNNING')
               ORDER BY created_at ASC LIMIT $1""",
            limit,
        )
        return [dict(row) for row in rows]


class IBMQuantumSubmissionService:
    """One-shot remote submission guarded by durable local state."""

    def __init__(self, ledger: QuantumJobLedger) -> None:
        self.ledger = ledger

    async def submit(
        self,
        *,
        client: IBMQuantumComputeClient,
        idempotency_key: str,
        artifact_uri: str,
        backend: str,
        qasm_circuits: Sequence[str],
        shots: int | None = None,
        explicitly_authorized: bool = False,
    ) -> dict[str, Any]:
        if os.getenv("TMRDS_IBM_QUANTUM_SUBMISSION_ENABLED") != "true":
            raise QuantumJobLedgerError(
                "Hardware submission is disabled; set TMRDS_IBM_QUANTUM_SUBMISSION_ENABLED=true after approval."
            )
        if not explicitly_authorized:
            raise QuantumJobLedgerError("Explicit workload authorization is required.")
        if not idempotency_key or len(idempotency_key) > 200:
            raise ValueError("idempotency_key must contain 1-200 characters.")
        if not artifact_uri or len(artifact_uri) > 2048:
            raise ValueError("artifact_uri must contain 1-2048 characters.")
        if not backend or not qasm_circuits or any(
            not isinstance(circuit, str) or not circuit.strip() for circuit in qasm_circuits
        ):
            raise ValueError("A backend and non-empty circuit list are required.")

        canonical_input = json.dumps(
            {"backend": backend, "circuits": list(qasm_circuits), "shots": shots},
            sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        ).encode("utf-8")
        config = client._config
        submission = QuantumSubmission(
            submission_id=uuid.uuid4(),
            idempotency_key=idempotency_key,
            input_sha256=hashlib.sha256(canonical_input).hexdigest(),
            artifact_uri=artifact_uri,
            backend=backend,
            shots=shots,
            api_version=config.api_version,
            region=config.region,
        )
        await self.ledger.prepare(submission)
        claimed = await self.ledger.transition(
            submission.submission_id, "PREPARED", "SUBMITTING"
        )
        if not claimed:
            raise QuantumJobLedgerError("Submission state changed concurrently; refusing remote submission.")

        try:
            response = await _run_blocking_submission(
                client, backend, list(qasm_circuits), shots
            )
        except Exception as exc:
            # A failure after request initiation cannot prove the remote job was not created.
            await self.ledger.transition(
                submission.submission_id, "SUBMITTING", "SUBMISSION_UNKNOWN",
                error_code=type(exc).__name__[:80],
            )
            raise QuantumJobLedgerError(
                "Submission outcome is uncertain; do not resubmit. Reconcile against IBM job history."
            ) from None

        job_id = response.get("id") if isinstance(response, dict) else None
        if not isinstance(job_id, str) or not job_id:
            await self.ledger.transition(
                submission.submission_id, "SUBMITTING", "SUBMISSION_UNKNOWN",
                error_code="MISSING_REMOTE_JOB_ID",
            )
            raise QuantumJobLedgerError(
                "IBM response did not contain a job ID; submission requires reconciliation."
            )
        saved = await self.ledger.transition(
            submission.submission_id, "SUBMITTING", "SUBMITTED", ibm_job_id=job_id
        )
        if not saved:
            raise QuantumJobLedgerError(
                "IBM accepted the job but the ledger update did not complete; reconcile before any resubmission."
            )
        return {
            "submission_id": str(submission.submission_id),
            "ibm_job_id": job_id,
            "state": "SUBMITTED",
            "input_sha256": submission.input_sha256,
            "artifact_uri": submission.artifact_uri,
        }


async def _run_blocking_submission(
    client: IBMQuantumComputeClient,
    backend: str,
    circuits: list[str],
    shots: int | None,
) -> dict[str, Any] | list[Any]:
    """Keep the synchronous requests client from blocking the asyncio event loop."""
    import asyncio

    return await asyncio.to_thread(
        client.submit_sampler, backend=backend, qasm_circuits=circuits, shots=shots
    )
