"""Source-specific mappers that turn live upstream records into governed assertions."""
from __future__ import annotations

from typing import Any

from engines.biomedical_canonicalization import canonicalize_record
from engines.biomedical_evidence_models import Directness, EntityType, EvidenceType, ReplicationState
from engines.governed_evidence_ingestion import GovernedEvidenceIngestion, payload_hash


class ClinicalTrialsEvidenceAdapter:
    def __init__(self, ingestion: GovernedEvidenceIngestion) -> None:
        self.ingestion = ingestion

    async def ingest(self, response: dict[str, Any], source_version: str | None = None) -> int:
        created = 0
        for study in response.get("studies", []):
            protocol = study.get("protocolSection", {})
            ident = protocol.get("identificationModule", {})
            nct_id = ident.get("nctId")
            title = ident.get("briefTitle") or ident.get("officialTitle")
            if not nct_id or not title:
                continue
            trial = canonicalize_record(EntityType.CLINICAL_TRIAL, title, [("nct", nct_id)], source_ids=["clinicaltrials_gov"])
            await self.ingestion.repository.upsert_entity(trial)
            await self.ingestion.ingest_observation(source_id="clinicaltrials_gov", source_record_id=nct_id, payload=study, source_version=source_version)
            for condition in protocol.get("conditionsModule", {}).get("conditions", []):
                disease = canonicalize_record(EntityType.DISEASE, condition, [], source_ids=["clinicaltrials_gov"])
                await self.ingestion.repository.upsert_entity(disease)
                await self.ingestion.assert_relation(subject=disease, predicate="investigated_in", object_entity=trial, source_id="clinicaltrials_gov", source_record_id=nct_id, source_version=source_version, evidence_type=EvidenceType.CLINICAL_TRIAL, evidence_grade="source_asserted", directness=Directness.DIRECT_HUMAN, replication_state=ReplicationState.UNKNOWN)
                created += 1
            for intervention in protocol.get("armsInterventionsModule", {}).get("interventions", []):
                name = intervention.get("name")
                if not name:
                    continue
                intervention_type = str(intervention.get("type", "")).upper()
                entity_type = EntityType.DRUG if intervention_type in {"DRUG", "BIOLOGICAL"} else EntityType.COMPOUND
                drug = canonicalize_record(entity_type, name, [], source_ids=["clinicaltrials_gov"], properties={"intervention_type": intervention.get("type"), "description": intervention.get("description")})
                await self.ingestion.repository.upsert_entity(drug)
                await self.ingestion.assert_relation(subject=drug, predicate="investigated_in", object_entity=trial, source_id="clinicaltrials_gov", source_record_id=nct_id, source_version=source_version, evidence_type=EvidenceType.CLINICAL_TRIAL, evidence_grade="source_asserted", directness=Directness.DIRECT_HUMAN, replication_state=ReplicationState.UNKNOWN)
                created += 1
            for reference in protocol.get("referencesModule", {}).get("references", []):
                pmid = str(reference.get("pmid") or "").strip()
                citation = reference.get("citation") or pmid
                if not pmid:
                    continue
                publication = canonicalize_record(EntityType.PUBLICATION, citation, [("pmid", pmid)], source_ids=["clinicaltrials_gov"], properties={"reference_type": reference.get("type")})
                await self.ingestion.repository.upsert_entity(publication)
                await self.ingestion.assert_relation(subject=trial, predicate="reports", object_entity=publication, source_id="clinicaltrials_gov", source_record_id=nct_id, source_version=source_version, evidence_type=EvidenceType.CURATED_DATABASE, evidence_grade="source_asserted", directness=Directness.DIRECT_HUMAN, replication_state=ReplicationState.UNKNOWN)
                created += 1
        return created


class OpenNeuroEvidenceAdapter:
    def __init__(self, ingestion: GovernedEvidenceIngestion) -> None:
        self.ingestion = ingestion

    async def ingest(self, response: dict[str, Any]) -> int:
        created = 0
        for edge in response.get("data", {}).get("datasets", {}).get("edges", []):
            node = edge.get("node", {})
            dataset_id = node.get("id")
            if not dataset_id:
                continue
            description = node.get("latestSnapshot", {}).get("description", {})
            label = description.get("Name") or dataset_id
            entity = canonicalize_record(EntityType.IMAGING_DATASET, label, [("openneuro", dataset_id)], source_ids=["openneuro"], properties={"created": node.get("created"), "authors": description.get("Authors", [])})
            await self.ingestion.repository.upsert_entity(entity)
            await self.ingestion.ingest_observation(source_id="openneuro", source_record_id=dataset_id, payload=node)
            created += 1
        return created


class PublicationEvidenceAdapter:
    """Stores publication identity and source provenance; it does not infer unsupported biomedical relationships."""

    def __init__(self, ingestion: GovernedEvidenceIngestion) -> None:
        self.ingestion = ingestion

    async def ingest_pubmed_result(self, result: dict[str, Any]) -> int:
        created = 0
        for article in result.get("articles", []):
            pmid = str(article.get("uid") or article.get("pmid") or "").strip()
            title = article.get("title") or pmid
            if not pmid:
                continue
            entity = canonicalize_record(EntityType.PUBLICATION, title, [("pmid", pmid)], source_ids=["pubmed"], properties={"journal": article.get("fulljournalname"), "pubdate": article.get("pubdate")})
            await self.ingestion.repository.upsert_entity(entity)
            await self.ingestion.ingest_observation(source_id="pubmed", source_record_id=pmid, payload=article)
            created += 1
        return created


def source_record_hash(record: Any) -> str:
    return payload_hash(record)
