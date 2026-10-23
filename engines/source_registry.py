"""
TMRDS Phase 0 — Versioned Source Registry
File: engines/source_registry.py equivalent
Repo: ATphobia22/TMRDS | Branch: feature/evidence-discovery-research
Boundary: Research discovery only, not SaMD. Quantum Rubik's Cube workspace.

Acceptance Criteria (Phase 0):
- Versioned source catalog with api_endpoint, permitted_use, license_class,
  identifier_types, query_params, update_cadence, attribution, retention_policy,
  adapter_owner, version.
- Health/coverage view: last_success, last_upstream_update, rate_limit_errors,
  records_added, stale_warning.
- Deterministic contract test fixtures, no live network dependency in CI.
- MOCK_ONLY adapters return empty confidence / no fabricated metrics.
- Importable with no external deps beyond requests (requests optional at runtime).

Design Principles from Roadmap:
- Every result source-traceable; partial source failures disclosed.
- No "all research searched" assertion; respect rate limits, robots, TDM.
- Store citation/metadata first; full-text only when license permits.
- pLDDT/pTM/etc only when genuine backend present; mock returns MOCK_ONLY.
"""

from __future__ import annotations

import datetime as dt
import json
import os
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Literal, Tuple

# ---------------------------------------------------------------------------
# Enums / Constants
# ---------------------------------------------------------------------------

class LicenseClass(str, Enum):
    CC_BY_4_0 = "CC-BY-4.0"
    CC_BY_NC_4_0 = "CC-BY-NC-4.0"
    CC0 = "CC0"
    OPEN = "open"           # Public domain / open government data / API open
    RESTRICTED = "restricted"  # Requires API key, gated, or model weights license
    MIXED = "mixed"         # Per-record license must be checked
    MIT = "MIT"
    APACHE_2_0 = "Apache-2.0"
    CUSTOM = "custom"

class PermittedUse(str, Enum):
    # High-level governed categories aligned to docs/ARCHITECTURE_VERIFICATION.md
    METADATA_ONLY = "metadata_only"  # citation/abstract metadata OK, full-text check per item
    OPEN_RETRIEVAL = "open_retrieval"  # open API, citation + selective full-text when license allows
    REGULATORY_RETRIEVAL = "regulatory_retrieval"  # FDA etc, with disclaimer
    STRUCTURE_PREDICTED = "structure_predicted"  # predicted structures, mock-only by default in this branch
    GENOMIC_ANNOTATION = "genomic_annotation"  # variant/gene annotation, not clinical interpretation
    PATENT_SEARCH = "patent_search"  # lens etc
    ENVIRONMENTAL_DATA = "environmental_data"  # USGS/NOAA contextual
    MOCK_ONLY = "MOCK_ONLY"  # Placeholder adapter: must return empty confidence, no invented metrics

class IdentifierType(str, Enum):
    PMID = "PMID"
    PMCID = "PMCID"
    DOI = "DOI"
    NCT = "NCT"
    FDA_APPLICATION = "FDA_APPLICATION"
    ENSEMBL_GENE = "ENSEMBL_GENE"
    ENSEMBL_VARIANT = "ENSEMBL_VARIANT"
    CLINVAR_VCID = "CLINVAR_VCID"
    GNOMAD_VARIANT = "GNOMAD_VARIANT"
    GTEX_EGENE = "GTEX_EGENE"
    UNIPROT = "UNIPROT"
    AFDB_ID = "AFDB_ID"
    ESM_ATLAS_ID = "ESM_ATLAS_ID"
    LENS_ID = "LENS_ID"
    ARXIV_ID = "ARXIV_ID"
    Biorxiv_DOI = "BIORXIV_DOI"
    CROSSREF_DOI = "CROSSREF_DOI"
    USGS_SITE = "USGS_SITE"
    NOAA_STATION = "NOAA_STATION"
    STRUCTURE_HASH = "STRUCTURE_HASH"  # artifact hash, not a fake URI

class UpdateCadence(str, Enum):
    REALTIME = "realtime"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    VERSIONED_RELEASE = "versioned_release"  # gnomAD, GTEx, Ensembl
    ON_DEMAND = "on_demand"

# ---------------------------------------------------------------------------
# Core Dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SourceDefinition:
    """Canonical definition for a research source. Versioned, auditable."""
    key: str  # stable machine key: pubmed, clinicaltrials_v2, etc.
    display_name: str
    api_endpoint: str
    permitted_use: PermittedUse
    license_class: LicenseClass
    identifier_types: List[IdentifierType] = field(default_factory=list)
    query_params: Dict[str, Any] = field(default_factory=dict)  # allowed/expected params
    update_cadence: UpdateCadence = UpdateCadence.DAILY
    attribution: str = ""  # required citation string
    retention_policy: str = "Store citations + retrieval timestamp + source version hash; check TDM/robots; honor takedown/retraction. No mirror bulk full-text by default."
    adapter_owner: str = "engines/adapters/{key}_adapter.py"
    version: str = "1.0.0"  # registry version for this source adapter
    upstream_version_pinned: Optional[str] = None  # e.g., Ensembl release 112, gnomAD v4.1.0
    docs_url: Optional[str] = None
    rate_limit: Optional[str] = None  # human readable
    requires_api_key: bool = False
    evidence_class: str = "observed"  # observed | derived | predicted | hypothesized per docs
    notes: str = ""

@dataclass
class SourceHealth:
    """Health/coverage view per source."""
    key: str
    last_success: Optional[dt.datetime] = None
    last_upstream_update: Optional[dt.datetime] = None
    last_attempt: Optional[dt.datetime] = None
    rate_limit_errors: int = 0
    records_added: int = 0
    records_updated: int = 0
    errors: int = 0
    stale_warning: bool = False
    stale_reason: Optional[str] = None
    coverage_note: str = ""
    observed_upstream_version: Optional[str] = None  # detected from headers/payload
    # For federated search partial-failure disclosure
    last_error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        for k in ("last_success", "last_upstream_update", "last_attempt"):
            if d[k]:
                d[k] = d[k].isoformat()
        return d

    def compute_stale(self, definition: SourceDefinition, now: Optional[dt.datetime] = None) -> bool:
        now = now or dt.datetime.now(dt.timezone.utc)
        if not self.last_success:
            self.stale_warning = True
            self.stale_reason = "Never succeeded"
            return True
        delta = now - self.last_success
        # Map cadence to stale thresholds
        thresholds = {
            UpdateCadence.REALTIME: dt.timedelta(hours=24),
            UpdateCadence.DAILY: dt.timedelta(days=3),
            UpdateCadence.WEEKLY: dt.timedelta(days=14),
            UpdateCadence.MONTHLY: dt.timedelta(days=45),
            UpdateCadence.QUARTERLY: dt.timedelta(days=130),
            UpdateCadence.VERSIONED_RELEASE: dt.timedelta(days=200),
            UpdateCadence.ON_DEMAND: dt.timedelta(days=90),
        }
        thresh = thresholds.get(definition.update_cadence, dt.timedelta(days=7))
        if delta > thresh:
            self.stale_warning = True
            self.stale_reason = f"Last success {delta.days}d ago exceeds {definition.update_cadence.value} threshold ({thresh.days}d)"
            return True
        if self.rate_limit_errors > 5 and (now - self.last_success) > dt.timedelta(hours=6):
            self.stale_warning = True
            self.stale_reason = f"Rate-limit errors {self.rate_limit_errors} impair freshness"
            return True
        self.stale_warning = False
        self.stale_reason = None
        return False

# ---------------------------------------------------------------------------
# Registry Builder — 16 required sources
# ---------------------------------------------------------------------------

def build_default_registry() -> Dict[str, SourceDefinition]:
    """Returns versioned catalog. All endpoints are documented public APIs."""
    reg: Dict[str, SourceDefinition] = {}

    def add(sd: SourceDefinition):
        reg[sd.key] = sd

    # 1. PubMed
    add(SourceDefinition(
        key="pubmed",
        display_name="PubMed / NCBI E-utilities",
        api_endpoint="https://eutils.ncbi.nlm.nih.gov/entrez/eutils",
        permitted_use=PermittedUse.METADATA_ONLY,
        license_class=LicenseClass.OPEN,
        identifier_types=[IdentifierType.PMID, IdentifierType.DOI, IdentifierType.PMCID],
        query_params={"db": "pubmed", "retmode": "json", "rettype": "abstract", "retmax": 100, "usehistory": True, "query": "string"},
        update_cadence=UpdateCadence.DAILY,
        attribution="PubMed data provided by NCBI, NLM. Cite NCBI.",
        retention_policy="Store PMID, title, authors, journal, year, DOI, retrieval date, source hash. Abstract OK; full-text only per license.",
        adapter_owner="engines/adapters/pubmed_adapter.py",
        version="2.0.0",
        docs_url="https://www.ncbi.nlm.nih.gov/books/NBK25499/",
        rate_limit="3 req/s without key, 10 req/s with key",
        requires_api_key=False,
        evidence_class="observed",
        notes="Use API adapters, not HTML scraping. Handle retractions via PMID corrections.",
    ))

    # 2. Europe PMC
    add(SourceDefinition(
        key="europe_pmc",
        display_name="Europe PMC REST API",
        api_endpoint="https://www.ebi.ac.uk/europepmc/webservices/rest",
        permitted_use=PermittedUse.OPEN_RETRIEVAL,
        license_class=LicenseClass.MIXED,
        identifier_types=[IdentifierType.PMID, IdentifierType.PMCID, IdentifierType.DOI],
        query_params={"query": "string", "format": "json", "pageSize": 100, "resultType": "core", "openAccess": "bool"},
        update_cadence=UpdateCadence.DAILY,
        attribution="Europe PMC. Check per-article license in 'license' field.",
        retention_policy="Store citation metadata; per-record license check before retaining full-text. OA subset only for TDM.",
        adapter_owner="engines/adapters/europe_pmc_adapter.py",
        version="2.0.0",
        docs_url="https://europepmc.org/RestfulWebService",
        rate_limit="Public, courteous pacing; respect Retry-After",
        evidence_class="observed",
    ))

    # 3. ClinicalTrials.gov v2
    add(SourceDefinition(
        key="clinicaltrials_v2",
        display_name="ClinicalTrials.gov API v2",
        api_endpoint="https://clinicaltrials.gov/api/v2/studies",
        permitted_use=PermittedUse.REGULATORY_RETRIEVAL,
        license_class=LicenseClass.OPEN,
        identifier_types=[IdentifierType.NCT],
        query_params={"query.term": "AREA[Condition]diabetes", "filter.overallStatus": "COMPLETED", "pageSize": 100, "format": "json"},
        update_cadence=UpdateCadence.DAILY,
        attribution="ClinicalTrials.gov, NLM. Data via API v2.",
        retention_policy="Preserve native status (RECRUITING etc), identifiers, timestamps, results semantics. Versioned by studyVersion.",
        adapter_owner="engines/adapters/clinicaltrials_adapter.py",
        version="3.0.0",
        upstream_version_pinned="v2",
        docs_url="https://clinicaltrials.gov/data-api/api",
        rate_limit="No key required, throttle 50 req/min recommended",
        evidence_class="observed",
        notes="Use v2, not legacy v1. Handle migration guide. Do not scrape ICTRP portal without permission.",
    ))

    # 4. openFDA
    add(SourceDefinition(
        key="openfda",
        display_name="openFDA APIs",
        api_endpoint="https://api.fda.gov",
        permitted_use=PermittedUse.REGULATORY_RETRIEVAL,
        license_class=LicenseClass.OPEN,
        identifier_types=[IdentifierType.FDA_APPLICATION, IdentifierType.DOI],
        query_params={"search": "openfda.brand_name:aspirin", "limit": 100, "skip": 0},
        update_cadence=UpdateCadence.WEEKLY,
        attribution="openFDA, U.S. FDA. Caveats apply: not for medical-care decisions.",
        retention_policy="Store event/report metadata with retrieval date + FDA disclaimer. Honor drug-event caveats.",
        adapter_owner="engines/adapters/openfda_adapter.py",
        version="2.0.0",
        docs_url="https://open.fda.gov/apis/",
        rate_limit="240 req/min with key, 40 req/min without; auth recommended",
        requires_api_key=False,
        evidence_class="observed",
        notes="Explicitly cautions against clinical use. Keep regulatory evidence class.",
    ))

    # 5. AlphaFold DB — MOCK_ONLY in this branch per Fix Plan
    add(SourceDefinition(
        key="alphafold_db",
        display_name="AlphaFold DB (EBI)",
        api_endpoint="https://alphafold.ebi.ac.uk/api/prediction",
        permitted_use=PermittedUse.MOCK_ONLY,
        license_class=LicenseClass.CC_BY_4_0,
        identifier_types=[IdentifierType.UNIPROT, IdentifierType.AFDB_ID, IdentifierType.STRUCTURE_HASH],
        query_params={"uniprot_id": "P69905", "format": "json"},
        update_cadence=UpdateCadence.VERSIONED_RELEASE,
        attribution="AlphaFold DB by EMBL-EBI/DeepMind. License CC-BY-4.0 for predictions; source/license reuse check required.",
        retention_policy="MOCK_ONLY in this branch: return empty confidence, no URI, no ranking. Real adapter needs weight/license validation before genuine execution.",
        adapter_owner="engines/alphafold3_node.py",
        version="1.1.0-mockfix",
        upstream_version_pinned="AFDB v4",
        docs_url="https://alphafold.ebi.ac.uk/api-docs",
        rate_limit="Paced REST; bulk download via FTP",
        evidence_class="predicted",
        notes="Fix Applied: placeholder backends must not emit pLDDT/pTM. Real adapter must record model DB version, source commit, artifact hash.",
    ))

    # 6. ESM Atlas — MOCK_ONLY until license review
    add(SourceDefinition(
        key="esm_atlas",
        display_name="ESM Atlas / ESM Metagenomic Atlas",
        api_endpoint="https://api.esmatlas.com",
        permitted_use=PermittedUse.MOCK_ONLY,
        license_class=LicenseClass.MIXED,
        identifier_types=[IdentifierType.ESM_ATLAS_ID, IdentifierType.UNIPROT, IdentifierType.STRUCTURE_HASH],
        query_params={"id": "MGYP000000001", "structure": "bool"},
        update_cadence=UpdateCadence.VERSIONED_RELEASE,
        attribution="ESM Atlas by Meta AI. Check ESMFold license before redistribution of structures.",
        retention_policy="MOCK_ONLY pending license/fit review. No synthetic compound ranking. If real, store model version, artifact hash.",
        adapter_owner="engines/adapters/esm_adapter.py",
        version="1.0.0-mockfix",
        docs_url="https://esmatlas.com/about#api",
        evidence_class="predicted",
        notes="Alternative to AF3; not drop-in replacement. Requires independent review.",
    ))

    # 7. Lens Patents
    add(SourceDefinition(
        key="lens_patents",
        display_name="Lens.org Patents API",
        api_endpoint="https://api.lens.org/patent/search",
        permitted_use=PermittedUse.PATENT_SEARCH,
        license_class=LicenseClass.MIXED,
        identifier_types=[IdentifierType.LENS_ID, IdentifierType.DOI],
        query_params={"query": "lens patent query DSL JSON", "size": 100, "include": ["title","abstract"]},
        update_cadence=UpdateCadence.WEEKLY,
        attribution="Patent data via Lens.org. Respect Lens terms.",
        retention_policy="Metadata-only; full patent text per Lens terms. Store Lens ID, retrieval date.",
        adapter_owner="engines/adapters/lens_adapter.py",
        version="1.0.0",
        docs_url="https://docs.api.lens.org/",
        requires_api_key=True,
        evidence_class="observed",
    ))

    # 8. ClinVar
    add(SourceDefinition(
        key="clinvar",
        display_name="ClinVar",
        api_endpoint="https://eutils.ncbi.nlm.nih.gov/entrez/eutils + https://ftp.ncbi.nlm.nih.gov/pub/clinvar",
        permitted_use=PermittedUse.GENOMIC_ANNOTATION,
        license_class=LicenseClass.OPEN,
        identifier_types=[IdentifierType.CLINVAR_VCID, IdentifierType.ENSEMBL_VARIANT],
        query_params={"variation_id": "int", "rcv": "RCV000...", "assembly": "GRCh38"},
        update_cadence=UpdateCadence.WEEKLY,
        attribution="ClinVar, NCBI. Preserve submitter, review status, date, conflicts, condition/context.",
        retention_policy="Do not collapse assertions into ground truth. Preserve conflict, review stars, last evaluated date.",
        adapter_owner="engines/adapters/clinvar_adapter.py",
        version="2.0.0",
        docs_url="https://www.ncbi.nlm.nih.gov/clinvar/docs/help/",
        evidence_class="observed",
        notes="Keep sensitive human data outside public ingestion unless governance pathway exists.",
    ))

    # 9. Ensembl
    add(SourceDefinition(
        key="ensembl",
        display_name="Ensembl REST API",
        api_endpoint="https://rest.ensembl.org",
        permitted_use=PermittedUse.GENOMIC_ANNOTATION,
        license_class=LicenseClass.APACHE_2_0,
        identifier_types=[IdentifierType.ENSEMBL_GENE, IdentifierType.ENSEMBL_VARIANT, IdentifierType.UNIPROT],
        query_params={"species": "homo_sapiens", "id": "ENSG000...", "content-type": "application/json", "assembly": "GRCh38"},
        update_cadence=UpdateCadence.VERSIONED_RELEASE,
        attribution="Ensembl REST. Pin release, assembly, transcript versions.",
        retention_policy="Store Ensembl release (e.g., 112), GRCh38, transcript version. Versioned crosswalk.",
        adapter_owner="engines/adapters/ensembl_adapter.py",
        version="2.0.0",
        upstream_version_pinned="Ensembl 112 / GRCh38",
        docs_url="https://rest.ensembl.org/",
        rate_limit="15 req/s",
        evidence_class="observed",
    ))

    # 10. gnomAD
    add(SourceDefinition(
        key="gnomad",
        display_name="gnomAD",
        api_endpoint="https://gnomad.broadinstitute.org/api",
        permitted_use=PermittedUse.GENOMIC_ANNOTATION,
        license_class=LicenseClass.CUSTOM,
        identifier_types=[IdentifierType.GNOMAD_VARIANT, IdentifierType.ENSEMBL_GENE],
        query_params={"dataset": "gnomad_r4", "variantId": "1-55516888-G-A", "reference_genome": "GRCh38"},
        update_cadence=UpdateCadence.VERSIONED_RELEASE,
        attribution="gnomAD v4, Broad Institute. Respect gnomAD terms + population warnings.",
        retention_policy="Include dataset version, ancestry/population representation warning, allele freq context. No clinical interpretation.",
        adapter_owner="engines/adapters/gnomad_adapter.py",
        version="2.0.0",
        upstream_version_pinned="v4.1.0",
        docs_url="https://gnomad.broadinstitute.org/api",
        evidence_class="observed",
        notes="Population representation warning required; explicit uncertainty.",
    ))

    # 11. GTEx
    add(SourceDefinition(
        key="gtex",
        display_name="GTEx Portal API",
        api_endpoint="https://gtexportal.org/api/v2",
        permitted_use=PermittedUse.GENOMIC_ANNOTATION,
        license_class=LicenseClass.CUSTOM,
        identifier_types=[IdentifierType.GTEX_EGENE, IdentifierType.ENSEMBL_GENE],
        query_params={"gencodeId": "ENSG000...", "tissueSiteDetailId": "Muscle_Skeletal", "datasetId": "gtex_v8"},
        update_cadence=UpdateCadence.VERSIONED_RELEASE,
        attribution="GTEx Portal. v8 dataset.",
        retention_policy="Store GTEx version (v8), tissue, dataset ID. Expression QTL context only.",
        adapter_owner="engines/adapters/gtex_adapter.py",
        version="1.1.0",
        upstream_version_pinned="GTEx v8",
        docs_url="https://gtexportal.org/api/v2/docs/",
        evidence_class="observed",
    ))

    # 12. bioRxiv
    add(SourceDefinition(
        key="biorxiv",
        display_name="bioRxiv API",
        api_endpoint="https://api.biorxiv.org/details/biorxiv",
        permitted_use=PermittedUse.METADATA_ONLY,
        license_class=LicenseClass.MIXED,
        identifier_types=[IdentifierType.Biorxiv_DOI, IdentifierType.DOI],
        query_params={"server": "biorxiv", "interval": "2024-01-01/2024-01-31", "cursor": 0, "format": "json"},
        update_cadence=UpdateCadence.DAILY,
        attribution="bioRxiv preprints. Distinguish preprint from published version; retain relationship, don't silently merge.",
        retention_policy="Metadata + license per preprint. Full-text only when allowed; distinguish TDM vs redistribution permission.",
        adapter_owner="engines/adapters/biorxiv_adapter.py",
        version="2.0.0",
        docs_url="https://api.biorxiv.org/",
        evidence_class="observed",
        notes="Access ≠ redistribution permission. Handle corrections.",
    ))

    # 13. arXiv
    add(SourceDefinition(
        key="arxiv",
        display_name="arXiv API",
        api_endpoint="http://export.arxiv.org/api/query",
        permitted_use=PermittedUse.METADATA_ONLY,
        license_class=LicenseClass.MIXED,
        identifier_types=[IdentifierType.ARXIV_ID],
        query_params={"search_query": "all:quantum", "max_results": 100, "sortBy": "submittedDate"},
        update_cadence=UpdateCadence.DAILY,
        attribution="arXiv.org. Honor content rights; metadata-first retrieval.",
        retention_policy="Metadata-first; honor request pacing and content rights.",
        adapter_owner="engines/adapters/arxiv_adapter.py",
        version="2.0.0",
        docs_url="https://info.arxiv.org/help/api/index.html",
        rate_limit="Follow pacing guidelines; 1 req per 3 sec recommended",
        evidence_class="observed",
    ))

    # 14. Crossref
    add(SourceDefinition(
        key="crossref",
        display_name="Crossref REST API",
        api_endpoint="https://api.crossref.org/works",
        permitted_use=PermittedUse.METADATA_ONLY,
        license_class=LicenseClass.OPEN,
        identifier_types=[IdentifierType.CROSSREF_DOI, IdentifierType.DOI],
        query_params={"query": "title", "filter": "from-pub-date:2024", "rows": 100},
        update_cadence=UpdateCadence.DAILY,
        attribution="Crossref metadata. Abstracts may remain copyrighted.",
        retention_policy="Enrich DOI metadata; abstracts may be copyrighted—check.",
        adapter_owner="engines/adapters/crossref_adapter.py",
        version="2.0.0",
        docs_url="https://api.crossref.org/swagger-ui/index.html",
        rate_limit="Polite pool with mailto; 50 req/s polite",
        evidence_class="observed",
    ))

    # 15. USGS
    add(SourceDefinition(
        key="usgs",
        display_name="USGS Water / Env Data Services",
        api_endpoint="https://waterservices.usgs.gov/nwis",
        permitted_use=PermittedUse.ENVIRONMENTAL_DATA,
        license_class=LicenseClass.CC0,
        identifier_types=[IdentifierType.USGS_SITE],
        query_params={"sites": "01491000", "parameterCd": "00060", "format": "json"},
        update_cadence=UpdateCadence.REALTIME,
        attribution="USGS public domain (CC0). Environmental context only.",
        retention_policy="Environmental contextual data—not clinical evidence. Store site, param code, retrieval time.",
        adapter_owner="engines/adapters/usgs_adapter.py",
        version="1.0.0",
        docs_url="https://waterservices.usgs.gov/docs/",
        evidence_class="observed",
        notes="Contextual factor for research facets (time, geography).",
    ))

    # 16. NOAA
    add(SourceDefinition(
        key="noaa",
        display_name="NOAA Climate Data Online / Weather API",
        api_endpoint="https://www.ncei.noaa.gov/cdo-web/api/v2",
        permitted_use=PermittedUse.ENVIRONMENTAL_DATA,
        license_class=LicenseClass.OPEN,
        identifier_types=[IdentifierType.NOAA_STATION],
        query_params={"datasetid": "GHCND", "stationid": "GHCND:USW00094728", "startdate": "2024-01-01", "limit": 100},
        update_cadence=UpdateCadence.DAILY,
        attribution="NOAA public data. Environmental context only.",
        retention_policy="Environment context only. Store station, dataset, timestamp.",
        adapter_owner="engines/adapters/noaa_adapter.py",
        version="1.0.0",
        docs_url="https://www.ncdc.noaa.gov/cdo-web/webservices/v2",
        requires_api_key=True,
        evidence_class="observed",
    ))

    # 17. Semantic Scholar
    add(SourceDefinition(
        key="semantic_scholar",
        display_name="Semantic Scholar API",
        api_endpoint="https://api.semanticscholar.org/graph/v1/paper/search",
        permitted_use=PermittedUse.METADATA_ONLY,
        license_class=LicenseClass.CUSTOM,
        identifier_types=[IdentifierType.DOI, IdentifierType.PMID, IdentifierType.ARXIV_ID],
        query_params={"query": "string", "limit": 100, "fields": "title,abstract,authors,year,doi,url,openAccessPdf,citationCount"},
        update_cadence=UpdateCadence.DAILY,
        attribution="Semantic Scholar API, Allen Institute for AI. Commercial use restricted by the S2 license.",
        retention_policy="Store citation metadata + retrieval timestamp. TLDRs are triage, not citable evidence.",
        adapter_owner="engines/semantic_scholar_pipeline.py",
        version="1.0.0",
        docs_url="https://www.semanticscholar.org/product/api",
        rate_limit="1 RPS keyed introductory tier; keyless shared pool throttled under load",
        evidence_class="observed",
        notes="Optional S2_API_KEY sent as x-api-key header. Client enforces >=1s between calls.",
    ))

    # 18. PubChem PUG-REST
    add(SourceDefinition(
        key="pubchem",
        display_name="PubChem PUG-REST",
        api_endpoint="https://pubchem.ncbi.nlm.nih.gov/rest/pug",
        permitted_use=PermittedUse.OPEN_RETRIEVAL,
        license_class=LicenseClass.OPEN,
        identifier_types=[],
        query_params={"name": "compound name", "properties": "IUPACName,InChIKey,CanonicalSMILES,...", "format": "JSON"},
        update_cadence=UpdateCadence.ON_DEMAND,
        attribution="PubChem, National Library of Medicine.",
        retention_policy="Store CID, queried name, properties, retrieval timestamp. Bulk via FTP, not API.",
        adapter_owner="engines/pubchem_pipeline.py",
        version="1.0.0",
        docs_url="https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest",
        rate_limit="<=5/s, <=400/min published ceilings; dynamic throttling shrinks them under load",
        evidence_class="observed",
        notes="Name-addressed lookup, not keyword search. Native identifier: CID (no enum entry).",
    ))

    # 19. ChEMBL
    add(SourceDefinition(
        key="chembl",
        display_name="ChEMBL",
        api_endpoint="https://www.ebi.ac.uk/chembl/api/data",
        permitted_use=PermittedUse.OPEN_RETRIEVAL,
        license_class=LicenseClass.CUSTOM,
        identifier_types=[],
        query_params={"q": "molecule search string", "limit": 100},
        update_cadence=UpdateCadence.ON_DEMAND,
        attribution="ChEMBL, EMBL-EBI. Database data CC BY-SA 3.0.",
        retention_policy="Store ChEMBL ID, query, assay context with any bioactivity value, retrieval timestamp.",
        adapter_owner="engines/chembl_pipeline.py",
        version="1.0.0",
        docs_url="https://www.ebi.ac.uk/chembl/api/data",
        rate_limit="None published; client spaces calls >=1s (be modest)",
        evidence_class="observed",
        notes="CC BY-SA 3.0: attribution required; share-alike applies to adapted redistribution. Bioactivity values are assay-heterogeneous.",
    ))

    # 20. DailyMed
    add(SourceDefinition(
        key="dailymed",
        display_name="DailyMed",
        api_endpoint="https://dailymed.nlm.nih.gov/dailymed/services/v2",
        permitted_use=PermittedUse.REGULATORY_RETRIEVAL,
        license_class=LicenseClass.OPEN,
        identifier_types=[],
        query_params={"drug_name": "string", "pagesize": 100},
        update_cadence=UpdateCadence.ON_DEMAND,
        attribution="DailyMed, National Library of Medicine. U.S. federal public data.",
        retention_policy="Store SPL SET ID, title, published date, retrieval timestamp. Label text is regulatory verbatim.",
        adapter_owner="engines/dailymed_pipeline.py",
        version="1.0.0",
        docs_url="https://dailymed.nlm.nih.gov/dailymed/app-support-web-services.cfm",
        rate_limit="None published for DailyMed specifically",
        evidence_class="observed",
        notes="v2 path verified live 2026-10-18; older v1 paths 302-redirect. Labels are labeler-specific SPLs (one drug -> many SPLs). Native identifier: SPL SET ID.",
    ))

    # 21. RxNorm / RxNav
    add(SourceDefinition(
        key="rxnorm",
        display_name="RxNorm / RxNav",
        api_endpoint="https://rxnav.nlm.nih.gov/REST",
        permitted_use=PermittedUse.METADATA_ONLY,
        license_class=LicenseClass.OPEN,
        identifier_types=[],
        query_params={"term": "drug name string", "maxEntries": 50},
        update_cadence=UpdateCadence.ON_DEMAND,
        attribution="RxNorm, National Library of Medicine.",
        retention_policy="Store RxCUI, matched name, score, retrieval timestamp. Terminology only.",
        adapter_owner="engines/rxnorm_pipeline.py",
        version="1.0.0",
        docs_url="https://lhncbc.nlm.nih.gov/RxNav/",
        rate_limit="20 req/s/IP (NLM API Terms of Service)",
        evidence_class="observed",
        notes="Terminology/normalization ONLY. The drug-drug Interaction API has been DEAD since Jan 2024 - never rebuild interaction checking. Native identifier: RxCUI.",
    ))

    # 22. Open Targets Platform
    add(SourceDefinition(
        key="opentargets",
        display_name="Open Targets Platform",
        api_endpoint="https://api.platform.opentargets.org/api/v4/graphql",
        permitted_use=PermittedUse.METADATA_ONLY,
        license_class=LicenseClass.OPEN,
        identifier_types=[IdentifierType.DOI],
        query_params={"query": "GraphQL: search(queryString) then target(ensemblId){associatedDiseases}"},
        update_cadence=UpdateCadence.ON_DEMAND,
        attribution="Open Targets Platform. Data CC0 1.0.",
        retention_policy="Store target/disease IDs, association score, retrieval timestamp. Scores are relative rankings.",
        adapter_owner="engines/opentargets_pipeline.py",
        version="1.0.0",
        docs_url="https://platform-docs.opentargets.org/",
        rate_limit="None published — client stays modest (>=1s between calls)",
        evidence_class="observed",
        notes="Association scores are relative rankings (0-1 harmonic sums), NOT calibrated confidence. Release-based freshness. GraphQL is not a bulk route.",
    ))

    # 23. STRING
    add(SourceDefinition(
        key="string",
        display_name="STRING",
        api_endpoint="https://string-db.org/api/json",
        permitted_use=PermittedUse.METADATA_ONLY,
        license_class=LicenseClass.CUSTOM,
        identifier_types=[],
        query_params={"identifiers": "protein name", "species": 9606, "required_score": 400, "limit": 50},
        update_cadence=UpdateCadence.ON_DEMAND,
        attribution="STRING. CC BY 4.0 — attribution required.",
        retention_policy="Store STRING IDs, partner names, scores, retrieval timestamp.",
        adapter_owner="engines/string_pipeline.py",
        version="1.0.0",
        docs_url="https://string-db.org/help/api/",
        rate_limit="Courtesy ~1 call/second; per-call protein-count limits",
        evidence_class="observed",
        notes="Functional-association confidences, not clinical assertions. Resolve names to STRING IDs first (ambiguity).",
    ))

    # 24. Reactome
    add(SourceDefinition(
        key="reactome",
        display_name="Reactome",
        api_endpoint="https://reactome.org/ContentService",
        permitted_use=PermittedUse.METADATA_ONLY,
        license_class=LicenseClass.OPEN,
        identifier_types=[],
        query_params={"query": "keyword", "species": "Homo sapiens"},
        update_cadence=UpdateCadence.ON_DEMAND,
        attribution="Reactome. Data CC0; illustrations CC BY 4.0.",
        retention_policy="Store stable IDs (R-HSA-*), names, retrieval timestamp.",
        adapter_owner="engines/reactome_pipeline.py",
        version="1.0.0",
        docs_url="https://reactome.org/dev/content-service",
        rate_limit="None published — client stays modest (>=1s between calls)",
        evidence_class="observed",
        notes="Curated coverage only; stale between releases; non-human content mostly inferred orthology.",
    ))

    # 25. ClinVar
    add(SourceDefinition(
        key="clinvar",
        display_name="ClinVar",
        api_endpoint="https://eutils.ncbi.nlm.nih.gov/entrez/eutils",
        permitted_use=PermittedUse.METADATA_ONLY,
        license_class=LicenseClass.OPEN,
        identifier_types=[],
        query_params={"db": "clinvar", "term": "search string", "retmax": 50},
        update_cadence=UpdateCadence.ON_DEMAND,
        attribution="ClinVar, National Library of Medicine.",
        retention_policy="Store variation ID, classification, review status, conditions, retrieval timestamp. Always keep stars with labels.",
        adapter_owner="engines/clinvar_pipeline.py",
        version="1.0.0",
        docs_url="https://www.ncbi.nlm.nih.gov/clinvar/docs/programmatic_access/",
        rate_limit="3 req/s keyless, 10 req/s with free NCBI API key (E-utilities policy)",
        evidence_class="observed",
        notes="Conflicting interpretations common — review status MUST surface with every label. Published interpretations only; never per-patient interpretation.",
    ))

    # 26. Ensembl REST
    add(SourceDefinition(
        key="ensembl",
        display_name="Ensembl REST",
        api_endpoint="https://rest.ensembl.org",
        permitted_use=PermittedUse.METADATA_ONLY,
        license_class=LicenseClass.OPEN,
        identifier_types=[],
        query_params={"symbol": "gene symbol", "species": "homo_sapiens"},
        update_cadence=UpdateCadence.ON_DEMAND,
        attribution="Ensembl (EBI/EMBL). Free for all uses; cite Ensembl.",
        retention_policy="Store Ensembl stable ID, symbol, assembly, location, retrieval timestamp.",
        adapter_owner="engines/ensembl_pipeline.py",
        version="1.0.0",
        docs_url="https://rest.ensembl.org/",
        rate_limit="55,000 requests/hour per IP; 429 + Retry-After on exceed",
        evidence_class="observed",
        notes="GRCh38 by default; GRCh37 via grch37.rest.ensembl.org. VEP predictions are computational, not clinical assertions.",
    ))

    # 27. bioRxiv / medRxiv
    add(SourceDefinition(
        key="biorxiv",
        display_name="bioRxiv / medRxiv",
        api_endpoint="https://api.biorxiv.org",
        permitted_use=PermittedUse.METADATA_ONLY,
        license_class=LicenseClass.CUSTOM,
        identifier_types=[IdentifierType.DOI],
        query_params={"server": "biorxiv|medrxiv", "interval": "date range", "cursor": 0},
        update_cadence=UpdateCadence.DAILY,
        attribution="bioRxiv/medRxiv (Cold Spring Harbor Laboratory). Per-paper license field.",
        retention_policy="Store DOI, version, license, published-linkage, retrieval timestamp. Always label un-peer-reviewed.",
        adapter_owner="engines/biorxiv_pipeline.py",
        version="1.0.0",
        docs_url="https://api.biorxiv.org/",
        rate_limit="None published — client stays modest (>=1s between calls)",
        evidence_class="observed",
        notes="Metadata-only; NO keyword search — client downloads a date window and filters locally. Every record is_preprint=True. License is per-paper; no blanket corpus license.",
    ))

    # 28. NCATS Translator (Node Normalization + Name Resolution)
    add(SourceDefinition(
        key="ncats",
        display_name="NCATS Translator (Node Normalization + Name Resolution)",
        api_endpoint="https://nodenormalization-sri.renci.org",
        permitted_use=PermittedUse.METADATA_ONLY,
        license_class=LicenseClass.OPEN,
        identifier_types=[],
        query_params={"curies": ["CURIE list"], "string": "lexical name"},
        update_cadence=UpdateCadence.ON_DEMAND,
        attribution="NCATS Biomedical Data Translator (NIH).",
        retention_policy="Store input, preferred CURIE, equivalents, Biolink types, retrieval timestamp.",
        adapter_owner="engines/ncats_pipeline.py",
        version="1.0.0",
        docs_url="https://github.com/NCATSTranslator/ReasonerAPI",
        rate_limit="None published — client stays modest (>=1s between calls)",
        evidence_class="observed",
        notes="Identifier mappings only — not evidence of any association. Some upstream components carry distinct licenses (mixed).",
    ))

    # 29. Monarch Initiative
    add(SourceDefinition(
        key="monarch",
        display_name="Monarch Initiative",
        api_endpoint="https://api.monarchinitiative.org/v3/api",
        permitted_use=PermittedUse.METADATA_ONLY,
        license_class=LicenseClass.CUSTOM,
        identifier_types=[],
        query_params={"q": "search string", "category": "optional", "limit": 50},
        update_cadence=UpdateCadence.ON_DEMAND,
        attribution="Monarch Initiative. Code 3-Clause BSD; integrated-KG license mixed.",
        retention_policy="Store CURIE, name, category, retrieval timestamp. Do not redistribute bulk without license review.",
        adapter_owner="engines/monarch_pipeline.py",
        version="1.0.0",
        docs_url="https://monarch-initiative.github.io/monarch-documentation/",
        rate_limit="None published — client stays modest (>=1s between calls)",
        evidence_class="observed",
        notes="Schema pinned to v3. Integrated-KG license mixed/inconsistent — bulk redistribution UNVERIFIED. Published annotations, not clinical assertions.",
    ))

    # 30. MeSH
    add(SourceDefinition(
        key="mesh",
        display_name="MeSH (NLM)",
        api_endpoint="https://id.nlm.nih.gov/mesh",
        permitted_use=PermittedUse.METADATA_ONLY,
        license_class=LicenseClass.CUSTOM,
        identifier_types=[],
        query_params={"label": "descriptor label", "match": "exact"},
        update_cadence=UpdateCadence.ON_DEMAND,
        attribution="MeSH, National Library of Medicine.",
        retention_policy="Store descriptor ID, label, tree numbers, retrieval timestamp.",
        adapter_owner="engines/mesh_pipeline.py",
        version="1.0.0",
        docs_url="https://id.nlm.nih.gov/mesh/",
        rate_limit="None published — client stays modest (>=1s between calls)",
        evidence_class="observed",
        notes="Terminology bridge for query expansion — not an evidence corpus. NLM T&C specifics UNVERIFIED. ASCII serialization discontinued Jan 2026; JSON/RDF used.",
    ))

    return reg

# ---------------------------------------------------------------------------
# Registry Container
# ---------------------------------------------------------------------------

class SourceRegistry:
    """Versioned registry + health store. Importable, no extra deps."""
    REGISTRY_VERSION = "0.1.0-phase0"

    def __init__(self, definitions: Optional[Dict[str, SourceDefinition]] = None):
        self.definitions: Dict[str, SourceDefinition] = definitions or build_default_registry()
        self.health: Dict[str, SourceHealth] = {
            k: SourceHealth(key=k) for k in self.definitions
        }
        self._validate()

    def _validate(self):
        """Invariant checks: keys, enums, mock constraints."""
        for k, sd in self.definitions.items():
            assert sd.key == k, f"Key mismatch {sd.key} != {k}"
            assert isinstance(sd.permitted_use, PermittedUse)
            assert isinstance(sd.license_class, LicenseClass)
            if sd.permitted_use == PermittedUse.MOCK_ONLY:
                # Enforce MOCK_ONLY rule: must not promise real metrics
                assert "MOCK_ONLY" in sd.retention_policy, f"{k} MOCK_ONLY must note empty confidence"
                assert sd.evidence_class in ("predicted", "hypothesized"), f"{k} MOCK_ONLY should be predicted/hypothesized"

    # ----- Accessors -----
    def get(self, key: str) -> SourceDefinition:
        if key not in self.definitions:
            raise KeyError(f"Source {key!r} not in registry. Available: {list(self.definitions)}")
        return self.definitions[key]

    def list_keys(self) -> List[str]:
        return sorted(self.definitions.keys())

    def to_json(self, pretty: bool = True) -> str:
        """Export versioned catalog for evidence packet / audit."""
        payload = {
            "registry_version": self.REGISTRY_VERSION,
            "exported_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "sources": {k: asdict(v) for k, v in self.definitions.items()},
        }
        # Convert enums to values for JSON
        for src in payload["sources"].values():
            for f in ("permitted_use", "license_class", "update_cadence"):
                if isinstance(src[f], Enum):
                    src[f] = src[f].value
            src["identifier_types"] = [e.value if isinstance(e, Enum) else e for e in src["identifier_types"]]
        return json.dumps(payload, indent=2 if pretty else None, default=str)

    # ----- Health / Coverage View -----
    def update_health(self, key: str, success: bool, records_added: int = 0,
                      records_updated: int = 0, rate_limited: bool = False,
                      error_msg: Optional[str] = None,
                      upstream_update: Optional[dt.datetime] = None,
                      observed_version: Optional[str] = None):
        h = self.health[key]
        now = dt.datetime.now(dt.timezone.utc)
        h.last_attempt = now
        if success:
            h.last_success = now
            h.records_added += records_added
            h.records_updated += records_updated
            if upstream_update:
                h.last_upstream_update = upstream_update
            if observed_version:
                h.observed_upstream_version = observed_version
            h.last_error_message = None
        else:
            h.errors += 1
            h.last_error_message = error_msg
        if rate_limited:
            h.rate_limit_errors += 1
        h.compute_stale(self.definitions[key], now)

    def health_view(self) -> Dict[str, Any]:
        """Single source health/coverage view."""
        rows = []
        for k in self.list_keys():
            sd = self.definitions[k]
            h = self.health[k]
            h.compute_stale(sd)
            rows.append({
                "key": k,
                "display": sd.display_name,
                "permitted_use": sd.permitted_use.value,
                "license": sd.license_class.value,
                "update_cadence": sd.update_cadence.value,
                "version": sd.version,
                "upstream_pinned": sd.upstream_version_pinned,
                "observed_upstream": h.observed_upstream_version,
                **h.to_dict(),
            })
        # Partial-source warning summary
        stale = [r for r in rows if r["stale_warning"]]
        total_rate_limits = sum(r["rate_limit_errors"] for r in rows)
        return {
            "registry_version": self.REGISTRY_VERSION,
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "total_sources": len(rows),
            "stale_sources": len(stale),
            "total_rate_limit_errors": total_rate_limits,
            "disclosure": "Partial or unavailable sources must be disclosed in UX; no 'all research searched' assertion.",
            "sources": rows,
            "stale_details": [{"key": s["key"], "reason": s["stale_reason"]} for s in stale],
        }

    def coverage_disclosure(self) -> str:
        """Human-readable disclosure for UX footer."""
        hv = self.health_view()
        if hv["stale_sources"] == 0 and hv["total_rate_limit_errors"] == 0:
            return f"Source coverage: {hv['total_sources']} governed sources at registry {self.REGISTRY_VERSION}. All reachable at last check. Does NOT imply exhaustive literature coverage—indexes differ, some content licensed/delayed/not indexed."
        stale_list = ", ".join([d["key"] for d in hv["stale_details"]]) or "none"
        return (f"Source coverage: {hv['total_sources']} sources, {hv['stale_sources']} stale/never-success ({stale_list}), "
                f"{hv['total_rate_limit_errors']} rate-limit events. Results are source-traceable and limited to governed APIs. "
                f"Partial or unavailable sources disclosed. Not all research searched.")

# ---------------------------------------------------------------------------
# Contract Test Fixtures — deterministic, no network
# ---------------------------------------------------------------------------

def contract_test_fixtures() -> Dict[str, Dict[str, Any]]:
    """
    Returns deterministic fixtures for CI contract tests.
    Each fixture validates: identifier dedup, evidence envelope fields, MOCK_ONLY behavior.
    """
    now_iso = "2026-05-13T00:00:00Z"
    fixtures: Dict[str, Dict[str, Any]] = {}

    # PubMed fixture
    fixtures["pubmed"] = {
        "source_key": "pubmed",
        "sample_query": {"db": "pubmed", "query": "BRCA1 variant", "retmax": 2},
        "sample_response_doc": {
            "uids": ["12345678"],
            "result": {"12345678": {"pmid": "12345678", "doi": "10.1234/example", "title": "BRCA1 study", "pubdate": "2024-01-01"}},
        },
        "expected_evidence_envelope": {
            "stable_id": "PMID:12345678",
            "source_key": "pubmed",
            "source_url": "https://pubmed.ncbi.nlm.nih.gov/12345678/",
            "source_version": "2.0.0",
            "retrieval_timestamp": now_iso,
            "access_license_state": "open:metadata",
            "evidence_class": "observed",
            "identifier_types": ["PMID", "DOI"],
            "parse_warnings": [],
        },
        "dedup_key": "doi:10.1234/example",  # Crossref vs PubMed should dedup via DOI lowercasing
    }

    # ClinicalTrials v2 fixture
    fixtures["clinicaltrials_v2"] = {
        "source_key": "clinicaltrials_v2",
        "sample_query": {"query.term": "AREA[Condition]Alzheimer"},
        "sample_response_doc": {
            "nctId": "NCT04251164",
            "status": "RECRUITING",
            "hasResults": False,
            "version": "2024-03-01",
        },
        "expected_evidence_envelope": {
            "stable_id": "NCT:NCT04251164",
            "source_key": "clinicaltrials_v2",
            "source_url": "https://clinicaltrials.gov/study/NCT04251164",
            "source_version": "v2",
            "retrieval_timestamp": now_iso,
            "evidence_class": "observed",
        },
        "dedup_key": "nct:NCT04251164",
    }

    # AlphaFold DB MOCK_ONLY fixture — must enforce empty confidence
    fixtures["alphafold_db"] = {
        "source_key": "alphafold_db",
        "permitted_use": PermittedUse.MOCK_ONLY.value,
        "sample_query": {"uniprot_id": "P69905"},
        "mock_adapter_contract": {
            "must_return": {
                "status": "MOCK_ONLY",
                "confidence": None,  # empty confidence
                "plddt": None,
                "ptm": None,
                "structure_uri": None,
                "rank": None,
                "metrics_fabricated": False,
            },
            "must_not_contain": ["plDDT", "pLDDT_score", "structure_url_invented", "compound_ranking"],
            "explanation": "In this branch, structure adapters return MOCK_ONLY with empty confidence; real backend requires genuine execution provenance.",
        },
        "real_adapter_requirements_when_enabled": [
            "validated_request_payload",
            "job_lifecycle",
            "output_artifact_checks",
            "model/database/release_provenance",
            "license/terms_check",
            "resource_limits",
            "artifact_hash",
        ],
    }

    # ESM Atlas same
    fixtures["esm_atlas"] = {
        "source_key": "esm_atlas",
        "mock_adapter_contract": fixtures["alphafold_db"]["mock_adapter_contract"],
    }

    # Crossref dedup fixture
    fixtures["crossref"] = {
        "source_key": "crossref",
        "sample_response_doc": {"DOI": "10.1234/EXAMPLE", "title": ["BRCA1 study"], "type": "journal-article"},
        "dedup_normalization": {
            "input": ["10.1234/example", "10.1234/EXAMPLE ", "https://doi.org/10.1234/example"],
            "normalized": "doi:10.1234/example",
        },
        "expected_evidence_envelope": {
            "stable_id": "DOI:10.1234/example",
            "identifier_types": ["DOI"],
        },
    }

    # ClinVar fixture — preserve submitter/conflict
    fixtures["clinvar"] = {
        "source_key": "clinvar",
        "sample_response_doc": {
            "variation_id": 12345,
            "rcv": "RCV000001",
            "clinical_significance": "Pathogenic/Likely pathogenic",
            "review_status": "criteria provided, conflicting interpretations",
            "submitters": ["GeneDx", "Invitae"],
            "last_evaluated": "2023-06-01",
        },
        "evidence_handling_rule": "Do not collapse into ground truth; preserve conflicts, review_status, dates.",
    }

    # Retraction / correction fixture
    fixtures["retraction_handling"] = {
        "rule": "Represent retractions/corrections and preprint/publication links explicitly.",
        "example": {
            "pmid_original": "11111111",
            "pmid_retraction_notice": "22222222",
            "crossref_crossmark": {"is_retracted": True, "update_type": "retraction"},
            "expected_graph": {
                "edge_type": "corrects/retracts",
                "retain_both_nodes": True,
                "do_not_silently_merge": True,
            },
        },
    }

    # Health view fixture
    fixtures["_health_view"] = {
        "simulate": {
            "pubmed": {"success": True, "records_added": 10, "observed_version": "2024-01"},
            "clinicaltrials_v2": {"success": False, "rate_limited": True, "error_msg": "429 Rate limit"},
        },
        "expect_stale_warning_logic": True,
    }

    return fixtures


def run_contract_tests(verbose: bool = False) -> Tuple[bool, List[str]]:
    """
    Runs deterministic contract tests without network.
    Returns (passed, messages).
    """
    msgs: List[str] = []
    ok = True
    registry = SourceRegistry()
    fixtures = contract_test_fixtures()

    # 1. All required sources present
    required = ["pubmed", "europe_pmc", "clinicaltrials_v2", "openfda",
                "alphafold_db", "esm_atlas", "lens_patents", "clinvar",
                "ensembl", "gnomad", "gtex", "biorxiv", "arxiv", "crossref",
                "usgs", "noaa"]
    for k in required:
        if k not in registry.definitions:
            ok = False
            msgs.append(f"FAIL: required source {k} missing")
        else:
            msgs.append(f"PASS: source {k} present v{registry.definitions[k].version}")

    # 2. MOCK_ONLY returns empty confidence contract
    for k in ["alphafold_db", "esm_atlas"]:
        sd = registry.definitions[k]
        if sd.permitted_use != PermittedUse.MOCK_ONLY:
            ok = False
            msgs.append(f"FAIL: {k} must be MOCK_ONLY in Phase0, got {sd.permitted_use}")
        else:
            msgs.append(f"PASS: {k} is MOCK_ONLY with empty confidence contract")

    # 3. Health view structure
    hv = registry.health_view()
    required_health_fields = ["last_success", "rate_limit_errors", "records_added", "stale_warning"]
    sample = hv["sources"][0]
    for f in required_health_fields:
        if f not in sample:
            ok = False
            msgs.append(f"FAIL: health_view missing field {f}")
    msgs.append(f"PASS: health_view fields {required_health_fields} present")

    # 4. Deduplication normalization logic (deterministic)
    def normalize_doi(raw: str) -> str:
        raw = raw.strip().lower()
        if raw.startswith("https://doi.org/"):
            raw = raw.replace("https://doi.org/", "")
        if raw.startswith("doi:"):
            raw = raw[4:]
        return f"doi:{raw.strip()}"
    inp = fixtures["crossref"]["dedup_normalization"]["input"]
    expected = fixtures["crossref"]["dedup_normalization"]["normalized"]
    for i in inp:
        if normalize_doi(i) != expected:
            ok = False
            msgs.append(f"FAIL: DOI norm {i!r} -> {normalize_doi(i)!r} != {expected!r}")
    msgs.append(f"PASS: DOI dedup normalization deterministic")

    # 5. Evidence envelope required fields
    for key in ["pubmed", "clinicaltrials_v2"]:
        env = fixtures[key]["expected_evidence_envelope"]
        for ef in ["stable_id", "source_key", "source_url", "retrieval_timestamp", "evidence_class"]:
            if ef not in env:
                ok = False
                msgs.append(f"FAIL: evidence envelope missing {ef} in fixture {key}")
    msgs.append("PASS: evidence envelope contains required fields")

    if verbose:
        for m in msgs:
            print(m)
    return ok, msgs


# ---------------------------------------------------------------------------
# Optional: Minimal evidence envelope builder (no fabricated metrics)
# ---------------------------------------------------------------------------

def build_evidence_envelope(
    source_key: str,
    stable_id: str,
    source_url: str,
    registry: Optional[SourceRegistry] = None,
    evidence_class: Optional[str] = None,
    access_license_state: Optional[str] = None,
    parse_warnings: Optional[List[str]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Builds source-traceable envelope. Never fabricates pLDDT/pTM/rank.
    If source is MOCK_ONLY, confidence must be None/empty.
    """
    reg = registry or SourceRegistry()
    sd = reg.get(source_key)
    if sd.permitted_use == PermittedUse.MOCK_ONLY:
        # Enforce empty-confidence rule per roadmap acceptance criteria
        envelope = {
            "stable_id": stable_id,
            "source_key": source_key,
            "source_url": source_url,
            "source_version": sd.version,
            "upstream_version_pinned": sd.upstream_version_pinned,
            "retrieval_timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
            "permitted_use": sd.permitted_use.value,
            "license_class": sd.license_class.value,
            "evidence_class": sd.evidence_class,
            "status": "MOCK_ONLY",
            "confidence": None,
            "plddt": None,
            "ptm": None,
            "structure_uri": None,
            "ranking": None,
            "disclosure": "MOCK_ONLY: no invented metrics, no structure URI, no synthetic compound ranking",
        }
        return envelope

    return {
        "stable_id": stable_id,
        "source_key": source_key,
        "source_url": source_url,
        "source_version": sd.version,
        "upstream_version_pinned": sd.upstream_version_pinned,
        "retrieval_timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "permitted_use": sd.permitted_use.value,
        "license_class": sd.license_class.value,
        "evidence_class": evidence_class or sd.evidence_class,
        "access_license_state": access_license_state or f"{sd.license_class.value}:{sd.permitted_use.value}",
        "attribution": sd.attribution,
        "parse_warnings": parse_warnings or [],
        **(extra or {}),
    }


# ---------------------------------------------------------------------------
# CLI self-test if run as module
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    passed, messages = run_contract_tests(verbose=True)
    print("\n--- Registry JSON excerpt ---")
    reg = SourceRegistry()
    print(reg.to_json()[:2000] + "\n...")
    print("\n--- Health View ---")
    print(json.dumps(reg.health_view(), indent=2)[:3000])
    print("\nContract tests passed:" if passed else "\nContract tests FAILED:")
    print(passed)
