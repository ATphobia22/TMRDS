"""Governed ingestion primitives connecting live source records to the evidence graph."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from engines.biomedical_canonicalization import NORMALIZATION_VERSION, canonicalize_record
from engines.biomedical_evidence_models import (
    CanonicalEntity,
    Directness,
    EvidenceAssertion,
    EvidenceType,
    IngestionObservation,
    ReplicationState,
)
from engines.evidence_graph_repository import EvidenceGraphRepository

ADAPTER_VERSION = "1.0.0"


def payload_hash(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class GovernedEvidenceIngestion:
    def __init__(self, repository: EvidenceGraphRepository) -> None:
        self.repository = repository

    async def ingest_observation(
        self,
        *,
        source_id: str,
        source_record_id: str,
        payload: Any,
        request_parameters: dict[str, Any] | None = None,
        source_version: str | None = None,
    ) -> IngestionObservation:
        observation = IngestionObservation(
            source_id=source_id,
            source_record_id=source_record_id,
            retrieved_at=datetime.now(timezone.utc),
            source_version=source_version,
            request_parameters=request_parameters or {},
            raw_payload_hash=payload_hash(payload),
            adapter_version=ADAPTER_VERSION,
            normalization_version=NORMALIZATION_VERSION,
        )
        await self.repository.record_observation(observation.model_dump())
        return observation

    async def normalize_entity(
        self,
        *,
        source_id: str,
        entity_type,
        label: str,
        identifiers: list[tuple[str, str]],
        synonyms: list[str] | None = None,
        properties: dict[str, Any] | None = None,
    ) -> CanonicalEntity:
        entity = canonicalize_record(
            entity_type=entity_type,
            label=label,
            identifiers=identifiers,
            synonyms=synonyms,
            properties=properties,
            source_ids=[source_id],
        )
        await self.repository.upsert_entity(entity)
        return entity

    async def assert_relation(
        self,
        *,
        subject: CanonicalEntity,
        predicate: str,
        object_entity: CanonicalEntity,
        source_id: str,
        source_record_id: str,
        evidence_type: EvidenceType,
        evidence_grade: str,
        source_uri: str | None = None,
        published_at: datetime | None = None,
        source_version: str | None = None,
        directness: Directness = Directness.UNKNOWN,
        replication_state: ReplicationState = ReplicationState.UNKNOWN,
        effect_direction: str | None = None,
        effect_measure: float | None = None,
        effect_units: str | None = None,
        population_context: str | None = None,
        methodology: str | None = None,
    ) -> EvidenceAssertion:
        if not source_id or not source_record_id:
            raise ValueError("source provenance is required")
        retrieved_at = datetime.now(timezone.utc)
        material = {
            "subject": subject.entity_id,
            "predicate": predicate,
            "object": object_entity.entity_id,
            "source_id": source_id,
            "source_record_id": source_record_id,
            "source_version": source_version,
            "evidence_type": evidence_type.value,
            "evidence_grade": evidence_grade,
            "directness": directness.value,
            "replication_state": replication_state.value,
            "effect_direction": effect_direction,
            "effect_measure": effect_measure,
            "effect_units": effect_units,
            "population_context": population_context,
            "methodology": methodology,
        }
        content_hash = payload_hash(material)
        assertion_id = "assertion:" + content_hash[:32]
        assertion = EvidenceAssertion(
            assertion_id=assertion_id,
            subject_entity_id=subject.entity_id,
            predicate=predicate,
            object_entity_id=object_entity.entity_id,
            source_id=source_id,
            source_record_id=source_record_id,
            source_uri=source_uri,
            published_at=published_at,
            retrieved_at=retrieved_at,
            source_version=source_version,
            adapter_version=ADAPTER_VERSION,
            normalization_version=NORMALIZATION_VERSION,
            evidence_type=evidence_type,
            evidence_grade=evidence_grade,
            directness=directness,
            replication_state=replication_state,
            effect_direction=effect_direction,
            effect_measure=effect_measure,
            effect_units=effect_units,
            population_context=population_context,
            methodology=methodology,
            content_hash=content_hash,
        )
        await self.repository.create_assertion(assertion)
        return assertion
