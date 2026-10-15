from __future__ import annotations

import hashlib
import json

import pytest

from engines.quantum_artifact_store import LocalQuantumArtifactStore, QuantumArtifactStoreError


@pytest.mark.asyncio
async def test_store_writes_canonical_result_and_returns_content_addressed_uri(tmp_path) -> None:
    payload = {"counts": {"0": 2, "1": 3}}
    store = LocalQuantumArtifactStore(tmp_path)
    uri = await store.store("ibm-job-1", payload)

    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    expected_hash = hashlib.sha256(serialized).hexdigest()
    job_key = hashlib.sha256(b"ibm-job-1").hexdigest()
    assert uri == f"artifact://quantum-results/{job_key}-{expected_hash}.json"
    assert (tmp_path / f"{job_key}-{expected_hash}.json").read_bytes() == serialized


@pytest.mark.asyncio
async def test_store_is_idempotent_for_same_job_and_payload(tmp_path) -> None:
    store = LocalQuantumArtifactStore(tmp_path)
    first = await store.store("job_2", {"ok": True})
    second = await store.store("job_2", {"ok": True})
    assert first == second


@pytest.mark.asyncio
@pytest.mark.parametrize("job_id", ["../escape", "/tmp/file", "bad id", ""])
async def test_store_rejects_unsafe_job_ids(tmp_path, job_id: str) -> None:
    with pytest.raises(QuantumArtifactStoreError, match="Invalid remote job identifier"):
        await LocalQuantumArtifactStore(tmp_path).store(job_id, {"ok": True})


@pytest.mark.asyncio
async def test_store_rejects_non_finite_json(tmp_path) -> None:
    with pytest.raises(QuantumArtifactStoreError, match="canonical JSON"):
        await LocalQuantumArtifactStore(tmp_path).store("job_3", {"value": float("nan")})
