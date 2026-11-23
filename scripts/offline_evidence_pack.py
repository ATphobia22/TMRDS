"""Prepare official public citation metadata online; verify/search it offline.

Prepare only on a connected trusted machine, using a PUBLIC nonpatient topic.
Never pass patient files to a public research API or redistribute full text.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib import request as urlrequest
from urllib.parse import urlencode

from engines.offline_evidence_pack import (
    EvidencePackError, MAX_PACK_BYTES, build_pack, load_pack, save_pack, search_pack,
)

SOURCE = "https://tmrds-public-evidence-api.onrender.com/api/v1/research/cross-check"


class NoRedirect(urlrequest.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_crosscheck(query: str) -> dict:
    """Only the audited HTTPS metadata endpoint; redirects and large bodies rejected."""
    url = SOURCE + "?" + urlencode({"query": query, "limit": 2})
    req = urlrequest.Request(url, headers={
        "Accept": "application/json", "User-Agent": "TMRDS-OfflineEvidencePack/1.0"
    })
    opener = urlrequest.build_opener(NoRedirect)
    with opener.open(req, timeout=55) as response:
        if (response.status != 200 or response.geturl() != url
                or "application/json" not in response.headers.get("Content-Type", "").lower()
                or int(response.headers.get("Content-Length") or 0) > 1_048_576):
            raise EvidencePackError("Unexpected biomedical source response")
        body = response.read(1_048_577)
        if len(body) > 1_048_576:
            raise EvidencePackError("Official source response exceeded size cap")
    value = json.loads(body)
    if not isinstance(value, dict):
        raise EvidencePackError("Official cross-check response is not a JSON object")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TMRDS public citation metadata pack, not a clinical database")
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare", help="Requires Internet; fetch original-source citation metadata")
    prepare.add_argument("--query", required=True, help="Public research term only, NEVER patient details")
    prepare.add_argument("--out", required=True, type=Path)
    verify = sub.add_parser("verify", help="No Internet; verify complete pack SHA-256 and rights")
    verify.add_argument("--path", required=True, type=Path)
    search = sub.add_parser("search", help="No Internet; search original citation metadata")
    search.add_argument("--path", required=True, type=Path)
    search.add_argument("--term", required=True, help="Public topic or source citation identifier")
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            # Reject private/invalid queries BEFORE contacting any remote service.
            from engines.offline_evidence_pack import _query
            term = _query(args.query)
            upstream = fetch_crosscheck(term)
            from datetime import datetime, timezone
            pack = build_pack(
                upstream, query=term,
                retrieved_at=datetime.now(timezone.utc).isoformat(),
            )
            save_pack(args.out, pack)
            result = {
                "status": "public_citation_metadata_pack_created", "record_count": pack["record_count"],
                "pack_sha256": pack["pack_sha256"], "source_status": pack["source_status"],
                "offline_search_ready": True, "full_text_redistribution_allowed": False,
            }
        elif args.command == "verify":
            pack = load_pack(args.path)
            result = {
                "status": "verified_local_pack", "record_count": pack["record_count"],
                "pack_sha256": pack["pack_sha256"], "original_query": pack["original_query"],
                "source_freshness_currently_verified": False,
            }
        else:
            result = search_pack(load_pack(args.path), args.term)
    except (EvidencePackError, OSError, ValueError, KeyError, json.JSONDecodeError):
        print(json.dumps({
            "status": "pack_unverified_or_not_available", "patient_data_uploaded": False,
            "clinical_interpretation": None,
        }), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
