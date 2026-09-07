"""Async PostgreSQL repository for governed TMRDS biomedical evidence."""
from __future__ import annotations

import json
import os
from typing import Any

import asyncpg

from engines.biomedical_evidence_models import CanonicalEntity, ConflictGroup, EvidenceAssertion, EvidenceAssessment, SourceRecord


class EvidenceGraphRepository:
    """Transactional persistence boundary; PostgreSQL is the evidence authority."""

    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or os.getenv("TMRDS_DATABASE_URL", "postgresql://tmrds:tmrds@localhost:5432/tmrds")
        self.pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        if self.pool is None:
            self.pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=10, command_timeout=30)

    async def close(self) -> None:
        if self.pool is not None:
            await self.pool.close()
            self.pool = None

    async def _pool(self) -> asyncpg.Pool:
        await self.connect()
        assert self.pool is not None
        return self.pool

    async def upsert_source(self, source: SourceRecord) -> SourceRecord:
        pool = await self._pool()
        async with pool.acquire() as conn:
            await conn.execute("""INSERT INTO evidence_sources
                (source_id, provider, name, endpoint, protocol, authority_class, license, access_policy,
                 allowed_use, update_frequency, version_strategy, schema_version, identifier_namespaces, entity_types, updated_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13::jsonb,$14::jsonb,now())
                ON CONFLICT (source_id) DO UPDATE SET provider=EXCLUDED.provider, name=EXCLUDED.name,
                endpoint=EXCLUDED.endpoint, protocol=EXCLUDED.protocol, authority_class=EXCLUDED.authority_class,
                license=EXCLUDED.license, access_policy=EXCLUDED.access_policy, allowed_use=EXCLUDED.allowed_use,
                update_frequency=EXCLUDED.update_frequency, version_strategy=EXCLUDED.version_strategy,
                schema_version=EXCLUDED.schema_version, identifier_namespaces=EXCLUDED.identifier_namespaces,
                entity_types=EXCLUDED.entity_types, updated_at=now()""",
                source.source_id, source.provider, source.name, source.endpoint, source.protocol,
                source.authority_class, source.license, source.access_policy, source.allowed_use,
                source.update_frequency, source.version_strategy, source.schema_version,
                json.dumps(source.identifier_namespaces), json.dumps([x.value for x in source.entity_types]))
        return source

    async def record_observation(self, observation: dict[str, Any]) -> int:
        pool = await self._pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""INSERT INTO evidence_observations
                (source_id, source_record_id, retrieved_at, source_version, request_parameters, raw_payload_hash, adapter_version, normalization_version)
                VALUES ($1,$2,$3,$4,$5::jsonb,$6,$7,$8)
                ON CONFLICT (source_id, source_record_id, raw_payload_hash) DO UPDATE SET retrieved_at=EXCLUDED.retrieved_at
                RETURNING observation_id""",
                observation["source_id"], observation["source_record_id"], observation["retrieved_at"],
                observation.get("source_version"), json.dumps(observation.get("request_parameters", {})),
                observation["raw_payload_hash"], observation["adapter_version"], observation["normalization_version"])
        return int(row["observation_id"])

    async def upsert_entity(self, entity: CanonicalEntity) -> CanonicalEntity:
        pool = await self._pool()
        async with pool.acquire() as conn, conn.transaction():
            await conn.execute("""INSERT INTO canonical_entities
                (entity_id, entity_type, label, normalized_label, synonyms, properties, created_at, updated_at)
                VALUES ($1,$2,$3,$4,$5::jsonb,$6::jsonb,$7,$8)
                ON CONFLICT (entity_id) DO UPDATE SET label=EXCLUDED.label, normalized_label=EXCLUDED.normalized_label,
                synonyms=EXCLUDED.synonyms, properties=EXCLUDED.properties, updated_at=EXCLUDED.updated_at""",
                entity.entity_id, entity.entity_type.value, entity.label, entity.normalized_label,
                json.dumps(entity.synonyms), json.dumps(entity.properties), entity.created_at, entity.updated_at)
            for namespace, identifier in entity.identifiers.items():
                await conn.execute("INSERT INTO entity_identifiers(entity_id, namespace, identifier) VALUES ($1,$2,$3) ON CONFLICT DO NOTHING", entity.entity_id, namespace, identifier)
            for source_id in entity.source_ids:
                await conn.execute("INSERT INTO entity_sources(entity_id, source_id) VALUES ($1,$2) ON CONFLICT DO NOTHING", entity.entity_id, source_id)
        return entity

    async def create_assertion(self, assertion: EvidenceAssertion) -> bool:
        pool = await self._pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""INSERT INTO evidence_assertions
                (assertion_id, subject_entity_id, predicate, object_entity_id, source_id, source_record_id,
                 source_uri, published_at, retrieved_at, source_version, adapter_version, normalization_version,
                 evidence_type, evidence_grade, directness, replication_state, effect_direction, effect_measure,
                 effect_units, population_context, methodology, content_hash, supersedes_assertion_id, conflict_group_id, human_review_state)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,$23,$24,$25)
                ON CONFLICT (assertion_id) DO NOTHING RETURNING assertion_id""",
                assertion.assertion_id, assertion.subject_entity_id, assertion.predicate, assertion.object_entity_id,
                assertion.source_id, assertion.source_record_id, assertion.source_uri, assertion.published_at,
                assertion.retrieved_at, assertion.source_version, assertion.adapter_version, assertion.normalization_version,
                assertion.evidence_type.value, assertion.evidence_grade, assertion.directness.value,
                assertion.replication_state.value, assertion.effect_direction, assertion.effect_measure,
                assertion.effect_units, assertion.population_context, assertion.methodology, assertion.content_hash,
                assertion.supersedes_assertion_id, assertion.conflict_group_id, assertion.human_review_state.value)
        return row is not None

    async def create_assessment(self, assessment: EvidenceAssessment) -> None:
        pool = await self._pool()
        async with pool.acquire() as conn:
            await conn.execute("""INSERT INTO evidence_assessments
                (assertion_id, source_authority, evidence_type, directness, replication_state, methodological_quality,
                 recency_class, graph_confidence, reviewer_id, assessed_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)""",
                assessment.assertion_id, assessment.source_authority, assessment.evidence_type.value,
                assessment.directness.value, assessment.replication_state.value, assessment.methodological_quality,
                assessment.recency_class, assessment.graph_confidence, assessment.reviewer_id, assessment.assessed_at)

    async def create_conflict_group(self, conflict: ConflictGroup) -> None:
        pool = await self._pool()
        async with pool.acquire() as conn, conn.transaction():
            await conn.execute("""INSERT INTO conflict_groups
                (conflict_group_id, conflict_type, affected_entity_ids, detected_at, comparison_basis, state, resolution_provenance)
                VALUES ($1,$2,$3::jsonb,$4,$5,$6,$7)
                ON CONFLICT (conflict_group_id) DO UPDATE SET state=EXCLUDED.state, resolution_provenance=EXCLUDED.resolution_provenance""",
                conflict.conflict_group_id, conflict.conflict_type.value, json.dumps(conflict.affected_entity_ids),
                conflict.detected_at, conflict.comparison_basis, conflict.state.value, conflict.resolution_provenance)
            for assertion_id in conflict.assertion_ids:
                await conn.execute("INSERT INTO conflict_members(conflict_group_id, assertion_id) VALUES ($1,$2) ON CONFLICT DO NOTHING", conflict.conflict_group_id, assertion_id)

    async def get_entity(self, entity_id: str) -> dict[str, Any] | None:
        pool = await self._pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM canonical_entities WHERE entity_id=$1", entity_id)
            if row is None:
                return None
            identifiers = await conn.fetch("SELECT namespace, identifier FROM entity_identifiers WHERE entity_id=$1", entity_id)
        result = dict(row)
        result["identifiers"] = {r["namespace"]: r["identifier"] for r in identifiers}
        return result

    async def get_assertions_for_entity(self, entity_id: str, limit: int = 100) -> list[dict[str, Any]]:
        pool = await self._pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM evidence_assertions WHERE subject_entity_id=$1 OR object_entity_id=$1 ORDER BY retrieved_at DESC LIMIT $2", entity_id, max(1, min(limit, 500)))
        return [dict(row) for row in rows]

    async def get_assertion(self, assertion_id: str) -> dict[str, Any] | None:
        pool = await self._pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM evidence_assertions WHERE assertion_id=$1", assertion_id)
        return dict(row) if row else None

    async def list_sources(self) -> list[dict[str, Any]]:
        pool = await self._pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM evidence_sources ORDER BY source_id")
        return [dict(row) for row in rows]

    async def list_conflicts(self, limit: int = 100) -> list[dict[str, Any]]:
        pool = await self._pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM conflict_groups ORDER BY detected_at DESC LIMIT $1", max(1, min(limit, 500)))
            result = []
            for row in rows:
                members = await conn.fetch("SELECT assertion_id FROM conflict_members WHERE conflict_group_id=$1", row["conflict_group_id"])
                item = dict(row)
                item["assertion_ids"] = [m["assertion_id"] for m in members]
                result.append(item)
            return result

    async def ingestion_status(self) -> list[dict[str, Any]]:
        pool = await self._pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT source_id, max(retrieved_at) AS last_retrieved, count(*) AS observations FROM evidence_observations GROUP BY source_id ORDER BY source_id")
        return [dict(row) for row in rows]
