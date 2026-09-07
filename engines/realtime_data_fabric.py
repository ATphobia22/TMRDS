"""Real-world real-time data fabric for TMRDS.

The fabric provides bounded, provenance-first ingestion for authoritative public
feeds. It deliberately separates upstream observations from governed biomedical
evidence so environmental, geospatial, emergency, and scientific feeds cannot
silently become clinical assertions.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator


FABRIC_VERSION = "1.0.0"
MAX_PAYLOAD_BYTES = 5 * 1024 * 1024


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def sha256_payload(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


class SourceDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=2, max_length=128)
    provider: str = Field(min_length=1, max_length=256)
    name: str = Field(min_length=1, max_length=256)
    endpoint: str = Field(min_length=8, max_length=2048)
    format: str = Field(pattern=r"^(json|geojson)$")
    authority_class: str = Field(default="public_authoritative", min_length=1, max_length=64)
    update_frequency: str = Field(default="source-defined", max_length=64)
    requires_api_key: bool = False
    enabled: bool = True
    default_params: dict[str, str] = Field(default_factory=dict)

    @field_validator("endpoint")
    @classmethod
    def https_only(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("real-time source endpoints must use HTTPS")
        return value


class CanonicalObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    record_id: str
    observed_at: datetime
    retrieved_at: datetime
    payload: dict[str, Any]
    payload_hash: str = Field(min_length=64, max_length=64)
    source_version: str | None = None
    source_uri: str | None = None
    etag: str | None = None
    last_modified: str | None = None
    provenance_status: str = "source-retrieved"
    fabric_version: str = FABRIC_VERSION


class IngestionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accepted: bool
    quarantined: bool
    source_id: str
    record_id: str
    reason: str | None = None
    payload_hash: str | None = None
    retrieved_at: datetime = Field(default_factory=utc_now)


@dataclass(slots=True)
class SourceState:
    etag: str | None = None
    last_modified: str | None = None
    last_success_at: datetime | None = None
    last_error: str | None = None
    consecutive_failures: int = 0


class DataFabric:
    """Bounded in-process fabric used by API workers and deterministic tests."""

    def __init__(self, sources: list[SourceDefinition] | None = None) -> None:
        self._sources: dict[str, SourceDefinition] = {source.source_id: source for source in sources or []}
        self._states: dict[str, SourceState] = {}
        self._observations: dict[str, CanonicalObservation] = {}
        self._quarantine: list[IngestionResult] = []

    def register(self, source: SourceDefinition) -> None:
        existing = self._sources.get(source.source_id)
        if existing is not None and existing != source:
            raise ValueError(f"source_id already registered with different metadata: {source.source_id}")
        self._sources[source.source_id] = source

    def source(self, source_id: str) -> SourceDefinition:
        try:
            return self._sources[source_id]
        except KeyError as exc:
            raise KeyError(f"unknown data-fabric source: {source_id}") from exc

    def sources(self) -> list[SourceDefinition]:
        return [self._sources[key] for key in sorted(self._sources)]

    def state(self, source_id: str) -> SourceState:
        return self._states.setdefault(source_id, SourceState())

    def observations(self) -> list[CanonicalObservation]:
        return list(self._observations.values())

    def quarantined(self) -> list[IngestionResult]:
        return list(self._quarantine)

    def accept(self, observation: CanonicalObservation) -> bool:
        identity = f"{observation.source_id}:{observation.record_id}:{observation.payload_hash}"
        if identity in self._observations:
            return False
        self._observations[identity] = observation
        return True

    def ingest_payload(
        self,
        source_id: str,
        record_id: str,
        payload: Any,
        observed_at: datetime,
        *,
        source_version: str | None = None,
        source_uri: str | None = None,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> IngestionResult:
        retrieved_at = utc_now()
        if not isinstance(payload, dict):
            result = IngestionResult(accepted=False, quarantined=True, source_id=source_id, record_id=record_id, reason="payload must be a JSON object", retrieved_at=retrieved_at)
            self._quarantine.append(result)
            return result
        payload_hash = sha256_payload(payload)
        observation = CanonicalObservation(
            source_id=source_id,
            record_id=record_id,
            observed_at=observed_at,
            retrieved_at=retrieved_at,
            payload=payload,
            payload_hash=payload_hash,
            source_version=source_version,
            source_uri=source_uri,
            etag=etag,
            last_modified=last_modified,
        )
        accepted = self.accept(observation)
        return IngestionResult(
            accepted=accepted,
            quarantined=False,
            source_id=source_id,
            record_id=record_id,
            reason=None if accepted else "duplicate observation",
            payload_hash=payload_hash,
            retrieved_at=retrieved_at,
        )

    async def fetch(self, source_id: str, *, timeout_seconds: float = 15.0) -> dict[str, Any]:
        source = self.source(source_id)
        if not source.enabled:
            raise RuntimeError(f"source disabled: {source_id}")
        headers = {"Accept": "application/json", "User-Agent": "TMRDS-DataFabric/1.0 (+research)"}
        state = self.state(source_id)
        if state.etag:
            headers["If-None-Match"] = state.etag
        if state.last_modified:
            headers["If-Modified-Since"] = state.last_modified
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=False) as client:
                response = await client.get(source.endpoint, params=source.default_params, headers=headers)
            if response.status_code == 304:
                state.last_success_at = utc_now()
                state.consecutive_failures = 0
                return {"status": "not_modified", "source_id": source_id}
            response.raise_for_status()
            if len(response.content) > MAX_PAYLOAD_BYTES:
                raise ValueError("upstream payload exceeds bounded ingestion limit")
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("upstream response must be a JSON object")
            state.etag = response.headers.get("ETag")
            state.last_modified = response.headers.get("Last-Modified")
            state.last_success_at = utc_now()
            state.last_error = None
            state.consecutive_failures = 0
            return {
                "status": "fetched",
                "source_id": source_id,
                "retrieved_at": state.last_success_at.isoformat(),
                "payload_hash": sha256_payload(payload),
                "etag": state.etag,
                "last_modified": state.last_modified,
                "data": payload,
            }
        except Exception as exc:
            state.last_error = str(exc)[:512]
            state.consecutive_failures += 1
            raise


def build_default_fabric() -> DataFabric:
    """Return the authoritative public real-world feed catalog for TMRDS."""
    return DataFabric([
        SourceDefinition(
            source_id="usgs_water",
            provider="USGS",
            name="USGS Water Services Instantaneous Values",
            endpoint="https://waterservices.usgs.gov/nwis/iv/",
            format="json",
            update_frequency="real-time",
            default_params={"format": "json", "sites": "", "parameterCd": "00060", "siteStatus": "all"},
        ),
        SourceDefinition(
            source_id="usgs_earthquakes",
            provider="USGS",
            name="USGS Earthquake Hazards Program GeoJSON Feed",
            endpoint="https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson",
            format="geojson",
            update_frequency="hourly",
        ),
        SourceDefinition(
            source_id="noaa_weather",
            provider="NOAA/NWS",
            name="National Weather Service API",
            endpoint="https://api.weather.gov/points/39.1001,-84.5120",
            format="json",
            update_frequency="source-defined",
        ),
        SourceDefinition(
            source_id="nws_alerts",
            provider="NOAA/NWS",
            name="National Weather Service Active Alerts",
            endpoint="https://api.weather.gov/alerts/active",
            format="geojson",
            update_frequency="near-real-time",
            default_params={"status": "actual"},
        ),
        SourceDefinition(
            source_id="fema_disasters",
            provider="FEMA",
            name="FEMA Disaster Declarations Summaries",
            endpoint="https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries",
            format="json",
            update_frequency="source-defined",
        ),
        SourceDefinition(
            source_id="cdc_cdi",
            provider="CDC",
            name="CDC Chronic Disease Indicators",
            endpoint="https://data.cdc.gov/resource/a8ys-9fjs.json",
            format="json",
            update_frequency="source-defined",
        ),
    ])


@dataclass(slots=True)
class FabricHealth:
    source_id: str
    healthy: bool
    consecutive_failures: int
    last_success_at: datetime | None
    last_error: str | None


def health_snapshot(fabric: DataFabric) -> list[FabricHealth]:
    return [
        FabricHealth(
            source_id=source.source_id,
            healthy=fabric.state(source.source_id).consecutive_failures == 0,
            consecutive_failures=fabric.state(source.source_id).consecutive_failures,
            last_success_at=fabric.state(source.source_id).last_success_at,
            last_error=fabric.state(source.source_id).last_error,
        )
        for source in fabric.sources()
    ]
