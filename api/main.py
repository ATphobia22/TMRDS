"""TMRDS real-time public medical research gateway.

All routes are read-only research retrieval endpoints. They expose source data and
provenance without converting retrieved evidence into diagnosis or treatment advice.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Query

from engines.cdc_data_pipeline import CDCDataPipeline
from engines.clinical_trials_pipeline import ClinicalTrialsPipeline
from engines.europe_pmc_pipeline import EuropePMCPipeline
from engines.nlm_research_pipeline import NLMResearchPipeline
from engines.openfda_pipeline import OpenFDAPipeline
from engines.openneuro_pipeline import OpenNeuroPipeline
from engines.pubmed_literature_bridge import PubMedLiteratureBridge

app = FastAPI(
    title="TMRDS Research Gateway",
    version="2.0.0-research",
    description="Live public biomedical evidence and research-data gateway.",
)

cdc = CDCDataPipeline()
openneuro = OpenNeuroPipeline()
trials = ClinicalTrialsPipeline()
openfda = OpenFDAPipeline()
nlm = NLMResearchPipeline()
europepmc = EuropePMCPipeline()
pubmed = PubMedLiteratureBridge()


def research_envelope(data: Any, source: str) -> dict[str, Any]:
    return {
        "status": "research-advisory",
        "human_authority_final": True,
        "not_samd": True,
        "read_only": True,
        "source": source,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }


@app.get("/api/v1/research/health")
async def research_health() -> dict[str, Any]:
    return research_envelope(
        {
            "cdc": "configured",
            "openneuro": "configured",
            "clinicaltrials": "configured",
            "openfda": "configured",
            "nlm": "configured",
            "europepmc": "configured",
            "pubmed": pubmed.status(),
        },
        "TMRDS",
    )


@app.get("/api/v1/research/datasets/cdc")
async def get_cdc_disease_data(
    limit: int = Query(default=50, ge=1, le=500),
    query: str | None = Query(default=None),
) -> dict[str, Any]:
    try:
        data = await cdc.search_indicators(query, limit) if query else await cdc.fetch_indicators(limit)
        return research_envelope(data, "CDC Chronic Disease Indicators")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"CDC upstream error: {exc}") from exc


@app.get("/api/v1/research/datasets/openneuro")
async def get_openneuro_data(
    query: str = Query(default="MRI", min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
) -> dict[str, Any]:
    try:
        return research_envelope(await openneuro.search_datasets(query, limit), "OpenNeuro")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OpenNeuro upstream error: {exc}") from exc


@app.get("/api/v1/research/trials")
async def search_trials(
    query: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    try:
        return research_envelope(await trials.search(query, limit), "ClinicalTrials.gov API v2")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"ClinicalTrials.gov upstream error: {exc}") from exc


@app.get("/api/v1/research/drugs/labels")
async def search_drug_labels(
    query: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    try:
        return research_envelope(await openfda.drug_labels(query, limit), "openFDA drug labeling")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"openFDA upstream error: {exc}") from exc


@app.get("/api/v1/research/drugs/adverse-events")
async def search_drug_adverse_events(
    query: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    try:
        return research_envelope(await openfda.adverse_events(query, limit), "openFDA drug adverse events")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"openFDA upstream error: {exc}") from exc


@app.get("/api/v1/research/drugs/shortages")
async def search_drug_shortages(
    query: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    try:
        return research_envelope(await openfda.drug_shortages(query, limit), "openFDA drug shortages")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"openFDA upstream error: {exc}") from exc


@app.get("/api/v1/research/nlm/conditions")
async def search_conditions(
    terms: str = Query(..., min_length=1),
    limit: int = Query(default=25, ge=1, le=500),
) -> dict[str, Any]:
    try:
        return research_envelope(await nlm.search_conditions(terms, limit), "NLM Clinical Tables")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"NLM upstream error: {exc}") from exc


@app.get("/api/v1/research/nlm/hpo")
async def search_hpo(
    terms: str = Query(..., min_length=1),
    limit: int = Query(default=25, ge=1, le=500),
) -> dict[str, Any]:
    try:
        return research_envelope(await nlm.search_hpo(terms, limit), "NLM Human Phenotype Ontology table")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"NLM upstream error: {exc}") from exc


@app.get("/api/v1/research/nlm/genes")
async def search_genes(
    terms: str = Query(..., min_length=1),
    limit: int = Query(default=25, ge=1, le=500),
) -> dict[str, Any]:
    try:
        return research_envelope(await nlm.search_genes(terms, limit), "NLM Clinical Tables genes")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"NLM upstream error: {exc}") from exc


@app.get("/api/v1/research/nlm/rxterms")
async def search_rxterms(
    terms: str = Query(..., min_length=1),
    limit: int = Query(default=25, ge=1, le=500),
) -> dict[str, Any]:
    try:
        return research_envelope(await nlm.search_rxterms(terms, limit), "NLM RxTerms")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"NLM upstream error: {exc}") from exc


@app.get("/api/v1/research/literature/europe-pmc")
async def search_europe_pmc(
    query: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    try:
        return research_envelope(await europepmc.search(query, limit), "Europe PMC")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Europe PMC upstream error: {exc}") from exc


@app.get("/api/v1/research/literature/pubmed")
async def search_pubmed(
    query: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    try:
        result = await asyncio.to_thread(pubmed.search, query, limit)
        if result.get("status") == "ERROR":
            raise RuntimeError(result.get("error", "PubMed request failed"))
        if result.get("pmids"):
            summaries = await asyncio.to_thread(pubmed.summaries, result["pmids"])
            result["articles"] = summaries.get("articles", [])
        return research_envelope(result, "NCBI PubMed E-utilities")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"PubMed upstream error: {exc}") from exc


@app.get("/api/v1/research/federated-search")
async def federated_search(
    query: str = Query(..., min_length=2),
    limit: int = Query(default=10, ge=1, le=25),
) -> dict[str, Any]:
    """Run a live parallel evidence search across major public biomedical sources."""
    async def pubmed_task() -> dict[str, Any]:
        result = await asyncio.to_thread(pubmed.search, query, limit)
        if result.get("pmids"):
            summaries = await asyncio.to_thread(pubmed.summaries, result["pmids"])
            result["articles"] = summaries.get("articles", [])
        return result

    tasks = {
        "pubmed": pubmed_task(),
        "europe_pmc": europepmc.search(query, limit),
        "clinical_trials": trials.search(query, limit),
        "openfda_labels": openfda.drug_labels(query, limit),
        "cdc": cdc.search_indicators(query, limit),
        "openneuro": openneuro.search_datasets(query, limit),
    }
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    data: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for name, result in zip(tasks, results):
        if isinstance(result, Exception):
            errors[name] = str(result)
        else:
            data[name] = result
    return research_envelope(
        {"query": query, "results": data, "upstream_errors": errors},
        "TMRDS Federated Public Biomedical Research Gateway",
    )
