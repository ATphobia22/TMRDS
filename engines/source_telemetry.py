"""Explicit read-only provider probing; process-local observations, no patient data."""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
import os
import time
from typing import Literal
import httpx
from pydantic import BaseModel, ConfigDict, Field


class CircuitPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    failure_threshold: int = Field(default=3, ge=1, le=20)
    recovery_timeout_seconds: int = Field(default=60, ge=1, le=3600)


class SourceState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["not_checked", "operational", "degraded", "auth_blocked", "balance_exhausted", "circuit_open", "not_configured", "stale"] = "not_checked"
    timeout_seconds: int = Field(default=15, ge=1, le=60)
    max_retries: Literal[0] = 0
    circuit_breaker: CircuitPolicy = Field(default_factory=CircuitPolicy)
    checked_at: str | None = None
    latency_ms: float | None = None


class SourceCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"] = "1.0"
    research_advisory: Literal[True] = True
    telemetry_scope: Literal["process_local"] = "process_local"
    upstream_sources: dict[str, SourceState]


class SourceMonitor:
    def __init__(self):
        self.states = {name: SourceState() for name in ("tamarind", "patsnap")}
        self.failures = {name: 0 for name in self.states}
        self.retry_after = {name: 0.0 for name in self.states}
        self.lock = asyncio.Lock()

    def snapshot(self) -> dict:
        # No credentials, endpoint response bodies or account details are exposed.
        snapshot = SourceCatalog(upstream_sources=self.states).model_dump()
        for name, state in snapshot["upstream_sources"].items():
            if time.monotonic() < self.retry_after[name]:
                state["status"] = "circuit_open"
            elif state["checked_at"] and (datetime.now(timezone.utc) - datetime.fromisoformat(state["checked_at"])).total_seconds() > 300:
                state["status"] = "stale"
        return snapshot

    async def probe(self, provider: str) -> dict:
        if provider not in self.states:
            raise ValueError("unknown provider")
        async with self.lock:
            state = self.states[provider]
            if time.monotonic() < self.retry_after[provider]:
                return {**state.model_dump(), "status": "circuit_open"}
            state.latency_ms = None
            state.checked_at = datetime.now(timezone.utc).isoformat()
            if provider == "patsnap":
                # No verified no-charge balance/health API is configured.
                state.status = "not_configured"
                return state.model_dump()
            key = os.getenv("TAMARIND_API_KEY", "").strip()
            if not key:
                state.status = "auth_blocked"
                return state.model_dump()
            started = time.monotonic()
            try:
                async with httpx.AsyncClient(timeout=state.timeout_seconds, follow_redirects=False) as client:
                    response = await client.get("https://app.tamarind.bio/api/tools", headers={"x-api-key": key, "Accept": "application/json"})
                if response.status_code in (401, 403):
                    state.status = "auth_blocked"
                elif response.status_code == 200 and isinstance(response.json(), (dict, list)):
                    state.status = "operational"
                else:
                    state.status = "degraded"
            except (httpx.HTTPError, ValueError):
                state.status = "degraded"
            state.latency_ms = round((time.monotonic() - started) * 1000, 2)
            if state.status == "operational":
                self.failures[provider] = 0
                self.retry_after[provider] = 0
            else:
                self.failures[provider] += 1
                if self.failures[provider] >= state.circuit_breaker.failure_threshold:
                    self.retry_after[provider] = time.monotonic() + state.circuit_breaker.recovery_timeout_seconds
            return state.model_dump()
