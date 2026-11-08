"""Read-only PDB core-entry metadata; no model execution or therapeutic inference."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
import re
import httpx


class RCSBPipeline:
    async def entry(self, pdb_id: str) -> dict:
        # Explicit legacy-ID subset; computed model identifiers are not accepted.
        if not isinstance(pdb_id, str) or not re.fullmatch(r"[1-9][A-Za-z0-9]{3}", pdb_id):
            raise ValueError("a four-character PDB accession is required")
        identity = pdb_id.upper()
        url = f"https://data.rcsb.org/rest/v1/core/entry/{identity}"
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=False) as client:
            response = await client.get(url)
            response.raise_for_status()
            if response.is_redirect:
                raise ValueError("redirect rejected")
            data = response.json()
        if not isinstance(data, dict) or data.get("rcsb_id") != identity:
            raise ValueError("PDB response identity mismatch")
        methods = data.get("exptl") or []
        if not isinstance(methods, list) or any(not isinstance(m, dict) for m in methods):
            raise ValueError("PDB experimental-method metadata malformed")
        method_names = [m["method"] for m in methods if m.get("method")]
        return {"source": "rcsb_pdb", "source_id": identity,
                "source_url": f"https://www.rcsb.org/structure/{identity}",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "title": (data.get("struct") or {}).get("title"),
                "experimental_methods": method_names,
                "experimental_status": "source_reports_method" if method_names else "not_reported",
                "source_version": data.get("rcsb_accession_info") or {},
                "record_sha256": hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                "hash_scope": "parsed_upstream_json", "hash_is_signature": False,
                "research_advisory": True, "clinical_promotion_allowed": False,
                "limitations": ["Metadata only; coordinates not downloaded.", "Experimental structure does not establish treatment efficacy."]}
