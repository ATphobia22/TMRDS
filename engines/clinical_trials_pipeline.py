"""Live ClinicalTrials.gov API v2 research pipeline."""
from __future__ import annotations

from typing import Any

import httpx


class ClinicalTrialsPipeline:
    """Read-only access to public ClinicalTrials.gov study records."""

    BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
    VERSION_URL = "https://clinicaltrials.gov/api/v2/version"

    async def search(self, query: str, page_size: int = 20) -> dict[str, Any]:
        if not query.strip():
            raise ValueError("query must not be empty")
        params = {"query.term": query.strip(), "pageSize": max(1, min(page_size, 100)), "format": "json"}
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict):
            raise ValueError("ClinicalTrials.gov returned an unexpected response shape")
        return data

    async def version(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(self.VERSION_URL)
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict):
            raise ValueError("ClinicalTrials.gov version endpoint returned an unexpected response shape")
        return data
