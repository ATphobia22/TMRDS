"""Federated live evidence search for the TMRDS Quantum Rubik's Cube workspace.

Orchestrates the repository's live, read-only source pipelines
(Europe PMC, PubMed/E-utilities, ClinicalTrials.gov, openFDA, OpenAlex,
arXiv, AlphaFold DB, Semantic Scholar, Crossref, PubChem, ChEMBL, DailyMed,
RxNorm) into normalized evidence envelopes with per-source
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
from engines.biorxiv_pipeline import BiorxivPipeline
from engines.chembl_pipeline import ChEMBLPipeline
from engines.clinical_trials_pipeline import ClinicalTrialsPipeline
from engines.clinvar_pipeline import ClinVarPipeline
from engines.crossref_pipeline import CrossrefPipeline
from engines.dailymed_pipeline import DailyMedPipeline
from engines.ensembl_pipeline import EnsemblPipeline
from engines.europe_pmc_pipeline import EuropePMCPipeline
from engines.mesh_pipeline import MeshPipeline
from engines.monarch_pipeline import MonarchPipeline
from engines.ncats_pipeline import NcatsPipeline
from engines.openalex_pipeline import OpenAlexPipeline
from engines.openfda_pipeline import OpenFDAPipeline
from engines.opentargets_pipeline import OpenTargetsPipeline
from engines.pubchem_pipeline import PubChemPipeline
from engines.pubmed_literature_bridge import PubMedLiteratureBridge
from engines.reactome_pipeline import ReactomePipeline
from engines.rxnorm_pipeline import RxNormPipeline
from engines.semantic_scholar_pipeline import SemanticScholarPipeline
from engines.string_pipeline import StringPipeline

AFDB_API = "https://alphafold.ebi.ac.uk/api/prediction"

COVERAGE = {
    "europe_pmc": "Europe PMC REST: open metadata + OA subset; check per-item license; not all biomedical literature.",
    "pubmed": "PubMed/Entrez E-utilities: MEDLINE subset; rate-limited; not all biomedical literature.",
    "clinicaltrials_gov": "ClinicalTrials.gov API v2: registry-native statuses/identifiers; protocol data only; not an outcomes guarantee.",
    "openfda": "openFDA: labels/FAERS signals for safety/regulatory context only; not for care decisions.",
    "openalex": "OpenAlex: open scholarly metadata incl. preprints; coverage varies by publisher.",
    "arxiv": "arXiv: preprints, not peer-reviewed; quantitative biology subset most relevant.",
    "alphafold_db": "AlphaFold DB: predicted structures; confidence metrics only from genuine API responses.",
    "semantic_scholar": "Semantic Scholar: open scholarly metadata + citation graph; 1 RPS keyed tier; commercial-use restrictions apply.",
    "crossref": "Crossref: DOI metadata authority; abstracts/references are optional deposits, coverage uneven.",
    "pubchem": "PubChem PUG-REST: compound properties; published rate limits are ceilings under dynamic throttling.",
    "chembl": "ChEMBL: bioactivity data, CC BY-SA 3.0; values are literature-curated and assay-heterogeneous.",
    "dailymed": "DailyMed: FDA SPL labels; labeler-specific; regulatory verbatim, not curated indications.",
    "rxnorm": "RxNorm/RxNav: drug terminology/normalization only; interaction API dead since Jan 2024.",
    "opentargets": "Open Targets Platform: target-disease associations, data CC0; scores are relative rankings, not calibrated confidence; release-based freshness.",
    "string": "STRING: protein functional associations, CC BY 4.0; courtesy ~1 call/sec; per-call protein limits.",
    "reactome": "Reactome Content Service: curated pathways, CC0; curated coverage only, stale between releases.",
    "clinvar": "ClinVar: published variant interpretations with review status; conflicting interpretations common — stars surfaced, not just labels.",
    "ensembl": "Ensembl REST: genomic reference data; 55k req/hour; VEP predictions are computational, not clinical assertions.",
    "biorxiv": "bioRxiv/medRxiv: preprints, NOT peer-reviewed; metadata-only, browse-by-date with local filtering.",
    "ncats": "NCATS Node Normalization + Name Resolution: identifier mappings only; rate limits unverified.",
    "monarch": "Monarch v3: phenotype/disease knowledge graph; integrated-KG license mixed — redistribution unverified.",
    "mesh": "MeSH (NLM): controlled vocabulary lookup; terminology bridge, not an evidence corpus.",
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
        self.semantic_scholar = SemanticScholarPipeline()
        self.crossref = CrossrefPipeline()
        self.pubchem = PubChemPipeline()
        self.chembl = ChEMBLPipeline()
        self.dailymed = DailyMedPipeline()
        self.rxnorm = RxNormPipeline()
        self.opentargets = OpenTargetsPipeline()
        self.string = StringPipeline()
        self.reactome = ReactomePipeline()
        self.clinvar = ClinVarPipeline()
        self.ensembl = EnsemblPipeline()
        self.biorxiv = BiorxivPipeline()
        self.ncats = NcatsPipeline()
        self.monarch = MonarchPipeline()
        self.mesh = MeshPipeline()

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
            self._guard("semantic_scholar", self._search_semantic_scholar(query, per_source)),
            self._guard("crossref", self._search_crossref(query, per_source)),
            self._guard("pubchem", self._search_pubchem(query, per_source)),
            self._guard("chembl", self._search_chembl(query, per_source)),
            self._guard("dailymed", self._search_dailymed(query, per_source)),
            self._guard("rxnorm", self._search_rxnorm(query, per_source)),
            self._guard("opentargets", self._search_opentargets(query, per_source)),
            self._guard("string", self._search_string(query, per_source)),
            self._guard("reactome", self._search_reactome(query, per_source)),
            self._guard("clinvar", self._search_clinvar(query, per_source)),
            self._guard("ensembl", self._search_ensembl(query, per_source)),
            self._guard("biorxiv", self._search_biorxiv(query, per_source)),
            self._guard("ncats", self._search_ncats(query, per_source)),
            self._guard("monarch", self._search_monarch(query, per_source)),
            self._guard("mesh", self._search_mesh(query, per_source)),
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

    async def _search_semantic_scholar(self, query: str, n: int) -> list[dict[str, Any]]:
        papers = await self.semantic_scholar.search(query, n)
        out = []
        for p in papers:
            env = _make_envelope("semantic_scholar", "Semantic Scholar", p, "citation")
            env["cited_by_count"] = p.get("cited_by_count")
            out.append(env)
        return out

    async def _search_crossref(self, query: str, n: int) -> list[dict[str, Any]]:
        works = await self.crossref.search(query, n)
        out = []
        for w in works:
            env = _make_envelope("crossref", "Crossref", w, "citation")
            env["cited_by_count"] = w.get("cited_by_count")
            out.append(env)
        return out

    async def _search_pubchem(self, query: str, n: int) -> list[dict[str, Any]]:
        # PubChem is name-addressed: one lookup per query term, not a keyword search.
        compounds = await self.pubchem.search_by_name(query)
        out = []
        for c in compounds[:n]:
            env = _make_envelope("pubchem", "PubChem", c, "compound")
            env["cid"] = c.get("cid")
            env["compound_properties"] = c.get("properties")
            out.append(env)
        return out

    async def _search_chembl(self, query: str, n: int) -> list[dict[str, Any]]:
        molecules = await self.chembl.search_molecule(query, n)
        out = []
        for m in molecules:
            env = _make_envelope("chembl", "ChEMBL", m, "compound")
            env["chembl_id"] = m.get("chembl_id")
            env["canonical_smiles"] = m.get("canonical_smiles")
            env["warnings"].append("Bioactivity values are literature-curated and assay-heterogeneous; check assay conditions.")
            out.append(env)
        return out

    async def _search_dailymed(self, query: str, n: int) -> list[dict[str, Any]]:
        records = await self.dailymed.search_by_drug_name(query, n)
        out = []
        for r in records:
            env = _make_envelope("dailymed", "DailyMed", r, "regulatory_signal")
            env["spl_set_id"] = r.get("spl_set_id")
            env["warnings"].append("Label text is regulatory verbatim, not a curated indication; not for care decisions.")
            out.append(env)
        return out

    async def _search_rxnorm(self, query: str, n: int) -> list[dict[str, Any]]:
        candidates = await self.rxnorm.approximate_term(query, n)
        out = []
        for c in candidates:
            env = _make_envelope("rxnorm", "RxNorm", c, "terminology")
            env["rxcui"] = c.get("rxcui")
            env["warnings"].append("Terminology/normalization only; the interaction API has been dead since Jan 2024.")
            out.append(env)
        return out

    async def _search_opentargets(self, query: str, n: int) -> list[dict[str, Any]]:
        assocs = await self.opentargets.associated_diseases(query, n)
        out = []
        for a in assocs:
            env = _make_envelope("opentargets", "Open Targets", a, "association")
            env["target_id"] = a.get("target_id")
            env["disease_id"] = a.get("disease_id")
            env["association_score"] = a.get("association_score")
            env["warnings"].append("Score is a relative ranking (0-1), not calibrated confidence; not a clinical assertion.")
            out.append(env)
        return out

    async def _search_string(self, query: str, n: int) -> list[dict[str, Any]]:
        edges = await self.string.interactions(query, n)
        out = []
        for e in edges:
            env = _make_envelope("string", "STRING", e, "interaction")
            env["association_score"] = e.get("association_score")
            env["warnings"].append("Functional-association confidence; CC BY 4.0 — attribution required.")
            out.append(env)
        return out

    async def _search_reactome(self, query: str, n: int) -> list[dict[str, Any]]:
        entries = await self.reactome.search_pathways(query, page_size=n)
        out = []
        for e in entries:
            env = _make_envelope("reactome", "Reactome", e, "pathway")
            env["stable_id"] = e.get("stable_id")
            env["warnings"].append("Curated pathways only; coverage is release-based, not exhaustive.")
            out.append(env)
        return out

    async def _search_clinvar(self, query: str, n: int) -> list[dict[str, Any]]:
        records = await self.clinvar.search_variants(query, n)
        out = []
        for r in records:
            env = _make_envelope("clinvar", "ClinVar", r, "variant_interpretation")
            env["variation_id"] = r.get("variation_id")
            env["classification"] = r.get("classification")
            env["review_status"] = r.get("review_status")
            env["warnings"].append(
                "Published interpretation with review status shown; conflicting interpretations are common — "
                "not per-patient variant interpretation."
            )
            out.append(env)
        return out

    async def _search_ensembl(self, query: str, n: int) -> list[dict[str, Any]]:
        gene = await self.ensembl.lookup_gene(query)
        if gene is None:
            return []
        env = _make_envelope("ensembl", "Ensembl", gene, "reference")
        env["ensembl_id"] = gene.get("ensembl_id")
        env["warnings"].append("Reference annotation (GRCh38); consequence predictions are computational, not clinical.")
        return [env]

    async def _search_biorxiv(self, query: str, n: int) -> list[dict[str, Any]]:
        papers = await self.biorxiv.search_recent(query, days_back=60, max_pages=3)
        out = []
        for p in papers[:n]:
            env = _make_envelope("biorxiv", "bioRxiv", p, "preprint")
            env["warnings"].append("PREPRINT — not peer-reviewed; check version and published-linkage before citing.")
            out.append(env)
        return out

    async def _search_ncats(self, query: str, n: int) -> list[dict[str, Any]]:
        hits = await self.ncats.resolve_name(query, n)
        out = []
        for h in hits:
            env = _make_envelope("ncats", "NCATS", h, "terminology")
            env["curie"] = h.get("curie")
            env["warnings"].append("Identifier mapping only — not evidence of any association.")
            out.append(env)
        return out

    async def _search_monarch(self, query: str, n: int) -> list[dict[str, Any]]:
        entities = await self.monarch.search(query, page_size=n)
        out = []
        for e in entities:
            env = _make_envelope("monarch", "Monarch", e, "association")
            env["curie"] = e.get("curie")
            env["warnings"].append("Published KG annotations; integrated-KG license is mixed — redistribution unverified.")
            out.append(env)
        return out

    async def _search_mesh(self, query: str, n: int) -> list[dict[str, Any]]:
        descriptors = await self.mesh.lookup(query)
        out = []
        for d in descriptors[:n]:
            env = _make_envelope("mesh", "MeSH", d, "terminology")
            env["descriptor_id"] = d.get("descriptor_id")
            env["warnings"].append("Controlled-vocabulary term for query expansion — not an evidence corpus.")
            out.append(env)
        return out

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
