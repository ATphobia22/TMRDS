"""On-demand live ingestion service for the governed evidence graph."""
from __future__ import annotations

from typing import Any

from engines.cdc_data_pipeline import CDCDataPipeline
from engines.clinical_trials_pipeline import ClinicalTrialsPipeline
from engines.europe_pmc_pipeline import EuropePMCPipeline
from engines.evidence_graph_repository import EvidenceGraphRepository
from engines.evidence_source_registry import default_source_registry
from engines.governed_evidence_ingestion import GovernedEvidenceIngestion
from engines.openfda_pipeline import OpenFDAPipeline
from engines.openneuro_pipeline import OpenNeuroPipeline
from engines.source_ingestion_adapters import ClinicalTrialsEvidenceAdapter, OpenNeuroEvidenceAdapter


class LiveEvidenceIngestionService:
    def __init__(self, repository: EvidenceGraphRepository | None = None) -> None:
        self.repository = repository or EvidenceGraphRepository()
        self.ingestion = GovernedEvidenceIngestion(self.repository)
        self.registry = default_source_registry()
        self.trials = ClinicalTrialsPipeline()
        self.openneuro = OpenNeuroPipeline()
        self.cdc = CDCDataPipeline()
        self.openfda = OpenFDAPipeline()
        self.europepmc = EuropePMCPipeline()

    async def ingest_trials(self, query: str, limit: int = 10) -> dict[str, Any]:
        source = self.registry.get("clinicaltrials_gov")
        await self.repository.upsert_source(source)
        version = await self.trials.version()
        source_version = str(version.get("dataTimestamp") or version.get("apiVersion") or "") or None
        response = await self.trials.search(query, limit)
        created = await ClinicalTrialsEvidenceAdapter(self.ingestion).ingest(response, source_version)
        return {"source_id": source.source_id, "query": query, "source_version": source_version, "records_seen": len(response.get("studies", [])), "assertions_created": created}

    async def ingest_openneuro(self, query: str = "MRI", limit: int = 10) -> dict[str, Any]:
        source = self.registry.get("openneuro")
        await self.repository.upsert_source(source)
        response = await self.openneuro.search_datasets(query, limit)
        created = await OpenNeuroEvidenceAdapter(self.ingestion).ingest(response)
        return {"source_id": source.source_id, "query": query, "records_seen": len(response.get("data", {}).get("datasets", {}).get("edges", [])), "entities_created": created}
