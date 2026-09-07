"""PostgreSQL persistence adapter for real-time data-fabric observations."""
from __future__ import annotations

import os
from typing import Iterable

import asyncpg

from engines.realtime_data_fabric import CanonicalObservation, SourceDefinition


class PostgresDataFabricStore:
    """Persist source metadata and append-only observations in PostgreSQL."""

    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or os.getenv("DATABASE_URL")
        if not self.dsn:
            raise RuntimeError("DATABASE_URL is required for durable data-fabric persistence")

    async def _connect(self) -> asyncpg.Connection:
        return await asyncpg.connect(self.dsn)

    async def register_sources(self, sources: Iterable[SourceDefinition]) -> None:
        connection = await self._connect()
        try:
            async with connection.transaction():
                for source in sources:
                    await connection.execute(
                        """
                        INSERT INTO data_fabric_sources
                            (source_id, provider, name, endpoint, format, authority_class,
                             update_frequency, requires_api_key, enabled, default_params)
                        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10::jsonb)
                        ON CONFLICT (source_id) DO UPDATE SET
                            provider=EXCLUDED.provider,
                            name=EXCLUDED.name,
                            endpoint=EXCLUDED.endpoint,
                            format=EXCLUDED.format,
                            authority_class=EXCLUDED.authority_class,
                            update_frequency=EXCLUDED.update_frequency,
                            requires_api_key=EXCLUDED.requires_api_key,
                            enabled=EXCLUDED.enabled,
                            default_params=EXCLUDED.default_params,
                            updated_at=now()
                        """,
                        source.source_id, source.provider, source.name, source.endpoint,
                        source.format, source.authority_class, source.update_frequency,
                        source.requires_api_key, source.enabled,
                        __import__("json").dumps(source.default_params, sort_keys=True),
                    )
                    await connection.execute(
                        "INSERT INTO data_fabric_source_state (source_id) VALUES ($1) ON CONFLICT DO NOTHING",
                        source.source_id,
                    )
        finally:
            await connection.close()

    async def insert_observation(self, observation: CanonicalObservation) -> bool:
        connection = await self._connect()
        try:
            result = await connection.execute(
                """
                INSERT INTO data_fabric_observations
                    (source_id, record_id, observed_at, retrieved_at, payload, payload_hash,
                     source_version, source_uri, etag, last_modified, provenance_status, fabric_version)
                VALUES ($1,$2,$3,$4,$5::jsonb,$6,$7,$8,$9,$10,$11,$12)
                ON CONFLICT (source_id, record_id, payload_hash) DO NOTHING
                """,
                observation.source_id, observation.record_id, observation.observed_at,
                observation.retrieved_at,
                __import__("json").dumps(observation.payload, sort_keys=True),
                observation.payload_hash, observation.source_version, observation.source_uri,
                observation.etag, observation.last_modified, observation.provenance_status,
                observation.fabric_version,
            )
            return result.endswith("1")
        finally:
            await connection.close()
