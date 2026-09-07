"""TMRDS real-time public biomedical research and governed evidence gateway.

Public research routes expose live source data. Evidence-graph routes expose only
provenance-bearing governed assertions and remain research-advisory/read-only.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Query

from api.ai_governance_routes import router as ai_governance_router
from api.evidence_retrieval_routes import router as evidence_retrieval_router
from engines.cdc_data_pipeline import CDCDataPipeline
from engines.clinical_trials_pipeline import ClinicalTrialsPipeline
from engines.europe_pmc_pipeline import EuropePMCPipeline
from engines.nlm_research_pipeline import NLMResearchPipeline
from engines.openfda_pipeline import OpenFDAPipeline
from engines.openneuro_pipeline import OpenNeuroPipeline
from engines.pubmed_literature_bridge import PubMedLiteratureBridge
from engines.evidence_graph_repository import EvidenceGraphRepository
from engines.evidence_graph_service import EvidenceGraphService
from engines.evidence_source_registry import default_source_registry

app = FastAPI(title="TMRDS Research Gateway", version="2.2.0-research", description="Live biomedical research gateway and source-governed evidence graph.")

cdc = CDCDataPipeline()
openneuro = OpenNeuroPipeline()
trials = ClinicalTrialsPipeline()
openfda = OpenFDAPipeline()
nlm = NLMResearchPipeline()
europepmc = EuropePMCPipeline()
pubmed = PubMedLiteratureBridge()
evidence_repository = EvidenceGraphRepository()
evidence_service = EvidenceGraphService(evidence_repository)
source_registry = default_source_registry()


def research_envelope(data: Any, source: str) -> dict[str, Any]:
    return {"status": "research-advisory", "human_authority_final": True, "not_samd": True, "read_only": True, "source": source, "retrieved_at": datetime.now(timezone.utc).isoformat(), "data": data}


@app.get("/api/v1/research/health")
async def research_health() -> dict[str, Any]:
    return research_envelope({"cdc": "configured", "openneuro": "configured", "clinicaltrials": "configured", "openfda": "configured", "nlm": "configured", "europepmc": "configured", "pubmed": pubmed.status()}, "TMRDS")


@app.get("/api/v1/research/datasets/cdc")
async def get_cdc_disease_data(limit: int = Query(default=50, ge=1, le=500), query: str | None = Query(default=None)) -> dict[str, Any]:
    try:
        data = await cdc.search_indicators(query, limit) if query else await cdc.fetch_indicators(limit)
        return research_envelope(data, "CDC Chronic Disease Indicators")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"CDC upstream error: {exc}") from exc


@app.get("/api/v1/research/datasets/openneuro")
async def get_openneuro_data(query: str = Query(default="MRI", min_length=1), limit: int = Query(default=10, ge=1, le=50)) -> dict[str, Any]:
    try:
        return research_envelope(await openneuro.search_datasets(query, limit), "OpenNeuro")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OpenNeuro upstream error: {exc}") from exc


@app.get("/api/v1/research/trials")
async def search_trials(query: str = Query(..., min_length=1), limit: int = Query(default=20, ge=1, le=100)) -> dict[str, Any]:
    try:
        return research_envelope(await trials.search(query, limit), "ClinicalTrials.gov API v2")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"ClinicalTrials.gov upstream error: {exc}") from exc


@app.get("/api/v1/research/drugs/labels")
async def search_drug_labels(query: str | None = Query(default=None), limit: int = Query(default=20, ge=1, le=100)) -> dict[str, Any]:
    try:
        return research_envelope(await openfda.drug_labels(query, limit), "openFDA drug labeling")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"openFDA upstream error: {exc}") from exc


@app.get("/api/v1/research/drugs/adverse-events")
async def search_drug_adverse_events(query: str | None = Query(default=None), limit: int = Query(default=20, ge=1, le=100)) -> dict[str, Any]:
    try:
        return research_envelope(await openfda.adverse_events(query, limit), "openFDA drug adverse events")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"openFDA upstream error: {exc}") from exc


@app.get("/api/v1/research/drugs/shortages")
async def search_drug_shortages(query: str | None = Query(default=None), limit: int = Query(default=20, ge=1, le=100)) -> dict[str, Any]:
    try:
        return research_envelope(await openfda.drug_shortages(query, limit), "openFDA drug shortages")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"openFDA upstream error: {exc}") from exc


@app.get("/api/v1/research/nlm/conditions")
async def search_conditions(terms: str = Query(..., min_length=1), limit: int = Query(default=25, ge=1, le=500)) -> dict[str, Any]:
    try:
        return research_envelope(await nlm.search_conditions(terms, limit), "NLM Clinical Tables")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"NLM upstream error: {exc}") from exc


@app.get("/api/v1/research/nlm/hpo")
async def search_hpo(terms: str = Query(..., min_length=1), limit: int = Query(default=25, ge=1, le=500)) -> dict[str, Any]:
    try:
        return research_envelope(await nlm.search_hpo(terms, limit), "NLM Human Phenotype Ontology table")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"NLM upstream error: {exc}") from exc


@app.get("/api/v1/research/nlm/genes")
async def search_genes(terms: str = Query(..., min_length=1), limit: int = Query(default=25, ge=1, le=500)) -> dict[str, Any]:
    try:
        return research_envelope(await nlm.search_genes(terms, limit), "NLM Clinical Tables genes")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"NLM upstream error: {exc}") from exc


@app.get("/api/v1/research/nlm/rxterms")
async def search_rxterms(terms: str = Query(..., min_length=1), limit: int = Query(default=25, ge=1, le=500)) -> dict[str, Any]:
    try:
        return research_envelope(await nlm.search_rxterms(terms, limit), "NLM RxTerms")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"NLM upstream error: {exc}") from exc


@app.get("/api/v1/research/literature/europe-pmc")
async def search_europe_pmc(query: str = Query(..., min_length=1), limit: int = Query(default=20, ge=1, le=100)) -> dict[str, Any]:
    try:
        return research_envelope(await europepmc.search(query, limit), "Europe PMC")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Europe PMC upstream error: {exc}") from exc


@app.get("/api/v1/research/literature/pubmed")
async def search_pubmed(query: str = Query(..., min_length=1), limit: int = Query(default=20, ge=1, le=100)) -> dict[str, Any]:
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
async def federated_search(query: str = Query(..., min_length=2), limit: int = Query(default=10, ge=1, le=25)) -> dict[str, Any]:
    async def pubmed_task() -> dict[str, Any]:
        result = await asyncio.to_thread(pubmed.search, query, limit)
        if result.get("pmids"):
            summaries = await asyncio.to_thread(pubmed.summaries, result["pmids"])
            result["articles"] = summaries.get("articles", [])
        return result
    tasks = {"pubmed": pubmed_task(), "europe_pmc": europepmc.search(query, limit), "clinical_trials": trials.search(query, limit), "openfda_labels": openfda.drug_labels(query, limit), "cdc": cdc.search_indicators(query, limit), "openneuro": openneuro.search_datasets(query, limit)}
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    data, errors = {}, {}
    for name, result in zip(tasks, results):
        if isinstance(result, Exception):
            errors[name] = str(result)
        else:
            data[name] = result
    return research_envelope({"query": query, "results": data, "upstream_errors": errors}, "TMRDS Federated Public Biomedical Research Gateway")


@app.get("/api/v1/evidence/entities/{entity_id}")
async def evidence_entity(entity_id: str) -> dict[str, Any]:
    try:
        result = await evidence_service.entity(entity_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Evidence database unavailable: {exc}") from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Evidence entity not found")
    return research_envelope(result, "TMRDS Governed Evidence Graph")


@app.get("/api/v1/evidence/entities/{entity_id}/assertions")
async def evidence_entity_assertions(entity_id: str, limit: int = Query(default=100, ge=1, le=500)) -> dict[str, Any]:
    try:
        return research_envelope(await evidence_service.assertions(entity_id, limit), "TMRDS Governed Evidence Graph")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Evidence database unavailable: {exc}") from exc


@app.get("/api/v1/evidence/assertions/{assertion_id}")
async def evidence_assertion(assertion_id: str) -> dict[str, Any]:
    try:
        result = await evidence_service.assertion(assertion_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Evidence database unavailable: {exc}") from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Evidence assertion not found")
    return research_envelope(result, "TMRDS Governed Evidence Graph")


@app.get("/api/v1/evidence/path")
async def evidence_path(subject_id: str = Query(..., min_length=3), object_id: str = Query(..., min_length=3), max_hops: int = Query(default=4, ge=1, le=6), predicate: list[str] | None = Query(default=None), source_id: str | None = Query(default=None)) -> dict[str, Any]:
    try:
        result = await evidence_service.path(subject_id, object_id, max_hops, predicate, source_id)
        return research_envelope({"subject_id": subject_id, "object_id": object_id, "paths": result}, "TMRDS Governed Evidence Graph")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Evidence graph unavailable: {exc}") from exc


@app.get("/api/v1/evidence/graph")
async def evidence_graph(entity_id: str = Query(..., min_length=3), limit: int = Query(default=100, ge=1, le=500)) -> dict[str, Any]:
    try:
        entity = await evidence_service.entity(entity_id)
        assertions = await evidence_service.assertions(entity_id, limit)
        return research_envelope({"entity": entity, "assertions": assertions}, "TMRDS Governed Evidence Graph")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Evidence graph unavailable: {exc}") from exc


@app.get("/api/v1/evidence/conflicts")
async def evidence_conflicts(limit: int = Query(default=100, ge=1, le=500)) -> dict[str, Any]:
    try:
        return research_envelope(await evidence_repository.list_conflicts(limit), "TMRDS Evidence Conflict Engine")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Evidence database unavailable: {exc}") from exc


@app.get("/api/v1/evidence/sources")
async def evidence_sources() -> dict[str, Any]:
    try:
        persisted = await evidence_service.sources()
        if not persisted:
            return research_envelope([source.model_dump(mode="json") for source in source_registry.list()], "TMRDS Source Registry")
        return research_envelope(persisted, "TMRDS Source Registry")
    except Exception:
        return research_envelope([source.model_dump(mode="json") for source in source_registry.list()], "TMRDS Source Registry")


@app.get("/api/v1/evidence/sources/{source_id}")
async def evidence_source(source_id: str) -> dict[str, Any]:
    try:
        source = source_registry.get(source_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Evidence source not registered") from exc
    return research_envelope(source.model_dump(mode="json"), "TMRDS Source Registry")


@app.get("/api/v1/evidence/ingestion/status")
async def evidence_ingestion_status() -> dict[str, Any]:
    try:
        return research_envelope(await evidence_service.ingestion_status(), "TMRDS Evidence Ingestion")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Evidence database unavailable: {exc}") from exc


from api.evidence_ingestion_routes import router as evidence_ingestion_router
app.include_router(evidence_ingestion_router)
app.include_router(ai_governance_router)
app.include_router(evidence_retrieval_router)
