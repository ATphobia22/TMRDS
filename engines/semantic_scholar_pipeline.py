"""Live Semantic Scholar pipeline — open scholarly metadata + citation graph.

Semantic Scholar (https://www.semanticscholar.org/product/api, Allen Institute
for AI) indexes 214M+ papers with citation graphs, TLDRs, and open-access PDF
links. Open without a key (shared pool); an optional free key (emailed on
request, sent as `x-api-key`) moves to a 1 RPS introductory tier.

Honest limitation: 1 RPS introductory keyed tier; commercial-use restrictions
in the S2 license (https://api.semanticscholar.org/license/). TLDRs are triage,
not citable evidence.
"""
from __future__ import annotations

import os
import time
from typing import Any

import httpx


class SemanticScholarPipeline:
    """Read-only access to the Semantic Scholar Graph API."""

    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
    FIELDS = "title,abstract,authors,year,doi,externalIds,url,openAccessPdf,citationCount,venue"

    def __init__(self, api_key: str | None = None, timeout: float = 30.0, min_interval: float = 1.0) -> None:
        self.api_key = api_key or os.environ.get("S2_API_KEY")
        self.timeout = timeout
        self.min_interval = min_interval
        self._last_call = 0.0

    def _throttle(self) -> None:
        # 1 RPS keyed introductory tier; stay polite on the keyless shared pool too.
        wait = self.min_interval - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

    async def search(self, query: str, page_size: int = 20) -> list[dict[str, Any]]:
        """Search papers; raises on transport/HTTP errors so callers can isolate failures."""
        if not query.strip():
            raise ValueError("query must not be empty")
        self._throttle()
        params = {
            "query": query.strip(),
            "limit": max(1, min(page_size, 100)),
            "fields": self.FIELDS,
        }
        headers = {"User-Agent": "TMRDS/1.0 (research evidence discovery; mailto:tmrds@example.org)"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, headers=headers) as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict) or not isinstance(data.get("data"), list):
            raise ValueError("Semantic Scholar returned an unexpected response shape")
        return [self.normalize(p) for p in data["data"]]

    @staticmethod
    def normalize(paper: dict[str, Any]) -> dict[str, Any]:
        """Project one Semantic Scholar paper into the TMRDS common evidence shape."""
        authors = [
            a.get("name") for a in (paper.get("authors") or [])
            if isinstance(a, dict) and a.get("name")
        ]
        external = paper.get("externalIds") or {}
        doi = external.get("DOI") or paper.get("doi")
        oa = paper.get("openAccessPdf") or {}
        return {
            "title": paper.get("title"),
            "abstract": paper.get("abstract"),
            "authors": authors,
            "published": str(paper.get("year")) if paper.get("year") else None,
            "doi": doi,
            "pmid": external.get("PubMed") or None,
            "nct_id": None,
            "arxiv_id": external.get("ArXiv") or None,
            "source_url": paper.get("url"),
            "open_access_url": oa.get("url"),
            "journal": paper.get("venue"),
            "cited_by_count": paper.get("citationCount"),
            "is_preprint": False,
            "raw": paper,
        }
