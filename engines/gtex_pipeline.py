"""Live GTEx Portal pipeline — single-tissue eQTL associations, no API key.

GTEx Portal API v2 (https://gtexportal.org/api/v2) serves expression
quantitative trait loci (eQTLs) linking variants to gene expression per
tissue. Verified live 2026-11-07: TP53 (ENSG00000141510.18) returns 51
single-tissue eQTLs in gtex_v10; gene-expression and gene-reference
endpoints return real records for the same gene.

Validation and response-shape rules are adapted from the synchronous
``GTExAdapter`` in engines/disease_graph_model.py (versioned GENCODE ID
requirement, dataset allowlist, data + paging_info shape checks,
dataset/gene mismatch guards, explicit partial-page flagging),
reimplemented here as an async httpx pipeline following the Tier 1/2
pattern so the federated search can call it with per-source failure
isolation.

Endpoint note: the wired endpoint is ``singleTissueEqtl``. The
``independentEqtl`` endpoint used by the earlier synchronous adapter was
checked live on 2026-11-07 and returns genuinely empty results for TP53
in both gtex_v8 and gtex_v10 (conditionally independent signals are
sparse); an empty result is reported as zero records, never as an error.
A tissue with no eQTL for a gene (e.g. TP53 in Whole_Blood) likewise
returns zero records honestly.

GENCODE-version note (verified live 2026-11-07): eQTL records are keyed
to the GENCODE release of their dataset — gtex_v10 pairs with GENCODE
v39 (TP53 is ENSG00000141510.18) and gtex_v8 pairs with GENCODE v26
(TP53 is ENSG00000141510.16); the other versions return genuinely empty
results. Symbol resolution therefore passes the dataset-matched
``gencodeVersion`` to the reference endpoint and requests a wide page
(prefix search returns ~22 rows for TP53, with the exact symbol at
index 17).

Honest limitation: eQTL associations are population-level observational
statistics — not causal claims and not clinical interpretations. Gene
symbols resolve through the GTEx reference endpoint with an exact-symbol
match only; ambiguous or unmatched symbols return no records. Only the
first bounded page is fetched; additional pages are flagged, not silently
fetched. No published rate limit; a courtesy throttle is applied.
"""
from __future__ import annotations

import re
import time
from typing import Any

import httpx


class GTExLookupError(RuntimeError):
    """Raised when QTL data cannot be obtained and validated from GTEx."""


class GTExPipeline:
    """Read-only access to the GTEx Portal API v2 (gtex_v10 by default)."""

    BASE = "https://gtexportal.org/api/v2"
    TERMS = "https://gtexportal.org/home/apiPage"
    DATASETS = {"gtex_v8", "gtex_v10", "gtex_snrnaseq_pilot"}
    DEFAULT_DATASET = "gtex_v10"
    # eQTL records are keyed to the GENCODE release of their dataset
    # (verified live 2026-11-07); unmapped datasets fall back to v39.
    GENCODE_VERSIONS = {"gtex_v10": "v39", "gtex_v8": "v26"}

    _GENCODE_ID = re.compile(r"ENSG[0-9]{11}\.[0-9]+")

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
    def is_gencode_id(cls, query: str) -> bool:
        """True when the query is a versioned GENCODE ID (ENSG…​.N)."""
        return bool(query and query.strip() and cls._GENCODE_ID.fullmatch(query.strip()))

    @staticmethod
    def _normalize_gencode_id(ensembl_gene_id: str) -> str:
        if not isinstance(ensembl_gene_id, str):
            raise ValueError("ensembl_gene_id must be a string")
        value = ensembl_gene_id.strip()
        if not GTExPipeline._GENCODE_ID.fullmatch(value):
            raise ValueError(
                "ensembl_gene_id must be a versioned GTEx GENCODE ID such as ENSG00000141510.18"
            )
        return value

    @staticmethod
    def _validate_dataset(dataset_id: str) -> str:
        if dataset_id not in GTExPipeline.DATASETS:
            raise ValueError(f"dataset_id must be one of {sorted(GTExPipeline.DATASETS)}")
        return dataset_id

    async def _get(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        self._throttle()
        headers = {
            "Accept": "application/json",
            "User-Agent": "TMRDS/1.0 (research evidence discovery; mailto:tmrds@example.org)",
        }
        url = f"{self.BASE}{endpoint}"
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, headers=headers) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict):
            raise GTExLookupError("GTEx returned an unexpected response shape")
        return data

    @staticmethod
    def _validate_paging(paging: Any) -> tuple[int | None, int | None]:
        if not isinstance(paging, dict):
            raise GTExLookupError("GTEx response is missing data or paging metadata")
        total_results = paging.get("totalNumberOfItems")
        if total_results is not None and (
            isinstance(total_results, bool) or not isinstance(total_results, int) or total_results < 0
        ):
            raise GTExLookupError("GTEx returned invalid total result count")
        total_pages = paging.get("numberOfPages")
        if total_pages is not None and (
            isinstance(total_pages, bool) or not isinstance(total_pages, int) or total_pages < 0
        ):
            raise GTExLookupError("GTEx returned invalid page count")
        return total_results, total_pages

    async def resolve_gene_symbol(self, symbol: str, dataset_id: str = DEFAULT_DATASET) -> str | None:
        """Resolve a gene symbol to a versioned GENCODE ID via GTEx reference.

        Exact symbol match only (case-insensitive); returns None when the
        symbol does not match exactly. The dataset-matched GENCODE version
        is requested so the returned ID is the one the eQTL data is keyed
        to. Raises for caller isolation on transport or shape failures.
        """
        if not symbol or not symbol.strip():
            raise ValueError("symbol must not be empty")
        self._validate_dataset(dataset_id)
        payload = await self._get(
            "/reference/geneSearch",
            {
                "geneId": symbol.strip(),
                "gencodeVersion": self.GENCODE_VERSIONS.get(dataset_id, "v39"),
                "page": 0,
                "itemsPerPage": 100,
            },
        )
        raw_records = payload.get("data")
        if not isinstance(raw_records, list):
            raise GTExLookupError("GTEx gene search returned an unexpected response shape")
        wanted = symbol.strip().upper()
        for row in raw_records:
            if not isinstance(row, dict):
                raise GTExLookupError("GTEx gene search returned a malformed record")
            if (row.get("geneSymbol") or "").upper() == wanted:
                gencode_id = row.get("gencodeId")
                if isinstance(gencode_id, str) and self._GENCODE_ID.fullmatch(gencode_id):
                    return gencode_id
        return None

    async def fetch_eqtls(
        self,
        ensembl_gene_id: str,
        dataset_id: str = DEFAULT_DATASET,
        tissue_ids: list[str] | None = None,
        max_results: int = 100,
    ) -> dict[str, Any]:
        """Fetch one bounded page of real single-tissue eQTL records.

        Returns the normalized records plus paging metadata; the caller
        sees whether more pages remain. Raises for caller isolation.
        """
        gene_id = self._normalize_gencode_id(ensembl_gene_id)
        self._validate_dataset(dataset_id)
        if isinstance(max_results, bool) or not isinstance(max_results, int) or not 1 <= max_results <= 1000:
            raise ValueError("max_results must be an integer between 1 and 1000")
        normalized_tissues: list[str] = []
        for tissue in tissue_ids or []:
            if not isinstance(tissue, str) or not re.fullmatch(r"[A-Za-z0-9_:-]{1,128}", tissue):
                raise ValueError("tissue_ids must contain valid GTEx tissue IDs")
            normalized_tissues.append(tissue)
        if len(normalized_tissues) > 10:
            raise ValueError("at most 10 tissue IDs may be queried per call")
        params: dict[str, Any] = {
            "gencodeId": gene_id,
            "datasetId": dataset_id,
            "page": 0,
            "itemsPerPage": max_results,
        }
        if normalized_tissues:
            params["tissueSiteDetailId"] = normalized_tissues
        payload = await self._get("/association/singleTissueEqtl", params)
        raw_records = payload.get("data")
        total_results, total_pages = self._validate_paging(payload.get("paging_info"))
        if not isinstance(raw_records, list):
            raise GTExLookupError("GTEx response is missing data or paging metadata")
        records: list[dict[str, Any]] = []
        for row in raw_records:
            if not isinstance(row, dict):
                raise GTExLookupError("GTEx returned a malformed eQTL record")
            if row.get("datasetId") not in (None, dataset_id):
                raise GTExLookupError("GTEx returned records from an unexpected dataset")
            row_gene_id = row.get("gencodeId")
            if row_gene_id and row_gene_id != gene_id:
                raise GTExLookupError("GTEx returned a record for a different gene")
            records.append(self.normalize(row, dataset_id))
        is_partial = bool(total_pages and total_pages > 1)
        return {
            "records": records,
            "total_results": total_results,
            "total_pages": total_pages,
            "is_partial": is_partial,
            "dataset_id": dataset_id,
            "gencode_id": gene_id,
        }

    async def search(self, query: str, n: int = 10) -> list[dict[str, Any]]:
        """Gene-addressed search: a symbol or versioned GENCODE ID returns eQTLs.

        A query that is neither returns [] — GTEx cannot answer it, and an
        empty result is honest, not an error.
        """
        if not query or not query.strip():
            raise ValueError("query must not be empty")
        query = query.strip()
        if self.is_gencode_id(query):
            gene_id = query
        else:
            gene_id = await self.resolve_gene_symbol(query)
            if gene_id is None:
                return []
        result = await self.fetch_eqtls(gene_id, max_results=max(1, min(n, 100)))
        records = result["records"]
        if result["is_partial"]:
            for rec in records:
                rec["has_more"] = True
        return records

    @staticmethod
    def normalize(row: dict[str, Any], dataset_id: str) -> dict[str, Any]:
        """Project one GTEx single-tissue eQTL row into the TMRDS common evidence shape."""
        gencode_id = row.get("gencodeId")
        gene_symbol = row.get("geneSymbol")
        snp_id = row.get("snpId")
        tissue = row.get("tissueSiteDetailId")
        title = f"{gene_symbol or gencode_id} eQTL"
        if snp_id:
            title += f" {snp_id}"
        if tissue:
            title += f" ({tissue})"
        return {
            "title": title,
            "abstract": None,
            "authors": [],
            "published": None,
            "doi": None,
            "pmid": None,
            "nct_id": None,
            "arxiv_id": None,
            "source_url": f"https://gtexportal.org/home/gene/{gencode_id}" if gencode_id else "https://gtexportal.org/",
            "open_access_url": None,
            "journal": "GTEx Portal",
            "snp_id": snp_id,
            "variant_id": row.get("variantId"),
            "p_value": row.get("pValue"),
            "nes": row.get("nes"),
            "tissue": tissue,
            "ontology_id": row.get("ontologyId"),
            "chromosome": row.get("chromosome"),
            "pos": row.get("pos"),
            "gencode_id": gencode_id,
            "gene_symbol": gene_symbol,
            "dataset_id": dataset_id,
            "is_preprint": False,
            "raw": row,
        }
