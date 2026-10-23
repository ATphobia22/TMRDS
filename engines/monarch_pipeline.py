"""Live Monarch Initiative pipeline — phenotype/disease knowledge graph, no API key.

Monarch (https://monarchinitiative.org) is a cross-species knowledge graph
(genes, variants, diseases, phenotypes; HPO/Mondo/Phenio ontologies). REST
v3 API: https://api.monarchinitiative.org/v3/api/... (verified live
2026-10-18 and 2026-10-23; schema pinned to v3).

Honest limitation: integrated-KG license is mixed/inconsistent across
upstream sources — treat bulk redistribution as UNVERIFIED; cite Monarch
and upstream ontologies. Rate limits UNVERIFIED (none published) — stay
modest. Legacy TRAPI endpoint did not respond in checks; only the v3 REST
API is used here. Phenotype/disease associations are published
annotations, not clinical assertions.
"""
from __future__ import annotations

import time
from typing import Any

import httpx


class MonarchPipeline:
    """Read-only access to the Monarch Initiative v3 API."""

    BASE_URL = "https://api.monarchinitiative.org/v3/api"

    def __init__(self, timeout: float = 30.0, min_interval: float = 1.0) -> None:
        self.timeout = timeout
        self.min_interval = min_interval
        self._last_call = 0.0

    def _throttle(self) -> None:
        wait = self.min_interval - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

    async def search(self, query: str, category: str | None = None, page_size: int = 10) -> list[dict[str, Any]]:
        """Search entities (genes, diseases, phenotypes); raises for caller isolation."""
        if not query.strip():
            raise ValueError("query must not be empty")
        self._throttle()
        params: dict[str, Any] = {
            "q": query.strip(),
            "limit": max(1, min(page_size, 50)),
            "offset": 0,
        }
        if category:
            params["category"] = category
        headers = {"User-Agent": "TMRDS/1.0 (research evidence discovery; mailto:tmrds@example.org)"}
        url = f"{self.BASE_URL}/search"
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, headers=headers) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        items = data.get("items")
        if not isinstance(items, list):
            raise ValueError("Monarch returned an unexpected response shape")
        return [self.normalize(e) for e in items if isinstance(e, dict)]

    async def entity(self, curie: str) -> dict[str, Any] | None:
        """Fetch one entity by CURIE; raises for caller isolation; None on 404."""
        if not curie.strip():
            raise ValueError("curie must not be empty")
        self._throttle()
        headers = {"User-Agent": "TMRDS/1.0 (research evidence discovery; mailto:tmrds@example.org)"}
        url = f"{self.BASE_URL}/entity/{curie.strip()}"
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, headers=headers) as client:
            response = await client.get(url)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Monarch returned an unexpected response shape")
        return self.normalize(data)

    @staticmethod
    def normalize(entity: dict[str, Any]) -> dict[str, Any]:
        """Project one Monarch entity into the TMRDS common evidence shape."""
        curie = entity.get("id")
        return {
            "title": entity.get("name"),
            "abstract": entity.get("description"),
            "authors": [],
            "published": None,
            "doi": None,
            "pmid": None,
            "nct_id": None,
            "arxiv_id": None,
            "source_url": f"https://monarchinitiative.org/{curie}" if curie else None,
            "open_access_url": None,
            "journal": "Monarch Initiative (v3)",
            "curie": curie,
            "category": entity.get("category"),
            "synonyms": entity.get("synonym") or [],
            "xrefs": entity.get("xref") or [],
            "is_preprint": False,
            "raw": entity,
        }
