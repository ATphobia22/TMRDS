from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from engines.quantum_result_store import LocalQuantumResultStore


@pytest.mark.asyncio
async def test_local_result_store_writes_private_immutable_artifact(tmp_path: Path) -> None:
    store = LocalQuantumResultStore(tmp_path / "results")
    payload = {"counts": {"0": 512}}

    uri = await store("job-123", payload)

    assert uri.startswith("artifact://quantum-results/")
    files = list((tmp_path / "results").glob("result-*.json"))
    assert len(files) == 1
    assert json.loads(files[0].read_text(encoding="utf-8")) == payload
    assert os.stat(files[0]).st_mode & 0o777 == 0o600


@pytest.mark.asyncio
async def test_local_result_store_is_idempotent_for_same_payload(tmp_path: Path) -> None:
    store = LocalQuantumResultStore(tmp_path / "results")
    payload = {"counts": {"1": 8}}

    first = await store("job-123", payload)
    second = await store("job-123", payload)

    assert first == second
    assert len(list((tmp_path / "results").glob("result-*.json"))) == 1


@pytest.mark.asyncio
async def test_local_result_store_rejects_non_json_payload(tmp_path: Path) -> None:
    store = LocalQuantumResultStore(tmp_path / "results")

    with pytest.raises(ValueError, match="JSON"):
        await store("job-123", {"value": float("nan")})
