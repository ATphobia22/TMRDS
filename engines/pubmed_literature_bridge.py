"""
PubMed Literature Bridge for TMRDS.
Programmatic access to NCBI PubMed via E-utilities for verifiable medical
journal evidence. Feeds KRAGEN + QuantumRubiksCureEngine treatment search.

API: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
No key: 3 req/s | With NCBI API key: 10 req/s
"""
from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger("TMRDS.PubMed")

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


class PubMedLiteratureBridge:
    """Search and fetch PubMed citations for disease / gene / treatment queries."""

    def __init__(self, api_key: Optional[str] = None, tool: str = "TMRDS", email: Optional[str] = None) -> None:
        self.api_key = api_key
        self.tool = tool
        self.email = email

    def _params(self, extra: Dict[str, Any]) -> str:
        p = {"retmode": "json", "tool": self.tool, **extra}
        if self.api_key:
            p["api_key"] = self.api_key
        if self.email:
            p["email"] = self.email
        return urllib.parse.urlencode(p)

    def search(
        self,
        query: str,
        max_results: int = 20,
        sort: str = "relevance",
    ) -> Dict[str, Any]:
        """ESearch — return PMIDs + count for a clinical/scientific query."""
        if not query or not query.strip():
            raise ValueError("query required")
        url = f"{EUTILS}/esearch.fcgi?{self._params({
            'db': 'pubmed',
            'term': query,
            'retmax': max(1, min(max_results, 100)),
            'sort': sort,
        })}"
        try:
            with urllib.request.urlopen(url, timeout=20) as resp:
                data = json.loads(resp.read().decode())
            result = data.get("esearchresult", {})
            return {
                "query": query,
                "count": int(result.get("count", 0)),
                "pmids": result.get("idlist", []),
                "status": "OK",
                "source": "PubMed E-utilities",
            }
        except Exception as exc:  # noqa: BLE001
            logger.error("PubMed search failed: %s", exc)
            return {
                "query": query,
                "count": 0,
                "pmids": [],
                "status": "ERROR",
                "error": str(exc),
                "fallback": "offline_cache_or_manual",
            }

    def summaries(self, pmids: List[str]) -> Dict[str, Any]:
        """ESummary — title, authors, source, pubdate for PMID list."""
        if not pmids:
            return {"articles": [], "status": "EMPTY"}
        ids = ",".join(pmids[:50])
        url = f"{EUTILS}/esummary.fcgi?{self._params({'db': 'pubmed', 'id': ids})}"
        try:
            with urllib.request.urlopen(url, timeout=25) as resp:
                data = json.loads(resp.read().decode())
            articles = []
            for uid, rec in data.get("result", {}).items():
                if uid == "uids":
                    continue
                articles.append({
                    "pmid": uid,
                    "title": rec.get("title"),
                    "source": rec.get("source"),
                    "pubdate": rec.get("pubdate"),
                    "authors": [a.get("name") for a in rec.get("authors", [])[:8]],
                })
            return {"articles": articles, "status": "OK", "count": len(articles)}
        except Exception as exc:  # noqa: BLE001
            logger.error("PubMed summary failed: %s", exc)
            return {"articles": [], "status": "ERROR", "error": str(exc)}

    def search_treatments(
        self,
        disease: str,
        gene: Optional[str] = None,
        max_results: int = 15,
    ) -> Dict[str, Any]:
        """Targeted query for treatment / therapy evidence."""
        parts = [f"({disease})", "(treatment OR therapy OR drug OR clinical trial)"]
        if gene:
            parts.append(f"({gene})")
        q = " AND ".join(parts)
        search = self.search(q, max_results=max_results)
        if search.get("pmids"):
            sums = self.summaries(search["pmids"])
            search["articles"] = sums.get("articles", [])
        else:
            search["articles"] = []
        search["intent"] = "treatment_evidence"
        return search

    def status(self) -> Dict[str, Any]:
        return {
            "node": "PubMedLiteratureBridge",
            "endpoint": EUTILS,
            "api_key_configured": bool(self.api_key),
            "status": "READY",
        }
