"""Live NLM Clinical Tables research pipeline."""
from __future__ import annotations

from typing import Any

import httpx


class NLMResearchPipeline:
    """Read-only access to NLM Clinical Tables condition, HPO, gene and RxTerm data."""

    BASE_URL = "https://clinicaltables.nlm.nih.gov/api"

    async def search_conditions(self, terms: str, limit: int = 25) -> Any:
        return await self._search("conditions/v3/search", terms, limit)

    async def search_hpo(self, terms: str, limit: int = 25) -> Any:
        return await self._search("hpo/v3/search", terms, limit)

    async def search_genes(self, terms: str, limit: int = 25) -> Any:
        return await self._search("genes/v4/search", terms, limit)

    async def search_rxterms(self, terms: str, limit: int = 25) -> Any:
        return await self._search("rxterms/v3/search", terms, limit)

    async def _search(self, path: str, terms: str, limit: int) -> Any:
        if not terms.strip():
            raise ValueError("terms must not be empty")
        params = {"terms": terms.strip(), "maxList": max(1, min(limit, 500))}
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            response = await client.get(f"{self.BASE_URL}/{path}", params=params)
            response.raise_for_status()
            return response.json()
