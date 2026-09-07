"""Live openFDA public drug evidence pipeline."""
from __future__ import annotations

from typing import Any

import httpx


class OpenFDAPipeline:
    """Read-only access to public FDA drug labeling and safety data."""

    BASE_URL = "https://api.fda.gov"

    async def drug_labels(self, query: str | None = None, limit: int = 20) -> dict[str, Any]:
        return await self._get("/drug/label.json", query=query, limit=limit)

    async def adverse_events(self, query: str | None = None, limit: int = 20) -> dict[str, Any]:
        return await self._get("/drug/event.json", query=query, limit=limit)

    async def drug_shortages(self, query: str | None = None, limit: int = 20) -> dict[str, Any]:
        return await self._get("/drug/drugshortages.json", query=query, limit=limit)

    async def _get(self, path: str, query: str | None, limit: int) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": max(1, min(limit, 100))}
        if query and query.strip():
            params["search"] = query.strip()
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(f"{self.BASE_URL}{path}", params=params)
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict):
            raise ValueError("openFDA returned an unexpected response shape")
        return data
