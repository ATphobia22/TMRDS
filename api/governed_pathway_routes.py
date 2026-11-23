"""Public bounded biomedical pathway and source-use disclosures (research only)."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Query, Request

from api.ops import FEDERATED_SEARCH_RATE_LIMIT, limiter
from engines.governed_pathway import (
    PathwaySourceClient, PathwaySourceError, evaluate_license,
    load_reference_pathways, validate_reference_pathways,
)
from engines.federated_evidence_search import COVERAGE

router = APIRouter(prefix="/api/v1/research", tags=["governed-pathway"])


@router.get("/source-governance")
async def source_governance() -> dict:
    """Policy inventory, not live provider monitoring or license counsel."""
    return {
        "schema_version": "1.0", "as_of": datetime.now(timezone.utc).isoformat(),
        "source_policies": {
            key: {"coverage": coverage, "policy": evaluate_license(key)}
            for key, coverage in sorted(COVERAGE.items())
        },
        "health_scope": "not_probed", "legal_approval": "human_review_required",
        "clinical_promotion_allowed": False,
    }


@router.get("/evidence-pathway")
@limiter.limit(FEDERATED_SEARCH_RATE_LIMIT)
async def disease_target_compound_pathway(
    request: Request,
    disease: str = Query(..., min_length=2, max_length=120),
    limit: int = Query(default=8, ge=1, le=25),
) -> dict:
    """No implicit scientific joins: disease ID + source-reported target mechanism."""
    try:
        return await PathwaySourceClient().search(disease, limit=limit)
    except PathwaySourceError:
        return {
            "schema_version": "1.0",
            "status": "source_unavailable", "query": disease,
            "links": [], "source": "opentargets",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "source_warning": "Source request failed, exceeded bounds or returned an incompatible schema.",
            "license_review": [evaluate_license("opentargets"), evaluate_license("chembl")],
            "governance": {"clinical_promotion_allowed": False, "human_authority_final": True},
        }


@router.get("/reference-pathway-contract")
async def reference_pathway_contract() -> dict:
    """Static reference provenance; does NOT imply live or blinded validation."""
    ref = load_reference_pathways()
    return {
        "schema_version": ref["schema_version"],
        "created_at": ref["created_at"],
        "reference_review_status": ref["source_review_status"],
        "independent_human_review_completed": False,
        "expected_links": ref["expected_links"],
        "negative_controls": ref["negative_controls"],
        "methodology": ref["methodology"],
        "clinical_validation": False,
    }
