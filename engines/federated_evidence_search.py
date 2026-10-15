"""Federated live evidence search for the TMRDS Quantum Rubik's Cube workspace.

Orchestrates the repository's live, read-only source pipelines
(Europe PMC, PubMed/E-utilities, ClinicalTrials.gov, openFDA, OpenAlex,
arXiv, AlphaFold DB) into normalized evidence envelopes with per-source
provenance. Every source runs isolated: one source failing never poisons
the others, and failures are reported as warnings — never as invented
records.

Research discovery only. Not SaMD. Not diagnostic, prescribing, or
treatment direction. Human clinical authority remains final.

Sources that require credentials or paid access (Lens patents, IBM Quantum
hardware, NOAA CDO) are reported as unavailable with instructions, never
mocked.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx

from engines.arxiv_pipeline import ArxivPipeline
from engines.clinical_trials_pipeline import ClinicalTrialsPipeline
from engines.europe_pmc_pipeline import EuropePMCPipeline
from engines.openalex_pipeline import OpenAlexPipeline
from engines.openfda_pipeline import OpenFDAPipeline
from engines.pubmed_literature_bridge import PubMedLiteratureBridge

AFDB_API = "https://alphafold.ebi.ac.uk/api/prediction"

COVERAGE = {
    "europe_pmc": "Europe PMC REST: open metadata + OA subset; check per-item license; not all biomedical literature.",
    "pubmed": "PubMed/Entrez E-utilities: MEDLINE subset; rate-limited; not all biomedical literature.",
    "clinicaltrials_gov": "ClinicalTrials.gov API v2: registry-native statuses/identifiers; protocol data only; not an outcomes guarantee.",
    "openfda": "openFDA: labels/FAERS signals for safety/regulatory context only; not for care decisions.",
    "openalex": "OpenAlex: open scholarly metadata incl. preprints; coverage varies by publisher.",
    "arxiv": "arXiv: preprints, not peer-reviewed; quantitative biology subset most relevant.",
    "alphafold_db": "AlphaFold DB: predicted structures; confidence metrics only from genuine API responses.",
    "lens_patents": "Lens Patents: requires an API token; unavailable without credentials. Not legal advice.",
    "ibm_quantum": "IBM Quantum: requires API key + instance CRN; unavailable without credentials.",
}


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _record_hash(payload: Any) -> str:
    try:
        canonical = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False)
    except Exception:
        canonical = str(payload)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _make_envelope(source: str, source_name: str, record: dict[str, Any], evidence_class: str) -> dict[str, Any]:
    core = {k: record.get(k) for k in ("title", "abstract", "authors", "published", "doi", "pmid", "nct_id", "arxiv_id", "source_url", "journal")}
    stable_seed = record.get("doi") or record.get("pmid") or record.get("nct_id") or record.get("arxiv_id") or record.get("source_url") or record.get("title")
    return {
        "stable_id": f"{source}:{_record_hash(stable_seed)[:16]}",
        "source": source,
        "source_name": source_name,
        "evidence_class": evidence_class,
        "is_mock": False,
        "is_authoritative": False,
        "title": record.get("title"),
        "abstract": record.get("abstract"),
        "authors": record.get("authors") or [],
        "published": record.get("published"),
        "doi": record.get("doi"),
        "pmid": record.get("pmid"),
        "nct_id": record.get("nct_id"),
        "arxiv_id": record.get("arxiv_id"),
        "journal": record.get("journal"),
        "source_url": record.get("source_url"),
        "open_access_url": record.get("open_access_url"),
        "retrieved_at": _utcnow(),
        "record_hash": _record_hash(core),
        "coverage": COVERAGE.get(source, ""),
        "warnings": [],
    }


@dataclass
class SourceResult:
    source: str
    ok: bool
    envelopes: list[dict[str, Any]] = field(default_factory=list)
    warning: str | None = None
    count: int = 0


class FederatedEvidenceSearch:
    """Run live searches across all credential-free sources with failure isolation."""

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout
        self.europepmc = EuropePMCPipeline()
        self.pubmed = PubMedLiteratureBridge()
        self.trials = ClinicalTrialsPipeline()
        self.openfda = OpenFDAPipeline()
        self.openalex = OpenAlexPipeline()
        self.arxiv = ArxivPipeline()

    async def _guard(self, source: str, coro) -> SourceResult:
        try:
            envelopes = await coro
            return SourceResult(source=source, ok=True, envelopes=envelopes, count=len(envelopes))
        except Exception as exc:  # noqa: BLE001 — isolate per source, report honestly
            return SourceResult(source=source, ok=False, warning=f"{source} unavailable: {type(exc).__name__}: {str(exc)[:160]}")

    async def search_all(self, query: str, per_source: int = 10) -> dict[str, Any]:
        """Search every live source concurrently. Never raises for a single-source failure."""
        if not query or not query.strip():
            raise ValueError("query must not be empty")
        query = query.strip()
        results = await asyncio.gather(
            self._guard("europe_pmc", self._search_europepmc(query, per_source)),
            self._guard("pubmed", self._search_pubmed(query, per_source)),
            self._guard("clinicaltrials_gov", self._search_trials(query, per_source)),
            self._guard("openfda", self._search_openfda(query, per_source)),
            self._guard("openalex", self._search_openalex(query, per_source)),
            self._guard("arxiv", self._search_arxiv(query, per_source)),
        )
        envelopes: list[dict[str, Any]] = []
        source_status: dict[str, dict[str, Any]] = {}
        for r in results:
            envelopes.extend(r.envelopes)
            source_status[r.source] = {
                "ok": r.ok,
                "count": r.count,
                "warning": r.warning,
                "coverage": COVERAGE[r.source],
            }
        # credential-gated sources: reported, never mocked
        for gated in ("lens_patents", "ibm_quantum"):
            source_status[gated] = {
                "ok": False,
                "count": 0,
                "warning": f"{gated} requires credentials; not queried. {COVERAGE[gated]}",
                "coverage": COVERAGE[gated],
            }
        deduped = self._dedupe(envelopes)
        return {
            "query": query,
            "searched_at": _utcnow(),
            "total_envelopes": len(deduped),
            "envelopes": deduped,
            "source_status": source_status,
            "governance": {
                "research_advisory_only": True,
                "human_authority_final": True,
                "not_samd": True,
                "no_mock_records": True,
            },
        }

    def search_all_sync(self, query: str, per_source: int = 10) -> dict[str, Any]:
        return asyncio.run(self.search_all(query, per_source))

    # ---- per-source adapters (live HTTP only) ----

    async def _search_europepmc(self, query: str, n: int) -> list[dict[str, Any]]:
        data = await self.europepmc.search(query, n)
        out = []
        for r in (data.get("resultList") or {}).get("result") or []:
            rec = {
                "title": r.get("title"),
                "abstract": r.get("abstractText"),
                "authors": [a.get("fullName") for a in (r.get("authorList") or {}).get("author") or [] if a.get("fullName")],
                "published": r.get("firstPublicationDate") or r.get("pubYear"),
                "doi": r.get("doi"),
                "pmid": r.get("pmid"),
                "journal": r.get("journalTitle"),
                "source_url": f"https://europepmc.org/article/{r.get('source')}/{r.get('id')}" if r.get("id") else None,
            }
            out.append(_make_envelope("europe_pmc", "Europe PMC", rec, "preprint" if (r.get("source") or "") == "PPR" else "citation"))
        return out

    async def _search_pubmed(self, query: str, n: int) -> list[dict[str, Any]]:
        # PubMedLiteratureBridge is synchronous; run in a thread.
        bridge = self.pubmed
        search_data = await asyncio.to_thread(bridge.search, query, n)
        if search_data.get("status") == "ERROR":
            raise RuntimeError(str(search_data.get("error") or "PubMed E-utilities error"))
        pmids = search_data.get("pmids") or []
        summaries = await asyncio.to_thread(bridge.summaries, pmids[:n]) if pmids else {"articles": []}
        out = []
        for a in summaries.get("articles") or []:
            rec = {
                "title": a.get("title"),
                "abstract": None,
                "authors": a.get("authors") or [],
                "published": a.get("pubdate"),
                "doi": None,
                "pmid": a.get("pmid"),
                "journal": a.get("source"),
                "source_url": f"https://pubmed.ncbi.nlm.nih.gov/{a.get('pmid')}/" if a.get("pmid") else None,
            }
            out.append(_make_envelope("pubmed", "PubMed", rec, "citation"))
        return out

    async def _search_trials(self, query: str, n: int) -> list[dict[str, Any]]:
        data = await self.trials.search(query, n)
        out = []
        for s in data.get("studies") or []:
            proto = s.get("protocolSection") or {}
            status_mod = proto.get("statusModule") or {}
            ident = proto.get("identificationModule") or {}
            cond = proto.get("conditionsModule") or {}
            rec = {
                "title": (ident.get("briefTitle") or ident.get("officialTitle")),
                "abstract": (ident.get("briefSummary")),
                "authors": [],
                "published": status_mod.get("studyFirstSubmitDate"),
                "doi": None,
                "pmid": None,
                "nct_id": ident.get("nctId"),
                "journal": None,
                "source_url": f"https://clinicaltrials.gov/study/{ident.get('nctId')}" if ident.get("nctId") else None,
            }
            env = _make_envelope("clinicaltrials_gov", "ClinicalTrials.gov", rec, "trial")
            env["trial_status"] = status_mod.get("overallStatus")
            env["conditions"] = cond.get("conditions")
            out.append(env)
        return out

    async def _search_openfda(self, query: str, n: int) -> list[dict[str, Any]]:
        data = await self.openfda.drug_labels(query, n)
        out = []
        for r in data.get("results") or []:
            oid = r.get("id")
            rec = {
                "title": (r.get("openfda") or {}).get("brand_name", [None])[0] or r.get("description", [""])[0][:120] if r.get("description") else None,
                "abstract": None,
                "authors": [],
                "published": None,
                "doi": None,
                "pmid": None,
                "journal": None,
                "source_url": f"https://api.fda.gov/drug/label.json?search=id:\"{oid}\"" if oid else "https://api.fda.gov/drug/label.json",
            }
            env = _make_envelope("openfda", "openFDA", rec, "regulatory_signal")
            env["warnings"].append("Regulatory signal only; not for care decisions.")
            out.append(env)
        return out

    async def _search_openalex(self, query: str, n: int) -> list[dict[str, Any]]:
        data = await self.openalex.search(query, n)
        out = []
        for w in data.get("results") or []:
            rec = OpenAlexPipeline.normalize(w)
            out.append(_make_envelope("openalex", "OpenAlex", rec, "preprint" if rec.get("is_preprint") else "citation"))
        return out

    async def _search_arxiv(self, query: str, n: int) -> list[dict[str, Any]]:
        entries = await self.arxiv.search(query, n)
        return [_make_envelope("arxiv", "arXiv", e, "preprint") for e in entries]

    async def fetch_structure(self, uniprot_id: str) -> dict[str, Any]:
        """Live AlphaFold DB structure metadata for one UniProt accession. Fail-closed."""
        uid = (uniprot_id or "").strip()
        if not uid:
            raise ValueError("uniprot_id must not be empty")
        url = f"{AFDB_API}/{uid}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url)
                if response.status_code == 404:
                    return {"status": "not_found", "backend": "alphafold_db", "uniprot_id": uid,
                            "warning": "No AlphaFold DB entry for this accession.", "retrieved_at": _utcnow()}
                response.raise_for_status()
                data = response.json()
        except Exception as exc:  # noqa: BLE001
            return {"status": "unavailable", "backend": "alphafold_db", "uniprot_id": uid,
                    "warning": f"AlphaFold DB unreachable: {type(exc).__name__}", "retrieved_at": _utcnow()}
        entry = data[0] if isinstance(data, list) and data else (data if isinstance(data, dict) else {})
        payload_hash = _record_hash(entry)
        # Real AlphaFold DB field for mean pLDDT is `globalMetricValue`
        # (per-residue scores live in the CIF/mmCIF file, never invented here).
        mean_plddt = entry.get("globalMetricValue")
        return {
            "status": "real_predicted" if mean_plddt else "real_observed",
            "backend": "alphafold_db",
            "is_mock": False,
            "uniprot_id": uid,
            "gene": entry.get("gene"),
            "pdb_url": entry.get("pdbUrl"),
            "cif_url": entry.get("cifUrl"),
            "pae_url": entry.get("paeDocUrl"),
            "mean_plddt": mean_plddt,
            "model_version": entry.get("latestVersion"),
            "source_url": url,
            "license": "CC-BY-4.0",
            "retrieved_at": _utcnow(),
            "record_hash": payload_hash,
            "warning": "Predicted structure confidence, not a clinical or efficacy measure.",
        }

    @staticmethod
    def _dedupe(envelopes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: dict[str, dict[str, Any]] = {}
        for env in envelopes:
            key = (env.get("doi") or "").lower() if env.get("doi") else env["stable_id"]
            if key in seen:
                existing = seen[key]
                urls = set(existing.get("related_ids") or [])
                if env.get("source_url"):
                    urls.add(env["source_url"])
                existing["related_ids"] = sorted(urls)[:10]
                continue
            env["related_ids"] = [env["source_url"]] if env.get("source_url") else []
            seen[key] = env
        return list(seen.values())
