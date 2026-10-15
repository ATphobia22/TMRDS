"""Live arXiv pipeline — open preprint metadata, no API key required.

Uses the arXiv export API (https://export.arxiv.org/api/query), which returns
Atom XML. No authentication. Subject to arXiv's usage terms: be polite,
cache aggressively, and never hammer the endpoint.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET

import httpx

ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"


class ArxivPipeline:
    """Read-only access to arXiv preprint metadata."""

    BASE_URL = "https://export.arxiv.org/api/query"

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout

    async def search(self, query: str, page_size: int = 20) -> list[dict[str, Any]]:
        """Search arXiv; raises on transport/HTTP/parse errors for caller isolation."""
        if not query.strip():
            raise ValueError("query must not be empty")
        params = {
            "search_query": f"all:{query.strip()}",
            "start": 0,
            "max_results": max(1, min(page_size, 100)),
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
        headers = {"User-Agent": "TMRDS/1.0 (research evidence discovery; mailto:tmrds@example.org)"}
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, headers=headers) as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            text = response.text
        return [self.normalize(e) for e in self._parse(text)]

    @staticmethod
    def _parse(xml_text: str) -> list[ET.Element]:
        root = ET.fromstring(xml_text)
        return root.findall(f"{ATOM_NS}entry")

    @staticmethod
    def normalize(entry: ET.Element) -> dict[str, Any]:
        def text(tag: str) -> str | None:
            el = entry.find(f"{ATOM_NS}{tag}")
            return el.text.strip() if el is not None and el.text else None

        arxiv_id = text("id") or ""
        arxiv_id = arxiv_id.rsplit("/abs/", 1)[-1] if "/abs/" in arxiv_id else arxiv_id
        authors = [
            (a.find(f"{ATOM_NS}name").text.strip() if a.find(f"{ATOM_NS}name") is not None and a.find(f"{ATOM_NS}name").text else None)
            for a in entry.findall(f"{ATOM_NS}author")
        ]
        authors = [a for a in authors if a]
        doi = None
        for link in entry.findall(f"{ATOM_NS}link"):
            if link.get("title") == "doi":
                doi = (link.get("href") or "").replace("https://doi.org/", "").replace("http://dx.doi.org/", "") or None
        categories = [c.get("term") for c in entry.findall(f"{ARXIV_NS}primary_category")]
        return {
            "title": (text("title") or "").replace("\n", " ").strip(),
            "abstract": (text("summary") or "").replace("\n", " ").strip() or None,
            "authors": authors,
            "published": text("published"),
            "doi": doi,
            "pmid": None,
            "nct_id": None,
            "arxiv_id": arxiv_id or None,
            "source_url": text("id"),
            "open_access_url": text("id"),
            "journal": None,
            "categories": [c for c in categories if c],
            "is_preprint": True,
        }
