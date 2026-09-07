"""Governance registry for TMRDS biomedical data sources."""
from __future__ import annotations

from engines.biomedical_evidence_models import EntityType, SourceRecord


class EvidenceSourceRegistry:
    def __init__(self) -> None:
        self._sources: dict[str, SourceRecord] = {}

    def register(self, source: SourceRecord) -> SourceRecord:
        existing = self._sources.get(source.source_id)
        if existing is not None and existing != source:
            raise ValueError(f"source_id already registered with different metadata: {source.source_id}")
        self._sources[source.source_id] = source
        return source

    def get(self, source_id: str) -> SourceRecord:
        try:
            return self._sources[source_id]
        except KeyError as exc:
            raise KeyError(f"unknown evidence source: {source_id}") from exc

    def list(self) -> list[SourceRecord]:
        return [self._sources[key] for key in sorted(self._sources)]

    def validate_access(self, source_id: str) -> bool:
        policy = self.get(source_id).access_policy.casefold()
        return policy in {"public", "api_key", "oauth", "credentialed", "licensed", "institutional"}


def default_source_registry() -> EvidenceSourceRegistry:
    registry = EvidenceSourceRegistry()
    public_sources = [
        SourceRecord(source_id="cdc_cdi", provider="CDC", name="CDC Chronic Disease Indicators", endpoint="https://data.cdc.gov/resource/a8ys-9fjs.json", authority_class="government", license="CDC public data", access_policy="public", allowed_use="Public research use subject to CDC dataset terms", update_frequency="source-defined", version_strategy="source-defined", identifier_namespaces=["cdc"], entity_types=[EntityType.DISEASE, EntityType.PHENOTYPE]),
        SourceRecord(source_id="openneuro", provider="OpenNeuro", name="OpenNeuro", endpoint="https://openneuro.org/crg/graphql", authority_class="research_repository", license="dataset-specific", access_policy="public", allowed_use="Dataset-specific terms", identifier_namespaces=["openneuro"], entity_types=[EntityType.IMAGING_DATASET, EntityType.RESEARCH_DATASET]),
        SourceRecord(source_id="clinicaltrials_gov", provider="NIH/NLM", name="ClinicalTrials.gov API v2", endpoint="https://clinicaltrials.gov/api/v2/studies", authority_class="government", license="ClinicalTrials.gov terms", access_policy="public", allowed_use="Public research access", update_frequency="daily", version_strategy="dataTimestamp", identifier_namespaces=["nct"], entity_types=[EntityType.CLINICAL_TRIAL, EntityType.PUBLICATION, EntityType.DISEASE]),
        SourceRecord(source_id="openfda", provider="FDA", name="openFDA", endpoint="https://api.fda.gov", authority_class="regulatory", license="openFDA terms", access_policy="public", allowed_use="Public research access; not a substitute for validated clinical data", update_frequency="endpoint-specific", version_strategy="endpoint-specific", identifier_namespaces=["fda"], entity_types=[EntityType.DRUG, EntityType.ADVERSE_EVENT]),
        SourceRecord(source_id="nlm_clinical_tables", provider="NLM", name="NLM Clinical Tables", endpoint="https://clinicaltables.nlm.nih.gov/api", authority_class="government_curated", license="NLM terms", access_policy="public", allowed_use="Public research access", update_frequency="source-defined", version_strategy="source-defined", identifier_namespaces=["icd", "hpo", "gene", "rxnorm"], entity_types=[EntityType.DISEASE, EntityType.PHENOTYPE, EntityType.GENE, EntityType.DRUG]),
        SourceRecord(source_id="pubmed", provider="NCBI/NLM", name="PubMed E-utilities", endpoint="https://eutils.ncbi.nlm.nih.gov/entrez/eutils", authority_class="government_curated", license="NCBI terms", access_policy="public", allowed_use="Public research access", update_frequency="source-defined", version_strategy="record identifiers", identifier_namespaces=["pmid"], entity_types=[EntityType.PUBLICATION]),
        SourceRecord(source_id="europe_pmc", provider="EMBL-EBI", name="Europe PMC", endpoint="https://www.ebi.ac.uk/europepmc/webservices/rest/search", authority_class="research_repository", license="source-specific", access_policy="public", allowed_use="Public research access subject to source licenses", update_frequency="source-defined", version_strategy="record identifiers", identifier_namespaces=["pmcid", "pmid", "doi"], entity_types=[EntityType.PUBLICATION, EntityType.PREPRINT]),
    ]
    for source in public_sources:
        registry.register(source)
    return registry
