"""Opt-in read-only source checks. No patient data, full text or paid compute."""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines.federated_evidence_search import FederatedEvidenceSearch


async def run_checks() -> dict:
    search = FederatedEvidenceSearch()

    async def protein():
        records = await search._search_uniprot("gene:TP53 AND organism_id:9606 AND reviewed:true", 1)
        if not records or records[0]["protein_metadata"]["accession"] != "P04637":
            raise ValueError("expected public protein record not returned")
        r = records[0]
        return {"source": "uniprot", "status": "passed", "source_url": r["source_url"],
                "accession": r["protein_metadata"]["accession"], "source_release": r["source_release"],
                "entry_audit": r["protein_metadata"]["entry_audit"], "record_hash": r["record_hash"]}

    async def integrity():
        records = await search._search_europepmc("EXT_ID:42550576 AND SRC:MED", 1)
        if not records or records[0]["publication_integrity"]["retraction_status"] != "retraction_reported":
            raise ValueError("expected public retraction metadata not returned")
        r = records[0]
        return {"source": "europe_pmc", "status": "passed", "source_url": r["source_url"],
                "pmid": r["pmid"], "publication_integrity": r["publication_integrity"], "record_hash": r["record_hash"]}

    async def bounded(source, coro):
        try:
            return await asyncio.wait_for(coro, timeout=35)
        except Exception as exc:
            return {"source": source, "status": "failed", "exception_type": type(exc).__name__}

    checks = await asyncio.gather(bounded("uniprot", protein()), bounded("europe_pmc", integrity()))
    paths = ["engines/uniprot_pipeline.py", "engines/publication_integrity.py", "engines/federated_evidence_search.py"]
    return {"checked_at": datetime.now(timezone.utc).isoformat(), "checks": checks,
            "implementation_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
            "scope": "Two read-only live adapter checks; not all-source health, clinical validation or therapeutic benefit."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Explicitly allow public upstream requests")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.live:
        parser.error("--live is required; no upstream request made")
    report = asyncio.run(run_checks())
    rendered = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered)
    print(rendered, end="")
    return 0 if all(c["status"] == "passed" for c in report["checks"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
