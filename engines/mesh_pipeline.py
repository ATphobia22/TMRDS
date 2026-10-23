"""Live MeSH pipeline — NLM controlled vocabulary lookup, no API key.

MeSH (Medical Subject Headings, https://id.nlm.nih.gov/mesh/) is NLM's
biomedical controlled vocabulary. Verified live endpoints (2026-10-23):
- lookup: https://id.nlm.nih.gov/mesh/lookup/descriptor?label=...&match=exact
- descriptor JSON: https://id.nlm.nih.gov/mesh/{D-number}.json
(UI: https://meshb.nlm.nih.gov/record/ui?ui={D-number})

Honest limitation: NLM MeSH Terms and Conditions specifics UNVERIFIED;
rate limits UNVERIFIED (none published) — stay modest. MeSH indexing lags
for brand-new PubMed records; the ASCII serialization was discontinued
January 2026 (use JSON/RDF). Powers query expansion (entry terms,
synonyms) and hierarchical topic scoping — a terminology bridge, not an
evidence corpus.
"""
from __future__ import annotations

import time
from typing import Any

import httpx


class MeshPipeline:
    """Read-only access to NLM MeSH descriptor lookup."""

    BASE_URL = "https://id.nlm.nih.gov/mesh"

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

    async def lookup(self, label: str) -> list[dict[str, Any]]:
        """Descriptor lookup by label; raises for caller isolation."""
        if not label.strip():
            raise ValueError("label must not be empty")
        self._throttle()
        url = f"{self.BASE_URL}/lookup/descriptor"
        params = {"label": label.strip(), "match": "exact"}
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, headers=self._headers()) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, list):
            raise ValueError("MeSH lookup returned an unexpected response shape")
        out = []
        for hit in data:
            if not isinstance(hit, dict):
                continue
            resource = hit.get("resource") or ""
            descriptor_id = resource.rsplit("/", 1)[-1] if "/" in resource else None
            detail = await self.descriptor(descriptor_id) if descriptor_id else None
            out.append(self.normalize(hit.get("label"), descriptor_id, detail))
        return out

    async def descriptor(self, descriptor_id: str) -> dict[str, Any] | None:
        """Fetch one descriptor's JSON; raises for caller isolation; None on 404."""
        if not descriptor_id or not descriptor_id.strip():
            raise ValueError("descriptor_id must not be empty")
        self._throttle()
        url = f"{self.BASE_URL}/{descriptor_id.strip()}.json"
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, headers=self._headers()) as client:
            response = await client.get(url)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
        return data if isinstance(data, dict) else None

    @staticmethod
    def normalize(
        label: str | None, descriptor_id: str | None, detail: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Project one MeSH descriptor into the TMRDS common evidence shape."""
        scope_note = None
        tree_numbers: list[str] = []
        if detail:
            scope_note = detail.get("scopeNote")
            tree_numbers = [
                t for t in (detail.get("treeNumber") or []) if isinstance(t, str)
            ]
        return {
            "title": label,
            "abstract": scope_note,
            "authors": [],
            "published": None,
            "doi": None,
            "pmid": None,
            "nct_id": None,
            "arxiv_id": None,
            "source_url": f"https://meshb.nlm.nih.gov/record/ui?ui={descriptor_id}" if descriptor_id else None,
            "open_access_url": None,
            "journal": "MeSH (NLM)",
            "descriptor_id": descriptor_id,
            "tree_numbers": tree_numbers,
            "is_preprint": False,
            "raw": {"label": label, "descriptor_id": descriptor_id, "detail": detail},
        }
