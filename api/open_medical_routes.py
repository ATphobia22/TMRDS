"""Bounded public metadata integrations for medical software and structures.

Clinical EHR/FHIR and PACS systems are *catalog targets*, never queried here.
No patient data, dynamic URLs, credentials, AlphaFold 3 inference, or uploads.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Query, Request

from api.ops import limiter
from engines.federated_evidence_search import FederatedEvidenceSearch

router = APIRouter(prefix="/api/v1/research", tags=["governed-public-medical"])
_ROOT = Path(__file__).resolve().parents[1]
_REGISTRY = _ROOT / "public" / "medical-projects.json"
_AFDB_ORIGIN = "https://alphafold.ebi.ac.uk"
_ACCESSION = re.compile(r"^[A-Z0-9]{6,10}$")
_PMID = re.compile(r"^[0-9]{1,10}$")
_ALLOWED_FILE_HOSTS = {"alphafold.ebi.ac.uk"}
_MAX_RESPONSE_BYTES = 1024 * 1024


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def medical_project_catalog(category: str | None = None) -> dict[str, Any]:
    """The public backend and Pages frontend use the identical static inventory."""
    registry = json.loads(_REGISTRY.read_text(encoding="utf-8"))
    if registry.get("schema_version") != "1.0" or not isinstance(registry.get("projects"), list):
        raise ValueError("invalid medical project catalog")
    projects = registry["projects"]
    if category is not None:
        if category not in {p["category"] for p in projects}:
            raise ValueError("unknown project category")
        projects = [p for p in projects if p["category"] == category]
    return {**registry, "projects": projects, "count": len(projects),
            "runtime_health": "not_checked", "external_clinical_connections_enabled": False}


@router.get("/medical-projects")
@limiter.limit("30/minute")
async def list_medical_projects(request: Request, category: str | None = Query(None, max_length=30)):
    try:
        return medical_project_catalog(category)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from None


@router.get("/pubmed-citations")
@limiter.limit("10/minute")
async def pubmed_citations(
    request: Request,
    query: str = Query(..., min_length=2, max_length=100),
    limit: int = Query(default=5, ge=1, le=8),
):
    """Genuinely query NCBI E-utilities; expose *citation metadata only*."""
    if not query.strip() or any(ord(c) < 32 for c in query):
        raise HTTPException(422, detail="invalid public research query")
    service = FederatedEvidenceSearch(timeout=14)
    result = await service._guard("pubmed", service._search_pubmed(query.strip(), limit))
    records: list[dict[str, Any]] = []
    for record in result.envelopes[:limit]:
        pmid = str(record.get("pmid") or "")
        if not _PMID.fullmatch(pmid):
            continue
        records.append({
            "pmid": pmid, "title": str(record.get("title") or "")[:400],
            "journal": str(record.get("journal") or "")[:200],
            "published": str(record.get("published") or "")[:40],
            "source_url": "https://pubmed.ncbi.nlm.nih.gov/" + pmid + "/",
            "evidence_class": "research_literature",
        })
    return {
        "source": "NCBI PubMed E-utilities", "query": query.strip(),
        "retrieved_at": _timestamp(),
        "status": "responding" if result.ok else "source_unavailable",
        "records": records, "total_records_returned": len(records),
        "source_warning": None if result.ok else "PubMed source failed or exceeded a bounded timeout",
        "source_scope": "one limited metadata page; not an exhaustive review",
        "abstract_redistribution_enabled": False,
        "clinical_promotion_allowed": False,
    }


def _verified_afdb_file_url(value: Any) -> str | None:
    if not isinstance(value, str) or len(value) > 1200:
        return None
    try:
        parsed = urlparse(value)
    except ValueError:
        return None
    if (parsed.scheme != "https" or parsed.hostname not in _ALLOWED_FILE_HOSTS or
            parsed.port not in {None, 443} or parsed.username is not None or
            parsed.password is not None or parsed.fragment):
        return None
    return value


async def load_afdb_metadata(accession: str, *, transport: httpx.AsyncBaseTransport | None = None) -> dict[str, Any]:
    """Only a fixed EBI origin; refuse redirects/oversized or malformed data."""
    value = accession.strip().upper()
    if not _ACCESSION.fullmatch(value):
        raise ValueError("UniProt accession must be 6-10 uppercase alphanumeric characters")
    origin_url = _AFDB_ORIGIN + "/api/prediction/" + value
    timestamp = _timestamp()
    try:
        async with httpx.AsyncClient(timeout=12, follow_redirects=False, transport=transport) as client:
            async with client.stream("GET", origin_url, headers={"Accept": "application/json"}) as response:
                if response.status_code == 404:
                    return {"source": "AlphaFold Protein Structure Database", "status": "not_found",
                            "uniprot_accession": value, "retrieved_at": timestamp, "records": []}
                if response.status_code != 200:
                    raise ValueError("non-success upstream status")
                if int(response.headers.get("content-length") or 0) > _MAX_RESPONSE_BYTES:
                    raise ValueError("source record exceeded size limit")
                raw = bytearray()
                async for chunk in response.aiter_bytes():
                    raw.extend(chunk)
                    if len(raw) > _MAX_RESPONSE_BYTES:
                        raise ValueError("source record exceeded size limit")
        decoded = json.loads(raw)
        item = decoded[0] if isinstance(decoded, list) and decoded else decoded
        if not isinstance(item, dict) or not item:
            raise ValueError("invalid AlphaFold DB metadata schema")
        upstream_id = item.get("uniprotAccession")
        if upstream_id and str(upstream_id).upper() != value:
            raise ValueError("upstream accession mismatch")
        raw_score = item.get("globalMetricValue")
        confidence = (float(raw_score) if type(raw_score) in (float, int)
                      and 0 <= raw_score <= 100 else None)
        record = {
            "uniprot_accession": value,
            "gene": str(item.get("gene") or "")[:100],
            "model_version": item.get("latestVersion"),
            "mean_plddt": confidence,
            "pdb_url": _verified_afdb_file_url(item.get("pdbUrl")),
            "cif_url": _verified_afdb_file_url(item.get("cifUrl")),
            "pae_url": _verified_afdb_file_url(item.get("paeDocUrl")),
            "prediction_not_clinically_validated": True,
        }
        digest = hashlib.sha256(json.dumps(record, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return {
            "source": "AlphaFold Protein Structure Database", "status": "predicted_structure_metadata",
            "not_alphafold_3": True, "source_url": origin_url, "retrieved_at": timestamp,
            "license": "CC-BY-4.0; follow source attribution and per-item terms",
            "record_sha256_scope": "normalized_display_metadata_only",
            "record_sha256": digest, "records": [record],
            "clinical_promotion_allowed": False,
        }
    except (httpx.HTTPError, ValueError, json.JSONDecodeError, OverflowError):
        return {"source": "AlphaFold Protein Structure Database", "status": "source_unavailable",
                "uniprot_accession": value, "retrieved_at": timestamp, "records": [],
                "warning": "Source unavailable, invalid, redirected or oversized; no structure inferred"}


@router.get("/alphafold-db/{accession}")
@limiter.limit("10/minute")
async def alphafold_database_record(request: Request, accession: str):
    try:
        return await load_afdb_metadata(accession)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from None


@router.get("/alphafold3-status")
@limiter.limit("20/minute")
async def alphafold3_execution_state(request: Request):
    return {
        "engine": "AlphaFold 3", "status": "not_configured",
        "inference_submitted": False, "model_parameters_bundled": False,
        "public_run_enabled": False, "code_license": "Apache-2.0",
        "parameter_terms": "Restricted: eligible non-commercial use; manual review required",
        "official_source": "https://github.com/google-deepmind/alphafold3",
        "terms_url": "https://github.com/google-deepmind/alphafold3/blob/main/WEIGHTS_TERMS_OF_USE.md",
        "caution": "AlphaFold DB metadata are NOT AlphaFold 3 predictions or a substitute for experiments.",
        "clinical_promotion_allowed": False,
    }
