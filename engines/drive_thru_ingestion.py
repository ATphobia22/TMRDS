"""
Drive-Thru Ingestion Network for TMRDS.
Programmatic, browser-free multi-domain evidence intake for drug discovery
and clinical reasoning.

Sources (public APIs):
  - PubMed E-utilities (35M+ citations)
  - arXiv API
  - OpenAlex works API
  - Semantic Scholar Academic Graph
  - ClinicalTrials.gov API v2
  - WHO GHO OData (when reachable)

Evidence Altar: local index metadata (FTS5/Chroma-ready document records).
Does not scrape; uses official APIs only.
"""
from __future__ import annotations

import json
import logging
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger("TMRDS.DriveThru")


class DriveThruIngestion:
    """High-speed multi-domain literature / trial / preprint intake."""

    def __init__(self, email: Optional[str] = None, s2_api_key: Optional[str] = None) -> None:
        self.email = email
        self.s2_api_key = s2_api_key
        self._altar: List[Dict[str, Any]] = []  # Evidence Altar document index

    def _get_json(self, url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 25) -> Dict[str, Any]:
        req = urllib.request.Request(url, headers=headers or {"User-Agent": "TMRDS-DriveThru/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except Exception as exc:  # noqa: BLE001
            logger.warning("GET failed %s: %s", url[:80], exc)
            return {"error": str(exc), "url": url}

    def pubmed(self, query: str, max_results: int = 15) -> Dict[str, Any]:
        from .pubmed_literature_bridge import PubMedLiteratureBridge
        bridge = PubMedLiteratureBridge(email=self.email)
        result = bridge.search_treatments(query, max_results=max_results)
        self._index("pubmed", query, result.get("articles") or [])
        return result

    def arxiv(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        q = urllib.parse.quote(query)
        url = (
            f"http://export.arxiv.org/api/query?search_query=all:{q}"
            f"&start=0&max_results={max(1, min(max_results, 50))}"
        )
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "TMRDS-DriveThru/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            # Minimal Atom parse: collect titles
            titles = []
            for part in raw.split("<entry>")[1:]:
                if "<title>" in part:
                    t = part.split("<title>")[1].split("</title>")[0].strip()
                    titles.append({"title": t, "source": "arXiv"})
            self._index("arxiv", query, titles)
            return {"query": query, "count": len(titles), "items": titles, "status": "OK"}
        except Exception as exc:  # noqa: BLE001
            return {"query": query, "count": 0, "items": [], "status": "ERROR", "error": str(exc)}

    def openalex(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        q = urllib.parse.quote(query)
        url = f"https://api.openalex.org/works?search={q}&per_page={max(1, min(max_results, 25))}"
        data = self._get_json(url)
        if "error" in data and "results" not in data:
            return {"query": query, "status": "ERROR", "error": data.get("error"), "items": []}
        items = []
        for w in data.get("results", []):
            items.append({
                "id": w.get("id"),
                "title": w.get("title"),
                "publication_year": w.get("publication_year"),
                "cited_by_count": w.get("cited_by_count"),
                "doi": (w.get("doi") or ""),
                "source": "OpenAlex",
            })
        self._index("openalex", query, items)
        return {"query": query, "count": len(items), "items": items, "status": "OK"}

    def semantic_scholar(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        q = urllib.parse.quote(query)
        url = (
            f"https://api.semanticscholar.org/graph/v1/paper/search"
            f"?query={q}&limit={max(1, min(max_results, 30))}"
            f"&fields=title,year,citationCount,externalIds"
        )
        headers = {"User-Agent": "TMRDS-DriveThru/1.0"}
        if self.s2_api_key:
            headers["x-api-key"] = self.s2_api_key
        data = self._get_json(url, headers=headers)
        if "error" in data and "data" not in data:
            return {"query": query, "status": "ERROR", "error": data.get("error"), "items": []}
        items = []
        for p in data.get("data", []):
            items.append({
                "paperId": p.get("paperId"),
                "title": p.get("title"),
                "year": p.get("year"),
                "citationCount": p.get("citationCount"),
                "externalIds": p.get("externalIds"),
                "source": "SemanticScholar",
            })
        self._index("semantic_scholar", query, items)
        return {"query": query, "count": len(items), "items": items, "status": "OK"}

    def clinical_trials(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        q = urllib.parse.quote(query)
        url = (
            f"https://clinicaltrials.gov/api/v2/studies"
            f"?query.term={q}&pageSize={max(1, min(max_results, 20))}"
            f"&fields=NCTId,BriefTitle,OverallStatus,Phase"
        )
        data = self._get_json(url)
        studies = data.get("studies", [])
        items = []
        for s in studies:
            proto = s.get("protocolSection", {})
            ident = proto.get("identificationModule", {})
            status = proto.get("statusModule", {})
            design = proto.get("designModule", {})
            items.append({
                "nct_id": ident.get("nctId"),
                "title": ident.get("briefTitle"),
                "status": status.get("overallStatus"),
                "phases": design.get("phases"),
                "source": "ClinicalTrials.gov",
            })
        self._index("clinical_trials", query, items)
        return {"query": query, "count": len(items), "items": items, "status": "OK" if "error" not in data else "ERROR"}

    def multi_domain(self, query: str, max_per_source: int = 8) -> Dict[str, Any]:
        """Fan-out across PubMed, OpenAlex, Semantic Scholar, CT.gov, arXiv."""
        t0 = time.time()
        results = {
            "query": query,
            "pubmed": self.pubmed(query, max_per_source),
            "openalex": self.openalex(query, max_per_source),
            "semantic_scholar": self.semantic_scholar(query, max_per_source),
            "clinical_trials": self.clinical_trials(query, max_per_source),
            "arxiv": self.arxiv(query, max_per_source),
            "latency_sec": round(time.time() - t0, 3),
            "altar_size": len(self._altar),
            "status": "MULTI_DOMAIN_COMPLETE",
        }
        return results

    def _index(self, source: str, query: str, items: List[Any]) -> None:
        """Evidence Altar — local document metadata for FTS5/Chroma binding."""
        for it in items:
            title = it.get("title") if isinstance(it, dict) else str(it)
            self._altar.append({
                "source": source,
                "query": query,
                "title": title,
                "payload": it if isinstance(it, dict) else {"text": it},
                "indexed_at": time.time(),
            })

    def altar_snapshot(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._altar[-limit:]

    def status(self) -> Dict[str, Any]:
        return {
            "node": "DriveThruIngestion",
            "sources": ["pubmed", "arxiv", "openalex", "semantic_scholar", "clinical_trials", "who_gho"],
            "altar_documents": len(self._altar),
            "mode": "api_only_no_scrape",
            "status": "READY",
        }
