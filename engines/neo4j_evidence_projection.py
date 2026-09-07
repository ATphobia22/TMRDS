"""Rebuildable Neo4j projection for the governed TMRDS evidence graph."""
from __future__ import annotations

import os
from typing import Any, Iterable

from neo4j import AsyncGraphDatabase

from engines.biomedical_evidence_models import CanonicalEntity, ConflictGroup, EvidenceAssertion


class Neo4jEvidenceProjection:
    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ) -> None:
        self.uri = uri or os.getenv("TMRDS_NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("TMRDS_NEO4J_USER", "neo4j")
        self.password = password or os.getenv("TMRDS_NEO4J_PASSWORD", "")
        self.driver = AsyncGraphDatabase.driver(self.uri, auth=(self.user, self.password))

    async def close(self) -> None:
        await self.driver.close()

    async def project_entity(self, entity: CanonicalEntity) -> None:
        async with self.driver.session() as session:
            await session.execute_write(self._merge_entity, entity.model_dump(mode="json"))

    async def project_assertion(self, assertion: EvidenceAssertion) -> None:
        async with self.driver.session() as session:
            await session.execute_write(self._merge_assertion, assertion.model_dump(mode="json"))

    async def project_conflict(self, conflict: ConflictGroup) -> None:
        async with self.driver.session() as session:
            await session.execute_write(self._merge_conflict, conflict.model_dump(mode="json"))

    async def rebuild(self, entities: Iterable[CanonicalEntity], assertions: Iterable[EvidenceAssertion], conflicts: Iterable[ConflictGroup]) -> dict[str, int]:
        counts = {"entities": 0, "assertions": 0, "conflicts": 0}
        for entity in entities:
            await self.project_entity(entity)
            counts["entities"] += 1
        for assertion in assertions:
            await self.project_assertion(assertion)
            counts["assertions"] += 1
        for conflict in conflicts:
            await self.project_conflict(conflict)
            counts["conflicts"] += 1
        return counts

    @staticmethod
    async def _merge_entity(tx: Any, entity: dict[str, Any]) -> None:
        await tx.run(
            """MERGE (e:BiomedicalEntity {entity_id: $entity_id})
            SET e.entity_type=$entity_type, e.label=$label, e.normalized_label=$normalized_label,
                e.synonyms=$synonyms, e.properties=$properties, e.updated_at=$updated_at
            WITH e
            UNWIND keys($identifiers) AS namespace
            MERGE (i:Identifier {namespace: namespace, identifier: $identifiers[namespace]})
            MERGE (e)-[:HAS_IDENTIFIER]->(i)""",
            **entity,
        )

    @staticmethod
    async def _merge_assertion(tx: Any, assertion: dict[str, Any]) -> None:
        await tx.run(
            """MATCH (s:BiomedicalEntity {entity_id:$subject_entity_id})
            MATCH (o:BiomedicalEntity {entity_id:$object_entity_id})
            MERGE (s)-[r:EVIDENCE_ASSERTION {assertion_id:$assertion_id}]->(o)
            SET r.predicate=$predicate, r.source_id=$source_id, r.source_record_id=$source_record_id,
                r.source_uri=$source_uri, r.published_at=$published_at, r.retrieved_at=$retrieved_at,
                r.source_version=$source_version, r.evidence_type=$evidence_type,
                r.evidence_grade=$evidence_grade, r.directness=$directness,
                r.replication_state=$replication_state, r.effect_direction=$effect_direction,
                r.effect_measure=$effect_measure, r.effect_units=$effect_units,
                r.population_context=$population_context, r.methodology=$methodology,
                r.content_hash=$content_hash, r.conflict_group_id=$conflict_group_id,
                r.human_review_state=$human_review_state""",
            **assertion,
        )

    @staticmethod
    async def _merge_conflict(tx: Any, conflict: dict[str, Any]) -> None:
        await tx.run(
            """MERGE (c:ConflictGroup {conflict_group_id:$conflict_group_id})
            SET c.conflict_type=$conflict_type, c.state=$state,
                c.detected_at=$detected_at, c.comparison_basis=$comparison_basis
            WITH c
            UNWIND $assertion_ids AS assertion_id
            MATCH ()-[r:EVIDENCE_ASSERTION {assertion_id:assertion_id}]->()
            SET r.conflict_group_id=$conflict_group_id""",
            **conflict,
        )
