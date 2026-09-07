"""Contract tests for the TMRDS real-world real-time data fabric."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from engines.realtime_data_fabric import (
    CanonicalObservation,
    DataFabric,
    SourceDefinition,
    build_default_fabric,
    sha256_payload,
)


def test_payload_hash_is_deterministic() -> None:
    payload = {"b": 2, "a": [1, 3]}
    assert sha256_payload(payload) == sha256_payload({"a": [1, 3], "b": 2})


def test_source_definition_rejects_non_https_endpoint() -> None:
    with pytest.raises(ValueError):
        SourceDefinition(
            source_id="unsafe",
            provider="test",
            name="Unsafe",
            endpoint="http://example.com/feed",
            format="json",
        )


def test_fabric_deduplicates_observations_by_content_identity() -> None:
    fabric = DataFabric()
    observation = CanonicalObservation(
        source_id="test",
        record_id="1",
        observed_at=datetime(2026, 9, 7, tzinfo=timezone.utc),
        retrieved_at=datetime(2026, 9, 7, tzinfo=timezone.utc),
        payload={"value": 42},
        payload_hash=sha256_payload({"value": 42}),
    )
    assert fabric.accept(observation) is True
    assert fabric.accept(observation) is False
    assert len(fabric.observations()) == 1


def test_default_fabric_contains_authoritative_public_realtime_sources() -> None:
    fabric = build_default_fabric()
    source_ids = {source.source_id for source in fabric.sources()}
    assert {"usgs_water", "noaa_weather", "nws_alerts", "fema_disasters"}.issubset(source_ids)


def test_fabric_quarantines_invalid_payload() -> None:
    fabric = DataFabric()
    result = fabric.ingest_payload(
        source_id="test",
        record_id="bad",
        payload=None,
        observed_at=datetime(2026, 9, 7, tzinfo=timezone.utc),
    )
    assert result.accepted is False
    assert result.quarantined is True
