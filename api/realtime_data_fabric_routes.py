"""Read-only operational API for the TMRDS real-world data fabric."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from engines.realtime_data_fabric import build_default_fabric, health_snapshot

router = APIRouter(prefix="/api/v1/data-fabric", tags=["real-time-data-fabric"])
fabric = build_default_fabric()


def envelope(data: Any) -> dict[str, Any]:
    return {
        "status": "research-advisory",
        "human_authority_final": True,
        "read_only": True,
        "fabric_version": "1.0.0",
        "data": data,
    }


@router.get("/sources")
async def list_sources() -> dict[str, Any]:
    return envelope([source.model_dump(mode="json") for source in fabric.sources()])


@router.get("/sources/{source_id}")
async def source_status(source_id: str) -> dict[str, Any]:
    try:
        source = fabric.source(source_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Data-fabric source not registered") from exc
    state = fabric.state(source_id)
    return envelope({
        "source": source.model_dump(mode="json"),
        "state": {
            "etag": state.etag,
            "last_modified": state.last_modified,
            "last_success_at": state.last_success_at,
            "last_error": state.last_error,
            "consecutive_failures": state.consecutive_failures,
        },
    })


@router.get("/health")
async def fabric_health() -> dict[str, Any]:
    return envelope([asdict(item) for item in health_snapshot(fabric)])


@router.post("/sync/{source_id}")
async def sync_source(source_id: str, timeout_seconds: float = Query(default=15.0, ge=1.0, le=30.0)) -> dict[str, Any]:
    try:
        result = await fabric.fetch(source_id, timeout_seconds=timeout_seconds)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Data-fabric source not registered") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Authoritative upstream source unavailable") from exc
    return envelope(result)
