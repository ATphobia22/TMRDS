"""Evidence-only disease -> target -> compound pathway, with exact-ID joins.

Only public Open Targets records are consumed; ChEMBL-derived content retains
its underlying license obligations. This is discovery, not clinical validation.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timedelta, timezone
from importlib.resources import files
from typing import Any

import httpx

GRAPHQL_ENDPOINT = "https://api.platform.opentargets.org/api/v4/graphql"
MAX_BYTES = 2_000_000
TERMS_REVIEWED_AT = "2026-11-23"
_DISEASE_ID = re.compile(r"^(?:MONDO|EFO|HP|OTAR|DOID)_[0-9]{4,12}$")
_TARGET_ID = re.compile(r"^ENSG[0-9]{11}$")
_COMPOUND_ID = re.compile(r"^CHEMBL[0-9]{1,12}$")
_SOURCE_LICENSES = {
    "opentargets": ("CC0 1.0 platform data; embedded source-specific terms remain", "https://platform-docs.opentargets.org/licence", False),
    "chembl": ("CC BY-SA 3.0", "https://www.ebi.ac.uk/chembl/", True),
    "europe_pmc": ("Per-record full-text and publisher rights", "https://europepmc.org/RestfulWebService", True),
    "clinicaltrials_gov": ("Provider use and attribution terms", "https://clinicaltrials.gov/data-api/about-api", True),
    "pubmed": ("Per-article publisher and provider terms", "https://www.ncbi.nlm.nih.gov/books/NBK25499/", True),
    "gwas_catalog_v2": ("Per-source and publication rights; manual review required", "https://www.ebi.ac.uk/gwas/docs/programmatic-access/rest-api/", True),
    "dailymed": ("SPL label and provider-specific notices", "https://dailymed.nlm.nih.gov/dailymed/", True),
    "openfda": ("OpenFDA data terms and underlying label rights", "https://open.fda.gov/apis/", True),
    "reactome": ("Reactome pathway annotations CC0; images and code CC BY 4.0", "https://reactome.org/license", True),
    "uniprot": ("UniProtKB data CC BY 4.0; source annotations may require further rights review", "https://www.uniprot.org/help/license", True),
    "pubchem": ("NCBI PubChem data: individual depositors retain their own rights; metadata only", "https://pubchem.ncbi.nlm.nih.gov/docs/data-sources", True),
    "crossref": ("Crossref factual metadata generally CC0; article content/publisher rights separate", "https://www.crossref.org/documentation/retrieve-metadata/", True),
    "openalex": ("OpenAlex scholarly metadata, open metadata with upstream work rights", "https://docs.openalex.org/", True),
    "arxiv": ("arXiv bibliographic metadata and author-specific preprint licenses", "https://info.arxiv.org/help/api/", True),
    "biorxiv": ("bioRxiv / medRxiv author preprints, record-specific licenses", "https://www.biorxiv.org/about-biorxiv", True),
    "clinvar": ("NCBI ClinVar submitter assertions, clinical classification conflicts", "https://www.ncbi.nlm.nih.gov/clinvar/docs/", True),
    "ensembl": ("Ensembl genome reference and predicted effect metadata, source terms apply", "https://rest.ensembl.org/", True),
    "gnomad": ("gnomAD data release terms, variant-indexed population metadata only", "https://gnomad.broadinstitute.org/terms", True),
    "gtex": ("GTEx release terms, aggregated tissue association metadata only", "https://gtexportal.org/home/about", True),
    "string": ("STRING protein functional associations CC BY 4.0 with attribution", "https://string-db.org/cgi/access", True),
    "mesh": ("NLM MeSH controlled terms, terminology metadata and NLM terms", "https://www.nlm.nih.gov/mesh/meshhome.html", True),
    "ncats": ("NIH NCATS Translator Node Normalization/Name Resolution service metadata", "https://nodenormalization-sri.renci.org/docs", True),
}
_RESOLVE = """query TMRDSResolveDisease($query: String!) {
 search(queryString: $query, entityNames: ["disease"], page: {index: 0, size: 10}) {
   hits { id name entity }
 }
}"""
_PATHWAY = """query TMRDSEvidencePathway($id: String!, $size: Int!) {
 meta { apiVersion { x y z } dataVersion { year month iteration } }
 disease(efoId: $id) {
   id name
   associatedTargets(page: {index: 0, size: $size}, enableIndirect: false) {
     count rows { score target { id approvedSymbol } }
   }
   drugAndClinicalCandidates {
     count rows {
       maxClinicalStage
       drug {
         id name
         mechanismsOfAction {
           rows { actionType mechanismOfAction targets { id approvedSymbol } }
         }
       }
     }
   }
 }
}"""


class PathwaySourceError(ValueError):
    """Upstream or schema error: never convert to no-evidence finding."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_time(value: str | None) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None else None
    except ValueError:
        return None


def evaluate_freshness(retrieved_at: str | None, *, now: datetime | None = None,
                       release: str | None = None, max_age_hours: int = 24) -> dict[str, Any]:
    """Retrieval freshness is distinct from whether an upstream dataset is current."""
    now = now or _now()
    observed = _parse_time(retrieved_at)
    status = "unknown"
    age_seconds = None
    if observed is not None:
        age_seconds = int((now - observed).total_seconds())
        status = ("invalid_future_timestamp" if age_seconds < -60 else
                  "fresh" if age_seconds <= max_age_hours * 3600 and age_seconds >= -60 else "stale")
    return {
        "retrieval": status,
        "retrieved_at": retrieved_at,
        "retrieval_age_seconds": age_seconds,
        "upstream_release": "observed_not_independently_verified" if release else "unknown",
        "source_release": release,
        "scope": "request_scoped_not_durable_monitoring",
    }


def evaluate_license(source_id: str, *, now: datetime | None = None) -> dict[str, Any]:
    """Conservative data-use policy; a public HTTP endpoint isn't a license."""
    now = now or _now()
    policy = _SOURCE_LICENSES.get(source_id)
    if policy is None:
        return {
            "source": source_id, "license": "unverified", "terms_url": None,
            "review_state": "unregistered", "metadata_display_allowed": False,
            "bulk_redistribution_allowed": False, "attribution_required": True,
            "requires_human_license_review": True,
        }
    notice, url, attribution = policy
    as_of = datetime.fromisoformat(TERMS_REVIEWED_AT).replace(tzinfo=timezone.utc)
    overdue = now - as_of > timedelta(days=90)
    return {
        "source": source_id, "license": notice, "terms_url": url,
        "terms_metadata_checked_on": TERMS_REVIEWED_AT,
        "review_state": "review_overdue" if overdue else "needs_human_approval_for_reuse",
        "metadata_display_allowed": True,
        "bulk_redistribution_allowed": False,
        "attribution_required": attribution,
        "requires_human_license_review": True,
    }


def _strict_list(value: Any, name: str) -> list:
    if not isinstance(value, list):
        raise PathwaySourceError("invalid list in upstream " + name)
    return value


def _strict_id(value: Any, pattern: re.Pattern[str], context: str) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise PathwaySourceError("invalid " + context + " identifier")
    return value


def _release_meta(meta: Any) -> str | None:
    if not isinstance(meta, dict) or not isinstance(meta.get("dataVersion"), dict):
        return None
    data = meta["dataVersion"]
    def parse_part(value: Any) -> int | None:
        if type(value) is int and 0 <= value <= 9999:
            return value
        if isinstance(value, str) and value.isascii() and value.isdecimal() and 1 <= len(value) <= 4:
            return int(value)
        return None
    year, month = parse_part(data.get("year")), parse_part(data.get("month"))
    iteration_raw = data.get("iteration")
    iteration = parse_part(iteration_raw) if iteration_raw is not None else None
    if year is None or month is None or (iteration_raw is not None and iteration is None):
        return None
    return f"{year:02d}.{month:02d}" + (f".{iteration}" if iteration is not None else "")


def normalize_pathway(query: str, source: dict[str, Any], retrieved_at: str,
                      *, limit: int = 10) -> dict[str, Any]:
    """Join only if a source-supplied drug mechanism names an exact target ID."""
    if not isinstance(source, dict) or not isinstance(source.get("disease"), dict):
        raise PathwaySourceError("disease record absent in upstream response")
    disease = source["disease"]
    disease_id = _strict_id(disease.get("id"), _DISEASE_ID, "disease")
    if not isinstance(disease.get("name"), str) or not disease["name"]:
        raise PathwaySourceError("source disease name absent")
    targets = disease.get("associatedTargets")
    drugs = disease.get("drugAndClinicalCandidates")
    if not isinstance(targets, dict) or not isinstance(drugs, dict):
        raise PathwaySourceError("source relation fields absent")
    target_rows = _strict_list(targets.get("rows"), "associatedTargets")
    drug_rows = _strict_list(drugs.get("rows"), "drugAndClinicalCandidates")
    for context, block, retrieved in (
        ("associatedTargets", targets, target_rows),
        ("drugAndClinicalCandidates", drugs, drug_rows),
    ):
        count = block.get("count")
        if type(count) is not int or count < len(retrieved) or count < 0:
            raise PathwaySourceError("invalid source row count in " + context)
    target_index: dict[str, dict] = {}
    for row in target_rows:
        if not isinstance(row, dict) or not isinstance(row.get("target"), dict):
            raise PathwaySourceError("malformed target row")
        node = row["target"]
        tid = _strict_id(node.get("id"), _TARGET_ID, "target")
        score = row.get("score")
        if type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 1:
            raise PathwaySourceError("invalid association ranking score")
        target_index[tid] = {"id": tid, "symbol": str(node.get("approvedSymbol") or "")[:64],
                             "relative_association_score": float(score)}
    links = []
    seen: set[tuple[str, str]] = set()
    for row in drug_rows:
        if not isinstance(row, dict) or not isinstance(row.get("drug"), dict):
            raise PathwaySourceError("malformed drug candidate")
        drug = row["drug"]
        cid = _strict_id(drug.get("id"), _COMPOUND_ID, "compound")
        mechanism = drug.get("mechanismsOfAction")
        if not isinstance(mechanism, dict):
            continue  # Not linked: no inferred mechanism.
        for mechanism_row in _strict_list(mechanism.get("rows"), "mechanismsOfAction"):
            if not isinstance(mechanism_row, dict):
                raise PathwaySourceError("malformed mechanism row")
            reported_targets = mechanism_row.get("targets")
            # Current upstream mechanisms may report null when targets have not
            # been established. Do not infer targets or fail other usable rows.
            if reported_targets is None:
                continue
            for target in _strict_list(reported_targets, "mechanism targets"):
                if not isinstance(target, dict):
                    raise PathwaySourceError("malformed mechanism target")
                tid = _strict_id(target.get("id"), _TARGET_ID, "mechanism target")
                if tid not in target_index or (tid, cid) in seen:
                    continue
                seen.add((tid, cid))
                anchor = {
                    "disease_id": disease_id, "target_id": tid, "compound_id": cid,
                    "action_type": str(mechanism_row.get("actionType") or "")[:120],
                    "mechanism": str(mechanism_row.get("mechanismOfAction") or "")[:300],
                    "reported_stage": str(row.get("maxClinicalStage") or "unknown")[:64],
                }
                digest = hashlib.sha256(json.dumps(anchor, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
                links.append({
                    "disease_id": disease_id, "target": target_index[tid],
                    "compound": {"id": cid, "name": str(drug.get("name") or cid)[:160]},
                    "evidence_kind": "source_reported_drug_mechanism",
                    "source": "opentargets", "underlying_data_source": "ChEMBL/integrated sources",
                    "source_url": f"https://platform.opentargets.org/drug/{cid}",
                    "source_record_hash": digest, "hash_scope": "selected_source_fields_not_signed",
                    **anchor, "clinical_efficacy_verified": False,
                    "human_review_state": "unreviewed",
                })
    release = _release_meta(source.get("meta"))
    truncated = (len(target_rows) < targets.get("count", len(target_rows)) or
                 len(drug_rows) < drugs.get("count", len(drug_rows)) or len(links) > limit)
    return {
        "schema_version": "1.0",
        "status": "links_retrieved" if links else "no_verified_links_in_sample",
        "query": query, "disease": {"id": disease_id, "name": disease["name"]},
        "retrieved_at": retrieved_at,
        "source_freshness": evaluate_freshness(retrieved_at, release=release),
        "license_review": [evaluate_license("opentargets"), evaluate_license("chembl")],
        "links": links[:limit],
        "coverage": {
            "disease_target_total": targets.get("count"),
            "compound_rows_total": drugs.get("count"),
            "retrieved_targets": len(target_rows), "retrieved_candidate_rows": len(drug_rows),
            "truncated": bool(truncated), "indirect_associations_enabled": False,
            "disclaimer": "No link is evidence of efficacy; absent link is not evidence of absence.",
        },
        "governance": {
            "research_advisory_only": True, "human_authority_final": True,
            "clinical_promotion_allowed": False, "not_samd": True,
            "independent_clinical_review": False, "bulk_redistribution_allowed": False,
        },
    }


class PathwaySourceClient:
    """Two bounded, non-redirecting POST requests to one fixed HTTPS GraphQL origin."""

    def __init__(self, timeout: float = 18.0) -> None:
        self.timeout = timeout

    async def _query(self, query: str, variables: dict) -> dict:
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=False) as client:
                response = await client.post(GRAPHQL_ENDPOINT, json={"query": query, "variables": variables},
                                             headers={"Accept": "application/json"})
            if response.status_code != 200 or len(response.content) > MAX_BYTES:
                raise PathwaySourceError("Open Targets unavailable or response exceeds bounded size")
            payload = response.json()
            if not isinstance(payload, dict) or payload.get("errors") or not isinstance(payload.get("data"), dict):
                raise PathwaySourceError("Open Targets GraphQL response invalid")
            return payload["data"]
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise PathwaySourceError("Open Targets request unavailable or incompatible") from exc

    async def search(self, disease_query: str, *, limit: int = 10) -> dict[str, Any]:
        term = disease_query.strip()
        if not 2 <= len(term) <= 120 or any(ord(c) < 32 for c in term):
            raise ValueError("Public research disease query must be 2-120 characters")
        limit = max(1, min(limit, 25))
        if _DISEASE_ID.fullmatch(term):
            identifier = term
        else:
            resolved = await self._query(_RESOLVE, {"query": term})
            hits = _strict_list((resolved.get("search") or {}).get("hits"), "disease search hits")
            exact = [h for h in hits if isinstance(h, dict) and h.get("entity") == "disease"
                     and isinstance(h.get("name"), str) and h["name"].casefold() == term.casefold()
                     and isinstance(h.get("id"), str) and _DISEASE_ID.fullmatch(h["id"])]
            if len(exact) != 1:
                return {
                    "schema_version": "1.0", "status": "disease_not_unambiguously_resolved",
                    "query": term, "links": [],
                    "candidates": [{"id": h.get("id"), "name": h.get("name")}
                                   for h in hits if isinstance(h, dict) and h.get("entity") == "disease"][:10],
                    "governance": {"clinical_promotion_allowed": False, "human_authority_final": True},
                }
            identifier = exact[0]["id"]
        data = await self._query(_PATHWAY, {"id": identifier, "size": limit})
        return normalize_pathway(term, data, _now().isoformat(), limit=limit)


def load_reference_pathways() -> dict:
    return json.loads(files("engines").joinpath("pathway_reference_cases.json").read_text())


def validate_reference_pathways(result: dict, reference: dict | None = None) -> dict:
    """Technical identifier consistency only; not an independent clinical review."""
    reference = reference or load_reference_pathways()
    link_keys = {
        (r.get("disease_id"), r.get("target_id"), r.get("compound_id"))
        for r in result.get("links", []) if isinstance(r, dict)
    }
    expected = reference["expected_links"]
    negatives = reference["negative_controls"]
    found = sum((r["disease_id"], r["target_id"], r["compound_id"]) in link_keys for r in expected)
    clean = sum((r["disease_id"], r["target_id"], r["compound_id"]) not in link_keys for r in negatives)
    return {
        "technical_consistency": "pass" if found == len(expected) and clean == len(negatives) else "fail",
        "expected_links_found": found, "expected_links_total": len(expected),
        "negative_controls_passed": clean, "negative_controls_total": len(negatives),
        "reference_source": "FDA label and independently published gene/compound identifiers",
        "independent_human_review_completed": bool(reference.get("independent_human_review_completed")),
        "external_live_validation": False,
        "clinical_validation": False,
        "note": "Contract checks do not establish real-world clinical efficacy or comprehensive evidence coverage.",
    }
