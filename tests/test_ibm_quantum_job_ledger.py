from __future__ import annotations

import os
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from engines.ibm_quantum_job_ledger import (
    IBMQuantumSubmissionService,
    QuantumJobLedgerError,
    QuantumJobLedger,
)


class FakeLedger:
    def __init__(
        self,
        *,
        transition_results: list[bool] | None = None,
        claim_result: bool = True,
    ) -> None:
        async def _prepare(submission):
            return submission.submission_id
        self.prepare = AsyncMock(side_effect=_prepare)
        self.transition_calls: list[tuple[uuid.UUID, str, str, dict]] = []
        self.transition_results = list(transition_results or [True, True])
        self.transition = AsyncMock(side_effect=self._transition)
        self.claim_for_submission = AsyncMock(return_value=claim_result)

    async def _transition(self, submission_id, expected, new, **kwargs):
        self.transition_calls.append((submission_id, expected, new, kwargs))
        if self.transition_results:
            return self.transition_results.pop(0)
        return True


def fake_client(response=None, side_effect=None):
    client = Mock()
    client._config = SimpleNamespace(api_version="2026-04-15", region="us")
    if side_effect is not None:
        client.submit_sampler.side_effect = side_effect
    else:
        client.submit_sampler.return_value = response or {"id": "ibm-job-123"}
    return client


@pytest.mark.asyncio
async def test_submission_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("TMRDS_IBM_QUANTUM_SUBMISSION_ENABLED", raising=False)
    ledger = FakeLedger()
    client = fake_client()
    service = IBMQuantumSubmissionService(ledger)

    with pytest.raises(QuantumJobLedgerError, match="disabled"):
        await service.submit(
            client=client, idempotency_key="req-1", artifact_uri="artifact://circuits/1",
            backend="backend", qasm_circuits=["OPENQASM 3.0;"], explicitly_authorized=True,
        )

    ledger.prepare.assert_not_awaited()
    client.submit_sampler.assert_not_called()


@pytest.mark.asyncio
async def test_submission_requires_explicit_authorization(monkeypatch):
    monkeypatch.setenv("TMRDS_IBM_QUANTUM_SUBMISSION_ENABLED", "true")
    ledger = FakeLedger()
    client = fake_client()

    with pytest.raises(QuantumJobLedgerError, match="Explicit workload authorization"):
        await IBMQuantumSubmissionService(ledger).submit(
            client=client, idempotency_key="req-1", artifact_uri="artifact://circuits/1",
            backend="backend", qasm_circuits=["OPENQASM 3.0;"], explicitly_authorized=False,
        )

    ledger.prepare.assert_not_awaited()
    client.submit_sampler.assert_not_called()


@pytest.mark.asyncio
async def test_submission_persists_before_single_remote_post(monkeypatch):
    monkeypatch.setenv("TMRDS_IBM_QUANTUM_SUBMISSION_ENABLED", "true")
    ledger = FakeLedger()
    client = fake_client({"id": "ibm-job-123"})

    result = await IBMQuantumSubmissionService(ledger).submit(
        client=client, idempotency_key="req-1", artifact_uri="artifact://circuits/1",
        backend="backend", qasm_circuits=["OPENQASM 3.0;"], shots=512,
        explicitly_authorized=True,
    )

    ledger.prepare.assert_awaited_once()
    ledger.claim_for_submission.assert_awaited_once()
    assert [call[1:3] for call in ledger.transition_calls] == [
        ("SUBMITTING", "SUBMITTED")
    ]
    assert ledger.transition_calls[-1][3]["ibm_job_id"] == "ibm-job-123"
    client.submit_sampler.assert_called_once_with(
        backend="backend", qasm_circuits=["OPENQASM 3.0;"], shots=512
    )
    assert result["state"] == "SUBMITTED"
    assert result["ibm_job_id"] == "ibm-job-123"
    assert len(result["input_sha256"]) == 64


@pytest.mark.asyncio
async def test_ambiguous_post_failure_is_marked_unknown_and_not_retried(monkeypatch):
    monkeypatch.setenv("TMRDS_IBM_QUANTUM_SUBMISSION_ENABLED", "true")
    ledger = FakeLedger()
    client = fake_client(side_effect=TimeoutError("network timeout"))

    with pytest.raises(QuantumJobLedgerError, match="outcome is uncertain"):
        await IBMQuantumSubmissionService(ledger).submit(
            client=client, idempotency_key="req-2", artifact_uri="artifact://circuits/2",
            backend="backend", qasm_circuits=["OPENQASM 3.0;"], explicitly_authorized=True,
        )

    assert ledger.transition_calls[-1][1:3] == ("SUBMITTING", "SUBMISSION_UNKNOWN")
    client.submit_sampler.assert_called_once()


@pytest.mark.asyncio
async def test_missing_remote_job_id_is_marked_unknown(monkeypatch):
    monkeypatch.setenv("TMRDS_IBM_QUANTUM_SUBMISSION_ENABLED", "true")
    ledger = FakeLedger()
    client = fake_client({"status": "accepted"})

    with pytest.raises(QuantumJobLedgerError, match="did not contain a job ID"):
        await IBMQuantumSubmissionService(ledger).submit(
            client=client, idempotency_key="req-3", artifact_uri="artifact://circuits/3",
            backend="backend", qasm_circuits=["OPENQASM 3.0;"], explicitly_authorized=True,
        )

    assert ledger.transition_calls[-1][1:3] == ("SUBMITTING", "SUBMISSION_UNKNOWN")


def test_invalid_state_transition_is_rejected_without_database():
    ledger = QuantumJobLedger(dsn="postgresql://unused")
    with pytest.raises(ValueError, match="Invalid quantum job state transition"):
        import asyncio
        asyncio.run(ledger.transition(uuid.uuid4(), "PREPARED", "COMPLETED"))



@pytest.mark.asyncio
async def test_submission_refuses_remote_post_when_atomic_rate_limit_claim_fails(monkeypatch):
    monkeypatch.setenv("TMRDS_IBM_QUANTUM_SUBMISSION_ENABLED", "true")
    ledger = FakeLedger(claim_result=False)
    client = fake_client()

    with pytest.raises(QuantumJobLedgerError, match="rate limit or concurrent state"):
        await IBMQuantumSubmissionService(ledger).submit(
            client=client, idempotency_key="req-rate", artifact_uri="artifact://circuits/rate",
            backend="backend", qasm_circuits=["OPENQASM 3.0;"], explicitly_authorized=True,
        )

    client.submit_sampler.assert_not_called()
    ledger.transition.assert_not_awaited()


@pytest.mark.asyncio
async def test_local_submission_limit_cannot_exceed_ibm_contract(monkeypatch):
    monkeypatch.setenv("TMRDS_IBM_QUANTUM_SUBMISSION_LIMIT_PER_MINUTE", "6")
    ledger = QuantumJobLedger(dsn=None)
    with pytest.raises(QuantumJobLedgerError, match="between 1 and 5"):
        await ledger.claim_for_submission(uuid.uuid4())
