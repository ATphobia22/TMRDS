"""Live Reactome pipeline — curated pathways, no API key.

Reactome (https://reactome.org) is a manually curated, peer-reviewed
pathway database (V96, 2026-04-02: 2,870 human pathways). Content Service
REST: https://reactome.org/ContentService/... (verified live 2026-10-18
and 2026-10-23).

Honest limitation: data CC0; pathway illustrations CC BY 4.0. Curated
coverage only — stale between releases; non-human content mostly inferred
orthology. Search matches names/summations; learn the data model before
deep use. No treatment or clinical claims are made or implied.
"""
from __future__ import annotations

import re
import time
from typing import Any
from urllib.parse import quote

import httpx


def _strip_html(text: str | None) -> str | None:
    if not text:
        return None
    return re.sub(r"<[^>]+>", "", text).strip() or None


class ReactomePipeline:
    """Read-only access to the Reactome Content Service."""

    BASE_URL = "https://reactome.org/ContentService"

    def __init__(self, timeout: float = 30.0, min_interval: float = 1.0) -> None:
        # Rate limits UNVERIFIED (none published) — stay modest.
        self.timeout = timeout
        self.min_interval = min_interval
        self._last_call = 0.0

    def _throttle(self) -> None:
        wait = self.min_interval - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

    async def search_pathways(self, query: str, species: str = "Homo sapiens", page_size: int = 10) -> list[dict[str, Any]]:
        """Search pathways/events by keyword; raises for caller isolation."""
        if not query.strip():
            raise ValueError("query must not be empty")
        self._throttle()
        url = f"{self.BASE_URL}/search/query"
        params = {"query": query.strip(), "species": species}
        headers = {"User-Agent": "TMRDS/1.0 (research evidence discovery; mailto:tmrds@example.org)"}
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, headers=headers) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        results = data.get("results")
        if not isinstance(results, list):
            raise ValueError("Reactome returned an unexpected response shape")
        out: list[dict[str, Any]] = []
        for block in results:
            if not isinstance(block, dict):
                continue
            for entry in block.get("entries") or []:
                if isinstance(entry, dict):
                    out.append(self.normalize(entry))
                if len(out) >= max(1, min(page_size, 50)):
                    return out
        return out

    @staticmethod
    def normalize(entry: dict[str, Any]) -> dict[str, Any]:
        """Project one Reactome entry into the TMRDS common evidence shape."""
        st_id = entry.get("stId") or entry.get("id")
        return {
            "title": _strip_html(entry.get("name")),
            "abstract": _strip_html(entry.get("summation")),
            "authors": [],
            "published": None,
            "doi": None,
            "pmid": None,
            "nct_id": None,
            "arxiv_id": None,
            "source_url": f"https://reactome.org/PathwayBrowser/#/{st_id}" if st_id else None,
            "open_access_url": None,
            "journal": "Reactome (curated)",
            "stable_id": st_id,
            "entry_type": entry.get("exactType") or entry.get("type"),
            "is_preprint": False,
            "raw": entry,
        }
