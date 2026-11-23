"""TMRDS public research-only app, isolated from clinical, database and write routes.

Do NOT expose the all-purpose api.main service as the public research website.
This app contains only read-only, bounded public evidence endpoints.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles

from api.error_responses import RequestCorrelationMiddleware
from api.governed_pathway_routes import router as pathway_router
from api.ops import (
    SecurityHeadersMiddleware, configure_logging, limiter, setup_rate_limiting,
)
from engines.federated_evidence_search import COVERAGE, FederatedEvidenceSearch
from engines.research_dossier import build_research_dossier

app = FastAPI(
    title="TMRDS Public Research Evidence Gateway",
    version="1.0.0",
    description="Public source-linked biomedical research discovery; no patient routes or writes.",
    docs_url=None, redoc_url=None, openapi_url=None,
)
configure_logging()
setup_rate_limiting(app)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestCorrelationMiddleware)
app.include_router(pathway_router)


@app.get("/health/live")
async def public_liveness() -> dict:
    return {"status": "alive", "service": "tmrds-public-research"}


@app.get("/health/ready")
async def public_readiness() -> dict:
    """Process readiness only: source availability is reported per request/audit."""
    return {"status": "ready", "external_sources_verified": False}


@app.get("/api/v1/research/dossier")
@limiter.limit("5/minute")
async def public_research_dossier(
    request: Request,
    query: str = Query(..., min_length=2, max_length=120),
    limit: int = Query(default=3, ge=1, le=5),
) -> dict:
    """Run 25 documented public research adapters with per-provider fault isolation."""
    if not query.strip():
        raise HTTPException(422, detail="research query must not be blank")
    try:
        search = await asyncio.wait_for(
            FederatedEvidenceSearch(timeout=18).search_all(
                query.strip(), limit, preserve_source_records=True
            ),
            timeout=40,
        )
    except Exception:
        raise HTTPException(503, detail="Research federation failed or exceeded safety bounds") from None
    dossier = build_research_dossier(search)
    dossier["service"] = "tmrds-public-research"
    dossier["data_use_warning"] = "Per-provider and per-record licenses require review before reuse"
    return dossier


@app.get("/api/v1/research/gwas-associations")
@limiter.limit("15/minute")
async def public_gwas(
    request: Request,
    trait: str = Query(..., min_length=2, max_length=120),
    limit: int = Query(default=8, ge=1, le=25),
) -> dict:
    service = FederatedEvidenceSearch(timeout=18)
    result = await service._guard("gwas_catalog_v2", service._search_gwas_catalog_v2(trait, limit))
    return {
        "query": trait,
        "searched_at": datetime.now(timezone.utc).isoformat(),
        "source": "gwas_catalog_v2",
        "source_status": {"ok": result.ok, "count": result.count, "warning": result.warning,
                          "coverage": COVERAGE["gwas_catalog_v2"]},
        "envelopes": result.envelopes,
        "governance": {"research_advisory_only": True, "human_authority_final": True,
                       "not_samd": True, "clinical_promotion_allowed": False},
    }


@app.get("/backend-config.json", include_in_schema=False)
async def public_configuration() -> dict:
    """Only the running API enables same-origin live governed research."""
    return {"schema_version": "1.0", "api_mode": "same-origin"}


# MUST remain last so static files cannot shadow backend endpoints.
app.mount("/", StaticFiles(directory=str(Path(__file__).resolve().parents[1] / "public"), html=True), name="public-atlas")
