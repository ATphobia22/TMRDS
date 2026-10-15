from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from engines.governed_evidence_ingestion import (
    ADAPTER_VERSION,
    GovernedEvidenceIngestion,
    NORMALIZATION_VERSION,
    payload_hash,
)


@pytest.mark.asyncio
async def test_observation_persists_canonical_payload_hash_and_version_provenance() -> None:
    repository = Mock()
    repository.record_observation = AsyncMock(return_value=1)
    ingestion = GovernedEvidenceIngestion(repository)
    payload = {"z": [3, 2, 1], "a": {"status": "example"}}

    observation = await ingestion.ingest_observation(
        source_id="example-source",
        source_record_id="record-123",
        payload=payload,
        request_parameters={"query": "example"},
        source_version="2026-10",
    )

    repository.record_observation.assert_awaited_once()
    persisted = repository.record_observation.await_args.args[0]
    assert observation.raw_payload_hash == payload_hash(payload)
    assert persisted["raw_payload_hash"] == payload_hash(payload)
    assert persisted["adapter_version"] == ADAPTER_VERSION
    assert persisted["normalization_version"] == NORMALIZATION_VERSION
    assert persisted["source_id"] == "example-source"
    assert persisted["source_record_id"] == "record-123"
    assert persisted["source_version"] == "2026-10"
    assert persisted["request_parameters"] == {"query": "example"}
    assert observation.retrieved_at.tzinfo is not None


@pytest.mark.asyncio
async def test_payload_hash_is_stable_across_mapping_key_order() -> None:
    assert payload_hash({"alpha": 1, "beta": 2}) == payload_hash({"beta": 2, "alpha": 1})


@pytest.mark.asyncio
async def test_relation_without_source_provenance_is_rejected_before_write() -> None:
    repository = Mock()
    repository.create_assertion = AsyncMock()
    ingestion = GovernedEvidenceIngestion(repository)

    with pytest.raises(ValueError, match="source provenance is required"):
        await ingestion.assert_relation(
            subject=None,
            predicate="supports",
            object_entity=None,
            source_id="",
            source_record_id="",
            evidence_type="unknown",
            evidence_grade="ungraded",
        )

    repository.create_assertion.assert_not_awaited()
