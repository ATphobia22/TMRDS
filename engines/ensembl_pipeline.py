"""Live Ensembl REST pipeline — genomic reference data, no API key.

Ensembl REST (https://rest.ensembl.org) serves genes, transcripts,
sequences, variant consequences (VEP), and region queries for the current
assembly (GRCh38); GRCh37 via https://grch37.rest.ensembl.org. Verified
live 2026-10-18 and 2026-10-23; VEP POST verified live 2026-11-08
(ENST00000269305:c.215C>G, TP53 P72R: missense, SIFT tolerated, PolyPhen
benign, 39 transcript consequences) and region GET verified live the same
day (17:7675218, missense, 39 transcript consequences).

Honest limitation: 55,000 requests/hour per IP with 429 + Retry-After on
exceed; bulk annotation belongs on local VEP or batched POSTs. VEP
consequence predictions are computational evidence, not clinical
assertions. Assembly matters — always record which assembly was queried.
Free for all uses; cite Ensembl.

VEP input rule (verified live): Ensembl transcript IDs (ENST…) resolve;
RefSeq NM_ accessions are REJECTED by Ensembl and are refused client-side
with a clear error instead of a confusing server 400. VEP is a capability
of the same Ensembl REST source — it is not counted as a second source.
"""
from __future__ import annotations

import re
import time
from typing import Any

import httpx


class EnsemblLookupError(RuntimeError):
    """Raised when a VEP annotation cannot be obtained and validated from Ensembl."""


class EnsemblPipeline:
    """Read-only access to the Ensembl REST API (GRCh38 by default)."""

    BASE_URL = "https://rest.ensembl.org"

    # HGVS notations Ensembl VEP accepts here: Ensembl transcript IDs
    # (ENST…:c./n./r.) and chromosome genomic (17:g.…) forms. RefSeq
    # NM_/NR_/NP_ accessions are rejected by Ensembl — refused client-side.
    _HGVS_ENST = re.compile(r"ENST\d+(?:\.\d+)?:[cnmr]\..+", flags=re.IGNORECASE)
    _HGVS_GENOMIC = re.compile(
        r"(?:[1-9]|1[0-9]|2[0-2]|X|Y|MT):g\..+", flags=re.IGNORECASE
    )
    _REFSEQ = re.compile(r"(?:NM|NR|NP|XM|XR|XP)_", flags=re.IGNORECASE)
    # Region query: 17:7675218-7675218:1/G (chrom:start-end:strand/alt).
    _REGION = re.compile(
        r"^(?:chr)?([1-9]|1[0-9]|2[0-2]|X|Y|MT):(\d+)-(\d+):(-?1)/([ACGTN]+)$",
        flags=re.IGNORECASE,
    )

    def __init__(self, timeout: float = 30.0, min_interval: float = 0.1) -> None:
        self.timeout = timeout
        self.min_interval = min_interval
        self._last_call = 0.0

    def _throttle(self) -> None:
        wait = self.min_interval - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        self._throttle()
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "TMRDS/1.0 (research evidence discovery; mailto:tmrds@example.org)",
        }
        url = f"{self.BASE_URL}{path}"
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, headers=headers) as client:
            response = await client.get(url, params=params or {})
            response.raise_for_status()
            return response.json()

    async def _post(self, path: str, payload: dict[str, Any]) -> Any:
        """POST with a longer read timeout: VEP annotation took 26 s live once."""
        self._throttle()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "TMRDS/1.0 (research evidence discovery; mailto:tmrds@example.org)",
        }
        url = f"{self.BASE_URL}{path}"
        timeout = httpx.Timeout(60.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()

    @classmethod
    def is_hgvs_notation(cls, query: str) -> bool:
        """True when the query looks like an HGVS notation Ensembl VEP accepts."""
        value = (query or "").strip()
        return bool(value) and bool(cls._HGVS_ENST.match(value) or cls._HGVS_GENOMIC.match(value))

    @classmethod
    def is_region_query(cls, query: str) -> tuple[str, int, int, int, str] | None:
        """Parse a region query (17:7675218-7675218:1/G) or return None."""
        match = cls._REGION.match((query or "").strip())
        if not match:
            return None
        chrom, start, end, strand, alt = match.groups()
        if int(start) > int(end) or int(start) < 1:
            return None
        return chrom.upper(), int(start), int(end), int(strand), alt.upper()

    @staticmethod
    def _check_hgvs_notation(notation: str) -> str:
        if not isinstance(notation, str) or not notation.strip():
            raise ValueError("HGVS notation must not be empty")
        value = notation.strip()
        if EnsemblPipeline._REFSEQ.search(value):
            raise ValueError(
                "Ensembl VEP does not resolve RefSeq accessions (NM_/NR_/NP_); "
                "use an Ensembl transcript ID (ENST…) or a chromosome genomic form (17:g.…)"
            )
        if not EnsemblPipeline.is_hgvs_notation(value):
            raise ValueError(
                "not a recognized HGVS notation for Ensembl VEP "
                "(expected ENST…:c./n./r.… or chromosome:g.…)"
            )
        return value

    async def annotate_hgvs(self, hgvs_notations: list[str]) -> list[dict[str, Any]]:
        """Annotate HGVS notations via POST /vep/human/hgvs; raises for caller isolation.

        RefSeq NM_ accessions are refused client-side (Ensembl rejects them).
        One notation returns one normalized record; the server may return an
        "error" entry per notation instead of an annotation — that is raised,
        never returned as a record.
        """
        if not hgvs_notations or not isinstance(hgvs_notations, list):
            raise ValueError("hgvs_notations must be a non-empty list")
        if len(hgvs_notations) > 200:
            raise ValueError("at most 200 HGVS notations per VEP POST")
        checked = [self._check_hgvs_notation(n) for n in hgvs_notations]
        data = await self._post("/vep/human/hgvs", {"hgvs_notations": checked})
        if not isinstance(data, list):
            raise EnsemblLookupError("Ensembl VEP returned an unexpected response shape")
        out = []
        for item in data:
            if not isinstance(item, dict):
                raise EnsemblLookupError("Ensembl VEP returned a malformed annotation")
            if item.get("error"):
                raise EnsemblLookupError(f"Ensembl VEP could not annotate {item.get('input')}: {item['error']}")
            out.append(self.normalize_vep(item))
        return out

    async def annotate_region(self, chrom: str, start: int, end: int, strand: int, alt: str) -> list[dict[str, Any]]:
        """Annotate one region allele via GET /vep/human/region; raises for caller isolation."""
        if strand not in (1, -1):
            raise ValueError("strand must be 1 or -1")
        if start < 1 or end < start or not alt or not re.fullmatch(r"[ACGTN]+", alt, flags=re.IGNORECASE):
            raise ValueError("invalid region allele for Ensembl VEP")
        data = await self._get(
            f"/vep/human/region/{chrom}:{start}-{end}:{strand}/{alt.upper()}",
            {"content-type": "application/json"},
        )
        if not isinstance(data, list):
            raise EnsemblLookupError("Ensembl VEP returned an unexpected response shape")
        out = []
        for item in data:
            if not isinstance(item, dict):
                raise EnsemblLookupError("Ensembl VEP returned a malformed annotation")
            if item.get("error"):
                raise EnsemblLookupError(f"Ensembl VEP could not annotate {item.get('input')}: {item['error']}")
            out.append(self.normalize_vep(item))
        return out

    async def search(self, query: str, n: int = 10) -> list[dict[str, Any]]:
        """Dispatch one query to the right Ensembl capability.

        HGVS notation → VEP annotation; region query → VEP region lookup;
        anything else → gene-symbol lookup (None → []). VEP and gene lookup
        are two capabilities of the same Ensembl REST source, not two sources.
        """
        if not query or not query.strip():
            raise ValueError("query must not be empty")
        value = query.strip()
        if self.is_hgvs_notation(value):
            return await self.annotate_hgvs([value])
        region = self.is_region_query(value)
        if region is not None:
            return await self.annotate_region(*region)
        gene = await self.lookup_gene(value)
        return [gene] if gene is not None else []

    @staticmethod
    def normalize_vep(result: dict[str, Any]) -> dict[str, Any]:
        """Project one Ensembl VEP annotation into the TMRDS common evidence shape.

        SIFT/PolyPhen are computational predictions, never clinical
        interpretations. The response carries no per-transcript HGVSc/HGVSp
        fields, so none are invented — the input notation is the identifier.
        """
        if not isinstance(result, dict):
            raise EnsemblLookupError("Ensembl VEP returned a malformed annotation")
        assembly = result.get("assembly_name")
        if assembly != "GRCh38":
            raise EnsemblLookupError(f"Ensembl VEP returned unexpected assembly {assembly!r}; expected GRCh38")
        consequences = result.get("transcript_consequences")
        if not isinstance(consequences, list):
            raise EnsemblLookupError("Ensembl VEP annotation has no transcript consequences")
        most_severe = result.get("most_severe_consequence")
        if not isinstance(most_severe, str) or not most_severe:
            raise EnsemblLookupError("Ensembl VEP annotation has no most-severe consequence")
        trimmed_consequences = []
        for item in consequences[:100]:
            if not isinstance(item, dict):
                continue
            trimmed_consequences.append({
                "transcript_id": item.get("transcript_id"),
                "gene_symbol": item.get("gene_symbol"),
                "gene_id": item.get("gene_id"),
                "consequence_terms": item.get("consequence_terms") or [],
                "amino_acids": item.get("amino_acids"),
                "sift_prediction": item.get("sift_prediction"),
                "sift_score": item.get("sift_score"),
                "polyphen_prediction": item.get("polyphen_prediction"),
                "polyphen_score": item.get("polyphen_score"),
                "impact": item.get("impact"),
                "biotype": item.get("biotype"),
                "variant_allele": item.get("variant_allele"),
            })
        colocated = []
        for item in (result.get("colocated_variants") or [])[:50]:
            if not isinstance(item, dict):
                continue
            colocated.append({
                "id": item.get("id"),
                "allele_string": item.get("allele_string"),
                "clin_sig": item.get("clin_sig"),
                "phenotype_or_disease": item.get("phenotype_or_disease"),
                "somatic": item.get("somatic"),
            })
        rsid = next((c["id"] for c in colocated if isinstance(c.get("id"), str) and c["id"].startswith("rs")), None)
        input_notation = result.get("input") or result.get("id")
        return {
            "title": f"{input_notation} — {most_severe}" if input_notation else most_severe,
            "abstract": None,
            "authors": [],
            "published": None,
            "doi": None,
            "pmid": None,
            "nct_id": None,
            "arxiv_id": None,
            "source_url": (
                f"https://www.ensembl.org/Homo_sapiens/Variation/Explore?v={rsid}"
                if rsid else "https://rest.ensembl.org/"
            ),
            "open_access_url": None,
            "journal": "Ensembl VEP (EBI/EMBL)",
            "input_notation": input_notation,
            "most_severe_consequence": most_severe,
            "assembly": assembly,
            "location": f"{result.get('seq_region_name')}:{result.get('start')}-{result.get('end')}"
            if result.get("seq_region_name") else None,
            "strand": result.get("strand"),
            "allele_string": result.get("allele_string"),
            "transcript_consequences": trimmed_consequences,
            "transcript_consequence_count": len(trimmed_consequences),
            "colocated_variants": colocated,
            "research_only": True,
            "clinician_review_required": True,
            "predictions_are_computational": True,
            "is_preprint": False,
            "raw": result,
        }

    async def lookup_gene(self, symbol: str, species: str = "homo_sapiens") -> dict[str, Any] | None:
        """Look up a gene by symbol; raises for caller isolation; None if not found."""
        if not symbol.strip():
            raise ValueError("symbol must not be empty")
        try:
            data = await self._get(
                f"/lookup/symbol/{species}/{symbol.strip()}",
                {"content-type": "application/json", "expand": 0},
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise
        if not isinstance(data, dict):
            raise ValueError("Ensembl returned an unexpected response shape")
        return self.normalize(data, species)

    @staticmethod
    def normalize(gene: dict[str, Any], species: str = "homo_sapiens") -> dict[str, Any]:
        """Project one Ensembl gene record into the TMRDS common evidence shape."""
        stable_id = gene.get("id")
        return {
            "title": f"{gene.get('display_name')} ({stable_id})" if stable_id else gene.get("display_name"),
            "abstract": gene.get("description"),
            "authors": [],
            "published": None,
            "doi": None,
            "pmid": None,
            "nct_id": None,
            "arxiv_id": None,
            "source_url": (
                f"https://www.ensembl.org/{species.replace('_', ' ').title().replace(' ', '_')}/Gene/Summary?g={stable_id}"
                if stable_id else None
            ),
            "open_access_url": None,
            "journal": "Ensembl (EBI/EMBL)",
            "ensembl_id": stable_id,
            "display_name": gene.get("display_name"),
            "biotype": gene.get("biotype"),
            "assembly": gene.get("assembly_name"),
            "location": f"{gene.get('seq_region_name')}:{gene.get('start')}-{gene.get('end')}"
            if gene.get("seq_region_name") else None,
            "is_preprint": False,
            "raw": gene,
        }
