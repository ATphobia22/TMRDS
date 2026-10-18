"""Live ChEMBL pipeline — open bioactivity data, no API key.

ChEMBL (https://www.ebi.ac.uk/chembl, EMBL-EBI) curates bioactivity data
linking drug-like compounds to biological targets: molecules, targets,
assays, and measurements (IC50/Ki). Database data is CC BY-SA 3.0 —
attribution required and share-alike applies to adapted redistribution.

Honest limitation: no published rate limit (be modest — this client spaces
calls); bioactivity values are literature-curated and assay-heterogeneous,
so assay conditions must travel with values. Bulk extraction belongs on the
ChEMBL database dumps, not the API.
"""
from __future__ import annotations

import time
from typing import Any
from urllib.parse import quote_plus

import httpx


class ChEMBLPipeline:
    """Read-only access to the ChEMBL REST web services."""

    BASE_URL = "https://www.ebi.ac.uk/chembl/api/data"

    def __init__(self, timeout: float = 30.0, min_interval: float = 1.0) -> None:
        self.timeout = timeout
        self.min_interval = min_interval
        self._last_call = 0.0

    def _throttle(self) -> None:
        wait = self.min_interval - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

    async def search_molecule(self, query: str, page_size: int = 20) -> list[dict[str, Any]]:
        """Search molecules; raises on transport/HTTP errors so callers can isolate failures."""
        if not query.strip():
            raise ValueError("query must not be empty")
        self._throttle()
        url = f"{self.BASE_URL}/molecule/search.json"
        params = {"q": query.strip(), "limit": max(1, min(page_size, 100))}
        headers = {"User-Agent": "TMRDS/1.0 (research evidence discovery; mailto:tmrds@example.org)"}
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, headers=headers) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        molecules = data.get("molecules")
        if not isinstance(molecules, list):
            raise ValueError("ChEMBL returned an unexpected response shape")
        return [self.normalize(m) for m in molecules if isinstance(m, dict)]

    @staticmethod
    def normalize(molecule: dict[str, Any]) -> dict[str, Any]:
        """Project one ChEMBL molecule into the TMRDS common evidence shape."""
        chembl_id = molecule.get("molecule_chembl_id")
        structures = molecule.get("molecule_structures") or {}
        return {
            "title": molecule.get("pref_name") or chembl_id,
            "abstract": None,
            "authors": [],
            "published": None,
            "doi": None,
            "pmid": None,
            "nct_id": None,
            "arxiv_id": None,
            "source_url": f"https://www.ebi.ac.uk/chembl/compound_report_card/{chembl_id}/" if chembl_id else None,
            "open_access_url": None,
            "journal": None,
            "chembl_id": chembl_id,
            "canonical_smiles": structures.get("canonical_smiles"),
            "molecule_type": molecule.get("molecule_type"),
            "max_phase": molecule.get("max_phase"),
            "license": "CC BY-SA 3.0",
            "is_preprint": False,
            "raw": molecule,
        }
