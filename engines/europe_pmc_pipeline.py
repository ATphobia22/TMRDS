"""Live Europe PMC literature pipeline."""
from __future__ import annotations

from typing import Any

import httpx


class EuropePMCPipeline:
    """Read-only access to Europe PMC biomedical literature metadata."""

    BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

    async def search(self, query: str, page_size: int = 20) -> dict[str, Any]:
        if not query.strip():
            raise ValueError("query must not be empty")
        params = {
            "query": query.strip(),
            "format": "json",
            "pageSize": max(1, min(page_size, 100)),
            "resultType": "core",
        }
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Europe PMC returned an unexpected response shape")
        return data
