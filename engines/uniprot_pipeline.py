"""Bounded, read-only UniProtKB metadata retrieval; no efficacy inference."""
from __future__ import annotations

from typing import Any

import httpx


class UniProtPipeline:
    BASE_URL = "https://rest.uniprot.org/uniprotkb/search"
    FIELDS = "accession,id,protein_name,gene_names,organism_id,reviewed,version,date_modified"

    async def search(self, query: str, page_size: int = 10) -> dict[str, Any]:
        if not isinstance(query, str) or not query.strip() or len(query) > 500:
            raise ValueError("query must contain 1-500 characters")
        params = {"query": query.strip(), "format": "json", "size": max(1, min(page_size, 25)),
                  "fields": self.FIELDS}
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=False) as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            if response.is_redirect:
                raise ValueError("UniProt redirect is not permitted")
            data = response.json()
        if not isinstance(data, dict) or not isinstance(data.get("results"), list):
            raise ValueError("UniProt returned an unexpected response shape")
        if any(not isinstance(r, dict) or not isinstance(r.get("primaryAccession"), str)
               or not r["primaryAccession"].isalnum() for r in data["results"]):
            raise ValueError("UniProt result lacks a valid accession")
        return {"results": data["results"][:params["size"]],
                "source_release": response.headers.get("x-uniprot-release"),
                "source_release_date": response.headers.get("x-uniprot-release-date"),
                "has_more": 'rel="next"' in response.headers.get("link", "")}

    @staticmethod
    def normalize(record: dict[str, Any]) -> dict[str, Any]:
        accession = record["primaryAccession"]
        description = record.get("proteinDescription") or {}
        recommended = description.get("recommendedName") or {}
        name = (recommended.get("fullName") or {}).get("value")
        if not name:
            alternatives = description.get("submissionNames") or []
            name = (alternatives[0].get("fullName") or {}).get("value") if alternatives else None
        return {
            "title": name or record.get("uniProtkbId") or accession,
            "source_url": f"https://www.uniprot.org/uniprotkb/{accession}/entry",
            "protein_metadata": {
                "accession": accession, "entry_type": record.get("entryType"),
                "taxonomy_id": (record.get("organism") or {}).get("taxonId"),
                "gene_names": [(g.get("geneName") or {}).get("value")
                               for g in record.get("genes") or [] if (g.get("geneName") or {}).get("value")],
                "entry_audit": record.get("entryAudit") or {},
                "clinical_effectiveness": "not_assessed",
            },
        }
