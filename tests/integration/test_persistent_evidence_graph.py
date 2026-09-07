"""Live PostgreSQL/Neo4j integration tests; no mocks."""
from __future__ import annotations

import os

import pytest

from engines.biomedical_canonicalization import canonicalize_record
from engines.biomedical_evidence_models import EntityType
from engines.evidence_graph_repository import EvidenceGraphRepository
from engines.neo4j_evidence_projection import Neo4jEvidenceProjection

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_postgres_evidence_graph_round_trip() -> None:
    dsn = os.environ["TMRDS_DATABASE_URL"]
    repository = EvidenceGraphRepository(dsn)
    await repository.connect()
    try:
        entity = canonicalize_record(EntityType.GENE, "BRCA1", [("HGNC", "1100")], source_ids=["nlm_clinical_tables"])
        await repository.upsert_entity(entity)
        loaded = await repository.get_entity(entity.entity_id)
        assert loaded is not None
        assert loaded["entity_id"] == entity.entity_id
    finally:
        await repository.close()


@pytest.mark.asyncio
async def test_neo4j_credentials_are_live_and_required() -> None:
    projection = Neo4jEvidenceProjection(
        uri=os.environ["TMRDS_NEO4J_URI"],
        user=os.environ["TMRDS_NEO4J_USER"],
        password=os.environ["TMRDS_NEO4J_PASSWORD"],
    )
    try:
        async with projection.driver.session() as session:
            result = await session.run("RETURN 1 AS value")
            record = await result.single()
            assert record["value"] == 1
    finally:
        await projection.close()
