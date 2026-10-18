"""Live PubChem PUG-REST pipeline — open chemistry data, no API key.

PubChem PUG-REST (https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest) serves
compounds (CIDs), substances, assays, synonyms, and computed properties
(SMILES, InChI/InChIKey, IUPAC, formula, weight, XLogP, TPSA, H-bond counts).

Honest limitation: the published limits (<=5 requests/second, <=400/minute)
are ceilings, not guarantees — PubChem applies dynamic throttling under load
(`X-Throttling-Control` headers; overages return HTTP 503). This client stays
well under the ceiling and treats 503 as an honest upstream failure, never as
data. Bulk extraction belongs on the PubChem FTP, not this API.
"""
from __future__ import annotations

import time
from typing import Any
from urllib.parse import quote

import httpx


class PubChemPipeline:
    """Read-only access to PubChem PUG-REST compound data."""

    BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    PROPERTIES = (
        "Title,IUPACName,InChI,InChIKey,CanonicalSMILES,MolecularFormula,"
        "MolecularWeight,XLogP,TPSA,HBondDonorCount,HBondAcceptorCount,RotatableBondCount"
    )

    def __init__(self, timeout: float = 30.0, min_interval: float = 0.25) -> None:
        self.timeout = timeout
        self.min_interval = min_interval
        self._last_call = 0.0

    def _throttle(self) -> None:
        wait = self.min_interval - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

    async def search_by_name(self, name: str) -> list[dict[str, Any]]:
        """Look up compounds by name; raises on transport/HTTP errors for caller isolation."""
        if not name.strip():
            raise ValueError("name must not be empty")
        self._throttle()
        url = f"{self.BASE_URL}/compound/name/{quote(name.strip())}/property/{self.PROPERTIES}/JSON"
        headers = {"User-Agent": "TMRDS/1.0 (research evidence discovery; mailto:tmrds@example.org)"}
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, headers=headers) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
        table = (data.get("PropertyTable") or {}).get("Properties") or []
        if not isinstance(table, list):
            raise ValueError("PubChem returned an unexpected response shape")
        return [self.normalize(p) for p in table if isinstance(p, dict)]

    @staticmethod
    def normalize(prop: dict[str, Any]) -> dict[str, Any]:
        """Project one PubChem property record into the TMRDS common evidence shape."""
        cid = prop.get("CID")
        title = prop.get("IUPACName") or prop.get("Title") or (f"CID {cid}" if cid else None)
        properties = {
            k: prop.get(k)
            for k in (
                "MolecularFormula", "MolecularWeight", "CanonicalSMILES", "InChI",
                "InChIKey", "XLogP", "TPSA", "HBondDonorCount",
                "HBondAcceptorCount", "RotatableBondCount",
            )
            if prop.get(k) is not None
        }
        return {
            "title": title,
            "abstract": None,
            "authors": [],
            "published": None,
            "doi": None,
            "pmid": None,
            "nct_id": None,
            "arxiv_id": None,
            "source_url": f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}" if cid else None,
            "open_access_url": None,
            "journal": None,
            "cid": cid,
            "properties": properties,
            "is_preprint": False,
            "raw": prop,
        }
