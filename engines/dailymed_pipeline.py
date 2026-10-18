"""Live DailyMed pipeline — open FDA drug-label (SPL) data, no API key.

DailyMed (https://dailymed.nlm.nih.gov, NLM) is the official provider of FDA
label information as Structured Product Labeling (SPL). This client uses the
v2 REST service (`/dailymed/services/v2/`), verified live 2026-10-18; older
v1-style paths now 302-redirect and are not used.

Honest limitation: labels are labeler-specific SPLs (one drug -> many SPLs;
resolve the SET ID); label text is regulatory verbatim, not a curated
indication dataset. Dosage/indication content lives here and in openFDA —
not in RxNorm.
"""
from __future__ import annotations

from typing import Any

import httpx


class DailyMedPipeline:
    """Read-only access to DailyMed SPL label metadata."""

    BASE_URL = "https://dailymed.nlm.nih.gov/dailymed/services/v2"

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout

    async def search_by_drug_name(self, name: str, page_size: int = 20) -> list[dict[str, Any]]:
        """Find SPL labels by drug name; raises on transport/HTTP errors for caller isolation."""
        if not name.strip():
            raise ValueError("name must not be empty")
        url = f"{self.BASE_URL}/spls.json"
        params = {"drug_name": name.strip(), "pagesize": max(1, min(page_size, 100))}
        headers = {
            "User-Agent": "TMRDS/1.0 (research evidence discovery; mailto:tmrds@example.org)",
            "Accept": "application/json",
        }
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, headers=headers) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        records = data.get("data")
        if not isinstance(records, list):
            raise ValueError("DailyMed returned an unexpected response shape")
        return [self.normalize(r) for r in records if isinstance(r, dict)]

    @staticmethod
    def normalize(record: dict[str, Any]) -> dict[str, Any]:
        """Project one DailyMed SPL record into the TMRDS common evidence shape."""
        setid = record.get("setid")
        return {
            "title": record.get("title"),
            "abstract": None,
            "authors": [],
            "published": record.get("published_date"),
            "doi": None,
            "pmid": None,
            "nct_id": None,
            "arxiv_id": None,
            "source_url": f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={setid}" if setid else None,
            "open_access_url": None,
            "journal": None,
            "spl_set_id": setid,
            "spl_version": record.get("spl_version"),
            "is_preprint": False,
            "raw": record,
        }
