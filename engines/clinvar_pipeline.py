"""Live ClinVar pipeline — published variant interpretations, no API key.

ClinVar (https://www.ncbi.nlm.nih.gov/clinvar/) is NCBI's public archive of
variant-condition interpretations with review-status ("star") ratings.
Documented programmatic path: NCBI E-utilities with db=clinvar
(esearch -> esummary). Verified live 2026-10-18 and 2026-10-23.

Honest limitation: conflicting interpretations are COMMON — this pipeline
always surfaces the review status (e.g. "criteria provided, single
submitter") alongside the classification; a lone label without stars
misleads. VUS-heavy for rare variants. E-utilities policy: 3 req/s without
key, 10 req/s with a free NCBI API key; email/tool identification expected.
These are published interpretations for research review — never
per-patient variant interpretation.
"""
from __future__ import annotations

import os
import time
from typing import Any

import httpx


class ClinVarPipeline:
    """Read-only access to ClinVar via NCBI E-utilities."""

    EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(
        self,
        api_key: str | None = None,
        email: str | None = None,
        timeout: float = 30.0,
        min_interval: float = 0.4,
    ) -> None:
        self.api_key = api_key or os.environ.get("NCBI_API_KEY")
        self.email = email or os.environ.get("TMRDS_CONTACT_EMAIL", "tmrds@example.org")
        self.timeout = timeout
        self.min_interval = min_interval
        self._last_call = 0.0

    def _throttle(self) -> None:
        # Stay under the 3 req/s keyless E-utilities ceiling.
        wait = self.min_interval - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

    def _base_params(self) -> dict[str, Any]:
        params: dict[str, Any] = {"tool": "TMRDS", "email": self.email}
        if self.api_key:
            params["api_key"] = self.api_key
        return params

    async def _eutils(self, script: str, params: dict[str, Any]) -> dict[str, Any]:
        self._throttle()
        merged = {**self._base_params(), **params}
        headers = {"User-Agent": f"TMRDS/1.0 (research evidence discovery; mailto:{self.email})"}
        url = f"{self.EUTILS}/{script}"
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, headers=headers) as client:
            response = await client.get(url, params=merged)
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict):
            raise ValueError("E-utilities returned an unexpected response shape")
        return data

    async def search_variants(self, term: str, page_size: int = 10) -> list[dict[str, Any]]:
        """Search ClinVar records; raises for caller isolation."""
        if not term.strip():
            raise ValueError("term must not be empty")
        search = await self._eutils(
            "esearch.fcgi",
            {"db": "clinvar", "term": term.strip(), "retmax": max(1, min(page_size, 50)), "retmode": "json"},
        )
        idlist = (search.get("esearchresult") or {}).get("idlist") or []
        if not idlist:
            return []
        summary = await self._eutils(
            "esummary.fcgi", {"db": "clinvar", "id": ",".join(idlist), "retmode": "json"}
        )
        result = summary.get("result") or {}
        out = []
        for uid in idlist:
            rec = result.get(uid)
            if isinstance(rec, dict):
                out.append(self.normalize(rec))
        return out

    @staticmethod
    def normalize(record: dict[str, Any]) -> dict[str, Any]:
        """Project one ClinVar esummary record into the TMRDS common evidence shape.

        Always surfaces germline review status alongside the classification.
        """
        germline = record.get("germline_classification") or {}
        traits = germline.get("trait_set") or []
        conditions = [
            t.get("trait_name") for t in traits
            if isinstance(t, dict) and t.get("trait_name")
        ]
        uid = record.get("uid")
        return {
            "title": record.get("title"),
            "abstract": None,
            "authors": [],
            "published": germline.get("last_evaluated"),
            "doi": None,
            "pmid": None,
            "nct_id": None,
            "arxiv_id": None,
            "source_url": f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{uid}/" if uid else None,
            "open_access_url": None,
            "journal": "ClinVar (NCBI)",
            "variation_id": uid,
            "classification": germline.get("description"),
            "review_status": germline.get("review_status"),
            "conditions": conditions,
            "is_preprint": False,
            "raw": record,
        }
