"""Read-only, source-scoped biomedical crosschecks and FDA patent *metadata*.

This service neither ingests patient data nor makes patent freedom-to-operate
determinations. It never accepts arbitrary upstream domains or raw URLs.
"""
from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query, Request

from api.ops import limiter
from engines.federated_evidence_search import COVERAGE, FederatedEvidenceSearch
from engines.governed_pathway import evaluate_license
from engines.qrce_public_crosscheck import build_crosscheck

router = APIRouter(prefix="/api/v1/research", tags=["bounded-public-crosscheck"])
_ORANGE_BOOK = "https://api.fda.gov/drug/orangebook.json"
_MAX_BYTES = 1_048_576
_DRUG_QUERY = re.compile(r"^[a-zA-Z][a-zA-Z0-9 -]{1,55}$")
_PATENT_NUMBER = re.compile(r"^[0-9]{5,12}(?:\*PED)?$")
_SOURCE_HANDLERS: dict[str, str] = {
    "pubmed": "_search_pubmed",
    "europe_pmc": "_search_europepmc",
    "clinicaltrials_gov": "_search_trials",
    "opentargets": "_search_opentargets",
    "chembl": "_search_chembl",
    "openfda": "_search_openfda",
    "dailymed": "_search_dailymed",
    "gwas_catalog_v2": "_search_gwas_catalog_v2",
    "reactome": "_search_reactome",
    "pubchem": "_search_pubchem",
    "uniprot": "_search_uniprot",
    "crossref": "_search_crossref",
    "openalex": "_search_openalex",
    "arxiv": "_search_arxiv",
    "biorxiv": "_search_biorxiv",
    "clinvar": "_search_clinvar",
    "ensembl": "_search_ensembl",
    "gnomad": "_search_gnomad",
    "gtex": "_search_gtex",
    "string": "_search_string",
    "mesh": "_search_mesh",
    "ncats": "_search_ncats",
}


def validate_public_query(query: str) -> str:
    query = query.strip()
    if len(query) < 2 or len(query) > 100 or any(ord(c) < 32 for c in query):
        raise ValueError("invalid research term")
    if re.search(r"\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b|[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", query):
        raise ValueError("Patient or identifying information must not be sent to public sources")
    return query


@router.get("/cross-check")
@limiter.limit("3/minute")
async def public_crosscheck(
    request: Request,
    query: str = Query(..., min_length=2, max_length=100),
    limit: int = Query(default=2, ge=1, le=4),
):
    try:
        query = validate_public_query(query)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from None
    allowed = {source: fn for source, fn in _SOURCE_HANDLERS.items()
               if evaluate_license(source)["metadata_display_allowed"]}
    if set(allowed) != set(_SOURCE_HANDLERS):
        raise HTTPException(503, detail="Crosscheck source policy missing or out of date")
    service = FederatedEvidenceSearch(timeout=16)
    try:
        results = await asyncio.wait_for(
            asyncio.gather(*(service._guard(source, getattr(service, handler)(query, limit))
                             for source, handler in allowed.items())),
            timeout=42,
        )
    except Exception:
        raise HTTPException(503, detail="Source lookup exceeded bounded execution budget") from None
    packet = build_crosscheck(query, results, expected_sources=tuple(allowed))
    packet["source_coverage"] = {
        source: COVERAGE[source] for source in _SOURCE_HANDLERS
    }
    packet["source_licensing"] = {
        source: {"metadata_display_allowed": evaluate_license(source)["metadata_display_allowed"],
                 "bulk_redistribution_allowed": False,
                 "human_review_required": True}
        for source in _SOURCE_HANDLERS
    }
    return packet


def _normalized_date(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    if re.fullmatch(r"[0-9]{8}", value):
        try:
            return datetime.strptime(value, "%Y%m%d").date().isoformat()
        except ValueError:
            return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None


def _reported_comparison(date_str: str | None, as_of: str) -> str:
    if date_str is None:
        return "unreported"
    return ("listed_date_precedes_lookup" if date_str < as_of else
            "listed_date_is_lookup_date" if date_str == as_of else
            "listed_date_follows_lookup")


def _safe_patent_number(value: Any) -> str | None:
    candidate = str(value or "").strip().upper()
    return candidate if _PATENT_NUMBER.fullmatch(candidate) else None


def _parse_orangebook_response(payload: dict[str, Any], ingredient: str,
                               *, limit: int, as_of: str, retrieved_at: str) -> dict[str, Any]:
    entries = payload.get("results")
    if not isinstance(entries, list):
        raise ValueError("FDA Orange Book result schema invalid")
    meta = payload.get("meta") or {}
    if not isinstance(meta, dict):
        raise ValueError("FDA metadata schema invalid")
    records = []
    for record in entries[:limit]:
        if not isinstance(record, dict):
            continue
        products = []
        for product in (record.get("products") or [])[:6]:
            if not isinstance(product, dict):
                continue
            active = [str(item.get("name") or "")[:100]
                      for item in (product.get("active_ingredients") or [])[:8]
                      if isinstance(item, dict)]
            application = str(product.get("application_number") or "")
            if not re.fullmatch(r"[0-9]{1,9}", application):
                continue
            products.append({
                "application_number": application,
                "application_type": str(product.get("application_type") or "")[:5],
                "product_name": str(product.get("brand_name") or "")[:100],
                "active_ingredients": active,
                "marketing_status_as_reported": str(product.get("marketing_status") or "")[:80],
            })
        patents = []
        for patent in (record.get("patents") or [])[:25]:
            if not isinstance(patent, dict):
                continue
            number = _safe_patent_number(patent.get("patent_number"))
            if not number:
                continue
            expiry = _normalized_date(patent.get("expiration_date"))
            patents.append({
                "patent_number_as_filed": number,
                "fda_reported_date": expiry,
                "date_relation": _reported_comparison(expiry, as_of),
                "pediatric_extension_marker": number.endswith("*PED"),
                "reported_drug_substance_flag": patent.get("drug_substance_flag") is True,
                "reported_drug_product_flag": patent.get("drug_product_flag") is True,
                "reported_use_code": str(patent.get("patent_use_code") or "")[:35],
                "legal_status": "UNVERIFIED",
                "freedom_to_operate": "NOT_DETERMINED",
            })
        exclusivity = []
        for row in (record.get("exclusivity") or [])[:20]:
            if not isinstance(row, dict):
                continue
            expiry = _normalized_date(row.get("exclusivity_expiration_date"))
            exclusivity.append({
                "code": str(row.get("exclusivity_code") or "")[:40],
                "fda_reported_date": expiry,
                "date_relation": _reported_comparison(expiry, as_of),
                "legal_status": "UNVERIFIED",
            })
        if products:
            records.append({
                "products": products, "patents": patents, "exclusivity": exclusivity,
                "fda_reported_approval_date": _normalized_date(record.get("approval_date")),
                "original_source_record": "https://api.fda.gov/drug/orangebook.json",
            })
    return {
        "source": "FDA Orange Book / openFDA",
        "source_endpoint": _ORANGE_BOOK,
        "source_updated_at": str(meta.get("last_updated") or "")[:30] or None,
        "retrieved_at": retrieved_at, "as_of": as_of, "ingredient": ingredient,
        "status": "records_retrieved" if records else "no_relevant_records_on_page",
        "record_count": len(records), "records": records,
        "source_is_monthly": True,
        "federal_patent_database_checked": False,
        "patent_freedom_to_operate": "NOT_DETERMINED",
        "expired_public_domain_claim": False,
        "indication_efficacy_inferred": False,
        "clinical_promotion_allowed": False,
        "verification_queue": [
            "Confirm exact patent claims, family members, application and jurisdiction at the USPTO.",
            "Review maintenance, patent-term adjustment/extension, pediatric extensions and litigation.",
            "Review FDA regulatory exclusivities independently of listed patent dates.",
            "Check later blocking patents, formulations, manufacturing processes and combinations.",
            "Obtain qualified freedom-to-operate analysis before production or commercial use.",
        ],
        "official_references": [
            "https://www.fda.gov/drugs/drug-approvals-and-databases/orange-book-data-files",
            "https://www.uspto.gov/patents/maintain",
            "https://data.uspto.gov/",
        ],
    }


async def lookup_fda_patent_metadata(
    ingredient: str, *, limit: int = 3,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict[str, Any]:
    term = ingredient.strip().upper()
    if not _DRUG_QUERY.fullmatch(term) or len(term) > 56:
        raise ValueError("Enter a public ingredient name, not patient information or a URL")
    if not isinstance(limit, int) or not (1 <= limit <= 5):
        raise ValueError("limit out of bounds")
    stamp = datetime.now(timezone.utc)
    as_of, retrieved_at = stamp.date().isoformat(), stamp.isoformat()
    try:
        async with httpx.AsyncClient(transport=transport, timeout=12, follow_redirects=False) as client:
            async with client.stream(
                "GET", _ORANGE_BOOK,
                params={"search": "products.active_ingredients.name:" + term, "limit": str(limit)},
                headers={"Accept": "application/json"},
            ) as result:
                if result.status_code == 404:
                    # OpenFDA returns NOT_FOUND for a correctly executed empty lookup.
                    data = {"results": []}
                elif result.status_code != 200:
                    raise ValueError("FDA upstream unavailable")
                else:
                    if int(result.headers.get("content-length") or 0) > _MAX_BYTES:
                        raise ValueError("FDA response too large")
                    body = bytearray()
                    async for chunk in result.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > _MAX_BYTES:
                            raise ValueError("FDA response too large")
                    data = json.loads(body)
                    if not isinstance(data, dict):
                        raise ValueError("FDA response schema invalid")
        response = _parse_orangebook_response(data, term, limit=limit, as_of=as_of, retrieved_at=retrieved_at)
        if result.status_code == 404:
            response["status"] = "no_matches_reported_by_fda"
        return response
    except (ValueError, httpx.HTTPError, json.JSONDecodeError, OverflowError):
        return {
            "source": "FDA Orange Book / openFDA", "status": "source_unavailable",
            "ingredient": term, "records": [], "retrieved_at": retrieved_at,
            "patent_freedom_to_operate": "NOT_DETERMINED",
            "clinical_promotion_allowed": False,
            "warning": "Source unavailable, invalid, redirected or exceeded bounds; no patent status assumed",
        }


@router.get("/patent-landscape")
@limiter.limit("5/minute")
async def public_patent_landscape(
    request: Request,
    ingredient: str = Query(..., min_length=2, max_length=56),
    limit: int = Query(default=3, ge=1, le=5),
):
    try:
        return await lookup_fda_patent_metadata(ingredient, limit=limit)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from None
