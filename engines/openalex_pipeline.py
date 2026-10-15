"""Live OpenAlex pipeline — open scholarly metadata, no API key required.

OpenAlex (https://openalex.org) indexes journal articles, preprints
(including arXiv, bioRxiv, medRxiv), and conference papers with DOIs,
authorships, and open-access locations. Free without a key; polite usage
identifies itself via User-Agent/mailto.
"""
from __future__ import annotations

from typing import Any

import httpx


class OpenAlexPipeline:
    """Read-only access to OpenAlex works metadata."""

    BASE_URL = "https://api.openalex.org/works"

    def __init__(self, mailto: str = "tmrds@example.org", timeout: float = 30.0) -> None:
        self.mailto = mailto
        self.timeout = timeout

    async def search(self, query: str, page_size: int = 20) -> dict[str, Any]:
        """Search works; raises on transport/HTTP errors so callers can isolate failures."""
        if not query.strip():
            raise ValueError("query must not be empty")
        params = {
            "search": query.strip(),
            "per-page": max(1, min(page_size, 100)),
            "mailto": self.mailto,
        }
        headers = {"User-Agent": f"TMRDS/1.0 (mailto:{self.mailto})"}
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, headers=headers) as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict):
            raise ValueError("OpenAlex returned an unexpected response shape")
        return data

    @staticmethod
    def normalize(work: dict[str, Any]) -> dict[str, Any]:
        """Project one OpenAlex work into the TMRDS common evidence shape."""
        authorships = work.get("authorships") or []
        authors = [
            (a.get("author") or {}).get("display_name")
            for a in authorships
            if isinstance(a, dict)
        ]
        authors = [a for a in authors if a]
        doi = work.get("doi")
        if isinstance(doi, str):
            doi = doi.replace("https://doi.org/", "").strip() or None
        primary = work.get("primary_location") or {}
        source = primary.get("source") or {}
        abstract = work.get("abstract")
        if not abstract:
            inv = work.get("abstract_inverted_index") or {}
            abstract = OpenAlexPipeline._reconstruct_abstract(inv)
        return {
            "title": work.get("display_name"),
            "abstract": abstract,
            "authors": authors,
            "published": work.get("publication_date"),
            "doi": doi,
            "pmid": None,
            "nct_id": None,
            "arxiv_id": None,
            "source_url": work.get("id"),
            "open_access_url": (primary.get("pdf_url") or primary.get("landing_page_url")),
            "journal": source.get("display_name"),
            "cited_by_count": work.get("cited_by_count"),
            "is_preprint": "preprint" in str(work.get("type") or "").lower(),
            "raw": work,
        }

    @staticmethod
    def _reconstruct_abstract(inverted: dict[str, list[int]]) -> str | None:
        try:
            positions: dict[int, str] = {}
            for word, idxs in inverted.items():
                for i in idxs:
                    positions[int(i)] = word
            if not positions:
                return None
            return " ".join(positions[i] for i in sorted(positions))[:4000]
        except Exception:
            return None
