"""Live bioRxiv/medRxiv pipeline — preprint metadata, no API key.

The bioRxiv API (https://api.biorxiv.org) serves preprint metadata: DOI,
title, authors, date, version, license, category, abstract, and the
published-linkage field. Endpoints verified against the official API docs
2026-10-18 (https://api.biorxiv.org/): details/[server]/[interval]/[cursor]
/[format]; live end-to-end check passed 2026-10-23 (the host was
intermittently unreachable from this network earlier that day, then
responded normally — at runtime any outage surfaces as an honest
per-source warning, never as data.

Honest limitation: metadata-only and browse-by-date/category — there is NO
full-text keyword search, so this client downloads a recent window and
filters titles/abstracts locally. EVERY record is labeled un-peer-reviewed
(is_preprint=True); monitor version/publication status. License is
per-paper (e.g. cc_by_nc); no blanket corpus license.
"""
from __future__ import annotations

import datetime as _dt
import time
from typing import Any

import httpx


class BiorxivPipeline:
    """Read-only access to bioRxiv/medRxiv preprint metadata."""

    BASE_URL = "https://api.biorxiv.org"

    def __init__(self, timeout: float = 45.0, min_interval: float = 1.0) -> None:
        # Rate limits UNVERIFIED (none published) — stay modest.
        self.timeout = timeout
        self.min_interval = min_interval
        self._last_call = 0.0

    def _throttle(self) -> None:
        wait = self.min_interval - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

    async def _details(self, server: str, start: str, end: str, cursor: int = 0) -> dict[str, Any]:
        self._throttle()
        url = f"{self.BASE_URL}/details/{server}/{start}/{end}/{cursor}/json"
        headers = {"User-Agent": "TMRDS/1.0 (research evidence discovery; mailto:tmrds@example.org)"}
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, headers=headers) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict) or "collection" not in data:
            raise ValueError("bioRxiv returned an unexpected response shape")
        return data

    async def search_recent(
        self,
        query: str,
        server: str = "biorxiv",
        days_back: int = 30,
        max_pages: int = 4,
    ) -> list[dict[str, Any]]:
        """Fetch a recent window and filter locally; raises for caller isolation.

        The API has no keyword search, so this is honest local filtering of
        titles + abstracts over the window. Every hit is labeled un-peer-reviewed.
        """
        if not query.strip():
            raise ValueError("query must not be empty")
        if server not in {"biorxiv", "medrxiv"}:
            raise ValueError("server must be 'biorxiv' or 'medrxiv'")
        tokens = [t.lower() for t in query.strip().split() if len(t) > 2]
        if not tokens:
            raise ValueError("query has no usable tokens")
        end = _dt.date.today()
        start = end - _dt.timedelta(days=max(1, days_back))
        out: list[dict[str, Any]] = []
        cursor = 0
        for _ in range(max(1, min(max_pages, 10))):
            data = await self._details(server, start.isoformat(), end.isoformat(), cursor)
            collection = data.get("collection") or []
            if not collection:
                break
            for paper in collection:
                if not isinstance(paper, dict):
                    continue
                haystack = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
                if all(t in haystack for t in tokens):
                    out.append(self.normalize(paper, server))
            cursor += len(collection)
        return out

    @staticmethod
    def normalize(paper: dict[str, Any], server: str = "biorxiv") -> dict[str, Any]:
        """Project one preprint record into the TMRDS common evidence shape."""
        authors = paper.get("authors")
        author_list = [a.strip() for a in authors.split(";")] if isinstance(authors, str) else []
        doi = paper.get("doi")
        return {
            "title": paper.get("title"),
            "abstract": paper.get("abstract"),
            "authors": [a for a in author_list if a],
            "published": paper.get("date"),
            "doi": doi,
            "pmid": None,
            "nct_id": None,
            "arxiv_id": None,
            "source_url": f"https://doi.org/{doi}" if doi else None,
            "open_access_url": None,
            "journal": f"{server} (preprint — NOT peer-reviewed)",
            "preprint_server": server,
            "version": paper.get("version"),
            "license": paper.get("license"),
            "category": paper.get("category"),
            "published_journal": paper.get("published"),
            "is_preprint": True,
            "raw": paper,
        }
