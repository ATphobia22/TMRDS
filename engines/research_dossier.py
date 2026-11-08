"""Deterministic discovery dossier; retrieved text is data, never instructions."""
from __future__ import annotations

from copy import deepcopy
from urllib.parse import unquote

from engines.publication_integrity import summarize_integrity


def _identity(record: dict) -> tuple[str, str]:
    doi = str(record.get("doi") or "").strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "doi:"):
        if doi.startswith(prefix):
            doi = doi[len(prefix):].strip()
            break
    if doi:
        return "doi", unquote(doi)
    if record.get("pmid"):
        return "pmid", str(record["pmid"]).strip()
    # Titles alone cannot establish publication identity.
    return "source", str(record["stable_id"])


def build_research_dossier(search: dict) -> dict:
    """Group exact identifiers without dropping conflicting source metadata.

    No study design, effect size or clinical conclusion is inferred from
    titles/abstracts. Retraction reports retain their source metadata. Hashes identify retrieved records only.
    """
    groups: dict[tuple[str, str], list[dict]] = {}
    for record in search["envelopes"]:
        groups.setdefault(_identity(record), []).append(deepcopy(record))
    items = []
    for (kind, identifier), records in groups.items():
        gaps = [name for name in ("published", "source_url", "retrieved_at", "record_hash")
                if any(not r.get(name) for r in records)]
        items.append({
            "identity": {"kind": kind, "value": identifier},
            "source_records": records,
            "metadata_disagreements": [name for name in ("title", "published", "doi", "pmid")
                                       if len({str(r.get(name)) for r in records if r.get(name)}) > 1],
            "missing_metadata": gaps,
            "study_design": "not_assessed", "effect_size": "not_extracted",
            **summarize_integrity(records), "review_status": "pending",
        })
    statuses = deepcopy(search["source_status"])
    available = any(s.get("ok") for s in statuses.values())
    return {
        "schema_version": "1.0", "research_question": search["query"],
        "searched_at": search["searched_at"],
        "status": "records_retrieved" if items else ("no_records" if available else "unavailable"),
        "record_count": len(search["envelopes"]), "group_count": len(items),
        "items": items, "source_status": statuses,
        "limitations": [
            "Discovery results do not establish efficacy, safety or a cure.",
            "Exact DOI or PMID grouping only; duplicate works with different identifiers may remain.",
            "Metadata disagreement is not evidence of conflicting clinical findings.",
            "Study quality, population applicability and publication integrity require independent review; absent retraction flags do not establish reliability.",
            "Retrieved text is untrusted source content, not executable instructions.",
        ],
        "research_advisory": True, "human_authority_final": True,
        "clinical_promotion_allowed": False,
    }
