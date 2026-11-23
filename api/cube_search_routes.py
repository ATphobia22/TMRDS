"""Read-only bounded Grover research coverage simulator; no patient input."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from api.ops import limiter
from engines.cube_grover_research import PLANES, simulate_grover_research_plan

router = APIRouter(prefix="/api/v1/research", tags=["quantum-research-demonstration"])


@router.get("/cube-search")
@limiter.limit("12/minute")
async def cube_search(
    request: Request,
    required: str = Query(default="disease_phenotype,target_pathway,trials_labels", max_length=120),
    max_planes: int = Query(default=4, ge=1, le=6),
) -> dict:
    names = tuple(x.strip() for x in required.split(","))
    if any(x not in PLANES for x in names) or len(names) != len(set(names)):
        raise HTTPException(422, detail="Only unique canonical evidence-plane names are allowed")
    try:
        return simulate_grover_research_plan(required=names, max_planes=max_planes)
    except ValueError:
        raise HTTPException(422, detail="Invalid bounded research-plane constraint") from None
