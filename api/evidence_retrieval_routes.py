"""Provenance-preserving semantic retrieval routes."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from engines.evidence_graph_repository import EvidenceGraphRepository

router = APIRouter(prefix="/api/v1/evidence", tags=["evidence-retrieval"])
repository = EvidenceGraphRepository()


class SemanticSearchRequest(BaseModel):
    embedding: list[float] = Field(min_length=1, max_length=1536)
    limit: Annotated[int, Field(ge=1, le=100)] = 20


@router.post("/semantic-search")
async def semantic_search(request: SemanticSearchRequest) -> dict[str, object]:
    try:
        results = await repository.semantic_search(request.embedding, request.limit)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Evidence retrieval unavailable: {exc}") from exc
    return {
        "status": "research-advisory",
        "human_authority_final": True,
        "read_only": True,
        "embedding_is_derived_projection": True,
        "results": results,
    }
