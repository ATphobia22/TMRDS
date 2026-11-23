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
from api.open_medical_routes import router as open_medical_router
from api.public_crosscheck_routes import router as public_crosscheck_router
from api.governed_pathway_routes import router as pathway_router
from api.ops import (
    SecurityHeadersMiddleware, configure_logging, limiter, setup_rate_limiting,
)
from engines.federated_evidence_search import COVERAGE, FederatedEvidenceSearch
from engines.governed_pathway import evaluate_license
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
app.include_router(open_medical_router)
app.include_router(public_crosscheck_router)


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
    if any(ord(char) < 32 for char in query):
        raise HTTPException(422, detail="control characters are not permitted")
    # Connect ONLY adapters that have an explicit, reviewable policy permitting
    # bounded public metadata display. Cataloged but unapproved providers are
    # visible as withheld and are never queried by this public service.
    allowed = {
        "opentargets": "_search_opentargets",
        "chembl": "_search_chembl",
        "europe_pmc": "_search_europepmc",
        "pubmed": "_search_pubmed",
        "clinicaltrials_gov": "_search_trials",
        "openfda": "_search_openfda",
        "dailymed": "_search_dailymed",
        "gwas_catalog_v2": "_search_gwas_catalog_v2",
    }
    if not all(evaluate_license(provider)["metadata_display_allowed"] for provider in allowed):
        raise HTTPException(503, detail="Public research license policy review is not current")
    service = FederatedEvidenceSearch(timeout=18)
    try:
        results = await asyncio.wait_for(
            asyncio.gather(*(
                service._guard(provider, getattr(service, adapter)(query.strip(), limit))
                for provider, adapter in allowed.items()
            )),
            timeout=40,
        )
    except Exception:
        raise HTTPException(503, detail="Research federation failed or exceeded safety bounds") from None
    envelopes = []
    status = {}
    for result in results:
        # Do not rebroadcast abstracts, underlying source blobs, or structures:
        # a metadata-display policy is not blanket full-text redistribution.
        for envelope in result.envelopes:
            envelopes.append({
                key: value for key, value in envelope.items()
                if key not in {"abstract", "open_access_url", "canonical_smiles", "raw_record"}
            })
        status[result.source] = {
            "ok": result.ok, "count": result.count, "warning": result.warning,
            "coverage": COVERAGE[result.source],
            "governance": "public_metadata_only",
        }
    for provider, coverage in COVERAGE.items():
        if provider not in allowed:
            status[provider] = {
                "ok": False, "count": 0, "coverage": coverage,
                "warning": "License or access review required; not queried",
                "governance": "license_review_required_not_queried",
            }
    search = {
        "query": query.strip(),
        "searched_at": datetime.now(timezone.utc).isoformat(),
        "envelopes": envelopes,
        "source_status": status,
    }
    dossier = build_research_dossier(search)
    dossier["service"] = "tmrds-public-research"
    dossier["data_use_warning"] = "Eight explicitly registered adapters expose bounded metadata only. Other providers are withheld pending individual licensing; third-party text and bulk redistribution remain prohibited without human approval."
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
