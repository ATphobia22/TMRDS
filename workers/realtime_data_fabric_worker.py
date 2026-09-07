"""Continuous real-world source synchronization worker for TMRDS."""
from __future__ import annotations

import asyncio
import logging
import os

from engines.realtime_data_fabric import build_default_fabric
from engines.realtime_data_fabric_store import PostgresDataFabricStore

LOGGER = logging.getLogger("tmrds.data_fabric")


async def sync_once() -> None:
    fabric = build_default_fabric()
    store = PostgresDataFabricStore()
    await store.register_sources(fabric.sources())

    for source in fabric.sources():
        try:
            result = await fabric.fetch(source.source_id)
            if result.get("status") != "fetched":
                continue
            payload = result["data"]
            observation = fabric.ingest_payload(
                source.source_id,
                record_id=result["payload_hash"],
                payload=payload,
                observed_at=fabric.state(source.source_id).last_success_at,
                source_version=result.get("etag") or result.get("last_modified"),
                source_uri=source.endpoint,
                etag=result.get("etag"),
                last_modified=result.get("last_modified"),
            )
            if observation.accepted:
                stored = next(item for item in fabric.observations() if item.payload_hash == observation.payload_hash)
                await store.insert_observation(stored)
        except Exception as exc:
            LOGGER.exception("data-fabric source sync failed source_id=%s error=%s", source.source_id, str(exc)[:256])


async def run_forever() -> None:
    interval = max(10, int(os.getenv("TMRDS_DATA_FABRIC_INTERVAL_SECONDS", "60")))
    while True:
        await sync_once()
        await asyncio.sleep(interval)


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    asyncio.run(run_forever())
