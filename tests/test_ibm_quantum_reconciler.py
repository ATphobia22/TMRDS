from __future__ import annotations

import hashlib
import json
import uuid
from unittest.mock import AsyncMock, Mock

import pytest

from engines.ibm_quantum_reconciler import IBMQuantumReconciler


@pytest.fixture(autouse=True)
def enable_test_reconciliation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TMRDS_IBM_QUANTUM_RECONCILER_ENABLED", "true")


def candidate(state: str, job_id: str | None) -> dict:
    return {
        "submission_id": uuid.uuid4(),
        "state": state,
        "ibm_job_id": job_id,
        "created_at": None,
    }


class FakeLedger:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.transition = AsyncMock(return_value=True)
        self.list_reconciliation_candidates = AsyncMock(return_value=rows)


@pytest.mark.asyncio
async def test_unknown_submission_without_remote_id_is_never_guessed_or_resubmitted() -> None:
    row = candidate("SUBMISSION_UNKNOWN", None)
    ledger = FakeLedger([row])
    client = Mock()
    reconciler = IBMQuantumReconciler(ledger, client)

    result = await reconciler.reconcile_once()

    assert result["unresolved"] == 1
    client.get_job.assert_not_called()
    client.submit_sampler.assert_not_called()
    ledger.transition.assert_not_awaited()


@pytest.mark.asyncio
async def test_completed_job_result_is_saved_before_terminal_state_transition() -> None:
    row = candidate("SUBMITTED", "ibm-job-42")
    ledger = FakeLedger([row])
    client = Mock()
    client.get_job.return_value = {"id": "ibm-job-42", "state": {"status": "Completed"}}
    payload = {"results": [{"data": {"counts": {"0": 512}}}]}
    client.get_job_results.return_value = payload
    stored = []

    async def result_sink(job_id: str, value: object) -> str:
        stored.append((job_id, value))
        return "artifact://quantum-results/ibm-job-42.json"

    reconciler = IBMQuantumReconciler(ledger, client, result_sink=result_sink)
    result = await reconciler.reconcile_once()

    expected_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    assert result["completed"] == 1
    assert stored == [("ibm-job-42", payload)]
    assert ledger.transition.await_args_list[-1].args[1:3] == ("SUBMITTED", "COMPLETED")
    assert ledger.transition.await_args_list[-1].kwargs["result_sha256"] == expected_hash
    assert ledger.transition.await_args_list[-1].kwargs["result_artifact_uri"] == "artifact://quantum-results/ibm-job-42.json"


@pytest.mark.asyncio
async def test_running_job_transitions_once_without_fetching_results() -> None:
    row = candidate("SUBMITTED", "ibm-job-43")
    ledger = FakeLedger([row])
    client = Mock()
    client.get_job.return_value = {"id": "ibm-job-43", "status": "Running"}

    result = await IBMQuantumReconciler(ledger, client).reconcile_once()

    assert result["running"] == 1
    ledger.transition.assert_awaited_once()
    assert ledger.transition.await_args.args[1:3] == ("SUBMITTED", "RUNNING")
    client.get_job_results.assert_not_called()


@pytest.mark.asyncio
async def test_completed_job_is_not_marked_complete_without_result_sink() -> None:
    row = candidate("RUNNING", "ibm-job-44")
    ledger = FakeLedger([row])
    client = Mock()
    client.get_job.return_value = {"id": "ibm-job-44", "status": "Completed"}
    client.get_job_results.return_value = {"results": []}

    result = await IBMQuantumReconciler(ledger, client).reconcile_once()

    assert result["result_storage_unavailable"] == 1
    ledger.transition.assert_not_awaited()
