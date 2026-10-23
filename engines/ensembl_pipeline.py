"""Live Ensembl REST pipeline — genomic reference data, no API key.

Ensembl REST (https://rest.ensembl.org) serves genes, transcripts,
sequences, variant consequences (VEP), and region queries for the current
assembly (GRCh38); GRCh37 via https://grch37.rest.ensembl.org. Verified
live 2026-10-18 and 2026-10-23.

Honest limitation: 55,000 requests/hour per IP with 429 + Retry-After on
exceed; bulk annotation belongs on local VEP or batched POSTs. VEP
consequence predictions are computational evidence, not clinical
assertions. Assembly matters — always record which assembly was queried.
Free for all uses; cite Ensembl.
"""
from __future__ import annotations

import time
from typing import Any

import httpx


class EnsemblPipeline:
    """Read-only access to the Ensembl REST API (GRCh38 by default)."""

    BASE_URL = "https://rest.ensembl.org"

    def __init__(self, timeout: float = 30.0, min_interval: float = 0.1) -> None:
        self.timeout = timeout
        self.min_interval = min_interval
        self._last_call = 0.0

    def _throttle(self) -> None:
        wait = self.min_interval - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        self._throttle()
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "TMRDS/1.0 (research evidence discovery; mailto:tmrds@example.org)",
        }
        url = f"{self.BASE_URL}{path}"
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, headers=headers) as client:
            response = await client.get(url, params=params or {})
            response.raise_for_status()
            return response.json()

    async def lookup_gene(self, symbol: str, species: str = "homo_sapiens") -> dict[str, Any] | None:
        """Look up a gene by symbol; raises for caller isolation; None if not found."""
        if not symbol.strip():
            raise ValueError("symbol must not be empty")
        try:
            data = await self._get(
                f"/lookup/symbol/{species}/{symbol.strip()}",
                {"content-type": "application/json", "expand": 0},
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise
        if not isinstance(data, dict):
            raise ValueError("Ensembl returned an unexpected response shape")
        return self.normalize(data, species)

    @staticmethod
    def normalize(gene: dict[str, Any], species: str = "homo_sapiens") -> dict[str, Any]:
        """Project one Ensembl gene record into the TMRDS common evidence shape."""
        stable_id = gene.get("id")
        return {
            "title": f"{gene.get('display_name')} ({stable_id})" if stable_id else gene.get("display_name"),
            "abstract": gene.get("description"),
            "authors": [],
            "published": None,
            "doi": None,
            "pmid": None,
            "nct_id": None,
            "arxiv_id": None,
            "source_url": (
                f"https://www.ensembl.org/{species.replace('_', ' ').title().replace(' ', '_')}/Gene/Summary?g={stable_id}"
                if stable_id else None
            ),
            "open_access_url": None,
            "journal": "Ensembl (EBI/EMBL)",
            "ensembl_id": stable_id,
            "display_name": gene.get("display_name"),
            "biotype": gene.get("biotype"),
            "assembly": gene.get("assembly_name"),
            "location": f"{gene.get('seq_region_name')}:{gene.get('start')}-{gene.get('end')}"
            if gene.get("seq_region_name") else None,
            "is_preprint": False,
            "raw": gene,
        }
