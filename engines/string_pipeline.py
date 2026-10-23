"""Live STRING pipeline — protein functional associations, no API key.

STRING (https://string-db.org) scores functional associations between
proteins (experimental, computational, text-mined) with per-channel
confidence scores. REST: https://string-db.org/api/{json}/... (verified
live 2026-10-18 and 2026-10-23).

Honest limitation: CC BY 4.0 — attribution required, commercial use
allowed. Courtesy guideline: ~1 second between calls; per-call protein
limits apply (bulk belongs on the downloads). Common names must be
resolved to STRING IDs first (ambiguity); scores are association
confidences, not clinical assertions.
"""
from __future__ import annotations

import time
from typing import Any
from urllib.parse import quote

import httpx


class StringPipeline:
    """Read-only access to the STRING protein-association API."""

    BASE_URL = "https://string-db.org/api/json"

    def __init__(self, timeout: float = 30.0, min_interval: float = 1.0, taxon: int = 9606) -> None:
        self.timeout = timeout
        self.min_interval = min_interval
        self.taxon = taxon
        self._last_call = 0.0

    def _throttle(self) -> None:
        # Courtesy ~1 call/second guideline.
        wait = self.min_interval - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

    async def _get(self, method: str, params: dict[str, Any]) -> Any:
        self._throttle()
        headers = {"User-Agent": "TMRDS/1.0 (research evidence discovery; mailto:tmrds@example.org)"}
        url = f"{self.BASE_URL}/{method}"
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, headers=headers) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    async def resolve(self, name: str) -> dict[str, Any] | None:
        """Resolve a protein name to its STRING ID; raises for caller isolation."""
        if not name.strip():
            raise ValueError("name must not be empty")
        data = await self._get(
            "get_string_ids",
            {"identifiers": name.strip(), "species": self.taxon, "limit": 1,
             "caller_identity": "TMRDS"},
        )
        if not isinstance(data, list) or not data:
            return None
        hit = data[0]
        return hit if isinstance(hit, dict) else None

    async def interactions(self, name: str, limit: int = 10, required_score: int = 400) -> list[dict[str, Any]]:
        """Top interaction partners for a protein; raises for caller isolation."""
        resolved = await self.resolve(name)
        if resolved is None:
            return []
        data = await self._get(
            "network",
            {
                "identifiers": resolved.get("stringId") or name.strip(),
                "species": self.taxon,
                "required_score": required_score,
                "limit": max(1, min(limit, 50)),
                "caller_identity": "TMRDS",
            },
        )
        if not isinstance(data, list):
            raise ValueError("STRING returned an unexpected response shape")
        return [self.normalize(e) for e in data if isinstance(e, dict)]

    @staticmethod
    def normalize(edge: dict[str, Any]) -> dict[str, Any]:
        """Project one STRING interaction into the TMRDS common evidence shape."""
        a = edge.get("preferredName_A")
        b = edge.get("preferredName_B")
        return {
            "title": f"{a} — {b} functional association" if a and b else None,
            "abstract": None,
            "authors": [],
            "published": None,
            "doi": None,
            "pmid": None,
            "nct_id": None,
            "arxiv_id": None,
            "source_url": "https://string-db.org/",
            "open_access_url": None,
            "journal": None,
            "protein_a": a,
            "protein_b": b,
            "string_id_a": edge.get("stringId_A"),
            "string_id_b": edge.get("stringId_B"),
            "association_score": edge.get("score"),
            "is_preprint": False,
            "raw": edge,
        }
