"""Research-only biomedical connector discovery and evidence metadata gates.

A ChatGPT plugin connection is not a deployable backend credential. This module
performs no network request and never processes patient-level information.
"""
from __future__ import annotations
from datetime import datetime, timezone
from urllib.parse import urlsplit

PROVIDERS = {
    "arca": ("regulatory", "literature", "clinical_trials"),
    "litmaps": ("literature",),
    "scite": ("literature",),
    "consensus": ("literature",),
    "elicit": ("literature", "clinical_trials"),
    "prognyx": ("clinical_trials",),
    "biohub_esm": ("protein_structure",),
    "tamarind_bio": ("protein_structure", "research_compute"),
    "adaptyv_bio": ("experimental_assay",),
    "proto": ("genomics", "protein_structure", "research_compute"),
    "genomic_intelligence": ("genomics",),
    "tabulous": ("research_workspace",),
}
COMPUTE_PROVIDERS = frozenset({"biohub_esm", "tamarind_bio", "adaptyv_bio", "proto", "genomic_intelligence"})


def list_providers(domain: str | None = None) -> dict:
    """Enumerate capability targets, never imply remote account entitlement."""
    supported = {domain for domains in PROVIDERS.values() for domain in domains}
    if domain is not None and domain not in supported:
        raise ValueError("unsupported research domain")
    return {
        "research_advisory": True,
        "human_authority_final": True,
        "clinical_promotion_allowed": False,
        "connection_status_verified": False,
        "providers": [
            {
                "provider_id": name,
                "domains": list(domains),
                "status": "NOT_CONNECTED",
                "execution_enabled": False,
                "external_compute_or_order": name in COMPUTE_PROVIDERS,
            }
            for name, domains in PROVIDERS.items()
            if domain is None or domain in domains
        ],
    }


def validate_research_record(record: dict) -> dict:
    """Validate provenance metadata, NOT scientific truth, citations or efficacy."""
    if not isinstance(record, dict):
        raise TypeError("research record must be an object")
    if record.get("provider_id") not in PROVIDERS:
        raise ValueError("unknown evidence provider")
    allowed = {"provider_id", "source_id", "source_url", "retrieved_at", "summary",
               "doi", "pmid", "trial_id", "source_version", "limitations",
               "clinical_promotion_allowed", "human_authority_final"}
    if set(record) - allowed:
        raise ValueError("unexpected research metadata fields")
    for key in ("source_id", "source_url", "retrieved_at", "summary"):
        value = record.get(key)
        if not isinstance(value, str) or not value.strip() or len(value) > 4000:
            raise ValueError(f"{key} must be a bounded non-empty string")
    url = urlsplit(record["source_url"])
    if url.scheme != "https" or not url.hostname or url.username or url.password:
        raise ValueError("source_url must be a credential-free HTTPS URL")
    try:
        timestamp = datetime.fromisoformat(record["retrieved_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("retrieved_at must be ISO-8601") from exc
    if timestamp.tzinfo is None or timestamp > datetime.now(timezone.utc):
        raise ValueError("retrieved_at must be timezone-aware and not future-dated")
    if record.get("clinical_promotion_allowed") is not False or record.get("human_authority_final") is not True:
        raise ValueError("research-only human authority cannot be bypassed")
    return {**record, "status": "UNREVIEWED_SOURCE_RECORD", "research_advisory": True}
