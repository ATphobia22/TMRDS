"""Live Crossref REST pipeline — open DOI metadata, no API key.

Crossref (https://www.crossref.org) holds DOI-centric metadata for 150M+
records: titles, authors, dates, funders, licenses, reference lists, and
citation counts. Open with an identifying User-Agent; the `mailto` parameter
places callers in the polite pool (10 RPS; public pool is 5 RPS).

Honest limitation: abstracts and references are optional deposits — coverage
is uneven across records, and many biomedical records lack them. Crossref is
DOI-centric: items without DOIs (some preprints, grey literature) are
invisible here. Use it as the authority for DOI -> metadata resolution.
"""
from __future__ import annotations

import os
import time
from typing import Any

import httpx


class CrossrefPipeline:
    """Read-only access to the Crossref REST API."""

    BASE_URL = "https://api.crossref.org/works"
    SELECT = "DOI,title,author,published,abstract,URL,is-referenced-by-count,container-title"

    def __init__(
        self,
        mailto: str | None = None,
        timeout: float = 30.0,
        min_interval: float = 0.2,
    ) -> None:
        self.mailto = mailto or os.environ.get("TMRDS_CONTACT_EMAIL", "tmrds@example.org")
        self.timeout = timeout
        self.min_interval = min_interval
        self._last_call = 0.0

    def _throttle(self) -> None:
        wait = self.min_interval - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

    async def search(self, query: str, page_size: int = 20) -> list[dict[str, Any]]:
        """Search works; raises on transport/HTTP errors so callers can isolate failures."""
        if not query.strip():
            raise ValueError("query must not be empty")
        self._throttle()
        params = {
            "query": query.strip(),
            "rows": max(1, min(page_size, 100)),
            "mailto": self.mailto,
            "select": self.SELECT,
        }
        headers = {"User-Agent": f"TMRDS/1.0 (research evidence discovery; mailto:{self.mailto})"}
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, headers=headers) as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
        items = (data.get("message") or {}).get("items")
        if not isinstance(items, list):
            raise ValueError("Crossref returned an unexpected response shape")
        return [self.normalize(w) for w in items if isinstance(w, dict)]

    @staticmethod
    def normalize(work: dict[str, Any]) -> dict[str, Any]:
        """Project one Crossref work into the TMRDS common evidence shape."""
        authors = [
            " ".join(p for p in (a.get("given"), a.get("family")) if p)
            for a in (work.get("author") or [])
            if isinstance(a, dict)
        ]
        authors = [a for a in authors if a]
        titles = work.get("title") or []
        published = None
        for key in ("published", "published-online", "published-print", "created"):
            block = work.get(key) or {}
            parts = block.get("date-parts") or []
            if parts and parts[0]:
                published = "-".join(str(p) for p in parts[0])
                break
        containers = work.get("container-title") or []
        doi = work.get("DOI")
        return {
            "title": titles[0] if titles else None,
            "abstract": work.get("abstract"),
            "authors": authors,
            "published": published,
            "doi": doi,
            "pmid": None,
            "nct_id": None,
            "arxiv_id": None,
            "source_url": work.get("URL") or (f"https://doi.org/{doi}" if doi else None),
            "open_access_url": None,
            "journal": containers[0] if containers else None,
            "cited_by_count": work.get("is-referenced-by-count"),
            "is_preprint": False,
            "raw": work,
        }
