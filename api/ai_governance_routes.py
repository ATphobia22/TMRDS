"""Research-only AI governance API for TMRDS."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from engines.ai_governance import EvidenceEnvelope, GovernanceStatus, validate_generation_for_research

router = APIRouter(prefix="/api/v1/governance/ai", tags=["ai-governance"])


@router.get("/status")
async def ai_governance_status() -> dict[str, object]:
    return {
        "status": "research-advisory",
        "human_authority_final": True,
        "clinical_promotion_allowed": False,
        "autonomous_treatment_allowed": False,
        "provenance_required": True,
        "governance_framework": "NIST AI RMF",
    }


@router.post("/validate")
async def validate_ai_generation(envelope: EvidenceEnvelope) -> dict[str, object]:
    try:
        decision = validate_generation_for_research(envelope)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "status": "research-advisory",
        "human_authority_final": True,
        "clinical_promotion_allowed": False,
        "decision": decision.model_dump(mode="json"),
        "governance_status": envelope.governance_status.value,
        "generation_id": envelope.generation_id,
    }
