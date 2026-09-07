"""
Overlooked Blessings Protocol for TMRDS.
Programmatic USPTO PatentsView queries for pre-March 2006 filings to surface
expired foundational pathways for zero-cost drug / formulation repurposing research.

API: PatentsView Search Platform (X-Api-Key for production volume)
Cutoff: patents with date before 2006-03-01 (20-year term heuristic).

Advisory only — patent legal status must be verified by qualified counsel;
this module does not provide legal advice or freedom-to-operate opinions.
"""
from __future__ import annotations

import json
import logging
import urllib.request
from typing import Any, Dict, Optional

logger = logging.getLogger("TMRDS.OverlookedBlessings")

PATENTSVIEW = "https://api.patentsview.org/patents/query"
CUTOFF = "2006-03-01"


class OverlookedBlessings:
    """Search historical USPTO patents for expired foundational technology pathways."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key

    def search(self, keyword: str, max_results: int = 25) -> Dict[str, Any]:
        if not keyword or not keyword.strip():
            raise ValueError("keyword required")

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
            patents = data.get("patents") or []
            if not isinstance(patents, list):
                patents = []
            items = []
            for p in patents:
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
            logger.warning("PatentsView query failed: %s", exc)
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
