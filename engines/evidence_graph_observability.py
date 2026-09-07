"""Operational metrics for evidence-source and graph health."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import monotonic
from typing import Any


@dataclass
class SourceMetrics:
    requests: int = 0
    successes: int = 0
    failures: int = 0
    records_seen: int = 0
    records_ingested: int = 0
    records_deduplicated: int = 0
    conflicts_detected: int = 0
    total_latency_ms: float = 0.0
    last_success_at: str | None = None
    last_error: str | None = None


@dataclass
class EvidenceGraphObservability:
    sources: dict[str, SourceMetrics] = field(default_factory=dict)

    def record_ingestion_metrics(self, source_id: str, *, success: bool, latency_ms: float, records_seen: int = 0, records_ingested: int = 0, records_deduplicated: int = 0, conflicts_detected: int = 0, error: str | None = None) -> None:
        metrics = self.sources.setdefault(source_id, SourceMetrics())
        metrics.requests += 1
        metrics.successes += int(success)
        metrics.failures += int(not success)
        metrics.records_seen += records_seen
        metrics.records_ingested += records_ingested
        metrics.records_deduplicated += records_deduplicated
        metrics.conflicts_detected += conflicts_detected
        metrics.total_latency_ms += max(0.0, latency_ms)
        if success:
            metrics.last_success_at = datetime.now(timezone.utc).isoformat()
        else:
            metrics.last_error = error

    def source_health(self, source_id: str) -> dict[str, Any]:
        metrics = self.sources.get(source_id, SourceMetrics())
        return {"source_id": source_id, "requests": metrics.requests, "successes": metrics.successes, "failures": metrics.failures, "success_rate": (metrics.successes / metrics.requests) if metrics.requests else None, "avg_latency_ms": (metrics.total_latency_ms / metrics.requests) if metrics.requests else None, "last_success_at": metrics.last_success_at, "last_error": metrics.last_error}

    def graph_health(self) -> dict[str, Any]:
        return {"status": "ready", "sources": {source_id: self.source_health(source_id) for source_id in sorted(self.sources)}}

    @staticmethod
    def timer() -> float:
        return monotonic()
