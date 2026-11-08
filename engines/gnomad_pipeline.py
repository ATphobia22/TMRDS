"""Live gnomAD pipeline — reference-population allele frequencies, no API key.

gnomAD GraphQL API (https://gnomad.broadinstitute.org/api) serves
exome/genome allele counts, allele numbers and frequencies for a
normalized GRCh38 variant ID (chromosome-position-reference-alternate,
e.g. 17-7676154-G-C). Verified live 2026-11-07 against TP53 P72R
(rs1042522): real exome/genome callsets and per-population breakdowns.

Validation and normalization rules are adapted from the synchronous
``GnomADAdapter`` in engines/disease_graph_model.py (including the
allele-count-must-not-exceed-allele-number guard), reimplemented here as
an async httpx pipeline following the Tier 1/2 pattern so the federated
search can call it with per-source failure isolation.

Honest limitation: gnomAD is VARIANT-addressed, not gene-addressed — a
gene symbol query returns nothing here (use Ensembl/ClinVar for genes).
Frequencies are reference-population summaries, not clinical evidence;
absence or low frequency does not establish pathogenicity, and ancestry
and coverage limitations apply. gnomad_r4 is GRCh38 only; SPDI, HGVS,
rsIDs and GRCh37 inputs are not silently translated. No published rate
limit; a courtesy throttle is applied.
"""
from __future__ import annotations

import math
import re
import time
from typing import Any

import httpx


class GnomADLookupError(RuntimeError):
    """Raised when population data cannot be obtained and validated from gnomAD."""


class GnomADPipeline:
    """Read-only access to the gnomAD GraphQL API (gnomad_r4, GRCh38)."""

    BASE = "https://gnomad.broadinstitute.org/api"
    TERMS = "https://gnomad.broadinstitute.org/about#terms"
    DATASET = "gnomad_r4"
    ASSEMBLY = "GRCh38"
    QUERY = """
    query TMRDSPopulationFrequency($variantId: String!) {
      variant(variantId: $variantId, dataset: gnomad_r4) {
        variant_id
        chrom
        pos
        ref
        alt
        rsids
        exome {
          ac
          an
          af
          populations { id ac an }
        }
        genome {
          ac
          an
          af
          populations { id ac an }
        }
      }
    }
    """

    _VARIANT_ID = re.compile(
        r"(?:[1-9]|1[0-9]|2[0-2]|X|Y|MT)-[1-9][0-9]*-[ACGTN]+-[ACGTN]+",
        flags=re.IGNORECASE,
    )

    def __init__(self, timeout: float = 30.0, min_interval: float = 0.2) -> None:
        self.timeout = timeout
        self.min_interval = min_interval
        self._last_call = 0.0

    def _throttle(self) -> None:
        wait = self.min_interval - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

    @classmethod
    def is_variant_id(cls, query: str) -> bool:
        """True when the query looks like a normalized gnomAD variant ID."""
        return bool(query and query.strip() and cls._VARIANT_ID.fullmatch(query.strip()))

    @staticmethod
    def _normalize_variant_id(variant_id: str) -> str:
        if not isinstance(variant_id, str):
            raise ValueError("variant_id must be a string")
        value = variant_id.strip()
        if len(value) > 256 or not GnomADPipeline._VARIANT_ID.fullmatch(value):
            raise ValueError(
                "variant_id must be a normalized GRCh38 gnomAD ID "
                "(chromosome-position-reference-alternate); SPDI/HGVS conversion is not implemented"
            )
        chrom, pos, ref, alt = value.split("-", 3)
        if chrom.upper() in {"X", "Y", "MT"}:
            chrom = chrom.upper()
        return f"{chrom}-{int(pos)}-{ref.upper()}-{alt.upper()}"

    @staticmethod
    def _count(value: Any, field_name: str) -> int | None:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise GnomADLookupError(f"gnomAD returned invalid {field_name}")
        return value

    @staticmethod
    def _frequency(value: Any, field_name: str) -> float | None:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise GnomADLookupError(f"gnomAD returned invalid {field_name}")
        frequency = float(value)
        if not math.isfinite(frequency) or not 0.0 <= frequency <= 1.0:
            raise GnomADLookupError(f"gnomAD returned out-of-range {field_name}")
        return frequency

    @staticmethod
    def _normalize_callset(value: Any, callset: str) -> dict[str, Any] | None:
        if value is None:
            return None
        if not isinstance(value, dict):
            raise GnomADLookupError(f"gnomAD returned malformed {callset} data")
        ac = GnomADPipeline._count(value.get("ac"), f"{callset}.ac")
        an = GnomADPipeline._count(value.get("an"), f"{callset}.an")
        af = GnomADPipeline._frequency(value.get("af"), f"{callset}.af")
        if ac is not None and an is not None and ac > an:
            raise GnomADLookupError("gnomAD allele count exceeds allele number")
        raw_populations = value.get("populations") or []
        if not isinstance(raw_populations, list):
            raise GnomADLookupError(f"gnomAD returned malformed {callset} populations")
        populations: list[dict[str, Any]] = []
        for item in raw_populations:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                raise GnomADLookupError(f"gnomAD returned malformed {callset} population row")
            pop_ac = GnomADPipeline._count(item.get("ac"), f"{callset}.population.ac")
            pop_an = GnomADPipeline._count(item.get("an"), f"{callset}.population.an")
            if pop_ac is not None and pop_an is not None and pop_ac > pop_an:
                raise GnomADLookupError("gnomAD population allele count exceeds allele number")
            pop_af = (pop_ac / pop_an) if pop_ac is not None and pop_an else None
            populations.append(
                {"id": item["id"], "ac": pop_ac, "an": pop_an, "af": pop_af, "callset": callset}
            )
        if af is None and ac is not None and an:
            af = ac / an
        return {"ac": ac, "an": an, "af": af, "populations": populations}

    async def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._throttle()
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "TMRDS/1.0 (research evidence discovery; mailto:tmrds@example.org)",
        }
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, headers=headers) as client:
            response = await client.post(self.BASE, json=payload)
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict):
            raise GnomADLookupError("gnomAD returned an unexpected response shape")
        return data

    async def fetch_variant(self, variant_id: str) -> dict[str, Any]:
        """Fetch one variant's population frequencies; raises for caller isolation."""
        normalized_id = self._normalize_variant_id(variant_id)
        payload = await self._post(
            {"query": self.QUERY, "variables": {"variantId": normalized_id}}
        )
        if payload.get("errors"):
            raise GnomADLookupError("gnomAD GraphQL query failed; no partial response was accepted")
        data = payload.get("data")
        raw_variant = data.get("variant") if isinstance(data, dict) else None
        if raw_variant is None:
            raise GnomADLookupError(
                f"Variant {normalized_id} was not found in dataset {self.DATASET}"
            )
        return self.normalize(raw_variant, normalized_id)

    async def search(self, query: str, n: int = 10) -> list[dict[str, Any]]:
        """Variant-addressed search: a normalized variant ID returns one record.

        Any other query (gene symbol, rsID, free text) returns [] — gnomAD
        cannot answer it, and an empty result is honest, not an error.
        """
        if not query or not query.strip():
            raise ValueError("query must not be empty")
        if not self.is_variant_id(query):
            return []
        return [await self.fetch_variant(query.strip())]

    @staticmethod
    def normalize(variant: dict[str, Any], normalized_id: str) -> dict[str, Any]:
        """Project one gnomAD variant record into the TMRDS common evidence shape.

        Exome and genome callsets are kept separate — they are never collapsed
        into a single allele frequency.
        """
        if not isinstance(variant, dict) or variant.get("variant_id") != normalized_id:
            raise GnomADLookupError("gnomAD returned a mismatched or malformed variant")
        chrom = str(variant.get("chrom", ""))
        pos = variant.get("pos")
        if not chrom or isinstance(pos, bool) or not isinstance(pos, int) or pos < 1:
            raise GnomADLookupError("gnomAD returned invalid variant coordinates")
        exome = GnomADPipeline._normalize_callset(variant.get("exome"), "exome")
        genome = GnomADPipeline._normalize_callset(variant.get("genome"), "genome")
        populations = [
            row
            for callset in (exome, genome)
            if callset is not None
            for row in callset["populations"]
        ]
        rsids = variant.get("rsids") or []
        title = normalized_id
        if rsids:
            title = f"{normalized_id} ({rsids[0]})"
        return {
            "title": title,
            "abstract": None,
            "authors": [],
            "published": None,
            "doi": None,
            "pmid": None,
            "nct_id": None,
            "arxiv_id": None,
            "source_url": f"https://gnomad.broadinstitute.org/variant/{normalized_id}?dataset={GnomADPipeline.DATASET}",
            "open_access_url": None,
            "journal": "gnomAD (Broad Institute)",
            "variant_id": normalized_id,
            "rsids": rsids,
            "dataset": GnomADPipeline.DATASET,
            "assembly": GnomADPipeline.ASSEMBLY,
            "exome": exome,
            "genome": genome,
            "populations": populations,
            "allele_frequency": None,  # Do not collapse exome and genome into one number.
            "is_preprint": False,
            "raw": variant,
        }
