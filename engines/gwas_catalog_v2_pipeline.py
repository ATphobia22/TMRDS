"""Bounded, read-only NHGRI–EBI GWAS Catalog v2 association adapter.

GWAS associations are literature-curated observational signals. They do NOT
establish causality, pathogenicity, therapeutic efficacy or a clinical diagnosis.
The public API is not the full summary-statistics collection.
"""
from __future__ import annotations

import math
import re
from typing import Any

import httpx


class GWASCatalogV2Error(RuntimeError):
    """Upstream returned data that cannot safely become TMRDS evidence."""


class GWASCatalogV2Pipeline:
    """Retrieve one bounded page of public trait-association metadata only."""

    BASE_URL = "https://www.ebi.ac.uk/gwas/rest/api/v2/associations"
    DOCS_URL = "https://www.ebi.ac.uk/gwas/docs/programmatic-access/rest-api/"
    MAX_PAGE_SIZE = 25
    MAX_PAYLOAD_BYTES = 1_000_000

    def __init__(self, timeout: float = 20.0) -> None:
        if not 0 < timeout <= 60:
            raise ValueError("timeout must be greater than 0 and at most 60 seconds")
        self.timeout = timeout

    @staticmethod
    def _validate_trait(query: str) -> str:
        if not isinstance(query, str):
            raise ValueError("GWAS trait query must be a string")
        if any(ord(char) < 32 or ord(char) == 127 for char in query):
            raise ValueError("GWAS trait query contains control characters")
        text = query.strip()
        if len(text) < 2 or len(text) > 120:
            raise ValueError("GWAS trait query must be 2–120 characters")
        return text

    @staticmethod
    def _identity(value: Any) -> int:
        if isinstance(value, bool) or not re.fullmatch(r"[1-9][0-9]{0,18}", str(value)):
            raise GWASCatalogV2Error("GWAS association has an invalid source identifier")
        return int(value)

    @staticmethod
    def _p_value(value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (float, int, str)):
            raise GWASCatalogV2Error("GWAS p-value is malformed")
        try:
            numeric = float(value)
        except (ValueError, OverflowError) as exc:
            raise GWASCatalogV2Error("GWAS p-value is not numeric") from exc
        if not math.isfinite(numeric) or not 0.0 <= numeric <= 1.0:
            raise GWASCatalogV2Error("GWAS p-value is out of range")
        return numeric

    @staticmethod
    def _text_list(value: Any, field: str) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise GWASCatalogV2Error("GWAS returned malformed " + field)
        return [entry[:512] for entry in value[:30]]

    @classmethod
    def normalize(cls, raw: dict[str, Any], trait_query: str, *, has_more: bool) -> dict[str, Any]:
        if not isinstance(raw, dict):
            raise GWASCatalogV2Error("GWAS association is not an object")
        association_id = cls._identity(raw.get("association_id"))
        p_value = cls._p_value(raw.get("p_value"))
        traits = raw.get("efo_traits") or []
        if not isinstance(traits, list) or any(
            not isinstance(t, dict) or not isinstance(t.get("efo_id"), str)
            or not isinstance(t.get("efo_trait"), str) for t in traits
        ):
            raise GWASCatalogV2Error("GWAS ontology traits are malformed")
        source_traits = [
            {"efo_id": t["efo_id"][:100], "efo_trait": t["efo_trait"][:300]}
            for t in traits[:30]
        ]
        reported_traits = cls._text_list(raw.get("reported_trait"), "reported_trait")
        effect_alleles = cls._text_list(raw.get("snp_effect_allele"), "snp_effect_allele")
        mapped_genes = raw.get("mapped_genes") or []
        if not isinstance(mapped_genes, list):
            raise GWASCatalogV2Error("GWAS mapped genes are malformed")
        published_pmid = raw.get("pubmed_id")
        pmid = str(published_pmid) if published_pmid is not None else None
        if pmid and not re.fullmatch(r"[1-9]\d{0,12}", pmid):
            raise GWASCatalogV2Error("GWAS PubMed identifier is malformed")
        accession_id = raw.get("accession_id")
        if accession_id is not None and (
            not isinstance(accession_id, str)
            or not re.fullmatch(r"GCST\d{1,15}", accession_id)
        ):
            raise GWASCatalogV2Error("GWAS study accession is malformed")
        name = source_traits[0]["efo_trait"] if source_traits else trait_query
        url = cls.BASE_URL + "/" + str(association_id)
        return {
            "title": f"{name} — GWAS association {association_id}",
            "abstract": None,
            "authors": [],
            "published": None,  # Association response does not contain a publication date.
            "doi": None,
            "pmid": pmid,
            "journal": "NHGRI–EBI GWAS Catalog",
            "source_url": url,  # Constructed from trusted host + validated numeric ID.
            "open_access_url": None,
            "association_id": association_id,
            "study_accession": accession_id,
            "p_value": p_value,
            "pvalue_mantissa": raw.get("pvalue_mantissa"),
            "pvalue_exponent": raw.get("pvalue_exponent"),
            "effect_description": raw.get("beta"),
            "risk_frequency_reported": raw.get("risk_frequency"),
            "snp_effect_alleles": effect_alleles,
            "reported_traits": reported_traits,
            "efo_traits": source_traits,
            "mapped_genes": mapped_genes[:30],
            "has_more": bool(has_more),
            "clinical_interpretation": "not_assessed",
            "causality_established": False,
            "study_cohort_review": "required",
            "effect_size_heterogeneity_review": "required",
            "source_api_version": "v2",
            "raw": raw,
        }

    async def search_trait(self, query: str, n: int = 10) -> list[dict[str, Any]]:
        """Get first page for an EFO-mapped trait. Do not follow upstream next links."""
        trait = self._validate_trait(query)
        if isinstance(n, bool) or not isinstance(n, int):
            raise ValueError("page size must be an integer")
        page_size = min(max(n, 1), self.MAX_PAGE_SIZE)
        params = {
            "efo_trait": trait,
            "size": page_size,
            "page": 0,
            "show_child_traits": "false",
        }
        headers = {
            "Accept": "application/json",
            "User-Agent": "TMRDS/1.0 (public biomedical metadata; https://github.com/ATphobia22/TMRDS)",
        }
        # Fixed HTTPS host, no caller-provided URL, no redirects, no credentials.
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=False, headers=headers) as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            declared_length = response.headers.get("Content-Length")
            if declared_length and declared_length.isdigit() and int(declared_length) > self.MAX_PAYLOAD_BYTES:
                raise GWASCatalogV2Error("GWAS response exceeds the source payload cap")
            if len(response.content) > self.MAX_PAYLOAD_BYTES:
                raise GWASCatalogV2Error("GWAS response exceeds the source payload cap")
            try:
                payload = response.json()
            except ValueError as exc:
                raise GWASCatalogV2Error("GWAS returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise GWASCatalogV2Error("GWAS response must be an object")
        embedded = payload.get("_embedded")
        if not isinstance(embedded, dict) or not isinstance(embedded.get("associations"), list):
            raise GWASCatalogV2Error("GWAS response has no association list")
        records = embedded["associations"]
        if len(records) > page_size:
            raise GWASCatalogV2Error("GWAS response exceeded requested page size")
        links = payload.get("_links") or {}
        if not isinstance(links, dict):
            raise GWASCatalogV2Error("GWAS response links are malformed")
        has_more = bool(links.get("next"))
        return [self.normalize(record, trait, has_more=has_more) for record in records]
