"""Live NCATS Translator identifier-resolution pipelines — open, no API key.

Two confirmed-live services (verified 2026-10-18 and 2026-10-23):
- Node Normalization: https://nodenormalization-sri.renci.org — CURIE in,
  preferred CURIE + equivalent identifiers + Biolink types out.
- Name Resolution: https://name-resolution-sri.renci.org — lexical string
  in, candidate CURIEs out.

Honest limitation: rate limits UNVERIFIED (none published) — stay modest.
Results are identifier mappings, not evidence; federation/probabilistic
reasoning outputs (ARS/ARAs) are NOT queried here and would need human
expert review. Some upstream components carry distinct licenses (mixed).
"""
from __future__ import annotations

import time
from typing import Any

import httpx


class NcatsPipeline:
    """Read-only access to NCATS Node Normalization + Name Resolution."""

    NODE_NORM_URL = "https://nodenormalization-sri.renci.org/1.3/get_normalized_nodes"
    NAME_RES_URL = "https://name-resolution-sri.renci.org/lookup"

    def __init__(self, timeout: float = 30.0, min_interval: float = 1.0) -> None:
        self.timeout = timeout
        self.min_interval = min_interval
        self._last_call = 0.0

    def _throttle(self) -> None:
        wait = self.min_interval - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": "TMRDS/1.0 (research evidence discovery; mailto:tmrds@example.org)"}

    async def normalize_nodes(self, curies: list[str]) -> list[dict[str, Any]]:
        """CURIEs -> preferred CURIE + equivalents; raises for caller isolation."""
        curies = [c.strip() for c in curies if c and c.strip()]
        if not curies:
            raise ValueError("curies must not be empty")
        self._throttle()
        headers = {**self._headers(), "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, headers=headers) as client:
            response = await client.post(self.NODE_NORM_URL, json={"curies": curies[:50]})
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Node Normalization returned an unexpected response shape")
        return [self.normalize_node(curie, node) for curie, node in data.items() if isinstance(node, dict)]

    async def resolve_name(self, text: str, limit: int = 5) -> list[dict[str, Any]]:
        """Lexical string -> candidate CURIEs; raises for caller isolation."""
        if not text.strip():
            raise ValueError("text must not be empty")
        self._throttle()
        params = {"string": text.strip(), "offset": 0, "limit": max(1, min(limit, 20))}
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, headers=self._headers()) as client:
            response = await client.get(self.NAME_RES_URL, params=params)
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, list):
            raise ValueError("Name Resolution returned an unexpected response shape")
        return [self.normalize_resolution(r) for r in data if isinstance(r, dict)]

    @staticmethod
    def normalize_node(curie: str, node: dict[str, Any]) -> dict[str, Any]:
        """Project one normalized node into the TMRDS common evidence shape."""
        preferred = node.get("id") or {}
        equivalents = node.get("equivalent_identifiers") or []
        return {
            "title": f"{preferred.get('label') or curie} ({preferred.get('identifier') or curie})",
            "abstract": None,
            "authors": [],
            "published": None,
            "doi": None,
            "pmid": None,
            "nct_id": None,
            "arxiv_id": None,
            "source_url": None,
            "open_access_url": None,
            "journal": "NCATS Node Normalization",
            "curie": preferred.get("identifier") or curie,
            "label": preferred.get("label"),
            "equivalent_identifiers": [
                e.get("identifier") for e in equivalents
                if isinstance(e, dict) and e.get("identifier")
            ],
            "biolink_types": node.get("type") or [],
            "is_preprint": False,
            "raw": {"input_curie": curie, "node": node},
        }

    @staticmethod
    def normalize_resolution(hit: dict[str, Any]) -> dict[str, Any]:
        """Project one name-resolution hit into the TMRDS common evidence shape."""
        return {
            "title": f"{hit.get('label')} ({hit.get('curie')})" if hit.get("curie") else hit.get("label"),
            "abstract": None,
            "authors": [],
            "published": None,
            "doi": None,
            "pmid": None,
            "nct_id": None,
            "arxiv_id": None,
            "source_url": None,
            "open_access_url": None,
            "journal": "NCATS Name Resolution",
            "curie": hit.get("curie"),
            "label": hit.get("label"),
            "synonyms": hit.get("synonyms") or [],
            "biolink_types": hit.get("types") or [],
            "is_preprint": False,
            "raw": hit,
        }
