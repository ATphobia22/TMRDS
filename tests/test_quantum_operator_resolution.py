from __future__ import annotations

import uuid

import pytest

from engines.ibm_quantum_job_ledger import QuantumJobLedger


@pytest.mark.asyncio
async def test_operator_resolution_rejects_signed_or_credential_bearing_evidence_reference() -> None:
    ledger = QuantumJobLedger(dsn=None)

    with pytest.raises(ValueError, match="evidence reference"):
        await ledger.resolve_unknown_submission(
            uuid.uuid4(),
            ibm_job_id="known-job-id",
            operator_id="operator-1",
            evidence_reference="https://example.invalid/evidence?signature=private",
        )


@pytest.mark.asyncio
async def test_operator_resolution_rejects_path_like_remote_job_ids() -> None:
    ledger = QuantumJobLedger(dsn=None)

    with pytest.raises(ValueError, match="IBM job ID"):
        await ledger.resolve_unknown_submission(
            uuid.uuid4(),
            ibm_job_id="../other-job",
            operator_id="operator-1",
            evidence_reference="artifact://evidence/ticket-123",
        )
