"""Nonclinical, exact-identifier QRCE evidence cross-check and model exchange.

Never compute a cure score. Multiple database entries for a paper are NOT
independent scientific replication. Only source-reported exact identifiers join.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

DOI = re.compile(r"^10\.[0-9]{4,9}/[^\s]{1,180}$", re.I)
PMID = re.compile(r"^[0-9]{1,10}$")
NCT = re.compile(r"^NCT[0-9]{8}$")
PMCID = re.compile(r"^PMC[0-9]{1,12}$", re.I)
ENSG = re.compile(r"^ENSG[0-9]{11}$")
CHEMBL = re.compile(r"^CHEMBL[0-9]{1,12}$")
RSID = re.compile(r"^rs[0-9]{1,12}$", re.I)
PUBLIC_FIELDS = frozenset({
    "stable_id", "source", "source_name", "evidence_class", "title",
    "published", "doi", "pmid", "pmcid", "nct_id", "journal", "source_url",
    "ensembl_id", "chembl_id", "snp_id", "rsids", "variation_id", "cid", "uniprot_id",
    "classification", "review_status", "assembly", "most_severe_consequence",
    "record_hash", "record_hash_scope", "retrieved_at", "source_release",
    "source_release_date", "publication_integrity", "warnings",
})
SOURCE_COUNT_LIMIT = 100


def _normalize_doi(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    doi = value.strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if doi.lower().startswith(prefix):
            doi = doi[len(prefix):]
            break
    return doi.lower() if DOI.fullmatch(doi) else None


def _keyset(record: dict[str, Any]) -> set[str]:
    keys = set()
    doi = _normalize_doi(record.get("doi"))
    if doi:
        keys.add("doi:" + doi)
    pmid = str(record.get("pmid") or "").strip()
    if PMID.fullmatch(pmid):
        keys.add("pmid:" + pmid)
    pmcid = str(record.get("pmcid") or "").strip().upper()
    if PMCID.fullmatch(pmcid):
        keys.add("pmcid:" + pmcid)
    nct = str(record.get("nct_id") or "").strip().upper()
    if NCT.fullmatch(nct):
        keys.add("nct:" + nct)
    return keys


def _safe_metadata(envelope: dict[str, Any], source: str) -> dict[str, Any] | None:
    if not isinstance(envelope, dict) or envelope.get("is_mock") is True:
        return None
    if envelope.get("source") != source:
        return None
    identity = envelope.get("stable_id")
    if not isinstance(identity, str) or not identity.startswith(source + ":"):
        return None
    record = {key: envelope[key] for key in PUBLIC_FIELDS if key in envelope}
    for key in ("title", "journal", "published", "source_url"):
        if key in record:
            record[key] = str(record[key] or "")[:500]
    record["doi"] = _normalize_doi(record.get("doi"))
    record["pmid"] = str(record.get("pmid") or "") if PMID.fullmatch(str(record.get("pmid") or "")) else None
    record["nct_id"] = str(record.get("nct_id") or "") if NCT.fullmatch(str(record.get("nct_id") or "")) else None
    record["pmcid"] = str(record.get("pmcid") or "").upper() if PMCID.fullmatch(str(record.get("pmcid") or "")) else None
    record["ensembl_id"] = str(record.get("ensembl_id") or "") if ENSG.fullmatch(str(record.get("ensembl_id") or "")) else None
    record["chembl_id"] = str(record.get("chembl_id") or "") if CHEMBL.fullmatch(str(record.get("chembl_id") or "")) else None
    record["snp_id"] = str(record.get("snp_id") or "") if RSID.fullmatch(str(record.get("snp_id") or "")) else None
    record["uniprot_id"] = str(record.get("uniprot_id") or "")[:12] if isinstance(record.get("uniprot_id"), str) else None
    record["rsids"] = [str(v) for v in (record.get("rsids") or [])[:12] if isinstance(v, str) and RSID.fullmatch(v)] if isinstance(record.get("rsids"), list) else []
    for name in ("classification", "review_status", "assembly", "most_severe_consequence"):
        record[name] = str(record[name])[:120] if isinstance(record.get(name), str) else None
    for name in ("variation_id", "cid"):
        value = record.get(name)
        record[name] = value if type(value) is int and 0 < value < 10**12 else None
    record["warnings"] = [str(x)[:180] for x in (record.get("warnings") or [])[:4]
                          if isinstance(x, str)]
    # Retain only reviewed, non-executable publication integrity metadata.
    record["publication_integrity"] = "review_required" if record.get("publication_integrity") else None
    return record


def _context_keys(record: dict[str, Any]) -> set[str]:
    """Context relationship != identity. Never merge distinct experiments on a gene."""
    keys = set()
    if record.get("ensembl_id") and ENSG.fullmatch(record["ensembl_id"]):
        keys.add("ensembl:" + record["ensembl_id"])
    if record.get("chembl_id") and CHEMBL.fullmatch(record["chembl_id"]):
        keys.add("chembl:" + record["chembl_id"])
    if record.get("snp_id") and RSID.fullmatch(record["snp_id"]):
        keys.add("dbsnp:" + record["snp_id"].lower())
    for rsid in record.get("rsids") or []:
        if RSID.fullmatch(rsid):
            keys.add("dbsnp:" + rsid.lower())
    if record.get("variation_id") is not None:
        keys.add("clinvar_variation:" + str(record["variation_id"]))
    if record.get("cid") is not None:
        keys.add("pubchem_cid:" + str(record["cid"]))
    return keys


def _context_graph(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # A shared target can mean different experiments or species; this only
    # exposes navigational context, never evidence aggregation or confirmation.
    by_key: dict[str, list[dict[str, str]]] = defaultdict(list)
    for entry in entries:
        for key in _context_keys(entry):
            by_key[key].append({"source": entry["source"],
                                "record_id": entry["stable_id"][:160]})
    edges = []
    for identifier, rows in by_key.items():
        if len(set(r["source"] for r in rows)) < 2:
            continue
        edges.append({
            "identifier": identifier,
            "records": rows[:20],
            "relationship": "same_source_reported_context_identifier",
            "independent_replication_verified": False,
            "causal_relation_verified": False,
        })
    return sorted(edges, key=lambda item: item["identifier"])[:40]


def build_crosscheck(
    query: str,
    provider_results: list[Any],
    *,
    searched_at: str | None = None,
    expected_sources: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Union exact DOI/PMID/PMCID/NCT matches, preserve per-source outages and disagreement.

    No fuzzy title/entity joins. No study efficacy synthesis. Nonclinical output.
    """
    searched_at = searched_at or datetime.now(timezone.utc).isoformat()
    entries: list[dict[str, Any]] = []
    source_status: dict[str, dict[str, Any]] = {}
    known = set(expected_sources)
    for result in provider_results:
        source = str(result.source)
        if known and source not in known:
            continue
        records = []
        if bool(result.ok):
            for envelope in result.envelopes[:SOURCE_COUNT_LIMIT]:
                cleaned = _safe_metadata(envelope, source)
                if cleaned is not None:
                    records.append(cleaned)
        entries.extend(records)
        source_status[source] = {
            "state": "responding" if result.ok else "source_unavailable",
            "records_returned": len(records),
            "warning": (str(result.warning)[:180] if result.warning else None),
            "review": "source_metadata_only",
        }
    for source in expected_sources:
        source_status.setdefault(source, {
            "state": "not_queried", "records_returned": 0,
            "warning": "Source not invoked; no coverage conclusion", "review": "source_metadata_only",
        })

    # DSU joins are transitive ONLY through exact source-supplied IDs.
    parent = list(range(len(entries)))
    def find(n: int) -> int:
        while parent[n] != n:
            parent[n] = parent[parent[n]]
            n = parent[n]
        return n
    seen: dict[str, int] = {}
    keys_per_record = [_keyset(x) for x in entries]
    for idx, keys in enumerate(keys_per_record):
        for key in sorted(keys):
            other = seen.setdefault(key, idx)
            root_a, root_b = find(idx), find(other)
            if root_a != root_b:
                parent[root_a] = root_b

    clusters: dict[int, list[int]] = defaultdict(list)
    for idx in range(len(entries)):
        clusters[find(idx)].append(idx)
    groups = []
    for index_list in clusters.values():
        members = [entries[i] for i in index_list]
        ids = sorted(set().union(*(keys_per_record[i] for i in index_list)))
        # Metadata disagreement is NOT a conflict between clinical outcomes.
        titles = {str(m.get("title") or "").strip().casefold() for m in members if m.get("title")}
        dates = {str(m.get("published") or "")[:10] for m in members if m.get("published")}
        groups.append({
            "exact_identifiers": ids,
            "sources": sorted({m["source"] for m in members}),
            "record_count": len(members),
            "metadata_disagreements": (["title"] if len(titles) > 1 else []) +
                                      (["source_publication_date"] if len(dates) > 1 else []),
            "source_records": members,
            "interpretation": ("cross_index_metadata_overlap_only" if len({m["source"] for m in members}) > 1
                               else "single_source_or_unlinked_record"),
            "independent_replication_verified": False,
            "clinical_effectiveness_verified": False,
        })
    groups.sort(key=lambda g: (-len(g["sources"]), g["exact_identifiers"], g["sources"]))
    snapshot = {
        "query": query, "searched_at": searched_at,
        "sources": {s: source_status[s] for s in sorted(source_status)},
        "records": len(entries), "groups": len(groups),
        "metadata_overlap_groups": sum(len(x["sources"]) > 1 for x in groups),
    }
    digest = hashlib.sha256(json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    source_items = [
        {"source_id": source, "value": stat["records_returned"], "unit": "1",
         "state": stat["state"], "retrieved_at": searched_at}
        for source, stat in sorted(source_status.items())
    ]
    return {
        "schema_version": "1.0", "query": query, "searched_at": searched_at,
        "status": ("records_retrieved" if entries else
                   "no_records_with_partial_coverage" if any(x["state"] == "responding" for x in source_status.values())
                   else "sources_unavailable"),
        "record_count": len(entries), "group_count": len(groups),
        "metadata_overlap_groups": snapshot["metadata_overlap_groups"],
        "groups": groups, "source_status": source_status,
        "molecular_context_links": _context_graph(entries),
        "snapshot_sha256": digest, "sha256_scope": "normalized_counts_and_source_status_not_raw_upstream_payload",
        "openmi_inspired_exchange": {
            "specification": "OGC OpenMI 2.0, concepts only",
            "conformance": "NOT_CONFORMANCE_TESTED",
            "producer": "TMRDS-PublicEvidenceSnapshot", "consumer": "TMRDS-RubiksEvidenceCube",
            "exchange_item": "source_public_record_count",
            "value_type": "integer", "unit": "1", "temporal_context": searched_at,
            "items": source_items,
            "clinical_data_included": False,
        },
        "patent_freedom_to_operate": "not_determined",
        "discovery_only": True, "independent_experiments_inferred": False,
        "clinical_promotion_allowed": False, "human_authority_final": True,
        "limitations": [
            "Metadata overlap is the same record indexed by multiple systems, not independent replication.",
            "Provider failures do not imply absence of scientific findings.",
            "No fuzzy title matching; bibliographic identity requires source-supplied DOI, PMID, PMCID or NCT.",
            "Molecular context links are navigational only and NEVER merge distinct studies or assess causality.",
            "Patents, regulatory exclusivity and clinical evidence are separate assessment planes.",
            "OpenMI-inspired exchange envelope is NOT a compliant OpenMI runtime component.",
        ],
    }
