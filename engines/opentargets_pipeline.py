"""Live Open Targets Platform pipeline — target-disease associations, no API key.

Open Targets Platform (https://platform.opentargets.org) aggregates
target-disease evidence from 20+ sources (ChEMBL, Ensembl, ClinVar, GWAS
Catalog, UniProt, Reactome, Europe PMC). GraphQL endpoint:
https://api.platform.opentargets.org/api/v4/graphql (verified live
2026-10-18 and 2026-10-23).

Honest limitation: association scores are relative rankings (0-1 harmonic
sums across evidence sources), NOT calibrated confidence or clinical
assertions. Data is CC0 1.0; release-based freshness (e.g. 25.03). GraphQL
is not a bulk route — corpus-scale work belongs on the EBI FTP/BigQuery
dumps. No treatment, diagnosis, or efficacy claims are made or implied.
"""
from __future__ import annotations

import time
from typing import Any

import httpx


class OpenTargetsPipeline:
    """Read-only access to Open Targets Platform target-disease associations."""

    GRAPHQL_URL = "https://api.platform.opentargets.org/api/v4/graphql"

    _SEARCH = """query searchTarget($q: String!) {
      search(queryString: $q, entityNames: ["target"]) {
        hits { id name entity }
      }
    }"""

    _DISEASES = """query targetDiseases($id: String!, $size: Int!) {
      target(ensemblId: $id) {
        approvedSymbol
        id
        associatedDiseases(page: {index: 0, size: $size}) {
          rows { score disease { id name } }
        }
      }
    }"""

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

    async def _graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        self._throttle()
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "TMRDS/1.0 (research evidence discovery; mailto:tmrds@example.org)",
        }
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, headers=headers) as client:
            response = await client.post(
                self.GRAPHQL_URL, json={"query": query, "variables": variables}
            )
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict) or "data" not in data:
            raise ValueError("Open Targets returned an unexpected response shape")
        if data.get("errors"):
            raise ValueError(f"Open Targets GraphQL errors: {data['errors']!r}"[:200])
        return data["data"]

    async def associated_diseases(self, target_symbol: str, page_size: int = 10) -> list[dict[str, Any]]:
        """Top disease associations for a target symbol; raises for caller isolation."""
        if not target_symbol.strip():
            raise ValueError("target_symbol must not be empty")
        search = await self._graphql(self._SEARCH, {"q": target_symbol.strip()})
        hits = ((search.get("search") or {}).get("hits")) or []
        target = next((h for h in hits if isinstance(h, dict) and h.get("entity") == "target"), None)
        if target is None:
            return []
        detail = await self._graphql(
            self._DISEASES, {"id": target["id"], "size": max(1, min(page_size, 50))}
        )
        node = detail.get("target") or {}
        rows = ((node.get("associatedDiseases") or {}).get("rows")) or []
        out = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            disease = row.get("disease") or {}
            out.append(self.normalize(
                target_symbol=node.get("approvedSymbol") or target_symbol,
                target_id=node.get("id") or target.get("id"),
                disease_id=disease.get("id"),
                disease_name=disease.get("name"),
                score=row.get("score"),
            ))
        return out

    @staticmethod
    def normalize(
        target_symbol: str | None,
        target_id: str | None,
        disease_id: str | None,
        disease_name: str | None,
        score: float | None,
    ) -> dict[str, Any]:
        """Project one target-disease association into the TMRDS common evidence shape."""
        return {
            "title": f"{target_symbol} — associated with {disease_name}" if disease_name else target_symbol,
            "abstract": None,
            "authors": [],
            "published": None,
            "doi": None,
            "pmid": None,
            "nct_id": None,
            "arxiv_id": None,
            "source_url": (
                f"https://platform.opentargets.org/target/{target_id}" if target_id else None
            ),
            "open_access_url": None,
            "journal": None,
            "target_symbol": target_symbol,
            "target_id": target_id,
            "disease_id": disease_id,
            "disease_name": disease_name,
            "association_score": score,
            "is_preprint": False,
            "raw": {
                "target_symbol": target_symbol,
                "target_id": target_id,
                "disease_id": disease_id,
                "disease_name": disease_name,
                "score": score,
            },
        }
