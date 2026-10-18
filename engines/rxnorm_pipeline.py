"""Live RxNorm/RxNav pipeline — open drug terminology, no API key.

RxNav (https://rxnav.nlm.nih.gov, NLM) provides drug-name normalization:
names <-> RxCUIs via `approximateTerm` fuzzy search. Open, no key, no UMLS
license needed for RXNORM-via-API. NLM API Terms of Service: 20 requests /
second per IP (this client stays far below that).

CRITICAL: the drug-drug Interaction API (`/REST/interaction/list.json`) has
been DEAD since January 2024 (endpoints return empty responses). This module
is terminology/normalization ONLY — it must never be used to rebuild
interaction checking. Dosage/indication/boxed-warning content lives in
DailyMed SPLs and openFDA, not here.
"""
from __future__ import annotations

import time
from typing import Any

import httpx


class RxNormPipeline:
    """Read-only access to RxNav terminology (approximate term matching)."""

    BASE_URL = "https://rxnav.nlm.nih.gov/REST"

    def __init__(self, timeout: float = 30.0, min_interval: float = 0.1) -> None:
        self.timeout = timeout
        self.min_interval = min_interval
        self._last_call = 0.0

    def _throttle(self) -> None:
        wait = self.min_interval - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

    async def approximate_term(self, term: str, max_entries: int = 10) -> list[dict[str, Any]]:
        """Fuzzy drug-name -> RxCUI candidates; raises on transport/HTTP errors for caller isolation."""
        if not term.strip():
            raise ValueError("term must not be empty")
        self._throttle()
        url = f"{self.BASE_URL}/approximateTerm.json"
        params = {"term": term.strip(), "maxEntries": max(1, min(max_entries, 50))}
        headers = {"User-Agent": "TMRDS/1.0 (research evidence discovery; mailto:tmrds@example.org)"}
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, headers=headers) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        group = data.get("approximateGroup") or {}
        candidates = group.get("candidate") or []
        if not isinstance(candidates, list):
            raise ValueError("RxNav returned an unexpected response shape")
        return [self.normalize(c) for c in candidates if isinstance(c, dict)]

    @staticmethod
    def normalize(candidate: dict[str, Any]) -> dict[str, Any]:
        """Project one RxNav candidate into the TMRDS common evidence shape."""
        rxcui = candidate.get("rxcui")
        return {
            "title": candidate.get("name"),
            "abstract": None,
            "authors": [],
            "published": None,
            "doi": None,
            "pmid": None,
            "nct_id": None,
            "arxiv_id": None,
            "source_url": (
                f"https://mor.nlm.nih.gov/RxNav/search?searchBy=RXCUI&searchTerm={rxcui}"
                if rxcui else None
            ),
            "open_access_url": None,
            "journal": None,
            "rxcui": rxcui,
            "match_score": candidate.get("score"),
            "vocabulary_source": candidate.get("source"),
            "is_preprint": False,
            "raw": candidate,
        }
