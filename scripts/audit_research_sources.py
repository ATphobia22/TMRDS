#!/usr/bin/env python3
"""Generate a bounded audit receipt for official public biomedical APIs.

This records current reachability/version observations and policy REVIEW states.
It does not approve data licenses, substitute for a legal review, or validate a
drug's safety or efficacy. Expected failures are visible, never filled with mocks.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

from engines.governed_pathway import (
    PathwaySourceClient, evaluate_license, validate_reference_pathways,
)

PROBES: dict[str, tuple[str, dict | None]] = {
    "opentargets": (
        "https://api.platform.opentargets.org/api/v4/graphql",
        {"query": "{ meta { apiVersion { x y z } dataVersion { year month iteration } } }"},
    ),
    "chembl": ("https://www.ebi.ac.uk/chembl/api/data/status.json", None),
    "europe_pmc": (
        "https://www.ebi.ac.uk/europepmc/webservices/rest/search?format=json&resultType=lite&pageSize=1&query=CFTR",
        None,
    ),
    "clinicaltrials_gov": ("https://clinicaltrials.gov/api/v2/version", None),
    "gwas_catalog_v2": (
        "https://www.ebi.ac.uk/gwas/rest/api/v2/associations?efo_trait=asthma&size=1&page=0&show_child_traits=false",
        None,
    ),
}


async def run_online_audit() -> dict:
    """One limited request per upstream + one bounded pathway reference case."""
    inspected_at = datetime.now(timezone.utc).isoformat()
    receipt = {
        "schema_version": "1.0", "inspected_at": inspected_at,
        "scope": "public_API_metadata_and_one_case_only",
        "upstream_version_verified_as_current": False,
        "independent_human_license_approval": False,
        "independent_clinical_validation": False,
        "providers": {},
        "reference_case": {},
    }
    async with httpx.AsyncClient(timeout=14, follow_redirects=False) as client:
        for provider, (url, payload) in PROBES.items():
            observed = {"source": provider, "url": url, "checked_at": datetime.now(timezone.utc).isoformat(),
                        "license": evaluate_license(provider), "source_state": "unavailable",
                        "upstream_body_sha256": None, "upstream_release": None}
            try:
                if payload is None:
                    response = await client.get(url, headers={"Accept": "application/json"})
                else:
                    response = await client.post(url, json=payload, headers={"Accept": "application/json"})
                if response.status_code != 200 or len(response.content) > 2_000_000:
                    observed["source_state"] = "unexpected_http_or_oversize"
                    observed["status_code"] = response.status_code
                else:
                    decoded = response.json()
                    if not isinstance(decoded, dict) or decoded.get("errors"):
                        observed["source_state"] = "invalid_schema"
                    else:
                        observed["source_state"] = "responding"
                        observed["upstream_body_sha256"] = hashlib.sha256(response.content).hexdigest()
                        if provider == "opentargets":
                            observed["upstream_release"] = decoded.get("data", {}).get("meta", {}).get("dataVersion")
                        elif provider == "chembl":
                            observed["upstream_release"] = decoded.get("chembl_db_version")
                        elif provider == "clinicaltrials_gov":
                            observed["upstream_release"] = decoded.get("dataTimestamp")
            except (httpx.HTTPError, ValueError, TypeError, KeyError):
                observed["source_state"] = "unavailable"
            receipt["providers"][provider] = observed
    try:
        result = await PathwaySourceClient(timeout=18).search("MONDO_0009061", limit=25)
        receipt["reference_case"] = {
            "status": result["status"],
            "disease_id": (result.get("disease") or {}).get("id"),
            "source_release": (result.get("source_freshness") or {}).get("source_release"),
            "result_count": len(result["links"]),
            "reference_contract": validate_reference_pathways(result),
            "warning": "One-case exact-ID check; technical consistency only, not clinical validation.",
        }
    except (ValueError, httpx.HTTPError):
        receipt["reference_case"] = {
            "status": "unavailable",
            "reference_contract": None,
            "warning": "Missing live check is not a failed biological finding.",
        }
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="build/audit/research-sources.json")
    args = parser.parse_args()
    receipt = asyncio.run(run_online_audit())
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(target),
        "inspected_at": receipt["inspected_at"],
        "provider_states": {k: v["source_state"] for k, v in receipt["providers"].items()},
        "reference_case_status": receipt["reference_case"].get("status"),
        "reference_technical_consistency": (
            (receipt["reference_case"].get("reference_contract") or {}).get("technical_consistency", "inconclusive")
        ),
        "license_approval": False, "clinical_validation": False,
    }, sort_keys=True))
    # A live source reply that contradicts the reference is a real audit
    # failure, unlike an explicitly unavailable source (inconclusive).
    verification = receipt["reference_case"].get("reference_contract") or {}
    if receipt["reference_case"].get("status") == "links_retrieved" and verification.get("technical_consistency") != "pass":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
