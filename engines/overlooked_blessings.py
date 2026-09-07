"""
Overlooked Blessings Protocol for TMRDS.
Programmatic USPTO PatentsView queries for pre-March 2006 filings to surface
expired foundational pathways for zero-cost drug / formulation repurposing research.

API: https://search.patentsview.org (X-Api-Key required for production volume)
Cutoff: patents with filing/priority before 2006-03-01 (20-year term heuristic).

Advisory only — patent legal status must be verified by qualified counsel;
this module does not provide legal advice or freedom-to-operate opinions.
"""
from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger("TMRDS.OverlookedBlessings")

PATENTSVIEW = "https://api.patentsview.org/patents/query"
CUTOFF = "2006-03-01"


class OverlookedBlessings:
    """Search historical USPTO patents for expired foundational technology pathways."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key

    def search(
        self,
        keyword: str,
        max_results: int = 25,
    ) -> Dict[str, Any]:
        """
        Query PatentsView for patents matching keyword with early dates.
        Falls back to structured offline guidance if API unavailable.
        """
        if not keyword or not keyword.strip():
            raise ValueError("keyword required")

        # PatentsView legacy query shape (may require key / endpoint updates)
        query = {
            "_and": [
                {"_text_any": {"patent_abstract": keyword}},
                {"_lt": {"patent_date": CUTOFF}},
            ]
        }
        body = json.dumps({
            "q": query,
            "f": ["patent_number", "patent_title", "patent_date", "patent_abstract"],
            "o": {"per_page": max(1, min(max_results, 50))},
        }).encode()

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "TMRDS-OverlookedBlessings/1.0",
        }
        if self.api_key:
            headers["X-Api-Key"] = self.api_key

        try:
            req = urllib.request.Request(PATENTSVIEW, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
            patents = data.get("patents') or data.get("patents") or []
            if isinstance(patents, str):
                patents = []
            items = []
            for p in patents if isinstance(patents, list) else []:
                items.append({
                    "patent_number": p.get("patent_number"),
                    "title": p.get("patent_title"),
                    "date": p.get("patent_date"),
                    "abstract_excerpt": (p.get("patent_abstract") or "")[:400],
                })
            return {
                "keyword": keyword,
                "cutoff": CUTOFF,
                "count": len(items),
                "patents": items,
                "status": "OK",
                "disclaimer": (
                    "Not legal advice. Verify expiry, terminal disclaimers, and FTO with counsel."
                ),
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("PatentsView query failed: %s", exp if False else exc)
            return {
                "keyword": keyword,
                "cutoff": CUTOFF,
                "count": 0,
                "patents": [],
                "status": "OFFLINE_OR_ERROR",
                "error": str(exc),
                "guidance": (
                    "Configure PatentsView API key; query patents with date < 2006-03-01. "
                    "Examples: nanoparticle stabilization, liposomal delivery, prodrug linkers."
                ),
                "disclaimer": (
                    "Not legal advice. Verify expiry and freedom-to-operate with qualified counsel."
                ),
            }

    def status(self) -> Dict[str, Any]:
        return {
            "node": "OverlookedBlessings",
            "cutoff": CUTOFF,
            "api": PATENTSVIEW,
            "api_key_configured": bool(self.api_key),
            "status": "READY",
        }
