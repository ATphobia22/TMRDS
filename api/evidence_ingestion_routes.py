"""Live ingestion routes for the governed biomedical evidence graph."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from engines.live_evidence_ingestion_service import LiveEvidenceIngestionService
from api.realtime_data_fabric_routes import router as data_fabric_router

router = APIRouter(prefix="/api/v1/evidence/ingest", tags=["governed-evidence-ingestion"])
service = LiveEvidenceIngestionService()


def envelope(data: Any) -> dict[str, Any]:
    from datetime import datetime, timezone
    return {"status": "research-advisory", "human_authority_final": True, "not_samd": True, "read_only": False, "source": "TMRDS Governed Live Ingestion", "retrieved_at": datetime.now(timezone.utc).isoformat(), "data": data}


@router.post("/clinical-trials")
async def ingest_clinical_trials(query: str = Query(..., min_length=2), limit: int = Query(default=10, ge=1, le=50)) -> dict[str, Any]:
    try:
        return envelope(await service.ingest_trials(query, limit))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"ClinicalTrials.gov ingestion failed: {exc}") from exc


@router.post("/openneuro")
async def ingest_openneuro(query: str = Query(default="MRI", min_length=1), limit: int = Query(default=10, ge=1, le=50)) -> dict[str, Any]:
    try:
        return envelope(await service.ingest_openneuro(query, limit))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OpenNeuro ingestion failed: {exc}") from exc


# The data fabric is mounted through the existing ingestion router so the
# current api/main.py remains backward-compatible and requires no route surgery.
router.include_router(data_fabric_router)
