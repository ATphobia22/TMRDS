"""Application service for provenance-aware biomedical graph queries."""
from __future__ import annotations

from typing import Any

from engines.evidence_graph_repository import EvidenceGraphRepository


class EvidenceGraphService:
    def __init__(self, repository: EvidenceGraphRepository) -> None:
        self.repository = repository

    async def entity(self, entity_id: str) -> dict[str, Any] | None:
        return await self.repository.get_entity(entity_id)

    async def assertions(self, entity_id: str, limit: int = 100) -> list[dict[str, Any]]:
        return await self.repository.get_assertions_for_entity(entity_id, limit)

    async def assertion(self, assertion_id: str) -> dict[str, Any] | None:
        return await self.repository.get_assertion(assertion_id)

    async def sources(self) -> list[dict[str, Any]]:
        return await self.repository.list_sources()

    async def ingestion_status(self) -> list[dict[str, Any]]:
        return await self.repository.ingestion_status()

    async def path(
        self,
        subject_id: str,
        object_id: str,
        max_hops: int = 4,
        predicates: list[str] | None = None,
        source_id: str | None = None,
    ) -> list[dict[str, Any]]:
        max_hops = max(1, min(max_hops, 6))
        pool = await self.repository._pool()
        predicate_filter = predicates or []
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """WITH RECURSIVE paths AS (
                    SELECT a.object_entity_id AS current_id,
                           ARRAY[a.assertion_id] AS assertion_ids,
                           ARRAY[a.subject_entity_id, a.object_entity_id] AS entity_ids,
                           1 AS hops
                    FROM evidence_assertions a
                    WHERE a.subject_entity_id=$1
                      AND (cardinality($3::text[]) = 0 OR a.predicate = ANY($3::text[]))
                      AND ($4::text IS NULL OR a.source_id=$4)
                    UNION ALL
                    SELECT a.object_entity_id,
                           p.assertion_ids || a.assertion_id,
                           p.entity_ids || a.object_entity_id,
                           p.hops + 1
                    FROM paths p
                    JOIN evidence_assertions a ON a.subject_entity_id=p.current_id
                    WHERE p.hops < $5
                      AND NOT a.object_entity_id = ANY(p.entity_ids)
                      AND (cardinality($3::text[]) = 0 OR a.predicate = ANY($3::text[]))
                      AND ($4::text IS NULL OR a.source_id=$4)
                )
                SELECT assertion_ids, entity_ids, hops FROM paths WHERE current_id=$2
                ORDER BY hops LIMIT 100""",
                subject_id, object_id, predicate_filter, source_id, max_hops,
            )
            output: list[dict[str, Any]] = []
            for row in rows:
                evidence = []
                for assertion_id in row["assertion_ids"]:
                    assertion = await conn.fetchrow("SELECT * FROM evidence_assertions WHERE assertion_id=$1", assertion_id)
                    if assertion:
                        evidence.append(dict(assertion))
                output.append({"entity_ids": row["entity_ids"], "hops": row["hops"], "evidence": evidence})
            return output
