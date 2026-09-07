"""Live CDC Chronic Disease Indicators pipeline."""
from __future__ import annotations

from typing import Any

import httpx


class CDCDataPipeline:
    """Read-only client for the CDC Chronic Disease Indicators SODA API."""

    BASE_URL = "https://data.cdc.gov/resource/a8ys-9fjs.json"

    async def fetch_indicators(self, limit: int = 100) -> list[dict[str, Any]]:
        """Retrieve current public CDC chronic-disease indicator records."""
        bounded_limit = max(1, min(limit, 500))
        params = {"$limit": bounded_limit}
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, list):
            raise ValueError("CDC API returned an unexpected response shape")
        return data

    async def search_indicators(self, query: str, limit: int = 100) -> list[dict[str, Any]]:
        """Search CDC indicator records using SODA full-text query."""
        if not query.strip():
            raise ValueError("query must not be empty")
        params = {"$q": query.strip(), "$limit": max(1, min(limit, 500))}
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, list):
            raise ValueError("CDC API returned an unexpected response shape")
        return data
