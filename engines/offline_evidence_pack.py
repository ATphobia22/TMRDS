"""Self-verifying, source-bounded OFFLINE biomedical citation metadata cache.

No patient records, publication full text, automatic clinical interpretations,
online dependencies, or user-directed arbitrary URL fetching are permitted.
Prepare on a connected computer; read/search on a disconnected workstation.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

MAX_PACK_BYTES = 524288
MAX_RECORDS = 256
MAX_SOURCE_GROUPS = 128
SOURCE_IDS = frozenset((
    "pubmed", "europe_pmc", "clinicaltrials_gov", "opentargets", "chembl",
    "openfda", "dailymed", "gwas_catalog_v2", "reactome", "pubchem", "uniprot",
    "crossref", "openalex", "arxiv", "biorxiv", "clinvar", "ensembl",
    "gnomad", "gtex", "string", "mesh", "ncats",
))
_DOI = re.compile(r"^10\.[0-9]{4,9}/[^\s]{1,180}$", re.I)
_PMID = re.compile(r"^[0-9]{1,10}$")
_PMCID = re.compile(r"^PMC[0-9]{1,12}$", re.I)
_NCT = re.compile(r"^NCT[0-9]{8}$", re.I)
_PII = re.compile(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}|\b\d{3}-\d{2}-\d{4}\b|Patient/[A-Za-z0-9]+", re.I)
_ALLOWED_STATES = frozenset(("responding", "source_unavailable", "not_queried"))


class EvidencePackError(ValueError):
    """Pack failed a provenance, rights, integrity, or local-boundary check."""


def _encode(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("utf-8")


def _hash(value: dict) -> str:
    return hashlib.sha256(_encode(value)).hexdigest()


def _query(text: str) -> str:
    if (not isinstance(text, str) or not (2 <= len(text.strip()) <= 80)
            or any(ord(c) < 32 for c in text) or _PII.search(text)
            or ".." in text or ("/" in text and not _DOI.fullmatch(text.strip())) or "\\" in text):
        raise EvidencePackError("Use only public, short non-identifying biomedical research terms")
    return text.strip()


def _timestamp(raw: str) -> datetime:
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None or dt.year < 2000:
            raise ValueError
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError, AttributeError):
        raise EvidencePackError("Pack requires timestamped UTC source retrieval") from None


def _citation(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise EvidencePackError("Malformed source metadata")
    source = item.get("source")
    ident = item.get("stable_id")
    if (source not in SOURCE_IDS or not isinstance(ident, str)
            or not ident.startswith(source + ":") or len(ident) > 180
            or _PII.search(ident)):
        raise EvidencePackError("Unknown source or invalid original source identity")
    title = item.get("title")
    if title is not None and (not isinstance(title, str) or len(title) > 350 or _PII.search(title)):
        raise EvidencePackError("Unreviewed or identifying publication title")
    rec = {
        "source": source, "stable_id": ident,
        "title": title or None,
        "pmid": str(item["pmid"]) if _PMID.fullmatch(str(item.get("pmid") or "")) else None,
        "pmcid": str(item["pmcid"]).upper() if _PMCID.fullmatch(str(item.get("pmcid") or "")) else None,
        "doi": str(item["doi"]).lower() if _DOI.fullmatch(str(item.get("doi") or "")) else None,
        "nct_id": str(item["nct_id"]).upper() if _NCT.fullmatch(str(item.get("nct_id") or "")) else None,
        "published": str(item.get("published") or "")[:20],
        "full_text_included": False,
        "independent_replication_verified": False,
        "clinical_efficacy_inferred": False,
    }
    if _PII.search(rec["published"]):
        raise EvidencePackError("Invalid original publication date")
    return rec


def build_pack(source_payload: dict[str, Any], *, query: str, retrieved_at: str) -> dict[str, Any]:
    query = _query(query)
    when = _timestamp(retrieved_at).isoformat()
    if (not isinstance(source_payload, dict) or source_payload.get("query") != query
            or source_payload.get("schema_version") != "1.0"
            or not isinstance(source_payload.get("groups"), list)
            or len(source_payload["groups"]) > MAX_SOURCE_GROUPS):
        raise EvidencePackError("Invalid or mismatched original cross-check contract")
    status = source_payload.get("source_status")
    license_policy = source_payload.get("source_licensing")
    if not isinstance(status, dict) or not isinstance(license_policy, dict) or not status:
        raise EvidencePackError("No source-status and licensing metadata to review")
    clean_states: dict[str, str] = {}
    for name, value in status.items():
        if name not in SOURCE_IDS or not isinstance(value, dict) or value.get("state") not in _ALLOWED_STATES:
            raise EvidencePackError("Unknown evidence provider or availability state")
        policy = license_policy.get(name)
        if (not isinstance(policy, dict) or policy.get("metadata_display_allowed") is not True
                or policy.get("bulk_redistribution_allowed") is not False):
            raise EvidencePackError("Source metadata display rights have not been approved")
        clean_states[name] = value["state"]
    found: dict[tuple[str, str], dict] = {}
    for group in source_payload["groups"]:
        if not isinstance(group, dict) or not isinstance(group.get("source_records"), list):
            raise EvidencePackError("Malformed evidence groups")
        for item in group["source_records"]:
            record = _citation(item)
            if record["source"] not in clean_states:
                raise EvidencePackError("Record source has no rights and availability policy")
            if clean_states[record["source"]] != "responding":
                raise EvidencePackError("Unavailable source cannot report trusted records")
            found[(record["source"], record["stable_id"])] = record
            if len(found) > MAX_RECORDS:
                raise EvidencePackError("Bounded offline metadata pack record count exceeded")
    package = {
        "schema_version": "1.0", "type": "tmrds_public_citation_metadata_snapshot",
        "original_query": query, "retrieved_at": when, "records": [found[x] for x in sorted(found)],
        "record_count": len(found), "source_status": dict(sorted(clean_states.items())),
        "rights": {
            "usage": "local_citation_metadata_reference_only",
            "per_source_terms_must_be_reviewed": True, "bulk_redistribution_approved": False,
        },
        "patient_data_included": False, "full_text_included": False,
        "clinical_promotion_allowed": False, "source_freshness_currently_verified": False,
        "independent_replication_inferred": False, "human_authority_final": True,
    }
    package["pack_sha256"] = _hash(package)
    if len(_encode(package)) > MAX_PACK_BYTES:
        raise EvidencePackError("Offline metadata pack exceeds maximum size")
    return package


def _local_file(path: Path) -> Path:
    raw = str(path)
    if (raw.startswith(("//", "\\\\")) or path.is_symlink()
            or any(part == ".." for part in path.parts)):
        raise EvidencePackError("Network paths, symlinks and traversal are prohibited")
    return path


def save_pack(path: Path, pack: dict[str, Any]) -> None:
    path = _local_file(path)
    validate_pack(pack)
    try:
        with path.open("x", encoding="utf8") as stream:
            stream.write(json.dumps(pack, indent=2, sort_keys=True, ensure_ascii=True) + "\n")
    except FileExistsError:
        raise EvidencePackError("Refusing to overwrite existing signed-scope snapshot") from None
    except OSError:
        raise EvidencePackError("Unable to save local snapshot") from None


def validate_pack(pack: dict[str, Any]) -> None:
    if not isinstance(pack, dict) or pack.get("schema_version") != "1.0":
        raise EvidencePackError("Unknown evidence snapshot schema")
    stored = pack.get("pack_sha256")
    if not isinstance(stored, str) or not re.fullmatch(r"[a-f0-9]{64}", stored):
        raise EvidencePackError("Missing digest")
    plain = {key: value for key, value in pack.items() if key != "pack_sha256"}
    if _hash(plain) != stored:
        raise EvidencePackError("Evidence pack altered since receipt; refuse usage")
    if (pack.get("type") != "tmrds_public_citation_metadata_snapshot"
            or pack.get("patient_data_included") is not False
            or pack.get("full_text_included") is not False
            or pack.get("clinical_promotion_allowed") is not False
            or pack.get("rights", {}).get("bulk_redistribution_approved") is not False):
        raise EvidencePackError("Unsafe pack use or source-rights state")
    _query(pack.get("original_query"))
    _timestamp(pack.get("retrieved_at"))
    records = pack.get("records")
    states = pack.get("source_status")
    if (not isinstance(records, list) or len(records) > MAX_RECORDS
            or not isinstance(states, dict) or not states
            or any(k not in SOURCE_IDS or v not in _ALLOWED_STATES for k, v in states.items())
            or pack.get("record_count") != len(records)):
        raise EvidencePackError("Invalid or excessive source records")
    if len(_encode(pack)) > MAX_PACK_BYTES:
        raise EvidencePackError("Pack over size cap")
    for record in records:
        if not isinstance(record, dict) or set(record) != {
                "source", "stable_id", "title", "pmid", "pmcid", "doi", "nct_id", "published",
                "full_text_included", "independent_replication_verified", "clinical_efficacy_inferred"}:
            raise EvidencePackError("Unexpected source record fields")
        if _citation(record) != record or states.get(record["source"]) != "responding":
            raise EvidencePackError("Untrusted or altered source record")
        if any(record[key] is not False for key in ("full_text_included",
                "independent_replication_verified", "clinical_efficacy_inferred")):
            raise EvidencePackError("Clinical or licensed text claims not permitted")


def load_pack(path: Path) -> dict[str, Any]:
    path = _local_file(path)
    if not path.is_file() or path.stat().st_size > MAX_PACK_BYTES:
        raise EvidencePackError("Local evidence snapshot missing or over size bound")
    try:
        pack = json.loads(path.read_text(encoding="utf8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise EvidencePackError("Unable to read local evidence snapshot") from None
    validate_pack(pack)
    return pack


def search_pack(pack: dict[str, Any], term: str, *, as_of: str | None = None) -> dict[str, Any]:
    validate_pack(pack)
    term = _query(term).casefold()
    now = (datetime.fromisoformat(as_of).date() if as_of else datetime.now(timezone.utc).date())
    retrieved = _timestamp(pack["retrieved_at"]).date()
    if now < retrieved:
        raise EvidencePackError("Cannot claim freshness before the source was retrieved")
    days = (now - retrieved).days
    matches = [
        record for record in pack["records"]
        if term in " ".join(str(record.get(k) or "") for k in
                            ("title", "stable_id", "pmid", "pmcid", "doi", "nct_id")).casefold()
    ][:20]
    failures = [name for name, state in pack["source_status"].items() if state != "responding"]
    return {
        "status": "local_metadata_matches" if matches else "no_cached_metadata_matches",
        "match_count": len(matches), "matches": matches, "query": term,
        "source_retrieved_at": pack["retrieved_at"], "age_days": days,
        "freshness": "stale" if days > 90 else "snapshot_age_within_90_days",
        "current_source_freshness_verified": False, "coverage_partial": bool(failures),
        "sources_unavailable_or_unqueried": failures, "search_executed_online": False,
        "patient_data_used": False, "clinical_interpretation": None,
        "negative_evidence_inferred": False, "human_authority_final": True,
        "pack_sha256": pack["pack_sha256"],
    }
